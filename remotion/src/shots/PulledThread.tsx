// SHOT · Pulled Thread — these were WOVEN, not stacked. One thread is pulled, and the ones the film says
// it crosses are dragged out of line with it; the rest lie flat. The cloth is the argument: in a stack you
// can lift one layer and leave the others, and in a weave you cannot.
//
// WHAT IT ARGUES, AND WHY THE LIBRARY COULD NOT SAY IT. `GearTrain` drives a CHAIN — one turns the next,
// in order, and the last one lands the payoff. `RestsOn` is a HIERARCHY — the thing on top and the broader
// reasons under it. Both are directed and both are about structure holding still. This is the claim
// neither makes: that changing this one REQUIRES moving those, not later and not downstream but at the
// same instant, because they pass through each other. "You cannot touch this without touching those" is
// the sentence every dependency conversation is actually about, and the library drew it with arrows or
// not at all.
//
// WHY A WEAVE AND NOT A GRAPH. A dependency graph draws the coupling as an EDGE — a line you add between
// two things that are otherwise separate, which quietly says they could be separated by deleting the line.
// In cloth the coupling is not drawn at all: it is the material. Nothing is added to say these threads are
// connected, and nothing can be removed to disconnect them. The picture cannot be misread as "we could
// decouple this" because there is no coupling object to delete.
//
// WHERE THE HONESTY LINE IS. WHICH threads move is the film's claim and is never inferred — not from
// adjacency, not from distance from the pull. A register that decided "the neighbours move" would be
// asserting that nearness is coupling, which is exactly the thing the beat is there to state. The
// register supplies only the physics of the drag, and the faint cross-threads behind it are texture.
//
// WHAT FOLLOWS, FOLLOWS IN TIME — never in amplitude. A dragged thread could be drawn displaced by less
// the further it sits from the pull, which looks physical and would be the register inventing DEGREES of
// coupling the film never gave. They move by the same amount, staggered slightly in time, so the frame
// says "these came with it" and declines to say how much.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, hash01, easeOutCubic, springAt, SPRING_SEAT} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn, plane} from '../runtime/dna';

export const DURATION = 195; // 6.5s

/** Two threads make a PAIR, and "pull one, the other follows" is a pair's property, not a cloth's — the
 *  claim here is that a change reaches ACROSS something. Past seven the threads are closer together than
 *  the drag is deep and the displaced ones stop being tellable from the flat ones. */
export const MIN_THREADS = 3, MAX_THREADS = 7;

const BG_D0 = '#141014', FG_D0 = '#f2ecef', DIM_D0 = '#8d8087';
const ACC_D0 = '#c9566f', LINE_D0 = '#2b2229';

// Placeholder copy in the library's placeholder voice — the preview and all three measurement scripts
// render with defaults, and a prop left at '' does not draw at all.
const DEMO: Thread[] = [
  {label: 'the one that was changed', moves: false},
  {label: 'this had to move with it', moves: true},
  {label: 'this held still', moves: false},
  {label: 'this had to move too', moves: true},
];
const DEMO_PULLED = 0;

type Thread = {
  /** what this thread is, in the film's words */
  label?: string;
  /** the FILM's claim that this one is dragged by the pull — never inferred from where it sits */
  moves?: boolean;
};

