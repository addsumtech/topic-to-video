"""The style engine — the film's drawing style applied to what every register draws (runtime/style.tsx).

The pure parts (what an element IS, which ink outlines a fill, how a gradient is stepped) are asked in node. The
parts only a browser can answer — that an outline lands on a shape and never on a glyph, that a photograph keeps
its pixels — are asked of real renders, behind STYLE_RENDER=1 (run them under the render lock).
"""
import json
import os
import re
import subprocess
import tempfile

import numpy as np
import pytest
from PIL import Image

import _tsprobe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "remotion")
FILM = os.path.join(REMOTION, "src", "Film.tsx")
STYLE = os.path.join(REMOTION, "src", "runtime", "style.tsx")

needs_ts = pytest.mark.skipif(not _tsprobe.available(), reason="node/esbuild not available")
needs_render = pytest.mark.skipif(not os.environ.get("STYLE_RENDER"), reason="renders: set STYLE_RENDER=1 (under rlock)")

# A minimal Element-shaped object for classify(): tag, parent, attributes, text children.
_EL = """
const el = (tagName: string, parent: any = null, attrs: Record<string, string> = {}, text = '') => {
  const e: any = {tagName, parentElement: parent, getAttribute: (k: string) => (k in attrs ? attrs[k] : null),
    childNodes: text ? [{nodeType: 3, textContent: text}] : []};
  return e;
};
"""


def _ts(body):
    return _tsprobe.run_ts("import * as C from %s;\n%s" % (_tsprobe.mod("styleClassify.ts"), _EL), body)


@needs_ts
def test_svg_text_is_text():
    out = _ts("""
      const svg = el('svg'); const t = el('text', svg, {}, 'Hello'); const ts = el('tspan', t, {}, '你好');
      const fo = el('foreignObject', svg); const div = el('DIV', fo, {}, '图例');
      const span = el('SPAN', el('DIV'), {}, '标签');
      const path = el('path', svg);
      out.r = [C.classify(t), C.classify(ts), C.classify(div), C.classify(span), C.classify(path)];
    """)
    assert out["r"] == ["text", "text", "text", "text", "shape"]


@needs_ts
def test_caption_echo_image_canvas_are_named():
    out = _ts("""
      const cap = el('DIV', null, {'data-caption': '1'}); const capT = el('SPAN', cap, {}, 'caption');
      const echo = el('DIV', null, {'data-echo': 'margin'}); const inEcho = el('rect', el('svg', echo));
      out.r = [C.classify(capT), C.classify(inEcho), C.classify(el('IMG')), C.classify(el('image', el('svg'))),
               C.classify(el('CANVAS')), C.classify(el('DIV'))];
    """)
    assert out["r"] == ["caption", "echo", "image", "image", "canvas", "box"]


@needs_ts
def test_ink_outline_contrasts_on_dark_and_light_grounds():
    out = _tsprobe.run_ts(
        "import {inkFor} from %s; import {TERMINAL_DNA, EDITORIAL_DNA, contrastOf} from %s;"
        % (_tsprobe.mod("styleClassify.ts"), _tsprobe.mod("dna.tsx")),
        """
        out.a = contrastOf(inkFor('#f4d35e', TERMINAL_DNA), '#f4d35e');
        out.b = contrastOf(inkFor('#1b2a41', EDITORIAL_DNA), '#1b2a41');
        out.c = contrastOf(inkFor('rgb(128, 128, 128)', null), '#808080');
        out.d = contrastOf(inkFor('rgba(244, 211, 94, 0.5)', TERMINAL_DNA), '#f4d35e');
        """)
    for k in "abcd":
        assert out[k] >= 3.0, (k, out[k])


