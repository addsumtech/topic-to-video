"""The cinematic tier renders one beat at a time and keeps the beats that did not change.

It used to render the whole Film in one `npx remotion render`, so any edit re-rendered every beat; on a
machine with ~1 GB free that render failed repeatedly and a one-beat fix never reached the delivered film.
A cache is only worth having if it can never serve a stale beat, so most of what is pinned here is the KEY:
what a beat's frames depend on, read off Film.tsx, and a pin that fails when Film.tsx starts reading the
scene list somewhere the key does not know about. The render tests then check the thing that matters —
that a film joined from segments IS the film a single render makes, and that an edit reuses what it should.
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
from collections import Counter

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import remotion_segments as rs          # noqa: E402

TR = rs.seam_frames()


def _props(durs, **film):
    scenes = [{"shot": "TermTable", "durF": d, "mp3": "audio/%02d.mp3" % (i + 1), "caption": "第 %d 拍" % (i + 1),
               "props": {"kicker": "B%d" % (i + 1), "rows": [["a", str(i)], ["b", str(i * 2)]]}}
              for i, d in enumerate(durs)]
    return dict({"scenes": scenes, "dna": "product", "captions": True, "camera": 0}, **film)


def _keys(props, public, code="c0"):
    return [s["key"] for s in rs.plan(props, str(public), {"gl": "angle"}, tr=TR, code=code)[0]]


# ── the timeline ───────────────────────────────────────────────────────────────────────────────────────
def test_halves_round_up_as_the_film_rounds_them():
    """Film.tsx rounds with Math.round. Python's round() sends 150.5 to 150; a one-frame disagreement per beat
    puts every seam in the wrong segment."""
    assert rs.js_round(150.5) == 151 and round(150.5) == 150
    assert rs.js_round(149.5) == 150 and rs.js_round(0.4) == 0


def test_the_segments_tile_the_film_exactly():
    """Contiguous, from frame 0 to the last, and the total is Film.tsx's own filmDuration formula."""
    rnd = random.Random(7)
    for _ in range(200):
        durs = [rnd.choice([TR + 1, rnd.uniform(TR + 1, 600)]) for _ in range(rnd.randint(1, 40))]
        scenes = [{"durF": d} for d in durs]
        segs, total = rs.timeline(scenes, TR)
        rounded = [max(1, rs.js_round(d)) for d in durs]
        assert total == max(1, sum(rounded) - (len(rounded) - 1) * TR)
        assert segs[0][0] == 0 and segs[-1][1] == total - 1
        assert all(b + 1 == a2 for (_a, b), (a2, _b) in zip(segs, segs[1:])), segs


def test_a_beat_no_longer_than_the_seam_is_refused_not_guessed():
    with pytest.raises(rs.ModelMismatch):
        rs.timeline([{"durF": 60}, {"durF": TR}, {"durF": 60}], TR)


# ── the key ────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def public(tmp_path):
    (tmp_path / "audio").mkdir()
    for i in range(1, 9):
        (tmp_path / "audio" / ("%02d.mp3" % i)).write_bytes(b"voice-%d" % i)
    return tmp_path


def test_the_same_film_gives_the_same_keys(public):
    """Nothing run-specific may reach a key, or the cache never hits."""
    p = _props([60, 70, 80, 90])
    assert _keys(p, public) == _keys(json.loads(json.dumps(p)), public)


def test_a_visual_edit_redoes_that_beat_and_the_next_and_nothing_else(public):
    """The shot-critic loop's edits. The next beat is redone because its seam shows this beat's tail."""
    a = _props([60, 70, 80, 90, 60])
    b = json.loads(json.dumps(a))
    b["scenes"][2]["props"]["kicker"] = "EDITED"
    changed = [i for i, (x, y) in enumerate(zip(_keys(a, public), _keys(b, public))) if x != y]
    assert changed == [2, 3], changed


