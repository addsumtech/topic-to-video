#!/usr/bin/env python3
"""frame_safe_qa.py — deterministic FRAME-CRAFT gate on the remotion tier's per-scene keyframes.

The video-craft feedback exposed two failures the shot-critic + keyframe_qa did NOT catch:
  (1) on-frame text/graphics running OFF the edge (title/action-safe violation), and
  (2) a scene whose look CLASHES with the committed palette (a white/bright scene in a dark film).

Both are mechanically detectable on the rendered `_keyframes/scene_NN.png`, so they become gates rather
than eyeballing. The Film's content-inset should keep the outer border clear (atmosphere only); this backstops
that structurally and catches any regression or any shot that still bleeds to the edge.

  EDGE-BLEED (ERROR): the outer action-safe border (top/left/right — NOT the bottom caption band) should be
    low-contrast atmosphere. Bright, structured content there means something overflowed the safe box.
  BRIGHTNESS OUTLIER (WARN): a scene whose mean luminance deviates far from the deck median = a palette clash
    (e.g. a white-ground shot dropped into a dark film) — the exact "white grid / white bloom" defect.

Exit non-zero on any EDGE-BLEED error. Run alongside keyframe_qa_remotion before delivery. No CV deps beyond PIL.
"""
import os, sys, glob, json, statistics

try:
    from PIL import Image
except Exception:
    Image = None

MARGIN = 0.035          # action-safe outer border fraction to inspect (EBU R95 ~3.5%)
INK_DELTA = 60          # a pixel this far from the frame's OWN ground counts as content.
# It used to be an ABSOLUTE brightness (>=120 = content), which is only true on a dark film. On a
# light-ground shot every border pixel is >=120, so this gate — a hard DELIVERY gate — reported
# "100.0% of the safe border is bright content" on every scene and a light film could never ship.
# Measuring DEPARTURE from the frame's own ground gives the same answer on a dark frame and the
# right one on a light frame.
EDGE_FRAC_ERR = 0.045   # >this fraction of the (top+left+right) border being bright = an overflow ERROR
# The caption band is read from runtime/layout.ts, not restated. As a literal 0.135 here it silently
# disagreed with the renderer the moment the caption's type size changed, and this gate then measured a
# band 80px shallower than the one the film actually reserves.
from _caption_band import caption_band_px          # noqa: E402


def _ground_luma(px, w, h, step=6):
    """The frame's own dominant luminance — its GROUND."""
    hist = {}
    for y in range(0, h, step):
        for x in range(0, w, step):
            k = px[x, y] // 8
            hist[k] = hist.get(k, 0) + 1
    return (max(hist, key=hist.get) * 8 + 4) if hist else 0


def _gray(im):
    return im.convert("L")


def _keyframes(out_dir):
    d = os.path.join(out_dir, "_keyframes")
    return sorted(glob.glob(os.path.join(d, "scene_*.png")))


def evaluate(out_dir):
    """Returns {ok, errors, warnings, scenes, lums}. Pure — no side effects."""
    errors, warnings = [], []
    if Image is None:
        return {"ok": True, "errors": [], "warnings": ["PIL not available — frame_safe skipped"], "scenes": 0, "lums": []}
    files = _keyframes(out_dir)
    if not files:
        return {"ok": True, "errors": [], "warnings": ["no _keyframes/scene_*.png — nothing to check"], "scenes": 0, "lums": []}

    lums = []
    for f in files:
        name = os.path.basename(f)
        try:
            g = _gray(Image.open(f))
        except Exception as e:
            warnings.append("%s: could not open (%s)" % (name, e)); lums.append(None); continue
        W, H = g.size
        px = g.load()
        ground = _ground_luma(px, W, H)
        m = max(1, int(round(min(W, H) * MARGIN)))
        cap_top = H - caption_band_px(W, H)                   # rows below this are the caption band (skip)
        # --- edge-bleed: sample the top strip + left/right strips (above the caption band) ---
        bright = tot = 0
        step = 2                                              # subsample for speed
        for y in range(0, m, step):                          # top strip (full width)
            for x in range(0, W, step):
                tot += 1
                if abs(px[x, y] - ground) > INK_DELTA:
                    bright += 1
        for y in range(m, cap_top, step):                    # left + right strips (excluding caption band)
            for x in range(0, m, step):
                tot += 1
                if abs(px[x, y] - ground) > INK_DELTA:
                    bright += 1
            for x in range(W - m, W, step):
                tot += 1
                if abs(px[x, y] - ground) > INK_DELTA:
                    bright += 1
        frac = bright / max(1, tot)
        if frac > EDGE_FRAC_ERR:
            errors.append("%s: %.1f%% of the safe border is content — text/graphics likely OFF-FRAME "
                          "(action-safe overflow); inset or wrap the shot's edge elements" % (name, frac * 100))
        # --- scene mean luminance (for the outlier pass) ---
        # cheap mean over a subsample of the whole frame
        s = c = 0
        for y in range(0, H, 6):
            for x in range(0, W, 6):
                s += px[x, y]; c += 1
        lums.append(s / max(1, c))

    # --- brightness outlier: a scene far from the deck median ---
    vals = [l for l in lums if l is not None]
    if len(vals) >= 5:
        med = statistics.median(vals)
        for f, l in zip(files, lums):
            if l is None:
                continue
            # flag a scene >2.4x the deck median brightness (a light scene in a dark deck) or the inverse on a light deck
            if med < 90 and l > max(90, med * 2.4):
                warnings.append("%s: mean luminance %.0f vs deck median %.0f — a BRIGHT scene in a dark film "
                                "(palette clash); use a shot that holds the committed dark palette" % (os.path.basename(f), l, med))
            elif med > 150 and l < min(120, med * 0.5):
                warnings.append("%s: mean luminance %.0f vs deck median %.0f — a DARK scene in a light film "
                                "(palette clash)" % (os.path.basename(f), l, med))

    return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": len(files), "lums": lums}


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    as_json = "--json" in sys.argv
    r = evaluate(out_dir)
    if as_json:
        print(json.dumps(r, indent=1)); sys.exit(0 if r["ok"] else 1)
    for e in r["errors"]:
        print("  ERROR: " + e)
    for w in r["warnings"]:
        print("  warn : " + w)
    print("[frame_safe_qa] %s  %d scene(s), %d error(s), %d warning(s)"
          % ("OK" if r["ok"] else "FAIL", r["scenes"], len(r["errors"]), len(r["warnings"])))
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
