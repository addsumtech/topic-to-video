"""beat_clock — where each beat of a rendered film is, on the film's OWN clock. One reader for every tool that asks.

Three tools kept a copy each (settled_frame.beat_window, film_energy_qa.beat_spans, review_sheet.spans), and they
disagreed: two subtracted the Remotion seam at every cut whatever drew the film, so on an HTML film (render.py
concatenates its clips as they are) `settled_frame --beat N` landed 0.4 s early per cut; the third read the render
record and trimmed a hard-coded 12-frame seam even after a beat that continues a stage run, which has none.

The film's `_plan.json` (written by render.py, render_remotion.py and promo_film.py beside the video) holds each
beat's real frames, so it is read first — when it names the video asked about and is no older than it. Otherwise the
board is read on the clock of the renderer that draws it: Remotion mounts a beat after a seam `tr` frames before the
last one ends (none inside a stage run); render.py does not overlap.
"""
import json
import os

PLAN = "_plan.json"
STALE_S = 5          # a video written this long after its plan is a later render the plan does not describe


def plan_spans(out_dir, video=None):
    """[(start_s, end_s)] per beat from `_plan.json`, or None when there is no plan, it describes another video, or the
    video was replaced after it was written."""
    p = os.path.join(out_dir, PLAN)
    try:
        plan = json.load(open(p, encoding="utf-8"))
        fps = float(plan["fps"])
        segs = plan["segments"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    vid = video or os.path.join(out_dir, plan.get("video") or "out.mp4")
    if plan.get("video") and os.path.basename(vid) != plan["video"]:
        return None
    if os.path.exists(vid) and os.path.getmtime(vid) > os.path.getmtime(p) + STALE_S:
        return None
    if not fps > 0 or not segs:
        return None
    return [(float(s["start"]) / fps, float(s["end"]) / fps) for s in segs]


def board_spans(board, fps=None):
    """[(start_s, end_s)] per beat from the board's durations, on its renderer's clock."""
    slides = board.get("slides") or []
    meta = board.get("meta") or {}
    fps = float(fps or meta.get("fps") or 30)
    seam, joined = 0.0, [False] * len(slides)
    if (meta.get("renderer") or "") == "remotion":
        import render_remotion as _rr
        import stage_runs as _sr
        seam = _rr._REMOTION2_TR / fps
        joined = _sr.joined_flags(slides)
    out, t = [], 0.0
    for i, s in enumerate(slides):
        d = float(s.get("duration") or 0)
        out.append((t, t + d))
        t += d - (seam if i + 1 < len(slides) and not joined[i + 1] else 0.0)
    return out


def spans(out_dir=None, board=None, video=None):
    """[(start_s, end_s)] per beat: the film's plan when it describes this video, else the board's clock. `out_dir`
    defaults to the video's folder; `board` to its storyboard.json."""
    if out_dir is None and video:
        out_dir = os.path.dirname(os.path.abspath(video))
    if out_dir:
        sp = plan_spans(out_dir, video)
        if sp is not None:
            return sp
        if board is None:
            board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    if board is None:
        raise ValueError("beat_clock.spans needs an out_dir, a video or a board")
    return board_spans(board)


def clear(sp, k):
    """(start_s, end_s) of beat k (0-based) that NO SEAM TOUCHES: after the overlap with the beat before, before the
    one with the beat after. The whole beat when its two seams leave nothing between them."""
    s, e = sp[k]
    a = max(s, sp[k - 1][1]) if k > 0 else s
    b = min(e, sp[k + 1][0]) if k + 1 < len(sp) else e
    return (a, b) if b > a else (s, e)
