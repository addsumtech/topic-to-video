"""Backstops for the Phase-2 cinematic COMPONENTS (frame-driven, generalisable): spotlight (travelling
light-pool), hud (FUI reticle + corner readout), connector (draw-on line/arrow). Each is a pure function of
the frame; these guard that the fields thread through build_props and that the TS render branches survive."""
import os
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
import render_remotion as rr  # noqa: E402
import storyboard as sb  # noqa: E402
import validate as v  # noqa: E402


def _board(elements):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = 6.0
    s["stage"] = {"elements": elements}
    s["shots"] = [{"type": "MEDIUM", "target": elements[0]["id"], "duration": 6.0}]
    d["slides"] = [s]
    return d


def test_new_kinds_are_known():
    for k in ("spotlight", "hud", "connector"):
        assert k in v._ELEM_KINDS


def test_spotlight_fields_thread(tmp_path):
    el = {"id": "s", "kind": "spotlight", "position": [0, 0, 0], "sweep": [-0.5, 0.5], "sweepSpan": 120, "hue": "#37E0FF"}
    out = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert out["sweep"] == [-0.5, 0.5] and out["sweepSpan"] == 120 and out["hue"] == "#37E0FF"


def test_hud_fields_thread(tmp_path):
    el = {"id": "h", "kind": "hud", "position": [0, 0, 0], "hudLabel": "SYS", "hudStatus": "locked", "lockAtFrame": 70}
    out = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert out["hudLabel"] == "SYS" and out["hudStatus"] == "locked" and out["lockAtFrame"] == 70


def test_connector_fields_thread(tmp_path):
    el = {"id": "c", "kind": "connector", "position": [0, 0, 0], "to": [560, 0], "arrow": True,
          "strokeColor": "#ffb020", "drawAtFrame": 40}
    out = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert out["to"] == [560, 0] and out["arrow"] is True and out["strokeColor"] == "#ffb020" and out["drawAtFrame"] == 40


def test_bad_tuple_fails_loud(tmp_path):
    el = {"id": "s", "kind": "spotlight", "position": [0, 0, 0], "sweep": [0.5]}  # must be [a,b]
    with pytest.raises(RuntimeError, match="must be"):
        rr.build_props(_board([el]), str(tmp_path))


def test_component_branches_present_in_tsx():
    el = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    assert "kind === 'spotlight'" in el and "kind === 'hud'" in el and "kind === 'connector'" in el
    assert "strokeDashoffset" in el, "connector draw-on lost"
    assert "mixBlendMode" in el, "spotlight light-pool lost"


def test_hud_spotlight_render_screen_fixed_not_in_world():
    # the audit bug: a HUD/spotlight placed in the preserve-3d world pans/scales with the camera. They must be
    # partitioned out and rendered in the OUTER 2D overlay (siblings of Finish), centred on the viewport.
    st = open(os.path.join(_SKILL, "remotion", "src", "stage", "SceneStage.tsx"), encoding="utf-8").read()
    assert "OVERLAY_KINDS" in st and "worldEls" in st and "overlayEls" in st
    assert "'hud'" in st and "'spotlight'" in st


def test_color_worlds_wired_into_render_pipeline(tmp_path):
    """The audit's #1 fix: cine_palette is WIRED into the render path. A card with a `colorWorld` spec + a
    template + accent gets its aurora page GENERATED automatically (not by a hand-run script)."""
    (tmp_path / "theme.css").write_text(":root{--accent:#e0a020;}")
    data = {"meta": {"renderer": "remotion", "cinematic_template": "molten-ledger", "accent": "#e0a020"},
            "slides": [{"index": 1, "type": "cinematic", "stage": {"elements": [
                {"id": "cw", "kind": "card", "position": [0, 0, 0], "size": [2000, 1125],
                 "colorWorld": {"title": "收入", "kicker": "Q3", "grad": "翻倍", "sub": "核实"}}]}}]}
    rr._generate_color_worlds(data, str(tmp_path))
    el = data["slides"][0]["stage"]["elements"][0]
    assert el.get("html", "").startswith("pages/"), "colorWorld card must get a GENERATED html page"
    assert (tmp_path / el["html"]).exists(), "the generated aurora page must be written to disk"


def test_color_worlds_noop_without_template(tmp_path):
    data = {"meta": {"renderer": "remotion"}, "slides": [{"index": 1, "type": "cinematic", "stage": {"elements": [
        {"id": "cw", "kind": "card", "position": [0, 0, 0], "colorWorld": {"title": "x"}}]}}]}
    rr._generate_color_worlds(data, str(tmp_path))  # no template -> no-op, no crash
    assert data["slides"][0]["stage"]["elements"][0].get("html") is None


# ── template contest mechanical trace (a hardcoded single template must not pass as a contest) ──────────
def _cine(extra=None):
    m = {"renderer": "remotion", "fps": 30, "cinematic_template": "defrag", "accent": "#37e0ff"}
    m.update(extra or {})
    return {"meta": m, "slides": [{"index": 1, "type": "cinematic", "archetype": "hero-on-void", "duration": 5,
            "narration": "x", "stage": {"elements": [{"id": "a", "kind": "display", "text": "x", "position": [0, 0, 0]}]},
            "shots": [{"type": "HERO", "target": "a"}]}]}


def test_template_contest_required_at_bold_audacity():
    r = v.evaluate(_cine({"audacity": "bold"}), "/tmp", pre_tts=True)
    assert any("template_contest" in e for e in r["errors"]), "bold audacity must ERROR without a contest record"


def test_template_contest_shape_validated():
    r = v.evaluate(_cine({"template_contest": {"candidates": ["defrag"], "winner": "defrag"}}), "/tmp", pre_tts=True)
    assert any("candidates" in e for e in r["errors"]), "<2 candidates must error"
    r2 = v.evaluate(_cine({"template_contest": {"candidates": ["defrag", "command-surface"], "winner": "command-surface"}}),
                    "/tmp", pre_tts=True)
    assert any("winner" in e for e in r2["errors"]), "winner != chosen template must error"


def test_valid_template_contest_passes():
    r = v.evaluate(_cine({"audacity": "bold", "template_contest": {
        "candidates": ["defrag", "command-surface"], "winner": "defrag", "user_pick": True}}), "/tmp", pre_tts=True)
    assert not any("template_contest" in e for e in r["errors"]), "a valid contest record must pass"


# ── transition honesty: a 'blur' seam has no rack-defocus presentation yet → it must WARN it approximates ──
def test_blur_seam_warns_it_is_approximated_on_remotion():
    d = _cine()
    d["slides"][0]["transition_style"] = "blur"
    r = v.evaluate(d, "/tmp", pre_tts=True)
    assert any("blur" in w and "cross-dissolve" in w for w in r["warnings"]), \
        "a 'blur' seam renders as a fade on the Remotion tier — the approximation must make a noise, not ship silently"


def test_known_seam_style_does_not_warn():
    d = _cine()
    d["slides"][0]["transition_style"] = "wipe"  # a real, distinct presentation
    r = v.evaluate(d, "/tmp", pre_tts=True)
    assert not any("transition_style" in w and "wipe" in w for w in r["warnings"])
