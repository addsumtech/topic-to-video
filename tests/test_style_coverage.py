"""Who the style reaches, who it cannot, and why — derived from the registers, never restated.

A register whose picture is a photograph (evidence) or a canvas cannot be restyled: the engine still styles its DOM
(frame, labels' boxes) but its picture stays as drawn, so it is left out of the film's consistency check and listed
with its reason. A register may also declare STYLE_HOOKS — axes it draws itself — and the engine leaves those to it.
"""
import os
import re

import pytest

import _tsprobe
import style_coverage as sc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "remotion", "src", "shots")
needs_ts = pytest.mark.skipif(not _tsprobe.available(), reason="node/esbuild not available")


def test_every_canvas_shot_is_exempt_with_a_reason():
    canvas = [f[:-4] for f in os.listdir(SHOTS) if f.endswith(".tsx")
              and re.search(r"<canvas|getContext\(|@react-three|ThreeCanvas|@remotion/three", open(os.path.join(SHOTS, f), encoding="utf-8").read())]
    ex = sc.exempt_registers()
    assert canvas, "the grep found no canvas register: the test is looking at the wrong thing"
    for s in canvas:
        assert s in ex and "canvas" in ex[s], (s, ex.get(s))


def test_every_evidence_register_is_exempt():
    import register_energy as re_
    ex = sc.exempt_registers()
    for s in re_.evidence_props():
        assert s in ex and "photograph" in ex[s], (s, ex.get(s))


def test_exempt_reason_is_not_empty():
    assert all(isinstance(r, str) and r.strip() for r in sc.exempt_registers().values())


def _board(shots):
    return {"meta": {"renderer": "remotion"}, "slides": [{"index": i + 1, "shot": s} for i, s in enumerate(shots)]}


def test_coverage_reports_the_quarter_rule():
    board = _board(["PhotoPlate", "RealVersus", "PortRail", "ChartLive", "ClayStack", "KnowledgeGraph", "FlowSankey",
                    "AtomOrbital", "TermSpace", "WordTunnel"])
    rep = sc.film_coverage(board)
    assert rep["exempt_fraction"] == pytest.approx(0.3)
    assert [b["shot"] for b in rep["exempt"]] == ["PhotoPlate", "RealVersus", "PortRail"]
    assert any("more than a quarter" in w for w in rep["warnings"]), rep["warnings"]
    rep = sc.film_coverage(_board(["PhotoPlate", "ChartLive", "ClayStack", "KnowledgeGraph", "FlowSankey"]))
    assert rep["exempt_fraction"] == pytest.approx(0.2) and rep["warnings"] == []


def test_hooks_map_lists_every_register_that_declares_hooks():
    declared = sorted(f[:-4] for f in os.listdir(SHOTS) if f.endswith(".tsx")
                      and "export const STYLE_HOOKS" in open(os.path.join(SHOTS, f), encoding="utf-8").read())
    src = open(os.path.join(ROOT, "remotion", "src", "runtime", "styleHooks.ts"), encoding="utf-8").read()
    for s in declared:
        assert re.search(r"\b%s\b" % s, src), "%s declares STYLE_HOOKS and styleHooks.ts does not list it" % s
    film = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert "skip={STYLE_HOOKS_BY_SHOT[sc.shot]}" in film


@needs_ts
def test_a_hooked_axis_is_left_to_the_register():
    out = _tsprobe.run_ts("import {withoutAxes} from %s; import {resolveStyle} from %s;"
                          % (_tsprobe.mod("styleHooks.ts"), _tsprobe.mod("styleSpec.ts")), """
      const s = resolveStyle({name: 't', refs: [], refs_missing: 'x', line: {wobble: 3, weight: 4}, fill: {mode: 'cel'}});
      const k = withoutAxes(s, ['line.wobble', 'fill']);
      out.k = [k.line.wobble, k.line.weight, k.fill.mode, s.line.wobble];
      out.same = withoutAxes(s, []) === s;
    """)
    assert out["k"] == [0, 4, "as-drawn", 3]
    assert out["same"] is True


_LIGHT_DNA = {"id": "t", "bg": "#fff4df", "fg": "#231a14", "accent": "#e5432a", "accent2": "#2a74d1"}


def test_a_dark_world_register_on_a_light_style_is_named():
    """A cartoon film on cream cut to SpotlightStage's own night (#09090b): one ground cannot repaint it (its type is
    set for dark), so the SELECTION has to change — and only the ground table knows which registers keep a world of
    their own under a film's DNA."""
    board = {"meta": {"renderer": "remotion", "design_dna": _LIGHT_DNA,
                      "style": {"name": "x", "refs": [], "refs_missing": "t", "line": {"outline": "all"}}},
             "slides": [{"index": 1, "shot": "CinematicTitle"}, {"index": 2, "shot": "SpotlightStage"},
                        {"index": 3, "shot": "KnowledgeGraph"}]}
    rows = sc.ground_conflicts(board)
    assert [r["shot"] for r in rows] == ["SpotlightStage"], rows
    assert rows[0]["ground"].lower() == "#09090b"
    import validate
    errs, warns = [], []
    validate._check_style(board["meta"], errs, warns, board["slides"])
    assert any("SpotlightStage" in w and "#09090b" in w.lower() for w in warns), warns


def test_no_style_or_no_dna_asks_nothing():
    board = {"meta": {"renderer": "remotion", "design_dna": _LIGHT_DNA}, "slides": [{"index": 1, "shot": "SpotlightStage"}]}
    assert sc.ground_conflicts(board) == []


def test_a_ground_far_from_the_films_is_named_even_of_the_same_tone():
    board = {"meta": {"renderer": "remotion", "design_dna": dict(_LIGHT_DNA, bg="#54717f", fg="#ffffff"),
                      "style": {"name": "x", "refs": [], "refs_missing": "t"}},
             "slides": [{"index": 1, "shot": "SpotlightStage"}]}
    assert [r["shot"] for r in sc.ground_conflicts(board)] == ["SpotlightStage"]
