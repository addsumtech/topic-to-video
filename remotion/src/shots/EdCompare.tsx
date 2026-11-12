// SHOT · EdCompare — an EDITORIAL two-column contrast (the editorial analogue of TermDiff): two serif-headed
// columns split by a hairline rule, like a feature spread's "this vs that". The 'contrast/A-vs-B' idea in the
// editorial DNA. Deterministic (column reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, EdFrame} from '../runtime/dna';
import {useGlide} from '../runtime/glide';
import {LitStage, softShadow} from '../runtime/craftStage';

export const DURATION = 160;
type Col = {head?: string; body?: string; hero?: boolean};

export const EdCompare: React.FC<{kicker?: string; left?: Col; right?: Col; framed?: boolean}> = ({
  // placeholder copy in the library's placeholder voice: it names the form, not a topic
  kicker = 'THE DIVIDE', left = {head: 'Before', body: 'The way it was done'}, right = {head: 'After', body: 'The way it is done now', hero: true},
  framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const disp = dna?.fontDisplay ?? '"Playfair Display", Georgia, serif';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const fg = dna?.fg ?? '#efe9df', dim = dna?.dim ?? '#9a9084', acc = dna?.accent ?? '#e2603f', line = dna?.line ?? '#2a2018';

  // THE SPREAD IS TWO LIT CARDS ON A THEMED FILM (craft standard, 2026-11-12): two columns of 24 / 46 px type in the
  // middle of a dark frame read as a template. The quiet side is a plain card, the hero side the lit one (accent edge,
  // glow), heads at 32 px, the bodies in the display face sized to their length up to 84 px. Un-themed: the original.
  const themed = !!dna;
  const bodyPx = (s: string) => (!themed ? 46 : s.length <= 28 ? 84 : s.length <= 56 ? 66 : s.length <= 96 ? 54 : 46);
  const Column: React.FC<{c: Col; at: number}> = ({c, at}) => {
    const show = clamp01(seg(t, at, at + 0.16));
    const glide = useGlide();
    const card: React.CSSProperties = themed ? {padding: '40px 44px', borderRadius: (dna?.radius ?? 18) + 4,
      background: c.hero ? `linear-gradient(180deg, ${dna!.surface}, ${dna!.bg})` : `${dna!.surface}66`,
      border: `1px solid ${c.hero ? acc + '88' : line}`,
      boxShadow: c.hero ? `0 0 0 1px ${acc}33, 0 0 90px ${acc}26, ${softShadow(3, '#000000')}` : 'none'} : {};
    return (
      <div style={{flex: 1, opacity: show, transform: glide(`translateY(${(1 - show) * 16}px)`, true), ...card}}>
        <div style={{color: c.hero ? acc : dim, font: `700 ${themed ? 32 : 24}px/1 ${body}`, letterSpacing: '0.14em',
          textTransform: 'uppercase', marginBottom: themed ? 26 : 18}}>{c.hero ? '↳ ' : ''}{c.head}</div>
        <div style={{color: c.hero ? fg : dim, font: `${c.hero ? 500 : 400} ${bodyPx(String(c.body ?? ''))}px/1.12 ${disp}`,
          letterSpacing: themed ? '-0.015em' : undefined}}>{c.body}</div>
      </div>
    );
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      {themed ? <LitStage ground={dna!.bg} light={acc} fill={dna!.accent2 ?? null} keyAt={{x: 0.68, y: 0.4}} intensity={0.8} /> : null}
      <EdFrame dna={dna} kicker={kicker} t={t} framed={framed} align="left">
        <div style={{display: 'flex', gap: themed ? 40 : 64, width: '100%', maxWidth: themed ? undefined : 1200, alignItems: 'stretch'}}>
          <Column c={left} at={0.24} />
          {themed ? null : <div style={{width: 1, background: line, alignSelf: 'stretch'}} />}
          <Column c={right} at={0.36} />
        </div>
      </EdFrame>
    </AbsoluteFill>
  );
};
export default EdCompare;
