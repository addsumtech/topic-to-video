// SHOT · Shortening Hold — they kept coming, and there was less and less room between them. Each statement
// REPLACES the one before it and is held for less time than its predecessor; the spent ones stack above,
// packing tighter as they pile up, and the last one is never cut away.
//
// WHAT IT ARGUES, AND WHY `Escalation` IS NOT IT. Both argue acceleration, and they argue it by opposite
// means: `Escalation` DRAWS a rate — a persistent time rule with marks on it, which a viewer reads and
// analyses — while this one DOES the rate to the viewer, in the pacing, and the spent stack is only the
// receipt. Given the choice, a director picks between "understand how fast this got" and "feel it".
//
// But the deciding difference is not taste, it is what the film HAS. `Escalation` needs real time data:
// its `when` is the film's own word for a date and it refuses a computed one, because a fabricated
// timeline is a fabricated claim. A beat whose content is five support tickets, five things that broke, or
// five asks that landed in one week has NO timeline — nothing to put on a rule and nothing honest to write
// under a mark — and until now that beat had nowhere to go. This register asks for no dates at all; the
// only claim it makes about time is the one the film states in `accel`.
//
// WHY THE SPENT ONES STAY. Cut cleanly away, the settled frame is one statement on a ground — a title
// card, indistinguishable from a dozen registers, and the whole argument would live in frames nobody
// looks at (the contact sheet, `shot_still_qa` and the energy sweep all read stills). The stack keeps the
// evidence ON the settled frame: what came, and how much closer together it came.
//
// WHY THE HOLDS COME FROM `cadenceAt`. It is the same series `Escalation` places its marks with, and the
// same one `cadence` walks to time them. A second interval formula would be a second definition of the
// library's only rhythm — the failure runtime/motion's own header is about — so there is one, and every
// reader of a rhythm reads it.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, cadenceAt, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn} from '../runtime/dna';

// LONGER THAN THE HOUSE 5.5s, because an accelerating series is front-heavy by construction: the first
// hold is the baseline the rest are read against, so it is the longest one, and at four statements it is
// already half the shot. Squeezed into 5.5s the last hold of a six-statement run lands under MIN_HOLD_S
// and the register refuses its own declared capacity — a capacity nothing can use is not a capacity.
// (In a film this number is not used: the scene's own duration is, so a beat with more narration gets
// more room and the refusal is measured against what the shot actually has.)
export const DURATION = 210; // 7s

/** Two statements make ONE gap, which cannot shorten against anything; past six the last holds are
 *  shorter than the eye needs to read a line, so the argument lands as a stutter instead of a pace. */
export const MIN_HOLDS = 3, MAX_HOLDS = 6;

/** The shortest a hold may get, in SECONDS of screen time. Below this the statement is gone before it can
 *  be read, and the register stops arguing "faster" and starts arguing "nothing was legible" — which is a
 *  real feeling but not one a film chooses on purpose. */
export const MIN_HOLD_S = 0.34;

const BG_D0 = '#12100e', FG_D0 = '#f4efe7', DIM_D0 = '#8a8175';
const ACC_D0 = '#c8613a', LINE_D0 = '#2d2925';

// Placeholder copy, in the placeholder voice every register in this library keeps: the preview and all
// three measurement scripts render with defaults, and a prop left at '' does not draw — so a default left
// empty is a register measured as a fraction of itself. Generic on purpose, so no film's words become the
// next film's default.
const DEMO = ['one thing came up', 'then another', 'then two at once', 'and it did not stop'];

