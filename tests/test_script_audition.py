"""The script must be HEARD before it is approved, on either tier.

Every voice check in this pipeline reads. The defect that motivated this one is audible: a 37-beat film
cleared sentence-length CV, antithesis, connectives, aphorism endings and balanced pairs, passed two
independent content critics, was read end-to-end by its author, and the person it was made for said on
the first listen 「脚本没有人的感觉，读起来也很机器」. `references/anti-ai-voice.md` had opened with "the
last pass is always a human read-aloud" since before that film, and the workflow's own instruction was
"do not synthesize audio until they sign off" — so the sign-off was a READING of a document whose only
destiny is to be heard.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import script_audition as sa          # noqa: E402


def _board(n, marks=None):
    marks, sl = marks or {}, []
    for i in range(n):
        s = {"index": i, "narration": "第 %d 拍，这里说一句话。" % (i + 1)}
        s.update(marks.get(i, {}))
        sl.append(s)
    return {"meta": {"language": "zh", "voice": "auto"}, "slides": sl}


def test_it_picks_the_beats_a_listener_judges_the_film_by():
    b = _board(37, {12: {"climax": True}, 36: {"hold": True}})
    got = [i for i, _ in sa.pick(b["slides"])]
    assert 0 in got, "the hook is not auditioned — the first beat is the one that decides if anyone stays"
    assert 12 in got, "the climax is not auditioned"
    assert 36 in got, "the close is not auditioned"
    assert len(got) == sa.AUDITION_BEATS


def test_it_includes_consecutive_beats_because_a_habit_needs_two_in_a_row():
    """One beat in a shape sounds fine; the tell is the SECOND one. A picker that spreads evenly across
    the film would never put two neighbours together and would miss exactly the defect this catches."""
    got = sorted(i for i, _ in sa.pick(_board(37, {12: {"climax": True}, 36: {"hold": True}})["slides"]))
    assert any(b - a == 1 for a, b in zip(got, got[1:])), (
        "no two auditioned beats are adjacent, so a repeated opener is never heard twice: %r" % got)


def test_a_short_board_auditions_everything_rather_than_guessing():
    assert len(sa.pick(_board(3)["slides"])) == 3


def test_a_beat_with_no_narration_is_never_auditioned_as_silence():
    b = _board(6)
    b["slides"][2]["narration"] = "   "
    assert all(t.strip() for _i, t in sa.pick(b["slides"]))


def test_it_refuses_rather_than_returning_a_silent_file(tmp_path):
    """A checkpoint that passes on silence is the defect this script exists to prevent."""
    board = {"meta": {"language": "zh", "voice": "openai:nova"}, "slides": [
        {"index": i, "narration": "一句话。"} for i in range(4)]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(RuntimeError) as e:
        sa.audition(str(tmp_path))
    assert "nobody heard" in str(e.value) or "do NOT approve" in str(e.value).lower() or "audition" in str(e.value)


def test_it_reads_only_what_BOTH_tiers_carry():
    """Tier-agnostic by construction: an html board has no `shot`, a remotion board has no `page`, and
    this must work on either. It may read narration, meta.voice and the climax/hold marks — nothing else."""
    src = open(os.path.join(_ROOT, "scripts", "script_audition.py"), encoding="utf-8").read()
    for tier_only in ('"shot"', "'shot'", '"page"', "'page'", "shot_props", "registry", "renderer"):
        assert tier_only not in src, (
            "script_audition reads %s, so it is not tier-agnostic and the html branch loses the one "
            "check that can hear" % tier_only)


def test_the_workflow_requires_it_before_the_script_checkpoint():
    """A capability nothing calls is indistinguishable from an absent one — the failure this repo keeps
    finding. The instruction it replaces actively FORBADE audio before the sign-off."""
    skill = open(os.path.join(_ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "script_audition.py" in skill, "the workflow never tells anyone to run the audition"
    i_aud = skill.index("script_audition.py")
    i_chk = skill.index("present the full, critic-panel-passed script")
    assert i_aud < i_chk, "the audition is mentioned AFTER the checkpoint it is supposed to inform"
    # The rule is that the workflow no longer PRESCRIBES silence before the sign-off — not that the
    # words never appear. This file's own explanation of what changed quotes the old instruction, and a
    # test pinned to the string failed on that quotation: a rule pinned to text rather than to behaviour.
    prescribes = [l for l in skill.splitlines()
                  if "synthesize audio until" in l and "old instruction" not in l]
    assert not prescribes, (
        "the workflow still instructs the reader not to make audio before the sign-off, so the "
        "checkpoint stays a reading: %r" % prescribes)


def test_voice_qa_says_out_loud_that_it_cannot_hear():
    """A clean voice_qa run is exactly when it gets mistaken for 'the voice has been checked'."""
    import voice_qa as v
    assert "deaf" in v._MSG and {"zh", "en"} <= set(v._MSG["deaf"])
    r = v.evaluate([(i, "这一拍说一句自然的话，长短不一，带点连接词。") for i in range(8)])
    joined = " ".join(r.get("notes") or [])
    assert "script_audition" in joined, "a clean run does not point at the check that can actually hear"
