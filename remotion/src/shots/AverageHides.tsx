// SHOT · Average Hides — the number everyone quotes, and the distance to the one nobody does. Most cases
// pile up near the typical value; a few sit far out, and the frame's whole job is the GAP between them,
// drawn as a length you can compare against the width of the pile.
//
// WHAT IT ARGUES, AND WHY THE LIBRARY COULD NOT SAY IT. Asked of the PROPS rather than the prose — which
// this repo's own peer study says is the reliable question — the library accepts a `label`, sometimes a
// `value`, and a handful of flags. It has NO field anywhere for a quantity's spread: `spread` appears in
// exactly one register, `OverlapSeparation`, and there it belongs to two populations being compared by a
// metric. So a film could say "it takes 200ms" and could compare two measures, and could not say the one
// thing that is true of every system it might describe: **the average is not the experience**. `EdStat` and
// `TermCounter` set one headline figure beautifully and are the very instrument this register exists to
// answer — a quoted number with nothing around it is the claim being corrected.
//
// WHY THE GEOMETRY DOES THE ARGUING. Both values are the film's own, and the axis is scaled to the larger,
// so a tail twenty times the typical value COLLAPSES the pile into a mark at the left and strands the tail
// against the right edge. That is the true picture and it is exactly what a bar chart of the average hides;
// nothing here is tuned to produce it, and a film whose tail is close to its typical case gets a frame that
// says so instead.
//
// WHERE THE HONESTY LINE IS. The pile is TEXTURE — it says "many cases", which is all a cloud of unlabelled
// marks can honestly say — and it is declared as such. Every number on the frame is one the film wrote,
// never a computed statistic: this register does not know how many cases there were, what the mean is, or
// what the distribution's shape was, and it draws none of them.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, hash01, easeOutCubic, easeOutBack} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn, plane} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {useGlide} from '../runtime/glide';

export const DURATION = 195; // 6.5s

// There is deliberately NO share threshold. `share` is the film's own words — "1 in 20", "每二十次一次" —
// because a fraction this register computed would be a statistic it was never given, and the one number it
// could check against is the one it must not invent. An earlier draft exported a `MAX_TAIL_SHARE` constant
// that nothing could ever compare against: a header promising a rule the code does not have, which this
// session has already shipped once.
/** How far out the tail must sit before the gap is the point. Below this the two values are near enough
 *  that the average is a fair summary, and this register would be manufacturing an alarm. */
export const MIN_TAIL_RATIO = 1.5;

const BG_D0 = '#0f1216', FG_D0 = '#eef2f7', DIM_D0 = '#79838f';
const ACC_D0 = '#e2b33c', LINE_D0 = '#232830';

// Placeholder copy in the library's placeholder voice — the preview and all three measurement scripts
// render with defaults, and a prop left at '' does not draw at all.
const DEMO_TYPICAL = {label: 'what gets quoted', value: 1};
const DEMO_TAIL = {label: 'what some of them get', value: 9, share: '1 in 20'};

type Point = {
  /** what this value IS, in the film's words — never a computed statistic */
  label?: string;
  /** the film's own number, in whatever unit it is speaking */
  value?: number;
  /** how often, in the film's words ("1 in 20", "每二十次一次") — never a fraction this computes */
  share?: string;
};

