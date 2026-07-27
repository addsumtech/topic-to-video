"""P0 backward-compat backstop — the LEGACY (non-shot) Remotion props contract.

The shot-based refactor is additive: build_props may GAIN keys (a later phase adds e.g.
stage/shots/transitionPreset), but it must NOT change or drop any field a legacy image /
camera / lens board already produces. That guarantee is what lets the HTML + existing
Remotion boards keep rendering identically while the cinematic engine grows.

Semantics: each golden asserts CONTAINMENT — every frozen key must equal the built value;
new keys are allowed. So an intended additive prop won't fail these, but any regression to a
legacy field's value will fail loudly. Frozen from build_props output on 2026-07-27.
"""
import render_remotion as rr
import storyboard as sb


def _img_board():
    m = {"language": "en", "aspect": "16:9", "captions": True, "fps": 30, "renderer": "remotion"}
    d = sb.new_storyboard(m)
    s = sb.new_scene(1, "title", {"kicker": "K", "title": "T"}, narration="Alpha beta gamma delta.")
    s["image"] = ".assets/x.png"; s["audio"] = "audio/01.mp3"; s["duration"] = 4.0
    s["transition"] = "dip"; s["transition_seconds"] = 0.2
    d["slides"] = [s]
    return d


def _lens_board():
    m = {"aspect": "16:9", "fps": 30, "renderer": "remotion"}
    d = sb.new_storyboard(m)
    s = sb.new_scene(1, "cinematic", {}, narration="Depth.")
    s["audio"] = "audio/01.mp3"; s["duration"] = 6.0; s["perspective"] = 1250
    s["layers"] = [{"kind": "grid", "z": -1200, "blur": 8}, {"kind": "panel", "z": 120, "title": "T"}]
    s["lens"] = [{"atFrame": 0, "dolly": -500, "pitch": 30, "yaw": 10, "easing": "inout"},
                 {"atFrame": 180, "dolly": 200, "pitch": 4, "yaw": -2, "easing": "inout"}]
    d["slides"] = [s]
    return d


GOLDEN_IMAGE_SCENE = {
    "index": 1, "audio": "audio/01.mp3", "image": ".assets/x.png", "kicker": "K", "title": "T",
    "durationInFrames": 120, "fadeInFrames": 6, "fadeOutFrames": 6, "fit": "contain",
    "kenburns": True, "camera": None, "layers": None, "lens": None, "perspective": None,
    "reducedMotion": False, "callouts": [],
    "motion": {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
    "captions": [{"from": 0, "text": "Alpha beta gamma delta.", "to": 120}],
}

GOLDEN_LENS_SCENE = {
    "index": 1, "audio": "audio/01.mp3", "image": None, "kicker": None, "title": None,
    "durationInFrames": 180, "fadeInFrames": 6, "fadeOutFrames": 6, "fit": "contain",
    "kenburns": False, "camera": None, "perspective": 1250.0, "reducedMotion": False, "callouts": [],
    "layers": [{"blur": 8.0, "kind": "grid", "z": -1200.0}, {"kind": "panel", "title": "T", "z": 120.0}],
    "lens": [{"atFrame": 0, "dolly": -500.0, "easing": "inout", "pitch": 30.0, "roll": 0.0, "yaw": 10.0, "zoom": 1.0},
             {"atFrame": 180, "dolly": 200.0, "easing": "inout", "pitch": 4.0, "roll": 0.0, "yaw": -2.0, "zoom": 1.0}],
    "motion": {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
    "captions": [{"from": 0, "text": "Depth.", "to": 180}],
}


def _assert_contains(actual, golden):
    diffs = ["%s: expected %r, got %r" % (k, v, actual.get(k)) for k, v in golden.items() if actual.get(k) != v]
    assert not diffs, "legacy Remotion props regressed:\n  " + "\n  ".join(diffs)


def test_golden_legacy_image_scene(tmp_path):
    _assert_contains(rr.build_props(_img_board(), str(tmp_path))["scenes"][0], GOLDEN_IMAGE_SCENE)


def test_golden_legacy_lens_scene(tmp_path):
    _assert_contains(rr.build_props(_lens_board(), str(tmp_path))["scenes"][0], GOLDEN_LENS_SCENE)


def test_golden_top_level_props(tmp_path):
    p = rr.build_props(_img_board(), str(tmp_path))
    assert (p["width"], p["height"], p["fps"], p["captionFontPx"]) == (1920, 1080, 30, 43)
    # base 5 theme colours keep their fallback values; the reader may ADD keys in a later phase.
    for k, v in {"bg": "#0d1117", "fg": "#f0f3f8", "muted": "#94989e",
                 "accent": "#5fb3c4", "accent2": "#e0894a"}.items():
        assert p["theme"][k] == v


def test_theme_reader_parses_extended_tokens(tmp_path):
    """P1: the widened _theme() must read the full token set theme.py emits — colours (surface/scrim/
    on-accent), the type FACES (a comma-stack survives whole), style/radius/grain/tracking — so the
    cinematic tier renders the deck's real design world, not a 5-colour + mono placeholder."""
    import theme as th
    theme = {"bg": "#0b0e14", "surface": "#141a24", "fg": "#eef2f8", "muted": "#8b97a8",
             "accent": "#e3b23c", "accent2": "#5fb3c9", "scrim": "rgba(11,14,20,.55)",
             "on_accent": "#000000", "on_accent2": "#ffffff", "style": "editorial",
             "style_vars": {"radius": "6px", "grain": ".10", "ink": "wash"}, "language": "en"}
    th.write_theme_css(theme, str(tmp_path / "theme.css"))
    t = rr._theme(str(tmp_path))
    assert t["surface"] == "#141a24" and t["scrim"] == "rgba(11,14,20,.55)" and t["onAccent"] == "#000000"
    assert t["fontKind"] == "serif" and t["style"] == "editorial" and t["radius"] == "6px"
    assert t["grainAmount"] == ".10"
    assert t["fontDisplay"].startswith('"Playfair Display"') and t["fontDisplay"].endswith("serif")  # full stack
    assert t["fontNumber"].startswith('"Space Grotesk"')                                              # lining figures


def test_theme_reader_fallbacks_when_themeless(tmp_path):
    """No theme.css -> the extended tokens fall back to today's implicit look (additive-safe)."""
    t = rr._theme(str(tmp_path))
    assert t["bg"] == "#0d1117" and t["fontKind"] == "sans" and t["grainAmount"] == "0"
    assert t["fontDisplay"].startswith('"Space Grotesk"')
