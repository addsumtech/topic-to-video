#!/usr/bin/env python3
"""SHOT PROOF SHEET — catch the mechanical half of a shot review BEFORE the full render.

Run:
  python3 scripts/shot_proof.py <out_dir>              # static checks only (~1s)
  python3 scripts/shot_proof.py <out_dir>              # static + RENDERED checks (~5s/beat) — the default
  python3 scripts/shot_proof.py <out_dir> --no-stills  # source-only, for a fast pass while authoring

WHY. A shot-critic pass over a finished 37-beat film cost a full render plus a long review and filed 15
findings. Sorting them by kind, more than half were things a script can decide:

  * a shot's own label sitting inside the burned-caption band, or content sliced by the frame edge
  * a colour outside the film's DNA (a hardcoded gradient stop put royal blue over ~25% of one frame in
    a green/amber film)
  * content parked in a narrow column with half the 16:9 frame dead
  * a register's DEMO DEFAULT left in shot_props on a real topic (a card's backLabel still reading
    「实际」 on the film's closing frame; a metric register still showing its sample figure)
  * two beats rendering the SAME picture because the same register got near-identical props

The other findings — does the design ENCODE the idea, is the number sourced, does the register fit the
beat — are judgment, and stay the critic's job. This script exists so the critic spends its pass on those
instead of re-finding the mechanical ones, and so a FIRST draft arrives with them already fixed.

It is a floor, not a verdict: passing here says nothing about whether the film is any good.
"""
import json
import shutil
import os
import re
from onscreen_text_qa import _strip_comments   # the ONE comment stripper
import subprocess
import _common as _c   # run_render: one render at a time, machine-wide

import render_remotion as _rr   # the renderer's own reading of a beat: its props, and the frame useT calls settled
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")

# THE FILM'S OWN REGISTERS. While a film is proofed, its workshop's shots/ folder (scripts/workshop.py) is read
# after the library's, and every still renders in a bundle that holds the workshop. Empty otherwise.
_FILM_SHOTS = []
_FILM_ENV = {}

UNFED_TAG = "UNFED-TEXT "      # runtime/textSafe.tsx UNFED_TEXT_TAG — tests/test_unfed_text.py holds them equal


def _number_leaves(v, out=None):
    """Every non-bool int/float anywhere in a props tree — a figure-shaped numeral (runtime/textSafe.tsx's
    numeral rule) may match a raw numeric prop value directly, not only a numeral spelled out inside a fed
    string. A separate walk from `cjk_type_qa._string_leaves`, which collects STRINGS — that one walk stays a
    single definition, not every leaf-shaped question sharing it."""
    out = [] if out is None else out
    if isinstance(v, bool):
        pass
    elif isinstance(v, (int, float)):
        out.append(v)
    elif isinstance(v, dict):
        for x in v.values():
            _number_leaves(x, out)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _number_leaves(x, out)
    return out


def _fmt_number(x):
    """A numeral prop as fed text: an integral float prints without its trailing ".0" ("1200", not
    "1200.0") — the numeral rule compares by VALUE, so the exact string never changes a match, but this pool
    is also printed back into a finding, where a bare "1200" reads truer than "1200.0" for a value nothing
    ever wrote as a float."""
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def _unfed_text(shot, payload, frame, proof, beat, out_dir, scope, declared):
    """The words on this beat's frame that no prop supplied: (words, total, None) on a clean answer — `words`
    is what the runtime itself already capped (runtime/textSafe.tsx MAX_REPORTED), `total` the true count past
    that cap — or (None, None, reason) when the render gave no answer, `reason` the render's own message
    (`_stderr_reason`), not a shrug. `declared` are the words the workshop code names with `// @fixed-text:`
    (scripts/jsx_words.cjs).

    Built from the beat's own `shot_props` — `dna` and `aspect` are the RENDER's own context, stacked onto
    `payload` after the film's props (see `_prove`), never copy the film wrote. A film's Design DNA is
    typically an OBJECT of some two dozen tokens (font stacks, a gradient, 'smooth', 'solid', …); left in the
    fed pool, a baked word sharing a run of letters with one of them (a font name, a motion keyword) read as
    fed. An object ref's `id` is dropped BY PATH — the one string at the exact path object_refs() found it,
    never by VALUE — so a beat's own label that happens to equal an object's id (a "Grinder" caption on a beat
    that also holds the object `Grinder`) stays fed; only the id itself, wiring no viewer is meant to read, is
    removed. Numeral props are added too, so a figure-shaped numeral can match a raw numeric value directly."""
    import copy
    import cjk_type_qa
    import workshop as _ws
    src = _ws.shot_source(out_dir, shot)
    props = copy.deepcopy({k: v for k, v in payload.items() if k not in ("dna", "aspect")})
    for _p, ref in _ws.object_refs(src, props, shot):
        if isinstance(ref, dict) and isinstance(ref.get("id"), str):
            del ref["id"]
    fed = ([x for x in cjk_type_qa._string_leaves(props) if x.strip()]
           + [_fmt_number(x) for x in _number_leaves(props)]
           + list(declared or []))
    pj = os.path.join(proof, "beat_%02d.unfed.json" % beat)
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump(dict(payload, unfedText=fed, unfedScope=scope), fh, ensure_ascii=False)
    png = os.path.join(proof, "beat_%02d.unfed.png" % beat)
    r = _c.run_render(["npx", "remotion", "still", "src/index.ts", shot, png, "--frame=%d" % frame, "--gl=angle",
                        "--props=" + pj, "--log=error", "--public-dir=" + os.path.abspath(out_dir)],
                       cwd=_REMOTION, capture_output=True, text=True, **_FILM_ENV)
    for f in (pj, png):
        if os.path.exists(f):
            os.remove(f)
    blob = (r.stdout or "") + (r.stderr or "")
    if UNFED_TAG not in blob:
        return None, None, _stderr_reason(blob)
    try:
        data = json.JSONDecoder().raw_decode(blob.split(UNFED_TAG, 1)[1])[0] or {}
    except json.JSONDecodeError:
        return None, None, _stderr_reason(blob)
    words = data.get("unfed") or []
    return words, data.get("total", len(words)), None


