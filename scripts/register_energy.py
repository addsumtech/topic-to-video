#!/usr/bin/env python3
"""Measure EVERY register as a moving picture, not a still — the library-wide energy diagnostic.

    python3 scripts/register_energy.py            # measure all, write the manifest, print the ranking
    python3 scripts/register_energy.py --only A,B  # a few
    python3 scripts/register_energy.py --report    # re-print the ranking from the manifest, render nothing
    python3 scripts/register_energy.py --check     # which rows no longer describe their source (no renders)
    python3 scripts/register_energy.py --dna=none  # ...measured un-themed instead (the fallback path)

WHY. `film_energy_qa.py` judges a delivered FILM. It found one this skill shipped measuring 3.3x under the
quietest reference launch film on motion, 5.6x on density and 3.4x on light — but a film is only as alive as
the beats in it, and nothing has ever measured a beat. Every visual gate here reads a STILL: shot_still_qa,
frame_safe_qa, keyframe_qa_remotion, the contact sheet the critic reads. A register can be perfectly composed
in every still and completely inert as five seconds of film, and the entire pipeline will call it good.

So this renders each register as VIDEO at its own DURATION with its own default props and measures the same
three axes. Default props are the only uniform basis (the same choice band_debt.py makes); a register that
looks dead here may come alive with real content, which is why the manifest records numbers rather than
verdicts.

It also writes three frames per register (early / settled / late) into `--stills`, so a design review can look
at what the numbers are describing instead of trusting them.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c                                                  # noqa: E402
import film_energy_qa as fe                                      # noqa: E402
import render_remotion as rr                                     # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REMOTION = os.path.join(_ROOT, "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
MANIFEST = os.path.join(_REMOTION, "register_energy.json")
# Below this footprint an empty frame is empty because the COMPOSITION is small; above it, because the
# composition spans the frame and has no tone. Set between the two clusters measured on the sparsest
# registers a delivered film used (9-19% against 53-57%), which is where the gap actually is.
FOOTPRINT_SPLIT = 0.35
REGEN = "python3 scripts/register_energy.py"


_FIXTURE_REL = "_energy_fixture.png"


# A register whose evidence is more than one image. `PageWrite` films a CAPTURED page and needs both halves
# of that capture — the texture and the boxes measured from the same load — so a `src` alone leaves it
# throwing. Written out rather than inferred, for the reason `cjk_type_qa._ARRAY_SHAPES` gives: a wrong shape
# renders nothing and reads as "this register is fine". The demo artefact is a page THIS repo generated
# (public/textures/demo-report.html), captured by scripts/capture_page.py — never a customer's document.
def _page_fixture():
    """The demo capture, STAGED into the public dir the way the drawn fixture is.

    It lives tracked under `remotion/fixtures/` and is copied into `public/textures/` on demand, because
    `remotion/public/` is git-ignored on purpose — it is the per-film staging directory, wiped and refilled
    by every render. A fixture committed into a disposable directory is one a fresh clone does not have, and
    the way that fails is a permanent "PageWrite RENDER FAILED" that reads as a broken register.

    The artefact is a page THIS repo generates (`fixtures/demo-report.html`, captured by
    scripts/capture_page.py) — never a customer's document.
    """
    import shutil
    src_dir = os.path.join(_REMOTION, "fixtures")
    dst_dir = os.path.join(_REMOTION, "public", "textures")
    try:
        with open(os.path.join(src_dir, "demo-report.layout.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        os.makedirs(dst_dir, exist_ok=True)
        png = os.path.join(dst_dir, "demo-report.png")
        if not os.path.exists(png):
            shutil.copy2(os.path.join(src_dir, "demo-report.png"), png)
    except (OSError, ValueError):
        return None
    return {"src": "textures/demo-report.png", "pageW": d["pageW"], "pageH": d["pageH"],
            "bg": d.get("bg", "#ffffff"), "blocks": d["blocks"]}


def evidence_props():
    """{register: {prop: fixture path}} — DERIVED from each shot's own `requireEvidence(...)` call.

    Four registers exist to put a real photograph on the frame and now REFUSE to draw without one
    (runtime/evidence.ts). Sweeping them with default props would therefore record four permanent failures,
    and sweeping them BEFORE that guard existed recorded something worse: PhotoPlate at 0.6% and RealVersus
    at 0.0%, which are measurements of an empty box, not of a register. An empty plate measured as a register
    is a lie the sweep was telling.

    The list is parsed, not restated: a fifth register that adopts the guard is measured with a fixture the
    day it does, and one that drops it stops being special without anyone remembering to edit this file."""
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        n = os.path.basename(f)[:-4]
        for m in re.finditer(r"requireEvidence\(\s*'([A-Za-z0-9]+)'\s*,\s*'([A-Za-z0-9]+)'", src):
            out.setdefault(m.group(1), {})[m.group(2)] = _FIXTURE_REL
        if n in out:
            # a paired register (srcLeft/srcRight) guards only one of them; fill every src-shaped prop it
            # declares, or half the frame is still the hole this exists to end
            head = re.search(r"export const %s: React\.FC<\{(.*?)\}> =" % n, src, re.S)
            if head:
                for pm in re.finditer(r"\b(src[A-Za-z0-9]*)\s*\?\s*:", head.group(1)):
                    out[n][pm.group(1)] = _FIXTURE_REL
    # A register whose evidence is a CAPTURED PAGE needs both halves of that capture, and which ones those
    # are is read from their own signatures rather than listed here — a restated list drifts, which is the
    # whole reason the block above parses the call sites instead of naming them.
    page = _page_fixture()
    if page:
        for n in list(out):
            sig = open(os.path.join(_SHOTS, n + ".tsx"), encoding="utf-8").read()
            if re.search(r"\bblocks\s*\?\s*:\s*\w*Block\[\]", sig):
                out[n] = dict(page)      # a page texture and its boxes, not the photograph stand-in

    # ...AND A REGISTER WHOSE EVIDENCE IS A LIST OF PICTURES. `requireEvidence` names ONE `src` prop, so a
    # register that draws N images — `StateSheet`'s `cells: {src: string; label?: string}[]` — matched
    # nothing above and was measured by rendering its defaults, which is an empty sheet: it threw, and the
    # three measurement scripts each recorded RENDER FAILED. That is the same lie this whole function
    # exists to end, one shape further out — the register is fine, the fixture was missing.
    #
    # Which prop it is comes from the TYPE (an array whose element declares a `src: string`), never from a
    # name written here, so the next register to take a list of pictures is fed the day it is written.
    #
    # ...AND EVERY SUCH PROP, NOT THE FIRST ONE. This stopped at the first match and skipped any register
    # already carrying a `requireEvidence` fixture, which left `StateSheet.family` — a SECOND list of
    # pictures, the strip of siblings under the sheet — filled by whatever the caller had: `cjk_type_qa`
    # hands every string field a sentence of Chinese copy, so `<Img src={staticFile('它自己拆解任务…')}>` 404'd
    # and the render died. `prop_reach` recorded that as "StateSheet: empty frame or render failure", which
    # is the gate's own input blamed on the register — the same shape as the probe DNA that made
    # `CardStack3D` "refuse to render" for eleven sweeps. Fill them all; skip only a prop already filled
    # above, because the captured page and the guarded `src` are more specific answers than this one.
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        n = os.path.basename(f)[:-4]
        head = re.search(r"export const %s: React\.FC<\{(.*?)\}>\s*=" % re.escape(n), src, re.S)
        if not head:
            continue
        for pm in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:\s*"
                              r"(\{[^{}]*\}|[A-Z][A-Za-z0-9_]*)\[\]", head.group(1)):
            prop, ty = pm.group(1), pm.group(2)
            if prop in out.get(n, {}):
                continue
            body = ty[1:-1] if ty.startswith("{") else ""
            if not body:
                m = re.search(r"type\s+%s\s*=\s*\{([^{}]*)\}" % re.escape(ty), src, re.S)
                body = m.group(1) if m else ""
            if not re.search(r"\bsrc\s*\??\s*:\s*string", body):
                continue
            label = re.search(r"\b(label|name|caption|title)\s*\??\s*:\s*string", body)
            cell = {"src": _FIXTURE_REL}
            if label:
                cell[label.group(1)] = "fixture"
            out.setdefault(n, {})[prop] = [dict(cell) for _ in range(6)]
    return out


def ensure_fixture():
    """A deterministic stand-in photograph in remotion/public/, drawn rather than committed.

    Drawn from a fixed formula so two sweeps on two machines measure the same pixels, and NOT a real
    photograph: the sweep is measuring what a register does with an image, not which image."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    pub = os.path.join(_REMOTION, "public")
    os.makedirs(pub, exist_ok=True)
    path = os.path.join(pub, _FIXTURE_REL)
    if os.path.exists(path):
        return _FIXTURE_REL
    w, h = 1400, 933
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            # a smooth field plus a coarse grid: mid-tone overall, with structure, like a photograph's
            v = 60 + int(90 * (x / w)) + int(50 * (y / h))
            if (x // 70 + y // 70) % 2 == 0:
                v = min(255, v + 34)
            px[x, y] = (v, min(255, int(v * 0.94)), min(255, int(v * 0.86)))
    d = ImageDraw.Draw(im)
    d.ellipse([w * 0.28, h * 0.24, w * 0.72, h * 0.78], fill=(232, 226, 214))
    d.rectangle([w * 0.08, h * 0.66, w * 0.30, h * 0.92], fill=(38, 42, 52))
    im.save(path)
    return _FIXTURE_REL


_IMPORT = re.compile(r"""^\s*import\s[^'"]*['"](\.[^'"]+)['"]""", re.M)


def _deps(path, seen=None):
    """Every project file a register's picture is drawn from — its own source and, transitively, the runtime
    modules it imports.

    Hashing the .tsx alone was right while every register drew itself. It stopped being right the moment two
    of them shared a visual primitive: `uiSurface` decides what `SurfaceCarousel` and `PointerTour` actually
    look like, so editing it changes both pictures while leaving both hashes untouched — a row that reads as
    measured and describes a frame that no longer exists. That is the exact failure this function was written
    to end, one level up. Following the imports keeps the answer precise instead of invalidating the whole
    manifest whenever anything in `runtime/` moves.
    """
    seen = set() if seen is None else seen
    path = os.path.realpath(path)
    if path in seen or not os.path.exists(path):
        return seen
    seen.add(path)
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return seen
    base = os.path.dirname(path)
    for rel in _IMPORT.findall(src):
        for ext in (".tsx", ".ts", "/index.tsx", "/index.ts", ""):
            cand = os.path.join(base, rel + ext)
            if os.path.isfile(cand):
                _deps(cand, seen)
                break
    return seen


def source_hash(name):
    """sha256 over ONE register's .tsx and every runtime module it imports, read NOW.

    Read now, and per register, because a full sweep is a two-and-a-half hour render and the source can move
    under it. Hashing the whole library once at the start and again at the end both lie, in opposite
    directions: the first records a hash for pixels rendered from a later edit, the second — which this file
    did — records the FINAL source against pixels rendered from the earlier one, so the row looks fresh and
    is not, and `stale()` reports nothing. That is the exact failure this hash exists to catch, produced by
    the code that writes it. Hashing immediately before the render makes the recorded hash describe the
    bytes the render actually read, whatever happens to the file afterwards.
    """
    f = os.path.join(_SHOTS, name + ".tsx")
    h = hashlib.sha256()
    for dep in sorted(_deps(f)):
        h.update(_dep_bytes(dep, name))
    return h.hexdigest()[:16]


# A PER-REGISTER TABLE IS NOT SHARED CODE. `runtime/shotLuma.ts` is one line per shot, and every register
# that reads it imports the whole file — so REGISTERING a new shot, or re-measuring one shot's ground,
# rewrote the table and marked every other reader's energy row stale. Nothing about their pictures had
# changed. A sweep is a two-and-a-half hour render, so a check that cries wolf here is a check that gets
# answered by re-measuring the whole library or by ignoring it; this repo has already recorded both.
# What a reader actually depends on is the file's CODE plus its OWN row, so that is what is hashed.
_LUMA_ENTRY = re.compile(r"^\s*(?:'|\")?([A-Za-z][A-Za-z0-9_]*)(?:'|\")?\s*:\s*'(?:dark|mid|light)'\s*,?",
                         re.M)


# ...AND THE ALLOW LIST IS A PER-REGISTER TABLE TOO. `GROUND_FOLLOWS_MEASURED` lives in the same file, and
# `measure_ground_reach.py --emit` rewrites it whenever ANY register's ground behaviour is re-measured — so
# merging one row staled 29 registers whose pixels had not moved, through `light.tsx`, which imports this
# file. Same rule as the luminance table: a reader depends on the module's CODE and on its OWN membership.
_FOLLOWS_BLOCK = re.compile(r"(GROUND_FOLLOWS_MEASURED[^=]*=\s*new Set\(\[)(.*?)(\]\))", re.S)


# ── SYMBOL REACHABILITY ───────────────────────────────────────────────────────────────────────────────
# A REGISTER DEPENDS ON THE SYMBOLS IT USES, NOT ON EVERY BYTE OF THE FILE THEY LIVE IN.
#
# `_deps` already narrowed this once, from "anything in runtime/ moved" to "a module this register
# imports moved", and the two per-register tables below narrowed it twice more. What was left is still
# the dominant cost: `runtime/dna.tsx` is imported by all 174 registers (every one of them calls
# `useDNA`), so ANY edit to it invalidates the entire manifest. Measured on the session that motivated
# this: adding `plane` — a new export nothing imported yet — staled 174 rows, and changing
# `separatedPair`, which exactly ONE register imports (`VersusSplit`), staled 174 rows again. Each of
# those cost a ~20 min prop_reach sweep plus a ~29 min register_energy sweep to answer a question whose
# true answer was "0 rows" and "1 row". The file's own comment on `shotLuma.ts` already says why that
# matters: "a check that cries wolf here is a check that gets answered by re-measuring the whole library
# or by ignoring it; this repo has already recorded both."
#
# So a DIRECTLY imported module is hashed as: its preamble (imports, module-level statements — anything
# before the first top-level declaration) plus the bodies of the top-level symbols REACHABLE from the
# names this register actually imports. Reachability is deliberately an OVER-approximation: a symbol is
# pulled in when its identifier appears anywhere in an included body, comments included. Over-approximating
# can only ever hash too much, which costs a needless re-measure; it can never mark a row fresh whose
# pixels moved, which is the failure the hash exists to catch. Anything this cannot parse with confidence
# — a default import, a namespace import, a module with no recognisable declarations — falls back to the
# whole file. Transitive modules (imported by a module rather than by the register) are hashed whole too:
# narrowing those needs the closure across module boundaries and the measured cost is not there.
_TOP_DECL = re.compile(r"^(?:export\s+)?(?:declare\s+)?(?:const|let|var|function|class|type|interface|enum)"
                       r"\s+([A-Za-z_$][\w$]*)", re.M)
_NAMED_IMPORT = re.compile(r"""^\s*import\s*\{([^}]*)\}\s*from\s*['"](\.[^'"]+)['"]""", re.M)
_BARE_IMPORT = re.compile(r"""^\s*import\s+(?!\{|type\s*\{)[A-Za-z_$*][^'"]*from\s*['"](\.[^'"]+)['"]""", re.M)


def _imported_names(register_src, dep_path, register_dir):
    """The names `register_src` imports from `dep_path`, or None when it cannot be narrowed safely."""
    want = None
    for spec in _BARE_IMPORT.findall(register_src):          # default or namespace import → cannot narrow
        if _resolve_rel(spec, register_dir) == dep_path:
            return None
    for names, spec in _NAMED_IMPORT.findall(register_src):
        if _resolve_rel(spec, register_dir) != dep_path:
            continue
        want = set() if want is None else want
        for n in names.split(","):
            n = n.strip()
            if not n:
                continue
            n = n.split(" as ")[0].strip()                   # `mix as blend` still depends on `mix`
            n = re.sub(r"^type\s+", "", n).strip()
            if n:
                want.add(n)
    return want


def _resolve_rel(spec, base):
    for ext in (".tsx", ".ts", "/index.tsx", "/index.ts", ""):
        cand = os.path.realpath(os.path.join(base, spec + ext))
        if os.path.isfile(cand):
            return cand
    return None


# The narrowing is a REGEX CLOSURE over every symbol of every module a register imports, and `source_hash`
# is called per register by `stale()`, which the gates and the tests call constantly. Unmemoised it took a
# full `source_hashes()` from milliseconds to 9.6s and the test suite from 13 minutes to 66 — a performance
# regression introduced by a performance fix. Keyed on (path, mtime_ns, size) so an edit DURING a sweep is
# still picked up, which is the property the per-register re-read exists for in the first place.
_BLOCK_CACHE = {}
_NARROW_CACHE = {}
_IMPORTS_CACHE = {}


def _stamp(path):
    try:
        st = os.stat(path)
        return (path, st.st_mtime_ns, st.st_size)
    except OSError:
        return (path, None, None)


def _blocks_of(path, src):
    key = _stamp(path)
    hit = _BLOCK_CACHE.get(key)
    if hit is None:
        marks = [(m.start(), m.group(1)) for m in _TOP_DECL.finditer(src)]
        if not marks:
            hit = (None, None)
        else:
            # A BLOCK ENDS BEFORE THE COMMENTS THAT INTRODUCE THE NEXT ONE. Splitting at the next
            # declaration's first character attributes the doc-comment ABOVE it to the PREVIOUS symbol —
            # measured: adding `cadenceAt` to runtime/motion.ts, with its header written above it, staled
            # 88 of 174 rows because that header landed inside `easeOutBack`, which most of the library
            # imports. Nothing about those registers' pixels had moved. The trailing run of comment and
            # blank lines is trimmed off each block, so a note written for the next symbol belongs to the
            # next symbol — and it is not dropped, because that symbol's own span starts where it ends.
            blocks, starts = {}, [q for q, _ in marks] + [len(src)]
            for i, (pos, nm) in enumerate(marks):
                body = src[pos:starts[i + 1]]
                if i + 1 < len(marks):
                    lines = body.split("\n")
                    while lines and (not lines[-1].strip()
                                     or lines[-1].lstrip().startswith(("//", "/*", "*", "*/"))):
                        lines.pop()
                    body = "\n".join(lines)
                blocks[nm] = blocks.get(nm, "") + body
            hit = (src[: marks[0][0]], blocks)
        _BLOCK_CACHE[key] = hit
    return hit


_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_GRAPH_CACHE = {}


def _mentions_of(path, blocks):
    """{symbol: the other top-level symbols its body mentions} — built once per file version."""
    key = _stamp(path)
    hit = _GRAPH_CACHE.get(key)
    if hit is None:
        names = set(blocks)
        hit = {k: {n for n in _IDENT.findall(v) if n in names} for k, v in blocks.items()}
        _GRAPH_CACHE[key] = hit
    return hit


def _narrowed(src, want, path=None):
    """`src` reduced to its preamble + the top-level symbols reachable from `want`, or None if unparseable."""
    ckey = (_stamp(path) if path else None, frozenset(want))
    if ckey[0] is not None and ckey in _NARROW_CACHE:
        return _NARROW_CACHE[ckey]
    preamble, blocks = _blocks_of(path, src) if path else (None, None)
    if blocks is None:
        if path:
            _NARROW_CACHE[ckey] = None
        return None
    keep = {w for w in want if w in blocks}
    if len(keep) != len(want):
        if path:
            _NARROW_CACHE[ckey] = None
        return None                                          # imports a name this file does not declare
    # The closure walks a symbol->mentions GRAPH built once per file, not a regex re-scan of the joined
    # bodies per iteration: that inner loop was O(rounds x symbols x bytes) and cost 9.6s for one
    # `source_hashes()`. Same over-approximation — a symbol is a dependency when its identifier appears
    # anywhere in a body, comments included — computed by extracting identifiers instead of searching for
    # each name in turn.
    graph = _mentions_of(path, blocks) if path else {
        k: {n for n in _IDENT.findall(v) if n in blocks} for k, v in blocks.items()}
    todo = list(keep)
    while todo:
        for nm in graph.get(todo.pop(), ()):  # noqa: B007
            if nm not in keep:
                keep.add(nm)
                todo.append(nm)
    # Each block is rstripped: the LAST declaration's span runs to end-of-file, so a file that merely gains
    # a trailing newline — or a new declaration appended after it — moved that block's text and staled 29
    # rows whose symbols had not changed. Only TRAILING whitespace is touched; whitespace INSIDE a block can
    # be load-bearing (a template literal's spacing reaches the frame), so it is hashed as written.
    out = preamble.rstrip() + "".join(blocks[k].rstrip() for k in sorted(keep))
    if path:
        _NARROW_CACHE[ckey] = out
    return out


def _dep_bytes(dep, name):
    if os.path.basename(dep) != "shotLuma.ts":
        raw = open(dep, "rb").read()
        # narrow a DIRECTLY imported module to the symbols this register reaches (see above). Any doubt —
        # an unparseable module, a default/namespace import, a name the module does not declare — keeps the
        # whole file, so the hash is never narrower than what the register actually reads.
        own = os.path.join(_SHOTS, name + ".tsx")
        try:
            ikey = (_stamp(own), os.path.realpath(dep))
            if ikey in _IMPORTS_CACHE:
                want = _IMPORTS_CACHE[ikey]
            else:
                want = _imported_names(open(own, encoding="utf-8").read(), os.path.realpath(dep), _SHOTS)
                _IMPORTS_CACHE[ikey] = want
            if want:
                cut = _narrowed(raw.decode("utf-8"), want, os.path.realpath(dep))
                if cut is not None:
                    return cut.encode("utf-8")
        except (OSError, UnicodeDecodeError, re.error):
            pass
        return raw
    src = open(dep, encoding="utf-8").read()
    m = _FOLLOWS_BLOCK.search(src)
    if m:
        listed = "yes" if re.search(r"'%s'" % re.escape(name), m.group(2)) else "no"
        src = src[:m.start()] + m.group(1) + " /*follows:" + listed + "*/ " + m.group(3) + src[m.end():]
    mine = [m2.group(0).strip() for m2 in _LUMA_ENTRY.finditer(src) if m2.group(1) == name]
    # entries can share a line; drop every entry from the text, then add back only this register's
    stripped = _LUMA_ENTRY.sub("", src)
    stripped = re.sub(r"\b([A-Za-z][A-Za-z0-9_]*)\s*:\s*'(?:dark|mid|light)'\s*,?", "", stripped)
    # ...and the WHITESPACE the removals leave behind is normalised, or the hash still moves when a row that
    # shared a line with another register is taken out and the line collapses differently.
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return (stripped + " | " + " ".join(sorted(mine))).encode("utf-8")


def source_hashes():
    """{register: sha256 over its .tsx AND the runtime modules it imports}. A measured row describes the
    SOURCE it was rendered from, and nothing said so: three registers were rewritten and the committed
    manifest went on reporting 0.6%, 2.0% and 1.0% against measured 32.2%, 51.1% and 2.4%, while
    `density_advice.py` — which reads this file — kept offering one of the densest registers in the library as
    a starved beat's problem. A record nobody can tell is stale is not a record, it is a lie with a
    timestamp."""
    return {n: source_hash(n) for n in universe()}


def fed_hash(name, ev=None):
    """sha256 over the ARTEFACTS a register was fed — its evidence props and the bytes of any file they name.

    The cache key below has always included these, because the pixels depend on them. The MANIFEST did not,
    so a row measured with half a fixture read as fresh forever: `StateSheet` declares two picture lists and
    `evidence_props()` filled only the first, and when that was repaired its committed row still described
    the old render (ink 11.6% against 8.9%, footprint 27.1% against 37.6%) with `--check` reporting OK. A
    row that cannot be told stale is the lie this file already refuses one dimension of.

    ...AND A FIXTURE IN A SUBDIRECTORY IS STILL A FIXTURE. This read only artefacts sitting at the top of
    `public/`, so `PageWrite` — whose entire evidence is `textures/demo-report.png` — had NONE of its
    picture's bytes in its hash, only the layout numbers beside it. Re-capture that page with different
    pixels at the same page size and the row reads fresh forever: the same lie as above, one directory
    deeper, on the one register whose artefact this repo actually regenerates. Containment is now checked
    by resolving the path instead of by banning the separator, which is what the ban was standing in for —
    an absolute path or one climbing out of `public/` is refused, a nested one is read.
    """
    ev = evidence_props() if ev is None else ev
    props = ev.get(name)
    if not props:
        return ""
    blob = json.dumps(props, sort_keys=True)
    h = hashlib.sha256(blob.encode())
    pub = os.path.realpath(os.path.join(_REMOTION, "public"))
    for v in sorted(blob.split('"')):
        if not v:
            continue
        f = os.path.realpath(os.path.join(pub, v))
        if f.startswith(pub + os.sep) and os.path.isfile(f):
            h.update(open(f, "rb").read())
    return h.hexdigest()[:10]


def register_maps(data):
    """The manifest's top-level keys whose value is a map KEYED BY REGISTER NAME — what `--only` must merge.

    Structural, never a list, because the list IS the bug. `_source` was merged forward by name and `_fed`
    — added later, for the artefact a register was fed — was not, so every targeted re-measure replaced the
    whole map with the one or two registers that run had touched. The other evidence registers lost their
    recorded artefact hash, `stale()` reads an absent hash as a changed one, and re-measuring THOSE evicted
    the first the same way: a manifest that no sequence of sweeps could bring to zero stale rows. That is
    the record-nobody-can-tell-is-stale `source_hashes` refuses, arrived at from the opposite side — not a
    row that cannot be told stale, but one that cannot be told fresh, which teaches a reader to ignore the
    check entirely.

    Read off the FRESH `data`, never the file on disk: its maps are built from this run's own rows, so a
    register deleted from the library cannot make a map stop looking like one and silently opt out."""
    names = set(universe())
    return [k for k, v in data.items()
            if k.startswith("_") and isinstance(v, dict) and set(v) <= names]


def stale(data):
    """[(register, why)] for rows that no longer describe their source. Costs no renders, so it can run
    anywhere — which is the point: a check that needs 149 renders is a check nobody runs."""
    now = source_hashes()
    rows = data.get("registers") or {}
    was = data.get("_source") or {}
    # the SECOND dimension: rows written before this existed carry no `_fed`, and are left to the source
    # check alone rather than all being declared stale at once
    fed_was = data.get("_fed") or {}
    try:
        ev_now = evidence_props()
        fed_now = {n: fed_hash(n, ev_now) for n in rows}
    except Exception:
        fed_now = {}
    out = []
    for n in sorted(rows):
        if n not in now:
            out.append((n, "the register is gone"))
        elif n not in was:
            out.append((n, "measured before source hashes were recorded"))
        elif was[n] != now[n]:
            out.append((n, "source changed since it was measured"))
        elif fed_was and n in fed_now and fed_was.get(n, "") != fed_now[n]:
            out.append((n, "the artefact it was fed changed since it was measured (evidence fixture)"))
    for n in sorted(set(now) - set(rows)):
        out.append((n, "never measured"))
    return out


def floors():
    """The floors, TAKEN from film_energy_qa — never restated.

    Restating them is how this repo's caption band became four disagreeing copies. A diagnostic that ranks
    registers against a private copy of the numbers would keep ranking against them after the real gate moved.
    """
    # ...EXCEPT INK, WHICH NO LONGER HAS ONE TO TAKE. `film_energy_qa` retired the absolute ink floor with
    # the metric that could not tell a drawn frame from a blurred blank one, and did NOT re-guess a
    # replacement — its reference films were measured under the old definition and are not in the repo. A
    # diagnostic cannot invent the constant the gate refused to invent. So the register-level ink cut is
    # taken from the LIBRARY'S OWN distribution instead: the bottom fifth of 174 measured registers is a
    # fact about this library, needs no corpus, and moves with the library as it grows. `_floors()` fills
    # it in at sweep time from the rows it just measured; the two axes that still have derived floors keep
    # taking them from the gate, never restating them.
    # ...AND NEITHER DOES LIGHT, for a reason the ink note above states and nobody carried across.
    # `fe.LUMA_RANGE_FLOOR` is 0.135 — half the LOWEST reference LAUNCH FILM (Apple, 0.270) — and a film's
    # luminance range is mostly the CUT: it comes from moving between a dark beat and a light one, which is
    # what `luma_steps` measures as the arc. A single register paints on ONE ground by construction
    # (`DNA_GROUND_TOKEN` records which token each one takes, and 148 of them take `bg`), so it cannot
    # produce a film's range and was never the thing that number described.
    #
    # Measured before this was changed: 147 of 180 registers clear the ink cut, 63 clear motion, and **12
    # clear light — the same 12 that clear all three**, verified as set equality. So "clears all three" was
    # the light axis wearing three hats, and the twelve are the registers whose own composition happens to
    # span dark to light (`PageWrite` is a white page on a dark ground; `RealVersus` is photographs) rather
    # than the registers with an arc. Judging one shot against a whole film's number is the same category
    # error the ink floor was retired for, one axis over.
    #
    # The gate keeps its constant, because there it judges FILMS and is right. Here the reference is the
    # library's own distribution, which needs no corpus of single-register reference renders — there is no
    # such corpus and inventing one is the thing `film_energy_qa` refused to do.
    return {"motion_p75": fe.MOTION_P75_FLOOR, "ink_median": None, "luma_range": None}


INK_QUINTILE = 0.20           # "under-inked" = the bottom fifth of the library's own measured distribution


def _ink_cut(rows):
    """The ink level below which a register is in this LIBRARY's bottom fifth. None when nothing measured."""
    vals = sorted(v["ink_median"] for v in rows.values() if v.get("ink_median") is not None)
    if len(vals) < 5:
        return None
    return vals[max(0, int(len(vals) * INK_QUINTILE) - 1)]


LIGHT_QUINTILE = 0.20         # "flat" = the bottom fifth of the library's own measured light range


def _light_cut(rows):
    """The luminance range below which a register is in this LIBRARY's bottom fifth. None under 5 rows.

    The same shape as `_ink_cut` and for the same reason — see `floors()`. Kept as a separate function
    rather than one parameterised by key, because the two are separate DECISIONS: if the gate ever gains a
    per-register light reference, this is what gets deleted and ink stays."""
    vals = sorted(v["luma_range"] for v in rows.values() if v.get("luma_range") is not None)
    if len(vals) < 5:
        return None
    return vals[max(0, int(len(vals) * LIGHT_QUINTILE) - 1)]


def universe():
    """EVERY register this sweep claims to cover, parsed from the shots directory — the source of truth.

    Said out loud and derived, because the headline used to be `len(rows)`: a sweep that lost nineteen
    registers printed the number it had measured and a reader had no way to tell it from the library. The
    one number that makes a skip visible is the one nothing was computing.
    """
    return sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(_SHOTS, "*.tsx")))


