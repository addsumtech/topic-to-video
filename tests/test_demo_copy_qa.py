"""A register must not print its own DEMO COPY on a delivered frame.

THE EVIDENCE THIS WAS BUILT FROM. A delivered Chinese film about a real product used BentoReveal and gave it
`title`, `hero` and `heroKicker` in its own words but no `items` — so six of the frame's seven cells printed
the register's English demo labels (Throughput / Coverage / Trend / Signals / Team / Auto-sync). The render
succeeded, `shot_props` was non-empty so the empty-props warning stayed quiet, and the energy sweep measured
healthy ink, because placeholder text is ink. The frame was verified by rendering it and looking.

It is the twin of the empty-plate defect and the worse half: an empty plate says nothing, a demo default says
something FALSE about the subject. BentoReveal's own source records this exact bug being fixed once before
for `heroKicker` — the fix turned a hardcoded English word into a prop, which moved the default one level
down and left the hole where it was. That is why the check is on the PROP, not on any list of words.
"""
import json
import os
import sys

import demo_copy_qa as q
import validate as v

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(q.__file__)))


def test_it_reads_the_signature_not_the_component_body():
    """The first version regexed to the first `} = {})` and, on a register whose props type contains an
    object literal, ran past it into the JSX — reporting `fill='none'` and `transform='rotate(-90 55 55)'`
    as demo copy. A gate that invents findings gets switched off."""
    src = '''
export const Demo: React.FC<{title?: string; marks?: {n: number; label: string}[]}> = ({
  title = 'WorkBuddy', marks = [{n: 1, label: 'what to notice here'}], accent = '#22d3ee',
} = {}) => {
  return <svg fill="none" strokeLinecap="round" transform="rotate(-90 55 55)"><text>hi</text></svg>;
};
'''
    got = q.demo_defaults(src, "Demo")
    assert "title" in got and got["title"] == "WorkBuddy"
    assert "marks" in got and "what to notice here" in got["marks"]
    assert "accent" not in got, "a colour is configuration, not copy"
    for body_attr in ("fill", "strokeLinecap", "transform"):
        assert body_attr not in got, "%r came from the component body, not the signature" % body_attr


def test_the_finding_shows_what_a_viewer_will_READ():
    """'[2 items of placeholder copy]' tells an author a prop is missing but not whether the default is
    harmless or six English words landing on a Chinese frame — which is the whole finding."""
    src = """export const D: React.FC<{a?: string[]}> = ({items = ['Throughput', 'Coverage']} = {}) => null;"""
    got = q.demo_defaults(src, "D")
    assert "Throughput" in got["items"] and "Coverage" in got["items"]


def test_the_real_library_still_carries_the_defect_this_gate_names():
    """Pinned against the real register, so a future edit that re-hardcodes those labels is caught."""
    lib = q.library()
    assert "Docs" in lib["BentoReveal"]["items"], "BentoReveal's demo labels moved — re-verify the gate"
    assert lib["PhotoPlate"]["caption"] == "the thing itself"


def test_a_default_named_by_a_module_const_is_still_a_default():
    """`panels: PANELS = DEFAULT_PANELS` printed four English labels on any film that omitted `panels`, and a
    reader that only knew an inline `[...]` reported the register clean. A picture NAME (`icon: 'file'`) in the
    same literal is configuration, not copy, and must not be reported as words a viewer reads."""
    src = """const DEFAULT_PANELS = [{label: 'Find it', icon: 'search'}, {label: 'Edit it', glyph: 'checks'}];
export const D: React.FC<{panels?: {label: string}[]}> = ({panels: PANELS = DEFAULT_PANELS} = {}) => null;"""
    got = q.demo_defaults(src, "D")
    assert "Find it" in got["panels"] and "Edit it" in got["panels"], got
    assert "search" not in got["panels"] and "checks" not in got["panels"], got
    lib = q.library()
    assert "Find it" in lib["QuadSplit"]["panels"], "the real const-referenced default went unread again"
    # a string const and an object const print just the same (FallbackPath: `action = DEMO_ACTION`)
    strobj = """const DEMO_ACTION = 'One click';
const DEMO_FIRST: Route = {label: 'Go to the one already open', when: 'if it is there'};
export const F: React.FC<{action?: string; first?: Route}> = ({action: A = DEMO_ACTION, first: B = DEMO_FIRST} = {}) => null;"""
    got = q.demo_defaults(strobj, "F")
    assert got.get("action") == "One click" and "Go to the one already open" in got.get("first", ""), got
    unresolved = """export const E: React.FC<{items?: string[]}> = ({items = MISSING_CONST} = {}) => null;"""
    assert "items" not in q.demo_defaults(unresolved, "E"), "an unresolvable name must be skipped, not guessed"


