// SHOT · ProfileGrowth — one cross-section redrawn at successive states, each larger than the last, the
// earlier ones left ghosted behind it. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "it became something else by being ENLARGED, not by being replaced." That is a
// different claim from a pipeline (raw → machine → finished, three separate objects) and from a before/after
// (two states, one hidden at any moment). Here there is one object the whole time, and the argument is
// carried by the ghosts: you can see every earlier size still sitting inside the current one, which is why
// the last state is startling — a tunnel that kept being widened until the tunnel was the warehouse.
//
// Any film with an incremental-until-transformed subject can use it: a footprint, an allocation, a scope, a
// pit, a caseload. The states, their labels and the note are all props.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';

export const DURATION = 160;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';

type State = {label?: string; w?: number; h?: number; note?: string};   // w/h are 0..1 of the field

export const ProfileGrowth: React.FC<{
  kicker?: string;
  states?: State[];        // in order; the LAST one is what the thing became
  ground?: string;         // the line the profile is cut into ("street", "the bank", "grade")
  note?: string;
}> = ({
  kicker = 'THE SAME SECTION, WIDENED',
  states: STATES = [{label: 'at first', w: 0.16, h: 0.30},
                    {label: 'wider', w: 0.34, h: 0.48},
                    {label: 'and then this', w: 0.62, h: 0.72}],
  ground = '',
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? '#e5dac6';
  const disp = 'var(--f-display, Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  const top = CONTENT_TOP + H * 0.04;
  const bottom = H - captionBand(W, H) - H * 0.10;
  const fieldH = bottom - top;
  const fieldW = Math.min(W * 0.56, fieldH * 1.7);
  const fx = (W - fieldW) / 2;
  const baseY = bottom;                       // every profile is cut DOWN from the same ground line

  const kick = easeOutCubic(clamp01(seg(t, 0.02, 0.16)));
  const gline = easeOutCubic(clamp01(seg(t, 0.08, 0.28)));
  const land = easeOutExpo(clamp01(seg(t, 0.80, 0.94)));

  const states = STATES.slice(0, 5);
  const n = Math.max(1, states.length);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left: fx, top: CONTENT_TOP - H * 0.055, opacity: kick,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
        letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>

      {/* the ground the section is cut into — a heavier rule, with hatching above it */}
      <div style={{position: 'absolute', left: fx - W * 0.03, top: baseY,
        width: (fieldW + W * 0.06) * gline, height: hair * 3, background: FG}} />
      {Array.from({length: 26}).map((_, i) => {
        const x = fx - W * 0.03 + i * ((fieldW + W * 0.06) / 26);
        const on = clamp01(gline * 26 - i);
        return (
          <div key={'h' + i} style={{position: 'absolute', left: x, top: baseY - Math.round(W * 0.011),
            width: hair, height: Math.round(W * 0.011) * on, background: LINE,
            transform: 'rotate(20deg)', transformOrigin: '50% 100%'}} />
        );
      })}
      {ground ? (
        <div style={{position: 'absolute', left: fx - W * 0.03, top: baseY - Math.round(W * 0.026),
          opacity: gline, font: `500 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: DIM,
          letterSpacing: '0.06em'}}>{ground}</div>
      ) : null}

      {/* TWO PASSES, and the order is load-bearing. Drawing each state's fill and then its label meant the
          NEXT state's fill — larger by construction — covered the previous label, so every inner state was
          annotated invisibly. Fills first, all labels above them. */}
      {states.map((st, i) => {
        const a = 0.20 + i * (0.52 / n);
        const on = easeOutCubic(clamp01(seg(t, a, a + 0.52 / n + 0.06)));
        if (on <= 0) return null;
        const last = i === n - 1;
        const w = (st.w ?? 0.3) * fieldW, h = (st.h ?? 0.4) * fieldH;
        const x = fx + fieldW / 2 - w / 2;
        // the ghosts: earlier profiles keep a faint fill, the current one is drawn in the accent
        const fill = last ? ACC : (mix ? mix(SURF, ACC, 0.10 + 0.08 * i) : SURF);
        return (
          <div key={'f' + i} style={{position: 'absolute', left: x, top: baseY - h * on, width: w,
            height: h * on, background: fill, opacity: last ? 0.30 : 0.55,
            border: `${last ? hair * 3 : hair}px solid ${last ? ACC : LINE}`,
            borderBottom: 'none', boxSizing: 'border-box'}} />
        );
      })}
      {states.map((st, i) => {
        const a = 0.20 + i * (0.52 / n);
        const on = easeOutCubic(clamp01(seg(t, a, a + 0.52 / n + 0.06)));
        if (on <= 0) return null;
        const last = i === n - 1;
        const w = (st.w ?? 0.3) * fieldW, h = (st.h ?? 0.4) * fieldH;
        const x = fx + fieldW / 2 - w / 2;
        return (
          <div key={'l' + i} style={{position: 'absolute', left: x, top: baseY - h * on - Math.round(W * 0.021),
            width: w, opacity: on, textAlign: 'center',
            font: `${last ? 700 : 600} ${Math.round(W * (last ? 0.017 : 0.0135))}px/1.2 ${mono}`,
            color: last ? ACC : FG, letterSpacing: '0.05em', textWrap: 'balance'}}>{st.label}</div>
        );
      })}

      {/* what the last state turned out to be */}
      {states[n - 1]?.note ? (
        <div style={{position: 'absolute', left: fx, top: bottom + H * 0.045, width: fieldW,
          textAlign: 'center', opacity: land,
          font: `700 ${Math.round(W * 0.026)}px/1.25 ${disp}`, textWrap: 'balance', color: FG}}>{states[n - 1].note}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left: fx, top: bottom + H * 0.045 + Math.round(W * 0.030),
          width: fieldW, textAlign: 'center', opacity: land * 0.9,
          font: `400 ${Math.round(W * 0.0135)}px/1.4 var(--f-body, system-ui, sans-serif)`,
          color: DIM, textWrap: 'balance'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ProfileGrowth;
