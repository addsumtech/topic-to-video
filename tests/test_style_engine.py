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
    assert re.search(r"<StyleLayer beat=\{i\} skip=\{STYLE_HOOKS_BY_SHOT\[sc\.shot\]\}>\s*<BeatClock warp=\{sc\.warp\}>\{C \? <C \{\.\.\.\(sc\.props \?\? \{\}\)\} /> : <Missing",
                     film), "the plain register path is not styled"
    # the platform-safe margin: the WHOLE echo inside a style layer, so its ground matches the beat's, and never a
    # style element between the echo's selectors and the register they hide (ECHO_GROUND_ONLY)
    assert re.search(r"<StyleLayer beat=\{i\} skip=\{STYLE_HOOKS_BY_SHOT\[sc\.shot\]\}>\s*<SafeEcho ", film), "the platform-safe margin is not styled"
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
    # 100: every glyph on the probe sits 190+ from its ground; the grey hairline under the heading — a SHAPE, which a
    # style may texture and wobble — sits ~60 from it, and must not be read as type
    return np.abs(reg - ground).max(axis=2) > 100


def _ink_moved(a, b):
    """The fraction of the box where type ink differs by MORE than its own antialiased edge: a pixel that flips within
    1 px of a glyph's edge is the ground under a partly-covered pixel changing (a texture, a flattened gradient), not
    the glyph; one farther out is a glyph drawn differently."""
    def grow(m):
        g = m.copy()
        g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        return g
    def shrink(m):
        return ~grow(~m)
    edge = grow(a) & ~shrink(a)
    return float(((a ^ b) & ~edge).mean())


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
        moved = _ink_moved(_ink(un, box), _ink(st, box))
        assert moved <= 0.0005, ("type ink changed", box, moved)


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


# ── Task 4: per-pixel filters (wobble, boil, posterize, the outer edge) and the surface ─────────────────────────

def _filters(body):
    return _tsprobe.run_ts("import * as F from %s;" % _tsprobe.mod("styleFilters.tsx"), body)


@needs_ts
def test_wobble_seed_is_a_pure_function_of_frame():
    out = _filters("""
      out.same = [F.wobbleSeed(10, 150, 30, 8, false), F.wobbleSeed(10, 150, 30, 8, false)];
      out.hold = [0, 1, 2, 3].map((f) => F.wobbleSeed(f, 150, 30, 8, false));
      out.next = F.wobbleSeed(4, 150, 30, 8, false);
      out.still = [0, 40, 99].map((f) => F.wobbleSeed(f, 150, 30, 0, false));
      out.reduced = [0, 40, 99].map((f) => F.wobbleSeed(f, 150, 30, 8, true));
    """)
    assert out["same"][0] == out["same"][1]
    assert len(set(out["hold"])) == 1, out["hold"]               # 8 Hz at 30 fps: one drawing for 3.75 frames
    assert out["next"] != out["hold"][0]
    assert len(set(out["still"])) == 1 and len(set(out["reduced"])) == 1


def test_the_seed_reads_only_the_beat_clock():
    """A seam's container copy is the same beat drawn twice at the same frame: in phase iff the seed reads nothing
    else (no counter, no time, no randomness)."""
    src = open(os.path.join(REMOTION, "src", "runtime", "styleFilters.tsx"), encoding="utf-8").read()
    body = src[src.index("export const wobbleSeed"):]
    body = body[:body.index("\n};") + 3]
    for banned in ("Math.random", "Date", "performance", "useRef", "let "):
        assert banned not in body, banned


@needs_ts
def test_a_layer_inside_an_echo_still_styles_its_shapes():
    out = _ts("""
      const echo = el('DIV', null, {'data-echo': 'seam-container'}); const layer = el('DIV', echo);
      const rect = el('rect', el('svg', layer));
      out.r = [C.classify(rect), C.classify(rect, layer)];
    """)
    assert out["r"] == ["echo", "shape"]


def test_surface_is_static_and_never_over_type():
    src = open(os.path.join(REMOTION, "src", "runtime", "styleSurface.ts"), encoding="utf-8").read()
    for banned in ("useCurrentFrame", "Math.random", "Date.now"):
        assert banned not in src, banned
    eng = open(STYLE, encoding="utf-8").read()
    # the texture goes UNDER content: a box's own background layer (painted beneath its text) or a filter on a group
    # that holds no type — never an overlay above the register
    assert "background-blend-mode" in eng and "surfaceTile(" in eng
    assert "mix-blend-mode" not in eng


