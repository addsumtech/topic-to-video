"""ATMOSPHERE library + topic routing + the render-substrate bridge.

An atmosphere is a whole-film WORLD that reaches the pixels (material CLASS + post + style), not a colour
re-skin. `route(topic)` is the contest candidate generator (topic -> best ~3). `build_props` threads the
picked world's style (overriding theme.style) + {materialClass, post} onto every scene, so a terminal deck
renders terminal and a cartoon deck renders cel-shaded. These lock the library, the routing, the wiring, and
the render-side source (toon material + CRT/clean post)."""
import os

import atmospheres as A
import render_remotion as rr
import storyboard as sb
import validate

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src")
_VALID_STYLES = {"swiss", "editorial", "bauhaus", "brutalism", "glassmorphism", "claymorphism", "manga",
                 "risograph", "memphis", "noir", "cyberpunk", "vaporwave", "watercolor", "artdeco",
                 "cinematic", "blueprint", "terminal", "cartographic"}


# ── library integrity ─────────────────────────────────────────────────────────────────────────────────
def test_every_atmosphere_has_a_valid_render_bundle():
    assert len(A.keys()) >= 8, "the atmosphere library is too thin"
    for k in A.keys():
        p = A.profile(k)
        assert p["style"] in _VALID_STYLES, "%s has an unknown base style %r" % (k, p["style"])
        assert p["materialClass"] in A._MATERIAL_CLASSES, "%s bad materialClass" % k
        assert p["post"] in A._POST_PROFILES, "%s bad post" % k


def test_three_seed_worlds_are_render_distinct():
    # the 3 seeds must differ at the RENDER layer, not just palette: post + materialClass.
    t, c, a = A.profile("terminal"), A.profile("cartoon"), A.profile("app")
    assert t["post"] == "crt", "terminal must be a CRT world"
    assert c["materialClass"] == "toon", "cartoon must be cel-shaded (toon)"
    assert a["post"] == "clean", "app must be a clean product world"
    # they are genuinely different substrates, not one look re-coloured
    assert len({(t["materialClass"], t["post"]), (c["materialClass"], c["post"]), (a["materialClass"], a["post"])}) == 3


def test_profile_unknown_is_none():
    assert A.profile("nope") is None and A.profile(None) is None


# ── topic routing (the contest candidate generator) ───────────────────────────────────────────────────
def test_route_picks_topic_fit_and_always_returns_three():
    assert A.route("an AI agent framework CLI")[0] == "terminal"
    assert A.route("a kids math learning app")[0] == "cartoon"
    assert "noir" in A.route("a luxury security brand")
    assert len(A.route("something completely generic with no keywords")) == 3   # pads from the fallback order
    assert len(set(A.route("logistics supply chain"))) == 3                     # distinct


def test_route_is_deterministic():
    assert A.route("a fintech savings platform") == A.route("a fintech savings platform")


# ── the render bridge: build_props threads the world onto the render ──────────────────────────────────
def _deck(tmp, atmosphere):
    aud = os.path.join("audio", "01.mp3")
    os.makedirs(os.path.join(str(tmp), "audio"), exist_ok=True)
    open(os.path.join(str(tmp), aud), "wb").write(b"\x00")
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s.update({"planes": [{"kind": "bars", "data": [3, 5, 8], "position": [0, 0, 0]}],
              "camera3d": [{"at": 0.0, "yaw": 0, "radius": 8, "height": 4}], "audio": aud, "duration": 3.0})
    data = sb.new_storyboard({"renderer": "remotion", "atmosphere": atmosphere})
    data["slides"] = [s]
    return data


def test_build_props_overrides_style_and_threads_substrate(tmp_path):
    p = rr.build_props(_deck(tmp_path, "terminal"), str(tmp_path))
    assert p["theme"]["style"] == "terminal", "atmosphere did not override theme.style"
    a = p["scenes"][0]["atmosphere"]
    assert a["materialClass"] == "standard" and a["post"] == "crt"


