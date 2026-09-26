"""DeviceHero: the device settles and shows its screen; a recording plays the moment the beat maps to it."""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _still(tmp_path, props, frame, name):
    pf = tmp_path / (name + ".json")
    pf.write_text(json.dumps(dict(props, dna="product"), ensure_ascii=False), encoding="utf-8")
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceHero", png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + str(pf), "--public-dir=" + str(tmp_path)],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    return png


@needs_toolchain
def test_a_recording_shows_the_moment_its_span_maps_to(tmp_path):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    import device_geometry as dg
    v = str(tmp_path / "rec.mp4")
    # each frame's grey level encodes its index (N*2), so the rendered colour says which moment is showing
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=390x844:r=30:d=4,geq=lum='min(255,N*2)':cb=128:cr=128", "-pix_fmt", "yuv420p", v],
                   check=True)
    screen = {"video": "rec.mp4", "spans": [{"f0": 0, "f1": 150, "v0": 1.0, "v1": 3.0}]}
    png = _still(tmp_path, {"device": "phone", "look": "flat", "screen": screen}, 75, "vid")
    s = dg.geometry("phone", "flat", 1920, 1080)["screen"]
    a = np.asarray(Image.open(png).convert("L"), dtype=float)
    centre = a[s["y"] + s["h"] // 2 - 5:s["y"] + s["h"] // 2 + 5, s["x"] + s["w"] // 2 - 5:s["x"] + s["w"] // 2 + 5]
    # frame 75 of the beat maps to 1.0 + 75/150 * 2.0 = 2.0 s = source frame 60 -> grey 120
    assert abs(float(centre.mean()) - 120) < 12, centre.mean()


@needs_toolchain
def test_the_standalone_demo_renders(tmp_path):
    _still(tmp_path, {}, 120, "demo")


def _still_err(tmp_path, props, frame, name):
    pf = tmp_path / (name + ".json")
    pf.write_text(json.dumps(dict(props, dna="product", aspect="16:9"), ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceHero", str(tmp_path / (name + ".png")),
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + str(pf),
                        "--public-dir=" + str(tmp_path)], cwd=_REM, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout + r.stderr


@needs_toolchain
def test_the_entrance_never_leaves_the_fitted_rect(tmp_path):
    """The laptop fills the content zone exactly at 16:9 (its bottom IS contentBottom), and the entrance used to
    slide up from below with a perspective centred on the frame: 35 px into the caption band while half opaque,
    and the settled turn's near corner still dipped below the edge. No bright device pixel may leave the body."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    import device_geometry as dg
    for aspect, (W, H), frame in (("16:9", (1920, 1080), 20), ("16:9", (1920, 1080), 30), ("16:9", (1920, 1080), 47),
                                  ("9:16", (1080, 1920), 20)):
        b = dg.geometry("laptop", "real", W, H)["body"]
        pf = tmp_path / ("e%s.json" % frame)
        pf.write_text(json.dumps({"device": "laptop", "look": "real", "dna": "product", "aspect": aspect}),
                      encoding="utf-8")
        png = str(tmp_path / ("e_%s_%d.png" % (aspect.replace(":", "x"), frame)))
        r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceHero", png, "--frame=%d" % frame,
                            "--gl=angle", "--log=error", "--props=" + str(pf)], cwd=_REM, capture_output=True,
                           text=True, timeout=900)
        assert r.returncode == 0, (r.stdout + r.stderr)[-400:]
        a = np.asarray(Image.open(png).convert("L"), dtype=int)
        out = a > 90
        out[max(0, b["y"] - 2):b["y"] + b["h"] + 2, max(0, b["x"] - 2):b["x"] + b["w"] + 2] = False
        assert not out.any(), "%s frame %d: %d bright pixels outside the body %r" % (aspect, frame, out.sum(), b)


@needs_toolchain
def test_a_screen_without_content_is_refused(tmp_path):
    for name, screen, needle in (("empty", {}, "needs an image, a recording"),
                                 ("bogus", {"page": "nonsense"}, "needs an image, a recording"),
                                 ("nospans", {"video": "rec.mp4"}, "needs its `spans`")):
        code, out = _still_err(tmp_path, {"device": "phone", "look": "flat", "screen": screen}, 60, name)
        assert code != 0 and needle in out, (name, out[-300:])

