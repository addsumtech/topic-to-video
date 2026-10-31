"""A platform-safe (9:16) film's MARGIN is the beat's own GROUND, carried to the canvas edge — never a copy of its content.

The `social` profile draws every register in a frame scaled by 0.8 with feathered edges, so on 9:16 every beat was a
panel on the film's ground ("every beat becomes a panel on black" — a 9:16 launch benchmark's first finding). Film.tsx
SafeEcho paints the beat's measured ground token behind it and, over that, the register's own ROOT ground drawn again with
everything on it hidden. Two earlier echoes drew the beat itself — magnified (smudges in the corners) and then unscaled
(a ghost phone under the caption, a ghost slab beside its frame); frame_safe_qa's margin_seam and margin_structure
measure the panel edge and the ghost. It must be invisible to every instrument: `data-echo` + `aria-hidden` (the text gates' echo rule),
`data-echo="margin"` (the seams' anchor lookup), no optic, no voice, and nothing at all on a film without the profile.

Measured by mutation (E7) on OdometerRoll at 9:16, frame 45, with the type-collision audit armed: with the echo's
`data-echo` / `aria-hidden` removed the audit reported the echo's type overlapping the frame's own; marked, it reports
what the film reports with the echo switched off.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
FILM = open(os.path.join(_REM, "src", "Film.tsx"), encoding="utf-8").read()
SEAMS = open(os.path.join(_REM, "src", "seams.tsx"), encoding="utf-8").read()
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")) or not shutil.which("npx"),
                                     reason="needs the remotion toolchain")


def test_the_echo_declares_itself_to_every_instrument():
    body = FILM.split("const SafeEcho: React.FC")[1].split("\n};")[0]
    assert 'aria-hidden data-echo="margin"' in body, "the text gates skip [data-echo] (+ aria-hidden by their rule)"
    assert "React.useContext(SeamCopyContext)" in body and "return null" in body, "not drawn inside a container copy"
    assert "<SeamCopyContext.Provider value={true}>" in body, "a beat voice inside it must not play"
    assert "BeatOptic" not in body, "an echo anchors no optic"


def test_only_a_platform_safe_film_mounts_it():
    seq = FILM.split("const beatSeq = ")[1].split("const runSeq")[0]
    assert "{regFrame ? (" in seq and "rootGround={safeEcho}" in seq, (
        "the margin ground must be gated on the safe profile, and safe_echo choose root ground or token")
    assert "safeEcho = true" in FILM


def test_the_seams_never_measure_the_echo_s_anchors():
    assert "closest('[data-echo=\"margin\"]')" in SEAMS
    # every anchor lookup goes through the echo-blind helper
    assert not re.search(r"querySelector\(`\[data-carry=", SEAMS), "a lookup that can find the echo's copy first"


def _still(tmp_path, name, extra):
    props = dict({"scenes": [{"shot": "OdometerRoll", "durF": 60, "props": {}, "caption": "每个数字都对得回原文那一句。"}],
                  "dna": "product", "captions": True, "camera": 0, "cameraBed": False, "safe": "social",
                  "aspect": "9:16"}, **extra)
    pf = str(tmp_path / (name + ".json"))
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=45", "--gl=angle",
                        "--timeout=150000", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r


def _payload(r, tag):
    blob = (r.stdout or "") + (r.stderr or "")
    if tag not in blob:
        assert r.returncode == 0, "the still measured nothing: " + blob[-600:]
        return []
    found, _ = json.JSONDecoder().raw_decode(blob.split(tag, 1)[1])
    return found


@needs_toolchain
def test_the_type_audits_read_the_film_the_same_with_and_without_the_echo(tmp_path):
    for flag, tag in (("typeCollisions", "TYPE-COLLISIONS "), ("textSafe", "TEXT-SAFE-VIOLATIONS ")):
        on = _still(tmp_path, flag + "_on", {flag: True})
        off = _still(tmp_path, flag + "_off", {flag: True, "safeEcho": False})
        a, b = _payload(on, tag), _payload(off, tag)
        assert [x.get("text") for x in a] == [x.get("text") for x in b], (flag, a, b)


def test_a_board_can_refuse_the_echo_for_its_render_cost():
    rr = open(os.path.join(_ROOT, "scripts", "render_remotion.py"), encoding="utf-8").read()
    body = rr.split("zone = safe_zone(meta, aspect)")[1].split("theme = meta.get")[0]
    assert 'if meta.get("safe_echo") is False:' in body and 'props["safeEcho"] = False' in body


def test_the_margin_is_ground_only():
    body = FILM.split("const SafeEcho: React.FC")[1].split("\n};")[0]
    assert "ECHO_GROUND_ONLY" in body and "groundPaint(shot, dna)" in body
    rule = FILM.split("const ECHO_GROUND_ONLY = ")[1].split(";\n")[0]
    assert '>div>* *{visibility:hidden!important}' in rule, "everything drawn on the register's root must be hidden"
    for gone in ("scale(${cover})", "blur(", "brightness("):
        assert gone not in body, "the margin echo must not draw (or magnify, blur, dim) the beat: %s" % gone


# ── the margin seam, measured (scripts/frame_safe_qa.margin_seam) ───────────────────────────────────────────────
import sys  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import frame_safe_qa as fsq  # noqa: E402
import text_safe_qa as tsq  # noqa: E402

W9, H9 = 1080, 1920


def _radial(W, H, cx, cy, r, inner, outer):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    t = np.clip(np.hypot((xx - cx) / r, (yy - cy) / r), 0, 1)[..., None]
    return np.array(inner) * (1 - t) + np.array(outer) * t


def _framed(ground_canvas, ground_frame, blob=None):
    """A synthetic platform-safe frame: `ground_frame` drawn into the 0.8 frame over `ground_canvas`, with the frame's
    feathered mask — the composite Film.tsx makes. `blob` = (x, y, r, rgb) painted in the margin (a smudge)."""
    prof = tsq.safe_profile()
    k, asf = prof["k"], tsq.action_safe_frac()
    x0, y0 = (1 - k) * W9 / 2, prof["y0"] * H9
    yy, xx = np.mgrid[0:H9, 0:W9].astype(np.float64)
    u, v = (xx - x0) / (k * W9), (yy - y0) / (k * H9)
    inside = ((u >= 0) & (u <= 1) & (v >= 0) & (v <= 1))[..., None]
    m = (np.clip(np.minimum(u, 1 - u) / asf, 0, 1) * np.clip(np.minimum(v, 1 - v) / asf, 0, 1))[..., None] * inside
    out = ground_frame * m + ground_canvas * (1 - m)
    if blob:
        bx, by, br, rgb = blob
        b = np.clip(1 - np.hypot(xx - bx, yy - by) / br, 0, 1)[..., None]
        out = out * (1 - b) + np.array(rgb) * b
    return out.clip(0, 255).astype(np.uint8)


def test_a_continued_ground_reads_clean_a_panel_and_a_smudge_do_not():
    g = _radial(W9, H9, 540, 300, 1700, (29, 24, 19), (8, 7, 6))
    clean = fsq.margin_seam(_framed(g, g))
    assert max(v for v, _ in clean.values()) <= fsq.MARGIN_SEAM_WARN, clean
    flat = np.zeros_like(g) + (13, 11, 9)                       # the film's flat root ground round a radial frame
    panel = fsq.margin_seam(_framed(flat, g))
    assert panel["top"][0] > fsq.MARGIN_SEAM_WARN, panel
    smudge = fsq.margin_seam(_framed(g, g, blob=(60, 300, 90, (190, 150, 60))))   # a gold arc in the margin
    assert smudge["left"][0] > fsq.MARGIN_SEAM_WARN and smudge["top"][0] <= fsq.MARGIN_SEAM_WARN, smudge


def _ghost_frame():
    """A plain radial ground, and in its bottom margin the outline of a phone's foot blurred 16 px — the ghost the
    unscaled echo drew under the caption (2026-10-31)."""
    from scipy.ndimage import gaussian_filter
    g = _radial(W9, H9, 540, 300, 1700, (29, 24, 19), (8, 7, 6))
    yy, xx = np.mgrid[0:H9, 0:W9]
    ring = ((np.abs(xx - 540) < 290) & (np.abs(yy - 1700) < 110)) & ~((np.abs(xx - 540) < 278) & (np.abs(yy - 1700) < 98))
    bar = (np.abs(xx - 540) < 90) & (np.abs(yy - 1780) < 4)
    ink = gaussian_filter((ring | bar).astype(np.float64), 16)[..., None] * 60
    return (g + ink).clip(0, 255).astype(np.uint8), g.astype(np.uint8)


def test_a_ghost_in_the_margin_is_structure_and_a_ground_is_not():
    ghost, plain = _ghost_frame()
    s_ghost, s_plain = fsq.margin_structure(ghost), fsq.margin_structure(plain)
    assert max(s_ghost["bottom"]) > fsq.MARGIN_STRUCTURE_WARN, s_ghost
    assert max(max(v) for v in s_plain.values()) <= fsq.MARGIN_STRUCTURE_WARN, s_plain
    # and the colour-across-the-edge check cannot tell the two apart — which is why the structure check exists
    assert fsq.margin_seam(ghost) == fsq.margin_seam(plain)


def test_a_frame_that_holds_no_seam_at_all_reads_clean():
    # E19: an input with no signal (one flat colour everywhere) must read as nothing, not as a step
    flat = np.zeros((H9, W9, 3), np.uint8) + 128
    assert all(v == 0 for v, _ in fsq.margin_seam(flat).values())
    assert all(max(v) < 1e-6 for v in fsq.margin_structure(flat).values())


@needs_toolchain
def test_the_margin_continues_the_frame_on_a_rendered_beat(tmp_path):
    from PIL import Image
    on = _still(tmp_path, "seam_on", {})
    off = _still(tmp_path, "seam_off", {"safeEcho": False})
    assert on.returncode == 0 and off.returncode == 0, ((on.stderr or "") + (off.stderr or ""))[-600:]
    for tag in ("seam_on", "seam_off"):          # the register's root ground, and the ground token alone
        arr = np.asarray(Image.open(str(tmp_path / (tag + ".png"))).convert("RGB"))
        seam, struct = fsq.margin_seam(arr), fsq.margin_structure(arr)
        assert max(v for v, _ in seam.values()) <= fsq.MARGIN_SEAM_WARN, (tag, seam)
        assert max(max(v) for v in struct.values()) <= fsq.MARGIN_STRUCTURE_WARN, (tag, struct)
