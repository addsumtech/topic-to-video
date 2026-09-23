// SHOT · Near The Line — a rule has an EDGE; a model has a MARGIN. The boundary it learned crosses the
// field, a band either side of it is where its answer is a coin-flip, and the cases the film names sit
// where the film says they sit: some clear of the band, at least one inside it.
//
// WHAT IT ARGUES, AND WHY THE LIBRARY COULD NOT SAY IT. Search the catalogue for "confidence" or
// "uncertain" and there is nothing. The nearest register, `OverlapSeparation`, argues about MEASURES —
// this metric cannot tell these two apart, that one can — which is a claim about instruments. This one is
// a claim about a single system's own answers: it is certain in the middle and guessing at the edge, and
// **from outside, the guess looks exactly as confident as the certainty**. That sentence is the honest
// thing to say about any learned classifier, it is what an audience most needs told, and nothing here
// could draw it.
//
// WHY THE BOUNDARY BENDS. A ruled straight line is a RULE — someone wrote it, and you can read it off.
// What a model has is a surface fitted to what it happened to see, so it wanders, and it wanders most
// where it saw least. Drawing it straight would illustrate the wrong object and quietly make the
// register's own argument impossible: a rule's edge has no margin to be near.
//
// WHERE THE HONESTY LINE IS. The anonymous field behind the argument is TEXTURE — it says "there were
// many cases", which is the one thing a field of dots can honestly say. Every case the film NAMES is
// placed from the film's own words: which side it is on, and whether it is near the line. The register
// chooses no case's standing, because which cases are marginal is the entire claim and a register that
// picks them has made the argument up.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, hash01, easeOutCubic, easeOutBack} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn, plane} from '../runtime/dna';
import {drawOn} from '../runtime/draw';

export const DURATION = 195; // 6.5s

/** One named case cannot show a margin (there is nothing for it to be near OR clear of); past six the
 *  labels are closer together than the band is wide and the picture stops separating the two readings. */
export const MIN_CASES = 2, MAX_CASES = 6;

/** How wide the coin-flip band is, as a fraction of the field's height. Not a knob a film turns: how
 *  uncertain a model is near its own boundary is not something a beat measures, and a band the film could
 *  widen would be a number invented here and presented as a reading. */
const MARGIN_FRAC = 0.155;

const BG_D0 = '#0b0e14', FG_D0 = '#e6ecf5', DIM_D0 = '#6f7a8b';
const ACC_D0 = '#7c6cf0', LINE_D0 = '#1c2230';

// Placeholder copy in the library's placeholder voice — the preview and all three measurement scripts
// render with defaults, and a prop left at '' does not draw at all.
const DEMO: Case[] = [
  {label: 'clearly one', side: 'a'},
  {label: 'clearly the other', side: 'b'},
  {label: 'this one it is guessing about', side: 'a', near: true},
];

type Case = {
  /** what this case is, in the film's words */
  label?: string;
  /** which side of the boundary the FILM says it falls — never decided here */
  side?: 'a' | 'b';
  /** the film's claim that this case sits in the band where the answer is a coin-flip */
  near?: boolean;
};

