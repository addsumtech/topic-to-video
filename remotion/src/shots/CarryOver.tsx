// SHOT · CarryOver — a handoff in which only SOME of what was there crosses over.
//
// WHAT IT ARGUES. A form is filled in one place and a COPY of it arrives in another, and the copy is not the
// same document: the fields marked as carried come through, and the rest arrive as the printed rule with
// nothing on it. That second sheet — complete in its ruling and incomplete in its ink — IS the claim. The
// library could already draw "a run that stops short" (LastLeg) and "before → after" (TermDiff), and neither
// says this: LastLeg asserts that MOST of the distance was covered, which is the opposite proportion when a
// handoff carries one field of four; a diff says what CHANGED, when nothing here changed — it was simply not
// brought. The office object for exactly that is a duplicate form with a carbon under it.
//
// WHY IT IS REUSABLE. The argument shape is "a transfer with a loss of fields": an export that drops columns,
// a summary that keeps the conclusion and not the caveats, a translation, a schema migration, a referral
// letter, an API version bump. The topic arrives entirely through props — the two places are `from`/`to`, the
// fields are the film's own, and the words for the two states are props too, so the form speaks any language.
//
// THE CLAIM COMES FROM THE PROP. `carried` is read off each field and from nowhere else: no index rule, no
// hash, no clock. A field with no `label` throws rather than drawing a nameless rule, and past
// MAX_CARRYOVER_FIELDS it throws with the maximum instead of silently dropping the tail — a form that omits
// a row while still looking like a form is the failure this register exists to draw.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, lerp} from '../runtime/motion';
import {captionBand, CONTENT_TOP, fitTextPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix, readableOn, dimOn} from '../runtime/dna';
import {onAccentInk} from '../runtime/onAccent';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s

/** Five rows is where a sheet stops being a form and becomes a table: at 16:9 the zone gives each row
 *  ~0.085·U, which still sets a label at 0.030·U beside a value at 0.036·U. A sixth takes both under the
 *  size at which a viewer reads a field name at a glance. */
export const MAX_CARRYOVER_FIELDS = 5;

const BG_D0 = '#10131a', FG_D0 = '#eef2f8', DIM_D0 = '#8b93a8',
  ACC_D0 = '#d8743c', SURF_D0 = '#191d26', LINE_D0 = '#2b3140';

type Field = {
  /** the name printed in the form's left column — required, because a rule with no field name is furniture */
  label?: string;
  /** what the first copy holds in that field */
  value?: string;
  /** whether this field reaches the SECOND copy. The film says so; nothing here infers it. */
  carried?: boolean;
};

const DEMO: Field[] = [
  {label: 'the decision', value: 'what was agreed', carried: true},
  {label: 'the reason', value: 'why it was agreed', carried: false},
  {label: 'what was rejected', value: 'and on what grounds', carried: false},
];