def test_a_prop_explicitly_left_empty_is_a_DECISION_and_passes():
    """The opt-out has to exist and has to be honoured, or the gate forces authors to invent copy for parts
    of a register they deliberately want blank. `items: []` was rendered and confirmed to drop the labels
    without breaking the layout."""
    lib = {"Reg": {"items": "['A', 'B']", "note": "note"}}
    board = {"slides": [{"index": 0, "shot": "Reg", "shot_props": {"items": [], "note": ""}}]}
    assert q.audit_board(board, lib) == []


def test_a_partially_supplied_beat_is_the_case_that_matters():
    """Empty props were already caught. The dangerous beat is the one that LOOKS authored."""
    lib = {"Reg": {"title": "WorkBuddy", "items": "['A']"}}
    board = {"slides": [{"index": 4, "shot": "Reg", "shot_props": {"title": "腾讯"}}]}
    found = q.audit_board(board, lib)
    assert [(f[1], f[2]) for f in found] == [("Reg", "items")]


def test_validate_ERRORS_because_the_frame_says_something_false(tmp_path, monkeypatch):
    """A warning would be the wrong severity: this ships invented English content as the subject's own."""
    monkeypatch.setattr(v, "_DEMO_COPY_CACHE", {"BentoReveal": {"items": "['Throughput', 'Coverage']"}})
    errors, warnings = [], []
    slides = [{"index": 4, "shot": "BentoReveal", "shot_props": {"title": "腾讯"},
               "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"}}]
    v._check_remotion({"renderer": "remotion"}, slides, errors, warnings)
    hit = [e for e in errors if "DEMO COPY" in e]
    assert hit, "a partial-props beat did not ERROR: %r" % (errors,)
    assert "Throughput" in hit[0], "the error does not say what will print"
    assert "[]" in hit[0], "the error offers the string opt-out for an array prop"


def test_the_gate_is_parsed_not_listed():
    """The `NUM` map two lines below it in validate.py is the cautionary tale: a restated list of registers
    went stale and left two number-bearing registers exempt from the faithfulness check. This list would be
    136 registers and ~268 props."""
    src = open(v.__file__, encoding="utf-8").read()
    fn = src.split("def _demo_copy_library():")[1].split("\ndef ")[0]
    code = "\n".join(l.split("#")[0] for l in fn.split('"""')[2].splitlines())
    for name in ("BentoReveal", "PhotoPlate", "Throughput", "WorkBuddy"):
        assert name not in code, "_demo_copy_library hardcodes %r instead of parsing signatures" % name


def test_an_EMPTY_props_beat_keeps_its_own_finding_and_gains_the_copy(monkeypatch):
    """Stacking a second, longer error on a beat that already has an accurate finding teaches an author
    nothing. But the mannequin warning never said what would actually be READ off the frame, and an
    empty-props beat ships EVERY default — so the warning now names them."""
    monkeypatch.setattr(v, "_DEMO_COPY_CACHE", {"BentoReveal": {"items": "['Throughput']"}})
    errors, warnings = [], []
    v._check_remotion({"renderer": "remotion"},
                      [{"index": 4, "shot": "BentoReveal", "shot_props": {}}], errors, warnings)
    assert not [e for e in errors if "DEMO COPY" in e], "the empty-props beat got a duplicate error"
    assert any("will PRINT its demo copy" in w and "Throughput" in w for w in warnings), warnings
