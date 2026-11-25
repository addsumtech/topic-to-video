"""A real app recording edited as a tutorial: scripts/app_record.py's pure parts (steps checked, the log aligned to the
video by its own frame changes, the record written) and assets/html/screenrec.js (each action landing on its word,
holds and capped speed-ups, a close-up that follows the action within the recording's pixels, click rings, the frame
drawn), on a synthetic recording — the live capture needs macOS Screen Recording and is proven on a real film."""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common  # noqa: E402
import app_record as ar  # noqa: E402

CHROME = _common.find_chrome()
needs_chrome = pytest.mark.skipif(not CHROME, reason="Chrome not installed")


def test_the_committed_bundle_matches_its_source(tmp_path):
    out = tmp_path / "screenrec.js"
    subprocess.run([os.path.join(ROOT, "remotion", "node_modules", ".bin", "esbuild"),
                    os.path.join(ROOT, "assets", "html", "screenrec", "src.js"), "--bundle", "--minify", "--format=iife",
                    "--global-name=ScreenRec", "--log-level=warning", "--outfile=%s" % out], check=True)
    assert out.read_bytes() == open(os.path.join(ROOT, "assets", "html", "screenrec.js"), "rb").read(), \
        "assets/html/screenrec.js is stale: run scripts/build_screenrec_page.sh"


def test_steps_are_checked_all_at_once():
    assert ar.check_steps({"app": "Numbers", "steps": [{"click": [10, 20]}, {"menu": ["Insert", "Chart"]}]}) == []
    errs = ar.check_steps({"app": "Numbers", "window": [100, 900],
                           "steps": [{"click": [1]}, {"type": "x", "key": "a"}, {"menu": ["Insert"]}, {"wait": 99}]})
    assert len(errs) == 5, errs
    assert ar.check_steps({"steps": []})[0].startswith('steps.json needs "app"')


def test_the_log_is_aligned_to_the_video_by_its_own_frame_changes():
    fps, true_off = 30, 0.6
    times = [1.0, 2.5, 4.2, 5.0]
    e = np.random.RandomState(1).rand(fps * 8) * 0.2
    for t in times:
        a = int((t + true_off) * fps)
        e[a:a + 8] += 5.0
    off, conf = ar.align_offset(e, fps, times)
    assert abs(off - true_off) <= 1.0 / fps and conf == 1.0, (off, conf)
    for t in times:                                     # the cursor gliding in before each click changes frames too
        a = int((t + true_off - 0.6) * fps)
        e[a:a + 18] += 1.5
    assert abs(ar.align_offset(e, fps, times)[0] - true_off) <= 1.0 / fps



def test_the_record_is_in_recording_pixels_on_the_videos_clock():
    rec = ar.record_json("Numbers", [80, 60, 800, 500], 2.0, (1600, 1000), 90,
                         [{"kind": "click", "t": 1.0, "t_end": 1.0, "x": 100, "y": 50}], 0.25, 4.0)
    a = rec["actions"][0]
    assert (a["x"], a["y"], a["t"]) == (200, 100, 1.25) and rec["sync"] == {"offset": 0.25, "confidence": 4.0}


def test_no_screen_recording_permission_stops_before_driving_anything(monkeypatch):
    if sys.platform != "darwin":
        pytest.skip("macOS only")

    class R:
        returncode, stdout, stderr = 1, "", "could not create image from display"
    monkeypatch.setattr(ar.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(ar.RecordError, match="Screen & System Audio Recording"):
        ar.preflight()


# ── the edit, on a synthetic recording ──────────────────────────────────────────────────────────────────────────
W, H, N = 800, 500, 90
ACTIONS = [{"i": 0, "kind": "click", "label": "File", "t": 0.5, "t_end": 0.5, "x": 100, "y": 100},
           {"i": 1, "kind": "click", "label": "Chart", "t": 1.5, "t_end": 1.5, "x": 700, "y": 400},
           {"i": 2, "kind": "key", "label": "cmd+s", "t": 2.5, "t_end": 2.5, "x": None, "y": None}]


def _film(d, script, actions=ACTIONS):
    fr = d / "clips" / "rec" / "frames"
    fr.mkdir(parents=True)
    for i in range(N):
        im = Image.new("RGB", (W, H), (240, 240, 244))
        ImageDraw.Draw(im).rectangle((i * 8, 200, i * 8 + 40, 240), fill=(int(i * 2.8), 60, 200))
        im.save(fr / ("%05d.jpg" % (i + 1)), quality=95)
    rec = {"fps": 30, "n": N, "width": W, "height": H, "scale": 1, "window": [0, 0, W, H], "app": "Synth",
           "actions": actions, "sync": {"offset": 0, "confidence": 5}}
    shutil.copy(os.path.join(ROOT, "assets", "html", "screenrec.js"), d)
    (d / "film.html").write_text("""<!doctype html><html><head><meta charset='utf-8'></head>
<body style='margin:0;width:1920px;height:1080px;background:#111'><div id="r"><img><svg></svg></div>
<script src="screenrec.js"></script><script>const REC = %s;
(async () => { %s })().then(() => {}, (e) => { document.title = 'ERR ' + e.message; });
</script></body></html>""" % (json.dumps(rec), script))


def _title(d):
    dom = subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--window-size=1920,1080",
                          "--virtual-time-budget=5000", "--dump-dom", "file://%s" % (d / "film.html")],
                         capture_output=True, text=True, timeout=120).stdout
    t = dom[dom.index("<title>") + 7:dom.index("</title>")].replace("&quot;", '"').replace("&amp;", "&")
    assert not t.startswith("ERR"), t
    return json.loads(t)


