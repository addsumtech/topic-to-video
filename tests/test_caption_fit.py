"""The burned caption stays inside the band it reserves, whatever the sentence.

A sentence longer than two lines is cut at a clause boundary before it is shown, and that decision is only as
good as the width it is made against: the caption block is padded on both sides, so its text wraps in less
than the block's own width. Judged against the whole block, a 68-glyph Chinese sentence counted as two lines
and was set in three, the third laid over the shot's own title and note. Rendered here with captions on and
off; the difference between the two frames is exactly the caption, and none of it may sit above the band.
"""
import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import _caption_band as cb  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

# one sentence, clause marks inside it, longer than two lines of the 16:9 text measure (32 glyphs at 45px)
# and shorter than two lines of the whole block (35) — the case the block's width hid
LONG = ("这时机器发出一段射频脉冲，频率正好跟它们打转的频率一样，所以它们跟着共振，被一起扳倒；"
        "倒下之后还在接着转，旁边的线圈里就感应出了电信号。")
SCALE = 0.5


def _frame(tmp_path, aspect, captions, safe=None):
    scene = {"shot": "TermTable", "durF": 150, "caption": LONG,
             "props": {"kicker": "K", "rows": [["a", "1"], ["b", "2"]]}}
    pf = str(tmp_path / ("%s-%s-%s.json" % (aspect.replace(":", "x"), captions, safe)))
    props = {"scenes": [scene], "dna": "product", "captions": captions, "camera": 0, "aspect": aspect}
    if safe:
        props["safe"] = safe
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    png = pf[:-5] + ".png"
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=40", "--gl=angle",
                        "--timeout=150000", "--scale=%s" % SCALE, "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return png


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16"])
def test_a_long_sentence_never_climbs_out_of_the_caption_band(tmp_path, aspect):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    on = np.asarray(Image.open(_frame(tmp_path, aspect, True)).convert("L"), dtype=float)
    off = np.asarray(Image.open(_frame(tmp_path, aspect, False)).convert("L"), dtype=float)
    rows = np.where((np.abs(on - off) > 40).any(axis=1))[0]
    assert len(rows), "no caption was drawn — the frame or the scene's caption window is wrong"
    w, h = cb.aspect_wh(aspect)
    band_top = (h - cb.caption_band_px(w, h)) * SCALE
    assert rows.min() >= band_top - 1, (
        "the caption reaches %d px above its band (%.0f px from the top, band starts at %.0f) — it was fitted "
        "against a wider measure than the one its text wraps in" % (band_top - rows.min(), rows.min(), band_top))


@needs_toolchain
def test_a_platform_safe_caption_stays_clear_of_the_platform_ui(tmp_path):
    # runtime/safeZone.ts: on a 9:16 film for the platforms the caption ends above the bottom share the description
    # covers and its lines end short of the button column. A full CJK line (it breaks anywhere, so it fills the
    # measure) ran to x 960 of 1080 — under the buttons from 929.
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    import text_safe_qa as tq
    prof = tq.safe_profile()
    on = np.asarray(Image.open(_frame(tmp_path, "9:16", True, "social")).convert("L"), dtype=float)
    off = np.asarray(Image.open(_frame(tmp_path, "9:16", False, "social")).convert("L"), dtype=float)
    ink = np.abs(on - off) > 40
    rows, cols = np.where(ink.any(axis=1))[0], np.where(ink.any(axis=0))[0]
    assert len(rows), "no caption was drawn"
    w, h = cb.aspect_wh("9:16")
    assert cols.max() / SCALE <= w * (1 - prof["right"]), (
        "the caption runs to x %.0f, into the button column from %.0f" % (cols.max() / SCALE, w * (1 - prof["right"])))
    assert rows.max() / SCALE <= h * (1 - prof["bottom"]), (
        "the caption reaches y %.0f, into the platform's bottom from %.0f" % (rows.max() / SCALE, h * (1 - prof["bottom"])))
    assert cols.max() / SCALE >= w * (1 - prof["right"]) - 80, "the caption no longer fills its measure — the test lost its point"
