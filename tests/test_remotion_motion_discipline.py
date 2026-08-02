"""Camera + motion discipline backstops (#6 energy-arc + #10 shared motion physics). #6: when energy is
unset the tier DERIVES an arc (calm open -> bold climax ~80% -> resolve) and weights screen TIME by energy;
lints nudge a motive on a big push, a flat arc, and the >=2.6s comfort budget. #10: one shared HOUSE_EASE
settle + a motion_personality dial that scales every move's amplitude."""
import os

import pytest
import render_remotion as rr
import storyboard as sb
import validate as v

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _shots(shots, dur=10.0, meta=None):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False, **(meta or {})})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = dur
    s["stage"] = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0], "title": "X"}]}
    s["shots"] = shots
    d["slides"] = [s]
    return d


# ── #6 energy arc + time weighting ───────────────────────────────────────────────────────────────────
def test_energy_arc_derived_when_unset(tmp_path):
    sc = rr.build_props(_shots([{"type": "ESTABLISH", "target": "a"}, {"type": "MEDIUM", "target": "a"},
                                {"type": "MEDIUM", "target": "a"}, {"type": "HERO", "target": "a"}]), str(tmp_path))["scenes"][0]
    ens = [x["energy"] for x in sc["shots"]]
    assert ens[0] == "subtle" and ens[-1] == "bold" and "bold" in ens, "calm open, bold climax/hero"


def test_author_energy_is_respected(tmp_path):
    sc = rr.build_props(_shots([{"type": "ESTABLISH", "target": "a", "energy": "balanced"},
                                {"type": "HERO", "target": "a", "energy": "balanced"}]), str(tmp_path))["scenes"][0]
    assert all(x["energy"] == "balanced" for x in sc["shots"]), "a hand-set energy means the author owns the arc"


def test_bold_beats_get_more_screen_time(tmp_path):
    est, hero = rr.build_props(_shots([{"type": "ESTABLISH", "target": "a"}, {"type": "HERO", "target": "a"}]),
                               str(tmp_path))["scenes"][0]["shots"]
    assert hero["durationFrames"] > est["durationFrames"], "the bold beat gets more time than the subtle open"


def test_motive_threads(tmp_path):
    sc = rr.build_props(_shots([{"type": "HERO", "target": "a", "motive": "show the result"}]), str(tmp_path))["scenes"][0]
    assert sc["shots"][0]["motive"] == "show the result"


# ── #10 shared motion physics ────────────────────────────────────────────────────────────────────────
def test_house_ease_and_ampscale_wired():
    src = _src("remotion", "src", "stage", "camera.ts")
    assert "house:" in src and "Easing.bezier(0.16, 1, 0.3, 1)" in src, "the shared premium HOUSE_EASE"
    assert "ampScale" in src and "|| 'house'" in src, "personality amp + house as the default settle"


def test_uneased_shot_actually_gets_house(tmp_path):
    # BEHAVIOURAL (not a source grep): an un-eased shot must carry easing 'house' — Python used to default
    # 'inout', which shadowed the TS `|| 'house'` fallback and left the shared motion physics dead.
    sc = rr.build_props(_shots([{"type": "HERO", "target": "a"}]), str(tmp_path))["scenes"][0]
    assert sc["shots"][0]["easing"] == "house"


@pytest.mark.parametrize("pers,amp", [("energetic", 1.4), ("calm", 0.72), ("balanced", 1.0), ("weird", 1.0)])
def test_motion_personality_scales_amplitude(tmp_path, pers, amp):
    sc = rr.build_props(_shots([{"type": "HERO", "target": "a"}], meta={"motion_personality": pers}), str(tmp_path))["scenes"][0]
    assert sc["motionAmp"] == amp


# ── #6 discipline lints ──────────────────────────────────────────────────────────────────────────────
def test_motive_nudge_on_a_big_push():
    errs, warns = [], []
    v._shot_stage_fields({"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]},
                         [{"type": "HERO", "target": "a"}], "s1", errs, warns)
    assert any("motive" in w for w in warns)


def test_flat_energy_arc_warns():
    errs, warns = [], []
    shots = [{"type": "MEDIUM", "target": "a", "energy": "bold"} for _ in range(4)]
    v._shot_stage_fields({"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]}, shots, "s1", errs, warns)
    assert any("uniformly" in w for w in warns)


def test_comfort_budget_warns_on_too_many_shots():
    errs, warns = [], []
    s = {"type": "cinematic", "duration": 4.0, "archetype": "process-flow",
         "stage": {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]},
         "shots": [{"type": "MEDIUM", "target": "a"} for _ in range(4)]}
    v._cinematic_fields(s, {"fps": 30}, "/tmp", "s1", errs, warns)
    assert any("vertigo" in w for w in warns), "4 shots in 4s (~1s each) exceeds the comfort budget"
