"""A GENERATED surface (surface.source: 'generated') — through the Codex subscription, never a metered API by default.

The Codex account has been on a free plan with no image tool (2026-10-03), so the fallback is the ordinary path: the
procedural medium, with a shortfall recorded on the spec so the sample sheet says what was wanted and what was drawn.
Real generation cannot be verified here; these tests run the path with a stub generator.
"""
import json
import os

import numpy as np
import pytest
from PIL import Image

import imagegen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
needs_render = pytest.mark.skipif(not os.environ.get("STYLE_RENDER"), reason="renders: set STYLE_RENDER=1 (under rlock)")

_SPEC = {"name": "paper", "refs": [], "refs_missing": "t", "surface": {"kind": "paper", "strength": 0.6,
                                                                        "source": "generated"}}


def _film(tmp_path):
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "remotion", "style": _SPEC},
                                                          "slides": []}))
    return str(tmp_path)


def _no_metered(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the metered API was called")
    monkeypatch.setattr(imagegen, "generate", boom)


def test_no_codex_falls_back_with_a_shortfall(tmp_path, monkeypatch):
    _no_metered(monkeypatch)
    monkeypatch.setattr(imagegen, "_codex_available", lambda: False)
    d = _film(tmp_path)
    assert imagegen.texture(d, "paper", 0.6) is None
    sf = json.load(open(os.path.join(d, "storyboard.json")))["meta"]["style"]["shortfalls"]
    assert len(sf) == 1 and sf[0]["axis"] == "surface.source" and sf[0]["got"] == "procedural", sf
    imagegen.texture(d, "paper", 0.6)                                    # a second miss records it once
    assert len(json.load(open(os.path.join(d, "storyboard.json")))["meta"]["style"]["shortfalls"]) == 1


def test_a_codex_failure_is_a_shortfall_with_its_reason(tmp_path, monkeypatch):
    _no_metered(monkeypatch)
    monkeypatch.setattr(imagegen, "_codex_available", lambda: True)
    def fail(prompt, out_path, size="1024x1024", quality="medium"):
        raise RuntimeError("codex produced no image")
    monkeypatch.setattr(imagegen, "_generate_codex", fail)
    d = _film(tmp_path)
    assert imagegen.texture(d, "paper", 0.6) is None
    why = json.load(open(os.path.join(d, "storyboard.json")))["meta"]["style"]["shortfalls"][0]["why"]
    assert "codex produced no image" in why


def test_texture_prompt_forbids_text_and_subjects():
    p = imagegen.texture_prompt("canvas").lower()
    assert "no text" in p and "no objects" in p and "seamless" in p and "canvas" in p


def test_stub_texture_is_used_when_present(tmp_path, monkeypatch):
    _no_metered(monkeypatch)
    monkeypatch.setattr(imagegen, "_codex_available", lambda: True)
    def stub(prompt, out_path, size="1024x1024", quality="medium"):
        rng = np.random.default_rng(3)
        a = (200 + 40 * rng.random((1024, 1024))).astype(np.uint8)        # a paper-ish grey with tooth
        Image.fromarray(a).convert("RGB").save(out_path)
    monkeypatch.setattr(imagegen, "_generate_codex", stub)
    d = _film(tmp_path)
    got = imagegen.texture(d, "paper", 0.6)
    assert set(got) == {"light", "dark"}
    light = np.asarray(Image.open(os.path.join(d, got["light"])).convert("L")).astype(float)
    dark = np.asarray(Image.open(os.path.join(d, got["dark"])).convert("L")).astype(float)
    assert light.mean() > 240 and light.std() > 2, (light.mean(), light.std())     # grain on white: multiplies
    assert dark.mean() < 15 and dark.std() > 1, (dark.mean(), dark.std())          # grain on black: screens
    # seamless: the tile's opposite edges match (it is mirrored)
    assert np.abs(light[:, 0] - light[:, -1]).mean() < 1 and np.abs(light[0] - light[-1]).mean() < 1
    assert "shortfalls" not in json.load(open(os.path.join(d, "storyboard.json")))["meta"]["style"]
    calls = []
    monkeypatch.setattr(imagegen, "_generate_codex", lambda *a, **k: calls.append(1))
    assert imagegen.texture(d, "paper", 0.6) == got and calls == []         # cached: generated once


def test_the_render_props_carry_a_generated_texture(tmp_path):
    import render_remotion as rr
    d = _film(tmp_path)
    assert rr.style_texture_props(json.load(open(os.path.join(d, "storyboard.json")))["meta"], d) is None
    os.makedirs(os.path.join(d, "style"))
    for k in ("light", "dark"):
        Image.new("RGB", (8, 8), "white").save(os.path.join(d, "style", "surface-paper-%s.png" % k))
    got = rr.style_texture_props(json.load(open(os.path.join(d, "storyboard.json")))["meta"], d)
    assert got == {"light": "style/surface-paper-light.png", "dark": "style/surface-paper-dark.png"}


@needs_render
def test_a_generated_tile_textures_the_ground(tmp_path):
    import subprocess
    stripes = np.full((64, 64, 3), 255, np.uint8)
    stripes[:, ::8] = 180                                                # a pattern no procedural noise makes
    os.makedirs(tmp_path / "style")
    Image.fromarray(stripes).save(tmp_path / "style" / "t-light.png")
    Image.fromarray(255 - stripes).save(tmp_path / "style" / "t-dark.png")
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps({"style": _SPEC, "styleTexture": {"light": "style/t-light.png", "dark": "style/t-dark.png"}}))
    out = tmp_path / "st.png"
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "StyleProbe", str(out), "--frame=10", "--gl=angle",
                        "--log=error", "--props=" + str(pf), "--public-dir=" + str(tmp_path)],
                       cwd=os.path.join(ROOT, "remotion"), capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    full = np.asarray(Image.open(out).convert("L")).astype(float)
    cols = full[60:160, 1300:1700].mean(axis=0)
    assert cols.max() - cols.min() > 20, "the generated tile's stripes are not on the ground"
    rect = full[260:440, 260:540].mean(axis=0)                          # inside the SVG rect: the filter path
    assert rect.max() - rect.min() > 15, "the generated tile's stripes are not on the SVG drawing"