def test_a_length_edit_redoes_every_later_beat(public):
    """THE HONEST LIMIT, pinned so nobody 'optimises' it away: every later beat starts on a new frame, and
    the Atmosphere under the film pulses on the absolute frame."""
    a = _props([60, 70, 80, 90, 60])
    b = json.loads(json.dumps(a))
    b["scenes"][1]["durF"] = 75
    changed = [i for i, (x, y) in enumerate(zip(_keys(a, public), _keys(b, public))) if x != y]
    assert changed == [1, 2, 3, 4], changed


def test_appending_a_beat_redoes_the_old_last_one(public):
    """The outro veil and the caption's closing window belong to whichever beat is last."""
    a, b = _props([60, 70, 80]), _props([60, 70, 80, 90])
    ka, kb = _keys(a, public), _keys(b, public)
    assert ka[:2] == kb[:2] and ka[2] != kb[2]


def test_a_resynthesised_voice_at_the_same_path_is_a_new_beat(public):
    """The path in the props does not change when tts.py re-voices a beat; the file does."""
    p = _props([60, 70, 80, 90])
    before = _keys(p, public)
    (public / "audio" / "03.mp3").write_bytes(b"a different take")
    changed = [i for i, (x, y) in enumerate(zip(before, _keys(p, public))) if x != y]
    assert changed == [2, 3], changed


def test_film_wide_settings_and_code_redo_everything(public):
    p = _props([60, 70, 80])
    base = _keys(p, public)
    assert all(x != y for x, y in zip(base, _keys(dict(p, dna="editorial"), public)))
    assert all(x != y for x, y in zip(base, _keys(p, public, code="c1")))


def test_the_code_hash_reaches_the_fonts_outside_src():
    """The bundle imports its typefaces from the skill's assets/fonts; a font swap is a code change."""
    files = [os.path.relpath(f, _ROOT) for f in rs.code_files()]
    assert any(f.startswith(os.path.join("assets", "fonts")) for f in files), files[:8]
    assert os.path.join("remotion", "src", "Film.tsx") in files
    assert os.path.join("remotion", "package-lock.json") in files


# ── the pin: the key knows every place Film.tsx reads the scene list ───────────────────────────────────
# Each entry was read and accounted for in remotion_segments.py's header. A new read (a look-ahead to
# scenes[i + 2], a film-wide pass that feeds pixels) must be decided — does the key need it? — and then
# added here. A removal is harmless but still has to be acknowledged.
_KNOWN_READS = Counter({
    "scenes.reduce": 1,            # filmDuration -> the outro, last segment only (its frames are in the key)
    "scenes.length": 4,            # filmDuration, the caption loop's bound and closing window, the last-beat check
    "scenes.map": 1,               # caption starts: relative offsets, translation-invariant
    "scenes[i]": 1,                # caption window of the active beat (k-1 or k)
    "scenes[active]": 1,
    "(scenes||[]).some": 1,        # refuses drift+pan: throws, draws nothing
    "scenes.forEach": 1,           # refuses bgLum/ground disagreement: throws, draws nothing
    "scenes[0]": 1,                # the root fill -> the film-wide key's `root`
    "scenes[scenes.length-1]": 1,  # the outro veil -> the last segment's own scene
    "scenes.flatMap": 1,           # one Sequence per beat
    "scenes[i+1]": 2,              # the seam into the NEXT beat -> that segment's `prev`
})


def _reads(src):
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
    code = re.sub(r"\s+", "", code)
    found = Counter()
    for m in re.finditer(r"\(scenes\|\|\[\]\)\.\w+|scenes(?:\.\w+|\[(?:[^\[\]]|\[[^\]]*\])*\])", code):
        found[m.group(0)] += 1
    return found


def test_the_key_knows_every_place_the_film_reads_the_scene_list():
    got = _reads(open(os.path.join(_REM, "src", "Film.tsx"), encoding="utf-8").read())
    assert got == _KNOWN_READS, (
        "Film.tsx reads the scene list differently from what the segment cache key was derived from.\n"
        "  new/changed : %r\n  gone        : %r\n"
        "Decide whether a beat's frames now depend on another beat (remotion_segments.plan), then update "
        "_KNOWN_READS." % (dict(got - _KNOWN_READS), dict(_KNOWN_READS - got)))


