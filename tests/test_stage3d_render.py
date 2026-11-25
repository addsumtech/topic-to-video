"""The 3D stage's offline renderer and its Blender hand-off (references/3d-engines.md).
WHY: measured on an MRI scanner rendered every way (2026-11-25): the kit's defaults (a procedural room, one hard key)
read as CG beside Cycles; an HDRI, area lights averaged over many passes and an occlusion atlas baked by Cycles brought
three.js to within ~10 % of Cycles' luminance in 0.3 s a frame instead of ~45 s. These pin what that promises: passes
turn a shadow edge into a penumbra and stay a pure function of the state; the lens needs passes and the old bokeh
cannot be mixed in; a baked atlas darkens a model where it says and is refused on a model with no second UV set; and
the Blender export keeps a sheen's weight and writes the atlas."""
import base64
import json
import os
import shutil
import struct
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402
from test_blender_runner import needs_blender  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None
needs_chrome = pytest.mark.skipif(not CHROME, reason="Chrome not installed")
HDRI = os.path.join(ROOT, "blender", "kit", "hdri", "studio_small_09_1k.hdr")


def _run(tmp_path, body, shot=None, W=480, H=270):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    (tmp_path / "p.html").write_text("""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<canvas id="c" width="%d" height="%d"></canvas><script src="stage3d.js"></script><script>
window.filmReady = (async () => { %s })().then((r) => { window.__res = r; return 'ok'; }, (e) => { window.__res = 'ERR ' + e.message; return 'ok'; });
window.seek = () => {};
</script></body></html>""" % (W, H, body))
    port, srv = _fp.serve(str(tmp_path))
    try:
        p = _fp.FilmPage(port, "p.html", W, H)
        try:
            res = p.ev("window.__res")
            if shot:
                p.shot(str(tmp_path / shot), "png")
            return res
        finally:
            p.close()
    finally:
        srv.shutdown()


SHADOW = """
  const st = Stage3D.create({canvas: document.getElementById('c'), width: 480, height: 270, background: '#808080',
                             toneMapping: 'agx', passes: %d});
  const T = st.THREE;
  const floor = new T.Mesh(new T.PlaneGeometry(40, 40), new T.MeshStandardMaterial({color: '#dddddd', roughness: 1}));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; st.scene.add(floor);
  const box = new T.Mesh(new T.BoxGeometry(1, 2, 1), new T.MeshStandardMaterial({color: '#dddddd', roughness: 1}));
  box.position.set(0, 1, 0); box.castShadow = true; st.scene.add(box);
  st.areaLight({pos: [-3, 5, 0], aim: [0, 0, 0], size: 2.5, power: 900});
  await st.ready();
  const draw = () => { st.render({pos: [0, 9, 0.01], look: [0, 0, 0], fov: 40}); return st.renderer.domElement.toDataURL(); };
  const a = draw(), b = draw();
  return a === b;
"""


def _penumbra(png):
    """Rows of the column just beside the box that sit between the shadow's core and the lit floor above it: the width
    of the shadow's side edge (one pass: a stepped hard edge; many passes over an area light: a penumbra)."""
    a = np.asarray(Image.open(png).convert("L")).astype(float)
    col = a[60:135, 285]
    lit, core = col[:8].mean(), col.min()
    assert lit - core > 60, "the test scene should cast a visible shadow beside the box (lit %.0f, core %.0f)" % (lit, core)
    lo, hi = core + 0.1 * (lit - core), lit - 0.1 * (lit - core)
    return int(((col > lo) & (col < hi)).sum())


@needs_chrome
def test_passes_turn_a_hard_shadow_edge_into_a_penumbra_and_stay_deterministic(tmp_path):
    hard = tmp_path / "one"; hard.mkdir()
    soft = tmp_path / "many"; soft.mkdir()
    assert _run(hard, SHADOW % 1, "f.png") is True
    assert _run(soft, SHADOW % 48, "f.png") is True, "two renders of the same state must be identical (Halton, no clock)"
    w1, w48 = _penumbra(hard / "f.png"), _penumbra(soft / "f.png")
    assert w48 >= 3 * max(w1, 2), "an area light averaged over passes should widen the soft edge (1 pass %d px, 48 passes %d px)" % (w1, w48)


@needs_chrome
def test_the_lens_needs_passes_and_bokeh_does_not_mix_with_them(tmp_path):
    r = _run(tmp_path, """
  const st = Stage3D.create({canvas: document.getElementById('c'), width: 480, height: 270});
  st.render({pos: [0, 2, 8], look: [0, 1, 0], lens: 0.02});""")
    assert r.startswith("ERR") and "passes" in r
    r = _run(tmp_path, """
  Stage3D.create({canvas: document.getElementById('c'), width: 480, height: 270, passes: 16, dof: {aperture: 0.002}});""")
    assert r.startswith("ERR") and "lens" in r


