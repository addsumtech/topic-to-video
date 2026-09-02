// SHOT · Versus Split — a head-to-head split screen: two contenders slide in from opposite edges across a
// diagonal seam, a VS badge slams in the middle, attribute rows tick in per side, and the winner side lights
// up. The "A vs B / this beats that" register (family H — comparison). Attributes/winner are QUALITATIVE and
// overridable (a real film supplies the honest comparison). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette, mix, shade, tint, separated, separatedPair, readableOn, readableOnAll, dimOn, TONE_MIN_STEP} from '../runtime/dna';

export const DURATION = 155; // ~5.2s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'WINNER',
];

type Side = {label?: string; points?: string[]};

// `ground` is THIS HALF's fill, not the film's. The three inks below were literals chosen for a near-black
// half; once `separatedPair` gives each half a real tone, a literal light grey lands on a mid-blue and the
// right-hand points drop to ~2:1. Ink is picked against the surface it actually sits on.
const Panel: React.FC<{side: Side; enter: number; align: 'left' | 'right'; tone: string; win: boolean;
  t: number; base: number; ground: string; themed: boolean}> = ({
  side, enter, align, tone, win, t, base, ground, themed}) => {
  // The EFFECTIVE ground, not the half. A winning panel paints `${tone}2e` over its own half — 18% of the
  // accent — and the text sits on that composite, which is lighter than the half it was picked against.
  // Measured: picking ink from the half alone left the right column at 2.63:1 after the halves were
  // separated. Ink is chosen against the surface that is actually under it.
  //
  // ONLY WHEN A DESIGN SYSTEM IS PRESENT. With no DNA the register keeps its original literals byte for
  // byte — `test_null_dna_preserves_every_original_colour` is the contract, and it is the right one: the
  // un-themed render is the register's own authored look, and this derivation is about surviving grounds
  // the author never saw.
  const surface = win ? mix(ground, tone, 0.18) : ground;
  const strong = themed ? readableOn(surface, '#ffffff', '#0a0c12') : (win ? '#fff' : '#c7cee0');
  const soft = themed ? dimOn(surface, strong) : '#aeb6ca';
  // The chip must step away from the surface it sits ON, not merely be the accent: once the half is
  // mixed toward that same accent the two are the same tone and the chip loses its shape. Same rule
  // as the halves, applied one level down.
  // Toward whichever POLE has headroom, not toward the accent: on a half already mixed toward that accent
  // the two are the same tone and `separated` throws rather than paint a region that is not there — which
  // is how this line was written the first time.
  const chipBg = themed ? separated(surface, readableOn(surface, '#ffffff', '#05070c'), TONE_MIN_STEP * 1.4) : tone;
  const chipInk = themed ? readableOn(chipBg, '#ffffff', '#04120d') : '#04120d';
  return (
  <div style={{position: 'absolute', top: 0, bottom: 0, [align]: 0, width: '58%',
    transform: `translateX(${(align === 'left' ? -1 : 1) * (1 - enter) * 60}%)`,
    display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: align === 'left' ? '0 0 0 130px' : '0 130px 0 0',
    alignItems: align === 'left' ? 'flex-start' : 'flex-end',
    background: win ? `linear-gradient(${align === 'left' ? 105 : 255}deg, ${tone}2e, #0000 70%)` : 'transparent'}}>
    <div style={{color: strong, font: '800 92px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
      textShadow: win ? `0 0 40px ${tone}88` : 'none'}}>{side.label}</div>
    <div style={{marginTop: 30, display: 'flex', flexDirection: 'column', gap: 18,
      alignItems: align === 'left' ? 'flex-start' : 'flex-end'}}>
      {(side.points ?? []).slice(0, 4).map((p, i) => {
        const on = clamp01(seg(t, base + i * 0.08, base + 0.2 + i * 0.08));
        return <div key={i} style={{opacity: on, transform: `translateY(${(1 - on) * 10}px)`,
          display: 'flex', flexDirection: align === 'left' ? 'row' : 'row-reverse', alignItems: 'center', gap: 14,
          color: soft, font: '600 32px/1 var(--f-body, Inter, system-ui, sans-serif)'}}>
          <span style={{color: tone, fontWeight: 800}}>{win ? '✓' : '•'}</span>{p}</div>;
      })}
    </div>
    {win ? <div style={{marginTop: 34, padding: '12px 28px', borderRadius: 999, background: chipBg, color: chipInk,
      font: '800 30px/1 var(--f-body, Inter, system-ui, sans-serif)', opacity: clamp01(seg(t, 0.8, 0.95))}}>WINNER</div> : null}
  </div>
  );
};