def test_the_pin_catches_a_look_ahead():
    """The pin itself, mutated: a register-feeding read of the beat after next must be noticed."""
    src = open(os.path.join(_REM, "src", "Film.tsx"), encoding="utf-8").read()
    mutated = src.replace("pickPresentation(sc, scenes[i + 1]", "pickPresentation(sc, scenes[i + 2]", 1)
    assert mutated != src and _reads(mutated) != _KNOWN_READS


# ── the render: a film joined from segments IS the film one render makes ───────────────────────────────
needs_toolchain = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("ffmpeg") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain and ffmpeg")

_FLAGS = ["--gl=angle", "--scale=0.25", "--log=error", "--timeout=150000"]


def _probe_film(d, kicker="ONE"):
    """Three beats with a PUSH seam — a whole frame sliding across the screen, so a segment that started one
    frame early or late would show as a large difference, not a rounding one — captions on, and a distinct
    tone per beat so the audio join can be heard in the numbers."""
    (d / "audio").mkdir(exist_ok=True)
    for i, hz in enumerate((440, 660, 880), 1):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=%d:sample_rate=48000"
                        % hz, "-t", "2", str(d / "audio" / ("%02d.mp3" % i))], check=True)
    scenes = [
        {"shot": "TermTable", "durF": 45, "mp3": "audio/01.mp3", "caption": "第一拍在这里。",
         "props": {"kicker": kicker, "rows": [["a", "1"], ["b", "2"]]}},
        {"shot": "MadeOf", "durF": 50, "mp3": "audio/02.mp3", "caption": "第二拍接着说。",
         "props": {"whole": "TWO"}, "transitionIn": {"type": "push", "direction": "from-left"}},
        {"shot": "TermTable", "durF": 40, "mp3": "audio/03.mp3", "caption": "第三拍收尾。",
         "props": {"kicker": "THREE", "rows": [["c", "3"], ["d", "4"]]}},
    ]
    props = {"scenes": scenes, "dna": "product", "captions": True, "camera": 0}
    pf = d / ".remotion-props.json"
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    return props, str(pf)


def _full(d, pf, out):
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Film", out, "--props=" + pf,
                        "--public-dir=" + str(d)] + _FLAGS, cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]


def _frames(path):
    np = pytest.importorskip("numpy")
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
                       capture_output=True, check=True)
    w, h = [int(x) for x in subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of",
         "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip().split(",")[:2]]
    return np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, h, w).astype(float)


def _audio(path):
    np = pytest.importorskip("numpy")
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "s16le", "-ac", "1",
                        "-ar", "48000", "pipe:1"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(float)


