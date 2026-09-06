// SHOT · AcceptanceStamp — two necessary conditions, and the result only exists when BOTH land: a claim of
// the form "A × B = C, and neither half alone is enough".
//
// WHY THE FORM IS AN ACCEPTANCE STAMP AND NOT A CONVEYOR. The library already had a way to draw "steps
// producing a thing" — an isometric belt carrying blocks past workstations — and a film about an office AI
// agent reached for it twice. A viewer's note was that a factory line is the wrong world for this product,
// and that is right in a way worth writing down: a belt says the output is MANUFACTURED, one stage after
// another, and each stage improves what the last one made. This argument is not sequential at all. It says
// two things must BOTH hold, in no order, and that the result does not exist in a partial form — with one
// condition missing you do not get a rougher deliverable, you get no deliverable. The office object for
// exactly that is an acceptance stamp: the conditions are ticked independently, and the stamp either lands
// or it does not.
//
// So the two conditions arrive from opposite sides and tick on their own; the result sits between them
// drawn as an EMPTY outline the whole time they are arriving; and only when the second tick lands does it
// fill and take the stamp. Remove either condition and the frame still tells the truth — the outline never
// fills. That is the argument, drawn.
//
// Every word comes from props. The `×` between the conditions is the FORM's own operator, declared below.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutBack, lerp} from '../runtime/motion';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s

// The conjunction operator belongs to the FORM the way an axis belongs to a graph — it is not copy about a
// topic, and onscreen_text_qa needs to be able to tell those apart.
export const INTRINSIC_TEXT = ['×'];

const BG_D0 = '#0f1117', FG_D0 = '#eef2f8', ACC_D0 = '#6b62e8', DIM_D0 = '#8b93a8', SURF_D0 = '#191c26';

type Props = {
  /** the two things that must BOTH hold. Exactly two — a third would make it a list, not a conjunction. */
  conditions?: [string, string] | string[];
  /** what exists only when both hold */
  result?: string;
  /** the word on the stamp */
  stamp?: string;
  /** one line under the result, for the consequence */
  note?: string;
};

