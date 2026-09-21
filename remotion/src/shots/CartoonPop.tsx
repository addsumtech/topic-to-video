// SHOT · Cartoon Pop — a CEL-SHADED cartoon register (the "style, not just content" axis): thick ink
// outlines, flat saturated fills, hard offset shadows (no gradients), squash-&-stretch bounce, a comic
// starburst + confetti. WorkBuddy pops in, zaps a messy task pile, and a "DONE!" burst pops. Deliberately
// playful — unlike every polished-digital shot. Deterministic (bounce = eased t; confetti seeded by index).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {leading} from '../runtime/cjkType';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, dnaPalette, mix, pilL, tint, shade} from '../runtime/dna';
import {paleEnd, onLight} from '../runtime/light';

export const DURATION = 155; // ~5.2s
// LEVEL-C: cel-shading is a TECHNIQUE (thick ink outlines, flat fills, hard offset shadows, squash-&-stretch),
// not a fixed palette — so on a themed DNA the whole cartoon re-hues into the film's world and the ink INVERTS to
// a light outline (a dark-mode / night-scene cartoon, still unmistakably cel-shaded). Flats come from
// dnaPalette() so the mascot, sun and accents stay 3 distinct hues. Null DNA = the original daylight cartoon.
const OUTLINE0 = '#1b2440';
const SKY0 = '#8fd0ff';
const BODY0 = '#4c8dff';
const FACE0 = '#fdf6e3';
const STAR0 = '#ffd23f';
const GREEN0 = '#2fcb6e';
const CONF0 = ['#ff6b6b', '#ffd23f', '#2fcb6e', '#4c8dff', '#b06cff', '#ff8fc7'];

// spiky comic starburst polygon
function starburst(cx: number, cy: number, spikes: number, ro: number, ri: number, phase: number): string {
  const pts: string[] = [];
  for (let i = 0; i < spikes * 2; i++) {
    const r = i % 2 === 0 ? ro : ri;
    const a = (Math.PI / spikes) * i + phase;
    pts.push(`${cx + Math.cos(a) * r},${cy + Math.sin(a) * r}`);
  }
  return 'M' + pts.join('L') + 'Z';
}