@needs_toolchain
def test_a_film_joined_from_segments_is_the_film_one_render_makes(tmp_path):
    np = pytest.importorskip("numpy")
    props, pf = _probe_film(tmp_path)
    full = str(tmp_path / "full.mp4")
    _full(tmp_path, pf, full)
    seg = str(tmp_path / "seg.mp4")
    rs.render_film(str(tmp_path), props, pf, seg, _FLAGS, {"gl": "angle", "scale": 0.25}, log=lambda *_: None)

    a, b = _frames(full), _frames(seg)
    assert a.shape == b.shape, "the joined film is %r, the single render %r" % (b.shape, a.shape)
    per_frame = np.abs(a - b).mean(axis=(1, 2))
    # Both are lossy encodes of the same frames, so they differ by compression noise; a frame from the
    # WRONG moment differs by the push seam's travel. The control below proves the probe can see that.
    shifted = np.abs(a[1:] - a[:-1]).mean(axis=(1, 2))
    assert shifted.max() > 8, "the probe has no motion a one-frame slip would show (max %.2f)" % shifted.max()
    assert per_frame.max() < 3.0, (
        "frame %d of the joined film differs from the single render by %.2f grey levels (a one-frame slip "
        "measures up to %.2f here)" % (int(per_frame.argmax()), per_frame.max(), shifted.max()))

    # THE AUDIO — the same sound at the same frames, NOT the same samples. Measured when this was written:
    #   * Remotion's own single render starts its whole track 2048 samples (42.7 ms) LATE — AAC encoder
    #     priming it never trims (start_time 0, no edit list); the joined film's PCM starts on the frame;
    #   * it places each beat's voice on a whole MILLISECOND: beat 3 starts on frame 71 = 2366.67 ms and was
    #     placed at 2367 ms, 16 samples late, while its segment places it on the frame exactly. Inside a seam
    #     the two beats are then shifted by different amounts, so no single lag aligns a full render's seam
    #     with anything — a per-frame WAVEFORM match is the wrong question there.
    # So: every frame carries the same SOUND (magnitude spectrum and energy, which a shift does not change
    # and a gap or a doubled block does), and at every join the leaving beat's tone runs on without a phase
    # jump — the direct test of a gap or a doubled block at the join itself.
    x, y = _audio(full), _audio(seg)

    def corr(a, b):
        k = min(len(a), len(b))
        a, b = a[:k], b[:k]
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    head = 60000
    prime = max(range(0, 2401), key=lambda L: corr(x[L:L + head], y[:head]))
    assert prime <= 2048, "the single render's track leads the joined one by %d samples" % prime
    for f in range(1, len(y) // 1600 - 1):
        wa, wb = x[prime + f * 1600:prime + (f + 1) * 1600], y[f * 1600:(f + 1) * 1600]
        ea, eb = float(np.sqrt((wa ** 2).mean())), float(np.sqrt((wb ** 2).mean()))
        if max(ea, eb) < 50:
            continue
        sa, sb = np.abs(np.fft.rfft(wa * np.hanning(1600))), np.abs(np.fft.rfft(wb * np.hanning(1600)))
        assert corr(sa, sb) > 0.98 and 0.9 < eb / max(ea, 1e-9) < 1.1, (
            "frame %d sounds different in the joined film (spectrum %.3f, energy %.0f vs %.0f)"
            % (f, corr(sa, sb), eb, ea))

    def phase(v, i0, hz, other):
        tt = np.arange(i0, i0 + 800) / 48000.0
        cols = [np.sin(2 * np.pi * h * tt) for h in (hz, other)] + [np.cos(2 * np.pi * h * tt) for h in (hz, other)]
        c = np.linalg.lstsq(np.stack(cols, 1), v[i0:i0 + 800], rcond=None)[0]
        return np.degrees(np.arctan2(c[2], c[0]))

    tones = (440, 660, 880)
    for k in (1, 2):                                                      # the two joins: frames 33 and 71
        j = sum(sc["durF"] - TR for sc in props["scenes"][:k]) * 1600
        jump = (phase(y, j, tones[k - 1], tones[k]) - phase(y, j - 800, tones[k - 1], tones[k]) + 180) % 360 - 180
        assert abs(jump) < 5, "the leaving beat's tone jumps %.1f degrees at the join into beat %d" % (jump, k + 1)
    seconds = lambda path, kind: float(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", kind + ":0", "-show_entries", "stream=duration", "-of",
         "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip().split(",")[0])
    assert abs(seconds(seg, "a") - seconds(seg, "v")) < 1e-3, (
        "the joined film's sound and picture are different lengths: %.4f vs %.4f s"
        % (seconds(seg, "a"), seconds(seg, "v")))


@needs_toolchain
def test_a_visual_edit_renders_two_beats_and_still_matches_a_full_render(tmp_path):
    np = pytest.importorskip("numpy")
    props, pf = _probe_film(tmp_path)
    out = str(tmp_path / "out.mp4")
    rs.render_film(str(tmp_path), props, pf, out, _FLAGS, {"gl": "angle", "scale": 0.25}, log=lambda *_: None)
    props, pf = _probe_film(tmp_path, kicker="EDITED")                   # the first beat's words change
    summary = rs.render_film(str(tmp_path), props, pf, out, _FLAGS, {"gl": "angle", "scale": 0.25},
                             log=lambda *_: None)
    assert summary["rendered"] == [0, 1], summary
    full = str(tmp_path / "full.mp4")
    _full(tmp_path, pf, full)
    a, b = _frames(full), _frames(out)
    assert a.shape == b.shape and np.abs(a - b).mean(axis=(1, 2)).max() < 3.0
    left = [f for f in os.listdir(tmp_path / rs.CACHE_DIR) if f.endswith(".mov")]
    assert len(left) == 3, "superseded segments were not cleared: %r" % left


def test_the_film_s_first_ground_is_in_every_key(public):
    """The root fill under the whole film is scene 0's opening ground (Film.tsx `rootBg`)."""
    a = _props([60, 70, 80])
    b = json.loads(json.dumps(a))
    b["scenes"][0]["key"] = "light"
    assert all(x != y for x, y in zip(_keys(a, public), _keys(b, public)))


# ── the failure paths, with a fake renderer that writes real (tiny) segment files ──────────────────────
needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


class _FakeRemotion:
    """Stands in for `npx remotion render`: writes a real .mov with exactly the frames and samples asked
    for, and can be told to fail on a given beat."""

    def __init__(self, total, fail_at=None):
        self.total, self.fail_at, self.calls = total, fail_at, []

    def __call__(self, cmd, cwd=None, check=True):
        if cmd[2] == "bundle":                                            # the once-per-render bundle
            dest = next(a for a in cmd if a.startswith("--out-dir=")).split("=", 1)[1]
            os.makedirs(dest, exist_ok=True)
            open(os.path.join(dest, "index.html"), "w").close()
            self.calls.append("bundle")
            return
        frames = next(a for a in cmd if a.startswith("--frames=")).split("=", 1)[1]
        a, b = frames.split("-")
        a, b = int(a), (int(b) if b else self.total - 1)
        self.calls.append(frames)
        if self.fail_at is not None and a == self.fail_at:
            raise subprocess.CalledProcessError(1, cmd)
        n = b - a + 1
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=64x36:r=30",
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-frames:v", str(n),
                        "-af", "atrim=end_sample=%d" % (n * 1600), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "pcm_s16le", cmd[5]], check=True)


