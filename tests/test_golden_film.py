"""Golden-film regression anchor. `docs/golden-film/storyboard.json` was produced end-to-end by the real
agent pipeline (content-planner -> design-director template contest -> scriptwriter -> render), verified from
rendered pixels, and hand-checked by the design-critic. This test locks the invariants that made it a valid,
premium cinematic film so a future change to validate/build_props/the toolkit can't silently break the
reference: it must still pass the pre-render gate with ZERO errors, build coherent props, and keep the
structural properties (a recorded template contest, only-known kinds, no crowding, one cold-open terminal,
the caret bookend). If a deliberate change to the engine changes the contract, update the fixture + this test
together (and re-render to confirm it still looks right — bytes passing is necessary, not sufficient)."""
import json
import os
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
import render_remotion as rr  # noqa: E402
import validate as v  # noqa: E402

_FIXTURE = os.path.join(_SKILL, "docs", "golden-film", "storyboard.json")


@pytest.fixture
def board():
    with open(_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def test_golden_film_present_and_wellformed(board):
    assert board["meta"]["renderer"] == "remotion"
    assert len(board["slides"]) == 5, "the reference film is 5 beats"
    assert all(s["type"] == "cinematic" for s in board["slides"])


def test_golden_film_validates_with_zero_errors(board):
    r = v.evaluate(board, "/tmp/nowhere", pre_tts=True)
    assert r["errors"] == [], "the golden film must still pass the pre-render gate cleanly:\n" + "\n".join(r["errors"])


def test_golden_film_has_no_crowding(board):
    # the reference was authored crowding-clean (textblock/callout for small nodes, z-staggered) — a change to
    # the footprint model that starts flagging it is a regression in the guard, not the film.
    r = v.evaluate(board, "/tmp/nowhere", pre_tts=True)
    assert not any("overlap on the same depth plane" in w for w in r["warnings"]), \
        "the golden film must stay collision-free"


def test_golden_film_records_the_template_contest(board):
    m = board["meta"]
    tc = m.get("template_contest")
    assert tc and len(tc["candidates"]) >= 2, "a bold-audacity film must record a >=2-way contest"
    assert tc["winner"] == m["cinematic_template"], "the contest winner must be the chosen template"
    assert m["cinematic_template"] in tc["candidates"]


def test_golden_film_uses_the_toolkit_with_discipline(board):
    kinds = [e.get("kind") for s in board["slides"] for e in s.get("stage", {}).get("elements", [])]
    assert kinds.count("terminal") == 1, "the terminal is a cold-open trigger — exactly once, not every beat"
    assert "metaphor" in kinds and "card" in kinds and "hud" in kinds and "connector" in kinds, \
        "the reference exercises the differentiator components"
    archetypes = [s.get("archetype") for s in board["slides"]]
    assert len(set(archetypes)) >= 3, "archetype variety (not one card reframed)"
    # the caret bookend: the film opens on a terminal and the last scene carries the returning caret callout.
    last = board["slides"][-1]["stage"]["elements"]
    assert any(e.get("kind") == "callout" for e in last), "the closer returns the command-surface caret"


def test_golden_film_builds_coherent_props(tmp_path, board):
    (tmp_path / "theme.css").write_text(":root{--accent:#7C5CFF;}")
    props = rr.build_props(board, str(tmp_path))
    assert props["width"] == 1920 and props["height"] == 1080
    assert len(props["scenes"]) == 5
    # every scene keeps a non-empty staged set the camera can move through
    assert all(sc["stage"]["elements"] for sc in props["scenes"])
