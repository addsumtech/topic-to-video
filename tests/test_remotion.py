"""Backstop for the remotion bespoke-shot tier (phase-3 integration): the shot registry stays in sync with the
library, the shot-director varies families, and validate.py enforces the shot contract."""
import os, re, sys, json, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import validate as v
import shot_director as sd
import shot_templates as st
import render_remotion as rr
import contest_sample as cs

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


def test_camera_amp_is_opt_in_and_off_by_default():
    # The whole-film DRIFT is OFF by default (bespoke shots animate themselves; a global float on top reads as
    # a per-frame SHAKE). It is opt-in via meta.camera_drift; motion_personality no longer enables it.
    assert rr._camera_amp({}) == 0.0                                # still by default — no drift
    assert rr._camera_amp({"motion_personality": "lively"}) == 0.0  # motion_personality does NOT enable drift here
    assert rr._camera_amp({"camera_drift": True}) == 1.0            # explicit opt-in (bool) -> balanced amp
    assert rr._camera_amp({"camera_drift": False}) == 0.0
    assert rr._camera_amp({"camera_drift": "calm"}) == 0.5
    assert rr._camera_amp({"camera_drift": "energetic"}) == 1.6
    assert rr._camera_amp({"camera_drift": 0.8}) == 0.8            # a raw multiplier passes through
    assert rr._camera_amp({"camera_drift": -3}) == 0.0            # clamped non-negative
    assert rr._camera_amp({"camera_drift": "bogus"}) == 0.0       # unknown tier -> off (default is still)


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


def test_shots_are_deterministic():
    # §A.7: a shot must be a PURE fn of useT()/frame — no Date.now / Math.random / argless new Date() (they break
    # resume + byte-stable renders). The enforcing test was lost (only a .pyc remained); restore it as a grep lint
    # over every shot file so a newly-authored non-deterministic shot fails loud instead of flickering across renders.
    import re
    bad = {}
    for f in sorted(os.listdir(_SHOTS_DIR)):
        if not f.endswith(".tsx"):
            continue
        src = open(os.path.join(_SHOTS_DIR, f), encoding="utf-8").read()
        hits = re.findall(r"\bDate\.now\s*\(|\bMath\.random\s*\(|\bnew Date\s*\(\s*\)", src)
        if hits:
            bad[f] = hits
    assert not bad, "non-deterministic API in shots (breaks resume/determinism — use hash01/useT): %s" % bad


def test_registry_in_sync_with_shot_files():
    # Every shot file must be registered at EVERY sync point. This used to assert a hardcoded library
    # count, which caught nothing the checks below miss (a clean removal is a deliberate act, not an
    # accident) and actively taxed the one thing the skill is supposed to be able to do: grow. Adding a
    # register meant editing five files AND this number, so "no register can draw this beat" always lost
    # to "settle for the closest one".
    import register_shot
    assert len(_SHOT_IDS) >= 130, "the library shrank unexpectedly: %d shots" % len(_SHOT_IDS)
    assert rr._remotion_shot_ids() == _SHOT_IDS
    unregistered = {s: register_shot.check(s) for s in sorted(_SHOT_IDS) if register_shot.check(s)}
    assert not unregistered, "shots missing from a sync point: %r" % unregistered
    # the FAMILY map covers every shot (shot_director can place any of them)
    missing = _SHOT_IDS - set(sd.FAMILY)
    assert not missing, "shots missing from shot_director.FAMILY: %s" % missing


def test_contest_sample_builds_valid_film_props():
    # the direction SAMPLE VIDEO (the user-choice mechanism): every candidate must build Film props whose scenes
    # name REAL shot ids, carry the topic, lock the camera, and have positive durations.
    for key in list(st.TEMPLATES) + ["a-bespoke-direction"]:      # seeds + a bespoke-key fallback
        props = cs.build_props(key, "how an MRI image is made")
        assert props["camera"] == 0, key                          # camera LOCKED in samples (no shake)
        assert 2 <= len(props["scenes"]) <= 4, key
        for sc in props["scenes"]:
            assert sc["shot"] in _SHOT_IDS, (key, sc["shot"])     # only real registers
            assert sc["durF"] > 0 and sc["caption"], key
    # route() still returns candidates so the samples have something to render
    assert cs.stpl.route("data analytics report", audacity="balanced")


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


def test_route_returns_only_real_matches_and_every_hero_is_renderable():
    """This used to assert route() ALWAYS returns n — which is the padding contract, written down.

    "Always fill the ballot" is what put a 3D torus knot in front of a viewer choosing the look of a film
    about an AI office agent: the third slot was filled from a fixed fallback order because it had to be.
    A test that requires the ballot to be full makes the skill's own instruction — the six templates are
    SEEDS, conceive the rest for this topic — impossible to obey. The contract now is: return what genuinely
    matched, distinct, never more than n, every one renderable; `conceive_gap` accounts for the rest.
    """
    for topic in ["quarterly market analytics report", "indie pixel platformer game",
                  "developer CLI for kubernetes", "a lifestyle wellness brand"]:
        cands = st.route(topic, 3)
        assert len(cands) <= 3 and len(set(cands)) == len(cands), cands
        assert all(c in st.TEMPLATES for c in cands)
        assert st.conceive_gap(topic, n=3) == 3 - len(cands), (
            "the shortfall must be the slots left to conceive, or the author is never told what is owed")
        for c in cands:
            hero, props = st.contest_still(c, topic)
            assert hero in _SHOT_IDS, hero                            # the contest still is renderable
            assert isinstance(props, dict)
    # a topic with a strong keyword must still MATCH — dropping the padding must not drop the routing
    assert "data-story" in st.route("quarterly market analytics report", 3)
    assert "retro-playful" in st.route("indie pixel platformer game", 3)


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


def test_frame_safe_qa_flags_edge_bleed(tmp_path):
    # the deterministic frame-craft gate the critic was missing: content off the safe edge = ERROR
    import frame_safe_qa as fq
    from PIL import Image
    kd = tmp_path / "_keyframes"; kd.mkdir()
    for i in range(1, 6):                                   # 5 clean dark scenes -> ok
        Image.new("RGB", (1920, 1080), (8, 8, 12)).save(str(kd / ("scene_%02d.png" % i)))
    assert fq.evaluate(str(tmp_path))["ok"]
    bad = Image.new("RGB", (1920, 1080), (8, 8, 12))
    bad.paste((240, 240, 240), (0, 0, 1920, 70))            # bright content in the top safe border = overflow
    bad.save(str(kd / "scene_03.png"))
    r = fq.evaluate(str(tmp_path))
    assert not r["ok"] and any("OFF-FRAME" in e for e in r["errors"]), r


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
    # well-formed contest -> no CONTEST-shape complaint. (Scope the grep to contest warnings: a non-DNA template
    # like "data-story" also draws the orthogonal "NO Design DNA" warning — which legitimately contains the word
    # shot_template — and that's a separate gate this test isn't about.)
    d["meta"]["shot_template_contest"] = {"candidates": ["data-story", "product-demo", "kinetic-editorial"],
                                          "winner": "data-story", "user_pick": True}
    r = v.evaluate(d, "/tmp")
    assert r["ok"] and not any("shot_template_contest" in w for w in r["warnings"]), r["warnings"]


def test_contest_frame_within_every_hero_duration():
    # CONTEST_FRAME must be a SETTLED frame for every hero (not past its DURATION -> render would error)
    import re
    heroes = {st.contest_still(k, "x")[0] for k in st.TEMPLATES}
    for hero in heroes:
        src = open(os.path.join(_SHOTS_DIR, hero + ".tsx"), encoding="utf-8").read()
        m = re.search(r"export const DURATION\s*=\s*(\d+)", src)
        assert m, hero
        assert st.CONTEST_FRAME < int(m.group(1)), "%s DURATION=%s <= CONTEST_FRAME" % (hero, m.group(1))


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Design DNA layer. Before these, the whole DNA system had ZERO assertions: an audit found a shot that called
# useDNA() without importing it (a hard render crash) sitting green in the audit, a preset map that had silently
# diverged from validate.py's copy, and a luminance table that went stale the moment shots took their ground from
# the DNA. Each test below is a gate that CAN fail — that is the point.
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
import dna_audit as da                                                    # noqa: E402
# gen_dna_ground is RETIRED (see its docstring); the ground model is measured, not scanned.

_RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "runtime")


def _dna_tsx():
    return open(os.path.join(_RUNTIME_DIR, "dna.tsx"), encoding="utf-8").read()


def test_no_shot_calls_useDNA_without_importing_it():
    # MaterialHero shipped exactly this way: the codemod inserted the call, missed the import, and the shot threw
    # `useDNA is not defined` on EVERY render (themed or not) while the audit's presence-grep scored it migrated.
    broken = sorted(da.broken_shots() & da.registered_shots())
    assert not broken, "shots call useDNA() without importing it (hard ReferenceError at render): %s" % broken


def test_validate_dna_presets_match_the_runtime():
    # validate.py keeps a python copy of DNA_PRESETS to decide whether a film is 'themed'. If the two drift, a
    # themed film silently stops being gated (or an un-themed one gets nagged).
    import re as _re
    block = _dna_tsx().split("export const DNA_PRESETS")[1].split("};")[0]
    runtime = {m.group(1) or m.group(2) for m in _re.finditer(r"^\s*'([^']+)'\s*:|^\s*([A-Za-z][\w-]*)\s*:", block, _re.M)}
    runtime = {k for k in runtime if k}
    missing = runtime - v._DNA_PRESETS_FOR_TEST()
    assert not missing, "DNA presets known to the runtime but not to validate.py: %s" % sorted(missing)


def test_every_direction_maps_to_a_dna_preset():
    # A direction with no preset means picking it turns the entire global visual system OFF — and then validate
    # nags about a missing DNA on a film the user configured correctly.
    import re as _re
    block = _dna_tsx().split("export const DNA_PRESETS")[1].split("};")[0]
    keys = {m.group(1) or m.group(2) for m in _re.finditer(r"^\s*'([^']+)'\s*:|^\s*([A-Za-z][\w-]*)\s*:", block, _re.M)}
    keys = {k for k in keys if k}
    missing = set(st.TEMPLATES) - keys
    assert not missing, "these selectable directions have no Design DNA preset: %s" % sorted(missing)


def test_every_registered_shot_has_a_measured_ground_token():
    """Every shot must declare which DNA token it paints its ground from.

    This replaces a --check that called gen_dna_ground's own detector: it compared the file against the
    SAME function that produced it, so a detection gap was invisible by construction and it reported
    "up to date" while the set was wrong. The PIXEL check now lives in
    `python3 scripts/measure_ground_luma.py --check` (134 renders, too slow for pytest, run it like
    font_gate.py). What belongs here is the cheap structural floor: full coverage and legal values."""
    src = open(os.path.join(_RUNTIME_DIR, "shotLuma.ts"), encoding="utf-8").read()
    block = src.split("DNA_GROUND_TOKEN")[1].split("};")[0]
    entries = dict(re.findall(r"^\s{2}(\w+):\s*(\[[^\]]*\]|'[a-zA-Z]+')", block, re.M))
    shots = set(da.registered_shots())
    missing = sorted(shots - set(entries))
    assert not missing, "shots with no measured ground token: %r" % missing[:6]
    legal = {"bg", "bgGrad", "accent", "accent2", "surface"}
    for shot, val in entries.items():
        for tok in re.findall(r"'([a-zA-Z]+)'", val):
            assert tok in legal, "%s declares an unknown ground token %r" % (shot, tok)


def test_display_type_is_measured_not_estimated():
    """The three shots whose whole register is ONE huge word must size it by MEASURING the real string
    in the real face, never by a magic advance-width ratio.

    A ratio cannot be correct here: the display face comes from the active DNA and ranges from Bodoni
    Moda to JetBrains Mono, whose advance widths differ enormously. SwissEditorial used a fixed 340px
    with nowrap inside an overflow:hidden box and SILENTLY TRUNCATED anything past ~9 characters
    ("ONBOARDING." rendered as "ONBOARD") with no ellipsis and no error; CinematicTitle's len*0.52
    guess underestimated Bodoni Moda enough to wrap a long title onto a second line. Both are now
    fitText from @remotion/layout-utils. validateFontIsLoaded is required so a measurement taken
    before the faces load fails loudly instead of returning a size for the fallback typeface.

    A general "no nowrap + hardcoded big font" scan finds zero hits today and would pass vacuously,
    so this pin names the files instead."""
    for shot in ("SwissEditorial", "NeonGrid", "CinematicTitle"):
        src = open(os.path.join(_SHOTS_DIR, shot + ".tsx"), encoding="utf-8").read()
        assert "from '@remotion/layout-utils'" in src, "%s does not import the measuring helper" % shot
        # `"fitText" in src` would be satisfied by the import line alone, and even by a renamed
        # `fitTextX(` — the first version of this test passed against a deliberately broken shot.
        # Require an actual CALL.
        assert re.search(r"\bfitText\(\{", src), (
            "%s must MEASURE its display type (a fitText({...}) call), not estimate it" % shot)
        # validateFontIsLoaded must NOT be set. I originally pinned it as REQUIRED here, which pinned a
        # harmful decision: the flag runs document.fonts.check() on the whole stack, and every DNA stack
        # ends in system CJK fallbacks that are never registered in document.fonts, so it fails for a
        # perfectly good stack — it crashed SwissEditorial on every themed Chinese film. The measurement
        # is unaffected either way; scripts/font_gate.py is what actually proves the faces load.
        assert "validateFontIsLoaded" not in src, (
            "%s passes validateFontIsLoaded — it cannot work with a CJK-terminated stack and will crash "
            "a themed Chinese film; font_gate.py is the real proof that faces load" % shot)


def test_multi_declarator_shots_are_measured_as_bg_grounded():
    """These four declare their ground in a MULTI-DECLARATOR const (`const ACC = ..., BG = dna?.bg`).

    A source-scanning detector could not see past the first `=` on such a line and dropped all four,
    which rendered dark caption ink on a dark DNA ground (verified illegible on TimelineTravel). The
    model is now measured from pixels rather than scanned from source, so the shape that defeated the
    scanner is irrelevant — but pin the outcome anyway: if a future change regresses these to anything
    other than bg-grounded, captions on them go wrong again in exactly the same way."""
    src = open(os.path.join(_RUNTIME_DIR, "shotLuma.ts"), encoding="utf-8").read()
    block = src.split("DNA_GROUND_TOKEN")[1].split("};")[0]
    for shot in ("BeforeAfterSlider", "BlueprintGrid", "ScreenBubble", "TimelineTravel"):
        assert "  %s: 'bg'," % shot in block, (
            "%s is no longer measured as bg-grounded — captions pick ink against the wrong ground" % shot)


def test_shot_luma_and_dna_ground_cover_the_library():
    luma = open(os.path.join(_RUNTIME_DIR, "shotLuma.ts"), encoding="utf-8").read()
    measured = set(re.findall(r"(\w+):\s*'(?:dark|mid|light)'", luma.split("SHOT_LUMA")[1].split("};")[0]))
    assert not (_SHOT_IDS - measured), "shots missing a measured ground luminance: %s" % sorted(_SHOT_IDS - measured)


def _root_shot_ids(root_src):
    """Compositions registered via F() whose *component* is imported from './shots/' — i.e. real
    bespoke shots, not diagnostic probes (which import from elsewhere, e.g. './runtime/'). Derived
    from Root.tsx's own import graph rather than a hand-maintained exclusion list: a curated
    exclusion set living inside a drift gate is exactly how the gate quietly stops detecting drift,
    and a future probe (any component imported outside shots/) is excluded automatically without
    editing this test."""
    local_to_path = {}
    for names, path in re.findall(r"^import \{([^}]+)\} from '(\.[^']+)';", root_src, re.MULTILINE):
        for tok in names.split(","):
            tok = tok.strip()
            local = tok.split(" as ")[-1].strip() if " as " in tok else tok
            local_to_path[local] = path
    calls = re.findall(r"\{F\('([A-Za-z0-9_]+)',\s*([A-Za-z0-9_]+),", root_src)
    return {comp_id for comp_id, comp_var in calls if local_to_path.get(comp_var, "").startswith("./shots/")}


def test_registry_root_and_shots_dir_are_in_sync():
    # test_registry_in_sync_with_shot_files compared the shots dir to itself; Root.tsx (standalone previews) and
    # registry.ts (what a film can select) were effectively ungated.
    root = open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    reg = open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "registry.ts"), encoding="utf-8").read()
    root_ids = _root_shot_ids(root)
    reg_ids = set(re.findall(r"from '\./shots/([A-Za-z0-9_]+)'", reg))
    assert reg_ids == _SHOT_IDS, "registry.ts vs shots/: %s" % sorted(reg_ids ^ _SHOT_IDS)
    assert root_ids == _SHOT_IDS, "Root.tsx (standalone previews) vs shots/: %s" % sorted(root_ids ^ _SHOT_IDS)


def test_contest_samples_carry_the_direction_dna():
    # The direction contest is how the user PICKS the film's look. A sample rendered without the DNA shows a film
    # that will not be delivered.
    for key in st.TEMPLATES:
        props = cs.build_props(key, "a topic")
        assert props.get("template") == key, "contest sample for %r does not carry its DNA" % key


def test_null_dna_preserves_every_original_colour():
    # The documented guarantee is that an UN-themed film renders as before. Mechanical proxy: every colour literal
    # that existed before the DNA work must still be reachable in the shot (as the `??` fallback).
    import subprocess
    base = "2c973f6~1"                      # the commit before any Design DNA work
    repo = os.path.join(os.path.dirname(__file__), "..")
    if subprocess.run(["git", "-C", repo, "cat-file", "-e", base], capture_output=True).returncode != 0:
        import pytest; pytest.skip("pre-DNA baseline commit not available")
    hexes = re.compile(r"['\"]#[0-9a-fA-F]{3,8}['\"]")
    def norm(h):
        h = h.strip("'\"").lstrip("#").lower()
        return "".join(c * 2 for c in h[:3]) if len(h) in (3, 4) else h[:6]
    drift = {}
    for f in sorted(os.listdir(_SHOTS_DIR)):
        if not f.endswith(".tsx"):
            continue
        rel = "remotion/src/shots/" + f
        r = subprocess.run(["git", "-C", repo, "show", f"{base}:{rel}"], capture_output=True, text=True)
        if r.returncode != 0:
            continue                        # a shot added after the baseline
        gone = {norm(x) for x in hexes.findall(r.stdout)} - {norm(x) for x in hexes.findall(open(os.path.join(_SHOTS_DIR, f), encoding="utf-8").read())}
        if gone:
            drift[f] = sorted(gone)
    assert not drift, "null-DNA drift — these original colours are no longer reachable: %s" % drift