@needs_ffmpeg
def test_the_last_beat_runs_to_the_film_s_own_end(public):
    """A timeline one frame short must never silently drop the close: the last segment is asked for
    'a-', not 'a-b', and its frame count is then checked against the model."""
    p = _props([60, 70, 80])
    pf = public / ".remotion-props.json"
    pf.write_text(json.dumps(p), encoding="utf-8")
    total = rs.timeline(p["scenes"], TR)[1]
    fake = _FakeRemotion(total)
    rs.render_film(str(public), p, str(pf), str(public / "out.mp4"), [], {"gl": "angle"}, log=lambda *_: None,
                   run=fake)
    renders = [c for c in fake.calls if c != "bundle"]
    assert renders[-1].endswith("-") and all(not c.endswith("-") for c in renders[:-1]), fake.calls
    assert rs.video_frames(str(public / "out.mp4")) == total


@needs_ffmpeg
def test_a_failed_beat_leaves_the_finished_ones_and_a_rerun_resumes(public):
    """The job-hunt film's full render died repeatedly with ~1 GB free and kept nothing. Here a failure on
    the third beat keeps the first two, leaves no half-written file under a final name, and the next run
    renders only what is missing."""
    p = _props([60, 70, 80, 90])
    pf = public / ".remotion-props.json"
    pf.write_text(json.dumps(p), encoding="utf-8")
    segs, total = rs.timeline(p["scenes"], TR)
    with pytest.raises(subprocess.CalledProcessError):
        rs.render_film(str(public), p, str(pf), str(public / "out.mp4"), [], {"gl": "angle"},
                       log=lambda *_: None, run=_FakeRemotion(total, fail_at=segs[2][0]))
    cache = public / rs.CACHE_DIR
    assert len([f for f in os.listdir(cache) if f.endswith(".mov") and ".part" not in f]) == 2
    assert not [f for f in os.listdir(cache) if ".part" in f and os.path.getsize(cache / f) > 0], os.listdir(cache)
    again = _FakeRemotion(total)
    done = rs.render_film(str(public), p, str(pf), str(public / "out.mp4"), [], {"gl": "angle"},
                          log=lambda *_: None, run=again)
    assert done["rendered"] == [2, 3] and [c for c in again.calls if c != "bundle"] == \
        ["%d-%d" % segs[2], "%d-" % segs[3][0]], (done, again.calls)


