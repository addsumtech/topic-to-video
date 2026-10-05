"""The HTML tier's half of narration<->visual sync.

  * a page of 2+ revealable points with NO cue anchors is an ERROR (validate + keyframe_qa), with its fix;
  * a cue on one of the narration's last words is LED just enough for its reveal to finish before the scene's
    out-transition (render_html used to start it on its word and leave it fading in under the dip);
  * the per-cue capture window is keyed by the cue's own index;
  * keyframe_qa's sync audit reads the frames render_html actually captures.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import _common  # noqa: E402
import scenes  # noqa: E402
import validate  # noqa: E402

BASE = os.path.join(_ROOT, "assets", "html")
FPS = 30


def _page(body):
    return ('<!doctype html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="file://{BASE}/base.css"></head><body>{body}'
            f'<script src="file://{BASE}/seek.js"></script></body></html>')


def _write(tmp_path, body, words=None, index=1):
    (tmp_path / "pages").mkdir(exist_ok=True)
    (tmp_path / "pages" / "p.html").write_text(_page(body), encoding="utf-8")
    if words is not None:
        (tmp_path / "audio").mkdir(exist_ok=True)
        json.dump(words, open(tmp_path / "audio" / ("%02d.words.json" % index), "w"))
    return {"html": "pages/p.html"}


# ── uncued pages ──────────────────────────────────────────────────────────────────────────────────────────────
_UNCUED = ('<div class="stage"><div class="kicker reveal">K</div><h1 class="title reveal-up">T</h1>'
           '<div class="reveal-up">one</div><div class="reveal-up">two</div><div class="reveal-up">three</div></div>')


def test_a_page_of_points_with_no_cues_is_counted_without_its_header():
    assert validate.uncued_reveal_points(_UNCUED) == 3


def test_one_point_a_cued_page_and_a_hero_are_exempt():
    assert validate.uncued_reveal_points('<div class="stage"><h1 class="title reveal">T</h1>'
                                         '<div class="reveal-up">only</div></div>') == 1
    assert validate.uncued_reveal_points(_UNCUED.replace('class="reveal-up">one',
                                                         'class="reveal-up" data-cue-index="0" data-cue="one">one')) == 0
    assert validate.uncued_reveal_points('<img class="bg-photo" src="x.jpg">' + _UNCUED) == 0


def test_points_inside_a_backdrop_do_not_count():
    assert validate.uncued_reveal_points('<div class="bg-motif"><div class="reveal">a</div>'
                                         '<div class="reveal">b</div></div><div class="reveal-up">c</div>') == 1


def test_validate_blocks_an_uncued_page_of_points_and_says_how_to_fix_it(tmp_path):
    _write(tmp_path, _UNCUED)
    s = {"index": 1, "type": "html", "props": {"html": "pages/p.html"}, "narration": "one two three",
         "duration": 6.0, "audio": "audio/01.mp3"}
    data = {"meta": {"renderer": "local", "aspect": "16:9", "fps": 30}, "slides": [s]}
    r = validate.evaluate(data, str(tmp_path))
    hits = [e for e in r["errors"] if "NO data-cue anchors" in e]
    assert hits and "data-cue-index" in hits[0] and 'data-cue="<the words that name it>"' in hits[0], r["errors"]


# ── a late cue must finish before the out-transition ──────────────────────────────────────────────────────────
def test_out_edge_follows_the_transition_rule():
    assert _common.out_edge_seconds({}, {}, 5.0) == 0.2                       # the default dip
    assert _common.out_edge_seconds({"transition": "in"}, {}, 5.0) == 0.0
    assert _common.out_edge_seconds({"transition": "out", "transition_seconds": 0.4}, {}, 5.0) == 0.4
    assert _common.out_edge_seconds({}, {"transition": "none"}, 5.0) == 0.0
    assert _common.out_edge_seconds({}, {}, 0.3) == 0.0                       # too short to dip at all


def test_a_late_cue_is_led_only_as_far_as_its_reveal_needs_and_never_past_the_cap():
    ordered = [(0, "a"), (1, "b"), (2, "c")]
    need = {0: 0.7, 1: 0.7, 2: 1.4}
    times, led = _common.clamp_cues_to_end(ordered, [1.0, 3.5, 3.5], need, 4.0, 0.2)
    assert times[0] == 1.0                          # early enough already
    assert times[1] == pytest.approx(3.1) and 1 in led
    assert times[2] == 3.5 and 2 not in led         # a 1.4 s draw would need a 1.1 s lead: left for validate


def test_the_capture_plan_leads_a_last_word_cue(tmp_path):
    props = _write(tmp_path, '<div class="stage"><div class="reveal" data-cue-index="0" data-cue="alpha">A</div>'
                             '<div class="reveal" data-cue-index="1" data-cue="omega">O</div></div>',
                   words=[{"w": "alpha", "t": 0.5}, {"w": "omega", "t": 3.6}])
    plan = scenes.html_capture_plan(props, {"_out": str(tmp_path), "fps": FPS, "_narration": "alpha omega"},
                                    4 * FPS, 1)
    assert plan["cue_times"][1] == pytest.approx(4.0 - 0.2 - 0.7)
    assert plan["tail_led"] == [1]
    assert plan["cue_param"].split(",")[1] == "3.100"


def test_the_capture_window_is_keyed_by_the_cues_own_index(tmp_path):
    # index 0 is an anchorless connector; index 1 is a 1.4 s draw. Its window must be ~1.5 s, not the default
    # 0.8 s that position 0 in the cue list used to hand it (freezing the draw at 57%).
    props = _write(tmp_path, '<div class="stage"><div class="arrow reveal" data-cue-index="0">-</div>'
                             '<svg><path class="draw" data-cue-index="1" data-cue="omega" d="M0 0 L9 9"/></svg>'
                             '</div>', words=[{"w": "x", "t": 0.2}, {"w": "omega", "t": 3.0}])
    plan = scenes.html_capture_plan(props, {"_out": str(tmp_path), "fps": FPS, "_narration": "x omega"},
                                    10 * FPS, 1)
    shot_frames = {i for i, _p in plan["shots"]}
    c = plan["cue_times"][0]
    late_in_draw = int(round((c + 1.3) * FPS))
    assert late_in_draw in shot_frames, (c, sorted(shot_frames)[-5:])


def test_only_a_led_page_gets_a_new_clip_fingerprint(tmp_path, monkeypatch):
    # the salt is added ONLY when a cue is led: a key present on every clip (even null) would re-render every
    # cached clip of every deck
    import render
    props = _write(tmp_path, '<div class="stage"><div class="reveal" data-cue-index="0" data-cue="alpha">A</div></div>',
                   words=[{"w": "alpha", "t": 0.5}])
    meta = {"_out": str(tmp_path), "fps": FPS}
    slide = {"index": 1, "type": "html", "props": props, "duration": 4.0, "narration": "alpha"}
    assert render._tail_led(slide, meta) == []
    seen = []
    real = render.json.dumps
    monkeypatch.setattr(render.json, "dumps", lambda obj, **k: (seen.append(obj), real(obj, **k))[1])
    plain = render._fingerprint(slide, meta, 1920, 1080, 1, True, False)
    assert "tail" not in seen[-1]
    monkeypatch.setattr(render, "_tail_led", lambda s, m: [0])
    assert render._fingerprint(slide, meta, 1920, 1080, 1, True, False) != plain
    assert seen[-1].get("tail") == "led1"


# ── through Chrome: the frames that ship ──────────────────────────────────────────────────────────────────────
def _chrome_present():
    return scenes._chrome_bin({}) is not None


needs_chrome = pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")


def _shipped(tmp_path, props, frames, meta, text):
    """Opacity of `text` on each SHIPPED frame (captures + their copies), via keyframe_qa's census."""
    import keyframe_qa as kq
    from urllib.parse import quote
    plan = scenes.html_capture_plan(props, meta, frames, 1)
    url = "file://" + quote(str(tmp_path / "pages" / "p.html"))
    q = (f"?p=0&cues={plan['cue_param']}&dur={frames / FPS:.3f}" if plan["cue_param"] is not None else "?p=0")
    chrome = kq._open_cdp({}, 1920, 1080)
    assert chrome, "no CDP Chrome"
    try:
        chrome.shot(url + q, str(tmp_path / "p0.jpg"))
        plist = [p for _i, p in plan["shots"]]
        r = chrome._cmd("Runtime.evaluate", {"expression": kq._GLIDE_JS_TMPL % (len(plist), json.dumps(plist)),
                                             "returnByValue": True}, chrome.sid)
        raw = json.loads(r["result"]["result"]["value"])
    finally:
        chrome.close()
    at = {i: raw[str(n)]["lines"] for n, (i, _p) in enumerate(plan["shots"])}
    src = dict(plan["copies"])
    out = []
    for i in range(frames):
        j = i
        while j in src:
            j = src[j]
        out.append(next((ln["o"] for ln in at[j] if ln["t"] == text), 0.0))
    return out


