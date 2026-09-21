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


# ---------------------------------------------------------------------------------------------------
# COVERAGE — what this gate did NOT judge. Before: `--library` printed "166 registers carry copy
# defaults" (a findings count, no denominator), and a film printed "no beat leaves a demo default in
# place" with no count of beats at all. Both read as the whole universe. Three items used to leave the
# measurement in silence: a register file that could not be read, a register whose signature this reader
# cannot parse (so a default it carries is invisible to every film check), and a beat naming a register
# that does not exist.

def _lib_dir(tmp_path, *, opaque=False, bad=False, bare=False):
    d = tmp_path / ("shots%d" % (int(opaque) * 4 + int(bad) * 2 + int(bare)))
    d.mkdir()
    (d / "Good.tsx").write_text(
        "export const Good: React.FC<{title?: string}> = ({title = 'Demo headline'}) => null;\n",
        encoding="utf-8")
    if bare:
        (d / "Bare.tsx").write_text(
            "export const Bare: React.FC<{n?: number}> = ({n = 3}) => null;\n", encoding="utf-8")
    if opaque:
        (d / "Opaque.tsx").write_text(
            "const P = {title: 'Demo headline'};\nexport function Opaque(props) { return null; }\n",
            encoding="utf-8")
    if bad:
        (d / "Bad.tsx").write_bytes(
            b"export const Bad: React.FC<{t?: string}> = ({t='x'}) => null;\n\xff\xfe")
    return str(d)


def test_the_library_count_is_coverage_and_the_denominator_is_derived(tmp_path):
    """`read N of M` where M is the number of .tsx on disk, not the number that yielded a finding."""
    import glob as _g
    d = _lib_dir(tmp_path, bare=True)
    lib, cov = q.library_covered(d)
    assert cov["universe"] == len(_g.glob(os.path.join(d, "*.tsx"))) == 2
    assert cov["read"] == 2 and cov["with_defaults"] == 1
    assert cov["no_defaults"] == ["Bare"], "a register with nothing to leave in must be named as measured"


def test_a_register_whose_signature_cannot_be_read_is_not_filed_as_having_no_defaults(tmp_path):
    """`_destructure` returning None gave `{}` — identical to a register that genuinely has none, and it
    is the case where demo copy ships while the film reports clean."""
    lib, cov = q.library_covered(_lib_dir(tmp_path, opaque=True))
    assert "Opaque" not in lib
    assert [n for n, _ in cov["no_signature"]] == ["Opaque"], cov
    assert "could not be parsed" in cov["no_signature"][0][1]
    assert "Opaque" not in cov["no_defaults"], "an unparsed signature was filed as 'carries none'"


def test_a_register_file_it_could_not_read_is_named(tmp_path):
    lib, cov = q.library_covered(_lib_dir(tmp_path, bad=True))
    assert cov["universe"] == 2 and cov["read"] == 1
    assert [n for n, _ in cov["unreadable"]] == ["Bad"] and "utf-8" in cov["unreadable"][0][1]


def test_a_library_run_that_could_not_read_part_of_itself_does_not_exit_clean(tmp_path, capsys,
                                                                              monkeypatch):
    monkeypatch.setattr(q, "SHOTS", _lib_dir(tmp_path, bad=True, opaque=True))
    rc = q.main(["--library"])
    out = capsys.readouterr().out
    assert "read 2 of 3 register file(s)" in out, out.splitlines()[0]
    assert "COULD NOT BE READ" in out and "Bad" in out
    assert "NOT MEASURED" in out and "Opaque" in out
    assert rc == 2, "part of the universe was unmeasured and the run exited %r" % rc


def test_a_film_report_says_how_many_beats_it_judged(tmp_path, capsys, monkeypatch):
    """"no beat leaves a demo default in place" is the same sentence for eight beats and for none."""
    monkeypatch.setattr(q, "SHOTS", _lib_dir(tmp_path))
    d = tmp_path / "film"
    d.mkdir()
    (d / "storyboard.json").write_text(json.dumps({"slides": [
        {"index": 1, "shot": "Good", "shot_props": {"title": "real copy"}},
        {"index": 2, "shot": "Vanished", "shot_props": {}},
        {"index": 3, "shot_props": {}},
    ]}), encoding="utf-8")
    rc = q.main([str(d)])
    out = capsys.readouterr().out
    assert "judged 1 of 3 beat(s)" in out, out.splitlines()[0]
    assert "NOT JUDGED" in out and "'Vanished' is not a register" in out, out
    assert "selects no register" in out, "a still beat must still be accounted for"
    assert rc == 2, "a beat nothing was checked on exited %r — a caller reads that as clean" % rc


def test_a_beat_naming_a_real_register_is_counted_as_judged(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(q, "SHOTS", _lib_dir(tmp_path, bare=True))
    d = tmp_path / "film2"
    d.mkdir()
    (d / "storyboard.json").write_text(json.dumps({"slides": [
        {"index": 1, "shot": "Bare", "shot_props": {}},
    ]}), encoding="utf-8")
    rc = q.main([str(d)])
    assert "judged 1 of 1 beat(s)" in capsys.readouterr().out
    assert rc == 0


def test_a_superseded_props_default_is_not_reported_because_it_never_draws():
    """`PortRail` declares `// @supersedes groups: items`: a beat that supplies `groups` makes `items` dead,
    so its demo default cannot reach the frame and reporting it is a wolf.

    This fired on a DELIVERED film — the AgentHalo cut's beat 3 supplies three named groups and this gate
    reported `PortRail.items → ['Docs','Chat','Mail','Calendar','Wiki']`. `validate.py` had applied the
    declaration since it existed; the standalone CLI never did, so the two disagreed about one board. Worse,
    `supersedes()` was defined BELOW `if __name__ == "__main__"`, so as a script the name was not yet bound
    when `main` ran — the rule was unreachable exactly where an operator would meet it.

    The silence is narrow on purpose: only the superseded prop goes quiet, and only when its superseder is
    actually supplied."""
    import importlib.util
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "demo_copy_qa", os.path.join(os.path.dirname(here), "scripts", "demo_copy_qa.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    sup = m.supersedes()
    assert sup.get("PortRail", {}).get("groups") == ["items"], \
        "PortRail no longer declares the supersession this test is about: %r" % (sup.get("PortRail"),)

    bare = {"slides": [{"index": 1, "shot": "PortRail", "shot_props": {"title": "x"}}]}
    grouped = {"slides": [{"index": 1, "shot": "PortRail", "shot_props": {
        "title": "x", "groups": [{"label": "a", "items": ["p"]}]}}]}
    props_of = lambda board: {p for _, _, p, _ in m.audit_board(board)}

    assert "items" in props_of(bare), "the default a film does NOT supersede must still be reported"
    assert "items" not in props_of(grouped), "a superseded prop's default cannot draw, so it is not a finding"
    # ...and the silence is only for that prop: everything else the beat leaves out still reports
    assert props_of(bare) - {"items"} == props_of(grouped), \
        "supersession silenced more than the prop it kills: %r vs %r" % (props_of(bare), props_of(grouped))

    # the entry point must stay below every definition, or the rule is unreachable from the CLI again
    src = open(os.path.join(os.path.dirname(here), "scripts", "demo_copy_qa.py"), encoding="utf-8").read()
    assert src.index('if __name__ == "__main__":') > src.index("def supersedes"), \
        "`supersedes()` is defined after the entry point again — as a script it will not be bound"