def test_build_props_no_atmosphere_is_unchanged(tmp_path):
    p = rr.build_props(_deck(tmp_path, None), str(tmp_path))
    assert p["scenes"][0]["atmosphere"] is None            # None -> the render is byte-identical to before


def test_cartoon_threads_toon(tmp_path):
    p = rr.build_props(_deck(tmp_path, "cartoon"), str(tmp_path))
    assert p["scenes"][0]["atmosphere"]["materialClass"] == "toon"


# ── validate + render-side source guards ──────────────────────────────────────────────────────────────
def test_validate_errors_on_unknown_atmosphere(tmp_path):
    data = _deck(tmp_path, "bogus-world")
    r = validate.evaluate(data, str(tmp_path))
    assert any("unknown meta.atmosphere" in e for e in r["errors"]), r["errors"]


def test_render_side_has_the_bridge():
    three = open(os.path.join(_SRC, "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "meshToonMaterial" in three and "TOON_GRADIENT" in three, "cartoon toon material is gone"
    assert "materialClass === 'toon'" in three and "post === 'clean'" in three, "atmosphere not read in ThreeScene"
    fin = open(os.path.join(_SRC, "theme", "Finish.tsx"), encoding="utf-8").read()
    assert "post === 'crt'" in fin and "repeating-linear-gradient" in fin, "CRT scanline post is gone from Finish"
    assert "post === 'clean'" in fin, "clean post is gone from Finish"


def test_atmosphere_contest_absent_warns_present_validates(tmp_path):
    # atmosphere set but no contest record -> warn (mirror the template contest)
    r = validate.evaluate(_deck(tmp_path, "terminal"), str(tmp_path))
    assert any("no `meta.atmosphere_contest`" in w for w in r["warnings"]), r["warnings"]


def test_atmosphere_contest_winner_must_match(tmp_path):
    d = _deck(tmp_path, "terminal")
    d["meta"]["atmosphere_contest"] = {"candidates": ["terminal", "hologram", "app"], "winner": "app", "user_pick": True}
    r = validate.evaluate(d, str(tmp_path))
    assert any("atmosphere_contest.winner" in e for e in r["errors"]), r["errors"]


def test_atmosphere_contest_valid_is_clean(tmp_path):
    d = _deck(tmp_path, "terminal")
    d["meta"]["atmosphere_contest"] = {"candidates": ["terminal", "hologram", "app"], "winner": "terminal", "user_pick": True}
    r = validate.evaluate(d, str(tmp_path))
    assert not any("atmosphere_contest" in e for e in r["errors"]), r["errors"]


def test_cartoon_has_the_ink_outline():
    # the CARTOON world = cel bands + an inverted-hull INK outline; all 3 box forms draw it when toon.
    three = open(os.path.join(_SRC, "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "BoxOutline" in three and "THREE.BackSide" in three, "the inverted-hull ink outline is gone"
    assert three.count("<BoxOutline") >= 3, "not all box forms (bars/stack/particles) draw the toon outline"


def test_per_atmosphere_motion_grammar_is_wired():
    # each world MOVES differently: bouncy/snap/boot grow cadences reach the forms via growEase.
    three = open(os.path.join(_SRC, "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "function growEase" in three, "the per-atmosphere grow cadence is gone"
    for m in ("'bouncy'", "'snap'", "'boot'"):
        assert m in three, "growEase is missing the %s cadence" % m
    assert three.count("growEase(motion,") >= 4, "not all forms use the atmosphere motion cadence"
    assert 'atmosphere?.motion' in three, "the motion grammar is not resolved from the atmosphere"


def test_build_props_threads_motion_and_camera(tmp_path):
    # the motion + camera grammar fields reach the scene props (camera wiring is a follow-up; the field flows now)
    p = rr.build_props(_deck(tmp_path, "cartoon"), str(tmp_path))
    a = p["scenes"][0]["atmosphere"]
    assert a["motion"] == "bouncy" and a["camera"] == "whip"
