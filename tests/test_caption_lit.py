"""The spoken half of a caption takes the punctuation its words close with (remotion/src/captionBreak.ts `litThrough`).

THE DEFECT (fridge validation film, 2026-11-01). Film.tsx darkens what the voice has said and holds back what it has
not, cutting at the END of the last spoken word. Punctuation belongs to no word, so the mark after the final word —
「。」「？」 — stayed at the held-back opacity for the rest of the beat: every caption of the film ended on a dim mark,
on the settled frame, with every gate green. A mark that closes what was said is said; one that opens what is coming
(「“」「（」) is not.
"""
import json
import os

import pytest

import _tsprobe

_CB = json.dumps(os.path.join(os.path.dirname(_tsprobe.RUNTIME), "captionBreak.ts"))


@pytest.mark.skipif(not _tsprobe.available(), reason="node/esbuild not available")
def test_the_spoken_half_takes_the_marks_that_close_it():
    cap = "冰箱里面冰凉，背后怎么是热的？"
    out = _tsprobe.run_ts("import {litThrough} from %s;" % _CB,
                          "const c = %s;" % json.dumps(cap, ensure_ascii=False)
                          + "out.end = litThrough(c, c.length - 1); out.mid = litThrough(c, 6);"
                          + "out.word = litThrough(c, 3);"
                          + "const q = '它叫“汗”。下一句（括号）'; out.open = litThrough(q, 2); out.close = litThrough(q, 4);"
                          + "out.en = litThrough('Heat moves out. Then', 14); out.none = litThrough('abc', 3);")
    assert out["end"] == len(cap)          # 「？」 after the last word is lit with it
    assert out["mid"] == 7                 # 「，」 goes with 「冰凉」
    assert out["word"] == 3                # inside a run of words: unchanged
    assert out["open"] == 2                # an opening quote belongs to what comes
    assert out["close"] == 6               # 「”。」 close 「汗」
    assert out["en"] == 15 and out["none"] == 3