@needs_chrome
def test_a_fade_cued_on_the_last_word_is_whole_before_the_dip(tmp_path):
    # measured before the fix: 0.65 opacity when the 0.2 s dip began (cue at 88% of a 4 s scene)
    props = _write(tmp_path, '<div class="stage"><div class="reveal" data-cue-index="0" data-cue="alpha">ALPHA</div>'
                             '<div class="reveal" data-cue-index="1" data-cue="omega">OMEGA</div></div>',
                   words=[{"w": "alpha", "t": 0.5}, {"w": "omega", "t": 3.52}])
    meta = {"_out": str(tmp_path), "fps": FPS, "_narration": "alpha omega", "_slide": {}}
    ops = _shipped(tmp_path, props, 4 * FPS, meta, "OMEGA")
    dip_starts = 4 * FPS - 1 - int(0.2 * FPS)
    assert ops[dip_starts] >= 0.99, ops[-12:]


@needs_chrome
def test_keyframe_qa_reads_a_late_reveal_as_late_and_a_cued_one_as_on_its_word(tmp_path):
    import keyframe_qa as kq
    import sync_qa as sq
    body = ('<div class="stage"><div class="reveal" data-cue-index="0" data-cue="alpha">ALPHA</div>'
            '<div class="reveal" data-cue-index="1" data-cue="omega">BETA</div></div>')
    _write(tmp_path, body, words=[{"w": "alpha", "t": 0.5}, {"w": "beta", "t": 1.5}, {"w": "omega", "t": 4.5}])
    s = {"index": 1, "type": "html", "props": {"html": "pages/p.html"}, "narration": "alpha beta omega",
         "duration": 6.0}
    from urllib.parse import quote
    chrome = kq._open_cdp({}, 1920, 1080)
    assert chrome
    try:
        recs = kq._sync_records(chrome, str(tmp_path), s, {"fps": FPS},
                                "file://" + quote(str(tmp_path / "pages" / "p.html")))
    finally:
        chrome.close()
    by = {r["text"]: r for r in recs}
    assert sq.level(by["ALPHA"]) == "ok" and abs(by["ALPHA"]["lag"]) < 0.6, by["ALPHA"]
    # BETA is said at 1.5 s but cued to "omega" (4.5 s): three seconds late, an ERROR the gate reports
    assert sq.level(by["BETA"]) == "error" and by["BETA"]["lag"] == pytest.approx(3.0, abs=0.4), by["BETA"]
    issues, _adv = kq._sync_verdict(recs)
    assert any("BETA" in x and "data-cue" in x for x in issues)
