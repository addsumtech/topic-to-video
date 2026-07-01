import json, os, subprocess, sys
import validate
import storyboard as sb


def _board(out_dir, slides, meta=None):
    """Write a storyboard.json (+ minimal real assets) into out_dir and return the dict."""
    data = sb.new_storyboard(meta)
    data["slides"] = slides
    sb.save(data, os.path.join(out_dir, "storyboard.json"))
    return data


def _slide_scene(tmp_path, index=0, **over):
    """A title scene with audio+duration already 'synthesised' (a real file on disk)."""
    aud = os.path.join("audio", f"{index:02d}.mp3")
    os.makedirs(os.path.join(str(tmp_path), "audio"), exist_ok=True)
    open(os.path.join(str(tmp_path), aud), "wb").write(b"\x00")
    s = sb.new_scene(index, "title", {"title": "Hello"}, narration="A short line.")
    s["audio"] = aud
    s["duration"] = 4.0
    s.update(over)
    return s


def test_missing_audio_is_error(tmp_path):
    s = sb.new_scene(0, "title", {"title": "Hi"}, narration="Hi there.")
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is False
    assert any("no audio/duration" in e for e in r["errors"])


def test_pre_tts_skips_audio(tmp_path):
    s = sb.new_scene(0, "title", {"title": "Hi"}, narration="Hi there.")
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert r["ok"] is True


def test_missing_image_file_is_error(tmp_path):
    s = _slide_scene(tmp_path, 0)
    s["type"] = "slide"; s["props"] = None
    s["image"] = "frames/nope.png"
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is False and any("not found" in e for e in r["errors"])


def test_duplicate_index_is_error(tmp_path):
    data = _board(str(tmp_path), [_slide_scene(tmp_path, 0), _slide_scene(tmp_path, 0)])
    r = validate.evaluate(data, str(tmp_path))
    assert any("duplicate scene index" in e for e in r["errors"])


def test_clean_board_passes(tmp_path):
    data = _board(str(tmp_path), [_slide_scene(tmp_path, 0), _slide_scene(tmp_path, 1)])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is True and r["errors"] == []


def test_big_zoom_is_warning_not_error(tmp_path):
    s = _slide_scene(tmp_path, 0)
    s["motion"] = {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.6]}
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is True and any("zoom delta" in w for w in r["warnings"])


def test_long_hold_is_warning(tmp_path):
    s = _slide_scene(tmp_path, 0, duration=20.0)
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("holds" in w for w in r["warnings"])


def test_consecutive_same_type_warns(tmp_path):
    slides = [_slide_scene(tmp_path, i) for i in range(3)]   # 3 title scenes in a row
    data = _board(str(tmp_path), slides)
    r = validate.evaluate(data, str(tmp_path))
    assert any("consecutive" in w for w in r["warnings"])


def test_dense_cjk_caption_wall_warns(tmp_path):
    # a CJK clause with no breakable mark becomes one dense cue — the char-density ceiling must
    # flag it even though it wraps to <= MAX_CAPTION_LINES (the line count alone would miss it).
    wall = "承载证据的图都是真的原图精准提取公式是真能改概念在真实输入上现算不是随手贴张糊图最后导出"
    s = _slide_scene(tmp_path, 0, narration=wall)
    data = _board(str(tmp_path), [s], meta={"language": "zh"})
    r = validate.evaluate(data, str(tmp_path))
    assert any("wall of text" in w for w in r["warnings"])


def test_caption_trailing_clause_mark_warns(tmp_path):
    # an explicit captions track whose chunk ends on a clause mark reads as cut-off
    s = _slide_scene(tmp_path, 0)
    s["captions"] = [{"start": 0, "end": 2, "text": "先听懂,"},
                     {"start": 2, "end": 4, "text": "再动手。"}]
    data = _board(str(tmp_path), [s], meta={"language": "zh"})
    r = validate.evaluate(data, str(tmp_path))
    assert any("dangling" in w for w in r["warnings"])