def _glb(path, uv1=True):
    """A 2 x 2 m quad facing +Z with TEXCOORD_0 and (optionally) TEXCOORD_1, one white rough material."""
    pos = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]], "<f4")
    nrm = np.array([[0, 0, 1]] * 4, "<f4")
    uv = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], "<f4")
    idx = np.array([0, 1, 2, 0, 2, 3], "<u2")
    blobs = [pos.tobytes(), nrm.tobytes(), uv.tobytes()] + ([uv.tobytes()] if uv1 else []) + [idx.tobytes()]
    views, acc, off = [], [], 0
    for i, b in enumerate(blobs):
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(b)})
        off += (len(b) + 3) // 4 * 4
    acc = [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3", "min": [-1, -1, 0], "max": [1, 1, 0]},
           {"bufferView": 1, "componentType": 5126, "count": 4, "type": "VEC3"},
           {"bufferView": 2, "componentType": 5126, "count": 4, "type": "VEC2"}]
    attrs = {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}
    if uv1:
        acc.append({"bufferView": 3, "componentType": 5126, "count": 4, "type": "VEC2"})
        attrs["TEXCOORD_1"] = 3
    acc.append({"bufferView": len(blobs) - 1, "componentType": 5123, "count": 6, "type": "SCALAR"})
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": attrs, "indices": len(acc) - 1, "material": 0}]}],
           "materials": [{"pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0, "roughnessFactor": 1}}],
           "buffers": [{"byteLength": off}], "bufferViews": views, "accessors": acc}
    js = json.dumps(doc).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    binb = b"".join(b + b"\0" * ((4 - len(b) % 4) % 4) for b in blobs)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(binb), 0x004E4942) + binb)


AO_PAGE = """
  const st = Stage3D.create({canvas: document.getElementById('c'), width: 480, height: 270, background: '#000000', shadows: false});
  st.hdri('studio.hdr', {intensity: 1});
  st.glb('%s', {ao: 'ao.png'});
  await st.ready();
  st.render({pos: [0, 0, 3], look: [0, 0, 0], fov: 50});
  return 'drawn';
"""


@needs_chrome
def test_a_baked_occlusion_atlas_darkens_a_model_where_it_says_and_needs_a_second_uv_set(tmp_path):
    shutil.copy(HDRI, tmp_path / "studio.hdr")
    ao = np.full((64, 64), 255, np.uint8)
    ao[:, :32] = 40                                            # occluded on the atlas's left half
    Image.fromarray(ao).save(tmp_path / "ao.png")
    _glb(tmp_path / "quad.glb")
    _glb(tmp_path / "flat.glb", uv1=False)
    assert _run(tmp_path, AO_PAGE % "quad.glb", "f.png") == "drawn"
    a = np.asarray(Image.open(tmp_path / "f.png").convert("L")).astype(float)
    left, right = a[100:170, 170:225].mean(), a[100:170, 255:310].mean()
    assert right - left > 25, "the occluded half should render darker (left %.0f, right %.0f)" % (left, right)
    r = _run(tmp_path, AO_PAGE % "flat.glb")
    assert r.startswith("ERR") and "second UV set" in r


@needs_blender
def test_the_blender_export_keeps_sheen_weight_and_writes_the_occlusion_atlas(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "blender_clip.py"), str(tmp_path),
                        os.path.join(ROOT, "tests", "fixtures", "blender", "glb_scene.py"), "--glb", "--ao", "128",
                        "--name", "m"], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    b = open(tmp_path / "models" / "m.glb", "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    doc = json.loads(b[20:20 + n])
    sheen = {m["name"]: m.get("extensions", {}).get("KHR_materials_sheen") for m in doc["materials"]}
    assert sheen["plinth"]["sheenColorFactor"] == pytest.approx([0.25] * 3, abs=1e-3), \
        "a 0.25 sheen must not export as a full white one (%s)" % sheen["plinth"]
    assert all("TEXCOORD_1" in p["attributes"] for m in doc["meshes"] for p in m["primitives"])
    ao = np.asarray(Image.open(tmp_path / "models" / "m_ao.png").convert("L")).astype(float)
    assert ao.min() < 100 < ao.max(), "the atlas should hold both open and occluded surface"


def test_glb_flags_are_checked_before_blender_runs(tmp_path, capsys):
    script = os.path.join(ROOT, "scripts", "blender_clip.py")
    scene = os.path.join(ROOT, "tests", "fixtures", "blender", "glb_scene.py")
    r = subprocess.run([sys.executable, script, str(tmp_path), scene], capture_output=True, text=True)
    assert r.returncode == 2 and "--seconds" in r.stderr
    r = subprocess.run([sys.executable, script, str(tmp_path), scene, "--seconds", "1", "--ao", "256"], capture_output=True, text=True)
    assert r.returncode == 2 and "--ao goes with --glb" in r.stderr