def _band_luminance(png):
    """Median relative luminance of the caption band — the ground the burned caption is inked for."""
    try:
        from PIL import Image
        import numpy as np
        from _caption_band import caption_band_px
    except ImportError:
        return None
    im = Image.open(png).convert("RGB")
    band = int(caption_band_px(im.width, im.height))
    a = np.asarray(im.crop((0, im.height - band, im.width, im.height)), dtype=float) / 255.0
    lin = np.where(a <= 0.03928, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    return float(np.median(y))


def _resolved_dna(dna_ref):
    """The Design DNA a beat actually renders under, mirroring runtime/dna.tsx's `coerceDna`: an OBJECT merges
    over the neutral preset's own tokens (so a partial DNA's missing keys resolve exactly as a component would
    see them, not as a bare partial dict); a preset NAME resolves through seam_plan's own table. None when
    nothing names a usable DNA. `dna_ref` is `design_dna` or `shot_template`, exactly as `_prove` already
    resolves it for the render itself (its own `dna_ref`) — this never disagrees with what a beat painted."""
    import seam_plan
    if isinstance(dna_ref, dict):
        return dict(seam_plan._resolve_dna("neutral") or {}, **dna_ref)
    if isinstance(dna_ref, str) and dna_ref:
        return seam_plan._resolve_dna(dna_ref)
    return None


def _ground_claim(png, shot, out_dir, dna_ref):
    """A film-local shot DECLARES the ground its caption is inked for (workshop GROUND); the library's registers
    are measured instead. Compare the claim with the caption band actually rendered, past the seam guard's own
    flash threshold — `seam_plan.ground_gap`'s own comparison, not a second copy of it re-derived with the
    wrong operator.

    Returns None (the claim holds), or `("error", <why>)` / `("unmeasured", <why>)` — never a bare string, and
    never silence for both at once: a caption inked for the wrong ground is a defect in the shot; a ground this
    check could not read at all (a gradient token, no Design DNA, an unreadable frame) is a hole in the check
    itself, and conflating the two under one `None` reported neither an error nor a beat left unmeasured.

    A declared LIST of tokens holds when the band sits within the gap of any ONE listed token, or of their
    AVERAGE — the same two readings the caption ink and the seam guard themselves take."""
    import workshop as _ws
    import seam_plan
    g = _ws.grounds(out_dir).get(shot)
    if g is None:
        return None
    candidates = []                              # [(label, luminance)] — every value this declaration could mean
    if isinstance(g, str) and g.startswith("#"):
        y = seam_plan._rel_lum(g)
        if y is not None:
            candidates = [(g, y)]
    else:
        dna = _resolved_dna(dna_ref)
        if dna is None:
            return "unmeasured", ("GROUND %r could not be measured — this beat has no Design DNA to resolve it "
                                  "against" % g)
        toks = [g] if isinstance(g, str) else list(g)
        resolved = [(t, y) for t, y in ((t, seam_plan._rel_lum(dna.get(t))) for t in toks) if y is not None]
        candidates = list(resolved)
        if len(resolved) > 1:
            candidates.append(("their average", sum(y for _t, y in resolved) / len(resolved)))
    if not candidates:
        return "unmeasured", ("GROUND %r could not be measured — none of its token(s) resolve to a plain colour "
                              "under this film's DNA (a gradient has no single luminance)" % g)
    try:
        from PIL import Image  # noqa: F401
        import numpy as np  # noqa: F401
    except ImportError:
        return "unmeasured", "GROUND %r could not be measured — PIL/numpy is unavailable to read the caption band" % g
    measured = _band_luminance(png)
    if measured is None:
        return "unmeasured", ("GROUND %r could not be measured — the caption band could not be read from the "
                              "rendered frame" % g)
    gaps = [(label, seam_plan.ground_gap(y, measured)) for label, y in candidates]
    if all(gap >= seam_plan.HARSH_GAP for _label, gap in gaps):
        label, gap = min(gaps, key=lambda lg: lg[1])
        return "error", ("declares GROUND %r but its caption band renders %.2f from %s (>= the %.2f seam-guard "
                         "flash threshold) — the burned caption would be inked for a ground that is not there; "
                         "set GROUND to what the shot really paints" % (g, gap, label, seam_plan.HARSH_GAP))
    return None


# The two inks the film burns its caption in (runtime/light.tsx CAPTION_INK_DARK / CAPTION_INK_LIGHT), and the
# floor under which a caption no longer reads: the caption is large type, so WCAG's large-text 3:1.
CAPTION_INKS = ("#141414", "#ffffff")
CAPTION_READABLE_MIN = 3.0


def _contrast(y1, y2):
    hi, lo = max(y1, y2), min(y1, y2)
    return (hi + 0.05) / (lo + 0.05)


def _caption_ink_y(ground_y):
    """Mirror of runtime/light.tsx `captionInk`: the luminance of whichever ink measures more on the ground."""
    import seam_plan
    dark, light = (seam_plan._rel_lum(c) for c in CAPTION_INKS)
    return dark if _contrast(dark, ground_y) >= _contrast(light, ground_y) else light


def caption_on_ground(expected_y, measured_y):
    """None when the caption the film inks for `expected_y` (the ground it RESOLVES for this beat) still reads on
    `measured_y` (the ground the beat really paints under it); otherwise (ink luminance, contrast) of that ink on
    the real ground. Pure, so the rule is testable without a render."""
    ink = _caption_ink_y(expected_y)
    c = _contrast(ink, measured_y)
    return None if c >= CAPTION_READABLE_MIN else (ink, c)


def _library_caption_ground(png, shot, slide, dna_ref):
    """A LIBRARY register's caption, judged against the ground it really paints under it.

    The film inks every caption from the ground it RESOLVES for the beat — `DNA_GROUND_TOKEN` under the film's
    DNA (`seam_plan.dna_ground_y`, the mirror of Film.tsx's `dnaGroundY`) — never from the pixels. A row that names
    the wrong ground therefore inks a caption nobody can read with every other gate green: the `@dark-world`
    registers (BokehPull, StarfieldWarp, …) were recorded `bg` from a dark probe alone, and on a light film
    resolved to the paper while painting night. Their rows now carry the night a LIGHT probe measured
    (measure_ground_luma.py `classify_world`), and this check stays for whatever row is wrong next: the resolved
    ground is checked against the caption band actually rendered, and only a caption that would no longer READ
    is an error.

    Returns None, ("error", why) or ("n/a", why)."""
    import seam_plan
    if slide.get("ground") is not None:
        return ("n/a", "the beat declares its own `ground`; the caption is inked from it, and a standalone still "
                       "does not paint it")
    dna = _resolved_dna(dna_ref)
    expected = seam_plan.dna_ground_y(shot, dna) if dna else None
    if expected is None:
        return None              # no DNA, or a ground the table does not resolve: the film falls back to its bucket
    measured = _band_luminance(png)
    if measured is None:
        return ("n/a", "the caption band could not be read from the rendered frame")
    bad = caption_on_ground(expected, measured)
    if bad is None:
        return None
    ink, c = bad
    return ("error", "the burned caption will be inked %s for the ground this register resolves to under the "
                     "film's DNA (Y=%.2f), but it paints Y=%.2f under the caption — %.1f:1, under the %.1f:1 a "
                     "caption needs to read. Its row in DNA_GROUND_TOKEN does not name the ground it paints under this "
                     "film's DNA — re-measure it (`measure_ground_luma.py --only %s --emit`), cast a register that "
                     "follows this film's ground here, or ground the beat yourself (`ground`)"
                     % ("dark" if ink < 0.5 else "light", expected, measured, c, CAPTION_READABLE_MIN, shot))


def _src_path(shot):
    """Where register `shot` is defined for the film being proofed: the library first, then the film's own. One
    lookup, so no check here reads the library for a register the film built itself."""
    for d in [_SHOTS] + _FILM_SHOTS:
        p = os.path.join(d, shot + ".tsx")
        if os.path.isfile(p):
            return p
    return os.path.join(_SHOTS, shot + ".tsx")           # the path the caller's message names


# Hue arc a colour must NOT fall in, expressed as "outside the film's own two accents by more than this
# many degrees". Computed per film from its DNA rather than hardcoded, so it works for any palette.
HUE_TOLERANCE = 28
OFF_SYSTEM_FRAC = 0.02      # >2% of the frame's chromatic ink outside the palette arc = a clash
NARROW_FRAC = 0.45          # content narrower than this share of the frame …
OFFSET_FRAC = 0.06          # … AND its centre this far off the frame's centre = a DEAD FRAME.
# Width alone is not the defect. Measured on a real film, "narrow" split cleanly in two: seven beats were
# narrow and dead-centre (a title, a cube, a counter — deliberate compositions), and four were narrow and
# pushed to one side, which is the thing a reviewer actually described as "half the frame is dead".
# Flagging on width alone reported 11 of 37 beats; a gate that cries wolf that often gets ignored.

# Registers whose colour is a CONVENTION, not the film's palette: a diff's removals are red and its
# additions green, a log's errors are red, an editor's syntax colours are its own system. Judging these
# against the DNA reports the convention as a defect. Keep the list short and say why.
SEMANTIC_COLOUR_SHOTS = {
    "TermDiff": "a diff is red/green by convention",
    "TermLog": "log levels are red/amber/green by convention",
    "TermGitLog": "commit/branch colouring is a convention",
    "CodeCompose": "syntax highlighting is its own colour system",
    "CodeRain": "terminal phosphor colour is the register",
    "AsciiField": "terminal phosphor colour is the register",
}
PROPS_SAME = 0.80           # two beats sharing a register with >=80% identical props = the same picture

# Registers that put a SOURCED FIGURE on screen. Every one of them animates it, and the delivery gate
# captures the MID-scene frame — so "settles eventually" is not good enough: a film shipped with a
# sourced 19.3-28.9 rendered as 19.3-16.5 and a sourced 19% rendered as 18%, digits caught mid-flight.
# ONLY the registers whose figure IS the frame's subject and whose only motion is that figure settling.
# The check compares the whole mid frame against the settled one, so it cannot tell a still-rolling digit
# from a chart that is legitimately still drawing: measured on their own demo props, ChartLive scores 201,
# ChartRace 200, BeforeAfterSlider 207 and GaugeCluster 118 — every one of them would be BLOCKED for
# animating exactly as designed. Those four display a figure too and are NOT covered here; separating the
# number from the graphic needs a region this check does not have, so their figures remain the critic's
# to verify. A gate that blocks four correct designs is worse than one that admits its reach.
FIGURE_SHOTS = ("OdometerRoll", "TermCounter", "EdStat")
FIGURE_SETTLE_BLOCK = 70    # max 32x32-block difference between the MID and SETTLED frames.
# Measured: a figure that lands early scores 0-34; one still moving at the midpoint scores 115-232. A
# whole-frame mean cannot separate them — one changed digit moves too few pixels (0.45 vs 0.00) — so the
# statistic is the worst LOCAL block, not the average.


_STACK_LINE = re.compile(r"^\s*(at\s|\.\.\.\s|node:internal|Node\.js v)")


def _stderr_reason(stderr, limit=220):
    """The MESSAGE a failed render actually carries, not the last line of its stack.

    The last line of `(r.stderr or "").strip().split("\\n")[-1]` is always a node stack's own tail,
    `at process.processTicksAndRejections (node:internal/…)`. The ink gate shipped eight registers
    marked "skipped" behind exactly that non-reason: the run said something failed and named nothing a
    reader could act on. Stack frames are dropped, the first line that carries a thrown message wins, and
    when nothing does, the surviving prose is returned rather than a shrug.
    """
    lines = [l.strip() for l in str(stderr or "").splitlines() if l.strip()]
    prose = [l for l in lines if not _STACK_LINE.match(l)]
    thrown = [l for l in prose
              if re.search(r"(?:^|\b)(\w*Error|Invariant|Cannot|Unexpected|Failed|Unable|throw)\b", l)]
    pick = thrown or prose or lines
    if not pick:
        return "the renderer wrote nothing to stderr (exit non-zero with no message)"
    # FIRST and LAST, not the first two. node puts the thrown message at the top and remotion puts the
    # resolved cause at the bottom (a teardown complaint from puppeteer often sits between them), so the
    # two ends carry the cause whichever tool produced it; the middle never does.
    pick = [pick[0]] if len(pick) == 1 else [pick[0], pick[-1]]
    out = " / ".join(pick)
    return out[:limit] + ("…" if len(out) > limit else "")


# A BEAT NOTHING TOUCHED IS NOT RENDERED AGAIN. The design pass on a 25-beat film ran this script eight times
# (18.6 min of its 58 tool minutes), each time re-rendering every beat although one shot had changed. A render is
# keyed on everything its picture is made of (scripts/beat_key.py: the shot's import closure, the runtime, every
# asset, the props, the DNA, the aspect, the frame, THIS script's own bytes) and a hit reuses that render's PNG and
# the words-from-props answer. Only RENDERS are reused: every measurement below still runs on the pixels, so a hit
# reports exactly what a fresh render would. `--no-cache` renders everything, as before.
_CACHE_DIR = ".cache"
_NO_CACHE = False


def _cache_key(out_dir, slide, meta, extra):
    try:
        import beat_key as _bk
        return _bk.beat_key(out_dir, slide, meta, os.path.abspath(__file__), extra=extra)
    except Exception:                                     # noqa: BLE001 - no key, no reuse: render as before
        return None


def _cached(proof, key, suffix):
    if _NO_CACHE or not key:
        return None
    f = os.path.join(proof, _CACHE_DIR, key + suffix)
    return f if os.path.exists(f) else None


def _keep(proof, key, suffix, src=None, data=None):
    if not key:
        return
    d = os.path.join(proof, _CACHE_DIR)
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, key + suffix)
    if src is not None:
        shutil.copyfile(src, dest)
    else:
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)


