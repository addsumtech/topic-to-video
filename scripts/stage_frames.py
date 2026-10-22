#!/usr/bin/env python3
"""THE FILM'S FRAMES OF A STAGE RUN — what a per-beat gate measures for a beat it cannot render on its own.

A per-beat gate (text_safe_qa, shot_proof, cjk_type_qa) renders a beat's register ALONE, as its own composition, at
its settled frame. A stage component cannot be rendered alone: it draws a whole run of beats at once and reads them
from the run Film.tsx builds (runtime/stageRun.tsx throws outside one). For a beat on a stage run those gates ask
this module instead, and render frames of the FILM — the frame of each keyframe's held state, and the middle of each
move — with the same audit switches a register would get (Film.tsx forwards them) and the captions off, as a
register still has none.

WHICH FRAMES. A beat's own keyframe moves in over its first moments and each of its steps arrives on its phrase
(runtime/stageRun.tsx `buildKeys`, mirrored here frame for frame — tests/test_stage_runs.py holds the two to the same
numbers). A keyframe's state is HELD from its arrival until the next move begins, so the frame just before that is
the state as the viewer reads it; the middle of a move is where the in-between states live (a name pushed off the
frame by a zoom, a part half way down). The last frames of a run that a seam dissolves away, and the film's closing
veil, are never taken as a held state.

    sample_frames(scenes, tr, fps) -> {beat index: {"held": [film frames], "moving": [film frames]}}
    film_payload(out_dir, board, **audit) -> the Film's props, captions off, the audit switches on
    Stills(out_dir, board).still(frame, payload, png) -> (returncode, output) — one bundle, many frames
"""
import json
import os
import shutil
import subprocess
import tempfile

import stage_runs as _sr

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
STEP_MOVE_S = 0.45          # runtime/stageRun.tsx STEP_MOVE_S
CLOSING_VEIL_FRAMES = 16    # Film.tsx: the last scene's caption closes 16 frames before the end, under the outro veil


def _js_round(x):
    import remotion_segments as _rs
    return _rs.js_round(x)


def morph_frames(dur_f, fps):
    """runtime/stageRun.tsx morphFrames."""
    return max(1, _js_round(min(dur_f * 0.4, fps * 0.8)))


def keyframes(scenes, first, last, fps):
    """runtime/stageRun.tsx buildKeys for the run scenes[first..last]: [{beat, step, from, to}], frames counted from
    the run's first frame. Steps must carry their resolved `t` (render_remotion writes it)."""
    keys, start = [], 0
    for k in range(first, last + 1):
        sc = scenes[k]
        dur = max(1, _js_round(sc.get("durF") or 0))
        keys.append({"beat": k, "step": -1, "from": start,
                     "to": start if k == first else start + morph_frames(dur, fps)})
        for j, st in enumerate(((sc.get("props") or {}).get("steps") or [])):
            t = st.get("t") if isinstance(st, dict) else None
            if not isinstance(t, (int, float)) or isinstance(t, bool):
                raise ValueError("stage beat %d step %d has no resolved `t`" % (k + 1, j + 1))
            prev_from = keys[-1]["from"]
            arrive = min(start + dur - 1, max(prev_from + 1, start + _js_round(t * fps)))
            move = st.get("move")
            want = _js_round((move if isinstance(move, (int, float)) and move > 0 else STEP_MOVE_S) * fps)
            d = max(1, min(want, arrive - prev_from))
            keys.append({"beat": k, "step": j, "from": arrive - d, "to": arrive})
        start += dur
    return keys


def sample_frames(scenes, tr, fps):
    """{beat index: {"held": [...], "moving": [...]}} in FILM frames, for every beat on a stage run."""
    import remotion_segments as _rs
    ranges, _total = _rs.timeline(scenes, tr)
    out = {}
    n = len(scenes)
    for first, last, _r in _sr.runs(scenes):
        base = ranges[first][0]
        run_len = sum(max(1, _js_round(scenes[k].get("durF") or 0)) for k in range(first, last + 1))
        # the frames a seam dissolves away (or the closing veil covers) are never a held state
        usable = run_len - 1 - (tr if last < n - 1 else CLOSING_VEIL_FRAMES)
        keys = keyframes(scenes, first, last, fps)
        for i, kf in enumerate(keys):
            nxt = keys[i + 1]["from"] if i + 1 < len(keys) else run_len
            held = max(kf["to"], min(nxt - 1, usable))
            slot = out.setdefault(kf["beat"], {"held": [], "moving": []})
            slot["held"].append(base + held)
            if kf["to"] - kf["from"] >= 3:
                slot["moving"].append(base + (kf["from"] + kf["to"]) // 2)
        for k in range(first, last + 1):
            slot = out.setdefault(k, {"held": [], "moving": []})
            slot["held"] = sorted(set(slot["held"]))
            slot["moving"] = sorted(set(slot["moving"]) - set(slot["held"]))
    return out


def film_payload(out_dir, board, **audit):
    """The Film's props for this board as render_remotion builds them, with the captions off (a register still has
    none, and a caption in the band would read as the stage's own ink) and the given audit switches on."""
    import render_remotion as _rr
    props, _slides = _rr.film_props(out_dir, board)
    props = dict(props, captions=False)
    props.update({k: v for k, v in audit.items() if v is not None})
    return props


class Stills:
    """Many stills of the Film from ONE bundle (a bundle per still is the per-register gates' cost, multiplied by
    every keyframe of every run). The bundle carries a public folder holding only the files the props name, and the
    film's workshop."""

    def __init__(self, out_dir, props):
        import remotion_segments as _rs
        import workshop as _ws
        self.out_dir = out_dir
        self.env = _ws.prepare(out_dir)
        self.work = tempfile.mkdtemp(prefix="stage_frames_")
        public = os.path.join(self.work, "public")
        _rs.minimal_public(props, out_dir, public)
        self.bundle = os.path.join(self.work, "bundle")
        cmd = ["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + self.bundle, "--log=error",
               "--public-dir=" + public]
        r = subprocess.run(cmd, cwd=_REMOTION, capture_output=True, text=True, **_ws.env_kwargs(self.env))
        if r.returncode != 0 or not os.path.isfile(os.path.join(self.bundle, "index.html")):
            self.close()
            raise RuntimeError("the stage-frames bundle failed: %s" % ((r.stdout or "") + (r.stderr or ""))[-600:])

    def still(self, frame, props, png):
        """(returncode, stdout+stderr) of one still of the Film at `frame` — an audit reports by cancelling the
        render with its tag in the message, so a non-zero code is how an armed audit answers."""
        import _common as _c
        import workshop as _ws
        pf = png + ".props.json"
        with open(pf, "w", encoding="utf-8") as fh:
            json.dump(props, fh, ensure_ascii=False, allow_nan=False)
        import remotion_segments as _rs
        cmd = ["npx", "remotion", "still", self.bundle, "Film", png, "--frame=%d" % frame, "--gl=" + _rs.default_gl(),
               "--log=error", "--props=" + os.path.abspath(pf)]
        try:
            r = _c.run_render(subprocess.run, cmd, capture_output=True, text=True, cwd=_REMOTION,
                              **_ws.env_kwargs(self.env))
        finally:
            if os.path.exists(pf):
                os.remove(pf)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def close(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


def run_slides(slides, k):
    """The slides of the stage run beat k is on — what a gate's cache key must hold besides beat k (every frame of a
    run draws every beat of it)."""
    for first, last, _r in _sr.runs(slides):
        if first <= k <= last:
            return slides[first:last + 1]
    return []
