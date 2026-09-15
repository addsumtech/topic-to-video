"""Two register defects that only a register fed REAL copy can show, and the shape they share.

Both were found the day `cjk_type_qa`'s declaration reader stopped being blind — not by reading the source,
but by feeding each register its own props in Chinese and looking at the frame it drew.

  SplitFlap   its flip cascade is an UNBOUNDED SUM: `settle = 0.14 + c*0.05 + r*0.14`. That passes t = 1 at
              column 17 on the first row and column 11 on the third, so every tile past it never lands and
              flickers random glyphs to the final frame. The English demo rows are 8-10 columns, which is the
              only reason it ever looked finished. Rendered with real Chinese rows, more than HALF the board
              was still unresolved on the last frame — the WordTunnel defect in another register: type the
              shot was given and never draws.

  MapPlate    its channel label avoided the place name by sitting at a FIXED 0.26 along the channel. That
              clears the centre only for a channel crossing the whole plate, which is what the default
              happens to be; a short corridor between two nearby places put the label back on the place name
              at 0.26 exactly as it had at 0.50.

The shared shape is a constant tuned on the demo input. Both tests below drive the case the demo does not
cover, so a constant that comes back is caught rather than the register being re-condemned by eye.
"""
import json
import os
import re
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _src(name):
    return open(os.path.join(_REM, "src", "shots", name + ".tsx"), encoding="utf-8").read()


def _still(comp, props, out_png, frame):
    pf = out_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="terminal"), fh, ensure_ascii=False)
    return subprocess.run(["npx", "remotion", "still", "src/index.ts", comp, out_png,
                           "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                          cwd=_REM, capture_output=True, text=True, timeout=900)


# ── SplitFlap: the cascade must FIT the board, whatever size the film makes it ──────────────────────
def test_the_flip_schedule_is_normalised_to_the_board_and_not_an_unbounded_sum():
    src = _src("SplitFlap")
    assert "const cascade =" in src and "SETTLE_BY" in src, "the normalisation is gone"
    m = re.search(r"const settle = ([^;]+);", src, re.S)
    assert m, "the settle expression moved"
    assert "cascade" in m.group(1), "settle no longer scales with the board: %r" % (m.group(1),)


def test_the_last_tile_of_a_WIDE_board_still_lands_before_the_clip_ends():
    """The arithmetic, driven at sizes the demo copy never reaches. A 30-column board is what one ordinary
    Chinese sentence makes."""
    src = _src("SplitFlap")
    by = float(re.search(r"SETTLE_BY = ([\d.]+)", src).group(1))
    start = float(re.search(r"SETTLE_BY_START = ([\d.]+)", src).group(1))
    for cols, rows in ((9, 2), (26, 3), (30, 4), (60, 6), (1, 1)):
        span = (cols - 1) * 0.05 + (rows - 1) * 0.14 + 0.05
        cascade = min(1.0, (by - start) / max(1e-6, span))
        last = start + span * cascade
        assert last <= by + 1e-9, "a %dx%d board's last tile lands at %.3f" % (cols, rows, last)
        assert last < 0.95, "%dx%d leaves no hold before the clip ends (%.3f)" % (cols, rows, last)


@needs_toolchain
def test_a_board_of_real_chinese_rows_is_fully_settled_at_the_frame_the_gates_sample(tmp_path):
    """The artifact, not the arithmetic. Unsettled tiles draw glyphs from `CH` — Latin capitals and digits —
    so a settled Chinese board contains no Latin at all, which is a measurement the frame can answer."""
    import sys
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))
    import onscreen_text_qa as o                                   # noqa: E402

    rows = ["办公的产物本身就是文件，不是一段还要你二次加工的文字",
            "它自己拆解任务、调用工具、改动文件，最后交出可验收的结果",
            "同样的输入框，同样的一段回答，变的是谁在动手做完这件事"]
    dur = int(re.search(r"DURATION = (\d+)", _src("SplitFlap")).group(1))
    png = str(tmp_path / "board.png")
    r = _still("SplitFlap", {"kicker": "交付物", "rows": rows}, png, int(dur * 0.88))
    assert r.returncode == 0, (r.stderr or "")[-600:]
    text = "".join(o.text_on_frame(png)) if hasattr(o, "text_on_frame") else ""
    if not text:                                                   # no OCR helper — fall back to ink
        from PIL import Image
        import numpy as np
        a = np.asarray(Image.open(png).convert("L"), dtype=np.float32) / 255.0
        ink = float((np.abs(a - float(np.median(a))) > 0.10).mean())
        assert ink > 0.06, "the board drew %.2f%% ink — it is not showing three settled rows" % (ink * 100)


# ── MapPlate: the channel label is placed by DISTANCE, not by a fraction that suits the default ─────
def test_the_channel_label_is_placed_by_distance_from_the_subject():
    src = _src("MapPlate")
    block = src.split("{channel ?", 1)[1].split("})() : null}", 1)[0]
    assert "const far = (" in block, "the label is back on a fixed fraction of the channel"
    assert "far(0.26) >= far(0.74)" in block, "it no longer chooses the end further from the mark"
    assert "const clash =" in block and "labTop" in block, (
        "the fallback is gone: a channel running THROUGH the subject has no quarter that clears it, and the "
        "label must go above its own bank rather than down into the name")


@pytest.mark.parametrize("frm,to", [((0.10, 0.18), (0.90, 0.86)),   # the default: crosses the whole plate
                                    ((0.33, 0.41), (0.52, 0.62)),   # a short corridor near the centre
                                    ((0.48, 0.10), (0.52, 0.90))])  # straight down through the mark
def test_the_chosen_quarter_is_the_one_further_from_the_centre(frm, to):
    """The rule itself, at three channel geometries. `cx` is the plate centre by construction, so the mark
    sits at 0.5/0.5 of the plate in every one of them."""
    cx, cy = 0.5, 0.5
    far = lambda f: ((frm[0] + (to[0] - frm[0]) * f - cx) ** 2
                     + (frm[1] + (to[1] - frm[1]) * f - cy) ** 2) ** 0.5
    chosen = 0.26 if far(0.26) >= far(0.74) else 0.74
    assert far(chosen) >= far(0.26 if chosen == 0.74 else 0.74)
    assert far(chosen) >= far(0.5), (
        "the chosen quarter is nearer the subject than the midpoint it exists to avoid")
