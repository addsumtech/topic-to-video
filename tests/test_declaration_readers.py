"""Every static reader of a register's props must SEE every register the library ships.

WHY THIS FILE IS CROSS-CUTTING. Four separate scripts answer "what does this register declare", each with
its own regex, and each regex has spellings it refuses. A refused spelling is not an error — it is an empty
result, which flows downstream as *this register declares nothing* and then as *this register is fine*. The
four instances found on 2026-09-15, three of them because ONE new register happened to use a spelling nobody
had used before:

    cjk_type_qa._one_prop        a prop preceded by a JSDoc comment   → 2 invisible, 25 read in part
    cjk_type_qa.prop_signature   `React.FC<Props>` (a named alias)    → AcceptanceStamp swept in English
    cjk_type_qa.prop_signature   `React.FC<{...} >` (one space)       → MRIPipeline swept in English
    cjk_type_qa._alias_fields    `type X = A | B` (a union)           → SplitFlap swept on a BLANK board

Each was fixed where it was found, and fixing an instance is not the same as closing the class: the next
register to use a spelling none of these regexes expect will produce the same silence. So the assertion here
is made of the FOLDER, not of a list — a new register is covered the day it lands, and a new reader is
covered by adding one line to `READERS`.

`LiquidMorph` is named rather than pattern-matched. It declares `React.FC` with no props at all, which is a
real finding about the register (a film cannot author it), and naming it means a SECOND propless register
has to be looked at instead of being absorbed into an allowance.
"""
import glob
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import cjk_type_qa as c              # noqa: E402
import demo_copy_qa as d             # noqa: E402
import onscreen_text_qa as o         # noqa: E402
import shot_proof as sp              # noqa: E402

# Empty since LiquidMorph took `forms` (2026-09): it printed "Ask. Draft. Analyse. Done." on every film and no
# film could change a word of it. A register added here is one a film cannot author at all.
PROPLESS = set()


def _names():
    names = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(_SHOTS, "*.tsx")))
    assert len(names) > 140, "the shots folder moved — this test would pass on an empty list"
    return names


def _takes_props(name):
    src = open(os.path.join(_SHOTS, name + ".tsx"), encoding="utf-8").read()
    return re.search(r"export const %s\s*:\s*React\.FC<" % re.escape(name), src) is not None


def _reader_cjk(name):
    return set(c.prop_signature(name)[0])


def _reader_demo(name):
    src = open(os.path.join(_SHOTS, name + ".tsx"), encoding="utf-8").read()
    return set(d._declared_types(src, name) or ())


def _reader_onscreen(name):
    body = o._strip_comments(open(os.path.join(_SHOTS, name + ".tsx"), encoding="utf-8").read())
    return bool(re.search(r"export const %s: React\.FC<.*?>\s*=\s*\(\{" % re.escape(name), body, re.S))


def _reader_shot_proof(name):
    return set(sp.exported_props(name) or ())


READERS = [("cjk_type_qa.prop_signature", _reader_cjk),
           ("demo_copy_qa._declared_types", _reader_demo),
           ("shot_proof.exported_props", _reader_shot_proof)]


@pytest.mark.parametrize("label,read", READERS, ids=[r[0] for r in READERS])
def test_the_reader_sees_every_register_that_declares_props(label, read):
    blind = [n for n in _names() if _takes_props(n) and not read(n)]
    assert not blind, (
        "%s reads NOTHING from %d register(s), so every gate built on it reports them clean about a frame "
        "rendered from their English demo defaults: %s" % (label, len(blind), ", ".join(blind)))


def test_the_destructuring_reader_finds_every_register_s_own_parameter_block():
    """`onscreen_text_qa` answers a different question (which declared props are never READ), so it is
    checked by whether it locates the register's own block at all."""
    blind = [n for n in _names() if _takes_props(n) and not _reader_onscreen(n)]
    assert not blind, "onscreen_text_qa cannot locate: %s" % (", ".join(blind),)


