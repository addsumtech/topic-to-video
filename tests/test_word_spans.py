"""The voice's own word times, reaching the tier that never had them.

`tts.py` has written `audio/NN.words.json` since edge-tts was adopted, and only the html renderer ever read
it: the remotion caption advanced its chunks by CHARACTER PROPORTION of the beat — a guess that a short
clause and a long one are spoken at the same rate. They are not, so the caption drifts off the speech inside
a single beat, and the drift is largest exactly where the writing is most uneven.

The timing is carried as CHARACTER RANGES into the caption rather than word indices, because each tier
re-chunks the caption to fit its own band and an index into "word 3 of chunk 2" means something different
after every re-wrap.
"""
import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import cues                                   # noqa: E402
import render_remotion as rr                  # noqa: E402


def _w(pairs):
    return [{"w": w, "t": t} for w, t in pairs]


def test_it_locates_chinese_tokens_that_have_no_spaces_to_split_on():
    """The case that forced ranges in the first place: Chinese has no word separators, so a space-split index
    cannot exist, while edge-tts still emits one boundary per token."""
    cap = "它自主拆解任务，在你授权的目录里真正动文件。"
    spans = cues.word_spans(_w([("它", 0.0), ("自主", 0.25), ("拆解", 0.6), ("任务", 1.0),
                                ("在", 1.5), ("你", 1.7), ("授权", 1.95), ("的", 2.3),
                                ("目录", 2.5), ("里", 2.9), ("真正", 3.1), ("动", 3.5), ("文件", 3.7)]), cap)
    assert [cap[s["a"]:s["b"]] for s in spans][:4] == ["它", "自主", "拆解", "任务"]
    assert all(spans[i]["a"] < spans[i + 1]["a"] for i in range(len(spans) - 1)), "spans must run forward"
    assert all(spans[i]["t"] <= spans[i + 1]["t"] for i in range(len(spans) - 1)), "times must run forward"


def test_latin_goes_through_the_same_matcher():
    cap = "It plans the steps and calls the tools it needs."
    spans = cues.word_spans(_w([(w, i * 0.3) for i, w in enumerate(cap.rstrip(".").split())]), cap)
    assert [cap[s["a"]:s["b"]] for s in spans][:3] == ["It", "plans", "the"]


def test_a_token_the_voice_normalised_is_skipped_not_bound_to_a_later_twin():
    """edge speaks "1.5" as one point five and "$30" as thirty dollars, so some tokens are not in the caption
    at all. Binding one to a far-forward duplicate lights the wrong word early AND starves every token
    between, which is worse than dropping it: the highlight would run ahead of the voice for a whole clause."""
    cap = "the plan costs 30 and the plan ships today"
    spans = cues.word_spans(_w([("the", 0.0), ("plan", 0.2), ("costs", 0.4), ("thirty", 0.6),
                                ("and", 0.9), ("the", 1.1), ("plan", 1.3), ("ships", 1.5),
                                ("today", 1.8)]), cap)
    got = [(cap[s["a"]:s["b"]], s["t"]) for s in spans]
    assert ("thirty", 0.6) not in got, "a token absent from the caption must not be placed"
    plans = [s for s in spans if cap[s["a"]:s["b"]] == "plan"]
    assert len(plans) == 2 and plans[0]["a"] < plans[1]["a"], "the second 'plan' must not re-bind the first"


def test_it_says_nothing_rather_than_guess_when_the_words_do_not_match_the_caption():
    """A caption rewritten after the synth, or a provider that emits no boundaries. The caller falls back to
    the estimated timing; what it must never get is a list of confident times for the wrong words, because a
    caption lit on the wrong word is harder to notice than one that merely drifts."""
    assert cues.word_spans(_w([("completely", 0.0), ("different", 0.4)]), "这是另一段文案") == []
    assert cues.word_spans([], "anything") == []
    assert cues.word_spans(_w([("a", 0.0)]), "") == []


def test_the_renderer_attaches_them_when_they_exist_and_omits_them_when_they_do_not():
    """`say` and MiniMax emit no boundaries at all, so absent is the normal case and must stay silent."""
    cap = "It plans the steps and calls the tools."
    words = _w([(w, i * 0.3) for i, w in enumerate(cap.rstrip(".").split())])
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "audio"))
        with open(os.path.join(td, "audio", "01.words.json"), "w", encoding="utf-8") as fh:
            json.dump(words, fh)
        got = rr._caption_word_spans(td, "audio/01.mp3", cap)
        assert got and [cap[s["a"]:s["b"]] for s in got][:2] == ["It", "plans"]
        assert rr._caption_word_spans(td, "audio/02.mp3", cap) == [], "no sidecar -> no timing, not a crash"
        assert rr._caption_word_spans(td, "audio/01.mp3", "") == []
