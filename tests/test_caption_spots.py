"""caption_spots: a caption sits on the picture's own empty ground, never over content (the user, 2026-11-25)."""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import caption_spots as cs  # noqa: E402

W, H = 1920, 1080


def frames(n, block=None, ground=255):
    """n frames of one ground; block(i) -> (x0, y0, x1, y1) of something drawn on frame i, or None."""
    out = []
    for i in range(n):
        a = np.full((H, W, 3), ground, np.uint8)
        b = block(i) if block else None
        if b:
            a[b[1]:b[3], b[0]:b[2]] = (40, 90, 200)
        out.append(a)
    return out


def test_an_empty_ground_takes_the_first_spot_and_its_tone_picks_the_ink():
    fr = frames(60)
    spots, bad = cs.place([[0.0, 1.5, "Here it is."]], lambda i: fr[i], [300], [960, 760], [1012], 56, W, H, 60)
    assert bad == [] and spots == {"0": [960, 1012, "light"]}
    dark = frames(60, ground=24)
    spots, _ = cs.place([[0.0, 1.5, "Here it is."]], lambda i: dark[i], [300], [960], [1012], 56, W, H, 60)
    assert spots["0"][2] == "dark"


def test_something_passing_through_moves_the_caption_and_a_frame_with_no_room_is_red():
    # a chart dragged across the bottom centre while the caption is up: the left spot is the clean one
    fr = frames(60, lambda i: (900 + i * 4, 960, 1300 + i * 4, 1070) if 20 <= i < 40 else None)
    spots, bad = cs.place([[0.0, 1.9, "There it is."]], lambda i: fr[i], [300], [960, 420], [1012], 56, W, H, 60)
    assert bad == [] and spots["0"][:2] == [420, 1012]
    full = frames(60)
    for a in full:                                   # content all along the bottom (rows of text, a chart's labels)
        a[900:, :, :][::12] = 30
    spots, bad = cs.place([[0.0, 1.9, "Nowhere"]], lambda i: full[i], [300], [960, 420], [1012], 56, W, H, 60)
    assert bad == [0] and spots == {}


def test_a_ground_that_changes_under_the_caption_is_not_one_ground():
    # the card's dark ground giving way to the white sheet mid-caption (a push out of the card)
    fr = [frames(1, ground=24)[0] if i < 30 else frames(1)[0] for i in range(60)]
    spots, bad = cs.place([[0.0, 1.9, "First, select"]], lambda i: fr[i], [300], [960], [1012], 56, W, H, 60)
    assert bad == [0]


def test_the_previous_spot_is_kept_while_it_stays_clean():
    fr = frames(90)
    caps = [[0.0, 1.0, "one"], [1.0, 2.0, "two"]]
    spots, _ = cs.place(caps, lambda i: fr[i], [200, 200], [1400, 960], [1012], 56, W, H, 90)
    assert spots["0"][:2] == spots["1"][:2] == [1400, 1012]
