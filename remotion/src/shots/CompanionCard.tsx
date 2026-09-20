// SHOT · CompanionCard — something small is perched beside your work, and it is watching something else.
//
// A card sits next to a companion. The card reports what ANOTHER thing is doing right now, in two states
// and no more; the state turns once while you watch; then a cursor arrives, presses the card, and the card
// says where it takes you back to. That last line is the whole reason the form exists — a status display
// tells you; this one RETURNS you.
//
// WHY IT WAS BUILT RATHER THAN CAST. A film about a desktop companion derived its own form vocabulary from
// its subject — twelve forms, ten of which this library does not hold — and then recorded `shot_fit: fit`
// on all eight beats and built nothing. Two of those beats declared THIS form, "the status card beside the
// pet", which is the product itself; one drew three terminal windows and the other settled for an airport
// departure board. An independent reviewer put it plainly: the vocabulary was derived and then not acted
// on. `shot_fit` has three verdicts and `fit` is the only one that costs nothing, which is exactly why a
// library stops growing — see references/remotion-shot-authoring.md on building when the STRUCTURE differs.
//
// AND IT IS A FORM, NOT A PRODUCT. Nothing here draws a pet, a menu bar or anyone's app by default: a
// companion is an abstract sitting shape in the film's own tokens, the card is a card, and every word arrives
// through props. A beat about a build agent, a long export, a CI run or a kettle uses the same register — what
// it carries is "a small thing reporting on a larger thing, and the way back". A film whose subject HAS a real
// companion passes its picture (`src`, served from the film's own folder) and the shape becomes that picture;
// a faceless blob beside a product whose sprites are on disk was a reviewer's note against the hero beat.
//
// THE TURN AND THE PRESS BELONG TO THE SENTENCE. They were fixed at 0.40-0.56 and 0.66-0.78 of the clip, and
// on a delivered film the card went grey ~0.6s BEFORE the voice said 「绿色的工作中」: for a second the frame
// said 等待中 under a sentence saying 工作中. `turnAt` / `pressAt` place them; a board writes
// `{"cue": "灰色"}` and render_remotion puts the event on the moment the voice says that word.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, wrapLines, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 185; // ~6.2s

