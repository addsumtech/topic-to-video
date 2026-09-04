"""The film FINISH — grain, corner falloff, a key direction — proved present, routed, and inert where it
must be inert.

WHY IT EXISTS. Side by side with the four reference launch films, this tier's frames read as web pages:
perfectly flat fills, no optical response. All four references carry grain, corner falloff and a lit
direction. One layer (runtime/finish.tsx) gives every one of 152 registers that floor at once.

THE ROUTING IS THE PART A TEST HAS TO HOLD. The finish was first added to the named presets only — and a
real film's `meta.design_dna` is an OBJECT the shot-director writes, which coerceDna spreads over NEUTRAL.
NEUTRAL had no finish, so the finish would have shipped on preset-string films (mostly tests) and never on
an actual delivery. The fix routes the default through NEUTRAL; these tests pin that routing, the opt-out,
and the two hard constraints: determinism and nothing at all on the un-themed path.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(ROOT, "remotion", "src", "runtime")


def _src(name):
    return open(os.path.join(RUNTIME, name), encoding="utf-8").read()


def test_every_preset_carries_a_finish_and_neutral_carries_the_default():
    """NEUTRAL's is the load-bearing one: coerceDna spreads every authored partial DNA over it, so deleting
    it silently unships the finish from every real film while every preset-string demo keeps it."""
    dna = _src("dna.tsx")
    blocks = re.findall(r"export const (\w+_DNA): DesignDNA = \{(.*?)\n\};", dna, re.S)
    assert len(blocks) >= 8, "preset blocks not found"
    missing = [n for n, body in blocks if "finish:" not in body]
    assert not missing, "presets with no finish (real films inherit NEUTRAL's): %s" % missing


def test_the_grain_seed_is_fixed_and_nothing_in_the_layer_is_time_dependent():
    """A print characteristic must be the same on frame 1 and frame 3000 and on every render — the
    determinism harness hashes real renders, and a drifting seed is also how a light ARC sneaks back in
    (the automatic arc was built and withdrawn; this layer must stay static)."""
    f = _src("finish.tsx")
    assert re.search(r"seed='\d+'", f), "the turbulence seed is not a fixed literal"
    for banned in ("useCurrentFrame", "Math.random", "Date.now"):
        assert banned not in f, "%s inside the finish layer — no longer static" % banned


def test_unthemed_films_get_nothing_at_all():
    """The null-DNA rule: no theming machinery may alter the original look."""
    f = _src("finish.tsx")
    assert re.search(r"if \(!dna \|\| !f\) return null", f), (
        "the finish no longer returns null for an un-themed film")


def test_a_film_can_opt_out_with_none():
    f = _src("finish.tsx")
    assert "raw === 'none' ? null : raw" in f, "the 'none' opt-out is gone"


def test_the_layer_is_mounted_below_the_caption_and_above_the_motif():
    """Grain over burned type reads as compression, and the caption's contrast maths assume the ground it
    measured — so order matters, and the order is only visible in Film.tsx's JSX."""
    film = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    i_motif = film.index("<FilmMotifLayer")
    i_finish = film.index("<FilmFinishLayer")
    i_caption = film.index("<CaptionTrack")
    assert i_motif < i_finish < i_caption, "layer order broke: motif < finish < caption required"
