"""The craft pass, checked on inputs it was not tuned on (references/craft-research.md).

  · a stage move lands ON its target — no last-frame click into place — at any duration and frame rate, and a move
    retargeted mid-way keeps its speed;
  · the platform-safe profile is a 9:16 thing: a 4:5 or 3:4 film is a feed post, not a full-screen one;
  · the 3:4 cover is cut from any portrait frame without padding it black;
  · the SFX bus is gain-staged under a voice that exists, and left alone when there is none;
  · a board's meta.safe_zone is checked before the voice is made.
"""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "tests"))
import _tsprobe  # noqa: E402

needs_node = pytest.mark.skipif(not _tsprobe.available(), reason="needs node + the remotion toolchain")


@needs_node
def test_a_move_lands_on_its_target_without_a_last_frame_jump():
    out = _tsprobe.run_ts("import {moveShare} from %s;" % _tsprobe.mod("stageRun.tsx"), """
      out.runs = [];
      for (const fps of [24, 30, 60]) for (const d of [4, 6, 9, 12, 18, 30, 45, 90]) {
        const v = []; for (let f = 0; f <= d + 2; f++) v.push(moveShare(f, d, fps));
        out.runs.push({fps, d, v});
      }""")
    for r in out["runs"]:
        v, d = r["v"], r["d"]
        assert v[0] == 0 and v[d] == 1 and v[d + 1] == 1, r
        steps = [v[i + 1] - v[i] for i in range(d)]
        assert min(steps) >= 0, ("a move went backwards", r)
        # the landing is continuous: the last step exceeds the one before it by under 0.2% of the move
        # (Remotion's own stretched spring jumped 0.4% on the last frame after a 0.1% step: 3.7 px on a 900 px move)
        assert steps[-1] - steps[-2] <= 0.002, ("a last-frame jump", r["fps"], d, steps[-3:])
        # front-loaded: half way well before half the time (premium UI curves: 13-16%; easeInOutCubic: 49%)
        half = next(i for i, x in enumerate(v) if x >= 0.5)
        assert half <= max(2, 0.35 * d), ("not front-loaded", r["fps"], d, half)


@needs_node
def test_springs_that_add_up_land_exactly_and_carry_their_speed_through_a_retarget():
    out = _tsprobe.run_ts("import {springSum} from %s;" % _tsprobe.mod("stageRun.tsx"), """
      // one actor x: 0 -> 900 over frames 0..24, retargeted at frame 10 to 1500 (landing at frame 34)
      const keys = [{from: -1, to: 0, step: -1, state: {x: 0}},
                    {from: 0, to: 24, step: 0, state: {x: 900}},
                    {from: 10, to: 34, step: 1, state: {x: 1500}}];
      for (const feel of ['settle', 'glide']) {
        const xs = [];
        for (let f = 0; f <= 60; f++) {
          const now = {frame: f, fps: 30, keys, reduced: false};
          xs.push((springSum(now, (s) => s.x, {feel}) as number));
        }
        out[feel] = xs;
      }""")
    for feel in ("settle", "glide"):
        xs = out[feel]
        assert xs[-1] == 1500 and xs[40] == 1500, (feel, xs[30:])
        v = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
        # no stall at the retarget: the speed through frames 9..12 never drops under half of the speed coming in
        assert min(v[9:12]) >= 0.5 * v[8], (feel, v[6:14])
        # the end is continuous: no frame moves more than the frame before it once the speed has fallen under 5 px
        tail = [i for i in range(20, 40) if abs(v[i - 1]) < 5]
        assert all(abs(v[i]) <= abs(v[i - 1]) + 1.0 for i in tail), (feel, v[20:40])


@needs_node
def test_the_platform_profile_is_for_full_screen_vertical_films_only():
    out = _tsprobe.run_ts("import {safeProfile} from %s;" % _tsprobe.mod("safeZone.ts"), """
      out.r = [[1080, 1920], [1080, 1350], [1080, 1440], [1080, 1080], [1920, 1080], [720, 1280]]
        .map(([w, h]) => !!safeProfile('social', w, h));""")
    assert out["r"] == [True, False, False, False, False, True]
    import render_remotion as rr
    assert [rr.safe_zone({}, a) for a in ("9:16", "4:5", "1:1", "16:9", "4:3")] == ["social", None, None, None, None]
    assert rr.safe_zone({"safe_zone": "none"}, "9:16") is None


