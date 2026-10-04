#!/usr/bin/env python3
"""Is any TYPE being cut off by the frame? — asked of the DOM, per beat.

    python3 scripts/text_safe_qa.py <out_dir>      # audit this film's beats, with their real copy
    python3 scripts/text_safe_qa.py --library      # sweep every register (dna=product, the themed path)
    python3 scripts/text_safe_qa.py --library --aspect=9:16     # ...at the aspect the film actually ships at
    python3 scripts/text_safe_qa.py --library --only=Id,Id      # iterate on one finding without 160 renders
    python3 scripts/text_safe_qa.py --library --all-aspects     # every aspect the renderer offers
    python3 scripts/text_safe_qa.py --library --cjk             # ...with CHINESE copy, not the demo strings
    python3 scripts/text_safe_qa.py --library --all-dna         # ...in every FACE the renderer offers

EXIT 0 = measured its whole universe and found nothing · 1 = findings · 2 = part of the universe was NOT
measured. The scope line always names WHICH universe a run covered — `N of M beats` for a film, `N of M
registers` for the catalogue, with the catalogue's own size beside a run narrowed by --only/--limit — so a
sweep of eight beats can never be read as the library.

WHY THIS REPLACES A PIXEL GATE. `frame_safe_qa.py`'s EDGE-BLEED check asks how much ink sits in the outer
border and calls a high answer an overflow. Measured on real cases, it is INVERTED:

    genuinely cut by the canvas   AtomOrbital 1.45%   BlockAssembly 1.00%   (its 4.5% ERROR floor: all pass)
    deliberately full-bleed       FlowField 9.6%   GameOfLife 12.7%   AuroraFlow 14.1%   HalftonePop 35.2%
                                  (all four blocked)

It would also refuse 100% of the sampled frames of OpenAI's launch film, 57% of Figma's and 57% of
Anthropic's, while passing all 30 frames of a film that measured as inert. The inversion is structural: a cut
word makes a THIN band and a flood makes a SOLID field, so coverage runs opposite to the defect. Moving the
threshold cannot fix a sign error. Two structural statistics were tried on the same samples (run structure
along the border; row-occupancy of border ink) and neither separated the classes.

The browser has the answer exactly. `remotion/src/runtime/textSafe.tsx` walks the DOM at the settled frame,
intersects each text element's box with any ancestor that CLIPS, and reports what still crosses the canvas.

DELIBERATE CROPS ARE NOT FINDINGS, and no flag is needed to say so: text clipped by an `overflow: hidden`
ancestor SMALLER than the frame is a marquee, a mask, a crop window — the author built the container, and the
container is the intent. Text cut by the canvas with no such ancestor is a layout that did not fit. (A
container the size of the frame is the frame, not a crop; Remotion's own AbsoluteFill sets `overflow: hidden`,
and the first version of this audit exempted every register in the library by counting it.)
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c                                             # noqa: E402
import render_remotion as rr                                     # noqa: E402  (needs the path above)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REMOTION = os.path.join(_ROOT, "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
TAG = "TEXT-SAFE-VIOLATIONS "


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


def audit_shot(shot, props, frame, tmp_png, public_dir=None, env=None):
    """Render one shot with the audit armed. Returns [] (clean) or the violation list it reported.

    Props travel by FILE, never on the command line: a beat's real copy is routinely CJK, and a multibyte
    character in a --props argument breaks the arg before remotion ever sees it.
    """
    payload = dict(props or {})
    payload["textSafe"] = True
    pf = tmp_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
    # A RENDER THAT FELL OVER IS NOT A TYPE DEFECT, AND IT USED TO BE FILED AS ONE. A browser that loses its
    # connection ("at TCP.<anonymous>") or dies mid-launch produces a non-zero exit and no payload, and the
    # reader gets a finding naming a register whose type is fine — measured at roughly one in twenty during a
    # loaded sweep, on SpeedLimit, GradientTilt and RansomZine, none of which reproduced alone. The
    # props-file race behind most of them is fixed, but a flaky render is still a flaky render, so it is
    # RETRIED once. What survives a retry is reported, and reported as a FAILURE — a frame nobody measured —
    # rather than as a finding about the copy on it.
    import workshop as _ws
    blob, r = "", None
    for _attempt in (1, 2):
        # THE FILM'S OWN ASSETS HAVE TO BE SERVED, and this never served them. `render_remotion.py` runs the
        # film with `--public-dir=<out_dir>`, so a register that draws a file the FILM supplies — every
        # evidence register, a brand mark, `PointerTour`'s captured page, and a 17-sprite contact sheet —
        # resolves its `staticFile()` against a directory this gate did not mount. The image 404s, the render
        # dies, and the beat is reported as a FAILURE: one beat of eight with no machine type reading at all,
        # which is the "a check that cannot run must say it did not run" hole from the inside.
        cmd = ["npx", "remotion", "still", "src/index.ts", shot, tmp_png,
               "--frame=%d" % frame, "--gl=angle", "--log=error",
               "--props=" + os.path.abspath(pf)]
        if public_dir:
            cmd.append("--public-dir=" + os.path.abspath(public_dir))
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REMOTION, **_ws.env_kwargs(env))
        blob = (r.stdout or "") + (r.stderr or "")
        if TAG in blob or r.returncode == 0:
            break
    if TAG in blob:
        # The payload arrives inside a render-cancelling error, wrapped in a stack trace. Let the JSON parser
        # find its own end: a hand-rolled bracket counter closes early on a ']' inside a string, and a beat's
        # copy is exactly where such a character shows up. (A test drove that bug out.)
        raw = blob.split(TAG, 1)[1]
        try:
            found, _end = json.JSONDecoder().raw_decode(raw)
            return found
        except json.JSONDecodeError:
            return [{"text": "(unparseable payload)", "out": {}}]
    if r.returncode != 0:
        # A render that failed measured NOTHING. Reporting it as clean is how a gate quietly stops gating —
        # so it still surfaces, but as a RENDER FAILURE after a retry, not as a finding about the type.
        from shot_proof import _stderr_reason        # the MESSAGE, never the last line of a stack
        return [{"text": "(render FAILED twice — nothing was measured on this frame: %s)"
                         % _stderr_reason(blob, limit=160), "out": {}}]
    return []


def _describe(v):
    """Name the DEFECT, not just the string. A finding that prints a line of copy and a font size leaves the
    reader to work out what is wrong with it, and the two defects this audit reports want opposite fixes:
    text off the canvas is a layout that did not fit, text in the caption band is a layout that fit into
    space it does not own."""
    parts = []
    sides = ", ".join("%s %spx" % (k, val) for k, val in sorted((v.get("out") or {}).items()))
    if sides:
        parts.append("CUT OFF — " + sides)
    if v.get("band"):
        parts.append("IN THE CAPTION BAND by %spx — the burned caption draws over it" % v["band"])
    return "%r %s%s" % (v.get("text", ""), "; ".join(parts),
                        "  [%s]" % v["font"] if v.get("font") else "")


def scan_film(out_dir):
    """(findings, checked, universe, skipped) — the last two are the point.

    `if not shot or shot not in durs: continue` dropped two different beats into one silent branch, and the
    caller then printed `N beats` where N was the number that SURVIVED it. A film of twelve beats, eight of
    which select a register, printed "8 beats" — a line indistinguishable from a twelve-beat film fully
    covered. The universe is the board's slides; anything that leaves it is named with the reason.
    """
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    durs = durations()
    import workshop as _ws
    # A FILM'S OWN SHOTS are registers too: measured the same way, rendered in a bundle that holds its workshop.
    durs.update(_ws.durations(out_dir))
    env = _ws.prepare(out_dir)
    findings, checked, skipped = [], 0, []
    slides = board.get("slides") or []
    tmp = os.path.join(out_dir, "._textsafe.png")
    for i, s in enumerate(slides, 1):
        shot = s.get("shot")
        if not shot:
            skipped.append("scene %02d: selects no register (a still or image beat) — this audit reads a "
                           "register's DOM and has none to read" % i)
            continue
        if shot not in durs:
            skipped.append("scene %02d: %r is not a register in shots/ (no DURATION could be read for it), "
                           "so no frame of this beat was measured" % (i, shot))
            continue
        import render_remotion as _rr                    # the renderer's own reading of a beat's props
        props = _rr.film_shot_props(s, out_dir)
        if meta.get("design_dna") is not None:
            props.setdefault("dna", meta["design_dna"])
        if meta.get("aspect"):
            props.setdefault("aspect", meta["aspect"])
        frame = int(round(rr.frame_at_t(durs[shot], rr.SETTLED_T)))
        checked += 1
        for v in audit_shot(shot, props, frame, tmp, public_dir=out_dir, env=env):
            findings.append("scene %02d (%s): %s" % (i, shot, _describe(v)))
    for p in (tmp, tmp + ".props.json"):
        if os.path.exists(p):
            os.remove(p)
    return findings, checked, len(slides), skipped


DEFAULT_DNA = "product"


def scan_library(limit=None, aspect=None, dna=DEFAULT_DNA, only=None, cjk=False):
    """Sweep the catalogue. `aspect` matters: a register laid out for 16:9 can hold its type comfortably and
    still clip it at 9:16, which is the failure mode a portrait film meets and a landscape sweep never sees.

    `dna` matters for the same reason it does in register_energy.py: the Design DNA sets the type family and
    therefore every metric this audit measures, and EVERY delivered film has one. Sweeping with bare props
    measures the un-themed fallback, a mode no film ships."""
    durs = durations()
    # `--only` is for ITERATING on a finding. A sweep is 160 renders and ~10 minutes; fixing the 21 registers
    # the 1:1 sweep found meant either re-running all of it per edit or trusting the edit, and trusting the
    # edit is how a fix that moves the number without clearing the band gets committed. Names that are not
    # registers are named back, rather than silently sweeping nothing and printing OK.
    if only:
        unknown = [n for n in only if n not in durs]
        if unknown:
            raise SystemExit("[text_safe] not a register: %s" % ", ".join(unknown))
        names = sorted(only)
    else:
        names = sorted(durs)[: limit or None]
    # A SCRATCH FILE WITH A FIXED NAME IS A RACE. Two of these sweeps running at once — a library sweep beside
    # a targeted one, which is the normal way this repo is used — write the same PNG and the same
    # `<png>.props.json` beside it, and one process reads the other's half-written props. Remotion answers
    # "Check that your input is parseable using `JSON.parse`", the sweep files that as a FINDING against
    # whichever register happened to be mid-render, and the reader chases a type defect that never existed:
    # measured at roughly one in twenty registers, on SpeedLimit, TermThink, GradientTilt and RansomZine, none
    # of which reproduced alone. The pid makes the scratch path this process's own.
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_textsafe_lib.%d.png" % os.getpid())
    base = {}
    if aspect:
        base["aspect"] = aspect
    if dna:
        base["dna"] = dna
    # The four evidence registers REFUSE to render without a real image (runtime/evidence.ts), so a bare
    # sweep reports them as four render failures — a true statement about the sweep and a useless one about
    # the registers. Same fixture the energy sweep uses, from the same parsed call sites: one definition.
    try:
        import register_energy as _re
        _re.ensure_fixture()
        evidence = _re.evidence_props()
    except Exception:
        evidence = {}
    # THE BAND WAS ONLY EVER CHECKED IN ENGLISH. This sweep feeds each register its own demo strings, which
    # are short Latin ones; `cjk_type_qa` feeds Chinese but asks a different question (does the type collide
    # with itself), and neither asked whether CHINESE copy lands in the caption band. Chinese is where it
    # would: a Han glyph is a full em wide, the leading floor is higher, so the same sentence takes more
    # lines and reaches further down. Same fixtures as the CJK gate — one definition of "what Chinese copy
    # for this register looks like", shaped from its own prop signature.
    cjk_fixture, not_cjk = {}, []
    if cjk:
        import cjk_type_qa as _cjk
        for n in names:
            # A SHAPING FAILURE USED TO BECOME AN ENGLISH SWEEP WEARING THE WORD "CJK". `except Exception:
            # cjk_fixture[n] = {}` left the register with nothing but base props, so it rendered its LATIN
            # demo defaults — and the scope line still said "CJK fixtures". Chinese is where this audit's
            # findings live (a Han glyph is a full em, the leading floor is higher, the same sentence
            # reaches further down the frame), so a register swept in English under a CJK headline is a
            # register this run says nothing about. Same for one whose props shaped to nothing at all.
            try:
                props, _untestable = _cjk.cjk_props(n)
            except Exception as e:
                not_cjk.append((n, "its CJK fixture could not be shaped (%s: %s)"
                                % (type(e).__name__, str(e)[:120])))
                continue
            if not [x for x in _cjk._string_leaves(props) if _cjk._HAS_CJK.search(x)]:
                not_cjk.append((n, "no CJK copy could be shaped for its props — it would be swept in its "
                                   "own English demo defaults under a CJK headline"))
                continue
            cjk_fixture[n] = props
    findings, swept = [], 0
    unfed = {n for n, _ in not_cjk}
    for i, n in enumerate(names, 1):
        if n in unfed:
            continue                                     # named in the report; never swept in the wrong copy
        frame = int(round(rr.frame_at_t(durs[n], rr.SETTLED_T)))
        props = dict(base)
        props.update(cjk_fixture.get(n) or {})
        props.update(evidence.get(n) or {})
        swept += 1
        for v in audit_shot(n, props, frame, tmp):
            findings.append("%s: %s" % (n, _describe(v)))
        if i % 20 == 0:
            print("  swept %d/%d" % (i, len(names)), flush=True)
    return findings, swept, len(names), not_cjk


# ── THE TYPE-GLIDE CENSUS (`--glide`) ────────────────────────────────────────────────────────────────────────
#
# WHAT IT FINDS. Type that MOVES while Skia snaps its baseline to whole pixels (runtime/glide.ts): under an
# axis-aligned matrix a line that crawls by less than a pixel a frame holds still for several frames and then jumps,
# while the rules and pictures beside it glide. A viewer reported it on a delivered film's camera push; every still
# gate passed that film, and shake_qa measured the same numbers before and after the fix — it watches the whole
# frame, and this is one element moving against its own drawing.
#
# HOW. Every frame of the film (or of a register) is rendered with no picture taken (scripts/glide_frames.cjs), and
# on each one the DOM lists every visible line of type whose composed matrix Skia would treat as axis-aligned, with
# its TRUE position (runtime/textSafe.tsx `auditGlide`: client rects are computed from the transform, before paint
# rounds anything). Read in frame order, a line's track says exactly what a viewer sees: while it crawls — moving,
# but by less than a pixel a frame — every whole pixel its true position crosses is one visible step.
#
# THE THRESHOLD IS THE VIEWER'S, not a statistic. Three or more steps inside one crawl is a staircase — hold, jump,
# hold, jump — and an ERROR; one or two is the tick at the end of a slow ease, a WARN that is reported and left for
# the register's next edit. A line moving a pixel or more every frame has no hold to step out of and is not a
# crawl; a line fainter than GLIDE_MIN_OPACITY is not yet being read. Type declared `data-type-steps` (a glitch's
# offset copies, a mechanical counter) is named and excused.
GLIDE_TAG = "TYPE-GLIDE "
GLIDE_STEPS_ERROR = 3          # whole-pixel steps inside one crawl: a staircase
GLIDE_CRAWL_PX = 1.0           # px a frame: at or above this the line moves every frame and never holds
GLIDE_STILL_PX = 1e-3          # px: below this a line did not move between two frames (layout noise)
GLIDE_MIN_OPACITY = 0.25       # fainter than this the line is still arriving, not being read
_GLIDE_RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glide_frames.cjs")


def glide_concurrency():
    return int(os.environ.get("GLIDE_CONCURRENCY") or max(1, min(6, (os.cpu_count() or 4) // 2)))


def glide_bundle(dest, public_dir=None, env=None):
    """Bundle the remotion project once for a census, with a film's workshop when `env` carries one."""
    import workshop as _ws
    cmd = ["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + dest, "--log=error"]
    if public_dir:
        cmd.append("--public-dir=" + os.path.abspath(public_dir))
    r = subprocess.run(cmd, cwd=_REMOTION, capture_output=True, text=True, **_ws.env_kwargs(env))
    if r.returncode != 0 or not os.path.isfile(os.path.join(dest, "index.html")):
        raise RuntimeError("the census bundle failed: %s" % ((r.stdout or "") + (r.stderr or ""))[-600:])
    return dest


def glide_run(jobs, bundle_dir, concurrency=None):
    """Render every job's frames with the census armed. Returns {tag: {"frames": {f: record}, "done": dict | None,
    "error": str | None}} — a job with no `done` line was not measured, whatever its frames say."""
    import tempfile
    import remotion_segments as _rs
    work = tempfile.mkdtemp(prefix="glide_run_")
    try:
        jobs_path, out_path = os.path.join(work, "jobs.json"), os.path.join(work, "out.jsonl")
        with open(jobs_path, "w", encoding="utf-8") as fh:
            json.dump(jobs, fh, ensure_ascii=False, allow_nan=False)
        cmd = ["node", _GLIDE_RUNNER, _REMOTION, bundle_dir, jobs_path, out_path, "--gl=" + _rs.default_gl(),
               "--concurrency=%d" % (concurrency or glide_concurrency())]
        r = subprocess.run(cmd, capture_output=True, text=True)
        res = {j["tag"]: {"frames": {}, "done": None, "error": None} for j in jobs}
        if os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as fh:
                for raw in fh:
                    rec = json.loads(raw)
                    slot = res.setdefault(rec.get("tag"), {"frames": {}, "done": None, "error": None})
                    if rec.get("done"):
                        slot["done"] = rec
                    elif "error" in rec:
                        slot["error"] = rec["error"]
                    elif "f" in rec:
                        slot["frames"][int(rec["f"])] = rec
        if r.returncode != 0:
            why = ((r.stderr or "") + (r.stdout or "")).strip().splitlines()
            for slot in res.values():
                if slot["done"] is None and not slot["error"]:
                    slot["error"] = "the census runner died: %s" % (why[-1] if why else "exit %d" % r.returncode)
        return res
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def judge_glide(frames):
    """Every crawl with at least one whole-pixel step, worst first: {"k", "t", "a", "b", "steps", "max_dy", "fl"}.

    `a`..`b` are the frames of the crawl's first and last STEP — where a viewer sees it — not of the run: a run
    begins wherever the line last moved a pixel or more, which is often long before it starts to step.

    `frames` is {frame: census record}. A track is one element (its DOM path) across frames; a crawl is a run of
    consecutive frames in which the line stays readable, stays axis-aligned (it is listed at all) and moves by less
    than GLIDE_CRAWL_PX each frame. A frame it is missing from — unlocked, hidden, unmounted — ends the run."""
    import math
    tracks = {}
    for f in sorted(frames):
        for ln in frames[f].get("lines") or []:
            tracks.setdefault(ln["k"], []).append((f, float(ln["y"]), float(ln.get("o", 1)), ln.get("t", ""),
                                                   ln.get("fl", "")))
    runs = []
    for key, pts in tracks.items():
        cur = None
        for (f0, y0, o0, _t0, fl0), (f1, y1, o1, t1, fl1) in zip(pts, pts[1:]):
            dy = y1 - y0
            if (f1 != f0 + 1 or o0 < GLIDE_MIN_OPACITY or o1 < GLIDE_MIN_OPACITY
                    or abs(dy) >= GLIDE_CRAWL_PX):
                if cur and cur["steps"] and cur["moved"]:
                    runs.append(cur)
                cur = None
                continue
            if cur is None:
                cur = {"k": key, "t": t1, "a": None, "b": None, "steps": 0, "max_dy": 0.0, "fl": "", "moved": False}
            if abs(dy) > GLIDE_STILL_PX:
                cur["moved"] = True
                cur["max_dy"] = max(cur["max_dy"], abs(dy))
                if math.floor(y1) != math.floor(y0):
                    cur["steps"] += 1
                    cur["a"] = f1 if cur["a"] is None else cur["a"]
                    cur["b"] = f1
            cur["fl"] = "".join(sorted(set(cur["fl"]) | set(fl0) | set(fl1)))
        if cur and cur["steps"] and cur["moved"]:
            runs.append(cur)
    for r in runs:
        r.pop("moved", None)
    return sorted(runs, key=lambda r: (-r["steps"], r["a"]))


def glide_level(runs):
    """('error' | 'warn' | 'clean', the runs that set it). Declared-stepped type never sets the level."""
    real = [r for r in runs if "s" not in r["fl"]]
    worst = max((r["steps"] for r in real), default=0)
    if worst >= GLIDE_STEPS_ERROR:
        return "error", [r for r in real if r["steps"] >= GLIDE_STEPS_ERROR]
    if worst:
        return "warn", real
    return "clean", []


def _describe_run(r):
    flags = []
    if "f" in r["fl"]:
        # the one case whose fix is not "add the unlock": a blur or drop-shadow keeps only the scale of the matrix
        # above it, so an unlock above the filter never reaches these glyphs (runtime/textSafe.tsx SPATIAL_FILTER)
        flags.append("inside a blur/drop-shadow filter — the unlock must sit INSIDE the filtered element")
    if "s" in r["fl"]:
        flags.append("declared data-type-steps")
    return ("%r steps %d whole pixel%s across frames %d-%d, crawling at most %.2fpx/frame under an axis-aligned "
            "matrix%s" % (r["t"], r["steps"], "" if r["steps"] == 1 else "s", r["a"], r["b"], r["max_dy"],
                          (" (" + ", ".join(flags) + ")") if flags else ""))


def _composited(frames):
    """The most lines any one frame drew on a 3D or will-change layer — type the census cannot read (it is
    rasterised once and moved by the compositor), so it is named as unread rather than counted as clean."""
    return max((int(rec.get("z") or 0) for rec in frames.values()), default=0)


def _glide_measured(slot, want_frames):
    """None when the job measured every frame it rendered; else why not — a census that silently lost frames must
    not read as clean."""
    if slot.get("error"):
        return "render FAILED: %s" % slot["error"][:200]
    if not slot.get("done"):
        return "the census never finished"
    logged = slot["done"].get("logged", 0)
    if logged < want_frames:
        return "only %d of %d frames logged a census" % (logged, want_frames)
    return None


def scan_film_glide(out_dir, concurrency=None):
    """(errors, warns, excused, notes, checked, universe, unmeasured, seconds) for one film: every frame of the Film
    composition exactly as render_remotion renders it — its seams, its cameras and its whole-film drift included,
    which a beat rendered on its own would never show."""
    import shutil
    import tempfile
    import time
    import remotion_segments as _rs
    import workshop as _ws
    t0 = time.time()
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    props, slides = rr.film_props(out_dir, board)
    props = dict(props, typeGlide=True)
    segs, total = _rs.timeline(props["scenes"], _rs.seam_frames())
    env = _ws.prepare(out_dir)
    work = tempfile.mkdtemp(prefix="glide_film_")
    try:
        public = _rs.minimal_public(props, out_dir, os.path.join(work, "public"))
        bundle = glide_bundle(os.path.join(work, "bundle"), public, env)
        res = glide_run([{"tag": "film", "id": "Film", "props": props}], bundle, concurrency)["film"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    why = _glide_measured(res, total)
    labels = [s.get("index", i + 1) for i, s in enumerate(slides)]
    shots = [s.get("shot") or "?" for s in slides]

    def beat_of(frame):
        for k, (a, b) in enumerate(segs):
            if a <= frame <= b:
                return k
        return len(segs) - 1

    by_beat = {}
    for run in judge_glide(res["frames"]):
        by_beat.setdefault(beat_of(run["a"]), []).append(run)
    errors, warns, excused = [], [], []
    for k in sorted(by_beat):
        level, worst = glide_level(by_beat[k])
        head = "scene %02d (%s)" % (labels[k], shots[k])
        for r in by_beat[k]:
            if "s" in r["fl"]:
                excused.append("%s: %s" % (head, _describe_run(r)))
        if level == "error":
            errors.extend("%s: STAIRCASE — %s" % (head, _describe_run(r)) for r in worst)
        elif level == "warn":
            warns.extend("%s: %s" % (head, _describe_run(r)) for r in worst)
    return {"errors": errors, "warns": warns, "excused": excused, "frames": total,
            "logged": len(res["frames"]), "unmeasured": [why] if why else [], "beats": len(slides),
            "composited": _composited(res["frames"]), "seconds": time.time() - t0}


def scan_library_glide(names, aspect=None, dna=DEFAULT_DNA, concurrency=None):
    """{name: {"level", "runs", "unmeasured"}} for every register in `names`, each rendered on its own across its
    whole DURATION with its own demo props (and the evidence fixture the other sweeps use)."""
    import shutil
    import tempfile
    import workshop as _ws
    durs = durations()
    base = {"typeGlide": True}
    if aspect:
        base["aspect"] = aspect
    if dna:
        base["dna"] = dna
    try:
        import register_energy as _re
        _re.ensure_fixture()
        evidence = _re.evidence_props()
    except Exception:
        evidence = {}
    work = tempfile.mkdtemp(prefix="glide_lib_")
    try:
        bundle = glide_bundle(os.path.join(work, "bundle"), None, _ws.prepare(None))
        jobs = [{"tag": n, "id": n, "props": dict(base, **(evidence.get(n) or {}))} for n in names]
        res = glide_run(jobs, bundle, concurrency)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out = {}
    for n in names:
        slot = res.get(n) or {"frames": {}, "done": None, "error": "no result"}
        runs = judge_glide(slot["frames"])
        level, worst = glide_level(runs)
        out[n] = {"level": level, "runs": worst if level != "clean" else [],
                  "excused": [r for r in runs if "s" in r["fl"]],
                  "unmeasured": _glide_measured(slot, durs.get(n, 0)),
                  "composited": _composited(slot["frames"]),
                  "seconds": (slot.get("done") or {}).get("ms", 0) / 1000.0}
    return out


def main_glide(argv):
    """`--glide` on a film or on the library. Exit 1 = a staircase; 2 = part of the universe went unmeasured."""
    import time
    argv = [a for a in argv if a != "--glide"]
    if "--library" in argv:
        _c.refuse_unknown(argv, valued=("aspect", "dna", "only", "limit", "json"),
                          switches=("library",), usage=_USAGE)
        durs = durations()
        only = _c.argflag_list(argv, "only")
        lim = _c.argflag(argv, "limit")
        names = sorted(only) if only else sorted(durs)[: int(lim) if lim else None]
        unknown = [n for n in names if n not in durs]
        if unknown:
            print("[text_safe] --only names %d register(s) that do not exist: %s" % (len(unknown), ", ".join(unknown)))
            return 2
        dna = _c.argflag(argv, "dna", DEFAULT_DNA)
        if dna in ("", "none"):
            dna = None
        t0 = time.time()
        result = scan_library_glide(names, _c.argflag(argv, "aspect"), dna)
        errors = sorted(n for n, v in result.items() if v["level"] == "error")
        warns = sorted(n for n, v in result.items() if v["level"] == "warn")
        unmeasured = sorted(n for n, v in result.items() if v["unmeasured"])
        for n in errors:
            for r in result[n]["runs"][:3]:
                print("[text_safe] ERROR %s: STAIRCASE — %s" % (n, _describe_run(r)))
        for n in warns:
            r = result[n]["runs"][0]
            print("[text_safe] WARN %s: %s" % (n, _describe_run(r)))
        for n in sorted(result):
            for r in result[n]["excused"][:1]:
                print("[text_safe] excused %s: %s" % (n, _describe_run(r)))
        for n in unmeasured:
            print("[text_safe] NOT MEASURED %s: %s" % (n, result[n]["unmeasured"]))
        for n in sorted(n for n, v in result.items() if v["composited"]):
            print("[text_safe] note %s: up to %d line(s) a frame on a 3D or will-change layer — not read by the "
                  "census" % (n, result[n]["composited"]))
        js = _c.argflag(argv, "json")
        if js:
            with open(js, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=1, sort_keys=True)
        catalogue = len(durs)
        print("[text_safe] glide %s  %d staircase register(s), %d with a tick (warn), %d not measured — %d of %d "
              "registers%s · dna=%s · %.0fs"
              % ("FAIL" if errors else "OK", len(errors), len(warns), len(unmeasured), len(names), catalogue,
                 "" if len(names) == catalogue else " (narrowed)", dna or "none", time.time() - t0))
        return 1 if errors else (2 if unmeasured else 0)
    if len(argv) != 1 or argv[0].startswith("-"):
        print(_USAGE)
        return 2
    import workshop as _ws
    try:
        rep = scan_film_glide(os.path.abspath(argv[0]))
    except _ws.WorkshopError as e:
        for x in e.problems:
            print("[text_safe] PROBLEM: " + x)
        return 2
    for x in rep["errors"]:
        print("[text_safe] ERROR %s" % x)
    for x in rep["warns"]:
        print("[text_safe] WARN %s" % x)
    for x in rep["excused"]:
        print("[text_safe] excused %s" % x)
    for x in rep["unmeasured"]:
        print("[text_safe] NOT MEASURED: %s" % x)
    if rep["composited"]:
        print("[text_safe] note: up to %d line(s) a frame on a 3D or will-change layer — not read by the census"
              % rep["composited"])
    print("[text_safe] glide %s  %d staircase(s), %d tick(s) — %d of %d frames of %d beats · %.0fs"
          % ("FAIL" if rep["errors"] else "OK", len(rep["errors"]), len(rep["warns"]), rep["logged"], rep["frames"],
             rep["beats"], rep["seconds"]))
    return 1 if rep["errors"] else (2 if rep["unmeasured"] else 0)


def dna_presets():
    """The DNA names the renderer actually offers, read from runtime/dna.tsx rather than listed here — a
    list written in this file is a list that goes stale the day a preset is added."""
    src = open(os.path.join(_REMOTION, "src", "runtime", "dna.tsx"), encoding="utf-8").read()
    m = re.search(r"export const DNA_PRESETS[^=]*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        raise RuntimeError("could not read DNA_PRESETS from runtime/dna.tsx — the sweep cannot enumerate "
                           "the faces it is supposed to cover, and guessing the list is how it came to "
                           "sweep exactly one")
    names = re.findall(r"^\s*([A-Za-z0-9_]+)\s*:", m.group(1), re.M)
    if not names:
        raise RuntimeError("DNA_PRESETS parsed to an EMPTY list — see above")
    return names


_USAGE = ("usage: text_safe_qa.py <out_dir> | --library [--only=A,B] [--aspect=16:9 | --all-aspects] "
          "[--dna=NAME | --all-dna] [--cjk] [--limit=N]\n"
          "       text_safe_qa.py <out_dir> --glide | --library --glide [--only=A,B] [--aspect=..] [--dna=..] "
          "[--json=PATH]   (the type-glide census: every frame, no picture)")


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: text_safe_qa.py <out_dir> | --library")
        return 2
    if "--glide" in argv:
        return main_glide(argv)
    if argv[0] == "--library" and "--all-dna" in argv:
        # THE SWEEP SWEPT ONE DNA, AND THE DNA IS WHAT CHOOSES THE FACE. `scan_library`'s own docstring says
        # the Design DNA "sets the type family and therefore every metric this audit measures" — and then
        # the sweep only ever ran `product`, whose display face is a narrow grotesque. Under `editorial`'s
        # serif, VariableTypeMorph's one enormous word was sliced at BOTH edges of a 1:1 frame while the
        # product sweep reported the register clean at all five aspects. A register that passes in one face
        # has been tested in one face. The list is READ from the renderer's own presets, so a ninth DNA is
        # covered the day it is added.
        rest = [a for a in argv if not a.startswith("--dna=") and a != "--all-dna"]
        worst = 0
        for name in dna_presets():
            print("## dna %s" % name, flush=True)
            worst = max(worst, main(rest + ["--dna=" + name]))
        return worst
    if argv[0] == "--library" and "--all-aspects" in argv:
        # THE LIBRARY WAS SWEPT AT TWO OF THE FIVE ASPECTS IT SHIPS. `--aspect` has existed since the
        # portrait work and 1:1, 4:5 and 4:3 had never been passed to it — the square sweep then found 21
        # registers drawing into the caption band, one of them ('DONE!' at 190px) by 81. The list is READ
        # from Root.tsx's ASPECTS rather than written here, so a sixth aspect is covered the day it is added
        # instead of the day someone remembers this file.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _caption_band as _cb
        rest = [a for a in argv if not a.startswith("--aspect=") and a != "--all-aspects"]
        worst = 0
        for asp in _cb.aspect_table():
            print("### aspect %s" % asp, flush=True)
            worst = max(worst, main(rest + ["--aspect=" + asp]))
        return worst
    if argv[0] == "--library":
        # BOTH SPELLINGS, AND NOTHING SILENTLY IGNORED. `--only Zed` (no `=`) matched nothing here and the
        # register name was then read as the out_dir, so the sweep died on `--only/storyboard.json` — honest,
        # but only by accident. In `register_energy` the same typing dropped the filter and swept all 164
        # registers in silence. One reader, one guard, everywhere (scripts/_common.argflag).
        _c.refuse_unknown(argv, valued=("limit", "aspect", "dna", "only"),
                          switches=("library", "all-aspects", "all-dna", "cjk"), usage=_USAGE)
        _lim = _c.argflag(argv, "limit")
        limit = int(_lim) if _lim else None
        aspect = _c.argflag(argv, "aspect")
        dna = _c.argflag(argv, "dna", DEFAULT_DNA)
        only = _c.argflag_list(argv, "only")
        if only:
            _known = set(durations())
            _missing = [n for n in only if n not in _known]
            if _missing:
                print("[text_safe] --only names %d register(s) that do not exist: %s"
                      % (len(_missing), ", ".join(_missing)))
                return 2
        cjk = "--cjk" in argv
        if dna in ("", "none"):
            dna = None
        findings, n, universe, notmeasured = scan_library(limit, aspect, dna, only, cjk)
        # `--only` AND `--limit` NARROW THE UNIVERSE, and "4 of 4 registers" reads as the catalogue. The
        # catalogue's own size is printed beside them so a narrowed run can never be mistaken for a full one.
        catalogue = len(durations())
        why_narrow = "--only" if only else ("--limit=%d" % limit if limit else "narrowed")
        narrowed = ("" if universe == catalogue
                    else " (%s — of %d registers in shots/)" % (why_narrow, catalogue))
        scope = "%d of %d registers%s at %s · dna=%s%s" % (
            n, universe, narrowed, "CJK fixtures" if cjk else "default props", dna or "none",
            " · aspect %s" % aspect if aspect else "")
        what = "register(s) NOT swept"
    else:
        import workshop as _ws
        try:
            findings, n, universe, notmeasured = scan_film(os.path.abspath(argv[0]))
        except _ws.WorkshopError as e:
            for x in e.problems:
                print("[text_safe] PROBLEM: " + x)
            return 2
        scope = "%d of %d beats" % (n, universe)
        what = "beat(s) NOT measured"
        notmeasured = [(x, None) for x in notmeasured]
    for f in findings:
        print("[text_safe] ERROR %s" % f)
    # THE SCOPE LINE IS THE COVERAGE LINE, and the two universes this script covers must never be mistaken
    # for each other: `--library` is the catalogue, an out_dir is one film's beats. Both now carry
    # `measured of universe`, and anything that left the measurement is named under the headline rather
    # than subtracted from it in silence.
    if notmeasured:
        print("[text_safe] %d %s:" % (len(notmeasured), what))
        for item, why in notmeasured:
            print("    %s" % (item if why is None else "%-22s %s" % (item, why)))
    print("[text_safe] %s  %d finding(s) across %s"
          % ("FAIL" if findings else "OK", len(findings), scope))
    # A run that did not measure part of its universe is not the same answer as one that found nothing.
    return 1 if findings else (2 if notmeasured else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
