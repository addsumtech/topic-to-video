#!/usr/bin/env python3
"""energy_skeleton — does the film's VISUAL energy follow the energy its plan wrote? (pre-render, no render)

    python3 scripts/energy_skeleton.py <out_dir>            # the curve, the findings, the alternatives
    python3 scripts/energy_skeleton.py <out_dir> --json

WHY THIS EXISTS. The content-planner writes an energy skeleton for every film — each beat carries `energy`
(low / medium / high / peak) and the plan carries a `rhythm` line like "第7拍重重落下 → 第23拍高潮拉长 → 末拍稀疏".
The shot-director then chooses a register per beat by intent and family variety, and nothing in between ever
reads the skeleton. Measured on a delivered 30-beat film, using the library's own per-register motion sweep:

    beat  4  CinematicTitle   declared HIGH   motion 0.0004   (the library's quietest fifth)
    beat 17  GrantedTree      declared HIGH   motion 0.0003
    beat 23  DataMonolith     declared PEAK   motion 0.0034   (UNDER the delivery motion floor, 0.0037)
    beat 24  StrataColumn     declared HIGH   motion 0.0006
    beat 25  TermTable        declared HIGH   motion 0.0002
    beat  9  MetaballMerge    declared MEDIUM motion 0.0068   (the film's most kinetic register)

The plan's climax was one of the film's stillest beats and its visual summit sat on a medium beat nine
minutes earlier. Nobody chose that; the register picker simply could not see energy. This is the gap a
mature peer library closes with a rule its authors call "fill the skeleton first, then pick the cards":
allocate the film's energy per slot BEFORE choosing a shot for the slot, alternate kinetic and steady beats
("连续高能量读作嘈杂" — consecutive high energy reads as noise), and never omit the two ends — the open
holds, the close lands.

WHAT THIS MEASURES, AND WHAT IT CANNOT. A register's motion here is `motion_p75` from the library sweep
(`register_energy.py`): the p75 frame difference of the register rendered with its evidence props on one
DNA. A beat's real motion also depends on its props, its ground, its camera and its length, so a finding
is a CANDIDATE with a named cause, not a work order. The bands are the library's own terciles — "quiet" is
the stillest third of what the director could have picked, "kinetic" the liveliest third — so the check
asks only whether a high beat was handed one of the still registers when livelier ones existed. `medium`
never mismatches. And a stale sweep produces no findings at all, with a reason: a finding built on a
measurement of a different library is worse than none.

THE RULES (each one a line in `findings()`, each with its case):

  high-on-quiet     a HIGH or PEAK beat on a register in the quiet third            (beats 4/17/24/25 above)
  peak-under-floor  the PEAK beat on a register under the delivery motion floor     (beat 23 above)
  low-on-kinetic    a LOW beat (the sparse hold, the close) on a kinetic register   (the close that fidgets)
  run-of-kinetic    three or more kinetic registers in a row                        (the peer's noise case)
  summit-off-peak   the film's most kinetic register is not on its peak beat        (beat 9 above)

THE OTHER UNIVERSE. This gate reads TWO sets and can be blind in either: the film's beats, and the manifest
rows behind them. A beat whose register has no row — or whose row `stale()` drops because the shot's source
changed since it was measured — used to fall out of `findings()` on a bare `continue`, and it took the
`run-of-kinetic` and `summit-off-peak` scans with it (an unmeasured beat BREAKS a kinetic run, so four
kinetic beats with one unmeasured among them produce no finding at all). Both now surface as an `unmeasured`
finding that names the beat and WHICH of the two it is, because the fixes differ: a missing row wants the
shot-director or a sweep that includes the new register, a stale row wants `register_energy.py` re-run. The
headline states `measured N of M`, and the "follows the plan's skeleton" verdict is printed only when
N == M — it is a claim about every beat, and it used to be printed over beats nobody had looked at.

Deterministic; reads the storyboard and the sweep, writes nothing. `validate.py` reports the same findings
as warnings; `shot_director.py` uses `band_for()` to prefer an in-band register on the deterministic path.
"""
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _common as _c                                                # noqa: E402

