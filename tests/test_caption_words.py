"""A caption line never breaks inside a number or a word — on either tier, by one definition.

THE DEFECT (validation films, 2026-10-31). The HTML tier wrapped Chinese between any two characters and hard-split a
long clause every N characters: 「正方 / 形」, 「四百 / 五十」 burned into a 1:1 film with every gate green (the tier had
no break gate). The Remotion tier breaks at Intl.Segmenter's words, and ICU cuts numerals — 负|四, 四百|五十, 两|万|八千
— so its gate read 「负 / 四」 as a word boundary and passed it.

THE RULES. remotion/src/captionGlue.json (number spans: prefix + numerals with joiners + unit), read by captionBreak.ts
`glueSpans` and scripts/caption_words.py `glue_spans`; words from ICU in both (the Python side runs it in plain node),
with ICU's one-character out-of-vocabulary fragments joined back for the BREAKER (黑|尔|斯, 正|多边|形). These tests
hold the two implementations to the same answers on one corpus in four scripts, sweep the measure, and keep the old
breaks as the gate's positive control.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import caption_breaks_qa as cbq  # noqa: E402
import caption_words as cw  # noqa: E402

needs_node = pytest.mark.skipif(not shutil.which("node") or not shutil.which("npx")
                                or not os.path.isdir(os.path.join(_ROOT, "remotion", "node_modules")),
                                reason="needs node and the remotion toolchain (esbuild)")
has_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node (Intl.Segmenter)")

CORPUS = [
    # zh — the validation films' own lines, and numbers in every shape
    "瑞士天文台认证要求：平均每天误差，在负四到正六秒之间。",
    "而蜜蜂要吃掉约三点八公斤蜂蜜，才能分泌出四百五十克蜡。",
    "能铺满平面的正多边形，只有三种：三角形、正方形、六边形。",
    "常见机芯每秒八拍，每小时两万八千八百拍，误差不超过百分之零点零一。",
    "一九九九年，黑尔斯证明了它；第三十二届会议在零下二十度召开，三十多岁的人来了十几个。",
    # ja
    "日本の人口は約一億二千万人で、東京タワーは三百三十三メートルです。",
    # en
    "The movement beats 28,800 times an hour, and a COSC chronometer may drift only -4 to +6 seconds a day.",
    "It weighs 3.8 kg, costs $1,299 and draws 45 W at 95% load.",
    # mixed
    "这块表每天误差 -4 到 +6 秒，相当于 99.99% 的精度，振频 4 Hz。",
    "iPhone 18 Pro 的屏幕是 1206×2622 像素，约 460 ppi。",
]


# ── the number rule, on its own ───────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text, spans", [
    ("在负四到正六秒之间", ["负四", "正六秒"]),
    ("才换来四百五十克蜡", ["四百五十克"]),
    ("约三点八公斤蜂蜜", ["约三点八公斤"]),
    ("每小时 28,800 拍", ["28,800 拍"]),
    ("It weighs 3.8 kg at 95% load", ["3.8 kg", "95%"]),
    ("約一億二千万人です", ["約一億二千万人"]),
    ("第三十二届，三十多岁，十几天", ["第三十二届", "三十多岁", "十几天"]),
    ("百分之零点零一", ["百分之零点零一"]),
])
def test_number_spans(text, spans):
    got = [text[a:b] for a, b in cw.glue_spans(text)]
    for s in spans:
        assert s in got, (text, got)


@pytest.mark.parametrize("text", ["统一的方法", "COVID cases", "a plain sentence", "三 men"])
def test_no_number_where_there_is_none_worth_holding(text):
    got = [text[a:b] for a, b in cw.glue_spans(text)]
    assert all(len(g) < 3 or any(c.isdigit() for c in g) for g in got), (text, got)


# ── the two implementations agree ─────────────────────────────────────────────────────────────────────────────
_PARITY_JS = r"""
const cb = require(process.argv[2]);
const texts = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
process.stdout.write(JSON.stringify(texts.map((t) => ({glue: cb.glueSpans(t), breaks: cb.breakPoints(t)}))));
"""


@needs_node
def test_python_and_typescript_draw_the_same_spans_and_breaks():
    with tempfile.TemporaryDirectory() as td:
        b = cbq._bundle(td)
        js = os.path.join(td, "p.cjs")
        open(js, "w", encoding="utf-8").write(_PARITY_JS)
        jf = os.path.join(td, "t.json")
        json.dump(CORPUS, open(jf, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run(["node", js, b["cb"], jf], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-600:]
        ts = json.loads(r.stdout)
    cw.prime(CORPUS)
    assert cw.backend()[0] == "icu"
    for t, got in zip(CORPUS, ts):
        assert [tuple(x) for x in got["glue"]] == cw.glue_spans(t), t
        assert got["breaks"] == cw.break_points(t), (t, got["breaks"], cw.break_points(t))


# ── the HTML tier's wrap and chunks ───────────────────────────────────────────────────────────────────────────
def _draw():
    from PIL import Image, ImageDraw
    import render as rd
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    return rd, d, rd._load_font(44, rd._font_path({}, "中文"))


@has_node
def test_the_html_wrap_never_breaks_inside_a_word_or_a_number_at_any_measure():
    """Every corpus line at every measure from 6 to 30 em: the lines render.py draws keep the text, and none of their
    breaks is inside a number or (ICU's) word. The old per-character wrap broke the validation film's lines."""
    rd, d, f = _draw()
    cw.prime(CORPUS)
    for t in CORPUS:
        for em in range(6, 31):
            lines = rd._wrap(d, t, f, em * 44)
            assert "".join(lines).replace(" ", "") == t.replace(" ", ""), (t, lines)
            bad = [x for x in cw.line_faults(lines, source=t) if x[1] in ("number", "split")]
            assert not bad, (t, em, lines, bad)


@has_node
def test_the_old_breaks_are_caught():
    """The positive control: the validation film's burned lines, as the old wrap drew them, are errors."""
    assert [k for _i, k, _t in cw.line_faults(["能铺满平面的正多边形，只有三种：三角形、正方", "形、六边形。"])] == ["split"]
    assert [k for _i, k, _t in cw.line_faults(["而蜜蜂要吃掉约三点八公斤蜂蜜，才能分泌出四百", "五十克蜡。"])] == ["number"]
    assert [k for _i, k, _t in cw.line_faults(["平均每天误差，在负", "四到正六秒之间。"])] == ["number"]
    assert [k for _i, k, _t in cw.line_faults(["It weighs 3.8", "kg at full load"])] == ["number"]
    assert cw.line_faults(["平均每天误差，", "在负四到正六秒之间。"]) == []


@has_node
def test_the_hard_wrap_cuts_a_long_clause_at_words_only():
    rd, _d, _f = _draw()
    s = "约三点八公斤蜂蜜才换来四百五十克蜡而且还要很多天"
    parts = rd._hardwrap(s, 24)
    assert "".join(parts) == s and len(parts) > 1
    for a, b in zip(parts, parts[1:]):
        assert cw.boundary_fault(a, b) is None, parts


@has_node
def test_the_html_gate_reads_a_films_chunks_and_lines(tmp_path):
    """caption_breaks_qa on an HTML film judges render.py's own chunks and lines: clean on the validation film's
    narration today."""
    board = {"meta": {"aspect": "1:1", "width": 1080, "height": 1080, "language": "zh", "captions": True},
             "slides": [{"index": 1, "type": "html", "props": {"html": "p.html"},
                         "narration": "能铺满平面的正多边形，只有三种：三角形、正方形、六边形。"},
                        {"index": 2, "type": "html", "props": {"html": "p.html"},
                         "narration": "边越短，越省蜡。而蜜蜂要吃掉约三点八公斤蜂蜜，才能分泌出四百五十克蜡。"}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    rep = cbq.check(str(tmp_path))
    assert rep["tier"] == "html" and rep["errors"] == [], rep


def test_without_node_numbers_still_hold_and_the_fallback_says_so(monkeypatch, capsys):
    monkeypatch.setattr(cw.shutil, "which", lambda _n: None)
    monkeypatch.setattr(cw, "_CACHE", {})
    monkeypatch.setattr(cw, "_BACKEND", {"name": None, "why": None})
    t = "才能分泌出四百五十克蜡"
    pts = cw.break_points(t)
    assert cw.backend() == ("per-character", "node is not installed")
    assert "no word segmenter" in capsys.readouterr().err
    a, b = cw.glue_spans(t)[0]
    assert not any(a < k < b for k in pts) and pts, pts
    # Korean keeps its spaces as its only boundaries
    assert cw.break_points("벌집 이야기를 합니다") == [3, 8]
