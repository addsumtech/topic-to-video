"""REACH — the authoring path offers the capabilities the library built, routed by the argument's SHAPE.

Three benchmark films (2026-10-24) found the director barely used the kinetic registers and never reached camera
space: the intent keyword lists in scripts/shot_director.py never named EquationMorph, GrowingFigure, FunctionPlot,
TypeOnPath, CroppedType, WordRoll or LitMedium, and nothing said when a WorldStage run is the right tool. What is held:

  * every tool REACH names exists (registered, in FAMILY/PROVENANCE, a stage the Film draws, a move the world draws,
    an optic its register anchors) and every register built since the director docs is reachable;
  * a board whose forms argue a journey across scales, the flow of a quantity, a route between cities or a derivation
    gets the stage / register built for it, in English and in Chinese — and a board with no argument text is proposed
    exactly as before (forms come from the subject; REACH never writes one);
  * a route never breaks family variety, and one form across two beats keeps one register;
  * a kinetic register proposed for a beat shorter than its own length says so;
  * validate accepts the WorldStage board the reach describes;
  * the plan's purpose reaches the board, and seam_plan cuts a launch film hard while a calm explainer keeps dissolving;
  * the doc table (references/remotion-shot-authoring.md §F) names exactly the routes the code has.
"""
import os
import re
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import dna_audit  # noqa: E402
import seam_plan  # noqa: E402
import shot_director as sd  # noqa: E402
import stage_runs  # noqa: E402
import storyboard  # noqa: E402
import world_stage  # noqa: E402

# the registers built after the director docs were written (motion-research §0, LIBRARY.md 205-213)
NEW_REGISTERS = ["HeadlineReveal", "WordRoll", "TypeOnPath", "CroppedType", "EquationMorph", "GrowingFigure",
                 "FunctionPlot", "FlowSankey", "RankRace", "FlowCounter", "GlobeFocus", "FlightArcs", "LitMedium"]


def _board(forms, purpose=None, plan_text=None):
    """One beat per form; each form's vocabulary entry carries the argument the director wrote for it."""
    vocab = [{"form": f, "carries": c, "looks_like": "—"} for f, c in forms]
    slides = [{"index": i + 1, "shot_fit": {"form": f, "ideal": "the frame for %s" % f}} for i, (f, _c) in enumerate(forms)]
    meta = {"form_vocabulary": vocab}
    if purpose:
        meta["purpose"] = purpose
    return {"meta": meta, "slides": slides}


def _routes(slide):
    return [n["route"] for n in (slide.get("shot_fit") or {}).get("reach") or []]


# ── the table names real tools ──────────────────────────────────────────────────────────────────────────────────────
def test_every_route_names_tools_that_exist():
    registry = dna_audit.registered_shots()
    stages = set(stage_runs.stage_names())
    keys = [r["key"] for r in sd.REACH]
    assert len(keys) == len(set(keys)), keys
    for r in sd.REACH:
        assert r["registers"], r["key"]
        for c in r["registers"]:
            assert c in registry, (r["key"], c, "not in remotion/src/registry.ts")
            assert c in sd.FAMILY and c in sd.PROVENANCE, (r["key"], c)
        if r.get("stage"):
            assert r["stage"] in stages, (r["key"], r["stage"], stages)
            for m in list(r.get("moves") or []) + list((r.get("move_cues") or {})):
                assert m in world_stage.MOVES, (r["key"], m)
        if r.get("optic"):
            import validate
            for c in r["registers"]:
                offered = sd.register_optics(c)
                assert offered, "%s is on the light route but anchors no optic" % c
                assert offered == validate.register_optics(c), "the director and validate read %s's OPTICS apart" % c
        for k in ("when", "not", "needs"):
            assert len(str(r.get(k) or "")) > 20, (r["key"], k)
        for c in r["cues"]:
            re.compile(c)


def test_every_register_built_since_the_director_docs_is_reachable():
    reachable = {c for r in sd.REACH for c in r["registers"]}
    reachable |= {c for lst in sd.CANDIDATES.values() for c in lst} | set(sd.CLIMAX) | set(sd.CLOSE)
    missing = [c for c in NEW_REGISTERS if c not in reachable]
    assert not missing, "built but unreachable from the proposer: %s" % missing


