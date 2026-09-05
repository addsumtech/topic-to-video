"""The camera must be able to TRANSLATE, and must never do it by accident.

MEASURED, which is why this exists. A scale-only camera barely moves a frame: pixels near the transform
origin travel almost nothing, and most of a composed frame's content sits near the middle. Stamping the
existing camera on every beat of the delivered 30-beat film took its frame-diff p75 from 0.0022 to 0.0029 —
under the 0.0037 floor — while the same film under a constant-velocity lateral pan measured 0.0040. The
missing operation was a translate.

THE DEFAULT WAS REVERSED, deliberately and with evidence, after the shake instrumentation existed. The old
rule here read "a pan that appeared on its own would be a regression, not a feature" — correct for its time,
because shake could not then be proven absent, so the only safe camera was none: a floor on shake bought
with a ceiling on motion. What changed is that the ceiling's cost became measurable and the floor became
provable. Measured on the same six-beat themed film: the planner's punctuation covers ~10% of a real film's
runtime while the p75 delivery gate needs motion on >25% of frames (mathematically out of reach); the
ambient drift adds +9%; the camera BED — bedPan()'s slow lateral drift on beats nobody authored a camera
for — takes the film from 0.0035 to 0.0042 (over the 0.0037 floor) at wander p90 1.46 with local flicker
DOWN (17% -> 15%), byte-identical across renders, and an un-themed film pixel-identical to before. Shake is
now refused structurally (panAt is monotone: within a beat the frame travels, never vibrates) and checked
per delivery (scripts/shake_qa.py), instead of being prevented by keeping the camera dead.

Everything below still holds: an AUTHORED camera — even `hold` — wins outright, the pan stays monotone,
edge-safe and caption-bounded, reduced motion zeroes it, and the ambient drift and the bed refuse to
coexist.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
REMOTION = os.path.join(os.path.dirname(_HERE), "remotion")
RUNTIME = os.path.join(REMOTION, "src", "runtime")


def run_probe(body):
    """Bundle `body` against the REAL depth.tsx and run it — behaviour, not the presence of code."""
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="cam_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        header = ("import * as C from %s;\nconst out: any = {};\n"
                  "const fail = (k: string, e: unknown) => { out[k] = {threw: String(e)}; };\n"
                  % json.dumps(os.path.join(RUNTIME, "depth")))
        open(entry, "w", encoding="utf-8").write(header + body + "\nconsole.log(JSON.stringify(out));\n")
        out = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node",
                            "--external:react", "--external:remotion", "--outfile=" + out,
                            "--log-level=error"], cwd=REMOTION, capture_output=True, text=True)
        assert b.returncode == 0, "esbuild failed:\n" + b.stdout + b.stderr
        env = dict(os.environ, NODE_PATH=os.path.join(REMOTION, "node_modules"))
        r = subprocess.run(["node", out], cwd=REMOTION, capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_pan_declared_is_no_pan():
    """The backward-compat contract at its source. A film that says nothing must render as it always did."""
    out = run_probe("""
      out.undef = C.clampPan(undefined);
      out.nul = C.clampPan(null);
      out.zero = C.clampPan([0, 0]);
    """)
    assert out["undef"] is None and out["nul"] is None and out["zero"] is None


@pytest.mark.parametrize("bad", ['"0.5"', "[1]", "[1,2,3]", "[1,NaN]", "[Infinity,0]", "{}", "[null,0]", "5"])
def test_a_malformed_pan_throws_instead_of_silently_holding(bad):
    """A camera that quietly does nothing is the failure this runtime keeps finding — a pan that cannot be
    read must say so, not hold."""
    out = run_probe("try { out.r = C.clampPan(%s as any); } catch (e) { fail('r', e); }" % bad)
    assert isinstance(out["r"], dict) and "threw" in out["r"], out
    assert "pan must be" in out["r"]["threw"], out["r"]


def test_a_pan_is_clamped_to_the_overscan_it_can_afford():
    out = run_probe("out.big = C.clampPan([4, -9]); out.ok = C.clampPan([0.5, -0.25]);")
    assert out["big"] == [1, -1]
    assert out["ok"] == [0.5, -0.25]


def test_the_travel_is_centred_and_starts_and_ends_at_rest():
    """Centred so a pan does not bias the composition to one side, and at rest at both ends so a
    cross-dissolve never runs over a moving frame."""
    out = run_probe("""
      out.series = [];
      for (let i = 0; i <= 20; i++) out.series.push(C.panAt(i / 20));
    """)
    s = out["series"]
    assert abs(s[0] + 0.5) < 1e-6 and abs(s[-1] - 0.5) < 1e-6, s
    assert all(b >= a - 1e-9 for a, b in zip(s, s[1:])), "the travel reverses: %r" % s
    # at rest at the ends: the first and last steps are far smaller than the middle one
    mid = s[11] - s[10]
    assert (s[1] - s[0]) < mid * 0.5 and (s[-1] - s[-2]) < mid * 0.5, s


def test_the_travel_is_constant_velocity_through_the_middle():
    """The measured reason a scale-only camera failed: an ease-in-out spends most of its frames at the flat
    ends, which is where the motion went missing."""
    out = run_probe("""
      out.series = [];
      for (let i = 0; i <= 40; i++) out.series.push(C.panAt(i / 40));
    """)
    s = out["series"]
    steps = [b - a for a, b in zip(s, s[1:])][8:-8]
    assert max(steps) - min(steps) < max(steps) * 0.05, "the middle of the travel is not steady: %r" % steps


def test_the_travel_can_never_oscillate():
    """SHAKE IS OSCILLATION, not movement. A monotone travel cannot shake however large it is, so this is the
    property that makes the guarantee — pinned over a fine sampling, not eyeballed on a contact sheet."""
    out = run_probe("""
      out.series = [];
      for (let i = 0; i <= 600; i++) out.series.push(C.panAt(i / 600));
    """)
    s = out["series"]
    back = [(a, b) for a, b in zip(s, s[1:]) if b < a - 1e-12]
    assert not back, "the travel reverses %d time(s) — that is a shake: %r" % (len(back), back[:3])


def test_a_film_cannot_declare_both_an_oscillating_drift_and_a_travelling_pan(tmp_path):
    """The whole-film drift is three sines; a pan is a ramp. Together they read as shake, and Film.tsx
    refuses the combination. Driven through a REAL render rather than a source grep — a grep would pass on a
    file that mentions the words and no longer throws, which is the shape of check this repo keeps finding
    broken."""
    if not shutil.which("npx") or not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion toolchain unavailable")

    def render(drift):
        props = tmp_path / ("p%s.json" % drift)
        props.write_text(json.dumps({
            "scenes": [{"shot": "LastLeg", "durF": 60, "caption": "x",
                        "camera": {"move": "push", "pan": [0.6, 0.2]}},
                       {"shot": "LastLeg", "durF": 60, "caption": "y"}],
            "camera": drift, "aspect": "16:9", "captions": True}), encoding="utf-8")
        r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film",
                            str(tmp_path / ("out%s.png" % drift)), "--frame=30",
                            "--props=" + str(props), "--gl=angle", "--log=error"],
                           cwd=REMOTION, capture_output=True, text=True)
        return (r.stdout or "") + (r.stderr or ""), os.path.exists(tmp_path / ("out%s.png" % drift))

    blob, made = render(1.0)
    assert not made and "read as shake" in blob, "drift + pan rendered instead of being refused"
    _blob, made = render(0.0)
    assert made, "a pan on its own must still render"


def test_the_bed_rules_are_exactly_the_promised_ones():
    """bedPan is the reversal's contract: WHO gets the default drift, pinned as behaviour."""
    out = run_probe("""
try {
  out.themed = C.bedPan(2, true, 0, null);
  out.unthemed = C.bedPan(2, false, 0, null);
  out.authored = C.bedPan(2, true, 0, {move: 'hold'});
  out.drifting = C.bedPan(2, true, 1.0, null);
  out.disabled = C.bedPan(2, true, 0, null, false);
  out.again = C.bedPan(2, true, 0, null);
  out.next = C.bedPan(3, true, 0, null);
} catch (e) { fail('bed', e); }
""")
    assert out["themed"] and out["themed"]["bed"] is True, out
    assert out["unthemed"] is None, "an un-themed film grew a camera (null-DNA rule)"
    assert out["authored"] is None, "an authored camera — even hold — must win outright"
    assert out["drifting"] is None, "the bed coexisted with the ambient drift (the shake guard's case)"
    assert out["disabled"] is None, "meta.camera_bed:false did not switch it off"
    assert out["again"] == out["themed"], "the bed is not deterministic"
    dx2, dx3 = out["themed"]["pan"][0], out["next"]["pan"][0]
    assert dx2 * dx3 < 0, "adjacent beats drift the same way — one long pan a cut keeps interrupting"
    assert out["themed"]["pan"][1] < 0, "the bed drifts DOWNWARD — that is the caption's direction"


def test_the_bed_amplitude_stays_under_a_motivated_move():
    """Punctuation stays punctuation only while the bed is quieter than a move with a cause."""
    import re
    src = open(os.path.join(RUNTIME, "depth.tsx"), encoding="utf-8").read()
    m = re.search(r"BED_AMOUNT_FRAC = ([\d.]+)", src)
    assert m and float(m.group(1)) < 0.75, "the bed takes as much of the cap as a motivated move"
