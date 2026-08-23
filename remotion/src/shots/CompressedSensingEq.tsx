// CompressedSensingEq — the concept AS ITS EQUATION, not an abstract ridgeline. Compressed sensing is literally a
// constrained optimisation: minimise the L1 norm of the image in a sparse transform, subject to consistency with
// the measured (undersampled) k-space. Showing the formula + annotating each term teaches it precisely; a typeset
// equation is a legitimate, high-craft design, not only diagrams. Deterministic (terms reveal in order).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 180; // 6s
const SERIF = "var(--f-display, 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif)";

export const CompressedSensingEq: React.FC<{accent?: string; accent2?: string; label?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Compressed sensing',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const eqY = H * 0.46;
  const app = clamp01(seg(t, 0.08, 0.4));                   // the equation writes in
  const a1 = clamp01(seg(t, 0.42, 0.62));                   // annotate the sparse term
  const a2 = clamp01(seg(t, 0.6, 0.82));                    // annotate the data-consistency term

  const span = (txt: string, color: string, o = 1) => <span style={{color, opacity: o}}>{txt}</span>;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      {/* the equation */}
      <div style={{position: 'absolute', left: 0, right: 0, top: eqY, textAlign: 'center', opacity: app,
        font: `400 92px/1.1 ${SERIF}`, color: '#eef4fb', letterSpacing: '0.01em'}}>
        {span('min', '#9fb4cc')}&nbsp;&nbsp;
        {span('‖', '#cfe0f2')}{span('Ψx', accent)}{span('‖', '#cfe0f2')}<span style={{fontSize: 44, verticalAlign: 'sub', color: '#cfe0f2'}}>1</span>
        &nbsp;&nbsp;&nbsp;<span style={{font: `italic 400 44px/1 ${SERIF}`, color: '#9fb4cc'}}>subject&nbsp;to</span>&nbsp;&nbsp;&nbsp;
        {span('‖', '#cfe0f2')}{span('Fx−y', accent2)}{span('‖', '#cfe0f2')}<span style={{fontSize: 44, verticalAlign: 'sub', color: '#cfe0f2'}}>2</span>
        &nbsp;{span('≤', '#9fb4cc')}&nbsp;{span('ε', '#9fb4cc')}
      </div>

      {/* annotation: the sparse transform term */}
      <div style={{position: 'absolute', left: W * 0.2, top: eqY - 120, width: 300, textAlign: 'center', opacity: a1}}>
        <div style={{color: accent, font: "700 24px/1.2 var(--f-body, Inter, sans-serif)"}}>sparse in a transform</div>
        <div style={{color: '#8aa', font: "400 18px/1.3 var(--f-body, Inter, sans-serif)", marginTop: 4}}>L1 favors the fewest coefficients</div>
        <div style={{position: 'absolute', left: 150, top: 62, width: 2, height: 46, background: `${accent}88`}} />
      </div>
      {/* annotation: the data-consistency term */}
      <div style={{position: 'absolute', left: W * 0.5, top: eqY + 120, width: 360, textAlign: 'center', opacity: a2}}>
        <div style={{position: 'absolute', left: 180, top: -48, width: 2, height: 46, background: `${accent2}88`}} />
        <div style={{color: accent2, font: "700 24px/1.2 var(--f-body, Inter, sans-serif)"}}>consistent with the measured k-space</div>
        <div style={{color: '#8aa', font: "400 18px/1.3 var(--f-body, Inter, sans-serif)", marginTop: 4}}>random undersampling → noise-like aliasing</div>
      </div>

      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default CompressedSensingEq;