# ── the argument's shape picks the tool ────────────────────────────────────────────────────────────────────────────
def test_proposals_follow_the_argument_shape_in_english():
    b = _board([("the powers-of-ten flight", "a journey across scales, from the planet down to one city"),
                ("the energy ledger", "where the energy goes — the flow of energy through the grid, conserved"),
                ("the airline map", "the route between London and Tokyo"),
                ("the blackboard", "the derivation of the period, step by step from the equation")])
    sd.assign_shots(b, None)
    s = b["slides"]
    assert "journey-across-scales" in _routes(s[0])
    stage = [n for n in s[0]["shot_fit"]["reach"] if n.get("stage")]
    assert stage and stage[0]["stage"] == "WorldStage" and "scale-zoom" in stage[0]["moves"], s[0]["shot_fit"]
    assert s[1]["shot"] == "FlowSankey", s[1]
    assert s[2]["shot"] == "FlightArcs", s[2]
    assert s[3]["shot"] == "EquationMorph", s[3]
    for sl in s:
        assert sl["shot_fit"]["verdict"] == "unjudged", "a reach proposal is still MATERIAL, never the assignment"
        assert sl["shot_fit"]["assigned_by"].startswith("reach '"), sl["shot_fit"]


def test_proposals_follow_the_argument_shape_in_chinese():
    b = _board([("十的幂次", "一层层放大到细胞"), ("能量账本", "能量的去向，守恒"),
                ("航线图", "从北京飞往伦敦的航线"), ("黑板", "推导出周期的公式")])
    sd.assign_shots(b, None)
    s = b["slides"]
    assert any(n.get("stage") == "WorldStage" for n in s[0]["shot_fit"]["reach"]), s[0]["shot_fit"]
    assert [x["shot"] for x in s[1:]] == ["FlowSankey", "FlightArcs", "EquationMorph"], [x["shot"] for x in s]


def test_the_plan_s_learning_point_is_read_when_the_form_says_little():
    b = {"meta": {}, "slides": [{"index": 1, "shot_fit": {"form": "plate", "ideal": "x"}}]}
    plan = {"beats": [{"id": 1, "visual_intent": "metric",
                       "learning_point": "the ranking of the five ports changed every decade — who overtook whom"}]}
    sd.assign_shots(b, plan)
    assert b["slides"][0]["shot"] == "RankRace", b["slides"][0]


def test_a_board_with_no_argument_text_is_proposed_as_before():
    """Forms come from the subject: with no form, ideal or plan text there is nothing to read, so REACH stays out of
    the way and the intent lists propose exactly what they did — and REACH never writes a form of its own."""
    plan = {"beats": [{"id": i + 1, "visual_intent": vi} for i, vi in
                      enumerate(["statement", "structure", "list", "metric", "sequence", "contrast"])]}
    b = {"meta": {}, "slides": [{"index": i + 1} for i in range(6)]}
    sd.assign_shots(b, plan)
    for sl in b["slides"]:
        assert "reach" not in sl["shot_fit"] and "form" not in sl["shot_fit"], sl["shot_fit"]
        assert not sl["shot_fit"]["assigned_by"].startswith("reach"), sl["shot_fit"]


def test_ordinary_product_copy_does_not_fire_the_specialised_routes():
    for text in ("The app solves your workflow problems", "a light, fast editor", "the user flow of the settings page",
                 "our customer journey to purchase", "The team grew"):
        assert not sd.match_reach(text), (text, [r["key"] for r in sd.match_reach(text)])


