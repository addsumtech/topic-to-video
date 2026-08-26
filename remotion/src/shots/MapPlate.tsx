// SHOT · MapPlate — an engraved map plate: a graticule, a place mark, leader-lined labels, a scale bar.
// Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "where a thing sits, and what that position does to it." A network diagram says the
// same nouns but in the wrong dialect — it belongs to systems and integrations, and it makes a river town
// look like a service mesh. A plate says position: the graticule fixes the frame, the mark fixes the
// place, and when `routes` is on, hairlines run from the outer labels INTO the mark, which is what
// convergence actually looks like on a map.
//
// Topic-free: the marks and their positions are props, so any film arguing from location — a hub, a
// frontier, a site, a catchment — can use it.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 160;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', ACC2_D0 = '#2e5e4e', LINE_D0 = '#cdbfa7';

type Mark = {label?: string; x?: number; y?: number};   // x/y are 0..1 of the plate

export const MapPlate: React.FC<{
  title?: string;
  place?: string;                 // the mark at the centre — the subject of the plate
  marks?: Mark[];                 // outer places, positioned in plate fractions
  routes?: boolean;               // draw hairlines from each mark INTO the centre
  scaleLabel?: string;
  note?: string;
}> = ({
  title = '',
  place = 'the place',
  marks: MARKS = [{label: 'north', x: 0.5, y: 0.1}, {label: 'west', x: 0.12, y: 0.55},
                  {label: 'east', x: 0.88, y: 0.55}, {label: 'south', x: 0.5, y: 0.92}],
  routes = true,
  scaleLabel = '',
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0011));

  // the plate: a framed rectangle inside the content zone, kept clear of the caption band
  const top = CONTENT_TOP + H * 0.01;
  const bottom = H - captionBand(W, H) - H * 0.06;
  const px0 = W * 0.20, px1 = W * 0.80;
  const PW = px1 - px0, PH = bottom - top;
  const fx = (u: number) => px0 + clamp01(u) * PW;
  const fy = (v: number) => top + clamp01(v) * PH;
  const cx = fx(0.5), cy = fy(0.52);

  const frame = easeOutCubic(clamp01(seg(t, 0.02, 0.20)));
  const grat = easeOutCubic(clamp01(seg(t, 0.12, 0.40)));
  const centre = easeOutCubic(clamp01(seg(t, 0.34, 0.50)));
  const dot = Math.max(6, Math.round(W * 0.006));

  const GRAT_N = 5;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {title ? (
        <div style={{position: 'absolute', left: px0, top: CONTENT_TOP - H * 0.055, opacity: frame,
          font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
          letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{title}</div>
      ) : null}

      {/* the plate frame — a double rule, the way an engraved plate is bounded */}
      <div style={{position: 'absolute', left: px0, top, width: PW * frame, height: PH,
        border: `${hair * 2}px solid ${LINE}`, boxSizing: 'border-box'}} />
      <div style={{position: 'absolute', left: px0 + hair * 5, top: top + hair * 5,
        width: (PW - hair * 10) * frame, height: PH - hair * 10,
        border: `${hair}px solid ${LINE}`, boxSizing: 'border-box', opacity: 0.7}} />

      {/* graticule */}
      {Array.from({length: GRAT_N}).map((_, i) => {
        const u = (i + 1) / (GRAT_N + 1);
        const on = clamp01(grat * GRAT_N - i);
        return (
          <React.Fragment key={'g' + i}>
            <div style={{position: 'absolute', left: fx(u), top, width: hair, height: PH * on,
              background: LINE, opacity: 0.55}} />
            <div style={{position: 'absolute', left: px0, top: fy(u), width: PW * on, height: hair,
              background: LINE, opacity: 0.55}} />
          </React.Fragment>
        );
      })}

      {/* routes running INTO the centre — convergence, in the plate's own dialect */}
      {routes && MARKS.slice(0, 8).map((m, i) => {
        const st = 0.46 + i * 0.045;
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.16)));
        if (on <= 0) return null;
        const x = fx(m.x ?? 0.5), y = fy(m.y ?? 0.5);
        const len = Math.hypot(cx - x, cy - y) * on;
        const ang = Math.atan2(cy - y, cx - x) * 180 / Math.PI;
        return (
          <div key={'r' + i} style={{position: 'absolute', left: x, top: y - hair, width: len,
            height: hair * 2, background: ACC2, opacity: 0.75,
            transformOrigin: '0 50%', transform: `rotate(${ang}deg)`}} />
        );
      })}

      {/* outer marks */}
      {MARKS.slice(0, 8).map((m, i) => {
        const st = 0.44 + i * 0.045;
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.14)));
        const x = fx(m.x ?? 0.5), y = fy(m.y ?? 0.5);
        const rightSide = (m.x ?? 0.5) > 0.5;
        return (
          <React.Fragment key={'m' + i}>
            <div style={{position: 'absolute', left: x - dot / 2, top: y - dot / 2, width: dot, height: dot,
              borderRadius: dot, background: FG, opacity: on}} />
            <div style={{position: 'absolute', top: y - Math.round(W * 0.012),
              left: rightSide ? x + dot : undefined, right: rightSide ? undefined : W - x + dot,
              textAlign: rightSide ? 'left' : 'right', width: W * 0.14, opacity: on,
              font: `500 ${Math.round(W * 0.0135)}px/1.25 ${mono}`, color: DIM,
              paddingLeft: rightSide ? Math.round(W * 0.006) : 0,
              paddingRight: rightSide ? 0 : Math.round(W * 0.006)}}>{m.label}</div>
          </React.Fragment>
        );
      })}

      {/* the subject: a ringed mark and its name, set in the display face */}
      <div style={{position: 'absolute', left: cx - dot * 1.6, top: cy - dot * 1.6,
        width: dot * 3.2, height: dot * 3.2, borderRadius: dot * 3.2,
        border: `${hair * 3}px solid ${ACC}`, opacity: centre,
        transform: `scale(${0.6 + 0.4 * centre})`}} />
      <div style={{position: 'absolute', left: cx - W * 0.13, top: cy + dot * 2.4, width: W * 0.26,
        textAlign: 'center', opacity: centre,
        font: `700 ${Math.round(W * 0.030)}px/1.2 ${disp}`, color: ACC}}>{place}</div>

      {/* scale bar, bottom-left inside the plate */}
      {scaleLabel ? (
        <div style={{position: 'absolute', left: px0 + W * 0.018, top: bottom - H * 0.055,
          opacity: grat, display: 'flex', alignItems: 'center', gap: Math.round(W * 0.006)}}>
          <div style={{display: 'flex'}}>
            {[0, 1, 2, 3].map((k) => (
              <div key={k} style={{width: Math.round(W * 0.016), height: Math.round(W * 0.0055),
                background: k % 2 ? 'transparent' : FG, border: `${hair}px solid ${FG}`}} />
            ))}
          </div>
          <div style={{font: `500 ${Math.round(W * 0.0115)}px/1 ${mono}`, color: DIM}}>{scaleLabel}</div>
        </div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left: px0, right: W - px1, top: bottom + H * 0.018,
          opacity: easeOutCubic(clamp01(seg(t, 0.80, 0.94))),
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default MapPlate;
