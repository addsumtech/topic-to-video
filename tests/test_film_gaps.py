"""Gaps an end-to-end run of the GPS test film (2026-10-16) hit that no unit test had: a board built from the plan
without the fields its tools read, warnings that asked a built film for levers it cannot pull, and a remotion film
the cross-film register could not record."""
import json
import os
import subprocess
import sys

import register_ledger as rl
import storyboard as sb
import validate as v

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
PLAN = {"arc_kind": "expository", "beats": [
    {"id": i + 1, "relation": rel, "energy": "medium", "stage": "build", "climax": i == 6, "hold": i == 8}
    for i, rel in enumerate(["new-topic", "continuation", "continuation", "continuation", "new-topic",
                             "continuation", "payoff", "continuation", "close"])]}


def test_a_board_built_from_the_plan_carries_the_fields_its_tools_read(tmp_path):
    json.dump(PLAN, open(tmp_path / "content_plan.json", "w"))
    p = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "storyboard.py"), str(tmp_path), "--from-plan",
                        "language=zh", "renderer=remotion", "target_seconds=40"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    b = json.load(open(tmp_path / "storyboard.json"))
    assert b["meta"]["target_seconds"] == 40 and b["meta"]["arc_kind"] == "expository"
    assert [s["relation"] for s in b["slides"]][6] == "payoff" and b["slides"][6]["climax"] is True
    p = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "storyboard.py"), str(tmp_path), "--from-plan"],
                       capture_output=True, text=True)
    assert p.returncode == 2 and "not overwritten" in p.stdout


def test_seam_plan_takes_the_plans_relations_when_the_board_lacks_them(tmp_path):
    json.dump(PLAN, open(tmp_path / "content_plan.json", "w"))
    board = {"meta": {"renderer": "remotion"},
             "slides": [{"index": i + 1, "shot": "CinematicTitle", "narration": "x"} for i in range(9)]}
    json.dump(board, open(tmp_path / "storyboard.json", "w"))
    assert sb.plan_fields_missing(board["slides"], PLAN)["relation"] == 9
    p = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "seam_plan.py"), str(tmp_path)],
                       capture_output=True, text=True)
    assert "took" in p.stdout and "relation on 9 beat(s)" in p.stdout, p.stdout + p.stderr
    p = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "seam_plan.py"), "--help"], capture_output=True, text=True)
    assert p.returncode == 0 and "Traceback" not in p.stderr
    # a board that has diverged from the plan is left alone
    assert sb.plan_fields_missing(board["slides"][:5], PLAN) == {}


def test_a_built_film_is_not_asked_for_a_ground_it_cannot_declare(tmp_path):
    shots = tmp_path / "workshop" / "shots"
    shots.mkdir(parents=True)
    for i in range(9):
        (shots / ("Built%d.tsx" % i)).write_text("export const Built%d = () => null;\n" % i)
    slides = [{"index": i + 1, "shot": "Built%d" % i} for i in range(9)]
    warns = []
    v._beat_grounds(slides, [], warns, str(tmp_path))
    assert any("this film's own shots, which draw their own light" in w for w in warns), warns
    assert not any("ONE flat exposure" in w for w in warns), warns
    warns = []
    v._beat_grounds([{"index": i + 1, "shot": "CinematicTitle"} for i in range(9)], [], warns, str(tmp_path))
    assert any("ONE flat exposure" in w for w in warns), "a library film still hears the original warning"


def test_a_remotion_film_enters_the_cross_film_register(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDES_TO_VIDEO_HOME", str(tmp_path / "home"))
    film = tmp_path / "gps"
    film.mkdir()
    meta = {"renderer": "remotion", "language": "zh", "shot_template": "orbit-light",
            "design_dna": {"bg": "#04060c", "accent": "#F2C46B"},
            "shot_template_contest": {"directions": {"orbit-light": {"ideal": "a sunlit satellite over the limb"}}}}
    json.dump({"meta": meta, "slides": []}, open(film / "storyboard.json", "w"))
    e = rl.record(str(film))
    assert e and e["register"] == "orbit-light" and e["mode"] == "dark" and e["accent"] == "#f2c46b"
    assert e["angle"] == "a sunlit satellite over the limb" and rl.recent(1)[0]["deck"] == "gps"


def test_a_built_films_unmeasured_energy_is_one_line_and_a_designed_direction_is_not_questioned(tmp_path):
    shots = tmp_path / "workshop" / "shots"
    shots.mkdir(parents=True)
    for i in range(4):
        (shots / ("Built%d.tsx" % i)).write_text("export const Built%d = () => null;\nexport const DURATION = 120;\n" % i)
    slides = [{"index": i + 1, "shot": "Built%d" % i, "energy": "high", "narration": "x"} for i in range(4)]
    meta = {"renderer": "remotion", "shot_template": "orbit-light", "audacity": "balanced",
            "shot_template_contest": {"candidates": ["orbit-light", "b"], "winner": "orbit-light", "user_pick": True,
                                      "directions": {"orbit-light": {"ideal": "x" * 20, "hero": "Built0",
                                                                     "palette_source": [{"colour": "#000", "from": "space"}]}}}}
    r = v.evaluate({"meta": meta, "slides": slides}, str(tmp_path), pre_tts=True)
    own = [w for w in r["warnings"] if "this film's own shots (" in w]
    assert len(own) == 1 and "4 beat(s)" in own[0], [w for w in r["warnings"] if "energy" in w]
    assert not any("is unmeasured BY DESIGN" in w for w in r["warnings"])
    assert not any("not one of the 6 SEED directions" in w for w in r["warnings"])


def test_a_helper_subfolder_of_code_is_allowed_and_a_picture_in_it_is_named(tmp_path):
    import workshop as ws
    parts = tmp_path / "workshop" / "shots" / "parts"
    parts.mkdir(parents=True)
    (parts / "satellite.ts").write_text("export const n = 1;\n")
    assert not [p for p in ws.names_problems(str(tmp_path)) if "parts" in p], ws.names_problems(str(tmp_path))
    (parts / "foil.png").write_bytes(b"x")
    assert any("parts/foil.png: a helper folder holds .ts/.tsx code only" in p for p in ws.names_problems(str(tmp_path)))


def test_an_outdated_edge_tts_403_names_the_upgrade():
    import tts
    hint = tts.failure_hint("edge", Exception("403, message='Invalid response status', url='wss://speech…'"))
    assert "pip install -U edge-tts" in hint
    assert tts.failure_hint("edge", Exception("timed out")) == "" and tts.failure_hint("say", Exception("403")) == ""
