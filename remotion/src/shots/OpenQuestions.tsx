// OpenQuestions — unresolved questions surfaced one by one under a descending scan-light, then left standing
// together (no arrows, no sequence — they are PARALLEL open questions, not steps). The dramatic-interrogation
// vibe of a spotlight, but a layout that fits long questions and encodes "these are all still open." A blinking
// caret at the end says: unanswered. Prop-driven (kicker + questions) → generalises. Deterministic (fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';

export const DURATION = 170; // ~5.7s

export const OpenQuestions: React.FC<{kicker?: string; questions?: string[]; accent?: string; footer?: string}> = ({
  kicker = 'The open questions', questions = ['How fast is too fast?', 'Is it safe?', 'Who gets a say?'],
  accent = '#10a37f', footer = 'still unresolved',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const qs = questions.slice(0, 4);
  const n = qs.length;
  const topY = H * 0.34, stepY = H * 0.15;
  const scanProg = clamp01(seg(t, 0.1, 0.14 + n * 0.2));           // the light descends past each question
  const scanY = lerp(topY - stepY * 0.5, topY + stepY * (n - 0.5), scanProg);

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 30%, #0d1119, #05060a 70%)'}}>
      {/* kicker */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center', opacity: clamp01(t * 5),
        color: '#8f9bb0', font: '600 26px/1 "JetBrains Mono", monospace', letterSpacing: '0.34em', textTransform: 'uppercase'}}>{kicker}</div>

      {/* the descending scan light */}
      <div style={{position: 'absolute', left: 0, right: 0, top: scanY - 60, height: 120, pointerEvents: 'none',
        background: `radial-gradient(60% 100% at 50% 50%, ${accent}22, transparent 70%)`, opacity: scanProg < 1 ? 1 : 0.0}} />
      <div style={{position: 'absolute', left: '18%', right: '18%', top: scanY, height: 2, pointerEvents: 'none',
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`, opacity: scanProg < 1 ? 0.9 : 0}} />

      {/* the questions — each lights as the scan passes, then stays lit */}
      {qs.map((q, i) => {
        const yc = topY + stepY * i;
        const lit = clamp01(seg(t, 0.12 + i * 0.2, 0.3 + i * 0.2));
        const glow = clamp01(1 - Math.abs(scanY - yc) / 90) * (scanProg < 1 ? 1 : 0);
        const b = Math.max(lit * 0.86, glow);
        return (
          <div key={i} style={{position: 'absolute', left: 0, right: 0, top: yc, transform: 'translateY(-50%)', textAlign: 'center'}}>
            <span style={{color: `rgba(${lerp(70, 238, b)},${lerp(78, 244, b)},${lerp(92, 252, b)},1)`,
              font: '700 62px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em', opacity: clamp01(lit * 1.3),
              textShadow: glow > 0.3 ? `0 0 46px ${accent}${Math.round(glow * 140).toString(16).padStart(2, '0')}` : 'none'}}>
              {q}</span>
          </div>
        );
      })}

      {/* footer: unresolved + a blinking caret (once all questions are up) */}
      <div style={{position: 'absolute', left: 0, right: 0, top: topY + stepY * (n - 1) + H * 0.13, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.78, 0.92)), color: accent, font: '600 24px/1 "JetBrains Mono", monospace', letterSpacing: '0.2em'}}>
        {footer}<span style={{opacity: Math.sin(t * Math.PI * 2 * 6) > 0 ? 1 : 0}}> _</span>
      </div>
    </AbsoluteFill>
  );
};
export default OpenQuestions;
