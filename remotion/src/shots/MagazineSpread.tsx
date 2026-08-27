// SHOT · Magazine Spread — a designer editorial COVER sets itself: a serif masthead, a hairline rule that
// draws, a bold hero colour block that slides in, a giant feature headline that sets word-by-word, a deck,
// column body-rules, and a folio. Precise print-grid typography on an off-white ground (family L · editorial).
// A rare LIGHT register. Deterministic (every reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
const PAPER_D0 = '#f3f0e8', INK_D0 = '#161512';

export const MagazineSpread: React.FC<{sectionLabel?: string; title?: string; headline?: string; deck?: string; issue?: string; accent?: string}> = ({
  sectionLabel = 'FEATURE',
  title: TITLE = 'OBLIQUE', headline: HEADLINE = 'The quiet revolution in how we work',
  deck: DECK = 'A field guide to the tools reshaping the day', issue: ISSUE = 'ISSUE 07 — 2026',
  accent: accentProp} = {}) => {
  const dna = useDNA();
  // accent is a PROP (an explicit override always wins); fall back to the DNA accent so a themed film unifies,
  // then the register's own editorial red as the un-themed default — not a fixed red block on a terminal/blue film.
  const PAPER = dna?.bg ?? PAPER_D0, INK = dna?.fg ?? INK_D0, ACC = accentProp ?? dna?.accent ?? '#e8452e';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const M = 150; // margin
  const mast = easeOutExpo(seg(t, 0.05, 0.34));
  const rule = easeOutCubic(seg(t, 0.2, 0.5));
  const block = easeOutExpo(seg(t, 0.34, 0.6));
  const words = HEADLINE.split(' ');
  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden', color: INK}}>
      {/* masthead */}
      <div style={{position: 'absolute', left: M, top: 92, opacity: clamp01(mast * 1.3),
        transform: `translateY(${(1 - mast) * -20}px)`,
        font: '800 132px/0.9 var(--f-display, "Playfair Display", Georgia, serif)', letterSpacing: '-0.02em'}}>{TITLE}</div>
      <div style={{position: 'absolute', right: M, top: 128, opacity: clamp01(seg(t, 0.28, 0.44)),
        font: '600 26px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.16em'}}>{ISSUE}</div>
      {/* hairline rule */}
      <div style={{position: 'absolute', left: M, top: 250, height: 3, background: INK,
        width: (W - 2 * M) * rule}} />

      {/* hero colour block */}
      <div style={{position: 'absolute', right: M, top: 320, width: 560, height: 560,
        transform: `translateX(${(1 - block) * 120}px)`, opacity: block,
        background: `linear-gradient(160deg, ${ACC}, ${dna?.accent2 ?? '#b0311f'})`, boxShadow: '0 40px 80px #0002'}}>
        <div style={{position: 'absolute', left: 34, bottom: 30, color: '#fff',
          font: '700 26px/1.3 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.08em', opacity: clamp01(seg(t, 0.5, 0.66))}}>
          FEATURE<br />No. 01</div>
        {/* a couple of framing corner ticks */}
        <div style={{position: 'absolute', left: 20, top: 20, width: 40, height: 40, borderLeft: '3px solid #fff', borderTop: '3px solid #fff', opacity: 0.7}} />
      </div>

      {/* giant feature headline, word by word */}
      <div style={{position: 'absolute', left: M, top: 470, width: W - 2 * M - 640,
        font: '800 116px/0.98 var(--f-display, "Playfair Display", Georgia, serif)', letterSpacing: '-0.015em'}}>
        {words.map((w, i) => {
          const on = easeOutCubic(clamp01(seg(t, 0.44 + i * 0.06, 0.62 + i * 0.06)));
          return <span key={i} style={{display: 'inline-block', marginRight: '0.28em', opacity: on,
            transform: `translateY(${(1 - on) * 24}px)`}}>{w}</span>;
        })}
      </div>

      {/* deck + body column rules */}
      <div style={{position: 'absolute', left: M, bottom: 190, width: 720, opacity: clamp01(seg(t, 0.72, 0.9)),
        font: 'italic 600 34px/1.35 var(--f-body, "Playfair Display", Georgia, serif)', color: '#3a352c'}}>{DECK}</div>
      <div style={{position: 'absolute', left: M, bottom: 96, display: 'flex', gap: 40}}>
        {[0, 1, 2].map((c) => (
          <div key={c} style={{display: 'flex', flexDirection: 'column', gap: 9}}>
            {[...Array(4)].map((_, r) => {
              const on = clamp01(seg(t, 0.8 + c * 0.03 + r * 0.02, 0.95));
              return <div key={r} style={{width: 200 * (r === 3 ? 0.6 : 1), height: 5, background: '#00000022', opacity: on}} />;
            })}
          </div>
        ))}
      </div>
      {/* folio */}
      <div style={{position: 'absolute', right: M, bottom: 84, font: '700 24px/1 var(--f-mono, "JetBrains Mono", monospace)',
        letterSpacing: '0.1em', opacity: clamp01(seg(t, 0.6, 0.8))}}>{TITLE}.CO — 01</div>
    </AbsoluteFill>
  );
};
export default MagazineSpread;
