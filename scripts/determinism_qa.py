#!/usr/bin/env python3
"""DETERMINISM — does a composition draw the same frame however, and whenever, it is asked for it?

    python3 scripts/determinism_qa.py <CompositionId> [--props JSON|FILE] [--range M-N] [--aspect 16:9]
                                      [--layer NAME=JSONPATCH ...] [--scale 0.5] [--json]
    python3 scripts/determinism_qa.py --film <out_dir> [--range M-N] ...      # a film's own .remotion-props.json

WHY THIS EXISTS. A Remotion composition is meant to be a pure function of the frame: that contract is why it
can render frames in parallel tabs, and why the per-beat cache (remotion_segments.py) can join a film from
segments rendered hours apart. Every effect that keeps STATE breaks it silently — and the eye cannot see it,
because each frame on its own looks fine. Measured in the effects research (2026-10-24): a Canvas2D layer that
left `globalCompositeOperation` set between frames made 29 of 30 frames depend on render ORDER; HtmlInCanvas
over CSS 3D was not byte-identical between renders; angle vs swangle differ by up to 10/255 on a gradient. None
of that shows in a still. It shows as a flicker at a segment boundary, or a beat that changes when re-rendered.

WHAT IT ASKS, of the same frames M..N, on the film's own GL backend (remotion_segments.default_gl):
  twice        concurrency 1, rendered twice                 — is it repeatable at all?
  concurrency  concurrency 1 vs 3                            — does a frame depend on which tab drew it?
  cold         frame N alone (a fresh tab) vs frame N after M..N-1 in one tab — does it carry state forward?

THE FLOOR: a frame FAILS when more than 0.01% of its pixels differ by more than 2/255 in any channel. The
effects research measured concurrency 1 vs 3 at <=2/255 on <=0.003% of the pixels for compositions that ARE
deterministic (JPEG-free PNG frames, Chrome's own rasterisation noise), so the floor sits above that noise and
far below the 10/255 a backend change makes.

WHICH LAYER. A failure names the comparison and the frame, the worst difference and where it sits (the bounding
box of the differing pixels), and — when `--layer` toggles are given, or for a film, where the built-in ones are
used — re-runs the failing comparison with each layer switched off in turn and names the layer whose removal
makes the frames agree. A `--layer` is `name=JSON` merged into the props (a dotted key reaches into an object):
    --layer optic='{"optic": null}'   --layer finish='{"dna.finish": "none"}'   --layer dither='{"dither": false}'

ADVISORY for a new register (register_shot.py says so): run it on the register's composition before the
register ships anything that keeps state — a canvas, a WebGL context, a module-level cache.
Exit status: 0 every comparison within the floor, 1 a failure, 2 the tool could not run.
"""
import argparse
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REMOTION = os.path.join(SKILL, "remotion")
sys.path.insert(0, HERE)

TOL = 2                 # /255 per channel — above the measured rasterisation noise of a deterministic composition
MAX_FRAC = 0.0001       # 0.01% of the frame's pixels may exceed TOL before the frame fails
CONC_B = 3              # the second concurrency asked for (the research measured 1 vs 3)

# The film's own optional layers, in the order they are suspected: the delivery dither and the finish are
# film-wide overlays; `optics: false` switches every beat's optic off (Film.tsx); `captions` is the HUD.
FILM_LAYERS = [("optics", {"optics": False}), ("dither", {"dither": False}), ("finish", {"dna.finish": "none"}),
               ("captions", {"captions": False})]


class ToolError(RuntimeError):
    pass


def _patch(props, patch):
    """`props` with `patch` merged in; a dotted key reaches into an object (a missing parent is created)."""
    out = copy.deepcopy(props)
    for key, val in patch.items():
        parts = key.split(".")
        cur = out
        for p in parts[:-1]:
            if not isinstance(cur.get(p), dict):
                # a DNA given as a preset NAME has no fields to reach into: expand it to an object that names it
                cur[p] = {"id": cur[p]} if isinstance(cur.get(p), str) else {}
            cur = cur[p]
        if val is None:
            cur.pop(parts[-1], None)
        else:
            cur[parts[-1]] = val
    return out


