"""The review depth the user chose after the first clean render (`meta.review = {tier, user_answer}`) is honoured
by the delivery gate, `critic_ledger.py --final` — and the floors do not move with it: `none` is only ever the
user's own answer, an unrecorded depth is the full loop, and a capped tier still needs a real, pinned ledger."""
import json
import os
import sys

from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import critic_ledger as cl  # noqa: E402


def _out(tmp_path, review=None):
    out = str(tmp_path)
    Image.new("RGB", (64, 64), (30, 40, 60)).save(os.path.join(out, cl.CONTACT_SHEET))
    os.makedirs(os.path.join(out, "_keyframes"), exist_ok=True)
    Image.new("RGB", (32, 32), (200, 200, 200)).save(os.path.join(out, "_keyframes", "scene_01.png"))
    meta = {"renderer": "remotion"}
    if review is not None:
        meta["review"] = review
    json.dump({"meta": meta, "slides": []}, open(os.path.join(out, "storyboard.json"), "w"))
    return out


def _ledger(out, **over):
    dims = [d for d, _ in cl.dimensions()]
    led = {"reviewer": "independent", "verdict": "PASS", "round": 1,
           "contact_sheet_sha256": cl.sha256_of(os.path.join(out, cl.CONTACT_SHEET)),
           "rows": [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_01.png"} for d in dims]}
    led.update(over)
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    return dims


def _rerender(out):
    """The fixes were applied and the film re-rendered: a new contact sheet, the old one in the history."""
    cl.record_render(out)
    Image.new("RGB", (64, 64), (90, 20, 20)).save(os.path.join(out, cl.CONTACT_SHEET))
    cl.record_render(out)


def _revise_round(out, **row):
    dims = _ledger(out)
    led = json.load(open(os.path.join(out, cl.LEDGER_NAME)))
    led["verdict"] = "REVISE"
    led["rows"][0] = dict({"id": dims[0], "verdict": "fail", "evidence": "_keyframes/scene_01.png",
                           "fix": "re-pick the beat"}, **row)
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))


def test_none_is_never_inferred(tmp_path):
    # no recorded depth → the full loop, never a waiver: no ledger is a refusal
    out = _out(tmp_path)
    assert cl.validate(out, final=True)[0]
    assert cl.capped(out)[0] == "thorough"
    # `none` with no answer, a placeholder, or a default marker is not the user's answer
    sha = cl.sha256_of(os.path.join(out, cl.CONTACT_SHEET))
    for ans in ("", "<the user's words>", "default", "inferred"):
        out = _out(tmp_path, {"tier": "none", "user_answer": ans, "render_sha256": sha})
        errs = cl.validate(out, final=True)[0]
        assert any("not an answer" in e for e in errs), (ans, errs)
    # `none` can never be the pre-selected option
    out = _out(tmp_path, {"tier": "none", "user_answer": "none", "render_sha256": sha, "preselected": "none"})
    assert any("never pre-selected" in e for e in cl.validate(out, final=True)[0])


def test_none_answered_by_the_user_waives_this_render_only(tmp_path):
    out = _out(tmp_path)
    sha = cl.sha256_of(os.path.join(out, cl.CONTACT_SHEET))
    out = _out(tmp_path, {"tier": "none", "user_answer": "none", "render_sha256": sha})
    errs, warns = cl.validate(out, final=True)
    assert not errs and any("REVIEW WAIVED" in w for w in warns), (errs, warns)
    Image.new("RGB", (64, 64), (1, 2, 3)).save(os.path.join(out, cl.CONTACT_SHEET))
    assert any("DIFFERENT render" in e for e in cl.validate(out, final=True)[0])


def test_fast_ships_after_its_one_round_with_the_fixes_recorded(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    _revise_round(out)
    _rerender(out)
    errs = cl.validate(out, final=True)[0]
    assert any("neither `applied`" in e for e in errs), errs          # the record must say what was done
    _revise_round(out, applied="moved beat 3 to a built shot")
    # _revise_round re-pinned to the CURRENT sheet; point it at the reviewed (earlier) render
    led = json.load(open(os.path.join(out, cl.LEDGER_NAME)))
    led["contact_sheet_sha256"] = sorted(cl._history(out) - {cl.sha256_of(os.path.join(out, cl.CONTACT_SHEET))})[0]
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    errs, warns = cl.validate(out, final=True)
    assert not errs and any("round cap is spent" in w for w in warns), (errs, warns)


def test_the_tier_never_lowers_the_floors(tmp_path):
    out = _out(tmp_path, {"tier": "fast", "user_answer": "fast"})
    # a pin to a render this film never had is refused, capped tier or not
    _revise_round(out, applied="x")
    led = json.load(open(os.path.join(out, cl.LEDGER_NAME)))
    led["contact_sheet_sha256"] = "0" * 64
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    assert any("does not match" in e for e in cl.validate(out, final=True)[0])
    # the maker's own review is still refused at delivery
    _ledger(out, reviewer="in-context")
    assert any("confirmation bias" in e for e in cl.validate(out, final=True)[0])
    # thorough (and standard before its 2nd round) keep the loop: a REVISE on an earlier render is refused
    for tier, rnd in (("thorough", 5), ("standard", 1)):
        out = _out(tmp_path, {"tier": tier, "user_answer": tier})
        _revise_round(out, applied="x")
        led = json.load(open(os.path.join(out, cl.LEDGER_NAME)))
        led["round"] = rnd
        json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
        _rerender(out)
        assert any("does not match" in e for e in cl.validate(out, final=True)[0]), tier
