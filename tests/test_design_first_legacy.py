"""A film made BEFORE the design-first rule (no beat carries `shot_fit.ideal`, out.mp4 older than the rule) gets a
user-decided path instead of a dead end: validate.py replaces the floor's errors with ONE that puts the choice to the
user, a keep is recorded as meta.design_first = {legacy, user_answer, out_mp4_mtime}, and then design-first is one
WARNING and the critic's route rows are not required. Auto mode cannot choose it; a film made under the rule cannot
claim it; and evidence that is missing says so plainly. Both tiers."""
import json
import os
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


def _since(tier):
    return v._ts(v.DESIGN_FIRST_SINCE[tier])


def _mp4(out, ts):
    p = os.path.join(out, "out.mp4")
    open(p, "wb").write(b"an old render")
    os.utime(p, (ts, ts))
    return v._iso(ts)


def _remotion(tmp_path, routes="xxxx"):
    meta, slides = rdf._film(tmp_path, routes)              # x = an as-is beat with no shot_fit at all
    return meta, slides, str(tmp_path)


def _html(tmp_path):
    meta, slides, out = hdf._film(tmp_path, [hdf.BESPOKE_STYLE, hdf.STOCK, hdf.STOCK, hdf.STOCK])
    meta["renderer"] = "local"
    return meta, slides, out


def _df(meta, slides, out, tier):
    errs, warns = [], []
    v._design_first(meta, slides, errs, warns, out, tier)
    return [e for e in errs if e.startswith("design-first")], [w for w in warns if w.startswith("design-first")]


def test_a_pre_rule_film_gets_one_question_instead_of_the_floor(tmp_path):
    for tier, build in (("remotion", _remotion), ("html", _html)):
        meta, slides, out = build(tmp_path / tier)
        floor, _ = _df(meta, slides, out, tier)
        assert len(floor) >= 2 and not any("LEGACY" in e for e in floor), (tier, floor)   # no out.mp4: the floor
        when = _mp4(out, _since(tier) - 10 * 86400)
        errs, warns = _df(meta, slides, out, tier)
        assert len(errs) == 1 and "LEGACY FILM" in errs[0], (tier, errs)
        assert "AskUserQuestion" in errs[0] and "KEEP ITS EXISTING DESIGN" in errs[0] and "BRING IT UP" in errs[0]
        assert '"out_mp4_mtime": "%s"' % when in errs[0], "the record to keep carries the evidence date"
        assert not warns


def test_the_users_keep_is_one_warning_and_survives_the_re_render(tmp_path):
    for tier, build in (("remotion", _remotion), ("html", _html)):
        meta, slides, out = build(tmp_path / tier)
        when = _mp4(out, _since(tier) - 10 * 86400)
        meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": KEEP, "out_mp4_mtime": when}
        errs, warns = _df(meta, slides, out, tier)
        assert not errs and len(warns) == 1 and "LEGACY film" in warns[0] and KEEP[:6] in warns[0], (tier, errs, warns)
        # the edit is rendered: out.mp4 is new now, and the recorded date is what still shows the film is old
        _mp4(out, time.time())
        errs, warns = _df(meta, slides, out, tier)
        assert not errs and len(warns) == 1 and ("first rendered %s" % when) in warns[0], (tier, errs, warns)


def test_a_keep_without_the_date_is_asked_for_the_date(tmp_path):
    meta, slides, out = _remotion(tmp_path)
    when = _mp4(out, _since("remotion") - 86400)
    meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": KEEP}
    errs, _ = _df(meta, slides, out, "remotion")
    assert len(errs) == 1 and "out_mp4_mtime is missing" in errs[0] and when in errs[0], errs


def test_auto_mode_cannot_choose_legacy(tmp_path):
    meta, slides, out = _remotion(tmp_path)
    when = _mp4(out, _since("remotion") - 86400)
    for ans in ("", "auto", "auto mode", "no reply", "default", "<what the user said>", "inferred"):
        meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": ans, "out_mp4_mtime": when}
        errs, warns = _df(meta, slides, out, "remotion")
        assert len(errs) == 1 and "records no user answer" in errs[0] and "AskUserQuestion" in errs[0], (ans, errs)
        assert not warns


def test_legacy_is_refused_on_a_film_that_is_not_pre_rule(tmp_path):
    meta, slides, out = _remotion(tmp_path / "a")
    _mp4(out, _since("remotion") - 86400)
    keep = {"legacy": True, "user_answer": KEEP, "out_mp4_mtime": v._iso(_since("remotion") - 86400)}
    # (1) a beat records an ideal: made (or brought up) under the rule
    slides[0]["shot_fit"] = dict(rdf.AS_IS_FIT)
    meta[v.LEGACY_KEY] = dict(keep)
    errs, _ = _df(meta, slides, out, "remotion")
    assert any("legacy is refused" in e and "record `shot_fit.ideal`" in e for e in errs), errs
    assert len(errs) >= 2, "the floor's own errors still apply when the claim is refused"
    # (2) out.mp4 written after the rule and no earlier date recorded — a copy without -p looks exactly like this
    meta, slides, out = _remotion(tmp_path / "b")
    _mp4(out, time.time())
    meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": KEEP}
    errs, _ = _df(meta, slides, out, "remotion")
    msg = [e for e in errs if "legacy is refused" in e]
    assert msg and "nothing shows this film predates the rule" in msg[0] and "cp -p" in msg[0] \
        and "touch -r" in msg[0], errs
    # (3) a recorded date that is after the rule is not evidence
    meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": KEEP, "out_mp4_mtime": v._iso(time.time())}
    assert any("is not evidence" in e for e in _df(meta, slides, out, "remotion")[0])
    # (4) no out.mp4 at all
    os.remove(os.path.join(out, "out.mp4"))
    meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": KEEP}
    assert any("there is no out.mp4" in e for e in _df(meta, slides, out, "remotion")[0])


def test_a_fresh_film_is_never_steered_to_legacy(tmp_path):
    """A film made under the rule that simply has not written its ideals yet gets the floor, word for word."""
    for tier, build in (("remotion", _remotion), ("html", _html)):
        meta, slides, out = build(tmp_path / tier)
        _mp4(out, time.time())
        errs, _ = _df(meta, slides, out, tier)
        floor = []
        (v._design_share if tier == "remotion" else v._html_design_share)(meta, slides, floor, [], out)
        assert errs == floor and not any("LEGACY" in e or "legacy" in e for e in errs), (tier, errs)


def test_the_critic_needs_no_route_rows_on_a_kept_legacy_film(tmp_path):
    from PIL import Image
    meta, slides, out = _html(tmp_path)
    json.dump({"meta": meta, "slides": slides}, open(os.path.join(out, "storyboard.json"), "w"))
    when = _mp4(out, _since("html") - 86400)
    assert cl._design_routes(out) == [(1, "bespoke")], "a credited page needs its route row on a normal film"
    meta[v.LEGACY_KEY] = {"legacy": True, "user_answer": KEEP, "out_mp4_mtime": when}
    json.dump({"meta": meta, "slides": slides}, open(os.path.join(out, "storyboard.json"), "w"))
    assert cl._design_routes(out) == []
    os.makedirs(os.path.join(out, "_keyframes"), exist_ok=True)
    Image.new("RGB", (32, 18), (1, 2, 3)).save(os.path.join(out, "_keyframes", "scene_01.png"))
    errs = v.evaluate({"meta": meta, "slides": slides}, out)["errors"]
    assert not [e for e in errs if e.startswith("design-first")], errs
