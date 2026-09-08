// SHOT · Anti-Design Chaos — a deliberately "wrong" maximalist collage: a huge clashing headline, scattered
// mismatched words in different fonts/sizes/rotations, sticker shapes, hand-drawn arrows + scribbles, on a
// loud ground — every element popping in askew with a bounce. The 2026 anti-design / maximalist trend
// (family Q · anti-design). Deterministic (placement + rotation from hash01, not RNG).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 150; // 5s
// LEVEL-C: maximalism needs a CLASH, not one accent — dnaPalette() grows six distinct hues out of the DNA's two
// accents, so the collage stays loud and mismatched while still belonging to the film; the ground/headline invert
// on a dark DNA. Null DNA = the original yellow anti-design page.
const GROUND0 = '#f4e63a';
const POP0 = ['#ff2e6e', '#1b1b1b', '#2b6bff', '#00c37a', '#8b2fff', '#ff7a1a'];
const FONTS = ['Impact, system-ui, sans-serif', '"Playfair Display", Georgia, serif',
  '"JetBrains Mono", monospace', '"Baloo 2", Inter, sans-serif', 'Georgia, serif'];

export const AntiDesignChaos: React.FC<{title?: string; items?: string[]; tagline?: string}> = ({
  title: TITLE = 'RULES?', items: ITEMS = ['no grid', 'more!', 'why not', 'LOUD', 'oops', 'yes.'],
  tagline: TAG = 'break it on purpose'} = {}) => {
  const dna = useDNA();
  const GROUND = dna?.bg ?? GROUND0;
  const POP = dnaPalette(dna, 6) ?? POP0;
  const HEAD = dna?.fg ?? '#111';
  const CHIP_BG = dna?.fg ?? '#111', CHIP_FG = dna?.bg ?? GROUND0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const bg = seg(t, 0, 0.12) > 0.5 || t > 0.12;
  return (
    <AbsoluteFill style={{background: GROUND, overflow: 'hidden'}}>
      {/* sticker shapes scattered */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(9)].map((_, i) => {
          const x = 120 + hash01(i * 3.1) * (W - 240), y = 120 + hash01(i * 7.7) * (H - 240);
          const s = clamp01(seg(t, 0.1 + i * 0.05, 0.34 + i * 0.05));
          const col = POP[i % POP.length];
          const kind = i % 3;
          const rot = (hash01(i * 5) - 0.5) * 40;
          return (
            <g key={i} transform={`translate(${x} ${y}) rotate(${rot * s}) scale(${easeOutBack(s)})`} opacity={s}>
              {kind === 0 && <path d="M0,-46 L13,-14 46,-14 19,7 29,40 0,20 -29,40 -19,7 -46,-14 -13,-14 Z" fill={col} />}
              {kind === 1 && <circle r={40} fill="none" stroke={col} strokeWidth={12} />}
              {kind === 2 && <rect x={-42} y={-42} width={84} height={84} fill={col} transform="rotate(12)" />}
            </g>
          );
        })}
        {/* hand-drawn arrows / scribbles */}
        {[...Array(4)].map((_, i) => {
          const x = 200 + hash01(i * 9.3) * (W - 500), y = 200 + hash01(i * 4.1) * (H - 400);
          const on = clamp01(seg(t, 0.3 + i * 0.08, 0.6 + i * 0.08));
          const col = POP[(i + 2) % POP.length];
          return <path key={'a' + i} d={`M${x} ${y} q 80 -60 150 -10 t 120 20`} fill="none" stroke={col}
            strokeWidth={9} strokeLinecap="round" strokeDasharray={320} strokeDashoffset={320 * (1 - on)}
            transform={`rotate(${(hash01(i) - 0.5) * 50} ${x} ${y})`} />;
        })}
      </svg>

      {/* scattered mismatched words */}
      {ITEMS.map((w, i) => {
        const x = 160 + hash01(i * 2.3 + 1) * (W - 520), y = 180 + hash01(i * 8.1 + 2) * (H - 420);
        const pop = easeOutBack(clamp01(seg(t, 0.16 + i * 0.07, 0.4 + i * 0.07)));
        const rot = (hash01(i * 6.6) - 0.5) * 44;
        const col = POP[(i + 1) % POP.length];
        const sz = 60 + hash01(i * 3.7) * 90;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, opacity: clamp01(pop * 1.4),
            transform: `rotate(${rot * pop}deg) scale(${pop})`, color: col,
            fontFamily: FONTS[i % FONTS.length], fontWeight: 900, fontSize: sz, lineHeight: leading(w, 1),
            textShadow: '3px 3px 0 #00000022', whiteSpace: 'nowrap'}}>{w}</div>
        );
      })}

      {/* the loud headline, dead center but tilted */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `rotate(-6deg) scale(${easeOutBack(clamp01(seg(t, 0.3, 0.56)))})`,
          fontFamily: 'var(--f-display, Impact, system-ui, sans-serif)', fontSize: 300, lineHeight: leading(TITLE, 0.9), color: HEAD,
          WebkitTextStroke: `6px ${POP[0]}`, letterSpacing: '-0.02em',
          textShadow: `12px 12px 0 ${POP[2]}`}}>{TITLE}</div>
      </AbsoluteFill>

      <div style={{position: 'absolute', left: 60, bottom: bottomInset(W, H, 54), opacity: easeOutCubic(seg(t, 0.7, 0.9)),
        transform: 'rotate(-3deg)', background: CHIP_BG, color: CHIP_FG, padding: '10px 22px',
        font: '800 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.1em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default AntiDesignChaos;
