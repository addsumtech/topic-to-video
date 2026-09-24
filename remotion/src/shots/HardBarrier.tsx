// SHOT · HardBarrier — conditions that effort can close, and conditions nothing closes: the approach steps
// over the gaps and stops dead at a wall with no opening in it.
//
// THE ARGUMENT SHAPE, and why it is not a list. A beat that names several requirements usually gets a list
// register, and a list says every row is the same KIND of thing. This claim is that they are not: some of
// the named conditions are a GAP — a step you close by learning it, rewording it, doing it — and some are a
// WALL, where no amount of effort or phrasing opens anything, and the only honest move is to say so. Drawn
// as a list, "no reframing closes a legal barrier" is a sentence beside four identical bullets. Drawn here,
// the approach visibly steps over the gaps and is visibly stopped by the face of the wall, so the frame
// argues it with or without the caption.
//
// Re-usable by construction: a visa or a licence in a hiring film, an export-control rule, a hard
// eligibility criterion, a physical clearance. The topic arrives entirely through props; the defaults are
// generic placeholder copy so a film that forgets to pass its own is caught by the demo-copy gate.
//
// REFUSALS. No condition, or one with no label, throws. A board where NOTHING is a wall throws too — that
// frame draws a run with a clear road at the end of it, which is the opposite claim, convincingly, past
// every gate.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, cadence} from '../runtime/motion';
import {captionBand, CONTENT_TOP, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix, readableOn, dimOn} from '../runtime/dna';

export const DURATION = 150; // 5s

const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', ACC_D0 = '#e0563f', DIM_D0 = '#7b8a9c', LINE_D0 = '#22303f';
const SURF_D0 = '#121a24';

export const MAX_BARRIER_CONDITIONS = 8;

/** A condition on the way in. `kind` is the FILM's reading and is never inferred from the row's position. */
export type BarrierCondition = {
  /** what the condition is, in the film's words */
  label?: string;
  /** 'gap' = effort or wording closes it · 'barrier' = nothing does */
  kind?: 'gap' | 'barrier';
};

const DEMO: BarrierCondition[] = [
  {label: 'something you could learn', kind: 'gap'},
  {label: 'something you could say better', kind: 'gap'},
  {label: 'the one nothing opens', kind: 'barrier'},
];

