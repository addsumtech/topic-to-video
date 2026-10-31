#!/usr/bin/env python3
"""frame_safe_qa.py — deterministic FRAME-CRAFT gate on the remotion tier's per-scene keyframes.

The video-craft feedback exposed two failures the shot-critic + keyframe_qa did NOT catch:
  (1) on-frame text/graphics running OFF the edge (title/action-safe violation), and
  (2) a scene whose look CLASHES with the committed palette (a white/bright scene in a dark film).

Both are mechanically detectable on the rendered `_keyframes/scene_NN.png`, so they become gates rather
than eyeballing. The Film's content-inset should keep the outer border clear (atmosphere only); this backstops
that structurally and catches any regression or any shot that still bleeds to the edge.

  EDGE-BLEED (WARN, was an ERROR): how much of the outer border (top/left/right — NOT the bottom caption
    band) carries content. It was a hard delivery gate on the theory that border ink means an overflow. That
    theory is measurably backwards — see the comment at the check — so it now reports rather than blocks, and
    `text_safe_qa.py` asks the DOM the question this one was trying to answer by inference.
  BRIGHTNESS OUTLIER (WARN): a scene whose mean luminance deviates far from the deck median = a palette clash
    (e.g. a white-ground shot dropped into a dark film) — the exact "white grid / white bloom" defect.

This gate is therefore ADVISORY on its own: read its warnings, and let `text_safe_qa.py` be the gate
that blocks. Run both alongside keyframe_qa_remotion before delivery. No CV deps beyond PIL.
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


# THE 9:16 MARGIN MUST CONTINUE THE FRAME, NOT FRAME IT. A platform-safe film draws every register in a frame scaled
# by k (runtime/safeZone.ts) whose edges dissolve over the action-safe border; what shows round it is the margin. Two
# defects lived there and no gate saw either (2026-10-30 generality film A): with the echo on, the register MAGNIFIED
# about the frame's centre carried interior content into the margin — the balance wheel as gold arcs in the top corners
# (measured here: up to 61 levels against the frame's own edge); with it off, the film's flat ground round the
# register's radial one — a lit panel whose top edge stepped 13 levels. Measured per segment along each side: the
# median colour just inside the frame's dissolving edge against the median just outside it, in the margin. A
# continuation reads a few levels (the ground's own slope across the gap); a panel edge or a smudge reads far more.
# The bottom side is not judged: the caption is burned there, over the platform's own UI.
MARGIN_SEAM_WARN = 8      # levels (max over RGB) between the frame's edge and the margin beside it
_SEG = 0.05               # segment length along a side, as a share of the short side
_BAND = 0.02              # band depth either side of the edge, as a share of the short side
_GAP = 0.006              # kept clear of the edge itself, as a share of the short side


def margin_seam(rgb, prof=None, asf=None):
    """{side: (worst level step, at px along the side)} for a platform-safe frame `rgb` (H x W x 3 uint8 array):
    the largest median-colour step between the scaled frame's inner edge band and the margin band beside it, per side
    (top / left / right), over segments of the side. Profile and border are READ from the runtime."""
    import numpy as np
    import text_safe_qa as tsq
    prof = prof or tsq.safe_profile()
    asf = tsq.action_safe_frac() if asf is None else asf
    H, W = rgb.shape[:2]
    short = min(W, H)
    k = prof["k"]
    x0, y0 = (1 - k) * W / 2, prof["y0"] * H
    x1, y1 = W - x0, y0 + k * H
    fx, fy = asf * k * W, asf * k * H                     # the mask's ramp, in frame px (a share of the scaled box)
    d, gap, seg = (max(2, round(v * short)) for v in (_BAND, _GAP, _SEG))
    cap_top = y1 - k * caption_band_px(W, H)              # the register's own caption band, where the caption burns
    a = rgb.astype(np.int16)

    def med(y_lo, y_hi, x_lo, x_hi):
        y_lo, y_hi, x_lo, x_hi = (int(round(v)) for v in (max(0, y_lo), min(H, y_hi), max(0, x_lo), min(W, x_hi)))
        if y_hi - y_lo < 2 or x_hi - x_lo < 2:
            return None
        return np.median(a[y_lo:y_hi, x_lo:x_hi].reshape(-1, 3), axis=0)

    out = {}
    sides = {
        "top": [(med(y0 + fy, y0 + fy + d, s, s + seg), med(y0 - gap - d, y0 - gap, s, s + seg), s)
                for s in range(int(x0 + fx), int(x1 - fx - seg) + 1, seg)],
        "left": [(med(s, s + seg, x0 + fx, x0 + fx + d), med(s, s + seg, x0 - gap - d, x0 - gap), s)
                 for s in range(int(y0 + fy), int(cap_top - seg) + 1, seg)],
        "right": [(med(s, s + seg, x1 - fx - d, x1 - fx), med(s, s + seg, x1 + gap, x1 + gap + d), s)
                  for s in range(int(y0 + fy), int(cap_top - seg) + 1, seg)],
    }
    for side, pairs in sides.items():
        steps = [(float(np.abs(i - o).max()), at) for i, o, at in pairs if i is not None and o is not None]
        if steps:
            out[side] = max(steps)
    return out


# A COPY OF THE CONTENT IN THE MARGIN IS NOT A STEP AT ITS EDGE. margin_seam compares colour across the frame's edge, so
# it read the second echo — the register drawn unscaled behind its frame, a ghost iPhone and its home bar under the
# caption — as a continuation: the ghost IS continuous with the frame. What gives a ghost away is STRUCTURE: a ground is
# smooth at every scale an object has. Two difference-of-Gaussian bands over the margin alone (a normalised blur, so the
# frame's own content never leaks in), the 99.9th percentile of |response| over RGB, per region:
#   fine 3-16 px: outlines, a home bar;  coarse 12-48 px: blobs, the heavily blurred first echo's smudges.
# Measured on film A at 9:16 (2026-10-31): plain grounds (echo off, and the ground-only margin on the photo, slab,
# mechanism and phone beats) 0.3-1.6; the ghost phone 12.4 / 23.6 (bottom), the ghost slab and wheel rim 11-17 / 36-42
# (sides), the first echo's smudges coarse 7-20, the photo plate's ghost box edge 3.3-3.9.
MARGIN_STRUCTURE_WARN = 3.0   # levels, either band — about twice a plain ground's worst, under every ghost's
_GUARD = 0.05                 # kept clear of the frame edge (its own feathered border), as a share of the short side


def margin_structure(rgb, prof=None):
    """{region: (fine, coarse)} object-scale structure in the margin of a platform-safe frame `rgb` (H x W x 3): the
    99.9th percentile of the two band-pass responses, computed on the margin only (bottom: under the frame past a guard;
    left/right: beside it)."""
    import numpy as np
    from scipy.ndimage import gaussian_filter
    import text_safe_qa as tsq
    prof = prof or tsq.safe_profile()
    H, W = rgb.shape[:2]
    k = prof["k"]
    x0, y0 = (1 - k) * W / 2, prof["y0"] * H
    x1, y1 = W - x0, y0 + k * H
    g = max(2, round(_GUARD * min(W, H)))
    yy, xx = np.mgrid[0:H, 0:W]
    margin = (xx < x0 - g / 2) | (xx > x1 + g / 2) | (yy > y1 + g)
    regions = {"bottom": (yy > y1 + g) & (yy < H - 8) & (xx > 8) & (xx < W - 8),
               "left": (xx < x0 - g / 2) & (xx > 8) & (yy > y0) & (yy < y1),
               "right": (xx > x1 + g / 2) & (xx < W - 8) & (yy > y0) & (yy < y1)}
    m = margin.astype(np.float64)
    nb = {s: gaussian_filter(m, s, mode="nearest") for s in (3, 12, 16, 48)}
    resp = []
    for c in range(3):
        ch = rgb[..., c].astype(np.float64) * m
        b = {s: gaussian_filter(ch, s, mode="nearest") / np.maximum(nb[s], 1e-3) for s in nb}
        resp.append((b[3] - b[16], b[12] - b[48]))
    out = {}
    for name, sel in regions.items():
        # only where the margin dominates every kernel's footprint: a blur half off the margin is an edge effect
        sel = sel & (nb[48] > 0.6)
        if sel.sum() < 100:
            continue
        out[name] = tuple(max(float(np.percentile(np.abs(r[i][sel]), 99.9)) for r in resp) for i in (0, 1))
    return out


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
    safe_film = _platform_safe(out_dir)
    seams_checked = 0
    for f in files:
        name = os.path.basename(f)
        try:
            im = Image.open(f)
            g = _gray(im)
        except Exception as e:
            warnings.append("%s: could not open (%s)" % (name, e)); lums.append(None); continue
        W, H = g.size
        if safe_film:
            import numpy as np
            import text_safe_qa as tsq
            if tsq.safe_applies(W, H):
                seams_checked += 1
                arr = np.asarray(im.convert("RGB"))
                for side, (step, at) in sorted(margin_seam(arr).items()):
                    if step > MARGIN_SEAM_WARN:
                        warnings.append(
                            "%s: the platform-safe frame's %s edge steps %.0f levels into the margin (at %dpx along "
                            "it; a continuation of the ground reads <= %d) — a panel edge, or the register's content "
                            "cut by the frame's dissolving edge (keep it off the register's outer 10%%). Look at the "
                            "frame's border (Film.tsx SafeEcho)" % (name, side, step, at, MARGIN_SEAM_WARN))
                for region, (fine, coarse) in sorted(margin_structure(arr).items()):
                    if max(fine, coarse) > MARGIN_STRUCTURE_WARN:
                        warnings.append(
                            "%s: the %s margin of the platform-safe frame holds object-scale structure (%.1f fine / "
                            "%.1f coarse; a ground reads <= %.0f) — a copy of the beat's content, a ghost, where only "
                            "its ground belongs (Film.tsx SafeEcho)" % (name, region, fine, coarse,
                                                                         MARGIN_STRUCTURE_WARN))
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
            # A WARNING, not a delivery ERROR. Measured against real cases this test is INVERTED: the three
            # registers whose type is genuinely cut by the canvas read 1.00%, 1.45% and 4.40% — all UNDER
            # this threshold — while four deliberately full-bleed registers read 9.6%, 12.7%, 14.1% and
            # 35.2% and were all blocked. It would also refuse 100% of the sampled frames of OpenAI's launch
            # film, 57% of Figma's and 57% of Anthropic's, while passing all 30 frames of a film that
            # measured as inert. Coverage runs OPPOSITE to the defect (a cut word is a thin band; a flood is
            # a solid field), so no threshold fixes it. `text_safe_qa.py` asks the DOM instead, exactly.
            # What this number still reports honestly is that the shot floods its border — worth seeing,
            # never worth blocking a technique for.
            warnings.append("%s: %.1f%% of the safe border carries content. If that is a full-bleed field or "
                            "flood it is FINE (this measure cannot tell them apart — see text_safe_qa.py, "
                            "which asks the DOM whether any TYPE is actually cut)" % (name, frac * 100))
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

    if safe_film and not seams_checked:
        warnings.append("the film is platform-safe but no keyframe is a full-screen vertical frame — the margin seam "
                        "was NOT measured")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": len(files), "lums": lums,
            "margin_seams_checked": seams_checked}


def _platform_safe(out_dir):
    """Whether this film renders with the platform-safe profile (render_remotion.safe_zone: a 9:16 remotion film
    unless meta.safe_zone is "none"). No board, or another tier: False."""
    try:
        meta = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {}
    except (OSError, ValueError):
        return False
    if meta.get("renderer") != "remotion" or meta.get("safe_zone", "social") in (None, "", "none", False):
        return False
    return meta.get("aspect") == "9:16"


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
    print("[frame_safe_qa] %s  %d scene(s), %d error(s), %d warning(s)%s"
          % ("OK" if r["ok"] else "FAIL", r["scenes"], len(r["errors"]), len(r["warnings"]),
             "; margin seam measured on %d keyframe(s)" % r["margin_seams_checked"]
             if r.get("margin_seams_checked") else ""))
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
