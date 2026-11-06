"""A taught rule is ANSWERED before delivery (spec 2026-11-06 A3): critic_ledger --final refuses a film while an
active taste rule has no answer pinned to an artifact of this film, and a user waiver by name passes it."""
import hashlib
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import critic_ledger as cl  # noqa: E402
import taste_ledger as tl  # noqa: E402


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    p = tmp_path / "ledger.json"
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(p))
    return p


def _film(tmp_path, meta=None):
    d = tmp_path / "film"
    d.mkdir()
    (d / "storyboard.json").write_text(json.dumps({"meta": dict({"renderer": "remotion"}, **(meta or {})),
                                                   "slides": [{"index": 1, "shot": "X"}]}))
    (d / "_sketch_review.png").write_bytes(b"sheet")
    return str(d)


def _taste(errs):
    return [e for e in errs if "taste" in e.lower()]


def test_check_names_each_unanswered_active_rule(tmp_path, ledger):
    tl.add("每个元素1秒看懂", "every element decodable in ~1 s", "design")
    tl.add("x", "lining figures", "render", gate="validate lining")       # retired: never asked
    probs = tl.check(_film(tmp_path))
    assert len(probs) == 1 and "every-element-decodable" in probs[0]


def test_an_answer_must_pin_a_file_of_this_film(tmp_path, ledger):
    tl.add("每个元素1秒看懂", "every element decodable in ~1 s", "design")
    sha = hashlib.sha256(b"sheet").hexdigest()
    ok = _film(tmp_path, {"taste_review": {"every-element-decodable-in-1-s": {"answer": "checked", "sha256": sha}}})
    assert tl.check(ok) == []
    bad_dir = tmp_path / "b"
    bad_dir.mkdir()
    (bad_dir / "storyboard.json").write_text(json.dumps({"meta": {"taste_review": {
        "every-element-decodable-in-1-s": {"answer": "checked", "sha256": "0" * 64}}}, "slides": []}))
    assert any("no file" in p for p in tl.check(str(bad_dir)))


def test_final_refuses_an_unanswered_rule_and_a_waiver_by_name_passes(tmp_path, ledger):
    tl.add("每个元素1秒看懂", "every element decodable in ~1 s", "design")
    errs, _w = cl.validate(_film(tmp_path), final=True)
    assert _taste(errs)
    waived = tmp_path / "w"
    waived.mkdir()
    os.replace(str(tmp_path / "film"), str(waived / "film"))
    sb = waived / "film" / "storyboard.json"
    b = json.loads(sb.read_text())
    b["meta"]["delivery_waivers"] = {"taste_ledger": "the user watched it and accepts it"}
    sb.write_text(json.dumps(b))
    errs, warns = cl.validate(str(waived / "film"), final=True)
    assert not _taste(errs) and any("taste" in w.lower() for w in warns)


def test_interim_run_does_not_ask(tmp_path, ledger):
    tl.add("每个元素1秒看懂", "every element decodable in ~1 s", "design")
    errs, _w = cl.validate(_film(tmp_path), final=False)
    assert not _taste(errs)


def test_a_corrupt_ledger_is_a_final_error_naming_the_file(tmp_path, ledger):
    ledger.write_text("{nope")
    errs, _w = cl.validate(_film(tmp_path), final=True)
    assert any(str(ledger) in e for e in errs)


def test_promotion_of_a_delivered_film_does_not_reread_the_taste_ledger(tmp_path, ledger, monkeypatch):
    """Review I8: promote.user_waived calls critic_ledger.validate(final=True); a film the user shipped before a rule
    was taught would become unpromotable the moment any rule exists. Taste is asked at delivery, not at promotion."""
    tl.add("每个元素1秒看懂", "every element decodable in ~1 s", "design")
    monkeypatch.setattr(cl, "_validate", lambda d, final=False: ([], []))
    monkeypatch.setattr(cl, "waiver", lambda d: ({"reason": "r"}, []))
    monkeypatch.setattr(cl, "render_id", lambda d: "rid")
    import promote
    assert promote.user_waived(_film(tmp_path)) == "rid"
    errs, _w = cl.validate(str(tmp_path / "film"), final=True)
    assert _taste(errs)                                  # delivery still asks
