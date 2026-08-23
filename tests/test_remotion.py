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
    # every shot file is a valid id, and the count matches the assertion below (the whole library).
    # 123 base + 8 terminal-native (Term*) + 3 editorial-native (Ed*) style-native family shots = 134.
    assert len(_SHOT_IDS) == 134, _SHOT_IDS
    assert rr._remotion_shot_ids() == _SHOT_IDS
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
import gen_dna_ground as gdg                                              # noqa: E402

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


def test_dna_ground_set_is_regenerated():
    # DNA_GROUND tells the film which shots take their ground from the DNA, which is how captions pick contrast.
    # A shot migrated later without regenerating it would render dark ink on a dark ground.
    assert gdg.main(["--check"]) == 0, "shotLuma.ts DNA_GROUND is stale — run: python scripts/gen_dna_ground.py"


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
    """The HTML tier already declares these faces. The remotion tier must name the SAME families
    with the SAME weight ranges, or a variable font silently renders synthesised weights."""
    css = open(_BASE_CSS, encoding="utf-8").read()
    faces = re.findall(
        r'@font-face\{font-family:"([^"]+)";src:url\("\.\./fonts/([^"]+)"\);font-weight:([^;]+);',
        css,
    )
    assert len(faces) >= 4, "could not parse @font-face out of base.css (got %r)" % (faces,)
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
