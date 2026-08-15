"""Backstop for the remotion bespoke-shot tier (phase-3 integration): the shot registry stays in sync with the
library, the shot-director varies families, and validate.py enforces the shot contract."""
import os, sys, json, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import validate as v
import shot_director as sd
import shot_templates as st
import render_remotion as rr

_SHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "shots")
_SHOT_IDS = {f[:-4] for f in os.listdir(_SHOTS_DIR) if f.endswith(".tsx")}


def _deck(n=6):
    """A minimal valid remotion storyboard with n scenes, each with a real shot + audio/duration."""
    shots = ["CinematicTitle", "ExplodedSchematic", "CollaborativeCursors", "KnowledgeGraph", "MapRoutes", "LiquidChrome"]
    return {"meta": {"renderer": "remotion"},
            "slides": [{"index": i + 1, "shot": shots[i % len(shots)], "shot_props": {},
                        "audio": f"audio/{i+1:02d}.mp3", "duration": 8.0, "narration": "A sentence."} for i in range(n)]}


def test_shotluma_covers_all_shots():
    # the film tier's luminance foundation (captions contrast + P2 dip) must know EVERY shot's ground —
    # a new shot has to be MEASURED, not silently defaulted. (groundLum falls back to 'dark', but the map
    # should be complete so the fallback is only for truly-new shots between renders.)
    import re
    ts = open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "runtime", "shotLuma.ts"), encoding="utf-8").read()
    body = ts.split("SHOT_LUMA")[1].split("{", 1)[1].split("};")[0]
    keys = set(re.findall(r"(\w+):\s*'(?:dark|mid|light)'", body))
    missing = _SHOT_IDS - keys
    assert not missing, "shotLuma.ts missing luminance for: %s" % sorted(missing)


def test_transition_in_mapping():
    # P2 seam grammar reaches REAL films: the storyboard's transition vocabulary → the Film `transitionIn` mark.
    assert rr._transition_in({"transition_style": "slide"}) == {"type": "slide", "direction": "from-right"}
    assert rr._transition_in({"transition_style": "lift"}) == {"type": "slide", "direction": "from-bottom"}
    assert rr._transition_in({"transition_style": "wipe"})["type"] == "wipe"
    assert rr._transition_in({"transition_style": "Clock-Wipe"}) == {"type": "clock"}    # case/alias-insensitive
    assert rr._transition_in({"transition_style": "dissolve"}) == {"type": "dissolve"}
    assert rr._transition_in({"transition_style": "carry"}) == {"type": "carry"}
    assert rr._transition_in({"transition_style": "match-cut"}) == {"type": "carry"}   # alias
    # non-kinetic styles + absent → None (the luminance-safe default fade, no mark)
    for st_ in ("fade", "dip", "drift", "blur", "none", "", "bogus"):
        assert rr._transition_in({"transition_style": st_}) is None, st_
    assert rr._transition_in({}) is None
    # an explicit remotion mark wins and is sanitized (unknown type ignored)
    assert rr._transition_in({"transition_in": {"type": "wipe", "direction": "from-left"}}) == {"type": "wipe", "direction": "from-left"}
    assert rr._transition_in({"transition_in": {"type": "spin"}}) is None


def test_sfx_sounds_only_marked_seams():
    import sfx                                                    # plan_cues is pure python (no numpy needed)
    scenes = [{"durationInFrames": 120},
              {"durationInFrames": 120, "transitionIn": None},                  # fade  -> silent
              {"durationInFrames": 120, "transitionIn": {"type": "slide"}},     # slide -> whoosh 0.5
              {"durationInFrames": 120, "transitionIn": None},                  # fade  -> silent
              {"durationInFrames": 120, "transitionIn": {"type": "carry"}}]     # carry -> soft whoosh 0.32
    whooshes = [round(g, 2) for (t, nm, g) in sfx.plan_cues(scenes, 30) if nm == "whoosh"]
    assert len(whooshes) == 2, whooshes                          # only the 2 MARKED seams are sounded
    assert 0.32 in whooshes and 0.5 in whooshes                  # carry = softer swell; slide = motion whoosh
    # a legacy caller (no transitionIn key declared) keeps the old behavior: a whoosh at EVERY seam
    legacy = [{"durationInFrames": 120} for _ in range(5)]
    assert sum(1 for _, nm, _ in sfx.plan_cues(legacy, 30) if nm == "whoosh") == 4


