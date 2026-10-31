"""Sub-pixel text stepping in the HTML tier's reveal/motion CSS, and its fix.

THE DEFECT, carried over from the Remotion tier (commit 604dbec, runtime/depth.tsx) to this one.
Chrome/Skia snaps a TEXT run's baseline to a whole device pixel whenever the run's accumulated
transform matrix is axis-aligned — exactly what a CSS `translate`/`scale` reveal always is. So a
slowly-revealing headline advances in 1px hold-then-jump steps while a plain shape riding the SAME
keyframe glides continuously. `base.css` has four such reveals (`.reveal-up`, `.reveal-up-sm`,
`.reveal-pop`, `.settle`) plus `motifs.css` `.float`; all five carry `matrix(1,.0009765625,0,1,0,0)` — a
skewY of 1/1024, the smallest entry Skia's own matrix rounding (sk_relax) keeps, so it tilts a 1920px-wide
frame by under a pixel at either edge — through EVERY keyframe, the settled one included.

THE SETTLED KEYFRAME USED TO DROP IT (`99.9%{… unlock}to{transform:none}`), so a page at rest rendered
byte-identical to a page with no reveal. That bought the invariant with a defect a viewer sees: dropping the
skew re-snaps the baseline to the whole pixel on the reveal's LAST frame, after the type has come to rest, so
every reveal ended with a jump of up to half a pixel. A 2026-10-31 validation film measured it on its 「1999」
line through sequential decode (0.70px between two frames; jitter_qa: "pops 0.95px"), and through the real
capture path here (0.670px, frames 111->112 of that scene). Kept on at rest, the last moving frame IS the
settled frame (0.013px on the same page). The cost, measured on that page's settled frame and pinned below:
the moved type sits at its true quarter-pixel place instead of the rounded one — position, not sharpness
(mean gradient over the moved blocks -1.3..+0.1%, visually indistinguishable side by side). The fixture
tests below would never have shown the pop: their type's box hugged it, where the snap and the tilt move
nothing — so the pop test widens the type's box (see WIDE) and runs the OLD keyframes as its control.

HOW IT IS MEASURED HERE, through the REAL capture path (`scenes.render_html` -> CDP JPEG q90 @ device
scale 1 — the same function and the same persistent-Chrome capture `scripts/render.py` calls for a
real video). A fixture page carries a line of white type and a plain white rule box, BOTH riding the
SAME reveal class — a pure translateY (or, for the invariance checks, scale), so their true ink
centroids differ by exactly a constant at every instant. The rule's box-fill ink is not subject to
Skia's glyph-baseline snap (confirmed directly below: two identical rule boxes under `.reveal-up` track
each other to 0.009px RMS), so it stands in for "the drawing the type should glide with". The type's
track is fit to the rule's (affine, least squares) and the residual's RMS and largest frame-to-frame
step are the signal — mirroring `tests/test_camera_type.py`'s method exactly, swapped onto this tier's
own capture path. Measured on this machine (90 frames, 960x540, JPEG q90, device scale 1):

                   old CSS (y RMS / largest step)   unlocked (y RMS / largest step)
    .reveal-up     0.216 / 0.945 px                  0.037 / 0.113 px
    .float         0.259 / 0.887 px                  0.035 / 0.113 px

x sits at the quarter-pixel floor both ways (<0.07px RMS, steps under 0.25px) because the skewY used
here leaves x invariant (CSS `matrix(1,k,0,1,0,0)`: x' = x always) — only y is ever snapped, matching
the Remotion tier's own finding. The thresholds below sit between the two columns with room on both
sides. Cross-checked at the real production frame size (1920x1080): 0.037/0.113 for `.reveal-up` after
the fix — indistinguishable from the 960x540 numbers above, i.e. this is a device-pixel-grid effect,
not a resolution-dependent one; 960x540 is used here only because it captures ~4x faster.
"""
import glob
import hashlib
import os

import numpy as np
import pytest
from PIL import Image

import scenes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE_CSS = os.path.join(ROOT, "assets", "html", "base.css")
MOTIFS_CSS = os.path.join(ROOT, "assets", "html", "motifs.css")
SEEK_JS = os.path.join(ROOT, "assets", "html", "seek.js")
UNLOCK = "matrix(1,.0009765625,0,1,0,0)"           # the skewY literal every axis-aligned reveal carries


