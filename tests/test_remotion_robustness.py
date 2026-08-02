"""Generalization + robustness backstops for the Remotion cinematic tier — each guards one edge-case fix
found in the strict self-check (arbitrary topics/styles/aspects/languages/data a real user WILL throw at it):

  1. sound-design SFX synthesis is DETERMINISTIC across processes (str hash() is PYTHONHASHSEED-salted, so
     the noise cues used to synthesize a different waveform every render — the frame-driven determinism law).
  2. the 3D-text rasterizer detects non-Latin (CJK/Kana/Hangul) labels the bundled Latin faces can't cover,
     and either routes them to a system CJK font or WARNS — never silently ships .notdef tofu.
  3. a `stack` plane with a large count is capped in the renderer AND flagged by validate (one cube per unit
     would be hundreds of shadow-casters that never finish accreting; use `bars` for magnitudes).
  4. a NaN/Infinity in plane `data` is a hard ERROR (it blanks the WebGL render), on the shot-based /
     cinematic3d paradigm too (which returns before the legacy cam/lens NaN checks).
  5. the 9:16 landscape-tuning overflow warning covers cinematic3d, not only `type:"cinematic"`.
"""
import os
import subprocess
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))

import validate as v  # noqa: E402


# ── 1. SFX determinism across processes ───────────────────────────────────────────────────────────────
def _cue_digest(seed):
    """Synthesize the noise cues in a FRESH process under a given PYTHONHASHSEED; return a stable digest."""
    code = (
        "import sys,hashlib; sys.path.insert(0,%r); import sfx\n"
        "h=hashlib.sha1()\n"
        "for n in ('click','whoosh','tick','reveal'):\n"
        "    a=sfx.cue(n)\n"
        "    h.update(a.tobytes() if a is not None else b'none')\n"
        "print(h.hexdigest())\n" % os.path.join(_SKILL, "scripts")
    )
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    return out.stdout.strip(), out.stderr


def test_sfx_synthesis_is_deterministic_across_process_hash_seeds():
    pytest.importorskip("numpy")
    d0, e0 = _cue_digest(0)
    d1, e1 = _cue_digest(1)
    assert d0 and d1, "sfx.cue produced no output: %s %s" % (e0, e1)
    assert d0 == d1, (
        "SFX cue synthesis differs across PYTHONHASHSEED (%s vs %s) — a re-render is not reproducible; "
        "the seed must derive from a STABLE hash (zlib.crc32), not str hash()" % (d0, d1)
    )


# ── 2. CJK / non-Latin rasterizer degradation ─────────────────────────────────────────────────────────
import render_remotion as rr  # noqa: E402


def test_needs_nonlatin_detects_cjk_not_latin():
    assert rr._needs_nonlatin("增长率") is True
    assert rr._needs_nonlatin("ﾃｽﾄ") is True          # halfwidth kana
    assert rr._needs_nonlatin("한글") is True
    assert rr._needs_nonlatin("Growth 4,200%") is False
    assert rr._needs_nonlatin("") is False


def test_cjk_label_warns_when_no_cjk_font_available(tmp_path, monkeypatch, capsys):
    """With no system CJK font, a CJK bar label must WARN (fail loud) rather than silently rasterize tofu."""
    pytest.importorskip("PIL")
    monkeypatch.setattr(rr, "_resolve_cjk_font", lambda: None)
    data = {"slides": [{"index": 1, "type": "cinematic3d",
                        "planes": [{"kind": "bars", "data": [10, 20], "labels": ["增长", "下降"],
                                    "position": [0, 0, 0]}]}]}
    rr._rasterize_text3d(data, str(tmp_path))
    out = capsys.readouterr().out
    assert "[text3d]" in out and "non-Latin" in out, "no loud warning when a CJK label falls back to tofu"


def test_cjk_font_candidates_are_declared():
    assert rr._CJK_FONT_CANDIDATES, "no system CJK fallback fonts declared"
    assert all(p.endswith((".ttc", ".ttf", ".otf")) for p in rr._CJK_FONT_CANDIDATES)


# ── 3 + 4. plane data: large stack + NaN ───────────────────────────────────────────────────────────────
def _cine(scene, meta=None):
    errors, warnings = [], []
    v._cinematic_fields(scene, meta or {"renderer": "remotion", "fps": 30}, "/tmp", "scene#1", errors, warnings)
    return errors, warnings


def test_large_stack_count_warns_toward_bars():
    errors, warnings = _cine({"index": 1, "type": "cinematic3d", "archetype": "data-materializes",
                              "duration": 6, "planes": [{"kind": "stack", "data": [420, 380],
                                                         "position": [0, 0, 0]}]})
    assert any("stack" in w and "bars" in w for w in warnings), "no large-stack -> bars steer: %s" % warnings


def test_small_stack_count_is_silent():
    errors, warnings = _cine({"index": 1, "type": "cinematic3d", "archetype": "data-materializes",
                              "duration": 6, "planes": [{"kind": "stack", "data": [7, 12],
                                                         "position": [0, 0, 0]}]})
    assert not any("cube per unit" in w for w in warnings), "a small stack must not warn: %s" % warnings


def test_nan_in_plane_data_is_a_hard_error():
    errors, warnings = _cine({"index": 1, "type": "cinematic3d", "archetype": "data-materializes",
                              "duration": 6, "planes": [{"kind": "bars", "data": [10, float("inf")],
                                                         "position": [0, 0, 0]}]})
    assert any("NaN/Infinity" in e for e in errors), "NaN/Inf in plane data must ERROR: %s" % errors


