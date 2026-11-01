"""The CJK display VOICE a Chinese film's titles are set in (meta.cjk_display; runtime/cjkVoice.ts).

WHY. Two CJK display faces were bundled (assets/fonts/TTV-SC-SUBSET-NOTE.txt) and nothing could reach them: every DNA
stack names a Latin face, then Noto, so a Chinese title falls to Noto whatever the film is. The choice is the film's
— launch/product voice, warm learning voice, or the Noto it had — so validate asks for it on a CJK remotion film and
the renderer puts the chosen face AFTER the stack's Latin face and BEFORE Noto: Latin stays in its face, Han takes the
voice, and a character the voice lacks falls back to Noto.
"""
import pytest

import validate


def test_the_voice_goes_after_the_latin_face_and_before_noto():
    import _tsprobe
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    out = _tsprobe.run_ts("import {withCjkDisplay} from %s;" % _tsprobe.mod("cjkVoice.ts"),
                          "const s = 'Inter, \"Noto Sans SC\", \"PingFang SC\", system-ui, sans-serif';"
                          "out.d = withCjkDisplay(s, 'TTV Display'); out.k = withCjkDisplay(s, 'TTV Kai');"
                          "out.n = withCjkDisplay(s, 'noto'); out.u = withCjkDisplay(s, undefined);"
                          "out.twice = withCjkDisplay(withCjkDisplay(s, 'TTV Kai'), 'TTV Kai');"
                          "out.noNoto = withCjkDisplay('Inter, system-ui', 'TTV Kai');")
    assert out["d"] == 'Inter, "TTV Display", "Noto Sans SC", "PingFang SC", system-ui, sans-serif'
    assert out["k"].startswith('Inter, "TTV Kai", "Noto Sans SC"')
    assert out["n"] == out["u"] == 'Inter, "Noto Sans SC", "PingFang SC", system-ui, sans-serif'
    assert out["twice"].count("TTV Kai") == 1
    assert out["noNoto"] == 'Inter, "TTV Kai", system-ui'


def _meta(**kw):
    m = {"renderer": "remotion", "language": "zh", "design_dna": "product"}
    m.update(kw)
    return m


def test_a_cjk_film_is_asked_for_its_voice_and_an_unknown_one_is_refused():
    errors, warnings = [], []
    validate._check_cjk_voice(_meta(), errors, warnings)
    assert errors == [] and any("cjk_display" in w for w in warnings), warnings
    for ok in ("noto", "TTV Display", "TTV Kai"):
        errors, warnings = [], []
        validate._check_cjk_voice(_meta(cjk_display=ok), errors, warnings)
        assert errors == [] and warnings == [], (ok, errors, warnings)
    errors, warnings = [], []
    validate._check_cjk_voice(_meta(cjk_display="Smiley Sans"), errors, warnings)
    assert any("cjk_display" in e for e in errors), errors
    errors, warnings = [], []
    validate._check_cjk_voice(_meta(language="en"), errors, warnings)
    assert errors == [] and warnings == []


def test_the_render_props_carry_the_voice(tmp_path):
    import shutil
    import subprocess
    import render_remotion as rr
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg needed for the audio stub")
    (tmp_path / "audio").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3",
                    str(tmp_path / "audio" / "01.wav")], check=True)
    board = {"meta": _meta(cjk_display="TTV Kai"), "slides": [{"index": 1, "shot": "TermTable", "duration": 3.0,
             "narration": "x", "caption": "x", "audio": "audio/01.wav", "shot_props": {"rows": [["a", "1"]]}}]}
    assert rr.film_props(str(tmp_path), board)[0]["cjkDisplay"] == "TTV Kai"
    board["meta"]["cjk_display"] = "noto"
    assert "cjkDisplay" not in rr.film_props(str(tmp_path), board)[0]


def test_the_python_and_the_runtime_name_the_same_voices():
    import os
    import re
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "runtime",
                            "cjkVoice.ts"), encoding="utf-8").read()
    ts = re.findall(r"'([^']+)'", re.search(r"CJK_VOICES = \[(.*?)\]", src).group(1))
    assert tuple(ts) == validate.CJK_VOICES
