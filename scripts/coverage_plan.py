#!/usr/bin/env python3
"""Coverage plan — the framings one beat is cut between, on the voice (runtime/coverage.tsx draws them).

WHY (measured, 2026-11-10 craft study, ~/code_project/film_work/craft_study). One narrated sentence was one shot: our
films' shot lengths ran p90/p10 1.6-1.9 against 2.7-37 on 26 published brand films, with no shot under 1.5 s against
7-68% of theirs, and our explainers held one scale (foreground share p90-p10 0.18-0.26 against 0.45-0.68). Their
editors cut a moment into coverage: the whole, then the thing being named, then the next — and a list read aloud is a
burst of close-ups that ends on the whole (iPhone Air cut its camera samples at 0.7 s; Nothing (3) accelerated to 0.6 s
into its climax; TE and B&O show fragments and give the whole last).

THE RULES.
  * items    a clause that names a listed item cuts to a close-up of it (focus_plan's own matching, at a burst pace:
             MIN_SHOT_S between cuts instead of the lead's 1.2 s). After the last item the beat cuts back to the WHOLE
             for its closing END_WIDE_S — fragments first, the whole last.
  * punch    a beat with no named item and at least PUNCH_MIN_BEAT_S long cuts once, on a clause onset in the middle
             of the beat, between the composition and a PUNCH crop around its centre. Beats alternate the order
             (wide→punch, punch→wide) so a film of them is not one more metronome.
  * never    a stage run (its stage moves its own camera); any authored camera, hero move or a hand-off arriving from
             the beat before (two cameras on one frame); a beat shorter than MIN_BEAT_S; the first and the last beat
             (the opening and the end card are composed as they stand); a Blender/3D plate (a raster or a WebGL
             canvas cannot be magnified past its own pixels — the runtime refuses it too, this saves the probe);
             `meta.coverage: false` or a slide's `coverage: false`; no word times (a cut on a guessed word is worse
             than none).
  * entrance a beat's first ENTRY_S (its seam; a register re-posing from the beat before) is never framed: a step
             planned inside it starts at ENTRY_S and the beat opens wide.
  * seams    an anchored seam (container / grow / through-window / punch / carry / return) measures its anchor on the
             composed frame, so a beat on either side of one starts or ends WIDE for at least END_WIDE_S.
  * framing  only WHICH framing is decided here; the runtime measures the frame and refuses any crop that would cut a
             line of type, push content into the caption band or magnify a raster — that step then renders wide.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import focus_plan as _fp                                                         # noqa: E402

MIN_SHOT_S = 0.5          # the shortest framing: a burst cut, still long enough to read one named thing
MIN_BEAT_S = 3.0
PUNCH_MIN_BEAT_S = 5.0
PUNCH = 1.3               # the punch-in's scale: a clear change of framing that keeps the composition's core
PUNCH_WINDOW = (0.35, 0.7)
END_WIDE_S = 0.9          # the whole, held at the end of an item burst (and either side of an anchored seam)
ENTRY_S = 0.8             # a beat's entrance (the seam, a register re-posing from the beat before): never framed —
                          # measured on the fridge film, FridgeLoop re-composes over its first ~0.8 s
ANCHORED = frozenset(("container", "grow", "through-window", "punch", "carry", "return"))
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "shots")
_SOURCE_CACHE = {}


def _is_plate(shot, props):
    """A register that draws a raster plate or a WebGL scene (nothing to magnify past its pixels)."""
    if isinstance(props, dict) and ("plate" in props or "plates" in props):
        return True
    if shot not in _SOURCE_CACHE:
        src = ""
        for root, _d, files in os.walk(_SRC):
            for f in files:
                if f in (shot + ".tsx", shot + ".ts"):
                    with open(os.path.join(root, f), encoding="utf-8") as fh:
                        src = fh.read()
                    break
            if src:
                break
        _SOURCE_CACHE[shot] = bool(re.search(r"@react-three|from 'three'|<Canvas\b|BlenderPlate|PlateImage", src))
    return _SOURCE_CACHE[shot]


def _seam_type(sc):
    return ((sc or {}).get("transitionIn") or {}).get("type")


def _tidy(steps, duration):
    """Drop framings shorter than MIN_SHOT_S (the later one wins) and repeats; keep the first step at 0."""
    out = []
    for s in sorted(steps, key=lambda x: x["t"]):
        if s["t"] >= duration - MIN_SHOT_S:
            continue
        if out and s["t"] - out[-1]["t"] < MIN_SHOT_S:
            if len(out) == 1:
                continue                 # the opening framing keeps its place
            out[-1] = s
        else:
            out.append(s)
        if len(out) >= 2 and out[-1]["frame"] == out[-2]["frame"]:
            out.pop()
    if out and out[0]["t"] > 0:
        out.insert(0, {"t": 0.0, "frame": "wide"})
    return out


def coverage_plan(sc, duration, index, n_beats, prev=None, nxt=None, enabled=True):
    """({"coverage": [...], "coverageItems": {...}} | None) for one scene of the film EDL."""
    if not enabled or sc.get("stage") or index == 0 or index == n_beats - 1 or duration < MIN_BEAT_S:
        return None
    if sc.get("camera") or ((prev or {}).get("camera") or {}).get("handoff"):
        return None
    props, shot = sc.get("props") or {}, sc.get("shot") or ""
    spans, caption = sc.get("capWords") or [], sc.get("caption") or ""
    if not spans or not caption or _is_plate(shot, props):
        return None
    wide_in = _seam_type(sc) in ANCHORED
    wide_out = _seam_type(nxt) in ANCHORED
    items_plan = _fp.focus_plan(props, spans, caption, duration, shot=shot, min_lead=MIN_SHOT_S)
    steps, items = [], None
    if items_plan and any(s.get("key") for s in items_plan):
        items = _fp.focus_items(props, items_plan, shot=shot)
        first = items_plan[0]
        if first["t"] >= 0.6 or wide_in:
            steps.append({"t": 0.0, "frame": "wide"})
        for s in items_plan:
            t = 0.0 if (s is first and not steps) else s["t"]
            steps.append({"t": round(t, 3), "frame": {"key": s["key"]} if s.get("key") else "wide"})
        last = max(s["t"] for s in items_plan)
        back = max(last + MIN_SHOT_S + 0.4, duration - END_WIDE_S - 0.6)
        if back <= duration - END_WIDE_S:
            steps.append({"t": round(back, 3), "frame": "wide"})
    elif duration >= PUNCH_MIN_BEAT_S:
        lo, hi = PUNCH_WINDOW[0] * duration, PUNCH_WINDOW[1] * duration
        onsets = [t for t, _txt, _end in _fp._clauses(spans, caption) if lo <= t <= hi and duration - t >= 1.5]
        if not onsets:
            return None
        b = round(min(onsets, key=lambda t: abs(t - duration / 2)), 3)
        punch = {"punch": PUNCH}
        if index % 2 == 0 or wide_in:
            steps = [{"t": 0.0, "frame": "wide"}, {"t": b, "frame": punch}]
        else:
            steps = [{"t": 0.0, "frame": punch}, {"t": b, "frame": "wide"}]
    # THE ENTRANCE STAYS WIDE: a framed step that would start inside it starts when it ends, the beat opening wide
    if steps and steps[0]["frame"] != "wide":
        steps = [{"t": 0.0, "frame": "wide"}] + [dict(x, t=max(x["t"], ENTRY_S)) for x in steps]
    else:
        steps = [x if (x["frame"] == "wide" or x["t"] >= ENTRY_S) else dict(x, t=ENTRY_S) for x in steps]
    if wide_out and steps and steps[-1]["frame"] != "wide":
        steps.append({"t": round(duration - END_WIDE_S, 3), "frame": "wide"})
    steps = _tidy(steps, duration)
    if not any(s["frame"] != "wide" for s in steps):
        return None
    out = {"coverage": steps}
    if items and any(isinstance(s["frame"], dict) and "key" in s["frame"] for s in steps):
        out["coverageItems"] = items
    return out


def attach(props, slides, meta, fps, total=None):
    """Set `coverage` (+ `coverageItems`) on every scene that gets a plan; clear stale ones. Returns how many.
    `total` is the FILM's beat count: a one-beat sample is still judged by where its beat sits in the film."""
    on = meta.get("coverage") is not False and not props.get("reducedMotion")
    scenes = props["scenes"]
    total = total or len(scenes)
    n = 0
    for i, (sc, sl) in enumerate(zip(scenes, slides)):
        sc.pop("coverage", None)
        sc.pop("coverageItems", None)
        at = int(sl.get("index") or (i + 1)) - 1 if len(scenes) < total else i
        plan = coverage_plan(sc, sc["durF"] / float(fps), at, total,
                             prev=scenes[i - 1] if i else None, nxt=scenes[i + 1] if i + 1 < len(scenes) else None,
                             enabled=on and sl.get("coverage") is not False)
        if plan:
            sc.update(plan)
            n += 1
    return n


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("usage: coverage_plan.py <.remotion-props.json>  — print the plan each beat would get")
        sys.exit(2)
    pr = json.load(open(sys.argv[1], encoding="utf-8"))
    fps = pr.get("fps", 30)
    sc = pr["scenes"]
    for i, s in enumerate(sc):
        p = coverage_plan(s, s["durF"] / float(fps), i, len(sc), sc[i - 1] if i else None,
                          sc[i + 1] if i + 1 < len(sc) else None)
        print(i + 1, s["shot"], round(s["durF"] / fps, 1), json.dumps(p["coverage"]) if p else "-")
