"""CJK caption line breaks: at word boundaries, never in front of closing punctuation, never ending on one glyph.

The caption HUD let the browser wrap Chinese, which breaks between ANY two characters: two 2026-10-24 benchmark films
burned 「交回成 / 片」, 「GPS 怎么 / 定位」, 「抓下 / 来的原文」 and 「…加速电 / 子。」, and nothing but a reviewer's eye saw
them. Film.tsx now draws a CJK caption in the lines `remotion/src/captionBreak.ts` decides, and
`scripts/caption_breaks_qa.py` runs the same file in node — these tests run it there too (no render).
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

import caption_breaks_qa as cbq

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
FILM = open(os.path.join(_ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
needs_node = pytest.mark.skipif(not shutil.which("node") or not shutil.which("npx")
                                or not os.path.isdir(os.path.join(_ROOT, "remotion", "node_modules")),
                                reason="needs node and the remotion toolchain (esbuild)")

_JS = r"""
const cb = require(process.argv[2]);
const job = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const adv = (c) => (/[　-〿㐀-鿿豈-﫿぀-ヿ가-힯＀-￯]/.test(c) ? 1 : 0.5);
const out = {seg: cb.hasSegmenter(), lines: job.lines.map(([t, m]) => cb.breakLines(t, m, adv)),
             faults: job.faults.map((ls) => cb.lineFaults(ls))};
process.stdout.write(JSON.stringify(out));
"""


def _node(lines=(), faults=()):
    with tempfile.TemporaryDirectory() as td:
        b = cbq._bundle(td)
        js = os.path.join(td, "t.cjs")
        open(js, "w", encoding="utf-8").write(_JS)
        jf = os.path.join(td, "j.json")
        json.dump({"lines": list(lines), "faults": list(faults)}, open(jf, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run(["node", js, b["cb"], jf], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-600:]
        return json.loads(r.stdout)


def _greedy_chars(text, measure):
    """What the browser did: fill each line character by character (CJK one unit, Latin half), breaking anywhere."""
    lines, cur, w = [], "", 0.0
    for ch in text:
        a = 0.5 if ch.isascii() else 1.0
        if cur and w + a > measure:
            lines.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += a
    return lines + ([cur] if cur else [])


@needs_node
def test_the_benchmark_captions_break_at_words_and_the_old_wrap_is_caught():
    caps = [("查资料、写稿、配音，交回成片。", 11), ("只给它一个题目：GPS 怎么定位。", 10),
            ("太阳风里的带电粒子沿着磁力线漏斗般地落下，再在尾巴里加速电子。", 15),
            ("造出来的，遮住字幕也要讲得明白。", 12)]
    old = [_greedy_chars(t, m) for t, m in caps]
    res = _node(lines=caps, faults=old + [[] for _ in caps])
    assert res["seg"], "Intl.Segmenter is missing from this node — the words cannot be found"
    new = res["lines"]
    # the positive control: the browser's old character wrap of these same captions IS caught
    caught = [f for f in res["faults"][:len(caps)] if f]
    assert caught, "the gate's fault check does not see the old wrap: %r" % old
    again = _node(faults=new)["faults"]
    assert all(not f for f in again), list(zip(new, again))
    for (t, m), ls in zip(caps, new):
        assert "".join(ls).replace(" ", "") == t.replace(" ", ""), (t, ls)      # nothing lost, nothing added
        assert all(sum(0.5 if c.isascii() else 1.0 for c in ln.strip()) <= m + 1e-9 for ln in ls), (m, ls)
    assert new[0] == ["查资料、写稿、", "配音，交回成片。"], new[0]                 # after a clause, not 交回成/片
    assert new[3] == ["造出来的，", "遮住字幕也要讲得明白。"], new[3]


@needs_node
def test_each_fault_kind_is_reported():
    f = _node(faults=[["交回成", "片。"], ["再在尾巴里加速电", "子。"], ["你好", "。世界"], ["The quick brown", "fox jumps"]])
    kinds = [sorted({x["kind"] for x in r}) for r in f["faults"]]
    assert kinds[0] == ["orphan"], kinds
    assert kinds[1] == ["orphan", "split"], kinds            # 电子 is one word
    assert kinds[2] == ["kinsoku"], kinds
    assert kinds[3] == [], "a Latin line break at a space is not a split"


@needs_node
def test_no_scrap_line_and_latin_is_left_to_the_browser_s_spaces():
    res = _node(lines=[("好，我们今天来讨论一下这个非常重要的问题。", 12), ("Every frame was drawn by code.", 8),
                       ("短句。", 10)])
    a, b, c = res["lines"]
    assert a[0] != "好，", "a two-glyph first line is a scrap, not a clause"
    assert all(" " not in ln.strip()[:0] for ln in b) and " ".join(b) == "Every frame was drawn by code.", b
    assert c == ["短句。"]


@needs_node
def test_the_gate_reads_the_film_and_skips_a_film_without_captions(tmp_path):
    caps = ["只给它一个题目：GPS 怎么定位。", "查资料、写稿、配音，交回成片。", "Every frame was drawn by code."]
    b = {"meta": {"renderer": "remotion", "aspect": "9:16", "design_dna": "product"},
         "slides": [{"shot": "MapPlate", "narration": c} for c in caps]}
    json.dump(b, open(tmp_path / "storyboard.json", "w"), ensure_ascii=False)
    rep = cbq.check(str(tmp_path))
    assert rep["skipped"] is None and rep["frame"] == [1080, 1920] and rep["safe"] == "social"
    assert not rep["errors"], rep["errors"]
    lines = [c["lines"] for bb in rep["beats"] for c in bb["chunks"]]
    assert lines[1] == ["查资料、写稿、", "配音，交回成片。"] and lines[2] is None, lines
    assert cbq.main([str(tmp_path)]) == 0
    b["meta"]["captions"] = False
    json.dump(b, open(tmp_path / "storyboard.json", "w"), ensure_ascii=False)
    assert cbq.check(str(tmp_path))["skipped"] == "captions are off"


@needs_node
def test_srt_cues_are_broken_at_words_within_sixteen_glyphs():
    out = cbq.srt_lines(["太阳风里的带电粒子沿着磁力线漏斗般地落下，再在尾巴里加速电子。", "Every frame was drawn by code."])
    zh, en = out
    assert len(zh) == 2 and all(len(x) <= 16 for x in zh) and "".join(zh) == "太阳风里的带电粒子沿着磁力线漏斗般地落下，再在尾巴里加速电子。", zh
    assert en == ["Every frame was drawn by code."]


def test_the_film_draws_the_lines_the_gate_checks():
    """One definition: the HUD's chunks and a CJK chunk's lines come from captionBreak.ts, which the gate runs."""
    assert "from './captionBreak'" in FILM
    for fn in ("splitCaption(", "fitCaption(", "cjkCaptionLines(", "captionBox("):
        assert fn in FILM, fn
    assert "const splitCaption" not in FILM and "const fitCaption" not in FILM, "a second copy in Film.tsx"