_BOIL = {"name": "boil", "refs": [], "refs_missing": "test",
         "line": {"weight": 3, "color": "ink", "outline": "all", "wobble": 3, "boil_hz": 8}}


@needs_render
def test_text_never_wobbles_and_shapes_boil(tmp_path):
    """Three frames of the probe one boil phase apart: the shapes' edges move between drawings, the type's ink not."""
    frames = [_render("StyleProbe", {"style": _BOIL}, f, str(tmp_path / ("b%d.png" % f))) for f in (0, 4, 8)]
    lay = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))
    x0, y0, x1, y1 = lay["rect"]
    edge = (slice(y0 - 12, y1 + 12), slice(x0 - 12, x0 + 12))
    assert np.abs(frames[0][edge] - frames[1][edge]).max() > 40, "the rect's edge did not move between drawings"
    for box in lay["type"]:
        for a, b in ((frames[0], frames[1]), (frames[1], frames[2])):
            moved = _ink_moved(_ink(a, box), _ink(b, box))
            assert moved <= 0.0005, ("type moved under the boil", box, moved)


@needs_render
def test_outer_outline_rings_a_drawing_not_its_parts(tmp_path):
    spec = {"name": "outer", "refs": [], "refs_missing": "test", "line": {"outline": "outer", "weight": 5, "color": "ink"}}
    un = _render("StyleProbe", {}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    lay = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))
    x0, y0, x1, y1 = lay["rect"]
    ym = (y0 + y1) // 2
    assert st[ym, x0 - 3].sum() < un[ym, x0 - 3].sum() - 300, "no outer ring at the rect's edge"
    for box in lay["type"]:
        assert _ink_moved(_ink(un, box), _ink(st, box)) <= 0.0005, ("type changed", box)


@needs_render
def test_a_paper_surface_textures_the_ground_and_not_the_type(tmp_path):
    spec = {"name": "paper", "refs": [], "refs_missing": "test", "surface": {"kind": "paper", "strength": 0.8}}
    un = _render("StyleProbe", {}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    patch = (slice(60, 160), slice(1300, 1700))            # an empty stretch of ground
    def tooth(img):          # high-frequency energy: a smooth gradient has none, a medium's tooth has it
        p = img[patch].astype(float)
        return float(np.abs(p[:, 1:] - p[:, :-1]).mean())
    assert tooth(st) > tooth(un) + 1.0, ("the ground took no texture", tooth(un), tooth(st))
    lay = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))
    for box in lay["type"]:
        assert _ink_moved(_ink(un, box), _ink(st, box)) <= 0.0005, ("type textured", box)


# ── found by LOOKING at the cartoon-like corpus run (CinematicTitle went grey, ChartLive's series went white) ──────

@needs_ts
def test_a_mean_colour_weighs_each_stop_by_its_alpha():
    """A fill fading to nothing is that colour, fainter — not that colour mixed with black (the area under ChartLive's
    series went grey)."""
    out = _ts("out.m = C.meanColor('linear-gradient(rgba(34, 197, 94, 0.6) 0%, rgba(0, 0, 0, 0) 100%)');")
    assert out["m"] == "rgba(34, 197, 94, 0.3)", out["m"]


_CARTOON = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "cartoonish_spec.json")))