@needs_ts
def test_gradient_flattens_to_mean_and_cel_quantizes():
    out = _ts("""
      out.mean = C.meanColor('linear-gradient(90deg, rgb(0, 0, 0) 0%, rgb(200, 100, 50) 100%)');
      out.q2 = C.quantizeStops(['#000000', '#ffffff'], 2);
      out.q3 = C.quantizeStops(['#000000', '#ffffff'], 3);
      out.step = C.steppedGradient('linear-gradient(135deg, rgb(0, 0, 0) 0%, rgb(255, 255, 255) 100%)', 2);
      out.radial = C.steppedGradient('radial-gradient(circle at 50% 50%, rgb(10, 20, 30) 0%, rgba(0, 0, 0, 0) 70%)', 3);
      out.none = C.steppedGradient('none', 3);
    """)
    assert out["mean"] == "rgba(100, 50, 25, 1)"
    assert len(out["q2"]) == 2 and len(out["q3"]) == 3
    lum = [int(c[1:3], 16) for c in out["q3"]]
    assert lum == sorted(lum) and lum[0] < lum[1] < lum[2]
    s = out["step"]
    assert s.startswith("linear-gradient(135deg") and s.count("rgb") == 2
    assert "0% 50%" in s and "50% 100%" in s, s          # each band holds its colour to a hard edge at 50%
    assert out["radial"].startswith("radial-gradient(circle at 50% 50%")
    assert out["none"] is None


def test_style_mounts_on_both_register_paths():
    film = open(FILM, encoding="utf-8").read()
    # the plain path: the register's clock inside the style layer
    assert re.search(r"<StyleLayer beat=\{i\}>\s*<BeatClock warp=\{sc\.warp\}>\{C \? <C \{\.\.\.\(sc\.props \?\? \{\}\)\} /> : <Missing",
                     film), "the plain register path is not styled"
    # the platform-safe margin: the WHOLE echo inside a style layer, so its ground matches the beat's, and never a
    # style element between the echo's selectors and the register they hide (ECHO_GROUND_ONLY)
    assert re.search(r"<StyleLayer beat=\{i\}>\s*<SafeEcho ", film), "the platform-safe margin is not styled"
    echo = film[film.index("<SafeEcho shot="):film.index("</SafeEcho>")]
    assert "StyleLayer" not in echo, "a style element sits inside the echo, under its ground-only selectors"


def test_unstyled_film_tree_is_unchanged():
    src = open(STYLE, encoding="utf-8").read()
    assert re.search(r"if \(!spec\) return <>\{children\}</>;", src), "with no style the layer is no longer its children"


def _render(comp, props, frame, out_png, public=None):
    pf = out_png + ".json"
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    cmd = ["npx", "remotion", "still", "src/index.ts", comp, out_png, "--frame=%d" % frame, "--gl=angle",
           "--log=error", "--props=" + pf]
    if public:
        cmd.append("--public-dir=" + public)
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return np.asarray(Image.open(out_png).convert("RGB")).astype(int)


def _ink(img, box):
    """The glyph ink in `box`: pixels far from the box's own ground (the median of its border). A style may repaint
    the ground under type; it may not change a glyph — so it is the INK that must match, not the pixels."""
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1]
    border = np.concatenate([reg[0], reg[-1], reg[:, 0], reg[:, -1]])
    ground = np.median(border, axis=0)
    return np.abs(reg - ground).max(axis=2) > 60


_OUTLINE = {"name": "probe", "refs": [], "refs_missing": "test",
            "line": {"outline": "all", "weight": 4, "color": "ink"}, "fill": {"mode": "flat"}}


