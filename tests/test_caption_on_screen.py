"""A headline that IS the spoken line yields the burned caption (scripts/render_remotion.caption_on_screen)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import render_remotion as rr                                                     # noqa: E402


def test_the_line_itself_on_screen_takes_the_caption_s_place():
    sc = {"shot": "HeadlineReveal", "caption": "Thinner, louder, better.",
          "props": {"lines": ["Thinner,", "louder, *better*."]}}
    assert rr.caption_on_screen(sc)


def test_a_headline_that_only_shares_words_keeps_the_caption():
    sc = {"shot": "HeadlineReveal", "props": {"lines": ["It doesn't block the hum."]},
          "caption": "Your earbud doesn't block the hum. It plays it back upside down, right on time."}
    assert not rr.caption_on_screen(sc)


def test_chinese_line_matches_through_punctuation():
    sc = {"shot": "HeadlineReveal", "caption": "冷，是热被搬走了。", "props": {"lines": ["冷，", "是热被*搬走*了"]}}
    assert rr.caption_on_screen(sc)


def test_only_a_register_whose_type_can_be_the_line():
    sc = {"shot": "FridgeLoop", "caption": "冷，是热被搬走了。", "props": {"lines": ["冷，是热被搬走了。"]}}
    assert not rr.caption_on_screen(sc)
