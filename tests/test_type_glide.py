"""Type that moves must glide with its drawing — and the census that says whether it does must see the defect.

THE DEFECT (runtime/glide.ts). Under an axis-aligned matrix Skia rounds a glyph run's baseline to the device pixel,
so type that crawls by less than a pixel a frame holds still and then jumps while everything drawn beside it glides.
A viewer saw it on a delivered film's camera push; every still gate passed that film and shake_qa read the same
numbers before and after the fix.

THE CENSUS (scripts/text_safe_qa.py --glide, runtime/textSafe.tsx auditGlide). Every frame is rendered with no
picture taken and the DOM lists each visible line of type whose matrix Skia would treat as axis-aligned, with its
true position. Read in frame order: three or more whole-pixel steps inside one crawl is a staircase (ERROR); one or
two is the tick at the end of a slow ease (WARN).

These tests pin both halves: the reader on synthetic tracks, and the whole census against CameraTypeProbe — the old
camera (the unlock switched off) must be found, the unlocked one must list nothing, and the one case the unlock does
not reach on its own (a blur or drop-shadow above the type, measured in tests/test_camera_type.py) must be found
too, with its fix (the unlock inside the filter) clean.
"""
import os
import shutil
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)
import _tsprobe  # noqa: E402
import text_safe_qa as tq  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")


def _track(ys, key="/body0/div0", text="Type", o=1.0, fl="", start=0):
    """{frame: record} for one line whose true top is `ys[i]` on frame start+i (None = not listed that frame)."""
    out = {}
    for i, y in enumerate(ys):
        rec = out.setdefault(start + i, {"f": start + i, "lines": [], "u": 0, "z": 0})
        if y is not None:
            line = {"k": key, "y": y, "o": o, "t": text}
            if fl:
                line["fl"] = fl
            rec["lines"].append(line)
    return out


# ── the reader ───────────────────────────────────────────────────────────────────────────────────────────────
def test_a_crawl_that_crosses_three_whole_pixels_is_a_staircase():
    ys = [100 + 0.3 * i for i in range(12)]                    # 3.3px in 11 frames: four whole-pixel crossings
    runs = tq.judge_glide(_track(ys))
    level, worst = tq.glide_level(runs)
    assert level == "error" and worst[0]["steps"] >= tq.GLIDE_STEPS_ERROR, runs


def test_a_tick_at_the_end_of_an_ease_is_a_warning_not_an_error():
    ys = [99.2, 99.6, 99.85, 100.05, 100.15, 100.2, 100.2]     # one crossing on the way in to rest
    level, worst = tq.glide_level(tq.judge_glide(_track(ys)))
    assert level == "warn" and worst[0]["steps"] == 1


def test_a_line_moving_a_pixel_or_more_every_frame_is_not_a_crawl():
    ys = [100 + 1.4 * i for i in range(20)]                    # no frame holds, so nothing steps out of a hold
    assert tq.judge_glide(_track(ys)) == []


def test_a_line_that_never_moves_is_silent():
    assert tq.judge_glide(_track([100.5] * 30)) == []


def test_a_line_still_too_faint_to_read_does_not_count():
    ys = [100 + 0.3 * i for i in range(12)]
    assert tq.judge_glide(_track(ys, o=tq.GLIDE_MIN_OPACITY / 2)) == []


def test_a_frame_the_line_is_missing_from_ends_the_crawl():
    # unlocked (not listed) on every other frame: no two consecutive listed frames, so no crawl at all
    ys = [100 + 0.3 * i if i % 2 == 0 else None for i in range(16)]
    assert tq.judge_glide(_track(ys)) == []


def test_type_declared_stepped_is_named_and_excused():
    ys = [100 + 0.3 * i for i in range(12)]
    runs = tq.judge_glide(_track(ys, fl="s"))
    assert runs and "s" in runs[0]["fl"]
    assert tq.glide_level(runs)[0] == "clean"


def test_a_census_that_lost_frames_reads_as_unmeasured_not_clean():
    slot = {"frames": {0: {}}, "done": {"logged": 90, "frames": 120}, "error": None}
    assert "90 of 120" in tq._glide_measured(slot, 120)
    assert "FAILED" in tq._glide_measured({"frames": {}, "done": None, "error": "boom"}, 120)
    assert tq._glide_measured({"frames": {}, "done": {"logged": 120}, "error": None}, 120) is None


