"""Fixes from the 2026-10-30 generality validation (two films off the Agent HUD path: a 9:16 remotion teach film and
a 1:1 HTML film). Each test is the defect as the run met it."""
import os

import jitter_qa as jq
import keyframe_qa as kq
import imagefetch as F
import storyboard as sb
import validate


def test_keyframe_qa_judges_a_square_film_on_its_own_canvas():
    # a 1:1 film's pages were captured and judged on 1920x1080 while render.py drew them at 1080x1080
    assert kq.canvas({"aspect": "1:1", "width": 1080, "height": 1080}) == (1080, 1080)
    assert kq.canvas({"aspect": "4:5", "width": 1080, "height": 1350}) == (1080, 1350)
    assert kq.canvas({"aspect": "9:16"}) == (1080, 1920)
    assert kq.canvas({}) == (1920, 1080)