def test_a_route_never_breaks_family_variety_and_one_form_keeps_one_register():
    b = _board([("the coast chart", "where is the coastline of the bay"), ("the island chart", "located on the island")])
    sd.assign_shots(b, None)
    a, c = b["slides"]
    assert a["shot"] == "GlobeFocus" and sd.FAMILY[c["shot"]] != sd.FAMILY[a["shot"]], (a["shot"], c["shot"])
    assert "where" in _routes(c), "the match is still recorded when variety moved the proposal"
    same = _board([("the blackboard", "the derivation, step by step"), ("the blackboard", "the derivation, step by step")])
    same["meta"]["form_vocabulary"] = same["meta"]["form_vocabulary"][:1]
    sd.assign_shots(same, None)
    assert [x["shot"] for x in same["slides"]] == ["EquationMorph", "EquationMorph"], same["slides"]
    assert "the same form" in same["slides"][1]["shot_fit"]["assigned_by"]


def test_a_routed_beat_is_never_touched():
    b = _board([("the blackboard", "the derivation")])
    b["slides"][0].update({"shot": "TechnicalPlate", "shot_fit": {"form": "the blackboard", "ideal": "x",
                                                                  "verdict": "build", "why": "drawn for this film"}})
    sd.assign_shots(b, None)
    assert b["slides"][0]["shot"] == "TechnicalPlate" and "reach" not in b["slides"][0]["shot_fit"]


def test_a_declared_stage_run_is_a_route_and_the_composition_written_first_survives():
    b = _board([("the flight", "a flight from the Sun to the Earth"), ("the flight", "a flight from the Sun to the Earth"),
                ("the ledger", "where the money goes, the budget")])
    for sl in b["slides"][:2]:
        sl.update({"shot": "WorldStage", "stage": {"run": "w"}})
    b["slides"][2]["shot_fit"]["composition"] = "plane"
    sd.assign_shots(b, None)
    assert [x["shot"] for x in b["slides"][:2]] == ["WorldStage", "WorldStage"], "a proposal would split the run"
    assert not any("mixes shots" in p for p in stage_runs.check(b["slides"]))
    assert b["slides"][2]["shot_fit"]["composition"] == "plane", "the director's composition was dropped"


# ── kinetic type and its reading time ──────────────────────────────────────────────────────────────────────────────
def test_a_kinetic_register_on_a_short_beat_says_what_its_reading_gate_will_hold():
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", "HeadlineReveal.tsx"), encoding="utf-8").read()
    frames = int(re.search(r"^export const DURATION\s*=\s*(\d+)", src, re.M).group(1))
    assert sd.authored_seconds("HeadlineReveal") == frames / 30.0
    assert sd.reading_held("HeadlineReveal") and sd.reading_held("WordRoll")
    assert not sd.reading_held("CinematicTitle"), "only the registers set with runtime/kinetic are reading-held"
    b = _board([("the manifesto line", "one sentence, said in one breath")])
    plan = {"beats": [{"id": 1, "visual_intent": "statement", "est_seconds": 3.5}]}
    sd.assign_shots(b, plan)
    fit = b["slides"][0]["shot_fit"]
    assert b["slides"][0]["shot"] == "HeadlineReveal" and "3.5 s" in fit["timing"] and "%.1f s" % (frames / 30.0) in fit["timing"]
    long = _board([("the manifesto line", "one sentence, said in one breath")])
    sd.assign_shots(long, {"beats": [{"id": 1, "est_seconds": frames / 30.0 + 1}]})
    assert "timing" not in long["slides"][0]["shot_fit"]


# ── camera space, shared elements, tempo: the film-level lines ──────────────────────────────────────────────────────
def test_consecutive_world_beats_are_one_suggested_run_with_their_moves():
    b = _board([("the title", "the opening claim"),
                ("the flight", "a flight from the Sun to the Earth"),
                ("the sky column", "a tilt up through the layers of the atmosphere"),
                ("the zoom", "zoom from the planet down to the ring round its pole, across scales"),
                ("the ledger", "where the money goes, the budget")])
    sd.assign_shots(b, None)
    hints = sd.stage_run_hints(b["slides"])
    assert hints == [(1, 3, "WorldStage", hints[0][3])], hints
    assert {"dolly", "tilt", "scale-zoom"} <= set(hints[0][3]), hints
    text = "\n".join(sd.reach_report(b))
    assert "beats 2-4 travel ONE world: declare a WorldStage run" in text, text


