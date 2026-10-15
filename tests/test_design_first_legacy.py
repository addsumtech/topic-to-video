"""A film made BEFORE the design-first rule gets a user-decided path instead of a dead end — scoped to beats, and
proven by nothing the maker can set (no dates):

* a board where NO beat carries `shot_fit.ideal` gets ONE error that puts the choice to the user, instead of the floor;
* `validate.py <out_dir> --keep-design "<their words>"` records the keep for every beat on the board at that moment —
  refused for a non-answer and for a board where any beat already has an ideal;
* a kept beat (same number, same shot / page) is exempt; a beat added or changed later follows the per-beat rules, and
  those beats as a group carry the floor's share; a new beat that writes its ideal does NOT void the keep;
* the critic's route rows are required for the non-kept credited beats only, and delivery says what was kept.
Both tiers."""
import json
import os
import subprocess
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import critic_ledger as cl  # noqa: E402
import validate as v  # noqa: E402
import test_design_first as rdf  # noqa: E402
import test_html_design_first as hdf  # noqa: E402

KEEP = "保持原样，只改那一句旁白就行"
VALIDATE = os.path.join(_ROOT, "scripts", "validate.py")


def _save(out, meta, slides):
    json.dump({"meta": meta, "slides": slides}, open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False)


def _load(out):
    b = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    return b["meta"], b["slides"]


def _remotion(tmp_path, routes="xxxx"):
    meta, slides = rdf._film(tmp_path, routes)              # x = an as-is beat with no shot_fit at all
    out = str(tmp_path)
    _save(out, meta, slides)
    return out


def _html(tmp_path):
    meta, slides, out = hdf._film(tmp_path, [hdf.BESPOKE_STYLE, hdf.STOCK, hdf.STOCK, hdf.STOCK])
    meta["renderer"] = "local"
    _save(out, meta, slides)
    return out


def _df(out, tier):
    meta, slides = _load(out)
    errs, warns = [], []
    v._design_first(meta, slides, errs, warns, out, tier)
    return [e for e in errs if e.startswith("design-first")], [w for w in warns if w.startswith("design-first")]


def _add_beat(out, tier, adapted=False):
    """A beat added AFTER the keep — an as-is stock beat, or (adapted) one carrying its ideal and a route."""
    meta, slides = _load(out)
    n = len(slides) + 1
    if tier == "remotion":
        s = {"index": n, "shot": "KnowledgeGraph", "shot_props": {"title": "new"}}
        if adapted:
            s["shot_props"] = {"title": "t", "items": ["a", "b", "c"], "links": [[0, 1]]}
            s["shot_adaptation"] = {"changes": [dict(rdf.GOOD_CHANGE)]}
            s["shot_fit"] = {"verdict": "adapt", "why": "x", "ideal": rdf.IDEAL}
    else:
        rel = "pages/scene_%02d.html" % n
        open(os.path.join(out, rel), "w").write("<!doctype html><html><head></head><body>%s</body></html>"
                                                % (hdf.BESPOKE_STYLE if adapted else hdf.STOCK))
        s = {"index": n, "type": "html", "narration": "A sentence.", "duration": 5.0, "props": {"html": rel}}
        if adapted:
            s["shot_fit"] = {"ideal": hdf.SHARES["ideal"]}
    slides.append(s)
    _save(out, meta, slides)
    return n


def test_a_board_with_no_ideal_gets_one_question_whatever_its_dates(tmp_path):
    for tier, build in (("remotion", _remotion), ("html", _html)):
        out = build(tmp_path / tier)
        for when in (None, time.time() - 400 * 86400, time.time()):     # no out.mp4 / an old one / a fresh one
            if when is not None:
                open(os.path.join(out, "out.mp4"), "wb").write(b"x")
                os.utime(os.path.join(out, "out.mp4"), (when, when))
            errs, warns = _df(out, tier)
            assert len(errs) == 1 and "made BEFORE design-first" in errs[0], (tier, when, errs)
            assert "AskUserQuestion" in errs[0] and "--keep-design" in errs[0] and "KEEP ITS EXISTING DESIGN" in errs[0]
            assert not warns


def test_keep_design_is_the_users_and_only_on_a_board_with_no_ideal(tmp_path):
    out = _remotion(tmp_path / "r")
    before = open(os.path.join(out, "storyboard.json")).read()
    for ans in ("", "auto", "auto mode", "no reply", "default", "<what the user said>", "x"):
        ok, msg = v.keep_design(out, ans)
        assert not ok and "not the user's answer" in msg, (ans, msg)
    meta, slides = _load(out)
    slides[1]["shot_fit"] = dict(rdf.AS_IS_FIT)                       # one beat already has its ideal
    _save(out, meta, slides)
    ok, msg = v.keep_design(out, KEEP)
    assert not ok and "already record an ideal" in msg, msg
    restored = json.loads(before)
    _save(out, restored["meta"], restored["slides"])
    p = subprocess.run([sys.executable, VALIDATE, out, "--keep-design", "auto mode"], capture_output=True, text=True)
    assert p.returncode == 2 and "REFUSED" in p.stdout and "design_first" not in _load(out)[0], p.stdout
    p = subprocess.run([sys.executable, VALIDATE, out, "--keep-design", KEEP], capture_output=True, text=True)
    assert "recorded meta.design_first" in p.stdout, p.stdout
    rec = _load(out)[0]["design_first"]
    assert rec["legacy"] is True and rec["user_answer"] == KEEP
    assert rec["kept"] == [{"beat": i, "shot": "KnowledgeGraph"} for i in (1, 2, 3, 4)], rec
    # HTML: each kept beat is pinned to its page and scene type
    out = _html(tmp_path / "h")
    assert v.keep_design(out, KEEP)[0]
    assert _load(out)[0]["design_first"]["kept"][1] == {"beat": 2, "page": "pages/scene_02.html", "type": "html"}