export const NearTheLine: React.FC<{
  kicker?: string;
  /** what the two sides are called, in the film's words */
  sideA?: string;
  sideB?: string;
  /** the cases the film points at — 2 to MAX_CASES, at least one of them `near` */
  cases?: Case[];
  /** one line under the field, in the film's voice */
  note?: string;
}> = ({kicker = 'WHAT IT IS SURE OF', sideA = 'one answer', sideB = 'the other answer',
       cases = DEMO, note = 'the guess and the certainty look the same from outside'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const CS: Case[] = Array.isArray(cases) ? cases : [];
  if (CS.length < MIN_CASES) {
    throw new Error(
      `NearTheLine needs at least ${MIN_CASES} cases, got ${CS.length}. The claim is that some answers are ` +
      'certain and some are a coin-flip, and one case alone has nothing to be certain BY comparison with.');
  }
  if (CS.length > MAX_CASES) {
    throw new Error(
      `NearTheLine holds at most ${MAX_CASES} cases, got ${CS.length}. Past that the labels are closer ` +
      'together than the band is wide, and the two readings the register exists to separate stop being ' +
      'separable on the frame.');
  }
  const badSide = CS.findIndex((c) => c?.side !== 'a' && c?.side !== 'b');
  if (badSide >= 0) {
    throw new Error(
      `NearTheLine's case ${badSide} has \`side\` ${JSON.stringify(CS[badSide]?.side)}; it must be 'a' or ` +
      "'b'. Which side of the boundary a case falls is the film's reading of it, and a register that " +
      'places it has decided the thing the beat is about.');
  }
  const noLabel = CS.findIndex((c) => !String(c?.label ?? '').trim());
  if (noLabel >= 0) {
    throw new Error(
      `NearTheLine was given a case with no \`label\` (index ${noLabel}). An unnamed dot in a field of dots ` +
      'is the field; name what this case is, or leave it to the texture.');
  }
  // ...AND AT LEAST ONE MUST BE NEAR THE LINE. This is the register, not a detail of it: with every case
  // clear of the band the frame shows a tidy separation, which is the OPPOSITE claim — "it can tell these
  // apart" — and the film should be reaching for a comparison register instead. A picture that argues the
  // reverse of the beat is worse than no picture, and it would pass every gate.
  if (!CS.some((c) => c?.near)) {
    throw new Error(
      'NearTheLine needs at least one case marked `near` — a case the film says sits in the band where the ' +
      'answer is a coin-flip. With every case clear of the boundary this frame argues the opposite: that ' +
      'the system separates them cleanly. If that is the beat, it is a comparison, not a margin.');
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

  // ── the field ───────────────────────────────────────────────────────────────────────────────────────
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const SIDE_PX = Math.round(U * 0.021), CASE_PX = Math.round(U * 0.021);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const noteLines = note ? wrapLines(String(note), NOTE_PX, W * 0.82) : 0;
  const noteH = note ? noteLines * NOTE_PX * 1.4 + U * 0.03 : 0;
  const fx = W * 0.08, fw = W * 0.84;
  const fy = zoneTop + U * 0.02, fh = Math.max(U * 0.2, zoneBot - noteH - fy);

  // THE BOUNDARY, as a function of x. A cubic through three control heights the shot fixes once: it has to
  // be the SAME curve every render (two renders of a frame are the same bytes) and it has to bend, because
  // a straight line is a rule and a rule has no margin.
  const boundaryAt = React.useCallback((u: number) => {
    const p = clamp01(u);
    return fy + fh * (0.52 + 0.17 * Math.sin(p * Math.PI * 1.15 - 0.5) - 0.07 * Math.cos(p * Math.PI * 2.1));
  }, [fy, fh]);
  const band = fh * MARGIN_FRAC;

  const draw = easeOutCubic(clamp01(seg(t, 0.06, 0.34)));
  const bandIn = clamp01(seg(t, 0.36, 0.56));
  const casesIn = clamp01(seg(t, 0.5, 0.78));
  const kickIn = clamp01(seg(t, 0.02, 0.1));
  const noteIn = clamp01(seg(t, 0.72, 0.84));

  const path = React.useMemo(() => {
    const pts: string[] = [];
    for (let i = 0; i <= 48; i++) {
      const u = i / 48;
      pts.push(`${(fx + fw * u).toFixed(2)},${boundaryAt(u).toFixed(2)}`);
    }
    return 'M' + pts.join(' L');
  }, [fx, fw, boundaryAt]);

  const bandPath = React.useMemo(() => {
    const top: string[] = [], bot: string[] = [];
    for (let i = 0; i <= 48; i++) {
      const u = i / 48, x = fx + fw * u, y = boundaryAt(u);
      top.push(`${x.toFixed(2)},${(y - band).toFixed(2)}`);
      bot.unshift(`${x.toFixed(2)},${(y + band).toFixed(2)}`);
    }
    return 'M' + top.join(' L') + ' L' + bot.join(' L') + ' Z';
  }, [fx, fw, band, boundaryAt]);

  // THE ANONYMOUS FIELD. It says one thing — "there were many cases" — which is the only thing a cloud of
  // unlabelled dots can say honestly. Deterministic from `hash01`, and thinned inside the band because a
  // model sees FEWEST examples where it is least sure, which is why the band is there at all.
  // @decor: positions and count are texture standing for "many cases", never a reading about anything the film named
  const field = React.useMemo(() => {
    const out: {x: number; y: number; a: boolean; r: number}[] = [];
    for (let i = 0; i < 132; i++) {
      const u = hash01(i * 3 + 1), v = hash01(i * 3 + 2);
      const x = fx + fw * (0.02 + 0.96 * u), y = fy + fh * (0.06 + 0.88 * v);
      const d = y - boundaryAt((x - fx) / fw);
      if (Math.abs(d) < band * (0.35 + 0.65 * hash01(i * 3 + 3))) continue;
      out.push({x, y, a: d < 0, r: U * (0.0026 + 0.0022 * hash01(i * 7))});
    }
    return out;
  }, [fx, fw, fy, fh, band, U, boundaryAt]);

  // WHERE A NAMED CASE SITS — from the film's own two words about it, nothing else. `side` picks which
  // half; `near` puts it inside the band and anything else well clear of it. Spread along x by index so
  // two cases never land on one another, which is layout, not a reading.
  const placed = CS.map((c, i) => {
    const u = (i + 0.5) / CS.length;
    const x = fx + fw * (0.08 + 0.84 * u);
    const b = boundaryAt((x - fx) / fw);
    const dir = c.side === 'a' ? -1 : 1;
    const off = c.near ? band * 0.52 : band + fh * (0.10 + 0.07 * hash01(i + 11));
    // CLAMPED INTO THE FIELD. A case clear of the band is pushed away from the boundary, and where the
    // boundary runs near the plot's own edge that push put the dot outside it — measured on the first
    // render with "clearly the other" sitting on the note. Clamping keeps the film's reading (which side,
    // how far) and only refuses to draw it off the picture.
    const lo = fy + fh * 0.08, hi = fy + fh * 0.92;
    return {...c, x, y: Math.max(lo, Math.min(hi, b + dir * off)), near: !!c.near};
  });

  return (
    <AbsoluteFill style={{background: BG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: fx, top: zoneTop - U * 0.05, opacity: kickIn,
          font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: '0.16em', color: ACC}}>{kicker}</div>
      ) : null}

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* the coin-flip band — the register's whole point, so it arrives AFTER the line and stays */}
        <path d={bandPath} fill={plane(BG, 0.11)} opacity={bandIn} />
        <path d={bandPath} fill="none" stroke={LINE} strokeWidth={hair} opacity={bandIn * 0.9} />
        {/* the anonymous field */}
        {field.map((p, i) => (
          // FILLED on one side, a RING on the other. Two greys a shade apart is what the first render
          // had, and at dot size that is one population, not two — which quietly removes half of what
          // the register is arguing. Fill-versus-outline is the one scatter distinction that survives
          // being small, and it survives a light DNA too.
          <circle key={i} cx={p.x} cy={p.y} r={p.r}
            fill={p.a ? 'none' : plane(BG, 0.34)}
            stroke={p.a ? soft : 'none'} strokeWidth={p.a ? Math.max(1, p.r * 0.5) : 0}
            opacity={clamp01(seg(t, 0.02 + 0.2 * hash01(i), 0.3 + 0.2 * hash01(i))) * 0.9} />
        ))}
        {/* the learned boundary */}
        <path d={path} fill="none" stroke={ACC} strokeWidth={hair * 2.5} strokeLinecap="round"
          pathLength={1} {...drawOn(draw)} />
      </svg>

      {/* the two sides, named by the film, set against the halves they label */}
      <div style={{position: 'absolute', left: fx, top: fy + U * 0.005, width: fw * 0.42,
        opacity: draw, font: `600 ${SIDE_PX}px/${leading(String(sideA), 1.2)} ${mono}`,
        letterSpacing: '0.08em', color: soft}}>{sideA}</div>
      <div style={{position: 'absolute', left: fx + fw * 0.58, width: fw * 0.42, textAlign: 'right',
        top: fy + fh - SIDE_PX * 1.6, opacity: draw,
        font: `600 ${SIDE_PX}px/${leading(String(sideB), 1.2)} ${mono}`,
        letterSpacing: '0.08em', color: soft}}>{sideB}</div>

      {/* the named cases */}
      {placed.map((c, i) => {
        const on = clamp01((casesIn * CS.length - i) * 1.6);
        if (on <= 0) return null;
        const pop = easeOutBack(clamp01(on));
        const above = c.y > fy + fh * 0.5;
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: c.x - U * 0.009 * pop, top: c.y - U * 0.009 * pop,
              width: U * 0.018 * pop, height: U * 0.018 * pop, borderRadius: '50%',
              background: c.near ? ACC : strong,
              boxShadow: c.near ? `0 0 ${U * 0.02}px ${ACC}` : 'none', opacity: on}} />
            <div style={{position: 'absolute', left: c.x - fw * 0.12, width: fw * 0.24, textAlign: 'center',
              ...(above ? {bottom: H - (c.y - U * 0.022)} : {top: c.y + U * 0.022}),
              opacity: on, font: `${c.near ? 700 : 500} ${CASE_PX}px/${leading(String(c.label), 1.25)} ${disp}`,
              color: c.near ? readableOn(BG, ACC, strong) : strong,
              transform: `translateY(${(1 - pop) * U * 0.008}px)`, textWrap: 'balance'}}>
              {/* No register-authored words. A hardcoded "inside the band" shipped ENGLISH onto a
                  Chinese film and was the register talking over the beat; the glow, the accent and the
                  dot's position inside the band already say it, and `note` is where the film says what
                  it MEANS. */}
              {c.label}
            </div>
          </React.Fragment>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.09, width: W * 0.82, opacity: noteIn,
          top: zoneBot - noteLines * NOTE_PX * 1.4 - U * 0.01,
          font: `400 ${NOTE_PX}px/${leading(String(note), 1.4)} ${mono}`, color: soft}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default NearTheLine;