@needs_render
def test_a_translucent_overlay_takes_no_opaque_medium(tmp_path):
    """The paper's tooth is opaque; laid on a vignette it covered the whole register (CinematicTitle: a grey frame)."""
    st = _render("StyleProbe", {"style": _CARTOON, "overlay": True}, 10, str(tmp_path / "st.png"))
    x0, y0, x1, y1 = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["rect"]
    mid = st[(y0 + y1) // 2, (x0 + x1) // 2]
    assert mid[0] > 150 and mid[2] < 140, ("the yellow rect is covered", mid)       # still yellow under the vignette


@needs_render
def test_a_coloured_line_keeps_its_hue_and_a_hairline_stays_lighter(tmp_path):
    spec = {"name": "ink lines", "refs": [], "refs_missing": "test", "line": {"weight": 4, "color": "ink"},
            "fill": {"mode": "flat"}}
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    lay = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))
    # per PIXEL: the series is #16a34a (G−R 141); the faint area under it ~45; an ink line ~0
    greenest = max(int((st[y - 6:y + 7, x - 6:x + 7, 1].astype(int) - st[y - 6:y + 7, x - 6:x + 7, 0]).max())
                   for x, y in lay["series"])
    assert greenest > 80, ("the data series lost its colour", greenest)
    gx, gy = lay["grid_x"], lay["grid_y"]
    col = np.abs(st[gy - 6:gy + 7, gx] - st[gy + 14, gx]).max(axis=1) > 12      # the area above ends at y=1030
    assert 0 < col.sum() <= 2, ("the hairline is no longer lighter than the main line", int(col.sum()))
    ax, ay = lay["area"]
    a = st[ay, ax]
    assert a[1] > a[0] + 10, ("the area under the series lost its hue", a)


@needs_render
def test_light_is_not_paint(tmp_path):
    """Translucent things are LIGHT: a vignette flattened became a grey veil over a title (CinematicTitle), a glint and a
    halo were outlined as if they were objects (ClayStack, KnowledgeGraph), and a letterbox bar took a ring."""
    spec = {"name": "flat ink", "refs": [], "refs_missing": "test", "fill": {"mode": "flat"},
            "line": {"outline": "all", "weight": 4, "color": "ink"}, "shadow": {"mode": "hard-offset", "offset": 6}}
    st = _render("StyleProbe", {"style": spec, "overlay": True}, 10, str(tmp_path / "st.png"))
    lay = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))
    # the vignette is still a vignette: the corner darker than the open ground near the middle
    assert st[1060, 20].astype(int).sum() < st[560, 700].astype(int).sum() - 40, (st[1060, 20], st[560, 700])
    # the glint has no ink ring: just outside its edge is still the yellow of the rect
    gx, gy = lay["glint_edge"]
    assert st[gy, gx].astype(int).sum() > 450, ("the glint was outlined", st[gy, gx])
    # the letterbox bar has no ring along its lower edge
    assert np.abs(st[42, 960].astype(int) - st[70, 960].astype(int)).max() <= 12, (st[42, 960], st[70, 960])


@needs_render
def test_a_medium_shows_on_a_dark_ground_too(tmp_path):
    """Multiplied, a tooth darkens: on a near-black ground that is one level, which no viewer sees (WordTunnel measured
    no surface at all under paper). A dark ground takes the medium as light grain."""
    spec = {"name": "paper", "refs": [], "refs_missing": "test", "surface": {"kind": "paper", "strength": 0.8}}
    un = _render("StyleProbe", {"dark": True}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"dark": True, "style": spec}, 10, str(tmp_path / "st.png"))
    patch = (slice(60, 160), slice(1300, 1700))
    def tooth(img):
        p = img[patch].astype(float)
        return float(np.abs(p[:, 1:] - p[:, :-1]).mean())
    assert tooth(st) > tooth(un) + 1.0, ("no medium on the dark ground", tooth(un), tooth(st))


