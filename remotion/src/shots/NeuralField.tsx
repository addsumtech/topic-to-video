// SHOT · Neural Field — a neural network THINKS: layered nodes and their edges light up as an activation front
// sweeps left→right, signals pulsing along the strongest connections until the output node locks. An AI-native
// register (family R · AI/neural). Deterministic (activation front = fn of t; edge strengths from hash). No
// fabricated stats — labels are layer names, not numbers.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#060a16', EDGE = '#1c2f57', LIVE = '#37e0ff', OUT = '#3affa0';
const LAYERS = [5, 8, 8, 3];

export const NeuralField: React.FC<{title?: string; input?: string; output?: string}> = ({
  title: TITLE = 'It reasons', input: INLABEL = 'your prompt', output: OUTLABEL = 'the answer'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const L = LAYERS.length;
  const x0 = 320, x1 = W - 320, midY = H / 2 + 10;
  const nodeX = (li: number) => lerp(x0, x1, li / (L - 1));
  const nodeY = (li: number, ni: number) => midY + (ni - (LAYERS[li] - 1) / 2) * 110;
  const front = clamp01(seg(t, 0.14, 0.86)) * (L - 1);            // activation front position (in layer units)
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const nodeAct = (li: number) => clamp01((front - (li - 0.5)) * 2.2);
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, #0c1430, ${BG} 74%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 72, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#8fb6d8', font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* edges */}
        {LAYERS.slice(0, -1).map((cnt, li) => (
          [...Array(cnt)].map((_, a) => (
            [...Array(LAYERS[li + 1])].map((_, b) => {
              const strong = hash01(li * 31 + a * 7 + b * 3) > 0.62;
              const pulse = clamp01((front - li) * 3) * (1 - clamp01((front - li - 1) * 3));
              const lit = strong ? pulse : 0;
              return <line key={`${li}-${a}-${b}`} x1={nodeX(li)} y1={nodeY(li, a)} x2={nodeX(li + 1)} y2={nodeY(li + 1, b)}
                stroke={lit > 0.05 ? LIVE : EDGE} strokeWidth={lit > 0.05 ? 2.4 : 1}
                opacity={lit > 0.05 ? 0.3 + 0.6 * lit : 0.16} />;
            })
          ))
        ))}
        {/* nodes */}
        {LAYERS.map((cnt, li) => (
          [...Array(cnt)].map((_, ni) => {
            const act = nodeAct(li);
            const isOut = li === L - 1;
            const col = isOut && act > 0.5 ? OUT : LIVE;
            const r = lerp(12, 22, act);
            return <g key={`${li}-${ni}`}>
              <circle cx={nodeX(li)} cy={nodeY(li, ni)} r={r + 8} fill={col} opacity={0.18 * act} />
              <circle cx={nodeX(li)} cy={nodeY(li, ni)} r={r} fill={act > 0.1 ? col : '#1a2340'}
                stroke={act > 0.1 ? col : '#2a3760'} strokeWidth={2}
                style={{filter: act > 0.4 ? `drop-shadow(0 0 8px ${col})` : undefined}} />;
            </g>;
          })
        ))}
      </svg>

      {/* io labels */}
      <div style={{position: 'absolute', left: nodeX(0), top: midY + 330, transform: 'translateX(-50%)',
        opacity: clamp01(seg(t, 0.1, 0.3)), color: '#9fb2c8', font: '600 26px/1 var(--f-mono, "JetBrains Mono", monospace)',
        letterSpacing: '0.1em'}}>{INLABEL}</div>
      <div style={{position: 'absolute', left: nodeX(L - 1), top: midY + 330, transform: 'translateX(-50%)',
        opacity: clamp01(seg(t, 0.72, 0.9)), color: OUT, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)',
        letterSpacing: '0.1em', textShadow: `0 0 16px ${OUT}`}}>{OUTLABEL}</div>
    </AbsoluteFill>
  );
};
export default NeuralField;