def test_clean_cjk_caption_no_wall_warning(tmp_path):
    # a normal CJK line that splits fine must NOT trip the density/dangling checks
    s = _slide_scene(tmp_path, 0, narration="先听懂,再动手。")
    data = _board(str(tmp_path), [s], meta={"language": "zh"})
    r = validate.evaluate(data, str(tmp_path))
    assert not any("wall of text" in w or "dangling" in w for w in r["warnings"])


def _html_scene(tmp_path, index, page_rel, body):
    os.makedirs(os.path.join(str(tmp_path), os.path.dirname(page_rel)), exist_ok=True)
    open(os.path.join(str(tmp_path), page_rel), "w").write(body)
    s = _slide_scene(tmp_path, index)
    s["type"] = "html"; s["props"] = {"html": page_rel}
    return s


def _align(html, narration, duration, anim_seconds=None, words_path="/nonexistent.json"):
    w = []
    validate._reveal_alignment(html, narration, duration, anim_seconds, words_path, "scene 1", w)
    return w

_TWO_PT = ('<div class="row reveal-up" data-cue-index="0" data-cue="甲">A</div>'
           '<div class="row reveal-up" data-cue-index="1" data-cue="乙">B</div>')

def test_reveal_alignment_text_estimate_aligns_uneven_narration():
    # no word-timings + uneven narration (points spoken late): reveals are ESTIMATED from text
    # position (matching render_html), so shown≈spoken -> NO leads/lags. This is the text-cue fix.
    narr = "开头先讲很多铺垫的内容占用了不少时间，后面才说到甲，最后才说到乙。"
    w = _align(_TWO_PT, narr, duration=10.0)
    assert not any("leads the voice" in x or "lags the voice" in x for x in w), w

def test_reveal_alignment_flags_ambiguous_wordcue(tmp_path):
    # edge path: a word-cue that resolves EARLIER than the anchor's text position (ambiguous anchor)
    # -> the reveal fires before it's spoken -> "leads the voice".
    import json
    wp = tmp_path / "05.words.json"
    json.dump([{"w": "甲", "t": 0.3}, {"w": "乙", "t": 0.6}], open(wp, "w"))
    narr = "这是一段较长的开场白用来铺垫背景信息，随后才真正提到甲，最后提到乙收尾。"
    w = _align(_TWO_PT, narr, duration=10.0, words_path=str(wp))
    assert any("leads the voice" in x for x in w), w

def test_reveal_alignment_missing_anchor_flags():
    html = ('<div data-cue-index="0" data-cue="甲">A</div>'
            '<div data-cue-index="1" data-cue="不存在">B</div>')
    w = _align(html, "只说了甲，没有第二个词。", duration=8.0)
    assert any("not in the narration" in x for x in w), w

def test_reveal_alignment_ignored_before_tts():
    # no duration yet (pre-tts) -> the timing gap can't be computed, so no leads/lags noise
    w = _align(_TWO_PT, "开头很多铺垫后面才说甲最后说乙。", duration=None, anim_seconds=1.0)
    assert not any("leads the voice" in x or "lags the voice" in x for x in w), w


def test_consecutive_html_scenes_do_not_warn(tmp_path):
    # all-html "designed deck" is recommended; the anti-slop run check must NOT fire on it
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", "<body>hi</body>") for i in range(3)]
    data = _board(str(tmp_path), slides)
    r = validate.evaluate(data, str(tmp_path))
    assert not any("consecutive" in w for w in r["warnings"])


