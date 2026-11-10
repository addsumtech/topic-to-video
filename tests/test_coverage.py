"""Coverage — one beat cut between framings on its voice (scripts/coverage_plan.py, runtime/coverage.tsx)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import coverage_plan as cp                                                       # noqa: E402


def _spans(caption, t0=0.2, step=0.35):
    """Word spans: one per whitespace word (Latin) at a steady pace."""
    out, t, a = [], t0, 0
    for w in caption.split(" "):
        out.append({"t": round(t, 3), "a": a, "b": a + len(w)})
        a += len(w) + 1
        t += step
    return out


def _scene(caption, props, shot="Probe", dur_s=6.0, step=0.35, **kw):
    sc = {"shot": shot, "props": props, "caption": caption, "capWords": _spans(caption, step=step),
          "durF": int(dur_s * 30)}
    sc.update(kw)
    return sc


LIST = {"parts": ["outside mic", "inside mic", "speaker", "chip"]}
LIST_CAP = ("It has an outside mic, then an inside mic, a speaker, and a chip. "
            "All four work together on every sound you hear.")


def test_a_list_read_aloud_is_a_burst_of_close_ups_that_ends_on_the_whole():
    plan = cp.coverage_plan(_scene(LIST_CAP, LIST, dur_s=8.0), 8.0, 3, 10)
    steps = plan["coverage"]
    keys = [s["frame"]["key"] for s in steps if isinstance(s["frame"], dict) and "key" in s["frame"]]
    assert keys[:2] == ["parts.0", "parts.1"]
    assert steps[-1]["frame"] == "wide"
    assert 8.0 - steps[-1]["t"] >= cp.END_WIDE_S - 1e-9
    assert plan["coverageItems"]["parts.0"] == "outside mic"


def test_every_framing_holds_at_least_the_burst_floor():
    plan = cp.coverage_plan(_scene(LIST_CAP, LIST, dur_s=8.0, step=0.18), 8.0, 3, 10)
    if plan:
        ts = [s["t"] for s in plan["coverage"]]
        assert all(b - a >= cp.MIN_SHOT_S - 1e-9 for a, b in zip(ts, ts[1:]))


def test_a_long_beat_with_nothing_named_gets_one_punch_on_a_clause():
    cap = "The wave travels through the air, and when it reaches your ear, the drum moves with it every time."
    plan = cp.coverage_plan(_scene(cap, {"title": "Sound"}, dur_s=7.0), 7.0, 4, 10)
    steps = plan["coverage"]
    assert len(steps) == 2 and {"punch": cp.PUNCH} in [s["frame"] for s in steps]
    lo, hi = cp.PUNCH_WINDOW
    assert lo * 7.0 <= steps[1]["t"] <= hi * 7.0


def test_beats_alternate_the_order_of_the_punch():
    cap = "The wave travels through the air, and when it reaches your ear, the drum moves with it every time."
    a = cp.coverage_plan(_scene(cap, {}, dur_s=7.0), 7.0, 4, 10)["coverage"]
    b = cp.coverage_plan(_scene(cap, {}, dur_s=7.0), 7.0, 5, 10)["coverage"]
    assert a[1]["frame"] == {"punch": cp.PUNCH} and b[1]["frame"] == {"punch": cp.PUNCH}
    assert a[-1]["frame"] == {"punch": cp.PUNCH} and b[-1]["frame"] == "wide"     # punch late / punch early


def test_the_entrance_is_never_framed():
    for i in (3, 4, 5):
        steps = cp.coverage_plan(_scene(LIST_CAP, LIST, dur_s=8.0, step=0.1), 8.0, i, 10) or {"coverage": []}
        for s in steps["coverage"]:
            assert s["frame"] == "wide" or s["t"] >= cp.ENTRY_S - 1e-9


@pytest.mark.parametrize("why", ["first", "last", "short", "camera", "handoff", "stage", "plate", "nowords", "off"])
def test_coverage_stays_off_where_it_must(why):
    sc = _scene(LIST_CAP, dict(LIST), dur_s=8.0)
    i, n, prev, on = 3, 10, None, True
    if why == "first":
        i = 0
    elif why == "last":
        i = n - 1
    elif why == "short":
        sc["durF"] = 60
    elif why == "camera":
        sc["camera"] = {"move": "push"}
    elif why == "handoff":
        prev = {"camera": {"move": "push", "handoff": True}}
    elif why == "stage":
        sc["stage"] = {"run": "deck"}
    elif why == "plate":
        sc["props"]["plate"] = "plates/x.png"
    elif why == "nowords":
        sc["capWords"] = []
    elif why == "off":
        on = False
    assert cp.coverage_plan(sc, sc["durF"] / 30.0, i, n, prev=prev, enabled=on) is None


def test_an_anchored_seam_out_leaves_the_beat_wide():
    cap = "The wave travels through the air, and when it reaches your ear, the drum moves with it every time."
    nxt = {"transitionIn": {"type": "container", "carry": "x"}}
    steps = cp.coverage_plan(_scene(cap, {}, dur_s=7.0), 7.0, 4, 10, nxt=nxt)["coverage"]
    assert steps[-1]["frame"] == "wide"


def test_a_one_beat_sample_is_judged_where_its_beat_sits_in_the_film():
    props = {"scenes": [_scene(LIST_CAP, LIST, dur_s=8.0)]}
    assert cp.attach(props, [{"index": 4}], {}, 30, total=10) == 1
    props = {"scenes": [_scene(LIST_CAP, LIST, dur_s=8.0)]}
    assert cp.attach(props, [{"index": 1}], {}, 30, total=10) == 0


def test_the_film_and_the_slide_can_turn_it_off():
    props = {"scenes": [_scene(LIST_CAP, LIST, dur_s=8.0) for _ in range(3)]}
    assert cp.attach(props, [{}, {"coverage": False}, {}], {}, 30) == 0       # middle one is the only candidate
    props = {"scenes": [_scene(LIST_CAP, LIST, dur_s=8.0) for _ in range(3)]}
    assert cp.attach(props, [{}, {}, {}], {"coverage": False}, 30) == 0


# ---- the runtime's pure framing --------------------------------------------------------------------------------------

def _ts(body):
    import _tsprobe
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    return _tsprobe.run_ts("import {coverFraming, itemRegion, tooAlike, punchCore, stepAt, probeFrame, probeFrames, iou, MIN_GAIN} from %s;"
                           % _tsprobe.mod("coverage.tsx"), body)


def test_a_close_up_shows_its_target_whole_and_cuts_no_type():
    out = _ts("""
      const W = 1920, H = 1080, bandTop = 878;
      const target = {x: 400, y: 300, w: 300, h: 200};
      const texts = [{x: 1500, y: 80, w: 300, h: 60}, {x: 420, y: 520, w: 200, h: 40}];
      const content = [target, ...texts];
      const f = coverFraming({W, H, bandTop, target, content, texts});
      const m = (r: any) => ({x: r.x * f!.s + f!.tx, y: r.y * f!.s + f!.ty, w: r.w * f!.s, h: r.h * f!.s});
      out.f = f; out.t = m(target); out.texts = texts.map(m);
    """)
    f, t = out["f"], out["t"]
    assert f and f["s"] >= 1.15
    assert t["x"] >= -2 and t["y"] >= -2 and t["x"] + t["w"] <= 1922 and t["y"] + t["h"] <= 880
    for r in out["texts"]:
        inside = r["x"] >= -2 and r["y"] >= -2 and r["x"] + r["w"] <= 1922 and r["y"] + r["h"] <= 880
        outside = r["x"] + r["w"] <= 2 or r["x"] >= 1918 or r["y"] + r["h"] <= 2 or r["y"] >= 1078
        assert inside or outside


def test_no_line_of_type_straddles_the_caption_band_under_a_close_up():
    # the framed layer is masked to the content zone, so a line the zone's bottom edge would cut is cut — refused
    out = _ts("""
      const W = 1920, H = 1080, bandTop = 878;
      const target = {x: 800, y: 600, w: 200, h: 200};
      const texts = [{x: 700, y: 820, w: 500, h: 40}];
      const f = coverFraming({W, H, bandTop, target, content: [target, ...texts], texts})!;
      out.ys = texts.map((r) => [r.y * f.s + f.ty, (r.y + r.h) * f.s + f.ty]);
    """)
    for y0, y1 in out["ys"]:
        assert y1 <= 880 or y0 >= 876


def test_a_raster_is_never_drawn_past_its_own_pixels():
    out = _ts("""
      const f = coverFraming({W: 1920, H: 1080, bandTop: 878, target: {x: 500, y: 300, w: 300, h: 200},
        content: [], texts: [], cap: 1.05});
      out.f = f;
    """)
    assert out["f"] is None


def test_two_framings_too_alike_are_not_a_cut():
    out = _ts("""
      out.same = tooAlike({s: 1.2, tx: -143, ty: -224}, {s: 1.2, tx: -255, ty: -224}, 1920, 1080);
      out.apart = tooAlike({s: 1.4, tx: 0, ty: -100}, {s: 1.4, tx: -760, ty: -100}, 1920, 1080);
      out.scale = tooAlike(null, {s: 1.6, tx: -300, ty: -200}, 1920, 1080);
    """)
    assert out["same"] is True and out["apart"] is False and out["scale"] is False


def test_an_item_region_takes_its_own_drawing_and_not_the_shared_base():
    out = _ts("""
      const W = 1920, H = 1080;
      const left = {x: 400, y: 790, w: 300, h: 60}, right = {x: 1130, y: 790, w: 300, h: 60};
      const content = [{x: 480, y: 150, w: 220, h: 560}, {x: 1210, y: 150, w: 220, h: 560},
                       {x: 300, y: 720, w: 1300, h: 30}, left, right];
      const isText = [false, false, false, true, true];
      out.r = itemRegion(left, [right], content, isText, W, H);
    """)
    d = out["r"]["drawing"]
    assert d["x"] == 480 and d["x"] + d["w"] == 700           # its own cylinder; the base spanning both is shared


def test_a_step_is_measured_just_before_it_ends():
    out = _ts("""
      const plan: any = [{t: 0, frame: 'wide'}, {t: 2, frame: {punch: 1.3}}, {t: 4, frame: 'wide'}];
      out.pf = probeFrame(plan, 1, 180, 30); out.at = stepAt(plan, 3.0)!.i; out.before = stepAt(plan, -1);
      out.pfs = probeFrames(plan, 1, 180, 30);
    """)
    assert out["pf"] == 118 and out["at"] == 1 and out["before"] is None
    assert out["pfs"] == [62, 90, 118]          # just after the cut, the middle, just before the end


def test_a_composition_that_recomposes_inside_a_step_is_told_by_its_hull():
    out = _ts("""
      out.same = iou({x: 100, y: 100, w: 800, h: 500}, {x: 110, y: 105, w: 790, h: 500});
      out.moved = iou({x: 0, y: 0, w: 1800, h: 900}, {x: 600, y: 300, w: 700, h: 400});
    """.replace("import {", "import {"))
    assert out["same"] > 0.9 and out["moved"] < 0.7


def test_an_item_region_reads_what_the_frame_shows_and_not_the_whole_diagram():
    out = _ts("""
      const W = 1920, H = 1080;
      const label = {x: 170, y: 340, w: 200, h: 120};
      // a pipe drawn far past the frame, a big shared panel, and the small part beside the label
      const content = [{x: 300, y: -1900, w: 60, h: 2800}, {x: 0, y: 0, w: 1300, h: 870}, {x: 400, y: 380, w: 90, h: 90}, label];
      out.r = itemRegion(label, [], content, [false, false, false, true], W, H);
    """)
    d = out["r"]["drawing"]
    assert d["y"] >= 0 and d["w"] * d["h"] <= 0.35 * 1920 * 1080
