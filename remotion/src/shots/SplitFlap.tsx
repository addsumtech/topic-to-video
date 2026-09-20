// SHOT · Split-Flap — a Solari departure-board register (mechanical, nostalgic-premium): a grid of flap tiles
// riffles through characters and SETTLES, staggered left→right, to spell the message. Amber-on-charcoal, a
// hairline split across each tile. The tactile "board updates" feel no digital shot has. Deterministic
// (each tile's flip stream + settle time = fn of cell + frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, clamp01, hash01, easeOutBack} from '../runtime/motion';
import {useDNA, mix, readableOn, shade} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const CH = '▚ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789▸✓'.split('');
const DEFAULT_ROWS = ['WORKBUDDY', 'DELIVERED'];

/** A row, and OPTIONALLY the tone it is lit in — named from the film's own DNA, never a raw colour. */
export type FlapRow = string | {text: string; tone?: 'accent' | 'accent2' | 'dim' | 'fg'};

// A BOARD'S WHOLE JOB IS THAT TWO ROWS CAN MEAN DIFFERENT THINGS, and for a while this one could not say
// so. Every flap was lit in a hardcoded `#ffcf4a`: `useDNA()` was read for the background and for nothing
// else, so a board sat in a green/blue film in a third colour that appeared in neither. The frame that
// found it was a beat whose entire narration was "只有两种状态：绿色的工作中，灰色的等待中" — and the
// register rendered both rows in the same amber, erasing the one distinction the beat existed to make.
// No prop could fix that, because there was no prop: the film could write the words and not the claim.
//
// So a row may name a TONE, and the tones are DNA token names rather than colours — a board cannot leave
// the film's palette, which is the rule `shot_proof` enforces for every other register. With no DNA the
// original amber is still exactly what renders, so an unthemed film is byte-identical to before.
export const SplitFlap: React.FC<{kicker?: string; rows?: FlapRow[]}> = ({
  kicker = 'STATUS · TODAY',rows: ROWS_IN = DEFAULT_ROWS} = {}) => {
  const t = useT();
  const dna = useDNA();
  const ROWS = (ROWS_IN ?? []).map((r) => (typeof r === 'string' ? r : String(r?.text ?? '')));
  const AMBER_ON = '#ffcf4a', AMBER_OFF = '#c9a24a';
  const toneOf = (i: number): {on: string; off: string} => {
    const row = ROWS_IN?.[i];
    const name = typeof row === 'string' ? undefined : row?.tone;
    const lit = !name || !dna ? (dna?.accent ?? AMBER_ON)
      : name === 'accent' ? dna.accent
      : name === 'accent2' ? (dna.accent2 ?? dna.accent)
      : name === 'dim' ? dna.dim
      : dna.fg;
    // The un-landed flap is the same ink at three quarters — one colour per row, two states of it, so a
    // rolling flap reads as the same tile mid-turn rather than as a different tile.
    return {on: lit, off: mix(lit, dna?.bg ?? '#0e0e12', 0.28)};
  };
  // THE BOARD IS A SURFACE, NOT A WORLD. Its plate, its flap bevel and its split were six charcoal literals,
  // so a film grounded warm white got a private black board bolted onto its paper — and the lit glyph, which
  // IS the film's accent, was then drawn on a tone the film never chose: measured, the light-key accent
  // #1d63d6 on the flap face #191920 is 2.7:1, a departure board whose message cannot be read.
  // So the flap is BUILT from the film's own ground, at the density steps the original tile already used
  // (+0.115 / +0.065 / +0.017 / +0.067 off its own ground), walked toward whichever pole it has room for —
  // which is what inverts the bevel on paper instead of clipping it. The split stays a shadow in the face at
  // either exposure, because a gap between two flaps is darker than the flaps in any light.
  const GROUND = dna?.bg ?? '#0a0a0e';
  const POLE = dna ? readableOn(GROUND, '#ffffff', '#05070c') : '#ffffff';
  const OPP = POLE === '#ffffff' ? '#05070c' : '#ffffff';
  // The four bevel stops are the ORIGINAL tile's own distances from its own ground — measured in the density
  // model as +0.115 / +0.065 / +0.017 / +0.067 — re-walked toward whichever pole THIS ground has room for.
  // `separated` is the wrong instrument here and said so out loud: its ladder starts at 0.08 and steps 0.03,
  // so it collapsed all four stops onto one tone on a light ground, and it THREW on a dark one because a
  // plate recessed below a near-black ground is a region that is not there. `mix` at the measured fractions
  // keeps the bevel on both keys, and the plate stays the subtle recess it always was.
  const F = (f: number) => mix(GROUND, POLE, f);
  const FACE_HI = dna ? F(0.115) : '#26262c';
  const FACE = dna ? F(0.065) : '#191920';
  const FACE_LO = dna ? F(0.017) : '#0e0e12';
  const FACE_FT = dna ? F(0.067) : '#1a1a20';
  // A GAP IS DARKER THAN THE FLAPS IN ANY LIGHT, so the split is always toward black — not toward `OPP`,
  // which on a paper ground would have drawn the hairline between two flaps in WHITE.
  const SPLIT = dna ? shade(FACE, 0.62) : '#000';
  const PLATE = dna ? mix(GROUND, OPP, 0.5) : '#050506';
  const PLATE_EDGE = dna ? F(0.10) : '#23232a';
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const COLS = Math.max(...ROWS.map((r) => r.length));
  // The tile yields to the frame: at 150px fixed, a nine-column board is 1462px wide — fine at 1920, and
  // 191px of letters off each edge of a 1080-wide portrait frame. Everything on the tile scales with it.
  const tw = Math.min(150, Math.floor((W * 0.92 - (COLS - 1) * 14) / COLS));
  const th = Math.round(tw * (178 / 150)), gap = 14;
  const glyphPx = Math.round(tw * (108 / 150));
  const boardW = COLS * tw + (COLS - 1) * gap;
  const x0 = (W - boardW) / 2, y0 = (H - (ROWS.length * th + (ROWS.length - 1) * gap)) / 2;

  // the longest tile's own offset under the original schedule, and the factor that pulls it back to
  // SETTLE_BY. A board small enough to have finished already keeps its timing exactly (factor capped at 1).
  const SETTLE_BY_START = 0.14, SETTLE_BY = 0.80;
  const span = (COLS - 1) * 0.05 + (ROWS.length - 1) * 0.14 + 0.05;
  const cascade = Math.min(1, (SETTLE_BY - SETTLE_BY_START) / Math.max(1e-6, span));

  const tiles: React.ReactNode[] = [];
  ROWS.forEach((label, r) => {
    const pad = Math.floor((COLS - label.length) / 2);
    for (let c = 0; c < COLS; c++) {
      const ch = label[c - pad] ?? ' ';
      // THE CASCADE IS NORMALISED TO THE BOARD, and for a long time it was an unbounded sum. Written as
      // `0.14 + c*0.05 + r*0.14`, the schedule passes t = 1 at column 17 on the first row and column 11 on
      // the third — so every tile beyond that NEVER lands, and a board wider than its demo copy flickers
      // random glyphs to the final frame. Rendered with real Chinese rows the last frame still showed more
      // than half the board unresolved; the English defaults are 8-10 columns, which is why it read fine.
      // That is the WordTunnel defect in another register: type the shot was given and never draws.
      // `SETTLE_BY` is the fraction the LAST tile lands at, so the whole board holds settled through the
      // close — which is also where every type gate samples.
      const settle = SETTLE_BY_START
        + (c * 0.05 + r * 0.14 + hash01(r * 40 + c) * 0.05) * cascade;
      const settled = t >= settle;
      const shown = settled ? ch : CH[Math.floor(hash01(r * 97 + c * 13 + Math.floor(frame / 2)) * CH.length)];
      const justLanded = clamp01((t - settle) / 0.05);
      const flapScale = settled ? 1 : 0.96;
      const tx = x0 + c * (tw + gap), ty = y0 + r * (th + gap);
      tiles.push(
        <div key={`${r}-${c}`} style={{position: 'absolute', left: tx, top: ty, width: tw, height: th,
          transform: `scaleY(${flapScale})`}}>
          <div style={{position: 'absolute', inset: 0, borderRadius: 12,
            background: `linear-gradient(${FACE_HI} 0%, ${FACE} 49%, ${FACE_LO} 51%, ${FACE_FT} 100%)`,
            border: `1px solid ${SPLIT}`, boxShadow: 'inset 0 1px 0 #ffffff10, 0 8px 20px #0007'}} />
          {/* hairline split */}
          <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 2, background: SPLIT, opacity: 0.7}} />
          <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            font: `800 ${glyphPx}px/1 var(--f-display, "Anton", Impact, sans-serif)`,
            color: settled ? toneOf(r).on : toneOf(r).off,
            opacity: settled ? 1 : 0.86, transform: `translateY(${(1 - justLanded) * 0}px)`,
            textShadow: settled ? `0 0 18px ${toneOf(r).on}55` : 'none'}}>{shown === ' ' ? '' : shown}</div>
        </div>
      );
    }
  });

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 34%, #17171d 0%, #0a0a0e 72%)')}}>
      {/* board backing plate */}
      <div style={{position: 'absolute', left: x0 - 30, top: y0 - 30, width: boardW + 60,
        height: ROWS.length * th + (ROWS.length - 1) * gap + 60, borderRadius: 22, background: PLATE,
        border: `1px solid ${PLATE_EDGE}`, boxShadow: '0 40px 120px #000b'}} />
      {tiles}
      {/* header label */}
      <div style={{position: 'absolute', left: 0, right: 0, top: y0 - 100, textAlign: 'center',
        color: dna?.dim ?? '#6f7078', font: '700 26px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.5em', paddingLeft: '0.5em'}}>{kicker}</div>
    </AbsoluteFill>
  );
};
export default SplitFlap;
