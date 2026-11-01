#!/usr/bin/env python3
"""Which real device a screenshot came from — read off its pixel size, never guessed from its look.

deviceSpec.json `models` holds Apple's published pixels for each model (apple.com tech-spec pages, sources and
dates beside every entry). A capture taken on a device is exactly its native pixels — 416x496 on a 46 mm Apple
Watch Series 12, 1206x2622 on a 6.3-inch iPhone — or those divided by the model's point scale (a capture saved at
1x). A full-page capture is the native WIDTH and taller than the screen: it scrolls. Anything else matches no
model and is drawn on its generic kind, with a warning that names the size.

    python3 scripts/device_models.py <image> [...]     # what each capture would be drawn as
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import device_script as ds          # noqa: E402


def models():
    return {k: v for k, v in ds.SPEC["models"].items() if not k.startswith("_")}


def _kind_of(device):
    return "tablet" if device == "tablet-landscape" else device


SHAPE_TOLERANCE = 0.0015   # relative: a resize keeps the ratio to its rounding (0.03-0.08% measured); a DIFFERENT device is 0.4%+ off (iPhone 13 vs 18 Pro Max)


def by_shape(w, h, kind=None):
    """The model (of `kind`, when given) whose screen is this capture's SHAPE within SHAPE_TOLERANCE, the closest
    first and, among equals, the larger screen — or None. For a capture that is no model's native pixels."""
    if not (isinstance(w, int) and isinstance(h, int)) or w <= 0 or h <= 0:
        return None
    best = None
    for name, m in models().items():
        if kind and m["kind"] != kind:
            continue
        pw, ph = m["published"]["px"]
        shapes = [(pw, ph)] + ([(ph, pw)] if m["kind"] in ("tablet", "laptop") else [])
        for a, b in shapes:
            err = abs((w / float(h)) / (a / float(b)) - 1)
            if err <= SHAPE_TOLERANCE:
                key = (round(err, 4), -a * b)
                if best is None or key < best[0]:
                    best = (key, name)
    return best[1] if best else None


def candidates(w, h, device=None):
    """[(model, how)] in table order — every model whose screen this w x h capture is. `how` is "native",
    "1/k" (saved at 1/k of its pixels) or "long" (the native width, taller: a scrolling capture). A tablet and a
    laptop match either orientation of their pixels; `device` (a kind) keeps only that kind's models."""
    out = []
    if not (isinstance(w, int) and isinstance(h, int)) or w <= 0 or h <= 0:
        return out
    want = _kind_of(device) if device else None
    for name, m in models().items():
        if want and m["kind"] != want:
            continue
        pw, ph = m["published"]["px"]
        sizes = [(pw, ph)] + ([(ph, pw)] if m["kind"] in ("tablet", "laptop") else [])
        hit = None
        for (a, b) in sizes:
            if (w, h) == (a, b):
                hit = "native"
            else:
                for k in m.get("scale") or []:
                    if (w * k, h * k) == (a, b):
                        hit = "1/%d" % k
                        break
            widths = [a] + [a // k for k in m.get("scale") or [] if a % k == 0]
            tall = h / float(w) > (b / float(a)) * (1 + float(ds.SPEC["aspectTolerance"]))
            if not hit and m["kind"] in ("phone", "watch", "tablet") and a < b and w in widths and tall:
                hit = "long"
            if hit:
                break
        if hit:
            out.append((name, hit))
    return out


def kind_for(model, w, h):
    """The device kind a model is drawn as for a w x h capture: a tablet held the way the capture was taken."""
    k = models()[model]["kind"]
    if k == "tablet" and w > h:
        return "tablet-landscape"
    return k


def describe(model):
    m = models()[model]
    return "%s (%dx%d px, %s)" % (m["name"], m["published"]["px"][0], m["published"]["px"][1], m["source"])


def main(argv):
    from PIL import Image
    if not argv:
        sys.exit("usage: device_models.py <image> [...] — the real device each capture would be drawn as")
    for p in argv:
        with Image.open(p) as im:
            w, h = im.size
        c = candidates(w, h)
        print("%s  %dx%d  %s" % (os.path.basename(p), w, h,
                                 "; ".join("%s [%s]" % (n, how) for n, how in c) if c else "no model — generic kind"))


if __name__ == "__main__":
    main(sys.argv[1:])
