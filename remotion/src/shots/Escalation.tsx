// SHOT · Escalation — a thing that kept happening, and happened MORE OFTEN. Marks land on a single time
// rule with the gaps closing between them, and the last one has nothing after it.
//
// WHAT IT ARGUES, AND WHY NOTHING ELSE IN THIS LIBRARY SAID IT. The library can draw a quantity going up
// (EdStat, TermCounter, ValueStagger), a tension that never resolves (TensionScale), a run that stops
// short (LastLeg) and a conclusion standing on what carries it (RestsOn). None of them can say the thing a
// rising line is usually MISTAKEN for: not "it got bigger" but "it got more FREQUENT". Those are different
// claims with different consequences — a number that doubles is a size problem, an interval that halves is
// a rate problem, and the second is what a deadline, a failure mode or a compounding cost actually is.
// A bar chart cannot say it, because a bar chart spends its x-axis on categories; this register spends the
// whole frame on ONE axis, time, and puts the argument in the spacing.
//
// SO THE PROOF IS THE SPACING, AND THE SPACING IS THE CLOCK. The marks are placed at the landings of
// `cadenceAt(n, accel)` (runtime/motion) — the SAME series `cadence` walks to decide when each one
// arrives, so a viewer watching the rhythm and a viewer reading the rule are given the same evidence and
// cannot be told two different things. Nothing here re-derives a position: a mark's x IS its landing time,
// read from the one definition rather than computed from the same parameters a second time. `accel` is the film's, not the register's, because how hard something escalated is a claim
// about the subject.
//
// WHY IT IS REUSABLE. The shape is "N events, closing up": incidents before an outage, releases shipping
// faster, revisions before a deadline, interest compounding, a symptom recurring. The topic arrives
// entirely through props — the marks' own labels, the rule's two ends, and the line the film wants to draw
// under it — so the form speaks any language and any subject.
//
// THE LAST MARK IS THE POINT, and it is drawn as the one with nothing after it: the rule continues past it
// into empty ruling. An escalation whose final mark sits at the end of the line reads as a thing that
// finished; the empty tail is what makes it read as a thing still going.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, cadence, cadenceAt, easeOutCubic, easeOutBack} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn} from '../runtime/dna';

export const DURATION = 165; // 5.5s

/** Seven marks is a rhythm; an eighth is a chart. Past this the gaps a viewer is asked to COMPARE are
 *  closer together than the marks themselves are wide, and the argument stops being visible. */
export const MAX_ESCALATION_MARKS = 7;

/** Where the LAST mark sits on the rule. The remainder is the tail this register's argument needs: an
 *  escalation whose final event sits at the end of the line reads as a thing that finished. */
const LAST_AT = 0.82;

const BG_D0 = '#0f1117', FG_D0 = '#eef1f6', DIM_D0 = '#79839a';
const ACC_D0 = '#d8743c', LINE_D0 = '#2a2f3d';

type Mark = {
  /** what happened — required, because an unlabelled tick is furniture, not an event */
  label?: string;
  /** when, in the film's own words ("3月", "v2.1", "第 4 周") — optional; the RULE is the time axis */
  when?: string;
};

// The demo set. It exists so the three measurement scripts can render this register at all — they sweep
// with default props, and a register that refuses without content records a permanent RENDER FAILED, which
// this repo has already learned is worse than a measurement (an empty plate measured as a register is a lie
// the sweep was telling). It reads as a PLACEHOLDER on purpose: a demo lifted from the film a register was
// written during ships that film's copy as every later film's default, and `shot_proof`'s demo-default
// check cannot tell a film that set the prop from one that forgot. The refusals below still bite on
// anything a film passes EXPLICITLY.
const DEMO: Mark[] = [
  {label: 'the first one', when: 'then'},
  {label: 'it happened again', when: 'later'},
  {label: 'and again', when: 'sooner'},
  {label: 'now it is constant', when: 'now'},
];