export const CarryOver: React.FC<{
  kicker?: string;
  /** where the handoff leaves */
  from?: string;
  /** where it arrives */
  to?: string;
  fields?: Field[];
  /** the word for a field that came through */
  carriedLabel?: string;
  /** the word for a field that did not */
  droppedLabel?: string;
  note?: string;
}> = ({
  kicker = 'THE HANDOVER',
  from = 'first copy',
  to = 'second copy',
  fields = DEMO,
  carriedLabel = 'carried',
  droppedLabel = 'not carried',
  note = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();

  const rows = (Array.isArray(fields) ? fields : []).filter((f) => f && String(f.label ?? '').trim());
  if (!rows.length) {
    throw new Error(
      'CarryOver needs at least one `fields` entry with a `label`. The whole form is which fields reach the ' +
      'second copy; with no field there is a ruled sheet arguing nothing.');
  }
  if (rows.length !== (Array.isArray(fields) ? fields.length : 0)) {
    throw new Error(
      'CarryOver was given a field with no `label`. A rule with no field name beside it is furniture — name ' +
      'the field, or leave it out.');
  }
  if (rows.length > MAX_CARRYOVER_FIELDS) {
    throw new Error(
      `CarryOver holds at most ${MAX_CARRYOVER_FIELDS} fields, got ${rows.length}. Past that the field name ` +
      'and its value both fall under the size a viewer reads at a glance — split the beat, or use a table.');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const LINE = dna?.line ?? LINE_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const RAD = dna?.radius ?? 6;
  const BW = Math.max(1, dna?.borderWidth ?? 1);
  const disp = dna?.fontDisplay ?? 'var(--f-display, Inter, system-ui, sans-serif)';
  const body = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';

  // The carbon copy is the SAME stock, one shade off the ground — a second ply, not a second colour.
  const CARBON = mix(SURF, GROUND, 0.55);
  const INK_ON_SHEET = readableOn(SURF, FG, GROUND, '#ffffff', '#0a0d14');
  const INK_ON_CARBON = readableOn(CARBON, FG, GROUND, '#ffffff', '#0a0d14');
  const DIM_ON_SHEET = dimOn(SURF, INK_ON_SHEET, 4.5);
  const DIM_ON_CARBON = dimOn(CARBON, INK_ON_CARBON, 4.5);
  // A value that CAME THROUGH is still an ordinary form entry, so it is set in the accent as text, at the
  // contrast the carbon can carry — never in a colour reserved for marks.
  const CARRIED_INK = readableOn(CARBON, ACC, INK_ON_CARBON);
  // The state chip is the one REVERSED object on the sheet: a solid block of the accent with its ink chosen
  // by measurement (`onAccentInk`), which is where a system's second accent gets to be type at all on a
  // light stock.
  const CHIP_BLOCK = readableOn(CARBON, ACC, INK_ON_CARBON);
  const CHIP_INK = onAccentInk(CHIP_BLOCK, dna?.accent2, dna?.onAccent, GROUND);

  const U = Math.min(W, H);
  const top = CONTENT_TOP;
  const bottom = H - captionBand(W, H);
  const stacked = W < H * 1.15;          // decided by the ROOM: a narrow frame puts the copies one over the other

  const kickPx = Math.round(U * 0.024);
  const headPx = Math.round(U * 0.030);
  const notePx = Math.round(U * 0.028);
  const noteH = note ? inkBlockH(notePx, 2) + Math.round(U * 0.02) : 0;

  const zoneTop = top + inkBlockH(kickPx) + Math.round(U * 0.03);
  const zoneBot = bottom - noteH;
  const zoneH = Math.max(U * 0.3, zoneBot - zoneTop);

  const gap = Math.round(U * 0.055);
  const sheetW = stacked ? Math.round(W * 0.82) : Math.round((Math.min(W * 0.9, U * 1.62) - gap) / 2);
  const sheetH = stacked ? Math.round((zoneH - gap) / 2) : Math.round(Math.min(zoneH, U * 0.62));
  const padX = Math.round(sheetW * 0.07);
  const padY = Math.round(sheetH * 0.10);
  const headH = inkBlockH(headPx) + Math.round(U * 0.016);
  const rowH = Math.max(Math.round(U * 0.05), Math.floor((sheetH - padY * 2 - headH) / rows.length));
  const labelPx = Math.min(Math.round(U * 0.024), Math.round(rowH * 0.34));
  const valuePx = Math.min(Math.round(U * 0.029), Math.round(rowH * 0.42));
  const labelW = Math.round((sheetW - padX * 2) * 0.40);
  const valueW = (sheetW - padX * 2) - labelW - Math.round(U * 0.012);

  const leftX = stacked ? Math.round((W - sheetW) / 2) : Math.round(W / 2 - gap / 2 - sheetW);
  const rightX = stacked ? leftX : Math.round(W / 2 + gap / 2);
  const topY = zoneTop + Math.round((stacked ? 0 : Math.max(0, (zoneH - sheetH) / 2)));
  const botY = stacked ? topY + sheetH + gap : topY;

  const kickIn = clamp01(seg(t, 0.02, 0.12));
  const sheetIn = easeOutCubic(clamp01(seg(t, 0.03, 0.18)));
  // DRAWN OUT, NOT SNAPPED. The pull spans a third of the clip because that is what the action is — a hand
  // drawing a duplicate from under a form — and because a reveal confined to a fifth of the clip leaves the
  // register measuring as a still: the sheet is the largest object on the frame and it should be moving for
  // as long as the narration is explaining what is on it.
  const carbonIn = easeInOutCubic(clamp01(seg(t, 0.16, 0.56)));
  const noteIn = clamp01(seg(t, 0.80, 0.90));
  // Each carried value presses through in order, AFTER the carbon is out. A field that was not carried has
  // no press at all — there is nothing on screen that could be mistaken for it arriving late.
  const pressAt = (i: number) => easeOutCubic(clamp01(seg(t, 0.52 + i * 0.085, 0.68 + i * 0.085)));

  const Row: React.FC<{f: Field; i: number; carbon: boolean}> = ({f, i, carbon}) => {
    const label = String(f.label ?? '');
    const value = String(f.value ?? '');
    const carried = f.carried === true;
    const ink = carbon ? INK_ON_CARBON : INK_ON_SHEET;
    const dim = carbon ? DIM_ON_CARBON : DIM_ON_SHEET;
    const show = carbon ? (carried ? pressAt(i) : 0) : 1;
    const lPx = fitTextPx(label, labelW, labelPx, {usable: 0.98});
    const vPx = fitTextPx(value, valueW, valuePx, {usable: 0.98});
    return (
      <div style={{position: 'absolute', left: padX, top: padY + headH + i * rowH, width: sheetW - padX * 2,
        height: rowH, boxSizing: 'border-box', display: 'flex', alignItems: 'center'}}>
        <div style={{width: labelW, flex: 'none', color: dim, textWrap: 'balance',
          letterSpacing: dna?.labelSpacing ?? '0.08em',
          font: `500 ${lPx}px/${leading(label, 1.25)} ${mono}`}}>{label}</div>
        <div style={{flex: 1, minWidth: 0, position: 'relative', height: rowH}}>
          {/* the printed rule is ALWAYS there — on the carbon it is what a missing field looks like */}
          <div style={{position: 'absolute', left: 0, right: 0, bottom: Math.round(rowH * 0.22),
            height: Math.max(1, BW), background: carbon && !carried ? LINE : mix(LINE, ink, 0.25)}} />
          {value ? (
            <div style={{position: 'absolute', left: 0, right: 0, bottom: Math.round(rowH * 0.30),
              color: carbon ? CARRIED_INK : ink, opacity: show,
              transform: glide(`translateY(${lerp(Math.round(U * 0.012), 0, show)}px)`, show !== 1),
              overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
              font: `600 ${vPx}px/${leading(value, 1.2)} ${body}`}}>{value}</div>
          ) : null}
          {carbon && !carried ? (
            <div style={{position: 'absolute', right: 0, bottom: Math.round(rowH * 0.28),
              color: dim, opacity: clamp01(carbonIn),
              font: `500 ${Math.round(lPx * 0.9)}px/1.2 ${mono}`,
              letterSpacing: dna?.labelSpacing ?? '0.08em'}}>{droppedLabel}</div>
          ) : null}
        </div>
      </div>
    );
  };

  const Sheet: React.FC<{x: number; y: number; head: string; carbon: boolean; enter: number}> = ({
    x, y, head, carbon, enter}) => {
    const ink = carbon ? INK_ON_CARBON : INK_ON_SHEET;
    const dim = carbon ? DIM_ON_CARBON : DIM_ON_SHEET;
    const hPx = fitTextPx(head, sheetW - padX * 2 - Math.round(U * 0.14), headPx, {usable: 0.98});
    // THE SECOND COPY IS PULLED OUT FROM UNDER THE FIRST, and the travel is the register's whole reveal:
    // it starts exactly BEHIND the top sheet — which is what "a carbon under the form" looks like — and
    // draws out to its own place. An earlier version nudged it 54px and faded it in, which reads as a second
    // panel appearing beside the first and says nothing about where it came from; it also left the shot in
    // the library's stillest third, measured, for a form whose one action is a sheet being drawn out.
    const px = carbon ? lerp(leftX, x, enter) : x;
    const py = carbon ? lerp(topY, y, enter) : y + lerp(U * 0.02, 0, enter);
    return (
      // the sheet travels by its LAYOUT position, which Skia rounds the same way it rounds a translate: the
      // type on it carries the unlock while it is being drawn out (runtime/glide.ts)
      <div style={{position: 'absolute', left: px, top: py, width: sheetW, height: sheetH, boxSizing: 'border-box',
        transform: glide(undefined, enter !== 1),
        background: carbon ? CARBON : SURF, border: `${BW}px solid ${LINE}`, borderRadius: RAD,
        opacity: carbon ? clamp01(enter * 4) : clamp01(enter * 1.2),
        boxShadow: carbon
          ? `0 ${Math.round(U * 0.006)}px ${Math.round(U * 0.02)}px #00000014`
          : `0 ${Math.round(U * 0.012)}px ${Math.round(U * 0.03)}px #00000022`}}>
        <div style={{position: 'absolute', left: padX, top: padY, right: padX, display: 'flex',
          alignItems: 'baseline', justifyContent: 'space-between', gap: Math.round(U * 0.02)}}>
          <div style={{color: ink, textWrap: 'balance',
            font: `700 ${hPx}px/${leading(head, 1.2)} ${disp}`}}>{head}</div>
          {carbon && carriedLabel ? (
            <div style={{flex: 'none', opacity: clamp01(seg(t, 0.44, 0.56)),
              background: CHIP_BLOCK, color: CHIP_INK, borderRadius: Math.max(2, RAD),
              padding: `${Math.round(U * 0.006)}px ${Math.round(U * 0.014)}px`, whiteSpace: 'nowrap',
              letterSpacing: dna?.labelSpacing ?? '0.08em',
              font: `700 ${Math.round(hPx * 0.50)}px/1.25 ${mono}`}}>{carriedLabel}</div>
          ) : null}
        </div>
        <div style={{position: 'absolute', left: padX, right: padX, top: padY + headH - Math.round(U * 0.010),
          height: Math.max(1, BW * 2), background: mix(LINE, ink, 0.35), opacity: 0.9}} />
        {rows.map((f, i) => <Row key={i} f={f} i={i} carbon={carbon} />)}
      </div>
    );
  };

  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', top, left: 0, right: 0, textAlign: 'center', color: DIM,
        opacity: kickIn, letterSpacing: dna?.labelSpacing ?? '0.16em',
        font: `600 ${kickPx}px/${leading(kicker, 1.2)} ${mono}`}}>{kicker}</div>

      {/* the carbon is painted FIRST so it is genuinely BEHIND the form it is under — the whole reveal is it
          coming out from there, and a copy that slid out OVER the original would be a different object */}
      <Sheet x={rightX} y={botY} head={to} carbon enter={carbonIn} />
      <Sheet x={leftX} y={topY} head={from} carbon={false} enter={sheetIn} />

      {note ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.1), right: Math.round(W * 0.1),
          top: zoneBot + Math.round(U * 0.012), textAlign: 'center', color: DIM, opacity: noteIn,
          font: `500 ${notePx}px/${leading(note, 1.4)} ${body}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default CarryOver;
