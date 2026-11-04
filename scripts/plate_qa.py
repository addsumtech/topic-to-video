#!/usr/bin/env python3
"""Does any TYPE sit on a Blender plate's object? — asked of the rendered Film, frame by frame.

    python3 scripts/plate_qa.py <out_dir> [--every=N] [--json]

EXIT 0 = every sampled frame measured, no type on a plate object · 1 = type sits on one (ERROR) · 2 = frames went
unmeasured.

WHY THIS EXISTS. A Blender plate (scripts/blender_plate.py) is a video: its objects are pixels, so every DOM gate is
blind to them. The first plate — a GPS satellite, 2026-11-04 — put a wing tip under the label 我在哪 with every gate
green. runtime/blenderPlate.tsx marks each object's box on each frame, runtime/plateClear.tsx measures each line of
the shot's own type against those boxes on the frames the Film really renders (captions off: the caption is the
film's, drawn on the frame's ground by rule, not the shot's), and this judges the census:

  ERROR  a line of type has at least ERROR_SHARE of its box over an object on at least MIN_FRAMES sampled frames
  WARN   at least WARN_SHARE

A box is the object's bounding box, so a line beside a thin diagonal part can read as over it: the gate errs toward
catching. THE FIX IS NEVER A THRESHOLD: move the type, or move the object (stage.place in the scene).
"""
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ERROR_SHARE = 0.15
WARN_SHARE = 0.05
MIN_FRAMES = 2           # one frame is a seam or an entrance passing
TAG = "PLATE-CLEAR "
DEFAULT_EVERY = 3


def judge(frames, beat_of, labels):
    """{"errors", "warns"} from {frame: census}; one finding per (beat, text, object), at its worst frame."""
    seen = {}
    for f in sorted(frames):
        for text, obj, ov, area in frames[f].get("hits") or []:
            share = ov / area if area else 0.0
            if share < WARN_SHARE:
                continue
            k = (beat_of(f), text, obj)
            s = seen.setdefault(k, {"n_err": 0, "n": 0, "worst": 0.0, "at": f})
            s["n"] += 1
            s["n_err"] += share >= ERROR_SHARE
            if share > s["worst"]:
                s["worst"], s["at"] = share, f
    errors, warns = [], []
    for (beat, text, obj), s in sorted(seen.items(), key=lambda kv: (kv[0][0], -kv[1]["worst"])):
        line = "beat %s: %r sits %d%% over plate object %r (worst at film frame %d)" % (
            labels[beat] if 0 <= beat < len(labels) else beat + 1, text, round(s["worst"] * 100), obj, s["at"])
        if s["n_err"] >= MIN_FRAMES:
            errors.append(line + " — move the type or the object")
        elif s["n"] >= MIN_FRAMES:
            warns.append(line)
    return {"errors": errors, "warns": warns}


def census_film(out_dir, every=DEFAULT_EVERY, concurrency=None):
    """(census, segs, slides, total) — the Film rendered once with the plate-clear census armed, captions off."""
    import remotion_segments as _rs
    import render_remotion as rr
    import text_safe_qa as ts
    import workshop as _ws
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    props, slides = rr.film_props(out_dir, board)
    props = dict(props, plateClear=True, captions=False)
    segs, total = _rs.timeline(props["scenes"], _rs.seam_frames())
    env = _ws.prepare(out_dir)
    work = tempfile.mkdtemp(prefix="plate_clear_")
    try:
        public = _rs.minimal_public(props, out_dir, os.path.join(work, "public"))
        bundle = ts.glide_bundle(os.path.join(work, "bundle"), public, env)
        res = ts.glide_run([{"tag": "film", "id": "Film", "props": props}], bundle, concurrency,
                           extra=("--tag=" + TAG.replace(" ", "_"), "--every=%d" % every))["film"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return res, segs, slides, total


def scan_film(out_dir, every=DEFAULT_EVERY, concurrency=None):
    import text_safe_qa as ts
    t0 = time.time()
    res, segs, slides, total = census_film(out_dir, every, concurrency)
    want = (total - 1) // every + 1
    why = ts._glide_measured(res, want)
    frames = res.get("frames") or {}
    if not why and len(frames) < want:
        why = "only %d of %d sampled frames reported a census" % (len(frames), want)
    labels = [s.get("index", i + 1) for i, s in enumerate(slides)]

    def beat_of(frame):
        for k, (a, b) in enumerate(segs):
            if a <= frame <= b:
                return k
        return len(segs) - 1

    out = judge(frames, beat_of, labels)
    out.update(frames=total, sampled=len(frames), every=every, objects=max((r.get("objects", 0) for r in frames.values()), default=0),
               texts=max((r.get("texts", 0) for r in frames.values()), default=0), unmeasured=[why] if why else [],
               seconds=round(time.time() - t0, 1))
    return out


def verdict(r):
    if r["errors"]:
        return "FAIL", 1
    if r["unmeasured"]:
        return "UNMEASURED", 2
    if not r["objects"]:
        return "NOTHING TO JUDGE", 0
    return "ok", 0


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Does any type sit on a Blender plate's object?")
    ap.add_argument("out_dir")
    ap.add_argument("--every", type=int, default=DEFAULT_EVERY)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = scan_film(a.out_dir, every=max(1, a.every))
    except (OSError, ValueError, RuntimeError) as e:
        print("[plate_qa] NOT MEASURED — %s: %s" % (type(e).__name__, e))
        print("[plate_qa] scope: nothing was measured (exit 2 is not a pass)")
        return 2
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    for e in r["errors"]:
        print("[plate_qa] ERROR " + e)
    for w in r["warns"]:
        print("[plate_qa] WARN  " + w)
    for u in r["unmeasured"]:
        print("[plate_qa] NOT MEASURED: " + u)
    word, code = verdict(r)
    print("[plate_qa] scope: MEASURED — the shot's own type (captions off) against every Blender plate object's "
          "bounding box, on %d of %d frames (every %d)" % (r["sampled"], r["frames"], r["every"]))
    print("[plate_qa] scope: NOT MEASURED — the burned caption; frames between samples; type over an object's "
          "transparent gaps (a box, not its silhouette)")
    print("[plate_qa] %s — %d plate object(s), %d line(s) of type, %.0f s" % (word, r["objects"], r["texts"], r["seconds"]))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