export const HardBarrier: React.FC<{
  kicker?: string;
  /** what is travelling in — an application, a shipment, a claim */
  subject?: string;
  conditions?: BarrierCondition[];
  /** the word for a condition effort closes */
  gapLabel?: string;
  /** the word for a condition nothing closes */
  wallLabel?: string;
  /** one line under the section, in the film's voice */
  note?: string;
}> = ({
  kicker = '',
  subject = 'the way in',
  conditions = DEMO,
  gapLabel = 'a gap',
  wallLabel = 'a wall',
  note = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  const rows = (Array.isArray(conditions) ? conditions : []).filter(
    (c) => c && String(c.label ?? '').trim());
  if (!rows.length) {
    throw new Error(
      'HardBarrier needs at least one `conditions` entry with a `label`. The whole form is which named ' +
      'conditions are steps and which are walls; with none there is a ground line arguing nothing.');
  }
  if (rows.length !== (Array.isArray(conditions) ? conditions.length : 0)) {
    throw new Error(
      'HardBarrier was given a condition with no `label`. An unnamed riser on the ground is furniture — ' +
      'name it, or leave it out.');
  }
  if (rows.length > MAX_BARRIER_CONDITIONS) {
    throw new Error(
      `HardBarrier holds at most ${MAX_BARRIER_CONDITIONS} conditions, got ${rows.length}. Past that each ` +
      'label falls under the size a viewer reads at a glance — split the beat.');
  }
  const walls = rows.filter((c) => c.kind === 'barrier');
  if (!walls.length) {
    throw new Error(
      'HardBarrier was given no condition with `kind: "barrier"`. Every condition being a gap draws a run ' +
      'with an open road at the end of it, which is the opposite of this register\'s claim — mark the ' +
      'condition(s) nothing closes, or use a list register.');
  }
  const gaps = rows.filter((c) => c.kind !== 'barrier');

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const disp = dna?.fontDisplay ?? 'var(--f-display, Inter, system-ui, sans-serif)';
  const body = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const spacing = dna?.labelSpacing ?? '0.12em';
  const upper = dna?.uppercaseLabels ? 'uppercase' : 'none';

  // The wall is masonry cut from the film's own stock — a course darker than the surface so the courses
  // read, never a second hue. Its ink is measured against it rather than assumed.
  const STONE = mix(SURF, FG, 0.18);
  const COURSE = mix(STONE, GROUND, 0.45);
  const INK_ON_STONE = readableOn(STONE, FG, GROUND, '#ffffff', '#0a0d14');
  const DIM_ON_GROUND = dimOn(GROUND, FG, 4.5);

  const U = Math.min(W, H);
  const top = CONTENT_TOP;
  const bottom = H - captionBand(W, H);

  const kickPx = Math.round(U * 0.023);
  const notePx = Math.round(U * 0.027);
  const labelPx = Math.round(U * 0.026);
  const tagPx = Math.round(U * 0.019);
  const subjPx = Math.round(U * 0.030);

  const noteH = note ? inkBlockH(notePx, 2) + Math.round(U * 0.022) : 0;
  const kickH = kicker ? inkBlockH(kickPx) + Math.round(U * 0.026) : 0;
  const zoneTop = top + kickH;
  const zoneBot = bottom - noteH;
  const zoneH = Math.max(U * 0.26, zoneBot - zoneTop);

  // LAYOUT BY THE ROOM, not by naming an aspect. The run travels along the frame's LONG axis, so a portrait
  // frame walks DOWN the page and meets the wall as a course across the foot. Both cases are one geometry
  // with the axes swapped; the type never rotates.
  const portrait = W < H;

  // The run: `gaps.length` risers spaced along it, then the wall occupying the last third.
  const padA = Math.round((portrait ? H : W) * 0.09);           // margin along the run
  const runLen = (portrait ? zoneH : W) - padA * 2;
  const wallLen = Math.round(runLen * 0.34);
  const walkLen = runLen - wallLen;
  const riserStep = walkLen / (gaps.length + 1);

  // The approach lands its steps as LANDINGS, not on a ramp: one per gap, then the stop.
  const landed = cadence(clamp01(seg(t, 0.10, 0.74)), gaps.length + 1, 1.15);
  const reached = landed * walkLen;
  // The recoil: the run hits the face and the head knocks back a little, once.
  const hit = clamp01(seg(t, 0.74, 0.82));
  const knock = Math.sin(hit * Math.PI) * (U * 0.012);
  const headA = padA + Math.min(reached, walkLen) - knock;
  const wallIn = easeOutCubic(clamp01(seg(t, 0.06, 0.34)));
  const tagIn = easeOutCubic(clamp01(seg(t, 0.80, 0.94)));

  // across-axis geometry: the ground sits low in the zone so the wall has height to rise into
  const acrossSpan = portrait ? W : zoneH;
  const groundAcross = portrait ? Math.round(W * 0.34) : Math.round(zoneTop + zoneH * 0.70);
  const wallRise = Math.round(acrossSpan * (portrait ? 0.34 : 0.78));
  const riserH = Math.round(acrossSpan * (portrait ? 0.055 : 0.085));

  /** (along, across) → absolute (left, top). Along runs left→right in landscape, top→bottom in portrait. */
  const alongX = (a: number) => (portrait ? 0 : a);
  const alongY = (a: number) => (portrait ? zoneTop + a : 0);

  const wallStartA = padA + walkLen;
  const labelW = Math.round(portrait ? W * 0.44 : Math.max(riserStep * 0.95, U * 0.16));

  const Riser: React.FC<{i: number; label: string}> = ({i, label}) => {
    const a = padA + riserStep * (i + 1);
    const on = clamp01((reached - (riserStep * (i + 1) - riserStep * 0.5)) / (riserStep * 0.5));
    const box = portrait
      ? {left: groundAcross - riserH, top: alongY(a) - Math.round(riserH * 0.28),
         width: riserH, height: Math.round(riserH * 0.56)}
      : {left: alongX(a) - Math.round(riserH * 0.28), top: groundAcross - riserH,
         width: Math.round(riserH * 0.56), height: riserH};
    return (
      <>
        <div style={{position: 'absolute', ...box, background: mix(GROUND, FG, 0.10),
          borderTop: `2px solid ${on > 0.5 ? ACC : LINE}`, opacity: 0.55 + 0.45 * wallIn}} />
        <div style={{position: 'absolute',
          left: portrait ? groundAcross + Math.round(U * 0.03) : alongX(a) - labelW / 2,
          top: portrait ? alongY(a) - labelPx : groundAcross + Math.round(U * 0.035),
          width: labelW, textAlign: portrait ? 'left' : 'center',
          color: on > 0.5 ? FG : DIM_ON_GROUND, opacity: 0.35 + 0.65 * wallIn,
          font: `500 ${labelPx}px/${leading(label, 1.32)} ${body}`}}>{label}</div>
        <div style={{position: 'absolute',
          left: portrait ? groundAcross + Math.round(U * 0.03) : alongX(a) - labelW / 2,
          top: portrait ? alongY(a) - labelPx + inkBlockH(labelPx, 1) + Math.round(U * 0.008)
                        : groundAcross + Math.round(U * 0.035) + inkBlockH(labelPx, 2)
                          + Math.round(U * 0.014),
          width: labelW, textAlign: portrait ? 'left' : 'center',
          color: DIM_ON_GROUND, opacity: on * 0.9,
          font: `600 ${tagPx}px/1.3 ${body}`, letterSpacing: spacing, textTransform: upper as any}}>
          {gapLabel}
        </div>
      </>
    );
  };

  const wallBox = portrait
    ? {left: groundAcross - wallRise, top: alongY(wallStartA), width: wallRise, height: wallLen}
    : {left: alongX(wallStartA), top: groundAcross - wallRise, width: wallLen, height: wallRise};

  // THE WALL IS BUILT OF THE BARRIERS — one course per named condition, so the mass a viewer sees is made
  // of exactly the things the film listed. A single block with the names joined into one line would be a
  // caption on a rectangle; this way the height of the wall IS the count, and nothing is invented to fill it.
  const courseH = (portrait ? wallLen : wallRise) / walls.length;
  const coursePx = Math.min(Math.round(U * 0.026), Math.round(courseH * 0.40));

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {kicker ? (
        <div style={{position: 'absolute', top, left: Math.round(W * 0.07), right: Math.round(W * 0.07),
          color: DIM_ON_GROUND, opacity: wallIn,
          font: `600 ${kickPx}px/1.3 ${body}`, letterSpacing: spacing, textTransform: upper as any}}>
          {kicker}
        </div>
      ) : null}

      {/* the ground the approach travels on */}
      <div style={{position: 'absolute',
        left: portrait ? groundAcross : padA, top: portrait ? zoneTop + padA : groundAcross,
        width: portrait ? 2 : runLen, height: portrait ? runLen : 2,
        background: LINE, opacity: 0.9 * wallIn}} />

      {/* the approach: the stretch actually covered, in the accent, ending where it was stopped */}
      <div style={{position: 'absolute',
        left: portrait ? groundAcross - 2 : padA,
        top: portrait ? zoneTop + padA : groundAcross - 2,
        width: portrait ? 6 : Math.max(0, headA - padA), height: portrait ? Math.max(0, headA - padA) : 6,
        background: ACC, opacity: 0.95}} />

      {/* the subject, riding the head of the approach */}
      <div style={{position: 'absolute',
        left: portrait ? groundAcross - Math.round(U * 0.32) - Math.round(U * 0.04)
                       : Math.max(padA, headA - Math.round(U * 0.32) - Math.round(U * 0.022)),
        top: portrait ? zoneTop + headA - subjPx : groundAcross - Math.round(U * 0.075) - subjPx,
        width: Math.round(U * 0.32), textAlign: 'right', color: ACC, opacity: 0.6 + 0.4 * wallIn,
        font: `700 ${subjPx}px/1.2 ${disp}`}}>{subject}</div>

      {gaps.map((g, i) => <Riser key={i} i={i} label={String(g.label)} />)}

      {/* THE WALL — its courses ARE the named barriers, and its face has no opening anywhere */}
      <div style={{position: 'absolute', ...wallBox, background: STONE,
        transform: `scale${portrait ? 'Y' : 'X'}(${0.2 + 0.8 * wallIn})`,
        transformOrigin: portrait ? 'top' : 'left',
        borderLeft: portrait ? 'none' : `${Math.max(3, Math.round(U * 0.006))}px solid ${ACC}`,
        borderTop: portrait ? `${Math.max(3, Math.round(U * 0.006))}px solid ${ACC}` : 'none',
        display: 'flex', flexDirection: 'column'}}>
        {walls.map((wv, i) => (
          <div key={i} style={{position: 'relative', flex: '1 1 0', minHeight: 0,
            display: 'flex', alignItems: 'center',
            padding: `0 ${Math.round(U * 0.018)}px`,
            borderBottom: i < walls.length - 1 ? `1px solid ${COURSE}` : 'none'}}>
            {/* the bond: one staggered head joint per course, so the face reads as masonry, not a table */}
            <div style={{position: 'absolute', top: 0, bottom: 0,
              left: `${(i % 2 ? 0.34 : 0.66) * 100}%`, width: 1, background: COURSE, opacity: 0.8}} />
            <div style={{position: 'relative', color: INK_ON_STONE, opacity: wallIn,
              font: `600 ${coursePx}px/${leading(String(wv.label), 1.28)} ${disp}`}}>{String(wv.label)}</div>
          </div>
        ))}
      </div>
      <div style={{position: 'absolute',
        left: portrait ? groundAcross - wallRise : alongX(wallStartA),
        width: portrait ? wallRise : wallLen,
        top: portrait ? alongY(wallStartA) + wallLen + Math.round(U * 0.018)
                      : groundAcross + Math.round(U * 0.035),
        textAlign: 'center', color: DIM_ON_GROUND, opacity: tagIn,
        font: `600 ${tagPx}px/1.3 ${body}`, letterSpacing: spacing, textTransform: upper as any}}>
        {wallLabel}
      </div>

      {note ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.07), right: Math.round(W * 0.07),
          top: zoneBot + Math.round(U * 0.012), color: DIM_ON_GROUND, opacity: tagIn,
          font: `400 ${notePx}px/${leading(note, 1.4)} ${body}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default HardBarrier;
