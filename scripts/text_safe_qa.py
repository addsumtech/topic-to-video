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


def audit_shot(shot, props, frame, tmp_png, public_dir=None, env=None, type_size=False):
    """Render one shot with the audit armed. Returns [] (clean) or the violation list it reported.

    Props travel by FILE, never on the command line: a beat's real copy is routinely CJK, and a multibyte
    character in a --props argument breaks the arg before remotion ever sees it.
    """
    payload = dict(props or {})
    payload["textSafe"] = True
    if type_size:
        payload["typeSize"] = True            # also report type rendered under the size floor (runtime/textSafe.tsx)
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


TITLE_TAG = "TITLE-PROBE "


def title_of(shot, props, frame, tmp_png, public_dir=None, env=None):
    """{text, ax, cy, px, align} for the settled frame's title (runtime/titleProbe.tsx), or None — no text that is not
    a figure, or a render that measured nothing (said by the caller's coverage, never guessed)."""
    import workshop as _ws
    payload = dict(props or {}, titleProbe=True)
    pf = tmp_png + ".title.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
    cmd = ["npx", "remotion", "still", "src/index.ts", shot, tmp_png, "--frame=%d" % frame, "--gl=angle",
           "--log=error", "--props=" + os.path.abspath(pf)]
    if public_dir:
        cmd.append("--public-dir=" + os.path.abspath(public_dir))
    blob = ""
    for _attempt in (1, 2):                              # a flaky browser is retried once, as audit_shot does
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REMOTION, **_ws.env_kwargs(env))
        blob = (r.stdout or "") + (r.stderr or "")
        if TITLE_TAG in blob:
            break
    if os.path.exists(pf):
        os.remove(pf)
    if TITLE_TAG not in blob:
        # a render that never reached the probe measured NOTHING — said as such, never read as "no title here"
        from shot_proof import _stderr_reason
        return {"failed": _stderr_reason(blob, limit=120) or "no output"}
    try:
        found, _end = json.JSONDecoder().raw_decode(blob.split(TITLE_TAG, 1)[1])
    except json.JSONDecodeError:
        return {"failed": "an unparseable payload"}
    return found if isinstance(found, dict) else None


# the floor's two levels, as fractions of the frame's short side — the SAME constants runtime/textSafe.tsx reports
# against (TYPE_WARN_FRAC there decides what is sent; this decides which of it is an error)
TYPE_WARN_FRAC, TYPE_ERROR_FRAC = 0.0275, 0.022


TYPE_DEBT = os.path.join(_REMOTION, "type_debt.json")


def type_debt():
    """{register: {min_px, under_error, under_warn}} — the library's known small type (remotion/type_debt.json)."""
    try:
        return json.load(open(TYPE_DEBT, encoding="utf-8")).get("registers") or {}
    except (OSError, ValueError, AttributeError):
        return {}


# TITLE PLACEMENT. A user's review of the GPS design found nearly every title top-left — a repeated composition no
# gate could see, because each frame alone is fine. `title_of` asks runtime/titleProbe.tsx for each settled frame's
# title — its largest type that is not a figure, placed by the edge its line is set from — and this asks whether one
# ninth of the frame holds most of the film's titles. (It first read "the largest type": on the compound-interest
# test that was the printed figures, while the titles sat top-left on 9 of 11 beats unreported.)
TITLE_ZONE_SHARE = 0.6
TITLE_ZONE_MIN = 4


def _zone(cx, cy):
    col = "left" if cx < 1 / 3 else "right" if cx > 2 / 3 else "centre"
    row = "top" if cy < 1 / 3 else "bottom" if cy > 2 / 3 else "middle"
    return row + "-" + col


TITLE_NEAR_X, TITLE_NEAR_Y = 0.08, 0.12      # "the same place": an anchor within 8% of the width, 12% of the height


def _anchors(t):
    a = [t.get(k) for k in ("lx", "cx", "rx", "ax") if isinstance(t.get(k), (int, float))]
    return a or [0.5]


def _same_place(a, b):
    return abs(a["cy"] - b["cy"]) <= TITLE_NEAR_Y and any(abs(x - y) <= TITLE_NEAR_X
                                                          for x in _anchors(a) for y in _anchors(b))


