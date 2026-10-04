// SHOT · BreaksWhenAsked — a statement that survives every read-only check and fails the one that talks
// back: readers pass over it leaving it whole, then a question lands and it breaks at the clause nothing
// supports.
//
// THE ARGUMENT SHAPE. Not "this one matters" (FocalIsolation, RackFocus — those point at something already
// visible), and not "one moment in a run" (HeldInstant — that claim needs a process to point inside). This
// one is about a MEDIUM: every check in the chain reads the same still surface, so a failure that only
// exists under interrogation is invisible to all of them at once, however many there are. Adding readers
// makes it worse, not better, and the frame has to show that — which is why the readers sweep and leave
// the line WHOLE, and why the fracture is caused by the question and by nothing else.
//
// Reusable: a claim on a page that dies in the interview, a spec that passes review and fails in
// production, a policy that reads fine and collapses at the counter, a metric that survives every
// dashboard and dies in one user session. The statement arrives as PARTS so the film says where it gives
// way; this register never picks the weak clause itself.
//
// REFUSALS. Fewer than two parts (nothing can break away from nothing); no `breaks` index once a film
// passes its own parts (which clause fails IS the claim); no readers; no question. Each throws.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo, cadenceAt} from '../runtime/motion';
import {captionBand, CONTENT_TOP, inkBlockH, fitBlockPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix, readableOn, dimOn} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 210; // 7s — the readers are quick; the break has to be allowed to land and be read

const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', ACC_D0 = '#e0563f', DIM_D0 = '#7b8a9c', LINE_D0 = '#22303f';
const SURF_D0 = '#121a24';

export const MAX_BREAK_PARTS = 4;
export const MAX_BREAK_READERS = 4;

const DEMO_PARTS = ['the part that is supported', 'the part that is not'];
const DEMO_READERS = ['the first reader', 'the second reader', 'the third reader'];