def _run(cmd, what):
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        raise ToolError("%s failed (exit %d): %s" % (what, r.returncode, (r.stdout + r.stderr)[-1200:]))
    return r


class Renderer:
    """One bundle, many renders of it — every render on the SAME named GL backend."""

    def __init__(self, comp, public_dir, gl, scale, work):
        self.comp, self.gl, self.scale, self.work = comp, gl, scale, work
        self.serve = os.path.join(work, "bundle")
        cmd = ["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + self.serve, "--log=error"]
        if public_dir:
            cmd.append("--public-dir=" + os.path.abspath(public_dir))
        _run(cmd, "remotion bundle")
        self.n = 0

    def _props_file(self, props):
        self.n += 1
        p = os.path.join(self.work, "props_%d.json" % self.n)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(props, fh, ensure_ascii=False)
        return p

    def sequence(self, props, a, b, conc):
        """{frame: png path} for frames a..b rendered in order at `conc` tabs."""
        self.n += 1
        out = os.path.join(self.work, "seq_%d" % self.n)
        os.makedirs(out)
        _run(["npx", "remotion", "render", self.serve, self.comp, out, "--sequence", "--image-format=png",
              "--frames=%d-%d" % (a, b), "--concurrency=%d" % conc, "--gl=" + self.gl, "--scale=%s" % self.scale,
              "--props=" + self._props_file(props), "--log=error"], "render %s %d-%d @%d" % (self.comp, a, b, conc))
        files = sorted(glob.glob(os.path.join(out, "*.png")))
        if len(files) != b - a + 1:
            raise ToolError("asked for %d frames (%d-%d), the sequence wrote %d" % (b - a + 1, a, b, len(files)))
        return {a + i: f for i, f in enumerate(files)}

    def still(self, props, f):
        self.n += 1
        out = os.path.join(self.work, "still_%d.png" % self.n)
        _run(["npx", "remotion", "still", self.serve, self.comp, out, "--frame=%d" % f, "--image-format=png",
              "--gl=" + self.gl, "--scale=%s" % self.scale, "--props=" + self._props_file(props), "--log=error"],
             "still %s frame %d" % (self.comp, f))
        return out


def diff(pa, pb):
    """{max, frac, bbox} of the per-pixel max-channel difference between two PNGs, over TOL."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(pa).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(pb).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        raise ToolError("frames of different size: %s vs %s" % (a.shape, b.shape))
    d = np.abs(a - b).max(axis=2)
    over = d > TOL
    frac = float(over.mean())
    box = None
    if over.any():
        ys, xs = np.nonzero(over)
        box = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return {"max": int(d.max()), "frac": frac, "bbox": box, "fail": frac > MAX_FRAC}


def ask(r, props, a, b, which=("twice", "concurrency", "cold")):
    """[{test, frame, max, frac, bbox, fail}] — the three questions over frames a..b."""
    base = r.sequence(props, a, b, 1)
    out = []
    if "twice" in which:
        again = r.sequence(props, a, b, 1)
        out += [dict(diff(base[f], again[f]), test="twice", frame=f) for f in range(a, b + 1)]
    if "concurrency" in which:
        par = r.sequence(props, a, b, CONC_B)
        out += [dict(diff(base[f], par[f]), test="concurrency", frame=f) for f in range(a, b + 1)]
    if "cold" in which:
        out.append(dict(diff(base[b], r.still(props, b)), test="cold", frame=b))
    return out


def attribute(r, props, a, b, failed, layers):
    """For each failing test, the first layer whose removal makes every one of its frames agree."""
    blame = {}
    for test in sorted({x["test"] for x in failed}):
        blame[test] = None
        for name, patch in layers:
            res = ask(r, _patch(props, patch), a, b, which=(test,))
            if not any(x["fail"] for x in res):
                blame[test] = name
                break
    return blame


def run(comp, props, a, b, public_dir=None, layers=(), scale=1, gl=None):
    """The whole check. Returns the report dict (`ok`, `results`, `blame`)."""
    import remotion_segments as rs
    gl = gl or rs.default_gl()
    work = tempfile.mkdtemp(prefix="determinism_qa_")
    try:
        r = Renderer(comp, public_dir, gl, scale, work)
        results = ask(r, props, a, b)
        failed = [x for x in results if x["fail"]]
        blame = attribute(r, props, a, b, failed, list(layers)) if failed and layers else {}
        return {"composition": comp, "frames": [a, b], "gl": gl, "scale": scale, "tol": TOL, "max_frac": MAX_FRAC,
                "ok": not failed, "results": results, "blame": blame}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _load_props(arg):
    if not arg:
        return {}
    if os.path.isfile(arg):
        with open(arg, encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(arg)


def _range(arg, default):
    if not arg:
        return default
    a, b = (int(x) for x in arg.split("-"))
    if not 0 <= a < b:
        raise SystemExit("--range must be M-N with 0 <= M < N (got %r): the cold test asks for N after M..N-1" % arg)
    return a, b


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("composition", nargs="?", help="a composition id (a register, a probe, or Film)")
    ap.add_argument("--film", help="a film's out_dir: renders its Film from .remotion-props.json")
    ap.add_argument("--props", help="JSON or a JSON file")
    ap.add_argument("--range", help="frames M-N (default: six frames from the middle of the composition)")
    ap.add_argument("--aspect", help="16:9 | 9:16 | 1:1 | 4:5 | 4:3")
    ap.add_argument("--layer", action="append", default=[], help="name=JSON props patch that switches one layer off")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if bool(a.composition) == bool(a.film):
        ap.error("name a composition OR --film <out_dir>")
    layers = []
    for spec in a.layer:
        name, _, patch = spec.partition("=")
        layers.append((name, json.loads(patch)))
    public = None
    if a.film:
        comp = "Film"
        pf = os.path.join(a.film, ".remotion-props.json")
        if not os.path.isfile(pf):
            raise SystemExit("%s has no .remotion-props.json — render the film once (render_remotion.py)" % a.film)
        props = _load_props(pf)
        public = a.film
        layers = layers or FILM_LAYERS
        sys.path.insert(0, HERE)
        import remotion_segments as rs
        total = rs.timeline(props.get("scenes") or [], rs.seam_frames())[1]
        default = (max(0, total // 2 - 5), max(1, total // 2))
    else:
        comp = a.composition
        props = _load_props(a.props)
        default = (40, 45)
    if a.aspect:
        props["aspect"] = a.aspect
    lo, hi = _range(a.range, default)
    try:
        rep = run(comp, props, lo, hi, public_dir=public, layers=layers, scale=a.scale)
    except ToolError as e:
        print("[determinism_qa] could not run: %s" % e, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        bad = [x for x in rep["results"] if x["fail"]]
        worst = max(rep["results"], key=lambda x: (x["frac"], x["max"]))
        print("[determinism_qa] %s frames %d-%d on --gl=%s: %d comparison(s), %d over the floor (>%d/255 on >%.2f%% "
              "of pixels); worst %s frame %d: max %d/255 on %.4f%%"
              % (comp, lo, hi, rep["gl"], len(rep["results"]), len(bad), TOL, MAX_FRAC * 100, worst["test"],
                 worst["frame"], worst["max"], worst["frac"] * 100))
        for x in bad:
            print("  FAIL %-11s frame %d: max %d/255, %.4f%% of pixels over %d, in box %s"
                  % (x["test"], x["frame"], x["max"], x["frac"] * 100, TOL, x["bbox"]))
        for test, layer in rep["blame"].items():
            print("  %s: %s" % (test, ("switching off the %r layer makes it agree" % layer) if layer
                                else "no single layer toggle makes it agree — it is in the composition itself"))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
