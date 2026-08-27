#!/usr/bin/env python3
"""The caption band, read from the ONE place that defines it: `remotion/src/runtime/layout.ts`.

WHY THIS FILE EXISTS. The height of the bottom strip a film reserves for its burned caption was a literal in
four places — `runtime/layout.ts` (150), `Film.tsx` (150), `frame_safe_qa.py` (0.135 of H = 146px) and
`shot_still_qa.py` (200/150) — and nothing made them agree. They were consistent only by coincidence, and the
coincidence ended the moment the caption's type size changed: the renderer reserved a taller band while both
gates went on measuring the old one, so a shot's label could sit in the new band, overlap the caption, and
still pass. A duplicated constant is not a constant; it is a bug with a delay.

The TypeScript is the definition because the renderer is what actually draws the band. This module parses the
fractions out of it, so a change there reaches the Python gates without anyone remembering to copy it.
"""
import os
import re

_LAYOUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "remotion", "src", "runtime", "layout.ts")

_KEYS = ("CAPTION_SIZE_FRAC", "CAPTION_LINES", "CAPTION_LEAD",
         "CAPTION_MARGIN_FRAC", "CAPTION_GAP_FRAC")

_ROOT_TSX = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "remotion", "src", "Root.tsx")


def aspect_wh(aspect=None):
    """Frame dimensions for a `meta.aspect`, read from Root.tsx's ASPECTS — the renderer's own table.

    Restating it here is how the caption band got four disagreeing copies. One definition, parsed.
    """
    src = open(_ROOT_TSX, encoding="utf-8").read()
    m = re.search(r"const ASPECTS[^{]*\{(.*?)\}", src, re.S)
    if not m:
        raise RuntimeError("ASPECTS not found in %s — it defines the frame sizes and is read here" % _ROOT_TSX)
    table = {k: (int(w), int(h))
             for k, w, h in re.findall(r"'([^']+)':\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]", m.group(1))}
    return table.get(str(aspect or "16:9"), table.get("16:9", (1920, 1080)))


def _fracs(path=None):
    src = open(path or _LAYOUT, encoding="utf-8").read()
    out = {}
    for k in _KEYS:
        m = re.search(r"\b%s\s*=\s*([0-9.]+)" % k, src)
        if not m:
            # Fail LOUDLY. A missing key used to mean a silent fallback to the old literal, which is the exact
            # failure this module exists to prevent — the gates would go green against a band nobody draws.
            raise RuntimeError(
                "%s not found in %s — the caption band is defined there and read here; "
                "if it was renamed, update scripts/_caption_band.py in the same change." % (k, _LAYOUT))
        out[k] = float(m.group(1))
    return out


def caption_size_px(w, h):
    """The caption's own type size at this frame — sized off the NARROW dimension, like the renderer."""
    return int(round(min(w, h) * _fracs()["CAPTION_SIZE_FRAC"]))


def caption_band_px(w, h):
    """The reserved band, mirroring `captionBand(W, H)` in runtime/layout.ts.

    A narrow frame (portrait / square / 4:5) wraps the same sentence to one more line, so it reserves one
    more line's worth of height — the same rule the TS applies.
    """
    f = _fracs()
    lines = f["CAPTION_LINES"] + (1 if w < 1400 else 0)
    return int(round(min(w, h) * (f["CAPTION_SIZE_FRAC"] * f["CAPTION_LEAD"] * lines
                                  + f["CAPTION_MARGIN_FRAC"] + f["CAPTION_GAP_FRAC"])))


if __name__ == "__main__":
    for w, h in [(1920, 1080), (1080, 1920), (1080, 1080), (1080, 1350)]:
        print("%dx%-6d caption %dpx  band %dpx (%.1f%% of H)"
              % (w, h, caption_size_px(w, h), caption_band_px(w, h),
                 caption_band_px(w, h) / h * 100))
