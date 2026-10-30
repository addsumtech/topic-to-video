"""Pictures drawn at their own resolution — scripts/media_res_qa.py over runtime/mediaRes.tsx.

A product film shipped its hero UI soft: 1000 px demo frames drawn 2.9x larger through a 3D slab and a camera push,
a bots row at 2.0x. Every gate was green, because every one measured text. These pin the judgement (what is an
ERROR, what is excused, that a sequence is one picture), that the census is wired into the Film and the delivery
gates, and that no register imports it — so adding it never re-keyed a measured manifest.
"""
import glob
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import media_res_qa as m          # noqa: E402


def _row(src, s, op=1.0, blur=0.0, nw=1000, nh=500):
    return ["img", src, nw, nh, int(nw * s), int(nh * s), "fill", s, op, blur]


def _judge(frames):
    return m.judge(frames, lambda f: 0, [2], ["ScreenSlab"])


def test_a_picture_held_past_the_error_scale_is_an_error_naming_its_pixels():
    r = _judge({f: {"m": [_row("loop/f%05d.jpg" % f, 2.86)]} for f in (3, 6, 9)})
    assert len(r["errors"]) == 1, r
    assert "1000x500" in r["errors"][0] and "2.86x" in r["errors"][0] and "loop/f#####.jpg" in r["errors"][0]


def test_a_mild_magnification_warns_and_native_is_silent():
    r = _judge({3: {"m": [_row("a.png", 1.12)]}, 6: {"m": [_row("a.png", 1.15)]}, 9: {"m": [_row("b.png", 1.0)]}})
    assert not r["errors"] and len(r["warns"]) == 1 and "a.png" in r["warns"][0]


def test_one_frame_is_a_seam_flash_not_a_finding():
    r = _judge({3: {"m": [_row("a.png", 3.0)]}, 6: {"m": []}})
    assert not r["errors"] and not r["warns"]


def test_blurred_or_faded_pictures_are_excused_not_judged():
    frames = {f: {"m": [_row("glow.png", 2.0, blur=19), _row("leaving.png", 2.0, op=0.1)]} for f in (3, 6)}
    r = _judge(frames)
    assert not r["errors"] and not r["warns"] and len(r["excused"]) == 2


def test_an_image_sequence_is_one_picture():
    assert m._sequence("loop/f00028.jpg") == m._sequence("loop/f00346.jpg") == "loop/f#####.jpg"
    assert m._sequence("media/watch-send.png") == "media/watch-send.png"


def test_the_film_mounts_the_census_only_when_asked():
    src = open(os.path.join(_ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert "{mediaRes ? <MediaResAudit /> : null}" in src and "mediaRes = false" in src


def test_no_register_imports_the_census():
    """The manifests key each register on its own source and every module it imports (register_energy.source_hash):
    a register importing this would re-key itself whenever the census changed."""
    hits = [os.path.basename(f) for f in glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))
            if "runtime/mediaRes" in open(f, encoding="utf-8").read()]
    assert not hits, hits


def test_the_census_is_a_blocking_delivery_gate_on_the_remotion_tier():
    import critic_ledger as cl
    rows = [r for r in cl.DELIVERY_GATES["remotion"] if r[1] == "media_res_qa.py"]
    assert rows and rows[0][4] is True


def test_the_runner_reads_the_census_tag():
    src = open(os.path.join(_ROOT, "scripts", "glide_frames.cjs"), encoding="utf-8").read()
    assert "opt('tag'" in src and "everyNthFrame" in src
    assert m.TAG.replace(" ", "_").replace("_", " ") == "MEDIA-RES "
    runtime = open(os.path.join(_ROOT, "remotion", "src", "runtime", "mediaRes.tsx"), encoding="utf-8").read()
    assert "export const MEDIA_RES_TAG = '%s'" % m.TAG in runtime


# ── the edges: every outcome is said in words, and an unmeasured census is never an ok ─────────────────────────────
def _finish(tmp_path, frames, want, why=None, mp4=True):
    import time
    out = str(tmp_path)
    open(os.path.join(out, "storyboard.json"), "w").write("{}")
    if mp4:
        time.sleep(0.01)
        open(os.path.join(out, "out.mp4"), "wb").write(b"\0")
    res = {"frames": frames}
    return m.finish(res, want, why, lambda f: 0, [1], ["PhotoPlate"], out, want * 3, 3, 1, time.time())


def test_a_film_with_no_raster_is_nothing_to_judge_said_in_those_words(tmp_path, capsys):
    r = _finish(tmp_path, {f: {"n": 0, "m": []} for f in range(0, 30, 3)}, 10)
    assert m.verdict(r) == ("NOTHING TO JUDGE", 0)
    assert r["sampled"] == 10 and r["pictures"] == 0 and not r["unmeasured"]