def switch_props(shot):
    """Props typed as a CHOICE of string literals — `camera?: 'still'`, `device?: DeviceKind` — whose value is a
    setting, not copy. Their default is a real choice a film makes (a phone), never leftover demo furniture, so
    the demo-default rule does not read them; it warned on every phone DeviceDemo."""
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return set()
    runtime = []
    for f in sorted(os.listdir(os.path.join(_REMOTION, "src", "runtime"))):
        if f.endswith((".ts", ".tsx")):
            runtime.append(open(os.path.join(_REMOTION, "src", "runtime", f), encoding="utf-8").read())
    lit = r"(?:'[^']*'\s*\|\s*)*'[^']*'"

    def literal_alias(name):
        for text in [src] + runtime:
            m = re.search(r"(?:export\s+)?type\s+%s\s*=\s*([^;]+);" % re.escape(name), text)
            if m:
                return bool(re.fullmatch(lit, m.group(1).strip()))
        return False
    out = set()
    for key, typ in re.findall(r"\b(\w+)\?\s*:\s*([^;\n]+);", src):
        typ = typ.strip()
        if re.fullmatch(lit, typ) or (re.fullmatch(r"[A-Za-z_]\w*", typ) and literal_alias(typ)):
            out.add(key)
    return out


def shot_defaults(shot):
    """{prop: default} for a registered shot — reads the file and delegates."""
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return {}
    return defaults_from_source(src, shot)


def defaults_from_source(src, shot):
    """{prop: default} parsed from a shot's destructuring defaults. Strings and numbers only — enough to
    catch a demo default left in place, which is what this is for. Pure, so a test can feed it BOTH
    destructuring forms; only the renamed one was parsed for a long time, which left 72 of 136 registers
    unchecked by the module's headline rule."""
    m = re.search(r"export const %s\s*:\s*React\.FC<" % re.escape(shot), src)
    if not m:
        return {}
    block = src[m.end():]
    stop = block.find("=> {")
    block = block[:stop if stop > 0 else 4000]
    out = {}
    # TWO destructuring forms are in use across the library and only the RENAMED one was parsed, so this
    # returned nothing at all for 72 of 136 registers — the demo-default check, this module's headline
    # reason for existing, was blind on more than half the library and said nothing.
    #   renamed:  title: TITLE = 'Your workspace'
    #   plain:    title = 'Your workspace'
    pats = [r"(\w+)\s*:\s*[A-Z_][A-Za-z0-9_]*\s*=\s*('([^']*)'|\"([^\"]*)\"|(-?[\d.]+))",
            # The plain form's name must start lowercase: prop names are camelCase and the RENAMED form's
            # alias is upper (`title: TITLE = 'x'`), so without this the alias came back as a phantom prop
            # called TITLE that no board can ever set.
            r"(?<![:\w])([a-z]\w*)\s*=\s*('([^']*)'|\"([^\"]*)\"|(-?[\d.]+))"]
    for pat in pats:
        for pm in re.finditer(pat, block):
            val = pm.group(3) if pm.group(3) is not None else (pm.group(4) if pm.group(4) is not None else pm.group(5))
            out.setdefault(pm.group(1), val)
    return out


def demo_content_props(shot):
    """{prop: CONST} for props whose default is a NAMED module constant — the register's own demo CONTENT.

    The text checks above catch demo COPY. They cannot see demo GEOMETRY: TechnicalPlate's `strokes` defaults
    to `BIKE`, so a beat about enterprise data isolation that did not pass strokes drew a bicycle, full size,
    in the middle of the frame. No string was involved, so nothing said a word.

    The rule generalises past drawings: a prop you did not pass whose default is a named constant means the
    REGISTER is supplying the content, not the film. Precise rather than noisy — 20 such props across the
    whole library.
    """
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return {}
    m = re.search(r"export const %s\s*:\s*React\.FC<" % re.escape(shot), src)
    if not m:
        return {}
    blk = src[m.end():]
    stop = blk.find("=> {")
    blk = blk[:stop if stop > 0 else 4000]
    return {pm.group(1): pm.group(2)
            for pm in re.finditer(r"(\w+)\s*:\s*[A-Z_][A-Za-z0-9_]*\s*=\s*([A-Z][A-Z0-9_]{2,})\b", blk)}


def slot_replaces(shot):
    """{slot: [props it takes the place of]} from the register's own `export const SLOT_REPLACES = {…}`.

    An object slot can stand in for a prop whose default is demo content: TechnicalPlate draws a film's `art`
    INSTEAD of `strokes` and refuses the two together, so a film using the slot cannot pass `strokes` at all.
    Without this, demo_content_props reported every such beat as drawing the demo bicycle — a finding the film
    had no way to clear. The register declares the replacement beside its own slot; nothing here names a
    register.
    """
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return {}
    m = re.search(r"export const SLOT_REPLACES\b[^=]*=\s*\{(.*?)\}", src, re.S)
    if not m:
        return {}
    return {km.group(1): re.findall(r"['\"](\w+)['\"]", km.group(2))
            for km in re.finditer(r"(\w+)\s*:\s*\[([^\]]*)\]", m.group(1))}


def icon_capable(shot):
    """True when a register can draw a real icon per item — DERIVED from the source, never a hardcoded list.

    A register gains icon support by importing runtime/icons, so asking the file is what keeps this honest:
    the next register to be wired is covered the day it is wired, and a list here would have gone stale on
    the first one somebody added.
    """
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return False
    return "runtime/icons" in src


_ICON_LIST_KEYS = ("panels", "items", "rows", "nodes", "faces")


def icons_missing(shot, props):
    """The labelled entries a beat passed to an icon-capable register WITHOUT an icon."""
    if not icon_capable(shot):
        return []
    out = []
    for key in _ICON_LIST_KEYS:
        v = props.get(key)
        if not isinstance(v, list) or len(v) < 2:
            continue
        for entry in v:
            label = entry.get("label") if isinstance(entry, dict) else (entry if isinstance(entry, str) else None)
            icon = entry.get("icon") if isinstance(entry, dict) else None
            if label and not icon:
                out.append("%s/%s" % (key, label))
    return out


