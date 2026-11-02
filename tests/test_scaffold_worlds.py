"""A new shot's scaffold names every idiom world it may declare, in so many words.

WHY. The comment said "one of shot_director.IDIOM_WORLDS"; three parallel builders of one film each guessed
'editorial' and `workshop.py check` refused it ('print-editorial' is the world). The list is written in."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import shot_director  # noqa: E402
import workshop  # noqa: E402


def test_a_new_shot_lists_the_worlds_it_may_name(tmp_path):
    path = workshop.scaffold(str(tmp_path), "shot", "Probe", "a probe")
    src = open(path, encoding="utf-8").read()
    for w in shot_director.IDIOM_WORLDS:
        assert "'%s'" % w in src, w