def test_a_census_that_lost_frames_is_unmeasured_exit_2_even_with_no_finding(tmp_path):
    """A frame-count mismatch between the census and the film: the frames it never logged are not clean."""
    r = _finish(tmp_path, {f: {"n": 1, "m": []} for f in range(0, 15, 3)}, 10)
    assert m.verdict(r) == ("UNMEASURED", 2) and "only 5 of 10" in r["unmeasured"][0]
    r = _finish(tmp_path, {}, 10, why="render FAILED: boom")
    assert m.verdict(r) == ("UNMEASURED", 2)


def test_an_error_outranks_an_unmeasured_tail(tmp_path):
    frames = {f: {"n": 1, "m": [_row("a.png", 2.0)]} for f in (0, 3, 6)}
    r = _finish(tmp_path, frames, 10)
    assert m.verdict(r) == ("FAIL", 1)


def test_the_scope_says_what_was_measured_and_where_from(tmp_path):
    r = _finish(tmp_path, {f: {"n": 1, "m": []} for f in range(0, 30, 3)}, 10, mp4=False)
    lines = m.scope_lines(r)
    assert any("MEASURED" in ln and "10 of 30 frames" in ln for ln in lines)
    assert any("NOT MEASURED" in ln and "background-image" in ln for ln in lines)
    assert "no out.mp4 yet" in r["source"]
    r = _finish(tmp_path, {f: {"n": 1, "m": []} for f in range(0, 30, 3)}, 10)
    assert "not older than the board" in r["source"]


def test_a_board_that_cannot_be_read_is_unmeasured_not_a_crash(tmp_path, capsys):
    assert m.main([str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "NOT MEASURED" in out and "scope: nothing was measured" in out


def test_the_icon_floor_is_one_number_and_scales_with_the_frame():
    runtime = open(os.path.join(_ROOT, "remotion", "src", "runtime", "mediaRes.tsx"), encoding="utf-8").read()
    assert "export const MIN_DRAWN_PX = %d;" % m.MIN_DRAWN_REF_PX in runtime
    assert "MIN_DRAWN_PX * Math.min(frame.width, frame.height) / 1080" in runtime


# ── the census at the frames it was never run at (E6/E8): a small and a large picture at 9:16 and 1:1 ──────────────
import json        # noqa: E402
import subprocess  # noqa: E402

import pytest      # noqa: E402

_RLOCK = "/Users/donghanglyu/code_project/film_work/tools/rlock.py"


def _photo_film(out, aspect, size):
    from PIL import Image, ImageDraw
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    os.makedirs(os.path.join(out, "audio"), exist_ok=True)
    im = Image.new("RGB", size, (40, 60, 90))
    d = ImageDraw.Draw(im)
    for x in range(0, size[0], max(4, size[0] // 60)):          # detail, so the picture is a picture
        d.line([(x, 0), (x, size[1])], fill=(200, 210, 220), width=1)
    im.save(os.path.join(out, "media", "photo.png"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3",
                    os.path.join(out, "audio", "01.wav")], check=True)
    board = {"meta": {"renderer": "remotion", "language": "en", "aspect": aspect},
             "slides": [{"index": 1, "type": "slide", "shot": "PhotoPlate", "narration": "Look at the photograph.",
                         "duration": 3.0, "audio": "audio/01.wav",
                         "shot_props": {"src": "media/photo.png", "title": "The photograph", "marks": []}}]}
    json.dump(board, open(os.path.join(out, "storyboard.json"), "w"))
    return out


@pytest.mark.skipif(not os.environ.get("GATE_RENDER"), reason="renders the census: set GATE_RENDER=1")
@pytest.mark.parametrize("aspect", ["9:16", "1:1"])
def test_a_small_picture_is_soft_and_a_large_one_is_not_at_portrait_and_square(tmp_path, aspect):
    res = {}
    for name, size in (("small", (480, 320)), ("large", (3000, 2000))):
        out = _photo_film(str(tmp_path / name), aspect, size)
        cmd = [sys.executable, os.path.join(_ROOT, "scripts", "media_res_qa.py"), out]
        if os.path.exists(_RLOCK) and not os.environ.get("RLOCK_HELD"):
            cmd = [sys.executable, _RLOCK, "--"] + cmd
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=_ROOT)
        res[name] = (r.returncode, r.stdout)
    assert res["small"][0] == 1 and "ERROR" in res["small"][1] and "480x320" in res["small"][1], res["small"]
    assert res["large"][0] == 0 and " ok " in res["large"][1], res["large"]
    for _code, out in res.values():
        assert "scope: MEASURED" in out and "scope: NOT MEASURED" in out
