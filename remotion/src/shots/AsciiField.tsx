// SHOT · ASCII Field — generative/terminal language (a 2026 procedural trend): a live monospace character
// field flickers, a scan-wave sweeps and BRIGHTENS the glyphs it crosses, and a clean message decodes out of
// the noise. AMBER terminal phosphor (distinct from CodeRain's green Matrix rain) — this DECODES in place,
// CodeRain FALLS. Code-native. Deterministic (each glyph = fn of cell + frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, fitBlockPx, monoFit} from '../runtime/layout';

export const DURATION = 150; // 5s
const CH = '01</>{}[]#*+=~.:$%&ABCDEFXYZ01'.split('');
const DEFAULT_MSG = 'DONE.';

export const AsciiField: React.FC<{message?: string}> = ({message: MSG = DEFAULT_MSG} = {}) => {
  const frame = useCurrentFrame();
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  // THE FIELD STOPS WHERE THE CAPTION STARTS. It used to run to the bottom of the frame, so at 9:16 the
  // type-safety gate found 224 glyphs sitting inside the caption band — the burned subtitle printed over a
  // moving field of amber characters. The glyphs are noise, not copy, but the viewer still has to read a
  // sentence through them, and every other register in this library reserves that strip. It is the shot's
  // own ground down there now, which is exactly what the caption is drawn on.
  const bottom = contentBottom(W, H);
  // Sized off the frame's short side rather than in bare pixels, so a cell is a cell at any aspect.
  const cw = Math.max(8, Math.round(U * 0.0315)), chh = Math.max(10, Math.round(U * 0.037));
  // WHOLE ROWS ONLY. Ceil left the last row straddling the boundary and the svg clipped it through the
  // middle of the glyphs — a row of half-characters along the band, which reads as a broken render rather
  // than as an edge. The field ends on a row it can draw.
  const cols = Math.ceil(W / cw), rows = Math.max(1, Math.floor(bottom / chh));
  const fieldH = rows * chh;
  const scanY = (t * 1.3 - 0.15) * rows; // the sweep row
  const cells = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const flick = Math.floor(hash01(r * 91.7 + c * 13.1 + Math.floor(frame / 3)) * CH.length);
    const near = Math.max(0, 1 - Math.abs(r - scanY) / 3); // brighten near the scan-wave
    const base = 0.10 + 0.12 * hash01(r * 3.1 + c);
    const op = clamp01(base + near * 0.9);
    const col = near > 0.4 ? '#ffc861' : '#7a531c';   // AMBER phosphor (distinct from CodeRain's green rain)
    cells.push(<text key={`${r}-${c}`} x={c * cw + 6} y={r * chh + Math.round(chh * 0.75)} fill={col} fillOpacity={op}
      style={{font: `600 ${Math.round(U * 0.0278)}px/1 var(--f-mono, "JetBrains Mono", ui-monospace, monospace)`}}>{CH[flick]}</text>);
  }
  const decode = easeOutCubic(seg(t, 0.5, 0.78));
  // THE MESSAGE IS FITTED TO THE FIELD IT DECODES IN. `U * 0.194` is 210px on every frame this register
  // offers, which holds 'DONE.' and five Han glyphs — and a real Chinese message is longer than that. It
  // wrapped to four lines inside a box centred on the field, so it grew out of BOTH ends and the gate read
  // the top: glyphs cut off by 369px at 1:1. The face is MONOSPACE, where a Han glyph is two cells, so the
  // fit is told that rather than the proportional default it would otherwise assume.
  // `MSG_W` is passed to the fitter AND set on the box, so the measure the fit wrapped in is the measure
  // the browser wraps in — the two disagreeing is what put KineticManifesto's last line in the band.
  const MSG_W = Math.round(W * 0.86);
  const msgPx = fitBlockPx(MSG, MSG_W, fieldH * 0.92, Math.round(U * 0.194),
    {usable: 1, leading: 1, min: 28, ...monoFit()});
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('#140b03')}}>
      <svg width={W} height={fieldH} style={{position: 'absolute', left: 0, top: 0}}>{cells}</svg>
      {/* the decoded message resolving out of the noise */}
      {/* the message centres in the CONTENT zone, with the field — centred in the whole frame it would sit
          low of the field's own middle, and lower still at 9:16 where the reserved band is deepest */}
      <AbsoluteFill style={{top: 0, height: fieldH, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'relative', maxWidth: MSG_W, textAlign: 'center', font: `900 ${msgPx}px/1 var(--f-mono, "JetBrains Mono", monospace)`, color: '#ffe6b0',
          letterSpacing: '0.04em', opacity: decode, textShadow: '0 0 40px rgba(255,190,90,.5)'}}>
          {[...MSG].map((ch, i) => <span key={i} style={{opacity: clamp01((decode - i * 0.12) / 0.3)}}>{ch}</span>)}
        </div>
      </AbsoluteFill>
      {/* scanline glow */}
      <div style={{position: 'absolute', left: 0, right: 0, top: (scanY / rows) * fieldH - 2, height: 4, background: 'rgba(120,255,180,.5)', filter: 'blur(3px)'}} />
    </AbsoluteFill>
  );
};
export default AsciiField;