def _err(d):
    dom = subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--window-size=1920,1080",
                          "--virtual-time-budget=5000", "--dump-dom", "file://%s" % (d / "film.html")],
                         capture_output=True, text=True, timeout=120).stdout
    return dom[dom.index("<title>") + 7:dom.index("</title>")]


@needs_chrome
def test_each_action_lands_on_its_word_with_holds_between(tmp_path):
    _film(tmp_path, """const E = ScreenRec.edit(REC, {base: 'clips/rec/frames/', box: {x: 100, y: 100, w: 600},
  start: 0, end: 9, anchors: [{action: 0, at: 2.0}, {action: 1, at: 5.0}, {action: 2, at: 6.0}]});
document.title = JSON.stringify([1.5, 2.0, 2.5, 3.5, 4.9, 5.0, 5.5, 6.0, 8.9].map((t) => +E.recAt(t).toFixed(3)));""")
    # 1.5 s before the first click: 1 s of it, held at the start before that; then the result plays (2.0-2.65 ->
    # 0.5-1.15) and holds 0.35 s of recording BEFORE the next click, whose approach then plays into it on its word
    # (5.0), never on it; past the last action it plays on and holds on the last frame
    assert _title(tmp_path) == [0.0, 0.5, 1.0, 1.15, 1.4, 1.5, 2.0, 2.5, 2.967]


@needs_chrome
def test_a_voice_quicker_than_the_hand_is_refused_past_the_speed_limit(tmp_path):
    _film(tmp_path, """ScreenRec.edit(REC, {base: 'f/', box: {x: 0, y: 0, w: 600}, start: 0, end: 9,
  anchors: [{action: 0, at: 2.0}, {action: 1, at: 2.2}]});""")
    assert "would play at 5.0x" in _err(tmp_path) and "at least 0.33 s" in _err(tmp_path)


@needs_chrome
def test_the_close_up_follows_the_action_and_never_draws_past_the_recordings_pixels(tmp_path):
    _film(tmp_path, """let refused = '';
try { ScreenRec.edit(REC, {base: 'f/', box: {x: 0, y: 0, w: 600}, start: 0, end: 9, zoom: 2}); }
catch (e) { refused = e.message; }
const E = ScreenRec.edit(REC, {base: 'clips/rec/frames/', box: {x: 100, y: 100, w: 600}, start: 0, end: 9, zoom: 1.3,
  anchors: [{action: 0, at: 2.0}, {action: 1, at: 5.0}]});
const c = (t) => { const v = E.at(t).view; return [Math.round(v[0] + v[2] / 2), Math.round(v[1] + v[3] / 2)]; };
const s = E.at(5.2);
const el = document.getElementById('r'); await ScreenRec.draw(el, s);
const img = el.querySelector('img');
document.title = JSON.stringify({refused, first: c(1.7), second: c(4.7), rings: s.rings.length,
  later: E.at(5.8).rings.length, src: img.getAttribute('src'), loaded: img.naturalWidth,
  circle: el.querySelectorAll('svg circle').length});""")
    got = _title(tmp_path)
    assert "past its pixels" in got["refused"], got
    # zoom 1.3 = a 615x385 view of the 800x500 window: centred on the click as far as the window's edge allows
    assert got["first"] == [308, 192] and got["second"] == [492, 308], got
    assert got["rings"] == 1 and got["later"] == 0 and got["circle"] == 1, got
    assert got["src"].endswith("/00052.jpg") and got["loaded"] == W, got   # 5.2 s -> 1.5 + 0.2 s of recording


def test_a_menu_item_its_menu_does_not_show_is_refused():
    """The TextEdit run (2026-11-25): with the Font submenu shut, "Bold" reported (-80, 1047) and the driver clicked
    the screen's corner. An item is clicked only where its open menu puts it."""
    title = (205, 0, 52, 24)                       # "Format" in the menu bar
    font = (205, 30, 230, 22)                      # its first item, "Font >"
    assert ar.menu_item_follows(title, font, 1)
    assert ar.menu_item_follows(font, (436, 30, 180, 22), 2)          # the submenu, opened to the right
    assert ar.menu_item_follows(font, (25, 60, 180, 22), 2)           # ... or to the left at the screen's edge
    assert not ar.menu_item_follows(font, (-80, 1047, 160, 22), 2)    # the shut submenu's stale place
    assert not ar.menu_item_follows(title, (600, 30, 120, 22), 1)     # another title's menu
    assert not ar.menu_item_follows(font, (436, 30, 0, 0), 2)         # no size: not on screen


