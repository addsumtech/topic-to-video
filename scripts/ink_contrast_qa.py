#!/usr/bin/env python3
"""ink_contrast_qa — does a register's ink still READ when the film's ground turns light?

WHY THIS EXISTS. All eight DNA presets are dark (the brightest, `editorial`, is Y=0.0053), so a register can
hardcode a light ink, be reviewed a hundred times, and never once be seen on a light ground. Real films do
have light grounds: `dna_from_deck` derives a film's DNA from the client's own deck, and a violet-branded
deck came out violet on warm white. On that film, a register whose type is a literal near-white draws white
on white — the words are all present, every type gate is satisfied (nothing is missing, nothing overflows,
nothing collides), and the frame is blank.

That is the exact shape this repository keeps paying for: a gate that measures type cannot see INK. Probed by
hand on 2026-09-20, `OpenQuestions` set its questions — the whole content of the beat — at about 1.4:1 on a
warm-white ground.

HOW IT MEASURES, and why this way.

Two DNAs that are IDENTICAL except for the ground and the inks: same fonts, same radius, same everything that
moves a glyph. So the two renders of a register differ in colour only, and the same pixel is the same mark in
both. That is what makes the measurement possible:

  1. the DARK render says WHERE the ink is — the pixels that clearly differ from that frame's ground;
  2. the LIGHT render says whether those same marks still read, as a gamma-correct WCAG contrast ratio
     against the light frame's own ground.

A register that reads the DNA inverts and keeps its contrast. A register that hardcodes near-white ink keeps
its PIXELS and loses its contrast, and that is reported as the share of its ink that fell under 3:1.

WHAT IT DOES NOT CLAIM. It says nothing about beauty, and nothing about a register whose ink is a deliberate
identity colour (a syntax palette, CPK element colours, a brand's own hue) — those keep their contrast, since
they are not near-white. It also cannot see a register that draws NO ink in either render; `register_energy`
measures that.

AND ITS KNOWN FALSE POSITIVE, because a gate whose limits are not written down is a gate that gets argued
with once and discounted after: a PANEL'S RIM counts as ink. A filled card is excluded from the marks by its
interior (there is no ground within three pixels of it), but its 3px edge survives, and where pale panels sit
on pale paper — `RansomZine`'s cut-paper scraps, `InfiniteCanvas`'s pastel notes — those edges chain into one
large connected region and are reported as a hole. The pictures read: the panels carry their own shadow. The
repair belongs in the register (a hairline in `surfaceBorder`, which those forms want anyway), not in a
weaker rule here — measured on the labelled set, no shape test separates a 6px scrap rim from small type.
LOOK AT `--mark` BEFORE ACTING ON A FINDING. Of the 26 this gate reported on 2026-09-21, eleven were checked
by eye and real, four were rims.

Usage:
  python3 scripts/ink_contrast_qa.py                  # sweep the library, print the offenders
  python3 scripts/ink_contrast_qa.py --only A,B       # a few (this is a render per register per ground)
  python3 scripts/ink_contrast_qa.py --json           # the measurements, for a test or a ledger
"""
import json
import os
import re
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _common as _c                                                            # noqa: E402

_REM = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REM, "src", "shots")

# The two grounds, and NOTHING else different. Every field that could move a glyph — the three faces, the
# radius — is shared, so a pixel is the same mark in both renders and the comparison is about colour alone.
_TYPE = {"fontDisplay": "Inter, sans-serif", "fontBody": "Inter, sans-serif",
         "fontMono": "ui-monospace, monospace", "radius": 14}
# THE PROBE'S OWN TOKENS ARE SOLID COLOURS, as all eight presets are. Written with `rgba(255,255,255,0.05)`
# for `surface` — which reads like this library's panels but is not what any DNA actually ships — the probe
# made `surfaceOn()` throw, and `CardStack3D` was recorded as "refused to render" for eleven sweeps. A gate
# whose own input a register cannot accept measures nothing and says the register is at fault.
DARK = dict(_TYPE, id="inkprobe-dark", bg="#0b0d12", fg="#f2f5fa", dim="#8b97a8", accent="#5ac8fa",
            accent2="#ff9f0a", onAccent="#05070b", surface="#171b28",
            surfaceBorder="#2b3244", line="#232838")
LIGHT = dict(_TYPE, id="inkprobe-light", bg="#f6f3ee", fg="#15181d", dim="#5d6570", accent="#1d63d6",
             accent2="#c2410c", onAccent="#ffffff", surface="#ffffff",
             surfaceBorder="#d8d3ca", line="#ded8cf")

