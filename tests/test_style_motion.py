"""The style's MOTION — stepping ("on twos"), an easing personality, squash — and what it may not touch.

Stepping holds the REGISTER's clock on every 2nd or 3rd frame, after the sync warp, so the drawing moves the way
drawn animation does; the caption, the voice, the camera and the seams stay on ones. The easing personality reaches
every register through the shared easings it already imports (178 of 218 import easeOut* from runtime/motion).
"""
import json
import os
import re
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

import _tsprobe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "remotion")
needs_ts = pytest.mark.skipif(not _tsprobe.available(), reason="node/esbuild not available")
needs_render = pytest.mark.skipif(not os.environ.get("STYLE_RENDER"), reason="renders: set STYLE_RENDER=1 (under rlock)")


def _m(body):
    return _tsprobe.run_ts("import * as S from %s; import * as M from %s;"
                           % (_tsprobe.mod("styleMotion.ts"), _tsprobe.mod("motion.ts")), body)


@needs_ts
def test_stepping_after_warp_is_monotone_and_holds():
    out = _m("""
      const warp = (f: number) => (f < 100 ? f * 0.7 : 70 + (f - 100) * 1.6);       // a monotone sync warp
      out.seq = Array.from({length: 300}, (_, f) => S.stepFrame(Math.round(warp(f)), 2));
      out.twos = [0, 1, 2, 3, 4, 5].map((f) => S.stepFrame(f, 2));
      out.threes = [0, 1, 2, 3, 4, 5].map((f) => S.stepFrame(f, 3));
      out.ones = [0, 1, 2, 3].map((f) => S.stepFrame(f, 1));
    """)
    seq = out["seq"]
    assert all(b >= a for a, b in zip(seq, seq[1:]))
    assert out["twos"] == [0, 0, 2, 2, 4, 4]
    assert out["threes"] == [0, 0, 0, 3, 3, 3]
    assert out["ones"] == [0, 1, 2, 3]


def test_only_the_register_clock_steps_and_reduced_motion_does_not():
    film = open(os.path.join(REMOTION, "src", "Film.tsx"), encoding="utf-8").read()
    clock = film[film.index("const BeatClock"):]
    clock = clock[:clock.index("\n};") + 3]
    assert "stepFrame(" in clock and "reduced" in clock, "BeatClock does not step, or steps under reduced motion"
    rest = film.replace(clock, "")
    assert "stepFrame(" not in rest, "something besides the register's clock steps (captions, camera and seams stay on ones)"


@needs_ts
def test_squash_preserves_area():
    out = _m("out.s = [0, 0.2, 0.5, 0.9, 1].map((p) => S.squashAt(p, 0.6));")
    for s in out["s"]:
        assert abs(s["sx"] * s["sy"] - 1) < 1e-9
    assert out["s"][0] == {"sx": 1, "sy": 1} and out["s"][-1] == {"sx": 1, "sy": 1}
    assert any(abs(s["sx"] - 1) > 0.05 for s in out["s"][1:-1])


@needs_ts
def test_the_easing_personality_reaches_the_shared_easings():
    out = _m("""
      const ts = Array.from({length: 51}, (_, i) => i / 50);
      const curve = (k: any) => { M.setStyleEase(k); const v = ts.map((t) => M.easeOutCubic(t)); M.setStyleEase('as-drawn'); return v; };
      out.drawn = curve('as-drawn'); out.over = curve('overshoot'); out.snappy = curve('snappy'); out.floaty = curve('floaty');
      out.back = M.easeOutCubic(0.5);
      out.extrap = [M.easeOutCubic(-0.2), M.easeOutCubic(1.3), M.easeOutExpo(-0.1), M.easeInOutCubic(1.2)];
    """)
    for k in ("drawn", "over", "snappy", "floaty"):
        c = out[k]
        assert abs(c[0]) < 1e-9 and abs(c[-1] - 1) < 1e-9, k            # every personality starts at 0 and lands at 1
    assert max(out["over"]) > 1.02                                       # overshoot overshoots
    assert out["snappy"][10] > out["drawn"][10] + 0.05                   # snappy gets there sooner
    assert out["floaty"][10] < out["drawn"][10] - 0.1                    # floaty eases in
    assert abs(out["back"] - (1 - 0.5 ** 3)) < 1e-9                      # and as-drawn is restored
    # no style: exactly the old functions, extrapolation outside 0..1 included
    assert out["extrap"][0] == pytest.approx(1 - 1.2 ** 3) and out["extrap"][1] == pytest.approx(1 - (-0.3) ** 3)
    assert out["extrap"][2] == pytest.approx(1 - 2 ** 1.0) and out["extrap"][3] == pytest.approx(1 - (-0.4) ** 3 / 2)


