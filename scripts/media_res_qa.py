#!/usr/bin/env python3
"""Is any PICTURE on screen magnified past its own pixels? — asked of the rendered Film, frame by frame.

    python3 scripts/media_res_qa.py <out_dir> [--every=N] [--json]

EXIT 0 = every sampled frame measured, nothing soft · 1 = a picture is upscaled (ERROR) · 2 = frames went unmeasured.

WHY THIS EXISTS. A product film shipped its hero UI soft: the product's own demo frames were 1000 px wide, the 3D
slab they sat in drew them ~1.5x larger, a camera push magnified them again, and they had been re-saved as JPEG on
the way. The user saw it at once ("分辨率有些低，貌似是截取的"). Every gate was green — validate, the type gates,
energy, banding — because every one of them measures TEXT in the DOM or pixels of the whole frame, and none asks
how many source pixels stand behind each pixel of a picture.

The browser knows exactly: an <img> has a natural size and is drawn in a box. `runtime/mediaRes.tsx` reports both
for every raster (img, video, canvas) on every sampled frame of the Film composition — the film's seams, cameras
and pushes included, which a still of one beat would never show — and this judges the census:

  ERROR  magnified more than ERROR_SCALE on at least MIN_FRAMES sampled frames: visibly soft
  WARN   magnified more than WARN_SCALE: soft to a careful eye, and the next push makes it an ERROR

A picture drawn blurred on purpose (a CSS blur of at least BLUR_EXCUSE_PX on it or an ancestor), or nearly
transparent, is listed as excused, never judged. A rotated or tilted picture is measured by its bounding box and
can only read LARGER than it is, so the gate errs toward catching softness.

THE FIX IS NEVER A THRESHOLD. Get pixels: a higher-resolution source, the product's own vector/code rendering,
a native rebuild of UI in the register, or draw the picture smaller. Prefer lossless (PNG) frames for UI.
"""
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WARN_SCALE = 1.08        # 8% past native: resampling softens hairlines and small type
ERROR_SCALE = 1.25       # a quarter past native: visibly soft at 1080p
MIN_FRAMES = 2           # sampled frames a magnification must hold before it is judged (one frame is a seam flash)
BLUR_EXCUSE_PX = 2.0     # drawn blurred on purpose
MIN_OPACITY = 0.25       # fainter than this the picture is arriving or leaving, not being looked at
TAG = "MEDIA-RES "
DEFAULT_EVERY = 3        # every 3rd frame: a camera push is smooth, so its peak is never more than 2 frames away


def _sequence(src):
    """An image SEQUENCE is one picture: `loop/f00028.jpg` and `loop/f00033.jpg` are the same footage, so the last
    run of digits is folded (`loop/f#####.jpg`) and the sequence is reported once, at its worst frame."""
    import re
    return re.sub(r"\d+(?=\.[A-Za-z0-9]+$)", lambda m: "#" * len(m.group(0)), src)


