"""The intro/outro veil is the EDGE BEAT's ground, read from its luminance when it declares none (Film.tsx veilFor).

WorkBuddy and ANC (2026-11-12): a light DNA, a dark first (and last) beat that paints its own ground; the veil was the
DNA's near-white, so the films faded in from white (and WorkBuddy out to white). flash_qa.edge_washes measures it on the
delivered file; this pins the cause."""
import os

FILM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "Film.tsx")


def test_the_veil_follows_the_edge_beats_luminance():
    src = open(FILM, encoding="utf-8").read()
    body = src.split("const veilFor = ")[1].split("};")[0]
    assert "dnaGroundLum(sc.shot, sc.bgLum, activeDna)" in body
    assert "lum === 'dark' ? '#000000' : '#ffffff'" in body
    assert "const firstBg = veilFor(scenes[0], 'in');" in src
    assert "const lastBg = veilFor(scenes[scenes.length - 1], 'out');" in src
