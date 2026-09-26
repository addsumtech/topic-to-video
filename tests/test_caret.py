"""CommandSummon's caret blinked on `t * 60` — a rate tied to the beat's LENGTH: measured frame by frame on a
5-second beat, 5.6 flashes a second, and it blinked while typing. A caret is solid while you type and blinks
at the system's pace afterwards; this measures the rendered frames, not the code."""
import json
import os
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _frames(tmp_path, durF=150):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    props = {"scenes": [{"shot": "CommandSummon", "durF": durF,
                         "props": {"command": "search last week feedback", "items": ["one", "two", "three"]}}],
             "dna": "product", "captions": False, "camera": 0}
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    mp4 = str(tmp_path / "cs.mp4")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Film", mp4, "--props=" + str(pf),
                        "--gl=angle", "--scale=0.5", "--log=error"], cwd=_REM, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-500:]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, 540, 960, 3).astype(int)


@needs_toolchain
def test_the_palette_caret_is_solid_while_typing_and_never_flickers(tmp_path):
    np = pytest.importorskip("numpy")
    fr = _frames(tmp_path)
    row = fr[:, 110:150, 215:785, :]
    on = ((row[..., 2] > 180) & (row[..., 2] - row[..., 0] > 60)).sum(axis=(1, 2)) > 20
    typing = on[20:60]
    assert typing.mean() > 0.9, "the caret is not solid while the command types: %r" % typing.astype(int)
    flips = int(np.sum(on[20:75][1:] != on[20:75][:-1]))
    assert flips <= 4, "the caret flipped %d times in under 2 s — it is flickering, not blinking" % flips
