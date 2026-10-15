"""EVERY GATE MUST BE ABLE TO SAY WHAT IT DID NOT MEASURE.

`ink_contrast_qa` swept 170 registers and reported 19 as "skipped" — a word that reads like a clean result
and hid four separate bugs (a fixed frame shorter registers could not reach, a missing fixture, a reason
that was only a node stack line, and an invalid probe input blamed on the register). None of it showed in
the headline, because the headline counted what the gate MEASURED.

These tests hold the five delivery gates to the other half of that contract:

  1. the universe is DERIVED from a source of truth, not restated in a list that rots;
  2. everything that leaves the measurement is COUNTED and NAMED with a reason a reader can act on;
  3. the headline states COVERAGE, not only findings;
  4. "could not measure" cannot be read as "clean".

Each coverage assertion is paired with a MUTATION: the gate is broken on purpose so it drops one item,
and the test must notice. A coverage test that passes while the gate is lying is worse than none.
"""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(_HERE, "..", "scripts")
sys.path.insert(0, _SCRIPTS)

import check_av                       # noqa: E402
import critic_ledger                  # noqa: E402
import keyframe_qa_remotion as kqr    # noqa: E402
import shot_proof                     # noqa: E402
import storyboard as sb               # noqa: E402
import validate                       # noqa: E402


def _board(out, n, meta=None):
    d = sb.new_storyboard(dict({"renderer": "remotion", "language": "en"}, **(meta or {})))
    d["slides"] = [dict(sb.new_scene(i, "slide", {}, narration="A line for beat %d." % i),
                        shot="TermSpace", shot_props={"title": "t%d" % i}) for i in range(n)]
    sb.save(d, os.path.join(out, "storyboard.json"))
    return d


# ── keyframe_qa_remotion: the universe is the FILM, and a beat with no frame is missing ──────────────

def _keyframes(out, frames, std=60):
    from PIL import Image
    kd = os.path.join(out, "_keyframes")
    os.makedirs(kd, exist_ok=True)
    for i in frames:
        im = Image.new("RGB", (160, 90), (10, 10, 10))
        for x in range(0, 160, 3):                       # texture, so the blank test does not fire
            for y in range(0, 90, 2):
                im.putpixel((x, y), (240, 240, 240))
        im.save(os.path.join(kd, kqr.FRAME_NAME % i))
    return kd


def test_keyframe_gate_counts_beats_not_files(tmp_path):
    out = str(tmp_path)
    _board(out, 4)
    _keyframes(out, [1, 2, 3, 4])
    r = kqr.check(out)
    assert r["ok"] and r["measured"] == 4 and r["scenes"] == 4
    assert "storyboard.json" in r["universe"], "the universe must name where the beat list came from"

    # MUTATION — the renderer writes nothing for beat 3 (ffmpeg runs with check=False, so this is silent).
    # Before the universe came from the board this printed "3 scene(s), 0 blank, 0 MISSING" and exited 0.
    os.remove(os.path.join(out, "_keyframes", kqr.FRAME_NAME % 3))
    m = kqr.check(out)
    assert not m["ok"], "a beat with no keyframe must not pass"
    assert m["measured"] == 3 and m["scenes"] == 4, "coverage must be 3 of 4, not 3 of 3"
    assert m["missing"] == ["03"]
    assert any("03" == x["scene"] for x in m["not_measured"])


def test_keyframe_gate_names_an_unreadable_frame_and_does_not_pass_it(tmp_path):
    out = str(tmp_path)
    _board(out, 2)
    _keyframes(out, [1, 2])
    open(os.path.join(out, "_keyframes", kqr.FRAME_NAME % 2), "wb").write(b"not a png")
    r = kqr.check(out)
    assert not r["ok"], "an unreadable frame is not a clean one"
    assert r["measured"] == 1 and r["scenes"] == 2
    why = r["unreadable"][0]["reason"]
    assert why and "unreadable" != why.lower() and ":" in why, (
        "the reason must be the exception's own message, not a one-word shrug: %r" % why)


def test_keyframe_gate_says_when_its_universe_is_only_the_directory(tmp_path):
    out = str(tmp_path)
    _keyframes(out, [1, 2])                              # no storyboard.json at all
    r = kqr.check(out)
    assert r["scenes"] == 2 and r["notes"], "a fallback universe must be declared, not silently used"
    assert "keyframe file" in r["universe"]


