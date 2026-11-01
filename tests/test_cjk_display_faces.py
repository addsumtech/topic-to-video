"""The two CJK DISPLAY faces (assets/fonts/TTV-SC-SUBSET-NOTE.txt): renamed OFL subsets, covering what Noto covers.

WHY. Noto Sans SC and Noto Serif SC were the only CJK faces, so every Chinese film's headlines had one of two voices;
published launch films set Chinese display type in a geometric oblique (得意黑). TTV Display (from Smiley Sans) and TTV
Kai (from LXGW WenKai Medium) are display faces; body text and captions stay on Noto.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
FACES = {"TTV Display": "TTVDisplaySC-Subset.ttf", "TTV Kai": "TTVKaiSC-Subset.ttf"}
RESERVED = ("Smiley", "得意黑", "LXGW", "霞鹜", "霞鶩", "落霞孤")

TTFont = pytest.importorskip("fontTools.ttLib").TTFont


def test_the_subsets_do_not_carry_the_reserved_font_names():
    """OFL condition 3: a Modified Version (a subset is one) may not use a Reserved Font Name. The copyright,
    manufacturer and designer fields keep the authors' names, as the licence requires."""
    for family, fname in FACES.items():
        names = TTFont(os.path.join(FONTS, fname), lazy=True)["name"].names
        bad = [(r.nameID, r.toUnicode()) for r in names
               if r.nameID in (1, 3, 4, 6, 16, 17, 18, 21, 22) and any(x in r.toUnicode() for x in RESERVED)]
        assert not bad, (fname, bad)
        fam = {r.toUnicode() for r in names if r.nameID == 1}
        assert family in fam, (fname, fam)


def test_every_gb2312_han_is_covered():
    han = [c for c in range(0x4E00, 0xA000) if len(chr(c).encode("gb2312", "ignore")) == 2]
    assert len(han) == 6763
    for fname in FACES.values():
        cmap = set(TTFont(os.path.join(FONTS, fname), lazy=True).getBestCmap())
        missing = [chr(c) for c in han if c not in cmap]
        assert not missing, (fname, "".join(missing[:20]))


def test_licences_ship_beside_them():
    for lic in ("OFL-SmileySans.txt", "OFL-LXGWWenKai.txt", "TTV-SC-SUBSET-NOTE.txt"):
        assert os.path.getsize(os.path.join(FONTS, lic)) > 1000, lic


def test_a_one_weight_face_is_a_static_file_registered_over_the_whole_range():
    """Registered at its own weight, a static display face is SYNTHESISED bold when a title asks 700-800."""
    ts = open(os.path.join(ROOT, "remotion", "src", "runtime", "fonts.ts"), encoding="utf-8").read()
    rows = re.findall(r"\{family: '([^']+)', file: '([^']+)'[^}]*oneWeight: true[^}]*\}", ts)
    assert {f for f, _ in rows} == set(FACES), rows
    for _f, fname in rows:
        assert "fvar" not in TTFont(os.path.join(FONTS, fname), lazy=True), fname
    assert "f.oneWeight ? '100 900' : f.weight" in ts


def test_cjk_latin_spacing_is_on_for_the_beats_and_not_for_the_caption(tmp_path):
    """`text-autospace` puts the thin gap between Han and Latin/digits (手机的GPS -> 手机的 GPS) that authors otherwise
    type by hand or forget (`normal`: the only value this Chrome accepts — `ideograph-alpha` was measured as refused). The caption is OUTSIDE `.dna-film`: its lines are broken by a canvas measure that knows
    nothing of the gap, so a caption under it could wrap a line the measure said fits."""
    film = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert re.search(r"\.dna-film \{ text-autospace: normal; \}", film), "no autospace on the beats"
    cap = film.index("<CaptionTrack")
    root = film.index('className="dna-film"')
    close = film.index("</AbsoluteFill>", film.index("</TransitionSeries>"))
    assert not (root < cap < close), "the caption sits inside .dna-film and would be autospaced"
    import json
    import shutil
    import subprocess
    import render_remotion as rr
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg needed for the audio stub")
    (tmp_path / "audio").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3",
                    str(tmp_path / "audio" / "01.wav")], check=True)
    board = {"meta": {"renderer": "remotion"}, "slides": [{"index": 1, "shot": "TermTable", "duration": 3.0,
             "narration": "x", "caption": "x", "audio": "audio/01.wav", "shot_props": {"rows": [["a", "1"]]}}]}
    assert rr.film_props(str(tmp_path), board)[0]["autospace"] is True
    board["meta"]["cjk_autospace"] = False
    assert rr.film_props(str(tmp_path), board)[0]["autospace"] is False
