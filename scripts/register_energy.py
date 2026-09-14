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
        h.update(open(dep, "rb").read())
    return h.hexdigest()[:16]


def source_hashes():
    """{register: sha256 over its .tsx AND the runtime modules it imports}. A measured row describes the
    SOURCE it was rendered from, and nothing said so: three registers were rewritten and the committed
    manifest went on reporting 0.6%, 2.0% and 1.0% against measured 32.2%, 51.1% and 2.4%, while
    `density_advice.py` — which reads this file — kept offering one of the densest registers in the library as
    a starved beat's problem. A record nobody can tell is stale is not a record, it is a lie with a
    timestamp."""
    return {os.path.basename(f)[:-4]: source_hash(os.path.basename(f)[:-4])
            for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx")))}


def stale(data):
    """[(register, why)] for rows that no longer describe their source. Costs no renders, so it can run
    anywhere — which is the point: a check that needs 149 renders is a check nobody runs."""
    now = source_hashes()
    rows = data.get("registers") or {}
    was = data.get("_source") or {}
    out = []
    for n in sorted(rows):
        if n not in now:
            out.append((n, "the register is gone"))
        elif n not in was:
            out.append((n, "measured before source hashes were recorded"))
        elif was[n] != now[n]:
            out.append((n, "source changed since it was measured"))
    for n in sorted(set(now) - set(rows)):
        out.append((n, "never measured"))
    return out


def floors():
    """The floors, TAKEN from film_energy_qa — never restated.

    Restating them is how this repo's caption band became four disagreeing copies. A diagnostic that ranks
    registers against a private copy of the numbers would keep ranking against them after the real gate moved.
    """
    return {"motion_p75": fe.MOTION_P75_FLOOR, "ink_median": fe.INK_FLOOR, "luma_range": fe.LUMA_RANGE_FLOOR}


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


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
    props = {}
    if dna:
        props["dna"] = dna
    props.update(extra or {})
    if props:
        cmd.append("--props=" + json.dumps(props))
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REMOTION)
    return os.path.exists(mp4), ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1:] or [""]


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
        print("[register_energy] %s  %d of %d row(s) no longer describe their source%s"
              % ("FAIL" if rows else "OK", len(rows), len(data.get("registers") or {}),
                 " — re-run `%s`" % REGEN if rows else ""))
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
            m = fe.measure(mp4)
            if not isinstance(m, dict):
                failed.append("%s (unmeasurable: %r)" % (n, m))
                continue
            rows[n] = {"motion_p75": round(m["motion_p75"], 4),
                       "ink_median": round(m["ink_median"], 3),
                       "luma_range": round(m["luma_range"], 3),
                       "seconds": round(m["seconds"], 1)}
            # The settled still, for the footprint. Written whether or not --stills was asked for, into a
            # temp dir if not: a diagnosis that cannot distinguish "too small" from "too flat" sends every
            # register the same advice, and the two need opposite work.
            sd = stills or os.path.join(tmp, "_fp")
            stills_from(mp4, sd, n, durs[n])
            fp = footprint(os.path.join(sd, "%s_b.png" % n))
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
                src = dict(prev.get("_source") or {})
                src.update({n: h for n, h in hashes.items() if n in rows})
                # a register that now renders is no longer a hole; one that now fails becomes one
                keep = [f for f in (prev.get("_failed") or []) if f.split(" (")[0] not in names]
                data["registers"] = dict(sorted(merged.items()))
                data["_source"] = src
                data["_failed"] = sorted(keep + failed)
        json.dump(data, open(MANIFEST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("[register_energy] wrote %s (%d rows%s)"
              % (MANIFEST, len(data["registers"]), ", merged" if only else ""))

    regs = data["registers"]
    fl = data["_floors"]
    unknown = data.get("_failed") or []
    def fails(r):
        return ((r["motion_p75"] < fl["motion_p75"]) + (r["ink_median"] < fl["ink_median"])
                + (r["luma_range"] < fl["luma_range"]))

    def why(r):
        """Which KIND of empty, when it is empty. The two need opposite fixes, so naming one is the
        difference between directable work and a number."""
        if r["ink_median"] >= fl["ink_median"]:
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
    print("\n[register_energy] %d registers · floors motion %.4f / ink %.0f%% / light %.3f"
          % (len(regs), fl["motion_p75"], fl["ink_median"] * 100, fl["luma_range"]))
    if unknown:
        print("[register_energy] %d register(s) UNMEASURED — absent from the ranking below, not passing it: %s"
              % (len(unknown), ", ".join(u.split(" ")[0] for u in unknown)))
    print("[register_energy] under all three: %d · two: %d · one: %d · clear: %d" % (n3, n2, n1, n0))
    print("\n%-24s %8s %7s %7s %7s  %-4s %s"
          % ("register", "motion", "ink", "light", "footprnt", "why", "under"))
    for n, r in ranked[:40]:
        marks = "".join(m for m, bad in (("M", r["motion_p75"] < fl["motion_p75"]),
                                         ("D", r["ink_median"] < fl["ink_median"]),
                                         ("L", r["luma_range"] < fl["luma_range"])) if bad)
        print("%-24s %8.4f %6.1f%% %7.3f %7s  %-4s %s"
              % (n, r["motion_p75"], r["ink_median"] * 100, r["luma_range"],
                 "-" if r.get("footprint") is None else "%.0f%%" % (r["footprint"] * 100),
                 why(r), marks or "-"))
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
