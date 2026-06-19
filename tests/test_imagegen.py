import os, sys, json, base64, types
import imagegen

# a 1x1 PNG, base64 (used as the fake API payload)
_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhV" "AAAAAElFTkSuQmCC")

def test_cache_key_stable_and_varies():
    a = imagegen._cache_key("a rocket", "gpt-image-2", "1536x1024", "medium")
    assert a == imagegen._cache_key("a rocket", "gpt-image-2", "1536x1024", "medium")
    assert a != imagegen._cache_key("a rocket", "gpt-image-2", "1536x1024", "high")
    assert a != imagegen._cache_key("a planet", "gpt-image-2", "1536x1024", "medium")

def test_cache_path_under_assets(tmp_path):
    p = imagegen._cache_path(str(tmp_path), "x", "gpt-image-2", "1536x1024", "medium")
    assert os.path.dirname(p).endswith(".assets") and p.endswith(".png")

def test_cost_estimate_monotonic():
    assert imagegen.cost_estimate(1, "low") < imagegen.cost_estimate(1, "medium") < imagegen.cost_estimate(1, "high")
    assert imagegen.cost_estimate(4, "medium") == round(4 * imagegen.cost_estimate(1, "medium"), 3)

def test_generate_builds_request_and_writes(tmp_path, monkeypatch):
    captured = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"data": [{"b64_json": _PNG_B64}]}
    fake = types.ModuleType("requests")
    def post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, body=json); return _Resp()
    fake.post = post
    monkeypatch.setitem(sys.modules, "requests", fake)
    out = str(tmp_path / "img.png")
    imagegen.generate("a generic rocket", out, "sk-test", size="1536x1024", quality="medium")
    assert captured["url"] == imagegen.API_URL
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["body"]["model"] == "gpt-image-2"
    assert captured["body"]["prompt"] == "a generic rocket"
    assert captured["body"]["size"] == "1536x1024" and captured["body"]["quality"] == "medium"
    assert captured["body"]["n"] == 1
    assert os.path.exists(out) and open(out, "rb").read()[:4] == b"\x89PNG"

def test_generate_no_key_raises(tmp_path):
    import pytest
    with pytest.raises(RuntimeError):
        imagegen.generate("x", str(tmp_path / "y.png"), "", )