@needs_ffmpeg
def test_a_segment_the_wrong_length_is_refused_and_not_kept(public):
    """The model's other failure: Remotion renders a different number of frames than the timeline expects.
    That film is never assembled, and the segment is not cached under a key that would be trusted later."""
    p = _props([60, 70, 80])
    pf = public / ".remotion-props.json"
    pf.write_text(json.dumps(p), encoding="utf-8")
    total = rs.timeline(p["scenes"], TR)[1]
    with pytest.raises(rs.ModelMismatch):
        rs.render_film(str(public), p, str(pf), str(public / "out.mp4"), [], {"gl": "angle"},
                       log=lambda *_: None, run=_FakeRemotion(total + 5))   # the "film" is 5 frames longer
    assert not (public / "out.mp4").exists()
    assert not [f for f in os.listdir(public / rs.CACHE_DIR) if f.endswith(".mov") and ".part" not in f
                and f.startswith(rs.plan(p, str(public), {"gl": "angle"})[0][-1]["key"][:40])]


# ── the renderer routes to it, and away from it ────────────────────────────────────────────────────────
def _route(monkeypatch, tmp_path, meta=None, env=None, whole=False, mismatch=False):
    import render_remotion as rr
    calls = {"segmented": 0, "whole": 0}

    def fake_film(*a, **k):
        calls["segmented"] += 1
        if mismatch:
            raise rs.ModelMismatch("probe")
        return {"beats": 1, "rendered": [0], "frames": 60, "segments": [(0, 59, "k0")]}

    def fake_run(cmd, cwd=None, check=True):
        calls["whole"] += 1

    monkeypatch.setattr(rs, "render_film", fake_film)
    monkeypatch.setattr(rr.subprocess, "run", fake_run)
    monkeypatch.setattr(rr, "_remotion_deliverables", lambda *a, **k: None)
    monkeypatch.setattr(rr, "build_scenes", lambda slides, out_dir, valid, fps=30: [{"shot": "TermTable", "durF": 60}])
    monkeypatch.setattr(rr, "_remotion_shot_ids", lambda: {"TermTable"})
    monkeypatch.setattr(rr.shutil, "which", lambda _x: "/usr/bin/npx")
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    data = {"meta": dict({"renderer": "remotion"}, **(meta or {})), "slides": [{"index": 1}]}
    rr._render_remotion(str(tmp_path), data, whole=whole)
    return calls


@pytest.mark.parametrize("meta,env,whole,want", [
    ({}, {}, False, {"segmented": 1, "whole": 0}),                               # the default
    ({}, {}, True, {"segmented": 0, "whole": 1}),                                # --whole
    ({"segment_cache": False}, {}, False, {"segmented": 0, "whole": 1}),         # the board opts out
    ({}, {"REMOTION_SEGMENTS": "0"}, False, {"segmented": 0, "whole": 1}),       # the machine opts out
])
def test_the_renderer_goes_per_beat_unless_told_not_to(monkeypatch, tmp_path, meta, env, whole, want):
    assert _route(monkeypatch, tmp_path, meta, env, whole) == want


def test_a_model_disagreement_renders_the_film_whole_instead(monkeypatch, tmp_path):
    """Never shipped, never a dead end: the film still renders, the way it always did."""
    assert _route(monkeypatch, tmp_path, mismatch=True) == {"segmented": 1, "whole": 1}