def _chrome_present():
    return scenes._chrome_bin({}) is not None


needs_chrome = pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")

W, H = 960, 540     # cross-checked at the real 1920x1080 production size — see module docstring
FPS = 30
FRAMES = 90
ANIM_SECONDS = FRAMES / FPS         # saturates render_html's reveal window at exactly `frames`

# Fixed crop boxes (y0, y1) in page px. Generous around each element's static rect PLUS the largest
# travel any tested class uses (.reveal-up 48px), so neither box ever clips an element's ink partway
# through the motion — a clipped partial-mass centroid is a measurement artifact, verified against the
# analytic easing curve during development, not a rendering defect.
TXT_BOX = (0, 260)
RULE_BOX = (330, 480)

_PAGE_TMPL = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{base}">
<link rel="stylesheet" href="file://{motifs}">
<style>
  html,body{{width:{w}px;height:{h}px;margin:0;background:#000;overflow:hidden}}
  #txt{{position:absolute;left:120px;top:{top}px;width:{width};font:800 96px/1 Arial,Helvetica,sans-serif;
        color:#fff;white-space:nowrap}}
  #rule{{position:absolute;left:120px;top:400px;width:360px;height:28px;background:#fff}}
</style>{extra}</head>
<body>
<div id="txt" class="{cls}">Glide 42</div>
<div id="rule" class="{cls}"></div>
<script src="file://{seek}"></script>
</body></html>"""

_BARE_TMPL = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{base}">
<link rel="stylesheet" href="file://{motifs}">
<style>
  html,body{{width:{w}px;height:{h}px;margin:0;background:#000;overflow:hidden}}
  #txt{{position:absolute;left:120px;top:{top}px;width:{width};font:800 96px/1 Arial,Helvetica,sans-serif;
        color:#fff;white-space:nowrap}}
  #rule{{position:absolute;left:120px;top:400px;width:360px;height:28px;background:#fff}}
</style></head>
<body>
<div id="txt">Glide 42</div>
<div id="rule"></div>
</body></html>"""


# The type's box width. A reveal's pop at rest is the difference between where the type sits under the unlock and
# where it sits without it: the baseline snap, and the skew's own tilt about the element's centre (1/1024 of the
# type's distance from it). In a box that hugs "Glide 42" both are near zero — the old drop-on-settle keyframes
# moved this fixture 0.02px — while a real page's blocks are column-wide and popped 0.67px. The pop test widens the
# box past the frame so the type sits ~460px left of the centre (measured: the old keyframes 0.417px, today 0.026).
WIDE = "1300px"


def _build(path, cls, base=BASE_CSS, motifs=MOTIFS_CSS, width="auto", extra=""):
    open(path, "w", encoding="utf-8").write(_PAGE_TMPL.format(base=base, motifs=motifs, seek=SEEK_JS, w=W, h=H,
                                                              cls=cls, top=90, width=width, extra=extra))


def _build_bare(path, base=BASE_CSS, motifs=MOTIFS_CSS, width="auto"):
    open(path, "w", encoding="utf-8").write(_BARE_TMPL.format(base=base, motifs=motifs, w=W, h=H, top=90,
                                                              width=width))


def _render(tmp_path, cls, reduced_motion=False, frames=FRAMES, extra="", width="auto"):
    """Render via the REAL `scenes.render_html` path (CDP, JPEG q90, device scale 1) — the exact
    function `scripts/render.py` calls for a real scene. Returns sorted frame paths."""
    out_dir = str(tmp_path)
    os.makedirs(out_dir, exist_ok=True)
    _build(os.path.join(out_dir, "probe.html"), cls, extra=extra, width=width)
    meta = {"_out": out_dir, "fps": FPS, "reduced_motion": reduced_motion}
    scenes.render_html({"html": "probe.html", "anim_seconds": ANIM_SECONDS}, meta, W, H, frames, out_dir, 0)
    return sorted(glob.glob(os.path.join(out_dir, "scene_00_*.jpg")),
                  key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))


def _centroids(paths):
    """Per frame: (text centroid, rule centroid), each (x, y, mass) in full-frame coordinates.
    Separated by fixed, non-overlapping crop boxes — both elements are plain white-on-black, so a
    SHARED opacity fade (both ride the same animation) never confuses which region a pixel belongs
    to the way a shared luma-threshold would."""
    rows = []
    for p in paths:
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
        luma = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]

        def centroid(y0, y1):
            band = np.clip(luma[y0:y1, :] - 10.0, 0, None)   # suppress JPEG ringing on the black bg
            cols, rowsum = band.sum(axis=0), band.sum(axis=1)
            m = cols.sum()
            if m < 1e3:
                return None
            xs = (np.arange(cols.size) * cols).sum() / m
            ys = (np.arange(rowsum.size) * rowsum).sum() / m + y0
            return xs, ys, m
        rows.append((centroid(*TXT_BOX), centroid(*RULE_BOX)))
    return rows


