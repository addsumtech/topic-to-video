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


def test_family_spread_counts_library_beats_not_a_films_own_shots():
    # a mostly-built film was told "16 beats span only 2 design families"; its own shots belong to no family
    built = [{"index": i + 1, "shot": "Built%d" % i} for i in range(14)]
    lib = [{"index": 15, "shot": "CinematicTitle"}, {"index": 16, "shot": "ObjectCompare"}]
    r = v.evaluate({"meta": {"renderer": "remotion"}, "slides": built + lib}, "/tmp", pre_tts=True)
    assert not any("design famil" in w and "span only" in w for w in r["warnings"]), \
        [w for w in r["warnings"] if "famil" in w]


def test_the_proof_run_tiles_a_design_review_sheet(tmp_path):
    """The 3.6 checkpoint showed form NAMES; what the user corrected on GPS (and the compound test's nine flat ledger
    pages) is only visible with every beat side by side. shot_proof writes that page itself."""
    from PIL import Image
    import shot_proof as sp
    (tmp_path / "_proof").mkdir()
    for k, col in ((1, (200, 30, 30)), (2, (30, 30, 200)), (4, (30, 160, 30))):
        Image.new("RGB", (1920, 1080), col).save(str(tmp_path / "_proof" / ("beat_%02d.png" % k)))
    board = {"slides": [{"shot": "A", "shot_fit": {"verdict": "build"}}, {"shot": "B"},
                        {"shot": "C"}, {"shot": "D", "shot_fit": {"verdict": "adapt"}}]}
    out = sp.design_sheet(str(tmp_path), board, cols=2, tile_w=320)
    img = Image.open(out)
    assert out.endswith("_design_review.png") and img.width == 2 * 320 + 3 * 16, img.size
    assert img.getpixel((16 + 160, 16 + 34 + 90))[0] > 150             # beat 1's tile, where it belongs
    assert sp.design_sheet(str(tmp_path), {"slides": []}) is None


def _comp(seq, meta=None):
    slides = [{"shot_fit": {"ideal": "x", "composition": c}} if c else {"shot_fit": {"ideal": "x"}} for c in seq]
    errs, warns = [], []
    v._composition_variety(dict({"form_vocabulary": [{"form": "a"}]}, **(meta or {})), slides, errs, warns)
    return errs, warns


def test_one_composition_carrying_the_film_is_an_error():
    """The compound-interest test: every beat built, every gate green, nine flat ledger pages in a row."""
    errs, _ = _comp(["plane"] * 9 + ["object", "wide"])
    assert errs and "9 of 11" in errs[0] and "'plane'" in errs[0] and "composition_system" in errs[0], errs
    errs, _ = _comp(["wide", "close", "plane", "plane", "plane", "plane", "object"])
    assert errs and "beats 3-6" in errs[0], errs


def test_a_varied_film_passes_and_three_wides_in_a_row_are_allowed():
    """GPS ran three orbital wides (beats 5-7) and read well; four of one in a row is the line."""
    gps = ["object", "wide", "wide", "plane", "wide", "wide", "wide", "split", "wide", "plane", "sequence",
           "object", "close", "plane", "full-bleed"]
    assert _comp(gps) == ([], [])


def test_composition_is_declared_on_every_designed_beat_from_a_closed_vocabulary():
    errs, _ = _comp(["wide", "", "page"])
    assert any("name no `shot_fit.composition`" in e and "beats 2" in e for e in errs), errs
    assert any("'page' is not one of" in e for e in errs), errs
    assert v._composition_variety({}, [{"shot_fit": {"ideal": "x"}}], [], []) is None   # pre-design-first board


def test_a_declared_composition_system_turns_the_error_into_a_kept_warning():
    errs, warns = _comp(["plane"] * 6, {"composition_system": "a ledger film where every beat is the printed page"})
    assert not errs and warns and "kept by meta.composition_system" in warns[0], (errs, warns)
    assert _comp(["plane"] * 6, {"composition_system": "on purpose"})[0], "a reason, not a token"


def test_a_sparse_film_is_named_between_a_line_of_type_and_a_full_frame():
    """HTTPS test: median 7.0% ink, clean line drawings in a mostly empty frame; the GPS film the user approved
    after asking for fuller beats measured 28.8%. Under 6% stays the old "line of type" warning."""
    import shot_proof as sp
    https = [4.0, 22.8, 9.8, 44.9, 7.0, 4.9, 3.7, 6.2, 5.4, 7.8, 7.6, 3.9, 7.8, 4.6]
    w = sp.tonal_warnings(list(enumerate(https, 1)), 14)
    assert len(w) == 1 and "SPARSE" in w[0] and "beat 7 3.7%" in w[0], w
    gps = [92.2, 85.0, 28.8, 5.6, 64.7, 18.4, 35.4, 13.0, 33.1, 82.8, 28.4, 21.2, 61.3, 24.7, 7.4]
    assert not any("SPARSE" in x for x in sp.tonal_warnings(list(enumerate(gps, 1)), 15))
    compound = [8.9, 18.3, 19.0, 14.1, 19.3, 10.5, 20.9, 28.6, 19.8, 11.6, 7.2]
    assert sp.tonal_warnings(list(enumerate(compound, 1)), 11) == []
    assert "TONAL REGISTER is thin" in sp.tonal_warnings([(1, 2.0), (2, 5.0), (3, 4.0)], 3)[0]


def test_words_and_substance_are_measured_in_any_script():
    """Latin+CJK-only counting measured a Russian, Greek, Arabic or Hindi justification at zero words — refused as
    "not specific" — and pace.py predicted a Russian line as its pauses alone. The title probe had the same blind
    spot: its letter class read every non-Latin, non-CJK title as a figure."""
    import _common as c
    import pace
    assert len(c.words("Три источника подключены к одному центру", digits=False)) == 6
    assert len(c.words("तीन स्रोत एक केंद्र से जुड़े हैं और दो आपस में", digits=False)) == 11   # vowel signs stay in the word
    assert len(c.words("don't stop here, it's fine", digits=False)) == 5
    assert v._specific("Три источника подключены к одному центру, два связаны")
    assert v._specific("كل المصادر الثلاثة متصلة بمركز واحد واثنان منها متصلان")
    assert not v._specific("it fits") and not v._specific("适合")
    assert c.substance("三个来源连到同一个中心") == 5.5                          # CJK unchanged: half a word each
    assert pace.features("Как работает GPS в вашем телефоне")["latin_word"] == 6
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src",
                            "runtime", "titleProbe.tsx"), encoding="utf-8").read()
    assert "/\\p{L}/gu" in src, "the title probe's letters must be any script's"
