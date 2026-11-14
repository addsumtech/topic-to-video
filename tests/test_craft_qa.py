"""craft_qa — the three measured craft gaps against a reference corpus of launch films (scripts/craft_qa.py).

Measured 2026-10-31 on 28 skillry.dev launch-film previews and 22 of our own Remotion films, one instrument for both:
our films hold a frame still for longer (median longest still 5.0 s against 2.5 s), move with smaller peaks (motion
p90 2.1 against 4.3) and give no single element the frame (largest element's share of the layout 0.48 against 0.63;
3 main elements against 2). Content occupancy did not separate those two corpora, but against product launch films it
did (craft-standard.md), so it is measured too. These tests pin the instrument on synthetic films whose answer is known
by construction.
"""
import json
import os
import shutil
import subprocess

import numpy as np
import pytest

import craft_qa as cq

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg needed")


def _film(path, frames, fps=12, size=(320, 180)):
    """Write frames (callables t -> HxWx3 uint8) to an mp4 at `fps`."""
    w, h = size
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h),
                             "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "12", str(path)],
                            stdin=subprocess.PIPE)
    for f in frames:
        proc.stdin.write(np.ascontiguousarray(f, dtype=np.uint8).tobytes())
    proc.stdin.close()
    assert proc.wait() == 0
    return str(path)


def _ground(w=320, h=180, c=(240, 236, 228)):
    return np.full((h, w, 3), c, np.uint8)


def _box(img, x, y, bw, bh, c=(30, 30, 30)):
    img = img.copy()
    img[y:y + bh, x:x + bw] = c
    return img


def test_a_held_frame_is_measured_as_its_length(tmp_path):
    fps = 12
    frames = []
    for k in range(fps * 2):                                   # 2 s of a box sliding
        frames.append(_box(_ground(), 10 + 4 * k, 60, 60, 60))
    held = frames[-1]
    frames += [held] * (fps * 5)                               # 5 s held still
    for k in range(fps * 1):
        frames.append(_box(_ground(), 106 - 4 * k, 60, 60, 60))
    m = cq.measure(_film(tmp_path / "hold.mp4", frames, fps))
    assert 4.5 <= m["longest_still_s"] <= 5.2, m["longest_still_s"]


def test_a_film_that_never_rests_has_no_long_still(tmp_path):
    fps = 12
    frames = [_box(_ground(), 10 + 2 * k, 60, 60, 60) for k in range(fps * 6)]
    m = cq.measure(_film(tmp_path / "move.mp4", frames, fps))
    assert m["longest_still_s"] < 0.5, m["longest_still_s"]


