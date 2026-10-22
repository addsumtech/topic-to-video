"""The per-beat caches in shot_proof and text_safe_qa keep only an ANSWER: a failed render is asked again."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import shot_proof as sp  # noqa: E402
import text_safe_qa as ts  # noqa: E402


def test_shot_proof_keeps_and_finds_a_render_by_key(tmp_path, monkeypatch):
    proof = str(tmp_path)
    png = tmp_path / "beat_01.png"
    png.write_bytes(b"\x89PNG-1")
    assert sp._cached(proof, "k1", ".png") is None
    sp._keep(proof, "k1", ".png", src=str(png))
    assert open(sp._cached(proof, "k1", ".png"), "rb").read() == b"\x89PNG-1"
    sp._keep(proof, "k1", ".unfed.json", data=[["w"], 1, ""])
    assert json.load(open(sp._cached(proof, "k1", ".unfed.json"))) == [["w"], 1, ""]
    monkeypatch.setattr(sp, "_NO_CACHE", True)
    assert sp._cached(proof, "k1", ".png") is None, "--no-cache renders everything"
    assert sp._cached(proof, None, ".png") is None, "no key, no reuse"


def test_text_safe_never_keeps_a_render_that_measured_nothing():
    assert ts._audit_failed([{"text": "(render FAILED twice — nothing was measured on this frame: x)", "out": {}}])
    assert ts._audit_failed([{"text": "(unparseable payload)", "out": {}}])
    assert not ts._audit_failed([])
    assert not ts._audit_failed([{"text": "Paris", "out": {"right": 12}}])


def test_text_safe_cache_round_trips(tmp_path):
    ts._save_beat_cache(str(tmp_path), {"k": {"title": {"text": "T"}, "audit": []}})
    assert ts._load_beat_cache(str(tmp_path)) == {"k": {"title": {"text": "T"}, "audit": []}}
    (tmp_path / ts.BEAT_CACHE).write_text("not json", encoding="utf-8")
    assert ts._load_beat_cache(str(tmp_path)) == {}
