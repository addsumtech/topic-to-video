import os, sys, json, base64, types
import imagegen
import storyboard as sb
from PIL import Image
import pytest

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

def _board(tmp_path, source="openai", provider="auto", prompt="a generic rocket"):
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    meta = {"image_source": source, "image_quality": "medium", "image_size": "1536x1024"}
    if provider != "auto":  # only add provider if it's not auto
        meta["image_provider"] = provider
    d = sb.new_storyboard(meta)
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
    out = _board(tmp_path, source="openai", provider="openai")
    def fake_gen(prompt, path, key, size, quality, model):
        os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "wb").write(b"\x89PNG")
    monkeypatch.setattr(imagegen, "generate", fake_gen)
    d = imagegen.synthesize_images(out, key="sk-x", date="2026-06-19")
    s = d["slides"][0]
    assert s["image"] and s["image"].startswith(".assets/") and s["image"].endswith(".png")
    assert os.path.exists(os.path.join(out, s["image"]))

def test_synthesize_uses_cache_skips_api(tmp_path, monkeypatch):
    out = _board(tmp_path, source="openai", provider="openai")
    # pre-create the cache file so generate must NOT be called
    cp = imagegen._cache_path(out, "a generic rocket", imagegen.DEFAULT_MODEL, "1536x1024", "medium")
    os.makedirs(os.path.dirname(cp), exist_ok=True); open(cp, "wb").write(b"\x89PNG")
    called = {"n": 0}
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    d = imagegen.synthesize_images(out, key="sk-x")
    assert called["n"] == 0 and d["slides"][0]["image"].endswith(".png")

def test_synthesize_no_key_falls_back(tmp_path, monkeypatch):
    out = _board(tmp_path, source="openai", provider="openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(imagegen, "_read_key_file", lambda: None)  # mock to prevent reading ~/.openai_key
    d = imagegen.synthesize_images(out, key=None)   # no key -> generate raises -> caught
    assert d["slides"][0]["image"] is None           # left for free-tier fallback, no crash

def _valid_png(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (8, 8), (10, 20, 30)).save(path)

def test_codex_available(monkeypatch):
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: "/usr/bin/codex" if n == "codex" else None)
    assert imagegen._codex_available() is True
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: None)
    assert imagegen._codex_available() is False

def test_generate_codex_builds_command_and_validates(tmp_path, monkeypatch):
    out = str(tmp_path / ".assets" / "x.png")
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: "/usr/bin/codex")
    cap = {}
    def fake_run(cmd, **kw):
        cap["cmd"] = cmd; cap["kw"] = kw
        _valid_png(out)                       # simulate codex producing the image
    monkeypatch.setattr(imagegen.subprocess, "run", fake_run)
    imagegen._generate_codex("a generic rocket", out, "1536x1024", "medium")
    cmd = cap["cmd"]
    assert cmd[0] == "/usr/bin/codex" and cmd[1] == "exec"
    assert "--skip-git-repo-check" in cmd and "workspace-write" in cmd and "-C" in cmd
    assert out in cmd[-1] and "a generic rocket" in cmd[-1]
    assert all(("Bearer" not in str(c)) and ("sk-" not in str(c)) for c in cmd)   # no key anywhere
    assert cap["kw"].get("capture_output") is True and cap["kw"].get("timeout") == 600
    assert os.path.exists(out)

from PIL import UnidentifiedImageError  # noqa: E402
def test_generate_codex_raises_when_no_image(tmp_path, monkeypatch):
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: "/usr/bin/codex")
    monkeypatch.setattr(imagegen.subprocess, "run", lambda cmd, **kw: None)   # writes nothing
    with pytest.raises(RuntimeError):
        imagegen._generate_codex("x", str(tmp_path / ".assets" / "y.png"))


def test_synthesize_auto_prefers_codex_no_key(tmp_path, monkeypatch):
    out = _board(tmp_path, source="openai", provider="auto")
    monkeypatch.setattr(imagegen, "_codex_available", lambda: True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    codex_calls = []; openai_calls = []
    monkeypatch.setattr(imagegen, "_generate_codex",
        lambda prompt, cp, size, quality: (codex_calls.append(cp), _valid_png(cp)))
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: openai_calls.append(a))
    d = imagegen.synthesize_images(out, key=None)
    assert len(codex_calls) == 1 and len(openai_calls) == 0     # codex used, no key
    img = d["slides"][0]["image"]
    assert img and "codex" in open(os.path.join(out, img[:-4] + ".json")).read()   # provider in manifest

def test_synthesize_auto_falls_to_openai_when_no_codex(tmp_path, monkeypatch):
    out = _board(tmp_path, source="openai", provider="auto")
    monkeypatch.setattr(imagegen, "_codex_available", lambda: False)
    calls = []
    monkeypatch.setattr(imagegen, "generate",
        lambda prompt, cp, key, size, quality, model: (calls.append(model), _valid_png(cp)))
    imagegen.synthesize_images(out, key="sk-test")
    assert calls and calls[0] == imagegen.DEFAULT_MODEL          # openai path, gpt-image-2

def test_synthesize_codex_cache_path_distinct(tmp_path):
    # codex (model 'codex') and openai (DEFAULT_MODEL) hash to different cache files
    a = imagegen._cache_path(str(tmp_path), "p", "codex", "1536x1024", "medium")
    b = imagegen._cache_path(str(tmp_path), "p", imagegen.DEFAULT_MODEL, "1536x1024", "medium")
    assert a != b