@pytest.mark.parametrize("W,H,top,bottom", [(1080, 1920, 54, 1388), (1080, 1920, 15, 1663), (1080, 1350, 30, 1100),
                                            (720, 1280, 20, 1100)])
def test_the_cover_is_a_3x4_card_with_no_padding_beyond_the_frame(W, H, top, bottom):
    Image = pytest.importorskip("PIL.Image")
    import cover
    im = Image.new("RGB", (W, H), (20, 30, 60))
    for y in range(int(top), int(bottom), 40):                 # stripes: the picture, to find in the card
        im.paste((230, 200, 40), (100, y, W - 100, y + 6))
    c = cover.card(im, top, bottom)
    assert c.size == (cover.COVER_W, cover.COVER_H)
    px = c.load()
    corners = [px[x, y] for x in (0, c.width - 1) for y in (0, c.height - 1)]
    assert all(p != (0, 0, 0) for p in corners), "the card was padded black past the frame"
    if H * cover.COVER_W >= W * cover.COVER_H:                  # a tall frame keeps the whole picture span
        rows = [y for y in range(c.height) if px[c.width // 2, y][0] > 150]
        span = (rows[-1] - rows[0]) if rows else 0
        assert span >= 0.85 * c.height * min(1.0, (bottom - top - 40) / (W * 4 / 3)), "the picture was cut"


def test_the_sfx_bus_is_capped_under_a_real_voice_only():
    import sfx
    assert sfx.sfx_peak_cap(None) is None
    assert sfx.sfx_peak_cap(0.0) is None
    assert sfx.sfx_peak_cap(10 ** (-60 / 20)) is None           # a silent track: the cues are not muted to it
    cap = sfx.sfx_peak_cap(0.8)
    assert cap == pytest.approx(0.8 * 10 ** (-6 / 20))


def test_an_unknown_safe_zone_is_an_error_before_the_voice_is_made(tmp_path):
    import validate
    board = {"meta": {"aspect": "9:16", "renderer": "remotion", "safe_zone": "tiktok"},
             "slides": [{"index": 1, "narration": "x", "caption": "x", "shot": "TermTable",
                         "shot_props": {"kicker": "K", "rows": [["a", "1"]]}}]}
    json.dump(board, open(os.path.join(str(tmp_path), "storyboard.json"), "w"))
    res = validate.check(str(tmp_path), pre_tts=True)
    errs = res[0] if isinstance(res, tuple) else res.get("errors", [])
    assert any("safe_zone" in e for e in errs), errs


@needs_node
def test_lit_surfaces_and_motion_blur_are_measured_quantities():
    surf = '"' + os.path.join(_ROOT, "remotion", "src", "stage", "surface.tsx") + '"'
    out = _tsprobe.run_ts("import {elevation, sheen, blurOf, topLight} from %s;" % surf, """
      out.elev = elevation(1, 1080, '#E9EAEE', false);
      out.elevDark = elevation(1, 1080, '#101114', true);
      out.rest = sheen(2.2, 0); out.turned = sheen(-18, 14);
      out.still = blurOf(0.39, 0.2); out.fast = blurOf(0, 40, 1); out.small = blurOf(0, 40, 0.5);
      out.capped = blurOf(900, 0);
      out.top = [topLight(1080, true), topLight(1080, false)];""")
    layers = out["elev"].split("), ")
    assert len(layers) == 5, out["elev"]                 # five layers, offsets doubling from one light above
    offs = [float(l.split("px")[0].split()[-1]) for l in layers]
    assert all(abs(offs[i + 1] / offs[i] - 2) < 1e-6 for i in range(4)), offs
    assert "rgba(0, 0, 0" in out["elevDark"] and "rgba(0, 0, 0" not in out["elev"], "a light ground's shadow is tinted"
    assert out["rest"] is None, "the sheen must not sit on a face at rest (where it is read)"
    assert out["turned"] and out["turned"]["opacity"] > 0.1
    assert out["still"] is None, "the idle float (under half a px a frame) must not blur"
    assert out["fast"]["sy"] == pytest.approx(0.144 * 40) and out["fast"]["sx"] == 0
    assert out["small"]["sy"] == pytest.approx(2 * 0.144 * 40), "the smear is in the element's own (scaled) px"
    assert out["capped"]["sx"] == 40
    assert out["top"][0] and not out["top"][1]
