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

def test_reveal_alignment_wholeword_anchor_no_phantom_with_edge(tmp_path):
    # "art" collides inside "start" earlier; with the whole-word matcher, validate's spoken position
    # matches resolve_cues' token time -> NO phantom leads/lags (regression for the substring skew).
    import json
    wp = tmp_path / "03.words.json"
    json.dump([{"w": "art", "t": 5.0}, {"w": "end", "t": 8.0}], open(wp, "w"))
    html = ('<div data-cue-index="0" data-cue="art">A</div>'
            '<div data-cue-index="1" data-cue="end">B</div>')
    narr = "we start the demo, then the art module runs, and it will end soon here."
    w = _align(html, narr, duration=10.0, words_path=str(wp))
    assert not any("leads the voice" in x or "lags the voice" in x for x in w), w

def test_reveal_alignment_missing_anchor_flags():
    html = ('<div data-cue-index="0" data-cue="甲">A</div>'
            '<div data-cue-index="1" data-cue="不存在">B</div>')
    w = _align(html, "只说了甲，没有第二个词。", duration=8.0)
    assert any("not in the narration" in x for x in w), w

def test_reveal_alignment_ignored_before_tts():
    # no duration yet (pre-tts) -> the timing gap can't be computed, so no leads/lags noise
    w = _align(_TWO_PT, "开头很多铺垫后面才说甲最后说乙。", duration=None, anim_seconds=1.0)
    assert not any("leads the voice" in x or "lags the voice" in x for x in w), w


def test_narration_ai_tells_flagged_en(tmp_path):
    s = _slide_scene(tmp_path, 0, narration="This delve underscores a pivotal moment, not only clever.")
    data = _board(str(tmp_path), [s])
    r = validate.evaluate(data, str(tmp_path))
    assert any("AI-tell" in w for w in r["warnings"])

def test_narration_ai_tells_flagged_cjk(tmp_path):
    s = _slide_scene(tmp_path, 0, narration="值得注意的是,它深入探讨,不仅快而且准。")
    data = _board(str(tmp_path), [s], meta={"language": "zh"})
    r = validate.evaluate(data, str(tmp_path))
    assert any("AI-tell" in w for w in r["warnings"])

def test_narration_clean_no_ai_tell(tmp_path):
    s = _slide_scene(tmp_path, 0, narration="它帮你把要紧的内容做成专业演示。真文字、真形状,能继续改。")
    data = _board(str(tmp_path), [s], meta={"language": "zh"})
    r = validate.evaluate(data, str(tmp_path))
    assert not any("AI-tell" in w for w in r["warnings"])


def test_layout_family_classifies():
    assert validate._layout_family('<div class="scorecard"><div class="tile">9</div></div>') == "scorecard"
    assert validate._layout_family('<div class="flow"><div class="step"></div></div>') == "flow"
    assert validate._layout_family('<div class="grid"><div class="card">x</div></div>') == "cards"
    assert validate._layout_family('<div class="pullquote">x</div>') == "quote"
    assert validate._layout_family('<h1 class="title">x</h1>') == "title"

def test_diversity_gate_warns_when_one_family_dominates(tmp_path):
    # 5 html scenes, all card grids -> >45% one family -> warn (the samey-deck signal)
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", '<div class="grid"><div class="card">x</div></div>')
              for i in range(5)]
    data = _board(str(tmp_path), slides)
    r = validate.evaluate(data, str(tmp_path))
    assert any("layout diversity" in w and "cards" in w for w in r["warnings"])

def test_diversity_gate_no_false_positive_on_tiny_deck(tmp_path):
    # 2 of 4 the same family (50%) must NOT flag — the dominant family needs >=3 scenes
    bodies = ['<div class="grid"><div class="card">x</div></div>',
              '<div class="grid"><div class="card">x</div></div>',
              '<div class="flow"><div class="step"></div></div>',
              '<h1 class="title">x</h1>']
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", b) for i, b in enumerate(bodies)]
    data = _board(str(tmp_path), slides)
    r = validate.evaluate(data, str(tmp_path))
    assert not any("layout diversity" in w for w in r["warnings"])