def test_a_double_click_is_a_click_with_clicks_2():
    ok = {"app": "Numbers", "steps": [{"click": [10, 10], "clicks": 2}, {"click_text": "Title", "clicks": 2}]}
    assert ar.check_steps(ok) == []
    bad = {"app": "Numbers", "steps": [{"type": "x", "clicks": 2}, {"click": [1, 1], "clicks": 5}]}
    errs = ar.check_steps(bad)
    assert len(errs) == 2 and all('"clicks"' in e for e in errs), errs


def test_a_shift_click_carries_its_modifier():
    assert ar.check_steps({"app": "Numbers", "steps": [{"click": [1, 1], "mods": "shift"}]}) == []
    errs = ar.check_steps({"app": "Numbers", "steps": [{"click": [1, 1], "mods": "hyper"}, {"key": "a", "mods": "shift"}]})
    assert len(errs) == 2 and all('"mods"' in e for e in errs), errs


def test_a_scroll_is_whole_wheel_lines():
    assert ar.check_steps({"app": "Numbers", "steps": [{"scroll": 10}, {"scroll": -3}]}) == []
    assert len(ar.check_steps({"app": "Numbers", "steps": [{"scroll": 0}, {"scroll": 1.5}, {"scroll": True}]})) == 3


@needs_chrome
def test_a_drag_plays_through_before_the_hold(tmp_path):
    """A 1.5 s drag anchored on its word plays to its end at real speed; the hold comes after it (a 1 s settle froze
    the Numbers chart halfway across, 2026-11-25)."""
    acts = [{"i": 0, "kind": "drag", "label": "move", "t": 0.5, "t_end": 2.0, "x": 300, "y": 300},
            {"i": 1, "kind": "click", "label": "Chart", "t": 2.6, "t_end": 2.6, "x": 700, "y": 400}]
    _film(tmp_path, """const E = ScreenRec.edit(REC, {base: 'clips/rec/frames/', box: {x: 0, y: 0, w: 600},
  start: 0, end: 9, anchors: [{action: 0, at: 1.0}, {action: 1, at: 6.0}]});
document.title = JSON.stringify([2.0, 2.5, 2.8, 4.0, 5.5].map((t) => +E.recAt(t).toFixed(3)));""", acts)
    # 1.0 -> 0.5: real speed through the drag's end (2.0), held 0.35 s of recording before the click (2.25), whose
    # approach runs into it at 6.0
    assert _title(tmp_path) == [1.5, 2.0, 2.25, 2.25, 2.25]


@needs_chrome
def test_keycaps_cursor_and_film_time(tmp_path):
    """What a screen recording cannot show: the held Shift on a click and the Return key get keycaps on the film
    seconds they play; the pointer's place comes from the logged glides (a halo can follow it)."""
    acts = [{"i": 0, "kind": "click", "label": "A1", "t": 0.5, "t_end": 0.5, "x": 100, "y": 100},
            {"i": 1, "kind": "click", "label": "C7", "t": 1.5, "t_end": 1.5, "x": 700, "y": 400, "mods": "shift"},
            {"i": 2, "kind": "key", "label": "Return", "key": "return", "t": 2.5, "t_end": 2.5, "x": None, "y": None}]
    rec_path = [{"t0": 0.0, "t1": 0.5, "x0": 0, "y0": 0, "x1": 100, "y1": 100},
                {"t0": 1.0, "t1": 1.5, "x0": 100, "y0": 100, "x1": 700, "y1": 400}]
    _film(tmp_path, """REC.path = %s;
const E = ScreenRec.edit(REC, {base: 'clips/rec/frames/', box: {x: 0, y: 0, w: 600}, start: 0, end: 9,
  anchors: [{action: 0, at: 1.0}, {action: 1, at: 3.0}, {action: 2, at: 5.0}]});
const k = (t) => E.keys(t).map((c) => c.label);
document.title = JSON.stringify({shift: k(3.1), ret: k(5.2), none: k(4.2), film: +E.filmTime(1.5).toFixed(2),
  cur0: E.cursor(1.0), curMid: E.cursor(2.85).map(Math.round), curEnd: E.cursor(3.5)});""" % json.dumps(rec_path), acts)
    got = _title(tmp_path)
    assert got["shift"] == ["⇧ Shift + click"] and got["ret"] == ["Return ↩"] and got["none"] == [], got
    assert abs(got["film"] - 3.0) < 0.02, got
    assert got["cur0"] == [100, 100] and got["curEnd"] == [700, 400], got
    assert 100 < got["curMid"][0] < 700, got          # mid-glide toward C7, eased
