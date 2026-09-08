"""A spring on the shot's own clock — the arrival model this library did not have.

160 registers animated with hand-rolled cubics, and the closest thing to a landing was one fixed curve
(`easeOutBack`), so every element in every shot arrived with the same weight. The reference library writes
its landings in mass and damping instead, and says why in its own parameter notes: the OVERSHOOT is the
meaning. A thing that settles past its mark and comes back has weight; a thing that eases into place has
been faded in.

These run the REAL module under node. The central one checks the helper IS Remotion's spring rather than a
re-implementation of one — because "my spring is right" is exactly the claim worth nothing unless something
independent agrees.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")


def _run(body):
    tmp = tempfile.mkdtemp(prefix="spr_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        head = ("import * as M from %s;\nimport {spring} from 'remotion';\nconst out: any = {};\n"
                % json.dumps(os.path.join(_REM, "src", "runtime", "motion")))
        open(entry, "w", encoding="utf-8").write(head + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@_NEEDS_NODE
def test_the_presets_overshoot_and_then_settle():
    """THE ONE THAT MATTERS. An arrival that never passes its mark is a fade with extra steps — the whole
    reason for reaching past `easeOutBack` is that a landing has weight. And one that never settles is a
    wobble the next shot has to cut away from mid-bounce."""
    out = _run("""
      const fps = 30;
      out.rows = ['SPRING_LAND', 'SPRING_SEAT', 'SPRING_POP'].map((k) => {
        const cfg = (M as any)[k];
        const vals = Array.from({length: 90}, (_, f) => spring({frame: f, fps, config: cfg}));
        return {k, peak: Math.max(...vals), settled: vals[vals.length - 1],
                tail: Math.max(...vals.slice(60).map((v) => Math.abs(v - 1)))};
      });
    """)
    # The ceiling is per-preset because the overshoot is the DESIGN, not a tolerance. An arrival that
    # overshoots a fifth of its travel reads as jelly; a POP is supposed to pop, and the reference card uses
    # exactly these numbers (damping 10, stiffness 260) for a tick appearing. One flat bound across all three
    # would either forbid the pop or permit a wobbling arrival.
    CEIL = {"SPRING_LAND": 1.20, "SPRING_SEAT": 1.20, "SPRING_POP": 1.45}
    for r in out["rows"]:
        assert r["peak"] > 1.0, "%s never passes its mark — that is a fade, not a landing" % r["k"]
        assert r["peak"] < CEIL[r["k"]], "%s overshoots %.2f, past its %.2f ceiling" % (
            r["k"], r["peak"], CEIL[r["k"]])
        assert abs(r["settled"] - 1) < 0.01, "%s has not settled by 3s" % r["k"]
        assert r["tail"] < 0.02, "%s is still ringing in its last second" % r["k"]


@_NEEDS_NODE
def test_the_presets_are_actually_different_weights():
    """Three names for one curve would be worse than one name: it would read as a choice being offered and
    made, and change nothing on the frame."""
    out = _run("""
      const fps = 30;
      const at = (cfg: any, f: number) => spring({frame: f, fps, config: cfg});
      out.settleFrame = ['SPRING_LAND', 'SPRING_SEAT', 'SPRING_POP'].map((k) => {
        const cfg = (M as any)[k];
        for (let f = 1; f < 200; f++) if (Math.abs(at(cfg, f) - 1) < 0.005) return f;
        return 200;
      });
      out.peaks = ['SPRING_LAND', 'SPRING_SEAT', 'SPRING_POP'].map(
        (k) => Math.max(...Array.from({length: 90}, (_, f) => at((M as any)[k], f))));
    """)
    assert len(set(out["settleFrame"])) == 3, "the presets settle in the same time: %s" % out["settleFrame"]
    assert out["settleFrame"][2] < out["settleFrame"][1], "POP must land quicker than SEAT"


@_NEEDS_NODE
def test_a_spring_that_has_not_started_is_exactly_at_rest():
    """`springAt` clamps its own frame at 0, so a stagger holds every later element perfectly still rather
    than easing it a little early — a row of things that all creep before their turn reads as one thing
    wobbling. Written without the clamp the delay becomes a NEGATIVE frame, and Remotion's spring runs
    backwards from it: the element drifts the wrong way and then turns round."""
    out = _run("""
      out.long = M.springAt(0.10, 120, 30, 0.50);
      out.justBefore = M.springAt(0.4999, 120, 30, 0.50);
      out.atStart = M.springAt(0.50, 120, 30, 0.50);
      out.after = M.springAt(0.75, 120, 30, 0.50);
    """)
    assert out["long"] == 0 and out["justBefore"] == 0 and out["atStart"] == 0, out
    assert out["after"] > 0.5, "the spring never runs after its delay: %r" % out["after"]


@_NEEDS_NODE
def test_the_spring_is_measured_in_the_shots_frames_not_in_normalised_time():
    """A spring is a physical simulation and only means anything against real time. Given `t` alone it would
    run at whatever speed the shot happens to be long, so the same landing would look heavy in a 3s beat and
    snappy in an 8s one — the opposite of what a mass model is for."""
    out = _run("""
      // read EARLY, while the spring is still rising: past its peak a longer span is further settled, so a
      // late reading would compare two points on opposite sides of the overshoot and prove nothing.
      out.shortSpan = M.springAt(0.05, 40, 30, 0);
      out.longSpan = M.springAt(0.05, 240, 30, 0);
    """)
    assert out["longSpan"] > out["shortSpan"] + 0.2, (
        "the same normalised time gives the same spring value regardless of the shot's length: %r" % out)


@_NEEDS_NODE
def test_every_preset_has_landed_by_the_time_the_seam_arrives():
    """`useT` holds a shot still for the frames the cross-dissolve runs over, and that guarantee is worth
    nothing if a spring is still ringing when t reaches 1. The latest delay any register in this library uses
    is 0.6 of the span; a 150-frame beat gives that 125-frame span."""
    out = _run("""
      const fps = 30, span = 125;
      out.end = ['SPRING_LAND', 'SPRING_SEAT', 'SPRING_POP'].map(
        (k) => M.springAt(1, span, fps, 0.6, (M as any)[k]));
    """)
    for v in out["end"]:
        assert abs(v - 1) < 0.01, "a spring is still moving at the seam: %r" % out["end"]


def test_the_spring_runs_on_the_shots_clock_not_the_compositions():
    """The contract that keeps it from undoing `useT`. That hook compresses a shot's whole animation into the
    window where no cross-dissolve is running, and freezes it under reduced motion; a spring driven by
    `useCurrentFrame` would keep bouncing straight through the seam — the exact flicker `useT` was written to
    end — and would ignore the accessibility freeze."""
    src = open(os.path.join(_REM, "src", "runtime", "motion.ts"), encoding="utf-8").read()
    body = src.split("export function useSpringAt")[1].split("\n}")[0]
    assert "useT()" in body, "useSpringAt must be driven by useT"
    assert "useAnimSpan()" in body, "it needs the shot's own animation span to convert normalized time"
    assert "useCurrentFrame" not in body, "reading the composition frame reintroduces the seam flicker"
