"""The tone helpers — the rules that came out of measuring why our frames are empty.

Density has no shared mechanism (four were built and refuted; see density_advice.py). What DOES transfer is a
handful of rules, and these are them, derived from measurements rather than taste:

  * a filled region must clear the density instrument's own ink threshold against what it sits on, or it is
    a composition that is there and invisible (VersusSplit spanned 53% of the frame and inked 3.2%);
  * two regions that COVER the frame create its median between them, so they must separate from each other
    by twice the step, not from the ground (deriving each from the ground moved that register 3.2% → 3.3%);
  * ink is picked by measured contrast against the surface actually under it, never by a mix fraction or an
    overlay's alpha (a fixed 28% dim took secondary text to 2.57:1 on a lightened half).
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


def probe(body):
    if not shutil.which("npx") or not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion toolchain unavailable")
    tmp = tempfile.mkdtemp(prefix="tone_probe_")
    try:
        entry = os.path.join(tmp, "p.tsx")
        head = ("import * as D from %s;\nconst out: any = {};\n"
                "const fail = (k: string, e: unknown) => { out[k] = {threw: String(e)}; };\n"
                % json.dumps(os.path.join(RUNTIME, "dna")))
        open(entry, "w", encoding="utf-8").write(head + body + "\nconsole.log(JSON.stringify(out));\n")
        out = os.path.join(tmp, "p.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--external:react",
                            "--external:remotion", "--outfile=" + out, "--log-level=error"],
                           cwd=REMOTION, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        env = dict(os.environ, NODE_PATH=os.path.join(REMOTION, "node_modules"))
        r = subprocess.run(["node", out], cwd=REMOTION, capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_separated_region_always_clears_the_instruments_own_threshold():
    out = probe("""
      out.rows = [];
      const grounds = ['#060709', '#0a0c12', '#171b28', '#f4f0e6', '#fafafa', '#3d5daa'];
      const towards = ['#5b8cff', '#ffffff', '#000000', '#b8412e', '#4d5b2a'];
      for (const g of grounds) for (const t of towards) {
        try { const c = D.separated(g, t);
              out.rows.push([g, t, c, Math.abs(D.pilL(c) - D.pilL(g))]); }
        catch (e) { out.rows.push([g, t, null, String(e).slice(0, 60)]); }
      }
      out.step = D.TONE_MIN_STEP;
    """)
    ok = [r for r in out["rows"] if r[2]]
    assert len(ok) > 20, out["rows"]
    for g, t, c, step in ok:
        assert step >= out["step"] - 1e-9, "separated(%s,%s)=%s is only %.3f away" % (g, t, c, step)


def test_separating_toward_the_ground_itself_throws_instead_of_painting_nothing():
    """A register asking for a second surface and silently getting the ground back is the invisible-container
    failure this exists to end — measured across all eight presets, whose `surface` token is exactly that."""
    out = probe("try { out.r = D.separated('#445fb0', '#445fb0'); } catch (e) { fail('r', e); }")
    assert isinstance(out["r"], dict) and "never reaches" in out["r"]["threw"], out


def test_a_pair_separates_from_each_other_not_from_the_ground():
    """Ink is measured against the frame's OWN median, so two regions covering the frame create that median
    between them. Deriving each from the ground moved VersusSplit from 3.2% to 3.3%; the pair has to split."""
    out = probe("""
      out.rows = [];
      for (const g of ['#060709', '#0a0c12', '#f4f0e6']) {
        const [a, b] = D.separatedPair(g, '#5b8cff', '#b8412e');
        out.rows.push([g, a, b, Math.abs(D.pilL(a) - D.pilL(b))]);
      }
      out.step = D.TONE_MIN_STEP;
    """)
    for g, a, b, gap in out["rows"]:
        assert gap >= out["step"] * 2, "pair on %s is only %.3f apart (%s vs %s)" % (g, gap, a, b)


def test_ink_is_picked_by_measured_contrast_not_by_a_rule_of_thumb():
    out = probe("""
      out.dark = D.readableOn('#0a0c12', '#ffffff', '#05070c');
      out.light = D.readableOn('#f4f0e6', '#ffffff', '#05070c');
      out.mid = D.readableOn('#445fb0', '#ffffff', '#05070c');
      out.midC = [D.contrastOf('#ffffff', '#445fb0'), D.contrastOf('#05070c', '#445fb0')];
    """)
    assert out["dark"] == "#ffffff" and out["light"] == "#05070c"
    assert out["mid"] == ("#ffffff" if out["midC"][0] >= out["midC"][1] else "#05070c")


def test_the_dim_tier_never_falls_through_its_contrast_floor():
    """A fixed fraction is a bet on how light the ground is, and it loses on the grounds this work adds:
    a 28% dim took secondary text from 4.54:1 to 2.57:1 on a lightened half."""
    out = probe("""
      out.rows = [];
      for (const g of ['#060709', '#171b28', '#445fb0', '#f4f0e6', '#b8412e']) {
        const ink = D.readableOn(g, '#ffffff', '#05070c');
        const d = D.dimOn(g, ink);
        out.rows.push([g, ink, d, D.contrastOf(d, g), D.contrastOf(ink, g)]);
      }
    """)
    for g, ink, d, cd, ci in out["rows"]:
        assert cd >= 4.5 - 1e-6, "dimOn on %s gives %s at %.2f:1" % (g, d, cd)
        assert cd <= ci + 1e-9, "dimOn brightened the ink on %s" % g


def test_the_two_colour_models_are_kept_apart():
    """`pilL` answers what the density instrument counts; `relLum` answers what an eye reads. Collapsing them
    would optimise legibility for the gate."""
    out = probe("""
      out.rows = ['#ff0000', '#00ff00', '#0000ff', '#808080'].map((c) => [c, D.pilL(c), D.relLum(c)]);
    """)
    diffs = [abs(p - r) for _c, p, r in out["rows"]]
    assert max(diffs) > 0.1, "pilL and relLum agree everywhere — one of them is not what it claims: %r" % out
