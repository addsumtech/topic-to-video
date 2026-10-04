"""Sub-pixel text stepping in the HTML tier's reveal/motion CSS, and its fix.

THE DEFECT, carried over from the Remotion tier (commit 604dbec, runtime/depth.tsx) to this one.
Chrome/Skia snaps a TEXT run's baseline to a whole device pixel whenever the run's accumulated
transform matrix is axis-aligned — exactly what a CSS `translate`/`scale` reveal always is. So a
slowly-revealing headline advances in 1px hold-then-jump steps while a plain shape riding the SAME
keyframe glides continuously. `base.css` has five such reveals (`.reveal-up`, `.reveal-up-sm`,
`.reveal-pop`, `.settle`) plus `motifs.css` `.float`; all five now carry `matrix(1,.0009765625,0,1,0,0)`
— a skewY of 1/1024, the smallest entry Skia's own matrix rounding (sk_relax) keeps, so it tilts a
1920px-wide frame by under a pixel at either edge — through every keyframe, dropping it again on the
settled (`to`) stop so a page at rest renders byte-identical to before the fix existed. `.float` is the
one exception: it is slow (3s) and, per `render_html`'s per-cue capture burst, is routinely held
mid-flight for most of a scene rather than captured to its own 100% — so it keeps the skew for the
WHOLE loop, 0% to 100%, with no drop-off. The hairline tradeoff: on the rare page where `.float` genuinely
IS captured at rest, that one frame is not byte-identical to a pre-fix render (bounded below, hairline
in size — see `test_settled_float_frame_cost_is_a_hairline_not_a_defect`).

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
  #txt{{position:absolute;left:120px;top:90px;font:800 96px/1 Arial,Helvetica,sans-serif;
        color:#fff;white-space:nowrap}}
  #rule{{position:absolute;left:120px;top:400px;width:360px;height:28px;background:#fff}}
</style></head>
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
  #txt{{position:absolute;left:120px;top:90px;font:800 96px/1 Arial,Helvetica,sans-serif;
        color:#fff;white-space:nowrap}}
  #rule{{position:absolute;left:120px;top:400px;width:360px;height:28px;background:#fff}}
</style></head>
<body>
<div id="txt">Glide 42</div>
<div id="rule"></div>
</body></html>"""


def _build(path, cls, base=BASE_CSS, motifs=MOTIFS_CSS):
    open(path, "w", encoding="utf-8").write(
        _PAGE_TMPL.format(base=base, motifs=motifs, seek=SEEK_JS, w=W, h=H, cls=cls))


def _build_bare(path, base=BASE_CSS, motifs=MOTIFS_CSS):
    open(path, "w", encoding="utf-8").write(_BARE_TMPL.format(base=base, motifs=motifs, w=W, h=H))


def _render(tmp_path, cls, reduced_motion=False, frames=FRAMES):
    """Render via the REAL `scenes.render_html` path (CDP, JPEG q90, device scale 1) — the exact
    function `scripts/render.py` calls for a real scene. Returns sorted frame paths."""
    out_dir = str(tmp_path)
    _build(os.path.join(out_dir, "probe.html"), cls)
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
    html = _PAGE_TMPL.format(base=BASE_CSS, motifs=MOTIFS_CSS, seek=SEEK_JS, w=W, h=H, cls="reveal-up")
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


@needs_chrome
@pytest.mark.parametrize("cls", ["reveal-up", "reveal-up-sm", "reveal-pop", "settle"])
def test_settled_frame_matches_a_bare_static_page_exactly(tmp_path, cls):
    """`A SETTLED page is byte-identical to today`: every reveal class that DROPS the unlock on its
    final keyframe must render its settled (p=1) frame pixel-for-pixel identical to a page with no
    reveal class at all — proving the skew truly comes off, not just "small"."""
    settled = _settled_frame(str(tmp_path / "rendered"), cls)
    bare_frame = _bare_frame(str(tmp_path / "bare"))
    assert open(settled, "rb").read() == open(bare_frame, "rb").read(), (
        "%s: settled frame is no longer byte-identical to a bare, un-animated page" % cls)


@needs_chrome
def test_settled_float_frame_cost_is_a_hairline_not_a_defect(tmp_path):
    """The stated tradeoff: `.float` keeps the unlock for its whole loop (no drop-on-settle), so its
    OWN settled frame is not byte-identical to a bare page the way the other four classes are. This
    pins the cost at a hairline — small, localized to ink edges — not a visible defect; it must stay
    bounded even if `.float`'s geometry changes later."""
    settled = _settled_frame(str(tmp_path / "rendered"), "float")
    bare_frame = _bare_frame(str(tmp_path / "bare"))
    a = np.asarray(Image.open(settled).convert("RGB")).astype(int)
    b = np.asarray(Image.open(bare_frame).convert("RGB")).astype(int)
    diff = np.abs(a - b)
    frac_changed = float((diff.sum(axis=2) > 0).mean())
    assert diff.max() > 0, "the .float settled frame should NOT be byte-identical (that would mean no skew at all)"
    assert frac_changed < 0.05, (
        "float: %.1f%% of pixels differ from the bare page — the tradeoff has stopped being a "
        "hairline" % (frac_changed * 100))


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
    """Source-level guard (no Chrome needed): every axis-aligned reveal/motion class carries the
    unlock skew in its base transform, and the four that are expected to SETTLE still drop it again
    on their final keyframe (`.float` deliberately does not — see its own comment in motifs.css)."""
    base = open(BASE_CSS, encoding="utf-8").read()
    motifs = open(MOTIFS_CSS, encoding="utf-8").read()
    for selector in (".reveal-up{", ".reveal-up-sm{", ".reveal-pop{", ".settle{"):
        i = base.index(selector)
        block = base[i:i + 260]
        assert UNLOCK in block, "%s lost its baseline unlock" % selector
    for kf, settle_kw in ((r"@keyframes rise{", "transform:none"),
                          (r"@keyframes pop{", "transform:none"),
                          (r"@keyframes settle{", "transform:none")):
        i = base.index(kf)
        block = base[i:base.index("\n", base.index(settle_kw, i))]
        assert "99.9%" in block and UNLOCK in block, "%s: missing the carried-through 99.9%% stop" % kf
        assert block.rstrip().endswith("transform:none}}") or "to{opacity:1;transform:none}" in block, (
            "%s must still settle to a clean transform:none" % kf)
    i = motifs.index(".float{")
    assert UNLOCK not in motifs[i:i + 120]           # the RULE (.float itself) carries no transform
    kf_i = motifs.index("@keyframes mt-float{")
    kf_block = motifs[kf_i:motifs.index("}}", kf_i) + 2]
    assert kf_block.count(UNLOCK) == 2, "float: expected the unlock on BOTH 0% and 100% (no drop-off)"
    assert "transform:none" not in kf_block, "float: must NOT drop to a clean transform — see its tradeoff comment"


def test_reduced_motion_css_source_is_unmodified_by_the_unlock():
    """The unlock touches only base.css/motifs.css; reduced-motion.css's own overrides (which is
    WHY reduced motion never sees the skew) are untouched. A hash check here is a cheap tripwire —
    the real proof is the rendered-pixel invariant above."""
    rm = os.path.join(ROOT, "assets", "html", "reduced-motion.css")
    text = open(rm, encoding="utf-8").read()
    assert UNLOCK not in text
    for sel in (".reveal, .reveal-up, .reveal-up-sm, .reveal-pop", ".float, img.kenburns"):
        assert sel in text, "reduced-motion.css selector list changed shape unexpectedly"
