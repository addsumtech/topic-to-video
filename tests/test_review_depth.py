"""The review depth the user chose after the first clean render (`meta.review = {tier, user_answer, preselected}`) is
honoured by the delivery gate, `critic_ledger.py --final` — and the floors do not move with it:

* `none` is only ever the user's own answer; a reviewing tier may be the pre-selected one applied without a reply;
  no recorded depth at all is refused at delivery ("ask the review question").
* A PASS covers only the render it saw. A ledger pinned to an EARLIER render is accepted only from a capped tier
  whose rounds are spent, on a REVISE whose every failed row is resolved — its fix applied in a later render, or
  accepted as-is by the USER (per finding, in their words). The model never declines; faithfulness is never accepted.
* The round is the render's place in the render history, never a field the ledger writes about itself.
* Every beat validate.py credits as ADAPTED or BUILT carries a route row: the critic saw the route in the frame."""
import json
import os
import subprocess
import sys
import time

from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import critic_ledger as cl  # noqa: E402

S3 = sorted(cl.never_accepted())[0]


def _sheet(out, colour):
    """A rebuilt contact sheet — always newer than the keyframes, as critic_brief.py leaves it."""
    p = os.path.join(out, cl.CONTACT_SHEET)
    Image.new("RGB", (64, 64), colour).save(p)
    later = time.time() + 1
    os.utime(p, (later, later))


def _out(tmp_path, review=None, slides=None, meta_extra=None):
    out = str(tmp_path)
    os.makedirs(os.path.join(out, "_keyframes"), exist_ok=True)
    Image.new("RGB", (32, 32), (200, 200, 200)).save(os.path.join(out, "_keyframes", "scene_01.png"))
    if not os.path.exists(os.path.join(out, cl.CONTACT_SHEET)):
        _sheet(out, (30, 40, 60))
    meta = {"renderer": "remotion"}
    if review is not None:
        meta["review"] = review
    meta.update(meta_extra or {})
    json.dump({"meta": meta, "slides": slides or []}, open(os.path.join(out, "storyboard.json"), "w"))
    return out


def _set_review(out, **fields):
    b = json.load(open(os.path.join(out, "storyboard.json")))
    b["meta"]["review"] = dict(b["meta"].get("review") or {}, **fields)
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))


def _cur(out):
    return cl.sha256_of(os.path.join(out, cl.CONTACT_SHEET))


