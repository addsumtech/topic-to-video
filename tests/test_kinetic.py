"""runtime/kinetic.tsx — kinetic type that is still the text it animates, and that the gates can still read.

Three claims, each held to a measurement rather than to a description:

1. A SETTLED KineticText IS ITS TEXT. It draws one grapheme per element, placed where one reference text node laid
   them out; the research measured 0 px against the single node (references/motion-research.md §1), and the first
   Chinese render of this primitive missed it by 2,428 px — two opening brackets Chrome had compressed were drawn
   half an em to the right. The probe draws the same copy both ways; they must be the same pixels, in both scripts.
2. THE GATES READ IT AS ITS LINES. Read element by element, a kinetic line is forty one-letter "lines". The census
   (runtime/textSafe.tsx `kineticGroups`) folds them back, and the proof is that each defect is found ONCE, by the
   line's own text: a line cut off by the frame, a line in the caption band, a block set into itself, a line that
   crawls in whole-pixel steps (found with the unlock off, clean with it on) — and that the clean twins stay clean.
3. A MUST-READ LINE HELD SHORTER THAN ITS READING TIME IS A FINDING (scripts/shot_proof.py), computed through the
   picture's own clock at the beat's real length.

Plus determinism: the same frame twice, and frame N cold against frame N after 0..N-1, are the same pixels.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _HERE)
import _tsprobe  # noqa: E402
import shot_proof as sp  # noqa: E402
import text_safe_qa as tq  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")
CORE = _tsprobe.mod("kineticCore.ts")
KINETIC_REGISTERS = ("HeadlineReveal", "WordRoll", "TypeOnPath", "CroppedType")


# ── the pure half (kineticCore.ts, in node) ────────────────────────────────────────────────────────────────
@needs_toolchain
def test_the_clock_copy_is_useT_and_its_constants_are_motion_s():
    """`tAtFrame` restates useT's mapping (useT is not rewritten to call it: every register's measured row hashes
    the symbols it reaches). So it is held to the Python mirror of the same clock, and its constants to motion.ts."""
    import render_remotion as rr
    out = _tsprobe.run_ts("import {tAtFrame, SEAM_FRAMES_K, ENTRY_T_K} from %s;" % CORE, """
        out.k = [SEAM_FRAMES_K, ENTRY_T_K];
        out.t = [30, 61, 150, 451].map((d) => Array.from({length: d}, (_, f) => tAtFrame(f, d)));
    """)
    motion = open(os.path.join(_REM, "src", "runtime", "motion.ts"), encoding="utf-8").read()
    assert out["k"][0] == int(re.search(r"export const SEAM_FRAMES = (\d+)", motion).group(1))
    assert out["k"][1] == float(re.search(r"export const ENTRY_T = ([\d.]+)", motion).group(1))
    for d, ts in zip([30, 61, 150, 451], out["t"]):
        pad = min(12, (d - 1) // 3)
        for f in range(pad, d - pad):
            assert abs(rr.frame_at_t(d, ts[f]) - f) < 1e-6, (d, f, ts[f])


@needs_toolchain
def test_the_range_selector_has_after_effects_shapes():
    out = _tsprobe.run_ts("import {rangeCoverage, permutation} from %s;" % CORE, """
        const n = 10, cov = (sel) => Array.from({length: n}, (_, i) => +rangeCoverage(sel, i, n).toFixed(3));
        out.square = cov({start: 0.2, end: 0.5});
        out.half = cov({start: 0.25, end: 0.55});
        out.up = cov({start: 0, end: 1, shape: 'rampUp'});
        out.down = cov({start: 0, end: 1, shape: 'rampDown'});
        out.tri = cov({start: 0, end: 1, shape: 'triangle'});
        out.amount = cov({start: 0, end: 1, amount: 0.5});
        out.offset = cov({start: 0, end: 0.3, offset: 0.7});
        out.perm = [permutation(8, 3), permutation(8, 3), permutation(8, 4)];
    """)
    assert out["square"] == [0, 0, 1, 1, 1, 0, 0, 0, 0, 0]
    assert out["half"][2] == 0.5 and out["half"][5] == 0.5, "a range edge across a unit covers it by its share"
    assert out["up"] == sorted(out["up"]) and out["up"][0] < 0.1 and out["up"][-1] > 0.9
    assert out["down"] == sorted(out["down"], reverse=True)
    assert max(out["tri"]) == out["tri"][4] or max(out["tri"]) == out["tri"][5]
    assert out["amount"] == [0.5] * 10
    assert out["offset"] == [0] * 7 + [1] * 3
    a, b, c = out["perm"]
    assert a == b and sorted(a) == list(range(8)) and a != c, "randomise is a SEEDED permutation"


@needs_toolchain
def test_the_named_eases_are_the_measured_curves():
    out = _tsprobe.run_ts("import {EASES} from %s;" % CORE, """
        out.ease = EASES.ease(0.5); out.stripe = EASES.stripe(0.5); out.ends = [EASES.ease(0), EASES.ease(1)];
    """)
    # CSS `ease` = cubic-bezier(.25,.1,.25,1): 0.8024 at x = 0.5 (the browser's own solver gives the same)
    assert abs(out["ease"] - 0.8024) < 2e-3 and out["ends"] == [0, 1]
    assert 0.85 < out["stripe"] < 0.95


@needs_toolchain
def test_runs_words_and_swaps():
    out = _tsprobe.run_ts("import {parseRuns, wordIds, swapTimes, orderRank} from %s;" % CORE, """
        out.runs = parseRuns('Ship *the model* \\\\*now');
        try { parseRuns('never *closed'); out.unclosed = 'no throw'; } catch (e) { out.unclosed = String(e); }
        out.zh = wordIds('我们今天讨论运动图形设计', 'zh');
        out.en = wordIds('one, two three.', 'en').ids;
        out.swap = swapTimes(4, 0.3, 0.75);
        out.cued = swapTimes(4, 0.3, 0.75, [null, 0.2, 0.9, 0.5]);
        out.center = Array.from({length: 5}, (_, i) => orderRank(i, 5, 'center'));
    """)
    assert out["runs"] == [{"text": "Ship ", "emph": False}, {"text": "the model", "emph": True},
                           {"text": " *now", "emph": False}]
    assert "never closes" in out["unclosed"]
    assert out["zh"]["count"] == 6, "zh word segmentation: 我们|今天|讨论|运动|图形|设计"
    assert out["en"] == [0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2], "punctuation and spaces join the word before"
    assert out["swap"] == pytest.approx([0, 0.3, 0.525, 0.75])
    # a cue only brings an arrival EARLIER (0.9 is ignored) and never before the one it replaces
    assert out["cued"] == pytest.approx([0, 0.2, 0.525, 0.525])
    assert out["center"] == [2, 1, 0, 1, 2]


# ── the hold verdict and the census reader (pure Python) ────────────────────────────────────────────────────
def test_a_hold_under_reading_time_is_an_error_and_under_must_read_a_warning():
    rep = {"reports": [{"texts": [
        {"text": "faster", "kind": "alt", "hold": 0.27, "chars": 6, "words": 1, "lang": "en"},
        {"text": "a line that is read once", "kind": "line", "hold": 1.4, "chars": 19, "words": 6, "lang": "en"},
        {"text": "一句标题", "kind": "line", "hold": 0.6, "chars": 4, "words": 2, "lang": "zh"},
        # Japanese reads at 4 characters a second, not Chinese's 9: 5 characters need 1.25 s (at 9 they would pass)
        {"text": "見出しです", "kind": "line", "hold": 1.0, "chars": 5, "words": 2, "lang": "ja"},
        {"text": "plenty", "kind": "block", "hold": 4.0, "chars": 6, "words": 1, "lang": "en"},
    ]}]}
    errors, warns = sp.kinetic_hold_findings(rep)
    assert len(errors) == 3 and "'faster'" in errors[0] and "一句标题" in errors[1] and "見出しです" in errors[2]
    # read once at 20 cps is under a second; must-read at 0.6 s a word is 3.6 s: a warning, not an error
    assert len(warns) == 1 and "a line that is read once" in warns[0]


def test_the_reading_table_is_the_caption_rule_s_numbers():
    """runtime/readingSpec.json paces kinetic type (TS) and judges it (shot_proof); validate.py's caption rule holds
    the same three published figures as constants. Two homes for one number is how they drift — so they are equal."""
    import validate as _v
    spec = json.load(open(os.path.join(_REM, "src", "runtime", "readingSpec.json"), encoding="utf-8"))
    assert spec["cps"]["zh"] == _v.CPS_CJK and spec["cps"]["latin"] == _v.CPS_LATIN
    assert spec["minSeconds"] == _v.MIN_CAPTION_SECONDS
    assert set(spec["sources"]) >= {"cps.zh", "cps.ja", "cps.latin", "cps.ko", "minSeconds", "mustReadSecondsPerWord"}


def test_the_report_tag_is_one_string_in_both_languages():
    dom = open(os.path.join(_REM, "src", "runtime", "kineticDom.ts"), encoding="utf-8").read()
    assert "KINETIC_HOLDS_TAG = '%s'" % sp.KINETIC_HOLDS_TAG in dom


def test_which_registers_draw_kinetic_type_is_read_from_their_source():
    assert all(sp.kinetic_capable(r) for r in KINETIC_REGISTERS)
    assert not sp.kinetic_capable("WeightedWheel")


def _kline(frames_ys, key="/body0/div0/kl0", text="Drifting line", unlocked=False, glyphs=6):
    out = {}
    for f, y in enumerate(frames_ys):
        g = [[i, y, 1 if unlocked else 0, 1.0] for i in range(glyphs)]
        out[f] = {"f": f, "u": 0, "z": 0, "lines": [{"k": key, "y": y, "o": 1, "t": text, "g": g, "ly": 0,
                                                    "px": 80, **({"u": 1} if unlocked else {})}]}
    return out


def test_a_kinetic_line_s_glyph_tracks_are_judged_and_reported_once():
    ys = [100 + 0.3 * i for i in range(12)]
    runs = tq.judge_glide(_kline(ys))
    assert len(runs) == 1 and runs[0]["t"] == "Drifting line" and runs[0]["glyphs"] == 6
    assert runs[0]["steps"] >= 3 and tq.glide_level(runs)[0] == "error"
    assert tq.judge_glide(_kline(ys, unlocked=True)) == [], "an unlocked glyph does not step"


# ── rendered: identity, the gates, the hold, determinism ───────────────────────────────────────────────────
def _still(comp, props, frame, png):
    pf = png + ".json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", comp, png, "--frame=%d" % frame,
                        "--props=" + pf, "--log=error"], cwd=_REM, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _pixels(png):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(png).convert("RGB")).astype(int)


@pytest.fixture(scope="module")
def work():
    d = tempfile.mkdtemp(prefix="kinetic_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@needs_toolchain
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_a_settled_kinetic_text_is_its_text_pixel_for_pixel(work, lang):
    a, b = os.path.join(work, "ref-%s.png" % lang), os.path.join(work, "kin-%s.png" % lang)
    assert _still("KineticProbe", {"variant": "reference", "lang": lang}, 60, a)[0] == 0
    assert _still("KineticProbe", {"variant": "settled", "lang": lang}, 60, b)[0] == 0
    pa, pb = _pixels(a), _pixels(b)
    assert (pa < 128).any(), "the reference drew no ink — the comparison would prove nothing"
    differing = int((abs(pa - pb).sum(axis=2) > 0).sum())
    assert differing == 0, "%d pixels differ between the glyphs and the text node they were placed from" % differing


@needs_toolchain
def test_the_type_gates_read_a_kinetic_text_as_its_lines(work):
    cut = tq.audit_shot("KineticProbe", {"variant": "cut"}, 60, os.path.join(work, "cut.png"))
    assert len(cut) == 1 and cut[0]["tag"] == "kinetic" and cut[0]["out"].get("right", 0) > 100, cut
    assert cut[0]["text"].startswith("AVATAR Wave To office"), "named by its LINE, not by a letter"
    band = tq.audit_shot("KineticProbe", {"variant": "band"}, 60, os.path.join(work, "band.png"))
    assert len(band) == 1 and band[0].get("band", 0) > 50 and band[0]["text"] == "Set in the caption band", band
    assert tq.audit_shot("KineticProbe", {"variant": "settled"}, 60, os.path.join(work, "ok.png")) == []
    # a block set into itself is ONE leading finding, on the whole block's text
    rc, blob = _still("KineticProbe", {"variant": "leading", "lang": "zh", "typeCollisions": True}, 60,
                      os.path.join(work, "lead.png"))
    hits = json.JSONDecoder().raw_decode(blob.split("TYPE-COLLISIONS ", 1)[1])[0]
    assert [h["kind"] for h in hits] == ["leading"] and hits[0]["text"].startswith("第一行文字在这里"), hits
    rc, blob = _still("KineticProbe", {"variant": "settled", "lang": "zh", "typeCollisions": True}, 60,
                      os.path.join(work, "lead-ok.png"))
    assert rc == 0 and "TYPE-COLLISIONS" not in blob
    # the title is the first LINE, not its largest letter
    rc, blob = _still("KineticProbe", {"variant": "settled", "titleProbe": True}, 60, os.path.join(work, "t.png"))
    title = json.JSONDecoder().raw_decode(blob.split("TITLE-PROBE ", 1)[1])[0]
    assert title["text"] == "AVATAR Wave To office flyaway" and title["align"] == "left", title


@needs_toolchain
def test_the_glide_census_finds_a_kinetic_staircase_once_and_clears_the_unlocked_one(work):
    import workshop as _ws
    bundle = tq.glide_bundle(os.path.join(work, "bundle"), None, _ws.prepare(None))
    res = tq.glide_run([{"tag": "off", "id": "KineticProbe", "props": {"variant": "drift", "typeGlide": True,
                                                                         "baselineUnlock": False}},
                        {"tag": "on", "id": "KineticProbe", "props": {"variant": "drift", "typeGlide": True}},
                        {"tag": "path", "id": "KineticProbe", "props": {"variant": "path", "typeGlide": True}}], bundle)
    for k in ("off", "on", "path"):
        assert tq._glide_measured(res[k], 90) is None, (k, res[k].get("error"))
    off = tq.judge_glide(res["off"]["frames"])
    assert tq.glide_level(off)[0] == "error" and len(off) == 1, off
    assert off[0]["t"] == "Drifting line" and off[0]["glyphs"] > 1
    assert tq.glide_level(tq.judge_glide(res["on"]["frames"]))[0] == "clean"
    assert tq.glide_level(tq.judge_glide(res["path"]["frames"]))[0] == "clean"
    # the census lists the line (for the sync audit) with its whole text, once per frame
    f = res["on"]["frames"][60]
    assert [ln["t"] for ln in f["lines"]] == ["Drifting line"] and f["lines"][0].get("u") == 1


@needs_toolchain
def test_the_hold_report_walks_the_picture_s_own_clock(work):
    def holds(variant, frames):
        rc, blob = _still("KineticProbe", {"variant": variant, "kineticHolds": True, "holdFrames": frames}, 0,
                          os.path.join(work, "h.png"))
        return json.JSONDecoder().raw_decode(blob.split(sp.KINETIC_HOLDS_TAG, 1)[1])[0]
    many = holds("swap", 120)
    texts = many["reports"][0]["texts"]
    assert [t["text"] for t in texts] == ["faster", "cheaper", "smaller", "quieter", "simpler", "safer"]
    errors, _ = sp.kinetic_hold_findings(many)
    assert errors, "six alternatives in four seconds cannot each be read"
    two = holds("swap-ok", 120)
    assert sp.kinetic_hold_findings(two) == ([], [])
    # the same register at a longer beat holds each alternative longer: the report is the beat's, not the register's
    longer = holds("swap", 300)
    assert longer["reports"][0]["texts"][1]["hold"] > texts[1]["hold"] * 2


@needs_toolchain
@pytest.mark.parametrize("comp,props,frame", [
    ("WordRoll", {"mode": "scramble"}, 102),
    ("TypeOnPath", {"path": "orbit"}, 70),
    ("CroppedType", {}, 70),
    ("HeadlineReveal", {"reveal": "char"}, 40),
])
def test_a_frame_is_the_same_cold_twice_and_after_its_predecessors(work, comp, props, frame):
    """Cold twice (two fresh browsers), and cold against the same frame rendered after every frame before it in one
    tab (`--concurrency=1`, so the measured layout and every cache are warm) — the same pixels all three times."""
    a, b = os.path.join(work, "%s-a.png" % comp), os.path.join(work, "%s-b.png" % comp)
    assert _still(comp, props, frame, a)[0] == 0 and _still(comp, props, frame, b)[0] == 0
    seq = os.path.join(work, "%s-seq" % comp)
    pf = os.path.join(work, "%s.json" % comp)
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh)
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", comp, seq, "--sequence", "--image-format=png",
                        "--frames=0-%d" % frame, "--concurrency=1", "--props=" + pf, "--log=error"],
                       cwd=_REM, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    warm = sorted(os.listdir(seq))[-1]
    pa, pb, pw = _pixels(a), _pixels(b), _pixels(os.path.join(seq, warm))
    assert (pa != pb).sum() == 0, "the same frame rendered twice differs"
    assert (pa != pw).sum() == 0, "frame %d after frames 0..%d differs from the same frame cold" % (frame, frame - 1)