def test_one_form_across_a_cut_is_named_as_a_container_seam():
    b = _board([("the passbook", "the account book on the desk"), ("the passbook", "the account book on the desk"),
                ("the receipt", "the price paid")])
    b["meta"]["form_vocabulary"] = b["meta"]["form_vocabulary"][1:]
    for sl, shot in zip(b["slides"], ("ObjectStage", "ObjectStage", "PhotoPlate")):
        sl["shot"] = shot
    hints = sd.container_hints(b["slides"])
    assert [i for i, _ in hints] == [1], hints
    assert "'figure'" in hints[0][1] and "`container`" in hints[0][1], "ObjectStage draws the `figure` anchor"


def test_the_report_states_the_film_s_cut_tempo():
    for purpose, word in (("launch", "tempo kinetic"), ("teach", "tempo calm")):
        b = _board([("x", "y")], purpose=purpose)
        sd.assign_shots(b, None)
        assert any(word in line for line in sd.reach_report(b)), sd.reach_report(b)


# ── the board the reach describes renders through validate ────────────────────────────────────────────────────────
def test_validate_accepts_the_world_stage_board_the_reach_describes():
    import validate
    world = {"objects": {"sun": {"kind": "glow", "at": [-3, 0, 0], "w": 1, "label": "Sun", "color": "accent"},
                         "earth": {"kind": "globe", "at": [0, 0, 0], "w": 1, "label": "Earth"},
                         "ring": {"kind": "frame", "in": "earth", "uv": [0.5, 0.2], "span": 0.3},
                         "word": {"kind": "type", "text": "one world", "at": [0, -0.8, 0.2], "size": 0.08}}}
    form = "a flight from the Sun to the ring round the pole"
    vocab = [{"form": form, "carries": "a journey across scales in one place", "looks_like": "a travelling camera"},
             {"form": "a title card", "carries": "the claim", "looks_like": "type"}]
    slides = [{"index": 1, "shot": "CinematicTitle", "shot_props": {"kicker": "", "tagline": "", "title": "One world"},
               "shot_fit": {"ideal": "the film's one line, alone", "form": "a title card", "verdict": "fit",
                            "why": "the opening title", "shares": "the title's scale is the film's claim"},
               "audio": "audio/01.mp3", "duration": 5.0, "narration": "A sentence."}]
    states = [{"world": world, "camera": {"frame": "sun"}, "labels": ["sun"], "move": 2.0},
              {"camera": {"frame": "earth", "move": "dolly"}, "labels": ["earth"], "move": 2.5},
              {"camera": {"frame": "ring", "move": "scale-zoom"}, "move": 3.0}]
    for i, p in enumerate(states):
        slides.append({"index": i + 2, "shot": "WorldStage", "stage": {"run": "w"}, "shot_props": p,
                       "shot_fit": {"ideal": "the camera flies from the Sun to the ring round the pole", "form": form,
                                    "verdict": "build", "why": "one world the camera travels through"},
                       "shot_adaptation": {"topic_idea": "the journey is the argument"},
                       "audio": "audio/%02d.mp3" % (i + 2), "duration": 6.0, "narration": "The Sun and the Earth."})
    board = {"meta": {"renderer": "remotion", "design_dna": "cinematic", "form_vocabulary": vocab,
                      "idiom_world": ["motion-graphics", "scientific"]}, "slides": slides}
    # the proposer's own reading of this board names the stage it is built on
    probe = {"meta": {"form_vocabulary": vocab}, "slides": [{"index": 1, "shot_fit": {"form": form, "ideal": "x"}}]}
    sd.assign_shots(probe, None)
    assert any(n.get("stage") == "WorldStage" for n in probe["slides"][0]["shot_fit"]["reach"])
    for sl in slides[1:]:                                   # the director keeps the reach record beside its route
        sl["shot_fit"]["reach"] = probe["slides"][0]["shot_fit"]["reach"]
    r = validate.evaluate(board, tempfile.mkdtemp())
    assert r["ok"] and not r["errors"], r["errors"]
    # and the same run with a camera that frames nothing is refused, by the world check, before any render
    bad = dict(board, slides=[dict(s) for s in slides])
    bad["slides"][2] = dict(bad["slides"][2], shot_props={"camera": {"frame": "ghost", "move": "dolly"}})
    assert any("frames 'ghost'" in e for e in validate.evaluate(bad, tempfile.mkdtemp())["errors"])


