"""Design-first is a floor validate enforces: at least half of a remotion film's non-exempt beats are ADAPTED or
BUILT, at least one is BUILT, and a register used AS-IS earns it (`shot_fit.ideal` + `shot_fit.shares`).
Definitions live in scripts/validate.py above `DESIGN_SHARE_FLOOR`; the method in agents/shot-director.md."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate as v  # noqa: E402
from test_build_list import SHOT  # noqa: E402  — a minimal valid workshop shot source

GOOD_CHANGE = {"aspect": "layout",
               "what": "the three cells become one horizontal timeline with the middle step enlarged",
               "why": "this beat argues that the middle step is the bottleneck, so it must dominate the row"}
IDEAL = "three sources wired to one hub, two of them also wired to each other"
AS_IS_FIT = {"verdict": "fit",
             "ideal": "a field of identical dots where one dot lights up and the rest stay dim",
             "shares": "its grid already encodes many-equal-items by position, and its single highlight "
                       "carries the one-that-matters by colour"}


def _film(tmp_path, routes):
    """routes: one letter per beat — b(uilt workshop shot) / a(dapted) / s (as-is, justified) / x (as-is, bare)."""
    d = tmp_path / "workshop" / "shots"
    d.mkdir(parents=True, exist_ok=True)
    (d / "WsShotA.tsx").write_text(SHOT % {"name": "WsShotA"}, encoding="utf-8")
    slides = []
    for i, r in enumerate(routes, 1):
        s = {"index": i, "shot": "KnowledgeGraph", "shot_props": {"title": "t"}}
        if r == "b":
            s = {"index": i, "shot": "WsShotA", "shot_props": {},
                 "shot_fit": {"verdict": "build", "ref": "WsShotA", "ideal": IDEAL}}
        elif r == "a":
            # the change is MEASURABLE: KnowledgeGraph's `links` (a structure prop) is set — chords it draws
            s["shot_props"] = {"title": "t", "items": ["a", "b", "c"], "links": [[0, 1]]}
            s["shot_adaptation"] = {"changes": [dict(GOOD_CHANGE)]}
            s["shot_fit"] = {"verdict": "adapt", "why": "x", "ideal": IDEAL}
        elif r == "s":
            s["shot_fit"] = dict(AS_IS_FIT)
        slides.append(s)
    meta = {"renderer": "remotion",
            "build_list": [{"id": "WsShotA", "kind": "shot", "slot": "own", "means": "m", "accept": "a"}]}
    return meta, slides


def _share(tmp_path, meta, slides):
    errs, warns = [], []
    v._design_share(meta, slides, errs, warns, str(tmp_path))
    return errs, warns


def test_too_many_as_is_beats_is_an_error_naming_them_and_the_routes(tmp_path):
    meta, slides = _film(tmp_path, "bssss")            # 1 of 5 credited
    errs, _ = _share(tmp_path, meta, slides)
    msg = [e for e in errs if "only 1 of 5" in e]
    assert msg, errs
    assert "scene #2" in msg[0] and "ADAPT" in msg[0] and "SLOT AN OBJECT" in msg[0] and "BUILD" in msg[0]


def test_exactly_half_passes(tmp_path):
    meta, slides = _film(tmp_path, "basss"[:4])        # b a s s → 2 of 4
    errs, _ = _share(tmp_path, meta, slides)
    assert not errs, errs


def test_a_film_with_no_built_beat_fails_even_when_all_are_adapted(tmp_path):
    meta, slides = _film(tmp_path, "aaaa")
    errs, _ = _share(tmp_path, meta, slides)
    assert any("no beat is BUILT" in e for e in errs), errs


def test_a_vague_adaptation_note_does_not_count(tmp_path):
    meta, slides = _film(tmp_path, "baaa")
    vague = [
        {"redesigned": "changed it for this topic", "topic_idea": "the idea"},          # legacy free text
        {"changes": [{"aspect": "copy", "what": "rewrote every label into this film's own words entirely",
                      "why": "the default demo labels describe a different product than this film"}]},
        {"changes": [{"aspect": "layout", "what": "tweaked", "why": "better"}]},        # too thin to verify
        {"changes": [{"aspect": "encoding", "what": "size now encodes the share of each source file",
                      "why": "size now encodes the share of each source file"}]},       # what == why
    ]
    for k, bad in enumerate(vague[:3], 1):
        slides[k]["shot_adaptation"] = bad
    errs, _ = _share(tmp_path, meta, slides)
    assert any("only 1 of 4" in e for e in errs), errs
    assert v.adaptation_problem(vague[3]) is not None
    assert v.adaptation_problem({"changes": [GOOD_CHANGE]}) is None


def test_an_as_is_beat_must_earn_it(tmp_path):
    meta, slides = _film(tmp_path, "bas")
    errs, _ = _share(tmp_path, meta, slides)
    assert not errs, errs
    slides[2]["shot_fit"] = {"verdict": "fit", "ideal": "x", "shares": "it fits"}
    errs, _ = _share(tmp_path, meta, slides)
    assert any("AS-IS without earning it" in e and "scene #3" in e for e in errs), errs


def test_exempt_set_is_narrow(tmp_path):
    # a closing CinematicTitle used as-is leaves the denominator; the same register mid-film does not
    meta, slides = _film(tmp_path, "bxx")
    slides[2] = {"index": 3, "shot": "CinematicTitle", "shot_props": {"title": "t"}}
    routes = dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))
    assert routes[3] == "exempt" and routes[2] == "as-is"
    slides[1], slides[2] = dict(slides[2], index=2), dict(slides[1], index=3)
    routes = dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))
    assert routes[2] == "as-is", "a title card in the middle of a film is not the open/close card"
    # an evidence register is exempt only with its real picture set
    slides[1] = {"index": 2, "shot": "PhotoPlate", "shot_props": {}}
    assert dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))[2] == "as-is"
    slides[1]["shot_props"] = {"src": "assets/real.jpg"}
    assert dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))[2] == "exempt"


def test_the_floor_is_wired_into_evaluate():
    d = {"meta": {"renderer": "remotion"},
         "slides": [{"index": i, "shot": "KnowledgeGraph", "shot_props": {}, "audio": "audio/%02d.mp3" % i,
                     "duration": 6.0, "narration": "A sentence."} for i in (1, 2, 3)]}
    assert any(e.startswith("design-first:") for e in v.evaluate(d, "/tmp")["errors"])


def test_a_promoted_entry_is_built_only_when_the_catalogue_names_this_film(tmp_path):
    # a LIBRARY register named on the build list as "promoted" builds nothing
    meta, slides = _film(tmp_path, "aa")
    slides[0] = {"index": 1, "shot": "KineticManifesto", "shot_props": {}, "shot_fit": {"ideal": IDEAL}}
    meta["build_list"].append({"id": "KineticManifesto", "kind": "shot", "promoted": True, "slot": "own",
                               "means": "m", "accept": "a"})
    routes = dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))
    assert routes[1] == "as-is", routes
    # a register promote.py really promoted FROM this film still counts as built
    lib = open(os.path.join(_ROOT, "remotion", "LIBRARY.md"), encoding="utf-8").read()
    import re as _re
    m = _re.search(r"^\d+\. \*\*(\w+)\*\* — .*built for the film (.+?)\.?\s*$", lib, _re.M)
    assert m, "no promoted register in LIBRARY.md to test against"
    meta["title"] = m.group(2).strip()
    meta["build_list"][-1]["id"] = m.group(1)
    slides[0]["shot"] = m.group(1)
    routes = dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))
    assert routes[1] == "built", routes
    meta["title"] = "some other film"
    assert dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))[1] == "as-is"


def test_exemptions_are_decided_before_an_adaptation_note(tmp_path):
    # the finding: changes added to the opening/closing CinematicTitle lifted 3/8 to 5/10
    meta, slides = _film(tmp_path, "bsss")
    for k in (0, 3):
        slides[k] = {"index": k + 1, "shot": "CinematicTitle", "shot_props": {"title": "t"},
                     "shot_adaptation": {"changes": [dict(GOOD_CHANGE)]}, "shot_fit": {"ideal": IDEAL}}
    slides[1] = {"index": 2, "shot": "WsShotA", "shot_props": {},
                 "shot_fit": {"verdict": "build", "ref": "WsShotA", "ideal": IDEAL}}
    routes = [r for _n, r, _w in v.design_routes(meta, slides, str(tmp_path))]
    assert routes == ["exempt", "built", "as-is", "exempt"], routes


def test_an_adaptation_must_be_measurable_in_the_props(tmp_path):
    meta, slides = _film(tmp_path, "ba")
    assert dict((n, r) for n, r, _w in v.design_routes(meta, slides, str(tmp_path)))[2] == "adapted"
    slides[1]["shot_props"] = {"title": "t", "items": ["a", "b", "c"]}       # copy only: the note describes nothing
    route, why = [(r, w) for n, r, w in v.design_routes(meta, slides, str(tmp_path)) if n == 2][0]
    assert route == "as-is" and "links" in why, (route, why)
    # a register whose props are all copy cannot be adapted from the board
    slides[1]["shot"] = "CinematicTitle"
    route, why = [(r, w) for n, r, w in v.design_routes(meta, slides + [dict(slides[0], index=3)],
                                                         str(tmp_path)) if n == 2][0]
    assert route == "as-is" and "only copy" in why, (route, why)
    # a structure prop left at the register's own default is no change
    assert v._register_defaults("ObjectPath").get("route") == "line"
    assert v.structural_change("ObjectPath", {"route": "line"})[0] == []
    assert v.structural_change("ObjectPath", {"route": "arc"})[0] == ["route"]
    assert v.structural_change("EdCompare", {"framed": False})[0] == []          # a boolean default is read too
    assert v.structural_change("EdCompare", {"framed": True})[0] == ["framed"]


def test_an_all_exempt_film_still_needs_its_built_beat_and_routes_need_an_ideal(tmp_path):
    meta, slides = _film(tmp_path, "bb")
    slides[0] = {"index": 1, "shot": "CinematicTitle", "shot_props": {"title": "t"}}
    slides[1] = {"index": 2, "shot": "CinematicTitle", "shot_props": {"title": "t"}}
    meta["build_list"] = []
    errs, _ = _share(tmp_path, meta, slides)
    assert any("no beat is BUILT" in e for e in errs), errs
    meta, slides = _film(tmp_path, "ba")
    slides[1]["shot_fit"].pop("ideal")
    errs, _ = _share(tmp_path, meta, slides)
    assert any("record no `shot_fit.ideal`" in e for e in errs), errs