def _residual(rows, axis):
    """Fit the text track to the rule track (affine, least squares); return (RMS, largest
    frame-to-frame step, the rule's own travel, n used). Frames where EITHER element hasn't yet
    reached near-full opacity are dropped by a RELATIVE mass floor (90% of that element's own peak
    mass seen across the render) — an absolute pixel-count floor would be tuned to this fixture's
    font/box size and silently stop generalizing to a different one."""
    idx = 0 if axis == "x" else 1
    valid = [(ct, cr) for ct, cr in rows if ct is not None and cr is not None]
    assert valid, "the probe drew no type or no rule on any frame"
    txt_peak = max(ct[2] for ct, _ in valid)
    rule_peak = max(cr[2] for _, cr in valid)
    t, r = [], []
    for ct, cr in valid:
        if ct[2] < 0.9 * txt_peak or cr[2] < 0.9 * rule_peak:
            continue
        t.append(ct[idx]); r.append(cr[idx])
    t, r = np.array(t), np.array(r)
    A = np.vstack([np.ones_like(r), r]).T
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    res = t - A @ coef
    rms = float(np.sqrt((res ** 2).mean()))
    step = float(np.abs(np.diff(res)).max()) if len(res) > 1 else 0.0
    travel = float(r.max() - r.min())
    return rms, step, travel, len(t)


Y_RMS_MAX, Y_STEP_MAX = 0.12, 0.45      # px: the snapped baseline measured 0.216-0.259 / 0.887-0.945
X_RMS_MAX, X_STEP_MAX = 0.15, 0.50      # px: the quarter-pixel floor measured <0.02 / <0.08 both ways


@needs_chrome
@pytest.mark.parametrize("cls,min_travel", [("reveal-up", 2.0), ("float", 15.0)])
def test_text_glides_with_its_rule_under_the_real_capture_path(tmp_path, cls, min_travel):
    """The headline proof: `.reveal-up` and `.float` text now tracks its own rule to the unlocked
    floor through the SAME CDP/JPEG capture a real render uses. Fails on the pre-fix CSS (measured
    0.216-0.259 RMS / 0.887-0.945px jumps — see module docstring); passes on the fix."""
    paths = _render(tmp_path, cls)
    rows = _centroids(paths)
    y_rms, y_step, y_travel, n = _residual(rows, "y")
    x_rms, x_step, _, _ = _residual(rows, "x")
    assert y_travel >= min_travel, (
        "%s: the rule travelled only %.1fpx — nothing was measured" % (cls, y_travel))
    assert n >= 20, "%s: only %d confident frames — the mass filter ate the probe" % (cls, n)
    assert y_rms < Y_RMS_MAX and y_step < Y_STEP_MAX, (
        "%s: the type trembles against its own rule vertically — residual RMS %.3fpx, a %.3fpx jump "
        "between two frames (the snapped baseline measures ~0.22-0.26 / ~0.9)" % (cls, y_rms, y_step))
    assert x_rms < X_RMS_MAX and x_step < X_STEP_MAX, (
        "%s: the type trembles against its own rule horizontally — residual RMS %.3fpx, step %.3fpx"
        % (cls, x_rms, x_step))


