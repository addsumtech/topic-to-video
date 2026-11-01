"""Focus plan — which listed item LEADS the frame while the voice talks about it (scripts/focus_plan.py).

WHY. craft_qa measured our beats letting several equal elements share the frame: the largest element held 48% of the
layout against 63% on 28 published launch films, with 3 elements against 2, and 116 of 311 beats had no element
leading at all (under 50% among 4 or more). Most of them are lists — callouts, steps, rows, parts — where every item is
drawn at the same weight for the whole beat while the voice talks about one of them at a time. The plan says which
one, from the narration: the item a clause names leads and keeps the lead through the rest of its sentence (「热水从这里
洒下」 is still about the 分水网 it follows); another named item takes it over; and once a sentence has ended, a clause
that names none gives the frame back to all of them. A lead that flickered off on every unnamed clause would be the
pumping it exists to replace.
"""
import pytest

import focus_plan as fp


def _spans(text, times):
    out, i = [], 0
    toks = [c for c in text if not c.isspace() and c not in "，。、；：！？,.;:!?"]
    assert len(toks) == len(times), (len(toks), len(times))
    for c, t in zip(toks, times):
        a = text.index(c, i)
        out.append({"t": t, "a": a, "b": a + 1})
        i = a + 1
    return out


CAP = "先看分水网，热水从这里洒下；再看粉饼，它被压得很实；最后是滤网，咖啡从它流出。"
PROPS = {"parts": [{"label": "分水网"}, {"label": "粉饼"}, {"label": "滤网"}], "kicker": "第三步 加压"}


def _timed():
    n = len([c for c in CAP if not c.isspace() and c not in "，。、；：！？"])
    return _spans(CAP, [0.25 * k for k in range(n)])


def test_each_clause_hands_the_lead_to_the_item_it_names():
    plan = fp.focus_plan(PROPS, _timed(), CAP, duration=10.0)
    assert [p["key"] for p in plan] == ["parts.0", "parts.1", "parts.2"], plan
    times = [p["t"] for p in plan]
    assert times == sorted(times) and times[0] == 0.0


def test_after_a_sentence_ends_a_clause_that_names_nothing_gives_the_frame_back():
    cap = "先看分水网，热水从这里洒下。另外，机器还要预热。"
    n = len([c for c in cap if c not in "，。"])
    plan = fp.focus_plan(PROPS, _spans(cap, [0.25 * k for k in range(n)]), cap, duration=6.0)
    assert [p["key"] for p in plan] == ["parts.0", None], plan
    assert plan[1]["t"] == 0.25 * len("先看分水网热水从这里洒下")


def test_only_a_list_of_two_or_more_items_is_focused():
    props = {"title": "分水网", "caption": "粉饼"}
    assert fp.focus_plan(props, _timed(), CAP, duration=10.0) == []
    one = {"parts": [{"label": "分水网"}]}
    assert fp.focus_plan(one, _timed(), CAP, duration=10.0) == []


def test_no_word_times_no_plan():
    assert fp.focus_plan(PROPS, [], CAP, duration=10.0) == []


def test_items_text_is_handed_over_for_the_runtime_to_find():
    texts = fp.item_texts_for_focus(PROPS)
    assert texts == {"parts.0": "分水网", "parts.1": "粉饼", "parts.2": "滤网"}


def test_latin_items_match_words():
    cap = "First the boiler heats the water, then the pump pushes it, and finally the basket holds the coffee."
    words = cap.replace(",", "").replace(".", "").split()
    spans, i = [], 0
    for k, w in enumerate(words):
        a = cap.index(w, i)
        spans.append({"t": 0.35 * k, "a": a, "b": a + len(w)})
        i = a + len(w)
    props = {"steps": ["Boiler", "Pump", "Basket"]}
    plan = fp.focus_plan(props, spans, cap, duration=9.0)
    assert [p["key"] for p in plan if p["key"]] == ["steps.0", "steps.1", "steps.2"], plan


@pytest.mark.parametrize("props", [
    {"lines": ["太阳风送来能量，", "磁场指路，", "*氧和氮发光。*"]},          # a sentence set as lines of type
    {"tokens": ["How", " chat", "bot"]},                                  # the narration's own tokens
    {"items": ["先看分水网，", "再看粉饼，", "最后是滤网。"]},                # fragments, whatever the prop is called
])
def test_a_sentence_broken_into_lines_is_not_a_list_of_peers(props):
    """Measured on our corpus: HeadlineReveal/SkyPlate set one sentence as `lines`, TokenStrip the narration's own
    tokens. Dimming the half of a headline the voice has passed breaks the one thing a headline is — read whole."""
    assert fp.item_texts_for_focus(props) == {}


def test_the_runtime_weights_hand_the_lead_over_smoothly_and_rest():
    import _tsprobe
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    out = _tsprobe.run_ts("import {focusWeights, FOCUS_EASE_S} from %s;" % _tsprobe.mod("focusLead.tsx"),
                          "const plan = [{t: 1, key: 'a'}, {t: 3, key: 'b'}, {t: 5, key: null}];"
                          "out.e = FOCUS_EASE_S;"
                          "out.w = [0.5, 1.0, 1.2, 2.0, 3.0, 3.1, 4.0, 5.0, 6.0].map((t) => focusWeights(plan, ['a','b','c'], t));")
    w = out["w"]
    assert w[0] == {"a": 1, "b": 1, "c": 1}                                   # before anyone is named
    assert w[3] == {"a": 1, "b": 0, "c": 0}                                   # a leads, at rest
    assert 0 < w[2]["b"] < 1                                                  # receding, eased
    assert w[6] == {"a": 0, "b": 1, "c": 0}                                   # handed to b
    assert 0 < w[5]["a"] < 1 and 0 < w[5]["b"] < 1                            # mid hand-over
    assert w[8] == {"a": 1, "b": 1, "c": 1}                                   # given back to all