ENERGIES = ("low", "medium", "high", "peak")
HARD = ("high-on-quiet", "peak-under-floor", "low-on-kinetic")   # the mismatches that set the exit code
RUN = 3                    # kinetic beats in a row that read as noise
SUMMIT_RATIO = 1.5         # another beat this much more kinetic than the peak beat = the summit is elsewhere
SPARK = " ▁▂▃▄▅▆▇█"


def load_sweep():
    """({register: motion_p75}, floor, quiet_cut, kinetic_cut, why_none) — see `sweep_status`."""
    return sweep_status()[:5]


def sweep_status():
    """(motion, floor, quiet_cut, kinetic_cut, why_none, stale_rows).

    `stale_rows` is {register: why} for the rows this call DROPPED — kept out of `motion` so nothing is
    judged against a measurement of different source, and returned so the caller can tell a beat whose
    register was never measured from one whose measurement went out of date. Reporting both as "not
    measured" sends the reader to the shot-director when the fix is `python3 scripts/register_energy.py`.
    """
    try:
        import register_energy as reg
        data = json.load(open(reg.MANIFEST, encoding="utf-8"))
        # `stale()` names the rows that no longer describe their source. One new or edited register must not
        # switch the whole check off, so only THOSE rows are dropped (a beat on one is reported as unmeasured);
        # past a quarter of the library the sweep no longer describes the library, and there is no basis.
        stale_rows = dict(reg.stale(data))
        rows = data["registers"]
        if len(stale_rows) > max(3, len(rows) // 4):
            return None, None, None, None, ("the register sweep is STALE for %d registers — run "
                                            "`python3 scripts/register_energy.py`" % len(stale_rows)), stale_rows
        motion = {n: float(r["motion_p75"]) for n, r in rows.items() if "motion_p75" in r and n not in stale_rows}
        floor = float(data["_floors"]["motion_p75"])
    except Exception as e:                                          # noqa: BLE001 — any failure = no basis
        return None, None, None, None, "no usable register sweep (%s)" % e, {}
    if len(motion) < 6:
        return (None, None, None, None,
                "the register sweep holds %d registers — too few for bands" % len(motion), stale_rows)
    vals = sorted(motion.values())
    q = lambda p: vals[int(round(p * (len(vals) - 1)))]           # noqa: E731
    return motion, floor, q(1 / 3.0), q(2 / 3.0), None, stale_rows


def band_for(energy, quiet_cut, kinetic_cut, floor):
    """(lo, hi) motion bounds a register should sit in for a declared energy. `medium` is unconstrained."""
    e = (energy or "medium").lower()
    if e == "low":
        return (0.0, kinetic_cut)
    if e == "high":
        return (quiet_cut, float("inf"))
    if e == "peak":
        return (max(quiet_cut, floor), float("inf"))
    return (0.0, float("inf"))


def declared(slide, beat=None):
    """The beat's declared energy: the storyboard's own field, else the plan's; a climax is a peak; a close
    with nothing declared is the sparse hold (low); everything else medium."""
    for src in (slide, beat or {}):
        e = str(src.get("energy") or "").lower()
        if e in ENERGIES:
            return e
    if (beat or {}).get("climax") or slide.get("climax"):
        return "peak"
    if (slide.get("relation") or (beat or {}).get("relation")) == "close":
        return "low"
    return "medium"


def _normalise(slides):
    """([slide dicts], {position: why}) — a board entry that is not an object cannot be read, and used to
    reach `s.get` as an AttributeError traceback that named a Python type and no beat. It becomes an empty
    beat here and an `unmeasured` finding with its position, so a malformed board is a named hole."""
    out, bad = [], {}
    for i, s in enumerate(slides):
        if isinstance(s, dict):
            out.append(s)
        else:
            bad[i] = ("storyboard entry is a %s, not a beat object — the board is malformed here and "
                      "nothing about this beat can be read" % type(s).__name__)
            out.append({})
    return out, bad


def _beats_by_position(plan, slides):
    """content_plan beats matched to slides the way shot_director does: by id, then id = index + 1, then position."""
    beats = (plan or {}).get("beats") or []
    by_id = {b.get("id"): b for b in beats if b.get("id") is not None}
    idx = [s.get("index") for s in slides]
    if by_id and set(by_id) == set(idx):
        return [by_id.get(i, {}) for i in idx]
    if by_id and set(by_id) == {i + 1 for i in idx if i is not None}:
        return [by_id.get((i or 0) + 1, {}) for i in idx]
    return [beats[p] if p < len(beats) else {} for p in range(len(slides))]


def _alternatives(slide, beat, lo, hi, motion, used, families, k=3):
    """Up to k registers the beat could take instead: from its intent's candidate pool (or the climax / close
    list), inside the band, not already in the film, and from a family unlike the beat's neighbours."""
    try:
        import shot_director as sd
    except Exception:                                               # noqa: BLE001
        return []
    intent = (beat or {}).get("visual_intent") or slide.get("visual_intent")
    if declared(slide, beat) == "peak":
        pool = list(sd.CLIMAX)
    elif (slide.get("relation") or (beat or {}).get("relation")) == "close":
        pool = list(sd.CLOSE)
    else:
        pool = list(sd.CANDIDATES.get(intent, [])) or list(motion)
    out = [c for c in pool if c in motion and lo <= motion[c] < hi and c not in used
           and sd.FAMILY.get(c) not in families]
    if not out:                                                     # the pool has nothing in band: widen
        out = [c for c in sorted(motion, key=lambda n: motion[n]) if lo <= motion[c] < hi and c not in used
               and sd.FAMILY.get(c) not in families]
    return out[:k]


def unmeasured_reason(shot, stale_rows, film_shots=()):
    """Why this beat carries no motion number, in words whose FIX differs — the whole point of separating
    them. `None` when there is nothing to say (the beat is measured).

    A FILM'S OWN WORKSHOP SHOT has no row by design: register_energy.py is a LIBRARY sweep and never sees a
    workshop, so telling the author to run it is telling them to run something that cannot help. The beat is
    still unmeasured here — its motion is read on the render instead."""
    if not shot:
        return "no register assigned yet — run the shot-director, then re-run this"
    if shot in (film_shots or ()):
        return ("%s is this film's own workshop shot and has not been measured yet — "
                "`python3 scripts/energy_skeleton.py <out_dir>` renders the film's own shots with their props and "
                "measures them (cached in .energy_own.json)" % shot)
    if shot in (stale_rows or {}):
        return ("%s's row in the sweep is STALE (%s), so it was dropped rather than trusted — run "
                "`python3 scripts/register_energy.py`" % (shot, stale_rows[shot]))
    return ("%s has no row in the sweep, so its motion is unknown rather than fine — if it is a new "
            "register, run `python3 scripts/register_energy.py`" % shot)


def findings(slides, motion, floor, quiet_cut, kinetic_cut, plan=None, stale_rows=None, malformed=None,
             film_shots=(), beat_motion=None):
    """The list of dicts described in the module docstring. Empty when the film follows its skeleton.

    A beat with no motion number is emitted as kind `unmeasured` rather than skipped: it is the one thing
    this check could not do, and it silently weakened two of the five rules as well as its own line.
    """
    try:
        import shot_director as sd
        fam = sd.FAMILY
    except Exception:                                               # noqa: BLE001
        fam = {}
    malformed = malformed or {}
    beats = _beats_by_position(plan, slides)
    used = {s.get("shot") for s in slides}
    rows = []
    for i, s in enumerate(slides):
        shot = s.get("shot")
        # a film's own shot is measured per BEAT (its props change the picture), the library's per register
        m = (beat_motion or {}).get(i + 1, motion.get(shot))
        rows.append({"beat": i + 1, "shot": shot, "energy": declared(s, beats[i]), "motion": m})
    out = []
    for i, r in enumerate(rows):
        if r["motion"] is None:
            out.append(dict(r, kind="unmeasured", alternatives=[],
                            why=malformed.get(i) or unmeasured_reason(r["shot"], stale_rows, film_shots)))
            continue
        e, m = r["energy"], r["motion"]
        kind = None
        if e in ("high", "peak") and m < quiet_cut:
            kind = "high-on-quiet"
        if e == "peak" and m < floor:
            kind = "peak-under-floor"                                # the stronger claim wins the line
        if e == "low" and m >= kinetic_cut:
            kind = "low-on-kinetic"
        if r["shot"] in (film_shots or ()):
            # A BUILT SHOT IS NEVER TOLD TO BECOME A TEMPLATE. Its fix is in its own source, so a mismatch is said about
            # the shot, advisory (the render's film_energy_qa separates "under the floor" from "frozen"), with no
            # library swap — a built PEAK beat used to get `peak-under-floor` (HARD) and three registers to replace it.
            if e != "low" and m < floor:
                out.append(dict(r, kind="own-under-floor", floor=floor, alternatives=[]))
            elif kind:
                out.append(dict(r, kind="own-off-energy", mismatch=kind, alternatives=[]))
            continue
        if kind:
            lo, hi = band_for(e, quiet_cut, kinetic_cut, floor)
            near = {fam.get(rows[j]["shot"]) for j in (i - 1, i + 1) if 0 <= j < len(rows)}
            out.append(dict(r, kind=kind, band=(lo, hi if hi != float("inf") else None),
                            alternatives=_alternatives(slides[i], beats[i], lo, hi, motion, used, near)))
    # a run of kinetic registers reads as noise whatever each beat declared.
    # NOTE a real blind spot that stays: an unmeasured beat BREAKS a run here, because a beat whose motion
    # is unknown cannot be asserted to be kinetic. So 4 kinetic beats with one unmeasured among them yield
    # no run-of-kinetic finding. That is the honest reading, and the `unmeasured` line above is what tells
    # the reader this rule may have been cut short — which is why it is emitted even when nothing else fires.
    run = []
    for r in rows + [{"motion": None}]:
        if r["motion"] is not None and r["motion"] >= kinetic_cut:
            run.append(r)
            continue
        if len(run) >= RUN:
            out.append({"kind": "run-of-kinetic", "beats": [x["beat"] for x in run],
                        "shots": [x["shot"] for x in run], "energy": None, "motion": None, "beat": run[0]["beat"],
                        "shot": run[0]["shot"], "alternatives": []})
        run = []
    # the summit belongs to the peak beat
    peaks = [r for r in rows if r["energy"] == "peak" and r["motion"] is not None]
    if peaks:
        pk = max(peaks, key=lambda r: r["motion"])
        top = max((r for r in rows if r["motion"] is not None), key=lambda r: r["motion"])
        if top["beat"] != pk["beat"] and top["motion"] > SUMMIT_RATIO * max(pk["motion"], 1e-9):
            out.append({"kind": "summit-off-peak", "beat": top["beat"], "shot": top["shot"], "energy": top["energy"],
                        "motion": top["motion"], "peak_beat": pk["beat"], "peak_shot": pk["shot"],
                        "peak_motion": pk["motion"], "alternatives": []})
    return out


def curve(slides, motion, quiet_cut, kinetic_cut, plan=None, beat_motion=None):
    """Two aligned strings: the declared skeleton (L/m/H/P per beat) and the measured register motion as a
    sparkline. Reading them together is the whole check."""
    beats = _beats_by_position(plan, slides)
    dec, meas = [], []
    for k, (s, b) in enumerate(zip(slides, beats), 1):
        e = declared(s, b)
        dec.append({"low": "L", "medium": "m", "high": "H", "peak": "P"}[e])
        m = (beat_motion or {}).get(k, motion.get(s.get("shot")))
        if m is None:
            meas.append("?")
        else:
            lvl = min(8, int(8 * min(1.0, m / max(kinetic_cut * 2.5, 1e-9))))
            meas.append(SPARK[max(1, lvl)])
    return "".join(dec), "".join(meas)


def coverage(fs, slides, curve_pair=None):
    """(measured, universe, [unmeasured findings]).

    M is every entry in `slides`, parsed from the board — never `measured + missing`, which shrinks in step
    with anything the loop silently drops and keeps the line reading 100%.

    `curve_pair` is the CROSS-CHECK. The sparkline marks an unmeasured beat `?` and `findings()` emits an
    `unmeasured` row for it, by two different paths over the same motion map. If they ever disagree, one of
    them has started hiding a beat, and that is a refusal rather than a smaller number.
    """
    miss = [f for f in fs if f.get("kind") == "unmeasured"]
    if curve_pair and curve_pair[1].count("?") != len(miss):
        raise RuntimeError(
            "the curve marks %d unmeasured beat(s) and the findings name %d — one of the two paths is "
            "dropping a beat without recording it, which is exactly the hole this coverage line exists to "
            "close" % (curve_pair[1].count("?"), len(miss)))
    return len(slides) - len(miss), len(slides), miss


def check_slides(slides, plan=None, film_shots=(), beat_motion=None):
    """(findings, curve_pair, why_none) for a storyboard's slides — what validate.py calls on the board it
    holds. Beats the sweep cannot measure arrive as `unmeasured` findings, so a caller that reports findings
    reports the coverage hole too without needing a second channel for it."""
    motion, floor, qc, kc, why, stale_rows = sweep_status()
    slides, malformed = _normalise(slides)
    if why:
        return [], None, why
    return (findings(slides, motion, floor, qc, kc, plan, stale_rows, malformed, film_shots, beat_motion),
            curve(slides, motion, qc, kc, plan, beat_motion), None)


# ── A FILM'S OWN SHOTS, MEASURED BEFORE THE RENDER ──────────────────────────────────────────────────────────────
# The library sweep never sees a workshop, so on a mostly-built film this check measured 0 of N and exited non-zero
# (the compound-interest test: 0/11, and 8 of its 11 beats later measured under the motion floor by hand). Each built
# beat is rendered here with its own props and the film's DNA — at half size, since the instrument reads a 192 px
# long side — and measured with the delivery gate's own `film_energy_qa.measure`. Results are cached per beat on the
# workshop's bytes, the props, the DNA and the aspect, in `<out_dir>/.energy_own.json`; validate reads only the cache.
OWN_CACHE = ".energy_own.json"


# The cache key sees what the picture is made of: every workshop file (code AND assets), the library code a built shot
# can import (runtime/, objects/, kits/ — hashed once per run), the beat's props, the DNA, the aspect, and this
# measurement's own version. It does NOT see the beat's spoken length: before narration that length does not exist,
# so a shot is measured at its own DURATION — an estimate of how much it moves; the render's film_energy_qa measures
# each beat at its real length.
OWN_MEASURE_VERSION = 1


def _library_hash():
    import hashlib
    h = hashlib.sha256()
    src = os.path.join(_HERE, "..", "remotion", "src")
    for sub in ("runtime", "objects", "kits"):
        for root, dns, files in os.walk(os.path.join(src, sub)):
            dns[:] = sorted(d for d in dns if not d.startswith("."))
            for f in sorted(files):
                if f.endswith((".ts", ".tsx")):
                    h.update(os.path.relpath(os.path.join(root, f), src).encode())
                    h.update(open(os.path.join(root, f), "rb").read())
    return h.hexdigest()


def _own_key(out_dir, slide, meta, lib=None):
    import hashlib
    h = hashlib.sha256()
    h.update(("v%d:%s" % (OWN_MEASURE_VERSION, lib if lib is not None else _library_hash())).encode())
    wdir = os.path.join(out_dir, "workshop")
    try:
        import workshop as _ws
        generated = set(_ws.GENERATED)                   # index.ts, _stills/ … — outputs, not what a shot is made of
    except Exception:                                    # noqa: BLE001
        generated = {"index.ts", ".tsconfig.json", "_stills"}
    for root, dns, files in os.walk(wdir):
        dns[:] = sorted(d for d in dns if not d.startswith(".") and not (root == wdir and d in generated))
        for f in sorted(files):
            if f.startswith(".") or (root == wdir and f in generated):
                continue
            h.update(os.path.relpath(os.path.join(root, f), wdir).encode())
            try:
                h.update(open(os.path.join(root, f), "rb").read())
            except OSError as e:
                h.update(("<unreadable: %s>" % type(e).__name__).encode())
    h.update(json.dumps([slide.get("shot"), slide.get("shot_props"), meta.get("design_dna") or
                         meta.get("shot_template"), meta.get("aspect")], sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def own_motion(out_dir, slides, meta, render=False, log=print):
    """{beat: motion_p75} for the beats on this film's own shots — from the cache, and (render=True) by rendering
    and measuring every one the cache does not hold."""
    import workshop as _ws
    own = _ws.shot_names(out_dir)
    path = os.path.join(out_dir, OWN_CACHE)
    try:
        cache = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    out, dirty = {}, False
    todo = [(i, s) for i, s in enumerate(slides, 1) if isinstance(s, dict) and s.get("shot") in own]
    if render and todo:
        import render_remotion as rr
        import film_energy_qa as fe
        env = _ws.prepare(out_dir)
    lib = _library_hash() if todo else ""
    for i, s in todo:
        key = _own_key(out_dir, s, meta, lib)
        if key in cache:
            out[i] = cache[key]
            continue
        if not render:
            continue
        props = rr.film_shot_props(s, out_dir)
        dna = meta.get("design_dna") or meta.get("shot_template")
        if dna is not None:
            props.setdefault("dna", dna)
        if meta.get("aspect"):
            props.setdefault("aspect", meta["aspect"])
        tmpd = os.path.abspath(os.path.join(out_dir, "._energy_own"))   # the render runs from remotion/, not here
        os.makedirs(tmpd, exist_ok=True)
        pf, mp4 = os.path.join(tmpd, "beat_%02d.json" % i), os.path.join(tmpd, "beat_%02d.mp4" % i)
        json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run(["npx", "remotion", "render", "src/index.ts", s["shot"], mp4, "--gl=angle", "--log=error",
                            "--scale=0.5", "--props=" + os.path.abspath(pf), "--public-dir=" + os.path.abspath(out_dir)],
                           cwd=os.path.join(_HERE, "..", "remotion"), capture_output=True, text=True,
                           **_ws.env_kwargs(env))
        if r.returncode != 0 or not os.path.exists(mp4):
            log("[energy_skeleton] beat %d (%s): render failed — %s" % (i, s["shot"], _c.render_error(r.stdout, r.stderr,
                                                                                                   limit=120)))
            continue
        m = fe.measure(mp4)
        if isinstance(m, dict) and m.get("motion_p75") is not None:
            out[i] = cache[key] = round(float(m["motion_p75"]), 4)
            dirty = True
            log("[energy_skeleton] beat %d (%s): measured motion %.4f" % (i, s["shot"], out[i]))
        for f in (pf, mp4):
            if os.path.exists(f):
                os.remove(f)
    if dirty:
        json.dump(cache, open(path, "w", encoding="utf-8"), indent=1)
    return out


def load_plan(out_dir):
    p = os.path.join(out_dir, "content_plan.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:                                           # noqa: BLE001
            return None
    return None


def check(out_dir, render_own=False):
    """(findings, curve_pair, why_none) for an out_dir — the CLI entry point."""
    data = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    try:
        import workshop
        film_shots = workshop.shot_names(out_dir)
    except Exception:                                               # noqa: BLE001 — a reason, never a crash
        film_shots = set()
    beat_motion = {}
    if film_shots:
        try:
            beat_motion = own_motion(out_dir, data.get("slides") or [], data.get("meta") or {}, render=render_own)
        except Exception as e:                                      # noqa: BLE001 — unmeasured says why
            print("[energy_skeleton] the film's own shots could not be measured: %s" % e)
    return check_slides(data.get("slides") or [], load_plan(out_dir), film_shots, beat_motion)


def describe(f):
    """One human line per finding, with the fix that is actually available."""
    if f["kind"] == "run-of-kinetic":
        return ("beats %s are %d kinetic registers in a row (%s) — consecutive high energy reads as noise; "
                "hand one of them a steady register so the run alternates"
                % ("-".join(str(b) for b in f["beats"]), len(f["beats"]), ", ".join(f["shots"])))
    if f["kind"] == "summit-off-peak":
        return ("the film's most kinetic register is %s on beat %d (%s, motion %.4f), not the peak beat %d "
                "(%s, %.4f) — the visual summit is somewhere the argument does not peak; swap them or give "
                "the peak a livelier register"
                % (f["shot"], f["beat"], f["energy"], f["motion"], f["peak_beat"], f["peak_shot"], f["peak_motion"]))
    if f["kind"] == "own-under-floor":
        return ("beat %d (%s, this film's own shot) motion %.4f is under the delivery floor %.4f — it settles and "
                "stops, which reads as a slide. Give it an idle that keeps the subject alive after its reveal (the "
                "runtime's life()/idle clock, light that moves, the object turning) or a motivated camera move"
                % (f["beat"], f["shot"], f["motion"], f.get("floor", 0.0)))
    if f["kind"] == "own-off-energy":
        return ("beat %d (%s, this film's own shot) motion %.4f: declared %s, and it moves like the library's %s third — "
                "tune the shot's own motion to the beat, or re-declare the beat's energy"
                % (f["beat"], f["shot"], f["motion"], f["energy"].upper(),
                   "liveliest" if f.get("mismatch") == "low-on-kinetic" else "stillest"))
    if f["kind"] == "unmeasured":
        return ("beat %d declared %s was NOT checked — %s"
                % (f["beat"], (f.get("energy") or "medium").upper(), f.get("why") or "no motion number"))
    why = {"high-on-quiet": "declared %s, and %s is in the library's stillest third",
           "peak-under-floor": "declared %s, and %s is under the delivery motion floor",
           "low-on-kinetic": "declared %s (a hold), and %s is in the library's liveliest third"}[f["kind"]]
    alt = ("; in band and unused: %s" % ", ".join(f["alternatives"])) if f["alternatives"] else \
        "; nothing in this intent's pool sits in band — widen the pool or change the declared energy"
    return "beat %d (%s) motion %.4f: %s%s" % (f["beat"], f["shot"], f["motion"],
                                               why % (f["energy"].upper(), f["shot"]), alt)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.split("\n\n")[0]); return 2
    fs, cv, why = check(argv[0], render_own="--no-render" not in argv)
    data = json.load(open(os.path.join(argv[0], "storyboard.json"), encoding="utf-8"))
    slides = data.get("slides") or []
    seen, universe, missing = coverage(fs, slides, None if why else cv)
    if "--json" in argv:
        # The JSON carried findings and no coverage, so a caller reading it could not tell a clean film from
        # one whose beats were never measured — the same hole the text path had.
        print(json.dumps({"findings": fs, "curve": cv, "basis": why or "ok",
                          "coverage": {"measured": 0 if why else seen, "universe": universe,
                                       "not_measured": [{"beat": f["beat"], "shot": f.get("shot"),
                                                         "why": f.get("why")} for f in missing]}},
                         ensure_ascii=False, indent=2))
        return 1 if (why or missing or any(f["kind"] in HARD for f in fs)) else 0
    if why:
        # Non-zero: this is "could not measure", and an exit code a caller reads as success is exactly how a
        # hole stays invisible. The line says NOT CHECKED, and now so does the status.
        _c.coverage("energy_skeleton", 0, universe,
                    {"the whole sweep": why} if universe else {})
        print("[energy_skeleton] NOT CHECKED: %s" % why); return 1
    # COVERAGE FIRST, through the shared printer — the same shape every gate here prints.
    _c.coverage("energy_skeleton", seen, universe,
                {"beat %3d %s" % (f["beat"], f.get("shot") or "(no register)"): f.get("why") or "unmeasured"
                 for f in missing})
    print("[energy_skeleton] declared  %s" % cv[0])
    print("[energy_skeleton] measured  %s   (L/m/H/P = plan; bars = register motion, full = 2.5x the kinetic cut)"
          % cv[1])
    if not universe:
        # An empty board used to print the pass sentence, which is a claim about registers over a film that
        # has none. Nothing measured is not the same as nothing wrong.
        print("[energy_skeleton] the board holds no beats — nothing was measured, which is not a pass")
        return 1
    if not fs:
        # Only reachable at full coverage: an unmeasured beat is itself a finding, so `fs` is non-empty
        # whenever one exists. This sentence is a claim about EVERY beat and must never be printed over
        # beats nobody looked at.
        print("[energy_skeleton] the registers follow the plan's skeleton"); return 0
    for f in fs:
        print("  %-17s %s" % (f["kind"], describe(f)))
    hard = sum(f["kind"] in HARD for f in fs)
    print("[energy_skeleton] measured %d of %d beat(s) · %d finding(s), %d hard%s. Findings are candidates: a "
          "beat's real motion also depends on props, ground, camera and length — check the beat, then swap "
          "or re-declare."
          % (seen, universe, len(fs), hard,
             "" if not missing else " · %d beat(s) could not be checked at all" % len(missing)))
    return 1 if (hard or missing) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
