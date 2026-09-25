"""THE FILM'S BOARD — the one seam that claims a PLACE rather than a relationship.

Every other word in this vocabulary says something about how two beats relate. None of them can say "this is
where we were", so a film that reaches back to an earlier idea had no way to show it. `relation: 'return'`
plus `returns_to` says it, and the direction it pans is derived from where the two beats sit.

The geometry here is not a matter of taste and the tests are written to hold that line. A first build made
the DISTANCE mean something — reach back five cells, travel further than two — and rendering it showed why
that is impossible: two full-frame pictures offset by V leave a strip exactly |V| wide that neither covers,
measured at left-edge luminance 9.5 against a centre of 74.6. A hard dark band sweeping across the frame is
a curtain, not a camera. `slide`/`push` escape it only because their separation is exactly one frame, so the
two tile. So the travel is a UNIT step along ONE axis, and the last test measures that it really does tile.
"""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import film_board as fb          # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _b(*rels):
    """A board from a list of relations; a tuple is ('return', returns_to)."""
    out = []
    for r in rels:
        if isinstance(r, tuple):
            out.append({"relation": "return", "returns_to": r[1]})
        else:
            out.append({"relation": r})
    return out


# ── the board itself ───────────────────────────────────────────────────────────────────────────────────
def test_a_film_with_no_relations_is_one_unbroken_row():
    """Most boards never set `relation`, and the layout has to be a true picture of that film rather than a
    refusal: one argument, one row."""
    assert fb.positions([{} for _ in range(4)]) == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_a_chapter_break_starts_a_new_row_and_a_step_stays_on_it():
    assert fb.positions(_b("", "continuation", "new-topic", "continuation", "new-topic")) == [
        (0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]


def test_a_returning_beat_takes_the_cell_it_returns_to():
    """It IS that place. Landing it in a neighbouring cell would make a second return to the same beat
    travel a different way than the first, which is the one thing a map must not do."""
    pos = fb.positions(_b("", "continuation", "new-topic", "continuation", ("return", 1)))
    assert pos[4] == pos[0] == (0, 0), pos


# ── what it refuses, and what it must not ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name,board,expect", [
    ("a forward reference", _b("", ("return", 5)), "earlier beat"),
    ("a return to itself", _b("", ("return", 2)), "earlier beat"),
    ("no target named", [{}, {"relation": "return"}], "no `returns_to`"),
    ("returns_to on an ordinary beat", [{}, {"relation": "continuation", "returns_to": 1}], "only means"),
    ("a boolean where a number goes", [{}, {"relation": "return", "returns_to": True}], "beat NUMBER"),
    ("a return to the cell we are in", _b("", "continuation", ("return", 2)), "already in"),
])
def test_it_refuses_a_return_that_claims_nothing(name, board, expect):
    got = fb.refusals(board)
    assert got, "%s was accepted — it would render as a quiet no-op" % name
    assert expect in got[0][1], (name, got)


def test_a_real_return_is_accepted_and_pans_toward_the_place():
    """The other side of every refusal above. A rule that only ever says no is a rule nobody can use."""
    board = _b("", "continuation", "new-topic", "continuation", ("return", 1))
    assert not fb.refusals(board)
    tv = fb.travels(board)
    assert set(tv) == {4}, tv
    # beat 1 sits at (0,0); beat 4 sits at (1,1). The place is LEFT, so the content pans RIGHT.
    assert tv[4] == (1, 0), tv


def test_a_reach_back_through_chapters_alone_pans_vertically():
    board = _b("", "new-topic", "new-topic", ("return", 1))
    assert fb.travels(board)[3] == (0, 1), fb.travels(board)


def test_the_travel_is_always_a_unit_step_along_one_axis():
    """The invariant the render depends on: anything else opens a band that nothing covers. Probed over a
    spread of boards rather than the one that motivated it."""
    boards = [
        _b("", "continuation", "continuation", "continuation", ("return", 1)),
        _b("", "new-topic", "continuation", "new-topic", "continuation", ("return", 2)),
        _b("", "new-topic", "new-topic", "new-topic", ("return", 1)),
        _b("", "continuation", "new-topic", ("return", 2)),
    ]
    for board in boards:
        for i, (dx, dy) in fb.travels(board).items():
            assert {abs(dx), abs(dy)} == {0, 1}, (
                "beat %d pans (%s, %s) — a diagonal or a fraction cannot tile, so a strip of the frame is "
                "covered by neither beat" % (i + 1, dx, dy))


# ── it reaches the renderer ────────────────────────────────────────────────────────────────────────────
def test_only_a_real_return_emits_the_seam():
    import render_remotion as rr
    assert rr.seam_type("return") == "return", "the renderer does not know the word"
    assert rr._transition_in({"relation": "return", "returns_to": 1}) is None, (
        "a return emitted a seam with no travel — the board is what decides, not the slide")
    assert rr._transition_in({"relation": "continuation"}, None) is None
    got = rr._transition_in({"relation": "return", "returns_to": 1}, (1, 0))
    assert got == {"type": "return", "dx": 1.0, "dy": 0.0}, got


# ── and it tiles, measured on the render ───────────────────────────────────────────────────────────────
_PROBE = [
    {"shot": "TermTable", "durF": 60, "props": {"kicker": "ONE", "rows": [["a", "1"], ["b", "2"]]}},
    {"shot": "MadeOf", "durF": 60, "props": {"whole": "TWO"}},
    {"shot": "TermTable", "durF": 60, "props": {"kicker": "BACK", "rows": [["a", "1"], ["b", "2"]]}},
]


def _still(tmp_path, transition_in, name, frame=102):
    scenes = json.loads(json.dumps(_PROBE))
    scenes[2]["transitionIn"] = transition_in
    pf = str(tmp_path / (name + ".json"))
    json.dump({"scenes": scenes, "dna": "product", "captions": False, "camera": 0},
              open(pf, "w", encoding="utf-8"))
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=%d" % frame,
                        "--gl=angle", "--timeout=150000", "--scale=0.5", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-500:]
    return png


@needs_toolchain
def test_the_return_tiles_exactly_as_a_push_does_and_uncovers_nothing(tmp_path):
    """THE ONE THAT MATTERS, and the one the first build failed.

    `push` is Remotion's own slide: two full frames passing each other with no gap, which is why nothing is
    ever uncovered by it. If a return in the matching direction draws the same picture, it tiles too. This
    compares the rendered frames rather than reasoning about the transforms, because the first build's
    transforms looked right and the frame had a black band a third of the way across it.
    """
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    a = np.asarray(Image.open(_still(tmp_path, {"type": "return", "dx": 1, "dy": 0}, "ret"))
                   .convert("L"), dtype=float)
    b = np.asarray(Image.open(_still(tmp_path, {"type": "push", "direction": "from-left"}, "push"))
                   .convert("L"), dtype=float)
    assert a.shape == b.shape
    diff = float(np.abs(a - b).mean())
    assert diff < 2.0, (
        "the return no longer draws what a push draws (mean |difference| %.2f grey levels). Either it has "
        "stopped tiling — which opens a strip of frame that neither beat covers — or its direction has "
        "flipped." % diff)
