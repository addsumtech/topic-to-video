"""Kinetic type v2 — what the benchmark films could not do, held to behaviour (tests/test_kinetic.py holds v1).

1. A SCRAMBLE NEVER SPELLS A WORD. Drawn from the copy's own glyphs, a slot resolving onto 大模型 flashed 大模刑
   (bench-launch). The stand-ins are blocks or the right glyph at another weight (CJK), symbols (everything else) —
   checked in node over every kind of target, and on the rendered DOM of a scrambling slot, frame by frame.
2. MAGIC MOVE. The glyph pairing keeps a shared word in order (LCS), pairs the rest by identity, never moves a space;
   a travelling glyph's arc lifts a rightward glyph and drops a leftward one, capped; the register's hold report has
   one record per phrase, and a beat too short for the phrases is an error, not a pass.
3. SHORT BEATS. A register paced in seconds is not reported "N x faster" by validate; WordRoll pays every option its
   read-once time first, so at a beat that can pay them the hold gate is clean, and at one that cannot it still errors.
4. CARRY. Every kinetic register and the magic move declare `word`; LandscapeWell declares `screen`. A word window's
   arriving beat is never smaller than the word it is seen through (the bench-rams postage stamp), and is unchanged at
   the cut and for a box window.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import shutil

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
_SRC = os.path.join(_REM, "src")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _HERE)
import _tsprobe  # noqa: E402
import shot_proof as sp  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")
CORE = _tsprobe.mod("kineticCore.ts")
MOVE = _tsprobe.mod("kineticMoveCore.ts")
HAN = re.compile(r"[㐀-鿿豈-﫿]")


# ── 1. scramble ────────────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_a_scramble_stand_in_is_never_a_letter_digit_or_another_character():
    out = _tsprobe.run_ts("import {scrambleGlyph, SCRAMBLE_SYMBOLS} from %s;" % CORE, """
        const targets = ['大', '模', '型', 'の', '한', 'a', 'Z', '7', 'é', 'Ж', 'λ'];
        out.syms = SCRAMBLE_SYMBOLS;
        out.got = targets.map((g) => {
          const seen = [];
          for (let seed = 1; seed < 6; seed++) for (let i = 0; i < 8; i++) for (let step = 0; step < 40; step++)
            seen.push(scrambleGlyph(g, seed, i, step));
          return {g, seen};
        });
        out.again = [scrambleGlyph('大', 7, 3, 9), scrambleGlyph('大', 7, 3, 9)];
    """)
    letter = re.compile(r"[^\W_]", re.U)            # any letter or digit, any script
    for row in out["got"]:
        g, seen = row["g"], row["seen"]
        kinds = {s["kind"] for s in seen}
        if HAN.search(g) or re.search(r"[぀-ヿ가-힯]", g):
            assert kinds <= {"block", "weight"} and kinds == {"block", "weight"}, (g, kinds)
            assert all(0 <= s["shape"] < 5 for s in seen if s["kind"] == "block")
        else:
            assert kinds == {"symbol"}, (g, kinds)
            chars = {s["ch"] for s in seen}
            assert chars <= set(out["syms"]) and not any(letter.match(c) for c in chars), (g, chars)
    assert out["again"][0] == out["again"][1], "a stand-in is a pure function of (seed, glyph, step)"


def test_the_symbol_pool_holds_no_letter_and_the_old_pool_would_have_failed_the_same_check():
    """The positive control for the check above (E7): the v1 pool — the copy's OWN glyphs — puts a real character
    in a real character's place, which is exactly what the predicate refuses."""
    src = open(os.path.join(_SRC, "runtime", "kineticCore.ts"), encoding="utf-8").read()
    pool = re.search(r"SCRAMBLE_SYMBOLS = \[([^\]]*)\]", src).group(1)
    syms = re.findall(r"'((?:\\\\|[^'])+)'", pool)
    letter = re.compile(r"[^\W_]", re.U)
    assert syms and not any(letter.match(s.replace("\\\\", "\\")) for s in syms)
    # the predicate itself is load-bearing: the v1 pool (the copy's own glyphs) drew 刑 for 型, and it is refused
    assert letter.match("刑") and letter.match("a") and letter.match("7") and not letter.match("#")