def judge(frames, beat_of, labels, shots):
    """{"errors", "warns", "excused"} from {frame: census}. One finding per (beat, picture), at its worst frame."""
    worst, excused = {}, {}
    for f in sorted(frames):
        for kind, src, nw, nh, dw, dh, fit, s, op, blur in frames[f].get("m") or []:
            if s <= WARN_SCALE:
                continue
            k = beat_of(f)
            key = (k, _sequence(src))
            if blur >= BLUR_EXCUSE_PX or op < MIN_OPACITY:
                excused.setdefault(key, (f, s, "blurred %.0f px" % blur if blur >= BLUR_EXCUSE_PX
                                         else "opacity %.2f" % op))
                continue
            w = worst.setdefault(key, {"f": f, "s": s, "n": 0, "nw": nw, "nh": nh, "dw": dw, "dh": dh, "kind": kind,
                                       "fit": fit, "over_err": 0})
            w["n"] += 1
            if s > ERROR_SCALE:
                w["over_err"] += 1
            if s > w["s"]:
                w.update(f=f, s=s, dw=dw, dh=dh)
    errors, warns = [], []
    for (k, src), w in sorted(worst.items(), key=lambda kv: -kv[1]["s"]):
        if w["n"] < MIN_FRAMES:
            continue
        head = "scene %02d (%s)" % (labels[k], shots[k])
        line = ("%s: %s %s is %dx%d px but drawn %dx%d (object-fit %s) at frame %d — magnified %.2fx past its own "
                "pixels" % (head, w["kind"], src, w["nw"], w["nh"], w["dw"], w["dh"], w["fit"], w["f"], w["s"]))
        if w["over_err"] >= MIN_FRAMES:
            errors.append(line + ". Get pixels: a sharper source, a native/vector rebuild, or draw it smaller.")
        else:
            warns.append(line)
    ex = ["scene %02d (%s): %s at %.2fx — %s" % (labels[k], shots[k], src, s, why)
          for (k, src), (f, s, why) in sorted(excused.items())]
    return {"errors": errors, "warns": warns, "excused": ex}


def scan_film(out_dir, every=DEFAULT_EVERY, concurrency=None):
    import remotion_segments as _rs
    import render_remotion as rr
    import text_safe_qa as ts
    import workshop as _ws
    t0 = time.time()
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    props, slides = rr.film_props(out_dir, board)
    props = dict(props, mediaRes=True)
    segs, total = _rs.timeline(props["scenes"], _rs.seam_frames())
    env = _ws.prepare(out_dir)
    work = tempfile.mkdtemp(prefix="media_res_")
    try:
        public = _rs.minimal_public(props, out_dir, os.path.join(work, "public"))
        bundle = ts.glide_bundle(os.path.join(work, "bundle"), public, env)
        res = ts.glide_run([{"tag": "film", "id": "Film", "props": props}], bundle, concurrency,
                           extra=("--tag=" + TAG.replace(" ", "_"), "--every=%d" % every))["film"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    want = (total - 1) // every + 1
    why = ts._glide_measured(res, want)
    labels = [s.get("index", i + 1) for i, s in enumerate(slides)]
    shots = [s.get("shot") or "?" for s in slides]

    def beat_of(frame):
        for k, (a, b) in enumerate(segs):
            if a <= frame <= b:
                return k
        return len(segs) - 1

    out = judge(res["frames"], beat_of, labels, shots)
    pictures = sum(r.get("n", 0) for r in res["frames"].values())
    out.update(frames=total, sampled=len(res["frames"]), every=every, pictures=pictures,
               unmeasured=[why] if why else [], beats=len(slides), seconds=time.time() - t0)
    return out


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Is any picture on screen magnified past its own pixels?")
    ap.add_argument("out_dir")
    ap.add_argument("--every", type=int, default=DEFAULT_EVERY, help="sample every Nth frame (default %(default)s)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out_dir, every, as_json = a.out_dir, max(1, a.every), a.json
    r = scan_film(out_dir, every=every)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        for e in r["errors"]:
            print("[media_res] ERROR " + e)
        for w in r["warns"]:
            print("[media_res] WARN  " + w)
        for x in r["excused"]:
            print("[media_res] excused " + x)
        for u in r["unmeasured"]:
            print("[media_res] NOT MEASURED: " + u)
        verdict = "FAIL" if r["errors"] else ("UNMEASURED" if r["unmeasured"] else "ok")
        print("[media_res] %s  %d ERROR(s), %d WARN(s) — %d of %d frames sampled (every %d), %d picture "
              "measurement(s), %d beats · %.0fs" % (verdict, len(r["errors"]), len(r["warns"]), r["sampled"],
                                                   r["frames"], r["every"], r["pictures"], r["beats"], r["seconds"]))
        if r["sampled"] and not r["pictures"]:
            print("[media_res] note: no raster picture is drawn anywhere in this film — nothing to be soft")
    if r["errors"]:
        return 1
    return 2 if r["unmeasured"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
