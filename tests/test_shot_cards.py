"""Every register has a CARD, and the card's parameter table names the props the register really reads.

The peer library's documentation carried a card per shot — identity, when to use it, the motion, a parameter
table where each row says what turning that knob FEELS like, and its known traps — and that form was recorded
as a capability this library lacked (references/launch-film-study.md, "The form of their documentation").
A card that drifts from the code is worse than none (LIBRARY.md drifted: `TermThink` advertised props it
never read, and films authored from it printed demo defaults), so the table is held to the declaration.
"""
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import demo_copy_qa as dq  # noqa: E402

SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")
CARDS = os.path.join(_ROOT, "remotion", "cards")
SECTIONS = ("**Identity:**", "**Use when:**", "**Motion core:**", "**Known traps:**", "**Reference:**")
# props that configure the film's plumbing rather than the picture — a card need not dwell on them
PLUMBING = {"accent", "accent2", "dna", "aspect", "framed", "imageAspect", "credit", "src"}


def _registers():
    return sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(SHOTS, "*.tsx")))


def _table_props(card):
    return set(re.findall(r"^\|\s*`([A-Za-z]\w*)`", card, re.M))


def test_every_register_has_a_card():
    missing = [r for r in _registers() if not os.path.exists(os.path.join(CARDS, r + ".md"))]
    assert not missing, "registers with no card in remotion/cards/: %r" % missing


def test_every_card_has_the_sections_and_points_at_its_register():
    bad = {}
    for r in _registers():
        p = os.path.join(CARDS, r + ".md")
        if not os.path.exists(p):
            continue
        card = open(p, encoding="utf-8").read()
        miss = [s for s in SECTIONS if s not in card]
        if not card.startswith("# %s\n" % r):
            miss.append("title '# %s'" % r)
        if "remotion/src/shots/%s.tsx" % r not in card:
            miss.append("reference path")
        if miss:
            bad[r] = miss
    assert not bad, "cards missing required parts: %r" % bad


def test_the_parameter_table_is_the_declaration():
    """Every declared prop (bar plumbing) has a row, and no row names a prop the register does not read."""
    drift = {}
    for r in _registers():
        p = os.path.join(CARDS, r + ".md")
        if not os.path.exists(p):
            continue
        declared = set(dq._declared_types(open(os.path.join(SHOTS, r + ".tsx"), encoding="utf-8").read(), r))
        rows = _table_props(open(p, encoding="utf-8").read())
        missing = declared - rows - PLUMBING
        extra = rows - declared
        if missing or extra:
            drift[r] = {"no row": sorted(missing), "not a prop": sorted(extra)}
    assert not drift, "card tables out of step with the code:\n%s" % "\n".join("%s %s" % kv for kv in drift.items())


def test_the_example_card_is_real():
    """The format's own example must satisfy the format — a template that fails its own test teaches nothing."""
    card = open(os.path.join(CARDS, "BentoReveal.md"), encoding="utf-8").read()
    assert _table_props(card) >= {"title", "hero", "heroKicker", "items"}