def test_camera_amp_from_motion_personality():
    assert rr._camera_amp({}) == 1.0                                # default balanced
    assert rr._camera_amp({"motion_personality": "calm"}) == 0.5
    assert rr._camera_amp({"motion_personality": "energetic"}) == 1.6
    assert rr._camera_amp({"motion_personality": "still"}) == 0.0   # a still tier disables the drift
    assert rr._camera_amp({"motion_personality": 0.8}) == 0.8       # a raw multiplier passes through
    assert rr._camera_amp({"motion_personality": -3}) == 0.0        # clamped non-negative
    assert rr._camera_amp({"motion_personality": "bogus"}) == 1.0   # unknown tier -> balanced


def test_color_arc_luma_and_flip():
    assert sd.shot_luma("KnowledgeGraph") == "dark"
    assert sd.shot_luma("BlockAssembly") == "light"
    assert sd.shot_luma("NotAShot") == "dark"                       # safe default
    assert sd._hard_flip("dark", "light") and not sd._hard_flip("dark", "mid")


def test_pick_softens_luminance_streak():
    cands = ["KnowledgeGraph", "BlockAssembly"]                     # dark, light
    # after a flip (last_luma light), soften prefers the non-flip (light) candidate over the dark one
    assert sd._pick(cands, None, set(), last_luma="light", soften=True) == "BlockAssembly"
    # without soften, fit order is preserved (the first candidate wins)
    assert sd._pick(cands, None, set(), last_luma="light", soften=False) == "KnowledgeGraph"


def _remotion_deck(shots):
    return {"meta": {"renderer": "remotion"},
            "slides": [{"index": i + 1, "shot": sh, "shot_props": {}, "audio": f"audio/{i+1:02d}.mp3",
                        "duration": 8.0, "narration": "A sentence."} for i, sh in enumerate(shots)]}


def test_validate_warns_on_luminance_strobe():
    strobe = ["KnowledgeGraph", "BlockAssembly", "MaterialHero", "BlueprintGrid", "MapRoutes", "HandDrawn"]
    r = v.evaluate(_remotion_deck(strobe), "/tmp")                  # dark/light every seam -> strobe
    assert r["ok"] and any("STROBES" in w for w in r["warnings"]), r["warnings"]
    calm = ["CinematicTitle", "KnowledgeGraph", "MaterialHero", "MapRoutes", "FocalIsolation", "ParticleForm"]
    assert not any("STROBES" in w for w in v.evaluate(_remotion_deck(calm), "/tmp")["warnings"])   # all dark -> calm


def test_registry_in_sync_with_shot_files():
    # every shot file is a valid id, and there are 100 of them (the whole library)
    assert len(_SHOT_IDS) == 100, _SHOT_IDS
    assert rr._remotion_shot_ids() == _SHOT_IDS
    # the FAMILY map covers every shot (shot_director can place any of them)
    missing = _SHOT_IDS - set(sd.FAMILY)
    assert not missing, "shots missing from shot_director.FAMILY: %s" % missing


def test_valid_deck_passes():
    r = v.evaluate(_deck(6), "/tmp")
    assert r["ok"], r["errors"]
    assert r["scenes"] == 6


def test_missing_shot_errors():
    d = _deck(3)
    d["slides"][0].pop("shot")            # a missing shot is a STRUCTURAL error (sb.validate, caught early)
    r = v.evaluate(d, "/tmp")
    assert not r["ok"]
    assert any("shot" in e for e in r["errors"])


