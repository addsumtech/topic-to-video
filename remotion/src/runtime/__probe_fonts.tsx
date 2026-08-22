// PROBE — one row per loaded face. Left tile: the family. Right tile: ONLY that family's bare
// generic fallback. If the family did not load, both tiles render the same face and the row's two
// tiles are pixel-identical — which is the single mechanical signal that a silent fallback happened.
// Variable faces get a second probe: a weight ladder. A VF loaded without its weight range clamps,
// so adjacent ladder steps collapse to identical pixels.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FACES} from './fonts';

const SAMPLE = 'Handgloves 0123';

// The generic each family must be distinguishable FROM. A mono face compared against `monospace`
// on a machine whose default mono IS the face would false-pass; these generics are deliberately the
// bare CSS keywords, never a named face.
//
// No fallback default: a family missing from this map would silently compare against e.g.
// 'sans-serif', which differs from a monospace/serif face whether or not it actually loaded — a
// FALSE PASS in the one gate whose entire job is detecting false passes. A missing entry must throw,
// not default, so a later face added to FACES is forced to extend this map.
const GENERIC: Record<string, string> = {
  'JetBrains Mono': 'monospace',
  'Playfair Display': 'serif',
  'Space Grotesk': 'sans-serif',
  Bangers: 'sans-serif',
};

export const DURATION = 1;

export const FontProbe: React.FC<{ladder?: boolean; expectedRows?: number}> = ({ladder = false, expectedRows}) => {
  const rows = FACES.filter((f) => !ladder || f.variable);
  // Cross-check against font_gate.py's regex parse of fonts.ts. That parse is fragile (a future
  // formatting change could make it silently drop a line instead of matching nothing at all), and a
  // row-count mismatch would misalign font_gate.py's crop grid against the ACTUAL rendered rows —
  // corrupting every tile comparison instead of failing loudly. rows.length here comes from real JS
  // module evaluation of FACES, not text-regex, so it is a genuinely independent count: throwing on
  // a mismatch turns a silent misalignment into a hard, named render failure.
  if (expectedRows !== undefined && rows.length !== expectedRows) {
    throw new Error(
      `__probe_fonts: font_gate.py expected ${expectedRows} row(s) but FontProbe actually rendered ${rows.length} — ` +
        `its regex parse of fonts.ts has drifted from the real FACES array; fix the parse before trusting this gate`,
    );
  }
  return (
    <AbsoluteFill style={{background: '#fff', color: '#000', display: 'flex', flexDirection: 'column'}}>
      {rows.map((f) => {
        const generic = GENERIC[f.family];
        if (!generic) {
          throw new Error(
            `__probe_fonts: no generic fallback declared for "${f.family}" — add one, or this gate silently false-passes`,
          );
        }
        return (
          <div key={f.family} style={{flex: 1, display: 'flex'}}>
            <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              // family THEN its generic — a real production font-stack. If the family fails to load,
              // this collapses onto tile B's generic (identical pixels, caught). Naming the family bare
              // with no fallback would instead resolve to Chromium's fixed UA-default face, which
              // differs from tile B's generic regardless of whether the real face loaded — a false pass.
              fontFamily: `${f.family}, ${generic}`, fontWeight: ladder ? 300 : 700, fontSize: 64}}>
              {SAMPLE}
            </div>
            <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: ladder ? f.family : generic,
              fontWeight: ladder ? 700 : 700, fontSize: 64}}>
              {SAMPLE}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default FontProbe;