def test_ranges_that_do_not_tile_the_film_are_refused_before_a_frame_is_rendered(public, monkeypatch):
    """The guard for a FUTURE broken timeline (a gap drops frames, an overlap doubles them, and neither
    changes any single segment's own frame count). Fed a gapped plan, nothing may be rendered."""
    p = _props([60, 70, 80])
    real = rs.plan

    def gapped(*a, **k):
        segs, total = real(*a, **k)
        segs[1] = dict(segs[1], a=segs[1]["a"] + 1)                    # frame a of beat 2 belongs to nobody
        return segs, total

    monkeypatch.setattr(rs, "plan", gapped)
    ran = []
    with pytest.raises(rs.ModelMismatch):
        rs.render_film(str(public), p, str(public / "p.json"), str(public / "out.mp4"), [], {},
                       log=lambda *_: None, run=lambda *a, **k: ran.append(a))
    assert not ran


@needs_ffmpeg
def test_the_film_is_bundled_once_and_every_beat_renders_from_that_bundle(public, monkeypatch):
    """Bundling measured 1.5-2 s of each segment's ~5 s fixed cost on the 37-beat film. Once per render,
    from a public folder of exactly the files the props name, and the scratch space is gone afterwards."""
    p = _props([60, 70, 80])
    pf = public / ".remotion-props.json"
    pf.write_text(json.dumps(p), encoding="utf-8")
    total = rs.timeline(p["scenes"], TR)[1]
    seen = []
    fake = _FakeRemotion(total)

    def spy(cmd, cwd=None, check=True):
        seen.append(list(cmd))
        return fake(cmd, cwd=cwd, check=check)

    made = []
    real_mkdtemp = rs.tempfile.mkdtemp
    monkeypatch.setattr(rs.tempfile, "mkdtemp", lambda **k: made.append(real_mkdtemp(**k)) or made[-1])
    rs.render_film(str(public), p, str(pf), str(public / "out.mp4"), [], {"gl": "angle"}, log=lambda *_: None,
                   run=spy)
    bundles = [c for c in seen if c[2] == "bundle"]
    renders = [c for c in seen if c[2] == "render"]
    assert len(bundles) == 1 and len(renders) == 3, [c[:4] for c in seen]
    served = next(a for a in bundles[0] if a.startswith("--out-dir=")).split("=", 1)[1]
    assert all(c[3] == served for c in renders), "a segment was rendered from something other than the bundle"
    assert not any(a.startswith("--public-dir=") for c in renders for a in c), "a render re-supplied the public dir"
    public_arg = next(a for a in bundles[0] if a.startswith("--public-dir=")).split("=", 1)[1]
    assert public_arg != str(public), "the bundle was given the whole out_dir as its public folder"
    assert made and not os.path.exists(made[0]), "the bundle's scratch space was left behind"


def test_the_minimal_public_folder_holds_exactly_what_the_props_name(public, tmp_path):
    (public / "big_old_render.mp4").write_bytes(b"x" * 1000)
    p = _props([60, 70])
    dest = rs.minimal_public(p, str(public), str(tmp_path / "pub"))
    got = sorted(os.path.relpath(os.path.join(d, f), dest) for d, _n, fs in os.walk(dest) for f in fs)
    assert got == ["audio/01.mp3", "audio/02.mp3"], got


def test_the_two_readers_of_the_seam_length_agree():
    """render_remotion and this module both read SEAM_FRAMES from runtime/motion.ts. The value cannot drift
    — it is one file — but a parse can: a regex that stopped matching would drop the timeline by a whole
    seam per cut in one module and not the other."""
    import render_remotion as rr
    assert rs.seam_frames() == rr.SEAM_FRAMES == rr._REMOTION2_TR


def _board(tmp_path, kicker="ONE"):
    (tmp_path / "audio").mkdir(exist_ok=True)
    slides = []
    for i in range(3):
        (tmp_path / "audio" / ("%02d.mp3" % (i + 1))).write_bytes(b"voice-%d" % i)
        slides.append({"index": i + 1, "shot": "TermTable", "narration": "第 %d 拍。" % (i + 1),
                       "audio": "audio/%02d.mp3" % (i + 1), "duration": 2.5,
                       "shot_props": {"kicker": kicker if i == 1 else "K%d" % i, "rows": [["a", "1"], ["b", "2"]]}})
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product"}, "slides": slides}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")