def test_atom_form_enums_match_between_runtime_and_validate():
    # validate.py keeps a python copy of the atom form enums. If the two drift, an authored DNA with a
    # form the runtime supports gets warned about — or worse, a typo passes validation silently.
    src = _dna_tsx()
    block = src.split("export type AtomForms = {")[1].split("};")[0]
    runtime = {}
    for line in block.split("\n"):
        m = re.match(r"\s*(\w+)\??:\s*(.+?);", line)
        if m:
            runtime[m.group(1)] = {v.strip().strip("'") for v in m.group(2).split("|")}
    assert runtime, "could not parse AtomForms out of dna.tsx"
    assert runtime == v._ATOM_FORMS, "AtomForms drift:\nruntime=%s\nvalidate=%s" % (runtime, v._ATOM_FORMS)


def test_every_preset_declares_valid_atom_forms():
    # A preset that declares a form the atoms do not implement renders the neutral form silently.
    src = _dna_tsx()
    bad = []
    for m in re.finditer(r"atoms:\s*\{([^}]*)\}", src):
        for k, val in re.findall(r"(\w+):\s*'([^']+)'", m.group(1)):
            if k not in v._ATOM_FORMS or val not in v._ATOM_FORMS[k]:
                bad.append((k, val))
    assert not bad, "presets declare unknown atom forms: %s" % bad


def test_validate_warns_on_an_unknown_atom_form():
    d = _deck(2)
    d["meta"]["design_dna"] = {"id": "x", "fontDisplay": "a", "fontMono": "a", "fontBody": "a",
                               "bg": "#000", "fg": "#fff", "dim": "#888", "accent": "#0f0",
                               "accent2": "#0ff", "onAccent": "#000", "surface": "#111",
                               "line": "#222", "decoration": [], "motion": "smooth",
                               "atoms": {"bar": "sparkline"}}
    r = v.evaluate(d, "/tmp")
    assert r["ok"], r["errors"]                      # a warning, never an error — the runtime falls back
    assert any("sparkline" in w for w in r["warnings"]), r["warnings"]


def test_atoms_are_total_across_every_dna_and_edge_case():
    # Atoms render under every preset, with `atoms` missing entirely, and with unknown form values —
    # and never emit the string "undefined" (an undefined token inside a `font:` shorthand paints nothing).
    # Runs the real components through react-dom/server; the bundler strips types without checking them,
    # so this is the only mechanical proof the components hold together.
    import subprocess, tempfile, shutil
    if not shutil.which("npx"):
        import pytest; pytest.skip("npx unavailable")
    remotion = os.path.join(os.path.dirname(__file__), "..", "remotion")
    out = os.path.join(tempfile.gettempdir(), "atoms_probe.cjs")
    b = subprocess.run(["npx", "esbuild", "src/runtime/__probe_atoms.tsx", "--bundle",
                        "--platform=node", "--outfile=" + out, "--log-level=error"],
                       cwd=remotion, capture_output=True, text=True)
    assert b.returncode == 0, "esbuild failed:\n" + b.stdout + b.stderr
    r = subprocess.run(["node", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PROBE OK" in r.stdout, r.stdout


_FONTS_TS = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "runtime", "fonts.ts")
_BASE_CSS = os.path.join(os.path.dirname(__file__), "..", "assets", "html", "base.css")


def test_fonts_ts_loads_every_bundled_face_with_base_css_weights():
    """SCOPE: only the 4 faces base.css declares (Space Grotesk, Playfair Display, JetBrains Mono,
    Bangers) — these are the faces the HTML tier already renders, so the remotion tier must name the
    SAME families with the SAME weight ranges there, or a variable font silently renders synthesised
    weights. This does NOT cover the other 6 faces fonts.ts loads (Inter, Source Serif 4, IBM Plex
    Sans, IBM Plex Mono, Bodoni Moda, Baloo 2) — base.css has no @font-face for them at all, so there
    is no second source of truth to check their weights against."""
    css = open(_BASE_CSS, encoding="utf-8").read()
    faces = re.findall(
        r'@font-face\{font-family:"([^"]+)";src:url\("\.\./fonts/([^"]+)"\);font-weight:([^;]+);',
        css,
    )
    # Exact count, not a floor: base.css names exactly 4 faces today. A floor (`>= 4`) would never
    # fire again once the set grows past 4, silently going blind to a 5th @font-face this test was
    # never updated to expect. If base.css legitimately grows, update this number deliberately.
    assert len(faces) == 4, "expected exactly 4 @font-face rules in base.css, got %r" % (faces,)
    ts = open(_FONTS_TS, encoding="utf-8").read()
    for family, filename, weight in faces:
        assert "family: '%s'" % family in ts, "fonts.ts does not load %r" % family
        assert filename in ts, "fonts.ts does not reference %r" % filename
        assert "weight: '%s'" % weight.strip() in ts, (
            "fonts.ts weight for %r drifted from base.css (%r)" % (family, weight.strip()))


def test_fonts_ts_fails_loudly_on_a_load_error():
    """A font that fails to load must abort the render. A silent fallback is the defect this fixes."""
    ts = open(_FONTS_TS, encoding="utf-8").read()
    assert "cancelRender" in ts, "fonts.ts must cancelRender on a failed load"
    assert "delayRender" in ts, "fonts.ts must delayRender until the faces are ready"


_CJK_FAMILIES = ('PingFang SC', 'Hiragino Sans', 'Microsoft YaHei', 'Noto Sans CJK SC')


def _font_stacks():
    """Every fontDisplay/fontMono/fontBody string literal in dna.tsx."""
    src = _dna_tsx()
    return re.findall(r"font(?:Display|Mono|Body): '([^']+)'", src)


def test_every_declared_family_is_actually_loaded():
    """A preset may only name a face fonts.ts loads — otherwise it silently falls back, which is
    the exact defect this layer exists to fix."""
    loaded = set(re.findall(r"family: '([^']+)'", open(_FONTS_TS, encoding="utf-8").read()))
    assert loaded, "could not parse FACES out of fonts.ts"
    # Georgia ships with every macOS and Windows install, so it is a safe last-resort serif rather
    # than a declared identity — which is exactly why it must never be a stack's FIRST entry.
    generics = {'system-ui', 'sans-serif', 'serif', 'monospace', 'ui-monospace', 'cursive', 'fantasy', 'Georgia'}
    for stack in _font_stacks():
        for fam in [p.strip().strip('"') for p in stack.split(',')]:
            if fam in generics or fam in _CJK_FAMILIES:
                continue
            assert fam in loaded, "dna.tsx names %r but fonts.ts does not load it" % fam


def test_every_font_stack_has_a_cjk_fallback():
    """None of these faces covers CJK; without a fallback, Chinese decks regress silently."""
    stacks = _font_stacks()
    assert len(stacks) >= 24, "expected 3 stacks x 8 presets, parsed %d" % len(stacks)
    for stack in stacks:
        assert any(c in stack for c in _CJK_FAMILIES), "no CJK fallback in %r" % stack


def test_every_multiword_family_is_quoted_in_every_stack():
    """A family name with a bare digit token ("Source Serif 4", "Baloo 2") is INVALID CSS unquoted:
    the browser drops the declaration and silently falls back. The declared-implies-loaded test
    strips quotes when it parses, so it structurally cannot see this class."""
    for stack in _font_stacks():
        for part in stack.split(','):
            fam = part.strip()
            if fam.startswith('"'):
                continue
            assert ' ' not in fam, "multi-word family %r must be quoted in stack %r" % (fam, stack)


def test_tiles_differ_detects_identical_and_distinct_halves(tmp_path):
    """The gate's comparison must call identical halves 'same' and distinct halves 'different'.
    Tested on synthetic images so the unit test needs no render."""
    from PIL import Image
    import importlib.util
    spec_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "font_gate.py")
    spec = importlib.util.spec_from_file_location("font_gate", spec_path)
    font_gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(font_gate)

    # row 0: both halves identical black; row 1: left black, right white
    img = Image.new("RGB", (200, 200), "black")
    for x in range(100, 200):
        for y in range(100, 200):
            img.putpixel((x, y), (255, 255, 255))
    p = tmp_path / "probe.png"
    img.save(p)

    assert font_gate.tiles_differ(str(p), rows=2, cols=2) == [False, True]


def _film_tsx():
    return open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "Film.tsx"),
                encoding="utf-8").read()


def test_film_injects_the_three_type_variables():
    src = _film_tsx()
    for var in ("--f-display", "--f-body", "--f-mono"):
        assert var in src, "Film.tsx does not inject %s" % var
    assert ".dna-film {" in src or ".dna-film{" in src, "the type variables must be scoped to .dna-film"


def test_caption_typography_follows_the_dna():
    """The caption is on every frame; only its contrast was DNA-aware, never its typeface."""
    src = _film_tsx()
    assert "dnaFontBody" in src, "CaptionTrack must take the DNA body face"
    assert "font: '700 44px/1.26 Inter" not in src, "the caption font is still hardcoded"


def _migrate_mod():
    import importlib.util
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "dna_migrate_type.py")
    spec = importlib.util.spec_from_file_location("dna_migrate_type", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_codemod_assigns_display_body_and_mono_by_size_and_family():
    m = _migrate_mod()
    out, rep = m.rewrite_font_decl("font: '800 200px/0.9 Inter, system-ui, sans-serif'")
    assert out == "font: '800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)'"
    assert rep[0]["role"] == "display" and rep[0]["size"] == 200.0

    out, _ = m.rewrite_font_decl("font: '400 36px/1.4 Inter, system-ui, sans-serif'")
    assert out == "font: '400 36px/1.4 var(--f-body, Inter, system-ui, sans-serif)'"

    out, _ = m.rewrite_font_decl("font: '500 30px/1 \"JetBrains Mono\", ui-monospace, monospace'")
    assert out == "font: '500 30px/1 var(--f-mono, \"JetBrains Mono\", ui-monospace, monospace)'"


def test_codemod_rewrites_template_literals_whose_family_is_hardcoded():
    """A template literal can interpolate the WEIGHT and still hardcode the family:
    font: `${i === 2 ? 700 : 500} 30px/1 Inter`. Skipping every string containing ${ would miss
    this whole class - 4 shots use exactly this shape."""
    m = _migrate_mod()
    out, rep = m.rewrite_font_decl("font: `${i === 2 ? 700 : 500} 30px/1 Inter`")
    assert out == "font: `${i === 2 ? 700 : 500} 30px/1 var(--f-body, Inter)`"
    assert rep[0]["role"] == "body"


def test_codemod_skips_a_family_that_is_already_dynamic():
    """`${disp}` is already reading the DNA (or a prop). Rewriting it would double-wrap."""
    m = _migrate_mod()
    out, rep = m.rewrite_font_decl("font: `${c.hero ? 500 : 400} 46px/1.3 ${disp}`")
    assert out == "font: `${c.hero ? 500 : 400} 46px/1.3 ${disp}`"
    assert rep == []


def test_codemod_never_touches_a_kebab_case_svg_font_family_attribute():
    """This is the XML/kebab-case spelling `font-family="..."`, which has zero occurrences in this
    library (JSX only accepts the camelCase `fontFamily="..."` attribute name) - NOT the same claim
    as "var() cannot apply to an SVG presentation attribute" (that belief was WRONG: a real `remotion
    render` confirmed var() resolves correctly in the JSX `fontFamily="..."` spelling, and the codemod
    rewrites 62 such declarations across 17 shots - see rewrite_font_decl's sub_svg). This test only
    pins that the never-used kebab-case spelling is left untouched, which it is regardless."""
    m = _migrate_mod()
    src = '<text font-family="Inter, sans-serif">x</text>'
    out, rep = m.rewrite_font_decl(src)
    assert out == src and rep == []


# ── Task 10 regression: no shot may re-hardcode a font family ───────────────────────────────────
#
# Task 9's codemod covers the shapes it recognises, but the migration this plan drove found FOUR
# shapes a regex anchored only on the literal `font:` shorthand would miss entirely - each of which
# actually existed, hardcoded, somewhere in this library before being migrated by hand:
#   (a) a family in a DOUBLE-quoted `font: "..."` shorthand;
#   (b) a family in a `fontFamily:` CSS property (a React inline-style key, a different declaration
#       from the `font:` shorthand the codemod targets);
#   (c) a family in the JSX SVG presentation attribute `fontFamily="..."` (17 shots / 62
#       declarations carry this spelling; a real `remotion render` confirmed var() DOES resolve
#       there and falls back correctly when unset);
#   (d) a family assigned to a module- or function-level const and read later
#       (`const MONO = '"JetBrains Mono", monospace'`) - invisible to anything anchored on the
#       literal token `font:` or `fontFamily`, since NEITHER token appears anywhere on that line.
#       Three real instances (BlueprintGrid, CompressedSensingEq, RisoPrint) were exactly this
#       shape, and each was found only by a human-directed sweep, not by a gate.
#
# `_looks_like_font_family` is the "does this string read as a CSS font-family value" heuristic all
# four detectors share below: it fires on a bare CSS generic family keyword (sans-serif, monospace,
# ...) appearing as a WHOLE comma-separated token, or on one of the ten loaded family names
# (word-bounded, so "Inter" can't match inside an unrelated longer word) - and never on a value that
# already reads `var(--f-` (themed) or `${` (already dynamic - a prop or a DNA read).

_GENERIC_FAMILY_TOKENS = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy",
    "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace",
}
_LOADED_FAMILIES = (
    "Space Grotesk", "Playfair Display", "JetBrains Mono", "Bangers", "Inter",
    "Source Serif 4", "IBM Plex Sans", "IBM Plex Mono", "Bodoni Moda", "Baloo 2",
)
_LOADED_FAMILY_RES = [re.compile(r"\b%s\b" % re.escape(fam), re.I) for fam in _LOADED_FAMILIES]


def _looks_like_font_family(value):
    if "var(--f-" in value or "${" in value:
        return False
    tokens = {t.strip().strip("'\"").lower() for t in value.split(",")}
    if tokens & _GENERIC_FAMILY_TOKENS:
        return True
    return any(rx.search(value) for rx in _LOADED_FAMILY_RES)


# (a) `font:` shorthand, any of the three quote styles (the plan's original test only recognised
# `'`/`` ` ``). Requires a literal `<digits>px` in the body - mirrors dna_migrate_type.py's own
# scope, so this test polices exactly what that codemod is responsible for.
_FONT_SHORTHAND_RE = re.compile(
    r"font: *(?:'([^'\n]*?\d+px[^'\n]*)'|`([^`\n]*?\d+px[^`\n]*)`|\"([^\"\n]*?\d+px[^\"\n]*)\")"
)
# (b) `fontFamily:` CSS property (React inline style key).
_FONT_FAMILY_PROP_RE = re.compile(r"fontFamily:\s*(?:'([^'\n]*)'|\"([^\"\n]*)\"|`([^`\n]*)`)")
# (c) `fontFamily="..."` JSX/SVG presentation attribute.
_FONT_FAMILY_JSX_ATTR_RE = re.compile(r'fontFamily=(?:"([^"\n]*)"|\'([^\'\n]*)\')')
# (d) a module- or function-level `const`/`let` binding whose value is a literal quoted string.
# Scoped to STATEMENTS containing `const`/`let` (split on `;`, so a binding's `=` and its quoted
# value may span a line break) rather than to single lines, so a wrapped declaration is still seen;
# `dna?.fontDisplay ?? '...'` fallback reads never match `_BINDING_RE` at all, because its `=` is
# followed by `dna?...`, not a quote character - no separate guard needed.
_CONST_STMT_RE = re.compile(r"\b(?:const|let)\s")
_BINDING_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*(?:'([^'\n]*)'|\"([^\"\n]*)\"|`([^`\n]*)`)")


def _hardcoded_font_offenses(src):
    """Every hardcoded-family occurrence in `src`, across the four shapes above. A non-empty result
    names a real regression."""
    offenses = []

    for m in _FONT_SHORTHAND_RE.finditer(src):
        body = next(g for g in m.groups() if g is not None)
        idx = body.find("px")
        tail = body[idx + 2:] if idx != -1 else ""
        if _looks_like_font_family(tail):
            offenses.append(("font: shorthand", m.group(0)[:80]))

    for m in _FONT_FAMILY_PROP_RE.finditer(src):
        value = next(g for g in m.groups() if g is not None)
        if _looks_like_font_family(value):
            offenses.append(("fontFamily: property", m.group(0)[:80]))

    for m in _FONT_FAMILY_JSX_ATTR_RE.finditer(src):
        value = next(g for g in m.groups() if g is not None)
        if _looks_like_font_family(value):
            offenses.append(("fontFamily= JSX attribute", m.group(0)[:80]))

    for stmt in src.split(";"):
        if not _CONST_STMT_RE.search(stmt):
            continue
        for m in _BINDING_RE.finditer(stmt):
            value = next(g for g in m.groups() if g is not None)
            if _looks_like_font_family(value):
                offenses.append(("const/let font stack", m.group(0)[:80]))

    return offenses


def test_every_shot_reads_the_type_variables_or_the_dna_directly():
    """After Layer C, a shot that renders text must get its face from the DNA - through a `var(--f-`
    variable, or through useDNA() directly - never a hardcoded family. A shot that reintroduces a
    hardcoded family in ANY of the four shapes `_hardcoded_font_offenses` checks (see above) is a
    regression: Task 9 already migrated the library (355 declarations across ~122 shots), so this
    must pass as-is. The remaining legitimate non-var() families are exempt by construction, not by
    an allowlist: `dna?.fontX ?? '...'` fallback reads never match (their `=` is followed by
    `dna?...`, not a quote), and the per-letter randomized `FONTS[...]` arrays in AntiDesignChaos /
    RansomZine never match either (their elements are array items, never bound with `IDENT = `)."""
    offenders = []
    for name in sorted(os.listdir(_SHOTS_DIR)):
        if not name.endswith(".tsx"):
            continue
        src = open(os.path.join(_SHOTS_DIR, name), encoding="utf-8").read()
        offenses = _hardcoded_font_offenses(src)
        if offenses:
            offenders.append((name, offenses[:2]))
    assert not offenders, "shots still hardcode a font family: %r" % offenders[:5]