export const CartoonPop: React.FC<{label?: string}> = ({label = 'DONE!'} = {}) => {
  const dna = useDNA();
  const P = dnaPalette(dna, 6);
  const OUTLINE = dna?.fg ?? OUTLINE0;                       // ink inverts to a LIGHT outline on a dark ground
  const BODY = P?.[0] ?? BODY0, GREEN = P?.[1] ?? GREEN0, STAR = P?.[2] ?? STAR0;
  // THE FACE PLATE IS PICKED AGAINST THE INK, NOT AGAINST THE DARK. This was `shade(BODY, 0.72)` with the
  // note "must contrast the (now light) eyes/ink" — true on all eight presets, where the outline inverts to
  // a light one, and false the moment a film grounds on paper: there the ink stays dark, so the screen went
  // dark under dark eyes and a dark smile and the robot lost its face. Measured on a light ground
  // (2026-09-21, scripts/ink_contrast_qa.py): 11.1% of this register's ink under 3:1, largest region 0.47%
  // of the frame, and that region is the face plate. The plate now takes whichever side of BODY the outline
  // is not — a dark screen under a light outline, a pale one under a dark outline — by the same 0.72,
  // mirrored, so every dark preset renders exactly what it rendered before.
  const FACE = dna ? (pilL(OUTLINE) > 0.5 ? shade(BODY, 0.72) : tint(BODY, 0.72)) : FACE0;
  // A DAYLIGHT CARTOON CANNOT BE DRAWN WITH A NIGHT PALETTE. `mix(dna.fg, dna.bg, k)` is "mostly ink, a
  // little ground" — a white cloud and a white sheet on all eight presets, which are all dark, and a BLACK
  // cloud and a black sheet on a film grounded on paper. It is high-contrast, so no ink gate can see it;
  // this was found by reading the register, not by measuring it. What both wanted is the film's PALE end.
  //
  // AND A CLOUD NEEDS ROOM ABOVE THE SKY. If the sky is the film's own paper there is nothing lighter left
  // to draw a cloud in, so on a light film the sky takes a wash of the film's accent — which is what a
  // cartoon sky is anyway — leaving the pale end free for the cloud and the sheets to sit on it.
  const PALE = paleEnd(dna, '#ffffff');
  const SKYFILL = dna?.bgGrad ?? (dna && onLight(dna)
    ? `linear-gradient(${mix(dna.bg, dna.accent, 0.30)}, ${mix(dna.bg, dna.accent, 0.12)})`
    : dna?.bg) ?? `linear-gradient(${SKY0}, #b9e4ff)`;
  const CLOUD = dna ? mix(PALE, dna.bg, 0.16) : '#ffffff';
  const GRASS = dna ? mix(BODY, dna.bg, 0.62) : '#a7e17f';   // the ground plane recedes toward the film's ground
  const PAPER = dna ? mix(PALE, dna.bg, 0.12) : '#fffdf5', RULE = dna?.dim ?? '#c9ccd6';
  const CONF = P ?? CONF0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 + 30;

  // phases
  const papersIn = easeOutBack(seg(t, 0.06, 0.24));
  const zap = seg(t, 0.5, 0.62);              // papers poof
  const papersGone = clamp01(1 - zap);
  const robotIn = easeOutBack(seg(t, 0.22, 0.42));
  const robotBob = Math.sin(t * Math.PI * 6) * 6 * clamp01(seg(t, 0.42, 0.9));
  const burst = easeOutBack(seg(t, 0.6, 0.78));
  const doneIn = easeOutBack(seg(t, 0.7, 0.9));
  const conf = easeOutCubic(seg(t, 0.62, 1));

  // squash-stretch on robot landing: tall as it rises, squashed at contact, settle to 1
  const land = seg(t, 0.22, 0.42);
  const sy = 1 + (1 - robotIn) * 0.35 - Math.max(0, Math.sin(land * Math.PI)) * 0.0; // stretch while entering
  const sx = 2 - sy;

  return (
    <AbsoluteFill style={{background: SKYFILL}}>
      {/* flat cartoon clouds drifting */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[{x: 300, y: 200, s: 1}, {x: 1500, y: 300, s: 1.3}, {x: 900, y: 150, s: 0.8}].map((c, i) => {
          const dx = (t * 60 * (i + 1)) % (W + 400) - 200;
          const x = (c.x + dx) % (W + 400) - 100;
          return (
            // OUTLINED LIKE EVERYTHING ELSE IN THIS REGISTER. The sun, the grass, the sheets, the poof
            // and the burst all carry an 8px `OUTLINE`; only the clouds did not, and on a pale sky a pale
            // cloud with no edge is the one shape here a reader has to find rather than see. Drawn as a
            // silhouette UNDER the fills — three stroked ellipses would put arcs through the cloud's
            // middle, which is why they were bare in the first place.
            <g key={i} transform={`translate(${x},${c.y}) scale(${c.s})`}>
              <g fill={OUTLINE}>
                <ellipse cx={0} cy={0} rx={114} ry={48} />
                <ellipse cx={70} cy={10} rx={74} ry={44} />
                <ellipse cx={-70} cy={12} rx={68} ry={40} />
              </g>
              <g fill={CLOUD}>
                <ellipse cx={0} cy={0} rx={110} ry={44} />
                <ellipse cx={70} cy={10} rx={70} ry={40} />
                <ellipse cx={-70} cy={12} rx={64} ry={36} />
              </g>
            </g>
          );
        })}
        {/* sun */}
        <circle cx={W - 240} cy={200} r={90} fill={STAR} stroke={OUTLINE} strokeWidth={8} opacity={0.95} />
      </svg>

      {/* ground */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <path d={`M0,${H - 180} Q${W / 2},${H - 240} ${W},${H - 180} L${W},${H} L0,${H} Z`} fill={GRASS} stroke={OUTLINE} strokeWidth={8} />
      </svg>

      {/* messy task papers (poof away on zap) */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: papersGone}}>
        <g transform={`translate(${cx - 360},${cy - 40}) scale(${lerp(0.4, 1, papersIn) * (0.4 + 0.6 * papersGone)}) rotate(${-8})`}>
          {[0, 1, 2].map((i) => (
            <g key={i} transform={`translate(${i * 14},${-i * 20}) rotate(${(hash01(i + 3) - 0.5) * 16})`}>
              <rect x={16} y={16} width={200} height={250} rx={10} fill="#00000022" />
              <rect x={0} y={0} width={200} height={250} rx={10} fill={PAPER} stroke={OUTLINE} strokeWidth={6} />
              {[0, 1, 2, 3].map((k) => <rect key={k} x={26} y={40 + k * 44} width={148} height={12} rx={6} fill={RULE} />)}
            </g>
          ))}
        </g>
        {/* poof puffs at zap */}
        {zap > 0 && [...Array(8)].map((_, i) => {
          const a = (i / 8) * Math.PI * 2, d = zap * 120;
          return <circle key={i} cx={cx - 300 + Math.cos(a) * d} cy={cy - 40 + Math.sin(a) * d} r={lerp(30, 6, zap)} fill={CLOUD} stroke={OUTLINE} strokeWidth={5} opacity={1 - zap} />;
        })}
      </svg>

      {/* comic starburst behind the DONE */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${cx + 260},${cy - 120}) scale(${burst}) rotate(${t * 40})`}>
          <path d={starburst(0, 0, 14, 300, 150, 0)} fill={STAR} stroke={OUTLINE} strokeWidth={8} />
          <path d={starburst(0, 0, 14, 250, 130, 0.2)} fill={dna ? tint(STAR, 0.55) : '#fff3c4'} opacity={0.6} />
        </g>
      </svg>

      {/* WorkBuddy robot */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${cx - 120},${cy + 40 + robotBob + (1 - robotIn) * 420}) scale(${sx},${sy})`} opacity={robotIn > 0 ? 1 : 0}>
          {/* offset shadow */}
          <g transform="translate(10,12)"><rect x={-10} y={-190} width={260} height={250} rx={40} fill="#00000022" /></g>
          {/* antenna */}
          <line x1={120} y1={-190} x2={120} y2={-250} stroke={OUTLINE} strokeWidth={8} />
          <circle cx={120} cy={-260} r={16} fill={GREEN} stroke={OUTLINE} strokeWidth={7} />
          {/* head/body */}
          <rect x={-10} y={-190} width={260} height={250} rx={40} fill={BODY} stroke={OUTLINE} strokeWidth={9} />
          {/* face plate */}
          <rect x={20} y={-150} width={200} height={130} rx={26} fill={FACE} stroke={OUTLINE} strokeWidth={7} />
          {/* eyes (blink) */}
          {[70, 170].map((ex, i) => {
            const blink = Math.sin(t * Math.PI * 8) > 0.9 ? 0.15 : 1;
            return <ellipse key={i} cx={ex} cy={-95} rx={20} ry={26 * blink} fill={OUTLINE} />;
          })}
          {/* smile */}
          <path d="M78,-58 Q120,-30 162,-58" fill="none" stroke={OUTLINE} strokeWidth={7} strokeLinecap="round" />
          {/* little wave hand */}
          <g transform={`translate(250,-90) rotate(${Math.sin(t * Math.PI * 10) * 18})`}>
            <circle cx={0} cy={0} r={26} fill={BODY} stroke={OUTLINE} strokeWidth={8} />
          </g>
        </g>
      </svg>

      {/* motion lines around the DONE */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: doneIn}}>
        {[...Array(12)].map((_, i) => {
          const a = (i / 12) * Math.PI * 2;
          const r0 = 210, r1 = 210 + 70 * doneIn;
          return <line key={i} x1={cx + 260 + Math.cos(a) * r0} y1={cy - 120 + Math.sin(a) * r0} x2={cx + 260 + Math.cos(a) * r1} y2={cy - 120 + Math.sin(a) * r1} stroke={OUTLINE} strokeWidth={7} strokeLinecap="round" />;
        })}
      </svg>

      {/* DONE! comic text */}
      <div style={{position: 'absolute', left: cx + 60, top: cy - 210, width: 400, textAlign: 'center',
        transform: `scale(${doneIn}) rotate(-8deg)`, transformOrigin: '50% 50%'}}>
        {/* 0.9 is the comic-poster punch in Latin, where caps have no descenders. In Chinese the two
            wrapped lines crash into each other (measured 84px of a 130px line box). The floor lifts only
            for CJK, so the Latin poster keeps its punch exactly. */}
        <div style={{font: `900 130px/${leading(label, 0.9)} var(--f-display, "Baloo 2", Inter, system-ui, sans-serif)`, color: GREEN,
          WebkitTextStroke: `9px ${OUTLINE}`, paintOrder: 'stroke', letterSpacing: '-0.01em', textWrap: 'balance'}}>{label}</div>
      </div>

      {/* confetti */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {conf > 0 && [...Array(26)].map((_, i) => {
          const a = hash01(i) * Math.PI * 2, spd = 260 + hash01(i * 2) * 360;
          const x = cx + 260 + Math.cos(a) * spd * conf;
          const y = cy - 120 + Math.sin(a) * spd * conf + conf * conf * 260; // gravity
          const rot = hash01(i * 3) * 360 + conf * 540;
          return <rect key={i} x={x} y={y} width={18} height={26} rx={4} fill={CONF[i % CONF.length]} stroke={OUTLINE} strokeWidth={3}
            transform={`rotate(${rot} ${x + 9} ${y + 13})`} opacity={clamp01(1.2 - conf)} />;
        })}
      </svg>
    </AbsoluteFill>
  );
};
export default CartoonPop;