@needs_render
def test_a_shadow_falls_under_a_shape_in_a_frame_filling_drawing(tmp_path):
    """Most registers draw in ONE frame-sized <svg>: a shadow set on the drawing's root never fell, because a root
    that fills the frame is its ground (ClayStack in the axis gallery: shadow.mode did nothing)."""
    spec = {"name": "shadow", "refs": [], "refs_missing": "test", "shadow": {"mode": "hard-offset", "offset": 10}}
    un = _render("StyleProbe", {}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    x0, y0, x1, y1 = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["rect"]
    p = (y1 + 5, (x0 + x1) // 2)                       # just below the rect, inside its offset shadow
    assert st[p].astype(int).sum() < un[p].astype(int).sum() - 60, (st[p], un[p])
    gx, gy = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["glint_edge"]
    # the glint casts nothing of its own: just below it, inside the rect, is still the rect's yellow
    assert st[gy + 52, gx].astype(int).sum() > 450, st[gy + 52, gx]


@needs_render
def test_hatch_shades_with_lines_not_bands(tmp_path):
    """shade 'hatch' drew exactly what 'cel' drew (the axis gallery showed them identical): a value that does not do
    what it names. Hatching is ink lines where the drawing is in shade."""
    cel = {"name": "cel", "refs": [], "refs_missing": "t", "shade": {"mode": "cel"}}
    hatch = {"name": "hatch", "refs": [], "refs_missing": "t", "shade": {"mode": "hatch"}}
    a = _render("StyleProbe", {"style": cel}, 10, str(tmp_path / "cel.png"))
    b = _render("StyleProbe", {"style": hatch}, 10, str(tmp_path / "hatch.png"))
    cx, cy, r = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["circle"]
    dark = (slice(cy - 30, cy + 30), slice(cx - r + 30, cx - r + 90))       # the gradient's darker (left) side
    def hf(img):
        p = img[dark].astype(float).mean(axis=2)
        return float(np.abs(p[:, 1:] - p[:, :-1]).mean() + np.abs(p[1:] - p[:-1]).mean())
    assert hf(b) > hf(a) + 8, ("no hatching in the shade", hf(a), hf(b))


@needs_ts
def test_a_stepped_translucent_gradient_keeps_each_bands_alpha():
    """Stepped with ONE mean alpha, a vignette (clear → 80% black) became a uniform 40% veil over the whole title
    (CinematicTitle in the cartoon acceptance sample: a cream ground read as muddy taupe)."""
    out = _ts("""
      out.s = C.steppedGradient('radial-gradient(120% 100% at 50% 50%, rgba(0, 0, 0, 0) 52%, rgba(0, 0, 0, 0.8) 100%)', 2);
      out.a = C.quantizeAlphas([0, 0.8], 2);
    """)
    alphas = [float(x) for x in re.findall(r"rgba\(\s*\d+,\s*\d+,\s*\d+,\s*([\d.]+)\)", out["s"])]
    assert len(alphas) == 2 and alphas[0] < alphas[1] - 0.2, out["s"]
    assert out["a"][0] < out["a"][1]


@needs_render
def test_a_frame_filling_light_is_removed_not_banded_or_veiled(tmp_path):
    spec = {"name": "cel light", "refs": [], "refs_missing": "test", "shade": {"mode": "cel"}}
    bare = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "bare.png"))
    lit = _render("StyleProbe", {"style": spec, "overlay": True}, 10, str(tmp_path / "lit.png"))
    # the open ground near the middle is what it is without the vignette — no veil
    assert np.abs(lit[560, 700].astype(int) - bare[560, 700].astype(int)).max() <= 3, (lit[560, 700], bare[560, 700])
    # and the corner is not a hard dark band either
    assert np.abs(lit[1060, 20].astype(int) - bare[1060, 20].astype(int)).max() <= 3, (lit[1060, 20], bare[1060, 20])


@needs_render
def test_a_flattened_radial_ground_is_the_ground_its_glow_fades_into(tmp_path):
    """A radial ground is a glow on a ground. Flattened to its MEAN, a 9:16 title's whole frame turned peach while the
    platform-safe margin (the DNA ground) stayed cream — the beat read as a panel. Its outer stop is the ground."""
    spec = {"name": "flat", "refs": [], "refs_missing": "test", "fill": {"mode": "flat"}}
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    outer = np.array([0xe6, 0xdc, 0xcb])                       # the probe ground's outer stop
    for p in ((560, 700), (60, 1500), (1060, 20)):
        assert np.abs(st[p].astype(int) - outer).max() <= 3, (p, st[p])


@needs_render
def test_one_ground_for_the_film_when_the_tones_agree(tmp_path):
    """surface.ground 'film': every frame-filling ground becomes the film's own ground — a register's glow, its own
    tint, its vignette go — so the beats read as one world (a cartoon film cut to a dark theatre stage did not).
    Only where the register's ground and the film's are the SAME tone: repainted the other way, type drawn for a dark
    ground would sit unreadable on a light one, and type is never restyled."""
    spec = {"name": "one ground", "refs": [], "refs_missing": "t", "surface": {"ground": "film"}}
    light = _render("StyleProbe", {"style": spec, "dna": "editorial"}, 10, str(tmp_path / "x.png"))
    # editorial is a DARK film; the probe's light ground disagrees: left as drawn, type untouched
    assert light[560, 700].astype(int).sum() > 600, light[560, 700]
    film = dict(_EDITORIAL_LIGHT)
    st = _render("StyleProbe", {"style": spec, "dna": film, "overlay": True}, 10, str(tmp_path / "st.png"))
    want = np.array([0xff, 0xf4, 0xdf])
    for p in ((560, 700), (60, 1500), (1060, 20)):        # the middle, an empty stretch, a vignetted corner
        assert np.abs(st[p].astype(int) - want).max() <= 3, (p, st[p])