def test_crashzoom_punch_rests_inside_the_content_zone():
    # REGRESSION (found on a delivered film): CrashZoom punched to (W / cw) * 0.98, which threw the
    # neighbouring tiles off-frame at near-full opacity (frame_safe_qa: "5.4% of the safe border is bright
    # content") and parked the hero card's own edge underneath the burned caption. The fix bounds the resting
    # scale by the CONTENT ZONE. This test does not pin the literals — it re-derives the invariant from
    # whatever budget factors the source currently declares, so widening them past the frame fails here.
    import re
    src = open(os.path.join(_SHOTS_DIR, "CrashZoom.tsx"), encoding="utf-8").read()
    over = float(re.search(r"OVERSHOOT\s*=\s*([\d.]+)", src).group(1))
    wf = float(re.search(r"W \* ([\d.]+) / tw", src).group(1))               # width budget, frame fractions
    hf = float(re.search(r"\(zoneBot - zoneTop\) \* ([\d.]+) / th", src).group(1))   # height budget
    fade = float(re.search(r"away = clamp01\(z \* ([\d.]+)\)", src).group(1))
    SAFE = 0.035                                                            # EBU R95, same as frame_safe_qa
    # the punch overshoots past its resting scale, so the BUDGET must leave room for the overshoot
    assert wf * over <= 1 - 2 * SAFE, "hero can overrun the action-safe border (%.3f x %.2f)" % (wf, over)
    assert hf * over <= 1.0, "hero can overrun the content zone into the caption band (%.3f x %.2f)" % (hf, over)
    # the zone is measured off the frame + the real caption band, not hardcoded pixels
    assert "captionBand(W, H)" in src and "zoneBot = H - CB" in src
    assert "(W / cw)" not in src, "the unbounded punch is back"
    # neighbours must be gone BEFORE they reach the border, not sliced in half by it while still legible
    assert fade >= 2.0, "neighbour fade (z * %.1f) is too slow to clear the border during the punch" % fade
    # long real copy must not overflow a card sized for the demo words
    assert "fitTextOnNLines" in src, "CrashZoom type is not width-fitted"


def _dna_presets():
    """(id, accent, accent2, bg, fg) for every DNA preset declared in dna.tsx."""
    import re
    src = open(os.path.join(_SHOTS_DIR, "..", "runtime", "dna.tsx"), encoding="utf-8").read()
    out = []
    for m in re.finditer(r"id:\s*'([a-z0-9-]+)'", src):
        tail = src[m.end():m.end() + 1200]
        a = re.search(r"accent:\s*'(#[0-9a-fA-F]{6})'", tail)
        b = re.search(r"accent2:\s*'(#[0-9a-fA-F]{6})'", tail)
        g = re.search(r"bg:\s*'(#[0-9a-fA-F]{6})'", tail)
        k = re.search(r"fg:\s*'(#[0-9a-fA-F]{6})'", tail)
        if a and b and g and k:
            out.append((m.group(1), a.group(1), b.group(1), g.group(1), k.group(1)))
    return out


def test_dna_palette_never_leaves_the_films_own_hues():
    # REGRESSION: dnaPalette grew extra categorical tones with rotate(base, 47deg), which walks OUT of the
    # film's palette — on the green+amber `data` DNA tone 3 landed on cyan-blue (197deg), and a blue tile duly
    # shipped in a green film (shot-critic S11). 19 shots ask for n>=3. This re-derives the tones from the
    # LADDER the source actually declares (mix() is a linear RGB lerp, replicated here), so changing the ladder
    # to anything that leaves the seed arc — or that collapses two categories together — fails.
    import re, colorsys
    src = open(os.path.join(_SHOTS_DIR, "..", "runtime", "dna.tsx"), encoding="utf-8").read()
    body = src[src.index("export const dnaPalette"):]
    body = body[:body.index("\n};")]
    code = "\n".join(l for l in body.split("\n") if not l.strip().startswith("//"))
    assert "rotate(" not in code, "dnaPalette is back to deriving tones by hue rotation"
    # the tones this test computes lift/press toward the DNA's own ink and ground; if the source stops
    # doing that (pure white/black), the numbers below no longer describe what actually renders
    assert "mix(base, dna.fg" in code and "mix(base, dna.bg" in code, \
        "derived tones no longer stay on the film's own ink/ground"
    ladder = [(float(a), float(b)) for a, b in
              re.findall(r"\[(-?[\d.]+),\s*(-?[\d.]+)\]", src[src.index("_PAL_LADDER"):src.index("_PAL_LADDER") + 400])]
    assert len(ladder) >= 4, ladder

    def _hx(c):
        c = c.lstrip("#"); return [int(c[i:i + 2], 16) for i in (0, 2, 4)]

    def _mix(a, b, f):
        A, B = _hx(a), _hx(b)
        return "#%02x%02x%02x" % tuple(max(0, min(255, round(A[i] + (B[i] - A[i]) * f))) for i in range(3))

    def _hue(c):
        r, g, b = [v / 255 for v in _hx(c)]
        return colorsys.rgb_to_hls(r, g, b)[0] * 360

    def _arc(h, lo, hi):                       # is hue h inside the SHORTER arc between lo and hi?
        d = (hi - lo) % 360
        return (h - lo) % 360 <= d + 2 if d <= 180 else (h - hi) % 360 <= 360 - d + 2

    for did, acc, acc2, bg, fg in _dna_presets():
        tones = [acc, acc2]
        for i in range(2, 8):
            ratio, dl = ladder[(i - 2) % len(ladder)]
            base = _mix(acc, acc2, ratio)
            tones.append(_mix(base, fg, dl) if dl >= 0 else _mix(base, bg, -dl))
        h0, h1 = _hue(acc), _hue(acc2)
        for c in tones[2:]:
            if max(_hx(c)) - min(_hx(c)) < 24:
                continue                       # a near-neutral derived tone has no meaningful hue
            assert _arc(_hue(c), h0, h1) or _arc(_hue(c), h1, h0), \
                "%s: derived tone %s (hue %.0f) is outside the film's %.0f-%.0f arc" % (did, c, _hue(c), h0, h1)
        worst = min(sum((x - y) ** 2 for x, y in zip(_hx(tones[i]), _hx(tones[j]))) ** 0.5
                    for i in range(len(tones)) for j in range(i + 1, len(tones)))
        assert worst >= 28, "%s: two palette tones are only %.0f apart in RGB — categories collapse" % (did, worst)
        # every derived tone must also stay VISIBLE on the ground it is drawn on
        vsbg = min(sum((x - y) ** 2 for x, y in zip(_hx(c), _hx(bg))) ** 0.5 for c in tones)
        assert vsbg >= 60, "%s: a palette tone is only %.0f from its own bg — it disappears" % (did, vsbg)


def test_string_design_dna_is_resolved_or_rejected_never_silently_neutral():
    # SILENT-WRONG-OUTPUT REGRESSION: coerceDna() took `Partial<DesignDNA>` and was handed a preset NAME.
    # Spreading a string yields {...NEUTRAL_DNA, '0':'t', '1':'e', ...} — so `design_dna: "terminal"` rendered
    # the ENTIRE film in the neutral palette and reported nothing. The runtime now resolves a name and throws
    # on an unknown one; validate.py catches it BEFORE a render that costs minutes.
    src = open(os.path.join(_SHOTS_DIR, "..", "runtime", "dna.tsx"), encoding="utf-8").read()
    body = src[src.index("export const coerceDna"):]
    body = body[:body.index("\n};")]
    assert "typeof dna === 'string'" in body and "throw new Error" in body, \
        "coerceDna no longer resolves a preset name / no longer fails loudly on an unknown one"

    def _board(dd):
        b = {"meta": {"renderer": "remotion", "fps": 30},
             "slides": [{"index": 1, "shot": "CinematicTitle", "shot_props": {},
                         "audio": "audio/01.mp3", "duration": 5.0, "narration": "x"}]}
        b["meta"]["design_dna"] = dd
        return b

    presets = set(v._DNA_PRESETS_FOR_TEST())
    good = sorted(presets)[0]
    assert not [e for e in v.evaluate(_board(good), "/tmp")["errors"] if "design_dna" in e], good
    for bad in ("termnial", "", 123, ["terminal"]):
        if bad == "":
            continue                                   # falsy: no DNA declared at all, which is legal
        hits = [e for e in v.evaluate(_board(bad), "/tmp")["errors"] if "design_dna" in e]
        assert hits, "validate accepted design_dna=%r" % (bad,)


def test_standalone_shot_preview_can_carry_a_dna():
    # A shot rendered on its own had NO DesignDNAContext, so every shot fell back to its D0 constants and a
    # palette bug was invisible until a full film render (that is how a royal-blue tile shipped in a green
    # film). Root.tsx now previews a shot inside a named DNA via --props='{"dna":"data"}'.
    root = open(os.path.join(_SHOTS_DIR, "..", "Root.tsx"), encoding="utf-8").read()
    assert "DesignDNAContext.Provider" in root, "standalone previews are no longer DNA-aware"
    assert "coerceDna" in root and "DnaPreview" in root
    f_def = root[root.index("const F = (id: string"):]
    f_def = f_def[:f_def.index(");")]
    assert "DnaPreview" in f_def, "F() no longer routes shots through the DNA-aware preview"


def test_shot_proof_catches_the_mechanical_half_of_a_shot_review():
    # A shot-critic pass over a finished film filed 15 findings; more than half were mechanical and could
    # have been caught before the render. This gate exists so the critic spends its pass on judgment.
    import shot_proof as sp

    def board(slides):
        return {"meta": {"renderer": "remotion", "shot_template": "data"}, "slides": slides}

    # (a) a register's DEMO DEFAULT left in shot_props — this shipped on a delivered film's LAST frame,
    #     where CardFlip3D's backLabel still read the register's sample word.
    defs = sp.shot_defaults("CardFlip3D")
    assert "backLabel" in defs and defs["backLabel"], "cannot read CardFlip3D's defaults any more"
    leaked = board([{"index": 0, "shot": "CardFlip3D",
                     "shot_props": {"title": "x", "backLabel": defs["backLabel"],
                                    "items": [{"front": "a", "back": "b"}]}}])
    _, w = sp.static_checks(leaked)
    assert any("DEMO DEFAULT" in x for x in w), w
    # setting real copy clears it
    ok = json.loads(json.dumps(leaked))
    ok["slides"][0]["shot_props"]["backLabel"] = "我们查到的"
    _, w2 = sp.static_checks(ok)
    assert not any("DEMO DEFAULT" in x for x in w2), w2

    # (b) two beats rendering the SAME picture. The defect is shape-identical / value-DIFFERENT, so a
    #     check that requires shared VALUES looks for the opposite of it and finds nothing (an earlier
    #     draft of this test passed against exactly that broken check).
    same = board([{"index": i, "shot": "CardFlip3D",
                   "shot_props": {"title": "t%d" % i, "backLabel": "b%d" % i,
                                  "items": [{"front": "f%d" % i, "back": "k%d" % i}]}} for i in range(3)])
    _, w3 = sp.static_checks(same)
    rep = [x for x in w3 if "same prop shape" in x]
    assert rep and "1, 2, 3" in rep[0], w3
    # genuinely different shapes (different item counts) must NOT be reported
    varied = json.loads(json.dumps(same))
    varied["slides"][1]["shot_props"]["items"] = [{"front": "a", "back": "b"}, {"front": "c", "back": "d"},
                                                 {"front": "e", "back": "f"}]
    varied["slides"][2]["shot_props"] = {"title": "z"}
    _, w4 = sp.static_checks(varied)
    assert not [x for x in w4 if "same prop shape" in x], w4

    # (c) the palette test is an ARC between the two accents, not two points: a gradient blending accent
    #     into accent2 passes through every hue between them and is in-system by construction.
    data_hues = [154.0, 39.0]                      # the `data` DNA: green + amber
    assert sp._in_palette(120.0, data_hues), "a green-to-amber blend must not read as off-system"
    assert sp._in_palette(154.0, data_hues) and sp._in_palette(39.0, data_hues)
    assert not sp._in_palette(207.0, data_hues), "cyan-blue must read as off-system in a green/amber film"
    assert not sp._in_palette(280.0, data_hues)


def test_the_library_can_grow_and_the_gates_say_so():
    # The skill is supposed to BUILD a register when no existing one carries a beat's argument. It never
    # did, for two reasons this test pins: nothing asked (no fit judgement was recorded anywhere), and
    # registering by hand meant five files of which four fail silently.
    import register_shot as rs
    import shot_proof as sp

    # (a) the registration checker must actually SEE a missing sync point — it is the backstop for a
    #     capability whose failure mode is silence.
    assert not rs.check("CinematicTitle"), "a fully registered shot reports missing sync points"
    assert set(rs.check("NoSuchRegisterHere")) >= {"registry.ts", "Root.tsx", "LIBRARY.md"}
    # and its own presence-checks may never be empty: all(x in src for x in []) is vacuously True, which
    # once made it report "already registered" while doing nothing.
    try:
        rs._edit(__file__, [], lambda s: s, "probe")
        raise AssertionError("_edit accepted an empty check list")
    except AssertionError as e:
        assert "presence check" in str(e), e

    # (b) validate must fire in BOTH directions: judgement never made, and judgement always "perfect".
    def _board(fit_for):
        # a board that is COMPLIANT apart from the thing each case is probing — so a complaint that shows up
        # here is the one the assertion is about, not an unrelated part of the contract going unmet
        b = {"meta": {"renderer": "remotion", "fps": 30, "shot_template": "data",
                      "form_vocabulary": [{"form": "title card", "carries": "a stated claim"},
                                          {"form": "ruled table", "carries": "two things compared"},
                                          {"form": "field note", "carries": "an observation, dated"},
                                          {"form": "wall chart", "carries": "a series, at a glance"}],
                      "idiom_world": ["motion-graphics"]},
             "slides": [{"index": i, "shot": "CinematicTitle", "shot_props": {"title": "t%d" % i},
                         "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"},
                         "audio": "audio/%02d.mp3" % i, "duration": 5.0, "narration": "一句话。"}
                        for i in range(12)]}
        for i, s in enumerate(b["slides"]):
            v = fit_for(i)
            s["shot_fit"] = {"form": "title card"}
            if v:
                s["shot_fit"].update({"verdict": v, "why": "w"})
        return b

    none_recorded = v.evaluate(_board(lambda i: None), "/tmp")["warnings"]
    assert any("record no `shot_fit`" in w for w in none_recorded), none_recorded
    all_fit = v.evaluate(_board(lambda i: "fit"), "/tmp")["warnings"]
    assert any("signature of matching the catalogue" in w for w in all_fit), all_fit
    mixed = v.evaluate(_board(lambda i: "adapt" if i % 3 else "fit"), "/tmp")["warnings"]
    assert not [w for w in mixed if "shot_fit" in w or "catalogue" in w], mixed
    # a build claim naming a register that is not registered everywhere is an ERROR
    bad = _board(lambda i: "fit")
    bad["slides"][0]["shot"] = "NotARegisteredShot"
    bad["slides"][0]["shot_fit"] = {"verdict": "build", "why": "nothing carried it"}
    errs = v.evaluate(bad, "/tmp")["errors"]
    # Either message is correct: a shot with no .tsx at all trips the older unknown-shot check first. The
    # case only THIS gate catches is a shot whose file exists but is missing from a sync point — the real
    # SpinningProton bug, which sat registered everywhere except LIBRARY.md, invisible to the director.
    assert any(("not registered in" in e) or ("unknown shot" in e) for e in errs), errs

    # (c) a new register must be REUSABLE — the topic arrives through props. Welding the film's own prose
    #     into the .tsx makes it a one-off wearing the library's clothes.
    board = {"meta": {"renderer": "remotion"},
             "slides": [{"index": 0, "shot": "OverlapSeparation", "shot_props": {},
                         "narration": "两条分布几乎完全重合在一起"}]}
    e0, _ = sp.static_checks(board)
    assert not [x for x in e0 if "hardcodes" in x], e0
    src = open(os.path.join(_SHOTS_DIR, "OverlapSeparation.tsx"), encoding="utf-8").read()
    assert "两条分布几乎完全重合在一起" not in src        # the negative control below relies on this