# ── purpose → tempo, from the plan to the cut ──────────────────────────────────────────────────────────────────────
def _plan(purpose, n=8, **extra):
    rel = ["new-topic"] + ["continuation"] * (n - 2) + ["close"]
    rel[3] = "new-topic"
    plan = {"purpose": purpose, "beats": [{"id": i + 1, "relation": rel[i], "energy": "medium"} for i in range(n)]}
    plan.update(extra)
    return plan


def test_the_plan_s_purpose_reaches_the_board_and_sets_the_cut():
    assert storyboard.TEMPOS == seam_plan.CUT_TEMPOS
    launch = storyboard.from_content_plan(_plan("launch"), {"renderer": "remotion"})
    assert launch["meta"]["purpose"] == "launch" and "cuts" not in launch["meta"]
    marks = seam_plan.plan(launch["slides"])
    tempo, _basis, cuts = seam_plan.plan_cuts(launch["slides"], launch["meta"], marks)
    assert tempo == "kinetic" and set(cuts) == set(range(1, 8)) - set(marks), (cuts, marks)
    teach = storyboard.from_content_plan(_plan("teach"), {"renderer": "remotion"})
    assert seam_plan.plan_cuts(teach["slides"], teach["meta"], seam_plan.plan(teach["slides"]))[:3:2] == ("calm", {})
    # a plan that names its tempo overrides what the purpose implies; the interview's own meta still wins over both
    punchy = storyboard.from_content_plan(_plan("teach", tempo="kinetic"), {})
    assert seam_plan.film_tempo(punchy["meta"]) == ("kinetic", "meta.cuts")
    told = storyboard.from_content_plan(_plan("teach", tempo="kinetic"), {"cuts": "calm", "purpose": "research"})
    assert told["meta"]["cuts"] == "calm" and told["meta"]["purpose"] == "research"
    assert "cuts" not in storyboard.from_content_plan(_plan("teach", tempo="fast"), {})["meta"], "an unknown tempo is ignored"


# ── the docs say what the code does ────────────────────────────────────────────────────────────────────────────────
def _section_f():
    doc = open(os.path.join(_ROOT, "references", "remotion-shot-authoring.md"), encoding="utf-8").read()
    m = re.search(r"^## F · .*?(?=^## )", doc, re.S | re.M)
    assert m, "references/remotion-shot-authoring.md has no §F reach table"
    return m.group(0)


def test_the_reach_table_in_the_reference_names_exactly_the_code_s_routes():
    f = _section_f()
    named = set(re.findall(r"^\| `([a-z-]+)` \|", f, re.M))
    assert named == {r["key"] for r in sd.REACH}, (sorted(named ^ {r["key"] for r in sd.REACH}))
    for r in sd.REACH:
        row = next(line for line in f.splitlines() if line.startswith("| `%s` |" % r["key"]))
        for tool in r["registers"][:1] + ([r["stage"]] if r.get("stage") else []):
            assert tool in row, (r["key"], tool, row)


def test_the_director_and_the_skill_index_point_at_the_reach_table():
    director = open(os.path.join(_ROOT, "agents", "shot-director.md"), encoding="utf-8").read()
    skill = open(os.path.join(_ROOT, "SKILL.md"), encoding="utf-8").read()
    for doc, name in ((director, "agents/shot-director.md"), (skill, "SKILL.md")):
        assert "remotion-shot-authoring.md` §F" in doc, "%s does not point at the reach table" % name
    for word in ("WorldStage", "`cut`", "optic", "HeadlineReveal", "EquationMorph", "FlowSankey", "FlightArcs"):
        assert word in director, "the shot-director prompt never names %s" % word
