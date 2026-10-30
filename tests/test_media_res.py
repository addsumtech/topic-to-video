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
