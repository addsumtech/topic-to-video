"""promo_film: the shot-table check refuses what would render wrong, and the sound is pinned to the table's actions."""
import os
import sys

import pytest

os.environ["TOPIC_TO_VIDEO_PROMO_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_promo_ledger_test.json")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import promo_film as pf  # noqa: E402


@pytest.fixture
def film(tmp_path):
    from PIL import Image
    Image.new("RGB", (800, 600), "white").save(tmp_path / "page.png")    # a 2x capture: CSS 400x300
    Image.new("RGB", (64, 64), "white").save(tmp_path / "other.png")
    (tmp_path / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    return tmp_path


def page(**kw):
    s = {"kind": "page", "dur": 90, "src": "page.png", "w": 400, "h": 300,
         "keys": [{"f": 0, "cx": 200, "cy": 150, "zoom": 1.2}, {"f": 40, "cx": 260, "cy": 150, "zoom": 1.8}],
         "layers": [{"kind": "pop", "box": {"x": 10, "y": 10, "w": 100, "h": 40}, "at": 10}]}
    s.update(kw)
    return s


def test_a_clean_table_passes(film):
    spec = {"shots": [{"kind": "brand", "dur": 80, "mark": "mark.svg", "aspect": 1}, {"kind": "title", "dur": 56, "text": "One *idea.*"}, page(),
                      {"kind": "outro", "dur": 120, "mark": "mark.svg", "aspect": 1, "recall": [2]}]}
    errs, adv = pf.check(spec, str(film))
    assert errs == [] and adv == []


@pytest.mark.parametrize("bad, words", [
    (page(src="missing.png"), "does not exist"),
    (page(w=800, h=600), "CSS size"),                                               # the 2x pixels taken as CSS px
    (page(keys=[{"f": 0, "cx": 200, "cy": 150, "zoom": 2.6}]), "density"),             # an upsampled texture
    (page(keys=[{"f": 30, "cx": 1, "cy": 1, "zoom": 1}, {"f": 10, "cx": 1, "cy": 1, "zoom": 1}]), "out of order"),
    (page(keys=[{"f": 0, "cx": 900, "cy": 150, "zoom": 1}]), "off the capture"),
    (page(layers=[{"kind": "lift", "box": {"x": 350, "y": 10, "w": 100, "h": 40}, "at": 5, "until": 30}]), "outside"),
    (page(layers=[{"kind": "pop", "box": {"x": 10, "y": 10, "w": 20, "h": 20}, "at": 4, "src": "other.png",
                   "srcBox": {"x": 25, "y": 25, "w": 20, "h": 20}}]), "srcBox"),      # crop past the OTHER capture's edge
    (page(layers=[{"kind": "sparkles", "at": 3}]), "unknown layer"),
    (page(cut="wipe"), "cut must be"),
])

def test_defects_stop_the_render_by_name(film, bad, words):
    errs, _ = pf.check({"shots": [bad]}, str(film))
    assert any(words in e for e in errs), errs


def test_outro_recalls_page_shots_only(film):
    errs, _ = pf.check({"shots": [{"kind": "title", "dur": 56, "text": "x"},
                                  {"kind": "outro", "dur": 120, "mark": "mark.svg", "aspect": 1, "recall": [0]}]}, str(film))
    assert any("recall" in e for e in errs) and any("there are none" in e for e in errs)


def test_low_contrast_accent_ink_is_refused(film):
    errs, _ = pf.check({"look": {"accentInk": "#16805f", "paper": "#f6f5f1"}, "shots": [page()]}, str(film))
    assert any("4.5:1" in e for e in errs)
    errs, _ = pf.check({"look": {"accentInk": "#137a5a", "paper": "#f6f5f1"}, "shots": [page()]}, str(film))
    assert errs == []


def test_shot_lengths_outside_the_band_are_advised_not_refused(film):
    errs, adv = pf.check({"shots": [{"kind": "title", "dur": 150, "text": "x"}, page(dur=20)]}, str(film))
    assert errs == [] and len(adv) == 2


def test_sound_is_pinned_to_the_table():
    spec = {"shots": [
        {"kind": "title", "dur": 50, "text": "x"},
        page(layers=[{"kind": "pop", "box": {}, "at": 10}, {"kind": "pop", "box": {}, "at": 11}, {"kind": "pop", "box": {}, "at": 16},
                     {"kind": "type", "box": {}, "at": 20, "text": "abcd", "cpf": 1},
                     {"kind": "cursor", "path": [{"f": 50, "x": 0, "y": 0}], "clicks": [60]}]),
        {"kind": "outro", "dur": 120, "mark": "m.svg", "aspect": 1, "stampAt": 40}]}
    cues = pf.plan_sfx(spec)
    names = [c for _, c, _ in cues]
    # every carried cut is one air sound ON the cut; the camera travels 60 px and 0.6 zoom in 40 frames: one whoosh
    # at the move's middle
    assert (50, "whoosh") in [(f, c) for f, c, _ in cues] and (50 + 90, "whoosh") in [(f, c) for f, c, _ in cues]
    assert (50 + 20, "whoosh") in [(f, c) for f, c, _ in cues]
    # pops one frame apart are ONE sound; 5 frames apart, two
    assert names.count("drop") == 2
    assert [f for f, c, _ in cues if c == "key"] == [50 + 20, 50 + 22]
    assert (50 + 62, "click") in [(f, c) for f, c, _ in cues]
    # the close: light swells under the recalled wall and the impact lands as the lockup forms — no synthesised bell
    o = 50 + 90
    assert [(f, c) for f, c, _ in cues if c in ("swell", "impact")] == [(o + 6, "swell"), (o + 40 + 10, "impact")]
    assert not {"reveal", "chime", "sparkle", "tick", "pop"} & set(names), "a synthesised tone in the promo's sound"
    assert all(c in pf.BANK or c in ("whoosh", "swell", "impact") for c in names), names
    # a film cut hard has no air on its cuts
    hard = pf.plan_sfx(dict(spec, cut="hard"))
    assert (50, "whoosh") not in [(f, c) for f, c, _ in hard]
    assert cues == sorted(cues)


@pytest.mark.parametrize("accent", ["#ffd400", "#57bf9c", "#6965db", "#e8452c", "#111111", "#ffffff"])
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_a_look_derived_from_any_accent_keeps_its_type_legible(accent, mode):
    look = pf.derive_look({"accent": accent, "mode": mode})
    assert pf._contrast(look["accentInk"], look["paper"]) >= 4.5
    assert pf._contrast(look["ink"], look["paper"]) >= 7
    assert look["accent"] == accent and "mode" not in look
    assert (pf._contrast(look["paper"], "#000000") < 7) == (mode == "dark")


def test_given_look_fields_win(film):
    look = pf.derive_look({"accent": "#57bf9c", "paper": "#f6f5f1", "accentInk": "#137a5a"})
    assert look["paper"] == "#f6f5f1" and look["accentInk"] == "#137a5a"


def test_aspect_table_matches_the_compositions():
    import re
    root = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    ts = dict((k, (int(a), int(b))) for k, a, b in re.findall(r"'(\d+:\d+)': \[(\d+), (\d+)\]", root.split("const ASPECTS")[1].split("};")[0]))
    assert ts == pf.ASPECTS


def test_zoom_cap_is_on_effective_density(film):
    # zoom 3 on a 1920 reference is 1.69 px/CSS px on a 1080-wide 9:16 frame: inside a 2x capture's density
    tall = {"aspect": "9:16", "shots": [page(keys=[{"f": 0, "cx": 200, "cy": 150, "zoom": 3.0}])]}
    assert pf.check(tall, str(film))[0] == []
    wide = {"shots": [page(keys=[{"f": 0, "cx": 200, "cy": 150, "zoom": 3.0}])]}
    assert any("density" in e for e in pf.check(wide, str(film))[0])


def test_the_page_camera_keeps_its_stillness_rules():
    """The four things that made a page step or shimmer (picture_glide_qa measures the result; these pin the causes):
    laid out once and moved by one transform, the raster pinned across render tabs, creeping segments collapsed into
    holds, landings with linear deceleration."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "promo", "PageCam.tsx"),
               encoding="utf-8").read()
    assert "willChange: 'transform'" in src
    assert "zoom: raster" in src and "scale3d(${s}, ${s}, 1)" in src
    assert "const CREEP = 8;" in src and "if (peak < CREEP)" in src
    assert "Math.cos(Math.PI * Math.pow(" in src          # the sine-bump landing
    assert "Math.exp(-(rx * rx + ry * ry + rz * rz) / 18)" in src   # containment smooth in the tilt


def test_a_close_up_past_the_density_needs_a_macro_under_it(film):
    from PIL import Image
    Image.new("RGB", (400, 160), "white").save(film / "hi.png")          # a 4x capture of a 100x40 element
    deep = [{"f": 0, "cx": 200, "cy": 150, "zoom": 1.2}, {"f": 40, "cx": 60, "cy": 30, "zoom": 3.6}]
    errs, _ = pf.check({"shots": [page(keys=deep, layers=[])]}, str(film))
    assert any("macro" in e for e in errs), errs
    macro = {"kind": "macro", "box": {"x": 10, "y": 10, "w": 100, "h": 40}, "src": "hi.png", "scale": 4}
    errs, _ = pf.check({"shots": [page(keys=deep, layers=[macro])]}, str(film))
    assert errs == [], errs
    off = [{"f": 0, "cx": 200, "cy": 150, "zoom": 3.6}]                  # pushed past 2x somewhere the macro is NOT
    assert any("macro" in e for e in pf.check({"shots": [page(keys=off, layers=[macro])]}, str(film))[0])
    wrong = dict(macro, box={"x": 10, "y": 10, "w": 120, "h": 40})        # a capture that is not its box at 4x
    assert any("stretched" in e for e in pf.check({"shots": [page(layers=[wrong])]}, str(film))[0])


def test_every_recorded_take_exists_and_is_licensed():
    import wave
    for name, takes in pf.BANK.items():
        for t in takes:
            p = os.path.join(pf._KENNEY, t + ".wav")
            with wave.open(p, "rb") as w:
                assert w.getnframes() > 0, p
    lic = open(os.path.join(pf._KENNEY, "LICENSE.txt"), encoding="utf-8").read()
    assert "CC0" in lic


def test_structure_is_a_word_and_a_repeat_is_named(tmp_path, monkeypatch):
    led = tmp_path / "ledger.json"
    monkeypatch.setattr(pf, "LEDGER", str(led))
    tour = {"shots": [{"kind": k} for k in ("brand", "title", "page", "page", "title", "page", "outro")]}
    other = {"shots": [{"kind": k} for k in ("page", "statement", "compare", "montage", "statement", "outro")]}
    assert pf.skeleton(tour) == "BCPPCPO" and pf.skeleton(other) == "PSVMSO"
    pf.record_skeleton(tour, str(tmp_path / "filmA"))
    assert any("repeats" in a for a in pf.skeleton_advice(tour, str(tmp_path / "filmB")))
    assert not pf.skeleton_advice(other, str(tmp_path / "filmC"))
    assert not pf.skeleton_advice(tour, str(tmp_path / "filmA"))          # a film never repeats itself


def test_narration_is_the_films_own_choice():
    assert not pf.narrated({"shots": [{"kind": "page"}]})
    assert pf.narrated({"shots": [{"kind": "page", "say": "It compresses images."}]})
    assert not pf.narrated({"narrate": False, "shots": [{"kind": "page", "say": "x"}]})
    assert pf.skeleton({"shots": [{"kind": "page", "say": "x"}]}).endswith("+vo")


def test_subtitles_follow_the_voice(tmp_path):
    words = tmp_path / "w.words.json"
    words.write_text('[{"w":"Open","t":0.0},{"w":"your","t":0.2},{"w":"image.","t":0.4},{"w":"Compare","t":1.1},{"w":"it.","t":1.5}]')
    subs = pf._subtitle_chunks("Open your image. Compare it.", str(words), 2.0, 2.0)
    assert [x[2] for x in subs] == ["Open your image.", "Compare it."]
    assert subs[0][0] == pytest.approx(2.0) and subs[1][0] == pytest.approx(3.1) and subs[1][1] > subs[1][0]


def test_new_kinds_and_the_through_cut_are_checked(film):
    from PIL import Image
    Image.new("RGB", (3840, 2160), "white").save(film / "big.png")       # a 2x capture big enough to fill the frame
    reg = {"src": "big.png", "w": 1920, "h": 1080, "box": {"x": 0, "y": 0, "w": 1600, "h": 900}}
    ok = {"shots": [{"kind": "statement", "dur": 50, "text": "One *line.*", "ground": "accent"},
                    {"kind": "compare", "dur": 60, "a": reg, "b": reg, "cut": "through"},
                    {"kind": "montage", "dur": 40, "items": [reg, reg]}]}
    assert pf.check(ok, str(film))[0] == []
    bad = {"shots": [{"kind": "compare", "dur": 60, "a": reg, "b": dict(reg, box={"x": 1000, "y": 0, "w": 1600, "h": 900})},
                     {"kind": "statement", "dur": 50, "text": "x", "ground": "neon"}]}
    errs = pf.check(bad, str(film))[0]
    assert any("outside" in e for e in errs) and any("ground" in e for e in errs)


# ---- recordings, the count act, the morph cut ----------------------------------------------------------------------

@pytest.fixture
def recording(film):
    import json
    from PIL import Image
    caps = film / "caps"
    caps.mkdir()
    Image.new("RGB", (800, 600), "white").save(caps / "rec.png")
    (caps / "rec.mp4").write_bytes(b"\0")
    lay = {"src": "caps/rec.png", "video": "caps/rec.mp4", "w": 400, "h": 300, "fps": 30, "frames": 90, "elements": [],
           "events": [{"frame": 20, "kind": "click", "x": 100, "y": 80},
                      {"frame": 50, "kind": "drag", "from": [100, 80], "to": [300, 80], "until": 70},
                      {"frame": 200, "kind": "click", "x": 5, "y": 5}]}
    (caps / "rec.layout.json").write_text(json.dumps(lay))
    return film


def rec_shot(**kw):
    s = {"kind": "page", "dur": 60, "recording": "caps/rec.layout.json", "keys": [{"f": 0, "cx": 200, "cy": 150, "zoom": 1.2}]}
    s.update(kw)
    return s


def test_a_recording_shot_takes_its_poster_and_size_from_the_recording(recording):
    errs, _ = pf.check({"shots": [{"kind": "title", "dur": 56, "text": "One *idea.*"}, rec_shot()]}, str(recording))
    assert errs == []
    out = pf.resolve_recordings(str(recording), {"shots": [rec_shot()]})["shots"][0]
    assert (out["src"], out["video"], out["w"], out["h"]) == ("caps/rec.png", "caps/rec.mp4", 400, 300)


def test_a_recording_gets_a_cursor_on_the_recorded_frames_shifted_by_videoStart(recording):
    out = pf.resolve_recordings(str(recording), {"shots": [rec_shot(videoStart=10)]})["shots"][0]
    cur = [a for a in out["layers"] if a["kind"] == "cursor"]
    assert len(cur) == 1
    assert cur[0]["clicks"] == [10]                         # frame 20 of the recording is frame 10 of the shot
    fs = [p["f"] for p in cur[0]["path"]]
    assert fs == sorted(fs) and len(set(fs)) == len(fs)     # a path that only moves forward in time
    assert cur[0]["path"][-1]["x"] == 300 and cur[0]["path"][-1]["f"] == 60   # the drag ends where it was released
    # an event past the shot's end is not drawn; a shot with its own cursor or cursor:false gets none
    assert all(p["f"] <= 60 for p in cur[0]["path"])
    mine = {"kind": "cursor", "path": [{"f": 0, "x": 1, "y": 1}]}
    assert pf.resolve_recordings(str(recording), {"shots": [rec_shot(layers=[mine])]})["shots"][0]["layers"] == [mine]
    assert pf.resolve_recordings(str(recording), {"shots": [rec_shot(cursor=False)]})["shots"][0]["layers"] == []


def test_a_recording_that_is_missing_or_too_short_is_named(recording):
    errs, _ = pf.check({"shots": [rec_shot(recording="caps/nope.json")]}, str(recording))
    assert any("does not exist" in e for e in errs)
    _, adv = pf.check({"shots": [rec_shot(dur=80, videoStart=30)]}, str(recording))
    assert any("run past it" in a for a in adv)


@pytest.mark.parametrize("shots, words", [
    ([page(cut="morph")], "first shot"),
    ([{"kind": "title", "dur": 56, "text": "One *idea.*"}, page(cut="morph", morphFrom={"x": 0.8, "y": 0.1, "w": 0.4, "h": 0.1})], "FRACTIONS"),
    ([page(layers=[{"kind": "count", "box": {"x": 10, "y": 10, "w": 40, "h": 20}, "to": "69"}])], "`to` must be"),
])
def test_morph_and_count_are_refused_when_they_cannot_render(film, shots, words):
    errs, _ = pf.check({"shots": shots}, str(film))
    assert any(words in e for e in errs), errs


def test_a_good_morph_and_count_pass(film):
    shots = [{"kind": "title", "dur": 56, "text": "One *idea.*"},
             page(cut="morph", morphFrom={"x": 0.2, "y": 0.6, "w": 0.1, "h": 0.12},
                  layers=[{"kind": "count", "box": {"x": 10, "y": 10, "w": 40, "h": 20}, "to": 69, "at": 8}])]
    errs, _ = pf.check({"shots": shots}, str(film))
    assert errs == []


def test_a_recording_at_another_rate_is_timed_in_film_frames(recording):
    import json
    lay = json.loads((recording / "caps" / "rec.layout.json").read_text())
    lay.update(fps=10, frames=30)                                # 3 s at 10 fps = 90 film frames
    (recording / "caps" / "rec.layout.json").write_text(json.dumps(lay))
    cur = [a for a in pf.resolve_recordings(str(recording), {"shots": [rec_shot(dur=90)]})["shots"][0]["layers"] if a["kind"] == "cursor"][0]
    assert cur["clicks"] == [60]                                 # recording frame 20 at 10 fps is film frame 60
    _, adv = pf.check({"shots": [rec_shot(dur=90)]}, str(recording))
    assert not any("run past" in a for a in adv), adv            # 90 film frames: it does not run past
    _, adv = pf.check({"shots": [rec_shot(dur=100)]}, str(recording))
    assert any("run past" in a for a in adv)


def test_a_light_mark_on_a_dark_film_gets_no_plate_and_a_dark_one_does(film):
    from PIL import Image
    Image.new("RGBA", (40, 20), (248, 232, 28, 255)).save(film / "light.png")     # a yellow wordmark
    Image.new("RGBA", (40, 20), (20, 20, 24, 255)).save(film / "darkm.png")
    dark = pf.derive_look({"accent": "#f8e81c", "mode": "dark"})
    light = pf.derive_look({"accent": "#f8e81c", "mode": "light"})
    shots = lambda m, **kw: {"shots": [dict({"kind": "outro", "dur": 100, "mark": m, "aspect": 2}, **kw)]}  # noqa: E731
    assert pf.resolve_marks(str(film), shots("light.png"), dark)["shots"][0]["plate"] is False
    assert "plate" not in pf.resolve_marks(str(film), shots("darkm.png"), dark)["shots"][0]       # default: the plate
    assert "plate" not in pf.resolve_marks(str(film), shots("light.png"), light)["shots"][0]      # no plate on light
    assert pf.resolve_marks(str(film), shots("light.png", plate=True), dark)["shots"][0]["plate"] is True   # authored wins
    assert "plate" not in pf.resolve_marks(str(film), shots("mark.svg"), dark)["shots"][0]       # unreadable: default


def test_a_box_written_as_a_list_is_named_not_a_traceback(film):
    shots = [page(layers=[{"kind": "pop", "box": [10, 10, 100, 40], "at": 10, "src": "other.png"},
                          {"kind": "macro", "box": [10, 10, 20, 20], "src": "other.png"}])]
    errs, _ = pf.check({"shots": shots}, str(film))
    assert sum("a box is {" in e for e in errs) == 2, errs
    assert all(e.startswith("shot 0 ") for e in errs if "a box is" in e)       # numbered from 0, as everywhere


@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1"])
def test_a_key_made_by_the_helper_never_frames_past_the_page(film, aspect):
    import random
    rnd = random.Random(3)
    for _ in range(40):
        z = rnd.uniform(1.0, 2.0)
        k = pf.key(0, rnd.uniform(-300, 1100), rnd.uniform(-300, 900), z, 400, 300, aspect=aspect)
        shot = page(keys=[k], layers=[])
        _, adv = pf.check({"aspect": aspect, "shots": [shot]}, str(film))
        assert not any("past the page's edge" in a for a in adv), (k, adv)
    tilted = pf.key(0, -500, 150, 1.2, 400, 300, ry=12)
    assert tilted["cx"] == -500                                   # a tilted object shot is not clamped


def test_a_recordings_typing_and_drag_are_heard_on_their_frames(recording):
    import json
    lay = json.loads((recording / "caps" / "rec.layout.json").read_text())
    lay["events"] = [{"frame": 5, "kind": "click", "x": 50, "y": 50},
                     {"frame": 5, "kind": "type", "text": "hello", "until": 15},
                     {"frame": 30, "kind": "drag", "from": [100, 80], "to": [300, 80], "until": 50}]
    (recording / "caps" / "rec.layout.json").write_text(json.dumps(lay))
    spec = pf.resolve_recordings(str(recording), {"shots": [rec_shot(dur=60)]})
    cues = pf.plan_sfx(spec, placed=True)
    keys = [f for f, c, g, h in cues if c == "key"]
    assert keys[:3] == [5, 9, 13] and 50 in keys                 # 'hello' typed 5-15: a key per 2 chars; the release
    assert (30, "click") in [(f, c) for f, c, g, h in cues]       # the drag's press
    clicks = [f for f, c, g, h in cues if c == "click"]
    assert clicks.count(7) == 1                                   # the click sounds ONCE (the cursor act's), not twice
    nocur = pf.plan_sfx(pf.resolve_recordings(str(recording), {"shots": [rec_shot(dur=60, cursor=False)]}), placed=True)
    assert [f for f, c, g, h in nocur if c == "click"].count(7) == 1   # cursor off: still heard, from the recording


def test_a_caption_on_the_pages_own_text_is_advised(tmp_path):
    import json
    from PIL import Image
    Image.new("RGB", (3840, 3200), "white").save(tmp_path / "p.png")       # a page taller than the frame
    (tmp_path / "p.layout.json").write_text(json.dumps({"elements": [
        {"x": 70, "y": 975, "w": 260, "h": 30, "text": "About  Source  Twitter"},
        {"x": 900, "y": 100, "w": 300, "h": 40, "text": "Heading"}]}))
    still = [{"f": 0, "cx": 960, "cy": 540, "zoom": 1.0}]
    shot = {"kind": "page", "dur": 90, "src": "p.png", "w": 1920, "h": 1600, "keys": still, "caption": {"text": "Every theme", "at": 8},
            "layers": [{"kind": "ring", "box": {"x": 900, "y": 100, "w": 300, "h": 40}, "at": 10}]}
    # no corner given: it moves off the footer by itself, and nothing is left to advise
    _, adv = pf.check({"shots": [shot]}, str(tmp_path))
    assert not any("caption" in a and " covers " in a for a in adv), adv
    moved = pf.place_captions(str(tmp_path), {"shots": [shot]})["shots"][0]["caption"]
    assert moved.get("pos") in ("br", "tl", "tr")
    # a corner the author PINNED is judged where it was put
    pinned = dict(shot, caption={"text": "Every theme", "at": 8, "pos": "bl"})
    _, adv = pf.check({"shots": [pinned]}, str(tmp_path))
    assert any("caption" in a and "About  Source" in a for a in adv), adv
    # the camera lifts the footer out of the band (a legal move: the page runs on below): no advisory
    up = dict(pinned, keys=[{"f": 0, "cx": 960, "cy": 760, "zoom": 1.0}])
    _, adv = pf.check({"shots": [up]}, str(tmp_path))
    assert not any(" covers " in a for a in adv), adv
    # a narrated shot's subtitle, centred, over a centred line of the page's text
    (tmp_path / "p.layout.json").write_text(json.dumps({"elements": [{"x": 700, "y": 960, "w": 520, "h": 40, "text": "Centre text"}]}))
    said = dict(shot, caption=None, say="Turn code into images.", layers=[])
    _, adv = pf.check({"shots": [said]}, str(tmp_path))
    assert not any("subtitle" in a for a in adv), adv             # the top is clear: the subtitle goes up, no advisory
    placed = pf.place_subtitles(str(tmp_path), {"shots": [said], "subtitles": [{"from": 10, "to": 60, "text": "Turn code into images."}]})
    assert placed["subtitles"][0]["pos"] == "top"
    # text at the top AND the bottom: nowhere to go — advised
    (tmp_path / "p.layout.json").write_text(json.dumps({"elements": [{"x": 700, "y": 960, "w": 520, "h": 40, "text": "Centre text"},
                                                                     {"x": 700, "y": 80, "w": 520, "h": 40, "text": "Top text"}]}))
    _, adv = pf.check({"shots": [said]}, str(tmp_path))
    assert any("subtitle" in a and "Centre text" in a for a in adv), adv
    kept = pf.place_subtitles(str(tmp_path), {"shots": [said], "subtitles": [{"from": 10, "to": 60, "text": "Turn code into images."}]})
    assert "pos" not in kept["subtitles"][0]


def test_a_subtitle_never_moves_onto_the_shots_subject(tmp_path):
    import json
    from PIL import Image
    Image.new("RGB", (3840, 2160), "white").save(tmp_path / "p.png")
    (tmp_path / "p.layout.json").write_text(json.dumps({"elements": [{"x": 700, "y": 960, "w": 520, "h": 40, "text": "Footer"}]}))
    still = [{"f": 0, "cx": 960, "cy": 540, "zoom": 1.0}]
    callout = {"kind": "callout", "x": 900, "y": 300, "lx": 760, "ly": 90, "at": 0, "text": "Side by side", "kicker": "ORIGINAL"}
    shot = {"kind": "page", "dur": 90, "src": "p.png", "w": 1920, "h": 1080, "keys": still, "say": "Open an image and compare.",
            "layers": [callout]}
    placed = pf.place_subtitles(str(tmp_path), {"shots": [shot], "subtitles": [{"from": 10, "to": 60, "text": "Open an image and compare."}]})
    assert "pos" not in placed["subtitles"][0]             # the top holds the callout's label: it stays low, on the footer
    _, adv = pf.check({"shots": [shot]}, str(tmp_path))
    assert any("subtitle covers" in a and "'Footer'" in a and "bottom band" in a for a in adv), adv
    # the hero under the low band, plain page text at the top: up it goes (the subject costs more)
    hero = dict(shot, layers=[{"kind": "ring", "box": {"x": 760, "y": 955, "w": 400, "h": 50}, "at": 0}])
    (tmp_path / "p.layout.json").write_text(json.dumps({"elements": [{"x": 700, "y": 960, "w": 520, "h": 40, "text": "862 kB"},
                                                                     {"x": 800, "y": 80, "w": 200, "h": 30, "text": "Reduce palette"}]}))
    placed = pf.place_subtitles(str(tmp_path), {"shots": [hero], "subtitles": [{"from": 10, "to": 60, "text": "Open an image and compare."}]})
    assert placed["subtitles"][0]["pos"] == "top"


def test_narration_falls_back_to_the_offline_voice_and_cuts_cjk_lines(tmp_path, monkeypatch):
    import re
    import shutil
    import tts
    assert [p for p in re.split(pf.SPLIT_RE, "磁共振成像用磁场成像。它不使用电离辐射。") if p.strip()] == ["磁共振成像用磁场成像。", "它不使用电离辐射。"]
    assert [p for p in re.split(pf.SPLIT_RE, "第一步，把图片拖进来，然后选择你想要的压缩格式和质量参数。") if p.strip()] == \
        ["第一步，把图片拖进来，", "然后选择你想要的压缩格式和质量参数。"]
    if not shutil.which("say"):
        pytest.skip("no macOS say")

    def offline(*a, **k):
        raise RuntimeError("offline")
    monkeypatch.setattr(tts, "_edge", offline)
    spec = {"narrate": True, "language": "en", "shots": [{"kind": "statement", "dur": 30, "text": "x",
                                                          "say": "Squoosh makes images small. It runs in your browser."}]}
    out, clips = pf.voice_pass(str(tmp_path), spec)
    assert clips and clips[0][1].endswith(".say.wav") and os.path.getsize(clips[0][1]) > 1000
    assert out["shots"][0]["dur"] > 30                                   # the voice still sets the shot's length
    subs = out["subtitles"]
    assert [x["text"] for x in subs] == ["Squoosh makes images small.", "It runs in your browser."]
    assert subs[0]["to"] == subs[1]["from"] and subs[1]["to"] <= out["shots"][0]["dur"]


def test_a_montage_or_compare_region_is_held_to_the_captures_density(film):
    small = {"src": "page.png", "w": 400, "h": 300, "box": {"x": 0, "y": 0, "w": 200, "h": 150}}   # 2x capture, 200 px wide
    errs, _ = pf.check({"shots": [{"kind": "montage", "dur": 48, "items": [small]}]}, str(film))
    assert any("past the capture's 2x" in e for e in errs), errs
    errs, _ = pf.check({"shots": [{"kind": "compare", "dur": 60, "a": small, "b": small}]}, str(film))
    assert any("past the capture's 2x" in e for e in errs), errs


def test_a_white_mark_on_a_light_film_is_advised(film):
    from PIL import Image
    Image.new("RGBA", (40, 20), (255, 255, 255, 255)).save(film / "white.png")
    o = {"kind": "outro", "dur": 120, "mark": "white.png", "aspect": 2, "recall": [0]}
    _, adv = pf.check({"look": {"accent": "#2b6cb0", "mode": "light"}, "shots": [page(), o]}, str(film))
    assert any("mark is light" in a for a in adv), adv
    _, adv = pf.check({"look": {"accent": "#2b6cb0", "mode": "dark"}, "shots": [page(), o]}, str(film))
    assert not any("mark is light" in a for a in adv), adv


# ---- staging: the product as objects (object / wall shots) ---------------------------------------------------------

@pytest.fixture
def parts(film):
    from PIL import Image
    Image.new("RGB", (1200, 1404), "white").save(film / "panel.png")      # a 4x part of a 300x351 CSS px panel
    Image.new("RGB", (300, 100), "white").save(film / "tiny.png")         # a 1x grab of the same panel's corner
    return film


def obj(**kw):
    s = {"kind": "object", "dur": 90, "world": "glow",
         "items": [{"src": "panel.png", "w": 300, "h": 351, "width": 0.3, "at": 0,
                    "acts": [{"kind": "count", "box": {"x": 10, "y": 10, "w": 40, "h": 20}, "to": 69, "at": 20}]}],
         "label": {"index": "01", "kicker": "Compress", "text": "2.79 MB in.\n*862 kB out.*"}}
    s.update(kw)
    return s


def test_an_object_shot_passes_and_is_heard_where_it_lands(parts):
    errs, _ = pf.check({"shots": [obj()]}, str(parts))
    assert errs == [], errs
    cues = pf.plan_sfx({"shots": [obj()]}, placed=True)
    by = [(f, c) for f, c, g, h in cues]
    assert (6, "whoosh") in by and (22, "drop") in by                     # it comes in, and lands
    land = [h for f, c, g, h in cues if c == "drop"][0]
    assert land > 0.2                                                     # a label on the left: the object lands right
    assert [f for f, c in by if c == "key"][:2] == [20, 26]               # its count, heard
    assert pf.skeleton({"shots": [obj(), {"kind": "wall", "dur": 90, "tiles": []}]}) == "XW"


@pytest.mark.parametrize("bad, words", [
    (obj(items=[]), "needs items"),
    (obj(world="neon"), "world must be"),
    (obj(label={"text": " "}), "label needs"),
    (obj(items=[{"src": "tiny.png", "w": 300, "h": 351, "width": 0.4}]), "upsampled"),          # 300 px shown 768 px wide
    (obj(items=[{"video": "nope.mp4", "w": 300, "h": 200, "width": 0.3}]), "needs `crop`"),
    (obj(items=[{"src": "panel.png", "h": 351}]), "w and h"),
])
def test_an_object_shot_that_would_render_wrong_is_refused(parts, bad, words):
    errs, _ = pf.check({"shots": [bad]}, str(parts))
    assert any(words in e for e in errs), errs


def test_a_wall_is_checked_heard_and_judged_by_the_glide_gate(parts, tmp_path):
    import json
    import picture_glide_qa as pg
    tiles = [{"src": "panel.png", "w": 300, "h": 351}] * 6
    wall = {"kind": "wall", "dur": 90, "tiles": tiles, "cols": 3, "tile": 560}
    assert pf.check({"shots": [wall]}, str(parts))[0] == []
    cues = pf.plan_sfx({"shots": [wall]}, placed=True)
    deals = [h for f, c, g, h in cues if c == "deal"]
    assert len(deals) == 6 and deals[0] < 0 < deals[2]                    # dealt across its columns, left to right
    small = dict(wall, tiles=[{"src": "tiny.png", "w": 300, "h": 351}])
    assert any("upsampled" in e for e in pf.check({"shots": [small]}, str(parts))[0])
    sp = tmp_path / "s.json"
    sp.write_text(json.dumps({"shots": [obj(), wall, {"kind": "statement", "dur": 40, "text": "x"}]}))
    assert [k for k, a, b in pg.spans_of(str(tmp_path), str(sp))] == [1, 2]   # the object and the wall, not the card


def test_a_staged_outro_needs_no_page_shots_and_names_its_world(parts):
    o = {"kind": "outro", "dur": 120, "mark": "panel.png", "aspect": 1, "world": "glow", "stampAt": 34}
    assert pf.check({"shots": [obj(), o]}, str(parts))[0] == []                  # objects only: the staged outro is fine
    errs = pf.check({"shots": [obj(), dict(o, world="neon")]}, str(parts))[0]
    assert any("world must be" in e for e in errs)
    errs = pf.check({"shots": [obj(), dict(o, world=None)]}, str(parts))[0]     # an unstaged outro still needs pages
    assert any("no page" in e or "there are none" in e for e in errs)
