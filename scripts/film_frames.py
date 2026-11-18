#!/usr/bin/env python3
"""film_frames — render a director-path film page to frames: every frame is window.seek(t), captured in headless Chrome.

    python3 scripts/film_frames.py <film_dir> [--page film.html] [--fps 30] [--from A] [--to B] [--workers 4]
                                   [--out work/frames] [--probe 6] [--quality 95]

Writes <out>/f_%05d.jpg for frames A..B-1 (default: the whole film, from _plan.json "frames" or timeline.json
"duration"). EVERY frame in the range is written: an existing file is replaced, never skipped (a renderer that skipped
existing frames re-rendered nothing after an edit, and the stale frames were judged as new, Grok Bot 2026-11-18).
Workers take CONTIGUOUS blocks, each its own page (scripts/_filmpage.py: ready = filmReady ok + fonts loaded + seek).

THE PROBE. A frame must be a pure function of t, the same in any page. After rendering, `--probe` K moments spread over
the range are drawn in two FRESH pages as PNG and compared; any visible difference fails (exit 1) and both pictures
are kept in <out>/_probe/. It catches what alternating render pages turn into flicker: canvas text drawn before its
font loaded (a fallback in one page, the real font in another), Math.random, timers, a texture still loading.
`--probe 0` skips it (a draft render).

Encode afterwards:  ffmpeg -framerate 30 -i <out>/f_%05d.jpg -i audio/mix.wav -c:v libx264 -crf 17 -pix_fmt yuv420p ...
Exit 0 rendered (and probe clean), 1 the probe found a page-dependent frame, 2 usage error or the page failed to load.
"""
import os
import sys
import time
from multiprocessing import Process, Queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

_USAGE = ("usage: film_frames.py <film_dir> [--page film.html] [--fps 30] [--from A] [--to B] [--workers 4]"
          " [--out work/frames] [--probe 6] [--quality 95]")
PROBE_LEVEL = 24        # a pixel differs when its RGB sum moves more than this (PNG: identical renders differ by 0)
PROBE_SHARE = 0.0002    # and the frame differs when more than this share of pixels do (a glyph, a speck, a texture)


def _worker(port, page, frames, fps, out, quality, q):
    try:
        p = _fp.FilmPage(port, page)
        try:
            for f in frames:
                p.seek(f / fps)
                p.shot(os.path.join(out, "f_%05d.jpg" % f), "jpeg", quality)
        finally:
            p.close()
        q.put(("ok", len(frames)))
    except Exception as e:  # reported by the parent; a worker must not die silently
        q.put(("err", "%s: %s" % (type(e).__name__, e)))


def probe(port, page, times, out):
    """Draw `times` in two fresh pages as PNG; return [(t, share_of_pixels_that_differ)] for the ones that differ."""
    import numpy as np
    from PIL import Image
    d = os.path.join(out, "_probe")
    os.makedirs(d, exist_ok=True)
    shots = []
    for k in ("a", "b"):
        p = _fp.FilmPage(port, page)
        try:
            for t in times:
                path = os.path.join(d, "%s_%08.3f.png" % (k, t))
                p.seek(t)
                p.shot(path, "png")
                shots.append(path)
        finally:
            p.close()
    bad = []
    for t in times:
        a = np.asarray(Image.open(os.path.join(d, "a_%08.3f.png" % t)).convert("RGB")).astype(int)
        b = np.asarray(Image.open(os.path.join(d, "b_%08.3f.png" % t)).convert("RGB")).astype(int)
        share = float((np.abs(a - b).sum(2) > PROBE_LEVEL).mean())
        if share > PROBE_SHARE:
            bad.append((t, share))
    if not bad:
        for s in shots:
            os.remove(s)
    return bad


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "fps", "from", "to", "workers", "out", "probe", "quality"), usage=_USAGE)
    vals = {k: _c.argflag(argv, k, None) for k in ("page", "fps", "from", "to", "workers", "out", "probe", "quality")}
    args = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    page = vals["page"] or "film.html"
    if not os.path.isfile(os.path.join(d, page)):
        print("film_frames: no page at %s" % os.path.join(d, page), file=sys.stderr)
        return 2
    fps = float(vals["fps"] or 30)
    total = _fp.film_frames_count(d, fps)
    a = int(vals["from"] or 0)
    b = int(vals["to"]) if vals["to"] else total
    if b is None:
        print("film_frames: no frame count (no _plan.json \"frames\" or timeline.json \"duration\"): pass --to",
              file=sys.stderr)
        return 2
    if not 0 <= a < b:
        print("film_frames: empty range %d..%d" % (a, b), file=sys.stderr)
        return 2
    out = os.path.join(d, vals["out"] or os.path.join("work", "frames"))
    os.makedirs(out, exist_ok=True)
    nw = max(1, min(int(vals["workers"] or 4), b - a))
    quality = int(vals["quality"] or 95)
    port, srv = _fp.serve(d)
    t0 = time.time()
    try:
        frames = list(range(a, b))
        size = -(-len(frames) // nw)
        blocks = [frames[i:i + size] for i in range(0, len(frames), size)]
        q = Queue()
        ps = [Process(target=_worker, args=(port, page, blk, fps, out, quality, q)) for blk in blocks]
        for p in ps:
            p.start()
        results = [q.get() for _ in ps]
        for p in ps:
            p.join()
        errs = [m for s, m in results if s == "err"]
        if errs:
            print("film_frames: a render page failed: %s" % errs[0], file=sys.stderr)
            return 2
        print("[film_frames] rendered frames %d-%d (%d) in %.0f s with %d page(s) -> %s"
              % (a, b - 1, b - a, time.time() - t0, len(ps), os.path.relpath(out, d)))
        k = int(vals["probe"] if vals["probe"] is not None else 6)
        if k > 0:
            span = (b - a) / fps
            times = [round(a / fps + span * (i + 0.5) / k, 3) for i in range(k)]
            bad = probe(port, page, times, out)
            if bad:
                for t, share in bad:
                    print("PAGE-DEPENDENT  t=%.3fs  %.3f%% of pixels differ between two fresh pages" % (t, share * 100))
                print("[film_frames] RED  a frame is not a pure function of t (fonts loaded after drawing? random?"
                      " timers?): compare %s" % os.path.relpath(os.path.join(out, "_probe"), d))
                return 1
            print("[film_frames] probe OK  %d moment(s) identical in two fresh pages" % k)
        return 0
    except _fp.PageError as e:
        print("film_frames: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