export const Escalation: React.FC<{
  kicker?: string;
  /** the two ends of the rule, in the film's own words — never a computed date */
  from?: string;
  to?: string;
  marks?: Mark[];
  /** how hard it closed up: 1 is a metronome, >1 accelerates. The film's claim, not this register's. */
  accel?: number;
  /** one line under the rule, in the film's voice */
  note?: string;
}> = ({kicker = '', from = '', to = '', marks = DEMO, accel = 1.8, note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const MS: Mark[] = Array.isArray(marks) ? marks : [];
  if (MS.length < 3) {
    throw new Error(
      'Escalation needs at least THREE `marks`: the claim is that the gaps between events are CLOSING, ' +
      'and two events make one gap, which cannot close against anything. Two events comparing before ' +
      'and after is a different register (VersusSplit / RackFocus).');
  }
  if (MS.length > MAX_ESCALATION_MARKS) {
    throw new Error(
      `Escalation holds at most ${MAX_ESCALATION_MARKS} marks, got ${MS.length}. Past that the gaps a ` +
      'viewer is asked to compare are narrower than the marks are wide — the argument is still true and ' +
      'no longer visible. Aggregate, or use a chart register.');
  }
  const bad = MS.findIndex((m) => !String(m?.label ?? '').trim());
  if (bad >= 0) {
    throw new Error(
      `Escalation was given a mark with no \`label\` (index ${bad}). A tick with nothing beside it is ` +
      'furniture: name what happened, or leave the mark out and let the rhythm be shorter.');
  }
  const A = Math.max(1, Math.min(5, Number(accel) || 1));

  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const body = 'var(--f-body, system-ui, sans-serif)';
  const U = Math.min(W, H);
  const hair = Math.max(1, Math.round(U * 0.0016));

  // ── geometry. Every measure is a fraction of the frame, so the shot reflows at 9:16 / 1:1 / 4:5. ────
  const x0 = W * 0.09, x1 = W * 0.91, span = x1 - x0;
  const LABEL_PX = Math.round(U * 0.026), WHEN_PX = Math.round(U * 0.017);
  const NOTE_PX = Math.round(U * 0.019);
  // The rule sits so that the TALLEST stack of label lines still clears the caption band. Reserved from
  // the type that goes in it, in the column each label actually wraps in — a Han glyph is a full em, so a
  // two-word Latin label and its Chinese translation do not wrap to the same number of lines.
  const colW = Math.max(U * 0.10, span / MS.length - U * 0.012);
  const lines = Math.max(1, ...MS.map((m) => wrapLines(String(m.label ?? ''), LABEL_PX, colW)));
  const stackH = lines * LABEL_PX * 1.25 + (MS.some((m) => m.when) ? WHEN_PX * 1.5 : 0) + U * 0.03;
  const noteH = note ? wrapLines(String(note), NOTE_PX, span) * NOTE_PX * 1.4 + U * 0.02 : 0;
  // The whole assembly is CENTRED in the content zone, not pinned to its floor. `Math.max(top, bottom)`
  // put the rule as low as both constraints allowed and left the upper two thirds of the frame empty —
  // measured on the first render, which is why a register gets rendered before it gets a card.
  const whenH = MS.some((m) => m.when) ? WHEN_PX * 1.6 : 0;
  const endsH = (from || to) ? WHEN_PX * 1.6 : 0;
  const blockH = stackH + whenH + endsH + noteH;
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H) - U * 0.02;
  const ruleY = Math.min(zoneBot - (blockH - stackH) - U * 0.02,
                         Math.max(zoneTop + stackH, zoneTop + (zoneBot - zoneTop - blockH) / 2 + stackH));

  // ── time. A mark's x IS its landing, so the rhythm and the rule cannot disagree. ─────────────────────
  const n = MS.length;
  // ONE DEFINITION, READ TWICE. `cadenceAt` returns where the landings are and `cadence` returns which
  // one has landed — both from the same series in runtime/motion, so the spacing a viewer reads and the
  // rhythm a viewer watches cannot be told two different things. An earlier build computed the positions
  // here from the same parameters, which is a second copy of a rule and how this repo's caption band came
  // to have four disagreeing definitions. `LAST_AT` scales the whole series so the tail exists.
  const at = React.useMemo(() => cadenceAt(n, A).map((v) => v * LAST_AT), [n, A]);

  const kickIn = clamp01(seg(t, 0.02, 0.12));
  const ruleIn = easeOutCubic(clamp01(seg(t, 0.04, 0.26)));
  const noteIn = clamp01(seg(t, 0.82, 0.92));
  const walked = cadence(t, n, A);                     // which mark has landed, in the film's rhythm

  const strong = readableOn(dna?.bg ?? BG_D0, FG, ACC);
  const soft = dimOn(dna?.bg ?? BG_D0, DIM);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: x0, top: CONTENT_TOP - U * 0.05, opacity: kickIn,
          font: `600 ${Math.round(U * 0.0145)}px/1.2 ${mono}`, color: ACC,
          letterSpacing: dna?.labelSpacing ?? '0.16em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}

      {/* THE RULE — one axis, time, drawn the full width. The tail past the last mark is deliberate: an
          escalation whose final event sits at the end of the line reads as a thing that finished. */}
      <div style={{position: 'absolute', left: x0, top: ruleY, width: span * ruleIn, height: hair,
        background: LINE}} />
      {from ? (
        <div style={{position: 'absolute', left: x0, top: ruleY + U * 0.016 + whenH, opacity: ruleIn,
          font: `500 ${WHEN_PX}px/${leading(from, 1.2)} ${mono}`, color: soft}}>{from}</div>
      ) : null}
      {to ? (
        <div style={{position: 'absolute', left: x0, top: ruleY + U * 0.016 + whenH, width: span,
          textAlign: 'right', opacity: ruleIn,
          font: `500 ${WHEN_PX}px/${leading(to, 1.2)} ${mono}`, color: soft}}>{to}</div>
      ) : null}

      {MS.map((m, i) => {
        const on = clamp01((walked * (n - 1) - i) * 3 + 1);      // this mark has landed
        if (on <= 0) return null;
        const pop = easeOutBack(clamp01(on));
        const x = x0 + span * at[i];
        const isLast = i === n - 1;
        const tick = U * (isLast ? 0.055 : 0.034);
        const lab = String(m.label ?? '');
        // The label WRAPS rather than shrinking: `lines` above reserved the rule's height for the tallest
        // stack, so shrinking here would contradict that reserve and leave the marks sitting low for no
        // reason. Short event names are what this register is for; a long one takes a second line.
        const px = LABEL_PX;
        return (
          <React.Fragment key={i}>
            {/* the mark itself — the last one is taller and takes the accent, because it is the point */}
            <div style={{position: 'absolute', left: x - hair, top: ruleY - tick * pop,
              width: hair * (isLast ? 3 : 2), height: tick * pop,
              background: isLast ? ACC : strong, opacity: on}} />
            {/* its label, stacked ABOVE the rule so the marks' spacing is never crowded by the words */}
            <div style={{position: 'absolute', left: Math.max(U * 0.02, Math.min(W - colW - U * 0.02, x - colW / 2)),
              top: ruleY - tick - U * 0.012 - lines * px * 1.25, width: colW, textAlign: 'center',
              opacity: on, transform: `translateY(${(1 - pop) * U * 0.012}px)`,
              font: `${isLast ? 700 : 500} ${px}px/${leading(lab, 1.25)} ${disp}`,
              color: isLast ? readableOn(dna?.bg ?? BG_D0, ACC, strong) : strong,
              textWrap: 'balance'}}>{lab}</div>
            {m.when ? (
              <div style={{position: 'absolute', left: Math.max(U * 0.02, Math.min(W - colW - U * 0.02, x - colW / 2)),
                top: ruleY + U * 0.016, width: colW, textAlign: 'center', opacity: on * 0.9,
                font: `500 ${WHEN_PX}px/${leading(String(m.when), 1.2)} ${mono}`,
                color: soft}}>{m.when}</div>
            ) : null}
          </React.Fragment>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left: x0, top: ruleY + U * 0.016 + whenH + endsH + U * 0.018,
          width: span, opacity: noteIn,
          font: `400 ${NOTE_PX}px/${leading(note, 1.4)} ${body}`, color: soft,
          textWrap: 'balance'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default Escalation;
