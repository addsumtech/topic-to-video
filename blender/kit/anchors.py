"""Named 3D points as pixels, per frame, so the Remotion overlay stays ON the thing it names while the camera moves."""
import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def project(sc, cam, p):
    """[x, y, depth, visible] in frame pixels (y down). Not visible behind the camera, outside the frame, or with
    geometry between it and the lens."""
    v = world_to_camera_view(sc, cam, Vector(p))
    w = sc.render.resolution_x * sc.render.resolution_percentage / 100
    h = sc.render.resolution_y * sc.render.resolution_percentage / 100
    x, y, depth = v.x * w, (1 - v.y) * h, v.z
    vis = depth > 0 and 0 <= v.x <= 1 and 0 <= v.y <= 1
    if vis:
        origin = cam.matrix_world.translation
        d = Vector(p) - origin
        dist = d.length
        hit, loc, *_ = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, d.normalized(),
                                   distance=max(0.0, dist - max(1e-3, dist * 1e-4)))
        vis = not hit
    return [round(x, 2), round(y, 2), round(depth, 4), bool(vis)]


def sphere_limb_crossing(sc, cam, centre, radius, from_px, samples=4320):
    """Where a line from `from_px` toward a sphere's centre meets its visible limb, in pixels — the NEAR crossing.
    (The first plate took the max-cosine limb point, which is the FAR one of the two on that ray.)"""
    c = cam.matrix_world.translation
    centre = Vector(centre)
    u = c - centre
    d = u.length
    u.normalize()
    cc = centre + u * (radius * radius / d)
    rr = radius * math.sqrt(max(0.0, 1 - (radius / d) ** 2))
    a = u.orthogonal().normalized()
    b = u.cross(a)
    A = Vector(from_px[:2])
    C = Vector(project(sc, cam, centre)[:2])
    want = (C - A).normalized()
    best = None
    for k in range(samples):
        th = 2 * math.pi * k / samples
        P = Vector(project(sc, cam, cc + (a * math.cos(th) + b * math.sin(th)) * rr)[:2])
        dv = P - A
        if dv.length < 1 or dv.normalized().dot(want) < 0.999:
            continue
        if best is None or dv.length < best[0]:
            best = (dv.length, P)
    if best is None:
        raise RuntimeError("no limb crossing on the ray from %s toward the sphere's centre" % (from_px[:2],))
    return [round(best[1].x, 2), round(best[1].y, 2)]