export const PulledThread: React.FC<{
  kicker?: string;
  /** the threads, in the order the film lays them out — 3 to MAX_THREADS */
  threads?: Thread[];
  /** which thread is pulled, an index — REQUIRED once a film supplies its own */
  pulled?: number;
  /** one line under the cloth, in the film's voice */
  note?: string;
}> = ({kicker = 'WOVEN, NOT STACKED', threads: THREADS = DEMO, pulled: PULLED_IN,
       note = 'nothing was added to connect them; it is what they are made of'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, fps, durationInFrames} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const TH: Thread[] = Array.isArray(THREADS) ? THREADS : [];
  if (TH.length < MIN_THREADS) {
    throw new Error(
      `PulledThread needs at least ${MIN_THREADS} threads, got ${TH.length}. "Pull one and the other ` +
      'follows" is a property of a PAIR; this register\'s claim is that a change reaches across a cloth, ' +
      'which needs something for it to reach past.');
  }
  if (TH.length > MAX_THREADS) {
    throw new Error(
      `PulledThread holds at most ${MAX_THREADS} threads, got ${TH.length}. Past that they sit closer ` +
      'together than the drag is deep, and a dragged thread stops being tellable from a flat one — which ' +
      'is the only distinction on the frame.');
  }
  const noLabel = TH.findIndex((x) => !String(x?.label ?? '').trim());
  if (noLabel >= 0) {
    throw new Error(
      `PulledThread was given a thread with no \`label\` (index ${noLabel}). An unnamed thread in a cloth ` +
      'is the cloth: name what this one is, or leave it to the weave behind.');
  }
  // WHICH THREAD IS PULLED IS THE WHOLE CLAIM, so it is never defaulted for a film — the demo keeps its
  // own index (identity check, not a length check) so the preview and the measurement scripts still
  // render something real.
  const pulled = PULLED_IN ?? (THREADS === DEMO ? DEMO_PULLED : undefined);
  if (pulled == null) {
    throw new Error(
      'PulledThread: pass `pulled` — the index of the thread that was pulled. Which one moved first is ' +
      'the cause the beat is about, and a register that picks it has made the argument up.');
  }
  const P = Math.round(Number(pulled));
  if (!Number.isFinite(P) || P < 0 || P >= TH.length) {
    throw new Error(
      `PulledThread's \`pulled\` must be an index into \`threads\` (0..${TH.length - 1}), got ` +
      `${JSON.stringify(pulled)}.`);
  }
  // ...AND SOMETHING ELSE HAS TO MOVE. With every other thread flat the frame argues the OPPOSITE — that
  // this one came away clean — which is a real and common finding, and a different beat with a different
  // register. A picture that argues the reverse of its narration passes every gate in this repo.
  const followers = TH.map((x, i) => (i !== P && !!x?.moves ? i : -1)).filter((i) => i >= 0);
  if (!followers.length) {
    throw new Error(
      'PulledThread needs at least one OTHER thread marked `moves` — the film\'s claim about what the ' +
      'pull drags with it. With everything else flat this frame says the thread came away clean, which is ' +
      'the opposite beat; draw that with a register that argues separation.');
  }

  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const BG = dna?.bg ?? BG_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const U = Math.min(W, H);
  const strong = readableOn(BG, FG, FG_D0);
  const soft = dimOn(BG, DIM, 3);

  // ── the cloth ───────────────────────────────────────────────────────────────────────────────────────
  const n = TH.length;
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const LABEL_PX = Math.round(U * 0.023);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const noteLines = note ? wrapLines(String(note), NOTE_PX, W * 0.82) : 0;
  const noteH = note ? noteLines * NOTE_PX * 1.4 + U * 0.03 : 0;

  // Labels live in their own column at the left, so a thread's name never sits ON the cloth where the drag
  // would move it — a label that travels with the thread it names is unreadable exactly when the thread is
  // doing the thing the register is about.
  const labW = Math.min(W * 0.30, W * 0.22 + U * 0.06);
  const cx = W * 0.07 + labW + U * 0.03, cw = W * 0.93 - (W * 0.07 + labW + U * 0.03);
  const lineOf = TH.map((x) => wrapLines(String(x.label), LABEL_PX, labW));
  const rowH = Math.max(LABEL_PX * 1.5, ...lineOf.map((l) => l * LABEL_PX * 1.3)) + U * 0.022;
  const clothH = rowH * n;
  const cy = Math.max(zoneTop + U * 0.01, zoneTop + (zoneBot - noteH - zoneTop - clothH) / 2);
  const yOf = (i: number) => cy + rowH * (i + 0.5);

  // ── the pull. One spring, seated: cloth does not oscillate, it takes up and holds. ──────────────────
  const grab = clamp01(seg(t, 0.10, 0.22));                 // the hand closes on the thread
  const amp = rowH * 0.62;
  const drawIn = easeOutCubic(clamp01(seg(t, 0.02, 0.26)));
  const kickIn = clamp01(seg(t, 0.02, 0.1));
  const noteIn = clamp01(seg(t, 0.84, 0.94));
  const PULL_AT = 0.26;                                     // where on the clip the pull begins

  // A thread's displacement: the pulled one leads, the followers arrive a beat later — IN TIME, never in
  // amplitude, because how MUCH a thing is coupled is a degree the film never stated.
  const dispOf = (i: number) => {
    if (i !== P && !followers.includes(i)) return 0;
    const lag = i === P ? 0 : 0.035 + 0.02 * hash01(i + 3);
    const s = springAt(t, durationInFrames, fps, PULL_AT + lag, SPRING_SEAT);
    return amp * clamp01(s);
  };
  // The pull is deepest at the grab point and eases to nothing at both selvedges — a thread pinned at its
  // ends is what makes a pull a CURVE rather than a translation.
  const GRAB_U = 0.62;
  const pathOf = (i: number) => {
    const y = yOf(i), d = dispOf(i);
    const pts: string[] = [];
    for (let k = 0; k <= 32; k++) {
      const u = k / 32;
      // a smooth tent peaked at GRAB_U, zero at both ends
      const w = u < GRAB_U ? u / GRAB_U : (1 - u) / (1 - GRAB_U);
      const bend = Math.pow(Math.max(0, w), 1.6);
      pts.push(`${(cx + cw * u).toFixed(2)},${(y + d * bend).toFixed(2)}`);
    }
    return 'M' + pts.join(' L');
  };

  return (
    <AbsoluteFill style={{background: BG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: W * 0.07, top: zoneTop - U * 0.05, opacity: kickIn,
          font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: '0.16em', color: ACC}}>{kicker}</div>
      ) : null}

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* the cross-threads the named ones are woven through. Texture: they say "this is cloth", which is
            the one thing they can say honestly, and the register's claim does not rest on them. */}
        {/* @decor: the warp is a material, not a reading — its count and spacing name nothing the film gave */}
        {Array.from({length: 46}, (_, k) => {
          const u = (k + 0.5) / 46, x = cx + cw * u;
          // THE WARP BENDS WITH THE THREADS IT PASSES THROUGH. Drawn straight — which is what the first
          // render did — the cross-threads read as a GRID the named lines happen to lie over, and the
          // register's whole premise is that the coupling is not a thing laid on top but the material
          // itself. A warp that dips where the weft was dragged is the same fact seen from ninety
          // degrees, and it is what makes the picture cloth instead of a chart.
          const w = u < GRAB_U ? u / GRAB_U : (1 - u) / (1 - GRAB_U);
          const bend = Math.pow(Math.max(0, w), 1.6);
          const pts = TH.map((_, i) => `${x.toFixed(2)},${(yOf(i) + dispOf(i) * bend).toFixed(2)}`);
          // the selvedge overhang, so the warp does not stop dead on the outermost thread
          const head = `${x.toFixed(2)},${(yOf(0) + dispOf(0) * bend - rowH * 0.3).toFixed(2)}`;
          const tail = `${x.toFixed(2)},${(yOf(n - 1) + dispOf(n - 1) * bend + rowH * 0.3).toFixed(2)}`;
          return (
            <path key={k} d={'M' + [head, ...pts, tail].join(' L')} fill="none"
              stroke={plane(BG, 0.14)} strokeWidth={Math.max(1, U * 0.0024)}
              opacity={drawIn * 0.95} />
          );
        })}
        {/* the named threads */}
        {TH.map((x, i) => {
          const isPull = i === P, follows = followers.includes(i);
          return (
            <path key={i} d={pathOf(i)} fill="none" strokeLinecap="round"
              stroke={isPull ? ACC : follows ? strong : soft}
              strokeWidth={Math.max(1.5, U * (isPull ? 0.0075 : follows ? 0.0055 : 0.0038))}
              opacity={drawIn * (isPull || follows ? 1 : 0.72)} />
          );
        })}
        {/* where the hand has it */}
        <circle cx={cx + cw * GRAB_U} cy={yOf(P) + dispOf(P)} r={U * 0.011 * grab}
          fill="none" stroke={ACC} strokeWidth={Math.max(1.5, U * 0.0035)} opacity={grab} />
      </svg>

      {/* the names, in their own column, level with the thread they name */}
      {TH.map((x, i) => {
        const isPull = i === P, follows = followers.includes(i);
        return (
          <div key={i} style={{position: 'absolute', left: W * 0.07, width: labW, textAlign: 'right',
            top: yOf(i) - lineOf[i] * LABEL_PX * 1.3 / 2, opacity: drawIn,
            font: `${isPull ? 700 : follows ? 600 : 400} ${LABEL_PX}px/${leading(String(x.label), 1.3)} ${disp}`,
            color: isPull ? readableOn(BG, ACC, strong) : follows ? strong : soft}}>{x.label}</div>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.07, width: W * 0.82, opacity: noteIn,
          top: zoneBot - noteLines * NOTE_PX * 1.4 - U * 0.01,
          font: `400 ${NOTE_PX}px/${leading(String(note), 1.4)} ${mono}`, color: soft}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default PulledThread;