def test_diversity_gate_silent_when_forms_vary(tmp_path):
    bodies = ['<div class="scorecard"><div class="tile">9</div></div>',
              '<div class="flow"><div class="step"></div></div>',
              '<div class="quadrant"><div class="cell"></div></div>',
              '<div class="timeline"><div class="tl-node"></div></div>',
              '<div class="grid"><div class="card">x</div></div>']
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", b) for i, b in enumerate(bodies)]
    data = _board(str(tmp_path), slides)
    r = validate.evaluate(data, str(tmp_path))
    assert not any("layout diversity" in w for w in r["warnings"])


def test_consecutive_html_scenes_do_not_warn(tmp_path):
    # all-html "designed deck" is recommended; the anti-slop run check must NOT fire on it
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", "<body>hi</body>") for i in range(3)]
    data = _board(str(tmp_path), slides)
    r = validate.evaluate(data, str(tmp_path))
    assert not any("consecutive" in w for w in r["warnings"])


def test_two_living_backdrops_warn(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<img class="bg-soft bg-live" src="x"><img class="bg-photo bg-drift" src="y"><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("living backdrops" in w for w in r["warnings"])   # >1 moving thing per page

def test_single_full_bleed_living_backdrop_ok(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<img class="bg-soft bg-live" src="x"><div class="stage">hi</div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("living backdrop" in w for w in r["warnings"])  # correct usage: no warning

def test_living_backdrop_on_non_fullbleed_warns(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="card bg-live">x</div><body></body>')   # motion on a card, not a backdrop
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("non-full-bleed" in w for w in r["warnings"])

def test_living_backdrop_lint_quote_agnostic_and_token_exact(tmp_path):
    # SINGLE-quoted ambient on a card -> warns (mirrors seek.js .matches(), which is quote-agnostic)
    s = _html_scene(tmp_path, 0, "pages/s0.html", "<div class='card bg-live'>x</div><body></body>")
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("non-full-bleed" in w for w in r["warnings"])
    # a LOOK-ALIKE token 'my-bg-live' is not the class 'bg-live' -> no living-backdrop warning
    s2 = _html_scene(tmp_path, 0, "pages/s1.html", '<div class="card my-bg-live">x</div><body></body>')
    r2 = validate.evaluate(_board(str(tmp_path), [s2]), str(tmp_path))
    assert not any("non-full-bleed" in w or "living backdrops" in w for w in r2["warnings"])


def test_duplicate_cue_index_warns(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="row" data-cue-index="0" data-cue="a">A</div>'
                    '<div class="row" data-cue-index="0" data-cue="b">B</div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("duplicate data-cue-index" in w for w in r["warnings"])


def test_html_cued_without_wordsjson_warns(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="row" data-cue-index="0" data-cue="alpha">A</div><body></body>')
    data = _board(str(tmp_path), [s])  # default voice "auto" wants edge -> words.json expected
    r = validate.evaluate(data, str(tmp_path))
    assert any("words.json" in w for w in r["warnings"])


# --- one-by-one reveals + arrows-with-blocks + composition/background lints -------------------------
_FLOW_CUED = ('<div class="stage"><div class="flow">'
              '<div class="step reveal-up" data-cue-index="0" data-cue="a">A</div>'
              '{arrow}'
              '<div class="step reveal-up" data-cue-index="1" data-cue="b">B</div>'
              '</div></div>')

def test_static_connector_among_cued_blocks_is_error(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html", _FLOW_CUED.format(arrow='<div class="arrow">→</div>'))
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not r["ok"]
    assert any("static" in e and "connector" in e for e in r["errors"])

def test_connector_reveal_shares_dest_index_no_error_no_dupe(tmp_path):
    # arrow reveals WITH its destination (index 1, no data-cue of its own) — legal co-reveal
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    _FLOW_CUED.format(arrow='<div class="arrow reveal" data-cue-index="1">→</div>'))
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("static" in e for e in r["errors"])          # not an error
    assert not any("duplicate data-cue-index" in w for w in r["warnings"])   # connector-aware accounting
    assert not any("missing a data-cue anchor" in w for w in r["warnings"])

def test_connector_index_below_destination_warns(tmp_path):
    # arrow at cue 0 but its destination block is at cue 1 -> warn (appears before the block)
    body = ('<div class="stage"><div class="flow">'
            '<div class="step reveal-up" data-cue-index="0" data-cue="a">A</div>'
            '<div class="arrow reveal" data-cue-index="0">→</div>'
            '<div class="step reveal-up" data-cue-index="1" data-cue="b">B</div>'
            '</div></div>')
    s = _html_scene(tmp_path, 0, "pages/s0.html", body)
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("points to a block at cue" in w for w in r["warnings"])

def test_uncued_reveal_on_cued_page_warns(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="note reveal-up" data-cue-index="0" data-cue="a">A</div>'
                    '<div class="note reveal-up">orphan</div><body></body>')   # 2nd reveal uncued
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("uncued on a cued page" in w for w in r["warnings"])

def test_uncued_chrome_reveal_is_exempt(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="kicker reveal-up">hat</div>'                  # chrome — exempt
                    '<div class="note reveal-up" data-cue-index="0" data-cue="a">A</div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("uncued on a cued page" in w for w in r["warnings"])

def test_facts_per_cue_warns(tmp_path):
    # two distinct LINE-ITEMS (rows) crammed under one cue -> they land all at once -> warn
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="dash reveal-up" data-cue-index="0" data-cue="a">'
                    '<div class="row">one</div><div class="row">two</div></div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("groups 2 independently-meaningful facts" in w for w in r["warnings"])

def test_facts_per_cue_excludes_number_delta_unit(tmp_path):
    # a number + its own delta/unit is ONE visual unit -> must NOT trip facts-per-cue
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="tile reveal-up" data-cue-index="0" data-cue="a">'
                    '<div class="num">5<span class="unit">%</span></div><div class="delta">▲</div></div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("independently-meaningful facts" in w for w in r["warnings"])

def test_facts_per_cue_label_value_line_item_ok(tmp_path):
    # a "label: value" row and a tile wrapping a labeled row are each ONE line-item -> no warn
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="row reveal-up" data-cue-index="0" data-cue="a">'
                    '<span class="label">GDP</span><span class="note">+5%</span></div>'
                    '<div class="tile reveal-up" data-cue-index="1" data-cue="b">'
                    '<div class="row"><span class="label">x</span><span class="stat">5</span></div></div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("independently-meaningful facts" in w for w in r["warnings"])

def test_opening_gap_no_header_late_first_reveal_warns(tmp_path):
    # a no-header hero whose only reveal is anchored to a LATE phrase -> blank while the opening plays
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="stage"><div class="stat reveal-up" data-cue-index="0" data-cue="the big number">42</div></div>')
    s["narration"] = "Let me set this up at length before I finally reach the big number at the very end."
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("sits BLANK while the opening" in w for w in r["warnings"])

def test_opening_gap_early_header_no_warn(tmp_path):
    # a kicker (uncued header) shows in the head window -> not blank, even if content is anchored late
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="stage"><div class="kicker">Setup</div>'
                    '<div class="stat reveal-up" data-cue-index="0" data-cue="the big number">42</div></div>')
    s["narration"] = "Let me set this up at length before I finally reach the big number at the very end."
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("sits BLANK while the opening" in w for w in r["warnings"])

def test_opening_gap_early_anchored_first_reveal_no_warn(tmp_path):
    # no header, but the first reveal is anchored to the OPENING phrase -> appears immediately
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="stage"><div class="stat reveal-up" data-cue-index="0" data-cue="Let me">42</div></div>')
    s["narration"] = "Let me set this up, and here is the big number right away at the start."
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert not any("sits BLANK while the opening" in w for w in r["warnings"])


def test_cue_contiguity_gap_warns(tmp_path):
    s = _html_scene(tmp_path, 0, "pages/s0.html",
                    '<div class="row reveal-up" data-cue-index="0" data-cue="a">A</div>'
                    '<div class="row reveal-up" data-cue-index="2" data-cue="b">B</div><body></body>')
    r = validate.evaluate(_board(str(tmp_path), [s]), str(tmp_path))
    assert any("not contiguous" in w for w in r["warnings"])


def _content_page(anchor_style="", cls="card", extra=""):
    return f'{extra}<div class="stage" style="{anchor_style}"><div class="{cls}">body text here</div></div>'

def test_ai_look_flat_content_page_warns(tmp_path):
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", _content_page()) for i in range(4)]
    r = validate.evaluate(_board(str(tmp_path), slides, meta={"image_source": "openai"}), str(tmp_path))
    assert any("content page is FLAT" in w for w in r["warnings"])

def test_ai_look_bg_soft_page_not_flat(tmp_path):
    open(os.path.join(str(tmp_path), "tex.png"), "wb").write(b"\x89PNG")
    body = ('<img class="bg-soft" src="tex.png" style="opacity:.12"><div class="bg-soft-tint"></div>'
            + _content_page())
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", body) for i in range(4)]
    r = validate.evaluate(_board(str(tmp_path), slides,
                                 meta={"image_source": "openai", "soft_textures": ["tex.png"]}), str(tmp_path))
    assert not any("content page is FLAT" in w for w in r["warnings"])

def test_ai_look_bg_soft_too_loud_and_missing_tint_warn(tmp_path):
    open(os.path.join(str(tmp_path), "tex.png"), "wb").write(b"\x89PNG")
    loud = '<img class="bg-soft" src="tex.png" style="opacity:.30">' + _content_page()  # no tint, loud
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", loud) for i in range(4)]
    r = validate.evaluate(_board(str(tmp_path), slides, meta={"image_source": "openai"}), str(tmp_path))
    assert any("opacity 0.30 > .20" in w or "opacity .30 > .20" in w or "> .20" in w for w in r["warnings"])
    assert any("no following .bg-soft-tint" in w for w in r["warnings"])

def test_composition_all_center_and_kicker_first_warn(tmp_path):
    body = '<div class="stage"><div class="kicker">k</div><div class="card">x</div></div>'
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", body) for i in range(4)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert any("CENTER-anchored" in w for w in r["warnings"])
    assert any("opens with a top .kicker" in w for w in r["warnings"])

def test_composition_varied_anchors_no_warn(tmp_path):
    bodies = [
        '<div class="stage" style="justify-content:flex-start"><div class="hero">x</div></div>',
        '<div class="stage" style="justify-content:flex-end"><div class="card">x</div></div>',
        '<div class="split"><div class="media">m</div><div class="body">b</div></div>',
        '<div class="stage"><div class="grid-asym"><div class="card">x</div></div></div>',
    ]
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", b) for i, b in enumerate(bodies)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert not any("CENTER-anchored" in w for w in r["warnings"])
    assert not any("break the centered column" in w for w in r["warnings"])

def test_background_flatness_warns(tmp_path):
    body = '<div class="stage"><div class="card">x</div></div>'   # bare --bg, no backdrop
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", body) for i in range(5)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert any("background flatness" in w for w in r["warnings"])

def test_bg_motif_counts_as_backdrop_not_flat(tmp_path):
    # a faint topical .bg-motif (the free flat-tier backdrop) makes a page read not-flat
    body = ('<div class="bg-motif"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="9" fill="currentColor"/></svg></div>'
            '<div class="bg-soft-tint"></div><div class="stage"><div class="card">x</div></div>')
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", body) for i in range(5)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert not any("background flatness" in w for w in r["warnings"])

def test_bg_grid_counts_as_backdrop_not_flat(tmp_path):
    body = '<div class="bg-grid"></div><div class="stage"><div class="card">x</div></div>'
    slides = [_html_scene(tmp_path, i, f"pages/s{i}.html", body) for i in range(5)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert not any("background flatness" in w for w in r["warnings"])

def test_backdrop_with_cue_inside_warns(tmp_path):
    # a cued chart SVG copied into a .bg-motif backdrop WITHOUT stripping markers poisons reveal timing
    body = ('<div class="bg-motif"><svg viewBox="0 0 100 100">'
            '<polyline class="reveal-wipe" data-cue-index="0" data-cue="revenue climbs" points="0,90 90,10"/></svg></div>'
            '<div class="stage"><div class="stat reveal" data-cue-index="1" data-cue="four point seven">$4.7M</div></div>')
    slides = [_html_scene(tmp_path, 0, "pages/s0.html", body)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert any("INSIDE a full-bleed backdrop" in w for w in r["warnings"])

def test_inert_backdrop_no_warn(tmp_path):
    # a clean, inert .bg-motif (no cue/reveal inside) on a cued page raises no backdrop-inertness warning
    body = ('<div class="bg-motif"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="9" fill="currentColor"/></svg></div>'
            '<div class="stage"><div class="stat reveal" data-cue-index="0" data-cue="four point seven">$4.7M</div></div>')
    slides = [_html_scene(tmp_path, 0, "pages/s0.html", body)]
    r = validate.evaluate(_board(str(tmp_path), slides), str(tmp_path))
    assert not any("INSIDE a full-bleed backdrop" in w for w in r["warnings"])


# --- design_plan.json hooks (form-fit + creativity presence, feeding design-critic D1/D2c) ---------
def _design_plan(tmp_path, plan):
    open(os.path.join(str(tmp_path), "design_plan.json"), "w").write(json.dumps(plan))

def test_design_plan_trend_as_stat_warns(tmp_path):
    _design_plan(tmp_path, {"beats": [{"index": 1, "content_shape": "revenue growth over 4 quarters", "form": "stat"}],
                            "signature_concept": {"beat": 1, "name": "x"}, "style_thesis": "blueprint"})
    r = validate.evaluate(_board(str(tmp_path), [_slide_scene(tmp_path, 0)]), str(tmp_path))
    assert any("trend rendered static" in w for w in r["warnings"])

def test_design_plan_share_as_stats_warns(tmp_path):
    _design_plan(tmp_path, {"beats": [{"index": 1, "content_shape": "share of total revenue by segment", "form": "scorecard"}],
                            "signature_concept": {"beat": 1, "name": "x"}, "style_thesis": "blueprint"})
    r = validate.evaluate(_board(str(tmp_path), [_slide_scene(tmp_path, 0)]), str(tmp_path))
    assert any("separate numbers hide the whole" in w for w in r["warnings"])

def test_design_plan_missing_creativity_fields_warn(tmp_path):
    _design_plan(tmp_path, {"beats": [{"index": 1, "content_shape": "one number", "form": "stat"}]})
    r = validate.evaluate(_board(str(tmp_path), [_slide_scene(tmp_path, 0)]), str(tmp_path))
    assert any("no signature_concept" in w for w in r["warnings"])
    assert any("no style_thesis" in w for w in r["warnings"])

def test_design_plan_signature_is_catalog_grid_warns(tmp_path):
    _design_plan(tmp_path, {"beats": [{"index": 2, "content_shape": "x", "form": "card grid"}],
                            "signature_concept": {"beat": 2, "name": "x"}, "style_thesis": "y"})
    r = validate.evaluate(_board(str(tmp_path), [_slide_scene(tmp_path, 0)]), str(tmp_path))
    assert any("signature_concept beat's form looks like a catalog grid" in w for w in r["warnings"])


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


# ── B: hardcoded-hex lint (semantic-var contract, color contexts only) ────────────────
def test_hardcoded_hex_lint_flags_style_svg_and_styleblock(tmp_path):
    (tmp_path / "theme.css").write_text(":root{--bg:#111;}")
    pg = tmp_path / "pages"; pg.mkdir()
    (pg / "scene_01.html").write_text(
        '<div style="color:#ff3366">x</div><rect fill="#0af"/><style>.y{background:#abcdef}</style>')
    errors, warnings = [], []
    validate._check_html_assets(str(tmp_path), "pages/scene_01.html", False, 1, errors, warnings)
    assert any("raw hex" in w for w in warnings) and not errors

def test_hex_lint_ignores_svg_ids_content_and_vars(tmp_path):
    (tmp_path / "theme.css").write_text(":root{--bg:#111;}")
    pg = tmp_path / "pages"; pg.mkdir()
    (pg / "scene_01.html").write_text(
        '<rect fill="url(#dead)"/><div style="background:var(--accent)">brand is #ff3366 in text</div>')
    errors, warnings = [], []
    validate._check_html_assets(str(tmp_path), "pages/scene_01.html", False, 1, errors, warnings)
    assert not any("raw hex" in w for w in warnings)


# ── alignment audit regressions ───────────────────────────────────────────────────────
def _cue_board(tmp_path, narration, callout):
    from PIL import Image
    os.makedirs(tmp_path / "frames", exist_ok=True)
    Image.new("RGB", (320, 180), "#333").save(str(tmp_path / "frames" / "01.png"))
    (tmp_path / "theme.css").write_text(":root{--bg:#111;}")
    return {"meta": {"language": "en", "captions": True},
            "slides": [{"index": 1, "type": "slide", "image": "frames/01.png",
                        "narration": narration,
                        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
                        "captions": [], "callouts": [callout]}]}

def test_timed_callout_cue_does_not_crash_and_warns_when_missing(tmp_path):
    # regression: _cues was undefined in evaluate() -> NameError on the first cue callout
    data = _cue_board(tmp_path, "Nothing matching here at all.",
                      {"box": [0.1, 0.1, 0.4, 0.4], "style": "highlight", "cue": "crucial region"})
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert any("not in the narration" in w for w in r["warnings"])

def test_timed_callout_cue_found_no_warning(tmp_path):
    data = _cue_board(tmp_path, "Look at the crucial region early on, then more talk follows here.",
                      {"box": [0.1, 0.1, 0.4, 0.4], "style": "highlight", "cue": "crucial region"})
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert not any('cue "crucial region" is not' in w for w in r["warnings"])

def test_reduced_motion_skips_zoom_warnings(tmp_path):
    data = _cue_board(tmp_path, "Some narration line.",
                      {"box": [0.4, 0.4, 0.6, 0.6], "style": "highlight"})
    data["slides"][0]["motion"]["to"] = [0.5, 0.5, 1.4]          # zoom delta 0.4 + past 1.25
    r1 = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert any("zoom" in w for w in r1["warnings"])
    data["meta"]["reduced_motion"] = True
    r2 = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert not any("zoom" in w for w in r2["warnings"])          # renderer forces to==from

def test_chrome_with_captions_on_warns(tmp_path):
    (tmp_path / "theme.css").write_text(":root{--bg:#111;}")
    pg = tmp_path / "pages"; pg.mkdir()
    (pg / "scene_01.html").write_text('<div class="chrome"><span>SECTION</span></div>')
    errors, warnings = [], []
    validate._check_html_assets(str(tmp_path), "pages/scene_01.html", False, 1, errors, warnings,
                                captions_on=True)
    assert any("chrome" in w and "caption" in w for w in warnings)
    warnings2 = []
    validate._check_html_assets(str(tmp_path), "pages/scene_01.html", False, 1, [], warnings2,
                                captions_on=False)
    assert not any("chrome" in w for w in warnings2)             # captions off: .chrome is fine


def test_transition_sanity_warnings(tmp_path):
    data = _cue_board(tmp_path, "Some line.", {"box": [0.4, 0.4, 0.6, 0.6], "style": "highlight"})
    data["slides"][0]["transition"] = "wipe"                      # not a supported value
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert any("unknown transition" in w for w in r["warnings"])
    data["slides"][0]["transition"] = "in"
    data["slides"][0]["transition_seconds"] = 0.8                 # sluggish
    r2 = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert not any("unknown transition" in w for w in r2["warnings"])
    assert any("sluggish" in w for w in r2["warnings"])


def _multi_board(tmp_path, transitions):
    from PIL import Image
    os.makedirs(tmp_path / "frames", exist_ok=True)
    Image.new("RGB", (320, 180), "#333").save(str(tmp_path / "frames" / "01.png"))
    (tmp_path / "theme.css").write_text(":root{--bg:#111;}")
    slides = []
    for i, tr in enumerate(transitions, 1):
        s = {"index": i, "type": "slide", "image": "frames/01.png", "narration": f"Beat {i} says something.",
             "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
             "captions": [], "callouts": []}
        if tr is not None:
            s["transition"] = tr
        slides.append(s)
    return {"meta": {"language": "en", "captions": True}, "slides": slides}

def test_seam_pairing_smash_in_warns(tmp_path):
    # B fades in from bg but A ends hard -> smash-cut-to-blank
    data = _multi_board(tmp_path, ["in", "none", "in"])
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert any("smash-cut" in w for w in r["warnings"])

def test_seam_pairing_proper_seam_clean(tmp_path):
    # A "out" + B "in" composes a proper dip; closer "dip" carries the end fade
    data = _multi_board(tmp_path, ["in", "out", "dip"])
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert not any("smash-cut" in w or "fade-down-then-pop" in w or "no out edge" in w
                   for w in r["warnings"])

def test_final_scene_hard_end_warns_unless_meta_none(tmp_path):
    data = _multi_board(tmp_path, ["in", "none", "none"])
    r = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert any("no out edge" in w for w in r["warnings"])
    data["meta"]["transition"] = "none"                          # user chose no transitions at all
    data["slides"][0]["transition"] = None if False else "none"  # normalize scene 1 too
    r2 = validate.evaluate(data, str(tmp_path), pre_tts=True)
    assert not any("no out edge" in w for w in r2["warnings"])
