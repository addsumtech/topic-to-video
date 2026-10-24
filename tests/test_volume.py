"""runtime/volume — light in a volume (aurora curtain, shafts, nebula, flame, layer), drawn by one shared WebGL context.

What is held here:
  * the pure core (runtime/volumeCore.ts, under node): a spec is checked loudly; the curtain's projection puts its
    lower border and top where the ruler beside it says; the colour key is the sourced emission physics; the keep-out
    leaves its floor inside the type and full light past its feather; the flame ramp is a blackbody ordering;
  * the WorldStage board check names a volume it could not draw;
  * RENDERED (VolumeProbe): every form draws something with structure (a layer that renders nothing passes a
    determinism check trivially), the keep-out actually clears the type's rect, the three registers keep their title
    at body contrast on their own lit ground;
  * DETERMINISM (scripts/determinism_qa.py): the probe is bit-stable twice / at concurrency 1 vs 3 / cold vs after its
    predecessors, and the stateLeak positive control FAILS — so the harness can see the defect it is run for.
Every rendering test here is slow; run this file under the render lock (rlock.py).
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe  # noqa: E402
import world_stage  # noqa: E402

_REM = os.path.join(_SKILL, "remotion")
CORE = _tsprobe.mod("volumeCore")
needs_node = pytest.mark.skipif(not _tsprobe.available(), reason="needs node + remotion/node_modules")


def _ts(body):
    return _tsprobe.run_ts("import * as V from %s;\n" % CORE, body)


# ── the pure core ───────────────────────────────────────────────────────────────────────────────────────────────
@needs_node
def test_a_spec_is_checked_loudly():
    r = _ts("""
      const tryIt = (s: any) => { try { V.checkVolume(s); return 'ok'; } catch (e: any) { return String(e.message); } };
      out.ok = tryIt({form: 'curtain'});
      out.form = tryIt({form: 'smoke'});
      out.hot = tryIt({form: 'nebula', intensity: V.VOLUME_MAX_INTENSITY + 0.01});
      out.zero = tryIt({form: 'nebula', intensity: 0});
      out.col = tryIt({form: 'shafts', colors: ['orange']});
      out.overlap = tryIt({form: 'curtain', bands: [{from: 100, to: 210, color: '#00ff00'}, {from: 200, to: 300, color: '#ff0000'}]});
      out.occ = tryIt({form: 'shafts', occluder: 'fog'});
      out.sheets = tryIt({form: 'curtain', sheets: 4});
      out.defaults = V.checkVolume({form: 'layer'});
    """)
    assert r["ok"] == "ok"
    assert "unknown volume form" in r["form"]
    assert "intensity" in r["hot"] and "intensity" in r["zero"]
    assert "#rrggbb" in r["col"]
    assert "overlap" in r["overlap"], "one altitude, one colour"
    assert "occluder" in r["occ"] and "sheets" in r["sheets"]
    assert r["defaults"]["intensity"] == 1.0 and r["defaults"]["speed"] == 1 and r["defaults"]["seed"] == 1


@needs_node
def test_the_colour_key_is_the_sourced_emission_physics():
    """NASA Science 'Auroras' (bench-aurora/sources/nasa-auroras.txt): pink <=100 km (N2), green 100-200 km (O),
    red >=200 km (O). The table must say exactly those spans, in that order, and the source text must still say them."""
    r = _ts("""out.b = V.AURORA_BANDS; out.low = V.AURORA_LOWER_KM;
      out.at = [90, 150, 260].map((k) => V.colourAt(V.AURORA_BANDS, k));
      out.at200 = V.colourAt(V.AURORA_BANDS, 200); out.below = V.colourAt(V.AURORA_BANDS, 60);
      out.w = [90, 150, 200, 260].map((k) => V.bandWeights(V.AURORA_BANDS, k));""")
    spans = [(b["from"], b["to"]) for b in r["b"]]
    assert spans[0][1] == 100 and spans[1] == (100, 200) and spans[2][0] == 200
    assert r["low"] == 100
    assert r["at"] == [b["color"] for b in r["b"]], "each altitude takes its own band's colour"
    assert r["at200"] not in [b["color"] for b in r["b"]], "the green turns red THROUGH the 200 km line"
    assert r["below"] is None, "no emission below the lower border"
    assert r["w"][0][1] == 0 and r["w"][0][0] == 1, "the thin pink fringe keeps its colour: no green bleeds into it"
    src = os.path.join(_SKILL, ".superpowers", "films", "bench-aurora", "sources", "nasa-auroras.txt")
    if os.path.exists(src):
        txt = open(src, encoding="utf-8").read()
        for row in ("Red≥120 miles (≥200 km)Oxygen", "Green60-120 miles (100-200 km)Oxygen", "Pink≤60 miles (≤100 km)Nitrogen"):
            assert row in txt, row


@needs_node
def test_the_ruler_and_the_light_share_one_projection():
    r = _ts("""
      const f = V.curtainFit(100, 700, 100, 320);
      out.low = f.yOf(100); out.top = f.yOf(320); out.mid = f.yOf(210); out.k = f.k;
      try { V.curtainFit(700, 100); out.err = 'none'; } catch (e: any) { out.err = String(e.message); }
    """)
    assert r["low"] == pytest.approx(700) and r["top"] == pytest.approx(100) and r["mid"] == pytest.approx(400)
    assert r["k"] == pytest.approx(600 / 220)
    assert "below the top" in r["err"]


@needs_node
def test_the_keep_out_leaves_its_floor_inside_and_full_light_past_its_feather():
    r = _ts("""
      const rect = {x: 100, y: 100, w: 400, h: 120};
      const rows = V.keepOutRows([rect]);
      out.inside = V.keepOutAt(rows, 300, 160);
      out.corner = V.keepOutAt(rows, 100, 100);
      out.far = V.keepOutAt(rows, 1500, 900);
      out.floor = V.VOLUME_KEEP_FLOOR;
      const big = V.keepOutRows([{x: 0, y: 0, w: 1200, h: 200}])[0], small = rows[0];
      out.bigFeather = big.rx - 600 * Math.SQRT2; out.smallFeather = small.rx - 200 * Math.SQRT2;
      try { V.keepOutRows(Array.from({length: V.VOLUME_MAX_KEEPOUT + 1}, () => rect)); out.many = 'none'; }
      catch (e: any) { out.many = String(e.message); }
    """)
    assert r["inside"] == pytest.approx(r["floor"]) and r["corner"] == pytest.approx(r["floor"])
    assert r["far"] == pytest.approx(1.0)
    assert r["bigFeather"] > r["smallFeather"] >= 90, "a big block of type gets a wider feather (no hard ellipse)"
    assert "at most" in r["many"]


@needs_node
def test_the_flame_ramp_is_a_blackbody_ordering():
    r = _ts("out.c = V.FLAME_KELVIN.map((k) => V.blackbody(k)); out.k = V.FLAME_KELVIN;")
    rgb = [[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in r["c"]]
    assert r["k"] == sorted(r["k"])
    for c in rgb:
        assert c[0] >= c[1] >= c[2], "a flame's colours are red-dominant at these temperatures"
    assert rgb[-1][2] > rgb[0][2] and rgb[-1][1] > rgb[0][1], "hotter is whiter"


def test_the_world_check_names_a_volume_it_could_not_draw(tmp_path):
    def run(obj):
        b1 = {"world": {"objects": {"sky": obj}}, "camera": {"frame": "sky"}}
        return [{"index": 1, "shot": "WorldStage", "stage": {"run": "w"}, "shot_props": b1, "narration": "天空"}]
    ok = world_stage.check(run({"kind": "volume", "form": "curtain", "at": [0, 0, 0], "w": 2}), 0, 0, str(tmp_path))
    assert ok == []
    no_form = world_stage.check(run({"kind": "volume", "at": [0, 0, 0], "w": 2}), 0, 0, str(tmp_path))
    assert any("needs `form`" in p for p in no_form), no_form
    hot = world_stage.check(run({"kind": "volume", "form": "nebula", "intensity": 9, "at": [0, 0, 0], "w": 2}), 0, 0)
    assert any("intensity" in p for p in hot), hot
    assert set(world_stage.volume_forms()) == {"curtain", "shafts", "nebula", "flame", "layer"}


# ── rendered ────────────────────────────────────────────────────────────────────────────────────────────────────
_rendering = pytest.mark.skipif(not _tsprobe.available() or os.environ.get("VOLUME_RENDER") == "0",
                                reason="needs node + remotion; VOLUME_RENDER=0 skips the rendering tests")


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("vol_bundle"))
    subprocess.run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + out, "--log=error"], cwd=_REM,
                   check=True, capture_output=True)
    return out


def _still(bundle, comp, frame, props, out):
    pf = out + ".json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh, ensure_ascii=False)
    subprocess.run(["npx", "remotion", "still", bundle, comp, out, "--frame=%d" % frame, "--gl=angle",
                    "--props=" + pf, "--log=error"], cwd=_REM, check=True, capture_output=True)
    from PIL import Image
    return np.asarray(Image.open(out).convert("RGB")).astype(np.float64) / 255.0


def _lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


@_rendering
def test_every_form_draws_light_with_structure(bundle, tmp_path):
    """Switched on, each form lifts its frame off the ground AND varies across it (a flat wash would pass a mean)."""
    for form in ("curtain", "shafts", "nebula", "flame", "layer"):
        a = _lum(_still(bundle, "VolumeProbe", 45, {"only": form}, str(tmp_path / ("%s.png" % form))))
        assert a.mean() > 0.04, (form, a.mean())
        assert a.std() > 0.03, (form, a.std())
        assert a.max() > 0.25, (form, a.max())


@_rendering
def test_the_keep_out_clears_the_type_rect(bundle, tmp_path):
    """The nebula fills the frame; with the probe's title rect kept out, the light inside that rect (glyphs excluded:
    its darker 80%) falls to about the floor's share of what it is without the keep-out."""
    a = _still(bundle, "VolumeProbe", 45, {"only": "nebula", "spec": {"seed": 9}}, str(tmp_path / "free.png"))
    b = _still(bundle, "VolumeProbe", 45, {"only": "nebula", "spec": {"seed": 9}, "keepOut": True}, str(tmp_path / "kept.png"))
    H, W = a.shape[:2]
    y0, y1, x0, x1 = int(H * 0.1), int(H * 0.22), int(W * 0.07), int(W * 0.43)
    la, lb = _lum(a[y0:y1, x0:x1]).ravel(), _lum(b[y0:y1, x0:x1]).ravel()
    ground = float(_lum(np.array([[[4, 7, 13]]]) / 255.0).ravel()[0])
    lit_a = np.percentile(la, 50) - ground
    lit_b = np.percentile(lb[lb <= np.percentile(lb, 80)], 50) - ground
    assert lit_a > 0.02, "the nebula has light in that rect to clear"
    assert lit_b < 0.45 * lit_a, (lit_a, lit_b)