def _ledger(out, **over):
    dims = [d for d, _ in cl.dimensions()]
    led = {"reviewer": "independent", "verdict": "PASS", "contact_sheet_sha256": _cur(out),
           "rows": [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_01.png"} for d in dims]}
    led.update(over)
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    return dims


def _brief(out):
    """critic_brief.py's side effect: the current render enters the history (one review round)."""
    cl.record_render(out)


def _rerender(out, colour=(90, 20, 20)):
    _sheet(out, colour)
    _brief(out)


def _revise(out, sid=None, pin=None, **row):
    dims = _ledger(out)
    led = json.load(open(os.path.join(out, cl.LEDGER_NAME)))
    led["verdict"] = "REVISE"
    sid = sid or dims[0]
    i = dims.index(sid)
    led["rows"][i] = dict({"id": sid, "verdict": "fail", "evidence": "_keyframes/scene_01.png",
                           "fix": "re-pick the beat"}, **row)
    if pin:
        led["contact_sheet_sha256"] = pin
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    return sid


# ── who decides the depth ───────────────────────────────────────────────────────────────────────────────

def test_none_is_never_inferred(tmp_path):
    sha = None
    for ans in ("", "<the user's words>", "default", "inferred", "no reply", "auto"):
        out = _out(tmp_path, {"tier": "none", "user_answer": ans})
        sha = _cur(out)
        _set_review(out, render_sha256=sha)
        errs = cl.validate(out, final=True)[0]
        assert any("not an answer" in e for e in errs), (ans, errs)
    out = _out(tmp_path, {"tier": "none", "user_answer": "none", "render_sha256": sha, "preselected": "none"})
    assert any("never pre-selected" in e for e in cl.validate(out, final=True)[0])


def test_no_recorded_depth_is_refused_at_delivery_not_run_as_thorough(tmp_path):
    out = _out(tmp_path)
    _brief(out)
    _ledger(out)
    assert not cl.validate(out)[0], "an interim run with no depth recorded is fine"
    errs = cl.validate(out, final=True)[0]
    assert any("review-depth question" in e for e in errs), errs
    p = subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    assert p.returncode == 1 and "review-depth question" in p.stdout, p.stdout


def test_a_preselected_reviewing_tier_applied_without_a_reply_is_valid(tmp_path):
    for tier in ("fast", "standard", "thorough"):
        out = _out(tmp_path, {"tier": tier, "user_answer": "no reply (auto mode)", "preselected": tier})
        _brief(out)
        _ledger(out)
        assert not cl.validate(out, final=True)[0], (tier, cl.validate(out, final=True)[0])
        # …but only as the PRE-SELECTED tier: a default answer naming another tier is nobody's choice
        _set_review(out, preselected="fast" if tier != "fast" else "standard")
        assert any("PRE-SELECTED" in e for e in cl.validate(out, final=True)[0]), tier


def test_none_answered_by_the_user_waives_this_render_only(tmp_path):
    out = _out(tmp_path)
    out = _out(tmp_path, {"tier": "none", "user_answer": "none", "render_sha256": _cur(out)})
    errs, warns = cl.validate(out, final=True)
    assert not errs and any("REVIEW WAIVED" in w for w in warns), (errs, warns)
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").write("# not yet\n")
    subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    nd = open(os.path.join(out, "NOT_DELIVERED.md")).read()
    assert "`meta.review` = `none`" in nd and "review_waiver" not in nd, nd
    _sheet(out, (1, 2, 3))
    errs = cl.validate(out, final=True)[0]
    assert any("DIFFERENT render" in e and "meta.review " in e for e in errs), errs


# ── the render pin ──────────────────────────────────────────────────────────────────────────────────────

def test_a_pass_must_be_on_the_current_render_even_when_the_cap_is_spent(tmp_path):
    # fast → render 1 PASS → the user asks for a change → re-render → briefed again → --final
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _brief(out)
    _ledger(out)
    assert not cl.validate(out, final=True)[0]
    old = _cur(out)
    _rerender(out)
    errs = cl.validate(out, final=True)[0]
    assert any("PASS reviewed an earlier render" in e for e in errs), errs
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").write("# not yet\n")
    p = subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    assert p.returncode == 1 and os.path.exists(os.path.join(out, "NOT_DELIVERED.md")), p.stdout
    assert old != _cur(out)


def test_a_rebuilt_film_with_a_stale_contact_sheet_is_refused(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _brief(out)
    _ledger(out)
    kf = os.path.join(out, "_keyframes", "scene_01.png")
    Image.new("RGB", (32, 32), (9, 9, 9)).save(kf)
    later = time.time() + 5
    os.utime(kf, (later, later))
    assert any("older than the keyframes" in e for e in cl.validate(out, final=True)[0])


# ── a capped tier's spent last round: the USER decides what is left ─────────────────────────────────────

def test_fast_ships_after_its_one_round_when_every_fix_was_applied(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _brief(out)
    reviewed = _cur(out)
    _revise(out)
    _rerender(out)
    _revise(out, pin=reviewed)
    errs = cl.validate(out, final=True)[0]
    assert any("unresolved" in e and "ONE MORE ROUND" in e for e in errs), errs
    _revise(out, pin=reviewed, applied="moved beat 3 to a built shot")
    errs, warns = cl.validate(out, final=True)
    assert not errs and any("round cap is spent" in w for w in warns), (errs, warns)
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").write("# not yet\n")
    subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    nd = open(os.path.join(out, "NOT_DELIVERED.md")).read()
    assert "not a PASS" in nd and "fix applied, not re-reviewed" in nd, nd


def test_the_model_may_not_decline_a_finding_the_user_may_accept_it(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _brief(out)
    sid = [d for d in [d for d, _ in cl.dimensions()] if d not in cl.never_accepted()][0]
    _revise(out, sid=sid, declined="it reads fine to me")
    errs = cl.validate(out, final=True)[0]
    assert any("may not decline" in e for e in errs), errs
    # the open finding goes back to the USER: an acceptance in their words, pinned to the reviewed render
    _revise(out, sid=sid)
    assert any("ACCEPT AS-IS" in e for e in cl.validate(out, final=True)[0])
    _set_review(out, accepted=[{"id": sid, "user_answer": "auto"}])
    assert any("no user answer" in e for e in cl.validate(out, final=True)[0])
    _set_review(out, accepted=[{"id": sid, "user_answer": "就这样，可以接受", "render_sha256": "0" * 64}])
    assert any("does not carry over" in e for e in cl.validate(out, final=True)[0])
    _set_review(out, accepted=[{"id": sid, "user_answer": "就这样，可以接受", "render_sha256": _cur(out)}])
    assert not cl.validate(out, final=True)[0], cl.validate(out, final=True)[0]
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").write("# not yet\n")
    subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    assert "ACCEPTED AS-IS by the user" in open(os.path.join(out, "NOT_DELIVERED.md")).read()


def test_a_faithfulness_finding_is_never_declined_or_accepted_only_fixed(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _brief(out)
    reviewed = _cur(out)
    _revise(out, sid=S3, declined="the number is close enough")
    assert any("may not decline" in e for e in cl.validate(out, final=True)[0])
    _revise(out, sid=S3)
    _set_review(out, accepted=[{"id": S3, "user_answer": "fine, ship it", "render_sha256": reviewed}])
    assert any("never accepted" in e for e in cl.validate(out, final=True)[0])
    _set_review(out, accepted=[])
    _revise(out, sid=S3, applied="replaced the figure with the sourced 41%")
    assert any("not fixed" in e for e in cl.validate(out, final=True)[0]), "applied on the current render"
    _rerender(out)
    _revise(out, sid=S3, pin=reviewed, applied="replaced the figure with the sourced 41%")
    assert not cl.validate(out, final=True)[0], cl.validate(out, final=True)[0]


# ── the round comes from the render history ─────────────────────────────────────────────────────────────

def test_the_round_is_derived_from_the_history_not_self_reported(tmp_path):
    out = _out(tmp_path, {"tier": "standard", "user_answer": "standard"})
    _brief(out)                                   # round 1
    r1 = _cur(out)
    assert cl.round_of(out, r1) == 1
    _revise(out, applied="x")
    led = json.load(open(os.path.join(out, cl.LEDGER_NAME)))
    led["round"] = 2                              # the old self-reported field, claiming the cap is spent
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    _rerender(out)                                # round 2 is briefed: it must be REVIEWED, not skipped
    led["contact_sheet_sha256"] = r1
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    errs, warns = cl.validate(out, final=True)
    assert any("rounds left" in e for e in errs), errs
    assert any("`round` field is ignored" in w for w in warns), warns
    assert cl.capped(out)[2:] == (1, False)
    # round 2's own review, then a re-render with its fixes: the cap is spent
    r2 = _cur(out)
    assert cl.round_of(out, r2) == 2
    _revise(out)
    _rerender(out, (5, 90, 5))
    _revise(out, pin=r2, applied="x")
    assert cl.capped(out)[2:] == (2, True)
    assert not cl.validate(out, final=True)[0], cl.validate(out, final=True)[0]
    # thorough never spends: a REVISE on an earlier render is refused
    out2 = _out(tmp_path / "t", {"tier": "thorough", "user_answer": "thorough"})
    _brief(out2)
    t1 = _cur(out2)
    _revise(out2, applied="x")
    _rerender(out2)
    _revise(out2, pin=t1, applied="x")
    assert any("rounds left" in e for e in cl.validate(out2, final=True)[0])


def test_a_render_briefed_before_the_depth_was_chosen_is_round_one_once_it_is(tmp_path):
    out = _out(tmp_path)
    _brief(out)                                   # briefed before the question was asked
    assert cl.round_of(out, _cur(out)) is None
    _set_review(out, tier="fast", user_answer="fast")
    _brief(out)
    assert cl.round_of(out, _cur(out)) == 1
    # the older history file (a sorted list of shas) still answers membership
    json.dump([_cur(out)], open(os.path.join(out, cl.HISTORY), "w"))
    assert _cur(out) in cl.history_shas(out) and cl.round_of(out, _cur(out)) is None


def test_the_tier_never_lowers_the_floors(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _brief(out)
    _revise(out, pin="0" * 64, applied="x")
    assert any("does not match" in e for e in cl.validate(out, final=True)[0])
    _ledger(out, reviewer="in-context")
    assert any("confirmation bias" in e for e in cl.validate(out, final=True)[0])
    # a FAIL row still needs its FIX on every tier
    _revise(out, fix="")
    assert any("no FIX" in e for e in cl.validate(out)[0])


# ── routes: the critic confirms in the frame what validate.py credits ───────────────────────────────────

def test_every_adapted_or_built_beat_needs_a_route_row(tmp_path):
    from test_design_first import _film
    meta, slides = _film(tmp_path, "ba")
    meta["design_dna"] = {"id": "x"}
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"}, slides=slides, meta_extra=meta)
    _brief(out)
    _ledger(out)
    errs = cl.validate(out)[0]
    assert any("`routes` is missing" in e for e in errs), errs
    tmpl = cl.template(out)
    assert [(r["beat"], r["route"]) for r in tmpl["routes"]] == [(1, "built"), (2, "adapted")]
    rows = [{"beat": 1, "route": "built", "visible": True, "evidence": "_keyframes/scene_01.png"},
            {"beat": 2, "route": "adapted", "visible": False, "evidence": "_keyframes/scene_01.png"}]
    _ledger(out, routes=rows)
    assert any("does not fail" in e for e in cl.validate(out)[0])
    rows[1]["visible"] = True
    _ledger(out, routes=rows[:1])
    assert any("beat #2" in e and "no route row" in e for e in cl.validate(out)[0])
    _ledger(out, routes=rows)
    assert not cl.validate(out)[0], cl.validate(out)[0]


def test_the_brief_tells_the_critic_the_fast_flow_and_the_routes_to_confirm(tmp_path, monkeypatch):
    import critic_brief
    from test_design_first import _film
    monkeypatch.setattr(critic_brief, "_run", lambda *a, **k: "(stubbed)")
    meta, slides = _film(tmp_path, "ba")
    out = _out(tmp_path, None, slides=slides, meta_extra=meta)
    text = critic_brief.build(out)
    assert "NOT RECORDED" in text and "review-depth question" in text
    assert "beat 1 · BUILT" in text and "beat 2 · ADAPTED" in text and "visible" in text
    _set_review(out, tier="fast", user_answer="fast")
    text = critic_brief.build(out)
    fast = text[text.index("**Review depth"):].split("\n")[0]
    assert "declined" not in fast and "never as a FAIL" in fast and "USER" in fast, fast
