#!/usr/bin/env python3
"""Does any TYPE sit on a Blender plate's object? — asked of the rendered Film, frame by frame.

    python3 scripts/plate_qa.py <out_dir> [--every=N] [--json]

EXIT 0 = every sampled frame measured, no type on a plate object · 1 = type sits on one (ERROR) · 2 = frames went
unmeasured.

WHY THIS EXISTS. A Blender plate (scripts/blender_plate.py) is a video: its objects are pixels, so every DOM gate is
blind to them. The first plate — a GPS satellite, 2026-11-04 — put a wing tip under the label 我在哪 with every gate
green. runtime/blenderPlate.tsx marks each object's box on each frame, runtime/plateClear.tsx measures each line of
the shot's own type, and the film's caption, against those boxes on the frames the Film really renders, and this
judges the census (the caption's place is fixed, so a finding on it names the OBJECT to move — GPS beat 2,
2026-11-04: the Earth's limb ran under the caption with every gate green while this census had the captions off):

  ERROR  at least ERROR_SHARE of a line's box is covered by an object's SILHOUETTE on at least MIN_FRAMES sampled frames
  WARN   at least WARN_SHARE

The census finds lines over an object's BOX, in their own beat only (during a dissolve the leaving beat's type over the
arriving beat's plate is a cross-fade); the share is then read from the plate's kept ID pass, so a line in the empty
corner of a round object's box is beside it, not on it (measured: the Earth's quarter-disc box put every title of an
orbit beat 'on' the Earth). THE FIX IS NEVER A THRESHOLD: move the type, or move the object (stage.place in the scene).
"""
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ERROR_SHARE = 0.15
CAPTION = object()      # the key the caption's hits are judged under, whatever its text on the frame
WARN_SHARE = 0.05
MIN_FRAMES = 2           # one frame is a seam or an entrance passing
TAG = "PLATE-CLEAR "
DEFAULT_EVERY = 3


def mask_share(ids_dir, colors, frame, rect, scale=2):
    """{object: share of `rect` (plate pixels, x0 y0 x1 y1) its SILHOUETTE covers} on plate frame `frame` (0-based),
    read from the plate's ID pass (`ids/NNNN.png`, `scale`x smaller than the plate). A round object's box has empty
    corners; the silhouette does not."""
    from PIL import Image
    path = os.path.join(ids_dir, "%04d.png" % (frame + 1))
    if not os.path.isfile(path):
        raise RuntimeError("the plate's ID pass has no frame %d (%s) — rebuild the plate" % (frame + 1, path))
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    x0, y0 = max(0, int(rect[0] // scale)), max(0, int(rect[1] // scale))
    x1, y1 = min(W, int(-(-rect[2] // scale))), min(H, int(-(-rect[3] // scale)))
    if x1 <= x0 or y1 <= y0:
        return {n: 0.0 for n in colors}
    import numpy as np
    px = np.asarray(im.crop((x0, y0, x1, y1)), dtype=np.int16).reshape(-1, 4)
    seen = px[:, 3] > 0
    out = {}
    for n, c in colors.items():
        want = np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.int16)
        hit = seen & (np.abs(px[:, :3] - want) <= 8).all(axis=1)
        out[n] = float(hit.sum()) / len(px)
    return out


def plate_coverage(out_dir):
    """coverage(plate_id, frame, rect) -> {object: share}, from each built plate's kept ID pass."""
    import blender_plate as bp
    cache = {}

    def cov(plate_id, frame, rect):
        if plate_id not in cache:
            pd = bp.plate_dir(out_dir, plate_id)
            pj = json.load(open(os.path.join(pd, "plate.json"), encoding="utf-8"))
            if not pj.get("ids"):
                raise RuntimeError("plate %r has no ID colours in plate.json — rebuild it" % plate_id)
            cache[plate_id] = (os.path.join(pd, "ids"), pj["ids"])
        ids_dir, colors = cache[plate_id]
        return mask_share(ids_dir, colors, int(frame), rect)
    return cov


def judge(frames, beat_of, labels, coverage):
    """{"errors", "warns"} from {frame: census}; one finding per (beat, text, object), at its worst frame. A hit is a
    line of type over a plate object's BOX; `coverage` says how much of it the object's silhouette really covers."""
    seen = {}
    for f in sorted(frames):
        for hit in frames[f].get("hits") or []:
            text, plate_id, pf, rect = hit[:4]
            cap = len(hit) > 4 and bool(hit[4])
            for obj, share in coverage(plate_id, pf, rect).items():
                if share < WARN_SHARE:
                    continue
                # a karaoke caption's text changes every frame: it is ONE line per beat and object
                k = (beat_of(f), CAPTION if cap else text, obj)
                s = seen.setdefault(k, {"n_err": 0, "n": 0, "worst": 0.0, "at": f})
                s["n"] += 1
                s["n_err"] += share >= ERROR_SHARE
                if share > s["worst"]:
                    s["worst"], s["at"] = share, f
    errors, warns = [], []
    for (beat, text, obj), s in sorted(seen.items(), key=lambda kv: (kv[0][0], -kv[1]["worst"])):
        line = "beat %s: %s sits %d%% over plate object %r (worst at film frame %d)" % (
            labels[beat] if 0 <= beat < len(labels) else beat + 1, "the caption" if text is CAPTION else repr(text),
            round(s["worst"] * 100), obj, s["at"])
        if s["n_err"] >= MIN_FRAMES:
            errors.append(line + (" — move the object (stage.place): the caption's place is fixed" if text is CAPTION
                                  else " — move the type or the object"))
        elif s["n"] >= MIN_FRAMES:
            warns.append(line)
    return {"errors": errors, "warns": warns}


def census_film(out_dir, every=DEFAULT_EVERY, concurrency=None):
    """(census, segs, slides, total) — the Film rendered once with the plate-clear census armed, captions on."""
    import remotion_segments as _rs
    import render_remotion as rr
    import text_safe_qa as ts
    import workshop as _ws
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    props, slides = rr.film_props(out_dir, board)
    # the film AS IT WILL PLAY: a beat whose warp is missing or stale is derived now, exactly as the render does
    # first (the layout gate runs before any render, and type on its register's own clock is not where it will be)
    if os.environ.get("REMOTION_SYNC", "1") != "0":
        import sync_qa as _sq
        _sq.derive_warps(out_dir, board, props, slides, log=print)
    props = dict(props, plateClear=True, captions=True)
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

    out = judge(frames, beat_of, labels, plate_coverage(out_dir))
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
    print("[plate_qa] scope: MEASURED — the shot's own type and the caption against every Blender plate object's "
          "silhouette (its ID pass), in the same beat, on %d of %d frames (every %d)" % (r["sampled"], r["frames"], r["every"]))
    print("[plate_qa] scope: NOT MEASURED — frames between samples; type of another beat during "
          "a dissolve; a silhouette finer than the half-size ID pass")
    print("[plate_qa] %s — %d plate object(s), %d line(s) of type, %.0f s" % (word, r["objects"], r["texts"], r["seconds"]))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