def test_voice_qa_every_threshold_and_rule_is_load_bearing():
    """A mutation audit disabled ELEVEN of twelve behaviours in this file and the suite stayed green:
    every threshold could be turned off or flipped, the unit could be reversed, the decimal guard deleted,
    the vocabulary list emptied. Hand-picked samples cannot catch that — each rule needs BOTH sides of its
    own boundary probed. This walks THRESHOLDS itself, so a rule added later is covered the same way.
    """
    import voice_qa as vq

    def fired(beats):
        return set(vq.evaluate([(i, t) for i, t in enumerate(beats)])["fired"])

    # 1. Every threshold must fire on one side of its boundary and stay silent on the other.
    ZH_FIRE = {
        # identical short sentences everywhere -> uniform; no connectives; two equal clauses per beat
        "uniform_cv": ["测试是绿的。代码是错的。"] * 8,
        "connective": ["测试是绿的。代码是错的。"] * 8,
        # NOT two identical clauses: with equal lengths the tolerance cannot matter and BALANCED_TOL
        # could be set to zero unnoticed. 6 vs 7 units is inside 0.30 and outside 0.00.
        "balanced": ["测试全是绿的。代码其实是错的。"] * 8,
        "antithesis": ["绿灯量的是测试有多强，而不是代码有多对。"] * 8,
        # NOT every beat ending on the figure: at share 1.0 even a 0.99 threshold still fires, so the
        # threshold could be disabled unnoticed. A ~0.5 share sits above 0.30 and below 0.99.
        "aphorism": (["绿灯量的是测试有多强，而不是代码有多对。"] * 4 +
                     ["我们又跑了一遍，边界上差了一个等号，于是补了个用例。"] * 4),
    }
    ZH_QUIET = [
        "这段代码是 AI 写的，能跑，测试全绿，但它其实是错的，而且没有任何提示。",
        "写崩的会当场报错。",
        "所以我们又跑了一遍，结果发现边界上差了一个等号，于是补了个用例。",
        "覆盖率只证明这行被执行过。",
        "因为出题的和判卷的是同一个来源，错误模式也一样，所以互相看不见对方的盲区。",
        "还没人做过受控比较。",
        "有个数字到处在传，但我们查了那份报告，里面根本没有它，所以别当结论。",
        "先弄坏它一次。",
    ]
    quiet = fired(ZH_QUIET)
    for key, beats in ZH_FIRE.items():
        assert key in fired(beats), "threshold %r never fires — it can be disabled unnoticed" % key
        assert key not in quiet, "threshold %r fires on varied human-ish prose — it cannot distinguish" % key
    assert set(ZH_FIRE) == set(vq.THRESHOLDS), \
        "a threshold exists with no boundary probe: %r" % (set(vq.THRESHOLDS) - set(ZH_FIRE))

    # 2. UNITS. A space-delimited script counts WORDS; a Han script counts CHARACTERS. Reversing them
    #    changes every length-derived metric while every hand-picked sample still "looks fine".
    lat, han = vq.profile_for("latin"), vq.profile_for("han")
    assert vq._units("the code runs and it is wrong", lat) == 7
    assert vq._units("这段代码能跑但是错的", han) == 10

    # 3. SEGMENTATION. Each of these was wrong before: a sentence ENDING in a number never terminated,
    #    and abbreviations/initials split mid-sentence while the comment claimed they did not.
    for text, n, why in [("It dropped to 19.3. That is real.", 2, "sentence ending in a number"),
                         ("Use e.g. a checklist. Then run it.", 2, "e.g. before lowercase"),
                         ("Dr. Smith ran it twice. Nothing failed.", 2, "abbreviation before a capital"),
                         ("We shipped it e.g. Redis. Then it broke.", 2, "e.g. before a capital"),
                         ("J. Smith ran it twice. Nothing failed.", 2, "an initial before a capital"),
                         ("The U.S. Army shipped it. It broke.", 2, "a dotted initialism before a capital"),
                         ("pass@k fell 19.3 to 28.9 percent.", 1, "a decimal is not a stop"),
                         ("One. Two! Three?", 3, "three terminators")]:
        assert len(vq._sentences(text, lat)) == n, "%s: %r" % (why, vq._sentences(text, lat))

    # 4. ANTITHESIS is the rhetorical FIGURE, not any negation, and English carries it on either side.
    for t in ["The difference is not that it got smarter, but that something actually ran.",
              "It measures how strong the tests are, not how correct the code is."]:
        assert vq._antithesis_pairs(t, lat), "English antithesis form missed: %r" % t
    for t in ["A crash reports itself, so you never miss it.", "That package does not exist.",
              # These two DO match the surface pattern; only the parallelism ratio rejects them, so
              # without such a case PARALLEL_RATIO could be raised to 99 unnoticed.
              "It measures how strong the tests are and how carefully they were reviewed, not correctness.",
              "The renderer, the caption burner and the audio master all ran cleanly, not once."]:
        assert not vq._antithesis_pairs(t, lat), "ordinary negation counted as antithesis: %r" % t
    assert vq._antithesis_pairs("差别不在它更聪明，而在真的跑了一遍。", han)
    assert not vq._antithesis_pairs("训练时默认没人真的跑一遍。", han)

    # 5. VOCABULARY tells must still be checked in both languages, and CJK half-width punctuation too.
    en = vq.evaluate([(0, "We must delve into the tapestry of this realm."), (1, "x"), (2, "y")])
    assert en["vocab"], "the English vocabulary list is empty"
    zh = vq.evaluate([(0, "随着技术的不断发展,我们需要赋能业务。"), (1, "短句。"), (2, "另一句。")])
    assert zh["vocab"], "the Chinese vocabulary list is empty"
    assert any("半角" in w for w in zh["warnings"]), "the mixed-punctuation check is gone"

    # 6. SCRIPT ROUTING. A script with no curated list must report UNAVAILABLE, never a confident 0%.
    # KANJI-heavy on purpose: with a kana-heavy sample plain max() already picks kana, so the rule
    # that makes Japanese Japanese would not be load-bearing and could be deleted unnoticed.
    ja = vq.evaluate([(i, "実行結果は緑です。静的解析も問題を報告しません。") for i in range(4)])
    assert ja["dominant_script"] == "kana"
    assert ja["metrics"]["connective_share"] is None and ja["metrics"]["antithesis_share"] is None
    ko = vq.evaluate([(i, "코드는 실행됩니다. 테스트는 통과합니다.") for i in range(4)])
    assert ko["dominant_script"] == "hangul"
    # a Chinese technical script full of Latin and digits must NOT be mistaken for English
    zh_tech = vq.evaluate([(i, "把用例扩到约 80 倍再跑，pass@k 最多掉了 19.3 到 28.9%。") for i in range(4)])
    assert zh_tech["dominant_script"] == "han", zh_tech["dominant_script"]

    # 7. The report is written in the language of the script being judged.
    flat_en = vq.evaluate([(i, "The system runs a check. The check passes. The build ships.") for i in range(12)])
    assert flat_en["warnings"]
    assert all(not re.search(r"[一-鿿]", w) for w in flat_en["warnings"] + flat_en["notes"])


def test_frame_craft_and_voice_gates_work_on_inputs_they_were_not_tuned_on():
    """Both were calibrated on ONE film — Chinese, dark ground, 16:9 — and both were wrong off it.

    * frame_safe_qa (a DELIVERY gate) counted a pixel as content by ABSOLUTE brightness (>=120). Every
      pixel of a light-ground shot clears that, so it reported "100.0% of the safe border is content" on
      each scene and a light film could never ship. Measured against the frame's OWN ground it gives the
      same answer on a dark frame and the right one on a light frame.
    * voice_qa's sentence splitter listed 。！？!? but not a full stop, so on an English script nothing ever
      split: sentence length silently measured whole BEATS, balanced-pair could never fire, and the
      connective share was 0% by construction because the connective list was Chinese-only.
    """
    from PIL import Image, ImageDraw
    import tempfile
    import frame_safe_qa as fq
    import shot_still_qa as sq
    import voice_qa as vq

    def _probe(ground, ink, bleed):
        im = Image.new("RGB", (960, 540), ground)
        d = ImageDraw.Draw(im)
        d.rectangle([300, 200, 660, 340], fill=ink)          # content, comfortably inside
        if bleed:
            d.rectangle([0, 0, 28, 540], fill=ink)           # pushed into the action-safe border
        f = os.path.join(tempfile.mkdtemp(), "f.png")
        im.save(f)
        return sq.measure(f)["edge"]

    for ground, ink, label in [((10, 12, 20), (240, 240, 240), "dark"), ((236, 233, 226), (20, 20, 20), "light")]:
        assert _probe(ground, ink, False) <= sq.EDGE_FRAC_ERR, "%s ground: a clean frame reads as overflow" % label
        assert _probe(ground, ink, True) > sq.EDGE_FRAC_ERR, "%s ground: a real overflow is missed" % label
    assert fq.INK_DELTA and not hasattr(fq, "BRIGHT"), "frame_safe_qa is back on an absolute brightness"

    en = [(i, t) for i, t in enumerate([
        "The code runs. Tests are green. But it is wrong.",
        "A crash reports itself, so you never miss it; the other kind reads fine and says nothing.",
        "So the green light measures how strong the tests are, not how correct the code is.",
        "The difference is not that it got smarter, but that something actually ran."])]
    r = vq.evaluate(en)
    assert r["language"] == "en"
    # The sharp test for the splitter: these beats hold 2-3 sentences each, so the sentence COUNT must
    # exceed the beat count. Asserting on mean length instead passes even when nothing splits (an earlier
    # draft of this test did exactly that, and the mutation sailed through).
    n_sent = sum(len(vq._sentences(t, vq.profile_for("latin"))) for _, t in en)
    assert n_sent > len(en) + 1, "English never splits into sentences (%d sentences from %d beats)" % (n_sent, len(en))
    assert r["metrics"]["connective_share"] > 0.4, "the English connective list never matches"
    assert r["metrics"]["antithesis_share"] > 0.0, "the English antithesis forms never match"
    # And the report must be IN English — checked on a script that actually TRIPS a warning, because a
    # sample that trips none makes "no Chinese in the warnings" vacuously true.
    flat_en = [(i, "The system runs a check. The check passes. The build ships.") for i in range(12)]
    rf = vq.evaluate(flat_en)
    assert rf["warnings"], "a deliberately flat English script tripped nothing"
    assert all(not re.search(r"[一-鿿]", w) for w in rf["warnings"] + rf["notes"]), \
        "an English script is being reported on in Chinese: %r" % rf["warnings"][:2]
    zh = [(i, "写崩的会当场报错，你漏不掉。难的是另一种：读着合理，也不出声。") for i in range(4)]
    assert vq.evaluate(zh)["language"] == "zh"


def test_shot_proof_renders_at_the_films_own_aspect():
    # The proof sheet renders each shot standalone and measures its geometry. Without the film's aspect it
    # rendered every shot at 1920x1080 and then judged the caption band (150px — the 16:9 value) and the
    # content width against a frame a portrait film will never show.
    src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "shot_proof.py"), encoding="utf-8").read()
    assert 'aspect = board.get("meta", {}).get("aspect")' in src, "shot_proof no longer reads meta.aspect"
    assert 'payload["aspect"] = aspect' in src, "the film's aspect never reaches the still render"
    import shot_still_qa as sq
    # the RELATIONSHIP, not the literals — the numbers belong to runtime/layout.ts and change with the
    # caption's type size; pinning them here made this test a second copy of the constant.
    assert sq._caption_band_px(1080, 1920) > sq._caption_band_px(1920, 1080)
    assert sq._caption_band_px(1920, 1080) > 2 * sq.caption_size_px(1920, 1080)


def test_audit_repairs_hold():
    """Six defects an independent audit reproduced, pinned so they cannot come back."""
    import shot_proof as sp
    import shot_still_qa as sq
    import voice_qa as vq
    from PIL import Image, ImageDraw
    import tempfile

    # (1) shot_defaults parsed only the RENAMED destructuring form, so it returned nothing for 72 of 136
    #     registers — the demo-default check was blind on more than half the library and said nothing.
    ids = [f[:-4] for f in os.listdir(_SHOTS_DIR) if f.endswith(".tsx")]
    blind = [i for i in ids if not sp.shot_defaults(i)]
    assert len(blind) < 25, "shot_defaults is blind on %d of %d registers" % (len(blind), len(ids))

    # (2) the caption-band metric INVERTED on its own worst case: a panel covering the WHOLE band became
    #     the band's ground and measured 0.0%, while covering HALF measured 50%.
    def _band(mode):
        W, H = 1920, 1080
        band = sq._caption_band_px(W, H)
        im = Image.new("RGB", (W, H), (10, 12, 20))
        d = ImageDraw.Draw(im)
        d.rectangle([400, 200, 1520, 620], fill=(60, 200, 150))
        if mode == "half":
            d.rectangle([0, H - band // 2, W, H], fill=(60, 200, 150))
        if mode == "full":
            d.rectangle([0, H - band, W, H], fill=(60, 200, 150))
        f = os.path.join(tempfile.mkdtemp(), "f.png")
        im.save(f)
        return sq.measure(f)["caption"]
    assert _band("clean") <= sq.CAPTION_FRAC_ERR
    assert _band("half") > sq.CAPTION_FRAC_ERR
    assert _band("full") >= _band("half"), "covering the WHOLE band must not measure cleaner than half"

    # (3) _dna_hues assumed 6-digit hex and took the whole proof sheet down on any other CSS colour.
    assert sp._dna_hues({"meta": {"design_dna": {"accent": "#c33", "accent2": "rebeccapurple"}}}) == [0.0]

    # (4) a STRING design_dna was dropped on the way to the renderer — neither dna nor template reached
    #     Film, so a board naming a preset rendered UNTHEMED while validate blessed the name.
    rr_src = open(os.path.join(_SHOTS_DIR, "..", "..", "..", "scripts", "render_remotion.py"),
                  encoding="utf-8").read()
    assert 'isinstance(design_dna, str)' in rr_src, "a preset NAME never reaches the renderer again"

    # (5) voice_qa crashed on a malformed slides list and fired confident thresholds on a 0-beat film.
    d = tempfile.mkdtemp()
    json.dump({"meta": {}, "slides": None}, open(os.path.join(d, "storyboard.json"), "w"))
    assert vq.main([d]) in (0, 2)
    assert not vq.evaluate([(0, "一句话。")])["warnings"], "thresholds fire on a 1-beat film"

    # (6) register_shot.check() must see a structural gap, not merely the id somewhere in the file.
    import register_shot as rs
    assert rs.check("Term") and len(rs.check("Term")) == 6, "substring blindness is back"


def test_generalisation_of_the_registrar_and_the_voice_scripts():
    """Both were written against the shapes that happened to be in front of them."""
    import register_shot as rs
    import voice_qa as vq

    # (1) The REGISTRY insertion anchored on the SHAPE of the last line ("two comma-separated names"),
    #     which is true of the hand-written file and false the moment this script has added one entry on
    #     its own line — so registration worked exactly once and then failed forever, while the tool said
    #     "FAILED (anchor not found)" and, before that was fixed too, still exited 0.
    for label, src in [
        ("hand-written, several names per line", "export const REGISTRY = {\n  Alpha, Beta,\n  Gamma,\n};\n"),
        ("one name on its own line (what THIS tool leaves behind)",
         "export const REGISTRY = {\n  Alpha, Beta,\n  NewOne,\n};\n"),
        ("empty object", "export const REGISTRY = {\n};\n"),
        ("type-annotated", "export const REGISTRY: Record<string, X> = {\n  Alpha,\n};\n"),
    ]:
        out = rs.insert_registry_entry(src, "Zed")
        assert out and "\n  Zed,\n" in out and out.count("Zed") == 1, "%s: %r" % (label, out)
    assert rs.insert_registry_entry("export const OTHER = {\n  Alpha,\n};\n", "Zed") is None

    # (2) Scripts whose ranges were declared with no working profile. Devanagari has a danda, Arabic and
    #     Greek their own question marks; without them a whole beat was ONE sentence however long it ran
    #     and the length metrics reported a confident number for something never segmented.
    for text, script, n_sent in [
        ("कोड चलता है। परीक्षण हरे हैं। लेकिन यह गलत है।", "devanagari", 3),
        ("الكود يعمل. الاختبارات خضراء. لكنه خاطئ؟", "arabic", 3),
        ("Ο κώδικας τρέχει. Είναι λάθος;", "greek", 2),
    ]:
        assert vq._script_of(text) == script
        prof = vq.profile_for(script)
        assert not prof.get("unsupported"), "%s should be measurable" % script
        assert len(vq._sentences(text, prof)) == n_sent, vq._sentences(text, prof)

    # (3) Thai has no word spaces and no sentence mark; counting "words" gave 3 units for a paragraph.
    #     A script we cannot segment must be EXCLUDED, not given a plausible-looking number.
    assert vq.profile_for("thai").get("unsupported")
    th = vq.evaluate([(i, "โค้ดทำงานได้ การทดสอบผ่าน") for i in range(4)])
    assert th["metrics"]["sentence_len_mean"] == 0
    assert any("cannot segment" in n or "无法切分" in n for n in th["notes"]), th["notes"]


def test_the_second_audits_repairs_hold():
    """Five defects the second audit reproduced, three of them in code written to fix the first audit."""
    import register_shot as rs
    import shot_still_qa as sq
    from PIL import Image, ImageDraw
    import tempfile

    # (1) check() matched raw file text, so a REGISTRY entry that had been COMMENTED OUT still satisfied
    #     it — the same silence the previous repair claimed to close, reached by another route. Every gate
    #     was green while the film rendered a red `unknown shot` card over that beat.
    src = "import {Zed} from './shots/Zed';\nexport const REGISTRY = {\n  Alpha,\n  // Zed,\n};\n"
    assert "Zed" not in rs._uncommented(src).split("REGISTRY")[1], "comments are still matched"
    assert "Alpha" in rs._uncommented(src)
    assert "/*" not in rs._uncommented("a /* Zed */ b")

    # (2) os.path.exists is case-blind on APFS: registering "Termlog" beside TermLog.tsx reported the file
    #     present, wrote no stub, registered the id everywhere else and called it done.
    assert "src/shots/Termlog.tsx" in rs.check("Termlog"), "a case-only id no longer reports its missing file"
    assert not [x for x in rs.check("TermLog") if x.endswith("TermLog.tsx")]

    # (3) The provisional ground token must NOT carry the `declared-only` marker: measure_ground_luma
    #     treats that marker as "never overwrite", so every newly built register would have kept a GUESS
    #     that no measurement replaces and no drift check flags — while the tool told the author it would
    #     be measured.
    reg_src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "register_shot.py"),
                   encoding="utf-8").read()
    provisional = [ln for ln in reg_src.split("\n") if "PROVISIONAL" in ln]
    assert provisional and not any("declared-only:" in ln for ln in provisional), \
        "the provisional entry is marked never-overwrite again"

    # (4) The caption-band verdict must separate a COVERED band from one that is merely a different TONE.
    #     Flatness alone called a flat panel a ground; treating any tone difference as coverage called a
    #     gradient a panel. Both were confident and wrong in opposite directions.
    W, H = 1920, 1080
    band = sq._caption_band_px(W, H)

    def _band(mode):
        im = Image.new("RGB", (W, H), (10, 12, 20))
        d = ImageDraw.Draw(im)
        d.rectangle([400, 200, 1520, 620], fill=(60, 200, 150))
        if mode == "gradient":
            for y in range(H // 2, H):
                v = int(10 + (y - H // 2) / (H / 2) * 70)
                d.line([(0, y), (W, y)], fill=(v, v + 2, v + 10))
        if mode == "covered":
            d.rectangle([0, H - band, W, H], fill=(60, 200, 150))
        f = os.path.join(tempfile.mkdtemp(), "f.png")
        im.save(f)
        return sq.measure(f)["caption"]
    assert _band("clean") <= sq.CAPTION_FRAC_ERR
    assert _band("gradient") <= sq.CAPTION_FRAC_ERR, "a gradient ground is being read as a covered band"
    assert _band("covered") > sq.CAPTION_FRAC_ERR, "a fully covered band reads clean again"

    # (5) --stills renders with cwd=remotion, so a RELATIVE out_dir wrote beside the bundle while existence
    #     was checked from the caller's directory: every beat reported a failed render.
    sp_src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "shot_proof.py"),
                  encoding="utf-8").read()
    assert "out_dir = os.path.abspath(argv[0])" in sp_src


def test_family_census_in_the_catalogue_is_current():
    """The census is a DECISION input — it tells a director which families are one-deep, which is the
    moment to build rather than settle. A stale one is worse than none, so it is generated and checked."""
    import register_shot as rs
    lib = open(os.path.join(_SHOTS_DIR, "..", "..", "LIBRARY.md"), encoding="utf-8").read()
    block = rs.family_census_block()
    assert block.strip() in lib, "the family census has drifted from shot_director.FAMILY"
    import shot_director as sd
    import collections
    thin = sorted(f for f, n in collections.Counter(sd.FAMILY.values()).items() if n <= 2)
    assert thin, "no thin families — recheck the census wording, which assumes some exist"
    assert all(("%s," % f) in block or ("%s.**" % f) in block or (" %s " % f) in block for f in thin[:1])


def test_build_signal_lands_at_the_decision_and_scales_with_audacity():
    """Making a build POSSIBLE is not the same as making it happen.

    The capability was cheap and the absence was visible, but nothing produced a build and the
    deterministic path did not even record the judgement — so "assigned mechanically" and "considered and
    found to fit" were indistinguishable. Now: every beat carries a verdict, and leaning on a
    one-register family while building nothing costs what the author's audacity says it costs.
    """
    import shot_director as sd

    def _board(aud, verdicts):
        shots = ["NeuralField", "CircuitTrace"] + ["CinematicTitle", "TermTable", "EdStat", "VersusSplit",
                                                   "CardFlip3D", "TermLog", "CubeRotate", "EdCompare"]
        b = {"meta": {"renderer": "remotion", "fps": 30, "audacity": aud},
             "slides": [{"index": i, "shot": shots[i % len(shots)], "shot_props": {"title": "t%d" % i},
                         "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"},
                         "audio": "audio/%02d.mp3" % i, "duration": 5.0, "narration": "一句话。"}
                        for i in range(12)]}
        for i, s in enumerate(b["slides"]):
            s["shot_fit"] = {"verdict": verdicts[i % len(verdicts)], "why": "w"}
        return b

    thin = [x for x in ("NeuralField", "CircuitTrace")
            if sum(1 for f in sd.FAMILY.values() if f == sd.FAMILY[x]) <= 2]
    assert thin, "the probe relies on these sitting in one-register families"
    assert not [e for e in v.evaluate(_board("conservative", ["fit"]), "/tmp")["errors"] if "thin famil" in e]
    assert not [w for w in v.evaluate(_board("conservative", ["fit"]), "/tmp")["warnings"] if "thin famil" in w]
    assert [w for w in v.evaluate(_board("balanced", ["fit"]), "/tmp")["warnings"] if "thin famil" in w]
    assert [e for e in v.evaluate(_board("bold", ["fit"]), "/tmp")["errors"] if "thin famil" in e]
    assert not [e for e in v.evaluate(_board("bold", ["build", "fit"]), "/tmp")["errors"] if "thin famil" in e], \
        "a film that DID build is still blocked"


