"""The style spec — a style the skill has never seen is a set of VALUES on fixed, general drawing axes.

WHY IT EXISTS. A user asks for "a cartoon", "水墨", "like Kurzgesagt". The library answered with a dozen craft
registers that carry a title, while every other beat kept its own drawing and took only the film's colours —
"只换了配色，画法和线条还是原来的样子", the failure the user named. The spec is the decomposition: line, fill,
shade, shadow, form, surface, type, motion. A new style fills new values; it never adds code, so no axis or value
may be named after a style. One table (runtime/styleAxes.json) is read by Python and TypeScript alike.
"""
import json
import os
import re

import pytest

import style_spec as ss

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _spec(**axes):
    s = {"name": "test", "refs": [{"src": "https://example.org/a.png", "from": "found"}]}
    s.update(axes)
    return s


def test_unknown_axis_or_value_is_an_error():
    errs, _ = ss.validate_spec(_spec(line={"boldness": 3}))
    assert any("style.line.boldness" in e for e in errs), errs
    errs, _ = ss.validate_spec(_spec(fill={"mode": "watercolour"}))
    assert any("style.fill.mode" in e for e in errs), errs
    errs, _ = ss.validate_spec(_spec(glow={"mode": "on"}))
    assert any("style.glow" in e for e in errs), errs
    errs, _ = ss.validate_spec(_spec(line={"weight": -1}))
    assert any("style.line.weight" in e for e in errs), errs
    errs, _ = ss.validate_spec(_spec(line={"boil_hz": 3}))          # 0, or a boil a viewer reads (6–12 Hz)
    assert any("style.line.boil_hz" in e for e in errs), errs
    errs, _ = ss.validate_spec(_spec(line={"color": "#12345"}))
    assert any("style.line.color" in e for e in errs), errs


def test_a_well_formed_spec_has_no_error():
    errs, _ = ss.validate_spec(_spec(line={"weight": 4, "color": "ink", "outline": "all", "boil_hz": 8, "wobble": 1.5},
                                     fill={"mode": "cel", "steps": 3}, shadow={"mode": "hard-offset", "offset": 6},
                                     motion={"stepping": 2}))
    assert errs == []


def test_refs_required_unless_reason_given():
    s = _spec(line={"outline": "all"})
    s["refs"] = []
    errs, _ = ss.validate_spec(s)
    assert any("refs" in e for e in errs), errs
    s["refs_missing"] = "offline: web search refused"
    errs, _ = ss.validate_spec(s)
    assert errs == []


def test_a_ref_says_where_it_came_from():
    errs, _ = ss.validate_spec(_spec(refs=[{"src": "a.png", "from": "dreamt"}]))
    assert any("refs[0].from" in e for e in errs), errs


def test_all_as_drawn_is_recolour_only_and_warns():
    s = _spec()
    assert ss.is_recolour_only(s)
    errs, warns = ss.validate_spec(s)
    assert errs == []
    assert sum("only the palette changes" in w for w in warns) == 1, warns
    assert not ss.is_recolour_only(_spec(fill={"mode": "flat"}))


def test_a_dependent_value_alone_is_not_a_structural_change():
    """`fill.steps` means nothing unless fill is cel; a surface's strength nothing without a surface."""
    assert ss.structural_axes(_spec(fill={"steps": 4}, surface={"strength": 0.9})) == []
    assert ss.structural_axes(_spec(fill={"mode": "cel", "steps": 4})) == ["fill.mode", "fill.steps"]


def test_no_axis_is_named_after_a_style():
    banned = re.compile(r"cartoon|anime|ghibli|watercolou?r|ink-?wash|pixel|comic|manga|clay|kurzgesagt|水墨|卡通",
                        re.I)
    words = []
    for group, params in ss.AXES.items():
        words.append(group)
        for name, p in params.items():
            words.append(name)
            words += [str(v) for v in p.get("values", [])]
    hits = [w for w in words if banned.search(w)]
    assert not hits, "a style-named axis or value: %s" % hits


def test_sha_ignores_shortfalls_and_credit():
    a = _spec(line={"outline": "all"})
    b = json.loads(json.dumps(a))
    b["shortfalls"] = [{"axis": "surface.source", "wanted": "generated", "got": "procedural", "why": "no codex"}]
    b["refs"][0]["credit"] = "someone"
    assert ss.spec_sha256(a) == ss.spec_sha256(b)
    c = json.loads(json.dumps(a))
    c["line"]["outline"] = "outer"
    assert ss.spec_sha256(a) != ss.spec_sha256(c)


def test_ts_reads_the_same_axis_table():
    """Parity by construction: the TypeScript imports the very JSON the Python reads."""
    ts = open(os.path.join(ROOT, "remotion", "src", "runtime", "styleSpec.ts"), encoding="utf-8").read()
    assert re.search(r"import\s+\w+\s+from\s+'\./styleAxes\.json'", ts), "styleSpec.ts does not read styleAxes.json"
    assert os.path.samefile(ss.AXES_PATH, os.path.join(ROOT, "remotion", "src", "runtime", "styleAxes.json"))


def test_ts_defaults_fill_an_empty_spec():
    import _tsprobe
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    out = _tsprobe.run_ts("import {resolveStyle} from %s;" % _tsprobe.mod("styleSpec.ts"),
                          "out.r = resolveStyle({name: 't', refs: [], refs_missing: 'x', fill: {mode: 'cel'}});")
    r = out["r"]
    assert r["fill"]["mode"] == "cel"
    assert r["fill"]["steps"] == ss.AXES["fill"]["steps"]["default"]
    assert r["line"]["weight"] == "as-drawn"
    assert r["motion"]["stepping"] == 1


def test_render_passes_style_prop(tmp_path):
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg needed for the audio stub")
    import render_remotion as rr
    (tmp_path / "audio").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3",
                    str(tmp_path / "audio" / "01.wav")], check=True)
    board = {"meta": {"renderer": "remotion", "aspect": "16:9"},
             "slides": [{"index": 1, "shot": "TermTable", "duration": 3.0, "narration": "x", "caption": "x",
                         "audio": "audio/01.wav", "shot_props": {"rows": [["a", "1"]]}}]}
    json.dump(board, open(tmp_path / "storyboard.json", "w"))
    props, _ = rr.film_props(str(tmp_path), board)
    assert "style" not in props
    style = _spec(line={"outline": "all"})
    props, _ = rr.film_props(str(tmp_path), dict(board, meta=dict(board["meta"], style=style)))
    assert props["style"] == style


def test_validate_reports_a_bad_style_on_a_remotion_board():
    import validate
    errors, warnings = [], []
    validate._check_style({"style": _spec(fill={"mode": "watercolour"})}, errors, warnings)
    assert any("style.fill.mode" in e for e in errors), errors
    errors, warnings = [], []
    validate._check_style({}, errors, warnings)                 # no style: nothing to say
    assert errors == [] and warnings == []
    src = open(os.path.join(ROOT, "scripts", "validate.py"), encoding="utf-8").read()
    body = src[src.index("def _check_remotion("):]
    body = body[:body.index("\ndef ")]
    assert "_check_style(meta, errors, warnings)" in body, "_check_remotion does not run the style check"


def test_film_takes_the_style_and_provides_it():
    film = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert re.search(r"style\?: StyleSpec \| null", film), "Film does not declare the style prop"
    assert "<StyleContext.Provider value=" in film, "Film does not provide the style"