@needs_render
def test_outline_all_strokes_shapes_and_never_text(tmp_path):
    """StyleProbe (runtime/__probe_style.tsx) lays out known shapes and known type at fixed places."""
    un = _render("StyleProbe", {}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"style": _OUTLINE}, 10, str(tmp_path / "st.png"))
    from_probe = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))
    # 1) just outside the yellow rect's edge is now ink (dark on this light ground), its middle still yellow, and the
    #    outline is the weight asked for: 4 px outside the edge, nothing 7 px out
    x0, y0, x1, y1 = from_probe["rect"]
    ym = (y0 + y1) // 2
    assert st[ym, x0 - 2].sum() < un[ym, x0 - 2].sum() - 300, (st[ym, x0 - 2], un[ym, x0 - 2])
    assert np.abs(st[ym, x0 - 7] - st[ym, x0 - 40]).max() <= 2           # 7 px out is ground again
    assert np.abs(st[ym, x0 + 2] - un[ym, x0 + 2]).max() <= 2              # the fill keeps all of its area
    # 1b) a line that bounds nothing is inked against what is BEHIND it: dark on this light ground
    lx, ly = from_probe["line_mid"]
    assert st[ly, lx].sum() < 200, st[ly, lx]
    assert np.abs(st[(y0 + y1) // 2, (x0 + x1) // 2] - un[(y0 + y1) // 2, (x0 + x1) // 2]).max() <= 2
    # 2) the gradient circle is one colour across
    cx, cy, r = from_probe["circle"]
    a, b = st[cy, cx - r // 2], st[cy, cx + r // 2]
    assert np.abs(a - b).max() <= 2 and np.abs(un[cy, cx - r // 2] - un[cy, cx + r // 2]).max() > 20
    # 3) the HTML box gets a ring at its edge
    bx0, by0, bx1, by1 = from_probe["box"]
    assert st[(by0 + by1) // 2, bx0 + 1].sum() != un[(by0 + by1) // 2, bx0 + 1].sum()
    # 4) every line of type is the same ink — and a hairline crossing the heading keeps the weight it was drawn with
    for box in from_probe["type"]:
        a, b = _ink(un, box), _ink(st, box)
        assert (a ^ b).mean() <= 0.002, ("type ink changed", box, float((a ^ b).mean()))


@needs_render
def test_a_ground_gradient_goes_flat_and_an_object_gradient_steps(tmp_path):
    """Stepped, a frame-filling ground draws contour rings that read as objects in the picture: a ground goes flat."""
    spec = dict(_OUTLINE, fill={"mode": "cel", "steps": 3})
    un = _render("StyleProbe", {}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    near, far = (60, 960), (1040, 1880)                  # (y, x): the ground near the centre's band and a corner
    assert np.abs(un[540, 1500] - un[far]).max() > 6       # the probe's ground really is a gradient
    assert np.abs(st[540, 1500] - st[far]).max() <= 2, (st[540, 1500], st[far])
    cx, cy, r = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["circle"]
    assert np.abs(st[cy, cx - int(r * 0.8)] - st[cy, cx + int(r * 0.8)]).max() > 20   # the object's gradient: bands


@needs_render
def test_evidence_images_are_never_repainted(tmp_path):
    public = os.path.join(ROOT, "tests", "fixtures", "images")
    props = {"src": "01.png", "credit": "fixture"}
    un = _render("PhotoPlate", props, 157, str(tmp_path / "un.png"), public)
    spec = dict(_OUTLINE, shadow={"mode": "hard-offset", "offset": 8}, form={"corner": 2})
    st = _render("PhotoPlate", dict(props, style=spec), 157, str(tmp_path / "st.png"), public)
    # the photograph's own pixels: the fixture is a white page with dark type, on a beige plate — its extent is the
    # white, inset away from the frame ring (the frame and its shadow are the style's to draw)
    white = (un >= 250).all(axis=2)
    ys, xs = np.nonzero(white)
    y0, y1, x0, x1 = ys.min() + 8, ys.max() - 8, xs.min() + 8, xs.max() - 8
    assert (x1 - x0) > 400 and (y1 - y0) > 200, "the photograph was not found"
    d = np.abs(st[y0:y1, x0:x1] - un[y0:y1, x0:x1]).max()
    assert d <= 2, "the photograph was repainted (max channel diff %d)" % d
