"""ObjectStage: a thing the film drew, standing on a floor, its parts called out, its name under it — at every
aspect, with its type inside the frame, and with a wide object letterboxed rather than stretched."""
import json
import math
import os
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
import cjk_type_qa as c  # noqa: E402
import device_geometry as dg  # noqa: E402
from _caption_band import caption_band_px  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

SQUARE = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: %(aspect)s, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps & {color?: string}> = ({w, h, color = '#ff00ff'}) => (
  <div style={{width: w, height: h, background: color}} />
);
"""
LABELS = [{"text": "压实的粉饼", "x": 0.5, "y": 0.35}, {"text": "粉碗", "x": 0.2, "y": 0.7, "side": "left"},
          {"text": "出水口", "x": 0.85, "y": 0.9}]
FILM_PROPS = {"object": {"id": "WsSquare"}, "labels": LABELS, "title": "意式浓缩的粉饼",
              "note": "水要穿过它，阻力就是关键", "kicker": "萃取"}

# A real sentence, cycled to any length — the same generator the layout review's own model used, so a
# counterexample found there reproduces here exactly.
_CJK_BASE = ("它自主拆解任务在你授权的目录里真正动文件并把重复动作沉淀成可复用的技能"
             "水穿过压实的粉饼时阻力分布决定了萃取是否均匀")


def cjk(n, seed=0):
    s, k = "", seed
    while len(s) < n:
        s += _CJK_BASE[k % len(_CJK_BASE)]
        k += 1
    return s


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("stage") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsSquare.tsx").write_text(SQUARE % {"name": "WsSquare", "aspect": "1"}, encoding="utf-8")
    (d / "WsBanner.tsx").write_text(SQUARE.replace("#ff00ff", "#00ffff") % {"name": "WsBanner", "aspect": "4"},
                                    encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "language": "zh"},
             "slides": [{"index": 1, "shot": "ObjectStage", "narration": "一", "shot_props": FILM_PROPS}]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _mask(png, rgb):
    a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
    m = np.all(np.abs(a - np.array(rgb)) < 40, axis=-1)
    ys, xs = np.nonzero(m)
    return int(m.sum()), ((xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None)


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1", "4:5"])
def test_the_stage_shows_the_object_named_with_its_type_inside_the_frame(film, tmp_path, aspect):
    props = dict(FILM_PROPS, dna="product", aspect=aspect)
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "s.png", props, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _mask(tmp_path / "s.png", (255, 0, 255))
    assert n > 60000 and box, (n, box)
    assert abs((box[2] - box[0]) - (box[3] - box[1])) <= 4, box
    assert g.audit_shot("ObjectStage", props, 150, str(tmp_path / "a.png"), env=env) == []
    hits = c.sweep(["ObjectStage"], dna="product", aspect=aspect, film_props={"ObjectStage": FILM_PROPS},
                   out_dir=film)["ObjectStage"]
    assert not hits["failed"] and not [h for h in hits["hits"] if h["kind"] in ("leading", "overlap", "orphan")], hits


@needs_toolchain
def test_a_wide_object_is_letterboxed_on_the_stage(film, tmp_path):
    """Review focus: a 4:1 object keeps its shape — never stretched to the stage's room."""
    props = {"object": {"id": "WsBanner"}, "title": "横幅", "dna": "product"}
    r = _still("ObjectStage", tmp_path / "w.png", props, _env(ws.workshop_dir(film)), frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    _n, box = _mask(tmp_path / "w.png", (0, 255, 255))
    ratio = (box[2] - box[0] + 1) / float(box[3] - box[1] + 1)
    assert abs(ratio - 4.0) < 0.08, (ratio, box)


def _standalone_box(W, H):
    """The box ObjectStage fits its object into for a bare `{dna}` call — no title/note/kicker/labels, so
    the object takes the whole room the content zone leaves (`side` is False with no labels; DemoForm's own
    META.aspect is 1). Mirrors ObjectStage.tsx's layout for exactly that case, reading the shared constants
    (TITLE_BAND, the caption band) from the same place the TypeScript does rather than restating them."""
    U = min(W, H)
    zTop = dg._content_top()
    zBot = H - caption_band_px(W, H)
    room_w = W * 0.84
    room_h = max(U * 0.2, zBot - zTop - U * 0.02)
    w = min(room_w, room_h)          # square: room_h is always <= room_w at every supported aspect
    x = (W - room_w) / 2 + (room_w - w) / 2
    y = zTop + max(U * 0.01, (zBot - zTop - w) / 2)
    return x, y, w, w


@needs_toolchain
def test_the_standalone_preview_draws_its_own_form_and_no_words(tmp_path):
    """The preview must draw a real, legible form, not a blank canvas — measured INSIDE the object's own
    box, not as a fraction of the whole frame (which also counts how much room the box itself gets, and
    that varies by aspect and by whether any words are set, telling a caller nothing about the object's own
    drawing). A blank box cannot clear this floor by construction. And the name promises "no words": nothing
    may print above the box (where a kicker would land), below it and its floor shadow (where a title/note
    would), or beside it (where a wide frame's side callouts would)."""
    W, H = 1920, 1080
    r = _still("ObjectStage", tmp_path / "d.png", {"dna": "product"}, _env(), frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    a = np.asarray(Image.open(str(tmp_path / "d.png")).convert("RGB")).astype(int)
    assert a.shape[1] == W and a.shape[0] == H, "the standalone still is not the 16:9 default — recheck the box math"
    ground = np.median(a.reshape(-1, 3), axis=0)
    ink = np.abs(a - ground).sum(axis=-1) > 60

    x, y, w, h = _standalone_box(W, H)
    x0, y0 = int(x), int(y)
    x1, y1 = int(math.ceil(x + w)), int(math.ceil(y + h))
    in_box = ink[y0:y1, x0:x1].mean()
    assert in_box > 0.10, (in_box, (x0, y0, x1, y1))

    u = min(W, H)
    shadow_bottom = int(math.ceil(y1 + u * 0.035))     # past the floor shadow's own blurred extent
    above = int(ink[:y0, :].sum())
    below = int(ink[shadow_bottom:, :].sum())
    left = int(ink[y0:y1, :x0].sum())
    right = int(ink[y0:y1, x1:].sum())
    assert above == 0, "ink above the object's box — a kicker printed with none set (%d px)" % above
    assert below == 0, "ink below the object and its floor shadow — a title/note printed with none set (%d px)" % below
    assert left == 0, "ink left of the object's box — a side callout printed with none set (%d px)" % left
    assert right == 0, "ink right of the object's box — a side callout printed with none set (%d px)" % right


@needs_toolchain
def test_words_that_still_dont_fit_at_half_size_refuse_by_name(film, tmp_path):
    """The fit loop must end only once the words actually fit or MIN_WORD_SCALE is reached, with the result
    checked on every exit path — not after a fixed number of passes, which can leave the key past the
    caption band with nothing having noticed. Six 8-glyph labels, an 8-glyph title and an 855-glyph note at
    1:1 overflow by 4.3px in the layout model — title/note/labels are free text with no length cap, so this
    is the register's own floor, reached honestly, not a contrived input."""
    labels = [{"text": cjk(8, i * 7), "x": 0.2 if i % 2 else 0.8, "y": 0.1 + 0.15 * i} for i in range(6)]
    props = {"object": {"id": "WsSquare"}, "labels": labels, "title": cjk(8, 3), "note": cjk(855, 11),
             "dna": "product", "aspect": "1:1"}
    r = _still("ObjectStage", tmp_path / "overflow.png", props, _env(ws.workshop_dir(film)))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "even at half size" in out, out[-800:]


@needs_toolchain
def test_the_words_loop_finds_the_largest_scale_that_fits(film, tmp_path):
    """A short title and an 855-glyph note at 16:9 (free text has no length cap, and a note this long is a
    real near-the-floor case, not a contrived one) push the words close to the room the frame leaves. A
    wrapped block's height comes from its LINE COUNT more than from its px size alone, so it falls closer to
    the SQUARE of the scale than linearly as the font shrinks — a step sized for a linear fall stops well
    short of the room actually available: on this exact note, in the layout model, such a step stalls at
    scale 0.657 (349px used of a 466px budget, the note wrapped to 12 lines) where scale 0.82 already fits
    (465px, 14 lines) — a fifth more of the frame's own room left on the floor. The words block's rendered
    height is the observable: near 432px at the larger, correct scale, far from the ~317px the smaller one
    would have drawn."""
    props = {"object": {"id": "WsSquare"}, "title": cjk(8, 3), "note": cjk(855, 11),
             "dna": "product", "aspect": "16:9"}
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "bisect169.png", props, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    W, H = 1920, 1080
    a = np.asarray(Image.open(str(tmp_path / "bisect169.png")).convert("RGB")).astype(int)
    assert a.shape[1] == W and a.shape[0] == H, "not the plain 16:9 still this measurement assumes"
    ground = np.median(a.reshape(-1, 3), axis=0)
    ink = np.abs(a - ground).sum(axis=-1) > 60

    _n, obj_box = _mask(tmp_path / "bisect169.png", (255, 0, 255))
    assert obj_box, "the object itself never rendered"
    u = min(W, H)
    words_top = obj_box[3] + 1 + round(u * 0.03)     # the object's own rendered floor, plus the fixed gap
    # to the words below it (the same U*0.03 the register itself adds — see ObjectStage.tsx's own `gap`)

    rows = np.nonzero(ink[words_top:, :].any(axis=1))[0]
    assert len(rows) > 0, "no ink below the object at all — the title/note never printed"
    words_h = int(rows.max()) + 1
    assert words_h > 375, ("the words block measures %dpx tall — close to the 317px a step sized for a "
                            "linear fall would have stopped at, not the ~432px the largest fitting scale "
                            "draws" % words_h)


@needs_toolchain
def test_a_short_column_is_never_refused_for_a_long_one_on_the_other_side(film, tmp_path):
    """One 4-glyph right label and one 60-glyph left label, at 4:3 with the film's own title and note: each
    column's OWN span is modest — the right column is a single short line, the left wraps to a few — but
    read as ONE span across both margins together (the two columns' extremes combined) the same board asks
    for 587px against the 586px the frame leaves, a refusal earned by nobody's own column. Measured per
    column instead (each margin is its own stack, and is never placed past the other's need), the same board
    needs only 172px and fits at the label's full, unshrunk size."""
    labels = [{"text": cjk(4, 0), "x": 0.9, "y": 0}, {"text": cjk(60, 2), "x": 0.1, "y": 1}]
    props = {"object": {"id": "WsSquare"}, "labels": labels, "title": FILM_PROPS["title"],
             "note": FILM_PROPS["note"], "dna": "product", "aspect": "4:3"}
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "shortcol.png", props, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    a = np.asarray(Image.open(str(tmp_path / "shortcol.png")).convert("RGB")).astype(int)
    ground = np.median(a.reshape(-1, 3), axis=0)
    ink = np.abs(a - ground).sum(axis=-1) > 60
    W = a.shape[1]
    assert ink[:, int(W * 0.75):].sum() > 0, "no ink in the right margin — the short column never printed"
    assert ink[:, :int(W * 0.25)].sum() > 0, "no ink in the left margin — the long column never printed"


@needs_toolchain
def test_side_labels_never_reach_into_the_words_below_them_at_4_3(film, tmp_path):
    """Three right-side labels anchored at 0.8/0.9/1.0 — all on the object's own lower half — cascade down
    from their own points until the last one's bottom meets the title/note block below it, its real bound
    here, one CONTENT_TOP alone never catches (nothing in this board comes near the top of the frame). A
    label column and the words block both sit inside the same centred width at 4:3, so a plain ink scan
    cannot tell one's pixels from the other's where they'd touch; the DOM's own measured boxes can, and this
    asks them the same way every other register's overlap check already does."""
    labels = [{"text": cjk(12, i * 5), "x": 0.95, "y": y} for i, y in enumerate([0.8, 0.9, 1.0])]
    props = {"object": {"id": "WsSquare"}, "labels": labels, "title": cjk(40, 3), "note": cjk(60, 9),
             "dna": "product", "aspect": "4:3"}
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "anchors43.png", props, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    hits = c.sweep(["ObjectStage"], dna="product", aspect="4:3", film_props={"ObjectStage": props},
                   out_dir=film)["ObjectStage"]
    assert not hits["failed"], hits
    bad = [h for h in hits["hits"] if h["kind"] in ("leading", "overlap", "orphan")]
    assert not bad, bad


@needs_toolchain
def test_side_columns_stay_off_the_title_band_at_4_3(film, tmp_path):
    """Same class as the words fit: a column measured and placed BEFORE its span is known to fit can be
    shifted to clear its bottom of the caption band by pushing its top above the content zone instead (or
    left over the title/note below, when the overflow was at the other end). Six same-side labels long
    enough to need more room than the column has at 4:3 (a real film photographing a real machine writes
    captions this long) fit — smaller, but never past CONTENT_TOP."""
    labels = [{"text": cjk(60, i * 5), "x": 0.9, "y": 0.1 + 0.15 * i} for i in range(6)]
    props = {"object": {"id": "WsSquare"}, "labels": labels, "title": "意式浓缩的粉饼",
             "note": "水要穿过它，阻力就是关键", "dna": "product", "aspect": "4:3"}
    r = _still("ObjectStage", tmp_path / "side43.png", props, _env(ws.workshop_dir(film)), frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    a = np.asarray(Image.open(str(tmp_path / "side43.png")).convert("RGB")).astype(int)
    ground = np.median(a.reshape(-1, 3), axis=0)
    ink = np.abs(a - ground).sum(axis=-1) > 60
    z_top = dg._content_top()
    above = int(ink[:z_top, :].sum())
    assert above == 0, "ink above CONTENT_TOP — the side column reached into the kicker band (%d px)" % above


@needs_toolchain
def test_side_columns_refuse_by_name_when_they_cannot_fit_even_shrunk(film, tmp_path):
    """The same six-label column, long enough (150 glyphs each) that even the smallest legible size cannot
    fit it clear of the title/note at 4:3 — the register refuses by name rather than print over the words
    or off the frame. All six sit on the one (right) side, so the column that overflows is also the column
    named in the refusal — its own shortfall, not a span borrowed from the empty side opposite it."""
    labels = [{"text": cjk(150, i * 5), "x": 0.9, "y": 0.1 + 0.15 * i} for i in range(6)]
    props = {"object": {"id": "WsSquare"}, "labels": labels, "title": "意式浓缩的粉饼",
             "note": "水要穿过它，阻力就是关键", "dna": "product", "aspect": "4:3"}
    r = _still("ObjectStage", tmp_path / "side43refuse.png", props, _env(ws.workshop_dir(film)))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "a side column needs" in out, out[-800:]


HEAVY_LABELS = [
    {"text": "压实的粉饼层", "x": 0.5, "y": 0.15},
    {"text": "粉碗与手柄接缝", "x": 0.1, "y": 0.3, "side": "left"},
    {"text": "萃取压力的传导路径", "x": 0.85, "y": 0.4},
    {"text": "滤网下方的出水口", "x": 0.15, "y": 0.6, "side": "left"},
    {"text": "咖啡液汇聚的底部锥面", "x": 0.85, "y": 0.75},
    {"text": "手柄与冲煮头的锁合处", "x": 0.5, "y": 0.9},
]
HEAVY_PROPS = {"object": {"id": "WsSquare"}, "labels": HEAVY_LABELS,
               "title": "意式浓缩萃取的压力曲线与流速控制",
               "note": "水穿过压实的粉饼时，阻力分布决定了萃取是否均匀，这是意式咖啡最容易出问题的一步",
               "kicker": "萃取剖面", "dna": "product", "aspect": "1:1"}


@needs_toolchain
def test_heavy_legal_props_still_fit_above_the_caption_band_at_1_1(film, tmp_path):
    """Six CJK-length labels (the MAX_STAGE_LABELS ceiling) plus a two-line title and a two-line note are
    each legal on their own; together at 1:1 they push the object down to its U*0.2 floor, and the words
    themselves must still fit the room that leaves — scaled to it rather than spilling the numbered key
    past `contentBottom` into the caption band."""
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "heavy.png", HEAVY_PROPS, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert g.audit_shot("ObjectStage", HEAVY_PROPS, 150, str(tmp_path / "heavy_a.png"), env=env) == []


@needs_toolchain
@pytest.mark.parametrize("labels,expect", [
    ([{"text": "a", "x": 0.1 * i, "y": 0.5} for i in range(7)], "0-6 `labels`"),
    ([{"text": "粉碗", "y": 0.5}], "needs `x` and `y`"),
    ("粉碗", "must be a LIST"),
    ([{"text": "粉碗", "x": 0.5, "y": 0.5, "side": "up"}], "is 'left' or 'right'"),
])
def test_malformed_labels_are_refused_by_name(film, tmp_path, labels, expect):
    r = _still("ObjectStage", tmp_path / "x.png", {"object": {"id": "WsSquare"}, "labels": labels},
               _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and expect in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]


def test_a_film_must_name_its_object_and_never_the_preview(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    (tmp_path / "audio" / "02.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "ObjectStage", "narration": "一。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"title": "它"}},
                        {"index": 2, "shot": "ObjectStage", "narration": "二。", "audio": "audio/02.mp3",
                         "duration": 3.0, "shot_props": {"object": {"id": "DemoForm"}, "title": "它"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("scene #1: ObjectStage needs `object` in a film" in e for e in errs), errs
    assert any("scene #2" in e and "a stage's own preview form" in e for e in errs), errs


@needs_toolchain
def test_the_workshop_puts_an_object_on_the_stage_to_look_at(film):
    png = ws.still(film, "WsSquare")
    assert os.path.basename(png) == "WsSquare.png"
    n, _box = _mask(png, (255, 0, 255))
    assert n > 60000
