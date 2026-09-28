"""TechnicalPlate draws a film's own drawing in place of strokes (`art`); HudReticle locks onto a film's object
(`object`). Each keeps its own words where they were and its type inside the frame at every aspect."""
import os
import re
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
import render_remotion as rr  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

ART = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'survey-archive'};
export const %(name)s: React.FC<ObjectProps> = ({w, h, t}) => (
  <div style={{width: w, height: h, background: '#ff00ff', opacity: t}} />
);
"""
PARTS = [{"n": 1, "label": "压粉面", "x": 0.3, "y": 0.4, "side": "left"},
         {"n": 2, "label": "手柄", "x": 0.8, "y": 0.6, "side": "right"}]


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("slotted") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsArt.tsx").write_text(ART % {"name": "WsArt"}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _duration(name):
    src = open(os.path.join(_REM, "src", "shots", name + ".tsx"), encoding="utf-8").read()
    return int(re.search(r"export const DURATION\s*=\s*(\d+)", src).group(1))


def _settled_frame(name):
    return int(round(rr.frame_at_t(_duration(name), rr.SETTLED_T)))


def _magenta(png):
    a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
    m = (a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] > 200)
    ys, xs = np.nonzero(m)
    return int(m.sum()), (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None


def _stray_ink_in_box(png, box):
    """Ink inside `box` (padded a little for anti-aliasing) that is neither the frame's own background nor the
    magenta object — a bicycle stroke sharing the art's own unit square, or a caption riding up into it, would
    both show up here; nothing else is drawn inside that square when an object fills it."""
    a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
    bg = a[2, 2]
    pad = 6
    x0, y0 = max(0, box[0] - pad), max(0, box[1] - pad)
    x1, y1 = min(a.shape[1] - 1, box[2] + pad), min(a.shape[0] - 1, box[3] + pad)
    region = a[y0:y1 + 1, x0:x1 + 1]
    is_bg = np.all(np.abs(region - bg) <= 24, axis=-1)
    is_magenta = (region[..., 0] > 200) & (region[..., 1] < 60) & (region[..., 2] > 200)
    return int((~(is_bg | is_magenta)).sum()), region.shape[0] * region.shape[1]


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16"])
def test_the_plate_draws_the_film_s_art_with_its_callouts_on_it(film, tmp_path, aspect):
    props = {"art": {"id": "WsArt"}, "parts": PARTS, "object": "压粉器", "kicker": "图版", "dna": "product",
             "aspect": aspect}
    frame = _settled_frame("TechnicalPlate")
    r = _still("TechnicalPlate", tmp_path / "p.png", props, _env(ws.workshop_dir(film)), frame=frame)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _magenta(tmp_path / "p.png")
    assert n > 40000 and box, (n, box)
    assert abs((box[2] - box[0]) - (box[3] - box[1])) <= 4, box          # the art keeps its square
    # NOTHING ELSE SHARES THE ART'S OWN SQUARE — in particular not the demo bicycle's strokes, which draw in
    # this same unit space and would leak through if `art` and `strokes` were ever rendered together.
    stray, area = _stray_ink_in_box(tmp_path / "p.png", box)
    assert stray < 0.03 * area, (stray, area, box)
    found = g.audit_shot("TechnicalPlate", props, frame, str(tmp_path / "a.png"), env=_env(ws.workshop_dir(film)))
    assert found == [], found


@needs_toolchain
def test_the_plate_caps_the_art_above_a_two_line_name_and_note(film, tmp_path):
    """At 16:9 the art's square can reach the drawing field's own bottom, close under a one-line caption — a
    two-line name and a two-line note need more room than that leaves, and without a cap the caption would
    rise into the art's own square rather than the art shrinking to leave room for it."""
    props = {"art": {"id": "WsArt"}, "parts": PARTS, "dna": "product", "aspect": "16:9",
             "object": "一台压粉器,压实每一份咖啡粉,让水流均匀通过",
             "note": "它决定了萃取是否均匀,是整条冲煮链路里最容易被忽略、却又最关键的一步,值得被看见"}
    frame = _settled_frame("TechnicalPlate")
    r = _still("TechnicalPlate", tmp_path / "p2.png", props, _env(ws.workshop_dir(film)), frame=frame)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _magenta(tmp_path / "p2.png")
    assert n > 20000 and box, (n, box)
    stray, area = _stray_ink_in_box(tmp_path / "p2.png", box)
    assert stray < 0.03 * area, (stray, area, box)                       # the two-line caption does not ride up into it
    found = g.audit_shot("TechnicalPlate", props, frame, str(tmp_path / "a2.png"), env=_env(ws.workshop_dir(film)))
    assert found == [], found


