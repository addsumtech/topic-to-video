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
//
// A POSITION ON A PLATE IS A CLAIM, AND SO IS A LINE BETWEEN TWO. This register used to supply both when the
// film did not. A mark with no coordinates was placed at `m.x ?? 0.5`, `m.y ?? 0.5` — ON the subject's own
// ring, with a zero-length route — and one outside 0..1 was clamped to the plate's border. A channel given a
// label but no ends was drawn from the demo's (0.10, 0.18) to (0.90, 0.86), straight across the plate. Marks
// past eight were cut by `.slice(0, 8)` with no word. And `routes` defaulted to TRUE, so every film that
// placed a few towns around its subject was drawn arguing that they converge on it — a relation nobody
// stated. Now: a mark needs `x` and `y` in 0..1, a channel needs `from` and `to`, more than eight marks
// throws, and routes are drawn only when the film asks (`routes: true`). The standalone demo still shows its
// compass marks converging, because that picture is the demo's own.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP, placeLabel} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 160;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', ACC2_D0 = '#2e5e4e', LINE_D0 = '#cdbfa7';

type Mark = {label?: string; x?: number; y?: number};   // x/y are 0..1 of the plate — REQUIRED

export const MAX_MAP_MARKS = 8;
const DEFAULT_MARKS: Mark[] = [{label: 'north', x: 0.5, y: 0.1}, {label: 'west', x: 0.12, y: 0.55},
                               {label: 'east', x: 0.88, y: 0.55}, {label: 'south', x: 0.5, y: 0.92}];

const unitPair = (v: unknown, what: string): [number, number] => {
  const ok = Array.isArray(v) && v.length === 2 && v.every((c) => typeof c === 'number' && c >= 0 && c <= 1);
  if (!ok) {
    throw new Error(`MapPlate: \`${what}\` must be [x, y] with both in 0..1 of the plate, got ${JSON.stringify(v)}. ` +
      'A channel is drawn between the two points the film names; without them it would run wherever the demo ran.');
  }
  return v as [number, number];
};