def durations():
    """{register: DURATION}. A register that exports none is NOT in here — see `not_measured`, which names
    it rather than letting it fall out of `names` in silence."""
    out = {}
    for n in universe():
        m = re.search(r"export const DURATION\s*=\s*(\d+)",
                      open(os.path.join(_SHOTS, n + ".tsx"), encoding="utf-8").read())
        if m:
            out[n] = int(m.group(1))
    return out


def not_measured(data):
    """{register: why} for every register in the UNIVERSE that has no measured row.

    Three populations, and they are different facts that used to print as the same silence: one that was
    swept and refused (its reason is recorded in `_failed`), one the sweep never reached at all (an older
    manifest, or a `--only` run), and one the sweep's own filter dropped because it exports no DURATION.
    """
    rows = data.get("registers") or {}
    univ, durs = universe(), durations()
    why = {}
    for f in (data.get("_failed") or []):
        n, _, tail = str(f).partition(" (")
        why[n] = tail.rstrip(")").strip() or "refused to render or measure, and no reason was recorded"
    for n in univ:
        if n in rows or n in why:
            continue
        why[n] = ("no `export const DURATION` — the sweep renders each register at its own length and "
                  "cannot place one that declares none" if n not in durs else
                  "never swept — this manifest has no row for it and no recorded failure")
    # Bounded by the UNIVERSE: a `_failed` line for a register that has since been deleted is not a hole in
    # today's coverage, and counting it would make K larger than the library.
    return {n: w for n, w in sorted(why.items()) if n not in rows and n in univ}


