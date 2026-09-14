"""A film's DNA written the SHORT way must be checked exactly like the same film written the long way.

THE EVIDENCE. `coerceDna` resolves a preset NAME at render, so `meta.design_dna: "product"` is a fully
themed film — every shot inherits that DNA. `validate.py` asked `isinstance(design_dna, dict)`, so it judged
such a film un-themed, and that cost twice over. Isolated on two boards identical but for that one key:

  * it WARNED "remotion: NO Design DNA … every shot renders its ORIGINAL hardcoded identity" about a film
    whose every shot does inherit one — a gate crying wolf at a correct board; and
  * the half that is silent and worse: `_themed` gates the DNA-coverage lints, so the same film skipped the
    `theme_cues` check (0 findings against 1 for the identical board written with `shot_template`) and the
    un-migrated-register lint. A themed film opted out of every themed-only check by writing its DNA the
    shorter way.

That is the shape `slide-maker` already recorded as "an opt-in gate is not a detector": the check exists,
and the deck that most needs it is the one it cannot see.

SO THE TEST IS PARITY, not a list of expected strings. Asserting "no NO-Design-DNA warning for a string" can
be satisfied by deleting the warning; asserting the two WRITINGS agree cannot, because the long form is the
one every other test already pins.
"""
import copy

import validate as v

_BEAT = {"index": 1, "shot": "TermLog",
         "shot_props": {"cmd": "x", "lines": [{"text": "a", "kind": "ok"}]},
         "narration": "one line.",
         "shot_fit": {"verdict": "fit", "why": "probe", "form": "a sweep log"},
         "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t", "theme_cues": ["c"]}}


def _findings(meta_extra, beat_edit=None):
    meta = {"renderer": "remotion", "aspect": "16:9", "fps": 30,
            "form_vocabulary": [{"form": "a sweep log", "carries": "counts"}],
            "idiom_world": ["developer-tooling"]}
    meta.update(meta_extra)
    beat = copy.deepcopy(_BEAT)
    if beat_edit:
        beat_edit(beat)
    errors, warnings = [], []
    v._check_remotion(meta, [beat], errors, warnings)
    return errors, warnings


def _drop_cues(beat):
    beat["shot_adaptation"].pop("theme_cues")


def test_a_preset_NAME_is_not_reported_as_having_no_design_system():
    _errors, warnings = _findings({"design_dna": "product"})
    assert not [w for w in warnings if "NO Design DNA" in w], (
        "a themed film was told it has none — the runtime resolves this name into the whole design system: %r"
        % (warnings,))


def test_a_preset_NAME_is_held_to_the_SAME_themed_checks_as_a_template():
    """The silent half. Two boards that differ only in how the same DNA is named must produce the same
    findings — otherwise the shorter spelling is an opt-out from every themed-only gate."""
    _e1, w_string = _findings({"design_dna": "product"}, _drop_cues)
    _e2, w_template = _findings({"shot_template": "product-demo"}, _drop_cues)
    cues_string = [w for w in w_string if "theme_cues" in w]
    cues_template = [w for w in w_template if "theme_cues" in w]
    assert cues_template, "the long-form board stopped being checked — this test's control is gone"
    assert len(cues_string) == len(cues_template), (
        "the string form skipped the themed lint: %d finding(s) against %d for the same film written long"
        % (len(cues_string), len(cues_template)))


def test_an_UNKNOWN_name_is_still_an_error_and_still_un_themed():
    """The fix must not make any string themed. A name the runtime would throw on is not a design system,
    and a film carrying one has to hear both things."""
    errors, warnings = _findings({"design_dna": "prodcut"})
    assert [e for e in errors if "not a known preset" in e], errors
    assert [w for w in warnings if "NO Design DNA" in w], (
        "a misspelt preset was treated as a themed film: %r" % (warnings,))


def test_a_film_with_NO_dna_at_all_still_hears_about_it():
    """The warning has to survive: it is the one that catches a film assembled with no visual system."""
    _errors, warnings = _findings({})
    assert [w for w in warnings if "NO Design DNA" in w], warnings
