"""Every register's PROVENANCE must be a world a film is allowed to declare.

THE CATCH-22 THIS ENDS, found by writing a real film that used `PortRail`. `validate._idiom_world` does two
things: it REFUSES a `meta.idiom_world` entry that is not in `shot_director.IDIOM_WORLDS`, and it ERRORS on a
beat whose register's provenance is not in the film's declared list. Seven registers carried a provenance
that was not a world at all — `product-demo`, `product-hardware`, `paper-craft` — so a film using one was
told it draws from an undeclared world AND that the world it would have to declare is unknown. There was no
board that could pass. The only escape was to stop using the register, which is how a gate gets switched off
rather than satisfied.

`product-demo` is the give-away: it is the name of a TEMPLATE, one of the six seed directions, written into
the provenance table as though it were a vocabulary. The five registers carrying it all speak a product
interface's own language and now say `product-ui`; `PortRail`'s connector rail is hardware (`industrial`)
and `PaperSlot`'s fed sheet is `craft-handmade`.

A LIST CANNOT BE CHECKED BY RESTATING IT. The tests below derive both sides from the module, so a world
added to `IDIOM_WORLDS` or a register registered with a new tag is covered the day it lands.
"""
import os
import re

import shot_director as sd
import validate as v


def test_every_provenance_is_a_declarable_world():
    known = set(sd.IDIOM_WORLDS)
    bad = {reg: world for reg, world in sd.PROVENANCE.items() if world not in known}
    assert not bad, (
        "these registers carry a provenance no film may declare, so every board using one is an error with "
        "no fix: %s. Known worlds: %s" % (bad, sorted(known)))


def test_a_film_can_actually_declare_every_world_the_library_uses():
    """The other half of the same loop, checked from the validator's side rather than the table's: build a
    board that declares every world in use and assert it is accepted."""
    worlds = sorted(set(sd.PROVENANCE.values()))
    errors, warnings = [], []
    v._idiom_world({"idiom_world": worlds}, [], errors, warnings)
    assert not [e for e in errors if "unknown world" in e], (
        "a film declaring exactly the worlds its library uses was refused: %r" % (errors,))


def test_a_register_from_a_declared_world_is_accepted_and_one_from_elsewhere_is_not():
    """The gate must still bite. Picking the registers from the table keeps this honest if either moves."""
    by_world = {}
    for reg, world in sd.PROVENANCE.items():
        by_world.setdefault(world, []).append(reg)
    pair = [(w, regs[0]) for w, regs in sorted(by_world.items()) if regs]
    assert len(pair) >= 2, "the library speaks fewer than two worlds — this test has nothing to contrast"
    (w_a, reg_a), (w_b, reg_b) = pair[0], pair[1]

    errors, warnings = [], []
    v._idiom_world({"idiom_world": [w_a]}, [{"index": 0, "shot": reg_a}], errors, warnings)
    assert not errors, "a beat from the film's OWN declared world was refused: %r" % (errors,)

    errors, warnings = [], []
    v._idiom_world({"idiom_world": [w_a]}, [{"index": 0, "shot": reg_b}], errors, warnings)
    assert [e for e in errors if w_b in e], (
        "a beat from an undeclared world (%s) passed — the gate is not biting: %r" % (w_b, errors))


def test_every_register_in_the_library_carries_a_provenance():
    """An untagged register is silently exempt from the gate, which is how the check would decay as the
    library grows. `validate` reports it as a finding about the LIBRARY; this catches it one step earlier."""
    shots = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(v.__file__))),
                         "remotion", "src", "shots")
    ids = {f[:-4] for f in os.listdir(shots) if f.endswith(".tsx")}
    missing = sorted(ids - set(sd.PROVENANCE))
    assert not missing, (
        "%d register(s) carry no provenance and are exempt from the idiom-world gate by accident: %s"
        % (len(missing), ", ".join(missing[:10])))


def test_the_worlds_are_not_restated_in_validate():
    """Two copies of one list is how the caption band became four disagreeing numbers in this repo."""
    src = open(v.__file__, encoding="utf-8").read()
    fn = src.split("def _idiom_world(")[1].split("\ndef ")[0]
    body = "\n".join(l.split("#")[0] for l in fn.splitlines())
    for world in sd.IDIOM_WORLDS:
        assert "'%s'" % world not in body and '"%s"' % world not in body, (
            "validate.py hardcodes the world %r instead of reading shot_director.IDIOM_WORLDS" % world)
    assert re.search(r"IDIOM_WORLDS", fn), "it no longer reads the list from the one place that defines it"
