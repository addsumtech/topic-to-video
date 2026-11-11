#!/usr/bin/env python3
"""surface_qa.py — is the film's subject a LIT SURFACE or a flat fill? (advisory; references/craft-study.md P0)

WHY. After the 2026-11-10 craft round the user saw "no real difference in the design", and was right: the round's
instruments (rhythm, scale, tonal key) never looked at what the eye sees first between a B&O frame and ours — whether
the subject is a surface the light has modelled. Measured on 28 published films and ours with this instrument:
LIT FRAMES (frames where modelled regions cover >= 5 % of the picture) B&O 0.70-0.87, Dyson 0.85-0.92, Nothing
0.58-0.90, Apple 0.59-0.73 against ours 0.10-0.29. Flat-graphic registers are flat BY DESIGN (Kurzgesagt 0.22,
Notion and Linear 0.00), so the band applies to a film whose subject is a PHYSICAL object.

A frame (480 px wide; the bottom 20 % — the burned caption — ignored; luma blurred sigma 1 so codec noise is not
shading): content = pixels > 24 RGB from the frame's dominant colour; regions = content split at strong edges
(gradient >= 8 /px); a region over 0.5 % of the frame is MODELLED when its luma p95-p5 >= 25.

    python scripts/surface_qa.py <out_dir | film.mp4> [--every 2.0] [--json]

ADVISORY: prints the film's numbers beside the band and never fails a render.
"""
import json
import os
import subprocess
import sys
from io import BytesIO

BAND = (0.54, 0.92)          # lit frames, physical-product films (B&O, Dyson, Nothing, Apple; craft study 2026-11-11)
LIT_REGION = 0.05            # a frame is lit when modelled regions cover this share of it
RAMP = 25.0                  # a region whose luma spans this (p95-p5) inside it is modelled
EDGE = 8.0                   # gradient (luma/px at 480 px) that splits regions
MIN_REGION = 0.005           # regions smaller than this share of the frame are ignored (type, hairlines, dots)
CAPTION = 0.2


def frame_stats(a):
    """{modelled, flat_area, content} of one RGB frame (H x W x 3, any size)."""
    import numpy as np
    from scipy import ndimage as ndi
    a = np.asarray(a, dtype="float32")
    if a.ndim != 3 or a.shape[2] < 3 or a.shape[0] < 10 or a.shape[1] < 10:
        raise ValueError("surface_qa: expected an RGB frame, got shape %r" % (a.shape,))
    a = a[: int(a.shape[0] * (1 - CAPTION)), :, :3]
    q = (a // 24).astype(int)
    codes = q[..., 0] * 10000 + q[..., 1] * 100 + q[..., 2]
    vals, cnt = np.unique(codes, return_counts=True)
    bg = a[codes == vals[cnt.argmax()]].mean(axis=0)
    content = np.linalg.norm(a - bg, axis=-1) > 24
    L = ndi.gaussian_filter(0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2], 1.0)
    gy, gx = np.gradient(L)
    G = np.hypot(gx, gy)
    lab, k = ndi.label(content & (G < EDGE))
    area = np.bincount(lab.ravel(), minlength=k + 1)
    modelled = flat = 0
    for r in np.where(area > MIN_REGION * content.size)[0]:
        if r == 0:
            continue
        v = L[lab == r]
        rng = float(np.percentile(v, 95) - np.percentile(v, 5))
        if rng >= RAMP:
            modelled += int(area[r])
        elif rng < 12:
            flat += int(area[r])
    n = float(content.size)
    return {"modelled": modelled / n, "flat_area": flat / n, "content": float(content.mean())}


def _grab(mp4, t):
    import numpy as np
    from PIL import Image
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", mp4, "-frames:v", "1", "-vf", "scale=480:-2",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        raise RuntimeError("could not read a frame at %.2fs of %s: %s" % (t, mp4, r.stderr.decode()[-200:]))
    return np.asarray(Image.open(BytesIO(r.stdout)).convert("RGB"))


def _beats(out_dir):
    """[(first_frame, last_frame, fps, shot)] of a rendered film dir, or [] when it has no render record."""
    rec, sb = os.path.join(out_dir, ".render_record.json"), os.path.join(out_dir, "storyboard.json")
    if not (os.path.isfile(rec) and os.path.isfile(sb)):
        return []
    segs = json.load(open(rec)).get("segments") or []
    board = json.load(open(sb, encoding="utf-8"))
    slides, fps = board.get("slides") or [], float((board.get("meta") or {}).get("fps") or 30)
    return [(int(a), int(b), fps, (slides[i].get("shot") or slides[i].get("blender", {}).get("id") or "?")
             if i < len(slides) else "?") for i, (a, b, *_rest) in enumerate(segs)]


def measure(path, every=2.0):
    import numpy as np
    mp4, beats = path, []
    if os.path.isdir(path):
        rec = os.path.join(path, ".render_record.json")
        name = json.load(open(rec)).get("out", "out.mp4") if os.path.isfile(rec) else "out.mp4"
        mp4 = os.path.join(path, name)
        beats = _beats(path)
    if not os.path.isfile(mp4):
        raise FileNotFoundError("surface_qa: no film at %s" % mp4)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                               capture_output=True, text=True).stdout or 0)
    if dur <= 1.0:
        raise RuntimeError("surface_qa: %s is too short to sample (%.2fs)" % (mp4, dur))
    ts = list(np.arange(min(1.0, dur / 4), dur - 0.3, every))
    # every beat gets at least one sample at its middle, so a short beat is never invisible in the per-beat list
    for a, b, fps, _shot in beats:
        if not any(a / fps <= t <= b / fps for t in ts):
            ts.append((a + b) / 2 / fps)
    ts.sort()
    rows = [frame_stats(_grab(mp4, t)) for t in ts]
    m = np.array([r["modelled"] for r in rows])
    out = {"frames": len(rows), "lit_frames": round(float((m >= LIT_REGION).mean()), 2),
           "modelled_mean": round(float(m.mean()), 3)}
    if beats:
        per = []
        for i, (a, b, fps, shot) in enumerate(beats):
            mine = [float(v) for t, v in zip(ts, m) if a / fps <= t <= b / fps]
            per.append({"beat": i + 1, "shot": shot, "lit": round(float(np.mean([v >= LIT_REGION for v in mine])), 2)})
        out["beats"] = per
    return out


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[0])
        return 2
    every = float(argv[argv.index("--every") + 1]) if "--every" in argv else 2.0
    r = measure(os.path.abspath(argv[0]), every)
    if "--json" in argv:
        print(json.dumps(r))
        return 0
    lo, hi = BAND
    where = "below" if r["lit_frames"] < lo else ("above" if r["lit_frames"] > hi else "inside")
    print("[surface] %d frames sampled; lit frames %.2f (published product films %.2f-%.2f: %s); mean modelled share %.3f"
          % (r["frames"], r["lit_frames"], lo, hi, where, r["modelled_mean"]))
    print("  the band applies to a PHYSICAL subject (a product, a machine, a part); a flat-graphic register is flat by design")
    flat = [b for b in r.get("beats") or [] if b["lit"] < 0.5]
    if flat:
        # the film-wide share mixes object beats with diagram beats: an explainer about a product (the ANC film,
        # 2026-11-11: every object beat lit, 11 of 24 beats waves and timelines) sits below the band with nothing
        # to fix. Read the list: an OBJECT drawn flat is the finding, a diagram drawn flat is the register.
        print("  flat beats (judge each: is its subject a physical object, or a diagram that is flat by design?):")
        for b in flat:
            print("    beat %d  %s  (lit %.2f)" % (b["beat"], b["shot"], b["lit"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
