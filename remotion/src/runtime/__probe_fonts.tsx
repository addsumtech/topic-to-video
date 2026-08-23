// PROBE — one row per loaded face. Left tile: the family. Right tile: ONLY that family's bare
// generic fallback. If the family did not load, both tiles render the same face and the row's two
// tiles are pixel-identical — which is the single mechanical signal that a silent fallback happened.
// Variable faces get a second probe: a weight ladder. A VF loaded without its weight range clamps,
// so adjacent ladder steps collapse to identical pixels.
//
// KNOWN BLIND SPOT: this only detects a fallback to the bare GENERIC (serif/sans-serif/monospace). If
// the family name also matches a font already installed on the render host, a failed loadFont() still
// resolves tile A to THAT system font — a different face from tile B's generic, so the row still
// "differs" and font_gate.py false-passes. Reproduced with "Baloo 2": macOS ships a system font of
// that exact name (Baloo-Devanagari.ttc), so this probe cannot tell the bundled Google Baloo 2 apart
// from Apple's Devanagari cut on such a host. See scripts/font_gate.py's module docstring.
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
  Inter: 'sans-serif',
  'Source Serif 4': 'serif',
  'IBM Plex Sans': 'sans-serif',
  'IBM Plex Mono': 'monospace',
  'Bodoni Moda': 'serif',
  'Baloo 2': 'sans-serif',
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
        // Always quote the family in the CSS value. A bare (unquoted) font-family value is only
        // valid CSS when every space-separated token is a legal identifier — a token that is pure
        // digits (e.g. the "4" in "Source Serif 4", the "2" in "Baloo 2") is NOT a legal identifier,
        // so the unquoted form is invalid CSS and the browser drops the whole declaration, silently
        // falling back to the inherited/UA default font. That default can coincidentally differ from
        // tile B's bare generic (a false PASS — this hit "Baloo 2" until quoting was added, since
        // Chromium's UA-default serif differs from the sans-serif generic) or coincidentally equal it
        // (a hard, correctly-caught FAIL — this hit "Source Serif 4", whose UA-default fallback IS a
        // serif, identical to tile B's bare "serif"). Quoting is always valid CSS, for every family
        // name, so it is applied unconditionally rather than only for the names known to need it.
        const quoted = `"${f.family}"`;
        return (
          <div key={f.family} style={{flex: 1, display: 'flex'}}>
            <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              // family THEN its generic — a real production font-stack. If the family fails to load,
              // this collapses onto tile B's generic (identical pixels, caught). Naming the family bare
              // with no fallback would instead resolve to Chromium's fixed UA-default face, which
              // differs from tile B's generic regardless of whether the real face loaded — a false pass.
              fontFamily: `${quoted}, ${generic}`, fontWeight: ladder ? 300 : 700, fontSize: 64}}>
              {SAMPLE}
            </div>
            <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: ladder ? quoted : generic,
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
