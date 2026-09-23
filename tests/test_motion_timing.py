import json, os, shutil, subprocess, tempfile
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REMOTION = os.path.join(ROOT, "remotion")
RUNTIME = os.path.join(REMOTION, "src", "runtime")


def _run(body):
    """Bundle `body` against the REAL motion.ts and run it — the same harness test_ground_light uses."""
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="motion_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        head = ("import * as M from %s;\nconst out: any = {};\n"
                % json.dumps(os.path.join(RUNTIME, "motion")))
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