INK_DELTA = 0.25        # how far from its own ground a pixel must sit in the DARK render to count as a mark
FAIL_RATIO = 3.0        # WCAG's floor for large text — a mark under this on the light ground is a finding
# WHAT IS REPORTED IS THE BULK, NOT THE WORST PIXEL. After the filtering above the surviving marks are
# glyphs and rules, and a register can still hold one low-contrast hairline without a reader losing anything —
# `BentoReveal`'s hero tile keeps a 1px border that is blue-on-white at 1.2:1 while every word on it reads at
# 4.5:1 or better. The MEDIAN mark is the honest headline: under the floor, the register's ink has gone. The
# share is kept as context, and a register that loses HALF its marks is reported too, because a beat whose
# left column vanished is not saved by a right column that did not.
SHARE_FLOOR = 0.50
# ...AND WHERE IT FAILED, WHICH NEITHER OF THOSE CAN SAY. A share is an amount; the two pictures that lose the
# same amount can be a register whose every tiny caption keeps a soft rim (nothing a reader misses) and one
# whose answer turned white-on-white mid-sentence. Held apart by share alone they sat either side of no line
# at all, and five real registers shipped under the 50% floor — one of them, `ExplodedSchematic`, by half a
# percentage point. So the largest CONNECTED failing region is reported too.
#
# The floor is a fraction of the FRAME, not of the ink, because what it describes is a hole a viewer sees:
# 0.0027 is about 5600px at 1080p — the area of one word of body copy. It is calibrated against the two
# measured neighbours either side of it, not chosen: `BentoReveal`'s hero tile keeps a 1px border that is
# blue-on-white (0.00247, and the picture is perfect), and `InflateType` loses its whole tagline (0.00294).
# Every one of the nine registers looked at above this line had really lost something a reader needed.
HOLE_FLOOR = 0.0027
# THE RIM, NAMED — because a gate with a permanent finding on it is a gate nobody reads to the end. These two
# were looked at, at 7x, after being repaired: every flagged pixel is the ~3px edge of a PALE panel on the
# film's PALE paper, chained across adjacent panels into one region. `RansomZine`'s scraps are cream and
# white cut-outs, `InfiniteCanvas`'s notes are pastel; both now draw a hairline in `surfaceBorder` (which
# those forms wanted anyway) and both still measure over the floor, because a quiet edge IS quiet — a real
# sticky note on real paper is separated by about this much and a reader has never had trouble with one.
# The mask cannot be made to drop them: a panel rim and a word of small type are the same shape at this
# scale, and excluding marks that touch a large flat area would have hidden `AnswerStream`'s card titles,
# which is the worst finding this gate has made.
#
# THE WAIVER IS CHECKED, not believed: it forgives the HOLE rule only (the median and the share still apply,
# so ink that stops reading is still reported), and only up to the number measured on the day it was
# written. A register that gets worse than its own ceiling is a finding again.
RIM_WAIVED = {
    "RansomZine": (0.0115, "cut-paper scraps in cream and white on the film's cream ground; the letters "
                           "read at 4.15:1 and the scraps carry their own drop shadow"),
    "InfiniteCanvas": (0.0085, "pastel sticky notes on cream; the labels read at 9.00:1 and the white hub "
                               "card, which has always drawn a border, is not flagged at all"),
    # ...and the case where the FORM is low contrast on purpose. A cloud on a sky is not a mark on a page:
    # it is separated by a tone step and a shadow, the way a real one is and the way cut paper is, and a
    # cloud that cleared 3:1 against its sky would be a dark blot. Everything flagged here is the rim of the
    # three paper clouds and of the sun; the card, its type and the tagline read at 5.51:1 median.
    # `CartoonPop` had the same shapes and is NOT waived — that register outlines every other shape it
    # draws, so its clouds take the same outline and the rim goes away. A waiver is for a form that cannot
    # draw the edge, not for one that had not got round to it.
    "PaperCutout": (0.0040, "cut-paper clouds and a paper sun on a warm paper sky, each carrying its own "
                            "drop shadow; a cut-paper layer has no outline by construction"),
}
# THE SETTLED FRAME IS PER REGISTER, not a constant. A fixed 142 is past the END of every register shorter
# than 143 frames, and `remotion still` refuses the frame rather than clamping it — so `CrashZoom`,
# `GlowPick`, `OdometerRoll`, `SurfaceCarousel`, `VelocitySnap`, `TemporalAccelerate` and `CursorStory` were
# never measured at all, and the sweep said "skipped" with a stack trace that named nothing. Each register
# declares its own DURATION; the settled point is the library's own REDUCED_MOTION_T through it.
FRAME = 142             # the fallback when a register declares no DURATION
_DUR = re.compile(r"export const DURATION\s*=\s*(\d+)")