export const AverageHides: React.FC<{
  kicker?: string;
  /** the number everyone quotes */
  typical?: Point;
  /** the one it hides */
  tail?: Point;
  /** what the axis is measuring, in the film's words */
  unit?: string;
  /** one line under the axis, in the film's voice */
  note?: string;
}> = ({kicker = 'THE NUMBER AND THE TAIL', typical = DEMO_TYPICAL, tail = DEMO_TAIL,
       unit = '', note = 'the average is not the experience'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const tv = Number(typical?.value), xv = Number(tail?.value);
  if (!Number.isFinite(tv) || !Number.isFinite(xv) || tv <= 0 || xv <= 0) {
    throw new Error(
      `AverageHides needs a positive \`value\` on both \`typical\` and \`tail\`, got ${JSON.stringify(typical?.value)} ` +
      `and ${JSON.stringify(tail?.value)}. Both numbers are the film's own; this register computes no ` +
      'statistic and cannot supply one.');
  }
  const noLabel = !String(typical?.label ?? '').trim() || !String(tail?.label ?? '').trim();
  if (noLabel) {
    throw new Error(
      'AverageHides needs a `label` on both `typical` and `tail`. A number on an axis with nothing beside ' +
      'it is a reading the viewer has to guess the meaning of, and the whole beat is what the two numbers ' +
      'MEAN to someone.');
  }
  // ...AND THE TAIL HAS TO BE OUT THERE. Below `MIN_TAIL_RATIO` the two values sit together, the average is
  // a fair summary of them, and this frame would be manufacturing an alarm out of an honest number — a
  // picture that argues something the beat did not, which is the failure this repo treats as the worst one.
  if (xv / tv < MIN_TAIL_RATIO) {
    throw new Error(
      `AverageHides was given a tail ${(xv / tv).toFixed(2)}x the typical value, under ${MIN_TAIL_RATIO}x. ` +
      'That close, the quoted number IS a fair summary and this frame would manufacture an alarm the beat ' +
      'did not make. Say the number plainly (EdStat / TermCounter), or find the case that is actually far out.');
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

  // ── geometry. The axis is scaled to the TAIL, so the distance on the frame is the ratio in the data. ──
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const NUM_PX = Math.round(U * 0.05), LAB_PX = Math.round(U * 0.021);
  const SHARE_PX = Math.round(U * 0.018);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const noteLines = note ? wrapLines(String(note), NOTE_PX, W * 0.82) : 0;
  const noteH = note ? noteLines * NOTE_PX * 1.4 + U * 0.03 : 0;
  const ax = W * 0.09, aw = W * 0.82;
  const ay = Math.max(zoneTop + U * 0.14, zoneTop + (zoneBot - noteH - zoneTop) / 2);
  // A little headroom past the tail so its mark is never on the frame's edge — the axis is the film's
  // range, and the pad is the drawing's, so it is taken off the DRAWN width rather than added to the data.
  const xOf = (v: number) => ax + aw * 0.94 * (v / xv);

  const drawIn = easeOutCubic(clamp01(seg(t, 0.04, 0.3)));
  const pileIn = clamp01(seg(t, 0.2, 0.52));
  const typIn = clamp01(seg(t, 0.4, 0.58));
  const tailIn = clamp01(seg(t, 0.6, 0.8));
  const gapIn = clamp01(seg(t, 0.66, 0.82));
  const kickIn = clamp01(seg(t, 0.02, 0.1));
  const noteIn = clamp01(seg(t, 0.74, 0.84));

  // THE PILE. Texture standing for "many cases", clustered around the typical value and thinning outward,
  // with a handful strung out toward the tail. Deterministic from `hash01`.
  // @decor: the marks are a crowd, not a count — this register is told no case count and draws none
  const pile = React.useMemo(() => {
    const out: {x: number; y: number; r: number; k: number}[] = [];
    for (let i = 0; i < 120; i++) {
      const u = hash01(i * 5 + 1), v = hash01(i * 5 + 2), w = hash01(i * 5 + 3);
      // most sit around the typical value; a thin scatter reaches out toward the tail
      const far = w > 0.86;
      const val = far ? tv + (xv - tv) * (0.15 + 0.85 * u) : tv * (0.45 + 0.85 * u);
      out.push({x: xOf(Math.min(val, xv)), y: ay - U * (0.012 + 0.10 * v * (far ? 0.45 : 1)),
        r: U * (0.0022 + 0.0016 * hash01(i * 7)), k: i});
    }
    return out;
  }, [tv, xv, ay, U, xOf]);

  const tx = xOf(tv), xx = xOf(xv);
  // A LABEL IS CENTRED ON ITS TICK, and clamped by its CENTRE rather than by its left edge. Clamping the
  // edge slides the box while its text stays centred inside it, so the number drifts off the tick it
  // names — measured at ~100px on the first render, with the tail's figure pointing at empty axis.
  // Narrow boxes so the clamp bites rarely, and when it must, the text still sits as near the tick as the
  // frame allows.
  const boxW = W * 0.22;
  const centred = (x: number) => Math.max(U * 0.02 + boxW / 2, Math.min(W - U * 0.02 - boxW / 2, x));
  // The figures ride ABOVE the crowd, not through it: the pile reaches 0.112U over the axis and the first
  // render set the typical figure inside that, so the number everyone quotes was printed on top of the
  // cases it summarises and neither read.
  const NUM_BOTTOM = H - (ay - U * 0.135);

  return (
    <AbsoluteFill style={{background: BG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: ax, top: zoneTop - U * 0.05, opacity: kickIn,
          font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: '0.16em', color: ACC}}>{kicker}</div>
      ) : null}

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <line x1={ax} y1={ay} x2={ax + aw} y2={ay} stroke={LINE} strokeWidth={hair * 2}
          pathLength={1} {...drawOn(drawIn)} />
        {/* the crowd */}
        {pile.map((p) => (
          <circle key={p.k} cx={p.x} cy={p.y} r={p.r} fill={plane(BG, 0.3)}
            opacity={pileIn * (0.5 + 0.5 * hash01(p.k * 11))} />
        ))}
        {/* the quoted number, and the one it hides */}
        <line x1={tx} y1={ay - U * 0.03} x2={tx} y2={ay + U * 0.016}
          stroke={strong} strokeWidth={hair * 2} opacity={typIn} />
        <line x1={xx} y1={ay - U * 0.05} x2={xx} y2={ay + U * 0.016}
          stroke={ACC} strokeWidth={hair * 3} opacity={tailIn} />
        {/* THE GAP IS A REGION, not a line. This repo's own peer study records why: mechanism registers
            measured a median 2.4% ink because "relations are conventionally drawn as boxes and arrows,
            and a line has no area — the relation had to become a REGION". The span between the quoted
            number and the one it hides IS the claim, so it is given area: everything in this band is what
            the average does not cover, and the eye reads its SIZE rather than tracing a rule. */}
        <rect x={tx} y={ay - U * 0.125} width={Math.max(0, (xx - tx) * gapIn)} height={U * 0.125 + U * 0.03}
          fill={ACC} opacity={gapIn * 0.1} />
        {/* ...and the measured rule under it, which is what turns an area into a LENGTH you can compare */}
        <line x1={tx} y1={ay + U * 0.052} x2={tx + (xx - tx) * gapIn} y2={ay + U * 0.052}
          stroke={ACC} strokeWidth={hair * 2} opacity={gapIn} />
        <line x1={tx} y1={ay + U * 0.042} x2={tx} y2={ay + U * 0.062}
          stroke={ACC} strokeWidth={hair * 2} opacity={gapIn} />
        <line x1={xx} y1={ay + U * 0.042} x2={xx} y2={ay + U * 0.062}
          stroke={ACC} strokeWidth={hair * 2} opacity={gapIn * (gapIn > 0.98 ? 1 : 0)} />
      </svg>

      {/* the quoted number */}
      <div style={{position: 'absolute', left: centred(tx) - boxW / 2, width: boxW,
        textAlign: 'center', bottom: NUM_BOTTOM, opacity: typIn,
        font: `700 ${NUM_PX}px/1.05 ${disp}`, color: strong}}>
        {typical?.value}{unit ? <span style={{font: `500 ${Math.round(NUM_PX * 0.44)}px/1 ${mono}`,
          color: soft, marginLeft: U * 0.006}}>{unit}</span> : null}
      </div>
      <div style={{position: 'absolute', left: centred(tx) - boxW / 2, width: boxW,
        textAlign: 'center', top: ay + U * 0.022, opacity: typIn,
        font: `500 ${LAB_PX}px/${leading(String(typical?.label), 1.25)} ${disp}`, color: soft}}>
        {typical?.label}
      </div>

      {/* the one it hides */}
      <div style={{position: 'absolute', left: centred(xx) - boxW / 2, width: boxW,
        textAlign: 'center', bottom: NUM_BOTTOM, opacity: tailIn,
        transform: glide(`translateY(${(1 - easeOutBack(tailIn)) * U * 0.012}px)`, tailIn !== 1),
        font: `700 ${NUM_PX}px/1.05 ${disp}`, color: readableOn(BG, ACC, strong)}}>
        {tail?.value}{unit ? <span style={{font: `500 ${Math.round(NUM_PX * 0.44)}px/1 ${mono}`,
          color: soft, marginLeft: U * 0.006}}>{unit}</span> : null}
      </div>
      <div style={{position: 'absolute', left: centred(xx) - boxW / 2, width: boxW,
        textAlign: 'center', top: ay + U * 0.022, opacity: tailIn,
        font: `600 ${LAB_PX}px/${leading(String(tail?.label), 1.25)} ${disp}`, color: strong}}>
        {tail?.label}
        {tail?.share ? (
          <div style={{font: `500 ${SHARE_PX}px/1.3 ${mono}`, color: ACC, letterSpacing: '0.06em',
            marginTop: U * 0.006}}>{tail.share}</div>
        ) : null}
      </div>

      {note ? (
        <div style={{position: 'absolute', left: ax, width: W * 0.82, opacity: noteIn,
          top: zoneBot - noteLines * NOTE_PX * 1.4 - U * 0.01,
          font: `400 ${NOTE_PX}px/${leading(String(note), 1.4)} ${mono}`, color: soft}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default AverageHides;