# ── 2. magic move (pure) ───────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_the_glyph_pairing_keeps_a_shared_word_and_never_moves_a_space():
    out = _tsprobe.run_ts("import {matchGlyphs} from %s;" % MOVE, """
        const g = (s) => Array.from(s);
        out.swap = matchGlyphs(g('what stays, moves'), g('what moves, stays'));
        out.ana = matchGlyphs(g('listen'), g('silent'));
        out.zh = matchGlyphs(g('少，但更好'), g('更好，但更少'));
        out.none = matchGlyphs(g('abc'), g('xyz'));
    """)
    a, b = list("what stays, moves"), list("what moves, stays")
    sw = out["swap"]
    for i, j in sw["pairs"]:
        assert a[i] == b[j] and a[i] != " "
    # every non-space glyph is accounted for exactly once on each side
    ia = sorted([i for i, _ in sw["pairs"]] + sw["leave"])
    jb = sorted([j for _, j in sw["pairs"]] + sw["arrive"])
    assert ia == [i for i, c in enumerate(a) if c != " "] and jb == [j for j, c in enumerate(b) if c != " "]
    assert [p for p in sw["pairs"] if p[0] < 4] == [[0, 0], [1, 1], [2, 2], [3, 3]], "the shared word stays put"
    assert len(out["ana"]["pairs"]) == 6 and not out["ana"]["leave"] and not out["ana"]["arrive"]
    zh = out["zh"]
    assert len(zh["pairs"]) == 5 and len(zh["arrive"]) == 1 and zh["leave"] == [], zh
    assert out["none"]["pairs"] == [] and len(out["none"]["leave"]) == 3


@needs_toolchain
def test_a_travelling_glyph_arcs_to_opposite_sides_capped_and_lands_exactly():
    out = _tsprobe.run_ts("import {arcAt, moveTiming, travelWindow} from %s;" % MOVE, """
        out.r = [0, 0.5, 1].map((p) => arcAt(p, 0, 100, 400, 100, 0.16));
        out.l = arcAt(0.5, 400, 100, 0, 100, 0.16);
        out.cap = arcAt(0.5, 0, 100, 4000, 100, 0.16, 50);
        const mt = moveTiming(1.0, 5);
        out.w = Array.from({length: 5}, (_, r) => travelWindow(r, 5, mt));
        out.dur = mt.dur;
    """)
    r = out["r"]
    assert r[0] == {"x": 0, "y": 100} and abs(r[2]["x"] - 400) < 1e-9 and abs(r[2]["y"] - 100) < 1e-9
    assert r[1]["y"] < 100 - 60, "a rightward glyph passes OVER the line"
    assert out["l"]["y"] > 100 + 60, "a leftward glyph passes UNDER it"
    assert abs(out["cap"]["y"] - 50) < 1e-6, "the lift is capped"
    assert all(b <= out["dur"] + 1e-9 for _, b in out["w"]), "every traveller lands inside the move"


@needs_toolchain
def test_a_word_window_never_shows_the_next_beat_smaller_than_the_word():
    out = _tsprobe.run_ts("import {windowInnerScale} from %s;" % json.dumps(os.path.join(_SRC, "seams")), """
        const W = 1080, H = 1080, word = {w: 300, h: 110};          // a 99 px glyph pair, like bench-rams' 少
        const K = 1.06 * Math.hypot(W / 2, H / 2) / 4;               // a 4 px stroke room: K ~ 202
        out.thin = [1, 2, 5, 20, K].map((k) => windowInnerScale(k, K, word, W, H));
        out.v1 = [1, 2, 5, 20, K].map((k) => 1.06 * k / K);         // the old scale, for the record
        out.box = [1, 3, 9].map((k) => [windowInnerScale(k, 9, null, W, H), 1.06 * k / 9]);
    """)
    thin = out["thin"]
    assert abs(thin[-1] - 1.06) < 1e-9, "at the cut the arriving beat is at WINDOW_OVER, as before"
    assert thin[0] >= 300 / 1080 * 1.06 - 1e-9, "at the start it covers the word's own box"
    assert out["v1"][0] * 1080 < 10, "the old scale drew the next beat a few px wide at the start"
    assert all(b >= a - 1e-12 for a, b in zip(thin, thin[1:])), "it only grows"
    assert all(abs(a - b) < 1e-12 for a, b in out["box"]), "a box window is unchanged"


# ── 3. short beats ─────────────────────────────────────────────────────────────────────────────────────────
def test_a_register_paced_in_seconds_is_not_reported_rushed_and_one_in_shares_still_is():
    import validate as v
    warns, errs = [], []
    v._shot_truncation({"fps": 30}, [{"shot": "WordRoll", "duration": 3.0}, {"shot": "MagicMoveType", "duration": 3.0},
                                     {"shot": "HeadlineReveal", "duration": 2.5}, {"shot": "SwissEditorial",
                                                                                 "duration": 2.5}], errs, warns)
    assert len(warns) == 1 and "SwissEditorial" in warns[0], warns
    for reg in ("HeadlineReveal", "WordRoll", "CroppedType", "TypeOnPath", "MagicMoveType", "LandscapeWell"):
        src = open(os.path.join(_SRC, "shots", reg + ".tsx"), encoding="utf-8").read()
        assert re.search(r"export const PACE = 'seconds'", src), reg