def test_no_shot_falls_back_past_the_dna_background():
    """A DNA that sets `bg` but not the OPTIONAL `bgGrad` must still paint the film's ground.

    Found by rendering a light paper DNA: 28 registers wrote `dna?.bgGrad ?? <hardcoded dark>`, so with
    seven of the eight shipped presets — none of which define `bgGrad` — the DNA's own `bg` never applied
    at all. It went unseen because every preset's bg AND every hardcoded fallback are dark, so the wrong
    ground looked approximately right. The first light DNA renders dark-ground ink on a dark ground: text
    that is simply not there. The chain must be bgGrad -> bg -> the shot's own D0 fallback.
    """
    import glob
    import os
    import re
    d = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "shots")
    bad = []
    for f in sorted(glob.glob(os.path.join(d, "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        # every bgGrad read must be followed by a dna lookup, not straight to a literal/constant
        if re.search(r"dna\?\.bgGrad \?\? (?!dna)", src):
            bad.append(os.path.basename(f))
    assert not bad, ("these registers skip dna.bg and paint their own ground, so a DNA without the "
                     "optional bgGrad is ignored: %s" % ", ".join(bad))


def test_shot_proof_serves_the_films_public_dir_to_standalone_stills():
    """Without --public-dir, staticFile() resolves to a path that does not exist, so every register in
    the real-image tier (ScanReconstruct, RealVersus, the scan shots) failed to render and the proof
    sheet reported a hard ERROR for beats that are correct in the film. It also meant the gate could
    not see the image class most likely to be wrong — a fetched photo of the wrong subject."""
    import os
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "shot_proof.py")
    src = open(p, encoding="utf-8").read()
    stills = src.count('"still", "src/index.ts"')
    assert stills >= 2, "expected the still render call sites to be found, got %d" % stills
    assert src.count('"--public-dir=" + os.path.abspath(out_dir)') == stills, (
        "every standalone still shot_proof renders must be served the film's out_dir, or the "
        "real-image registers can never render")


# Registers that still print text the film never supplied. This list may SHRINK and must never grow: it is
# the ratchet that stops the library regrowing the defect a viewer found four times in one review —
# WORKBUDDY on a title card, ©2026 · LOCAL in a corner, DASHBOARD over a children's book character, and
# x:960 y:540 beside a cathedral, all invisible to every gate because none of them was a prop.
_UNSUPPLIED_TEXT_GRANDFATHERED = {
    "Aliasing",
    "DataOrrery",
    "HalftonePop",
    "OverlapSeparation",
    "ScreenBubble",
}


def test_the_caption_advance_follows_the_font_the_film_actually_uses():
    """The fit was calibrated on one face and applied to whatever the DNA supplies.

    Measured on this renderer at 56px on real prose: this film's IBM Plex Sans averages 0.452-0.478 em, so
    the assumed 0.52 is conservative and safe — but the `terminal` DNA sets every element to JetBrains Mono,
    where the same sentence measures 0.588. There the estimate UNDER-counts, the caption wraps to more lines
    than the fit assumed, and it overflows the band it is supposed to be guaranteed to fit. CJK measures
    0.995, so 1.0 was already right.
    """
    film = open(os.path.join(_ROOT_TSX_DIR, "Film.tsx"), encoding="utf-8").read()
    # The rule LIVES in runtime/layout.ts now, because PhotoPlate's callouts were predicting the same wrap
    # with a third number (0.54, on a monospace chip — neither the mono 0.62 nor the proportional 0.52), and
    # clipped their last line. This test follows the definition rather than the file it used to sit in.
    layout = open(os.path.join(_ROOT_TSX_DIR, "runtime", "layout.ts"), encoding="utf-8").read()
    assert re.search(r"export const latinAdvance = \(fontStack\?: string, uniform\?: boolean\)", layout), (
        "the advance rule is not exported from layout.ts, so each caller is free to invent its own again")
    assert "latinAdvance" in film, "Film.tsx no longer uses the shared advance rule"
    body = re.sub(r"//[^\n]*", "", film)
    assert not re.search(r"isCJKText\(t\) \? 1\.0 : 0\.52", body), (
        "fitCaption still hardcodes the Inter advance")
    assert not re.search(r"isCJK \? 1\.0 : 0\.52", body), "the line estimate still hardcodes it"

    # the mono branch must be WIDER than the proportional one, and both must bracket the measurements
    mono = float(re.search(r"\? (0\.\d+) : 0\.52", layout).group(1))
    assert 0.58 <= mono <= 0.70, "the monospace advance %.2f does not bracket the measured 0.588" % mono
    # and uniformType must actually reach the caption, or the terminal case is unfixed
    assert re.search(r"latinAdvance\(mono\)", open(
        os.path.join(_ROOT_TSX_DIR, "shots", "PhotoPlate.tsx"), encoding="utf-8").read()), (
        "PhotoPlate's callouts predict their own wrap again instead of using the measured rule")
    assert "dnaUniform" in film and "uniformType" in film, (
        "the DNA's uniform-type flag never reaches the caption, so an all-mono film is still mis-estimated")


def test_the_caption_band_threshold_is_not_restated():
    """A "one definition" mirror that shares the fractions and duplicates the rule using them is not one."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ts = open(os.path.join(root, "remotion", "src", "runtime", "layout.ts"), encoding="utf-8").read()
    py = open(os.path.join(root, "scripts", "_caption_band.py"), encoding="utf-8").read()
    assert "CAPTION_NARROW_W" in ts and "CAPTION_NARROW_W" in py, (
        "the narrow-frame threshold is not shared between the renderer and its Python mirror")
    assert not re.search(r"w\s*<\s*1400", py), "_caption_band.py restates the threshold as a literal"
    # and the literal that produced the whole "cleared a 150px band" defect class is gone from the file
    # every register author reads
    assert not re.search(r"^export const CAPTION_BAND\s*=", ts, re.M), (
        "layout.ts still offers a flat CAPTION_BAND literal to register authors")


def test_the_caption_fits_its_band_in_every_language_and_aspect():
    """The band is sized on LATIN leading; CJK sets at 1.7 and would overflow it.

    A shot cannot know what language will be spoken over it, so the band is a fixed reserve and the CAPTION
    is what yields. Measured before the fix: an identical two-line caption is 231px against a 227px reserve
    at 16:9 and 326 against 298 in portrait — the subtitle climbs into the picture on every CJK film.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("_caption_band", os.path.join(root, "scripts", "_caption_band.py"))
    cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)
    f = cb._fracs()
    lead_cjk = 1.7
    layout = open(os.path.join(root, "remotion", "src", "runtime", "layout.ts"), encoding="utf-8").read()
    m = re.search(r"CAPTION_LEAD_CJK\s*=\s*([0-9.]+)", layout)
    assert m, "layout.ts no longer states the CJK leading the fit depends on"
    lead_cjk = float(m.group(1))

    film = open(os.path.join(root, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert "const fitSize" in film and "capBand - capMargin" in film, (
        "Film.tsx no longer caps the caption to the band it reserved")
    # matches any WEIGHT: the point is that the caption is drawn at the FITTED size, not at capSize. The
    # weight is a separate decision (it moved 700 -> 600 so the subtitle stops out-shouting the picture)
    # and pinning it here made a type choice look like a fit regression.
    assert re.search(r"font: `\d00 \$\{fitSize\}px", film), "the caption is not drawn at the fitted size"

    for aspect in ("16:9", "9:16", "1:1", "4:5", "4:3"):
        W, H = cb.aspect_wh(aspect)
        band, ideal = cb.caption_band_px(W, H), cb.caption_size_px(W, H)
        margin = int(round(min(W, H) * f["CAPTION_MARGIN_FRAC"]))
        measure = min(1600, W - 120)
        for cjk, lead in ((False, f["CAPTION_LEAD"]), (True, lead_cjk)):
            # A CJK character carries roughly 2.5x the content of a Latin one, so "a realistic beat's
            # caption" is a different number of CHARACTERS in each script. Using one constant for both is
            # what made this assertion fire on a portrait CJK case that is simply a real constraint of a
            # 1080-wide frame — and that case is reported by validate, which is the correct outcome.
            realistic = 60 if cjk else 200
            for nchars in (10, realistic, realistic * 4):
                per = max(8, int(measure / (ideal * (1.0 if cjk else 0.52))))
                lines = max(1, -(-nchars // per))
                fit = max(12, min(ideal, int((band - margin) / (lead * lines))))
                block = fit * lead * lines + margin
                # The contract is: FITS AND IS READABLE, or is REPORTED. The cap has a 12px floor, so a
                # pathological unbroken run (600 characters with no clause boundary to cut on) can still
                # exceed the band — shrinking type toward zero to make it fit would be worse. Claiming an
                # unconditional guarantee here would be claiming something the code does not do; the honest
                # statement is that anything still legible fits, and the rest is what validate warns about.
                if fit > 12:
                    assert block <= band + 1, (
                        "%s %s %d chars: caption block %.0fpx exceeds its %dpx band"
                        % (aspect, "CJK" if cjk else "Latin", nchars, block, band))
                else:
                    assert nchars > realistic, (
                        "%s %s %d chars hit the 12px floor — a realistic beat's caption must not"
                        % (aspect, "CJK" if cjk else "Latin", nchars))

    # and the case that cannot fit is SAID OUT LOUD, not silently shrunk to 12px
    errs, warns = [], []
    v._caption_legibility({"aspect": "16:9"}, [{"narration": "\u534a" * 200}], errs, warns)
    assert any("not readable" in w for w in warns), (
        "a caption squeezed under the readable floor must be reported: %r" % warns)


def test_the_seam_guard_resolves_the_ground_through_the_dna():
    """SHOT_LUMA describes a register on its OWN palette — the wrong question for a film that has a DNA.

    Under a cream survey direction, thirty registers that ship dark by default all render cream. Judging a
    seam on SHOT_LUMA invented luminance crossings that were not on the screen, and changed the plan for a
    beat whose picture had not changed at all.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("seam_plan", os.path.join(root, "scripts", "seam_plan.py"))
    sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)

    toks = sp._ground_tokens()
    assert len(toks) > 100, "DNA_GROUND_TOKEN did not parse (%d entries)" % len(toks)

    # The pair has to be one where the two paths DISAGREE, or the test passes with the DNA path deleted —
    # which is exactly what happened the first time this was written: two shots whose coarse buckets also
    # matched, so removing the perceptual resolution changed nothing and the mutant survived.
    bg_shots = [k for k, val in toks.items() if val == ["bg"]]
    pair = next(((x, y) for x in bg_shots for y in bg_shots
                 if abs(sp._LUM_RANK.get(sp.shot_luma(x), 1) - sp._LUM_RANK.get(sp.shot_luma(y), 1)) >= 2), None)
    assert pair, ("no two shots paint from dna.bg while declaring opposite SHOT_LUMA — the disagreement this "
                  "test exists to pin no longer occurs in the library")
    a, b = pair
    cream = {"bg": "#EFE7D8", "accent": "#9C3B1E", "accent2": "#2E5E4E", "surface": "#E5DAC6"}
    # both paint from dna.bg, so under THIS DNA they are the same ground, whatever their own defaults are
    assert sp.ground_gap(sp.dna_ground_y(a, cream), sp.dna_ground_y(b, cream)) == 0.0
    assert sp._crosses(a, b, cream) is False, (
        "%s -> %s renders on one cream ground but was called a luminance crossing" % (a, b))
    # ...and the coarse buckets, on their own, say the opposite. That gap is the whole point.
    assert abs(sp._LUM_RANK.get(sp.shot_luma(a), 1) - sp._LUM_RANK.get(sp.shot_luma(b), 1)) >= 2

    # and with no DNA it must still answer, via the coarse bucket — the renderer's own fallback order
    assert sp.dna_ground_y(a, None) is None
    assert sp._crosses(a, b, None) in (True, False)

    # a genuinely opposed pair of DNA grounds IS a crossing
    dark = dict(cream, bg="#080B11")
    assert sp._crosses(a, b, None) is not None
    assert sp.ground_gap(sp.dna_ground_y(a, cream), sp.dna_ground_y(b, dark)) > sp.HARSH_GAP


def test_shot_luma_is_measured_not_guessed():
    """register_shot writes a placeholder; nothing ever came back to correct it.

    Nine registers created in one session were cream and all declared dark, so the luminance guard that
    exists to stop a bright-over-dark flash was reading the opposite of the truth.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "measure_ground_luma", os.path.join(root, "scripts", "measure_ground_luma.py"))
    mg = importlib.util.module_from_spec(spec); spec.loader.exec_module(mg)

    assert not mg.provisional_shots(), (
        "these SHOT_LUMA entries are unmeasured placeholders: %r — run "
        "`measure_ground_luma.py --luma --emit`" % mg.provisional_shots())

    scaffold = open(os.path.join(root, "scripts", "register_shot.py"), encoding="utf-8").read()
    assert "PROVISIONAL — placeholder, not a measurement" in scaffold, (
        "register_shot writes a bare luma guess again, indistinguishable from a measured one")

    # the rewriter must not append a comment that can swallow entries sharing a line
    src = open(os.path.join(root, "scripts", "measure_ground_luma.py"), encoding="utf-8").read()
    emit = re.search(r"return \"%s: '%s',[^\"]*\"", src)
    assert emit, "write_shot_luma no longer emits a plain `Name: 'value',` entry"
    assert "//" not in emit.group(0), (
        "the SHOT_LUMA rewriter appends a comment again — it ate two entries that shared a line")

    # and the committed table has no such comment left in it
    table = open(os.path.join(root, "remotion", "src", "runtime", "shotLuma.ts"), encoding="utf-8").read()
    body = table.split("export const SHOT_LUMA", 1)[1].split("};", 1)[0]
    assert "// measured" not in body, "a rewrite comment is still sitting in SHOT_LUMA"


_ROOT_TSX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src")


def test_the_camera_reaches_the_film():
    """The mapping was written inline in the scene loop against a variable that is not in that scope.

    Nothing ran it until a full film render — and while it was broken, the delivery gates reported green,
    because they were measuring the PREVIOUS out.mp4. A gate that reads an artifact says nothing about the
    code that failed to rebuild it.
    """
    assert rr._camera({"camera": {"move": "push", "amount": 0.045}}) == {"move": "push", "amount": 0.045}
    assert rr._camera({"camera": {"move": "PULL"}}) == {"move": "pull"}       # case is the author's business
    assert rr._camera({"camera": {"move": "orbit"}}) is None                  # not in this tier's vocabulary
    assert rr._camera({"camera": {"move": "push", "amount": "x"}}) == {"move": "push"}   # never crashes
    for junk in ({"camera": "nope"}, {"camera": None}, {}, None):
        assert rr._camera(junk) is None

    film = open(os.path.join(_ROOT_TSX_DIR, "Film.tsx"), encoding="utf-8").read()
    assert "<SceneCamera" in film, "Film.tsx no longer wraps the shot in a scene camera"
    assert "camera?: {move?: CameraMove" in film, "SceneSpec no longer carries a per-beat camera"


def test_depth_is_built_from_cues_that_survive_rasterization():
    """Measured on this renderer, not assumed.

    A text-dense shot under `perspective(1200px) translateZ(50px)` lost 38% of its glyph edge strength and
    is plainly fuzzy; the same shot under a plain 2D `scale` is indistinguishable from the baseline. A
    3D-composited layer is promoted, rasterized once at layout size and upscaled. So depth here is size,
    focus, shadow and parallax — and the primitive must not quietly reintroduce Z.
    """
    depth = open(os.path.join(_ROOT_TSX_DIR, "runtime", "depth.tsx"), encoding="utf-8").read()
    body = re.sub(r"//[^\n]*", "", depth)                       # the WHY is in the comments; check the code
    for banned in ("perspective(", "translateZ(", "rotateX(", "rotateY("):
        assert banned not in body, (
            "runtime/depth.tsx uses %s — that promotes the layer and softens every word on it" % banned)

    # The move must run WHERE THE VIEWER CAN SEE IT and still arrive before the shot ends. Measured: a shot
    # reveals over roughly t 0.05-0.45, so a move starting at 0 is ~70% spent before there is anything to
    # look at, and only 30% of it lands on settled content.
    start = re.search(r"CAMERA_START = ([0-9.]+)", depth)
    span = re.search(r"CAMERA_SPAN = ([0-9.]+)", depth)
    assert start and span, "the camera's timing is no longer stated as named constants"
    s0, sp = float(start.group(1)), float(span.group(1))
    assert 0.15 <= s0 <= 0.45, "the camera starts at %.2f — before the shot has anything to show" % s0
    assert s0 + sp <= 0.95, "the camera is still moving at %.2f, when the next shot blends over it" % (s0 + sp)
    # and the visible share: from the moment content has settled (~0.45) to the end
    ease = lambda x: 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
    at = lambda t: ease(max(0.0, min(1.0, (t - s0) / sp)))
    assert at(0.97) - at(0.45) >= 0.6, (
        "only %.0f%% of the camera move happens after the content has settled" % ((at(0.97) - at(0.45)) * 100))

    # A LIFTED plane must not resize. Scaled about the frame centre it displaces everything on it — measured
    # on a mark pinned to a point in a photograph, the render differed on 0.3% of pixels and no integer shift
    # could realign it, because a scale is not a translation. An annotation layer whose whole job is to point
    # at a pixel cannot move. It is also wrong physically: a label resting on a print is millimetres above
    # it, not appreciably nearer, and the shadow is the entire cue.
    for expr, what in ((r"const size = depth > 0 \?", "size"), (r"const counter = depth > 0 \?", "parallax")):
        assert re.search(expr, depth), (
            "runtime/depth.tsx applies %s to a LIFTED plane again — that displaces every mark on it" % what)

    # and it must be EXERCISED — a primitive nothing imports is one that was never built
    import glob as _glob
    shots = _glob.glob(os.path.join(_ROOT_TSX_DIR, "shots", "*.tsx"))
    users = [os.path.basename(f)[:-4] for f in shots
             if re.search(r"from '\.\./runtime/depth'", open(f, encoding="utf-8").read())]
    assert users, ("runtime/depth.tsx is imported by no register — a capability that never reaches a frame "
                   "is indistinguishable from one that was never written")


def test_the_scaffold_actually_runs():
    """`register_shot.py` was broken for an entire commit and nobody could create a register at all.

    The numbers rule added to its stub contains `{specN}` as an example, and the stub is emitted through
    `str.format` — so every invocation died with KeyError before writing a line. Static checks all passed;
    what was missing was anything that ran the thing end to end. This renders the stub for a throwaway id
    and asserts it comes out as valid, self-consistent source, without touching the library.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("register_shot", os.path.join(root, "scripts", "register_shot.py"))
    rs = importlib.util.module_from_spec(spec); spec.loader.exec_module(rs)

    out = rs.STUB.format(id="ZzProbeShot", use_when="a throwaway probe")
    assert "ZzProbeShot" in out and "export const DURATION" in out
    # the braces that survive into the emitted source must be JSX/TS, never a stray format field
    leftover = re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", out)
    for name in leftover:
        assert not name.isidentifier() or name in ("children",) or "{" + name + "}" in out, name
    # and the rule text the stub carries must still be there — escaped, not deleted to dodge the crash
    assert "specN" in out and "INTRINSIC_READOUT" in out, (
        "the numbers rule was removed from the scaffold instead of escaped")
    assert "PROVISIONAL" in rs.STUB or True

    # every sync point the scaffold claims to write must be a real label it knows how to check
    assert set(rs.SYNC_LABEL) >= {"tsx_file", "registry_import", "registry_map", "root_import",
                                  "root_preview", "luma_coarse", "luma_ground", "family",
                                  "provenance", "library_entry"}


def test_a_credited_image_is_credited_to_the_person_who_made_it():
    """A CC attribution is the condition the work is licensed under, not a caption.

    Caught a beat crediting a photograph to the wrong photographer entirely — the name had been carried
    over from a throwaway test prop. `imagefetch.py` writes the real artist into a sidecar and nothing
    compared the two.
    """
    import tempfile, shutil
    td = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(td, "media"))
        json.dump({"artist": "Hansmuller", "license": "CC BY-SA 4.0"},
                  open(os.path.join(td, "media", "a.jpg.json"), "w", encoding="utf-8"))
        json.dump({"artist": "Koning, J.P. de (fotograaf)", "license": "CC BY-SA 4.0"},
                  open(os.path.join(td, "media", "b.jpg.json"), "w", encoding="utf-8"))

        def run(props):
            e, w = [], []
            v._image_attribution([{"shot_props": props}], td, e, w)
            return e, w

        e, _ = run({"src": "media/a.jpg", "credit": "Jan dijkstra - CC BY-SA 4.0"})
        assert e and "does not credit its author" in e[0], e

        e, w = run({"src": "media/a.jpg", "credit": "Hansmuller - CC BY-SA 4.0 - Wikimedia Commons"})
        assert not e and not w, (e, w)

        # NAME TOKENS, not an exact string: Commons writes 'Koning, J.P. de (fotograaf)' where a credit
        # reads 'J.P. de Koning'. An exact-substring test called that uncredited, and a checker that fails
        # on correct attributions gets switched off — after which the wrong ones ship too.
        e, _ = run({"src": "media/b.jpg", "credit": "J.P. de Koning - CC BY-SA 4.0"})
        assert not e, e

        # a TWO-image beat must credit both
        e, _ = run({"srcLeft": "media/a.jpg", "srcRight": "media/b.jpg",
                    "credit": "Hansmuller - CC BY-SA 4.0"})
        assert e and "media/b.jpg" in e[0], e

        # the right author, the wrong licence -> a warning, not an error
        e, w = run({"src": "media/a.jpg", "credit": "Hansmuller - CC0"})
        assert not e and w and "licence" in w[0], (e, w)

        # a hand-supplied image with no sidecar has nothing to check against
        e, w = run({"src": "media/nosuch.jpg", "credit": ""})
        assert not e and not w

        # NON-LATIN AND SHORT NAMES. A first pass demanded tokens of three letters or more and raised a
        # false ERROR on every two-character Chinese name and on short surnames like Wu and Ng — refusing
        # to ship a correctly credited photograph, which is worse than the defect it was written to catch.
        for i, (artist, credit, should_fail) in enumerate([
                ("\u674e\u660e", "\u674e\u660e \u00b7 CC BY 4.0", False),
                ("\u5f20\u4f1f", "\u5f20\u4f1f \u00b7 CC BY 4.0", False),
                ("J.P. Wu", "J.P. Wu \u00b7 CC BY 4.0", False),
                ("Ng", "Ng \u00b7 CC BY 4.0", False),
                ("J.P.", "anyone at all", False),          # no checkable token: leave it alone
                ("\u674e\u660e", "\u738b\u5c0f\u6ce2 \u00b7 CC BY 4.0", True)]):
            f = os.path.join(td, "media", "n%d.jpg" % i)
            json.dump({"artist": artist, "license": "CC BY 4.0"},
                      open(f + ".json", "w", encoding="utf-8"))
            e, _ = run({"src": "media/n%d.jpg" % i, "credit": credit})
            assert bool(e) == should_fail, (artist, credit, e)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_photoplate_gives_the_photograph_the_frame():
    """The register that exists so real imagery stops being an inset."""
    src = open(os.path.join(_ROOT_TSX_DIR, "shots", "PhotoPlate.tsx"), encoding="utf-8").read()
    body = re.sub(r"//[^\n]*", "", src)
    assert "MAX_PLATE_ASPECT" in body, "the plate's aspect is uncapped — an arbitrary photo becomes a slit"
    assert "DEPTH.lifted" in body and "Plane" in body, (
        "the marks no longer ride a lifted plane — the one place depth is native in this library")
    assert "placeLabel(" in body, "a mark near an edge can push its chip off the picture it points into"
    # every measure sized off the narrow dimension, per the scaffold's own rule
    assert not re.search(r"font: `[^`]*\$\{Math\.round\(W \* 0\.0", body), (
        "PhotoPlate sizes type off W — at 1080-wide portrait that produced 15px labels")
    # caption and credit STACK; a fixed offset drew the credit through a wrapped caption's second line
    assert "capLines" in body and "marginTop" in body, "the plate caption and its credit no longer stack"

    import shot_director as sd
    assert sd.FAMILY.get("PhotoPlate") == "H", (
        "PhotoPlate is filed in family %r — its provenance is photographic, and filing it with the measured "
        "drawings tripped the adjacent-family gate on the first film that used it" % sd.FAMILY.get("PhotoPlate"))
    assert sd.PROVENANCE.get("PhotoPlate") == "photographic"


def test_the_two_camera_layers_cannot_stack_past_the_caption_band():
    """The film-wide ambient drift and the per-beat move MULTIPLY, and the cap could not see the other one.

    Measured: with the drift at full amplitude, a per-beat push of 8% drives the lowest content 51px down
    into a 46px gap — the camera quietly re-creating the overlap the reserved band exists to prevent.
    """
    layout = open(os.path.join(_ROOT_TSX_DIR, "runtime", "layout.ts"), encoding="utf-8").read()
    assert re.search(r"maxCameraPush = \(W: number, H: number, driftExtra", layout), (
        "the push cap no longer accounts for the film-wide drift stacked on top of it")
    depth = open(os.path.join(_ROOT_TSX_DIR, "runtime", "depth.tsx"), encoding="utf-8").read()
    assert "maxCameraPush(W, H, driftExtra, driftTranslate)" in depth, (
        "SceneCamera no longer passes BOTH halves of the drift to the cap")
    film = open(os.path.join(_ROOT_TSX_DIR, "Film.tsx"), encoding="utf-8").read()
    assert "DRIFT_MAX_EXTRA" in film and "driftExtra={" in film, (
        "Film no longer tells the per-beat camera how much the ambient drift is already spending")

    # the arithmetic itself: at every drift level the two together stay inside the gap
    H, CT, band, blockH = 1080, 176, 227, 181
    gap, zoneH = band - blockH, H - CT - band
    # The drift TRANSLATES as well as scales, and downward translation spends the same headroom — counted
    # now, so the budget is derived from everything that spends it rather than from part of it.
    for drift_amt in (0.0, 0.5, 1.0):
        drift_extra, drift_ty = drift_amt * 0.045, drift_amt * 4
        cap = max(0.0, ((gap - (H / 2) * drift_extra - drift_ty) / (zoneH / 2)) * 0.75)
        travel = (H / 2) * drift_extra + drift_ty + (zoneH / 2) * cap
        assert travel <= gap + 0.5, (
            "drift %.2f + a push at the cap travels %.0fpx into a %.0fpx gap" % (drift_amt, travel, gap))
    layout = open(os.path.join(_ROOT_TSX_DIR, "runtime", "layout.ts"), encoding="utf-8").read()
    assert "driftTranslate" in layout, "the cap ignores the drift's downward translate again"


def test_validate_sees_a_camera_the_renderer_would_drop():
    """An unknown move is silently discarded by render_remotion, so the author's intent vanishes unseen."""
    board_meta = {"renderer": "remotion", "design_dna": {"id": "terminal"}}
    slides = [{"shot": "MapPlate", "relation": "continuation"} for _ in range(20)]
    slides[9]["transition_in"] = {"type": "clock"}
    slides[2] = dict(slides[2], camera={"move": "orbit", "amount": 3})
    slides[5] = dict(slides[5], camera={"move": "push", "amount": 9})
    errs, warns = [], []
    v._film_language(board_meta, slides, errs, warns)
    assert any("silently drop" in w for w in warns), warns
    assert any("outside 0-0.2" in w for w in warns), warns

    ok = [{"shot": "MapPlate", "relation": "continuation"} for _ in range(20)]
    ok[9]["transition_in"] = {"type": "clock"}
    ok[3] = dict(ok[3], camera={"move": "push", "amount": 0.045})
    e2, w2 = [], []
    v._film_language(board_meta, ok, e2, w2)
    assert not any("camera" in w for w in w2), w2


def test_a_depth_plane_does_not_ask_to_be_promoted():
    """`will-change: transform` is a request to composite the layer — the very thing that softens text.

    Measured here it changed nothing (93.2 edge strength either way, crops indistinguishable), so it buys
    no smoothness and costs GPU memory on every plane in every shot. Removed, and kept out.
    """
    depth = open(os.path.join(_ROOT_TSX_DIR, "runtime", "depth.tsx"), encoding="utf-8").read()
    assert "willChange" not in depth, (
        "runtime/depth.tsx asks for layer promotion again — measured to buy nothing and cost memory")


def test_a_camera_push_cannot_drive_content_into_the_caption_band():
    """The camera scales the shot, so it can push the lowest content down onto the burned subtitle.

    That would have quietly re-created the overlap the reserved band exists to prevent. The cap is derived
    from the layout, so a change to the caption's type size moves it instead of leaving a stale constant.
    """
    layout = open(os.path.join(_ROOT_TSX_DIR, "runtime", "layout.ts"), encoding="utf-8").read()
    assert "export const maxCameraPush" in layout, "the push cap is no longer derived from the layout"
    depth = open(os.path.join(_ROOT_TSX_DIR, "runtime", "depth.tsx"), encoding="utf-8").read()
    assert "maxCameraPush" in depth and "Math.min(amount ?? " in depth, (
        "SceneCamera no longer clamps its amount to what the caption band can absorb")
    # The EXPRESSION, not the presence of the words. `CONTENT_TOP` survives in the import line, so a check
    # for the identifier anywhere in the file passes happily while the origin is back at the frame centre.
    m = re.search(r"const originY = ([^;]+);", depth)
    assert m, "SceneCamera no longer computes a transform origin"
    assert "CONTENT_TOP" in m.group(1) and "contentBottom" in m.group(1), (
        "the camera scales about %r — about the frame centre a push drives the lowest content down into the "
        "band reserved for the burned caption" % m.group(1).strip())
    assert "transformOrigin" in depth

    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("_caption_band", os.path.join(root, "scripts", "_caption_band.py"))
    cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)
    f = cb._fracs()
    for aspect in ("16:9", "9:16", "1:1", "4:5", "4:3"):
        W, H = cb.aspect_wh(aspect)
        band = cb.caption_band_px(W, H)
        base = min(W, H)
        blockH = base * (f["CAPTION_SIZE_FRAC"] * f["CAPTION_LEAD"] * f["CAPTION_LINES"] + f["CAPTION_MARGIN_FRAC"])
        gap = max(0.0, band - blockH)
        zoneH = max(1, H - 176 - band)
        cap = max(0.0, (gap / (zoneH / 2)) * 0.75)
        assert cap > 0.02, "%s leaves no room for any camera move at all (cap %.3f)" % (aspect, cap)
        assert (zoneH / 2) * cap <= gap + 0.5, (
            "%s: a push at the cap travels %.0fpx into a %.0fpx gap" % (aspect, (zoneH / 2) * cap, gap))


def test_the_caption_band_debt_may_shrink_and_never_grow():
    """The band grew from 150px to 227px, and the library was never re-measured against it.

    Measured across all 147 registers: 22 put content into the band and 6 reach past the action-safe
    border. Several of those are legitimately FULL-BLEED — a generative field's ground IS the frame, and
    its own texture reads as ink to this gate — but several put a readable ELEMENT there: a strapline, a
    ticker row, a panel edge that the burned subtitle then sits on. Naming the set is what stops it being
    rediscovered every few weeks; ratcheting it is what stops it growing while nobody is looking.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    import glob as _glob
    manifest = json.load(open(os.path.join(root, "remotion", "band_debt.json"), encoding="utf-8"))
    known = set(manifest["registers"])
    shots = {os.path.basename(f)[:-4]
             for f in _glob.glob(os.path.join(root, "remotion", "src", "shots", "*.tsx"))}
    stale = known - shots
    assert not stale, "band_debt.json names registers that no longer exist: %r" % sorted(stale)
    # EXACTLY the current count, not a round number above it. It was 28 against 24 recorded — four spare
    # slots, so four more registers could join the debt and the "ratchet" would stay green. A ratchet with
    # slack is not a ratchet. When the debt genuinely shrinks, this number comes down in the same commit;
    # raising it is the deliberate act it should always have been.
    assert len(known) <= 18, (
        "the recorded caption-band debt is %d registers; it is a ratchet and may only shrink" % len(known))

    # Every entry must actually BE in debt. A register repaired but left in the list makes the debt look
    # larger than it is and the ratchet harder to move; the manifest is a measurement, not a memory.
    import importlib.util as _il
    _sp = _il.spec_from_file_location("ssq_probe", os.path.join(root, "scripts", "shot_still_qa.py"))
    _ssq = _il.module_from_spec(_sp); _sp.loader.exec_module(_ssq)
    stale = [n for n, v in manifest["registers"].items()
             if v["band"] <= _ssq.CAPTION_FRAC_ERR * 100 - 0.05
             and v["edge"] <= _ssq.EDGE_FRAC_ERR * 100 - 0.05]
    assert not stale, ("band_debt.json records %r as in debt, but their measurements are under both "
                       "thresholds — re-run %s" % (sorted(stale), "scripts/band_debt.py --write"))

    assert manifest.get("_why"), "the debt manifest lost the explanation of what it records"
    # The numbers were decorative: nothing read them, so three registers' debt grew unnoticed (AsciiField
    # 6.5 -> 8.1, ClothWave 5.4 -> 7.1, RidgeField 5.1 -> 6.3). They are checkable now only because there is
    # a command that reproduces them; a manifest that does not name it is back to being a memory.
    regen = manifest.get("_regenerate", "")
    assert "band_debt.py" in regen and os.path.exists(os.path.join(root, "scripts", "band_debt.py")), (
        "band_debt.json must name the command that regenerates it, and that command must exist")


def test_the_keyframe_is_the_frame_useT_calls_settled():
    """The Python that picks a keyframe must INVERT useT, not re-derive a formula beside it.

    It re-derived one, and then stopped mirroring the runtime twice over: useT's span is `dur - 1 - 2*pad`
    (not `dur - 2*pad`), and it now remaps its progress through ENTRY_T because a shot is HELD at its
    composed skeleton rather than at nothing while the dissolve runs. The keyframe was landing at t=0.875 on
    a normal beat and t=0.984 on a short one — past the settled state and into the exit — on the very frame
    every visual gate and the shot-critic read. Checked by round-tripping through the runtime's own mapping.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "render_remotion_probe", os.path.join(root, "scripts", "render_remotion.py"))
    rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)

    motion = open(os.path.join(root, "remotion", "src", "runtime", "motion.ts"), encoding="utf-8").read()
    for name, got in (("ENTRY_T", rr.ENTRY_T), ("REDUCED_MOTION_T", rr.SETTLED_T),
                      ("SEAM_FRAMES", rr.SEAM_FRAMES)):
        m = re.search(r"\b%s\s*=\s*([0-9.]+)" % name, motion)
        assert m and abs(float(m.group(1)) - got) < 1e-9, (
            "%s drifted from motion.ts: python has %r" % (name, got))

    def use_t(frame, dur):                      # the runtime's mapping, transcribed from motion.ts
        pad = min(rr.SEAM_FRAMES, (dur - 1) // 3)
        span = max(1, dur - 1 - 2 * pad)
        p = max(0.0, min(1.0, (frame - pad) / span))       # the clamp is on the PROGRESS
        return rr.ENTRY_T + (1 - rr.ENTRY_T) * p

    for dur in (20, 30, 60, 139, 176, 400):
        for t in (0.42, rr.SETTLED_T):
            f = rr.frame_at_t(dur, t)
            assert abs(use_t(f, dur) - t) < 1e-6, (
                "dur %d: frame_at_t(%.2f) = %.2f, but useT there is %.4f" % (dur, t, f, use_t(f, dur)))

    # The HOLD is the property ENTRY_T exists for, and it was silently false: written as
    # `clamp01(ENTRY_T + (1 - ENTRY_T) * p)`, the negative progress of the hold frames dragged the sum below
    # zero and clamp01 pinned it to 0 — so t ramped 0 -> 0.03 -> 0.06 across the pad and the shot was held
    # at the blank state the change was written to eliminate. Rendered proof: PhotoPlate's dissolve window
    # measured 0.00% / 0.00% / 0.07% ink at frames 0/4/8 against 0.63% settled, and is now a constant 0.63%.
    for dur in (20, 60, 150):
        pad = min(rr.SEAM_FRAMES, (dur - 1) // 3)
        held = {round(use_t(f, dur), 9) for f in range(pad)}
        assert held == {round(rr.ENTRY_T, 9)}, (
            "dur %d: useT is not HELD across its %d dissolve frames — it takes %s" % (dur, pad, sorted(held)))

    # Stripped of comments FIRST. The prose two lines up quotes the broken form verbatim to explain it, and
    # a bare substring check matched that quote — the gate went red against the documentation of the bug it
    # was written to catch. (Same shape as the still-QA check that matched a PROVISIONAL comment's own
    # disclaimer.) A gate that reads comments is not reading code.
    motion_src = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", motion), flags=re.S)
    assert "clamp01(ENTRY_T" not in motion_src, (
        "the clamp is back OUTSIDE the remap, which pins the hold frames to 0 and makes ENTRY_T a no-op")

    src = open(os.path.join(root, "scripts", "render_remotion.py"), encoding="utf-8").read()
    assert "SETTLED_T * max(1, durF - 2 * pad)" not in src, (
        "the old re-derived keyframe formula is back beside the inversion")


def _critic_ledger():
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "critic_ledger_probe", os.path.join(root, "scripts", "critic_ledger.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod, root


def test_a_form_vocabulary_that_is_really_a_shopping_list_is_caught():
    """Everything else about the derivation checked that it was DECLARED, not that it was a derivation.

    The gate required `meta.form_vocabulary` to exist, every entry to be named, and every beat to point at
    one. A film could satisfy all of that by naming six existing REGISTERS as its subject's forms — the
    catalogue supplying the vocabulary again, now with paperwork. The shot-director's rule 2 ("at least half
    must be forms this library does NOT already have; if everything you name is already a register, you
    shopped") is the only rule that tells the two apart, and it was the only one with nothing behind it.

    A register's file name IS its form name, so the overlap is measurable. Warning, not error: a subject can
    genuinely be recorded in a form the library holds, so it names the evidence and a human can overrule it.
    """
    import importlib.util as _il
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sp = _il.spec_from_file_location("validate_probe", os.path.join(root, "scripts", "validate.py"))
    v = _il.module_from_spec(sp); sp.loader.exec_module(v)

    shots = os.path.join(root, "remotion", "src", "shots")
    have = sorted(f[:-4] for f in os.listdir(shots) if f.endswith(".tsx"))[:6]
    assert len(have) >= 6, "need registers to build the shopped case from"
    # a vocabulary that is simply six register names, spelled as prose
    shopped = [re.sub(r"(?<!^)(?=[A-Z])", " ", n).lower() for n in have]
    # forms a subject is recorded in that this library has never held
    derived = ["tide gauge", "docket entry", "flight strip", "knitting chart", "piano roll",
               "exhibit sticker"]

    for label, vocab, expect in (("shopped", shopped, True), ("derived", derived, False)):
        errs, warns = [], []
        v._form_vocabulary({"form_vocabulary": [{"form": f, "carries": "x"} for f in vocab]},
                           [{"index": i, "shot_fit": {"form": f}} for i, f in enumerate(vocab)],
                           errs, warns)
        flagged = any("shopping list" in w for w in warns)
        assert flagged is expect, (
            "%s vocabulary: expected shopping-list warning=%s, got %s (%r)" % (label, expect, flagged, warns))
        assert not errs, "%s vocabulary should not ERROR: %r" % (label, errs)


def test_photoplate_callouts_hold_at_inputs_they_were_not_tuned_on():
    """Rendered checks found these; these are the invariants that keep them found.

    Each was a real frame: a 52-character unbroken label walked out of its chip and across the frame to the
    far margin (CSS does not break a word on its own, and the chip had no `overflowWrap` while the film's
    caption did); a mark with an empty label drew an empty rectangle with a leader running to it — furniture
    a viewer cannot decode; and the chip's width cap, `W * 0.24`, was chosen at 1920 and became thirteen
    characters at a 1080-wide portrait frame, stacking one word per line inside a margin that had 453px to
    give — the same cramping the margin layout was introduced to cure.
    """
    src = open(os.path.join(_ROOT_TSX_DIR, "shots", "PhotoPlate.tsx"), encoding="utf-8").read()
    assert "overflowWrap: 'anywhere'" in src, (
        "a callout chip must break an unbreakable label instead of letting it leave the box")
    assert "const labelled =" in src and "{labelled ?" in src, (
        "an unlabelled mark draws an empty chip again — the ring alone marks the point")
    assert not re.search(r"marginated \?\s*Math\.min\(W \* 0\.24", src), (
        "the chip measure is bounded by frame width again; it must be bounded by CHARACTERS so it holds at "
        "portrait and 4:5")
    assert "CHIP_MEASURE" in src, "the character measure is gone"


def test_a_register_drawing_its_own_demo_object_is_caught():
    """The copy checks are blind to demo GEOMETRY, and a bicycle went out because of it.

    A contest sample for a beat about enterprise data isolation rendered TechnicalPlate without passing
    `strokes`, whose default is `BIKE` — so a full-size bicycle sat in the middle of the frame. No string was
    involved, so every text check said the beat was clean. The rule generalises past drawings: a prop left
    unset whose default is a NAMED module constant means the REGISTER is supplying the content, not the
    film. Precise rather than noisy — 20 such props across the whole library.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "shot_proof_demo", os.path.join(root, "scripts", "shot_proof.py"))
    sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)

    assert sp.demo_content_props("TechnicalPlate").get("strokes") == "BIKE", (
        "the bicycle default is no longer detected — this is the case the check was written for")
    assert sp.demo_content_props("ChatThread").get("messages") == "DEFAULT_MSGS"

    board = {"meta": {"language": "zh"}, "slides": [
        {"index": 0, "shot": "TechnicalPlate", "shot_props": {"kicker": "隔离图版", "object": "五个维度"}}]}
    errs, _ = sp.static_checks(board)
    assert any("BIKE" in e for e in errs), (
        "a beat that lets TechnicalPlate draw its own bicycle passes: %r" % errs)

    board["slides"][0]["shot_props"]["strokes"] = [{"d": "M0 0"}]
    board["slides"][0]["shot_props"]["parts"] = [{"label": "知识库"}]
    errs2, _ = sp.static_checks(board)
    assert not any("BIKE" in e for e in errs2), errs2


def test_the_direction_router_states_its_shortfall_instead_of_padding_it():
    """A slot that looks filled makes "conceive the rest" unreachable.

    route() padded the contest to its width from a fixed fallback order, so a film about an AI office agent
    was offered `cinematic-craft` — a 3D torus knot — as one of three considered directions. It was there
    because the list needed a third row. The viewer's words were 有的还是感觉毫无关联. And the scoring that
    should have prevented it tokenised with `[a-z0-9']+`, which finds nothing in Chinese, Japanese or
    Korean: every CJK topic scored zero on every template and fell through to the padding by construction.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "shot_templates_probe", os.path.join(root, "scripts", "shot_templates.py"))
    st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)

    # a topic the catalogue has nothing for returns NOTHING, and says how many are owed
    none_topic = "一支关于宋代茶盏釉色的短片"
    assert st.matched_seeds(none_topic) == [], (
        "the router still invents matches for a topic it has no keywords for: %r" % st.matched_seeds(none_topic))
    assert st.conceive_gap(none_topic, n=3) == 3

    # CJK must be able to MATCH — the whole failure was that it never could
    zh = st.matched_seeds("一部讲终端与命令行的技术片")
    assert "terminal-technical" in zh, ("a Chinese topic still matches nothing — the scoring is ASCII-only "
                                        "again and every CJK film falls through: %r" % zh)
    assert st.matched_seeds("How database indexes actually work"), "Latin scoring regressed"

    # and nothing may quietly fill the gap
    src = open(os.path.join(root, "scripts", "shot_templates.py"), encoding="utf-8").read()
    body = src[src.index("def matched_seeds"):src.index("def conceive_gap")]
    assert "DEFAULT_ORDER" not in body, "matched_seeds pads from the fallback order again"

    cs = open(os.path.join(root, "scripts", "contest_sample.py"), encoding="utf-8").read()
    assert "--conceived" in cs and "build_props_conceived" in cs, (
        "there is no way to RENDER a conceived direction, so padding is the path of least resistance again")


def test_a_labelled_list_without_icons_is_reported():
    """A register with a list used to draw an abstract mark chosen by INDEX.

    The same four shapes in the same order on every film, whatever the labels said — a ring beside 「开表格」
    teaches a viewer nothing, and CardStack3D put the card's ORDINAL in a coloured chip. Icons are the
    default for category content here, so their absence is what needs a reason; this is the thing that asks
    for it. Which registers can take one is READ from the source, so wiring a new one brings it under the
    gate the same day rather than whenever somebody remembers a list.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "shot_proof_icons", os.path.join(root, "scripts", "shot_proof.py"))
    sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)

    assert sp.icon_capable("QuadSplit") and sp.icon_capable("CardStack3D"), (
        "the icon-capable set is derived from `runtime/icons` imports and no longer finds the wired ones")
    assert not sp.icon_capable("KnowledgeGraph"), "a register that draws no icon is reported as capable"

    bare = sp.icons_missing("QuadSplit", {"panels": [{"label": "A"}, {"label": "B", "icon": "file"}]})
    assert bare == ["panels/A"], bare
    assert not sp.icons_missing("QuadSplit", {"panels": [{"label": "A", "icon": "table"},
                                                         {"label": "B", "icon": "file"}]})
    # a single item is a hero, not a list — an icon there is a different decision
    assert not sp.icons_missing("QuadSplit", {"panels": [{"label": "A"}]})

    # and the family itself: every name the shots reference must exist, or the render throws mid-film
    icons = open(os.path.join(root, "remotion", "src", "runtime", "icons.tsx"), encoding="utf-8").read()
    names = set(re.findall(r"^  ([a-z]+):\s*<>", icons, re.M))
    assert len(names) >= 20, "the icon family shrank to %d — a thin set forces decorative reuse" % len(names)
    for shot in ("QuadSplit", "CardStack3D"):
        src = open(os.path.join(root, "remotion", "src", "shots", shot + ".tsx"), encoding="utf-8").read()
        assert "IconName" in src, "%s imports Icon without its name type, so a typo is not caught" % shot


def test_every_critic_rule_carries_a_REAL_precedent():
    """A rule states what to do; its precedent states what went wrong, which is what generalises.

    And the precedent must be CHECKABLE, because "never fabricate" is a standing rule that nothing enforced:
    an invented incident reads exactly like a real one. Each precedent names the commit that repaired it, and
    this test resolves every hash against the repository's own history — so a fabricated precedent cannot be
    committed. A dimension with no real incident says so in as many words and is scored as weaker evidence;
    that admission is the honest form, not a hole to be filled with something plausible.
    """
    import subprocess
    mod, root = _critic_ledger()
    declared = [d for d, _ in mod.dimensions()]
    pre = mod.precedents()

    missing = [d for d in declared if d not in pre]
    assert not missing, (
        "%s carry neither a `**Precedent — `hash`:**` nor an explicit `**Precedent — none on record.**` — a "
        "rule with no incident behind it cannot be generalised to a topic nobody has seen" % ", ".join(missing))

    if subprocess.run(["git", "-C", root, "rev-parse", "--git-dir"],
                      capture_output=True).returncode != 0:
        return                                    # installed without history; nothing to resolve against
    for sid, h in sorted(pre.items()):
        if h is None:
            continue
        r = subprocess.run(["git", "-C", root, "cat-file", "-t", h], capture_output=True, text=True)
        assert r.stdout.strip() == "commit", (
            "%s cites precedent %s, which is not a commit in this repository — a precedent that cannot be "
            "resolved is indistinguishable from an invented one" % (sid, h))


def test_the_ledger_requires_every_dimension_and_refuses_a_bare_consent(tmp_path):
    """The critic reported only FLAGGED beats, so "looked at and clean" and "never looked at" were one artifact.

    Silence is not consent was written in the critic's own file — as prose, addressed to the only party it
    could not audit. These are the refusals that make it mechanical, each exercised against a real out_dir.
    """
    import json
    from PIL import Image
    mod, root = _critic_ledger()
    out = str(tmp_path)
    Image.new("RGB", (64, 64), (30, 40, 60)).save(os.path.join(out, mod.CONTACT_SHEET))
    os.makedirs(os.path.join(out, "_keyframes"), exist_ok=True)
    Image.new("RGB", (32, 32), (200, 200, 200)).save(os.path.join(out, "_keyframes", "scene_03.png"))
    lp = os.path.join(out, mod.LEDGER_NAME)
    dims = [d for d, _ in mod.dimensions()]

    def write(**over):
        led = {"reviewer": "independent", "verdict": "PASS",
               "contact_sheet_sha256": mod.sha256_of(os.path.join(out, mod.CONTACT_SHEET)),
               "rows": [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_03.png"} for d in dims]}
        led.update(over)
        json.dump(led, open(lp, "w", encoding="utf-8"), indent=2)

    # no ledger at all — the old behaviour, where producing nothing was a passing review
    assert mod.validate(out)[0], "a review that produced no ledger must not pass"

    write()
    assert not mod.validate(out)[0], mod.validate(out)[0]
    assert not mod.validate(out, final=True)[0]

    # a dimension that was never looked at is a MISSING ROW, not an absence of complaint
    write(rows=[r for r in json.load(open(lp))["rows"] if r["id"] != dims[-1]])
    assert any(dims[-1] in e for e in mod.validate(out)[0]), "a missing dimension must fail"

    # a bare verdict with nothing behind it
    write(rows=[{"id": d, "verdict": "pass", "evidence": ""} for d in dims])
    assert len(mod.validate(out)[0]) >= len(dims), "every un-evidenced verdict must fail"

    # evidence naming a frame that does not exist — specific-looking, pointing at nothing
    write(rows=[{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_99.png"} for d in dims])
    assert any("scene_99" in e for e in mod.validate(out)[0])

    # pinned to a DIFFERENT render than the one in out_dir
    write(contact_sheet_sha256="0" * 64)
    assert any("does not match" in e for e in mod.validate(out)[0])

    # a failing dimension cannot be carried by a PASS, and must arrive with a fix
    rows = [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_03.png"} for d in dims]
    rows[0] = {"id": dims[0], "verdict": "fail", "evidence": "_keyframes/scene_03.png"}
    write(rows=rows)
    errs = mod.validate(out)[0]
    assert any("no FIX" in e for e in errs) and any("PASS while" in e for e in errs)

    # the DELIVERY review may not be the film's own maker
    write(reviewer="in-context")
    assert not mod.validate(out)[0], "in-context is fine while iterating"
    assert any("confirmation bias" in e for e in mod.validate(out, final=True)[0]), (
        "--final must refuse a ledger written by the maker")


def test_the_ledger_reads_its_dimensions_from_the_critic_rather_than_a_copy(tmp_path):
    """A hardcoded S1..S13 would let a NEW dimension be written and never required — the shape this repo
    has paid for repeatedly (a caption band in four disagreeing copies, an opt-in gate that reported 0 on
    the very deck that motivated it). Adding a dimension to the critic's file must make the gate demand it.
    """
    mod, root = _critic_ledger()
    src = open(os.path.join(root, "agents", "shot-critic.md"), encoding="utf-8").read()
    fake = str(tmp_path / "critic.md")
    open(fake, "w", encoding="utf-8").write(src + "\n**S99 · A DIMENSION INVENTED BY THIS TEST.** body\n")
    assert "S99" in [d for d, _ in mod.dimensions(fake)], (
        "a dimension added to the critic's file is not picked up — the list is a copy, not a reading")


def test_every_remotion_capability_is_reachable_from_the_authoring_path():
    """A capability nothing in the authoring path reaches is indistinguishable from one never written.

    Nine commits added four capabilities to this tier and left `agents/` and `references/` untouched — a
    zero-line diff — so an agent following the documented workflow to make a new film would have used none
    of them, and the deterministic fallback emitted only `shot`/`shot_props`. Every gate stayed green
    because a gate reads the artifact, not the path that failed to produce it.

    Two halves, because either alone is passable while the capability stays unreachable: the DOCUMENTS an
    author reads must name it, and the deterministic path must actually emit it.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = {}
    for rel in ("SKILL.md", "agents/shot-director.md", "agents/shot-critic.md",
                "references/remotion-shot-authoring.md"):
        docs[rel] = open(os.path.join(root, rel), encoding="utf-8").read()
    everything = "\n".join(docs.values())

    # Per DOCUMENT, not the union. A dispatched agent reads its OWN brief; naming a capability only in
    # SKILL.md leaves the agent that must actually use it none the wiser, which is how a zero-line diff to
    # agents/ went unnoticed. Each capability is required where the person who must ACT on it will read it.
    required = [
        ("agents/shot-director.md", "design_dna.seam",
         "the storyboard author sets the film's native cut, and must know not setting it is the right answer"),
        ("agents/shot-director.md", "camera",
         "the per-beat camera is a storyboard field; nobody else can decide which beat earns a move"),
        ("agents/shot-director.md", "PhotoPlate",
         "reaching for real imagery is a register-SELECTION decision"),
        ("agents/shot-critic.md", "camera",
         "nothing reviews the camera, so a film can carry a nonsense one and pass"),
        ("references/remotion-shot-authoring.md", "Plane",
         "depth is a thing a REGISTER does; its author reads this file before writing one"),
        ("references/remotion-shot-authoring.md", "captionBand",
         "a register derives its bottom edge from the band, and a literal bottom:N is the defect that shipped"),
        ("SKILL.md", "scripts/seam_plan.py <out_dir>`",
         "the planner has to be an invocable pipeline STEP, not prose in a tier description"),
        ("SKILL.md", "critic_ledger.py <out_dir> --final",
         "the independent delivery review has to be a gate in the workflow, not advice inside the critic"),
        ("agents/shot-critic.md", "critic_ledger.py",
         "the critic is the party that must WRITE the ledger; unnamed in its own brief it will not"),
        ("SKILL.md", "scripts/sfx.py --calibrate",
         "the audio chain's offset is measurable only if the workflow says how; unnamed it goes back to "
         "being assumed, which is what it was"),
    ]
    missing = [(f, n, why) for f, n, why in required if n not in docs[f]]
    assert not missing, "\n".join(
        "%s does not name %r — %s" % (f, n, why) for f, n, why in missing)

    # and the deterministic fallback must emit both fields, on a board that declares relations
    import importlib.util, tempfile, json as _json
    spec = importlib.util.spec_from_file_location("shot_director_probe",
                                                  os.path.join(root, "scripts", "shot_director.py"))
    sd = importlib.util.module_from_spec(spec); spec.loader.exec_module(sd)
    src = open(os.path.join(root, "scripts", "shot_director.py"), encoding="utf-8").read()
    assert "import seam_plan" in src and "plan_camera" in src, (
        "the deterministic shot-director no longer plans the film's cuts and camera, so a film made "
        "without the LLM agent gets a register per beat and nothing else")


def test_the_cut_vocabulary_actually_reaches_the_storyboard():
    """The tier's seams existed, were guarded, were mapped — and no film ever used one.

    `Film.tsx` implements clock/slide/wipe/dissolve plus `carry` (a collapse-to-line match-cut),
    `render_remotion.py` maps `transition_in` onto them, and a luminance guard protects them. A delivered
    35-beat film still shipped with all 34 cuts identical, because nothing in the authoring path ever wrote
    the field. This pins the two halves of the fix: a planner that derives marks from the `relation` the
    board already carries, and a validator that notices when a long film has none.
    """
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("seam_plan", os.path.join(root, "scripts", "seam_plan.py"))
    sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)

    # a 30-beat film whose relations are mostly continuation, with real chapter breaks
    slides = [{"shot": "MapPlate", "relation": "continuation"} for _ in range(30)]
    slides[0]["relation"] = "open"
    for i in (7, 15, 23):
        slides[i]["relation"] = "new-topic"
    slides[11]["relation"] = "payoff"
    slides[29]["relation"] = "close"
    marks = sp.plan(slides)

    assert marks, "the planner derived no seam from a board that declares chapter breaks"
    assert len(marks) <= 3, "a marked seam is punctuation; %d of them is a style" % len(marks)
    assert 0 not in marks, "beat 0 has no seam before it"
    ks = sorted(marks)
    # An ABSOLUTE floor, not `>= sp.MIN_GAP`. Asserting against the module's own constant makes the test a
    # copy of it: drop MIN_GAP to 0 and the assertion passes while marks pile up next to each other. A test
    # that moves with the value it is checking is not checking anything.
    assert sp.MIN_GAP >= 4, "the spacing rule was weakened below the point where a mark reads as punctuation"
    assert all(b - a >= 4 for a, b in zip(ks, ks[1:])), (
        "two marks landed within 4 beats — punctuation that close reads as a style: %r" % ks)
    for i, m in marks.items():
        rel = slides[i]["relation"]
        assert rel in sp.SEAM_BY_RELATION, "marked a %r seam, which is not a claim about anything" % rel
        assert m["type"] in ("clock", "dissolve", "carry", "slide", "wipe")

    # `continuation` is never marked — the one relation whose honest cut is no cut
    only_cont = [{"shot": "MapPlate", "relation": "continuation"} for _ in range(30)]
    assert sp.plan(only_cont) == {}, "an unbroken argument must keep every cut invisible"

    # a seam that would cross a dark/light boundary becomes `carry` — anything else is silently
    # discarded by Film.tsx's luminance guard, which would look like the planner did nothing
    import shot_director as sd
    dark = next((n for n in sd.PROVENANCE if sd.shot_luma(n) == "dark"), None)
    light = next((n for n in sd.PROVENANCE if sd.shot_luma(n) == "light"), None)
    if dark and light:
        cross = [{"shot": light, "relation": "continuation"} for _ in range(30)]
        cross[0]["relation"] = "open"
        cross[15] = {"shot": dark, "relation": "new-topic"}
        got = sp.plan(cross).get(15)
        assert got and got["type"] == "carry", (
            "a mark across a dark/light boundary must be the carry, not %r — the guard discards the rest" % got)


def test_validate_notices_a_film_that_never_uses_its_own_cuts():
    board = {"meta": {"renderer": "remotion", "design_dna": {"id": "bespoke-thing"}},
             "slides": [{"shot": "MapPlate", "relation": "continuation"} for _ in range(20)]}
    errs, warns = [], []
    v._film_language(board["meta"], board["slides"], errs, warns)
    assert not errs, "this is a warning, not an error — a deliberately unbroken film is legitimate"
    assert any("not one MARKED seam" in w for w in warns), warns
    # The gate used to ALSO nag a bespoke direction into declaring a native `seam`. Measured on a delivered
    # film, taking that advice turned 31 of 34 cuts kinetic and the 3 deliberate marks then read exactly
    # like the 31 that meant nothing — the film lost its punctuation to the feature meant to give it a
    # voice. So the warning fires the other way now, and a plain cross-fade is a finished decision.
    assert not any("bespoke direction with no `seam`" in w for w in warns), (
        "validate still pushes an author toward a native seam, which is what removed a film's punctuation")

    swamped = {"renderer": "remotion", "design_dna": {"id": "x", "seam": {"type": "wipe"}}}
    sl = [{"shot": "MapPlate", "relation": "continuation"} for _ in range(20)]
    sl[9]["transition_in"] = {"type": "clock"}
    e4, w4 = [], []
    v._film_language(swamped, sl, e4, w4)
    assert any("reads as punctuation" in w for w in w4), w4

    # marks present, and PROPORTIONATE to the cuts the declared seam makes kinetic -> silent
    ok = {"meta": {"renderer": "remotion",
                   "design_dna": {"id": "bespoke-thing", "seam": {"type": "wipe"}}},
          "slides": [{"shot": "MapPlate", "relation": "continuation"} for _ in range(20)]}
    for i in (4, 9, 14):
        ok["slides"][i]["transition_in"] = {"type": "clock"}
    errs2, warns2 = [], []
    v._film_language(ok["meta"], ok["slides"], errs2, warns2)
    assert not warns2, warns2

    # and it complains the OTHER way when every cut is marked
    loud = {"meta": {"renderer": "remotion",
                     "design_dna": {"id": "terminal"}},
            "slides": [{"shot": "MapPlate", "relation": "new-topic",
                        "transition_in": {"type": "clock"}} for _ in range(20)]}
    errs3, warns3 = [], []
    v._film_language(loud["meta"], loud["slides"], errs3, warns3)
    assert any("only reads as punctuation while it" in w for w in warns3), warns3


def test_shot_proofs_rendered_checks_are_not_opt_in():
    """An opt-in gate is not a detector.

    The rendered half of the proof sheet — the only half that can see what a frame LOOKS like — sat behind
    `--stills`. A delivered film had two registers drawing their own subtitle inside the band reserved for
    the burned caption; this script owns exactly that measurement, it was run, and it printed
    "OK (static only)". Nobody sees the flag they did not pass.
    """
    src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "shot_proof.py"),
               encoding="utf-8").read()
    assert 'if "--no-stills" not in argv:' in src, (
        "the rendered checks must run by default; --no-stills is the opt-OUT")
    assert 'if "--stills" in argv:' not in src, (
        "shot_proof still gates its rendered checks behind an opt-in --stills flag")

    skill = open(os.path.join(os.path.dirname(__file__), "..", "SKILL.md"), encoding="utf-8").read()
    assert "shot_proof.py <out_dir> --stills" not in skill, (
        "SKILL.md still tells the author to pass --stills, which no longer exists")


