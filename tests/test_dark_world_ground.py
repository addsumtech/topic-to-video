"""A @dark-world register's ground row is the night it keeps, not the film's paper.

`measure_ground_luma.py` measured every register under ONE dark probe, where "paints the film's ground" and
"paints the film's ground while it is dark" (runtime/light.tsx `darkGround`) look the same. So the fourteen
@dark-world registers were recorded `bg`; on a light film the caption was inked for paper on a night frame, the
seam guard read paper, and shot_proof had to refuse them. A second, LIGHT probe tells the two apart."""
import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import measure_ground_luma as gl  # noqa: E402
import seam_plan  # noqa: E402
import shot_proof as sp  # noqa: E402

KEY = gl.light_key_y()
LIGHT_DNA = {"id": "paper-film", "bg": "#f2efe9", "fg": "#16171a", "dim": "#66645f", "accent": "#d4481a",
             "accent2": "#2c6a8a", "onAccent": "#ffffff", "surface": "#fbfaf7", "surfaceBorder": "#d6d1c7",
             "line": "#dfdad1", "decoration": []}
DARK_DNA = dict(LIGHT_DNA, bg="#0b0d12", fg="#f4f4f4")


def _dark_world():
    """Every register that DECLARES @dark-world, read with ink_contrast_qa's own reader (the gate that holds the
    declaration to the pixels), so this census and that gate cannot disagree about who is one."""
    import ink_contrast_qa as icq
    names = [os.path.basename(f)[:-4] for f in glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))]
    return sorted(n for n in names if icq.dark_world_reason(n))


def test_a_bg_ground_that_stays_dark_under_the_light_probe_is_its_own_night():
    assert gl.classify_world("bg", (0.005, "#0a101c"), KEY) == "#0a101c"


def test_a_bg_ground_that_follows_the_light_probe_stays_bg():
    assert gl.classify_world("bg", (0.88, "#f2f2f2"), KEY) == "bg"


def test_the_light_probe_only_ever_rewrites_a_bg_row():
    """No other token is what `darkGround` substitutes, so no other row may move: an accent flood that is dark on
    a light film is OBEYING the film (its accents were exposed for paper)."""
    for tok in (["accent", "accent2"], "surface", None):
        assert gl.classify_world(tok, (0.01, "#101010"), KEY) == tok
    assert gl.classify_world("bg", None, KEY) == "bg"


def test_the_boundary_is_the_runtimes_own():
    src = open(os.path.join(_ROOT, "remotion", "src", "runtime", "light.tsx"), encoding="utf-8").read()
    assert ("export const LIGHT_KEY_Y = %s;" % ("%g" % KEY)) in src


def test_every_dark_world_register_is_found():
    """The census below must not pass vacuously: the library declares fourteen."""
    assert len(_dark_world()) >= 14, _dark_world()


def test_a_dark_world_caption_on_a_light_film_is_inked_light():
    """The caption ink Film.tsx picks (mirrored by shot_proof) for each @dark-world register on a LIGHT film is the
    LIGHT ink. On the old `bg` rows every one of them resolved to the film's paper and was inked dark."""
    light_ink = seam_plan._rel_lum(sp.CAPTION_INKS[1])
    wrong = {}
    for shot in _dark_world():
        y = seam_plan.dna_ground_y(shot, LIGHT_DNA)
        if y is None or y >= KEY or sp._caption_ink_y(y) != light_ink:
            wrong[shot] = y
    assert not wrong, "inked for paper on a frame that is night: %r" % wrong


def test_a_dark_world_ground_on_a_dark_film_is_still_dark():
    """...and the row did not break the case it used to get right: on a dark film the caption stays light and the
    resolved ground is within the seam guard's tolerance of the film's own."""
    film = seam_plan._rel_lum(DARK_DNA["bg"])
    for shot in _dark_world():
        y = seam_plan.dna_ground_y(shot, DARK_DNA)
        assert y is not None and y < KEY, (shot, y)
        assert seam_plan.ground_gap(y, film) < 0.34, (shot, y, film)
