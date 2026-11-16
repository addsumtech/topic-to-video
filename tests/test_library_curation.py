"""LIBRARY CURATION — the director proposes a look once, and a picture of a subject only for that subject.

The library review of 2026-11-03 (one still per register, ~/code_project/film_work/library_curation.md) found two
things the variety rule cannot see. Sets of registers say the SAME thing in a different finish — a centred wordmark in
six materials, a hub with things round it in four, a "done" check in seven, a bar race in two — and the picker, which
only refuses a register already used and an adjacent family, would hand one film three of the wordmarks. And about
fifteen registers are a picture of a SUBJECT (a DNA helix, an atom, a nebula, rain on glass) that the statement and close
lists offered to any film as a backdrop for a word: on a calendar app's film the helix is decoration, on a genetics film
it is the subject. Nothing is deleted (a board on disk may name any register); what changes is what is PROPOSED.

  * every register the two tables name is a real register;
  * a twin of a register the film already uses is taken only when nothing fresh is left;
  * a subject register is proposed only when the beat's argument or the film's title is about its subject, in English
    and Chinese, and a word said in another sense ("fire up the app") does not count;
  * validate WARNS on a board that uses two twins, naming the set.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import shot_director as sd  # noqa: E402


def _film(n, title, intent="statement", ideal=None):
    d = {"meta": {"title": title},
         "slides": [{"index": i, "narration": "x", "duration": 6,
                     **({"shot_fit": {"ideal": ideal}} if ideal else {})} for i in range(n)]}
    plan = {"beats": [{"id": i + 1, "visual_intent": intent} for i in range(n)]}
    sd.assign_shots(d, plan)
    return [s["shot"] for s in d["slides"]]


def test_the_tables_name_real_registers():
    named = [r for group in sd.TWINS.values() for r in group] + list(sd.TOPIC_ONLY)
    missing = [r for r in named if r not in sd.FAMILY]
    assert not missing, missing
    seen = [r for group in sd.TWINS.values() for r in group]
    assert len(seen) == len(set(seen)), "a register sits in two twin sets"
    for reg, (subject, cues) in sd.TOPIC_ONLY.items():
        assert subject and cues, reg


def test_a_film_takes_one_register_of_a_twin_set_while_fresh_ones_remain():
    """A second register of a twin set is cast only once every FRESH candidate is used — a fresh one being a statement
    register the beat may take (its subject allows it) that is neither used nor a twin of one used. Asserted as that
    rule, not as "at most one": once the audit of 2026-11-15 put 13 statement registers in the wordmark set, a 24-beat
    film of nothing but statements has fewer distinct looks than beats, and a repeat is the only choice left."""
    allowed = [c for c in sd.CANDIDATES["statement"] if sd.topic_allows(c, "A calendar app for teams")]
    for n in (14, 24, 30):
        shots = _film(n, "A calendar app for teams")
        if n == 14:                                   # plenty of fresh looks: no twin is spent
            for name, group in sd.TWINS.items():
                assert len([s for s in shots if s in group]) <= 1, (n, name)
        for k, s in enumerate(shots):
            g = sd._TWIN_OF.get(s)
            before = shots[:k]
            if not g or not any(sd._TWIN_OF.get(b) == g for b in before):
                continue
            sets = {sd._TWIN_OF[b] for b in before if b in sd._TWIN_OF}
            fresh = [c for c in allowed if c not in before and sd._TWIN_OF.get(c) not in sets]
            assert not fresh, (n, k, s, "a twin was cast while these were fresh", fresh[:5])


def test_a_subject_register_is_not_a_backdrop_for_another_subject():
    for n in (24, 40):
        shots = _film(n, "A calendar app for teams")
        stray = [s for s in shots if s in sd.TOPIC_ONLY]
        assert not stray, (n, stray)
    shots = _film(6, "A calendar app for teams", intent="statement")
    assert not set(shots) & set(sd.TOPIC_ONLY)


def test_a_subject_register_is_offered_to_its_own_subject():
    assert sd.topic_allows("DNAHelix", "how DNA stores the genes of a cell")
    assert sd.topic_allows("DNAHelix", "基因如何被复制")
    assert sd.topic_allows("NebulaField", "where stars are born in the galaxy")
    assert sd.topic_allows("EmberFlame", "how a forest fire spreads")
    assert sd.topic_allows("EmberFlame", "火焰的温度")
    assert not sd.topic_allows("EmberFlame", "fire up the app and you're ready")
    assert not sd.topic_allows("DNAHelix", "it's in our company's DNA")
    assert not sd.topic_allows("StarfieldWarp", "a five-star review")
    assert sd.topic_allows("CinematicTitle", "anything at all")     # not a subject register
    shots = _film(30, "How DNA is copied", ideal="the double helix unzips as the genes are copied")
    assert "DNAHelix" in shots[:3], "the subject's own picture leads, it does not wait for the list to run dry: %s" % shots


def test_a_list_runs_dry_before_a_twin_is_reused():
    # a list made only of one twin set still yields a register — the rule orders, it never empties the pool
    group = sd.TWINS["wordmark"]
    got = sd._pick(list(group), None, {group[0]})
    assert got in group and got != group[0]
    got = sd._pick([group[0], group[1]], None, set(group))
    assert got in group


def test_validate_warns_on_two_twins():
    import validate
    board = {"meta": {"renderer": "remotion"},
             "slides": [{"index": 1, "shot": "CinematicTitle"}, {"index": 2, "shot": "ChartLive"},
                        {"index": 3, "shot": "LiquidChrome"}]}
    w = validate.twin_warnings(board["slides"])
    assert len(w) == 1 and "CinematicTitle" in w[0] and "LiquidChrome" in w[0] and "wordmark" in w[0], w
    assert not validate.twin_warnings([{"shot": "CinematicTitle"}, {"shot": "ChartLive"}])
