// SHOT · Neon Grid — a synthwave / retro-futuristic register: a neon perspective floor scrolls toward a
// gridded sun on the horizon under a starfield, with a glowing chrome-neon wordmark. High-energy, unmistakable
// atmosphere. Deterministic (grid scroll + twinkle = fn of t/frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, hash01} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, tint} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {fitText} from '@remotion/layout-utils';

export const DURATION = 160; // ~5.3s
// @dark-world: NEON is emitted light. Every mark here is a source, not an ink: the floor lines, the sun and
// the horizon are drawn through a blur-merge bloom (`#neon`), the stars are points of light in a sky, and the
// wordmark is lit from behind by its own magenta drop-shadow. What the register measures is how much a tube
// GLOWS against the night behind it — on a warm-white film there is no night, so under the light probe it
// came back at sheet Y=0.005 with 7% of its marks under 3:1 (scripts/ink_contrast_qa.py), the sky simply
// sitting over the paper undeclared. Inverting it does not repair the picture, it makes a different one: a
// neon sign printed in dark ink on white is a poster, not a sign. So it keeps its own night.
const MAG_D0 = '#ff2d95', CYAN_D0 = '#22e3ff';
const OWN_NIGHT = 'linear-gradient(#160726 0%, #2a0b3f 38%, #5b1063 47%, #12061f 55%, #0a0413 100%)';
const OWN_NIGHT_FLAT = '#12061f';   // the same sky as one colour, for darkGround to judge
const SUN_GAP_D0 = '#2a0b3f';       // the sky showing through the sun's scanline gaps — the 38% stop above
const CHROME_D0 = 'linear-gradient(#fff, #a7e9ff 40%, #ff9ee0 60%, #ff2d95)';
const HORIZON_D0 = '#ffd0f0';