def _contrast(fg, bg):
    hi, lo = max(fg, bg), min(fg, bg)
    return (hi + 0.05) / (lo + 0.05)


def _lin(c):
    c = np.asarray(c)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


@_rendering
@pytest.mark.parametrize("shot,props,frame,box", [
    ("NebulaField", {"title": "恒星诞生的地方", "note": "气体被附近的热星点亮"}, 160, (0.07, 0.08, 0.46, 0.30)),
    ("LightShafts", {"title": "一道缝隙就够了", "breakAt": 0.45}, 140, (0.07, 0.55, 0.5, 0.82)),
    ("AuroraCurtain", {"title": "颜色，就是高度"}, 150, (0.065, 0.07, 0.6, 0.22)),
])
def test_the_title_keeps_body_contrast_on_its_lit_ground(bundle, tmp_path, shot, props, frame, box):
    """The title's glyphs (the brightest 3% of the box) against the ground under them (the box's median), in relative
    luminance — >= 4.5:1, at 16:9 and 9:16, on the settled frame."""
    for asp in ("16:9", "9:16"):
        a = _still(bundle, shot, frame, dict(props, aspect=asp), str(tmp_path / ("%s_%s.png" % (shot, asp.replace(":", "x")))))
        H, W = a.shape[:2]
        x0, y0, x1, y1 = box
        if asp == "9:16":
            x1 = min(0.92, x1 * 1.8)
        crop = a[int(H * y0):int(H * y1), int(W * x0):int(W * x1)]
        rl = (_lin(crop) * [0.2126, 0.7152, 0.0722]).sum(axis=-1).ravel()
        fg, bg = np.percentile(rl, 99), np.percentile(rl, 50)
        assert _contrast(fg, bg) >= 4.5, (shot, asp, fg, bg, _contrast(fg, bg))


@_rendering
def test_the_probe_is_deterministic_and_the_harness_sees_a_leak():
    import determinism_qa
    rep = determinism_qa.run("VolumeProbe", {}, 40, 44)
    assert rep["ok"], [x for x in rep["results"] if x["fail"]]
    assert len(rep["results"]) == 11, "twice x5, concurrency x5, cold x1 — every comparison counted"
    leak = determinism_qa.run("VolumeProbe", {"stateLeak": True}, 40, 44, layers=[("stateLeak", {"stateLeak": False})])
    assert not leak["ok"], "the positive control (a module counter fed into the seed) must FAIL the harness"
    failed = {x["test"] for x in leak["results"] if x["fail"]}
    assert {"cold", "concurrency"} <= failed, leak["results"]
    assert all(leak["blame"][t] == "stateLeak" for t in failed), leak["blame"]
