"""Colours as a scene script writes them (#rrggbb) turned into what Blender's nodes take (linear RGBA)."""


def hexc(h, a=1.0):
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError("a colour is #rrggbb, got %r" % h)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (a,)
