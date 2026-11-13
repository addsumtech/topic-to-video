#!/usr/bin/env python3
"""picture_glide_qa — does a PICTURE under a moving camera glide, or step? Read from the pixels.

    python3 scripts/picture_glide_qa.py <out_dir>                 # every beat of out.mp4 (the render record's spans)
    python3 scripts/picture_glide_qa.py <promo_dir> [--spec=promo.json] [--video=out.mp4]   # a promo film's page shots
    python3 scripts/picture_glide_qa.py --clip <file.mp4> [--from=F --to=F]
    python3 scripts/picture_glide_qa.py --calibrate                # synthetic glide vs whole-pixel staircase

WHY. jitter_qa judges TYPE against the DOM's own geometry, and it says so: pictures are out of its scope. shake_qa
judges a frame that vibrates in place (path / net), and a staircase is not a vibration — it walks the right way in
uneven steps. So a screenshot under a page camera that was re-laid out every frame (its box rounded to whole pixels
at each new zoom) trembled in a delivered zh film — the viewer saw "文字和图像抖动" — while jitter_qa measured only
the overlay labels and shake_qa said OK. This is the instrument for the picture itself.

HOW. Per beat, textured tiles on a grid; for every consecutive frame pair, each tile's shift by phase correlation
with a sub-pixel peak (skimage, upsample 20). A camera move is smooth, so each tile's shift series is smooth too:
the error is the series minus its own smoothed self (Savitzky-Golay, 9 frames, quadratic). A glide leaves ~0.02 px;
a whole-pixel staircase at sub-pixel speeds leaves 0.2-0.5 px with 1 px pops. Per beat the verdict is the MEDIAN
tile's RMS error (a moving overlay or a reveal disturbs a few tiles, not the median) over the frames that MOVE.

EXIT 0 every beat glides · 1 a beat steps · 2 nothing to judge.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAIL_RMS = 0.12      # px; calibrated below: a glide 0.01-0.04, a staircase 0.2+
POP = 0.6            # px; a single pair's error this large is a visible jump
SEAM = 12            # frames at each beat edge left out (the cut / dissolve)
TILE = 160


def _probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,nb_frames,r_frame_rate",
                          "-of", "json", video], capture_output=True, text=True).stdout
    streams = (json.loads(out or "{}") or {}).get("streams") or []
    if not streams:
        raise SystemExit("[picture_glide] %s: no video stream (missing or unreadable file)" % video)
    st = streams[0]
    num, den = st["r_frame_rate"].split("/")
    return int(st["width"]), int(st["height"]), int(st.get("nb_frames") or 0), float(num) / float(den)


def frames(video, a, b, W, H, fps):
    """Gray frames a..b (inclusive) at full resolution, decoded once in order."""
    # FRAME-EXACT: an input seek (`-ss` before `-i`) lands on a keyframe and can hand back the first frame twice — a
    # zero shift followed by the real one, which read as a 0.4 px "pop" on the first pair of every span
    cmd = ["ffmpeg", "-v", "error", "-i", video, "-vf", "select=between(n\\,%d\\,%d)" % (a, b), "-vsync", "0",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.float32)
    p.wait()


def tiles_for(W, H, cols=None, rows=None, top=0.06, bottom=0.80):
    # the grid follows the frame: ~one tile per 220 px each way (8 x 4 at 16:9, 4 x 6 at 9:16), so a portrait frame is
    # sampled down its height and not along one band of it
    cols = cols or max(3, int(round((W - TILE) / 220)))
    rows = rows or max(3, int(round(H * (bottom - top) / 220)))
    xs = np.linspace(TILE, W - 2 * TILE, cols).astype(int)
    ys = np.linspace(H * top, H * bottom - TILE, rows).astype(int)
    return [(int(x), int(y)) for y in ys for x in xs]


def judge_span(video, a, b, W, H, fps):
    from skimage.registration import phase_cross_correlation
    from scipy.signal import savgol_filter
    tl = tiles_for(W, H)
    prev = None
    shifts = {t: [] for t in tl}
    textured = {t: True for t in tl}
    for k, fr in enumerate(frames(video, a, b, W, H, fps)):
        if prev is not None:
            for t in tl:
                x, y = t
                p0, p1 = prev[y:y + TILE, x:x + TILE], fr[y:y + TILE, x:x + TILE]
                if p0.std() < 6:
                    textured[t] = False
                    shifts[t].append((np.nan, np.nan))
                    continue
                sh, err, _ = phase_cross_correlation(p0, p1, upsample_factor=20, normalization=None)
                shifts[t].append((sh[1], sh[0]))
        prev = fr
    # THE CAMERA IS COHERENT; AN ELEMENT IS LOCAL. Per pair, the tiles' shifts are fitted with one field — a translation
    # plus a uniform scale about the frame centre (a pan and a push) — refitted once without the worst tile; a tile more
    # than LOCAL px off the field on that pair is watching its OWN element move (a card popping in, a label rising) and
    # that pair is not counted for it. A whole-page staircase is in the field itself, so it is still measured; measured
    # on a 9:16 beat whose shapes pop in one by one, the acts alone read 0.230 px against 0.081 for the camera alone.
    keys = [t for t in tl if textured[t] and len(shifts[t]) and not np.isnan(np.array(shifts[t], float)).all()]
    n_pairs = max((len(shifts[t]) for t in tl), default=0)
    local = {t: np.zeros(n_pairs, bool) for t in tl}
    LOCAL = 0.4
    for i in range(n_pairs):
        pts = [(t, shifts[t][i]) for t in keys if i < len(shifts[t]) and not np.isnan(shifts[t][i][0])]
        if len(pts) < 3:
            continue
        use = list(range(len(pts)))
        for _ in range(2):
            A, bx, by = [], [], []
            for j in use:
                (x, y), (dx, dy) = pts[j]
                cx_, cy_ = x + TILE / 2 - W / 2, y + TILE / 2 - H / 2
                A.append([1, 0, cx_]); bx.append(dx)
                A.append([0, 1, cy_]); bx.append(dy)
            sol, *_ = np.linalg.lstsq(np.array(A, float), np.array(bx, float), rcond=None)
            res = []
            for j, ((x, y), (dx, dy)) in enumerate(pts):
                cx_, cy_ = x + TILE / 2 - W / 2, y + TILE / 2 - H / 2
                res.append(np.hypot(dx - (sol[0] + sol[2] * cx_), dy - (sol[1] + sol[2] * cy_)))
            worst = int(np.argmax([res[j] for j in use]))
            if len(use) > 3 and res[use[worst]] > LOCAL:
                use.pop(worst)
            else:
                break
        for j, (t, _) in enumerate(pts):
            if res[j] > LOCAL:
                local[t][i] = True
    per_tile = []
    worst_pop = 0.0
    for t, s in shifts.items():
        arr = np.array(s, float)
        if len(arr) < 12 or np.isnan(arr).mean() > 0.2:
            continue
        loc = local[t][:len(arr)]
        keep = ~np.isnan(arr).any(1)
        arr, loc = arr[keep], loc[keep]
        if len(arr) < 12:
            continue
        # a pair where this tile watched its own element: replaced by the camera's path through it, never counted
        if loc.any() and (~loc).sum() >= 4:
            idx = np.arange(len(arr))
            for c in (0, 1):
                arr[loc, c] = np.interp(idx[loc], idx[~loc], arr[~loc, c])
        mag = np.hypot(arr[:, 0], arr[:, 1])
        # JUDGE THE SLOW STRETCHES. A whole-pixel staircase is visible where the picture moves under a few px a frame
        # (a drift, the tail of a move settling); a fast move's own acceleration (49 -> 39 -> 31 px a frame) is not a
        # staircase, but a 9-frame quadratic cannot follow it and reported it as one. So the error counts only on pairs
        # moving 0.05-6 px that are 4+ pairs away from any faster pair.
        fast = mag > 6
        near_fast = np.convolve(fast.astype(float), np.ones(9), mode="same") > 0
        moving = (mag > 0.05) & ~near_fast & ~np.convolve(loc.astype(float), np.ones(5), mode="same").astype(bool)
        if moving.sum() < 6:
            continue
        smooth = np.stack([savgol_filter(arr[:, i], 9, 2) for i in (0, 1)], 1)
        e = np.hypot(*(arr - smooth).T)
        per_tile.append(float(np.sqrt((e[moving] ** 2).mean())))
        worst_pop = max(worst_pop, float(e[moving].max()))
    if len(per_tile) < 3:
        return None if not per_tile else {"rms": None, "tiles": len(per_tile), "pop": worst_pop}
    return {"rms": float(np.median(per_tile)), "tiles": len(per_tile), "pop": worst_pop}


def spans_of(out_dir, spec=None):
    """Each beat's frames, seams excluded: a narrated film's render record, or a promo film's shot table."""
    rec = os.path.join(out_dir, ".render_record.json")
    if spec is None and os.path.isfile(rec):
        r = json.load(open(rec, encoding="utf-8"))
        return [(k + 1, int(a) + SEAM, int(b) - SEAM) for k, (a, b, *_) in enumerate(r["segments"])]
    tbl = json.load(open(spec or os.path.join(out_dir, "promo.json"), encoding="utf-8"))
    out, t = [], 0
    for k, sh in enumerate(tbl["shots"]):
        d = int(round(sh["dur"]))
        if sh.get("kind") == "page":                    # only a page shot moves a picture under a camera
            out.append((k + 1, t + 8, t + d - 8))
        t += d
    return out