export const NeonGrid: React.FC<{title?: string; tagline?: string}> = ({title: TITLE = 'WORKBUDDY', tagline: TAGLINE = 'ON YOUR MACHINE'} = {}) => {
  const dna = useDNA();
  // DIRECT READS, not `var(--f-display, …)`. fitText below measures in a detached node OUTSIDE .dna-film, where
  // the CSS variables are undefined — it would have measured the FALLBACK face and returned a size for the wrong
  // typeface. Reading the DNA in JS is the second sanctioned mechanism (references/remotion-shot-authoring.md
  // §C3) and resolves to exactly the same string the var fallback gave when no DNA is active.
  const dispFace = dna?.fontDisplay ?? '"Antonio", Impact, sans-serif';
  const monoFace = dna?.fontMono ?? '"JetBrains Mono", monospace';
  // the film's ground while the film's ground is dark (all eight presets), this register's own sky when it is
  // not. The branch is on what `darkGround` RETURNED, so a dark film grounded on exactly this colour still
  // gets its own `bgGrad` treatment rather than ours.
  const night = darkGround(dna?.bg, OWN_NIGHT_FLAT);
  const onFilmGround = night === dna?.bg;
  const ground = onFilmGround ? (dna?.bgGrad ?? night) : OWN_NIGHT;
  // AND THE TUBES WITH IT. On a light film the DNA's accents were chosen to read ON PAPER — `groundFrom`
  // darkens them until they clear 3:1 there — and a darkened accent laid on this sky at strokeOpacity 0.35
  // is a tube that is off. So the neon follows the ground it is drawn on: the film's while the film's ground
  // is dark (unchanged for every preset and for null DNA), the register's own pair when it is not. Same move
  // BokehPull makes for its orbs.
  const MAG = (onFilmGround ? dna?.accent : null) ?? MAG_D0;
  const CYAN = (onFilmGround ? dna?.accent2 : null) ?? CYAN_D0;
  // the gaps cut through the sun are the SKY showing through, so they are painted in whatever the sky is —
  // as a literal plum they would have striped the sun on any dark film of another hue (a deep green one).
  const SKY = onFilmGround ? night : SUN_GAP_D0;
  // the chrome runs white → cyan → magenta, i.e. between the two tubes: derived from them when they are the
  // film's, the original literal when they are not (which keeps the no-DNA frame byte-for-byte).
  const chrome = onFilmGround
    ? `linear-gradient(#fff, ${tint(CYAN, 0.55)} 40%, ${tint(MAG, 0.45)} 60%, ${MAG})` : CHROME_D0;
  const horizon = onFilmGround ? tint(MAG, 0.75) : HORIZON_D0;
  // the wordmark's backlight is the floor's own magenta. Guarded because an 8-digit hex is only a colour if
  // the token was a 6-digit one — anything else would make the whole drop-shadow invalid and silently drop it.
  const MAG_GLOW = /^#[0-9a-fA-F]{6}$/.test(MAG) ? `${MAG}99` : MAG;
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const hy = H * 0.46, cx = W / 2;
  const scroll = (t * 0.6) % (1 / 16);
  const titleUp = easeOutExpo(seg(t, 0.12, 0.5));

  // The wordmark is centred full-bleed and the tagline carries 0.5em tracking; neither had any width guard, so a
  // long title ran off-frame and a long tagline wrapped onto the sun artwork at 1:1. Measure both against the
  // usable width (leave 120px of neon breathing room) and cap at the register's design sizes, so short copy is
  // pixel-identical and only long copy shrinks.
  const usable = W - 120;
  const titleSize = Math.min(168, fitText({
    text: String(TITLE), withinWidth: usable, fontFamily: dispFace, fontWeight: 900,
    letterSpacing: '0.02em',
  }).fontSize);
  const tagSize = Math.min(30, fitText({
    text: String(TAGLINE), withinWidth: usable, fontFamily: monoFace, fontWeight: 700,
    letterSpacing: '0.5em',
  }).fontSize);

  return (
    <AbsoluteFill style={{background: ground}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="neon"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          {/* the sun's own yellow→orange is the colour a setting sun IS, the way CodeRain's green is its
              rain — it stays a literal; only the bottom stop, where the disc meets the floor's neon, is the
              film's (and with no DNA that stop is #ff2d95 exactly as before) */}
          <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe25a" /><stop offset="0.5" stopColor="#ff8a3c" /><stop offset="1" stopColor={MAG} /></linearGradient>
          <clipPath id="floor"><rect x="0" y={hy} width={W} height={H - hy} /></clipPath>
        </defs>

        {/* stars — white because a star IS a white point of light, not because white is this film's ink */}
        {[...Array(70)].map((_, i) => {
          const x = hash01(i) * W, y = hash01(i * 2) * hy * 0.92;
          const tw = 0.4 + 0.6 * Math.abs(Math.sin(frame * 0.08 + i));
          return <circle key={i} cx={x} cy={y} r={hash01(i * 3) * 1.8 + 0.5} fill="#fff" opacity={tw * 0.8} />;
        })}

        {/* retro sun with scanline gaps */}
        <g>
          <circle cx={cx} cy={hy} r={180} fill="url(#sun)" filter="url(#neon)" />
          {[...Array(7)].map((_, i) => <rect key={i} x={cx - 190} y={hy + 30 + i * 22} width={380} height={11 + i * 1.6} fill={SKY} />)}
        </g>

        {/* perspective floor */}
        <g clipPath="url(#floor)">
          {/* vertical converging lines */}
          {[...Array(27)].map((_, i) => {
            const off = i - 13;
            return <line key={i} x1={cx} y1={hy} x2={cx + off * 200} y2={H} stroke={CYAN} strokeWidth={1.6} strokeOpacity={0.5} filter="url(#neon)" />;
          })}
          {/* horizontal scrolling lines (perspective-compressed) */}
          {[...Array(16)].map((_, i) => {
            const d = ((i / 16) + scroll) % 1;
            const y = hy + (H - hy) * d * d;
            return <line key={i} x1={0} y1={y} x2={W} y2={y} stroke={MAG} strokeWidth={1.2 + d * 2.4} strokeOpacity={0.35 + d * 0.5} filter="url(#neon)" />;
          })}
        </g>
        {/* horizon glow line */}
        <line x1={0} y1={hy} x2={W} y2={hy} stroke={horizon} strokeWidth={2.5} filter="url(#neon)" />
      </svg>

      {/* neon chrome wordmark */}
      <div style={{position: 'absolute', left: 0, right: 0, top: hy - 250, textAlign: 'center',
        transform: `translateY(${(1 - titleUp) * 30}px)`, opacity: titleUp}}>
        <div style={{font: `900 ${titleSize}px/${leading(TITLE, 0.9)} ${dispFace}`, letterSpacing: '0.02em',
          background: chrome, WebkitBackgroundClip: 'text',
          backgroundClip: 'text', color: 'transparent', WebkitTextStroke: `2px ${CYAN}`, filter: `drop-shadow(0 0 24px ${MAG_GLOW})`}}>{TITLE}</div>
        <div style={{marginTop: 14, font: `700 ${tagSize}px/1 ${monoFace}`, letterSpacing: '0.5em',
          paddingLeft: '0.5em', color: CYAN, opacity: clamp01(seg(t, 0.45, 0.72)), textShadow: `0 0 18px ${CYAN}`}}>{TAGLINE}</div>
      </div>
    </AbsoluteFill>
  );
};
export default NeonGrid;