def test_html_cued_without_wordsjson_warns(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="row" data-cue-index="0" data-cue="alpha">A</div><body></body>')
    data = _board(str(tmp_path), [s])  # default voice "auto" wants edge -> words.json expected
    r = validate.evaluate(data, str(tmp_path))
    assert any("words.json" in w for w in r["warnings"])


def test_html_local_asset_missing_is_error(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<img src="file:///nonexistent/dir/bg_nope.png"><body></body>')
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is False and any("asset not found" in e for e in r["errors"])


def test_vertical_flag_changes_canvas(tmp_path):
    # a caption tuned to just fit 1920-wide may overflow the 1080-wide vertical canvas; the
    # --vertical path must evaluate against 1080 width (mirrors render.py)
    long_line = " ".join(["alpha bravo charlie delta echo foxtrot"] * 3)  # no enders -> one chunk
    s = _slide_scene(tmp_path, 0, narration=long_line)
    data = _board(str(tmp_path), [s])
    horiz = validate.evaluate(data, str(tmp_path), vertical=False)
    vert = validate.evaluate(data, str(tmp_path), vertical=True)
    horiz_lines = sum("wraps to" in w for w in horiz["warnings"])
    vert_lines = sum("wraps to" in w for w in vert["warnings"])
    # narrower vertical canvas wraps to >= as many lines as the wide one
    assert vert_lines >= horiz_lines


def test_html_missing_page_is_error(tmp_path):
    s = _slide_scene(tmp_path, 0)
    s["type"] = "html"; s["props"] = {"html": "pages/scene_00.html"}
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is False and any("html page" in e for e in r["errors"])


def test_html_remote_asset_is_error(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "pages"), exist_ok=True)
    page = "pages/scene_00.html"
    open(os.path.join(str(tmp_path), page), "w").write(
        '<link rel="stylesheet" href="https://cdn.example.com/x.css"><body>hi</body>')
    s = _slide_scene(tmp_path, 0)
    s["type"] = "html"; s["props"] = {"html": page}
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is False and any("remote/data asset" in e for e in r["errors"])


def test_dangling_word_helper():
    assert validate._dangling_word(["a long first line here", "future"]) == "future"
    assert validate._dangling_word(["a long first line", "two words"]) is None   # not a lone word
    assert validate._dangling_word(["one line only"]) is None                    # single line
    assert validate._dangling_word(["filler text", "supercalifragilistic"]) is None  # long word, not a widow


def test_motion_not_framing_callout_warns(tmp_path):
    s = _slide_scene(tmp_path, 0)
    s["callouts"] = [{"at": 0.0, "box": [0.6, 0.05, 0.95, 0.38], "style": "box", "label": "x"}]
    # default centered motion leaves the off-center callout unframed
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is True and any("frame" in w and "callout" in w for w in r["warnings"])


def test_motion_framing_callout_is_clean(tmp_path):
    s = _slide_scene(tmp_path, 0)
    s["callouts"] = [{"at": 0.0, "box": [0.6, 0.05, 0.95, 0.38], "style": "box", "label": "x"}]
    # to ≈ callout center (0.775, 0.215) -> within tolerance -> no warn (clears for the RIGHT reason)
    s["motion"] = {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.78, 0.22, 1.18]}
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert not any("callout" in w and "frame" in w for w in r["warnings"])


def test_motion_misaimed_pan_warns(tmp_path):
    """A pan (to != from) aimed away from the callout is still unframed -> must warn."""
    s = _slide_scene(tmp_path, 0)
    s["callouts"] = [{"at": 0.0, "box": [0.6, 0.05, 0.95, 0.38], "style": "box", "label": "x"}]
    s["motion"] = {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.1, 0.9, 1.18]}  # far from callout
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("callout" in w and "frame" in w for w in r["warnings"])


def test_zoom_past_limit_warns(tmp_path):
    s = _slide_scene(tmp_path, 0)
    s["motion"] = {"type": "kenburns", "from": [0.5, 0.5, 1.15], "to": [0.5, 0.5, 1.30]}  # delta .15 ok, end >1.25
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("scale limit" in w for w in r["warnings"])
    assert not any("zoom delta" in w for w in r["warnings"])   # delta is within tolerance


def test_too_fast_caption_warns(tmp_path):
    s = _slide_scene(tmp_path, 0, duration=1.0, narration="First. Second. Third. Fourth point.")
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("too fast to read" in w for w in r["warnings"])


def test_wall_of_text_caption_warns(tmp_path):
    # one chunk (no sentence/clause marks) of many words -> wraps well past 3 lines
    wall = " ".join(["alpha bravo charlie delta echo foxtrot golf hotel india juliet"] * 6)
    s = _slide_scene(tmp_path, 0, narration=wall)
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("wraps to" in w and "lines" in w for w in r["warnings"])


def test_widow_caption_warns_end_to_end(tmp_path):
    # a 60-char single token fills line 1; the trailing short word is forced to a lone line 2
    s = _slide_scene(tmp_path, 0, narration=("x" * 60) + " to")
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("lone word" in w for w in r["warnings"])


