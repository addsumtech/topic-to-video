// SHOT · Particle Form — an elegant point-cloud (NOT cubes): ~140 dots fly in from scatter and ASSEMBLE into
// a giant checkmark — "a hundred moving parts resolve into one finished result." The film's ground + its
// accent. Deterministic (scatter seeded by index; assembly eased per dot).
//
// IT IS A DRAWING, NOT A LIGHT SOURCE — which is why it takes the film's ground instead of declaring a dark
// world. What this register measures is POSITION: 150 dots leaving a scatter and landing on one tick. The
// only per-dot cue is opacity (`0.5 + 0.5 * a`), which reads as "not yet arrived" on paper exactly as it does
// on black, and a dark dot on paper is still a dot — where a dark bokeh disc is a polka dot, which is why
// BokehPull keeps its night and this one does not. It used to paint a fixed near-black radial with a pale
// blue-white label, so under a light probe (bg #f6f3ee) the frame came back at Y=0.005 with 25% of its marks
// under 3:1 (scripts/ink_contrast_qa.py): the film's own accent, drawn on a night the film never asked for.
// On the film's ground that hole cannot open — `groundFrom` exposes `accent` until it clears 3:1 on the
// ground it will be drawn on. The `#pg` bloom stays on both exposures: it is a blurred copy of each dot
// merged under the dot, so it softens the mark in the mark's own colour rather than laying black on paper.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack, clamp01, hash01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {contentBottom, inkBlockH} from '../runtime/layout';

export const DURATION = 150; // 5s
const ACC_D0 = '#3FA9FF';
// the original dark-room literals, kept as the no-DNA rendering (byte-for-byte) and as the fallback chain
const GROUND_D0 = 'radial-gradient(120% 120% at 50% 44%, #0f1626, #05070e 72%)';
const SPARK_D0 = '#8fd0ff';   // the every-seventh dot, a step off the accent toward the light
const LABEL_D0 = '#eaf2ff';

export const ParticleForm: React.FC<{label?: string}> = ({label = 'Done.'} = {}) => {
  const dna = useDNA();
  const ACC = dna?.accent ?? ACC_D0;
  // the sparkle is the SAME step the literal pair took (#3FA9FF → #8fd0ff, the accent ~0.4 toward the light),
  // taken in the film's colours: toward the film's INK, so it stays a step off the accent in both exposures
  // instead of being a second hardcoded pale blue that only exists on a dark ground.
  const SPARK = dna ? mix(dna.accent, dna.fg, 0.4) : SPARK_D0;
  const LABEL_INK = dna?.fg ?? LABEL_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const LABEL = 70;               // `800 70px/1`
  const cyRaw = H / 2 - 30;
  // THE WHOLE COMPOSITION SLIDES UP BY EXACTLY WHAT DID NOT FIT. The label hangs a flat 300 below centre
  // and the centre is a flat fraction of the height, so on the three aspects nobody had swept the word
  // landed inside the caption band (66px at 1:1). Moving the label alone would break its relationship to
  // the checkmark it names — the particles assemble INTO it — so the anchor moves and everything built
  // from it follows. `over` is 0 at 16:9 and 9:16, which is why those two are untouched.
  const over = Math.max(0, cyRaw + 300 + inkBlockH(LABEL) - contentBottom(W, H));
  const cx = W / 2, cy = cyRaw - over, N = 150;
  // checkmark target polyline
  const A: [number, number] = [cx - 300, cy - 10], B: [number, number] = [cx - 90, cy + 200], C: [number, number] = [cx + 360, cy - 280];
  const l1 = Math.hypot(B[0] - A[0], B[1] - A[1]), l2 = Math.hypot(C[0] - B[0], C[1] - B[1]);
  const n1 = Math.round(N * (l1 / (l1 + l2)));
  const target = (i: number): [number, number] => {
    if (i < n1) {const u = i / n1; return [lerp(A[0], B[0], u), lerp(A[1], B[1], u)];}
    const u = (i - n1) / (N - n1); return [lerp(B[0], C[0], u), lerp(B[1], C[1], u)];
  };
  const assembled = easeInOutCubic(seg(t, 0.1, 0.72));
  const pulse = easeOutBack(seg(t, 0.72, 0.86));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? GROUND_D0}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><filter id="pg"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        <g filter="url(#pg)">
          {[...Array(N)].map((_, i) => {
            const [tx, ty] = target(i);
            const sx = cx + (hash01(i * 2.1) - 0.5) * W * 1.05, sy = cy + (hash01(i * 3.7) - 0.5) * H * 1.1;
            const a = clamp01((assembled - hash01(i) * 0.18) / 0.6);
            const x = lerp(sx, tx, a), y = lerp(sy, ty, a);
            const r = (5 + hash01(i * 5) * 4) * (1 + 0.5 * pulse);
            // @positional: a sparkle every seventh particle of an unlabelled cloud
            return <circle key={i} cx={x} cy={y} r={r} fill={i % 7 === 0 ? SPARK : ACC} opacity={0.5 + 0.5 * a} />;
          })}
        </g>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + 300, textAlign: 'center',
        opacity: clamp01((assembled - 0.7) / 0.2), font: `800 ${LABEL}px/1 var(--f-display, Inter,system-ui,sans-serif)`, color: LABEL_INK}}>{label}</div>
    </AbsoluteFill>
  );
};
export default ParticleForm;
