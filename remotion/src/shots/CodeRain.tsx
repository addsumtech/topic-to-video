// SHOT · Code Rain — Matrix-style digital rain: columns of glyphs fall with a bright leading head + a fading
// phosphor trail, then a message resolves out of the stream on a darkened core. Digital / "in the machine"
// (family M · glitch/digital-decay). Deterministic (head y = fn of t; glyphs from a hash-stepped charset).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {darkGround} from '../runtime/light';

export const DURATION = 150; // 5s
// @dark-world: PHOSPHOR rain. Every column is a bright leading head with a decaying trail behind it, and the
// decay is drawn as falling opacity — a glyph that has nearly burnt out. On paper "nearly burnt out" is
// "nearly the paper", so the stream measured a median 2.80:1 with 62% of its marks under 3:1
// (scripts/ink_contrast_qa.py) and read as smudges rather than as rain. The rain cannot be inverted either:
// a trail that fades to BLACK on white is a stream of falling shadows, which is a different picture.
const BG_D0 = '#020603', GREEN_D0 = '#28ff9a';
const CHARS = 'ｱｲｳｴｵｶｷｸ01<>[]{}=+*#$%&ABCDEFHKNVXZ0123456789';

export const CodeRain: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Decoded', tagline: TAG = 'meaning from the stream'} = {}) => {
  const dna = useDNA();
  // the film's ground while it is dark; this register's own night when not (see @dark-world above)
  const BG = darkGround(dna?.bg, BG_D0);
  // AND ITS OWN PHOSPHOR WITH IT. A light film's accent was picked to read on PAPER, so it can be as dark as
  // the film's ink — dropped onto this register's night it would be rain nobody can see. While the film's
  // ground is dark (all eight presets, and null DNA) the rain is the film's accent exactly as before.
  const GREEN = BG === dna?.bg ? (dna?.accent ?? GREEN_D0) : GREEN_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const COLW = 30, ROWS = Math.ceil(H / 34) + 2;
  const cols = Math.ceil(W / COLW);
  const titleIn = easeOutCubic(seg(t, 0.42, 0.66));
  const tagIn = easeOutCubic(seg(t, 0.6, 0.82));
  const glyph = (c: number, r: number) => CHARS[Math.floor(hash01(c * 12.9 + r * 7.1 + Math.floor(t * 9)) * CHARS.length)];
  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* data-bleed: the rain IS the texture. Glyphs falling past the bottom edge is the effect, not a
          layout that failed to fit — text_safe_qa would otherwise report ~45 half-cut characters a frame. */}
      <svg data-bleed width={W} height={H} style={{position: 'absolute', inset: 0, fontFamily: 'var(--f-mono, monospace)'}}>
        {[...Array(cols)].map((_, c) => {
          const speed = 0.6 + hash01(c * 3.3) * 1.4, off = hash01(c * 9.7) * ROWS;
          const head = ((t * speed * ROWS + off) % (ROWS + 14));
          return [...Array(ROWS)].map((_, r) => {
            const dist = head - r;                          // rows behind the head
            if (dist < 0 || dist > 16) return null;
            const lead = dist < 1.2;
            const op = lead ? 1 : clamp01(1 - dist / 16) * 0.8;
            return <text key={`${c}-${r}`} x={c * COLW + 6} y={r * 34 + 26} fill={lead ? '#daffe9' : GREEN}
              opacity={op} fontSize={26} style={{filter: lead ? `drop-shadow(0 0 8px ${GREEN})` : undefined}}>{glyph(c, r)}</text>;
          });
        })}
      </svg>
      {/* darkened core so the message reads */}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(38% 34% at 50% 50%, #02060388, #0000 72%)'}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#eafff4',
          font: '800 130px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: `0 0 40px ${GREEN}, 0 12px 40px #000`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: GREEN,
          font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em', textShadow: `0 0 16px ${GREEN}`}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default CodeRain;