def test_unknown_shot_errors():
    d = _deck(3)
    d["slides"][1]["shot"] = "NotAShot"   # a present-but-invalid id is caught by _check_remotion
    r = v.evaluate(d, "/tmp")
    assert not r["ok"]
    assert any("unknown shot" in e for e in r["errors"])


def test_number_bearing_shot_warns_on_demo_default():
    d = _deck(2)
    d["slides"][0]["shot"] = "ChartLive"      # a number-bearing register...
    d["slides"][0]["shot_props"] = {}         # ...left on its demo number
    r = v.evaluate(d, "/tmp")
    assert any("SOURCED figure" in w for w in r["warnings"])
    # passing the sourced figure silences it
    d["slides"][0]["shot_props"] = {"endVal": 68, "unit": "×", "label": "surge"}
    r2 = v.evaluate(d, "/tmp")
    assert not any("SOURCED figure" in w for w in r2["warnings"])


def test_shot_director_varies_family():
    cp = {"beats": [{"id": i + 1, "visual_intent": vi} for i, vi in
                    enumerate(["statement", "statement", "structure", "list", "metric", "statement",
                               "sequence", "structure", "statement", "structure"])]}
    data = {"meta": {}, "slides": [{"index": i + 1} for i in range(10)]}
    sd.assign_shots(data, cp)
    fams = [sd.FAMILY[s["shot"]] for s in data["slides"]]
    adj = sum(1 for a, b in zip(fams, fams[1:]) if a == b)
    assert adj == 0, "adjacent same-family repeats: %s" % list(zip([s["shot"] for s in data["slides"]], fams))
    assert data["meta"]["renderer"] == "remotion"
    assert all(s["shot"] in _SHOT_IDS for s in data["slides"])


# --- shot-template CONTEST (the remotion analogue of the html register-contest) ---

def _cp10():
    return {"beats": [{"id": i + 1, "visual_intent": vi} for i, vi in
                      enumerate(["statement", "structure", "list", "metric", "sequence",
                                 "statement", "structure", "list", "metric", "statement"])]}


def test_route_returns_n_distinct_and_hero_valid():
    for topic in ["quarterly market analytics report", "indie pixel platformer game",
                  "developer CLI for kubernetes", "a lifestyle wellness brand"]:
        cands = st.route(topic, 3)
        assert len(cands) == 3 and len(set(cands)) == 3, cands       # always 3 distinct
        assert all(c in st.TEMPLATES for c in cands)
        for c in cands:
            hero, props = st.contest_still(c, topic)
            assert hero in _SHOT_IDS, hero                            # the contest still is renderable
            assert isinstance(props, dict)


def test_template_biases_families_but_keeps_variety():
    # the chosen direction must LEAN toward its families AND never place two adjacent same-family beats
    for tmpl, fams in [("data-story", {"D", "F", "H"}), ("retro-playful", {"C", "G", "I"}),
                       ("terminal-technical", {"A", "C", "D"})]:
        data = {"meta": {}, "slides": [{"index": i + 1} for i in range(10)]}
        sd.assign_shots(data, _cp10(), template=tmpl)
        seq = [sd.FAMILY[s["shot"]] for s in data["slides"]]
        assert sum(1 for a, b in zip(seq, seq[1:]) if a == b) == 0, seq   # variety still wins
        assert data["meta"]["shot_template"] == tmpl
        in_dir = sum(1 for f in seq if f in fams)
        assert in_dir >= len(seq) // 2, "%s: only %d/%d beats in-direction (%s)" % (tmpl, in_dir, len(seq), seq)


def test_validate_warns_on_bespoke_template():
    # bespoke (topic-conceived) directions are ALLOWED — a non-seed key warns (heads-up), it does not error
    d = _deck(3)
    d["meta"]["shot_template"] = "molten-ledger-noir"
    r = v.evaluate(d, "/tmp")
    assert r["ok"] and any("not one of the 6 SEED directions" in w for w in r["warnings"])


