// SpeedLimit — why you can't just drive the gradients faster, with text that STAYS IN ITS LAYOUT (the old circuit
// shot spilled its node labels). A "gradient speed" bar rises but is blocked by TWO ceilings — the hardware
// slew-rate limit and peripheral nerve stimulation — so it can't go higher; the only lever left is to skip lines.
// Labels sit OUTSIDE the bar with room, never inside cramped nodes. Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY, latinAdvance, textWidthPx} from '../runtime/layout';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'blocked',
  'hardware: slew-rate limit',
  'patient: nerve stimulation',
  '→ skip k-space lines instead',
];
const WARN = '#ff5d6c';

export const SpeedLimit: React.FC<{accent?: string; label?: string}> = ({
  accent = '#22d3ee', label = "You can't just go faster",
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // the axis label is a BASELINE 40px under the track's foot, and the foot was a flat 0.74 of the height —
  // 22px of 'gradient speed' inside the caption band at 1:1. The track shortens; the label stays put.
  // THE LABELS' ROOM IS MEASURED, NOT RESERVED AS 344px. Each ceiling label was placed with a literal
  // width held back from the frame edge — `Math.min(bx + 230, W - 344)` — and 344 is how wide these words
  // are in INTER, the fallback in the font shorthand below. The face that actually renders is the DNA's
  // body stack: under `terminal` and `blueprint` it is JetBrains Mono, whose advance is 0.62 against
  // Inter's 0.52, and the same words run 16px and 30px off the right edge while the conclusion runs 73px
  // off the left. `latinAdvance` is the shared rule for exactly this question, and it takes the stack.
  const LBL = 24;
  const adv = latinAdvance(dna?.fontBody);
  const lblW = (x: string) => textWidthPx(x, LBL, {adv});
  const [HW_T, PNS_T, SKIP_T] = [INTRINSIC_TEXT[1], INTRINSIC_TEXT[2], INTRINSIC_TEXT[3]];
  const edge = Math.round(W * 0.02);
  const bx = W * 0.5, trackTop = H * 0.26;
  const trackBot = Math.min(H * 0.74, bottomTextY(W, H) - 40);
  const trackH = trackBot - trackTop;
  const hwY = trackTop + trackH * 0.28;                     // hardware ceiling (the binding one)
  const pnsY = trackTop + trackH * 0.14;                    // nerve-stimulation ceiling (even higher)
  const rise = clamp01(seg(t, 0.12, 0.62));                 // the bar rises, then jams at the hardware ceiling
  const topY = lerp(trackBot, hwY, rise);
  const blocked = rise > 0.96;
  const shake = blocked ? Math.sin(t * 60) * 2 : 0;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <rect x={bx - 46} y={trackTop} width={92} height={trackH} rx={12} fill="#0a1424" stroke={`${accent}44`} strokeWidth={1.4} />
        <rect x={bx - 40 + shake} y={topY} width={80} height={trackBot - topY} rx={9} fill={blocked ? WARN : accent} opacity={0.9} />
        <text x={bx} y={trackBot + 40} textAnchor="middle" fill="#c9d6ea" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>gradient speed</text>

        {/* two ceilings — labels OUTSIDE the track with room */}
        <line x1={bx - 210} y1={hwY} x2={bx + 210} y2={hwY} stroke={WARN} strokeWidth={2.5} strokeDasharray="6 5" opacity={clamp01(seg(t, 0.05, 0.3))} />
        <text x={Math.min(bx + 230, W - edge - lblW(HW_T))} y={hwY + 6} fill={WARN} fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={clamp01(seg(t, 0.05, 0.3))}>hardware: slew-rate limit</text>
        <line x1={bx - 180} y1={pnsY} x2={bx + 180} y2={pnsY} stroke="#f06ecb" strokeWidth={2} strokeDasharray="6 5" opacity={clamp01(seg(t, 0.1, 0.35))} />
        <text x={Math.min(bx + 200, W - edge - lblW(PNS_T))} y={pnsY + 6} fill="#ff8ad0" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={clamp01(seg(t, 0.1, 0.35))}>patient: nerve stimulation</text>

        {/* conclusion — left of the track, with room */}
        <text x={bx - 250} y={trackTop + trackH * 0.55} textAnchor="end" fill="#eaf6ff" fontSize="30" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} opacity={clamp01(seg(t, 0.66, 0.86))}>blocked</text>
        <text x={Math.max(bx - 250, edge + lblW(SKIP_T))} y={trackTop + trackH * 0.55 + 34} textAnchor="end" fill={accent} fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" opacity={clamp01(seg(t, 0.72, 0.9))}>→ skip k-space lines instead</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default SpeedLimit;
