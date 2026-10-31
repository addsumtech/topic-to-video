"""style_qa — did the DRAWING change the way the spec says, on every beat? Measured against the unstyled render.

The failure the user named: "只换了配色，画法和线条还是原来的样子" — only the colours changed. A recolour moves hue and
keeps every edge where it was, every gradient smooth, every surface clean; a drawing style moves the edges (outlines,
weights, shadows), flattens or steps the fills, puts a tooth on the surface. The gate measures those, per beat, styled
against unstyled, and fails a spec axis that changed nothing anywhere, and a beat that changed nothing while the rest
of the film did.
"""
import json
import os
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw

import style_qa as sq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
needs_render = pytest.mark.skipif(not os.environ.get("STYLE_RENDER"), reason="renders: set STYLE_RENDER=1 (under rlock)")

_SPEC = {"name": "ink + flat", "refs": [], "refs_missing": "test",
         "line": {"outline": "all", "weight": 4, "color": "ink"}, "fill": {"mode": "flat"}}


def _scene(path, outline=False, flat=False, hue=0, tooth=False, lift=0):
    """A picture with a gradient disc, a box and a line — drawn plainly, or as a style would draw it."""
    w, h = 640, 360
    img = Image.new("RGB", (w, h), (236, 230, 218))
    px = img.load()
    for y in range(80, 280):                               # a horizontal gradient disc
        for x in range(80, 280):
            if (x - 180) ** 2 + (y - 180) ** 2 <= 100 ** 2:
                t = (x - 80) / 200.0
                px[x, y] = (int(40 + 120 * t), int(80 + 100 * t), int(200 + 40 * t)) if not flat else (100, 130, 220)
    d = ImageDraw.Draw(img)
    d.rectangle([340, 100, 560, 260], fill=(244, 211, 94), outline=(20, 20, 20) if outline else None,
                width=4 if outline else 0)
    if outline:
        d.ellipse([78, 78, 282, 282], outline=(20, 20, 20), width=4)
    d.line([340, 300, 600, 330], fill=(60, 60, 60), width=4 if outline else 2)
    if tooth or lift:
        rng = np.random.default_rng(7)
        a = np.asarray(img).astype(float) * (1 + (0.12 * (rng.random((h, w, 1)) - 0.5) if tooth else 0)) + lift
        img = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    if hue:
        img = img.convert("HSV")
        a = np.asarray(img).copy()
        a[..., 0] = (a[..., 0].astype(int) + hue) % 256
        img = Image.fromarray(a, "HSV").convert("RGB")
    img.save(path)
    return str(path)


def _beat(tmp_path, n, shot="ChartLive", exempt=False, **styled):
    un = _scene(tmp_path / ("u%d.png" % n))
    st = _scene(tmp_path / ("s%d.png" % n), **styled)
    bare = {k: v for k, v in styled.items() if k not in ("tooth", "lift")}       # the same drawing without its medium
    ns = _scene(tmp_path / ("n%d.png" % n), **bare) if bare != styled else None
    return {"beat": n, "shot": shot, "exempt": exempt, "m": sq.measure(st, un, ns)}


def test_a_recolour_is_an_error(tmp_path):
    beats = [_beat(tmp_path, k, hue=60) for k in (1, 2, 3)]
    found = sq.judge(_SPEC, beats)
    errs = [m for lv, m in found if lv == "ERROR"]
    assert any("recolour" in m for m in errs), found
    assert any("line" in m for m in errs) and any("fill" in m for m in errs), found


def test_a_restyle_passes(tmp_path):
    beats = [_beat(tmp_path, k, outline=True, flat=True) for k in (1, 2, 3)]
    assert [f for f in sq.judge(_SPEC, beats) if f[0] == "ERROR"] == []


def test_one_unstyled_beat_breaks_consistency(tmp_path):
    beats = [_beat(tmp_path, 1, outline=True, flat=True), _beat(tmp_path, 2),
             _beat(tmp_path, 3, outline=True, flat=True)]
    errs = [m for lv, m in sq.judge(_SPEC, beats) if lv == "ERROR"]
    assert any("beat 2" in m and "unstyled" in m for m in errs), errs


def test_exempt_beats_are_outside_consistency(tmp_path):
    beats = [_beat(tmp_path, 1, outline=True, flat=True), _beat(tmp_path, 2, shot="PhotoPlate", exempt=True),
             _beat(tmp_path, 3, outline=True, flat=True)]
    assert [f for f in sq.judge(_SPEC, beats) if f[0] == "ERROR"] == []


