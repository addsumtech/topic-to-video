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


# ── the paths that move type, by construction ────────────────────────────────────────────────────────────────
@needs_toolchain
def test_a_drifting_film_carrying_the_unlock_still_covers_the_frame():
    """The whole-film drift (meta.camera_drift) carries the unlock, and the skew tilts its layer's top and bottom
    edges. Its scale is held at least at `unlockCoverScale` for the translation it has on each frame; the corners of
    the layer under scale(s) translate(x, y) skewY(k), about the frame centre, must clear every edge by the margin
    at every amplitude a film can ask for — including the smallest, where the breathing scale alone does not."""
    out = _tsprobe.run_ts(
        "import {BASELINE_UNLOCK_SKEW as K, unlockCoverScale} from %s;" % _tsprobe.mod("glide"),
        """
        out.worst = Infinity;
        for (const [W, H] of [[1920, 1080], [1080, 1920], [1080, 1080]]) {
          for (const amp of [0.02, 0.05, 0.2, 1, 2]) {
            for (let f = 0; f < 3000; f += 7) {
              const s = 1 + amp * (0.035 + 0.010 * Math.sin((f / 720) * 2 * Math.PI));
              const y = amp * 4 * Math.sin((f / 810) * 2 * Math.PI + 0.4);
              const sc = Math.max(s, unlockCoverScale(H / 2, W / 2, y));
              const Y = (px: number, py: number) => H / 2 + sc * ((py - H / 2) + y + K * (px - W / 2));
              const top = Math.max(Y(0, 0), Y(W, 0)), bottom = Math.min(Y(0, H), Y(W, H));
              out.worst = Math.min(out.worst, -top, bottom - H);
            }
          }
        }
        """)
    assert out["worst"] >= 1 - 1e-6, "the drifting layer left %.2fpx of frame edge uncovered" % (1 - out["worst"])


@needs_toolchain
def test_a_mark_drawn_over_a_toured_page_lands_where_the_camera_put_the_page():
    """pageToScreen must describe the transform PageCam2D draws, unlock and cover included — or the pointer, the
    ripple and every label drawn over a page land up to a pixel off what they name."""
    out = _tsprobe.run_ts(
        "import {pageCamTransform, pageToScreen, type CamUnlock} from %s;" % _tsprobe.mod("pageCam2D"),
        """
        // apply a css transform list (translate/scale/matrix only, origin 0 0) to a point, right to left
        const apply = (xf: string, p: [number, number]): [number, number] => {
          const fns = [...xf.matchAll(/(translate|scale|matrix)\\(([^)]*)\\)/g)].map((m) => [m[1], m[2].split(',').map((v) => parseFloat(v))] as const);
          let [x, y] = p;
          for (let i = fns.length - 1; i >= 0; i--) {
            const [fn, a] = fns[i];
            if (fn === 'translate') { x += a[0]; y += a[1]; }
            else if (fn === 'scale') { x *= a[0]; y *= (a.length > 1 ? a[1] : a[0]); }
            else { const nx = a[0] * x + a[2] * y + a[4], ny = a[1] * x + a[3] * y + a[5]; x = nx; y = ny; }
          }
          return [x, y];
        };
        out.err = 0;
        const unlocks: (CamUnlock | undefined)[] = [undefined, {on: true, under: 0.4, cover: false},
          {on: true, under: 1, cover: true}, {on: false, under: 1, cover: true}];
        for (const u of unlocks) for (const cam of [{x: 800, y: 500, s: 0.4}, {x: 1300, y: 300, s: 2.2}]) {
          const xf = pageCamTransform(cam, 1920, 890, u);
          for (const pt of [[0, 0], [2400, 1600], [810, 495]] as [number, number][]) {
            const a = apply(xf, pt), b = pageToScreen(cam, 1920, 890, pt[0], pt[1], u);
            out.err = Math.max(out.err, Math.abs(a[0] - b.x), Math.abs(a[1] - b.y));
          }
        }
        out.plain = pageCamTransform({x: 800, y: 500, s: 0.4}, 1920, 890);
        """)
    assert out["err"] < 1e-6, "pageToScreen disagrees with the page camera by %.4fpx" % out["err"]
    assert out["plain"] == "translate(640px, 245px) scale(0.4)", "a tour with no unlock must draw exactly as before"


@needs_toolchain
def test_the_films_moving_seams_and_drift_carry_the_unlock(census_bundle):
    """A film whose beats hold still: every crawl in it is the FILM's — its seams and its whole-film drift. With the
    unlock switched off (the film before it existed) the focus relay, the flight through dark and the drift are
    staircases; with it on, nothing steps more than once (the carry's collapse to a line, where no skew survives a
    0.006 scaleY, ticks once and is gone)."""
    def film(scenes, camera):
        return {"scenes": scenes, "camera": camera, "cameraBed": False, "reducedMotion": False, "aspect": "16:9",
                "captions": False, "dna": "product", "typeGlide": True}
    seams = [None, {"type": "drift", "direction": "from-bottom"}, {"type": "return", "dx": 0, "dy": 1},
             {"type": "focus"}, {"type": "through-dark"}, {"type": "portal"}, {"type": "carry"}]
    sc = [dict({"shot": "OpenQuestions", "props": {}, "durF": 120, "caption": ""},
               **({"transitionIn": ti} if ti else {})) for ti in seams]
    drift = [{"shot": "OpenQuestions", "props": {}, "durF": 240, "caption": ""} for _ in range(2)]
    jobs = [{"tag": "seams", "id": "Film", "props": film(sc, 0)},
            {"tag": "seams-old", "id": "Film", "props": dict(film(sc, 0), baselineUnlock=False)},
            {"tag": "drift", "id": "Film", "props": film(drift, 1)},
            {"tag": "drift-old", "id": "Film", "props": dict(film(drift, 1), baselineUnlock=False)}]
    res = tq.glide_run(jobs, census_bundle)
    level = {}
    for j in jobs:
        slot = res[j["tag"]]
        assert slot["done"] and not slot["error"], (j["tag"], slot["error"])
        level[j["tag"]] = tq.glide_level(tq.judge_glide(slot["frames"]))[0]
    assert level["seams-old"] == "error" and level["drift-old"] == "error", level
    assert level["seams"] in ("clean", "warn") and level["drift"] == "clean", level


@needs_toolchain
def test_the_unlock_written_into_dna_is_the_runtime_one():
    """TermFrame and EdFrame (runtime/dna.tsx) carry the baseline unlock as a LITERAL — every register imports that
    file, so importing runtime/glide there would move every register's measurement rows. A literal is a second copy
    of the constant, and a second copy drifts; this holds the two equal, and counts the sites so one cannot be
    dropped or added unseen."""
    import re
    dna = open(os.path.join(os.path.dirname(_HERE), "remotion", "src", "runtime", "dna.tsx"), encoding="utf-8").read()
    written = re.findall(r"' (matrix\([^)]*\))'", dna)
    assert len(written) == 3, "TermFrame's result and EdFrame's kicker and body each carry one: %r" % written
    out = _tsprobe.run_ts("import {BASELINE_UNLOCK} from %s;" % _tsprobe.mod("glide"), "out.u = BASELINE_UNLOCK;")
    assert set(written) == {out["u"]}, "dna.tsx's unlock %r is not runtime/glide's %r" % (set(written), out["u"])