def settled_frame(shot):
    """The frame `useT()` itself calls settled, for THIS register — one definition, not a fourth.

    This multiplied DURATION by REDUCED_MOTION_T, which is not the same frame: `useT` holds each shot STILL
    for SEAM_FRAMES at both edges and runs its span between them, so the settled point is the INVERSE of
    that mapping, not a fraction of the whole clip. Measured across the library the two disagreed on all 170
    registers by up to 12 frames — and `shot_proof`'s own `int(DURATION * 0.88)` was a third answer, up to 15
    frames out, with a hardcoded 120 behind it. `render_remotion.frame_at_t` is the inversion, already used
    by `band_debt`; everything asks it now. This repository records what two cameras that agree until they
    quietly do not cost it: six PortRail labels 215px off their own modules, on a frame that read as correct.
    """
    try:
        src = open(os.path.join(_SHOTS, shot + ".tsx"), encoding="utf-8").read()
    except OSError:
        return FRAME
    m = _DUR.search(src)
    if not m:
        return FRAME
    dur = int(m.group(1))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("render_remotion",
                                                      os.path.join(_HERE, "render_remotion.py"))
        rr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rr)
        return max(0, min(dur - 1, int(round(rr.frame_at_t(dur, rr.SETTLED_T)))))
    except Exception:
        return max(0, min(dur - 1, FRAME))