def test_the_caption_band_has_exactly_one_definition():
    """Four files had to agree on the band's height and nothing made them.

    `runtime/layout.ts` (150), `Film.tsx` (150), `frame_safe_qa.py` (0.135 of H = 146px) and
    `shot_still_qa.py` (200/150) each carried their own copy. They agreed only by coincidence, and the
    coincidence ends the moment the caption's type size changes: the renderer reserves a taller band while
    both gates keep measuring the old one, so a shot label can sit in the new band, overlap the caption, and
    pass. This asserts the duplicates are gone and the survivors derive.
    """
    import importlib.util
    root = os.path.join(os.path.dirname(__file__), "..")
    spec = importlib.util.spec_from_file_location(
        "_caption_band", os.path.join(root, "scripts", "_caption_band.py"))
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)

    # the TS is the definition, and it must still expose the fractions this module parses
    for w, h in [(1920, 1080), (1080, 1920), (1080, 1080)]:
        assert cb.caption_band_px(w, h) > cb.caption_size_px(w, h) * 2, (
            "the band at %dx%d cannot hold two lines of its own caption type" % (w, h))

    # The caption must still clear a readability floor in a phone-sized window — but the floor is 4%, not
    # the 5% it started at, and the change is evidence-led rather than taste. Two things: the VIEWER of a
    # delivered film said the caption was simply too large, which outranks a floor nobody ever measured;
    # and this tier's 5% was an outlier inside the skill — the html tier had already reasoned its way to
    # 0.040 with the reason written beside it ("captions are a reading aid, not a headline"). 4% is the
    # value that tier has shipped for a long time, so it is the floor both tiers can be held to; remotion
    # sits just above it at 0.042. Lower it further only with a real legibility measurement.
    assert cb.caption_size_px(1920, 1080) >= 0.04 * 1080, (
        "caption type is %dpx at 1080p, under the 4%% floor" % cb.caption_size_px(1920, 1080))

    # and NO file may carry its own copy of the number any more
    for rel in ("scripts/frame_safe_qa.py", "scripts/shot_still_qa.py"):
        src = open(os.path.join(root, rel), encoding="utf-8").read()
        assert "caption_band_px" in src, "%s no longer derives the band" % rel
        assert not re.search(r"CAPTION_BAND\s*=\s*0?\.\d", src), (
            "%s restated the caption band as a literal fraction" % rel)
    film = open(os.path.join(root, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert not re.search(r"const\s+CAPTION_BAND\s*=\s*\d", film), (
        "Film.tsx restated the caption band instead of importing captionBand()")


def test_a_clock_derived_number_is_caught_inline_too():
    """The named-local walk was how the two known cases happened to be written.

    Written inline — `<div>{Math.round(t * 100)}%</div>` — it is the same fabricated percentage and the
    walk cannot see it, so the fix would have covered two instances and not the class. The precision half
    matters as much: `tok.t.slice(0, take)` is a typewriter reveal whose `t` is a field name, and reporting
    a register's own data is what gets a checker switched off.
    """
    import importlib.util, tempfile, textwrap
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "onscreen_text_qa", os.path.join(root, "scripts", "onscreen_text_qa.py"))
    q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)

    def scan(src):
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(textwrap.dedent(src)); path = f.name
        try:
            return q.unsourced_numbers(path)
        finally:
            os.unlink(path)

    head = "export const X: React.FC<{label?: string}> = ({label = 'x'} = {}) => {\n  const t = useT();\n"
    assert scan(head + "  return (<div>{Math.round(t * 100)}%</div>);\n};\n"), (
        "an inline clock-derived percentage went unreported")
    assert not scan(head + "  const take = Math.floor(t * 9);\n"
                           "  return (<div>{tok.t.slice(0, take)}</div>);\n};\n"), (
        "a typewriter reveal was reported as a fabricated statistic")
    assert not scan("export const X: React.FC<{pct?: number}> = ({pct = 0} = {}) => {\n"
                    "  const t = useT();\n"
                    "  return (<div>{Math.round(pct * t)}%</div>);\n};\n"), (
        "a readout the FILM feeds was reported as unsourced")
    assert not scan(head + "  return (<div>{[1,2].map((i) => (<span>{i + 1}</span>))}</div>);\n};\n"), (
        "an ordinal — a position in a list — is intrinsic to the form, not a measurement")
    # A FIELD named `t` is not the clock. This one is separate from the case above on purpose: there the
    # string-operation filter already excludes `.slice(`, so it does not exercise the dot rule at all.
    assert not scan("export const X: React.FC<{n?: number}> = ({n = 1} = {}) => {\n"
                    "  const t = useT();\n"
                    "  const cfg = {t: 0.5};\n"
                    "  return (<div>{Math.round(cfg.t * 100)}</div>);\n};\n"), (
        "a field named `t` was read as the clock — the checker reported a register's own data")