# ── the helper ───────────────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_the_shared_unlock_is_the_cameras_and_reaches_type_at_any_scale():
    out = _tsprobe.run_ts(
        "import {BASELINE_UNLOCK, BASELINE_UNLOCK_SKEW as K, glide, unlockFor, unlockCoverScale, "
        "baselineUnlockOverscan} from %s;\n" % _tsprobe.mod("glide"),
        """
        out.unlock = BASELINE_UNLOCK;
        out.off = glide('translateY(3px)', false) ?? null;
        out.none = glide(undefined, false) ?? null;
        out.on = glide('translateY(3px)', true);
        out.bare = glide('none', true);
        // the skew Skia sees is the entry times the scale above the type; it must round to at least 1/1024
        out.seen = [0.3, 0.5, 1, 2].map((s) => Math.round(s * Number(/matrix\\(1, ([^,]+),/.exec(unlockFor(s))![1]) * 1024));
        out.cover = unlockCoverScale(450, 960) - 1;
        out.overscan = baselineUnlockOverscan(1920, 1080, 540);
        try { unlockFor(0); out.zero = 'no throw'; } catch (e) { out.zero = String(e); }
        """)
    # the exact string SceneCamera wrote before the unlock moved here: moving it must not change a pixel
    assert out["unlock"] == "matrix(1, 0.0009765625, 0, 1, 0, 0)"
    assert out["off"] == "translateY(3px)" and out["none"] is None, "off the span the transform must be untouched"
    assert out["on"] == "translateY(3px) " + out["unlock"] and out["bare"] == out["unlock"]
    assert all(v >= 1 for v in out["seen"]), "the skew rounds to zero for type at some scale: %r" % out["seen"]
    assert abs(out["cover"] - baselineUnlockOverscan_reference(1920, 450)) < 1e-12
    assert out["overscan"] > 0 and "positive" in out["zero"]


def baselineUnlockOverscan_reference(W, reach):
    tilt = W / 2 / 1024
    return (tilt + 1) / (reach - tilt)


# ── the whole census, against the probe ──────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def census_bundle():
    import workshop as _ws
    work = tempfile.mkdtemp(prefix="glide_test_")
    try:
        yield tq.glide_bundle(os.path.join(work, "bundle"), None, _ws.prepare(None))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _census(bundle, variants):
    jobs = [{"tag": k, "id": "CameraTypeProbe", "props": dict(v, typeGlide=True)} for k, v in variants.items()]
    res = tq.glide_run(jobs, bundle)
    out = {}
    for k in variants:
        slot = res[k]
        assert tq._glide_measured(slot, 120) is None, (k, slot.get("error"), slot.get("done"))
        runs = tq.judge_glide(slot["frames"])
        out[k] = {"level": tq.glide_level(runs)[0], "runs": runs,
                  "listed": sum(len(r.get("lines") or []) for r in slot["frames"].values()),
                  "z": tq._composited(slot["frames"])}
    return out


@needs_toolchain
def test_the_census_finds_the_old_camera_and_clears_the_unlocked_one(census_bundle):
    got = _census(census_bundle, {
        "push-old": {"move": "push", "legacy": True}, "push": {"move": "push"},
        "pull-old": {"move": "pull", "legacy": True}, "pull": {"move": "pull"},
        "pan-old": {"move": "hold", "pan": [0.6, -0.8], "legacy": True}, "pan": {"move": "hold", "pan": [0.6, -0.8]},
        "hold": {"move": "hold"}, "bare": {"bare": True},
    })
    for name in ("push-old", "pull-old", "pan-old"):
        assert got[name]["level"] == "error", (name, got[name]["runs"][:2])
    for name in ("push", "pull", "pan"):
        assert got[name]["listed"] == 0, "%s: the unlocked camera left type Skia would snap: %r" % (
            name, got[name]["runs"][:2])
    for name in ("hold", "bare"):
        assert got[name]["listed"] > 0 and got[name]["level"] == "clean", (name, got[name]["runs"][:2])


@needs_toolchain
def test_a_blur_or_drop_shadow_above_the_type_is_found_and_the_unlock_inside_it_is_clean(census_bundle):
    got = _census(census_bundle, {
        "shadow": {"move": "push", "layer": "shadow"}, "shadow-inner": {"move": "push", "layer": "shadow", "inner": True},
        "blur": {"move": "push", "layer": "blur"}, "blur-inner": {"move": "push", "layer": "blur", "inner": True},
        "saturate": {"move": "push", "layer": "saturate"}, "will-change": {"move": "push", "layer": "will-change"},
    })
    for name in ("shadow", "blur"):
        assert got[name]["level"] == "error" and all("f" in r["fl"] for r in got[name]["runs"]), (name, got[name])
    for name in ("shadow-inner", "blur-inner", "saturate"):
        assert got[name]["listed"] == 0, (name, got[name]["runs"][:2])
    # a will-change layer is rasterised once and moved by the compositor: not read, and SAID to be not read
    assert got["will-change"]["listed"] == 0 and got["will-change"]["z"] > 0
