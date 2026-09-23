// SHOT · Held Instant — a run that went past, and the one moment inside it that decided the outcome. A
// playhead crosses the whole track in ONE uncut move, and time is remapped so it crawls through the step
// the film marks and covers everything else briskly. The marked step's detail is legible only while the
// playhead is inside it, because that is the only moment there was time to read it.
//
// WHAT IT ARGUES, AND WHY THE LIBRARY COULD NOT SAY IT. `FocalIsolation` blurs everything but the key
// phrase and `RackFocus` turns from one reading to another: both say "this one matters", and both say it
// in SPACE, about things that are simply present. This register's claim needs a RUN — something that was
// already happening and kept happening — and it points inside that run at an instant. "Most of this went
// past without anyone watching; this is where it turned" is a different sentence from "look at this one",
// and no amount of blur can say it, because blur cannot say WHEN.
//
// WHY THE RAMP AND NOT A PAUSE. Stopping the playhead would be a cut in disguise: two static shots with a
// hold between them, and the viewer would read the marked step as a separate frame rather than as part of
// the same continuous thing. `speedRamp` (runtime/motion) remaps the shot's own normalised time — the
// motion never stops and never jumps, it only gets cheap and then expensive — so the run stays one run.
// `factor` is the number the film can state: 4 means that stretch plays at a quarter speed.
//
// WHY THE SLOW PART IS WHERE THE READING IS. The detail under the marked step is set at a size that needs
// real seconds to read. Placed in a shot with an even clock it would be unreadable or would force the
// whole shot to be slow; here the shot spends its time where the reading is, which is the entire point of
// a ramp and the reason it is a rhetorical device rather than a motion preset.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, speedRamp, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn} from '../runtime/dna';
import {drawOn} from '../runtime/draw';

export const DURATION = 195; // 6.5s

/** Two steps is a before/after (`VersusSplit`); past seven the steps are narrower than their own labels
 *  and the run stops being a run a viewer can follow. */
export const MIN_STEPS = 3, MAX_STEPS = 7;

/** The shortest the marked step may be given, in SECONDS of real screen time. The whole register exists to
 *  buy reading time for one moment; buying less than this buys nothing and the ramp is decoration. */
export const MIN_DWELL_S = 1.2;

const BG_D0 = '#0e1013', FG_D0 = '#eaeef4', DIM_D0 = '#78818f';
const ACC_D0 = '#4f9cf0', LINE_D0 = '#262c35';

// Placeholder copy in the library's placeholder voice: every measurement script renders with defaults, and
// a prop left at '' does not draw at all — so an empty default is a register measured as a fraction of
// itself. Generic on purpose, so no film's words become the next film's default.
const DEMO = ['it started', 'it kept going', 'this is where it turned', 'and then it finished'];
const DEMO_HELD = 2;