def calibrate():
    """A textured plane moving 0.37 px/frame: drawn at sub-pixel positions (a glide) vs rounded to whole pixels."""
    import tempfile
    from PIL import Image
    rng = np.random.default_rng(7)
    tex = (rng.random((1300, 2200)) * 255).astype(np.float32)
    from scipy import ndimage as ndi
    tex = ndi.gaussian_filter(tex, 1.2)
    out = {}
    for mode in ("glide", "stairs"):
        d = tempfile.mkdtemp()
        for i in range(60):
            dx = 0.37 * i
            if mode == "stairs":
                dx = round(dx)
            fr = ndi.shift(tex, (0, dx), order=3)[100:1180, 100:2020]
            Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).save(os.path.join(d, "%03d.png" % i))
        mp4 = os.path.join(d, "c.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(d, "%03d.png"), "-c:v", "libx264",
                        "-crf", "12", "-pix_fmt", "yuv420p", mp4], check=True)
        out[mode] = judge_span(mp4, 0, 59, 1920, 1080, 30)
    print("[picture_glide] calibrate: glide %.3f px · stairs %.3f px (fail over %.2f)" % (out["glide"]["rms"], out["stairs"]["rms"], FAIL_RMS))
    return 0 if out["glide"]["rms"] < FAIL_RMS < out["stairs"]["rms"] else 1  # noqa