export const CompanionCard: React.FC<{
  /** what the card is reporting ON — the task, the run, the thing that is elsewhere */
  task?: string;
  /** the TWO states it can be in, in order: the one it starts in, the one it turns to. Two, because a
   *  display that can say three things is a dashboard and this one is a glance. */
  states?: [string, string];
  /** where pressing the card puts you. The line that separates this form from a status light. */
  returnsTo?: string;
  /** one line under the card, for the rule behind the return */
  note?: string;
  /** when the state STARTS to turn, as the register's t (0..1) — or `{"cue": "<words>"}` in a board. The start,
   *  not the middle: centred on the cue, the card began going grey before the voice had said the word. */
  turnAt?: number;
  /** when the cursor presses the card; after the turn — the work finished on its own, THEN you went back */
  pressAt?: number;
  /** the companion's own picture (a path in the film's folder); omitted = the abstract sitting shape */
  src?: string;
}> = ({
  task: TASK = 'the long run', states: STATES = ['working', 'waiting for you'],
  returnsTo: RETURNS = '', note: NOTE = '', turnAt: TURN_AT = 0.40, pressAt: PRESS_AT = 0.72, src: SRC = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  const task = String(TASK ?? '').trim();
  const pair = (Array.isArray(STATES) ? STATES : []).map((s) => String(s ?? '').trim()).filter(Boolean);
  if (Array.isArray(STATES) && STATES.length > 2) {
    throw new Error(`CompanionCard shows exactly TWO states and was given ${STATES.length}. A third was ignored ` +
      'without a word; a display that can say three things is a dashboard, not this glance.');
  }
  const turnAt = Number(TURN_AT), pressAt = Number(PRESS_AT);
  if (!(turnAt >= 0.2 && turnAt <= 0.8) || !(pressAt >= turnAt + 0.14 && pressAt <= 0.95)) {
    throw new Error(`CompanionCard: turnAt ${JSON.stringify(TURN_AT)} and pressAt ${JSON.stringify(PRESS_AT)} ` +
      'must satisfy 0.2 <= turnAt <= 0.8 and turnAt + 0.14 <= pressAt <= 0.95 — the state turns on its own, and ' +
      'only after it has turned does the press take you back. A board can write {"cue": "<words>"} for either.');
  }
  if (!task || pair.length < 2) {
    throw new Error(
      'CompanionCard needs a `task` and TWO `states`. The form is a glance that can say one of two things ' +
      'about something happening elsewhere; with one state there is nothing to turn, and the shot is a ' +
      'label beside a shape.');
  }
  const returns = String(RETURNS ?? '').trim();
  const note = String(NOTE ?? '').trim();

  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 50% 38%, #141a26, #080a0f 74%)';
  const FG = dna?.fg ?? '#eef2f8';
  const DIM = dna?.dim ?? '#7c8699';
  const ACC = dna?.accent ?? '#3dd6a4';
  const SURF = dna?.surface ?? '#131a26';
  const LINE = dna?.surfaceBorder ?? dna?.line ?? '#243149';
  const MONO = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';

  // THE THREE MOMENTS, and they do not overlap. The card settles, the state TURNS, the cursor presses. A
  // state that turned while the cursor was arriving would read as the click causing it, which is the
  // opposite of what the form says: the thing elsewhere finished on its own, and only then did you go back.
  const arrive = easeOutCubic(clamp01(seg(t, 0.06, 0.26)));
  const turn = easeInOutCubic(clamp01(seg(t, turnAt, turnAt + 0.12)));
  const press = easeOutCubic(clamp01(seg(t, pressAt - 0.06, pressAt + 0.06)));
  const back = easeOutCubic(clamp01(seg(t, pressAt + 0.02, Math.min(0.98, pressAt + 0.18))));
  const src = String(SRC ?? '').trim();

  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const cy = (zTop + zBot) / 2;
  const portrait = H > W * 1.1;

  const CARD_W = Math.round(W * (portrait ? 0.78 : 0.44));
  const PAD = Math.round(U * 0.028);
  // the companion's own size — a real picture gets the room a character needs to be recognised; the abstract
  // shape stays small, because it has nothing to recognise
  const PET = Math.round(U * (String(SRC ?? '').trim() ? (portrait ? 0.2 : 0.2) : (portrait ? 0.13 : 0.11)));

  const taskPx = fitTextPx(task, CARD_W - PAD * 2, Math.round(U * 0.036), {usable: 1});
  const statePx = Math.round(U * 0.024);
  const notePx = Math.round(U * 0.020);
  const backPx = Math.round(U * 0.022);

  const state = turn < 0.5 ? pair[0] : pair[1];
  const stateTone = turn < 0.5 ? ACC : DIM;
  // THE BREATH, which this file described and never computed. The comment under the companion said its lit
  // part "breathes while the card says working and goes still when it does not"; the shadow it names was a
  // constant. `register_energy` measured the consequence and did not know what it was looking at —
  // motion_p75 0.0001 against a 0.0037 floor, which is a still frame with four eased events in it: four
  // moments that do not overlap leave the shot motionless for most of its length, and a status card with no
  // pulse reads as a screenshot of a companion rather than one that is watching something.
  //
  // It is a MEANING, not decoration, which is why it stops: the breath is the thing elsewhere still running.
  // When the state turns to the second value the pulse flattens, so the shot goes still at the same instant
  // the work does — the viewer sees the stillness before reading the word.
  const breath = 0.5 - 0.5 * Math.cos(t * Math.PI * 2 * 3.2);
  const alive = breath * (1 - turn);
  // a CONTINUOUS alpha: stepped at a threshold the glow pops once per cycle, which reads as a flicker.
  const glowA = Math.round(0x22 + (0x3a - 0x22) * alive).toString(16).padStart(2, '0');
  // The pill swaps at the midpoint of the turn and the label crossfades through it, so the change is one
  // event rather than a colour animating independently of the word it belongs to.
  const swap = Math.abs(turn - 0.5) * 2;

  const cardH = Math.round(PAD * 2 + inkBlockH(taskPx) * wrapLines(task, taskPx, CARD_W - PAD * 2)
    + Math.round(U * 0.018) + inkBlockH(statePx));
  // In portrait the companion sits ABOVE the card: beside it, a 0.78W card left it starting at x ≈ -42px on
  // a 1080-wide frame (computed from this layout by the card reviewer, confirmed by render).
  const cardTop = Math.round(cy - cardH / 2 + (portrait ? PET * 0.45 : 0));
  const cardLeft = Math.round((W - CARD_W) / 2 + (portrait ? 0 : PET * 0.55));
  const petLeft = portrait ? Math.round(cardLeft + PAD) : Math.round(cardLeft - PET * 1.15);
  const petTop = portrait ? Math.round(cardTop - PET * 1.02) : Math.round(cardTop + cardH - PET * 0.92);

  // The cursor comes from below-right, the way a hand does, and stops ON the card rather than beside it.
  const curX = lerp(cardLeft + CARD_W * 1.28, cardLeft + CARD_W * 0.72, press);
  const curY = lerp(cardTop + cardH * 2.1, cardTop + cardH * 0.62, press);
  const pressed = press > 0.82 ? 1 : 0;

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* THE COMPANION — an abstract sitting shape in the film's own tokens, never a character. It is the
          thing that is HERE; everything the card says is about something that is not. */}
      <div style={{position: 'absolute', left: petLeft, top: petTop, width: PET, height: PET,
        opacity: arrive, transform: `translateY(${(1 - arrive) * U * 0.03}px)`}}>
        {src ? (
          // the subject's own companion — it breathes the same way the shape does, and goes still with it
          <Img src={staticFile(src)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%',
            objectFit: 'contain', transform: `scale(${1 + alive * 0.02})`, transformOrigin: '50% 100%',
            filter: `drop-shadow(0 0 ${Math.round(PET * (0.06 + 0.08 * alive))}px ${stateTone}${glowA})`}} />
        ) : null}
        {src ? null : <div style={{position: 'absolute', inset: 0, borderRadius: '46% 46% 38% 38% / 52% 52% 32% 32%',
          background: `linear-gradient(170deg, ${SURF}, ${dna?.bg ?? '#0b1018'})`,
          border: `1px solid ${LINE}`,
          // the one lit part: it breathes while the card says "working" and goes still when it does not
          boxShadow: `inset 0 ${Math.round(PET * 0.1)}px ${Math.round(PET * (0.22 + 0.16 * alive))}px `
            + `${stateTone}${glowA}`,
          transform: `scale(${1 + alive * 0.012})`, transformOrigin: '50% 100%'}} />}
        {src ? null : [0, 1].map((i) => (
          <div key={i} style={{position: 'absolute', top: PET * 0.34,
            left: PET * (i === 0 ? 0.30 : 0.58), width: Math.round(PET * 0.09),
            height: Math.round(PET * 0.09 * (turn < 0.5 ? 1 : 0.32)), borderRadius: '50%',
            background: stateTone, opacity: 0.9}} />
        ))}
      </div>

      {/* THE CARD — what something ELSE is doing, in two states and no more. */}
      <div style={{position: 'absolute', left: cardLeft, top: cardTop, width: CARD_W,
        padding: PAD, boxSizing: 'border-box', borderRadius: Math.round(U * 0.016),
        // THE PRESS RING IS NOT A STATE COLOUR. It was `ACC` — the same accent the card uses for "working" —
        // so on the frame after the state turns, the card rings GREEN while its dot is grey and its word
        // says 等待中. A beat that prints its own key (绿色＝工作中　灰色＝等待中) and then contradicts it
        // teaches the viewer that the colour means nothing. A press is a physical affordance, not a state:
        // it takes the neutral ink.
        background: SURF, border: `1px solid ${pressed ? FG : LINE}`,
        opacity: arrive,
        transform: `translateY(${(1 - arrive) * U * 0.02}px) scale(${1 - pressed * 0.012})`,
        boxShadow: pressed ? `0 0 ${Math.round(U * 0.05)}px ${FG}2b` : `0 ${Math.round(U * 0.012)}px ${Math.round(U * 0.03)}px #0007`}}>
        <div style={{color: FG, font: `700 ${taskPx}px/${leading(task, 1.25)} var(--f-display, Inter, system-ui, sans-serif)`}}>
          {task}
        </div>
        <div style={{marginTop: Math.round(U * 0.018), display: 'flex', alignItems: 'center',
          gap: Math.round(U * 0.012)}}>
          <span style={{width: Math.round(statePx * 0.5), height: Math.round(statePx * 0.5),
            borderRadius: '50%', background: stateTone,
            boxShadow: `0 0 ${Math.round(statePx * (0.45 + 0.5 * alive))}px ${stateTone}66`,
            opacity: 0.72 + 0.28 * alive}} />
          <span style={{color: stateTone, font: `600 ${statePx}px/${leading(state, 1.2)} ${MONO}`,
            opacity: 0.35 + 0.65 * swap}}>{state}</span>
        </div>
      </div>

      {/* WHERE IT TAKES YOU BACK TO — the line that makes this a way back and not a light. */}
      {/* a `note` without a `returnsTo` used to vanish with it: both are drawn when given */}
      {returns || note ? (
        <div style={{position: 'absolute', left: cardLeft, top: Math.round(cardTop + cardH + U * 0.05),
          width: CARD_W, opacity: back,
          transform: `translateY(${(1 - back) * U * 0.018}px)`}}>
          {returns ? (
          <div style={{color: readableOn(dna?.bg ?? '#0b0f17', ACC, FG),
            font: `600 ${backPx}px/${leading(returns, 1.3)} ${MONO}`, letterSpacing: '0.04em'}}>
            <span style={{opacity: 0.65, marginRight: Math.round(backPx * 0.5)}}>↩</span>{returns}
          </div>
          ) : null}
          {note ? (
            <div style={{marginTop: Math.round(U * 0.012), color: DIM,
              font: `500 ${notePx}px/${leading(note, 1.35)} var(--f-body, system-ui, sans-serif)`}}>{note}</div>
          ) : null}
        </div>
      ) : null}

      {/* the cursor, drawn last so it is over everything it touches */}
      {press > 0.01 ? (
        <div style={{position: 'absolute', left: Math.round(curX), top: Math.round(curY),
          width: 0, height: 0, opacity: Math.min(1, press * 2.2)}}>
          <svg width={Math.round(U * 0.034)} height={Math.round(U * 0.034)} viewBox="0 0 24 24"
            style={{filter: 'drop-shadow(0 2px 6px rgba(0,0,0,.55))'}}>
            <path d="M5 3l14 8-6 1.4L10.6 19z" fill={FG} stroke={dna?.bg ?? '#0b0f17'} strokeWidth="1.2"
              strokeLinejoin="round" />
          </svg>
          {pressed ? (
            <span style={{position: 'absolute', left: -Math.round(U * 0.02), top: -Math.round(U * 0.02),
              width: Math.round(U * 0.04), height: Math.round(U * 0.04), borderRadius: '50%',
              border: `2px solid ${FG}`, opacity: 0.45}} />
          ) : null}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default CompanionCard;