export const BreaksWhenAsked: React.FC<{
  kicker?: string;
  /** the statement, in the pieces it would come apart into — 2 to MAX_BREAK_PARTS */
  parts?: string[];
  /** which piece gives way, an index into `parts` — REQUIRED once a film supplies its own parts */
  breaks?: number;
  /** the checks that only READ it; each passes over the line and leaves it whole */
  readers?: string[];
  /** the mark a reader leaves when it finds nothing wrong */
  passLabel?: string;
  /** the one thing that talks back — the question, in the film's words */
  question?: string;
  /** what is left where the piece was */
  breakLabel?: string;
  /** one line under the form, in the film's voice */
  note?: string;
}> = ({
  kicker = '',
  parts: PARTS_IN = DEMO_PARTS,
  breaks: BREAKS_IN,
  readers: READERS_IN = DEMO_READERS,
  passLabel = 'nothing found',
  question = 'and which part of it was yours?',
  breakLabel = 'nothing under it',
  note = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();

  const parts = (Array.isArray(PARTS_IN) ? PARTS_IN : []).map((p) => String(p ?? '')).filter((p) => p.trim());
  const readers = (Array.isArray(READERS_IN) ? READERS_IN : []).map((r) => String(r ?? '')).filter((r) => r.trim());
  if (parts.length < 2) {
    throw new Error(
      'BreaksWhenAsked needs at least two `parts`. The form is one statement coming apart at a named seam; ' +
      'with one piece there is nothing for the question to break away.');
  }
  if (parts.length > MAX_BREAK_PARTS) {
    throw new Error(
      `BreaksWhenAsked holds at most ${MAX_BREAK_PARTS} parts, got ${parts.length}. Past that the line is ` +
      'set too small for the break to be legible as a break — shorten the statement.');
  }
  const givenParts = PARTS_IN !== DEMO_PARTS;
  const breaks = typeof BREAKS_IN === 'number' && Number.isInteger(BREAKS_IN) ? BREAKS_IN : null;
  if (givenParts && breaks === null) {
    throw new Error(
      'BreaksWhenAsked needs `breaks` — the index of the piece that gives way — once a film passes its own ' +
      '`parts`. WHICH clause fails is the claim; a register that picked it would have made the argument up.');
  }
  const brk = breaks === null ? parts.length - 1 : breaks;
  if (brk < 0 || brk >= parts.length) {
    throw new Error(
      `BreaksWhenAsked: \`breaks\` is ${brk}, outside the ${parts.length} parts it was given.`);
  }
  if (!readers.length) {
    throw new Error(
      'BreaksWhenAsked needs at least one entry in `readers`. The claim is that every READ-ONLY check ' +
      'passes; with none, the frame shows a line breaking for no stated reason.');
  }
  if (readers.length > MAX_BREAK_READERS) {
    throw new Error(
      `BreaksWhenAsked holds at most ${MAX_BREAK_READERS} readers, got ${readers.length}.`);
  }
  if (!String(question ?? '').trim()) {
    throw new Error(
      'BreaksWhenAsked needs a `question`. The break has one cause and this register draws no other; an ' +
      'unnamed cause makes the fracture decoration.');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const ACC2 = dna?.accent2 ?? ACC_D0;
  const LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const disp = dna?.fontDisplay ?? 'var(--f-display, Inter, system-ui, sans-serif)';
  const body = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const spacing = dna?.labelSpacing ?? '0.12em';
  const upper = dna?.uppercaseLabels ? 'uppercase' : 'none';

  // The statement is PRINTED — it sits on a sheet of the film's own stock, because the claim is about what
  // a page can and cannot carry. Ink measured against the sheet, never assumed.
  const SHEET = mix(SURF, GROUND, 0.25);
  const INK = readableOn(SHEET, FG, GROUND, '#ffffff', '#0a0d14');
  const DIM_ON_SHEET = dimOn(SHEET, INK, 4.5);
  const DIM_ON_GROUND = dimOn(GROUND, FG, 4.5);

  const U = Math.min(W, H);
  const top = CONTENT_TOP;
  const bottom = H - captionBand(W, H);

  const kickPx = Math.round(U * 0.023);
  const tagPx = Math.round(U * 0.020);
  const notePx = Math.round(U * 0.027);
  const qPx = Math.round(U * 0.032);

  const kickH = kicker ? inkBlockH(kickPx) + Math.round(U * 0.024) : 0;
  const noteH = note ? inkBlockH(notePx, 2) + Math.round(U * 0.02) : 0;
  const zoneTop = top + kickH;
  const zoneBot = bottom - noteH;

  // ── the clock ────────────────────────────────────────────────────────────────────────────────────────
  // The readers go first and go FAST (a page is read quickly and that is the point). The question arrives
  // afterwards, alone, and only then does the line give way — so nothing on the frame can be read as the
  // readers having caused it.
  const sheetIn = easeOutCubic(clamp01(seg(t, 0.03, 0.16)));
  const READ_FROM = 0.06, READ_TO = 0.44, READ_SWEEP = 0.22;
  const sweepAt = cadenceAt(readers.length, 1);       // where each reader's sweep starts, in its own window
  const Q_AT = 0.68, BREAK_AT = 0.72;
  const qIn = easeOutCubic(clamp01(seg(t, Q_AT, Q_AT + 0.10)));
  const breakT = easeOutExpo(clamp01(seg(t, BREAK_AT, BREAK_AT + 0.28)));
  const tagIn = easeOutCubic(clamp01(seg(t, BREAK_AT + 0.14, BREAK_AT + 0.24)));

  // ── the sheet ────────────────────────────────────────────────────────────────────────────────────────
  const sheetW = Math.round(Math.min(W * 0.86, U * 1.5));
  const sheetX = Math.round((W - sheetW) / 2);
  const readerRowH = inkBlockH(tagPx) + Math.round(U * 0.011);
  const readersH = readerRowH * readers.length + Math.round(U * 0.02);
  const qH = inkBlockH(qPx, 1) + inkBlockH(tagPx) + Math.round(U * 0.028);
  const sheetTop = zoneTop;
  const sheetH = Math.max(U * 0.22, zoneBot - zoneTop - readersH - qH);

  const padX = Math.round(sheetW * 0.07);
  const padY = Math.round(sheetH * 0.14);
  const lineW = sheetW - padX * 2;

  // One statement, set as one block, sized to the sheet it is printed on — never a bare px literal.
  const whole = parts.join('');
  const statePx = fitBlockPx(whole, lineW, sheetH - padY * 2, Math.round(U * 0.052),
    {leading: leading(whole, 1.34)});

  // The break: the marked piece SHEARS away from the seam — about one line down, tilted, going pale, while
  // every other piece holds exactly where it was printed. The fall is capped by the room left on the page
  // (the sheet clips, as a page does), so a longer statement or a shorter sheet never drops the clause off
  // its own stock and out of the frame — which is how this shot first rendered a half-cut line.
  const maxDrop = Math.max(0, (sheetH - padY * 2) / 2 - statePx * 0.35);
  const drop = breakT * Math.min(statePx * 1.05, maxDrop);
  const tilt = breakT * 4.2;

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {kicker ? (
        <div style={{position: 'absolute', top, left: sheetX, width: sheetW,
          color: DIM_ON_GROUND, opacity: sheetIn,
          font: `600 ${kickPx}px/1.3 ${body}`, letterSpacing: spacing, textTransform: upper as any}}>
          {kicker}
        </div>
      ) : null}

      {/* THE PAGE — the surface all the read-only checks share */}
      <div style={{position: 'absolute', left: sheetX, top: sheetTop, width: sheetW, height: sheetH,
        background: SHEET, border: `${Math.max(1, dna?.borderWidth ?? 1)}px solid ${LINE}`,
        borderRadius: dna?.radius ?? 2, opacity: sheetIn,
        transform: glide(`translateY(${(1 - sheetIn) * U * 0.02}px)`, sheetIn !== 1), overflow: 'hidden'}}>

        {/* the statement, in its pieces, laid out as one continuous printed line */}
        <div style={{position: 'absolute', left: padX, top: padY, width: lineW,
          height: sheetH - padY * 2, display: 'flex', alignItems: 'center', flexWrap: 'wrap',
          alignContent: 'center'}}>
          {parts.map((p, i) => {
            const isBrk = i === brk;
            const type = {font: `600 ${statePx}px/${leading(whole, 1.34)} ${disp}`} as const;
            if (!isBrk) {
              return (
                <span key={i} style={{display: 'inline-block', maxWidth: '100%', color: INK, ...type}}>{p}</span>
              );
            }
            // The broken piece keeps its ORIGINAL box (a transform changes no layout), so the ragged edge
            // drawn at that box's foot marks exactly where the clause used to sit — the seam, not a rule
            // struck through the part that held.
            return (
              <span key={i} style={{position: 'relative', display: 'inline-block', maxWidth: '100%'}}>
                <span style={{display: 'inline-block', maxWidth: '100%',
                  color: mix(INK, SHEET, 0.55 * breakT),
                  transform: glide(`translateY(${drop}px) rotate(${tilt}deg)`, breakT > 0 && breakT < 1), transformOrigin: 'left top',
                  borderBottom: breakT > 0.02
                    ? `${Math.max(2, Math.round(U * 0.004))}px solid ${ACC}` : 'none',
                  ...type}}>{p}</span>
                {breakT > 0.02 ? (
                  <span style={{position: 'absolute', left: 0, right: 0, bottom: 0,
                    height: Math.max(2, Math.round(U * 0.003)),
                    background: `repeating-linear-gradient(90deg, ${ACC} 0 ${Math.round(U * 0.012)}px, ` +
                      `transparent ${Math.round(U * 0.012)}px ${Math.round(U * 0.02)}px)`,
                    opacity: 0.9 * breakT}} />
                ) : null}
              </span>
            );
          })}
        </div>

        {/* THE READERS — each passes over the WHOLE page and leaves it whole. A reading band, not a
            hairline: what a reader covers is an area, and an area is also what a viewer sees move. */}
        {readers.map((r, i) => {
          const a = READ_FROM + (READ_TO - READ_FROM) * sweepAt[i];
          const s = clamp01(seg(t, a, a + READ_SWEEP));
          const gone = clamp01(seg(t, a + READ_SWEEP, a + READ_SWEEP + 0.05));
          if (s <= 0 || gone >= 1) return null;
          const bandW = Math.round(sheetW * 0.34);
          return (
            <div key={i} style={{position: 'absolute', top: 0, bottom: 0,
              left: Math.round(-bandW + (sheetW + bandW) * easeOutCubic(s)), width: bandW,
              background: `linear-gradient(90deg, transparent, ${ACC2}2e 62%, ${ACC2} 99%)`,
              opacity: (1 - gone) * 0.9}} />
          );
        })}
      </div>

      {/* the readers' verdicts, stacked under the page — every one of them found nothing */}
      <div style={{position: 'absolute', left: sheetX, top: sheetTop + sheetH + Math.round(U * 0.018),
        width: sheetW}}>
        {readers.map((r, i) => {
          const a = READ_FROM + (READ_TO - READ_FROM) * sweepAt[i];
          const v = easeOutCubic(clamp01(seg(t, a + READ_SWEEP * 0.8, a + READ_SWEEP + 0.06)));
          return (
            <div key={i} style={{display: 'flex', justifyContent: 'space-between', gap: Math.round(U * 0.02),
              height: readerRowH, alignItems: 'baseline', opacity: v,
              borderBottom: `1px solid ${LINE}`}}>
              <span style={{color: FG, font: `500 ${tagPx}px/1.35 ${body}`}}>{r}</span>
              <span style={{color: DIM_ON_GROUND, font: `600 ${tagPx}px/1.35 ${body}`,
                letterSpacing: spacing, textTransform: upper as any, whiteSpace: 'nowrap'}}>{passLabel}</span>
            </div>
          );
        })}
      </div>

      {/* THE ONE THAT TALKS BACK — it arrives from under the page, after every reader has finished */}
      <div style={{position: 'absolute', left: sheetX, width: sheetW,
        top: sheetTop + sheetH + readersH, opacity: qIn,
        transform: glide(`translateY(${(1 - qIn) * U * 0.03}px)`, qIn !== 1)}}>
        <div style={{color: ACC, font: `700 ${qPx}px/${leading(question, 1.3)} ${disp}`}}>{question}</div>
        <div style={{color: DIM_ON_GROUND, opacity: tagIn, marginTop: Math.round(U * 0.010),
          font: `600 ${tagPx}px/1.3 ${body}`, letterSpacing: spacing, textTransform: upper as any}}>
          {breakLabel}
        </div>
      </div>

      {note ? (
        <div style={{position: 'absolute', left: sheetX, width: sheetW, top: zoneBot + Math.round(U * 0.012),
          color: DIM_ON_GROUND, opacity: tagIn,
          font: `400 ${notePx}px/${leading(note, 1.4)} ${body}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default BreaksWhenAsked;