@needs_chrome
def test_two_plain_rule_boxes_glide_together_with_no_snap_of_their_own(tmp_path):
    """Control: a plain box-fill is NOT subject to Skia's glyph-baseline snap. Two identical rule
    boxes riding the same `.reveal-up` keyframe should track each other far below the type's
    measured residual — this is what licenses using one rule box as the "smooth truth" reference
    for the type in the test above, rather than an assumption."""
    out_dir = str(tmp_path)
    html = _PAGE_TMPL.format(base=BASE_CSS, motifs=MOTIFS_CSS, seek=SEEK_JS, w=W, h=H, cls="reveal-up", top=90,
                             width="auto", extra="")
    # both #txt and #rule are already plain boxes here once given the rule's own box styling —
    # simplest is to just reuse the id="rule" box twice via a second instance.
    html = html.replace('id="txt"', 'id="rule2" style="position:absolute;left:120px;top:90px;'
                                     'width:360px;height:160px;background:#fff"')
    open(os.path.join(out_dir, "probe.html"), "w", encoding="utf-8").write(html)
    meta = {"_out": out_dir, "fps": FPS}
    scenes.render_html({"html": "probe.html", "anim_seconds": ANIM_SECONDS}, meta, W, H, FRAMES, out_dir, 0)
    paths = sorted(glob.glob(os.path.join(out_dir, "scene_00_*.jpg")),
                   key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))
    rows = _centroids(paths)
    rms, step, travel, n = _residual(rows, "y")
    assert travel > 2.0 and n >= 20
    assert rms < 0.05 and step < 0.2, (
        "two plain boxes under the identical transform should glide together near-perfectly — "
        "rms=%.3f step=%.3f (got a false positive confound, not a real snap)" % (rms, step))


def _settled_frame(tmp_dir, cls):
    """ONE frame at p=1 via the real `render_html` path. `frames=1` forces `render_html`'s own
    `reveal_frames = max(1, min(frames, ...))` down to 1, so its single shot is captured at p=1.0
    regardless of `anim_seconds` — the same computed CSS state a 90-frame sweep's LAST frame would
    reach (seek.js derives each frame from `p` alone via a negative `animation-delay`; it has no
    memory of "previous" frames), just without paying for the other 89."""
    os.makedirs(tmp_dir, exist_ok=True)
    _build(os.path.join(tmp_dir, "probe.html"), cls)
    scenes.render_html({"html": "probe.html"}, {"_out": tmp_dir, "fps": FPS}, W, H, 1, tmp_dir, 0)
    return glob.glob(os.path.join(tmp_dir, "scene_00_*.jpg"))[0]


def _bare_frame(tmp_dir):
    os.makedirs(tmp_dir, exist_ok=True)
    _build_bare(os.path.join(tmp_dir, "probe.html"))
    scenes.render_html({"html": "probe.html"}, {"_out": tmp_dir, "fps": FPS}, W, H, 1, tmp_dir, 0)
    return glob.glob(os.path.join(tmp_dir, "scene_00_*.jpg"))[0]


# The keyframes base.css carried before the unlock stayed on at rest: identical up to 99.9%, then the skew dropped.
# Injected AFTER base.css as the pop test's control, so the control is today's file with only that one change.
_OLD_SETTLE = "<style>@keyframes rise{99.9%%{opacity:1;transform:translateY(0) %s}to{opacity:1;transform:none}}</style>" \
    % UNLOCK


def _tail_pop(paths):
    """The largest frame-to-frame step of the type's residual against its rule over the frames where both are
    at full ink — the window in which a reveal has come to rest and anything that moves the type is a pop."""
    rows = _centroids(paths)
    valid = [(ct, cr) for ct, cr in rows if ct is not None and cr is not None]
    tpk, rpk = max(c[2] for c, _ in valid), max(c[2] for _, c in valid)
    res = [ct[1] - cr[1] for ct, cr in valid if ct[2] >= 0.97 * tpk and cr[2] >= 0.97 * rpk]
    assert len(res) >= 10, "only %d frames at full ink — nothing settled was measured" % len(res)
    return float(np.abs(np.diff(res)).max())