def test_motion_peak_separates_a_punch_from_a_drift(tmp_path):
    fps = 12
    drift = [_box(_ground(), 10 + k, 60, 60, 60) for k in range(fps * 4)]
    punch = []
    for k in range(fps * 4):
        x = 20 if (k // 6) % 2 == 0 else 220                   # the box jumps across the frame every half second
        punch.append(_box(_ground(), x, 40, 80, 100))
    a = cq.measure(_film(tmp_path / "drift.mp4", drift, fps))
    b = cq.measure(_film(tmp_path / "punch.mp4", punch, fps))
    assert b["motion_p90"] > 3 * a["motion_p90"], (a["motion_p90"], b["motion_p90"])


def test_one_dominant_element_reads_as_hierarchy_and_six_equal_ones_do_not(tmp_path):
    hero = _box(_box(_ground(), 60, 30, 200, 100), 20, 140, 24, 6)            # one big block + a small label
    six = _ground()
    for i in range(3):
        for j in range(2):
            six = _box(six, 20 + i * 100, 20 + j * 70, 70, 45)
    a = cq.measure(_film(tmp_path / "hero.mp4", [hero] * 36))
    b = cq.measure(_film(tmp_path / "six.mp4", [six] * 36))
    assert a["hierarchy"]["dom_med"] > 0.7 and a["hierarchy"]["nblob_med"] <= 2, a["hierarchy"]
    assert b["hierarchy"]["dom_med"] < 0.3 and b["hierarchy"]["nblob_med"] >= 5, b["hierarchy"]


def test_the_caption_band_is_not_counted_as_an_element(tmp_path):
    """Captions are a constant of our films and absent from the reference ones: counted, every one of our frames
    would gain an element the reference never has."""
    h = 180
    img = _box(_ground(), 60, 20, 200, 90)
    img = _box(img, 30, h - 20, 260, 10)                    # a caption line inside the bottom band
    m = cq.measure(_film(tmp_path / "cap.mp4", [img] * 36))
    assert m["hierarchy"]["nblob_med"] == 1, m["hierarchy"]


def test_an_empty_frame_is_not_a_hierarchy_verdict(tmp_path):
    m = cq.measure(_film(tmp_path / "blank.mp4", [_ground()] * 36))
    assert m["hierarchy"]["measured_s"] == 0
    assert m["hierarchy"]["dom_med"] is None


def test_a_film_that_cannot_be_decoded_says_so(tmp_path):
    p = tmp_path / "bad.mp4"
    p.write_bytes(b"not a film")
    with pytest.raises(cq.Unmeasurable):
        cq.measure(str(p))


def test_findings_name_the_beat(tmp_path):
    fps = 12
    a = [_box(_ground(), 10 + 3 * k, 60, 60, 60) for k in range(fps * 3)]
    b = [_box(_ground(), 100, 60, 60, 60)] * (fps * 6)             # beat 2 holds still for its whole length
    path = _film(tmp_path / "beats.mp4", a + b, fps)
    board = {"meta": {}, "slides": [{"index": 1, "shot": "Mover", "duration": 3.0},
                                    {"index": 2, "shot": "Holder", "duration": 6.0}]}
    m = cq.measure(path, board=board)
    rows = {r["shot"]: r for r in m["beats"]}
    assert rows["Holder"]["longest_still_s"] > 4.0 > rows["Mover"]["longest_still_s"]
    lines = cq.findings(m)
    assert any("Holder" in ln and "still" in ln for ln in lines), lines
    assert not any("Mover" in ln and "still" in ln for ln in lines), lines


def test_reference_is_numbers_with_provenance_not_media():
    ref = json.load(open(cq.REFERENCE_PATH, encoding="utf-8"))
    assert ref["source"].startswith("https://skillry.dev")
    assert len(ref["films"]) >= 25
    for f in ref["films"]:
        assert set(f) >= {"slug", "longest_still_s", "motion_p90", "dom_med", "nblob_med", "one_thing"}
    med = ref["median"]
    assert 2.0 <= med["longest_still_s"] <= 3.0 and med["dom_med"] > 0.55
    root = os.path.dirname(cq.REFERENCE_PATH)
    assert not any(n.endswith((".mp4", ".webm")) for n in os.listdir(root))


def _census_frames(spec):
    """{frame: {"lines": [...]}} from [(frame, beat, [(height px, opacity), ...])]."""
    out = {}
    for f, b, lines in spec:
        out[f] = {"lines": [{"k": "/l%d" % i, "b": b, "h": h, "o": o, "t": "x"} for i, (h, o) in enumerate(lines)]}
    return out


def test_type_by_beat_reads_the_settled_lead_and_line_count():
    """Calibrated 2026-11-01: on the same film, the census's line-box height over Vision OCR's glyph box read 0.95
    (IQR 0.78-1.12), so the census number stands against the OCR-measured reference (launch films' lead type 7.6% of
    the short side; ours 5.8%; lines per frame 2.8 against 4.0)."""
    segs = [(0, 100), (100, 200)]
    frames = _census_frames([
        (10, 0, [(20, 1.0)]),                                   # beat 0 entering: before the settle point
        (60, 0, [(90, 1.0), (30, 1.0), (30, 1.0)]),            # settled: one 90 px lead among 3 lines
        (80, 0, [(90, 1.0), (30, 1.0), (30, 0.2)]),            # a faint line is not read
        (160, 1, [(40, 1.0)] * 6),                              # beat 1: six 40 px lines, nothing larger
    ])
    t = cq.type_by_beat(frames, segs, short_side=1080)
    assert abs(t[0]["lead"] - 90 / 1080) < 1e-4 and t[0]["lines"] in (2, 2.5, 3)
    assert abs(t[1]["lead"] - 40 / 1080) < 1e-4 and t[1]["lines"] == 6


def test_small_crowded_type_with_nothing_leading_is_named_and_a_drawing_lead_is_not():
    m = {"beats": [
        {"index": 1, "shot": "Crowded", "longest_still_s": 1, "hierarchy": {"dom_med": 0.3, "nblob_med": 5},
         "type": {"lead": 0.04, "lines": 6}},
        {"index": 2, "shot": "Diagram", "longest_still_s": 1, "hierarchy": {"dom_med": 0.8, "nblob_med": 2},
         "type": {"lead": 0.03, "lines": 7}},                  # the drawing leads: its labels may be small
        {"index": 3, "shot": "Headline", "longest_still_s": 1, "hierarchy": {"dom_med": 0.3, "nblob_med": 5},
         "type": {"lead": 0.09, "lines": 6}},
    ]}
    lines = cq.findings(m)
    assert any("Crowded" in ln and "type" in ln for ln in lines), lines
    assert not any("Diagram" in ln and "type" in ln for ln in lines), lines
    assert not any("Headline" in ln and "type" in ln for ln in lines), lines


def _lit(w=320, h=180):
    """A lit stage as runtime/craftStage paints it: a vertical gradient, a bright key pool, corners vignetted ~35
    levels darker than the centre — no edge anywhere."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = 236 - 14 * (yy / h)
    pool = 18 * np.exp(-(((xx - w * 0.62) / (w * 0.22)) ** 2 + ((yy - h * 0.35) / (h * 0.3)) ** 2))
    vig = 36 * np.clip(np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) - 0.55, 0, None) / 0.85
    g = np.clip(base + pool - vig, 0, 255)
    return np.repeat(g[..., None], 3, 2).astype(np.uint8)


def test_a_lit_stage_is_ground_and_a_white_card_in_its_light_is_drawn(tmp_path):
    """Against the border colour, a lit stage's vignette and key pool read as content (2026-11-14). Light has no edge:
    it is ground; a WHITE card sitting in the pool keeps its edge and is drawn; on a flat ground the rule is unchanged."""
    from scipy import ndimage
    lit = _lit()
    lit_only = cq._ground_ink(lit[:144].astype(np.int16))
    assert lit_only.mean() < 0.01, lit_only.mean()                     # the light itself is not content
    card = lit.copy()
    card[30:100, 160:280] = 252                                        # a white card in the pool...
    card[100:103, 162:282] = 200                                       # ...its soft shadow line
    card[29, 160:280] = card[30:100, 159] = card[30:100, 280] = 214    # ...and its hairline edge
    card = _box(card, 30, 50, 60, 30)                                  # and a dark block elsewhere
    m = cq._ground_ink(card[:144].astype(np.int16))
    assert m[40:90, 170:270].mean() > 0.9, m[40:90, 170:270].mean()    # the card is drawn
    assert m[50:80, 30:90].mean() > 0.95                               # so is the block
    assert m[110:140, 0:20].mean() < 0.05                              # the vignetted corner is not
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=3))
    assert n == 2, n
    flat = _box(_box(_ground(), 60, 30, 200, 100, c=(250, 250, 250)), 20, 140, 24, 6)
    f = flat[:144].astype(np.int16)
    border = np.concatenate([f[:3].reshape(-1, 3), f[:, :3].reshape(-1, 3), f[:, -3:].reshape(-1, 3)])
    assert (cq._ground_ink(f) == (np.abs(f - np.median(border, 0)).max(2) > cq.INK_DELTA)).all()


def test_occupancy_reads_how_much_of_the_frame_the_subject_spans(tmp_path):
    big = _box(_ground(), 20, 10, 280, 120)
    small = _box(_ground(), 140, 50, 40, 30)
    a = cq.measure(_film(tmp_path / "big.mp4", [big] * 36))["occupancy"]
    b = cq.measure(_film(tmp_path / "small.mp4", [small] * 36))["occupancy"]
    assert a["extent_med"] > 0.6 and b["extent_med"] < 0.1, (a, b)      # 0.73 drawn, trimmed to its central 96 %
    m = {"beats": [], "longest_still_s": 0, "hierarchy": {"dom_med": None, "nblob_med": None}, "occupancy": b}
    assert any("subject spans" in ln for ln in cq.findings(m))
    m["occupancy"] = a
    assert not any("subject spans" in ln for ln in cq.findings(m))


def test_a_wide_line_of_type_is_not_a_small_subject(tmp_path):
    """A display line spans the width and little of the area (ANC's 'Adding sound' read 16 %): not small."""
    line = _box(_ground(), 30, 60, 260, 26)
    o = cq.measure(_film(tmp_path / "line.mp4", [line] * 36))["occupancy"]
    assert o["extent_med"] < 0.4 and o["width_med"] > 0.7, o
    m = {"beats": [], "longest_still_s": 0, "hierarchy": {"dom_med": None, "nblob_med": None}, "occupancy": o}
    assert not any("subject spans" in ln for ln in cq.findings(m))
