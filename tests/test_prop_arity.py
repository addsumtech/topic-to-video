"""A SLOT COUNT is part of a register's form, and the board must be held to it before anything renders.

THE EVIDENCE. Both halves of this defect have shipped here, and neither was caught by a board check:

  * `IsometricAssembly` declares `items?: [string, string, string]` and a fixture handed it FOUR. The
    fourth was dropped without a word. It surfaced only in the A4 campaign, because `cjk_type_qa` is the
    one audit that asks what a register DECLINED to draw — no gate on the board ever looked.
  * `AcceptanceStamp` demands exactly two conditions (a conjunction, not a list) and a real storyboard
    handed it three. That one is loud — the register throws — but it throws MID-RENDER, which on this
    machine cost a full bundle, a failed render, and an automatic retry without `--gl` before the reason
    was printed. `validate.py` had everything it needed to say so in a second.

The declaration already knew in both cases. Nothing read it.
"""
import os
import re
import sys

import demo_copy_qa as q
import validate as v

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(q.__file__)))
SHOTS = os.path.join(ROOT, "remotion", "src", "shots")


def _check(slides, arity):
    errors, warnings = [], []
    saved = v._ARITY_CACHE
    try:
        v._ARITY_CACHE = arity
        v._check_remotion({"renderer": "remotion"}, slides, errors, warnings)
    finally:
        v._ARITY_CACHE = saved
    return errors


def _beat(shot, props, index=1):
    return {"index": index, "shot": shot, "shot_props": props,
            "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"}}


def test_too_many_items_is_an_ERROR_on_the_board_not_a_surprise_at_render():
    errors = _check([_beat("AcceptanceStamp", {"conditions": ["a", "b", "c"]})], {"AcceptanceStamp": {"conditions": 2}})
    hit = [e for e in errors if "conditions" in e and "exactly 2" in e]
    assert hit, errors
    assert "supplies 3" in hit[0], "the error does not say what the board actually holds: %r" % hit[0]


def test_too_few_is_the_same_defect_read_from_the_other_side():
    errors = _check([_beat("IsometricAssembly", {"items": ["one", "two"]})], {"IsometricAssembly": {"items": 3}})
    assert [e for e in errors if "drawn empty" in e], errors


def test_a_correct_count_and_an_absent_prop_are_both_silent():
    """An absent prop renders the register's own default, which is a DIFFERENT finding (demo copy) with a
    different fix. Reporting it here would give one mistake two errors and neither of them the right one."""
    arity = {"IsometricAssembly": {"items": 3}}
    assert not _check([_beat("IsometricAssembly", {"items": ["a", "b", "c"]})], arity)
    # An omitted prop still has its OWN finding — the demo-copy error — and that one is correct. What must
    # not happen is this rule adding a second, wrong reading ("supplies 0") on top of it.
    absent = _check([_beat("IsometricAssembly", {"title": "x"})], arity)
    assert not [e for e in absent if "declared as exactly" in e or "must be a list" in e], absent
    assert [e for e in absent if "DEMO COPY" in e], "the absent prop lost its own finding: %r" % (absent,)


def test_a_non_list_is_reported_as_the_shape_error_it_is():
    errors = _check([_beat("PositioningMatrix", {"xAxis": "Simple to powerful"})], {"PositioningMatrix": {"xAxis": 2}})
    assert [e for e in errors if "must be a list of exactly 2" in e], errors


def test_the_real_library_still_declares_the_two_shapes_this_was_built_from():
    """Pinned against the registers themselves: if either declaration loosens, this test says so rather than
    the check quietly going silent on the two beats that produced it."""
    lib = q.arity_library(SHOTS)
    assert lib.get("IsometricAssembly", {}).get("items") == 3, lib.get("IsometricAssembly")
    assert lib.get("AcceptanceStamp", {}).get("conditions") == 2, (
        "AcceptanceStamp's type stopped fixing the count — its runtime still throws on anything but two, so "
        "the board check just went blind on the register that motivated it: %r" % (lib.get("AcceptanceStamp"),))


def test_the_declared_count_and_the_RUNTIME_guard_are_the_same_number():
    """Two copies of one rule is how the caption band became four disagreeing numbers in this repo. Here the
    type and the `throw` are necessarily two places, so they are pinned to each other."""
    src = open(os.path.join(SHOTS, "AcceptanceStamp.tsx"), encoding="utf-8").read()
    m = re.search(r"\.length\s*!==\s*(\d+)", src)
    assert m, "AcceptanceStamp no longer guards its own condition count at runtime"
    assert int(m.group(1)) == q.tuple_arity(src, "AcceptanceStamp")["conditions"], (
        "the type says %r and the runtime throws on %s" % (q.tuple_arity(src, "AcceptanceStamp"), m.group(1)))


def test_the_rule_is_parsed_not_listed():
    """The `NUM` map in validate.py is the cautionary tale it cites itself: a restated list of registers went
    stale and left two number-bearing registers exempt."""
    src = open(v.__file__, encoding="utf-8").read()
    fn = src.split("def _arity_library():")[1].split("\ndef ")[0]
    for name in ("IsometricAssembly", "AcceptanceStamp", "PositioningMatrix"):
        assert name not in fn, "_arity_library hardcodes %r instead of parsing the registers" % name


def test_it_stays_silent_when_the_parser_is_unavailable():
    """A checker that cannot read the registers must skip, not flag every beat. The import is wrapped for
    exactly this, and the wrapper is the kind of line that gets 'cleaned up'."""
    fn = open(v.__file__, encoding="utf-8").read().split("def _arity_library():")[1].split("\ndef ")[0]
    assert "except Exception" in fn and "= {}" in fn, fn
