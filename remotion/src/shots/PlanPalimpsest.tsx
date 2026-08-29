// SHOT · PlanPalimpsest — two plans registered over each other: the footprint of what WAS here, under the
// outline of what is here now. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "this open space is the shape of something that is gone." A before/after wipe gets
// this wrong twice — it implies the two states are alternatives, and it hides one of them at any moment.
// A palimpsest keeps both on the page at once, in register, which is the actual claim: the new thing is
// not merely later, it is the SAME GROUND. The lower plan is filled; the upper is drawn as hairline over
// it, with registration crosses at the corners so the eye reads them as one survey, not two pictures.
//
// Topic-free: any pair of "what stood here" / "what stands here" — a demolished wing, a rerouted line, a
// deprecated module under its replacement.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {Plane, DEPTH} from '../runtime/depth';
import {useDNA} from '../runtime/dna';

export const DURATION = 160;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', ACC2_D0 = '#2e5e4e', LINE_D0 = '#cdbfa7';

export const PlanPalimpsest: React.FC<{
  kicker?: string;
  underLabel?: string;      // what was here
  underDate?: string;
  underNote?: string;
  overLabel?: string;       // what is here now
  overDate?: string;
  overNote?: string;
  bays?: number;            // how many structural bays the lower plan is drawn with
}> = ({
  kicker = 'ON THE SAME GROUND',
  underLabel = 'the earlier plan', underDate = '', underNote = '',
  overLabel = 'the later plan', overDate = '', overNote = '',
  bays = 5} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const body = 'var(--f-body, system-ui, sans-serif)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  const top = CONTENT_TOP + H * 0.03;
  // The legend under the plan is a swatch + label + date + a NOTE that wraps to two lines, and H*0.11 (119px
  // at 1080) holds about half of that. The overflow used to fall into empty page; once the caption band grew
  // it fell under the burned subtitle instead, and beat 26 of a delivered film shipped with its last legend
  // line printed through. Reserved from the type that goes in it, like every other block in this library.
  const legendH = Math.round(W * 0.020 + W * 0.0145 + W * 0.0135 * 2 * 1.4 + H * 0.045);
  const bottom = H - captionBand(W, H) - legendH;
  const pw = Math.min(W * 0.44, (bottom - top) * 1.6);
  const ph = (bottom - top) * 0.76;
  const x0 = (W - pw) / 2, y0 = top + (bottom - top) * 0.12;

  const kick = easeOutCubic(clamp01(seg(t, 0.02, 0.16)));
  const under = easeOutCubic(clamp01(seg(t, 0.10, 0.42)));
  const over = easeOutCubic(clamp01(seg(t, 0.46, 0.78)));
  const land = easeOutExpo(clamp01(seg(t, 0.74, 0.92)));

  const n = Math.max(2, Math.min(9, bays));
  const bayW = pw / n;
  const cross = Math.round(W * 0.011);

  const Cross: React.FC<{cxp: number; cyp: number; on: number}> = ({cxp, cyp, on}) => (
    <>
      <div style={{position: 'absolute', left: cxp - cross, top: cyp, width: cross * 2, height: hair,
        background: LINE, opacity: on}} />
      <div style={{position: 'absolute', left: cxp, top: cyp - cross, width: hair, height: cross * 2,
        background: LINE, opacity: on}} />
    </>
  );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left: W * 0.08, top: CONTENT_TOP - H * 0.055, opacity: kick,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
        letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>

      {/* THE LOWER PLAN — a BUILDING footprint, not a filled box: two rows of piers inside a wall, so
          the eye reads masonry. It sits INSIDE the later boundary, which is the whole point.
          It also sits ONE PLANE BACK. That is not atmosphere: this register's entire claim is that two
          surveys are in REGISTER on the same ground, and a flat drawing can only assert it — the eye has
          no reason to read one as under the other. A plane's worth of separation gives it one, and when
          the beat's camera moves, the two drift by different amounts, which is what a viewer already knows
          to read as "these are at different distances". The labels stay on the subject plane, because they
          are the film speaking ABOUT the plans, not part of either. */}
      <Plane depth={DEPTH.behind}>
      {Array.from({length: n}).map((_, i) => {
        const on = clamp01(under * n - i);
        const bx = x0 + i * bayW;
        return (
          <React.Fragment key={'u' + i}>
            {/* the bay's floor */}
            <div style={{position: 'absolute', left: bx, top: y0, width: bayW * on, height: ph,
              background: ACC, opacity: 0.16}} />
            {/* its two piers, north and south — a nave reads as a rhythm of supports */}
            <div style={{position: 'absolute', left: bx + bayW * 0.30, top: y0 + ph * 0.16,
              width: bayW * 0.22 * on, height: ph * 0.12, background: ACC, opacity: 0.85}} />
            <div style={{position: 'absolute', left: bx + bayW * 0.30, top: y0 + ph * 0.72,
              width: bayW * 0.22 * on, height: ph * 0.12, background: ACC, opacity: 0.85}} />
          </React.Fragment>
        );
      })}
      {/* the outer wall of the lower plan, drawn with real thickness */}
      <div style={{position: 'absolute', left: x0, top: y0, width: pw * under, height: ph,
        border: `${hair * 4}px solid ${ACC}`, boxSizing: 'border-box', opacity: 0.9}} />
      </Plane>

      {/* THE UPPER PLAN — the later ground, DASHED and larger, enclosing the footprint in register.
          Dashed because it is an edge you cannot see on site: the square has no wall. */}
      <div style={{position: 'absolute', left: x0 - W * 0.045, top: y0 - H * 0.055,
        width: (pw + W * 0.09) * over, height: ph + H * 0.11,
        border: `${hair * 2}px dashed ${FG}`, boxSizing: 'border-box'}} />
      <Cross cxp={x0 - W * 0.045} cyp={y0 - H * 0.055} on={over} />
      <Cross cxp={x0 + pw + W * 0.045} cyp={y0 - H * 0.055} on={over} />
      <Cross cxp={x0 - W * 0.045} cyp={y0 + ph + H * 0.055} on={over} />
      <Cross cxp={x0 + pw + W * 0.045} cyp={y0 + ph + H * 0.055} on={over} />

      {/* the two legends, side by side under the plan — a filled swatch and an outline swatch */}
      <div style={{position: 'absolute', left: x0, top: bottom + H * 0.045, width: pw,
        display: 'flex', gap: W * 0.03, opacity: land}}>
        {[{sw: 'fill' as const, label: underLabel, date: underDate, note: underNote, tone: ACC},
          {sw: 'line' as const, label: overLabel, date: overDate, note: overNote, tone: FG}].map((L, i) => (
          <div key={i} style={{flex: 1, display: 'flex', gap: Math.round(W * 0.010), alignItems: 'flex-start'}}>
            <div style={{width: Math.round(W * 0.020), height: Math.round(W * 0.014), flexShrink: 0,
              marginTop: Math.round(W * 0.004),
              background: L.sw === 'fill' ? ACC : 'transparent', opacity: L.sw === 'fill' ? 0.35 : 1,
              border: `${hair * 2}px solid ${L.tone}`}} />
            <div>
              <div style={{font: `600 ${Math.round(W * 0.0195)}px/1.25 ${disp}`, color: L.tone}}>{L.label}</div>
              {L.date ? (
                <div style={{font: `500 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
                  letterSpacing: '0.06em', marginTop: Math.round(W * 0.002)}}>{L.date}</div>
              ) : null}
              {L.note ? (
                <div style={{font: `400 ${Math.round(W * 0.0135)}px/1.4 ${body}`, color: DIM,
                  marginTop: Math.round(W * 0.003)}}>{L.note}</div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
export default PlanPalimpsest;