export const ShorteningHold: React.FC<{
  kicker?: string;
  /** the statements, in the order they landed — no dates, because this register never claims any */
  statements?: string[];
  /** how hard the room between them closed: 1 is a metronome, >1 accelerates. The FILM's claim. */
  accel?: number;
  /** one line under the stack, in the film's voice — what the pace MEANT */
  note?: string;
}> = ({kicker = 'ONE AFTER ANOTHER', statements = DEMO, accel = 1.9,
       note = 'each one left less room than the last'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, fps, durationInFrames} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const SS = (Array.isArray(statements) ? statements : []).map((s) => String(s ?? '').trim());
  if (SS.length < MIN_HOLDS) {
    throw new Error(
      `ShorteningHold needs at least ${MIN_HOLDS} statements, got ${SS.length}. The claim is that the room ` +
      'between them kept SHORTENING, and two statements make one gap, which cannot shorten against ' +
      'anything. Two things compared is VersusSplit; one thing said is a title register.');
  }
  if (SS.length > MAX_HOLDS) {
    throw new Error(
      `ShorteningHold holds at most ${MAX_HOLDS} statements, got ${SS.length}. Past that the last holds ` +
      'are shorter than a line takes to read and the pace reads as a stutter. Aggregate, or give the tail ' +
      'its own beat.');
  }
  const empty = SS.findIndex((s) => !s);
  if (empty >= 0) {
    throw new Error(
      `ShorteningHold was given an empty statement (index ${empty}). A hold with nothing in it is dead ` +
      'air the viewer reads as a mistake: say what landed, or make the run shorter.');
  }
  const A = Math.max(1, Math.min(5, Number(accel) || 1));
  const n = SS.length;

  // ── the rhythm. The holds are the INTERVALS of the one series, so the pace a viewer feels and the
  //    spacing they read in the stack are the same evidence and cannot disagree. ───────────────────────
  // `cadenceAt(k)` returns k LANDINGS, which is k-1 intervals; this register needs n HOLDS, so it asks
  // for n+1 landings and reads the intervals between them. Asking for n gave the last statement a hold of
  // exactly zero — the series ends at 1 and there is nothing after the final landing to hold for — and the
  // refusal below caught it on this register's own demo before anything was rendered.
  const series = React.useMemo(() => cadenceAt(n + 1, A), [n, A]);
  // `cadenceAt` is asked for one more landing than there are statements precisely so the last hold has
  // an end to run to; taking the first n of them is reading that series, not shortening anything.
  // @truncates: a list of NUMBERS this file computed, never the film's statements — no statement is cut
  const at = series.slice(0, n);                        // where each hold STARTS
  // ...AND IT REFUSES A PACE TOO FAST TO READ. `accel` is the film's claim, and a hard enough claim closes
  // the last hold past what anyone can read — at accel 5 with six statements the final hold is a handful
  // of frames. A statement gone before it is read still passes every pixel gate, which is this repo's own
  // definition of the worst outcome, so it says so instead.
  const holds = at.map((v, i) => (i + 1 < n ? at[i + 1] : 1) - v);
  const shortestS = Math.min(...holds) * (durationInFrames / Math.max(1, fps));
  if (shortestS < MIN_HOLD_S) {
    throw new Error(
      `ShorteningHold's last hold is ${shortestS.toFixed(2)}s, under the ${MIN_HOLD_S}s a statement needs ` +
      `to be read. The pace is closing harder than the shot is long — lower \`accel\` (${A}), use fewer ` +
      'statements, or give the beat more time.');
  }

  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const BG = dna?.bg ?? BG_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const U = Math.min(W, H);
  const strong = readableOn(BG, FG, FG_D0);
  const soft = dimOn(BG, DIM, 3);
  const hair = Math.max(1, Math.round(U * 0.0016));

  // ── geometry. Fractions of the frame, so the shot reflows at 9:16 / 1:1 / 4:5. ──────────────────────
  const x0 = W * 0.09, colW = W * 0.82;
  const LIVE_PX = Math.round(U * 0.062), SPENT_PX = Math.round(U * 0.024);
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);

  // WHICH ONE IS LIVE, and how far into its own hold. `cadenceAt` gives the landings; the live index is
  // the last one that has landed, which is the same walk `cadence` does — read here directly because the
  // register needs the PHASE inside the hold as well as the index, and deriving the index a second way
  // would be the second definition this file's header refuses.
  let live = 0;
  for (let i = 1; i < n; i++) if (t >= at[i] - 1e-9) live = i;
  const inHold = clamp01((t - at[live]) / Math.max(1e-6, holds[live]));

  // The spent stack PACKS as it grows — the line gap closes on the same series the holds do, so the
  // picture of the pace and the pace itself are one measurement. Reserved from the type that goes in it.
  const spentLead = 1.9 - 0.7 * (live / Math.max(1, n - 1));
  const spentLines = SS.slice(0, live).map((s) => wrapLines(s, SPENT_PX, colW));
  const spentH = spentLines.reduce((a, l) => a + l * SPENT_PX * spentLead, 0);
  const liveLines = wrapLines(SS[live], LIVE_PX, colW);
  const liveH = liveLines * LIVE_PX * 1.14;
  const noteH = note ? wrapLines(String(note), NOTE_PX, colW) * NOTE_PX * 1.4 + U * 0.02 : 0;
  const blockH = spentH + liveH + noteH + U * 0.04;
  const top = Math.max(zoneTop, zoneTop + (zoneBot - zoneTop - blockH) / 2);

  const kickIn = clamp01(seg(t, 0.02, 0.1));
  const noteIn = clamp01(seg(t, 0.72, 0.84));
  // A CUT, NOT A DISSOLVE. The replacement is the argument, so the live statement arrives on one frame and
  // only SETTLES after — an eased fade-in would spend the first third of every hold being half-legible,
  // and the shortest holds would never be fully on screen at all.
  const settle = easeOutExpo(clamp01(inHold * 6));

  return (
    <AbsoluteFill style={{background: BG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: x0, top: zoneTop - U * 0.05, opacity: kickIn,
          font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: '0.16em', color: ACC}}>{kicker}</div>
      ) : null}

      {/* the spent ones, packed tighter the more of them there are */}
      {SS.slice(0, live).map((s, i) => {
        const above = SS.slice(0, i).reduce((a, _, k) => a + spentLines[k] * SPENT_PX * spentLead, 0);
        return (
          <div key={i} style={{position: 'absolute', left: x0, top: top + above, width: colW,
            font: `500 ${SPENT_PX}px/${leading(s, 1.35)} ${disp}`, color: soft, opacity: 0.85}}>{s}</div>
        );
      })}

      {/* the live one */}
      <div style={{position: 'absolute', left: x0, top: top + spentH + U * 0.012, width: colW,
        font: `700 ${LIVE_PX}px/${leading(SS[live], 1.14)} ${disp}`,
        color: live === n - 1 ? readableOn(BG, ACC, strong) : strong,
        transform: `translateY(${(1 - settle) * U * 0.012}px)`, opacity: 0.25 + 0.75 * settle,
        textWrap: 'balance'}}>{SS[live]}</div>

      {/* The rule under the live line is THIS statement's own hold, drawn against the first one's — so a
          viewer sees the same number they are being given: at the end it is a stub because the hold is a
          stub. An earlier build sized it `0.18 + 0.82 * (1 - live/(n-1))`, a formula invented here that
          merely trended the right way, which is a second definition of the pace disagreeing with the
          pace. It is now the ratio itself, and it cannot drift from what the shot actually does. */}
      <div style={{position: 'absolute', left: x0, top: top + spentH + U * 0.012 + liveH + U * 0.014,
        width: colW * (holds[live] / holds[0]) * easeOutCubic(clamp01(t / 0.12)),
        height: hair * 2, background: live === n - 1 ? ACC : LINE}} />

      {note ? (
        <div style={{position: 'absolute', left: x0, width: colW,
          top: top + spentH + U * 0.012 + liveH + U * 0.05, opacity: noteIn,
          font: `400 ${NOTE_PX}px/${leading(String(note), 1.4)} ${mono}`, color: soft}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default ShorteningHold;
