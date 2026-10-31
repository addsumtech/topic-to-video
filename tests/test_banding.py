"""Banding: the gate that sees it on the delivered file, and the dither that removes it (remotion/src/runtime/dither.tsx).

A dark gradient banded by the encode is invisible to every still a gate renders and to the DOM; CAMBI on the H.264 is
the only instrument that sees it. Measured on this tier's own films: 12-22 before the dither, 0.0 after.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import banding_qa  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _cambi_ok():
    if not shutil.which("ffmpeg"):
        return False
    r = subprocess.run(["ffmpeg", "-hide_banner", "-h", "filter=libvmaf"], capture_output=True, text=True)
    return r.returncode == 0 and "libvmaf" in (r.stdout + r.stderr)


needs_cambi = pytest.mark.skipif(not _cambi_ok(), reason="needs an ffmpeg with libvmaf")


def _film(tmp_path, noise):
    """A 2 s film of one dark radial gradient (two scenes of 1 s), encoded the way a film is: x264 CRF 18.

    The gradient is FIXED by its SEED. `gradients`' default seed is -1 (random), and setting x0..y1 does not take it
    out: with only those set, two runs still drew different pictures (CAMBI 3.4 in one, 15.0 in another, against the
    5.0 floor) — the test passed in one run and failed in the next on unchanged code. At seed=3 it reads 8.7 banded,
    0.0 dithered, every run (test_the_fixture_film_is_the_same_on_every_run)."""
    out = tmp_path / ("n%d" % noise)
    out.mkdir()
    vf = "format=yuv420p" + (",noise=c0s=%d:c0f=u" % noise if noise else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "gradients=s=960x540:c0=0x0b1020:c1=0x1a2a48:d=2:r=30:speed=0:type=radial:"
                    "x0=480:y0=270:x1=960:y1=540:seed=3", "-t", "2",
                    "-vf", vf, "-c:v", "libx264", "-crf", "18", str(out / "out.mp4")], check=True)
    json.dump({"meta": {}, "slides": [{"index": 1, "duration": 1.0}, {"index": 2, "duration": 1.0}]},
              open(out / "storyboard.json", "w"))
    return str(out)


def test_the_fixture_film_is_the_same_on_every_run(tmp_path):
    """Two draws of the fixture must be the same pixels, or the CAMBI floor below is judged on a different picture
    each run (it read 3.4 in one run and 15.0 in the next)."""
    import hashlib
    for i in (1, 2):
        (tmp_path / str(i)).mkdir()
    a, b = (_film(tmp_path / str(i), 0) for i in (1, 2))
    raw = [subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(f, "out.mp4"), "-frames:v", "1", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout for f in (a, b)]
    assert hashlib.sha256(raw[0]).hexdigest() == hashlib.sha256(raw[1]).hexdigest()


@needs_cambi
def test_a_banded_dark_gradient_is_found_and_a_dithered_one_is_not(tmp_path):
    film = _film(tmp_path, 0)
    banded = banding_qa.check(film, every=0.5)
    assert banded["measured"], banded
    assert {f["scene"] for f in banded["findings"]} == {"scene 01", "scene 02"}, banded
    clean = banding_qa.check(_film(tmp_path, 4), every=0.5)
    assert clean["measured"] and not clean["findings"], clean
    assert banding_qa.main([film, "--every=0.5"]) == 1


def test_no_film_is_not_measured_never_clean(tmp_path):
    r = banding_qa.check(str(tmp_path))
    assert r["measured"] is False and "out.mp4" in r["why"]
    assert banding_qa.main([str(tmp_path)]) == 2


@needs_ffmpeg
def test_the_render_asks_for_the_dither_and_a_gate_still_does_not(tmp_path):
    import render_remotion as rr
    import stage_frames as sf
    (tmp_path / "audio").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3",
                    str(tmp_path / "audio" / "01.wav")], check=True)
    board = {"meta": {"renderer": "remotion", "aspect": "16:9"},
             "slides": [{"index": 1, "shot": "TermTable", "duration": 3.0, "narration": "x", "caption": "x",
                         "audio": "audio/01.wav", "shot_props": {"rows": [["a", "1"]]}}]}
    json.dump(board, open(tmp_path / "storyboard.json", "w"))
    props, _ = rr.film_props(str(tmp_path), board)
    assert props["dither"] is True
    off, _ = rr.film_props(str(tmp_path), dict(board, meta=dict(board["meta"], dither=False)))
    assert off["dither"] is False
    assert sf.film_payload(str(tmp_path), board)["dither"] is False


def _still(tmp_path, name, dither):
    scene = {"shot": "TermTable", "durF": 90, "props": {"rows": [["a", "1"], ["b", "2"]]}}
    pf = str(tmp_path / (name + ".json"))
    json.dump({"scenes": [scene], "dna": "product", "captions": False, "camera": 0, "aspect": "16:9",
               "dither": dither}, open(pf, "w"))
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=60", "--gl=angle",
                        "--log=error", "--props=" + pf], cwd=_REM, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return png


@needs_toolchain
def test_the_dither_is_zero_mean_triangular_within_two_code_values_and_the_same_every_render(tmp_path):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    plain = np.asarray(Image.open(_still(tmp_path, "plain", False)).convert("RGB")).astype(int)
    d1 = np.asarray(Image.open(_still(tmp_path, "d1", True)).convert("RGB")).astype(int)
    d2 = np.asarray(Image.open(_still(tmp_path, "d2", True)).convert("RGB")).astype(int)
    assert (d1 == d2).all(), "two renders of the same dithered frame differ — the dither must be static and seeded"
    # on grounds brighter than the dither's own amplitude (where |b - n| = b - n), the change is the triangular ±2
    mask = plain.min(axis=2) >= 3
    diff = (d1 - plain)[mask]
    assert diff.min() >= -2 and diff.max() <= 2, (diff.min(), diff.max())
    assert abs(diff.mean()) < 0.05, diff.mean()
    share = {k: float((diff == k).mean()) for k in range(-2, 3)}
    assert share[0] > share[1] > share[2] > 0.05 and share[0] > share[-1] > share[-2] > 0.05, share