def title_repetition(titles):
    """A warning when most of a film's beats put their title in the same place, else None.

    "The same place" is a NEIGHBOURHOOD, not a ninth of the frame: fixed thirds split six titles set at x 0.31-0.36
    between "left" and "centre" and reported nothing. Two titles share a place when their heights are close and ANY of
    their left edges, centres or right edges line up — a left-set title keeps its left edge, a centred one its centre,
    whatever its length."""
    if len(titles) < TITLE_ZONE_MIN:
        return None
    best = []
    for _i, _s, t, _x in titles:
        group = [r for r in titles if _same_place(t, r[2])]
        if len(group) > len(best):
            best = group
    n = len(best)
    if n < TITLE_ZONE_MIN or n / float(len(titles)) < TITLE_ZONE_SHARE:
        return None
    t0 = best[0][2]
    where = _zone(sorted(_anchors(t0))[len(_anchors(t0)) // 2] if "ax" not in t0 else t0["ax"], t0["cy"])
    return ("TITLE PLACEMENT — %d of %d beats put their title (their largest type that is not a figure) in the same "
            "place, around the %s of the frame (beats %s): a repeated composition, however different the pictures. "
            "Move the title with each composition (bottom over the ground, a side column, inside the scene) or leave "
            "it out where the picture speaks" % (n, len(titles), where, ", ".join(str(r[0]) for r in best)))


def title_placement(titles, meta):
    """('error' | 'warn', sentence) or None. A repeated title position is an ERROR unless the film declares it as its
    system — `meta.fixed_title_position: "<why this film keeps one title position>"`, e.g. a lower-third every beat
    shares. It was a warning, and the unattended compound-interest run triaged it as "accepted" with the rest."""
    note = title_repetition(titles)
    if not note:
        return None
    why = str((meta or {}).get("fixed_title_position") or "").strip()
    if _c.substance(why) >= 6:
        return "warn", note + " — kept by meta.fixed_title_position: " + why[:120]
    return "error", note + (". If one title position IS this film's system, say why in meta.fixed_title_position")


def write_type_debt(findings, scope):
    """Rewrite remotion/type_debt.json from a `--library --type-size` sweep's findings — the ONE way the record is
    made, so it is a measurement anyone can repeat rather than a list someone kept."""
    reg = {}
    for f in findings:
        m = re.match(r"^(\w+): SMALL TYPE \((error|warn)\) — .*? is set at (\d+(?:\.\d+)?) px", f)
        if not m:
            continue
        r = reg.setdefault(m.group(1), {"min_px": 999.0, "under_error": 0, "under_warn": 0})
        r["min_px"] = round(min(r["min_px"], float(m.group(3))), 1)
        r["under_" + m.group(2)] += 1
    try:
        why = json.load(open(TYPE_DEBT, encoding="utf-8")).get("_why", "")
    except (OSError, ValueError, AttributeError):
        why = ""
    with open(TYPE_DEBT, "w", encoding="utf-8") as fh:
        json.dump({"_why": why, "_measured": "python3 scripts/text_safe_qa.py --library --type-size --write-debt · " + scope,
                   "registers": dict(sorted(reg.items()))}, fh, ensure_ascii=False, indent=1)
    return reg


def type_size_level(v):
    """'error' | 'warn' | None for one reported element: under ~24 px at 1080 a viewer cannot read it on a phone,
    under ~30 px it is a label the user's own review asked to be larger."""
    px, short = v.get("small"), v.get("short")
    if not px or not short:
        return None
    return "error" if px < TYPE_ERROR_FRAC * short else "warn"


def _describe_small(v):
    err = type_size_level(v) == "error"
    return ("%r is set at %.0f px — %s (at this frame: under %d px is an error, under %d px a warning). Cut words "
            "rather than shrink them; texture that is not copy may say so with data-small=\"why\""
            % (v.get("text", ""), v["small"], "too small to read on a phone" if err else "under the label floor",
               round(TYPE_ERROR_FRAC * v["short"]), round(TYPE_WARN_FRAC * v["short"])))


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


def scan_film(out_dir, warnings=None):
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
    findings, checked, skipped, titles, title_failed = [], 0, [], [], []
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
        debt, own = type_debt(), set(_ws.shot_names(out_dir))
        t = title_of(shot, props, frame, tmp, public_dir=out_dir, env=env)
        if t and t.get("failed"):
            title_failed.append("scene %02d (%s): %s" % (i, shot, t["failed"]))
        elif t:
            titles.append((i, shot, t, t.get("text", "")))
        for v in audit_shot(shot, props, frame, tmp, public_dir=out_dir, env=env, type_size=True):
            if v.get("title"):
                continue                                 # the walk's own "largest type" record; title_of decides
            lvl = type_size_level(v)
            if lvl and not v.get("out") and not v.get("band"):
                line = "scene %02d (%s): SMALL TYPE — %s" % (i, shot, _describe_small(v))
                if lvl == "error" and shot not in own:
                    # A LIBRARY register's type size is the library's to fix (remotion/type_debt.json lists what the
                    # default-props sweep found; a register's labels fed by a film — ObjectStage's callouts at 19-22 px
                    # on the mri film — can only show up here). Said loudly, never refused: a film should not be blocked
                    # for a register the catalogue still offers. A film's OWN shot is its author's, and is held to it.
                    known = debt.get(shot, {}).get("min_px")
                    lvl, line = "warn", line + (" — LIBRARY TYPE DEBT: %s sets type down to %s px" % (shot, known)
                                                if known else " — LIBRARY TYPE DEBT not yet listed for %s" % shot) + \
                        "; pick a register that does not, or adapt this one's type"
                if lvl == "error":
                    findings.append(line)
                elif warnings is not None:
                    warnings.append(line)
                continue
            findings.append("scene %02d (%s): %s" % (i, shot, _describe(v)))
    for p in (tmp, tmp + ".props.json"):
        if os.path.exists(p):
            os.remove(p)
    if title_failed and warnings is not None:
        warnings.append("TITLE PLACEMENT read on %d of %d beat(s) — the title probe did not render on: %s"
                        % (checked - len(title_failed), checked, "; ".join(title_failed[:4])))
    verdict = title_placement(titles, meta)
    if verdict and verdict[0] == "error":
        findings.append(verdict[1])
    elif verdict and warnings is not None:
        warnings.append(verdict[1])
    return findings, checked, len(slides), skipped


DEFAULT_DNA = "product"


def scan_library(limit=None, aspect=None, dna=DEFAULT_DNA, only=None, cjk=False, type_size=False):
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
        for v in audit_shot(n, props, frame, tmp, type_size=type_size):
            if v.get("title"):
                continue
            lvl = type_size_level(v)
            if lvl and not v.get("out") and not v.get("band"):
                findings.append("%s: SMALL TYPE (%s) — %s" % (n, lvl, _describe_small(v)))
                continue
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
GLIDE_RESET_PX = 0.5           # px of font size: a jump this large between two frames is the type re-set, not moved
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
        # Run from the remotion project, where the renderer keeps its browser (node_modules/.remotion): from
        # anywhere else it downloads a second copy into the caller's directory. And bounded: a register that
        # throws on every frame must come back as a failure, not hold the census forever.
        budget = 240 + 180 * len(jobs)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REMOTION, timeout=budget)
        except subprocess.TimeoutExpired:
            r = subprocess.CompletedProcess(cmd, 124, "", "the census runner did not finish in %ds" % budget)
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
    consecutive frames in which the line stays readable and moves by less than GLIDE_CRAWL_PX each frame. A frame it
    is missing from — hidden, unmounted — ends the run.

    WHAT IS A STEP depends on what moves the line. Under an axis-aligned matrix Skia rounds the baseline, so every
    whole pixel its true position crosses is one. Under an unlock (`u`) Skia places it to the quarter pixel — but a
    LAYOUT position is rounded to whole pixels by the browser before Skia sees it, so an unlocked line still steps
    each time its layout offset `ly` moves (measured on CameraTypeProbe: 0.284px moved by `top`, unlocked, against
    0.007px moved by a translate). Steps of that kind mark the run `L`: the fix is a transform, not a skew."""
    import math
    tracks = {}
    for f in sorted(frames):
        for ln in frames[f].get("lines") or []:
            if "c" in (ln.get("fl") or ""):
                continue                                  # a composited layer: listed for pixel checks, not judged
            tracks.setdefault(ln["k"], []).append((f, float(ln["y"]), float(ln.get("o", 1)), ln.get("t", ""),
                                                   ln.get("fl", ""), bool(ln.get("u")), ln.get("ly"),
                                                   ln.get("px")))
    # RE-SET between two frames: a line whose font size jumped (a whole-px size picked off a moving box). It moves
    # where it is drawn, and it moves every line laid out after it in the same parent — a re-flow, not a crawl.
    sized = {f: {ln["k"]: ln.get("px") for ln in (frames[f].get("lines") or [])} for f in frames}
    def _resets(f0, f1):
        a, b = sized.get(f0, {}), sized.get(f1, {})
        return {k for k in b if a.get(k) and b[k] and abs(float(b[k]) - float(a[k])) >= GLIDE_RESET_PX}
    runs = []
    for key, pts in tracks.items():
        parent = key.rsplit("/", 1)[0]
        cur = None
        for (f0, y0, o0, _t0, fl0, u0, ly0, px0), (f1, y1, o1, t1, fl1, u1, ly1, px1) in zip(pts, pts[1:]):
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
                # a ROUNDING step moves the layout offset by about as much as the line moved; a jump far larger than
                # the move is the line being RE-SEATED (its place moved from left/top into a transform, as QuadSplit's
                # hero does when its expand begins: offset 404 -> 0 while the line moved 0.013px) — not a step
                laid = (ly0 is not None and ly1 is not None and ly0 != ly1
                        and abs(ly1 - ly0) <= abs(dy) + 1)
                if any(k == key or k.rsplit("/", 1)[0] == parent for k in _resets(f0, f1)):
                    # RE-SET, not stepped: this line's font size jumped between the frames, or a sibling's did and
                    # re-flowed it. InOrder's label going 26 -> 27px moved its own top 0.36px; ViewSwitch's label
                    # refitted a px larger pushed its note 0.6px. A size LERPED a little each frame stays judged:
                    # below the threshold the line is still one size crawling.
                    step, why = False, ""
                elif u0 and u1:
                    step, why = laid, "L"                 # unlocked, but the layout offset moved a whole pixel
                elif not u0 and not u1:
                    step, why = math.floor(y1) != math.floor(y0), "L" if laid else ""
                else:
                    # a SPAN EDGE: the unlock switching on or off between these two frames. What changes is how the
                    # line is rounded, not a crawl step — at most the sub-pixel settle every span edge has — and a
                    # crawl that goes on after it is counted frame by frame on the other side.
                    step, why = False, ""
                if step:
                    cur["steps"] += 1
                    cur["a"] = f1 if cur["a"] is None else cur["a"]
                    cur["b"] = f1
                    if why and "L" not in cur["fl"]:
                        cur["fl"] += "L"
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
    if "L" in r["fl"]:
        # a layout offset is rounded to whole pixels before Skia draws anything, so no skew can reach it
        flags.append("moved by LAYOUT (top/left/margin) — move the position into a transform and glide() that")
    if "f" in r["fl"]:
        # the one case whose fix is not "add the unlock": a blur or drop-shadow keeps only the scale of the matrix
        # above it, so an unlock above the filter never reaches these glyphs (runtime/textSafe.tsx SPATIAL_FILTER)
        flags.append("inside a blur/drop-shadow filter — the unlock must sit INSIDE the filtered element")
    if "s" in r["fl"]:
        flags.append("declared data-type-steps")
    return ("%r steps %d whole pixel%s across frames %d-%d, crawling at most %.2fpx/frame%s"
            % (r["t"], r["steps"], "" if r["steps"] == 1 else "s", r["a"], r["b"], r["max_dy"],
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


# ── THE SYNC AUDIT (`--sync`) ────────────────────────────────────────────────────────────────────────────────
#
# Does each piece of on-screen text appear when the narration says it? The same census as `--glide` — every frame
# of the Film, no picture — read for a different question: per beat, when each line of type first becomes
# readable, against when the voice first says it (scripts/sync_qa.py holds the matching and the thresholds, which
# the html tier's keyframe_qa shares). ERROR past sync_qa.LAG_ERROR late, WARN past LAG_WARN; more than
# EARLY_WARN early is a spoiler WARN. The film is measured AS IT RENDERS — with the time warp render_remotion
# derives (Film.tsx `BeatClock`) — so a re-render's numbers are the after, and `raw=True` gives the before.
def film_census(out_dir, props, concurrency=None):
    """(census slot, segs, total, slides-in-order) for the Film with `props` — one bundle, one census run."""
    import shutil
    import tempfile
    import remotion_segments as _rs
    import workshop as _ws
    props = dict(props, typeGlide=True)
    segs, total = _rs.timeline(props["scenes"], _rs.seam_frames())
    env = _ws.prepare(out_dir)
    work = tempfile.mkdtemp(prefix="sync_film_")
    try:
        public = _rs.minimal_public(props, out_dir, os.path.join(work, "public"))
        bundle = glide_bundle(os.path.join(work, "bundle"), public, env)
        res = glide_run([{"tag": "film", "id": "Film", "props": props}], bundle, concurrency)["film"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return res, segs, total


def beat_samples(frames, segs, fps):
    """{beat k: [(t on the beat's own clock, [lines of beat k]), ...]} from Film census frames. A line belongs
    to the beat whose register it is in (`b`, Film.tsx data-beat); the caption and the chrome carry none."""
    starts = [a for a, _b in segs]
    out = {k: [] for k in range(len(segs))}
    for f in sorted(frames):
        by = {}
        for ln in frames[f].get("lines") or []:
            b = ln.get("b")
            if b is None:
                continue
            by.setdefault(int(b), []).append(ln)
        for k, lines in by.items():
            if 0 <= k < len(starts):
                out[k].append(((f - starts[k]) / float(fps), lines))
    return out


def scan_film_sync(out_dir, raw=False, concurrency=None, props=None, census_out=None, census_in=None, slides=None):
    """{"beats": {label: [records]}, "summary", "unmeasured", "seconds", "frames", "logged"} for one film.
    `raw` strips any time warp from the beats, measuring the registers on their own clocks. `census_out` keeps
    the census it rendered (gzip json); `census_in` judges a kept one instead of rendering — the judgment can
    then be re-run, and tested, without a browser."""
    import time
    import sync_qa as _sq
    t0 = time.time()
    if props is None or slides is None:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
        if props is None:
            props, slides = rr.film_props(out_dir, board)
        else:
            slides = board.get("slides", [])
    if raw:
        props = dict(props, scenes=[{k: v for k, v in sc.items() if k != "warp"} for sc in props["scenes"]])
    fps = 30
    if census_in:
        import gzip
        import remotion_segments as _rs
        with gzip.open(census_in, "rt", encoding="utf-8") as fh:
            kept = json.load(fh)
        res = {"frames": {int(f): v for f, v in kept["frames"].items()}, "done": kept.get("done"),
               "error": kept.get("error")}
        segs, total = _rs.timeline(props["scenes"], _rs.seam_frames())
    else:
        res, segs, total = film_census(out_dir, props, concurrency)
    if census_out:
        import gzip
        with gzip.open(census_out, "wt", encoding="utf-8") as fh:
            json.dump({"frames": res["frames"], "done": res.get("done"), "error": res.get("error")}, fh,
                      ensure_ascii=False)
    why = _glide_measured(res, total)
    samples = beat_samples(res["frames"], segs, fps)
    beats, sources, by_k, warped = {}, {}, [], {}
    for k, s in enumerate(slides):
        label = "scene %02d (%s)" % (s.get("index", k + 1), s.get("shot") or "?")
        spoken, src = _sq.spoken_units(_sq.narration_of(s), _sq.words_for(out_dir, s), s.get("duration"))
        sources[label] = src
        beats[label] = _sq.measure_beat(samples.get(k, []), spoken) if spoken else []
        by_k.append(beats[label])
        warped[label] = bool((props["scenes"][k] or {}).get("warp"))
    return {"beats": beats, "by_k": by_k, "summary": _sq.summarize(beats), "sources": sources,
            "unmeasured": [why] if why else [], "seconds": time.time() - t0, "frames": total,
            "logged": len(res["frames"]), "warped": warped}


def main_sync(argv):
    """`<out_dir> --sync [--raw] [--json=PATH]`. Exit 1 = an element ERROR-late; 2 = not measured."""
    import sync_qa as _sq
    argv = [a for a in argv if a != "--sync"]
    _c.refuse_unknown(argv, valued=("json", "census", "from-census"), switches=("raw",), usage=_USAGE)
    raw = "--raw" in argv
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) != 1:
        print(_USAGE)
        return 2
    import workshop as _ws
    try:
        rep = scan_film_sync(os.path.abspath(pos[0]), raw=raw, census_out=_c.argflag(argv, "census"),
                             census_in=_c.argflag(argv, "from-census"))
    except _ws.WorkshopError as e:
        for x in e.problems:
            print("[text_safe] PROBLEM: " + x)
        return 2
    except (RuntimeError, OSError, ValueError) as e:
        print("[text_safe] sync NOT MEASURED — the film could not be rendered for the census: %s" % e)
        return 2
    errors = warns = 0
    for label, recs in rep["beats"].items():
        for r in recs:
            lv = _sq.level(r)
            if lv == "error":
                errors += 1
                print("[text_safe] ERROR %s: LATE — %s" % (label, _sq.describe(r)))
            elif lv == "warn":
                warns += 1
                print("[text_safe] WARN %s: late — %s" % (label, _sq.describe(r)))
            elif lv == "early":
                warns += 1
                print("[text_safe] WARN %s: EARLY (gives the line away) — %s" % (label, _sq.describe(r)))
        if rep["sources"].get(label) == "text":
            print("[text_safe] note %s: no word times — spoken times estimated from the narration text" % label)
    for x in rep["unmeasured"]:
        print("[text_safe] NOT MEASURED: %s" % x)
    js = _c.argflag(argv, "json")
    if js:
        with open(js, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=1)
    sm = rep["summary"]
    if errors:
        print("[text_safe] FIX: re-render — render_remotion derives each beat's time warp from this census "
              "(scripts/sync_qa.py derive_warp) so a register's entrance lands on its word; when the warp cannot "
              "reach (slope limit) or the narration names items in another order than the frame shows them (a warp "
              "cannot reorder), time each item through `cue.win` (runtime/cue.ts — the render then cues it on its "
              "word), time the register by a `{\"cue\": ...}` prop, give the beat explicit `sync.anchors`, or move "
              "the text to the sentence that names it")
    print("[text_safe] sync %s  %d late ERROR(s) (>%.1fs), %d WARN(s) — %d text element(s) matched to the voice "
          "· worst lag %+.2fs · mean |lag| %.2fs · %d of %d frames%s · %.0fs"
          % ("FAIL" if errors else "OK", errors, _sq.LAG_ERROR, warns, sm["elements"], sm["worst_lag"],
             sm["mean_abs_lag"], rep["logged"], rep["frames"], " · RAW (no warp)" if raw else "",
             rep["seconds"]))
    return 1 if errors else (2 if rep["unmeasured"] else 0)


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
    except (RuntimeError, OSError, ValueError) as e:
        # a board this tree cannot render (a shot it does not have, a missing file) measured NOTHING — said so,
        # never read as a clean census
        print("[text_safe] glide NOT MEASURED — the film could not be rendered for the census: %s" % e)
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
          "[--json=PATH]   (the type-glide census: every frame, no picture)\n"
          "       text_safe_qa.py <out_dir> --sync [--raw] [--json=PATH] [--census=PATH | --from-census=PATH]   (does each text element appear when "
          "the narration says it? same census)")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip() if argv else __doc__.strip().splitlines()[0])
        print(_USAGE if argv else "usage: text_safe_qa.py <out_dir> | --library")
        return 0 if argv else 2
    if "--sync" in argv:
        return main_sync(argv)
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
                          switches=("library", "all-aspects", "all-dna", "cjk", "type-size", "write-debt"),
                          usage=_USAGE)
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
        findings, n, universe, notmeasured = scan_library(limit, aspect, dna, only, cjk, type_size="--type-size" in argv)
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
        if "--write-debt" in argv:
            if not ("--type-size" in argv and universe == catalogue and not cjk and not aspect):
                print("[text_safe] --write-debt needs the WHOLE library, at default props and aspect, with --type-size")
                return 2
            print("[text_safe] wrote %s: %d register(s) with type under the floor"
                  % (os.path.relpath(TYPE_DEBT, _ROOT), len(write_type_debt(findings, scope))))
    else:
        import workshop as _ws
        film_warnings = []
        try:
            findings, n, universe, notmeasured = scan_film(os.path.abspath(argv[0]), warnings=film_warnings)
        except _ws.WorkshopError as e:
            for x in e.problems:
                print("[text_safe] PROBLEM: " + x)
            return 2
        scope = "%d of %d beats" % (n, universe)
        what = "beat(s) NOT measured"
        notmeasured = [(x, None) for x in notmeasured]
        for w in film_warnings:
            print("[text_safe] WARN %s" % w)
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