def test_stack_renderer_cap_constant_present():
    """The TS renderer must bound the per-column cube count (validate warns; the renderer must not melt)."""
    src = open(os.path.join(_SKILL, "remotion", "src", "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "STACK_MAX_CUBES" in src and "Math.min(STACK_MAX_CUBES" in src, "Stack3D lost its per-column cap"


# ── 5. cinematic3d covered by the 9:16 overflow warning ────────────────────────────────────────────────
def test_cinematic3d_gets_the_vertical_overflow_warning():
    data = {"meta": {"renderer": "remotion", "aspect": "9:16", "fps": 30},
            "slides": [{"index": 1, "type": "cinematic3d", "archetype": "hero-on-void", "duration": 5,
                        "narration": "x", "camera3d": {"path": "orbit"},
                        "planes": [{"kind": "plane", "position": [0, 0, 0]}]}]}
    res = v.evaluate(data, "/tmp", pre_tts=True, vertical=False)
    warnings = res.get("warnings", [])
    assert any("landscape-tuned" in w for w in warnings), "cinematic3d not covered by the 9:16 warning: %s" % warnings


# ── 6. SIGNED DATA — the classic "every gate misses it" trap ───────────────────────────────────────────
@pytest.mark.parametrize("kind", ["bars", "stack"])
def test_negative_plane_data_is_a_hard_error(kind):
    errors, warnings = _cine({"index": 1, "type": "cinematic3d", "archetype": "data-materializes",
                              "duration": 6, "planes": [{"kind": kind, "data": [10, 20, -30],
                                                         "position": [0, 0, 0]}]})
    assert any("NEGATIVE" in e for e in errors), "signed %s data must ERROR (magnitude-only render): %s" % (kind, errors)


def test_dense_bar_chart_warns():
    errors, warnings = _cine({"index": 1, "type": "cinematic3d", "archetype": "data-materializes",
                              "duration": 9, "planes": [{"kind": "bars", "data": list(range(1, 20)),
                                                         "position": [0, 0, 0]}]})
    assert any("columns" in w for w in warnings), "a >12-column bar chart must warn: %s" % warnings


# ── 7. CJK on the cinematic tier is a portability trap ─────────────────────────────────────────────────
def test_cjk_cinematic_deck_warns_portability():
    data = {"meta": {"renderer": "remotion", "language": "zh", "fps": 30},
            "slides": [{"index": 1, "type": "cinematic", "archetype": "hero-on-void", "duration": 5,
                        "narration": "x", "stage": {"elements": [{"id": "t", "kind": "display",
                                                                  "text": "增长", "position": [0, 0, 0]}]},
                        "shots": [{"type": "HERO", "aim": {"target": "t"}}]}]}
    res = v.evaluate(data, "/tmp", pre_tts=True)
    assert any("CJK deck on the cinematic" in w for w in res.get("warnings", [])), \
        "CJK cinematic deck must warn about host-font portability: %s" % res.get("warnings")


# ── 8. metaphor semantic-direction gates ───────────────────────────────────────────────────────────────
def _stage(elements):
    errors, warnings = [], []
    v._shot_stage_fields({"elements": elements}, [{"type": "MEDIUM", "aim": {"target": elements[0]["id"]}}],
                         "sc", errors, warnings)
    return errors, warnings


def test_physical_fall_wrong_direction_warns():
    errors, warnings = _stage([{"id": "a", "kind": "metaphor", "concept": "physical-fall",
                                "values": [100, 150], "position": [0, 0, 0]}])
    assert any("FALL" in w for w in warnings), "physical-fall that rises must warn: %s" % warnings


def test_filling_vessel_ambiguous_one_warns():
    errors, warnings = _stage([{"id": "a", "kind": "metaphor", "concept": "filling-vessel",
                                "values": [1], "position": [0, 0, 0]}])
    assert any("fraction 1.0" in w for w in warnings), "filling-vessel value 1 must warn: %s" % warnings


# ── 9. shot windows: more shots than frames must fail loud ─────────────────────────────────────────────
import render_remotion as _rr  # noqa: E402


def test_more_shots_than_frames_errors():
    with pytest.raises(RuntimeError, match="shots but only"):
        _rr._clean_shots([{"type": "MEDIUM"}, {"type": "MEDIUM"}, {"type": "MEDIUM"}], 2, 30, set(), "sc")


def test_verbspan_zero_is_floored():
    st = _rr._clean_stage({"elements": [{"id": "a", "kind": "metaphor", "concept": "filling-vessel",
                                         "values": [42], "position": [0, 0, 0], "verbSpan": 0}]}, "sc")
    assert st["elements"][0]["verbSpan"] == 1, "verbSpan 0 must floor to 1 (else NaN at frame==fire)"


# ── 10. huge magnitudes abbreviate (no fixed-box overflow) ─────────────────────────────────────────────
def test_bar_value_abbreviates_large_magnitudes():
    assert _rr._fmt_bar_value(1_000_000_000) == "1B"
    assert _rr._fmt_bar_value(1_200_000) == "1.2M"
    assert _rr._fmt_bar_value(12_000) == "12,000"      # <1e6 stays exact + grouped
    assert _rr._fmt_bar_value(42) == "42"


def test_elements_and_shots_ts_carry_the_fixes():
    """Source backstops for the TS-only fixes (no Node in the unit suite): the abbreviator, the aspect-aware
    zoom, and the physical-fall sign fix must not silently regress out."""
    el = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    sh = open(os.path.join(_SKILL, "remotion", "src", "stage", "shots.ts"), encoding="utf-8").read()
    assert "abbrevNum" in el, "elements.tsx lost the large-number abbreviator"
    assert "before > after ? '-'" in el, "physical-fall lost its correct-sign label"
    assert "aspectRatio / (16 / 9)" in sh, "calculateShotFrame no longer consumes aspectRatio (9:16 regresses)"
