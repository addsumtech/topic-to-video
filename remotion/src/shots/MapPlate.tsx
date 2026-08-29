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
import {captionBand, CONTENT_TOP, placeLabel} from '../runtime/layout';
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
  channel?: {label?: string; from?: [number, number]; to?: [number, number]; width?: number};
  scaleLabel?: string;
  note?: string;
}> = ({
  title = '',
  place = 'the place',
  marks: MARKS = [{label: 'north', x: 0.5, y: 0.1}, {label: 'west', x: 0.12, y: 0.55},
                  {label: 'east', x: 0.88, y: 0.55}, {label: 'south', x: 0.5, y: 0.92}],
  routes = true,
  channel,
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

      {/* a CHANNEL driven through the plate — a cut, a river, a corridor. Drawn under the marks, with the
          double bank a survey draws a waterway with, so it reads as a route and not as a highlight bar. */}
      {channel ? (() => {
        const a = channel.from ?? [0.10, 0.18], b = channel.to ?? [0.90, 0.86];
        const x1 = fx(a[0]), y1 = fy(a[1]), x2 = fx(b[0]), y2 = fy(b[1]);
        const on = easeOutCubic(clamp01(seg(t, 0.30, 0.62)));
        const len = Math.hypot(x2 - x1, y2 - y1) * on;
        const ang = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        const cw = Math.max(hair * 4, (channel.width ?? 0.02) * PW);
        // A QUARTER along, not the midpoint. The centre of a plate is where the subject's own mark lives by
        // construction, so a channel label at 50% lands on top of the place name every time.
        const mx = x1 + (x2 - x1) * 0.26, my = y1 + (y2 - y1) * 0.26;
        return (
          <React.Fragment>
            <div style={{position: 'absolute', left: x1, top: y1 - cw / 2, width: len, height: cw,
              background: ACC2, opacity: 0.22, transformOrigin: '0 50%', transform: `rotate(${ang}deg)`}} />
            {[-1, 1].map((sd) => (
              <div key={sd} style={{position: 'absolute', left: x1, top: y1 - cw / 2 + (sd > 0 ? cw : 0),
                width: len, height: hair * 2, background: ACC2,
                transformOrigin: '0 50%', transform: `rotate(${ang}deg)`}} />
            ))}
            {channel.label ? (
              <div style={{position: 'absolute', left: mx - W * 0.09, top: my + cw, width: W * 0.18,
                textAlign: 'center', opacity: on,
                font: `500 ${Math.round(W * 0.0135)}px/1.3 ${mono}`, color: ACC2,
                letterSpacing: '0.06em'}}>{channel.label}</div>
            ) : null}
          </React.Fragment>
        );
      })() : null}

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
        // The side is chosen by WHERE THERE IS ROOM, not by which half of the plate the mark sits in. Keyed
        // on the half, a mark near the right edge got a right-hand label that ran straight out of the plate
        // — Groningen and Maastricht both crossed the border in a delivered film. A label is clamped inside
        // the plate as well, so no combination of positions can push one out.
        // A LABEL IS SHOWN, NOT GUILLOTINED. The box was a flat min(W*0.15, PW*0.30) with `nowrap` and
        // `text-overflow: ellipsis`, so anything past about fifteen characters was silently cut — a
        // delivered film shipped "a university since 1636" and "and everyone passing through" as stubs.
        // A place name is short; a NOTE about a place is not, and both arrive through the same prop.
        // The box is measured from the text now (CJK sets one glyph per em, Latin about half), capped at a
        // third of the plate, and wraps to two lines rather than losing words.
        const lab = String(m.label ?? '');
        const labCjk = lab.length
          ? lab.replace(/[^\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/g, '').length / lab.length : 0;
        const labFont = Math.round(W * 0.0135);
        const labW = Math.max(W * 0.09,
          Math.min(PW * 0.34, lab.length * labFont * (0.52 + 0.48 * labCjk) * 0.62 + labFont));
        const gap = dot + Math.round(W * 0.006);
        const {left, align} = placeLabel(x, px0 + hair * 2, px1 - hair * 2, labW, gap);
        const rightSide = align === 'left';
        // AND IT MUST NOT LAND ON THE SUBJECT'S OWN NAME. The centre name is the one thing on the plate
        // that is always there and always in the same place, and nothing stopped a mark's label from
        // sitting on top of it — the label side is chosen by room at the plate's edges, which knows
        // nothing about the middle. Where the two boxes would meet, the label steps clear vertically,
        // away from the centre, which is always the shorter move.
        const nameH = Math.round(W * 0.030) * 1.2, nameTop = cy + dot * 2.4;
        const labTop0 = y - Math.round(W * 0.012);
        const labH = labFont * 2.6;
        const hits = left < cx + W * 0.13 && left + labW > cx - W * 0.13
          && labTop0 < nameTop + nameH && labTop0 + labH > nameTop;
        const labTop = hits ? (y < cy ? nameTop - nameH * 0.35 - labH : nameTop + nameH + nameH * 0.25) : labTop0;
        return (
          <React.Fragment key={'m' + i}>
            <div style={{position: 'absolute', left: x - dot / 2, top: y - dot / 2, width: dot, height: dot,
              borderRadius: dot, background: FG, opacity: on}} />
            <div style={{position: 'absolute', top: labTop, left, width: labW,
              textAlign: rightSide ? 'left' : 'right', opacity: on,
              font: `500 ${labFont}px/1.25 ${mono}`, color: DIM,
              display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
              overflow: 'hidden'}}>{m.label}</div>
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