def test_the_personality_is_set_on_every_render_entry():
    """Module state must be SET by each render entry (Film, a shot alone), never left over from a previous job."""
    film = open(os.path.join(REMOTION, "src", "Film.tsx"), encoding="utf-8").read()
    root = open(os.path.join(REMOTION, "src", "Root.tsx"), encoding="utf-8").read()
    assert "setStyleEase(" in film and "setStyleEase(" in root


def test_sync_tolerance_only_when_stepping():
    import sync_qa as sq
    assert sq.stepping_slack(None, 30) == 0
    assert sq.stepping_slack({"motion": {"stepping": 1}}, 30) == 0
    assert sq.stepping_slack({"motion": {"stepping": 3}}, 30) == pytest.approx(2 / 30)
    late = {"lag": sq.LAG_WARN + 0.03}
    assert sq.level(late) == "warn"
    assert sq.level(dict(late, slack=2 / 30)) == "ok"


def test_easing_coverage_is_listed_not_hidden():
    import style_coverage as sc
    cov = sc.motion_coverage()
    assert cov["shared"] >= 150 and cov["own"], cov                    # most use the shared easings; the rest are named
    assert all(isinstance(s, str) for s in cov["own"])


def _film_props(tmp_path, style):
    import render_remotion as rr
    (tmp_path / "audio").mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "4",
                    str(tmp_path / "audio" / "01.wav")], check=True)
    meta = {"renderer": "remotion", "aspect": "16:9"}
    if style:
        meta["style"] = style
    board = {"meta": meta, "slides": [{"index": 1, "shot": "ClayStack", "duration": 4.0, "narration": "x",
                                       "caption": "", "audio": "audio/01.wav", "shot_props": {}}]}
    json.dump(board, open(tmp_path / "storyboard.json", "w"))
    props, _ = rr.film_props(str(tmp_path), board)
    return dict(props, captions=False)


@needs_render
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg")
def test_a_stepped_film_holds_its_drawing_for_two_frames(tmp_path):
    spec = {"name": "twos", "refs": [], "refs_missing": "test", "motion": {"stepping": 2}}
    out = {}
    for tag, style in (("ones", None), ("twos", spec)):
        props = _film_props(tmp_path, style)
        pf = tmp_path / ("%s.json" % tag)
        pf.write_text(json.dumps(props))
        d = tmp_path / tag
        d.mkdir()
        r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Film", str(d), "--sequence",
                            "--image-format=png", "--frames=30-33", "--gl=angle", "--log=error", "--props=" + str(pf),
                            "--public-dir=" + str(tmp_path)],                 # the film's own audio, as the render serves it
                           cwd=REMOTION, capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
        out[tag] = [np.asarray(Image.open(os.path.join(d, f)).convert("RGB")).astype(int) for f in sorted(os.listdir(d))]
    ones, twos = out["ones"], out["twos"]
    moved = lambda a, b: float((np.abs(a - b).max(axis=2) > 2).mean())
    assert moved(ones[0], ones[1]) > 0.001, "the register is not moving here: the test frame is wrong"
    assert moved(twos[0], twos[1]) < 1e-4 and moved(twos[2], twos[3]) < 1e-4, "a stepped drawing moved on a held frame"
    assert moved(twos[1], twos[2]) > 0.001, "a stepped drawing never advanced"


def test_the_boil_steps_with_the_drawing():
    """On twos the picture holds two frames; a line that kept boiling every frame read as a tween over a drawing."""
    src = open(os.path.join(REMOTION, "src", "runtime", "style.tsx"), encoding="utf-8").read()
    assert "wobbleSeed(stepFrame(frame, step)" in src