def test_a_register_that_declares_nothing_is_NAMED_not_allowed_by_pattern():
    propless = {n for n in _names() if not _takes_props(n)}
    assert propless == PROPLESS, (
        "the set of registers a film cannot author at all has changed: %r. That is a finding about the "
        "register, not about the readers — add it here deliberately or give it props." % (sorted(propless),))


def test_the_readers_agree_with_each_other_about_what_a_register_declares():
    """Three readers, one declaration. They disagreed for months and nothing asked: `cjk_type_qa` saw one
    prop of MadeOf's five while `shot_proof` saw all five, and each gate reported confidently on its own
    half. Agreement is not required to be exact — the readers answer slightly different questions — but one
    seeing a prop the others cannot is the signature of the defect this file exists for."""
    bad = {}
    for n in _names():
        if not _takes_props(n):
            continue
        seen = {label: read(n) for label, read in READERS}
        union = set().union(*seen.values())
        missing = {label: sorted(union - got) for label, got in seen.items() if union - got}
        if missing:
            bad[n] = missing
    assert not bad, (
        "these registers are read differently by different readers — one of them is blind to a spelling "
        "the others handle: %r" % (bad,))


# ── a prop can be supplied by ANOTHER prop, and the demo-copy check had no way to know ─────────────
def test_the_supersedes_relation_is_declared_in_the_register_and_parsed():
    """`PortRail` grew `groups` — items that belong to named kinds — and when a board gives groups, `items`
    is never read. The demo-copy check saw `items` unset, found demo copy behind it, and ERRORED that
    'Docs / Chat / Mail' would print on a delivered frame that does not contain them.

    A false error on a correct board is worse than a missed one: it is the finding people learn to route
    around, and this repo already has the shape on record (an opt-in gate reporting 0 on the very deck that
    caused it). `SurfaceCarousel` has carried the same either/or for weeks and would have produced the same
    false error the first time a board used its richer prop.

    The relation is declared in the REGISTER, beside the props, and parsed — never listed in a script, which
    is the drift this repo has paid for five times this week."""
    import demo_copy_qa as d                                        # noqa: E402
    sup = d.supersedes()
    assert sup.get("PortRail", {}).get("groups") == ["items"], sup.get("PortRail")
    assert sup.get("SurfaceCarousel", {}).get("surfaces") == ["items", "nav"], sup.get("SurfaceCarousel")
    for name, rel in sup.items():
        src = open(os.path.join(_SHOTS, name + ".tsx"), encoding="utf-8").read()
        declared = set(c.prop_signature(name)[0])
        for provider, supplied in rel.items():
            assert provider in declared, (
                "%s declares `@supersedes %s` and has no such prop" % (name, provider))
            for p in supplied:
                assert p in declared, "%s says %s supplies `%s`, which it does not declare" % (name, provider, p)


def test_the_directive_does_not_swallow_the_line_after_it():
    """The first version's character class included `\\s`, so it ran past the end of the line and took the
    next prop's name with it — `groups: ['items\\n  groups']`. A parser that silently absorbs the following
    line reports a relation nobody wrote."""
    import demo_copy_qa as d                                        # noqa: E402
    for name, rel in d.supersedes().items():
        for provider, supplied in rel.items():
            assert "\n" not in provider and all("\n" not in p for p in supplied), (name, provider, supplied)
            assert all(p == p.strip() and " " not in p for p in supplied), (name, supplied)


def test_a_superseded_prop_is_still_demo_copy_when_the_provider_is_absent():
    """The relation must not switch the check OFF. A board that gives neither `groups` nor `items` still
    prints PortRail's English demo labels, and that is the error this check exists for."""
    import validate as v                                            # noqa: E402
    lib = v._demo_copy_library()
    assert "items" in lib.get("PortRail", {}), (
        "PortRail's `items` stopped being demo copy — the supersedes relation was applied to the LIBRARY "
        "instead of to one beat's props, which turns the check off for every board")
