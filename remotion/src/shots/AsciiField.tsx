// SHOT · ASCII Field — generative/terminal language (a 2026 procedural trend): a live monospace character
// field flickers, a scan-wave sweeps and BRIGHTENS the glyphs it crosses, and a clean message decodes out of
// the noise. AMBER terminal phosphor (distinct from CodeRain's green Matrix rain) — this DECODES in place,
// CodeRain FALLS. Code-native. Deterministic (each glyph = fn of cell + frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const CH = '01</>{}[]#*+=~.:$%&ABCDEFXYZ01'.split('');
const DEFAULT_MSG = 'DONE.';

export const AsciiField: React.FC<{message?: string}> = ({message: MSG = DEFAULT_MSG} = {}) => {
  const frame = useCurrentFrame();
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cw = 34, chh = 40, cols = Math.ceil(W / cw), rows = Math.ceil(H / chh);
  const scanY = (t * 1.3 - 0.15) * rows; // the sweep row
  const cells = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const flick = Math.floor(hash01(r * 91.7 + c * 13.1 + Math.floor(frame / 3)) * CH.length);
    const near = Math.max(0, 1 - Math.abs(r - scanY) / 3); // brighten near the scan-wave
    const base = 0.10 + 0.12 * hash01(r * 3.1 + c);
    const op = clamp01(base + near * 0.9);
    const col = near > 0.4 ? '#ffc861' : '#7a531c';   // AMBER phosphor (distinct from CodeRain's green rain)
    cells.push(<text key={`${r}-${c}`} x={c * cw + 6} y={r * chh + 30} fill={col} fillOpacity={op}
      style={{font: '600 30px/1 "JetBrains Mono", ui-monospace, monospace'}}>{CH[flick]}</text>);
  }
  const decode = easeOutCubic(seg(t, 0.5, 0.78));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('#140b03')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>{cells}</svg>
      {/* the decoded message resolving out of the noise */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'relative', font: '900 210px/1 "JetBrains Mono", monospace', color: '#ffe6b0',
          letterSpacing: '0.04em', opacity: decode, textShadow: '0 0 40px rgba(255,190,90,.5)'}}>
          {MSG.split('').map((ch, i) => <span key={i} style={{opacity: clamp01((decode - i * 0.12) / 0.3)}}>{ch}</span>)}
        </div>
      </AbsoluteFill>
      {/* scanline glow */}
      <div style={{position: 'absolute', left: 0, right: 0, top: (scanY / rows) * H - 2, height: 4, background: 'rgba(120,255,180,.5)', filter: 'blur(3px)'}} />
    </AbsoluteFill>
  );
};
export default AsciiField;