def exported_props(shot):
    """The prop names a shot's EXPORTED component actually accepts, or None if it cannot be read.

    WHY THIS IS A GATE. A prop the register does not have is silently dropped by React, and the register
    then draws its own default — so a beat can carry perfectly good topic copy under the wrong key and put
    the register's DEMO WORDS on screen instead. It happened on this library's own first real film: the
    spine beat and the closing beat both passed `text` to KineticManifesto, whose prop is `phrases`, so the
    two most important frames in a Chinese film rendered the English demo line "YOUR AI TEAM." The mistake
    is easy to make from the outside, because most of these files declare an inner helper component FIRST —
    read the wrong `React.FC<{...}>` and you get a private interface that no board can address.
    """
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"export const %s\s*:\s*React\.FC<\{" % re.escape(shot), src)
    if not m:
        # A NAMED props type is the same declaration written in two places, and `None` here means "cannot be
        # read", which the caller turns into "skip" — silently exempt, the decay this whole file exists to
        # stop. `demo_copy_qa._declared_types` already resolves `React.FC<Props>` against `type Props = {…}`
        # and is alias-aware; one parser, not a second copy that knows less.
        try:
            import demo_copy_qa
            aliased = demo_copy_qa._declared_types(src, shot)
            if aliased:
                return set(aliased)
        except Exception:                                    # noqa: BLE001 — unreadable stays unreadable
            pass
        return None
    st, depth = m.end() - 1, 0
    end = st
    for k in range(st, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                end = k
                break
    # BOTH KINDS OF COMMENT, and for a while only one. This stripped `//` and left `/** */` alone, so a
    # register that documents its props with JSDoc — which is the house style for a new one — parsed to an
    # EMPTY set. Two failures, in opposite directions, from the same line: every board using such a register
    # was FAILED for passing props that do exist (`DollyZoom` blocked a correct film), and the wrong-prop
    # defect this gate was built for could never be caught there at all, because nothing is "not in" an
    # empty set's complement that the caller checks. `_strip_comments` is already imported at the top of
    # this file for exactly this job — the ONE comment stripper, per its own header — and was not used here.
    blk = _strip_comments(src[st + 1:end])
    keys, depth, cur = [], 0, ""
    for ch in blk:
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        if ch == ";" and depth == 0:
            keys.append(cur); cur = ""
        else:
            cur += ch
    keys.append(cur)
    out = set()
    for k in keys:
        mm = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:", k)
        if mm:
            out.add(mm.group(1))
    return out


_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'-]{1,}")
# A default that is a VALUE, not copy — a colour, a CSS length, an easing name. The first version of this
# check counted `ff` and `fa` inside `#ff4fa3` as two English words and reported a hex accent as "English
# demo copy" on beat 9. A gate that cries wolf is worse than no gate: it teaches the author to skim.
_NOT_COPY = re.compile(r"^\s*(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|[\d.]+(px|em|rem|%|s|ms|deg)?|"
                       r"var\(|linear-gradient|radial-gradient|ease|ease-in|ease-out|none|auto)\s*$")


def _is_demo_copy(v):
    """True when a default STRING is prose the viewer would read, not a value the renderer would consume."""
    if _NOT_COPY.match(v or ""):
        return False
    words = _LATIN_WORD.findall(v or "")
    # Prose has at least two Latin words AND whitespace between them; `#ff4fa3` has neither.
    return len(words) >= 2 and any(ch.isspace() for ch in (v or ""))


def default_copy(shot):
    """{prop: [default strings it will draw]} — including a default that is a NAMED module constant.

    `shot_defaults` reads literal defaults, which is enough to spot a demo word left in a prop the board
    DID set. This answers the other half: what a register prints when the board sets nothing. Those
    defaults are demo copy by construction, and on a film in another language they are the register talking
    over the film — `SwissEditorial`'s untouched ticker scrolled "WORKBUDDY -- ON YOUR MACHINE -- YOUR AI
    TEAM -- NO CLOUD" across a Chinese beat, and NO CLOUD contradicted the film's own sources.
    """
    try:
        src = open(_src_path(shot), encoding="utf-8").read()
    except OSError:
        return {}
    consts = {}
    for cm in re.finditer(r"const\s+([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\")", src):
        consts[cm.group(1)] = re.findall(r"'([^']*)'|\"([^\"]*)\"", cm.group(2))
    m = re.search(r"export const %s\s*:\s*React\.FC<" % re.escape(shot), src)
    if not m:
        return {}
    blk = src[m.end():]
    stop = blk.find("=> {")
    blk = blk[:stop if stop > 0 else 4000]
    out = {}
    for pm in re.finditer(r"(\w+)\s*:\s*[A-Z_][A-Za-z0-9_]*\s*=\s*([A-Z][A-Z0-9_]*|\[[^\]]*\]|'[^']*')", blk):
        prop, raw = pm.group(1), pm.group(2)
        vals = consts.get(raw) if raw in consts else re.findall(r"'([^']*)'", raw)
        flat = [a or b for pair in (vals or []) for a, b in ([pair] if isinstance(pair, tuple) else [(pair, "")])]
        flat = [x for x in flat if x]
        if flat:
            out[prop] = flat
    return out


def _flat(v, prefix=""):
    """Flatten shot_props to {path: scalar} so two beats' props can be compared and scanned."""
    out = {}
    if isinstance(v, dict):
        for k, x in v.items():
            out.update(_flat(x, prefix + "/" + str(k)))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out.update(_flat(x, prefix + "/%d" % i))
    else:
        out[prefix] = v
    return out


def static_checks(board, skips=None):
    """(errors, warnings). `skips` collects every beat/register that LEFT the measurement, with a reason.

    Three paths can drop an item in silence unless routed here: a beat with no `shot`, a register whose
    exported props could not be parsed (`exported_props` returns None and the caller reads that as "exempt"
    — its own docstring says so), and a register whose .tsx could not be opened for the welded-copy check.
    None of them moves a number in the headline on its own, so a run blind to a register would print the
    same line as a run that cleared it.
    """
    skips = skips if skips is not None else []
    errors, warns = [], []
    slides = board.get("slides", [])
    seen = {}
    # by POSITION — boards write `index` 1-based, so `index + 1` names the FOLLOWING beat (see
    # tests/test_beat_numbering.py; the same arithmetic mislabelled the critic's contact sheet).
    for _pos, s in enumerate(slides, start=1):
        beat = _pos
        shot = s.get("shot")
        props = s.get("shot_props") or {}
        if not shot:
            skips.append("beat %d: no `shot` — every per-register check below (unknown props, demo copy, "
                         "demo content, icons, duplicate composition) is skipped for this beat. "
                         "validate.py ERRORS on it; this gate simply cannot see it." % beat)
            continue
        # (0) A PROP THE REGISTER DOES NOT HAVE. React drops it silently and the register draws its own
        # default instead, so a beat carrying perfect topic copy under the wrong key ships the DEMO words.
        # Both of this film's most important frames — its spine and its close — passed `text` to a register
        # whose prop is `phrases`, and rendered the English demo line "YOUR AI TEAM." in a Chinese film.
        iface = exported_props(shot)
        if iface is None:
            skips.append("beat %d (%s): the register's exported prop list could not be read from "
                         "src/shots/%s.tsx (no `export const %s: React.FC<{…}>` and no resolvable named "
                         "props type) — the wrong-prop check is OFF for this beat, which is the exact "
                         "defect it exists to catch" % (beat, shot, shot, shot))
        if iface is not None:
            unknown = sorted(k for k in props if k not in iface)
            if unknown:
                errors.append("beat %d (%s): %s is not a prop of this register (it takes %s) — React drops "
                              "it and the register draws its own DEMO copy instead"
                              % (beat, shot, ", ".join(repr(u) for u in unknown), ", ".join(sorted(iface))))

        # (0b) A prop left UNSET whose default is demo copy in another language. This passes every key
        # check by construction: the prop name is right, it is simply absent. SwissEditorial's untouched
        # ticker scrolled "WORKBUDDY -- ON YOUR MACHINE -- YOUR AI TEAM -- NO CLOUD" across a Chinese beat,
        # and NO CLOUD contradicted that film's own sources. Only fires on a film whose language is not
        # English, and only for a default carrying two or more Latin WORDS — a one-word 'REC' belongs to
        # the form and is declared as INTRINSIC_TEXT.
        lang = str((board.get("meta") or {}).get("language") or "").lower()
        if lang and not lang.startswith("en"):
            for key, vals in default_copy(shot).items():
                if key in props:
                    continue
                latin = [v for v in vals if _is_demo_copy(v)]
                if latin:
                    errors.append("beat %d (%s): '%s' is unset, so the register draws its own English demo "
                                  "copy %r on a %s film — pass the prop"
                                  % (beat, shot, key, latin[0][:60], lang))

        # (0b2) THE REGISTER'S OWN DEMO CONTENT, where no text is involved. A prop left unset whose default
        # is a named constant means the register supplies the content: TechnicalPlate drew a BICYCLE, full
        # size and centred, on a beat about enterprise data isolation, because `strokes` was not passed. The
        # copy checks are blind to it — there is no string to compare.
        # A slot the beat FILLED that takes a demo prop's place (the register's SLOT_REPLACES) means that prop is
        # not being drawn at all — the film supplied the content through the slot.
        taken = {p for slot, ps in slot_replaces(shot).items() if props.get(slot) is not None for p in ps}
        for key, const in demo_content_props(shot).items():
            if key not in props and key not in taken:
                errors.append("beat %d (%s): '%s' is unset, so the register draws its own demo content "
                              "(`%s`) — pass the prop or choose a register whose form this beat supplies"
                              % (beat, shot, key, const))

        # (0c) A CATEGORY LIST WITH NO ICONS. An icon-capable register falls back to an abstract mark chosen
        # by INDEX — the same four shapes in the same order on every film, whatever the labels say. A ring
        # beside 「开表格」 teaches a viewer nothing; an icon answers what the row IS before the label is
        # read, which is the whole test in references/icons.md. Icons are the DEFAULT for category content
        # here, so their absence is what needs a reason, not their presence.
        bare = icons_missing(shot, props)
        if bare:
            warns.append("beat %d (%s): %d labelled item(s) carry no `icon`, so the register draws its "
                         "index-chosen abstract mark instead — %s. Name the icon for each (see "
                         "runtime/icons.tsx ICON_NAMES), or say why this beat is one where an icon would "
                         "compete (a headline figure, a motif-dominant frame)."
                         % (beat, shot, len(bare), ", ".join(bare[:4])))

        # (1) a register's DEMO DEFAULT left in place on a real topic
        defs = shot_defaults(shot)
        flat = _flat(props)
        switches = switch_props(shot)
        for key, dv in defs.items():
            if not isinstance(dv, str) or len(dv) < 2 or key in switches:
                continue
            for path, val in flat.items():
                if isinstance(val, str) and val.strip() == dv.strip():
                    warns.append("beat %d (%s): shot_props%s is the register's DEMO DEFAULT %r — a leftover "
                                 "default reads as mystery furniture on a real topic; pass real copy or drop it"
                                 % (beat, shot, path, dv))
        # a prop the beat never set but whose default is visible text: the register will draw ITS demo word
        for key, dv in defs.items():
            if key in ("title", "label", "backLabel", "heading", "kicker", "note", "unit") and key not in props:
                if isinstance(dv, str) and len(dv) >= 2 and re.search(r"[A-Za-z一-鿿]", dv):
                    warns.append("beat %d (%s): '%s' is not set, so the register draws its own demo word %r"
                                 % (beat, shot, key, dv))
        # (2) two beats rendering the same picture. The signal is an identical prop SHAPE — the same keys,
        # the same array lengths — regardless of the words in them. "The same picture with the words
        # swapped" is literally shape-identical and value-different, so requiring shared VALUES (an
        # earlier draft of this check did) looks for the opposite of the defect and finds nothing.
        seen.setdefault(shot, []).append((beat, tuple(sorted(flat))))

    # A register WELDED TO ONE FILM. The library only compounds if a new register carries an ARGUMENT
    # SHAPE ("two populations a measure cannot separate") with the topic arriving through props. If the
    # film's own copy is baked into the .tsx as a literal, the register is a one-off dressed as a library
    # entry: it inflates the catalogue and helps no later film. Checked against the film's OWN distinctive
    # strings, so it needs no vocabulary list and works in any language.
    # The topic set is built from the film's PROSE only. Prop VALUES are a mix of prose and API values —
    # glyph names, hex colours, code samples, enum keys — and feeding those in flagged 'checks', 'gutter',
    # 'f2b544' and even 'return' as "the film's own copy". A gate with false positives gets switched off.
    topic = set()
    for s in slides:
        cand = [s.get("narration", "")]
        for v in _flat(s.get("shot_props") or {}).values():
            # (No identifier/hex filter here: the extractors below take CJK runs of 4+ and Latin PHRASES
            # of two or more words, so a lone enum value or colour can never enter the topic set anyway.
            # A guard that cannot change an outcome is dead code, and a test written for it is theatre.)
            cand.append(str(v))
        for t in cand:
            for run in re.findall(r"[\u4e00-\u9fff]{4,}", str(t)):
                topic.add(run)
            for phrase in re.findall(r"[A-Za-z][A-Za-z0-9'\-]+(?: [A-Za-z][A-Za-z0-9'\-]+){1,4}", str(t)):
                if len(phrase) >= 10:
                    topic.add(phrase)          # a PHRASE, never a lone token: one word is never proof
    for shot in sorted({s.get("shot") for s in slides if s.get("shot")}):
        try:
            src = open(_src_path(shot), encoding="utf-8").read()
        except OSError as e:
            skips.append("%s: src/shots/%s.tsx could not be opened (%s) — the welded-copy check did not "
                         "run for this register" % (shot, shot, e))
            continue
        # Only the register's STRING LITERALS count. Matching the whole source flagged 'return' and
        # 'reverse' — JS keywords that reached the topic set from a beat whose props legitimately carry a
        # code sample. Topic copy welded into a register always appears as a literal, never as code.
        # Strip BOTH comment forms. Filtering only lines that START with `//` left every continuation line
        # of a `/* … */` or JSX `{/* … */}` block in the text, so a comment DOCUMENTING a defect — quoting
        # the very copy it was about — was read as that copy being welded into the register. A false ERROR
        # blocks delivery on correct code, which is worse than the defect the check exists to catch, and it
        # is the second time this shape has appeared today. One implementation, shared.
        body = _strip_comments(src)
        lits = " ".join(re.findall(r"'([^'\n]{2,120})'|\"([^\"\n]{2,120})\"", body) and
                        [a or b for a, b in re.findall(r"'([^'\n]{2,120})'|\"([^\"\n]{2,120})\"", body)])
        welded = sorted({t for t in topic if len(t) >= 4 and t in lits})[:3]
        if welded:
            errors.append("%s hardcodes this film's own copy (%s) — a register must carry the ARGUMENT "
                          "SHAPE with the topic arriving through props, or it is a one-off in the library's "
                          "clothing. Move that text into shot_props." % (shot, ", ".join(repr(w) for w in welded)))

    # Report repetition GROUPED BY REGISTER — one line per register, not one per pair. A 37-beat film
    # produced seven pair-warnings, which reads as noise; "CardFlip3D carries beats 2, 27, 37 as the same
    # composition" is the sentence a person would actually write.
    for shot, uses in sorted(seen.items()):
        if len(uses) < 2:
            continue
        group = [uses[0][0]]
        base = set(uses[0][1])
        for beat, shape in uses[1:]:
            common = base | set(shape)
            if common and len(base & set(shape)) / len(common) >= PROPS_SAME:
                group.append(beat)
        if len(group) >= 2:
            warns.append("%s carries beats %s with the same prop shape — they will render the same "
                         "composition with the words swapped. Vary the modules per beat, or move one of "
                         "them to a different register."
                         % (shot, ", ".join(str(b) for b in group)))
    return errors, warns


def _in_palette(h, accents):
    """Is hue h inside the film's palette? A film's system is the ARC BETWEEN its two accents, not two
    points: a gradient blending accent into accent2 passes through every hue in between, and those are
    in-system by construction. Measuring distance to the two endpoints instead flagged a green-to-green
    hero card at 120 deg as off-system because the accent sits at 154."""
    if not accents:
        return True
    for a in accents:
        if min(abs(h - a), 360 - abs(h - a)) <= HUE_TOLERANCE:
            return True
    if len(accents) >= 2:
        lo, hi = accents[0], accents[1]
        d = (hi - lo) % 360
        inside = ((h - lo) % 360 <= d) if d <= 180 else ((h - hi) % 360 <= 360 - d)
        if inside:
            return True
    return False


def _block_diff(a, b):
    """The worst 32x32 block's mean absolute difference between two frames.

    The average over the whole frame cannot see one changed digit (0.45 vs 0.00 on a real case); the worst
    local block can (114 vs 0)."""
    from PIL import Image, ImageChops
    d = ImageChops.difference(Image.open(a).convert("L"), Image.open(b).convert("L"))
    w, h = d.size
    px = d.load()
    best = 0.0
    for by in range(0, max(1, h - 32), 32):
        for bx in range(0, max(1, w - 32), 32):
            s = sum(px[bx + x, by + y] for y in range(0, 32, 4) for x in range(0, 32, 4)) / 64.0
            if s > best:
                best = s
    return best


def _hues(png, min_chroma=45, min_val=70):
    import colorsys
    from PIL import Image
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    hs, tot = [], 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) >= min_chroma and max(r, g, b) >= min_val:
                hs.append(colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[0] * 360)
            tot += 1
    return hs, tot


