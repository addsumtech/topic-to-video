"""A library register's burned caption is checked against the ground the register really paints under it.

The film inks every caption from the ground it RESOLVES for a beat (DNA_GROUND_TOKEN under the film's DNA), never
from the pixels. A `@dark-world` register keeps its own night on a light film while its row still names the film's
`bg`, so the caption came out dark ink on a dark frame — unreadable — and every gate passed it."""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import shot_proof as sp  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

PAPER = 0.86          # relative luminance of a warm paper ground
NIGHT = 0.004         # a register's own near-black night

LIGHT_DNA = {"id": "paper-film", "bg": "#f2efe9", "fg": "#16171a", "dim": "#66645f", "accent": "#d4481a",
             "accent2": "#2c6a8a", "onAccent": "#ffffff", "surface": "#fbfaf7", "surfaceBorder": "#d6d1c7",
             "line": "#dfdad1", "decoration": []}


def test_a_caption_inked_for_paper_does_not_read_on_a_night():
    ink, c = sp.caption_on_ground(PAPER, NIGHT)
    assert ink < 0.5 and c < sp.CAPTION_READABLE_MIN


def test_a_caption_on_the_ground_it_was_inked_for_reads():
    assert sp.caption_on_ground(PAPER, 0.8) is None
    assert sp.caption_on_ground(NIGHT, 0.006) is None


def test_a_ground_the_ink_still_reads_on_is_not_an_error():
    """Only a caption that would no longer READ is an error — a ground a little off the resolved one is not."""
    assert sp.caption_on_ground(PAPER, 0.45) is None


def test_a_beat_that_grounds_itself_is_not_judged_from_a_still():
    kind, why = sp._library_caption_ground(None, "BokehPull", {"ground": 1}, LIGHT_DNA)
    assert kind == "n/a" and "ground" in why


def _board(out, shot, props):
    os.makedirs(out, exist_ok=True)
    board = {"meta": {"renderer": "remotion", "language": "zh", "design_dna": LIGHT_DNA},
             "slides": [{"index": 1, "shot": shot, "narration": "一句话。", "shot_props": props}]}
    with open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False)


@needs_toolchain
def test_a_dark_world_register_on_a_light_film_is_an_unreadable_caption(tmp_path, capsys):
    out = str(tmp_path / "film")
    _board(out, "BokehPull", {"title": "看得见", "tagline": "概念"})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "caption ground" in printed and "under the 3.0:1 a caption needs" in printed, printed[-2000:]


@needs_toolchain
def test_a_register_that_follows_the_light_ground_passes(tmp_path, capsys):
    out = str(tmp_path / "film")
    _board(out, "CinematicTitle", {"kicker": "概念", "title": "看得见", "tagline": "一句话"})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "caption ground" not in printed, printed[-2000:]
