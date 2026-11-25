#!/usr/bin/env python3
"""blender_clip — a 3D clip rendered by Blender for a director-path film (SKILL.md step 6, the kit).

    python3 scripts/blender_clip.py <film_dir> <scene.py> --seconds S [--name N] [--fps 30] [--size 1920x1080]
                                    [--engine eevee|cycles] [--samples 64] [--env] [--params '{...}'] [--still F]
    python3 scripts/blender_clip.py <film_dir> <scene.py> --glb [--ao 2048] [--name N]   # a model for Stage3D.glb

The scene script uses the plate scene API (references/blender-plates.md "The scene-script API"): `build(k)` returns
{"objects": {...}, "anchors": {...}} and `pose(k, t)` sets the scene at t seconds; it may import the kit
(blender/kit: materials, studio lights, the HDRI, stage placement). This renders it with blender/runner.py, every
frame whole, into <film_dir>/clips/<name>/rgba/NNNN.png (with alpha unless --env), and writes a viewable
<film_dir>/clips/<name>.mp4. A page places the clip by drawing frame N at its time, so the film stays a pure
function of time. --still F renders one frame to <film_dir>/clips/<name>/still_NNNN.png to look at first.
--glb exports the built objects (posed at t=0) to <film_dir>/models/<name>.glb for the page's three.js stage instead
of rendering (blender/kit/glb.py: sheen kept right; --ao R bakes Cycles ambient occlusion into a second UV set,
<name>_ao.png, which Stage3D.glb applies). Use it when the camera or the story must move in the page around an object
Blender models best (references/3d-engines.md).

WHY. blender_plate.py builds plates from a classic storyboard's slide.blender; a film the director builds as one
page has no storyboard. This is the same runner and kit through a door that needs none.
Exit 0 on success, 1 when Blender fails (its log tail is printed), 2 on a usage error.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RUNNER = os.path.join(os.path.dirname(HERE), "blender", "runner.py")


def command(blender, scene, out, frames, fps, w, h, engine, samples, env, params, still=None, screen=None, glb=None, ao=0):
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python", RUNNER, "--",
           "--scene", os.path.abspath(scene), "--out", out, "--frames", str(frames), "--fps", str(fps),
           "--w", str(w), "--h", str(h), "--engine", engine, "--samples", str(samples),
           "--mode", "env" if env else "rgba", "--no-reuse", "--params", params]
    if still:
        cmd += ["--still", str(still)]
    if screen:
        cmd += ["--screen", os.path.abspath(screen)]   # a device scene's screen: one picture per frame
    if glb:
        cmd += ["--glb", glb, "--ao", str(int(ao))]
    return cmd


def main(argv):
    ap = argparse.ArgumentParser(description="render a Blender scene as a clip for a director-path film")
    ap.add_argument("film_dir")
    ap.add_argument("scene")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--glb", action="store_true", help="export a .glb for Stage3D.glb instead of rendering")
    ap.add_argument("--ao", type=int, default=0, help="with --glb: bake AO at this size (2048 or 4096)")
    ap.add_argument("--name")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--env", action="store_true", help="opaque: the scene draws its own ground")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--still", type=int)
    ap.add_argument("--screen", help="a folder of pictures a device's screen plays (blender/kit/scenes/laptop_screen.py)")
    a = ap.parse_args(argv)
    if a.seconds is None and not a.glb:
        ap.print_usage(sys.stderr)
        print("blender_clip: --seconds is required (or --glb)", file=sys.stderr)
        return 2
    if a.ao and not a.glb:
        print("blender_clip: --ao goes with --glb", file=sys.stderr)
        return 2
    import blender_plate
    blender = blender_plate.blender_bin()
    if not blender:
        print("blender_clip: no Blender found (install Blender 5, or set TTV_BLENDER)", file=sys.stderr)
        return 2
    if not os.path.isfile(a.scene):
        print("blender_clip: no scene script at %s" % a.scene, file=sys.stderr)
        return 2
    try:
        w, h = (int(v) for v in a.size.lower().split("x"))
        json.loads(a.params)
    except ValueError as e:
        print("blender_clip: bad --size or --params: %s" % e, file=sys.stderr)
        return 2
    name = a.name or os.path.splitext(os.path.basename(a.scene))[0]
    if a.glb:
        glb = os.path.join(os.path.abspath(a.film_dir), "models", name + ".glb")
        os.makedirs(os.path.dirname(glb), exist_ok=True)
        cmd = command(blender, a.scene, os.path.dirname(glb), 1, a.fps, 64, 64, "eevee", 1, False, a.params,
                      glb=glb, ao=a.ao)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or "RUNNER-DONE" not in r.stdout or not os.path.isfile(glb):
            print("blender_clip: Blender failed (exit %d)\n%s" % (r.returncode, "\n".join((r.stdout + r.stderr).splitlines()[-30:])),
                  file=sys.stderr)
            return 1
        print("[blender_clip] model -> %s%s" % (glb, " (+ %s_ao.png)" % glb[:-4] if a.ao else ""))
        return 0
    out = os.path.join(os.path.abspath(a.film_dir), "clips", name)
    os.makedirs(out, exist_ok=True)
    frames = max(1, int(round(a.seconds * a.fps)))
    cmd = command(blender, a.scene, out, frames, a.fps, w, h, a.engine, a.samples, a.env, a.params, a.still, a.screen)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or "RUNNER-DONE" not in r.stdout:
        print("blender_clip: Blender failed (exit %d)\n%s" % (r.returncode, "\n".join((r.stdout + r.stderr).splitlines()[-30:])),
              file=sys.stderr)
        return 1
    if a.still:
        print("[blender_clip] still -> %s" % os.path.join(out, "still_%04d.png" % a.still))
        return 0
    pngs = sorted(glob.glob(os.path.join(out, "rgba", "*.png")))
    if len(pngs) != frames:
        print("blender_clip: expected %d frames, found %d in %s" % (frames, len(pngs), os.path.join(out, "rgba")),
              file=sys.stderr)
        return 1
    mp4 = os.path.join(os.path.abspath(a.film_dir), "clips", name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", os.path.join(out, "rgba", "%04d.png"),
                    "-filter_complex", "color=black:s=%dx%d[b];[b][0:v]overlay=shortest=1,format=yuv420p" % (w, h),
                    "-c:v", "libx264", "-crf", "16", mp4], check=True)
    print("[blender_clip] %d frames -> %s (alpha PNGs) and %s (preview over black)" % (frames, os.path.join(out, "rgba"), mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