def test_reveal_lead_warns_when_uncued_anim_small(tmp_path):
    # 3 staggered points, no data-cue, tiny anim on a long scene -> content leads the voice
    body = ('<div class="row reveal-up-sm">a</div><div class="row reveal-up-sm">b</div>'
            '<div class="row reveal-up-sm">c</div><body></body>')
    s = _html_scene(tmp_path, 0, "pages/s0.html", body)
    s["props"]["anim_seconds"] = 2.0; s["duration"] = 12.0
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("appears well before the voice" in w for w in r["warnings"])


def test_reveal_lead_silent_when_cued(tmp_path):
    # same 3 points but audio-synced via data-cue -> no reveal-lead warning
    body = ('<div class="row reveal-up-sm" data-cue-index="0" data-cue="a">a</div>'
            '<div class="row reveal-up-sm" data-cue-index="1" data-cue="b">b</div>'
            '<div class="row reveal-up-sm" data-cue-index="2" data-cue="c">c</div><body></body>')
    s = _html_scene(tmp_path, 0, "pages/s0.html", body)
    s["props"]["anim_seconds"] = 2.0; s["duration"] = 12.0
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert not any("appears well before the voice" in w for w in r["warnings"])


def test_reveal_lead_silent_when_anim_spreads(tmp_path):
    # uncued but anim_seconds spreads across the scene -> no warning
    body = ('<div class="row reveal-up-sm">a</div><div class="row reveal-up-sm">b</div>'
            '<div class="row reveal-up-sm">c</div><body></body>')
    s = _html_scene(tmp_path, 0, "pages/s0.html", body)
    s["props"]["anim_seconds"] = 9.0; s["duration"] = 12.0
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert not any("appears well before the voice" in w for w in r["warnings"])


def test_html_links_theme_but_missing_is_error(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "pages"), exist_ok=True)
    page = "pages/scene_00.html"
    # relative href -> not resolved as a file asset; only the explicit theme.css check should fire
    open(os.path.join(str(tmp_path), page), "w").write(
        '<link rel="stylesheet" href="theme.css"><body>hi</body>')
    s = _slide_scene(tmp_path, 0)
    s["type"] = "html"; s["props"] = {"html": page}
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert r["ok"] is False and any("theme.css" in e for e in r["errors"])


def test_no_storyboard_file(tmp_path):
    r = validate.check(str(tmp_path))
    assert r["ok"] is False and any("no storyboard.json" in e for e in r["errors"])


def test_null_storyboard_does_not_crash(tmp_path):
    # valid JSON `null` parses to None -> the gate must report cleanly, not throw a traceback
    open(os.path.join(str(tmp_path), "storyboard.json"), "w").write("null")
    r = validate.check(str(tmp_path))
    assert r["ok"] is False and any("not a JSON object" in e for e in r["errors"])


def test_non_dict_meta_does_not_crash(tmp_path):
    open(os.path.join(str(tmp_path), "storyboard.json"), "w").write('{"meta": "oops", "slides": [{"index":0,"narration":"x"}]}')
    r = validate.check(str(tmp_path))
    assert r["ok"] is False and any("structure" in e for e in r["errors"])


def test_main_exit_code(tmp_path):
    _board(str(tmp_path), [_slide_scene(tmp_path, 0)])
    ok = subprocess.run([sys.executable, validate.__file__, str(tmp_path)], capture_output=True)
    assert ok.returncode == 0
    # break it: remove the audio file reference
    bad = sb.new_scene(0, "title", {"title": "Hi"}, narration="Hi.")
    _board(str(tmp_path), [bad])
    fail = subprocess.run([sys.executable, validate.__file__, str(tmp_path)], capture_output=True)
    assert fail.returncode == 1


def test_main_json_output(tmp_path):
    _board(str(tmp_path), [_slide_scene(tmp_path, 0)])
    out = subprocess.run([sys.executable, validate.__file__, str(tmp_path), "--json"],
                         capture_output=True, text=True)
    parsed = json.loads(out.stdout)
    assert parsed["ok"] is True and parsed["scenes"] == 1