def footprint(png):
    """What FRACTION OF THE FRAME the register's content spans — its ink's bounding box.

    Ink alone cannot tell the two ways a frame is empty apart, and they need opposite fixes. Measured on the
    six sparsest registers a delivered film used:

        TermTree      ink 1.1%  footprint  9.0%   |  CardStack3D  ink 2.9%  footprint 57.1%
        QuadSplit     ink 3.9%  footprint 11.3%   |  VersusSplit  ink 3.2%  footprint 53.2%

    The left column is content composed at a ninth of the frame — the fix is to fill it. The right column
    already spans the frame and is TONELESS: every element sits within 0.10 of the ground, so the composition
    is there and invisible. CardStack3D paints its cards from `dna.surface` and VersusSplit paints two halves
    outright; neither needs a new layout, both need real tone. One number cannot ask for both.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    a = np.asarray(Image.open(png).convert("L").resize((192, 108))).astype(np.float32) / 255.0
    ink = np.abs(a - np.median(a)) > 0.10
    if not ink.any():
        return 0.0
    ys, xs = np.nonzero(ink)
    return float(((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)) / (192 * 108))


# EVERY DELIVERED FILM HAS A DESIGN SYSTEM, and this swept without one. `npx remotion render <Id>` with no
# --props renders the un-themed fallback: the branch a register takes when `useDNA()` returns null. That is
# the path `test_null_dna_preserves_every_original_colour` deliberately freezes, so a register improved for
# themed films measures here exactly as it did before — CardStack3D read 0.6% in this manifest on the same
# day it measured 32.2% under `dna=product`, and nothing said the two numbers were about different renders.
# A diagnostic that measures a mode no film uses is worse than none: it is confidently about the wrong thing.
DEFAULT_DNA = "product"


def render_one(name, mp4, dna=DEFAULT_DNA, extra=None):
    cmd = ["npx", "remotion", "render", "src/index.ts", name, mp4, "--gl=angle", "--log=error"]
    # the same memory valve render_remotion.py honours: on a machine short of RAM a parallel render is killed
    # mid-sweep and the register is reported as FAILED rather than measured
    if os.environ.get("REMOTION_CONCURRENCY"):
        cmd.append("--concurrency=" + os.environ["REMOTION_CONCURRENCY"])
    props = {}
    if dna:
        props["dna"] = dna
    props.update(extra or {})
    if props:
        cmd.append("--props=" + json.dumps(props))
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REMOTION)
    # THE REASON, NOT THE LAST LINE. `splitlines()[-1]` on a failed render is
    # `at process.processTicksAndRejections (node:internal/…)`, which is what eight of ink_contrast_qa's
    # nineteen skips carried: a failure list nobody can act on. One reader, in _common.
    return os.path.exists(mp4), [_c.render_error(r.stdout, r.stderr, limit=100)]


def stills_from(mp4, out_dir, name, durF, fps=30):
    os.makedirs(out_dir, exist_ok=True)
    secs = durF / fps
    for tag, frac in (("a", 0.15), ("b", rr.SETTLED_T), ("c", 0.97)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % (secs * frac), "-i", mp4,
                        "-frames:v", "1", os.path.join(out_dir, "%s_%s.png" % (name, tag))],
                       capture_output=True)


_USAGE = ("usage: register_energy.py [--only=A,B | --only A,B] [--dna=NAME] [--stills=DIR] "
          "[--check] [--report]")


def main(argv):
    # REFUSE what this script does not understand, and read a flag in BOTH spellings. `--only DollyZoom`
    # matched nothing here and fell through to a FULL 164-register sweep — about forty-five minutes of
    # renders — with no message: the progress counter read "measured 10/164" and nothing said the filter had
    # been dropped. It happened twice in one session. See scripts/_common.argflag.
    _c.refuse_unknown(argv, valued=("only", "dna", "stills"), switches=("check", "report"), usage=_USAGE)
    if "--check" in argv:
        # CHEAP ON PURPOSE. Re-measuring is 149 video renders; comparing hashes is a read. The expensive
        # check is the one that does not get run before a commit.
        data = json.load(open(MANIFEST, encoding="utf-8"))
        rows = stale(data)
        for n, why in rows:
            print("[register_energy] STALE %-24s %s" % (n, why))
        measured = data.get("registers") or {}
        univ = set(universe())
        print("[register_energy] %s  %d of %d row(s) no longer describe their source%s"
              % ("FAIL" if rows else "OK", len(rows), len(measured),
                 " — re-run `%s`" % REGEN if rows else ""))
        # ...and the same coverage line the sweep prints, so `--check` cannot report OK over a manifest
        # that simply has no row for a third of the library.
        _c.coverage("register_energy", len([n for n in measured if n in univ]), len(univ),
                    not_measured(data))
        return 1 if rows else 0
    if "--report" in argv:
        data = json.load(open(MANIFEST, encoding="utf-8"))
    else:
        only = _c.argflag_list(argv, "only")
        dna = _c.argflag(argv, "dna", DEFAULT_DNA)
        if dna in ("", "none"):
            dna = None
        stills = _c.argflag(argv, "stills")
        # A FILTER THAT MATCHES NOTHING IS NOT A FULL SWEEP. `--only=Zed` on a typo'd name used to leave
        # `names` empty and write a manifest with no rows in it; `--only` that is dropped is the failure
        # above. Say which registers were asked for and not found, and stop.
        if only:
            missing = [n for n in only if n not in durations()]
            if missing:
                print("[register_energy] --only names %d register(s) that do not exist: %s"
                      % (len(missing), ", ".join(missing)))
                return 2
        tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_register_energy")
        os.makedirs(tmp, exist_ok=True)
        durs = durations()
        names = [n for n in sorted(durs) if not only or n in only]
        ensure_fixture()
        ev = evidence_props()
        hashes = {}                     # filled per register, at the moment its pixels are made — see source_hash
        rows, failed = {}, []
        for i, n in enumerate(names, 1):
            hashes[n] = source_hash(n)
            # CACHE KEY = everything the pixels depend on. Keyed by NAME alone, this cache re-measured
            # pre-fixture footage for four registers whose renders had changed underneath it, and it would
            # just as silently serve `--dna=product` video to a `--dna=editorial` sweep while `_basis`
            # announced editorial. A cache nobody can tell is stale is the same lie as a manifest nobody can
            # tell is stale — and this file already refuses the second one.
            key = hashlib.sha256(json.dumps(
                [hashes.get(n, ""), dna, ev.get(n)], sort_keys=True).encode()).hexdigest()[:10]
            mp4 = os.path.join(tmp, "%s.%s.mp4" % (n, key))
            if not os.path.exists(mp4):
                ok, tail = render_one(n, mp4, dna, ev.get(n))
                if not ok:
                    failed.append("%s (%s)" % (n, tail[0][:100]))
                    continue
            try:
                m = fe.measure(mp4)
            except Exception as exc:                 # noqa: BLE001 — one register, not the sweep
                # A FULL SWEEP IS TWO AND A HALF HOURS OF RENDERS. One unreadable mp4 raising here used to
                # end all of it, and an aborted sweep writes nothing at all — every register leaves the
                # measurement, unnamed, which is the failure this file's `_failed` list exists to prevent.
                failed.append("%s (measuring it raised: %r)" % (n, exc))
                continue
            if not isinstance(m, dict):
                failed.append("%s (unmeasurable: %r)" % (n, m))
                continue
            # INK COMES FROM `density()`, NOT FROM `measure()`. The two used to share one decode; density
            # moved to its own when its definition changed from "pixels far from the modal tone" to "local
            # structure", because the new question needs a resolution the motion floor's calibration must
            # not be dragged to (`film_energy_qa.DENSITY_LONG_SIDE`). A register's ink and a film's ink are
            # the same question, so they must keep using the same answer — a sweep measuring one definition
            # while the delivery gate measures another is a manifest that lies without being stale.
            _dn = fe.density(mp4)
            rows[n] = {"motion_p75": round(m["motion_p75"], 4),
                       "ink_median": round(_dn["median"], 3) if _dn else None,
                       "luma_range": round(m["luma_range"], 3),
                       "seconds": round(m["seconds"], 1)}
            # The settled still, for the footprint. Written whether or not --stills was asked for, into a
            # temp dir if not: a diagnosis that cannot distinguish "too small" from "too flat" sends every
            # register the same advice, and the two need opposite work.
            sd = stills or os.path.join(tmp, "_fp")
            try:
                stills_from(mp4, sd, n, durs[n])
                fp = footprint(os.path.join(sd, "%s_b.png" % n))
            except Exception:                        # noqa: BLE001 — the footprint is an EXTRA axis
                fp = None                            # `why()` already reports a missing one as "?"
            if fp is not None:
                rows[n]["footprint"] = round(fp, 3)
            if i % 10 == 0:
                print("  measured %d/%d" % (i, len(names)), flush=True)
        if failed:
            print("[register_energy] %d FAILED to render or measure (their energy is UNKNOWN, not fine):"
                  % len(failed))
            for f in failed:
                print("    " + f)
        data = {"_regenerate": REGEN,
                # the hash each row was RENDERED from, not a fresh read of the tree — see source_hash
                "_source": {n: h for n, h in hashes.items() if n in rows},
                "_fed": {n: fed_hash(n, ev) for n in rows if ev.get(n)},
                "_basis": ("each register rendered as VIDEO at its own DURATION, 16:9, under dna=%s — the "
                           "themed path, because every delivered film has a design system and the un-themed "
                           "fallback is a mode none of them use" % (dna or "none")),
                "_dna": dna,
                "_fixture": {"registers": sorted(ev), "why": "these refuse to draw without a real artefact "
                             "(runtime/evidence.ts); measured with a deterministic stand-in so the row "
                             "describes the register rather than an empty box"},
                "_floors": floors(),
                # RECORDED, not just printed. A register that failed to render has no energy reading, and an
                # absent row in a ranking reads as "fine" — the exact silent-improvement failure band_debt.py
                # refuses. Keeping the names in the artifact makes the hole visible to whoever reads it next.
                "_failed": sorted(failed),
                "_universe": len(universe()),
                "registers": dict(sorted(rows.items()))}
        if only:
            # MERGE a targeted re-measure into the record instead of dropping it. Refusing to write at all
            # (the previous behaviour, itself a fix for --only OVERWRITING all 149 rows) made a partial sweep
            # unable to correct the very rows it had just measured — so a register could be fixed, measured
            # at 37%, and the manifest would keep reporting 0.6% forever.
            try:
                prev = json.load(open(MANIFEST, encoding="utf-8"))
            except (OSError, ValueError):
                prev = None
            if prev and prev.get("_dna") != dna:
                # A row's numbers only mean anything beside rows rendered the same way. Blending a
                # product-DNA measurement into an editorial manifest would produce a table whose rows are
                # not comparable, which is worse than no table.
                print("[register_energy] REFUSING to merge: manifest was swept under dna=%r, this run used "
                      "%r. Re-sweep in full, or pass --dna=%s." % (prev.get("_dna"), dna, prev.get("_dna")))
                return 1
            if prev:
                merged = dict(prev["registers"]); merged.update(rows)
                # EVERY map keyed by register name merges forward — not the two anyone remembered to list.
                # A register the library no longer has is dropped on the way through, so a deleted name
                # cannot sit in the record forever describing nothing.
                per_reg, known = register_maps(data), set(universe())
                for k in per_reg:
                    m = {n: h for n, h in (prev.get(k) or {}).items() if n in known}
                    m.update(data[k])
                    data[k] = m
                # a register that now renders is no longer a hole; one that now fails becomes one
                keep = [f for f in (prev.get("_failed") or []) if f.split(" (")[0] not in names]
                # ...AND IT LOSES ITS OLD ROW. Merging only what succeeded left the previous number in place
                # beside a fresh failure line, so the manifest said both "0.6% ink" and "could not be
                # measured" about the same register — and `not_measured` believes the row, so the hole
                # disappears from the coverage it is supposed to appear in.
                for f in failed:
                    n = f.split(" (")[0]
                    merged.pop(n, None)
                    for k in per_reg:
                        data[k].pop(n, None)
                data["registers"] = dict(sorted(merged.items()))
                data["_failed"] = sorted(keep + failed)
        # The relative ink cut is recomputed from the rows about to be written and stored WITH them —
        # before the dump, not after, or the manifest ships a null that every later reader has to re-derive
        # (and a `--only` run would re-derive it from a merged set the sweep never saw whole).
        data["_floors"]["ink_median"] = _ink_cut(data["registers"])
        data["_floors"]["luma_range"] = _light_cut(data["registers"])
        json.dump(data, open(MANIFEST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("[register_energy] wrote %s (%d rows%s)"
              % (MANIFEST, len(data["registers"]), ", merged" if only else ""))

    regs = data["registers"]
    fl = data["_floors"]
    if fl.get("ink_median") is None:              # an older manifest, or a --check run that wrote nothing
        fl["ink_median"] = _ink_cut(regs)
    if fl.get("luma_range") is None:
        fl["luma_range"] = _light_cut(regs)
    unknown = data.get("_failed") or []
    # WHAT THIS RUN DID NOT SEE, derived from the shots directory rather than from the manifest's own rows.
    # `_failed` only ever held what a sweep TRIED and could not measure; a register the sweep never reached
    # — an older manifest, a `--only` run, a register exporting no DURATION — had no row, no failure line
    # and no absence anyone could count.
    gaps = not_measured(data)
    _cut = fl.get("ink_median")
    if _cut is None:
        _cut = _ink_cut(regs)

    def _thin(r):
        return _cut is not None and r.get("ink_median") is not None and r["ink_median"] < _cut

    _lcut = fl.get("luma_range")
    if _lcut is None:
        _lcut = _light_cut(regs)

    def _flat(r):
        return _lcut is not None and r.get("luma_range") is not None and r["luma_range"] < _lcut

    def fails(r):
        return (r["motion_p75"] < fl["motion_p75"]) + _thin(r) + _flat(r)

    def why(r):
        """Which KIND of empty, when it is empty. The two need opposite fixes, so naming one is the
        difference between directable work and a number."""
        if not _thin(r):
            return ""
        fp = r.get("footprint")
        if fp is None:
            return "?"
        return "small" if fp < FOOTPRINT_SPLIT else "flat"
    ranked = sorted(regs.items(), key=lambda kv: (-fails(kv[1]), kv[1]["motion_p75"]))
    n3 = sum(1 for _, r in ranked if fails(r) == 3)
    n2 = sum(1 for _, r in ranked if fails(r) == 2)
    n1 = sum(1 for _, r in ranked if fails(r) == 1)
    n0 = sum(1 for _, r in ranked if fails(r) == 0)
    # The ink cut is RELATIVE and can legitimately be absent — a sweep of fewer than five registers has no
    # distribution to take a fifth of. "not derivable" is printed as itself rather than as a zero, which
    # would read as "every register cleared it".
    print("\n[register_energy] floors motion %.4f / ink %s / light %s"
          % (fl["motion_p75"],
             "not derivable (<5 rows)" if fl["ink_median"] is None else "bottom fifth at %.1f%%"
             % (fl["ink_median"] * 100),
             "not derivable (<5 rows)" if fl["luma_range"] is None else "bottom fifth at %.3f"
             % fl["luma_range"]))
    # COVERAGE, NOT A COUNT. This line read "%d registers" with the number of rows in it, so a sweep that
    # measured 151 of 170 printed a line that reads as 170 and the nineteen holes were invisible.
    univ = universe()
    # rows for registers that are GONE are not coverage of the library — `stale()` names those separately
    _c.coverage("register_energy", len([n for n in regs if n in set(univ)]), len(univ), gaps)
    if gaps:
        print("[register_energy] the register(s) above are absent from the ranking, NOT passing it")
    print("[register_energy] under all three: %d · two: %d · one: %d · clear: %d" % (n3, n2, n1, n0))
    print("\n%-24s %8s %7s %7s %7s  %-4s %s"
          % ("register", "motion", "ink", "light", "footprnt", "why", "under"))
    for n, r in ranked[:40]:
        marks = "".join(m for m, bad in (("M", r["motion_p75"] < fl["motion_p75"]),
                                         ("D", _thin(r)),
                                         ("L", _flat(r))) if bad)
        print("%-24s %8.4f %6.1f%% %7.3f %7s  %-4s %s"
              % (n, r["motion_p75"], (r["ink_median"] or 0) * 100, r["luma_range"],
                 "-" if r.get("footprint") is None else "%.0f%%" % (r["footprint"] * 100),
                 why(r), marks or "-"))
    # A RUN THAT COULD NOT MEASURE PART OF ITS UNIVERSE IS NOT A CLEAN RUN, whether the register refused
    # (`unknown`) or was never reached at all (`gaps`). The second was exit 0 until now.
    return 1 if unknown or gaps else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