def _holds(comp, props, frames):
    tmp = tempfile.mkdtemp(prefix="kv2_")
    try:
        pf = os.path.join(tmp, "p.json")
        json.dump(dict(props, kineticHolds=True, holdFrames=frames), open(pf, "w", encoding="utf-8"),
                  ensure_ascii=False)
        r = subprocess.run(["npx", "remotion", "still", "src/index.ts", comp, os.path.join(tmp, "x.png"), "--frame=0",
                            "--props=" + pf, "--log=error"], cwd=_REM, capture_output=True, text=True, timeout=600)
        blob = (r.stdout or "") + (r.stderr or "")
        assert sp.KINETIC_HOLDS_TAG in blob, blob[-1500:]
        return json.JSONDecoder().raw_decode(blob.split(sp.KINETIC_HOLDS_TAG, 1)[1])[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@needs_toolchain
def test_word_roll_pays_every_option_its_reading_floor_on_a_short_beat_and_still_errors_when_it_cannot():
    zh = {"before": "它能写", "options": ["大模型", "代码", "成片"], "mode": "roll"}
    ok = _holds("WordRoll", zh, 120)                 # 4 s: three options can each be read once
    errors, _ = sp.kinetic_hold_findings(ok)
    assert errors == [], errors
    alts = [t for r in ok["reports"] for t in r["texts"] if t["kind"] == "alt"]
    assert [t["text"] for t in alts] == ["大模型", "代码", "成片"] and min(t["hold"] for t in alts) >= 0.83, alts
    tight = _holds("WordRoll", dict(zh, options=["大模型", "代码", "成片", "交付", "上线", "复盘"]), 120)
    assert sp.kinetic_hold_findings(tight)[0], "six options in four seconds cannot each be read — the gate says so"


@needs_toolchain
def test_the_magic_move_reports_each_phrase_and_a_short_beat_is_an_error():
    rep = _holds("MagicMoveType", {}, 210)
    texts = [t for r in rep["reports"] if r["id"] == "phrases" for t in r["texts"]]
    assert [t["text"] for t in texts] == ["what stays, moves", "what moves, stays"], texts
    assert sp.kinetic_hold_findings({"reports": [r for r in rep["reports"] if r["id"] == "phrases"]}) == ([], [])
    four = {"phrases": ["少，但更好", "更好", "更少", "少"]}
    errs, _ = sp.kinetic_hold_findings(_holds("MagicMoveType", four, 75))
    assert errs, "four phrases in 2.5 s cannot be read"


# ── 4. carry anchors ───────────────────────────────────────────────────────────────────────────────────────
def test_the_kinetic_registers_declare_word_and_the_landscape_well_a_screen():
    import carry_anchors as ca
    for reg in ("HeadlineReveal", "WordRoll", "CroppedType", "TypeOnPath", "MagicMoveType"):
        assert ca.has_anchor(reg, "word") is True, reg
    assert ca.has_anchor("LandscapeWell", "screen") is True
    assert ca.has_anchor("RankRace", "word") is False, "drawing a KineticText is not drawing a KineticWord"


@needs_toolchain
def test_cropped_type_in_a_platform_safe_film_keeps_its_type_out_of_the_buttons(tmp_path):
    """bench-launch: CroppedType's band ran under a 9:16 film's button column (text_safe --glide ERROR) with no prop to
    move it. The bands now stack above the column; and the census reads a cropped glyph by what its band DRAWS, so the
    letters the band cut away no longer count. Both scripts, in the Film's own platform-safe frame."""
    import text_safe_qa as tq
    import workshop as _ws
    bundle = tq.glide_bundle(str(tmp_path / "b"), None, _ws.prepare(None))
    base = {"aspect": "9:16", "safe": "social", "captions": False, "camera": 0, "cameraBed": False, "typeGlide": True,
            "dna": "product"}
    cases = {"zh": {"word": "代码", "statement": "每一帧，都是代码画的", "kicker": "一行一行"}, "en": {}}
    res = tq.glide_run([{"tag": k, "id": "Film", "props": dict(base, scenes=[{"shot": "CroppedType", "durF": 110,
                                                                             "props": p}])}
                        for k, p in cases.items()], bundle)
    for k in cases:
        assert tq._glide_measured(res[k], 110) is None, (k, res[k].get("error"))
        hits = tq.platform_zone_findings(res[k]["frames"], 1080, 1920, tq.safe_profile())
        assert [h for h in hits if h[0] == "error"] == [], (k, hits)
        assert tq.glide_level(tq.judge_glide(res[k]["frames"]))[0] == "clean", k