def _focus_board(tmp_path):
    import json
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg needed for the audio stub")
    (tmp_path / "audio").mkdir()
    cap = "先看分水网，热水从这里洒下；再看粉饼，它被压得很实；最后是滤网，咖啡从它流出。"
    spoken = [c for c in cap if c not in "，。；"]
    slides = []
    for i, props in enumerate([PROPS, {"rows": [["a", "1"]]}]):
        a = tmp_path / "audio" / ("%02d.wav" % (i + 1))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "10",
                        str(a)], check=True)
        (tmp_path / "audio" / ("%02d.words.json" % (i + 1))).write_text(
            json.dumps([{"w": c, "t": round(0.25 * k, 3)} for k, c in enumerate(spoken)], ensure_ascii=False))
        slides.append({"index": i + 1, "shot": "TechnicalPlate" if i == 0 else "TermTable", "duration": 10.0,
                       "narration": cap, "caption": cap, "audio": "audio/%02d.wav" % (i + 1), "shot_props": props})
    board = {"meta": {"renderer": "remotion", "aspect": "16:9"}, "slides": slides}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False))
    return board


def test_a_listed_beat_gets_a_focus_plan(tmp_path):
    """The lead changing hands IS the beat's event — nothing moves, so no type is re-positioned. (Camera steps on the
    same TechnicalPlate made its 1-5 callout digits tremble 0.19-0.22 px, as a scale and as a travel.)"""
    import render_remotion as rr
    props, _ = rr.film_props(str(tmp_path), _focus_board(tmp_path))
    a, b = props["scenes"]
    assert [p["key"] for p in a["focus"]] == ["parts.0", "parts.1", "parts.2"], a.get("focus")
    assert a["focusItems"] == {"parts.0": "分水网", "parts.1": "粉饼", "parts.2": "滤网"}
    assert "phrase" not in a and "phrase" not in b              # nobody asked for a camera: no steps
    assert "focus" not in b


def test_focus_is_off_where_the_camera_steps_are(tmp_path):
    import json
    import render_remotion as rr
    board = _focus_board(tmp_path)
    board["meta"]["phrase_camera"] = False
    props, _ = rr.film_props(str(tmp_path), board)
    assert not any("focus" in s for s in props["scenes"])
    board["meta"]["phrase_camera"] = True
    props, _ = rr.film_props(str(tmp_path), board, reduced_motion=True)
    assert not any("focus" in s for s in props["scenes"])


def test_a_list_read_out_fast_is_not_handed_round():
    """Measured on bench-rams: TuningScale's five principles named 0.8 s apart; the lead hopped every 0.8 s, which reads
    as flicker, not as attention — and jitter_qa caught a station number in it. A voice reading a list straight through
    is presenting the list as one thing: no plan when any hand-over would come sooner than MIN_LEAD_S."""
    cap = "创新，实用，美观，易懂，不张扬。"
    props = {"stations": [{"label": w} for w in ("创新", "实用", "美观", "易懂", "不张扬")]}
    n = len([c for c in cap if c not in "，。"])
    fast = fp.focus_plan(props, _spans(cap, [0.4 * k for k in range(n)]), cap, duration=6.0)
    slow = fp.focus_plan(props, _spans(cap, [1.0 * k for k in range(n)]), cap, duration=14.0)
    assert fast == [] and len(slow) == 5


def test_a_terminal_s_lines_are_entries_and_a_headline_s_are_not():
    """craft_qa --type named eight terminal beats of one film (4.2-4.9% type over 6-18 lines, nothing leading). A log's
    lines and a program's lines are separate entries the voice walks through; a headline's `lines` are one sentence."""
    log = {"lines": [{"text": "load open base model", "kind": "run"}, {"text": "+ 精选 & 合成数据", "kind": "run"},
                     {"text": "supervised fine-tune", "kind": "run"}]}
    assert len(fp.item_texts_for_focus(log, shot="TermLog")) == 3
    assert len(fp.item_texts_for_focus({"lines": ["resp = model.chat()", "print(resp)"]}, shot="CodeCompose")) == 2
    assert fp.item_texts_for_focus({"lines": ["一个题目", "一条成片"]}, shot="HeadlineReveal") == {}
    assert fp.item_texts_for_focus({"lines": ["一个题目", "一条成片"]}) == {}


def test_a_commit_message_is_an_item_text():
    commits = {"commits": [{"hash": "h4a2c1d", "msg": "混合推理 hybrid reasoning"},
                           {"hash": "h2p8a1c", "msg": "工具调用 tool calling"}]}
    assert fp.item_texts_for_focus(commits, shot="TermGitLog") == {"commits.0": "混合推理 hybrid reasoning",
                                                                     "commits.1": "工具调用 tool calling"}


def test_a_generic_shared_word_does_not_hand_over_the_lead():
    """Measured on hermes (TermLog): 「…拿一个开源基座模型…」 handed the lead to the line 「中立对齐 · 会用工具的模型」 on 模型
    alone — 2 of its 11 characters, which passes the cue matcher's 15% coverage. Lighting the wrong line is worse than
    lighting none, so the lead asks for a MENTION: 30% of the item, or a run of six characters on its own."""
    props = {"lines": [{"text": "中立对齐 · 会用工具的模型"}, {"text": "+ 精选 & 合成数据"}]}
    cap = "拿一个开源基座模型，用精选和合成数据做微调。"
    n = len([c for c in cap if c not in "，。"])
    plan = fp.focus_plan(props, _spans(cap, [0.25 * k for k in range(n)]), cap, duration=8.0, shot="TermLog")
    assert [p["key"] for p in plan] == ["lines.1"], plan
