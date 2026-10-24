"""A platform-safe (9:16) film's MARGIN is the beat itself: a blurred, dimmed echo of the register behind its 0.8 frame.

The `social` profile draws every register in a frame scaled by 0.8 with feathered edges, so on 9:16 every beat was a
panel on the film's ground ("every beat becomes a panel on black" — a 9:16 launch benchmark's first finding). Film.tsx
SafeEcho draws the same register again behind it, scaled to cover the canvas about the frame's centre, blurred and (on
a dark beat) dimmed. It must be invisible to every instrument: `data-echo` + `aria-hidden` (the text gates' echo rule),
`data-echo="margin"` (the seams' anchor lookup), no optic, no voice, and nothing at all on a film without the profile.

Measured by mutation (E7) on OdometerRoll at 9:16, frame 45, with the type-collision audit armed: with the echo's
`data-echo` / `aria-hidden` removed the audit reported the echo's type overlapping the frame's own; marked, it reports
what the film reports with the echo switched off.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
FILM = open(os.path.join(_REM, "src", "Film.tsx"), encoding="utf-8").read()
SEAMS = open(os.path.join(_REM, "src", "seams.tsx"), encoding="utf-8").read()
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")) or not shutil.which("npx"),
                                     reason="needs the remotion toolchain")


def test_the_echo_declares_itself_to_every_instrument():
    body = FILM.split("const SafeEcho: React.FC")[1].split("\n};")[0]
    assert 'aria-hidden data-echo="margin"' in body, "the text gates skip [data-echo] (+ aria-hidden by their rule)"
    assert "React.useContext(SeamCopyContext)" in body and "return null" in body, "not drawn inside a container copy"
    assert "<SeamCopyContext.Provider value={true}>" in body, "a beat voice inside it must not play"
    assert "BeatOptic" not in body, "an echo anchors no optic"


def test_only_a_platform_safe_film_mounts_it():
    seq = FILM.split("const beatSeq = ")[1].split("const runSeq")[0]
    assert "{regFrame && safeEcho ? (" in seq, "the echo must be gated on the safe profile"
    assert "safeEcho = true" in FILM


def test_the_seams_never_measure_the_echo_s_anchors():
    assert "closest('[data-echo=\"margin\"]')" in SEAMS
    # every anchor lookup goes through the echo-blind helper
    assert not re.search(r"querySelector\(`\[data-carry=", SEAMS), "a lookup that can find the echo's copy first"


def _still(tmp_path, name, extra):
    props = dict({"scenes": [{"shot": "OdometerRoll", "durF": 60, "props": {}, "caption": "每个数字都对得回原文那一句。"}],
                  "dna": "product", "captions": True, "camera": 0, "cameraBed": False, "safe": "social",
                  "aspect": "9:16"}, **extra)
    pf = str(tmp_path / (name + ".json"))
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=45", "--gl=angle",
                        "--timeout=150000", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r


def _payload(r, tag):
    blob = (r.stdout or "") + (r.stderr or "")
    if tag not in blob:
        assert r.returncode == 0, "the still measured nothing: " + blob[-600:]
        return []
    found, _ = json.JSONDecoder().raw_decode(blob.split(tag, 1)[1])
    return found


@needs_toolchain
def test_the_type_audits_read_the_film_the_same_with_and_without_the_echo(tmp_path):
    for flag, tag in (("typeCollisions", "TYPE-COLLISIONS "), ("textSafe", "TEXT-SAFE-VIOLATIONS ")):
        on = _still(tmp_path, flag + "_on", {flag: True})
        off = _still(tmp_path, flag + "_off", {flag: True, "safeEcho": False})
        a, b = _payload(on, tag), _payload(off, tag)
        assert [x.get("text") for x in a] == [x.get("text") for x in b], (flag, a, b)


def test_a_board_can_refuse_the_echo_for_its_render_cost():
    rr = open(os.path.join(_ROOT, "scripts", "render_remotion.py"), encoding="utf-8").read()
    body = rr.split("zone = safe_zone(meta, aspect)")[1].split("theme = meta.get")[0]
    assert 'if meta.get("safe_echo") is False:' in body and 'props["safeEcho"] = False' in body
