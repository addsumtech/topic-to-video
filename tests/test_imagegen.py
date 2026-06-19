import os, sys, json, base64, types
import imagegen
import storyboard as sb

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

def _board(tmp_path, source="openai", prompt="a generic rocket"):
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    d = sb.new_storyboard({"image_source": source, "image_quality": "medium", "image_size": "1536x1024"})
    s = sb.new_slide(1, None); s["image"] = None; s["image_prompt"] = prompt; s["image_tag"] = "broll"
    s["narration"] = "intro"
    d["slides"] = [s]
    sb.save(d, os.path.join(out, "storyboard.json"))
    return str(out)

def test_synthesize_noop_when_free(tmp_path, monkeypatch):
    out = _board(tmp_path, source="none")
    called = {"n": 0}
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    imagegen.synthesize_images(out, key="sk-x")
    assert called["n"] == 0          # free tier -> no generation

def test_synthesize_generates_and_fills_image(tmp_path, monkeypatch):
    out = _board(tmp_path)
    def fake_gen(prompt, path, key, size, quality, model):
        os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "wb").write(b"\x89PNG")
    monkeypatch.setattr(imagegen, "generate", fake_gen)
    d = imagegen.synthesize_images(out, key="sk-x", date="2026-06-19")
    s = d["slides"][0]
    assert s["image"] and s["image"].startswith(".assets/") and s["image"].endswith(".png")
    assert os.path.exists(os.path.join(out, s["image"]))

def test_synthesize_uses_cache_skips_api(tmp_path, monkeypatch):
    out = _board(tmp_path)
    # pre-create the cache file so generate must NOT be called
    cp = imagegen._cache_path(out, "a generic rocket", imagegen.DEFAULT_MODEL, "1536x1024", "medium")
    os.makedirs(os.path.dirname(cp), exist_ok=True); open(cp, "wb").write(b"\x89PNG")
    called = {"n": 0}
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    d = imagegen.synthesize_images(out, key="sk-x")
    assert called["n"] == 0 and d["slides"][0]["image"].endswith(".png")

def test_synthesize_no_key_falls_back(tmp_path, monkeypatch):
    out = _board(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    d = imagegen.synthesize_images(out, key=None)   # no key -> generate raises -> caught
    assert d["slides"][0]["image"] is None           # left for free-tier fallback, no crash
