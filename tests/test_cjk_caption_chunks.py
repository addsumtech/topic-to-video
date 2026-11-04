"""render.py's own caption chunks hold the CJK per-line ceiling validate gates, and follow the voice when it can.

The chunker budgeted 84 width-units a chunk, about 33 Han characters, which lays out as one ~30-character line at 16:9 —
and validate warns on any CJK caption line over 16 (CJK_CHARS_PER_LINE, the zh-Hans subtitle convention). Every CJK
film that left its captions to render tripped its own gate; a QR-code film (2026-11-04) authored every track by hand
instead. And the chunks were timed by length across the beat, so on a beat whose voice pauses a chunk showed seconds
before or after it was said, though the word times were on disk."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import render as rd  # noqa: E402
import validate  # noqa: E402

_ZH = ("二维码的每个模块都是一个比特，八个比特拼成一个码字，这些码字按照之字形的路线从右下角开始一路往上排列，"
       "读的时候扫描器也沿着同样的路线一格一格地读回来。")
_EN = ("Every module of the code is one bit, and eight bits make one codeword, laid out in a zigzag that starts "
       "in the bottom right corner and climbs the columns two at a time.")


def _han(s):
    return sum(1 for c in s if rd._CJK_RE.match(c))


def test_cjk_chunks_stay_within_the_per_line_ceiling():
    chunks = rd._split_caption_chunks(_ZH)
    assert chunks and all(_han(c) <= validate.CJK_CHARS_PER_LINE for c in chunks), chunks
    assert "".join(chunks).replace("，", "").replace("。", "") == _ZH.replace("，", "").replace("。", "")


def test_latin_chunks_keep_their_budget():
    assert rd._split_caption_chunks(_EN) == rd._split_caption_chunks(_EN, max_len=84)
    assert len(rd._split_caption_chunks(_EN)) <= 3


def _words(text, times):
    toks = [t for t in text.replace("，", " ").replace("。", " ").split() if t]
    return [{"w": w, "t": t} for w, t in zip(toks, times)]


def test_chunks_start_when_their_first_word_is_spoken():
    narr = "第一句话很短，然后停顿了很久很久。最后一句话。"
    words = _words("第一句话 很短 然后 停顿了 很久很久 最后 一句话", [0.1, 0.6, 1.2, 1.6, 2.0, 7.5, 8.0])
    slide = {"narration": narr, "duration": 9.0}
    segs = rd._captions_for(slide, words)
    assert [s["text"] for s in segs] == rd._split_caption_chunks(narr)
    last = segs[-1]
    assert last["text"].rstrip("。") == "最后一句话" and abs(last["start"] - 7.4) < 0.11, segs
    assert segs[0]["start"] == 0.0 and segs[-1]["end"] == 9.0
    assert all(a["end"] == b["start"] for a, b in zip(segs, segs[1:]))


def test_without_matching_words_chunks_fall_back_to_length_timing():
    narr = "第一句话很短，然后停顿了很久很久。最后一句话。"
    slide = {"narration": narr, "duration": 9.0}
    assert rd._captions_for(slide, [{"w": "unrelated", "t": 1.0}]) == rd._captions_for(slide)


def test_an_authored_track_still_wins():
    caps = [{"start": 0, "end": 1, "text": "a"}, {"start": 1, "end": 2, "text": "b"}]
    assert rd._captions_for({"narration": "x", "duration": 2, "captions": caps}, [{"w": "x", "t": 0}]) == caps