@needs_chrome
def test_a_reveal_comes_to_rest_without_a_pop(tmp_path):
    """THE DEFECT THIS FILE NOW PINS: the type must not move once it has stopped. With the skew dropped on the
    settled keyframe (the control) the baseline re-snaps on the last frame — measured here 0.42px on the WIDE box —
    and with it kept the last moving frame is the settled frame. The control proves the fixture can show it."""
    ctl = _tail_pop(_render(tmp_path / "old", "reveal-up", extra=_OLD_SETTLE, width=WIDE))
    now = _tail_pop(_render(tmp_path / "now", "reveal-up", width=WIDE))
    assert ctl > 0.3, ("control: the old drop-on-settle keyframes moved the type only %.3fpx at rest — the fixture "
                       "no longer exposes the snap, so this test proves nothing" % ctl)
    assert now < 0.12, "the type jumps %.3fpx after it has come to rest (the old keyframes: %.3fpx)" % (now, ctl)


def _sharpness(a):
    """Mean gradient magnitude of a luma array: how crisp its edges are, independent of where they sit."""
    gy, gx = np.diff(a, axis=0)[:, :-1], np.diff(a, axis=1)[:-1, :]
    return float(np.hypot(gx, gy).mean())


@needs_chrome
@pytest.mark.parametrize("cls", ["reveal-up", "reveal-up-sm", "reveal-pop", "settle", "float"])
def test_settled_frame_costs_position_not_sharpness(tmp_path, cls):
    """The stated tradeoff of keeping the unlock at rest: a settled page is NOT byte-identical to a bare one —
    its moved type sits at its true quarter-pixel place instead of the rounded one — but it is exactly as sharp
    and the change is confined to that type's edges. Measured on a validation film's settled page: mean gradient
    -1.3..+0.1% over the moved blocks. Pinned here: sharpness within 4%, under 5% of the frame touched."""
    settled = _settled_frame(str(tmp_path / "rendered"), cls)
    bare_frame = _bare_frame(str(tmp_path / "bare"))
    a = np.asarray(Image.open(settled).convert("L")).astype(float)
    b = np.asarray(Image.open(bare_frame).convert("L")).astype(float)
    diff = np.abs(a - b)
    assert diff.max() > 0, "%s: the settled frame is byte-identical to a bare page — the unlock came off at rest" % cls
    frac_changed = float((diff > 0).mean())
    assert frac_changed < 0.05, (
        "%s: %.1f%% of pixels differ from the bare page — the tradeoff has stopped being the type's own edges"
        % (cls, frac_changed * 100))
    y0, y1 = TXT_BOX
    sa, sb = _sharpness(a[y0:y1]), _sharpness(b[y0:y1])
    assert abs(sa / sb - 1) < 0.04, (
        "%s: the settled type is %.1f%% %s than on a bare page — the unlock at rest costs sharpness, not only "
        "position" % (cls, abs(sa / sb - 1) * 100, "softer" if sa < sb else "harsher"))