export const VersusSplit: React.FC<{left?: Side; right?: Side; winner?: number; title?: string}> = ({
  left: LEFT = {label: 'Before', points: ['Manual steps', 'Hours lost', 'Easy to miss']},
  right: RIGHT = {label: 'After', points: ['One command', 'Seconds', 'Always caught']},
  winner: WINNER = 1, title: TITLE = 'The difference'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const lEnter = easeOutExpo(seg(t, 0.08, 0.42));
  const rEnter = easeOutExpo(seg(t, 0.16, 0.5));
  const vs = easeOutBack(clamp01(seg(t, 0.46, 0.64)));
  const titleIn = easeOutCubic(seg(t, 0.02, 0.16));
  // The title is CENTRED ACROSS THE SEAM, so it sits on both halves and an ink chosen for one is
  // wrong for the other. Measured on the literal it replaces: 2.51:1 on the dark key, 1.07:1 on the
  // light one — invisible. `readableOnAll` maximises the WORST of the two, which is the only case a
  // viewer sees. Un-themed keeps its original literal.
  // The two panel tones and the split ground were hardcoded blue/teal, so on a themed film they OVERRODE
  // the DNA across most of the frame — measured at 55% of the frame's chromatic ink sitting at hue 222 in a
  // green/amber film, on three separate beats. Winner takes the film's primary accent, the other its
  // second; with no DNA both fall back to the exact original literals, whichever side wins.
  const vsPal = dnaPalette(dna, 2);
  // The two sides must ALWAYS take different tones. Written as two independent ternaries on WINNER, a
  // board that never set `winner` fell through both and handed BOTH sides the same colour — the split
  // vanished into one flat ground and the palette check read "clean" because there was only one hue left.
  const winLeft = WINNER === 0;
  const toneL = vsPal ? vsPal[winLeft ? 0 : 1] : '#5b8cff';
  const toneR = vsPal ? vsPal[winLeft ? 1 : 0] : '#37d4a6';
  const ground = dna?.bg ?? '#0a0c12';
  // 0.12 into a near-black ground left the two halves visually identical; the un-themed original separated
  // them clearly (navy vs plum), so the themed one has to separate too — hue AND a little lightness.
  // 0.22 lit the whole frame far brighter than the rest of a dark film; 0.11 keeps it in the film's
  // luminance band (0.118 / 0.166 against the original's 0.103 / 0.090) while separating the two halves
  // by 28 RGB — MORE distinguishable than the un-themed original's 18, not less.
  // The two halves are DERIVED to separate, not mixed by eye. The 0.11 above was itself a reduction from
  // 0.22 on the reasoning that a brighter frame would leave "the rest of a dark film" behind — a premise
  // this runtime has since falsified (every beat can carry its own ground, and the delivery gate rewards a
  // film whose light moves). Measured, the old fraction put both halves within 0.10 of the ground in the
  // density model: this register spanned 54% of the frame and inked 2.0%, a composition that is there and
  // invisible. `separated()` walks the mix until each half is a surface the instrument — and an eye — can
  // see, and stops there.
  // `separatedPair`, not two independent `separated` calls: ink is measured against the frame's own median,
  // and two halves that cover the whole frame CREATE that median between them — separating each from the
  // ground moved this register from 3.2% to 3.3%. The pair has to separate from each other.
  const [halfL, halfR] = dna ? separatedPair(ground, toneL, toneR) : ['#141a2e', '#1e1420'];
  const titleInk = dna ? readableOnAll([halfL, halfR], '#ffffff', '#05070c') : '#aeb6ca';
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('#0a0c12'), overflow: 'hidden'}}>
      {/* two grounds */}
      <div style={{position: 'absolute', inset: 0, background: `linear-gradient(120deg, ${halfL} 0%, ${halfL} 50%, ${halfR} 50%, ${halfR} 100%)`}} />
      {/* diagonal seam */}
      <div style={{position: 'absolute', top: -60, bottom: -60, left: '50%', width: 6, background: '#0a0c12',
        transform: 'translateX(-50%) rotate(8deg)', boxShadow: '0 0 30px #000'}} />

      <div style={{position: 'absolute', top: 54, left: 0, right: 0, textAlign: 'center', opacity: titleIn, zIndex: 5,
        color: titleInk, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <Panel side={LEFT} enter={lEnter} align="left" tone={toneL} win={WINNER === 0} t={t} base={0.5} ground={halfL} themed={Boolean(dna)} />
      <Panel side={RIGHT} enter={rEnter} align="right" tone={toneR} win={WINNER === 1} t={t} base={0.56} ground={halfR} themed={Boolean(dna)} />

      {/* VS badge */}
      <div style={{position: 'absolute', left: '50%', top: '50%', transform: `translate(-50%,-50%) scale(${vs}) rotate(${lerp(-14, 0, vs)}deg)`,
        width: 150, height: 150, borderRadius: '50%',
        background: dna ? `radial-gradient(circle at 40% 35%, ${dna.surface}, ${shade(dna.bg, 0.2)})`
                        : 'radial-gradient(circle at 40% 35%, #2a3048, #12141f)',
        border: `3px solid ${dna?.surfaceBorder ?? '#454d68'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 6,
        boxShadow: '0 20px 60px #000a'}}>
        <div style={{color: '#fff', font: '900 58px/1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em'}}>VS</div>
      </div>
    </AbsoluteFill>
  );
};
export default VersusSplit;