def _content_box(png, thresh=26):
    """Bounding box of everything that departs from the frame's modal (background) luminance."""
    from PIL import Image
    g = Image.open(png).convert("L")
    w, h = g.size
    px = g.load()
    hist = {}
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            hist[px[x, y] // 8] = hist.get(px[x, y] // 8, 0) + 1
    ground = (max(hist, key=hist.get) * 8 + 4) if hist else 0
    x0, x1 = w, 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            if abs(px[x, y] - ground) > thresh:
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
    return (x0, x1, (x1 - x0) / float(w)) if x1 > x0 else (0, 0, 0.0)


# A second tier above the "a line of type per beat" film (median < 6%): the HTTPS test (2026-10-17) measured 7.0% —
# clean line drawings in a mostly empty dark frame — against 28.8% on the GPS film the user approved after asking for
# fuller beats, and 18.3% on the compound test. Half the approved film's median is the line; a WARN, since emptiness
# can be the design, and the design sheet is where it is judged.
SPARSE_MEDIAN = 14.0


def tonal_warnings(ink_by_beat, n_beats):
    """The film-wide ink distribution's warnings, from [(beat, ink %)] over `n_beats` beats."""
    out = []
    inks_sorted = sorted(v for _b, v in ink_by_beat)
    med = inks_sorted[len(inks_sorted) // 2]
    lo, hi = inks_sorted[0], inks_sorted[-1]
    thin = [b for b, v in ink_by_beat if v < 3.0]
    # "across every beat" is a claim, so it states the count it is actually over. A distribution over
    # 5 of 8 beats reads exactly like one over 8 unless it says which.
    _over = "%d of %d beat(s)" % (len(ink_by_beat), n_beats)
    if med < 6.0:
        out.append("the film's TONAL REGISTER is thin (measured over %s): median %.1f%% of the content "
                   "zone carries ink (range %.1f-%.1f%%), and %d beat(s) are under 3%%. A film of "
                   "near-empty frames has no register — the caption carries it and the design is a "
                   "garnish. Give the sparsest beats something the sentence does not already say."
                   % (_over, med, lo, hi, len(thin)))
    elif med < SPARSE_MEDIAN:
        sparse = sorted((bv for bv in ink_by_beat if bv[1] < SPARSE_MEDIAN), key=lambda bv: bv[1])[:4]
        out.append("the film's frames are SPARSE (measured over %s): median %.1f%% of the content zone carries "
                   "ink, under half the GPS film the user approved after asking for fuller frames (28.8%%; the "
                   "compound-interest test 18.3%%). Sparsest: %s. Unless emptiness IS the design, give those "
                   "beats more of the subject — larger, closer, or a second read the sentence does not carry."
                   % (_over, med, ", ".join("beat %d %.1f%%" % bv for bv in sparse)))
    if med >= 6.0 and hi > 12 * max(0.5, med):           # the spread is its own question, sparse film or not
        out.append("the film's ink ranges %.1f-%.1f%% of the content zone around a %.1f%% median "
                   "(measured over %s) — the dense beats read as a different film from the sparse "
                   "ones. Vary within a band, not by an order of magnitude." % (lo, hi, med, _over))
    return out


def _content_ink(png):
    """(ink % of the CONTENT ZONE, None) — the beat's visual density — or (None, reason).

    The three ways this returns nothing are three different repairs (an absent dependency, an unreadable
    PNG, a frame with no content zone), and returning a bare None for all of them silently dropped the
    beat from the film-wide tonal distribution printed below. A median over an unknown subset is not a
    measurement of the film.
    """
    try:
        from PIL import Image
        import numpy as _np
    except Exception as e:                                   # noqa: BLE001 — name it, don't drop the beat
        return None, "%s: %s (Pillow/numpy)" % (type(e).__name__, e)
    try:
        a = _np.asarray(Image.open(png).convert("L"), dtype=_np.int16)
    except Exception as e:                                   # noqa: BLE001 — name it, don't drop the beat
        return None, "%s: %s" % (type(e).__name__, e)
    h, w = a.shape
    from _caption_band import caption_band_px
    zone = a[176:max(177, h - caption_band_px(w, h)), :]
    if zone.size == 0:
        return None, "the content zone is empty at %dx%d (the caption band leaves no rows)" % (w, h)
    mode = _np.bincount(zone.astype(_np.uint8).ravel(), minlength=256).argmax()
    return float((_np.abs(zone - mode) > 25).mean() * 100), None


def _dna_hues(board):
    """The film's own accent hues, from its DNA — the palette everything else is judged against."""
    import colorsys
    meta = board.get("meta", {})
    dna = meta.get("design_dna")
    accents = []
    if isinstance(dna, dict):
        accents = [dna.get("accent"), dna.get("accent2")]
    else:
        name = dna if isinstance(dna, str) else meta.get("shot_template")
        try:
            src = open(os.path.join(_REMOTION, "src", "runtime", "dna.tsx"), encoding="utf-8").read()
            key = re.search(r"^\s*'?%s'?\s*:\s*(\w+),\s*$" % re.escape(str(name)), src, re.M)
            preset = key.group(1) if key else None
            if preset:
                blk = src[src.index("export const %s: DesignDNA" % preset):][:1400]
                accents = [(re.search(r"accent:\s*'(#[0-9a-fA-F]{6})'", blk) or [None, None])[1],
                           (re.search(r"accent2:\s*'(#[0-9a-fA-F]{6})'", blk) or [None, None])[1]]
        except (OSError, ValueError, AttributeError):
            accents = []
    out = []
    for c in accents:
        # An authored DNA may hold any CSS colour. Assuming 6-digit hex crashed the whole proof sheet on
        # `#c33`, `rebeccapurple` or `rgb(...)` — a gate that dies is a gate that gets skipped.
        txt = str(c or "").strip()
        m6 = re.fullmatch(r"#?([0-9a-fA-F]{6})", txt)
        m3 = re.fullmatch(r"#?([0-9a-fA-F]{3})", txt)
        if m6:
            hx = m6.group(1)
        elif m3:
            hx = "".join(ch * 2 for ch in m3.group(1))
        else:
            continue
        r, g, b = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        out.append(colorsys.rgb_to_hls(r, g, b)[0] * 360)
    return out


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    # The still renderer runs with cwd=remotion, so a RELATIVE out_dir made it write beside the bundle
    # while existence was checked from the caller's directory — every beat then reported a failed render.
    out_dir = os.path.abspath(argv[0])
    board_path = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board_path):
        print("[shot_proof] no storyboard.json in %s" % out_dir)
        return 2
    board = json.load(open(board_path, encoding="utf-8"))
    import workshop as _ws
    # A BROKEN WORKSHOP IS NOT A CONTENT FINDING. `run_kwargs` (through `prepare`) raises `WorkshopError` for
    # a blocking problem — a name clash, a DURATION the index cannot wire — and letting that reach the CLI as
    # a bare traceback (exit 1) would read as the same failure this gate uses for "beat(s) NOT measured", when
    # it means the film cannot be proofed at all. Named and exited on its own code (2, "could not measure").
    try:
        wk = _ws.run_kwargs(out_dir)
        ws_durs = _ws.durations(out_dir)
    except _ws.WorkshopError as e:
        for x in e.problems:
            print("  PROBLEM: " + x)
        return 2
    # FILM-SCOPED STATE, RESTORED ON THE WAY OUT. `_FILM_SHOTS`/`_FILM_ENV` are read by every register lookup
    # and every still this run makes; leaving them set after `main` returns (or raises) would have the NEXT
    # film proofed in one process read THIS one's workshop — silently, since both are module-level.
    _FILM_SHOTS[:] = [os.path.join(_ws.workshop_dir(out_dir), "shots")]
    _FILM_ENV.clear()
    _FILM_ENV.update(wk)
    try:
        return _prove(argv, out_dir, board, ws_durs)
    finally:
        _FILM_SHOTS[:] = []
        _FILM_ENV.clear()


def _prove(argv, out_dir, board, ws_durs):
    if str(board.get("meta", {}).get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        print("[shot_proof] not a remotion deck — nothing to prove")
        return 0

    # THE UNIVERSE, parsed from the board rather than counted from whatever rendered. `unmeasured` holds
    # anything that left it, each with a reason a reader can act on; `exempt` holds what the gate
    # deliberately does not judge, said out loud so an exemption cannot be mistaken for a clean result.
    beats = board.get("slides", []) or []
    unmeasured, exempt = [], []
    errors, warns = static_checks(board, skips=unmeasured)
    # Hoisted out of the rendered-checks branch below: the tonal summary reads them unconditionally, so
    # defining them only when stills are rendered made `--no-stills` — the fast path this file's own usage
    # line recommends while authoring — die with an UnboundLocalError.
    inks, ink_by_beat = [], []
    rendered, fresh = 0, set()          # `fresh`: the beats rendered THIS run — the design sheet shows only those

    # THE RENDERED CHECKS RUN BY DEFAULT.
    #
    # An opt-in gate behind `--stills` is not a detector: two registers in a delivered film parked their own
    # subtitle inside the band the renderer reserves for the burned caption, this script owns the check that
    # measures exactly that, and without the flag it prints "OK (static only)" — nobody sees the flag they
    # did not pass. The band violation was found by a human looking at a frame, which is the one review that
    # does not scale.
    #
    # The static checks read source; only a RENDER can see what the frame actually looks like, which is the
    # half that matters. `--no-stills` still exists for a fast source-only pass while authoring.
    global _NO_CACHE
    _NO_CACHE = "--no-cache" in argv
    if "--no-stills" not in argv:
        import shot_still_qa
        import workshop as _ws
        # BUILT THINGS TAKE EVERY WORD FROM THE FILM (below, after each beat's `rendered += 1`) — computed only
        # here, under the rendered checks: under `--no-stills` nothing below reads it, and computing it outside
        # `_prove` left an exception free to skip the `finally` in `main` that clears the film's own state.
        # `baked_words` degrades cheaply (an os.walk, no subprocess) when the film's workshop is empty, so this
        # costs a real scan only on a film that actually has one.
        _bw = _ws.baked_words(out_dir, _ws.source_files(out_dir))
        film_shots, declared = _ws.shot_names(out_dir), _bw["declared"]
        # `problems` carries the scan's own HITS (a baked word it found) alongside a genuine "could not run"
        # reason, in the SAME list — treating any non-empty list as "the scan is broken" disabled the frame
        # check entirely for every beat the moment ONE baked word existed anywhere in the workshop. Only a
        # problem ending in workshop.NOTHING_CHECKED means the scan itself did not run.
        declared_broken = [p for p in _bw["problems"] if p.endswith(_ws.NOTHING_CHECKED)]
        dna_hues = _dna_hues(board)
        beat_by_index = {i + 1: (sl.get("shot_props") or {})
                         for i, sl in enumerate(board.get("slides", []))}
        proof = os.path.join(out_dir, "_proof")
        os.makedirs(proof, exist_ok=True)
        dna_ref = board.get("meta", {}).get("design_dna") or board.get("meta", {}).get("shot_template")
        aspect = board.get("meta", {}).get("aspect")
        for _pos, s in enumerate(board.get("slides", []), start=1):
            beat = _pos
            shot = s.get("shot")
            if not shot:
                unmeasured.append("beat %d: no `shot` — nothing to render, so every RENDERED check "
                                  "(off-frame, caption band, palette, empty/dead frame, ink) is skipped "
                                  "for this beat" % beat)
                continue
            src, src_err = "", None
            try:
                src = open(_src_path(shot), encoding="utf-8").read()
            except OSError as e:
                src_err = str(e)
            # A WORKSHOP SHOT'S DURATION comes from workshop.durations() (scripts/workshop.py) — the same
            # comment-stripped, typed-declaration-aware reader text_safe_qa and cjk_type_qa use, so a
            # workshop beat settles at the same frame in every gate. The regex below stays the library's
            # own reader, so a library register's frame does not move.
            dm = None if shot in ws_durs else re.search(r"export const DURATION\s*=\s*(\d+)", src)
            dur = ws_durs.get(shot) if shot in ws_durs else (int(dm.group(1)) if dm else None)
            # THE FRAME IS THE REGISTER'S OWN, never a house constant. `remotion still` REFUSES a frame past
            # the end of a composition rather than clamping, so a fixed frame silently excludes every
            # register shorter than it — the ink gate lost seven registers that way, three of which were
            # genuinely broken. The fallback below is still a constant, so when it is used the beat is
            # reported as proofed at a frame the register may never reach, instead of passing as if it were
            # measured at its settled point.
            # ...AND IT IS THE SAME SETTLED FRAME EVERY OTHER INSTRUMENT USES. `int(DURATION * 0.88)` was a
            # third answer: `useT()` holds each shot still for SEAM_FRAMES at both edges and runs its span
            # between them, so the settled point is the INVERSE of that mapping, not a fraction of the clip.
            # Measured across the library, this literal sat up to 15 frames from it on all 170 registers —
            # every proof sheet in this repo's history was read at a frame no other gate measured.
            frame = int(round(_rr.frame_at_t(dur, _rr.SETTLED_T))) if dur is not None else 120
            if dur is None:
                unmeasured.append("beat %d (%s): the settled frame cannot be derived — %s. Proofed at the "
                                  "fallback frame %d, which this register may never reach (if it is "
                                  "shorter, the still below simply fails)."
                                  % (beat, shot,
                                     "%s could not be opened (%s)" % (_src_path(shot), src_err) if src_err
                                     else "%s exports no `DURATION` — export it" % _src_path(shot),
                                     frame))
            pj = os.path.join(proof, "beat_%02d.json" % beat)
            payload = _rr.film_shot_props(s, out_dir)
            if dna_ref:
                payload["dna"] = dna_ref
            # The proof sheet must render at the FILM'S aspect. Without this it rendered every shot at
            # 1920x1080 and then measured the caption band (150px, the 16:9 value) and the content width
            # against a frame the film will never show — a portrait film's proof sheet was checking
            # geometry that does not exist.
            if aspect:
                payload["aspect"] = aspect
            json.dump(payload, open(pj, "w", encoding="utf-8"), ensure_ascii=False)
            png = os.path.join(proof, "beat_%02d.png" % beat)
            key = _cache_key(out_dir, s, board.get("meta", {}),
                             {"frame": frame, "payload": payload, "film_shot": shot in film_shots,
                              "declared": sorted(map(str, declared or [])), "broken": bool(declared_broken)})
            hit = _cached(proof, key, ".png")
            # --public-dir is NOT optional here. Every register in the real-image tier resolves its
            # picture through staticFile(), which without a public dir points at a path that does not
            # exist — so those shots ALWAYS failed to render and this gate reported a hard error for a
            # beat that is fine in the film. Worse, it meant the proof sheet was blind to exactly the
            # class most likely to carry a wrong or broken image. The film render passes the out_dir;
            # so does this.
            if hit:
                shutil.copyfile(hit, png)
                r = subprocess.CompletedProcess([], 0, "", "")
            else:
                r = _c.run_render(["npx", "remotion", "still", "src/index.ts", shot, png,
                                    "--frame=%d" % frame, "--gl=angle", "--props=" + pj, "--log=error",
                                    "--public-dir=" + os.path.abspath(out_dir)],
                                   cwd=_REMOTION, capture_output=True, text=True, **_FILM_ENV)
                if r.returncode == 0 and os.path.exists(png):
                    _keep(proof, key, ".png", src=png)
            if r.returncode != 0 or not os.path.exists(png):
                why = _stderr_reason(r.stderr)
                errors.append("beat %d (%s): the shot FAILED to render standalone at frame %d — %s"
                              % (beat, shot, frame, why))
                unmeasured.append("beat %d (%s): no still, so off-frame / caption-band / palette / "
                                  "empty-frame / ink were not measured — %s" % (beat, shot, why))
                continue
            rendered += 1
            fresh.add(beat)
            # BUILT THINGS TAKE EVERY WORD FROM THE FILM — asked of the frame. On a film-local register every run
            # is asked; on a library register holding an object, only what is inside the object's slot. One more
            # render, only on beats that show a built thing.
            _held = [ref for _p, ref in _ws.object_refs(_ws.shot_source(out_dir, shot), s.get("shot_props") or {}, shot)
                     if isinstance(ref, dict)]
            if shot in film_shots or _held:
                if declared_broken:
                    # The declared-word scan itself is broken (node/tsc missing, jsx_words.cjs failed) — an
                    # EMPTY declared list here is not "nothing is declared", it is "the question could not be
                    # asked", and proceeding as the former would report every `@fixed-text` word as unfed.
                    unmeasured.append("beat %d (%s): the words-from-props check did not run — the workshop's "
                                      "declared-word scan could not run (%s)" % (beat, shot, declared_broken[0]))
                else:
                    _uk = _cached(proof, key, ".unfed.json")
                    if _uk:
                        words, total, reason = json.load(open(_uk, encoding="utf-8"))
                    else:
                        words, total, reason = _unfed_text(shot, payload, frame, proof, beat, out_dir,
                                                            "all" if shot in film_shots else "slots", declared)
                        if words is not None:
                            _keep(proof, key, ".unfed.json", data=[words, total, reason])
                    if words is None:
                        unmeasured.append("beat %d (%s): the words-from-props check gave no answer — %s"
                                          % (beat, shot, reason))
                    elif words:
                        more = " (%d more not shown)" % (total - len(words)) if total > len(words) else ""
                        errors.append("beat %d (%s): %d word(s) on the frame that no prop supplied%s: %s — a "
                                      "built thing takes every word from the film's props (pass it in; a word "
                                      "that is part of the form is declared `// @fixed-text: <why>` in the "
                                      "workshop code)"
                                      % (beat, shot, total, more, " / ".join(repr(w) for w in words)))
            if shot in film_shots:
                _gc = _ground_claim(png, shot, out_dir, dna_ref)
                if _gc:
                    kind, msg = _gc
                    (errors if kind == "error" else unmeasured).append("beat %d (%s): %s" % (beat, shot, msg))
            else:
                _lc = _library_caption_ground(png, shot, s, dna_ref)
                if _lc:
                    kind, msg = _lc
                    (errors if kind == "error" else exempt).append("beat %d (%s): caption ground — %s"
                                                                   % (beat, shot, msg))
            # A figure-bearing register must be showing the RIGHT figure at the frame the gate captures.
            if shot in FIGURE_SHOTS and not dm:
                unmeasured.append("beat %d (%s): the figure-settle check needs the register's DURATION to "
                                  "find the mid-scene frame and %s.tsx declares none — the on-screen "
                                  "number was not checked for being caught mid-roll" % (beat, shot, shot))
            if shot in FIGURE_SHOTS and dm:
                mid_png = os.path.join(proof, "beat_%02d_mid.png" % beat)
                _mk = _cached(proof, key, ".mid.png")
                if _mk:
                    shutil.copyfile(_mk, mid_png)
                    rm = subprocess.CompletedProcess([], 0, "", "")
                else:
                    rm = _c.run_render(["npx", "remotion", "still", "src/index.ts", shot, mid_png,
                                         "--frame=%d" % int(int(dm.group(1)) * 0.5), "--gl=angle",
                                         "--props=" + pj, "--log=error",
                                         "--public-dir=" + os.path.abspath(out_dir)],
                                        cwd=_REMOTION, capture_output=True, text=True, **_FILM_ENV)
                    if rm.returncode == 0 and os.path.exists(mid_png):
                        _keep(proof, key, ".mid.png", src=mid_png)
                if rm.returncode != 0 or not os.path.exists(mid_png):
                    # The one ERROR that guards an on-screen NUMBER. Dropping it in silence when the
                    # second still fails is how a film ships a digit caught mid-flight with a green gate.
                    unmeasured.append("beat %d (%s): the mid-scene still did not render, so the "
                                      "figure-settle check did not run on a register whose subject IS a "
                                      "number — %s" % (beat, shot, _stderr_reason(rm.stderr)))
                if rm.returncode == 0 and os.path.exists(mid_png):
                    d = _block_diff(mid_png, png)
                    if d > FIGURE_SETTLE_BLOCK:
                        errors.append("beat %d (%s): the figure is still moving at the mid-scene frame "
                                      "(block diff %.0f > %d) — that is the frame the delivery gate "
                                      "captures, so the film ships an unsourced number"
                                      % (beat, shot, d, FIGURE_SETTLE_BLOCK))
            m = shot_still_qa.measure(png)
            # NO OFF-FRAME ERROR FROM BORDER INK. Coverage of the action-safe border runs OPPOSITE to the defect: a cut
            # word leaves a thin band (low), a deliberate full-bleed plane a solid field (high) — measured zero true
            # positives and four false ones (references/launch-film-study.md "The gate that was measuring backwards"),
            # and the compound test's full-bleed passbook cloth was called OFF-FRAME here. Cut TYPE is asked of the
            # DOM by text_safe_qa; a cut graphic is judged on the design sheet.
            if m["caption"] > shot_still_qa.CAPTION_FRAC_ERR:
                errors.append("beat %d (%s): %.1f%% ink in the caption band — the burned subtitle will sit "
                              "on the shot's own content" % (beat, shot, 100 * m["caption"]))
            # A BEAT SHOWING A PHOTOGRAPH CANNOT PASS A PALETTE CHECK THAT COUNTS THE PHOTOGRAPH. The
            # metric is meant to catch a register hardcoding an ink the DNA never chose; it was measuring
            # the sky in a Wikimedia photo as "a hardcoded colour overriding the DNA" and reporting 73% on
            # a beat whose own ink was 0% off-palette. No register change can move a photograph's sky, and
            # none should — it is the real evidence the beat exists to show. So a beat that supplies an
            # image is exempt: what is left to police there is its drawn ink, and the frame cannot separate
            # the two without knowing where the image sits.
            beat_props = (beat_by_index.get(beat) or {})
            shows_image = any(isinstance(v, str) and re.search(r"\.(jpe?g|png|webp|avif)$", v, re.I)
                              for v in beat_props.values())
            if not dna_hues:
                exempt.append("beat %d (%s): palette — this film's DNA yielded no accent hue "
                              "(meta.design_dna/%r), so there is nothing to judge a colour against"
                              % (beat, shot, dna_ref))
            elif shows_image:
                exempt.append("beat %d (%s): palette — the beat supplies a photograph, whose own colours "
                              "no register change can move" % (beat, shot))
            elif shot in SEMANTIC_COLOUR_SHOTS:
                exempt.append("beat %d (%s): palette — %s"
                              % (beat, shot, SEMANTIC_COLOUR_SHOTS[shot]))
            if dna_hues and not shows_image:
                hs, _ = _hues(png)
                if not hs:
                    exempt.append("beat %d (%s): palette — the frame carries no chromatic ink above the "
                                  "measurement floor (a monochrome beat)" % (beat, shot))
                if hs:
                    off = [h for h in hs if not _in_palette(h, dna_hues)]
                    if len(off) / len(hs) > OFF_SYSTEM_FRAC and shot not in SEMANTIC_COLOUR_SHOTS:
                        import statistics
                        warns.append("beat %d (%s): %.0f%% of the frame's chromatic ink is outside the film's "
                                     "palette (median hue %.0f deg vs accents %s) — a hardcoded colour is "
                                     "overriding the DNA"
                                     % (beat, shot, 100 * len(off) / len(hs), statistics.median(off),
                                        [round(a) for a in dna_hues]))
            x0, x1, frac = _content_box(png)
            if not frac:
                # NOTHING departs from the ground: the beat rendered an empty frame. Guarding the
                # dead-frame branch with `if frac and ...` let the emptiest possible result pass silently.
                errors.append("beat %d (%s): the frame is EMPTY — nothing departs from the background"
                              % (beat, shot))
            _ink, _ink_why = _content_ink(png)
            if _ink is not None:
                inks.append(_ink); ink_by_beat.append((beat, _ink))
            else:
                unmeasured.append("beat %d (%s): ink density could not be measured (%s) — this beat is "
                                  "NOT in the tonal-register distribution below" % (beat, shot, _ink_why))
            if frac and frac < NARROW_FRAC:
                m2 = shot_still_qa.measure(png)
                off = abs((x0 + x1) / 2 - m2["w"] / 2) / float(m2["w"])
                if off > OFFSET_FRAC:
                    warns.append("beat %d (%s): content spans %.0f%% of the width and sits %.0f%% off centre "
                                 "— one side of the frame is dead" % (beat, shot, 100 * frac, 100 * off))

    # THE FILM'S TONAL REGISTER, measured across every beat rather than judged one frame at a time. A
    # film whose frames are all nearly empty and whose few dense ones are outliers has no register — it
    # reads as a slideshow of captions with occasional graphics. Measured on a delivered film: median 5.6%
    # of the content zone carried ink, with a 1.1%-67.7% spread, i.e. most beats were a line of type on a
    # page. No per-beat check can see that; only the distribution can, so it is computed here where every
    # beat's still already exists.
    if inks:
        warns.extend(tonal_warnings(ink_by_beat, len(beats)))
    elif "--no-stills" not in argv and beats:
        unmeasured.append("the film's TONAL REGISTER: no beat yielded an ink measurement, so the "
                          "distribution check did not run at all")

    sheet = None
    if "--no-stills" not in argv and rendered:
        try:
            sheet = design_sheet(out_dir, board, only=fresh)
        except Exception as e:                           # noqa: BLE001 — the sheet is for eyes; the checks stand
            unmeasured.append("the design review sheet could not be tiled: %s" % e)
    for e in errors:
        print("  ERROR: " + e)
    for w in warns:
        print("  warn : " + w)
    for u in unmeasured:
        print("  NOT MEASURED: " + u)
    for x in exempt:
        print("  n/a  : " + x)
    static_only = "--no-stills" in argv
    # COVERAGE, not just findings. The universe is the board's beats; `rendered` is how many of them this
    # run actually put on a frame. A gate that measured 5 of 8 must not print a line that reads as 8.
    if static_only:
        cover = "static checks on %d beat(s); 0 rendered (--no-stills)" % len(beats)
    else:
        cover = "rendered %d of %d beat(s)" % (rendered, len(beats))
    state = "FAIL" if errors else ("INCOMPLETE" if unmeasured else "OK")
    print("[shot_proof] %s  %s · %d error(s), %d warning(s), %d not measured, %d n/a%s"
          % (state, cover, len(errors), len(warns), len(unmeasured), len(exempt),
             "  (static only — drop --no-stills for the rendered checks)" if static_only else ""))
    if sheet:
        print("[shot_proof] design review sheet: %s — every beat's settled frame on one page. SHOW IT at the 3.6 "
              "checkpoint (copy it to the Desktop): composition, type size and the subject's craft are judged on "
              "the picture, never on a list of form names" % sheet)
    return 1 if (errors or unmeasured) else 0


def design_sheet(out_dir, board, cols=3, tile_w=640, only=None):
    """Tile `_proof/beat_NN.png` into `<out_dir>/_design_review.png`, each labelled `beat N · route · shot`.

    WHY. The 3.6 checkpoint showed the user a content plan, a palette and a list of FORM NAMES; what the user
    corrected on the GPS film — titles all top-left, labels too small, half-empty frames, satellites too small —
    could only be seen with every beat side by side, and that page existed only because the orchestrator made it by
    hand. The compound-interest test's sheet showed nine flat ledger pages in a row the same way. It is now the
    proof run's own output."""
    from PIL import Image, ImageDraw
    slides = board.get("slides") or []
    tiles = []
    for pos, sl in enumerate(slides, 1):
        png = os.path.join(out_dir, "_proof", "beat_%02d.png" % pos)
        if not os.path.exists(png) or (only is not None and pos not in only):
            continue                                     # a beat that did not render THIS run shows no old frame
        fit = sl.get("shot_fit") if isinstance(sl.get("shot_fit"), dict) else {}
        tiles.append(("beat %d · %s · %s" % (pos, fit.get("verdict") or "?", sl.get("shot")), png))
    if not tiles:
        return None
    first = Image.open(tiles[0][1])
    th = int(round(tile_w * first.height / float(first.width)))
    pad, label = 16, 34
    rows = -(-len(tiles) // cols)
    sheet = Image.new("RGB", (cols * tile_w + (cols + 1) * pad, rows * (th + label + pad) + pad), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets",
                                               "fonts", "DejaVuSans.ttf"), 20)
    except Exception:                                    # noqa: BLE001 — a default face still labels the tile
        font = None
    for k, (text, png) in enumerate(tiles):
        r, c = divmod(k, cols)
        x, y = pad + c * (tile_w + pad), pad + r * (th + label + pad)
        d.text((x, y + 6), text, fill=(235, 235, 235), font=font)
        sheet.paste(Image.open(png).convert("RGB").resize((tile_w, th)), (x, y + label))
    out = os.path.join(out_dir, "_design_review.png")
    sheet.save(out)
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
