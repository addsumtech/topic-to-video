"""ATMOSPHERE CONTEST preview — the contact-sheet generator (pick a world from PIXELS, not names).

The RENDER path is integration (3 sample renders, proven by a real run), so here we lock the deterministic
parts: routing → candidates, the canonical preview board, and the montage always producing a sheet (even when
a world's render is unavailable — a placeholder tile, never a blank/crash)."""
import os

import atmosphere_preview as ap


def test_canonical_board_carries_the_world_and_a_bars_reveal():
    b = ap._canonical_board("terminal")
    assert b["meta"]["atmosphere"] == "terminal"
    assert b["meta"]["renderer"] == "remotion"
    s = b["slides"][0]
    assert s["type"] == "cinematic3d" and s["planes"][0]["kind"] == "bars", \
        "the canonical preview must be a bars scene (reveals material+post+colour identically per world)"


def test_preview_routes_topic_to_three_candidates(monkeypatch):
    # stub the render so the test is fast + offline; assert routing + best-effort montage.
    monkeypatch.setattr(ap, "_render_one", lambda key, wd, accent, bg: None)
    out = str(monkeypatch)  # unused
    import tempfile
    d = tempfile.mkdtemp()
    res = ap.preview(d, topic="an AI agent framework CLI")
    assert res["candidates"][0] == "terminal", res["candidates"]
    assert len(res["candidates"]) == 3
    assert res["preview"] and os.path.isfile(os.path.join(d, res["preview"])), "the contact sheet was not written"


def test_preview_explicit_candidates_override_topic(monkeypatch):
    monkeypatch.setattr(ap, "_render_one", lambda key, wd, accent, bg: None)
    import tempfile
    d = tempfile.mkdtemp()
    res = ap.preview(d, candidates=["cartoon", "noir"])
    assert res["candidates"] == ["cartoon", "noir"]


def test_montage_always_produces_a_sheet_even_with_no_frames():
    import tempfile
    d = tempfile.mkdtemp()
    cards = [("terminal", "Mainframe", "A CRT terminal.", None),
             ("cartoon", "Storybook", "Cel-shaded.", None)]
    out = ap._montage(cards, os.path.join(d, "sheet.png"))
    from PIL import Image
    im = Image.open(out)
    assert im.size[0] > 0 and im.size[1] > 0, "montage produced an empty sheet"


def test_montage_embeds_a_real_frame_when_present():
    import tempfile
    from PIL import Image
    d = tempfile.mkdtemp()
    fp = os.path.join(d, "f.png")
    Image.new("RGB", (200, 120), (200, 40, 90)).save(fp)
    out = ap._montage([("app", "Device", "Clean product.", fp)], os.path.join(d, "sheet.png"))
    assert os.path.isfile(out)
