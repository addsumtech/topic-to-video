import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import register_ledger as rl


def _mk_deck(d, register="画布register", style="custom", winner="C"):
    d.mkdir(parents=True, exist_ok=True)
    (d / "design_plan.json").write_text(json.dumps({
        "design_register": {"name": register, "motion_personality": "precise: x"},
        "visual_style": style,
        "register_contest": {"winner": winner, "candidates": [{"key": "C", "angle": "metaphor-embodied"}]},
        "beats": {}}, ensure_ascii=False))
    (d / "storyboard.json").write_text(json.dumps({"meta": {"language": "zh"}, "slides": []}))
    (d / "theme.css").write_text(":root{ --bg:#fbfaf6; --accent:#2f7ce8; }")


def test_record_and_recent_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDES_TO_VIDEO_HOME", str(tmp_path / "home"))
    _mk_deck(tmp_path / "deckA")
    e = rl.record(str(tmp_path / "deckA"))
    assert e and e["register"] == "画布register" and e["mode"] == "light" and e["accent"] == "#2f7ce8"
    assert e["angle"] == "metaphor-embodied" and e["language"] == "zh"
    got = rl.recent()
    assert len(got) == 1 and got[0]["deck"] == "deckA"


def test_record_dedupes_same_deck_and_caps(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDES_TO_VIDEO_HOME", str(tmp_path / "home"))
    _mk_deck(tmp_path / "deckA")
    rl.record(str(tmp_path / "deckA"))
    rl.record(str(tmp_path / "deckA"))          # re-delivering updates, not duplicates
    assert len(rl.recent(10)) == 1
    for i in range(15):
        _mk_deck(tmp_path / f"d{i}", register=f"r{i}")
        rl.record(str(tmp_path / f"d{i}"))
    assert len(rl.recent(99)) == rl._KEEP        # capped


def test_record_nothing_without_register(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDES_TO_VIDEO_HOME", str(tmp_path / "home"))
    d = tmp_path / "bare"; d.mkdir()
    (d / "design_plan.json").write_text(json.dumps({"beats": {}}))
    assert rl.record(str(d)) is None
    assert rl.recent() == []