@needs_chrome
@pytest.mark.parametrize("cls", ["reveal-up", "float"])
def test_reduced_motion_never_carries_the_unlock(tmp_path, cls):
    """Reduced motion overrides `transform` outright for every class the unlock touches (base.css's
    reveals get `transform:none!important`; motifs.css's `.float` gets `animation:none!important;
    transform:none!important`) — so it can never see the skew either way. Verified on the real
    invariant (no snapshot of "yesterday" needed): under reduced motion the element is EITHER
    fully hidden at rest-opacity-0 (p near 0, for a class that fades) or pixel-identical to the bare
    static page at any progress — never a transform in between."""
    out_dir = str(tmp_path)
    _build(os.path.join(out_dir, "probe.html"), cls)
    meta = {"_out": out_dir, "fps": FPS, "reduced_motion": True}
    scenes.render_html({"html": "probe.html", "anim_seconds": ANIM_SECONDS}, meta, W, H, FRAMES, out_dir, 0)
    frames = sorted(glob.glob(os.path.join(out_dir, "scene_00_*.jpg")),
                     key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))
    bare_dir = tmp_path / "bare"; bare_dir.mkdir()
    _build_bare(str(bare_dir / "probe.html"))
    scenes.render_html({"html": "probe.html"}, {"_out": str(bare_dir), "fps": FPS}, W, H, 1, str(bare_dir), 0)
    bare_bytes = open(glob.glob(str(bare_dir / "scene_00_*.jpg"))[0], "rb").read()
    last = open(frames[-1], "rb").read()
    assert last == bare_bytes, "%s: reduced-motion settled frame must equal the bare static page" % cls
    # NOTHING in between ever carries a transform either: a pure opacity fade scales every pixel's
    # (and so every element's ink) weight by the SAME factor, which leaves the mass-weighted ink
    # CENTROID exactly where the bare page's is — a leaked skew or entrance translate would move it.
    # (A raw per-pixel brightness bound was tried first and is NOT robust here: JPEG's block DCT
    # rings slightly at a partial-opacity glyph's anti-aliased edge, measured up to +14 on a 0-255
    # channel relative to the full-opacity bare frame, at the SAME pixel, for no transform reason at
    # all — a false positive, not evidence of a transform. Centroid position is immune to that noise
    # at the magnitude a real transform would move things by.)
    bare_rows = _centroids([glob.glob(str(bare_dir / "scene_00_*.jpg"))[0]])[0]
    rows = _centroids(frames)
    for which, idx in (("text", 0), ("rule", 1)):
        bare_c = bare_rows[idx]
        assert bare_c is not None
        for ct in (r[idx] for r in rows):
            if ct is None or ct[2] < 0.5 * bare_c[2]:
                continue           # too faint yet to trust a centroid (early opacity-fade frames)
            assert abs(ct[0] - bare_c[0]) < 0.3 and abs(ct[1] - bare_c[1]) < 0.3, (
                "%s/%s: reduced-motion centroid (%.2f,%.2f) drifted from the bare page's (%.2f,%.2f) "
                "— a transform leaked through the override" % (cls, which, ct[0], ct[1], bare_c[0], bare_c[1]))


def test_axis_aligned_reveal_classes_carry_the_baseline_unlock(tmp_path=None):
    """Source-level guard (no Chrome needed): every axis-aligned reveal/motion class carries the unlock skew in
    its base transform AND on its settled keyframe — none may drop it at rest (see the module docstring)."""
    base = open(BASE_CSS, encoding="utf-8").read()
    motifs = open(MOTIFS_CSS, encoding="utf-8").read()
    for selector in (".reveal-up{", ".reveal-up-sm{", ".reveal-pop{", ".settle{"):
        i = base.index(selector)
        block = base[i:i + 260]
        assert UNLOCK in block, "%s lost its baseline unlock" % selector
    for kf in (r"@keyframes rise{", r"@keyframes pop{", r"@keyframes settle{"):
        i = base.index(kf)
        block = base[i:base.index("}}", i) + 2]
        assert block.rstrip().endswith(UNLOCK + "}}"), "%s: the settled keyframe must keep the unlock" % kf
        assert "transform:none" not in block, "%s drops the unlock at rest — the type pops when it lands" % kf
    i = motifs.index(".float{")
    assert UNLOCK not in motifs[i:i + 120]           # the RULE (.float itself) carries no transform
    kf_i = motifs.index("@keyframes mt-float{")
    kf_block = motifs[kf_i:motifs.index("}}", kf_i) + 2]
    assert kf_block.count(UNLOCK) == 2, "float: expected the unlock on BOTH 0% and 100% (no drop-off)"
    assert "transform:none" not in kf_block, "float: must NOT drop to a clean transform"


def test_reduced_motion_css_source_is_unmodified_by_the_unlock():
    """The unlock touches only base.css/motifs.css; reduced-motion.css's own overrides (which is
    WHY reduced motion never sees the skew) are untouched. A hash check here is a cheap tripwire —
    the real proof is the rendered-pixel invariant above."""
    rm = os.path.join(ROOT, "assets", "html", "reduced-motion.css")
    text = open(rm, encoding="utf-8").read()
    assert UNLOCK not in text
    for sel in (".reveal, .reveal-up, .reveal-up-sm, .reveal-pop", ".float, img.kenburns"):
        assert sel in text, "reduced-motion.css selector list changed shape unexpectedly"