def test_the_plan_reads_the_board_as_it_is_now_not_the_last_render(tmp_path, capsys):
    """The question "which beats would a render redo?" is asked right after an edit. Answered from the
    last render's props file it says "none"; answered from the board it names the edited beat and the one
    whose seam shows it."""
    import render_remotion as rr
    import storyboard as sb
    _board(tmp_path)
    props, _slides = rr.film_props(str(tmp_path), sb.load(str(tmp_path / "storyboard.json")))
    cache = tmp_path / rs.CACHE_DIR
    cache.mkdir()
    for s in rs.plan(props, str(tmp_path), rs.pixel_flags(rs.default_gl()))[0]:
        open(rs.seg_path(str(cache), s["key"]), "w").close()             # "rendered"
    rs.main([str(tmp_path), "--plan"])
    assert "redoes 0 of 3" in capsys.readouterr().out
    _board(tmp_path, kicker="EDITED")                                     # edit the board, do not render
    rs.main([str(tmp_path), "--plan"])
    out = capsys.readouterr().out
    redo = [l.split()[1] for l in out.splitlines() if l.strip().endswith("RENDER")]
    assert redo == ["2", "3"] and "redoes 2 of 3" in out, out


@needs_ffmpeg
def test_an_unchanged_keyframe_is_kept_and_a_changed_one_is_not(tmp_path, monkeypatch):
    """Re-extracting all 74 keyframes was 42 of the 83 s a two-beat edit took on the 37-beat film. A frame of
    the joined film is a bit-exact copy of its segment's, so a keyframe at frame f of segment K is kept while
    both match — looked up BY FRAME, because a short beat settles inside the next beat's seam."""
    import render_remotion as rr
    scenes = [{"durF": 90, "caption": ""}, {"durF": 30, "caption": ""}, {"durF": 90, "caption": ""}]
    segs, total = rs.timeline(scenes, TR)
    film = str(tmp_path / "out.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=160x90:r=30", "-frames:v",
                    str(total), "-pix_fmt", "yuv420p", film], check=True)
    grabs = []
    real = rr.subprocess.run

    def spy(cmd, *a, **k):
        if cmd[0] == "ffmpeg":
            grabs.append(os.path.relpath(cmd[-1], str(tmp_path / "_keyframes")))
        return real(cmd, *a, **k)

    monkeypatch.setattr(rr.subprocess, "run", spy)
    keyed = lambda keys: [(a, b, k) for (a, b), k in zip(segs, keys)]
    rr._remotion_deliverables(str(tmp_path), scenes, film, 30, segments=keyed(["A", "B", "C"]))
    assert len(grabs) == 6, grabs                                         # first time: all of them
    grabs.clear()
    rr._remotion_deliverables(str(tmp_path), scenes, film, 30, segments=keyed(["A", "B", "C"]))
    assert grabs == [], "unchanged keyframes were extracted again: %r" % grabs
    # beat 2 (30 frames) settles inside beat 3's seam — so changing ONLY segment 3 must redo beat 2's
    # settled keyframe as well as beat 3's own two
    settled2 = rr.settled_frame(30) + segs[1][0]
    assert settled2 > segs[1][1], "the probe's short beat no longer settles in the next segment"
    rr._remotion_deliverables(str(tmp_path), scenes, film, 30, segments=keyed(["A", "B", "C2"]))
    assert sorted(grabs) == ["motion/scene_03.png", "scene_02.png", "scene_03.png"], grabs
    grabs.clear()
    rr._remotion_deliverables(str(tmp_path), scenes, film, 30)            # a whole render
    assert len(grabs) == 6 and not os.path.exists(str(tmp_path / "_keyframes" / rr._KEYFRAME_SOURCES))