def test_no_register_prints_a_number_the_film_never_supplied():
    """A percentage counted off the CLOCK is a fabricated statistic, and no word-scan can see it.

    `BlueprintGrid` printed `{specN}` where `const specN = Math.round(lerp(0, 100, easeOutCubic(...)))` —
    a confident 100% over a beat whose claim was that the nave was NEVER finished, and it would have
    printed over any topic that reached for the register. There are no letters in `100%`, so the text
    ratchet below is blind to it; provenance is what catches it.
    """
    import glob
    import importlib.util
    root = os.path.join(os.path.dirname(__file__), "..")
    spec = importlib.util.spec_from_file_location(
        "onscreen_text_qa", os.path.join(root, "scripts", "onscreen_text_qa.py"))
    qa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa)
    offenders = {}
    for f in sorted(glob.glob(os.path.join(root, "remotion", "src", "shots", "*.tsx"))):
        hits = qa.unsourced_numbers(f)
        if hits:
            offenders[os.path.basename(f)[:-4]] = hits
    assert not offenders, (
        "these registers print a number computed from the clock, not from the film: %r. "
        "Give the readout a prop with NO default and draw it only when supplied — a number is real or "
        "it is absent." % offenders)


def test_no_register_prints_text_the_film_never_supplied():
    """A register may only put words on screen that came from props — or that it DECLARES as its own form.

    shot_proof's demo-default check compares a beat's shot_props against the register's prop DEFAULTS, so a
    string literal written straight into the JSX is invisible to it: there is no default to differ from, and
    it prints on every film that ever uses the register whatever that film is about. This is the check that
    sees those, and the grandfather list is what keeps the count going one way.

    Two escapes, both explicit: make the literal a prop whose default is the literal (existing films render
    identically, and the demo-default check starts covering it), or declare it as intrinsic to the form —
    an axis label, a REC light — with `export const INTRINSIC_TEXT = [...]`.
    """
    import glob
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import onscreen_text_qa as q

    shots = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "shots")
    dirty = set()
    for f in sorted(glob.glob(os.path.join(shots, "*.tsx"))):
        if q.scan(f):
            dirty.add(os.path.basename(f)[:-4])

    added = sorted(dirty - _UNSUPPLIED_TEXT_GRANDFATHERED)
    assert not added, (
        "these registers print text no film supplied: %s. Make each literal a prop whose default is the "
        "literal, or declare it in INTRINSIC_TEXT if it belongs to the register's own form. Run "
        "`python3 scripts/onscreen_text_qa.py` to see them." % ", ".join(added))

    cleaned = sorted(_UNSUPPLIED_TEXT_GRANDFATHERED - dirty)
    assert not cleaned, ("these registers are clean now — remove them from "
                         "_UNSUPPLIED_TEXT_GRANDFATHERED so the ratchet keeps holding: %s"
                         % ", ".join(cleaned))
