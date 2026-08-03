"""Design-brain v1 backstops: the per-beat ARCHETYPE axis (references/shot-archetypes.md) is the selection
mechanism that gives every cinematic beat a bespoke, topic-driven design instead of the one glass panel.
The gate makes the catalogue enforceable ('does its absence make a noise?'): a beat with no archetype warns,
an unknown one errors, and a film that reuses one archetype or lacks a signature beat is flagged."""
import os

import validate as v

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _cine(**kw):
    s = {"type": "cinematic", "stage": {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]},
         "shots": [{"type": "HERO", "target": "a"}]}
    s.update(kw)
    return s


# ── catalogue + wiring coherence (the backstops that keep the catalogue reachable) ──
def test_every_archetype_is_documented():
    doc = _read("references", "shot-archetypes.md")
    for a in v._ARCHETYPES:
        assert a in doc, "archetype %r must be documented in shot-archetypes.md" % a


def test_director_and_skill_point_to_the_catalog():
    assert "shot-archetypes.md" in _read("agents", "design-director.md")
    assert "shot-archetypes.md" in _read("SKILL.md")


# ── per-scene gate ──
def test_missing_archetype_warns_not_errors():
    errs, warns = [], []
    v._cinematic_fields(_cine(), {"fps": 30}, "/tmp", "s1", errs, warns)
    assert any("archetype" in w for w in warns) and not errs


def test_unknown_archetype_errors():
    errs, warns = [], []
    v._cinematic_fields(_cine(archetype="bogus"), {"fps": 30}, "/tmp", "s1", errs, warns)
    assert any("unknown archetype" in e for e in errs)


def test_known_archetype_is_clean():
    errs, warns = [], []
    v._cinematic_fields(_cine(archetype="process-flow"), {"fps": 30}, "/tmp", "s1", errs, warns)
    assert not any("archetype" in w for w in warns) and not errs


# ── cross-scene design-variety lint (now ERROR-BLOCKS, not warns — the 3-arg signature reflects that) ──
def test_variety_flags_one_archetype_dominating():
    errs, warns = [], []
    v._design_variety_lint([{"index": i, "archetype": "metric-wall"} for i in range(1, 6)], errs, warns)
    assert any(">45%" in e for e in errs) and any("distinct" in e for e in errs), "same-look film must BLOCK"


def test_variety_flags_no_signature_beat():
    errs, warns = [], []
    slides = [{"index": 1, "archetype": "metric-wall"}, {"index": 2, "archetype": "process-flow"},
              {"index": 3, "archetype": "comparison-split"}, {"index": 4, "archetype": "system-map"}]
    v._design_variety_lint(slides, errs, warns)
    assert any("signature/metaphor" in e for e in errs)


def test_variety_flags_back_to_back_repeat():
    errs, warns = [], []
    v._design_variety_lint([{"index": 1, "archetype": "metric-wall"}, {"index": 2, "archetype": "metric-wall"}], errs, warns)
    assert any("back-to-back" in e for e in errs)


def test_varied_film_with_a_signature_beat_is_clean():
    errs, warns = [], []
    slides = [{"index": 1, "archetype": "hero-on-void"}, {"index": 2, "archetype": "metaphor-mechanic"},
              {"index": 3, "archetype": "process-flow"}, {"index": 4, "archetype": "metric-wall"},
              {"index": 5, "archetype": "data-materializes"}]
    v._design_variety_lint(slides, errs, warns)
    assert errs == [] and warns == []
