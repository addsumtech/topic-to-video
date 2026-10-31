"""The style sample and the sign-off the full render waits for.

Every styled film shows the user 2–3 beats beside the references BEFORE the full render (a decision the user made,
2026-10-31): a style decomposed wrong costs one sample, not a film. The sign-off records the spec it approved, so a
spec changed afterwards needs a new one; `--sample` renders are always allowed (they are how a sample is made).
"""
import json
import os
import shutil
import subprocess

import pytest
from PIL import Image

import style_sample as ss

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
needs_render = pytest.mark.skipif(not os.environ.get("STYLE_RENDER"), reason="renders: set STYLE_RENDER=1 (under rlock)")

_SPEC = {"name": "ink + flat", "refs": [{"src": "style_refs/a.png", "from": "found"}],
         "line": {"outline": "all", "weight": 4, "color": "ink"}, "fill": {"mode": "flat"}}


def _board(shots, style=_SPEC, **meta):
    m = {"renderer": "remotion", "aspect": "16:9"}
    if style is not None:
        m["style"] = style
    m.update(meta)
    return {"meta": m, "slides": [{"index": i + 1, "shot": s, "shot_props": p, "duration": 4.0}
                                  for i, (s, p) in enumerate(shots)]}


def test_pick_beats_spans_families():
    board = _board([("CinematicTitle", {}), ("KnowledgeGraph", {}), ("PhotoPlate", {"src": "x.png"}),
                    ("ObjectStage", {"object": {"id": "GpsSatellite"}}), ("ChartLive", {}), ("ElasticType", {})])
    picked = ss.pick_beats(board)
    assert 2 <= len(picked) <= 3
    shots = [board["slides"][i - 1]["shot"] for i in picked]
    assert "ObjectStage" in shots                                         # the object beat
    assert "PhotoPlate" not in shots                                      # never a beat the style cannot reach
    assert any(s in ("KnowledgeGraph", "ChartLive") for s in shots)       # a data/diagram beat
    assert any(s in ("CinematicTitle", "ElasticType") for s in shots)     # a type-led beat


def test_pick_beats_fills_from_what_there_is():
    assert len(ss.pick_beats(_board([("ChartLive", {}), ("FlowSankey", {})]))) == 2
    assert ss.pick_beats(_board([("PhotoPlate", {"src": "x"})])) == []


def test_sheet_notes_say_what_the_user_must_know():
    spec = dict(_SPEC, refs=[], refs_missing="web search refused",
                shortfalls=[{"axis": "surface.source", "wanted": "generated", "got": "procedural", "why": "no codex"}])
    notes = ss.sheet_notes(spec, _board([("PhotoPlate", {"src": "x"}), ("ChartLive", {})], style=spec))
    assert "no references" in notes["title"].lower() and "web search refused" in notes["title"]
    body = "\n".join(notes["lines"])
    assert "surface.source" in body and "procedural" in body
    assert "PhotoPlate" in body                                           # the beat the style cannot reach
    flat = dict(name="as drawn", refs=_SPEC["refs"])
    assert any("only the palette" in ln for ln in ss.sheet_notes(flat, _board([("ChartLive", {})], style=flat))["lines"])


def test_full_render_refused_without_signoff_and_a_sample_is_not():
    import render_remotion as rr
    board = _board([("ChartLive", {})])
    assert "sign-off" in (rr.style_refusal(board, sample=None) or "")
    assert rr.style_refusal(board, sample=1) is None
    assert rr.style_refusal(_board([("ChartLive", {})], style=None), sample=None) is None


def test_signoff_goes_stale_when_spec_changes(tmp_path):
    import render_remotion as rr
    import validate
    board = _board([("ChartLive", {})])
    (tmp_path / "_style").mkdir()
    (tmp_path / "_style" / "sample.json").write_text(json.dumps({"sample_sha256": "abc", "spec_sha256": ss.spec_hash(_SPEC)}))
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    ss.record_signoff(str(tmp_path))
    board = json.load(open(tmp_path / "storyboard.json"))
    assert board["meta"]["style_signoff"]["user_ok"] is True
    assert rr.style_refusal(board, sample=None) is None
    errs, warns = [], []
    validate._check_style(board["meta"], errs, warns)
    assert errs == [] and not any("sign-off" in w for w in warns)
    board["meta"]["style"] = dict(_SPEC, fill={"mode": "cel", "steps": 3})
    assert "stale" in (rr.style_refusal(board, sample=None) or "")
    errs, warns = [], []
    validate._check_style(board["meta"], errs, warns)
    assert any("stale" in e for e in errs), errs


def test_no_signoff_is_a_warning_not_an_error_before_the_sample():
    import validate
    errs, warns = [], []
    validate._check_style(_board([("ChartLive", {})])["meta"], errs, warns)
    assert errs == [] and any("style_sample.py" in w for w in warns), warns


def test_signoff_needs_a_sample(tmp_path):
    (tmp_path / "storyboard.json").write_text(json.dumps(_board([("ChartLive", {})])))
    with pytest.raises(SystemExit):
        ss.record_signoff(str(tmp_path))


@needs_render
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg")
def test_build_delivers_a_sheet_and_a_clip(tmp_path):
    film = tmp_path / "film"
    (film / "audio").mkdir(parents=True)
    (film / "style_refs").mkdir()
    Image.new("RGB", (640, 360), (240, 200, 90)).save(film / "style_refs" / "a.png")
    slides = []
    for i, shot in enumerate(["ChartLive", "ElasticType", "ClayStack"]):
        a = film / "audio" / ("%02d.wav" % (i + 1))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(a)],
                       check=True)
        slides.append({"index": i + 1, "shot": shot, "duration": 3.0, "narration": "x", "caption": "",
                       "audio": "audio/%02d.wav" % (i + 1), "shot_props": {"word": "画法"} if shot == "ElasticType" else {}})
    board = {"meta": {"renderer": "remotion", "aspect": "16:9", "title": "样张测试", "style": _SPEC}, "slides": slides}
    (film / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False))
    desk = tmp_path / "desk"
    desk.mkdir()
    rep = ss.build(str(film), to=str(desk))
    assert os.path.isfile(rep["png"]) and os.path.isfile(rep["mp4"])
    assert os.path.basename(rep["png"]) == "样张测试 风格样张.png"
    kept = json.load(open(film / "_style" / "sample.json"))
    assert kept["sample_sha256"] == rep["sample_sha256"] and kept["spec_sha256"] == ss.spec_hash(_SPEC)
