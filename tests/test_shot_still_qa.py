"""shot_still_qa's caption-band ink: what departs from the band's ground (a smooth surface), not from one grey."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import shot_still_qa as sq  # noqa: E402


def _lit(tmp_path, name, panel=False):
    import numpy as np
    from PIL import Image
    W, H = 1920, 1080
    yy, xx = np.mgrid[0:H, 0:W]
    a = (200 - 170 * np.clip(np.hypot((xx - 960) / 1100, (yy - 450) / 700), 0, 1)).astype(np.uint8)
    if panel:
        top = H - sq._caption_band_px(W, H)
        a[top + 10:H - 20, 300:1100] = 235
    p = tmp_path / name
    Image.fromarray(a).convert("RGB").save(p)
    return str(p)


def test_a_lit_ground_is_not_ink_but_a_panel_on_it_is(tmp_path):
    """A light pool across the band (the topic-to-video promo's spotlit KeyframeSheet read 41.8% over an empty band,
    2026-11-12): the band's ground is a smooth surface, and only what departs from it is content."""
    assert sq.measure(_lit(tmp_path, "pool.png"))["caption"] < sq.CAPTION_FRAC_ERR
    assert sq.measure(_lit(tmp_path, "panel.png", panel=True))["caption"] > sq.CAPTION_FRAC_ERR
