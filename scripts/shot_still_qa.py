#!/usr/bin/env python3
"""Frame-craft QA for ONE shot's still(s) — the per-shot analogue of frame_safe_qa.

Why this exists: the frame-craft floor (action-safe border, a clean caption zone) was only ever measured on
a FINISHED film's keyframes. Authoring or fixing a shot therefore had no way to check its own work short of
rendering the whole film, so shots shipped with content sliced by the frame edge or parked under the burned
subtitle and the defect surfaced a render-hour later.

Usage:
  python3 scripts/shot_still_qa.py a.png b.png ...        # exits non-zero on any violation

RUN IT ON A SHOT STILL, NOT ON A DELIVERED KEYFRAME. A film's _keyframes/ have the narration caption
already BURNED INTO the band, so the caption measure counts the subtitle itself and reports a collision
that is not there (measured: a long CJK subtitle alone scores 5.2%, and 13.7% over a gradient ground).
That is what frame_safe_qa.py excludes the band for. This script warns if you point it at a keyframe.

Per still it reports:
  edge      %% of the action-safe border (top/left/right, EBU R95 3.5%%) that is bright content.
            >4.5%% means something is running OFF-FRAME.  [same rule + constants as frame_safe_qa.py]
  caption   %% of the burned-caption band (the bottom band the renderer draws the subtitle on) that is
            content ink. The band must be the frame's OWN clean ground: a shot that puts a panel, a label
            or an image there collides with the subtitle. >5%% is a violation.
Both are measured against the frame's own ground, so a light shot and a dark shot are judged the same way.
"""
import statistics
import sys

MARGIN = 0.035          # action-safe outer border fraction (EBU R95) — frame_safe_qa.py
EDGE_FRAC_ERR = 0.045   # >this fraction of the border being content = OFF-FRAME
CAPTION_FRAC_ERR = 0.05  # >this fraction of the caption band being ink = it collides with the subtitle
# Calibrated on real frames: clean shots measure 3.7-4.0%, a shot whose panel labels sit in the band
# measures 6.0%, a shot whose hero panel fills it measures 40%.
_INK_DELTA = 34         # a pixel this far from the band's own ground counts as ink
_EDGE_DELTA = 60        # same idea for the action-safe border (frame_safe_qa.INK_DELTA)
_BAND_EDGE_STEP = 28    # a luminance step this hard at the band's top edge is a PANEL, not a gradient


def _caption_band_px(w, h):
    """The bottom band the renderer reserves for the burned caption — runtime/layout.ts captionBand()."""
    return 200 if w < 1400 else 150


def _ground_luma(px, w, h, step=6):
    """The frame's own dominant luminance — its GROUND."""
    hist = {}
    for y in range(0, h, step):
        for x in range(0, w, step):
            k = px[x, y] // 8
            hist[k] = hist.get(k, 0) + 1
    return (max(hist, key=hist.get) * 8 + 4) if hist else 0


def measure(path):
    from PIL import Image
    g = Image.open(path).convert("L")
    w, h = g.size
    px = g.load()
    ground_all = _ground_luma(px, w, h)
    m = max(1, int(round(min(w, h) * MARGIN)))
    band = _caption_band_px(w, h)
    cap_top = h - band

    bright = tot = 0
    for y in range(0, m, 2):                                  # top strip, full width
        for x in range(0, w, 2):
            tot += 1
            bright += abs(px[x, y] - ground_all) > _EDGE_DELTA
    for y in range(m, cap_top, 2):                            # left + right strips, above the caption band
        for x in list(range(0, m, 2)) + list(range(w - m, w, 2)):
            tot += 1
            bright += abs(px[x, y] - ground_all) > _EDGE_DELTA
    edge = bright / max(1, tot)

    # The band's OWN ground = its modal luminance; ink is whatever departs from it. Measuring against the
    # ground (not an absolute threshold) is what makes this work on a light shot as well as a dark one.
    hist = {}
    vals = []
    for y in range(cap_top, h, 2):
        for x in range(0, w, 2):
            v = px[x, y]
            vals.append(v)
            hist[v // 8] = hist.get(v // 8, 0) + 1
    band_ground = max(hist, key=hist.get) * 8 + 4 if hist else 0
    # INVERSION GUARD. Taking the band's OWN modal luminance as its ground is what makes this work on a
    # light shot and a dark one — but it also means a panel that covers the WHOLE band BECOMES the ground,
    # and the worst possible violation measured 0.0% while a half-covered band measured 50%. If the band's
    # ground is not the FRAME's ground, the band is not the frame's clean background at all.
    # A band whose ground differs from the frame's is EITHER covered by a panel OR simply a different
    # tone — a vertical gradient, a two-tone ground, a lower plate. The first inversion fix could not tell
    # them apart and returned 1.0 for both, so a legitimate gradient became a blocking error. Structure is
    # what separates them: content has edges, a ground does not.
    # Distinguishing the two took three tries, and the discriminant is the band's TOP EDGE, not its
    # flatness: a different-toned GROUND (a vertical gradient, a two-tone plate) arrives gradually, while
    # a panel laid over the band has a hard step where it starts. Flatness alone said a flat panel was a
    # ground; treating any tone difference as coverage said a gradient was a panel. Both were wrong in
    # opposite directions and each produced a confident number.
    above = [px[x, max(0, cap_top - 6)] for x in range(0, w, 4)]
    below = [px[x, min(h - 1, cap_top + 6)] for x in range(0, w, 4)]
    edge_step = abs((sum(above) / max(1, len(above))) - (sum(below) / max(1, len(below))))
    if abs(band_ground - ground_all) > _INK_DELTA and edge_step > _BAND_EDGE_STEP:
        caption = 1.0
    else:
        ink = sum(1 for v in vals if abs(v - band_ground) > _INK_DELTA)
        caption = ink / max(1, len(vals))
    return {"w": w, "h": h, "edge": edge, "caption": caption, "band": band}


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    bad = 0
    if any("_keyframes" in p for p in argv):
        print("[shot_still_qa] WARNING: these look like delivered keyframes — the caption is already burned\n"
              "                into the band, so caption-band ink is NOT meaningful here. Render the shot on\n"
              "                its own (npx remotion still ...) and measure that instead.")
    for p in argv:
        try:
            r = measure(p)
        except Exception as e:                                # noqa: BLE001 — report, never mask
            print("[shot_still_qa] %-40s could not read (%s)" % (p, e))
            bad += 1
            continue
        flags = []
        if r["edge"] > EDGE_FRAC_ERR:
            flags.append("OFF-FRAME (inset the shot's edge elements)")
        if r["caption"] > CAPTION_FRAC_ERR:
            flags.append("CONTENT IN THE CAPTION BAND (the subtitle will sit on it)")
        print("[shot_still_qa] %-44s %dx%d  edge=%.1f%%  caption-band ink=%.1f%% (band %dpx)  %s"
              % (p.split("/")[-1], r["w"], r["h"], r["edge"] * 100, r["caption"] * 100, r["band"],
                 "FAIL: " + "; ".join(flags) if flags else "OK"))
        bad += bool(flags)
    print("[shot_still_qa] %d still(s), %d violation(s)" % (len(argv), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
