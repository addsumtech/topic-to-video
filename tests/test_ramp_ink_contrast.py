"""A light<->dark ground ramp keeps its content readable on every frame, not only at its ends.

THE DEFECT, MEASURED. runtime/light.tsx's mixGround mixed every colour token across a ramp, so inks chosen to
read on opposite grounds passed through the ground's own tone at the moment the ground did: over the eight DNA
presets ramping to paper/gallery/clay/olive/#05060a, the mixed fg fell to 1.01:1 (cinematic -> paper, p 0.5) and
dim, line, outline and both accents to 1.0:1. Only the burned caption picked its ink per frame. Now each token is
picked per frame the same way: the mixed value while it clears its floor, otherwise the value the frame's ground
derives (validate.py's warning from 2177912 named the symptom before the render; this is the cure).
"""
import pytest

import _tsprobe

pytestmark = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")

_BODY = r'''
const C = (a: string, b: string) => { const x = lumValue(a)!, y = lumValue(b)!;
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
const worst: any = {};
const note = (k: string, v: number, at: string) => { if (!(k in worst) || v < worst[k].v) worst[k] = {v, at}; };
for (const [name, dna] of Object.entries(DNA_PRESETS)) {
  for (const to of ['paper', 'gallery', 'clay', 'olive', {bg: '#05060a'}]) {
    let a: any, b: any;
    try { a = resolveRef(dna as any, {bg: (dna as any).bg} as any); b = resolveRef(dna as any, to as any); }
    catch { continue; }
    for (let i = 1; i < 40; i++) {
      const p = i / 40, g: any = mixGround(a, b, p), at = `${name}->${JSON.stringify(to)} p=${p}`;
      note('fg', C(g.fg, g.bg), at);
      note('dim', C(g.dim, g.bg), at);
      note('accent', Math.min(C(g.accent, g.bg), C(g.accent2, g.bg)), at);
      note('onAccent', C(g.onAccent, g.accent), at);
      for (const k of ['line', 'surfaceBorder', 'surface'])
        note('rel_' + k, C(g[k], g.bg) / Math.min(C(a[k], a.bg), C(b[k], b.bg)), at);
    }
    out.ends = (out.ends ?? true) && mixGround(a, b, 0) === a && mixGround(a, b, 1) === b;
  }
}
out.worst = worst;
'''


def test_every_ramp_frame_clears_the_resting_floors():
    out = _tsprobe.run_ts(
        "import {DNA_PRESETS} from %s;\nimport {mixGround, resolveRef} from %s;\nimport {lumValue} from %s;"
        % (_tsprobe.mod("dna"), _tsprobe.mod("light"), _tsprobe.mod("shotLuma")), _BODY)
    w = out["worst"]
    assert w["fg"]["v"] >= 4.5 - 1e-6, w["fg"]          # INK_CONTRAST_MIN (was 1.01 mid-ramp)
    assert w["dim"]["v"] >= 2.4 - 1e-6, w["dim"]        # DIM_CONTRAST_MIN
    assert w["accent"]["v"] >= 3.0 - 1e-6, w["accent"]  # ACCENT_CONTRAST_MIN
    assert w["onAccent"]["v"] >= 4.5 - 1e-6, w["onAccent"]
    for k in ("rel_line", "rel_surfaceBorder", "rel_surface"):   # rules and fills: as visible as the weaker end
        assert w[k]["v"] >= 1 - 1e-6, (k, w[k])
    assert out["ends"], "a ramp's parked ends must stay exactly the resolved grounds"
