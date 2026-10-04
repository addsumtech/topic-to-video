// SHOT · EdCompare — an EDITORIAL two-column contrast (the editorial analogue of TermDiff): two serif-headed
// columns split by a hairline rule, like a feature spread's "this vs that". The 'contrast/A-vs-B' idea in the
// editorial DNA. Deterministic (column reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, EdFrame} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 160;
type Col = {head?: string; body?: string; hero?: boolean};

export const EdCompare: React.FC<{kicker?: string; left?: Col; right?: Col; framed?: boolean}> = ({
  kicker = 'THE DIVIDE', left = {head: 'A', body: '…'}, right = {head: 'B', body: '…', hero: true}, framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const disp = dna?.fontDisplay ?? '"Playfair Display", Georgia, serif';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const fg = dna?.fg ?? '#efe9df', dim = dna?.dim ?? '#9a9084', acc = dna?.accent ?? '#e2603f', line = dna?.line ?? '#2a2018';

  const Column: React.FC<{c: Col; at: number}> = ({c, at}) => {
    const show = clamp01(seg(t, at, at + 0.16));
    const glide = useGlide();
    return (
      <div style={{flex: 1, opacity: show, transform: glide(`translateY(${(1 - show) * 16}px)`, show !== 1)}}>
        <div style={{color: c.hero ? acc : dim, font: `700 24px/1 ${body}`, letterSpacing: '0.14em',
          textTransform: 'uppercase', marginBottom: 18}}>{c.hero ? '↳ ' : ''}{c.head}</div>
        <div style={{color: c.hero ? fg : dim, font: `${c.hero ? 500 : 400} 46px/1.3 ${disp}`}}>{c.body}</div>
      </div>
    );
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <EdFrame dna={dna} kicker={kicker} t={t} framed={framed} align="left">
        <div style={{display: 'flex', gap: 64, width: '100%', maxWidth: 1200, alignItems: 'stretch'}}>
          <Column c={left} at={0.24} />
          <div style={{width: 1, background: line, alignSelf: 'stretch'}} />
          <Column c={right} at={0.36} />
        </div>
      </EdFrame>
    </AbsoluteFill>
  );
};
export default EdCompare;
