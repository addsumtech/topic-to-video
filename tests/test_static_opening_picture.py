"""A page is not blank at its opening when a PICTURE is on it from frame 0 — not only text.

validate's opening-gap lint counted only uncued TEXT as early content, so a page whose card, photo or built component
stands on screen from the first frame (and whose words arrive later, on their cues) was warned as sitting BLANK while
the opening plays — four of a QR-code film's 31 pages (2026-11-04), each showing the code from frame 0. What paints at
frame 0 is any picture element (an <img>, an <svg>, a <canvas>, a custom element) with no reveal class on it or on an
ancestor — a cue on a wrapper that does not reveal does not hide it."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate  # noqa: E402


def test_a_picture_on_screen_from_frame_0_is_early_content():
    page = ('<body><div class="stage"><div class="abs" data-cue-index="0" data-cue="x">'
            '<qr-matrix bits="1"></qr-matrix></div><div class="vf-title reveal-up" data-cue-index="1" '
            'data-cue="y">later words</div></div></body>')
    assert validate._has_static_opening_picture(page)


def test_a_picture_that_reveals_is_not():
    page = ('<body><div class="stage"><div class="reveal" data-cue-index="0" data-cue="x"><img src="a.png"></div>'
            '<svg class="reveal-up"></svg><div><span class="reveal"><finder-card></finder-card></span></div></div></body>')
    assert not validate._has_static_opening_picture(page)
