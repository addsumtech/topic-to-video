import json, os, re, shutil, subprocess, tempfile
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REMOTION = os.path.join(ROOT, "remotion")
RUNTIME = os.path.join(REMOTION, "src", "runtime")


def _run(body, module="motion"):
    """Bundle `body` against the REAL runtime module and run it — the harness test_ground_light uses.

    `module` is the runtime file the probe imports as `M`; the rhythm primitives live in `motion` and the
    drawing ones in `draw`, and both are pinned here because both are read by registers as rules."""
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="motion_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        head = ("import * as M from %s;\nconst out: any = {};\n"
                % json.dumps(os.path.join(RUNTIME, module)))
        open(entry, "w", encoding="utf-8").write(head + body + "\nconsole.log(JSON.stringify(out));\n")
        outfile = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node",
                            "--external:react", "--external:remotion", "--outfile=" + outfile,
                            "--log-level=error"], cwd=REMOTION, capture_output=True, text=True)
        assert b.returncode == 0, "esbuild failed:\n" + b.stdout + b.stderr
        env = dict(os.environ, NODE_PATH=os.path.join(REMOTION, "node_modules"))
        r = subprocess.run(["node", outfile], cwd=REMOTION, capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cadence_lands_in_discrete_steps_and_the_intervals_carry_the_rhythm():
    """`cadence` is the one thing `motion.ts` could not say: DISCRETE advance. Every other easing there is
    continuous, and an audit of a peer library recorded that this one escaped "uniform motion reads as
    cheap PowerPoint" by easing 121 of 152 registers — smooth everywhere being its own uniformity.

    Four properties. The third is what a naive `floor(t*n)/n` gets wrong — the value would show (n-1)/n
    for the entire shot and land only on the final frame, a settled frame one step short, which is the
    class of defect `scripts/settled_frame.py` exists because of. The fourth is why this is `cadence` and
    not `stepped`: it is the INTERVALS that carry a rhythm, and writing only the metronome would have left
    the accelerating cut to be hand-rolled by the next register that wanted it."""
    r = _run("""
      const grid = (n: number, a = 1) => Array.from({length: 201}, (_, i) => M.cadence(i / 200, n, a));
      out.n2 = grid(2); out.n3 = grid(3); out.n4 = grid(4); out.n6 = grid(6);
      out.fast = grid(5, 1.8); out.slow = grid(5, 0.6); out.even = grid(5, 1);
      out.stepped_matches = Array.from({length: 101}, (_, i) =>
        [2, 3, 4, 6].every((n) => Math.abs(M.stepped(i / 100, n) - M.cadence(i / 100, n, 1)) < 1e-9));
      out.edges = [M.cadence(-1, 3), M.cadence(0, 3), M.cadence(1, 3), M.cadence(2, 3),
                   M.cadence(0.5, 1), M.cadence(0.5, 0), M.cadence(0.5, 4, 99), M.cadence(0.5, 4, -5)];
      out.composes = [M.easeOutCubic(M.cadence(0.0, 4)), M.easeOutCubic(M.cadence(0.5, 4)),
                      M.easeOutCubic(M.cadence(1.0, 4))];
    """)

    def landings(vals):
        out, prev = [], None
        for i, v in enumerate(vals):
            if v != prev:
                out.append(i / 200.0)
                prev = v
        return out

    for n in (2, 3, 4, 6):
        vals = r["n%d" % n]
        uniq = sorted(set(round(v, 6) for v in vals))
        # 1. exactly n distinct values, from 0 to 1
        assert len(uniq) == n, "steps=%d produced %d distinct values: %r" % (n, len(uniq), uniq)
        assert uniq[0] == 0.0 and uniq[-1] == 1.0, uniq
        # 2. monotone — a landing that goes backwards is a stutter, not a rhythm
        assert all(b >= a for a, b in zip(vals, vals[1:])), "steps=%d is not monotone" % n
        # 3. LANDS EARLY AND HOLDS: 1 is reached at (n-1)/n, not on the last frame
        first_one = next(i for i, v in enumerate(vals) if v >= 1.0) / 200.0
        assert abs(first_one - (n - 1) / n) < 0.02, (
            "steps=%d reaches 1 at t=%.2f, expected ~%.2f — a settled frame one step short"
            % (n, first_one, (n - 1) / n))

    # 4. THE INTERVALS ARE THE POINT. accel > 1 must shrink them monotonically, accel < 1 stretch them,
    #    accel == 1 hold them even — and all three must still finish at the same last landing.
    def gaps(vals):
        L = landings(vals)
        return [round(L[i + 1] - L[i], 4) for i in range(len(L) - 1)]

    fast, slow, even = gaps(r["fast"]), gaps(r["slow"]), gaps(r["even"])
    assert len(fast) == len(slow) == len(even) == 4, (fast, slow, even)
    assert all(b < a for a, b in zip(fast, fast[1:])), "accel>1 did not shrink the intervals: %r" % fast
    assert all(b > a for a, b in zip(slow, slow[1:])), "accel<1 did not stretch the intervals: %r" % slow
    assert max(even) - min(even) < 1e-6, "accel==1 is not a metronome: %r" % even
    for g in (fast, slow, even):
        assert abs(sum(g) - 0.8) < 0.02, "the last landing moved with accel: %r" % g

    assert all(r["stepped_matches"]), "`stepped` is not `cadence` at accel=1"
    # every edge resolves rather than throwing or dividing by zero
    assert r["edges"][:4] == [0.0, 0.0, 1.0, 1.0], r["edges"]
    assert all(0.0 <= v <= 1.0 for v in r["edges"]), r["edges"]
    # it quantises TIME, so it composes with the easings rather than replacing them
    a, b, c = r["composes"]
    assert a == 0.0 and c == 1.0 and 0.0 < b < 1.0, r["composes"]


def test_the_landing_series_is_one_definition_that_cadence_itself_reads():
    """`cadenceAt` exists because a register that DRAWS a rhythm has to place its marks at the same moments
    the rhythm lands them — `Escalation` puts a mark's x at its landing time. The first build of that
    register computed the positions from the same parameters in its own file, which is a second copy of a
    rule: this repo's caption band once had four disagreeing definitions that way, and a test pinning two
    copies together is a weaker answer than not having two.

    So what is asserted is that `cadence` is DERIVED from `cadenceAt` — every landing the series names is a
    moment the walker steps at, and it steps nowhere else."""
    r = _run("""
      out.series = {};
      out.walks = {};
      for (const key of ["3|1", "5|1.8", "4|0.6", "7|3"]) {
        const [n, a] = key.split("|").map(Number);
        out.series[key] = M.cadenceAt(n, a);
        out.walks[key] = Array.from({length: 1001}, (_, i) => M.cadence(i / 1000, n, a));
      }
    """)
    for key, pos in r["series"].items():
        n, a = [float(x) for x in key.split("|")]
        n = int(n)
        assert len(pos) == n and pos[0] == 0.0 and abs(pos[-1] - 1.0) < 1e-9, (key, pos)
        walk = r["walks"][key]
        # every step the walker takes must be AT a named landing, scaled by (n-1)/n — no step of its own
        last = (n - 1) / n
        steps = sorted({i / 1000.0 for i in range(1, 1001) if walk[i] != walk[i - 1]})
        want = [p * last for p in pos[1:]]
        assert len(steps) == len(want), "%s: walker took %d steps for %d landings" % (key, len(steps), len(want))
        for got, exp in zip(steps, want):
            assert abs(got - exp) <= 0.002, "%s: a step at %.3f is not a landing (%.3f)" % (key, got, exp)


def test_a_speed_ramp_is_monotone_lands_on_its_endpoints_and_spends_the_time_it_claims():
    """A ramp that is not monotone runs the shot BACKWARDS for a stretch, and nothing would catch it.

    The property that makes it a ramp rather than an ease is arithmetic, not visual: `factor` has to be the
    number a film can say out loud — "that stretch plays at a third speed" — or two registers reaching for a
    slow-down each pick their own curve and the library has two definitions of the same idea, which is the
    failure `cadenceAt` already carries a note about. So this checks the SPEED, by differencing the remap:
    inside the window the shot must advance about `factor`× less per unit time than outside it.
    """
    r = _run("""
const grid = Array.from({length: 401}, (_, i) => i / 400);
out.ramp = grid.map((t) => M.speedRamp(t, 0.5, 0.2, 3));
out.identity_f1 = grid.every((t) => Math.abs(M.speedRamp(t, 0.5, 0.2, 1) - t) < 1e-12);
out.identity_w0 = grid.every((t) => Math.abs(M.speedRamp(t, 0.5, 0, 3) - t) < 1e-12);
// the window pushed past either end must still land on its endpoints
out.edges = [M.speedRamp(0, 0.02, 0.3, 4), M.speedRamp(1, 0.02, 0.3, 4),
             M.speedRamp(0, 0.98, 0.3, 4), M.speedRamp(1, 0.98, 0.3, 4)];
// out-of-range arguments are clamped, never NaN
out.wild = [M.speedRamp(-1, 0.5, 0.2, 3), M.speedRamp(2, 0.5, 0.2, 3),
            M.speedRamp(0.5, 5, 9, 1e9), M.speedRamp(0.5, -3, -1, -7)];
""")
    v = r["ramp"]
    assert abs(v[0]) < 1e-9 and abs(v[-1] - 1) < 1e-9, (v[0], v[-1])
    assert all(b >= a - 1e-12 for a, b in zip(v, v[1:])), "the ramp runs the shot backwards somewhere"
    assert r["identity_f1"], "factor=1 is not the identity — a register would have to branch around it"
    assert r["identity_w0"], "width=0 is not the identity"
    assert r["edges"][:2] == [0.0, 1.0] and r["edges"][2:] == [0.0, 1.0], r["edges"]
    assert all(isinstance(x, (int, float)) and not isinstance(x, bool)
               and 0.0 <= x <= 1.0 for x in r["wild"]), r["wild"]

    # THE CLAIM ITSELF: the middle really does run ~3x slower than the ends.
    step = 1 / 400
    mid = [(b - a) / step for a, b in zip(v[195:205], v[196:206])]       # centre of the window
    out = [(b - a) / step for a, b in zip(v[0:20], v[1:21])]             # well outside it
    assert 0.9 < (sum(out) / len(out)) / (sum(mid) / len(mid)) / 3 < 1.1, (
        "the slow stretch does not run at 1/factor speed: outside=%.4f inside=%.4f"
        % (sum(out) / len(out), sum(mid) / len(mid)))


def test_line_boil_cycles_a_few_drawings_at_a_rate_that_does_not_depend_on_the_frame_rate():
    """A hand-drawn register whose jitter is seeded by the SHAPE index holds perfectly still — which is the
    one thing a hand cannot do, and the stillness is what reads as digital.

    Two properties make it boil rather than fizz. It CYCLES a small set of drawings, because an animator
    redraws the same shape two or three times and the eye keeps recognising them; a fresh variant every
    step is television snow. And its rate is in HERTZ, not frames, because the rate is a property of the
    eye: pinned to "every 3 frames" the same shot boils twice as fast on a 60fps film as on a 30fps one.
    """
    r = _run("""
const sample = (fps, durS, hz, phases) => {
  const durF = Math.round(durS * fps);
  return Array.from({length: durF}, (_, f) => M.boilPhase(f / (durF - 1), durF, fps, hz, phases));
};
out.at30 = sample(30, 3, 10, 3);
out.at60 = sample(60, 3, 10, 3);
out.two  = sample(30, 3, 10, 2);
out.deterministic = M.boilPhase(0.37, 165, 30) === M.boilPhase(0.37, 165, 30);
out.clamped_phases = new Set(sample(30, 3, 10, 99)).size;   // past BOIL_PHASES_MAX
out.refused = [];
for (const hz of [0, 1, 3.9, 15.1, 60, -4, NaN]) {
  try { M.boilPhase(0.5, 90, 30, hz); out.refused.push(false); }
  catch (e) { out.refused.push(String(e.message).includes('television snow')
                               || String(e.message).includes('slideshow')); }
}
""", module="draw")

    assert r["deterministic"], "the same frame gives two different drawings — the render is not reproducible"
    assert sorted(set(r["at30"])) == [0, 1, 2], "three phases were asked for and not cycled: %r" % sorted(set(r["at30"]))
    assert sorted(set(r["two"])) == [0, 1], sorted(set(r["two"]))
    assert r["clamped_phases"] <= 4, "phases is not clamped to BOIL_PHASES_MAX: %d" % r["clamped_phases"]
    assert all(r["refused"]), "a rate outside the readable band was accepted: %r" % r["refused"]

    # THE RATE ITSELF: ~10 redraws per second over a 3s shot, at BOTH frame rates.
    def redraws(seq):
        return sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    n30, n60 = redraws(r["at30"]), redraws(r["at60"])
    assert 27 <= n30 <= 31, "10Hz over 3s is ~29 redraws, got %d at 30fps" % n30
    assert abs(n30 - n60) <= 1, (
        "the boil rate follows the frame rate instead of the clock: %d redraws at 30fps, %d at 60fps"
        % (n30, n60))


# ── a reveal the settled frame cannot see ────────────────────────────────────────────────────────────
#
# `useT()` returns exactly REDUCED_MOTION_T under reduced motion, and motion.ts says why that value was
# picked: 0.86 "lands in the 'reveal complete, exit not begun' zone". So a window that only OPENS at or
# after 0.86 is at opacity exactly 0 in the frame the accessibility render freezes on — and in every still
# the gates inspect, because shot_still_qa, ink_contrast_qa and cjk_type_qa all capture the settled frame.
# The element is not dim there. It does not exist: its contrast is never measured, its type is never
# checked for overflow, and `--reduced-motion` ships the beat without it.
#
# Found by rendering seven registers this session and looking at them. Three (AverageHides, CraneUp,
# HeldInstant) opened their closing line at seg(t, 0.86, 0.96) — the only 3 of 158 in the library — and on
# CraneUp the kicker's fade-out completed at 0.86 as well, so the settled frame carried no words at all.
# The other four opened at 0.82–0.84, which is 20–40% opacity at that frame: a sentence the viewer gets
# about a quarter of a second of, at full strength, before the outgoing dissolve starts.
#
# The rule gated here is the BINARY one, because it is the one with no judgement in it. "Complete by 0.86"
# would name 69 registers, most of them slow settles that are 70%+ in and perfectly visible — that is a
# redesign, not a gate.
_LATE = re.compile(r"seg\(\s*t\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)")


def _windows_that_never_open(src, settled):
    """[(start, end)] for every reveal window this source opens at or after the settled frame."""
    return [(float(m.group(1)), float(m.group(2))) for m in _LATE.finditer(src)
            if float(m.group(1)) >= settled]


def test_no_register_reveals_something_the_settled_frame_cannot_see():
    settled = float(re.search(r"REDUCED_MOTION_T\s*=\s*([0-9.]+)",
                              open(os.path.join(RUNTIME, "motion.ts"), encoding="utf-8").read()).group(1))

    # the detector first, on a source built to violate it — a sweep that cannot fail is not a sweep
    assert _windows_that_never_open("const noteIn = clamp01(seg(t, %g, 0.96));" % settled, settled), (
        "the detector does not flag a window opening exactly at the settled frame, so the sweep below "
        "would pass whatever the library does")
    assert not _windows_that_never_open("const noteIn = clamp01(seg(t, 0.72, 0.84));", settled)

    shots = os.path.join(REMOTION, "src", "shots")
    bad = []
    for f in sorted(os.listdir(shots)):
        if not f.endswith(".tsx"):
            continue
        late = _windows_that_never_open(open(os.path.join(shots, f), encoding="utf-8").read(), settled)
        if late:
            bad.append("%s %s" % (f[:-4], ", ".join("seg(t, %g, %g)" % w for w in late)))
    assert not bad, (
        "%d register(s) open a reveal at or after t=%g, which is the frame `--reduced-motion` freezes on "
        "and the frame every still gate measures — the element is at opacity 0 there, so it ships in "
        "neither:\n  %s" % (len(bad), settled, "\n  ".join(bad)))