@needs_toolchain
def test_the_plate_refuses_art_and_strokes_together_and_art_without_parts(film, tmp_path):
    env = _env(ws.workshop_dir(film))
    both = _still("TechnicalPlate", tmp_path / "b.png", {"art": {"id": "WsArt"}, "parts": PARTS,
                  "strokes": [{"kind": "circle", "x": 0.5, "y": 0.5, "r": 0.2}]}, env)
    assert both.returncode != 0 and "both `art` and `strokes`" in both.stdout + both.stderr
    bare = _still("TechnicalPlate", tmp_path / "c.png", {"art": {"id": "WsArt"}}, env)
    assert bare.returncode != 0 and "`art` but no `parts`" in bare.stdout + bare.stderr


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1"])
def test_the_reticle_locks_onto_the_film_s_object_and_keeps_its_name_in_the_ring(film, tmp_path, aspect):
    props = {"object": {"id": "WsArt"}, "target": "咖啡机的冲煮头", "readouts": ["水温 · 稳定", "压力 · 上升"],
             "title": "锁定", "scanLabel": "扫描中", "lockLabel": "● 已锁定", "dna": "product", "aspect": aspect}
    W, H = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}[aspect]
    frame = _settled_frame("HudReticle")
    r = _still("HudReticle", tmp_path / "h.png", props, _env(ws.workshop_dir(film)), frame=frame)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _magenta(tmp_path / "h.png")
    assert n > 20000 and box, (n, box)
    # KEEPS ITS NAME IN THE RING: the object itself sits in the upper part of the inner ring (objBox's own
    # `y: cy - innerR * 0.8`), with the name below it — so the object's own vertical centre is above the
    # frame's mid-line, never in the lower half where the name and status line still need room.
    assert (box[1] + box[3]) / 2 < H * 0.5, (box, H)
    found = g.audit_shot("HudReticle", props, frame, str(tmp_path / "a.png"), env=_env(ws.workshop_dir(film)))
    assert found == [], found


def test_the_cjk_fixture_leaves_an_object_slot_to_the_register_s_preview():
    """An ObjectRef prop is not copy: the library sweeps (cjk_type_qa, prop_reach) feed a register Chinese words, and a
    slot left unset shows the register's own picture. Filed as untestable it would read as a coverage hole — exit 2 —
    on every register that can hold an object."""
    import cjk_type_qa as c
    for name, slot in (("TechnicalPlate", "art"), ("HudReticle", "object")):
        props, untestable = c.cjk_props(name)
        assert slot not in props and slot not in untestable, (name, props, untestable)


def test_validate_names_an_unknown_art_object(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "TechnicalPlate", "narration": "这是它。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"art": {"id": "NoSuchArt"}, "parts": [], "object": "它"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("TechnicalPlate.art names object 'NoSuchArt'" in e for e in errs), errs


def test_validate_refuses_a_caption_string_passed_as_the_reticles_object(tmp_path):
    """HudReticle destructures its own top-level slot under a local name (`object: OBJECT`) — the same style
    TechnicalPlate does not use for `art` — and that rename must not hide a malformed value from the same
    build check `art` already gets: a plain string is not `{"id": ..., "props": {...}}`."""
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "HudReticle", "narration": "它在这里。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"object": "冲煮头"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("HudReticle.object must be an object reference" in e for e in errs), errs