export const AcceptanceStamp: React.FC<Props> = ({
  conditions = ['Condition one', 'Condition two'],
  result = 'The deliverable',
  stamp = 'ACCEPTED',
  note = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const LINE = dna?.line ?? DIM;
  const RAD = dna?.radius ?? 16;
  const U = Math.min(W, H);                       // every size is a fraction of the SHORT side, so the shot
                                                  // reflows at 9:16 instead of assuming a landscape frame
  const top = CONTENT_TOP, bottom = H - captionBand(W, H);
  const midY = (top + bottom) / 2;

  // EXACTLY TWO, LOUDLY. The whole register is a CONJUNCTION: two things hold, in no order, and the result
  // does not exist in a partial form. Given one it drew an empty second card; given three it dropped the
  // third without a word — both are frames that look composed and say something false, which is the failure
  // this library's evidence guard exists to end (runtime/evidence.ts). A beat with three conditions is a
  // list, and wants a list register.
  if (!Array.isArray(conditions) || conditions.filter((x) => String(x ?? '').trim()).length !== 2) {
    throw new Error(
      `AcceptanceStamp needs exactly TWO non-empty \`conditions\`, got ` +
      `${Array.isArray(conditions) ? conditions.length : typeof conditions}. This register draws a ` +
      `conjunction — A and B, in no order, and the result does not exist unless both hold. One condition ` +
      `is not a conjunction and three is a list; either wants a different register.`);
  }
  const a = String(conditions[0] ?? '');
  const b = String(conditions[1] ?? '');
  // the two conditions arrive, then tick, then the result fills and takes the stamp
  const inA = easeOutCubic(clamp01(seg(t, 0.06, 0.26)));
  const inB = easeOutCubic(clamp01(seg(t, 0.16, 0.36)));
  const tickA = clamp01(seg(t, 0.30, 0.40));
  const tickB = clamp01(seg(t, 0.42, 0.52));
  const both = Math.min(tickA, tickB);            // the result cannot lead the SECOND tick
  const fill = easeOutCubic(clamp01(seg(t, 0.54, 0.68)));
  const land = easeOutBack(clamp01(seg(t, 0.66, 0.80)));
  const noteIn = clamp01(seg(t, 0.80, 0.92));

  const cardW = Math.round(U * 0.385), cardH = Math.round(U * 0.165);
  const gap = Math.round(U * 0.075);
  const condY = Math.round(midY - U * 0.245);
  const resW = Math.round(U * 0.56), resH = Math.round(U * 0.235);
  const resY = Math.round(midY - U * 0.035);
  const labelPx = (s: string) => fitTextPx(s, cardW - Math.round(U * 0.055), Math.round(U * 0.050),
    {usable: 1.15});

  const Condition: React.FC<{text: string; enter: number; tick: number; dx: number}> = ({
    text, enter, tick, dx}) => {
    const px = labelPx(text);
    return (
      <div style={{position: 'absolute', top: condY, left: W / 2 + dx - cardW / 2, width: cardW, height: cardH,
        borderRadius: RAD, background: SURF, border: `1px solid ${LINE}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: `0 ${Math.round(U * 0.03)}px`,
        boxSizing: 'border-box', textAlign: 'center',
        opacity: clamp01(enter), transform: `translateX(${lerp(dx > 0 ? U * 0.16 : -U * 0.16, 0, enter)}px)`}}>
        <div style={{color: FG, font: `600 ${px}px/${leading(text, 1.25)} var(--f-body, system-ui, sans-serif)`}}>
          {text}
        </div>
        {/* the tick: drawn, not a glyph, so it needs no font and cannot become tofu */}
        <svg width={U * 0.06} height={U * 0.06} viewBox="0 0 40 40"
          style={{position: 'absolute', right: -U * 0.022, top: -U * 0.022, opacity: clamp01(tick * 2)}}>
          <circle cx="20" cy="20" r="18" fill={ACC} />
          <path d="M11 20.5 L17.5 27 L29 14" fill="none" stroke={dna?.onAccent ?? '#fff'} strokeWidth="4"
            strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray="30" strokeDashoffset={30 * (1 - clamp01(tick))} />
        </svg>
      </div>
    );
  };

  const resPx = fitTextPx(result, resW - Math.round(U * 0.08), Math.round(U * 0.072), {usable: 1.0});
  return (
    <AbsoluteFill style={{background: BG}}>
      <Condition text={a} enter={inA} tick={tickA} dx={-(cardW / 2 + gap / 2)} />
      <Condition text={b} enter={inB} tick={tickB} dx={+(cardW / 2 + gap / 2)} />

      {/* the conjunction: the claim is AND, not THEN */}
      <div style={{position: 'absolute', top: condY + cardH / 2 - U * 0.03, left: 0, right: 0,
        textAlign: 'center', color: DIM, opacity: clamp01(Math.min(inA, inB)),
        font: `300 ${Math.round(U * 0.06)}px/1 var(--f-display, system-ui, sans-serif)`}}>×</div>

      {/* the result: an EMPTY outline until both ticks land — with one condition missing it never fills */}
      <div style={{position: 'absolute', top: resY, left: W / 2 - resW / 2, width: resW, height: resH,
        borderRadius: RAD, boxSizing: 'border-box',
        border: `${Math.max(2, Math.round(U * 0.003))}px ${fill > 0.5 ? 'solid' : 'dashed'} ${fill > 0.5 ? ACC : LINE}`,
        background: fill > 0 ? SURF : 'transparent',
        boxShadow: fill > 0.4 ? `0 ${Math.round(U * 0.014)}px ${Math.round(U * 0.05)}px ${ACC}22` : 'none',
        opacity: 0.35 + 0.65 * clamp01(both + fill),
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: `0 ${Math.round(U * 0.04)}px`, textAlign: 'center'}}>
        <div style={{color: fill > 0.2 ? FG : DIM,
          font: `700 ${resPx}px/${leading(result, 1.2)} var(--f-display, system-ui, sans-serif)`}}>{result}</div>
      </div>

      {/* the stamp lands only after the fill */}
      {/* clear of the result's own type: a stamp lands ACROSS the card's corner, not over its words */}
      <div style={{position: 'absolute', top: resY + resH * 0.66, left: W / 2 + resW * 0.28,
        transform: `rotate(-13deg) scale(${lerp(1.5, 1, land)})`, opacity: clamp01(land * 1.2),
        border: `${Math.max(3, Math.round(U * 0.005))}px solid ${ACC}`, borderRadius: Math.round(U * 0.012),
        padding: `${Math.round(U * 0.012)}px ${Math.round(U * 0.026)}px`, color: ACC,
        font: `800 ${fitTextPx(stamp, U * 0.30, Math.round(U * 0.048), {usable: 1.0})}px/${leading(stamp, 1.1)} var(--f-display, system-ui, sans-serif)`,
        letterSpacing: '0.04em'}}>{stamp}</div>

      {note ? (
        <div style={{position: 'absolute', top: resY + resH + Math.round(U * 0.05), left: 0, right: 0,
          textAlign: 'center', color: DIM, opacity: clamp01(noteIn),
          padding: `0 ${Math.round(W * 0.12)}px`,
          font: `500 ${Math.round(U * 0.031)}px/${leading(note, 1.45)} var(--f-body, system-ui, sans-serif)`}}>
          {note}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default AcceptanceStamp;
