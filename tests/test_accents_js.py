"""assets/html/accents.js: every accent is a pure function of (t, seed) — the same frame twice is the same picture —
it ends when its life ends, and nothing it draws returns to an earlier state (no overshoot: rewind_qa reads a
grow-past-and-shrink-back as the picture going back)."""
import json
import os
import shutil
import subprocess

import pytest

JS = os.path.join(os.path.dirname(__file__), "..", "assets", "html", "accents.js")

PROBE = r"""
const A = require(process.argv[2]);
const r = {};
const b1 = A.burst(0.4, {x: 960, y: 540, seed: 3}), b2 = A.burst(0.4, {x: 960, y: 540, seed: 3});
r.burst_pure = JSON.stringify(b1) === JSON.stringify(b2);
r.burst_seed_matters = JSON.stringify(b1) !== JSON.stringify(A.burst(0.4, {x: 960, y: 540, seed: 4}));
r.burst_count = b1.length;
r.burst_ends = A.burst(1.2, {}).length === 0 && A.burst(-0.01, {}).length === 0;
r.burst_starts_at_origin = A.burst(0, {x: 10, y: 20}).every(p => Math.abs(p.x - 10) < 1e-9 && Math.abs(p.y - 20) < 1e-9);
// particles fly outward: horizontal distance from the origin never shrinks
let out = true, prev = null;
for (let f = 0; f < 36; f++) {
  const ps = A.burst(f / 30, {x: 0, y: 0, seed: 9});
  if (prev) for (let i = 0; i < ps.length; i++) if (Math.abs(ps[i].x) + 1e-9 < Math.abs(prev[i].x)) out = false;
  prev = ps;
}
r.burst_outward = out;
// pop: scale and alpha never decrease, never exceed 1
let mono = true, cap = true, last = {scale: 0, alpha: 0};
for (let f = 0; f <= 30; f++) {
  const p = A.pop(f / 30, 0.35);
  if (p.scale < last.scale - 1e-12 || p.alpha < last.alpha - 1e-12) mono = false;
  if (p.scale > 1 + 1e-12 || p.alpha > 1 + 1e-12) cap = false;
  last = p;
}
r.pop_monotone = mono; r.pop_capped = cap;
// countUp lands exactly and never goes back
let cm = true, lv = -Infinity;
for (let f = 0; f <= 45; f++) { const v = A.countUp(f / 30, 0, 97, 1.2, 0); if (v < lv) cm = false; lv = v; }
r.count_monotone = cm; r.count_lands = A.countUp(1.2, 0, 97, 1.2, 0) === 97;
// sparkle stars only grow
let sg = true, sp = null;
for (let f = 0; f < 24; f++) {
  const s = A.sparkle(f / 30, {seed: 2, count: 1});
  if (s.length && sp && s[0].scale + 1e-12 < sp.scale) sg = false;
  if (s.length) sp = s[0];
}
r.sparkle_grows = sg;
// ring only grows and fades; rays' both ends only travel outward; both end on time
let rg = true, rl = null, ro = true, pr = null;
for (let f = 0; f < 18; f++) {
  const g = A.ring(f / 30, {x: 0, y: 0});
  if (g && rl && (g.r < rl.r - 1e-9 || g.alpha > rl.alpha + 1e-9)) rg = false;
  if (g) rl = g;
  const ys = A.rays(f / 30, {x: 0, y: 0, seed: 1});
  if (pr && ys.length) for (let i = 0; i < ys.length; i++) {
    if (Math.hypot(ys[i].x1, ys[i].y1) + 1e-9 < Math.hypot(pr[i].x1, pr[i].y1)) ro = false;
    if (Math.hypot(ys[i].x2, ys[i].y2) + 1e-9 < Math.hypot(pr[i].x2, pr[i].y2)) ro = false;
  }
  if (ys.length) pr = ys;
}
r.ring_grows = rg; r.rays_outward = ro;
r.ends = A.ring(0.6, {}) === null && A.rays(0.35, {}).length === 0;
console.log(JSON.stringify(r));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_accents_are_pure_finite_and_never_go_back(tmp_path):
    probe = tmp_path / "probe.js"
    probe.write_text(PROBE, encoding="utf-8")
    out = subprocess.run(["node", str(probe), os.path.abspath(JS)], capture_output=True, text=True, check=True)
    r = json.loads(out.stdout)
    assert r.pop("burst_count") == 36
    assert all(r.values()), r


def test_skill_md_points_at_the_accents():
    skill = open(os.path.join(os.path.dirname(__file__), "..", "SKILL.md"), encoding="utf-8").read()
    assert "assets/html/accents.js" in skill