export const MapPlate: React.FC<{
  title?: string;
  place?: string;                 // the mark at the centre — the subject of the plate
  marks?: Mark[];                 // outer places, positioned in plate fractions
  routes?: boolean;               // draw hairlines from each mark INTO the centre — only when the film says so
  channel?: {label?: string; from?: [number, number]; to?: [number, number]; width?: number};
  scaleLabel?: string;
  note?: string;
}> = ({
  title = '',
  place = 'the place',
  marks: MARKS = DEFAULT_MARKS,
  routes: ROUTES,
  channel,
  scaleLabel = '',
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0011));

  // Every mark at the point the film gives, every mark once; see the header for what each check replaces.
  if (!Array.isArray(MARKS) || MARKS.length > MAX_MAP_MARKS) {
    throw new Error(
      `MapPlate takes 0-${MAX_MAP_MARKS} \`marks\` (got ${Array.isArray(MARKS) ? MARKS.length : typeof MARKS}). ` +
      'Past eight the labels crowd the plate edge and stop reading as places — keep the ones the argument ' +
      'turns on, or split the plate across two beats.');
  }
  const marks = MARKS.map((m, i) => {
    const x = Number(m?.x), y = Number(m?.y);
    if (m?.x == null || m?.y == null || !(x >= 0 && x <= 1) || !(y >= 0 && y <= 1)) {
      throw new Error(
        `MapPlate: mark ${i + 1}${m?.label ? ` ("${m.label}")` : ''} needs \`x\` and \`y\` in 0..1 of the plate ` +
        `(got x=${String(m?.x)}, y=${String(m?.y)}). Its position IS the claim — without one it would be drawn ` +
        "on top of the subject's own mark.");
    }
    return {...m, x, y};
  });
  // Convergence is a relation, so it is the film's to assert. The demo keeps its converging compass.
  const routes = ROUTES ?? (MARKS === DEFAULT_MARKS);

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

  // THE CHANNEL'S GEOMETRY, computed once: the drawing below and the mark labels (which must not land on the
  // channel's own label) both read it
  const chan = channel ? (() => {
    // the two ends the film names — no demo ends to fall back on (see the header)
    const a = unitPair(channel.from, 'channel.from'), b = unitPair(channel.to, 'channel.to');
    const x1 = fx(a[0]), y1 = fy(a[1]), x2 = fx(b[0]), y2 = fy(b[1]);
    const cw = Math.max(hair * 4, (channel.width ?? 0.02) * PW);
    // A QUARTER ALONG, ON WHICHEVER SIDE IS FURTHER FROM THE SUBJECT — and measured, not assumed. The
    // centre of a plate is where the subject's own mark lives by construction, and a FIXED fraction only
    // clears it for a channel that crosses the whole plate, which is what the default happens to be. A
    // short corridor between two nearby places — a thing a film authors, and what the CJK sweep fed —
    // put the label straight back onto the place name at 0.26 exactly as it had at 0.50.
    const nameTop = cy + dot * 2.4, nameH = W * 0.036, labH = W * 0.018;
    const far = (f: number) =>
      Math.hypot(x1 + (x2 - x1) * f - cx, y1 + (y2 - y1) * f - (nameTop + nameH / 2));
    const f = far(0.26) >= far(0.74) ? 0.26 : 0.74;
    const mx = x1 + (x2 - x1) * f, my = y1 + (y2 - y1) * f;
    // ...and when the channel runs so near the mark that NEITHER quarter clears it, the label sits above
    // its own bank instead of dropping into the name. A plate may draw a channel through its subject.
    const clash = Math.abs(mx - cx) < W * 0.22
      && my + cw < nameTop + nameH && my + cw + labH > nameTop;
    const labTop = clash ? my - cw - labH * 1.4 : my + cw;
    const labPx = Math.round(W * 0.0156);
    return {x1, y1, x2, y2, cw, mx, labTop, labPx, labBox: {l: mx - W * 0.09, t: labTop, r: mx + W * 0.09,
      b: labTop + labPx * 1.3 * 2}};
  })() : null;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {title ? (
        <div style={{position: 'absolute', left: px0, top: CONTENT_TOP - H * 0.055, opacity: frame,
          font: `600 ${Math.round(W * 0.0156)}px/1.2 ${mono}`, color: ACC,
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
      {chan ? (() => {
        const {x1, y1, x2, y2, cw, mx, labTop, labPx} = chan;
        const on = easeOutCubic(clamp01(seg(t, 0.30, 0.62)));
        const len = Math.hypot(x2 - x1, y2 - y1) * on;
        const ang = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
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
              <div style={{position: 'absolute', left: mx - W * 0.09, top: labTop, width: W * 0.18,
                textAlign: 'center', opacity: on,
                font: `500 ${labPx}px/1.3 ${mono}`, color: ACC2,
                letterSpacing: '0.06em'}}>{channel.label}</div>
            ) : null}
          </React.Fragment>
        );
      })() : null}

      {/* routes running INTO the centre — convergence, in the plate's own dialect */}
      {routes && marks.map((m, i) => {
        const st = 0.46 + i * 0.045;
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.16)));
        if (on <= 0) return null;
        const x = fx(m.x), y = fy(m.y);
        const len = Math.hypot(cx - x, cy - y) * on;
        const ang = Math.atan2(cy - y, cx - x) * 180 / Math.PI;
        return (
          <div key={'r' + i} style={{position: 'absolute', left: x, top: y - hair, width: len,
            height: hair * 2, background: ACC2, opacity: 0.75,
            transformOrigin: '0 50%', transform: `rotate(${ang}deg)`}} />
        );
      })}

      {/* outer marks */}
      {(() => {
        // LABELS ARE PLACED TOGETHER, NOT ONE AT A TIME. Each label used to choose its side alone, avoiding only
        // the centre name, so two marks a few percent apart set their labels into one run — with the library's
        // CJK fixture, 「自主循环持续运转」 and 「自主循环运转」 read as one line on a light plate (2026-10-17). Each
        // label now takes the first of four places (the roomy side, the other side, above, below) that touches
        // neither the centre name nor a label already placed; if none does, it keeps the roomy side.
        // Labels are set at ~30 px at 1080 (they were 26: under the readable floor text_safe_qa measures).
        const labFont = Math.round(W * 0.0156);
        const nameH = Math.round(W * 0.030) * 1.2, nameTop = cy + dot * 2.4;
        type Box = {l: number; t: number; r: number; b: number};
        const overlap = (a: Box, b: Box) =>
          Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));
        // what a label must not cover: the centre name, the centre ring, and EVERY mark's own dot
        const placed: Box[] = [{l: cx - W * 0.13, t: nameTop, r: cx + W * 0.13, b: nameTop + nameH},
          {l: cx - dot * 1.8, t: cy - dot * 1.8, r: cx + dot * 1.8, b: cy + dot * 1.8},
          ...marks.map((mm) => ({l: fx(mm.x) - dot, t: fy(mm.y) - dot, r: fx(mm.x) + dot, b: fy(mm.y) + dot})),
          ...(chan && channel?.label ? [chan.labBox] : [])];
        const lo = px0 + hair * 2, hi = px1 - hair * 2;
        return marks.map((m, i) => {
          const st = 0.44 + i * 0.045;
          const on = easeOutCubic(clamp01(seg(t, st, st + 0.14)));
          const x = fx(m.x), y = fy(m.y);
          // A LABEL IS SHOWN, NOT GUILLOTINED: measured from the text (CJK one glyph per em, Latin about half),
          // capped at a third of the plate, two lines at most rather than losing words.
          const lab = String(m.label ?? '');
          const labCjk = lab.length
            ? lab.replace(/[^\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/g, '').length / lab.length : 0;
          const labW = Math.max(W * 0.09,
            Math.min(PW * 0.34, lab.length * labFont * (0.52 + 0.48 * labCjk) * 0.62 + labFont));
          const lines = Math.min(2, Math.max(1, Math.ceil(lab.length * labFont * (0.52 + 0.48 * labCjk) / labW)));
          const labH = labFont * 1.3 * lines;
          const gap = dot + Math.round(W * 0.006);
          // the side with ROOM first (placeLabel), then the other side, then above, then below — each tried where it
          // falls, never pushed back over its own dot; one that leaves the plate is not a candidate
          const {align} = placeLabel(x, lo, hi, labW, gap);
          type Cand = {l: number; t: number; a: 'left' | 'right' | 'center'};
          const right: Cand = {l: x + gap, t: y - labH / 2, a: 'left'};
          const left: Cand = {l: x - gap - labW, t: y - labH / 2, a: 'right'};
          const above: Cand = {l: x - labW / 2, t: y - gap - labH, a: 'center'};
          const below: Cand = {l: x - labW / 2, t: y + gap, a: 'center'};
          const cands: Cand[] = (align === 'left' ? [right, left] : [left, right]).concat([above, below])
            .filter((c) => c.l >= lo && c.l + labW <= hi && c.t >= top && c.t + labH <= bottom);
          const box = (c: {l: number; t: number}): Box => ({l: c.l, t: c.t, r: c.l + labW, b: c.t + labH});
          const cost = (c: {l: number; t: number}) => placed.reduce((s2, p) => s2 + overlap(box(c), p), 0);
          // the first clear place; if none is clear, the least covered one; if none fits the plate, the roomy side
          const pick = cands.find((c) => cost(c) === 0)
            ?? (cands.length ? cands.reduce((a2, b2) => (cost(b2) < cost(a2) ? b2 : a2)) : (align === 'left' ? right : left));
          placed.push(box(pick));
          return (
            <React.Fragment key={'m' + i}>
              <div style={{position: 'absolute', left: x - dot / 2, top: y - dot / 2, width: dot, height: dot,
                borderRadius: dot, background: FG, opacity: on}} />
              <div style={{position: 'absolute', top: pick.t, left: Math.min(Math.max(pick.l, lo), hi - labW), width: labW,
                textAlign: pick.a, opacity: on, textWrap: 'balance',
                font: `500 ${labFont}px/1.25 ${mono}`, color: DIM,
                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                overflow: 'hidden'}}>{m.label}</div>
            </React.Fragment>
          );
        });
      })()}

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
          <div style={{font: `500 ${Math.round(W * 0.0156)}px/1 ${mono}`, color: DIM}}>{scaleLabel}</div>
        </div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left: px0, right: W - px1, top: bottom + H * 0.018,
          opacity: easeOutCubic(clamp01(seg(t, 0.80, 0.94))),
          font: `400 ${Math.round(W * 0.0156)}px/1.4 ${mono}`, color: DIM, textWrap: 'balance',
          letterSpacing: '0.05em'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default MapPlate;