def _y(rgb):
    """Gamma-correct relative luminance (WCAG), from a float RGB triple in 0..1."""
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(v)) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _luma(img):
    """The same WCAG luminance as `_y`, for a whole image at once.

    `np.apply_along_axis(_y, 2, frame)` calls a Python function ONCE PER PIXEL — half a million calls per
    frame, two frames per register, and it turned a 2.4-second render into a two-and-a-half-minute
    measurement. The sweep measured six registers in sixteen minutes before this was found; vectorised, the
    arithmetic is milliseconds and the renders are the cost again.
    """
    import numpy as np
    c = np.asarray(img, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def _contrast(y1, y2):
    a, b = (y1, y2) if y1 >= y2 else (y2, y1)
    return (a + 0.05) / (b + 0.05)


def bundle(out_dir):
    """Build the compositions ONCE and render every probe from that build.

    `npx remotion still src/index.ts` re-bundles the whole library on every call: measured at ~24s per render
    against ~2.4s from a prepared bundle, which is the difference between a sweep of three hours and one of
    fifteen minutes. A gate nobody can afford to run is a gate nobody runs, and this file measures 340 frames.
    The bundle is built at the START of a run, so it always describes the tree being measured."""
    r = subprocess.run(["npx", "remotion", "bundle", "--out-dir=" + out_dir],
                       cwd=_REM, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError("could not bundle the library:\n" + (r.stderr or r.stdout)[-2000:])
    return out_dir


def _still(shot, dna, out_png, props=None, frame=None, serve=None):
    payload = dict(props or {}, dna=dna)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        pf = fh.name
    try:
        r = subprocess.run(["npx", "remotion", "still", serve or "src/index.ts", shot, out_png,
                            "--frame=%d" % (settled_frame(shot) if frame is None else frame), "--gl=angle", "--log=error", "--props=" + pf],
                           cwd=_REM, capture_output=True, text=True, timeout=900)
        return r
    finally:
        os.unlink(pf)


def _interior(mask, r):
    """True where EVERY pixel within r is also ink — the inside of a fill, as opposed to a stroke or an edge."""
    import numpy as np
    m = mask.astype(np.float64)
    s = np.pad(m.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    h, w = mask.shape
    r0 = np.clip(np.arange(h) - r, 0, h)[:, None]
    r1 = np.clip(np.arange(h) + r + 1, 0, h)[:, None]
    c0 = np.clip(np.arange(w) - r, 0, w)[None, :]
    c1 = np.clip(np.arange(w) + r + 1, 0, w)[None, :]
    got = s[r1, c1] - s[r0, c1] - s[r1, c0] + s[r0, c0]
    area = (r1 - r0) * (c1 - c0)
    return got >= area - 0.5


def _band(y, radius, op):
    """A separable 2-D max/min filter of half-width `radius` — the two passes a grey-scale opening needs."""
    import numpy as np
    out = y
    for axis in (0, 1):
        acc = out
        for k in range(1, radius + 1):
            acc = op(acc, np.roll(out, k, axis=axis))
            acc = op(acc, np.roll(out, -k, axis=axis))
        out = acc
    return out


_GROUND_TOKEN_RE = re.compile(r"^\s*(\w+)\s*:\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\")", re.M)


def _ground_tokens():
    """{register: which DNA token its ground comes from}, READ from `runtime/shotLuma.ts`.

    The library already records this, one entry per register, and it is the difference between a register
    that ignored the film and one whose ground IS the film — a colour the film chose. `KineticManifesto`
    floods `accent`->`accent2` edge to edge; on a light film those accents are dark BY CONSTRUCTION (they
    were exposed to read on paper), so the frame comes back at Y=0.13 with nothing wrong. Asking luminance
    alone would report it, and a gate that reports a register for obeying the film is a gate that teaches
    its reader to skip the section.

    Only a ground declared as the film's SHEET (`bg`/`bgGrad`) is held to the film's key. A literal hex is
    not an exemption — that IS the defect this rule is for.
    """
    try:
        src = open(os.path.join(_REM, "src", "runtime", "shotLuma.ts"), encoding="utf-8").read()
        i = src.index("export const DNA_GROUND_TOKEN")
        body = src[i:src.index("\n};", i)]
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in _GROUND_TOKEN_RE.findall(body)}


_GROUND_TOKENS = _ground_tokens()


def ground_is_the_films_sheet(shot):
    """True when this register's OWN table entry says its ground is the film's sheet, so the film's key
    applies to it. An unknown register is held to it too: the table covers the whole library, and a register
    missing from it is not a register with a special ground."""
    tok = _GROUND_TOKENS.get(shot)
    if tok is None:
        return True
    names = re.findall(r"[A-Za-z]\w*", tok)
    return bool(names) and all(n in ("bg", "bgGrad") for n in names)


def _edge_ground(img):
    """The luminance of the frame's outer RING — the sheet, as opposed to whatever is drawn on it.

    The median of the whole frame answers a different question: `FocalIsolation` draws a vignette, so its
    ring is dark while its sheet is plainly light, and `ChartLive` fills the frame with one dark field. Both
    measures are taken and a register is only called ground-blind when BOTH say dark.
    """
    import numpy as np
    h, w = img.shape[:2]
    k = max(2, int(min(h, w) * 0.03))
    ring = np.concatenate([img[:k].reshape(-1, 3), img[-k:].reshape(-1, 3),
                           img[:, :k].reshape(-1, 3), img[:, -k:].reshape(-1, 3)])
    return _y(np.median(ring, axis=0))


def is_finding(row, shot=None):
    """The verdict on ONE measured row — one definition, asked of stored rows and fresh ones alike."""
    if row.get("lie") or row.get("blind"):
        return True
    if "share" not in row:
        return False
    if row["median"] < FAIL_RATIO or row["share"] >= SHARE_FLOOR:
        return True
    ceiling, _why_waived = RIM_WAIVED.get(shot or "", (None, None))
    if ceiling is not None:
        return row.get("hole", 0.0) > ceiling
    return row.get("hole", 0.0) >= HOLE_FLOOR


def _largest_hole(bad, close=3):
    """The area of the BIGGEST CONNECTED REGION whose ink is gone — a share cannot tell the two apart.

    A share says how MUCH of a register's ink failed; it never says whether that ink was one place. Both
    answers are 43%: `StateSheet`, where every tiny mono caption keeps a soft anti-aliased rim and a dozen
    card borders lose their edge — nothing a reader misses — and `AnswerStream`, where the right half of a
    three-line sentence turns white-on-white and the beat's actual words stop existing. Held apart by share
    alone they sit either side of no line at all: at a 50% floor BOTH pass, and five real registers shipped
    (`AnswerStream`, `TerrainFly`, `ExplodedSchematic`, `PixelBuild`, `InflateType`) — one of them, at
    49.45%, by half a percentage point.

    What separates them is SHAPE. Failing marks are closed by `close` px so the glyphs of a word join, then
    the connected regions are labelled and the largest is returned: scattered rims can never grow a big
    region, and a lost sentence always does. Measured on the six: the artefact 552, the five real ones
    1526-20805.

    Labelled by propagating each pixel's own index through the region (a max filter masked to it) until it
    stops moving — `scipy.ndimage.label` is not a dependency of this skill, and a gate that needs one it
    cannot assume is a gate that does not run.
    """
    import numpy as np
    if not bad.any():
        return 0
    solid = _band(_band(bad, close, np.maximum), close, np.minimum)
    if not solid.any():
        return 0
    lab = np.where(solid, np.arange(solid.size).reshape(solid.shape) + 1, 0).astype(np.int64)
    while True:
        nxt = np.where(solid, _band(lab, 4, np.maximum), 0)
        if np.array_equal(nxt, lab):
            break
        lab = nxt
    counts = np.bincount(lab.ravel())
    counts[0] = 0
    return int(counts.max())


def _ground_behind(y, radius):
    """The ground BEHIND each mark, whatever the mark's polarity — the local maximum where the mark is dark
    on its surround, the local minimum where it is light on it.

    This is the document-imaging answer, and it is used because the two cheaper ones were wrong in ways that
    matter. Averaging the non-ink pixels around a mark needs to know which pixels are ink, and using the DARK
    render's mask for that erases a whole accent TILE — so `BentoReveal`'s white wordmark, sitting on its blue
    hero tile, was compared against the warm-white paper two hundred pixels away and scored 1.0:1. The frame's
    median is worse still: it says every mark in the register is read against the paper, which is false for
    anything drawn on a panel, a chip or a fill.
    """
    import numpy as np
    hi, lo = _band(y, radius, np.maximum), _band(y, radius, np.minimum)
    mid = (hi + lo) / 2.0
    return np.where(y < mid, hi, lo)


# A REGISTER WHOSE SUBJECT IS EMITTED LIGHT CANNOT BE DRAWN ON PAPER. An aurora, a phosphor screen, a signal
# glowing in a scanner, headlights on a wet road — the DARKNESS is not a palette choice there, it is what makes
# the light legible, and "invert the ink" is not a repair, it is a different picture. Such a register says so
# in its header:
#
#     // @dark-world: <why this form needs a dark field>
#
# ...and the declaration is CHECKED, not believed: the register must actually keep its own ground when the
# film's is light. One that declares darkness and then paints the film's warm white is reported — that is the
# loudest version of the defect this gate exists for, since it now carries a note saying it is fine.
_DARK_WORLD = re.compile(r"//[ \t]*@dark-world:[ \t]*(\S[^\n]*)")


def _light_key_y(default=0.35):
    """The exposure boundary, READ from runtime/light.tsx rather than chosen again here.

    `darkGround` hands the film's ground through while `keyFromY` calls it dark, and this check asks whether
    the register kept a dark field — the same question, so it must be the same number. Written independently
    as 0.18, the two disagreed across a whole band: a film grounded between them would have every
    `@dark-world` register legitimately take the film's ground and be reported by this gate as a LIE. No
    shipped preset is near that band (the brightest is Y=0.0053), which is exactly why it would have sat
    there unnoticed until the ground vocabulary grew.
    """
    try:
        src = open(os.path.join(_REM, "src", "runtime", "light.tsx"), encoding="utf-8").read()
        return float(re.search(r"LIGHT_KEY_Y\s*=\s*([0-9.]+)", src).group(1))
    except Exception:
        return default


DARK_GROUND_Y = _light_key_y()


def dark_world_reason(shot):
    try:
        src = open(os.path.join(_SHOTS, shot + ".tsx"), encoding="utf-8").read()
    except OSError:
        return None
    m = _DARK_WORLD.search(src)
    return m.group(1).strip() if m else None


# A PHOTOGRAPH IS NOT INK. The evidence registers put a real picture on the frame, and on the dark ground
# that picture is the brightest thing there — so every pixel of it enters the "legible marks" set, and on a
# light ground its mid-tones sit near the paper. `ScanReconstruct` was reported at 91% unreadable when the
# whole measurement was the fixture photograph; the register drew no type at all in that frame. Feeding the
# register a SECOND fixture of a different tone and taking the pixels that MOVED gives the picture's own
# area exactly, whatever shape the register composites it into — and it costs one render, only for the
# registers that take an image.
_ALT_FIXTURE_REL = "_ink_alt_fixture.png"


def ensure_alt_fixture():
    """A second stand-in photograph, deliberately a different tone from the energy sweep's."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    pub = os.path.join(_REM, "public")
    os.makedirs(pub, exist_ok=True)
    path = os.path.join(pub, _ALT_FIXTURE_REL)
    if not os.path.exists(path):
        w, h = 1400, 933
        im = Image.new("RGB", (w, h))
        px = im.load()
        for y in range(h):
            for x in range(w):
                v = 200 - int(70 * (x / w)) - int(40 * (y / h))
                if (x // 55 + y // 55) % 2 == 0:
                    v = max(0, v - 40)
                px[x, y] = (min(255, int(v * 0.86)), min(255, int(v * 0.92)), v)
        d = ImageDraw.Draw(im)
        d.rectangle([w * 0.30, h * 0.20, w * 0.78, h * 0.70], fill=(24, 28, 36))
        im.save(path)
    return _ALT_FIXTURE_REL


def _picture_mask(shot, tmpdir, props, serve, shape):
    """True where the register drew the PICTURE it was given, found by swapping the picture."""
    import numpy as np
    from PIL import Image
    alt = ensure_alt_fixture()
    if not alt or not props:
        return None
    swapped = {k: (alt if isinstance(v, str) and v.endswith(".png") else v) for k, v in props.items()}
    if swapped == props:
        return None
    png = os.path.join(tmpdir, shot + ".alt.png")
    r = _still(shot, DARK, png, swapped, serve=serve)
    if r.returncode != 0:
        return None
    a = np.asarray(Image.open(png).convert("RGB"), dtype=np.float32) / 255.0
    if a.shape != shape:
        return None
    return None, a


def measure(shot, tmpdir, props=None, mark_png=None, serve=None):
    """{ink, under, share, worst} for one register, or {'skipped': why}."""
    import numpy as np
    from PIL import Image

    dark_png = os.path.join(tmpdir, shot + ".dark.png")
    light_png = os.path.join(tmpdir, shot + ".light.png")
    rd = _still(shot, DARK, dark_png, props, serve=serve)
    if rd.returncode != 0:
        # A REFUSAL IS NOT A FINDING. An evidence register with no `src`, or any register refusing props it
        # was not given, fails both renders identically and has nothing to say about ink.
        return {"skipped": "refused to render: " + _why(rd)}
    rl = _still(shot, LIGHT, light_png, props, serve=serve)
    if rl.returncode != 0:
        return {"skipped": "rendered dark but not light: " + _why(rl)}

    d = np.asarray(Image.open(dark_png).convert("RGB"), dtype=np.float32) / 255.0
    l = np.asarray(Image.open(light_png).convert("RGB"), dtype=np.float32) / 255.0
    if d.shape != l.shape:
        return {"skipped": "the two renders are different sizes"}

    # each frame's own ground: the median pixel, which is the paper in every register this library draws
    dg = _y(np.median(d.reshape(-1, 3), axis=0))
    lg = _y(np.median(l.reshape(-1, 3), axis=0))
    declared = dark_world_reason(shot)
    if declared:
        if lg <= DARK_GROUND_Y:
            return {"dark_world": declared, "ground": round(float(lg), 4)}
        return {"ink": 0, "under": 0, "share": 1.0, "worst": 0.0, "median": 0.0,
                "lie": "declares @dark-world but took the film's LIGHT ground (measured Y=%.3f)" % lg}
    # ...AND THE OTHER DIRECTION, WHICH NOTHING ASKED. The declaration was checked and its ABSENCE was not,
    # so a register could ignore the film's ground entirely and sail through: its own night under its own
    # light ink is perfect contrast, which is all this gate measured. Nineteen registers came back dark from
    # the LIGHT probe, and `ChartLive`'s hero figure, `ParticleForm`'s wordmark and `ExplodedSchematic`'s
    # whole sheet read only because the ground they were promised never arrived. A register may keep its own
    # night — it says so, and then the rule above holds it to it.
    edge = _edge_ground(l)
    blind = (ground_is_the_films_sheet(shot) and lg <= DARK_GROUND_Y and edge <= DARK_GROUND_Y and
             "its own `DNA_GROUND_TOKEN` entry says its ground is the film's sheet, and on a LIGHT film it "
             "came back dark (sheet Y=%.3f, frame Y=%.3f) — it never took the ground, and it does not "
             "declare @dark-world" % (edge, lg))
    dy = _luma(d[::2, ::2])                            # every other pixel: this is a share, not a count
    ly = _luma(l[::2, ::2])
    # WHAT IS JUDGED IS WHAT WAS PLAINLY LEGIBLE ON THE DARK GROUND — nothing else. Two cheaper definitions
    # of "ink" were tried and both cried wolf, in opposite directions: a plain distance from the frame's
    # median counted `BentoReveal`'s white CARDS (which on warm-white paper read by their border and shadow,
    # not by their fill) and reported a third of the register unreadable; dropping thick marks as "fills"
    # then dropped its bold display type and reported three quarters. A mark that was under 4.5:1 on the dark
    # ground was never carrying anything on its own, and a mark that was over it is exactly what must survive
    # the change of ground.
    # A GLOW IS NOT A MARK EITHER. The ground is taken THREE pixels away, not eight: a soft halo around a
    # panel differs from the paper far away but barely from itself nearby, so at this radius it scores low and
    # drops out, while a glyph — which is sharp by construction — still stands clear of the paper beside it.
    # Before this, the pink tracing `BentoReveal` was the hero tile's shadow, whose disappearance on light
    # paper costs a reader nothing.
    dark_local = _ground_behind(dy, radius=3)
    d_hi = np.maximum(dy, dark_local) + 0.05
    d_lo = np.minimum(dy, dark_local) + 0.05
    mask = (d_hi / d_lo) >= 4.5
    sharp = int(mask.sum())                            # before the picture is taken out of it
    pic = _picture_mask(shot, tmpdir, props, serve, d.shape)
    if pic is not None:
        _, alt_rgb = pic
        moved = (np.abs(_luma(alt_rgb[::2, ::2]) - dy) > 0.02)
        # the picture's own area, grown by a pixel so its antialiased rim goes with it
        moved = moved | np.roll(moved, 1, 0) | np.roll(moved, -1, 0) | np.roll(moved, 1, 1) | np.roll(moved, -1, 1)
        mask = mask & ~moved
    # ...AND ONLY THE CORE OF A MARK, never its edge. An anti-aliased boundary pixel sits BETWEEN two regions
    # by construction, so against the far side of that boundary it always half-fails: the ring of pink tracing
    # `BentoReveal`'s hero tile was every edge pixel of the tile, not a word anybody cannot read. A pixel
    # counts only when its four neighbours are marks too.
    mask = mask & np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1)
    ink = int(mask.sum())
    if ink < 200:
        # A SKIP HAS TO SAY WHICH SKIP IT IS. One line covered three registers with 13%, 17% and 35% of the
        # frame in ink by `register_energy`'s measure, which reads as the gate being broken. Two of them are
        # evidence registers whose whole frame is the photograph — there is no drawn ink to judge, and that
        # is a complete answer. The third (`InkBloom`) is soft by construction: a displaced, blurred
        # diffusion with its wordmark inside its own glow, so nothing in it stands at 4.5:1 three pixels
        # away on EITHER ground. Different holes, different work.
        return ({"blind": blind} if blind else
                {"skipped": ("the frame is the evidence picture (%d mark(s) left outside it) — there is no "
                             "drawn ink here to judge" % ink) if pic is not None and sharp >= 200 else
                            ("nothing in this register stands at 4.5:1 three pixels away on the DARK ground "
                             "either: it is soft-edged throughout, so a change of ground cannot be measured "
                             "on it (register_energy measures whether it draws at all)")})

    # ...AND THE GROUND A MARK IS READ AGAINST IS THE ONE BEHIND IT, not the frame's. Compared against the
    # frame median, `BentoReveal`'s white wordmark on its blue accent tile scored 19% of its ink "unreadable"
    # — white on blue, which is exactly what `onAccent` is for. A gate that reports that teaches the reader
    # to discount it, and this repository has already recorded where that ends. The local ground is the mean
    # luminance of the NON-ink pixels around each mark, by box filter.
    local = _ground_behind(ly, radius=3)
    hi = np.maximum(ly[mask], local[mask]) + 0.05
    lo = np.minimum(ly[mask], local[mask]) + 0.05
    ratios = hi / lo
    under = int((ratios < FAIL_RATIO).sum())
    bad = np.zeros(mask.shape, dtype=bool)
    bad[mask] = ratios < FAIL_RATIO
    if mark_png:
        # WHERE the failing marks are, on the light render — because a share is not a diagnosis, and a gate
        # nobody can check by looking is a gate that gets believed when it is wrong.
        out = (l[::2, ::2] * 255).astype(np.uint8).copy()
        out[bad] = [255, 0, 128]
        Image.fromarray(out).save(mark_png)
    row = {"ink": ink, "under": under, "share": round(under / ink, 4),
           "hole": round(_largest_hole(bad) / float(bad.size), 5),
           "worst": round(float(ratios.min()), 2), "median": round(float(np.median(ratios)), 2)}
    if blind:
        row["blind"] = blind
    return row


def _why(r):
    """The REASON a render refused, not the last line of its stack.

    Reading `splitlines()[-1]` gave `at process.processTicksAndRejections (node:internal/…)` for eight
    registers — a skip list that says nothing about why anything skipped, which is the same failure as a
    gate reporting a count instead of a coverage.

    The reader itself now lives in `_common.render_error`, because four sweeps needed the same answer and
    this one's first version matched the literal word `Error` at the start of a line — which silently misses
    `RangeError: Cannot use frame 110: Duration of composition is 96`, the one message that names the
    fixed-frame bug this gate was repaired for.
    """
    return _c.render_error(r.stdout, r.stderr)


def _register_props():
    """The props each register needs before it will draw at all — reused from the energy sweep rather than
    rebuilt here.

    A REGISTER THAT REFUSES TO RENDER IS NOT A REGISTER THAT PASSED. The first library sweep reported 19
    registers "skipped", and a skip is a hole in the coverage, not a clean result: the evidence registers
    (a real photograph, a scan, a contact sheet of real pictures) and the ones that need a figure were the
    ones never measured. `register_energy` already derives a fixture per register from the shot's own
    `requireEvidence(...)` call and draws the stand-in image; this gate asks it for the same thing, so the
    two sweeps measure the same registers with the same inputs.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("register_energy",
                                                      os.path.join(_HERE, "register_energy.py"))
        re_ = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(re_)
        re_.ensure_fixture()
        return re_.evidence_props()
    except Exception as e:                                  # a missing fixture must not hide the sweep
        print("[ink_contrast] could not build the evidence fixtures (%s) — those registers will skip" % e)
        return {}


def main(argv):
    _c.refuse_unknown(argv, valued=("only", "mark", "store"), switches=("json",),
                      usage="usage: ink_contrast_qa.py [--only=A,B] [--mark=DIR] [--store=FILE] [--json]")
    only = _c.argflag_list(argv, "only")
    mark_dir = _c.argflag(argv, "mark")
    # A SWEEP THAT PRINTS ONLY AT THE END LOSES EVERYTHING IT MEASURED. This one renders 340 frames, and the
    # first full run was stopped by the machine's memory watchdog at 160 of 170 registers with nothing written
    # anywhere. Each measurement is appended as it is taken, and a run started against an existing file skips
    # what that file already holds — so an interrupted sweep is resumed, not repeated.
    store = _c.argflag(argv, "store")
    done = {}
    if store and os.path.exists(store):
        with open(store, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    done[row["shot"]] = row["m"]
    names = sorted(os.path.basename(f)[:-4] for f in os.listdir(_SHOTS) if f.endswith(".tsx"))
    if only:
        missing = [n for n in only if n not in names]
        if missing:
            print("[ink_contrast] --only names %d register(s) that do not exist: %s"
                  % (len(missing), ", ".join(missing)))
            return 2
        names = [n for n in names if n in only]

    out = {}
    with tempfile.TemporaryDirectory(prefix="ink_contrast_") as tmp:
        if not ("--json" in argv):
            print("[ink_contrast] bundling the library once...", flush=True)
        # THE FIXTURES HAVE TO EXIST BEFORE THE BUNDLE DOES. `npx remotion bundle` snapshots `public/`, so a
        # fixture written afterwards is simply not in the build the renders read — the picture-swap probe
        # silently did nothing, and the photograph went on being measured as ink.
        ev = _register_props()
        ensure_alt_fixture()
        todo = [n for n in names if n not in done]
        serve = bundle(os.path.join(tmp, "bundle")) if todo else None
        if done and not ("--json" in argv):
            print("[ink_contrast] %d register(s) already measured in %s" % (len(done), store), flush=True)
        for i, n in enumerate(names, 1):
            if n in done:
                out[n] = done[n]
                continue
            out[n] = measure(n, tmp, props=ev.get(n), serve=serve,
                             mark_png=(os.path.join(mark_dir, n + ".mark.png") if mark_dir else None))
            if store:
                with open(store, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"shot": n, "m": out[n]}, ensure_ascii=False) + "\n")
            if not ("--json" in argv) and i % 10 == 0:
                print("  measured %d/%d" % (i, len(names)), flush=True)

    # A RESUMED RUN USED TO REPORT NOTHING. The verdict was appended inside the measuring branch, so a row
    # read back from `--store` — which is the whole point of the store — skipped it: an interrupted sweep,
    # resumed, printed "every register's ink still reads on a light ground" over findings it had itself
    # written to disk. The verdict is a function of the row, and it is asked of every row.
    findings = [n for n in names if is_finding(out.get(n, {}), n)]

    if "--json" in argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 1 if findings else 0

    dark = {n: v["dark_world"] for n, v in out.items() if "dark_world" in v}
    if dark and not ("--json" in argv):
        print("\n[ink_contrast] %d register(s) keep their own dark field, as declared (@dark-world)" % len(dark))
    # A SKIP IS NOT ONE THING, AND ONLY ONE KIND OF IT IS A HOLE. "The frame is the evidence picture" and
    # "it is soft-edged throughout" are complete answers about a register that was rendered twice and read:
    # there is nothing here this gate can measure, and nothing it is missing. A register that REFUSED TO
    # RENDER is a different animal — it was never seen, and a sweep that exits 0 over it is the exact lie
    # this repository keeps paying for. So the two are separated, and only the second moves the exit code.
    answered = {n: v["skipped"] for n, v in out.items()
                if "skipped" in v and not v["skipped"].startswith(("refused to render", "rendered dark but"))}
    unseen = {n: v["skipped"] for n, v in out.items()
              if "skipped" in v and n not in answered}
    print("\n[ink_contrast] reported when the MEDIAN mark is under %.1f:1 on a light ground, when %d%% of "
          "the marks are, when one connected region bigger than a word of body copy has gone, or when the "
          "register never took the film's ground at all" % (FAIL_RATIO, int(SHARE_FLOOR * 100)))
    _c.coverage("ink_contrast", len(out) - len(unseen), len(names), unseen)
    if answered:
        print("    %d register(s) were read and have no ink this gate can judge:" % len(answered))
        for n in sorted(answered):
            print("    %-24s %s" % (n, answered[n]))
    ground = [n for n in findings if out[n].get("blind") or out[n].get("lie")]
    if ground:
        print("\nREGISTERS THAT DID NOT TAKE THE FILM'S GROUND:")
        for n in sorted(ground):
            print("    %-24s %s" % (n, out[n].get("blind") or out[n].get("lie")))
        print("\n    A register either follows the film's ground or says in its header WHY its form needs a"
              "\n    dark field (`// @dark-world: <reason>`) and takes it through `runtime/light.darkGround`,"
              "\n    which hands the film's own ground back whenever the film is dark too.")
    rest = [n for n in findings if n not in ground]
    if rest:
        print("\nINK THAT STOPS READING WHEN THE GROUND TURNS LIGHT:")
        for n in sorted(rest, key=lambda k: -out[k].get("hole", 1.0)):
            v = out[n]
            print("    %-24s %4.0f%% of its ink under %.1f:1   median %.2f:1   biggest hole %.2f%% of the frame"
                  % (n, v["share"] * 100, FAIL_RATIO, v["median"], v.get("hole", 0) * 100))
    if rest:
        print("\n    Each of these draws a literal ink instead of the film's. Read the colour from `useDNA()`"
              "\n    (fg / dim / accent / onAccent) — or, when the colour IS the meaning (a syntax palette, an"
              "\n    element's CPK colour, a brand hue), keep it and say so in the register's header.")
    waived = [n for n in names if n in RIM_WAIVED and "hole" in out.get(n, {})]
    if waived:
        print("\nWAIVED — a pale panel's rim on pale paper, looked at and judged furniture:")
        for n in sorted(waived):
            ceiling, why = RIM_WAIVED[n]
            print("    %-24s hole %.2f%% of %.2f%% allowed · %s" % (n, out[n]["hole"] * 100, ceiling * 100, why))
    if not findings:
        print("\n    every register takes the film's ground, and its ink still reads on a light one")
    # 0 = the whole universe was measured and is clean · 1 = findings · 2 = part of it was never seen
    return 1 if findings else (2 if unseen else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