# ── check_av: no clips is NOT a uniform clip set ─────────────────────────────────────────────────────

def test_check_av_separates_not_applicable_from_measured():
    r = check_av.evaluate(10.0, 10.05, [], 5, 3, clips_present=False)
    assert r["ok"] and r["complete"], "a tier with no clips must still pass"
    assert r["not_applicable"], "…but it must SAY the uniformity check did not apply"
    assert r["clips_total"] == 0


def test_check_av_an_unreadable_clip_is_incomplete_not_clean():
    # MUTATION — one clip present whose sample rate cannot be probed. The old clip_rates() dropped it,
    # leaving rates=[] -> len(set())<=1 -> "uniform", and the headline printed OK.
    r = check_av.evaluate(10.0, 10.0, [48000], 5, 3, clips_present=True,
                          clips_unreadable=[("scene_02.mp4", "ffprobe read no a:0 sample_rate")])
    assert r["ok"] is True                        # not a new refusal …
    assert r["complete"] is False                 # … but it cannot read as a clean run
    assert r["clips_measured"] == 1 and r["clips_total"] == 2
    assert any("scene_02.mp4" in n for n in r["not_measured"])


def test_check_av_main_exits_nonzero_when_it_could_not_measure(tmp_path):
    out = str(tmp_path)
    os.makedirs(os.path.join(out, ".clips"))
    open(os.path.join(out, ".clips", "scene_01.mp4"), "wb").write(b"not an mp4")
    p = subprocess.run([sys.executable, check_av.__file__, out], capture_output=True, text=True)
    assert p.returncode != 0, "an unmeasurable clip must not exit 0"
    assert "NOT MEASURED" in p.stdout


# ── critic_ledger: the dimension list is parsed, and the headline states how many were judged ─────────