def test_a_kept_film_is_one_warning_naming_the_beats(tmp_path):
    for tier, build in (("remotion", _remotion), ("html", _html)):
        out = build(tmp_path / tier)
        assert v.keep_design(out, KEEP)[0]
        errs, warns = _df(out, tier)
        assert not errs and len(warns) == 1, (tier, errs, warns)
        assert "kept by the user's decision" in warns[0] and "1, 2, 3, 4" in warns[0] and KEEP[:6] in warns[0]


def test_a_beat_added_after_the_keep_follows_the_rules_and_its_ideal_does_not_void_the_keep(tmp_path):
    for tier, build in (("remotion", _remotion), ("html", _html)):
        out = build(tmp_path / tier)
        assert v.keep_design(out, KEEP)[0]
        n = _add_beat(out, tier)                                    # a new STOCK beat, no ideal
        errs, warns = _df(out, tier)
        assert errs, (tier, "a new as-is beat with no ideal must not ride on the keep")
        share = [e for e in errs if "non-kept" in e]
        assert share and "a single new beat is adapted or built" in share[0], (tier, errs)
        assert any(("scene #%s" % n) in e and "shot_fit.ideal" in e for e in errs), (tier, errs)
        assert len(warns) == 1 and "1, 2, 3, 4" in warns[0], "the keep still holds for the beats it named"
        # the new beat does the right thing — its ideal and a route: the keep stands, nothing is left to fix
        meta, slides = _load(out)
        slides.pop()
        _save(out, meta, slides)
        _add_beat(out, tier, adapted=True)
        errs, warns = _df(out, tier)
        assert not errs and len(warns) == 1 and "kept by the user's decision" in warns[0], (tier, errs, warns)


def test_changing_a_kept_beats_shot_takes_it_out_of_the_keep(tmp_path):
    out = _remotion(tmp_path)
    assert v.keep_design(out, KEEP)[0]
    meta, slides = _load(out)
    slides[1]["shot"] = "QuadSplit"
    _save(out, meta, slides)
    errs, warns = _df(out, "remotion")
    assert any("scene #2" in e for e in errs), errs
    assert len(warns) == 1 and "no longer kept (changed or gone): 2" in warns[0] and "1, 3, 4" in warns[0], warns


def test_a_hand_written_keep_is_held_to_the_same_answer_rule(tmp_path):
    out = _remotion(tmp_path)
    meta, slides = _load(out)
    meta["design_first"] = {"legacy": True, "user_answer": "auto",
                            "kept": [{"beat": i, "shot": "KnowledgeGraph"} for i in (1, 2, 3, 4)]}
    _save(out, meta, slides)
    errs, _ = _df(out, "remotion")
    assert any("is not an answer" in e for e in errs), errs
    # a date record from the old design proves nothing and keeps nothing
    meta["design_first"] = {"legacy": True, "user_answer": KEEP, "out_mp4_mtime": "2026-10-01T00:00:00+02:00"}
    _save(out, meta, slides)
    errs, _ = _df(out, "remotion")
    assert any("must list the beats the user kept" in e for e in errs), errs


def test_a_fresh_film_with_ideals_gets_the_floor_word_for_word(tmp_path):
    out = _remotion(tmp_path, "bsss")                       # b carries an ideal, s carries ideal + shares
    meta, slides = _load(out)
    errs, _ = _df(out, "remotion")
    floor = []
    v._design_share(meta, slides, floor, [], out)
    assert errs == floor and not any("BEFORE design-first" in e for e in errs), errs


def test_route_rows_are_owed_for_the_beats_added_after_the_keep_only(tmp_path):
    from PIL import Image
    out = _html(tmp_path)
    assert cl._design_routes(out) == [(1, "bespoke")]
    assert v.keep_design(out, KEEP)[0]
    assert cl._design_routes(out) == []
    n = _add_beat(out, "html", adapted=True)
    assert cl._design_routes(out) == [(n, "bespoke")]
    # and delivery says what was kept
    os.makedirs(os.path.join(out, "_keyframes"), exist_ok=True)
    Image.new("RGB", (32, 18), (1, 2, 3)).save(os.path.join(out, "_keyframes", "scene_01.png"))
    assert "kept by the user's decision for beat(s) 1, 2, 3, 4" in cl.kept_line(out)


def test_a_keep_whose_every_beat_changed_says_so_and_holds_the_whole_film(tmp_path):
    out = _remotion(tmp_path)
    assert v.keep_design(out, KEEP)[0]
    meta, slides = _load(out)
    for s in slides:
        s["shot"] = "QuadSplit"
    _save(out, meta, slides)
    errs, warns = _df(out, "remotion")
    assert errs and any("none of them is on the board unchanged" in w for w in warns), (errs, warns)
    assert v._beat_order({10, 2, 1}) == [1, 2, 10]
