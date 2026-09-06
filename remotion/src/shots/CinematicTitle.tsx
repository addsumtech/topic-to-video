// SHOT · Cinematic Title — the premium "film-title" register (2026 cinematic-storytelling trend): letterboxed
// 2.39:1, a serif display title fading up from deep shadow with a slow push-in, an anamorphic lens-flare sweep,
// warm tungsten glow + drifting dust motes. Deep, unhurried, mood-first. Deterministic (push/flare/dust = fn t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic, hash01} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, dnaHas, Caret, mix} from '../runtime/dna';
import {fitText} from '@remotion/layout-utils';

export const DURATION = 170; // ~5.7s
export const CinematicTitle: React.FC<{kicker?: string; title?: string; tagline?: string}> = ({
  kicker: KICKER = 'A NEW KIND OF TEAMMATE', title: TITLE = 'WorkBuddy', tagline: TAG = 'your ai team · on your machine'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // DESIGN DNA — a themed system recolours the warm cinematic hero into the FILM'S OWN hue, swaps the serif for the
  // DNA display face, drops the film-specific flare/letterbox, and adds a caret; with no DNA it stays the original.
  // The room glow is DERIVED from the DNA (accent receding into the ground) — never a fixed hue, so it is right on
  // an editorial/product/blueprint film, not only on the terminal one it was first written for.
  const dna = useDNA();
  const bgBase = dna?.bg ?? '#05060a';
  const roomGlow = dna
    ? `radial-gradient(80% 70% at 62% 42%, ${mix(dna.accent, dna.bg, 0.78)} 0%, ${mix(dna.bg, dna.accent, 0.1)} 42%, ${dna.bg} 78%)`
    : 'radial-gradient(80% 70% at 62% 42%, #3a2a1c 0%, #14100c 42%, #05060a 78%)';
  const moteCol = dna?.accent ?? '#ffe6c0';
  const kickCol = dna?.accent ?? '#c69a63';
  const titleFont = dna?.fontDisplay ?? '"Playfair Display", Georgia, serif';
  // MEASURED, not estimated. The old formula guessed advance width as `len * 0.52`, which underestimates a
  // high-contrast display face (Bodoni Moda) badly enough that a long title still wrapped to two lines — and
  // the tagline's fixed marginTop then crowded that second line at 9:16. The guess cannot be fixed by tuning
  // the constant, because `titleFont` is whichever face the active DNA declares. Measure the real string.
  const titleFit = fitText({
    text: String(TITLE), withinWidth: W * 0.86, fontFamily: titleFont, fontWeight: 800,
  }).fontSize;
  const titleCol = dna?.fg ?? '#f4efe6';
  const tagCol = dna?.dim ?? '#8b93a3';
  const bar = 132; // letterbox height
  const push = lerp(1.06, 1.14, easeOutCubic(t)); // slow Ken-Burns push
  const titleUp = easeOutExpo(seg(t, 0.16, 0.62));
  const flareX = lerp(-0.15, 1.15, easeOutCubic(seg(t, 0.2, 0.85))) * W;
  const flareGlow = Math.sin(clamp01(seg(t, 0.2, 0.85)) * Math.PI); // rise then fall

  return (
    <AbsoluteFill style={{background: bgBase, overflow: 'hidden'}}>
      {/* room-glow, pushed (cool under a terminal DNA, warm tungsten otherwise) */}
      <div style={{position: 'absolute', inset: 0, transform: `scale(${push})`, background: roomGlow}} />

      {/* dust motes drifting */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><filter id="dust"><feGaussianBlur stdDeviation="2.2" /></filter></defs>
        {[...Array(34)].map((_, i) => {
          const bx = hash01(i) * W;
          const by = (hash01(i * 2) * H + t * (14 + hash01(i * 3) * 26)) % H;
          const r = 1.4 + hash01(i * 5) * 3;
          const op = 0.12 + 0.32 * hash01(i * 7);
          return <circle key={i} cx={bx} cy={by} r={r} fill={moteCol} opacity={op * (0.5 + 0.5 * flareGlow)} filter="url(#dust)" />;
        })}
      </svg>

      {/* title block */}
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: clamp01(seg(t, 0.24, 0.5)), color: kickCol, font: '600 26px/1 var(--f-mono, "JetBrains Mono", monospace)',
          letterSpacing: '0.5em', textTransform: 'uppercase', paddingLeft: '0.5em', marginBottom: 34,
          transform: `translateY(${(1 - titleUp) * 18}px)`}}>{dnaHas(dna, 'prompt') ? '▸ ' : ''}{KICKER}</div>
        <div style={{opacity: titleUp, transform: `translateY(${(1 - titleUp) * 46}px)`, maxWidth: W * 0.9,
          color: titleCol, display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
          // width-AND-length-aware so a long title / narrow (portrait|square) frame can't clip the wordmark
          font: `800 ${Math.min(176, W * 0.13, titleFit)}px/${leading(TITLE, 0.98)} ${titleFont}`,
          letterSpacing: '-0.01em', textShadow: dna ? 'none' : '0 30px 90px #000, 0 2px 0 #ffffff22'}}>{TITLE}
          {dnaHas(dna, 'cursor') ? <Caret color={dna!.accent} h={72} w={20} style={{marginLeft: 14}} /> : null}</div>
        <div style={{opacity: clamp01(seg(t, 0.55, 0.82)), color: tagCol, font: '500 30px/1 var(--f-mono, "JetBrains Mono", monospace)',
          letterSpacing: '0.36em', textTransform: 'uppercase', paddingLeft: '0.36em', marginTop: 30}}>{TAG}</div>
      </AbsoluteFill>

      {/* anamorphic lens flare sweep — a FILM cue; suppressed under a terminal DNA */}
      {!dna ? <svg width={W} height={H} style={{position: 'absolute', inset: 0, mixBlendMode: 'screen'}}>
        <defs>
          <radialGradient id="core"><stop offset="0" stopColor="#fff7e8" stopOpacity="0.95" /><stop offset="1" stopColor="#fff7e8" stopOpacity="0" /></radialGradient>
          <linearGradient id="streak" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#9fd0ff" stopOpacity="0" /><stop offset="0.5" stopColor="#dff0ff" stopOpacity="0.9" /><stop offset="1" stopColor="#9fd0ff" stopOpacity="0" /></linearGradient>
          <filter id="fb"><feGaussianBlur stdDeviation="6" /></filter>
        </defs>
        <g opacity={flareGlow}>
          <rect x={flareX - 620} y={H / 2 - 3} width={1240} height={6} fill="url(#streak)" filter="url(#fb)" />
          <ellipse cx={flareX} cy={H / 2} rx={70} ry={70} fill="url(#core)" />
          <ellipse cx={flareX} cy={H / 2} rx={16} ry={220} fill="url(#streak)" filter="url(#fb)" opacity={0.5} />
        </g>
      </svg> : null}

      {/* letterbox bars — cinematic 2.39:1; a terminal is full-frame, so OFF under a terminal DNA */}
      {!dna ? <><div style={{position: 'absolute', top: 0, left: 0, right: 0, height: bar, background: '#000'}} />
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: bar, background: '#000'}} /></> : null}
      {/* vignette */}
      <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 50%, #0000 52%, #000000cc 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default CinematicTitle;
