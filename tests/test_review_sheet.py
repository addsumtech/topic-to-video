"""review_sheet — the delivered film at 30/60/90 % of every beat and its two ends, for the eye (2026-11-12)."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import critic_ledger as cl  # noqa: E402
import review_sheet as rs  # noqa: E402


@pytest.fixture
def film(tmp_path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30:duration=4",
                    "-pix_fmt", "yuv420p", str(tmp_path / "out.mp4")], check=True)
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {}, "slides": [
        {"shot": "A", "duration": 2.0}, {"shot": "B", "duration": 2.0}]}))
    return tmp_path


def test_every_beat_gets_three_frames_and_the_film_its_ends(film):
    idx = rs.build(str(film))
    assert [r["beat"] for r in idx["rows"]] == [1, 2]
    assert all(len(r["seconds"]) == 3 for r in idx["rows"])
    a, b = idx["rows"][0]["seconds"][0], idx["rows"][0]["seconds"][-1]
    assert 0.3 <= a < b <= 2.0, idx["rows"][0]
    assert len(idx["sheets"]) == 1 and os.path.isfile(idx["sheets"][0]) and os.path.isfile(idx["ends"])


def test_the_label_is_never_drawn_on_a_frame(film):
    """A label inside a frame hid a title (read as a cut word) and a long caption's last words: it has its own strip."""
    from PIL import Image
    idx = rs.build(str(film))
    sheet = Image.open(idx["sheets"][0])
    h = round(rs.CELL_W * 180 / 320)
    assert sheet.height == 2 * (h + rs.LABEL_H + 4)


def test_it_is_an_advisory_delivery_gate_on_both_tiers():
    for tier in ("remotion", "html"):
        rows = [g for g in cl.DELIVERY_GATES[tier] if g[1] == "review_sheet.py"]
        assert len(rows) == 1 and rows[0][4] is False, tier