def test_validate_warns_on_template_without_contest():
    d = _deck(3)
    d["meta"]["shot_template"] = "data-story"
    r = v.evaluate(d, "/tmp")
    assert r["ok"] and any("no `meta.shot_template_contest`" in w for w in r["warnings"])


def test_validate_bold_audacity_requires_contest():
    d = _deck(3)
    d["meta"]["audacity"] = "bold"; d["meta"]["shot_template"] = "data-story"
    r = v.evaluate(d, "/tmp")
    assert not r["ok"] and any("REQUIRES a `meta.shot_template_contest`" in e for e in r["errors"])
    # conservative may skip the contest entirely
    d["meta"]["audacity"] = "conservative"; d["meta"].pop("shot_template", None)
    assert v.evaluate(d, "/tmp")["ok"]


def test_validate_warns_on_over_marked_seams():
    # marking EVERY seam kinetic is as monotonous as marking none — validate warns past the budget
    d = _deck(6)                                    # 6 scenes -> 5 seams -> budget max(3, 5//3)=3
    for s in d["slides"][1:]:
        s["transition_style"] = "slide"
    r = v.evaluate(d, "/tmp")
    assert r["ok"] and any("MARKED with a kinetic transition" in w for w in r["warnings"]), r["warnings"]
    # a budgeted film (2 marks) stays clean
    d2 = _deck(6)
    d2["slides"][2]["transition_style"] = "clock"
    d2["slides"][4]["transition_style"] = "dissolve"
    assert not any("MARKED with a kinetic transition" in w for w in v.evaluate(d2, "/tmp")["warnings"])


def test_keyframe_qa_remotion_flags_blank():
    import keyframe_qa_remotion as kq
    bad = kq.evaluate([("01", "/a", True, 3.0), ("02", "/b", True, 40.0), ("03", "/c", False, None)])
    assert not bad["ok"] and bad["blank"][0]["scene"] == "01" and "03" in bad["missing"]
    good = kq.evaluate([("01", "/a", True, 30.0), ("02", "/b", True, 40.0)])
    assert good["ok"]


def test_validate_contest_shape_and_winner():
    d = _deck(3)
    d["meta"]["shot_template"] = "data-story"
    # too few candidates -> error
    d["meta"]["shot_template_contest"] = {"candidates": ["data-story"], "winner": "data-story", "user_pick": True}
    assert any(">=2 `candidates`" in e for e in v.evaluate(d, "/tmp")["errors"])
    # winner != chosen template -> error
    d["meta"]["shot_template_contest"] = {"candidates": ["data-story", "product-demo"],
                                          "winner": "product-demo", "user_pick": True}
    assert any("winner" in e for e in v.evaluate(d, "/tmp")["errors"])
    # well-formed contest -> clean
    d["meta"]["shot_template_contest"] = {"candidates": ["data-story", "product-demo", "kinetic-editorial"],
                                          "winner": "data-story", "user_pick": True}
    r = v.evaluate(d, "/tmp")
    assert r["ok"] and not any("shot_template" in w for w in r["warnings"]), r["warnings"]


def test_contest_frame_within_every_hero_duration():
    # CONTEST_FRAME must be a SETTLED frame for every hero (not past its DURATION -> render would error)
    import re
    heroes = {st.contest_still(k, "x")[0] for k in st.TEMPLATES}
    for hero in heroes:
        src = open(os.path.join(_SHOTS_DIR, hero + ".tsx"), encoding="utf-8").read()
        m = re.search(r"export const DURATION\s*=\s*(\d+)", src)
        assert m, hero
        assert st.CONTEST_FRAME < int(m.group(1)), "%s DURATION=%s <= CONTEST_FRAME" % (hero, m.group(1))
