// SHOT · Holo Foil — an iridescent holographic-foil register: a wordmark filled with a shifting rainbow foil
// (conic gradient rotating), a bright specular sheen sweeping across, and sparkle glints twinkling. Distinct
// from LiquidChrome's grey metal — this is trading-card holo. Premium, playful-luxe. Deterministic (hue + sheen = t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, hash01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {fitTextPx} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
// THE FOIL IS A SURFACE, NOT A LIGHT, so this register takes the film's ground like any other — and it looks
// right on paper: rendered on a warm-white film the wordmark is still a foil wordmark and the wash behind it
// reads as pearl stock. What it was NOT was legible. The five foil hues all sit near 68% lightness because
// they were chosen against near-black, so on paper the word came in around 1.7-2.6:1, the pale lavender kicker
// at about 1.5:1, the white glints vanished outright, and the 2px white rim under the glyphs dissolved their
// own edges into the page (measured median 1.31:1, 100% of marks under 3:1 — scripts/ink_contrast_qa.py).
// Real foil is deep BECAUSE its substrate is dark metal, so the repair is exposure, not inversion: each hue is
// walked along its own black-to-white axis until it clears the floor and the hue is untouched. The sheen turns
// over with it: tilting a holo card moves the foil between a bright phase and a dark one, and against white
// stock it is the dark phase you see, so the same sweeping band multiplies there instead of screening white.
const FOIL_D0 = ['#ff5db2', '#ffd45b', '#5bffcf', '#5bb4ff', '#b45bff'];
const GLINT_D0 = '#fff', RIM_D0 = '#fff8';
// CJK-EXEMPT (tight leading, no floor): the word is sized by fitTextPx to one line, so there is never a second line to collide with.
export const HoloFoil: React.FC<{word?: string; tagline?: string}> = ({word: WORD = 'WORKBUDDY', tagline: TAGLINE = 'YOUR AI TEAM'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const angle = (t * 220) % 360;                 // rotating foil hue
  const sheen = lerp(-0.3, 1.3, (t * 0.8) % 1);  // specular band x
  const rise = easeOutExpo(seg(t, 0.06, 0.5));
  // Null DNA and all eight (dark) presets take the literals below untouched — the conic string they build is
  // character-for-character the one that shipped.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // Exposed to the INK floor, not the graphics one: the foil IS the wordmark, so it answers to the floor for
  // type — and 3.0 is also the exact ratio the ink gate fails at, so a colour solved to 3.00 lands on the
  // wrong side of it as soon as the ground behind a mark is sampled locally rather than as the flat page.
  const litHue = (c: string) => (dna && lit ? groundFrom(dna, {bg: dna.bg, fg: c}).fg : c);
  const stops = lit ? FOIL_D0.map(litHue) : FOIL_D0;
  const foil = `conic-gradient(from ${angle}deg at 50% 50%, ${stops.join(', ')}, ${stops[0]})`;
  // The 2px rim under the wordmark is a LIT edge — a white halo hugging each glyph, which against night reads
  // as the foil catching light and on paper erases the glyph's own boundary into the page (the halo the
  // caption rule forbids, one element over). A keyline in the film's ink was tried in its place and was worse:
  // a 2px band the same tone as the deepened foil, so the letter was then read against its own outline. On a
  // light ground there is simply no rim — the exposed foil meets the page directly — and the offset drop
  // shadow below still grounds the word.
  const wordShadow = `drop-shadow(0 8px 30px ${stops[0]}55)`;
  // A glint is a spark, and nothing can spark brighter than paper. On a light ground it is struck in the
  // film's own ink instead, which is the print convention for the same mark.
  const glint = lit ? lit.fg : GLINT_D0;
  // THE SHEEN SWEEPS THE OTHER WAY ON PAPER. Tilting a holo card moves the foil between a bright phase and a
  // dark one; against night the bright phase is the one you see, against white stock it is the dark one — and
  // a white `screen` band on paper washed the letters it crossed straight into the page, which is the defect
  // this whole pass is about. So on a light ground the same band multiplies a mid-tone off the film's own two
  // ends instead of screening white, and it is the identical sweep at the other phase.
  const sheenBlend = lit ? 'multiply' : 'screen';
  const sheenBand = lit ? mix(lit.bg, lit.fg, 0.30) : '#ffffffdd';

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 40%, #14121c 0%, #0a0910 70%)')}}>
      {/* faint foil wash on the backdrop */}
      <div style={{position: 'absolute', inset: 0, background: foil, opacity: 0.1, filter: 'blur(60px)'}} />

      {/* the holo wordmark */}
      {/* sized to the WIDTH it ships at: 210px fits this word at 1920 and loses 107px off each edge at 1080 */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
        <div style={{position: 'relative', transform: `translateY(${(1 - rise) * 40}px)`, opacity: rise}}>
          <div style={{font: `900 ${fitTextPx(WORD, W, 210, {track: 0.01})}px/0.9 var(--f-display, "Antonio", Impact, sans-serif)`, letterSpacing: '0.01em',
            background: foil, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
            filter: lit ? wordShadow : `${wordShadow} drop-shadow(0 0 2px ${RIM_D0})`}}>{WORD}</div>
          {/* specular sheen overlay (screen) */}
          <div style={{position: 'absolute', inset: 0, font: `900 ${fitTextPx(WORD, W, 210, {track: 0.01})}px/0.9 var(--f-display, "Antonio", Impact, sans-serif)`,
            letterSpacing: '0.01em', mixBlendMode: sheenBlend,
            background: `linear-gradient(105deg, #fff0 ${(sheen - 0.12) * 100}%, ${sheenBand} ${sheen * 100}%, #fff0 ${(sheen + 0.12) * 100}%)`,
            WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent'}}>{WORD}</div>
        </div>
        {/* the kicker is metadata on the film's ground, so it is the film's `dim` */}
        <div style={{marginTop: 30, opacity: clamp01(seg(t, 0.5, 0.76)), color: dna?.dim ?? '#c9c2e0',
          font: `600 ${fitTextPx(TAGLINE, W, 32, {track: 0.42})}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.42em', paddingLeft: '0.42em'}}>{TAGLINE}</div>
      </AbsoluteFill>

      {/* sparkle glints */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(16)].map((_, i) => {
          const x = W * (0.24 + hash01(i) * 0.52), y = H * (0.34 + hash01(i * 2) * 0.34);
          const ph = (t * 2 + hash01(i * 3)) % 1;
          const s = Math.sin(ph * Math.PI) * (6 + hash01(i * 5) * 10);
          if (s <= 0.5) return null;
          return <g key={i} stroke={glint} strokeWidth={2} opacity={Math.sin(ph * Math.PI)}>
            <line x1={x - s} y1={y} x2={x + s} y2={y} /><line x1={x} y1={y - s} x2={x} y2={y + s} /></g>;
        })}
      </svg>
    </AbsoluteFill>
  );
};
export default HoloFoil;
