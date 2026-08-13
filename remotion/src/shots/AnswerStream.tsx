// SHOT · Answer Stream — Perplexity language: a question, then a generated answer STREAMS in token by
// token with inline source chips + source cards materialising. Dark navy + teal (adds a second dark, cool
// language to balance the light ones). Deterministic typewriter (chars = floor(len·progress)).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
const TEAL = '#22D3C5', BG = '#0b1220', PANEL = '#111a2b';
const DEFAULT_Q = 'How do we cut Q3 costs?';
const DEFAULT_A = 'Start with the three largest line items: consolidate vendor contracts [1], move compute to reserved capacity [2], and automate the monthly close [3].';
const DEFAULT_SRC = [{t: 'Vendor audit', d: 'finance/'}, {t: 'Cloud cost report', d: 'infra/'}, {t: 'Monthly close checklist', d: 'ops/'}];

export const AnswerStream: React.FC<{query?: string; answer?: string; sources?: {t: string; d: string}[]}> = ({
  query: Q = DEFAULT_Q, answer: A = DEFAULT_A, sources: SRC = DEFAULT_SRC} = {}) => {
  const t = useT();
  const {width: W} = useVideoConfig();
  const qIn = easeOutCubic(seg(t, 0, 0.14));
  const chars = Math.floor(A.length * easeOutCubic(seg(t, 0.2, 0.78)));
  const streaming = t > 0.2 && t < 0.8;
  const CW = 1300, X = (W - CW) / 2;
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 18%, #14203a, ${BG} 62%)`, padding: 0}}>
      {/* query */}
      <div style={{position: 'absolute', left: X, top: 150, width: CW, opacity: qIn, transform: `translateY(${lerp(20, 0, qIn)}px)`,
        display: 'flex', alignItems: 'center', gap: 22}}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={TEAL} strokeWidth="2"><path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" /></svg>
        <div style={{font: '700 62px/1.1 Inter,system-ui,sans-serif', color: '#eaf2ff'}}>{Q}</div>
      </div>
      {/* streaming answer */}
      <div style={{position: 'absolute', left: X, top: 300, width: CW}}>
        <div style={{font: '500 50px/1.5 Inter,system-ui,sans-serif', color: '#c7d3e6'}}>
          {A.slice(0, chars).split(/(\[\d\])/).map((seg2, i) => /\[\d\]/.test(seg2)
            ? <span key={i} style={{display: 'inline-block', margin: '0 6px', padding: '2px 12px', borderRadius: 8, background: `${TEAL}22`, color: TEAL, font: '700 34px/1 Inter', verticalAlign: 'middle'}}>{seg2.replace(/[\[\]]/g, '')}</span>
            : <span key={i}>{seg2}</span>)}
          {streaming && <span style={{color: TEAL}}>▍</span>}
        </div>
      </div>
      {/* source cards */}
      <div style={{position: 'absolute', left: X, top: 600, width: CW, display: 'flex', gap: 26}}>
        {SRC.map((s, i) => {
          const r = easeOutBack(seg(t, 0.4 + i * 0.08, 0.4 + i * 0.08 + 0.22));
          return <div key={i} style={{flex: 1, opacity: clamp01(r), transform: `translateY(${lerp(24, 0, clamp01(r))}px)`,
            background: PANEL, border: '1px solid #22304a', borderRadius: 14, padding: '26px 28px'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14}}>
              <div style={{width: 26, height: 26, borderRadius: 7, background: TEAL, color: BG, font: '700 16px/26px Inter', textAlign: 'center'}}>{i + 1}</div>
              <div style={{width: 10, height: 10, borderRadius: 5, background: '#3a4a66'}} />
              <div style={{font: '600 26px/1 Inter', color: '#7f8ea8'}}>{s.d}</div>
            </div>
            <div style={{font: '700 36px/1.2 Inter,system-ui,sans-serif', color: '#eaf2ff'}}>{s.t}</div>
          </div>;
        })}
      </div>
    </AbsoluteFill>
  );
};
export default AnswerStream;