export const HeldInstant: React.FC<{
  kicker?: string;
  /** the run, in order — the whole thing the playhead crosses without cutting */
  steps?: string[];
  /** which step the film is pointing at, an index into `steps` — REQUIRED once a film supplies its own */
  held?: number;
  /** what there was finally time to read, shown only while the playhead is inside the held step */
  detail?: string;
  /** how much slower that stretch plays: 1 is no ramp, clamped to 20. The FILM's claim. */
  factor?: number;
  /** one line under the track, in the film's voice */
  note?: string;
}> = ({kicker = 'ONE MOMENT IN IT', steps: STEPS = DEMO, held: HELD_IN,
       detail = 'the thing that was true only here, and only for a moment',
       factor = 4, note = 'the rest of it went past at speed'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, fps, durationInFrames} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const ST = (Array.isArray(STEPS) ? STEPS : []).map((s) => String(s ?? '').trim());
  if (ST.length < MIN_STEPS) {
    throw new Error(
      `HeldInstant needs at least ${MIN_STEPS} steps, got ${ST.length}. The claim is that a RUN went past ` +
      'and one moment inside it decided the outcome; two steps are a before and an after, which is ' +
      'VersusSplit, and there is no run to be inside.');
  }
  if (ST.length > MAX_STEPS) {
    throw new Error(
      `HeldInstant holds at most ${MAX_STEPS} steps, got ${ST.length}. Past that each step is narrower ` +
      'than its own label and the run stops being one a viewer can follow. Aggregate the run, or give the ' +
      'tail its own beat.');
  }
  const blank = ST.findIndex((s) => !s);
  if (blank >= 0) {
    throw new Error(
      `HeldInstant was given an empty step (index ${blank}). An unnamed stop on a run is furniture: name ` +
      'what happened there, or make the run shorter.');
  }
  // WHICH MOMENT IS THE WHOLE CLAIM, so it is never defaulted for a film. A `held` of 2 on a run the
  // film supplied would point at a step the film never chose — the register making the argument instead
  // of carrying it, which is the one thing `content_contract_qa` exists to stop. The demo keeps its own
  // index (the identity check, not a length check: a film may legitimately pass four steps) so the
  // standalone preview and the three measurement scripts still render something real.
  const held = HELD_IN ?? (STEPS === DEMO ? DEMO_HELD : undefined);
  if (held == null) {
    throw new Error(
      'HeldInstant: pass `held` — the index of the step the film is pointing at. The whole register is ' +
      'ONE moment inside a run, and which moment it is is the claim; a register that picks it has made ' +
      'the argument up.');
  }
  const HELD = Math.round(Number(held));
  if (!Number.isFinite(HELD) || HELD < 0 || HELD >= ST.length) {
    throw new Error(
      `HeldInstant's \`held\` must be an index into \`steps\` (0..${ST.length - 1}), got ` +
      `${JSON.stringify(held)}.`);
  }
  const F = Math.max(1, Math.min(20, Number(factor) || 1));

  const n = ST.length;
  // The held step's share of the TRACK is 1/n; the ramp is centred on it and its half-width is half that
  // share, so the slow stretch is exactly the step and not a neighbourhood around it.
  const at = (HELD + 0.5) / n, width = 0.5 / n;
  // ...AND THE DWELL IS MEASURED, NOT ASSUMED. `factor` is the film's claim, and a shot short enough makes
  // even a fourfold ramp buy under a second — which is a ramp nobody can use the reading time from, so the
  // register says so rather than shipping an emphasis that emphasises nothing.
  const dwellS = React.useMemo(() => {
    const lo = speedRampInverse(at - width, at, width, F);
    const hi = speedRampInverse(at + width, at, width, F);
    return (hi - lo) * (durationInFrames / Math.max(1, fps));
  }, [at, width, F, durationInFrames, fps]);
  if (dwellS < MIN_DWELL_S) {
    throw new Error(
      `HeldInstant holds step ${HELD} for ${dwellS.toFixed(2)}s, under the ${MIN_DWELL_S}s this register ` +
      'exists to buy. The ramp is not paying for itself — raise `factor`, use fewer steps, or give the ' +
      'beat more time.');
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

  // ── geometry ────────────────────────────────────────────────────────────────────────────────────────
  const x0 = W * 0.08, span = W * 0.84;
  const STEP_PX = Math.round(U * 0.023), HELD_PX = Math.round(U * 0.036);
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const DETAIL_PX = Math.round(U * 0.027);
  const colW = span / n - U * 0.014;
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);

  // TIME, REMAPPED. Everything below reads `p`, never `t` — one clock for the whole shot, so the playhead,
  // the step that lights up and the detail that appears cannot disagree about where the run is.
  const p = speedRamp(t, at, width, F);
  const headX = x0 + span * p;
  const inHeld = p >= at - width && p <= at + width;
  const dwellPhase = clamp01((p - (at - width)) / Math.max(1e-6, 2 * width));

  const kickIn = clamp01(seg(t, 0.02, 0.1));
  const noteIn = clamp01(seg(t, 0.86, 0.96));
  // ONCE READ, IT STAYS — dimmer, because the dwell is when there was TIME to read it, not the only
  // moment it was true. Faded back out it also took the register's payoff off the settled frame, and the
  // contact sheet, `shot_still_qa` and every reviewer read that frame: an argument only visible mid-clip
  // is an argument nobody reviews.
  const read = clamp01((p - (at - width)) / Math.max(1e-6, 2 * width * 0.2));
  const detailIn = p < at - width ? 0 : (inHeld ? read : 0.45);

  const detailLines = detail ? wrapLines(String(detail), DETAIL_PX, span * 0.64) : 0;
  const stepLines = ST.map((s, i) => wrapLines(s, i === HELD ? HELD_PX : STEP_PX, colW));
  const labelH = Math.max(...stepLines.map((l, i) => l * (i === HELD ? HELD_PX : STEP_PX) * 1.25));
  const detailH = detail ? detailLines * DETAIL_PX * 1.35 + U * 0.02 : 0;
  const noteH = note ? wrapLines(String(note), NOTE_PX, span) * NOTE_PX * 1.4 + U * 0.02 : 0;
  const blockH = labelH + U * 0.08 + detailH + noteH;
  const trackY = Math.max(zoneTop + labelH + U * 0.03,
                          zoneTop + (zoneBot - zoneTop - blockH) / 2 + labelH + U * 0.03);

  return (
    <AbsoluteFill style={{background: BG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: x0, top: zoneTop - U * 0.05, opacity: kickIn,
          font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: '0.16em', color: ACC}}>{kicker}</div>
      ) : null}

      {/* the track — drawn once, ahead of the playhead, because the run existed before the shot did */}
      <svg width={W} height={Math.max(1, trackY + U * 0.02)} style={{position: 'absolute', left: 0, top: 0}}>
        <line x1={x0} y1={trackY} x2={x0 + span} y2={trackY} stroke={LINE} strokeWidth={hair * 2} />
        <line x1={x0} y1={trackY} x2={x0 + span} y2={trackY} stroke={ACC} strokeWidth={hair * 2}
          pathLength={1} {...drawOn(p)} />
      </svg>

      {/* the steps. The held one is larger and takes the accent once the playhead reaches it — before
          that it is a step like the others, because the film's point is that nobody could tell yet. */}
      {ST.map((s, i) => {
        const cx = x0 + span * ((i + 0.5) / n);
        const isHeld = i === HELD;
        const reached = p >= i / n;
        const px = isHeld ? HELD_PX : STEP_PX;
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: cx - hair, top: trackY - U * (isHeld ? 0.026 : 0.016),
              width: hair * (isHeld ? 3 : 2), height: U * (isHeld ? 0.026 : 0.016),
              background: isHeld && reached ? ACC : LINE}} />
            <div style={{position: 'absolute', left: cx - colW / 2, width: colW, textAlign: 'center',
              // BOTTOM-anchored, not positioned from a computed line count. `wrapLines` is deliberately
              // conservative — it over-estimated this label at two lines where the browser sets one — and
              // a block top-positioned by `top - lines * px` then floats by exactly that error: measured
              // 100px of daylight between the held label and its neighbours on the first render. Anchoring
              // the BOTTOM makes the layout immune to the estimator being wrong in either direction.
              bottom: H - (trackY - U * 0.026 - U * 0.012),
              font: `${isHeld ? 700 : 500} ${px}px/${leading(s, 1.25)} ${disp}`,
              color: isHeld && reached ? readableOn(BG, ACC, strong) : (reached ? strong : soft),
              opacity: reached ? 1 : 0.5, textWrap: 'balance'}}>{s}</div>
          </React.Fragment>
        );
      })}

      {/* the playhead */}
      <div style={{position: 'absolute', left: headX - hair * 1.5, top: trackY - U * 0.032,
        width: hair * 3, height: U * 0.064, background: ACC,
        opacity: easeOutCubic(clamp01(t / 0.06))}} />

      {/* what there was time to read — only while the playhead is inside the held step */}
      {detail ? (
        <div style={{position: 'absolute', left: x0 + span * 0.5 - span * 0.32, width: span * 0.64,
          top: trackY + U * 0.05, textAlign: 'center', opacity: detailIn,
          font: `400 ${DETAIL_PX}px/${leading(String(detail), 1.35)} ${disp}`, color: strong}}>{detail}</div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left: x0, width: span, opacity: noteIn,
          top: trackY + U * 0.05 + detailH, font: `400 ${NOTE_PX}px/${leading(String(note), 1.4)} ${mono}`,
          color: soft}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};

/** Where on the shot's own clock the remapped time `q` is reached — the inverse of `speedRamp`, by
 *  bisection because the forward map is monotone and this is called once per render, not per pixel.
 *  It exists so the DWELL can be measured in real seconds and refused when the ramp buys nothing: a
 *  register that cannot say how long it held something cannot be held to it. */
function speedRampInverse(q: number, at: number, width: number, factor: number): number {
  let lo = 0, hi = 1;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (speedRamp(mid, at, width, factor) < q) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

export default HeldInstant;
