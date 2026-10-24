"""Typeset maths and shape morphs (runtime/mathMorph.tsx, mathCore.ts, pathMorph.ts, pathCore.ts, scripts/tex_glyphs.mjs).

The claims, each held to a measurement:

1. THE TYPESETTER IS LOUD AND DETERMINISTIC. A TeX error is MathJax's own message and a non-zero exit, never red text in
   a frame; CJK inside the maths is refused by name (it would be set in whatever system face the browser finds); the
   library cache rebuilds byte for byte; the file a film's prep writes is named by the same function the bundle looks
   it up by.
2. THE GLYPH LAYER IS MATHJAX'S PICTURE. MathJax's own SVG, rasterised, against the glyph outlines drawn from the
   typeset file at the same place and size — rules, stretchy extenders sliced out of nested viewports, a stroked frame.
3. THE MATCHING READS LIKE A DERIVATION: shared marks stay, a term that changes sides travels on an ARC (never through
   the equals sign), two differently-named terms never trade a glyph.
4. THE MORPH DOES NOT TWIST. Resampled and aligned, the half-way shape keeps an area between its endpoints';
   @remotion/paths' interpolatePath, measured on the same shapes, collapses (and refuses a split outright).
5. THE GATES READ AN EQUATION AS ONE LINE named by its TeX: cut by the frame, in the caption band, under a label.
6. A FRAME IS A FUNCTION OF THE FRAME: the same frame cold twice and after its predecessors are the same pixels.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _HERE)
import _tsprobe  # noqa: E402
import mathtex  # noqa: E402
import text_safe_qa as tq  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")
TOOL = os.path.join(_ROOT, "scripts", "tex_glyphs.mjs")
LIB = os.path.join(_REM, "src", "runtime", "mathLibrary.json")
STRESS = (r"\sum_{k=1}^{n} \frac{1}{k^2} \le \sqrt{\frac{\pi^2}{6}} + \overbrace{a+b}^{n} + \boxed{E=mc^2} + "
          r"\begin{pmatrix}1&0\\0&1\end{pmatrix}")


def _tool(*args, stdin=None):
    r = subprocess.run(["node", "--no-warnings", TOOL, *args], capture_output=True, text=True, input=stdin)
    return r.returncode, json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip().startswith("{") else r.stdout


# ── 1. the typesetter ─────────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
@pytest.mark.parametrize("tex,needle", [
    (r"\frac{a}{", "Missing close brace"),
    (r"\foo x", "Undefined control sequence \\foo"),
    (r"\text{质量} = m", "质量"),
])
def test_a_tex_error_is_mathjax_s_message_and_a_failed_exit(tex, needle):
    rc, rep = _tool("--check", tex)
    assert rc == 2 and rep["errors"] and needle in rep["errors"][0]["error"], rep
    with pytest.raises(RuntimeError) as e:
        mathtex.typeset([(tex, True)], check=True)
    assert needle in str(e.value)


@needs_toolchain
def test_the_library_cache_rebuilds_byte_for_byte(tmp_path):
    out = tmp_path / "lib.json"
    rc, rep = _tool("--library", "--library-out", str(out))
    assert rc == 0 and not rep["errors"], rep
    assert out.read_bytes() == open(LIB, "rb").read(), \
        "mathLibrary.json is stale or the typesetter is not deterministic — run `node scripts/tex_glyphs.mjs --library`"


@needs_toolchain
def test_the_prep_step_files_an_equation_under_the_key_the_bundle_asks_for(tmp_path):
    texs = [r"E = mc^2", r"\int_0^1 x\,dx = \tfrac12", "a  ", "α + β ≤ 𝑥"]
    board = {"meta": {}, "slides": [{"shot": "EquationMorph", "shot_props": {"steps": [{"tex": t} for t in texs]}}]}
    rep = mathtex.ensure(str(tmp_path), board)
    assert len(rep["written"]) == 4
    keys = _tsprobe.run_ts("import {mathKey} from %s;" % _tsprobe.mod("mathKey.ts"),
                           "out.k = %s.map((t) => mathKey(t, true));" % json.dumps(texs))["k"]
    for t, k in zip(texs, keys):
        f = tmp_path / mathtex.MATH_DIR / ("%s.json" % k)
        assert f.exists(), (t, k)
        assert json.loads(f.read_text())["tex"] == t.strip()
    assert mathtex.ensure(str(tmp_path), board)["cached"] == rep["written"], "a second prep rewrites nothing"


# ── 3. matching ──────────────────────────────────────────────────────────────────────────────────────────────
def _lib_by_tex():
    eq = json.load(open(LIB, encoding="utf-8"))["eq"]
    return {e["tex"]: e for e in eq.values()}


def _match(a, b):
    lib = _lib_by_tex()
    return _tsprobe.run_ts("import {matchGlyphs, placeAll} from %s;" % _tsprobe.mod("mathCore.ts"), """
        const A = %s, B = %s;
        const pl = placeAll([A, B], {x: 100, y: 200, w: 1720, h: 500}, 140, 'equals');
        const m = matchGlyphs(A, B, pl.pl[0], pl.pl[1]);
        const ch = (g) => String.fromCodePoint(parseInt(g.c, 16));
        out.pairs = m.pairs.map((p) => [ch(A.glyphs[p.a]), p.kind]);
        out.out = m.out.map((i) => ch(A.glyphs[i]));
        out.in = m.in.map((i) => ch(B.glyphs[i]));
        out.aligned = pl.aligned;
    """ % (json.dumps(lib[a]), json.dumps(lib[b])))


@needs_toolchain
def test_a_term_that_changes_sides_travels_on_an_arc():
    m = _match(r"\class{a}{a} + \class{b}{b} = c", r"\class{a}{a} = c - \class{b}{b}")
    kinds = dict(m["pairs"])
    assert kinds["𝑏"] == "move", "b crosses the equals sign: on an arc, never through it"
    assert kinds["𝑎"] == "stay" and kinds["="] == "stay" and kinds["𝑐"] == "stay", m
    assert m["out"] == ["+"] and m["in"] == ["−"] and m["aligned"]


@needs_toolchain
def test_the_constant_moves_across_and_the_named_square_stays():
    m = _match(r"\class{sq}{(x+3)^2} - 4 = 0", r"\class{sq}{(x+3)^2} = 4")
    assert ["4", "move"] in m["pairs"] and ["=", "stay"] in m["pairs"], m
    assert sorted(m["out"]) == sorted(["−", "0"]) and m["in"] == []


@needs_toolchain
def test_two_differently_named_terms_never_trade_a_glyph():
    # the square's exponent 2 (term `sq`) and the 2 of ±2 (term `root`) are one character and two meanings
    m = _match(r"\class{sq}{(x+3)^2} = 4", r"x = -3 \class{root}{\pm 2}")
    assert "2" in m["out"] and "2" in m["in"], m


# ── 4. morphs ────────────────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_the_half_way_shape_keeps_its_area_where_interpolatepath_collapses():
    out = _tsprobe.run_ts("""
        import {interpolatePath} from '@remotion/paths';
        import {planMorph, morphAt, shapeD} from %s;
        import {parsePath, flatten, signedArea} from %s;
    """ % (_tsprobe.mod("pathMorph.ts"), _tsprobe.mod("pathCore.ts")), """
        const box = {x: 100, y: 100, w: 400, h: 400};
        const area = (d) => flatten(parsePath(d), 64).reduce((a, p) => a + signedArea(p.pts), 0);
        out.rows = [['circle', 'triangle'], ['circle', 'square'], ['triangle', 'hexagon']].map(([a, b]) => {
          const da = shapeD(a, box), db = shapeD(b, box);
          return {lo: Math.min(area(da), area(db)), ours: area(morphAt(planMorph(da, db), 0.5)),
                  theirs: area(interpolatePath(0.5, da, db))};
        });
        const one = shapeD('circle', box), two = shapeD('circle', box, 2);
        try { interpolatePath(0.5, one, two); out.splitErr = null; } catch (e) { out.splitErr = String(e.message || e); }
        const plan = planMorph(one, two);
        out.pieces = plan.pieces.length;
        out.startsAsOne = plan.pieces.every((pc) => pc.a.length === plan.pieces[0].a.length) &&
          JSON.stringify(plan.pieces[0].a) === JSON.stringify(plan.pieces[1].a);
        out.reprod = morphAt(plan, 0.37) === morphAt(planMorph(one, two), 0.37);
    """)
    for r in out["rows"]:
        assert r["ours"] >= 0.9 * r["lo"], ("our half-way shape lost its body", r)
        assert r["theirs"] < 0.5 * r["lo"], ("interpolatePath no longer twists here — re-measure the docstring", r)
    assert out["splitErr"], "interpolatePath refuses one subpath into two"
    assert out["pieces"] == 2 and out["startsAsOne"], "a split starts as the one cell drawn twice over itself"
    assert out["reprod"]


@needs_toolchain
def test_path_core_reads_every_command_and_refuses_garbage():
    out = _tsprobe.run_ts("import {parsePath, segsBBox} from %s;" % _tsprobe.mod("pathCore.ts"), """
        const bb = (d) => segsBBox(parsePath(d)).map((v) => Math.round(v * 100) / 100);
        out.rel = bb('m10 10 h20 v20 h-20 z');
        out.quadT = bb('M0 0 Q50 100 100 0 T200 0');
        out.arc = bb('M0 50 A50 50 0 0 1 100 50 A50 50 0 0 1 0 50 Z');
        out.cubicS = bb('M0 0 C0 100 100 100 100 0 S200 -100 200 0');
        for (const bad of ['10 10 L 20 20', 'M0 0 L 10', 'M0 0 X 5 5', 'M0 0 Z 4 4']) {
          try { parsePath(bad); out[bad] = 'parsed'; } catch (e) { out[bad] = 'threw'; }
        }
    """)
    assert out["rel"] == [10, 10, 30, 30]
    assert out["quadT"] == [0, -50, 200, 50], "a T reflects the last control point; extrema are the curve's"
    assert out["arc"] == [0, 0, 100, 100]
    assert out["cubicS"][1] == -75 and out["cubicS"][3] == 75
    assert all(out[b] == "threw" for b in ["10 10 L 20 20", "M0 0 L 10", "M0 0 X 5 5", "M0 0 Z 4 4"]), out


# ── the live number ──────────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_a_live_number_prints_the_film_s_values_at_its_ends_and_refuses_what_it_cannot_hold():
    lib = _lib_by_tex()
    out = _tsprobe.run_ts("import {liveText, liveDraws} from %s;" % _tsprobe.mod("mathCore.ts"), """
        out.a = [0, 0.5, 1].map((p) => liveText('0.0', '37.5', p));
        out.b = [0, 0.5, 1].map((p) => liveText('-5', '5', p));
        const eq = %s, pl = {x: 0, y: 0, s: 0.1};
        out.n = liveDraws(eq, pl, 'live', '37.5').length;
        for (const v of ['123.4', '1e3', '3–5']) {
          try { liveDraws(eq, pl, 'live', v); out[v] = 'drew'; } catch (e) { out[v] = String(e.message); }
        }
        try { liveText('N/A', '3', 0.5); out.na = 'ok'; } catch (e) { out.na = 'threw'; }
    """ % json.dumps(lib[r"T = \class{live}{00.0}\,\mathrm{K}"]))
    assert out["a"] == ["0.0", "18.8", "37.5"]
    assert out["b"] == ["−5", "0", "5"], "no −0 half way, the film's own sign at each end"
    assert out["n"] == 4
    assert "wider than its slot" in out["123.4"]
    assert out["1e3"] != "drew" and out["3–5"] != "drew" and out["na"] == "threw"


# ── rendered ─────────────────────────────────────────────────────────────────────────────────────────────────
def _still(comp, props, frame, png, public=None):
    pf = png + ".json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh, ensure_ascii=False)
    cmd = ["npx", "remotion", "still", "src/index.ts", comp, png, "--frame=%d" % frame, "--props=" + pf, "--log=error"]
    if public:
        cmd.append("--public-dir=" + public)
    r = subprocess.run(cmd, cwd=_REM, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _pixels(png):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(png).convert("L")).astype(int)


@pytest.fixture(scope="module")
def work():
    d = tempfile.mkdtemp(prefix="math_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@needs_toolchain
def test_the_glyph_layer_draws_mathjax_s_own_picture(work):
    pub = os.path.join(work, "pub")
    os.makedirs(pub, exist_ok=True)
    rc, svg = _tool("--svg", STRESS)
    assert rc == 0 and svg.startswith("<svg"), svg[:200]
    with open(os.path.join(pub, "ref.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg.replace("currentColor", "#000000"))
    a, b = os.path.join(work, "ref.png"), os.path.join(work, "gl.png")
    assert _still("MathProbe", {"variant": "reference"}, 10, a, pub)[0] == 0
    assert _still("MathProbe", {"variant": "glyphs"}, 10, b, pub)[0] == 0
    import numpy as np
    from scipy import ndimage
    pa, pb = _pixels(a), _pixels(b)
    ink = int((pa < 128).sum())
    assert ink > 20000, "the reference drew almost nothing — the comparison would prove nothing"
    # MEASURED AS THE SHAPE OF THE DIFFERENCE, not a share of it (engineering-case-law E16). A threshold-crossing count
    # reads 2% here and every pixel of its largest region is one row of the boxed frame's lower edge at 130 against 127
    # — the same grey either side of the threshold. What a defect looks like, measured on this frame: one glyph erased,
    # a 399 px region past 64 levels; the whole layer one pixel off, 807 px. The rendered pair: 25 px in all, at most 5
    # together.
    big = np.abs(pa - pb) > 64
    lab, n = ndimage.label(big, structure=np.ones((3, 3)))
    largest = int(max(ndimage.sum(big, lab, range(1, n + 1)))) if n else 0
    assert largest < 60 and int(big.sum()) < 400, \
        "MathJax's svg and the glyph layer differ: %d px past 64 levels, the largest region %d px" % (int(big.sum()), largest)


@needs_toolchain
def test_the_type_gates_read_an_equation_as_one_line(work):
    tex = r"\class{a}{a} + \class{b}{b} = c"
    cut = tq.audit_shot("MathProbe", {"variant": "cut"}, 10, os.path.join(work, "cut.png"))
    assert len(cut) == 1 and cut[0]["tag"] == "math" and cut[0]["out"].get("right", 0) > 100, cut
    assert cut[0]["text"] == tex
    band = tq.audit_shot("MathProbe", {"variant": "band"}, 10, os.path.join(work, "band.png"))
    assert len(band) == 1 and band[0].get("band", 0) > 30 and band[0]["text"] == tex, band
    assert tq.audit_shot("MathProbe", {"variant": "ok"}, 10, os.path.join(work, "ok.png")) == []
    rc, blob = _still("MathProbe", {"variant": "overlap", "typeCollisions": True}, 10, os.path.join(work, "ov.png"))
    hits = json.JSONDecoder().raw_decode(blob.split("TYPE-COLLISIONS ", 1)[1])[0]
    assert any(h["kind"] == "overlap" and tex in (h["text"] + (h.get("other") or "")) for h in hits), hits


@needs_toolchain
def test_a_tex_nobody_typeset_fails_the_render_by_name(work):
    rc, blob = _still("EquationMorph", {"steps": [{"tex": r"\zeta(2) = \frac{\pi^2}{6}"}]}, 40,
                      os.path.join(work, "miss.png"), os.path.join(work, "empty-pub"))
    assert rc != 0 and "TeX not typeset" in blob and "mathtex.py" in blob, blob[-600:]


@needs_toolchain
@pytest.mark.parametrize("comp,props,frame", [
    ("EquationMorph", {}, 171),
    ("GrowingFigure", {}, 150),
])
def test_a_frame_is_the_same_cold_twice_and_after_its_predecessors(work, comp, props, frame):
    a, b = os.path.join(work, "%s-a.png" % comp), os.path.join(work, "%s-b.png" % comp)
    assert _still(comp, props, frame, a)[0] == 0 and _still(comp, props, frame, b)[0] == 0
    seq = os.path.join(work, "%s-seq" % comp)
    pf = os.path.join(work, "%s.json" % comp)
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh)
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", comp, seq, "--sequence", "--image-format=png",
                        "--frames=0-%d" % frame, "--concurrency=1", "--props=" + pf, "--log=error"],
                       cwd=_REM, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    warm = sorted(os.listdir(seq))[-1]
    pa, pb, pw = _pixels(a), _pixels(b), _pixels(os.path.join(seq, warm))
    assert (pa != pb).sum() == 0, "the same frame rendered twice differs"
    assert (pa != pw).sum() == 0, "frame %d after frames 0..%d differs from the same frame cold" % (frame, frame - 1)