def test_critic_ledger_coverage_is_derived_from_the_critic(tmp_path):
    from PIL import Image
    out = str(tmp_path)
    os.makedirs(os.path.join(out, "_keyframes"))
    Image.new("RGB", (16, 16), (200, 200, 200)).save(os.path.join(out, "_keyframes", "scene_01.png"))
    # the sheet is built FROM the keyframes, so it is the newer file (a stale sheet is refused)
    Image.new("RGB", (32, 32), (20, 30, 40)).save(os.path.join(out, critic_ledger.CONTACT_SHEET))
    _t = os.path.getmtime(os.path.join(out, "_keyframes", "scene_01.png")) + 1
    os.utime(os.path.join(out, critic_ledger.CONTACT_SHEET), (_t, _t))
    dims = [d for d, _ in critic_ledger.dimensions()]
    led = {"reviewer": "independent", "verdict": "PASS",
           "render_sha256": critic_ledger.render_id(out),
           "rows": [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_01.png"} for d in dims]}
    lp = os.path.join(out, critic_ledger.LEDGER_NAME)
    json.dump(led, open(lp, "w", encoding="utf-8"))
    cov = critic_ledger.coverage(out)
    assert cov["declared"] == len(dims) > 1, "the denominator must come from agents/shot-critic.md"
    assert cov["judged"] == len(dims) and not cov["na"] and not cov["missing"]

    # MUTATION (a) — a dimension that was never looked at is a MISSING ROW.
    led["rows"] = [r for r in led["rows"] if r["id"] != dims[-1]]
    json.dump(led, open(lp, "w", encoding="utf-8"))
    cov = critic_ledger.coverage(out)
    assert cov["judged"] == len(dims) - 1 and cov["missing"], "a dropped row must move the coverage count"
    assert critic_ledger.validate(out)[0], "…and must still be a refusal"

    # MUTATION (b) — every row present and well formed, and nothing judged. The gate passes the LEDGER
    # (n/a is legal and carries a reason), so the only thing standing between that and "the review was
    # clean" is the coverage line.
    led["rows"] = [{"id": d, "verdict": "na", "note": "did not apply"} for d in dims]
    json.dump(led, open(lp, "w", encoding="utf-8"))
    cov = critic_ledger.coverage(out)
    assert not critic_ledger.validate(out)[0], "an all-n/a ledger is well formed"
    assert cov["judged"] == 0 and len(cov["na"]) == len(dims)
    p = subprocess.run([sys.executable, critic_ledger.__file__, out], capture_output=True, text=True)
    assert "judged 0 of %d" % len(dims) in p.stdout, p.stdout


# ── shot_proof: the reason a render failed must not be a stack line ──────────────────────────────────

def test_shot_proof_failure_reason_is_the_message_not_the_stack():
    stack = ("Error: Could not find composition with ID Nope\n"
             "    at Object.<anonymous> (/x/y.ts:3:1)\n"
             "    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)\n")
    why = shot_proof._stderr_reason(stack)
    assert "Could not find composition" in why
    assert "processTicksAndRejections" not in why, "the old reason was exactly this line, for every failure"
    # MUTATION — nothing but stack. It must still name what happened rather than quote a frame.
    only_stack = "    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)\n"
    assert shot_proof._stderr_reason(only_stack)
    assert shot_proof._stderr_reason("")


def test_shot_proof_static_pass_names_every_beat_it_could_not_see():
    skips = []
    board = {"meta": {"renderer": "remotion", "language": "en"},
             "slides": [{"index": 0, "shot": "TermSpace", "shot_props": {"title": "x"}},
                        {"index": 1}]}                         # a beat with no `shot` — silently dropped
    shot_proof.static_checks(board, skips=skips)
    assert any("beat 2" in s and "no `shot`" in s for s in skips), skips


# ── validate: the coverage line is measured, not asserted ────────────────────────────────────────────

def test_validate_coverage_is_derived_from_its_own_source(tmp_path):
    out = str(tmp_path)
    _board(out, 3)
    sites, funcs, returns = validate._self_sites()
    assert len(sites) > 200, "the universe is parsed from validate.py's own finding sites"
    r, cov = validate.coverage(out, pre_tts=True)
    assert cov["total"] == len(sites)
    assert 0 < cov["evaluated"] < cov["total"], "a real board reaches some checks and not others"
    assert cov["evaluated"] + cov["not_evaluated"] == cov["total"], "every check must be accounted for"
    # every unmeasured group carries a reason naming either the function or the guard that stopped it
    for row in cov["rows"]:
        assert row["reason"] and (row["func"] in row["reason"] or "`" in row["reason"]), row
    assert sum(x["checks"] for x in cov["rows"]) == cov["not_evaluated"]


def test_validate_coverage_moves_when_a_check_stops_running(tmp_path):
    """THE MUTATION. A constant denominator would pass every assertion above; this breaks the gate on
    purpose — a whole check function is made to return immediately — and the coverage number must fall."""
    out = str(tmp_path)
    _board(out, 3)
    _, before = validate.coverage(out, pre_tts=True)
    dropped = [r for r in before["rows"] if r["func"] == "_check_remotion"]
    reached_before = before["evaluated"]

    real = validate._check_remotion
    try:
        validate._check_remotion = lambda *a, **k: None       # the gate now drops a whole family of checks
        _, after = validate.coverage(out, pre_tts=True)
    finally:
        validate._check_remotion = real

    assert after["total"] == before["total"], "the universe is the source and must not move"
    assert after["evaluated"] < reached_before, (
        "a gate that stopped running a check must report a LOWER coverage number, or the line is a constant")
    assert any(r["func"] == "_check_remotion" and "never called" in r["reason"] for r in after["rows"]), \
        after["rows"]
    assert not dropped or dropped[0]["kind"] != "not called"


def test_validate_names_the_checks_its_own_inputs_switched_off(tmp_path):
    """A check that returns because an INPUT is absent must leave a trace. Two of them did not."""
    out = str(tmp_path)
    _board(out, 3)                                # 3 beats < 12, and no brief.json
    r = validate.check(out, pre_tts=True)
    skips = r.get("skipped") or []
    assert any("brief.json" in s for s in skips), (
        "with no brief.json NOTHING checks an on-screen figure against a source — that must be said")
    assert any("12" in s and "seam" in s.lower() for s in skips), (
        "the seam check's own length gate must announce itself")
    # MUTATION — give it a brief, and the figure skip must disappear (the skip is measured, not printed
    # unconditionally).
    json.dump({"evidence": ["throughput rose 19%"]}, open(os.path.join(out, "brief.json"), "w"))
    r2 = validate.check(out, pre_tts=True)
    assert not any("brief.json" in s for s in (r2.get("skipped") or []))


def test_validate_camera_checks_are_not_behind_the_seam_length_gate(tmp_path):
    """The gate's OWN constant used to exclude its own universe: `if n < 12: return` guarded the seam
    argument AND, in the same function, every camera check — which has nothing to do with film length.
    An 8-beat film carrying a move the renderer cannot execute drew no word at all."""
    out = str(tmp_path)
    d = _board(out, 8)
    d["slides"][2]["camera"] = {"move": "orbit", "amount": 3}
    sb.save(d, os.path.join(out, "storyboard.json"))
    r = validate.check(out, pre_tts=True)
    assert any("silently drop" in w for w in r["warnings"]), r["warnings"]


@pytest.mark.parametrize("beats", [1, 8])
def test_validate_coverage_survives_any_board_shape(tmp_path, beats):
    out = str(tmp_path)
    _board(out, beats)
    r, cov = validate.coverage(out, pre_tts=True)
    assert cov["total"] > 0 and cov["evaluated"] >= 0
    assert validate.check(out, pre_tts=True) == r, "tracing must not change what the gate finds"


def test_the_settled_frame_has_exactly_one_definition():
    """Three gates measured three different frames and called them all "settled".

    `useT()` holds a shot STILL for SEAM_FRAMES at both edges and runs its span between them, so the settled
    point is the INVERSE of that mapping — `render_remotion.frame_at_t(dur, SETTLED_T)`, which `band_debt`
    already used. `ink_contrast_qa` multiplied DURATION by REDUCED_MOTION_T and `shot_proof` by a literal
    0.88; measured across the library on 2026-09-21 the two sat up to 12 and 15 frames from it — on ALL 170
    registers. Every proof sheet this repo has produced was read at a frame no other instrument measured.

    This file's own subject is what a gate cannot see; a gate reading a different frame than the one it
    claims sees a different picture, which is the same failure one layer down. `runtime/aimCamera` records
    what two cameras that agree until they quietly do not cost: six PortRail labels 215px off their own
    modules, on a frame that read as perfectly correct.
    """
    import importlib.util
    import os
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    scripts = os.path.join(os.path.dirname(here), "scripts")

    def load(name):
        spec = importlib.util.spec_from_file_location(name, os.path.join(scripts, name + ".py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    rr = load("render_remotion")
    ink = load("ink_contrast_qa")
    shots = os.path.join(os.path.dirname(here), "remotion", "src", "shots")

    checked = 0
    for f in sorted(os.listdir(shots)):
        if not f.endswith(".tsx"):
            continue
        m = re.search(r"export const DURATION\s*=\s*(\d+)",
                      open(os.path.join(shots, f), encoding="utf-8").read())
        if not m:
            continue
        dur, name = int(m.group(1)), f[:-4]
        want = max(0, min(dur - 1, int(round(rr.frame_at_t(dur, rr.SETTLED_T)))))
        assert ink.settled_frame(name) == want, \
            "%s: the ink gate reads frame %d where useT settles at %d" % (name, ink.settled_frame(name), want)
        checked += 1
    assert checked > 150, "this test read only %d registers — it is not covering the library" % checked

    # ...and no gate may derive it again by hand. A literal fraction of DURATION is the shape that drifted.
    for name in ("shot_proof.py", "ink_contrast_qa.py", "band_debt.py"):
        src = open(os.path.join(scripts, name), encoding="utf-8").read()
        # read the CODE, not the prose: these files describe the drift they were repaired of, and a
        # docstring quoting `int(DURATION * 0.88)` is the record of the bug, not the bug
        code = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', "", src)
        code = "\n".join(l for l in code.split("\n") if not l.lstrip().startswith("#"))
        assert not re.search(r"DURATION[^\n]*\*\s*0\.\d+", code), \
            "%s derives the settled frame from a literal again — call render_remotion.frame_at_t" % name
        assert "frame_at_t" in code, "%s no longer asks the one definition" % name


# ── critic_ledger: the user may waive the review — but only for the render they watched ──────────────

def _waiver_fixture(tmp_path, reason="我看过整片了，就这样发，不用再评审", pin="self", extra=None):
    from PIL import Image
    out = str(tmp_path)
    sheet = os.path.join(out, critic_ledger.CONTACT_SHEET)
    if not os.path.exists(sheet):
        Image.new("RGB", (32, 32), (20, 30, 40)).save(sheet)
    w = {"reason": reason}
    if pin == "self":
        w["render_sha256"] = critic_ledger.render_id(out)
    elif pin is not None:
        w["render_sha256"] = pin
    if extra is not None:
        w = extra
    board = {"meta": {"renderer": "remotion", "review_waiver": w}, "slides": []}
    json.dump(board, open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8"))
    open(os.path.join(out, "NOT_DELIVERED.md"), "w", encoding="utf-8").write("# not yet\n")
    # what `critic_brief.py --gates` leaves: every delivery gate run on this render, all green — a waiver waives
    # taste, and --final still refuses a render nobody ran the gates on
    critic_ledger.record_render(out, gates={critic_ledger.gate_name(s, a): {"exit": 0, "blocking": b}
                                            for _l, s, a, _t, b in critic_ledger.delivery_gates(out)},
                                review_round=False)
    return out


def test_a_user_may_waive_the_critic_but_only_for_the_render_they_watched(tmp_path):
    """"Reviewed" and "not reviewed" are not the only truths: a user who has watched the film and judged it
    finished may waive the critic. What makes that safe to have is not the option, it is the three things
    around it — the reason is recorded in the user's own words, the waiver pins the RENDER it covers, and it
    waives taste only.

    The pin is the property that matters. "The user said fine once" must not become a standing licence over
    everything changed afterwards: re-render one beat and the contact sheet moves, the waiver stops applying
    and the gate asks again."""
    out = _waiver_fixture(tmp_path)
    errs, warns = critic_ledger.validate(out, final=True)
    assert not errs, errs
    assert any("WAIVED BY THE USER" in w for w in warns), warns
    cov = critic_ledger.coverage(out)
    assert cov["judged"] == 0 and cov["waived"] is True and not cov["missing"], cov

    # it is NOT a pass: the delivery marker is rewritten to say the film shipped unreviewed
    p = subprocess.run([sys.executable, critic_ledger.__file__, out, "--final"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
    nd = open(os.path.join(out, "NOT_DELIVERED.md"), encoding="utf-8").read()
    assert "WITHOUT a critic review" in nd and "我看过整片了" in nd, nd

    # ── and every way of getting it wrong is refused ────────────────────────────────────────────────
    # 1. the film was re-rendered since the waiver was given
    out2 = _waiver_fixture(tmp_path, pin="0" * 64)
    errs, _ = critic_ledger.validate(out2, final=True)
    assert errs and "DIFFERENT render" in errs[0], errs
    assert critic_ledger.coverage(out2)["waived"] is False
    # a broken waiver must not drown its own message in per-dimension noise
    assert not critic_ledger.coverage(out2)["missing"]

    # 2. no reason, or a reason too thin to be a decision
    for bad in ("", "ok", "   "):
        errs, _ = critic_ledger.validate(_waiver_fixture(tmp_path, reason=bad), final=True)
        assert errs and "reason" in errs[0], (bad, errs)

    # 3. no render pinned at all
    errs, _ = critic_ledger.validate(_waiver_fixture(tmp_path, pin=None), final=True)
    assert errs and "render_sha256" in errs[0], errs

    # 4. a bare string is accepted as the reason but still needs its pin — it cannot become the easy path
    errs, _ = critic_ledger.validate(
        _waiver_fixture(tmp_path, extra="我看过整片了，就这样发，不用再评审"), final=True)
    assert errs and "render_sha256" in errs[0], errs

    # 5. no waiver at all is unchanged: a missing ledger is still a refusal with every dimension named
    plain = _waiver_fixture(tmp_path)
    b = json.load(open(os.path.join(plain, "storyboard.json"), encoding="utf-8"))
    b["meta"].pop("review_waiver")
    json.dump(b, open(os.path.join(plain, "storyboard.json"), "w", encoding="utf-8"))
    errs, _ = critic_ledger.validate(plain, final=True)
    assert errs and "no %s" % critic_ledger.LEDGER_NAME in errs[0], errs
    assert len(critic_ledger.coverage(plain)["missing"]) == len(critic_ledger.dimensions())
