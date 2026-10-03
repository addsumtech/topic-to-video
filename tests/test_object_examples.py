"""The object-authoring examples do what the doc says they do: the three good ones pass every check a film's code
must pass; the one with words written into it is refused; and the two that MEAN nothing pass every check too —
which is the reason a critic looks at every built thing (agents/shot-critic.md S15)."""
import os
import shutil
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import workshop as ws  # noqa: E402

EX = os.path.join(_ROOT, "references", "object-examples")
GOOD, BAD_WORDS, BAD_MEANING = ["PuckInSection", "StrataOverTime", "ComposeScreen"], ["LabeledPuck"], \
    ["ChromeMachine", "SwirlOfCoffee"]
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_ROOT, "remotion", "node_modules")),
                                     reason="needs the remotion toolchain")


def _film(tmp_path, names):
    d = tmp_path / "film" / "workshop" / "objects"
    d.mkdir(parents=True)
    for n in names:
        shutil.copy(os.path.join(EX, n + ".tsx"), str(d / (n + ".tsx")))
    return str(tmp_path / "film")


@needs_toolchain
def test_the_good_examples_pass_every_check(tmp_path):
    assert ws.check(_film(tmp_path, GOOD)) == []


@needs_toolchain
def test_words_written_into_an_object_are_refused(tmp_path):
    probs = ws.check(_film(tmp_path, BAD_WORDS))
    assert any("LabeledPuck.tsx" in p and "粉饼" in p for p in probs), probs


@needs_toolchain
def test_objects_that_mean_nothing_pass_every_check_which_is_why_a_critic_looks(tmp_path):
    assert ws.check(_film(tmp_path, BAD_MEANING)) == []


def test_the_doc_shows_every_example_rendered():
    doc = open(os.path.join(_ROOT, "references", "object-authoring.md"), encoding="utf-8").read()
    for n in GOOD + BAD_WORDS + BAD_MEANING:
        assert "object-examples/%s.png" % n in doc and os.path.getsize(os.path.join(EX, n + ".png")) > 5000, n