def test_an_axis_left_as_drawn_is_not_checked(tmp_path):
    spec = {"name": "paper", "refs": [], "refs_missing": "t", "surface": {"kind": "paper", "strength": 0.8}}
    beats = [_beat(tmp_path, k, tooth=True) for k in (1, 2)]
    assert [f for f in sq.judge(spec, beats) if f[0] == "ERROR"] == []        # no line/fill axis set: none checked
    beats = [_beat(tmp_path, k) for k in (3, 4)]
    errs = [m for lv, m in sq.judge(spec, beats) if lv == "ERROR"]
    assert any("surface" in m for m in errs), errs


def test_no_style_is_nothing_to_judge(tmp_path):
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "remotion"}, "slides": []}))
    rep = sq.check(str(tmp_path))
    assert rep["measured"] is False and "no meta.style" in rep["why"]


@needs_render
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg")
def test_a_cartoon_like_film_passes_and_writes_its_sheet(tmp_path):
    spec = json.load(open(os.path.join(ROOT, "tests", "fixtures", "style", "cartoonish_spec.json")))
    (tmp_path / "audio").mkdir()
    slides = []
    for i, shot in enumerate(["ClayStack", "KnowledgeGraph", "ChartLive"]):
        a = tmp_path / "audio" / ("%02d.wav" % (i + 1))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "4", str(a)],
                       check=True)
        slides.append({"index": i + 1, "shot": shot, "duration": 4.0, "narration": "x", "caption": "",
                       "audio": "audio/%02d.wav" % (i + 1), "shot_props": {}})
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "remotion", "aspect": "16:9",
                                                                   "style": spec}, "slides": slides}))
    rep = sq.check(str(tmp_path))
    assert rep["measured"], rep
    assert [f for f in rep["findings"] if f[0] == "ERROR"] == [], rep["findings"]
    assert os.path.isfile(rep["sheet"])


@needs_render
def test_a_boiling_line_is_not_jitter_but_the_type_is_still_judged(tmp_path):
    """jitter_qa reads type from the pixels; a style's boil moves the LINES beside it, which is not a type defect."""
    spec = {"name": "boil", "refs": [], "refs_missing": "t", "line": {"weight": 3, "color": "ink", "outline": "all",
                                                                       "wobble": 3, "boil_hz": 8}}
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps({"style": spec}))
    d = tmp_path / "clip"
    d.mkdir()
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "StyleProbe", str(d), "--sequence",
                        "--image-format=png", "--frames=0-23", "--gl=angle", "--log=error", "--props=" + str(pf)],
                       cwd=os.path.join(ROOT, "remotion"), capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    # the census says where the TYPE is on every frame — as a film's gate run has it — so the pixels judged are the
    # type's (`--clip` alone has no census and judges every edge-dense tile, a boiling line included, by design)
    import gzip
    import text_safe_qa as tsq
    bundle = tsq.glide_bundle(str(tmp_path / "bundle"))
    cen = tsq.glide_run([{"tag": "p", "id": "StyleProbe", "props": {"style": spec, "typeGlide": True},
                          "from": 0, "to": 23}], bundle)["p"]
    assert cen["frames"], cen
    truth = tmp_path / "census.json.gz"
    with gzip.open(truth, "wt", encoding="utf-8") as fh:
        json.dump({"frames": cen["frames"]}, fh)
    j = subprocess.run([shutil.which("python3") or "python3", os.path.join(ROOT, "scripts", "jitter_qa.py"), "--clip", str(d),
                        "--truth=" + str(truth)], capture_output=True, text=True)
    out = j.stdout + j.stderr
    assert j.returncode == 0, out[-1500:]
    assert "JITTER" not in out and "SHIMMER" not in out, out[-1500:]
    print(out[-2500:])
    assert out.count("CLEAN") >= 3, ("the type was not judged", out[-1500:])           # the probe's three lines of type


def test_a_surface_that_shifts_the_tone_is_an_error(tmp_path):
    """A medium is grain, not a veil: a dark film's tooth first rendered as a grey lift over every dark ground
    (KnowledgeGraph, ChartLive, WordTunnel went mid-grey, and a subtitle lost its contrast) while this gate passed."""
    spec = {"name": "paper", "refs": [], "refs_missing": "t", "surface": {"kind": "paper", "strength": 0.8}}
    lifted = [_beat(tmp_path, k, tooth=True, lift=40) for k in (1, 2)]
    errs = [m for lv, m in sq.judge(spec, lifted) if lv == "ERROR"]
    assert any("tone" in m for m in errs), errs
    grain = [_beat(tmp_path, k, tooth=True) for k in (3, 4)]
    assert [f for f in sq.judge(spec, grain) if f[0] == "ERROR"] == []