def main(argv):
    from _common import argflag
    if "--calibrate" in argv:
        return calibrate()
    if "--clip" in argv:
        video = argv[argv.index("--clip") + 1]
        W, H, n, fps = _probe(video)
        spans = [(1, int(argflag(argv, "from", 0)), int(argflag(argv, "to", max(1, n - 1))))]
    elif argv and not argv[0].startswith("-"):
        out_dir = os.path.abspath(argv[0])
        video = argflag(argv, "video", os.path.join(out_dir, "out.mp4"))
        W, H, n, fps = _probe(video)
        spec = argflag(argv, "spec", None)
        spans = spans_of(out_dir, os.path.join(out_dir, spec) if spec else None)
    else:
        print(__doc__.strip().splitlines()[0])
        return 2
    bad, judged = [], 0
    for beat, a, b in spans:
        if b - a < 14:
            continue
        r = judge_span(video, a, b, W, H, fps)
        if r is None:
            print("  beat %2d  frames %d-%d  nothing moving to judge" % (beat, a, b))
            continue
        if r["rms"] is None:
            print("  beat %2d  frames %d-%d  too little texture to judge (%d tile(s); a verdict needs 3)" % (beat, a, b, r["tiles"]))
            continue
        judged += 1
        flag = r["rms"] > FAIL_RMS
        print("  beat %2d  frames %d-%d  %.3f px RMS (median of %d tiles) · worst pair %.2f px%s"
              % (beat, a, b, r["rms"], r["tiles"], r["pop"], "   <- STEPS" if flag else ""))
        if flag:
            bad.append(beat)
    if not judged:
        print("[picture_glide] NOTHING TO JUDGE — no beat moves a textured picture")
        return 2
    print("[picture_glide] %s — %d of %d beat(s) judged%s" % ("FAIL" if bad else "OK", judged, len(spans),
                                                             ", stepping: %s" % bad if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
