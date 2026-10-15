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
    i_chk = skill.index("present the full, critic-reviewed script")
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


# ── the audition speaks through the FILM'S OWN path ────────────────────────────────────────────────────
# Found while moving the voice question to this checkpoint: the audition had its own copy of the voice
# logic, and the copy disagreed with the film in two audible ways. Every test below feeds it a board the
# copy got wrong.
import subprocess as _sp          # noqa: E402

import tts as _tts                # noqa: E402


def _tone(path):
    """A real, short, silent clip where an engine would have written one."""
    _sp.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.3",
             path], check=True)


def _write(tmp_path, meta, lines):
    board = {"meta": meta, "slides": [{"index": i, "narration": t} for i, t in enumerate(lines)]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")


_ZH = ["它用的AI很好，先说这一点。", "第二拍换个说法。", "第三拍再往前走一步。", "第四拍讲清楚原因。"]


def test_the_voice_hears_the_same_text_the_film_sends_it(tmp_path, monkeypatch):
    """A Chinese edge voice is sent "A-I", because it hesitates on a bare "AI" and the listener picked the
    hyphenated reading by ear. The copy sent the bare text — so the audition sounded unlike the film on
    exactly the word the listener had chosen."""
    heard = []
    monkeypatch.setattr(_tts, "_have_edge", lambda: True)
    monkeypatch.setattr(_tts, "_edge", lambda text, out, voice, rate="+0%": (heard.append(text), _tone(out)))
    _write(tmp_path, {"language": "zh", "voice": "auto"}, _ZH)
    sa.audition(str(tmp_path))
    first = next(t for t in heard if "很好" in t)
    assert "A-I" in first and "的AI" not in first, (
        "the audition sent %r — not the text the film's voice is sent" % first)


def test_an_unset_language_is_detected_as_the_film_detects_it(tmp_path, monkeypatch):
    """With `meta.language` unset the copy asked for a voice without detecting one and got the ENGLISH
    `say:Samantha` for a Chinese script, while the film detected zh and spoke edge Xiaoxiao."""
    voices = []
    monkeypatch.setattr(_tts, "_have_edge", lambda: True)
    monkeypatch.setattr(_tts, "_edge", lambda text, out, voice, rate="+0%": (voices.append(voice), _tone(out)))
    _write(tmp_path, {"voice": "auto"}, _ZH)
    _path, _picked, voice = sa.audition(str(tmp_path))
    assert voice.startswith("edge:zh-"), "a Chinese script with no language set auditioned in %r" % voice
    assert voices and all(v.startswith("zh-") for v in voices), voices


def test_offline_it_is_a_language_matched_say_voice_not_the_english_default(tmp_path, monkeypatch):
    """The other engine branch: no edge-tts, so `say` — and a Chinese script gets the Chinese `say`
    voice, the one `synthesize` resolves, not the English name the board's default spells."""
    used = []
    monkeypatch.setattr(_tts, "_have_edge", lambda: False)
    monkeypatch.setattr(_tts, "_say", lambda text, out, voice, rate=175: (used.append(voice), _tone(out)))
    _write(tmp_path, {"language": "zh", "voice": "say:Samantha"}, _ZH)
    sa.audition(str(tmp_path))
    want, _note = _tts._resolve_say_voice("Samantha", "zh")
    assert used and set(used) == {want}, "offline audition used %r; the film would use %r" % (used, want)


def test_a_paid_voice_is_not_spent_until_the_user_chose_it(tmp_path, monkeypatch):
    """The voice is now chosen AT this checkpoint, so a board that merely carries a paid voice (copied
    from another project, say) must not spend on the user's key before they pick it. Refused with nothing
    sent; spoken through the real engine once allowed."""
    calls = []
    monkeypatch.setattr(_tts, "_minimax", lambda text, out, voice, meta: (calls.append(text), _tone(out)))
    _write(tmp_path, {"language": "zh", "voice": "minimax:female-shaonv"}, _ZH)
    with pytest.raises(RuntimeError) as e:
        sa.audition(str(tmp_path))
    assert "--allow-paid" in str(e.value) and not calls, (str(e.value), calls)
    path, picked, voice = sa.audition(str(tmp_path), allow_paid=True)
    assert voice == "minimax:female-shaonv" and len(calls) == len(picked) and os.path.getsize(path) > 0


def test_an_engine_failure_is_reported_not_replaced(tmp_path, monkeypatch):
    """`synthesize` falls back to `say` so a film can finish. An audition that did the same would let
    someone approve a voice they will not get."""
    def boom(*_a, **_k):
        raise RuntimeError("network down")
    monkeypatch.setattr(_tts, "_have_edge", lambda: True)
    monkeypatch.setattr(_tts, "_edge", boom)
    monkeypatch.setattr(_tts, "_say", lambda *a, **k: pytest.fail("the audition fell back to say"))
    _write(tmp_path, {"language": "zh", "voice": "auto"}, _ZH)
    with pytest.raises(RuntimeError) as e:
        sa.audition(str(tmp_path))
    assert "network down" in str(e.value)


def test_there_is_one_voice_path_not_two():
    """The structural half: the audition must not grow its own copy again. It reaches the engines only
    through the two functions `synthesize` itself calls."""
    aud = open(os.path.join(_ROOT, "scripts", "script_audition.py"), encoding="utf-8").read()
    syn = open(os.path.join(_ROOT, "scripts", "tts.py"), encoding="utf-8").read()
    for private in ("_resolve_voice(", "_tts._edge(", "_tts._say(", "_tts._minimax(", "_tts._openai("):
        assert private not in aud, "script_audition calls %s directly — a second voice path" % private
    body = syn[syn.index("def synthesize("):]
    assert "film_voice(" in body and "speak(" in body, "synthesize no longer uses the shared path"


def test_a_malformed_lexicon_still_fails_loudly(tmp_path):
    """Moving the pronunciation layer inside the per-clip try would have let the say-fallback swallow an
    authoring error and voice every beat with `say`. It is checked before the loop."""
    _write(tmp_path, {"language": "zh", "voice": "say:Tingting", "tts_lexicon": ["AI", "A-I"]}, _ZH)
    with pytest.raises(ValueError):
        _tts.synthesize(str(tmp_path))


def test_it_names_a_beat_by_the_boards_own_index(tmp_path, monkeypatch, capsys):
    """Boards are numbered from 1 (`ingest.py` enumerates from 1) and `tts.py --only N` matches that
    number. The audition printed index + 1, so on a real board "beat 5 sounds off" pointed at slide 4 —
    found on the first real run of the rewritten audition, which printed beats 2-6 for slides 1-5."""
    monkeypatch.setattr(_tts, "_have_edge", lambda: True)
    monkeypatch.setattr(_tts, "_edge", lambda text, out, voice, rate="+0%": _tone(out))
    board = {"meta": {"language": "zh", "voice": "auto"},
             "slides": [{"index": i + 1, "narration": t} for i, t in enumerate(_ZH)]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["script_audition.py", str(tmp_path)])
    sa.main()
    shown = [int(l.split()[1]) for l in capsys.readouterr().out.splitlines() if l.strip().startswith("beat ")]
    assert shown and set(shown) <= {1, 2, 3, 4}, "the audition labels beats %r on a board numbered 1-4" % shown
    assert 1 in shown, "the first beat (the hook) is labelled %r" % shown
