// SHOT · Answer Stream — Perplexity language: a question, then a generated answer STREAMS in token by
// token with inline source chips + source cards materialising. Dark navy + teal (adds a second dark, cool
// language to balance the light ones). Deterministic typewriter (chars = floor(len·progress)).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 165; // 5.5s
const TEAL_D0 = '#22D3C5', BG_D0 = '#0b1220', PANEL_D0 = '#111a2b';
const INK_D0 = '#eaf2ff', BODY_D0 = '#c7d3e6', DIM_D0 = '#7f8ea8', EDGE_D0 = '#22304a', DOT_D0 = '#3a4a66';
const DEFAULT_Q = 'How do we cut Q3 costs?';
const DEFAULT_A = 'Start with the three largest line items: consolidate vendor contracts [1], move compute to reserved capacity [2], and automate the monthly close [3].';
const DEFAULT_SRC = [{t: 'Vendor audit', d: 'finance/'}, {t: 'Cloud cost report', d: 'infra/'}, {t: 'Monthly close checklist', d: 'ops/'}];

export const AnswerStream: React.FC<{query?: string; answer?: string; sources?: {t: string; d: string}[]}> = ({
  query: Q = DEFAULT_Q, answer: A = DEFAULT_A, sources: SRC = DEFAULT_SRC} = {}) => {
  const dna = useDNA();
  const TEAL = dna?.accent ?? TEAL_D0, BG = dna?.bg ?? BG_D0, PANEL = dna?.surface ?? PANEL_D0;
  // EVERY WORD OF THE ANSWER WAS A LITERAL NEAR-WHITE. The ground followed the film and the type did not, so
  // on a light film the sentence broke mid-word — the half over the dark head of the gradient read and the
  // half over the paper did not, and the source cards (drawn on `surface`, which is WHITE there) lost their
  // titles entirely. The answer is the beat; it takes the film's ink.
  const INK = dna?.fg ?? INK_D0;
  const BODY = dna ? mix(dna.fg, dna.dim, 0.34) : BODY_D0;   // softer than the question, still the film's ink
  const DIM = dna?.dim ?? DIM_D0, EDGE = dna?.surfaceBorder ?? EDGE_D0, DOT = dna?.line ?? DOT_D0;
  const ON_TEAL = dna?.onAccent ?? BG;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const qIn = easeOutCubic(seg(t, 0, 0.14));
  const chars = Math.floor(A.length * easeOutCubic(seg(t, 0.2, 0.78)));
  const streaming = t > 0.2 && t < 0.8;
  const CW = Math.min(1300, Math.round(W * 0.92)), X = (W - CW) / 2;   // the column yields to a narrow frame
  // THE EVIDENCE ROW SITS AT A FIXED y=600, and its cards are as tall as the copy in them. A Han glyph is
  // a full em, so a Chinese source title wraps where the English one did not, the card grows downward from
  // a top that never moves, and the row reaches 101px into the caption band at 1:1. The row's top yields by
  // the height its tallest card actually needs. Latin is one line and the row stays at 600.
  const SRC_PX = 36, SRC_D_PX = 26;
  const colW = Math.max(80, (CW - 26 * Math.max(0, SRC.length - 1)) / Math.max(1, SRC.length) - 56);
  const srcCardH = 52 + 26 + 14
    + Math.max(1, ...SRC.map((s2) => wrapLines(String(s2.t ?? ''), SRC_PX, colW))) * SRC_PX * 1.2
    + Math.max(0, ...SRC.map((s2) => wrapLines(String(s2.d ?? ''), SRC_D_PX, colW) - 1)) * SRC_D_PX;
  const srcTop = Math.min(600, contentBottom(W, H) - srcCardH);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ??
      `radial-gradient(120% 100% at 50% 18%, #14203a, ${BG} 62%)`, padding: 0}}>
      {/* query */}
      <div style={{position: 'absolute', left: X, top: 150, width: CW, opacity: qIn, transform: `translateY(${lerp(20, 0, qIn)}px)`,
        display: 'flex', alignItems: 'center', gap: 22}}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={TEAL} strokeWidth="2"><path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" /></svg>
        <div style={{font: '700 62px/1.1 var(--f-body, Inter,system-ui,sans-serif)', color: INK}}>{Q}</div>
      </div>
      {/* streaming answer */}
      <div style={{position: 'absolute', left: X, top: 300, width: CW}}>
        <div style={{font: '500 50px/1.5 var(--f-body, Inter,system-ui,sans-serif)', color: BODY}}>
          {A.slice(0, chars).split(/(\[\d\])/).map((seg2, i) => /\[\d\]/.test(seg2)
            ? <span key={i} style={{display: 'inline-block', margin: '0 6px', padding: '2px 12px', borderRadius: 8, background: `${TEAL}22`, color: TEAL, font: '700 34px/1 var(--f-body, Inter)', verticalAlign: 'middle'}}>{seg2.replace(/[\[\]]/g, '')}</span>
            : <span key={i}>{seg2}</span>)}
          {streaming && <span style={{color: TEAL}}>▍</span>}
        </div>
      </div>
      {/* source cards */}
      <div style={{position: 'absolute', left: X, top: srcTop, width: CW, display: 'flex', gap: 26}}>
        {SRC.map((s, i) => {
          const r = easeOutBack(seg(t, 0.4 + i * 0.08, 0.4 + i * 0.08 + 0.22));
          return <div key={i} style={{flex: 1, opacity: clamp01(r), transform: `translateY(${lerp(24, 0, clamp01(r))}px)`,
            background: PANEL, border: `1px solid ${EDGE}`, borderRadius: dna?.radius ?? 14, padding: '26px 28px'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14}}>
              <div style={{width: 26, height: 26, borderRadius: 7, background: TEAL, color: ON_TEAL, font: '700 16px/26px var(--f-body, Inter)', textAlign: 'center'}}>{i + 1}</div>
              <div style={{width: 10, height: 10, borderRadius: 5, background: DOT}} />
              <div style={{font: `600 26px/${leading(s.d, 1)} var(--f-body, Inter)`, color: DIM}}>{s.d}</div>
            </div>
            <div style={{font: '700 36px/1.2 var(--f-body, Inter,system-ui,sans-serif)', color: INK}}>{s.t}</div>
          </div>;
        })}
      </div>
    </AbsoluteFill>
  );
};
export default AnswerStream;
