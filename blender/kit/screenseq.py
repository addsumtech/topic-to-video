"""A device's screen as a picture sequence: which picture a beat frame shows, and how far the camera stretches it.
Pure Python (no bpy), so scripts/blender_plate.py and the tests use the same arithmetic the runner does."""
import math
import os


def frames_in(folder):
    """The sequence's pictures, in order (Remotion writes element-000.png …)."""
    if not folder or not os.path.isdir(folder):
        return []
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(".png")]


def index(frame, frames, n):
    """The picture (0-based) a beat's frame (1-based, of `frames`) shows, from a sequence of `n`: one for one when the
    sequence was rendered on the beat's clock (holdFrames), by time when it was not; held on the last past the end."""
    if n < 1 or frames < 1:
        raise ValueError("a screen needs at least one picture and a beat at least one frame")
    if n == frames:
        return max(0, min(n - 1, int(frame) - 1))
    t = (int(frame) - 1) / max(1, frames - 1)
    return max(0, min(n - 1, int(round(t * (n - 1)))))


def magnification(corners, px):
    """How many frame pixels one screen pixel is drawn across: the screen's projected edges (corners in frame pixels,
    in order round the quad) over its own pixels, the larger of its two directions. Above ~1.25 the interface is
    stretched past its own resolution (the film's media_res_qa bound) and reads soft."""
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = corners
    top, bottom = math.hypot(bx - ax, by - ay), math.hypot(cx - dx, cy - dy)
    left, right = math.hypot(dx - ax, dy - ay), math.hypot(cx - bx, cy - by)
    return max(max(top, bottom) / float(px[0]), max(left, right) / float(px[1]))