_EDITORIAL_LIGHT = {"id": "probe-light", "bg": "#fff4df", "fg": "#231a14", "dim": "#6d5d4f", "accent": "#e5432a",
                    "accent2": "#2a74d1", "onAccent": "#ffffff", "surface": "#ffe9bf", "surfaceBorder": "#231a14",
                    "line": "#231a14", "finish": "none"}


@needs_render
def test_one_ground_leaves_a_ground_far_from_the_films_even_of_the_same_tone(tmp_path):
    """Black and slate are both "dark", 3.7:1 apart: repainted, a register's dim words set for black sank into the
    slate (SpotlightStage, the second cartoon film). Grounds are unified only when they are close (≤ 1.6:1)."""
    spec = {"name": "one ground", "refs": [], "refs_missing": "t", "surface": {"ground": "film"}}
    slate = dict(_EDITORIAL_LIGHT, bg="#54717f", fg="#ffffff")
    un = _render("StyleProbe", {"dark": True, "dna": slate}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"dark": True, "dna": slate, "style": spec}, 10, str(tmp_path / "st.png"))
    for p in ((560, 700), (1060, 20)):
        assert np.abs(st[p].astype(int) - un[p].astype(int)).max() <= 3, (p, st[p], un[p])


@needs_render
def test_both_draws_a_heavy_silhouette_and_light_inner_lines(tmp_path):
    """Illustration systems set TWO line weights, the outline double the inner line (Airbus, ServiceTitan guides): with
    every part outlined alike, a satellite's facets read as a diagram, not a drawing (the first cartoon film)."""
    both = {"name": "both", "refs": [], "refs_missing": "t", "line": {"outline": "both", "weight": 8, "color": "ink"}}
    alls = {"name": "all", "refs": [], "refs_missing": "t", "line": {"outline": "all", "weight": 8, "color": "ink"}}
    b = _render("StyleProbe", {"style": both}, 10, str(tmp_path / "b.png"))
    a = _render("StyleProbe", {"style": alls}, 10, str(tmp_path / "a.png"))
    x0, y0, x1, y1 = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["rect"]
    ym = (y0 + y1) // 2
    def band(img):       # how far out from the rect's edge the ink reaches
        g = img[ym, x0 - 30:x0].astype(int).sum(axis=1)
        return int((g < g[0] - 200).sum())
    assert band(b) >= band(a) + 4, ("no heavier silhouette", band(a), band(b))
    lx, ly = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "probe_layout.json")))["line_mid"]
    def thick(img):      # the free diagonal line's vertical thickness at its middle
        col = img[ly - 20:ly + 21, lx].astype(int).sum(axis=1)
        return int((col < col[0] - 120).sum())          # a thin antialiased line is not fully dark at any pixel
    assert 0 < thick(b) < thick(a), ("inner lines not lighter", thick(a), thick(b))


@needs_render
def test_a_speck_is_not_outlined(tmp_path):
    """Dust specks a few px wide took a ring each and read as boxed squares across a title (the third cartoon film)."""
    spec = {"name": "ink", "refs": [], "refs_missing": "t", "line": {"outline": "all", "weight": 6, "color": "ink"},
            "shadow": {"mode": "hard-offset", "offset": 6}}
    un = _render("StyleProbe", {}, 10, str(tmp_path / "un.png"))
    st = _render("StyleProbe", {"style": spec}, 10, str(tmp_path / "st.png"))
    for p in ((112, 1592), (112, 1607), (128, 1592), (128, 1607)):    # just outside the speck's box
        assert np.abs(st[p].astype(int) - un[p].astype(int)).max() <= 3, (p, st[p], un[p])
