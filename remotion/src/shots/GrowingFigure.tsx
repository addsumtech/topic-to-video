// SHOT · Growing Figure — one figure that BECOMES the next: a cell that stretches and divides, a point that becomes a
// line, a triangle, a closed shape; the film's own outlines in the order it names them. The figure is drawn on, then
// carried through each state by a true shape morph (runtime/pathMorph), while a rail names the state it is in.
//
// WHAT IT ARGUES. Continuity of one thing through its stages: what is on screen is never replaced, it is reshaped, and
// a piece that splits does so out of the whole it belonged to. Hide the caption and the sequence still says "this
// became that"; the rail says what each stage is called. Not for a list of different things (a grid), not for a
// before/after comparison of two separate objects (a comparison register), not for a quantity growing (a chart).
//
// HOW IT MOVES. The first state's outline draws on and its fill rises. Each later state: a hold so the stage is read,
// then the morph — both outlines resampled to the same points by arc length and aligned (same winding, least travel)
// so a circle does not spin or turn inside out on its way into a square; a state with more pieces shares the pieces
// before it, so one cell drawn twice over itself parts into two. The state just left lingers as a faint dashed ghost.
// The rail's marker travels to the new stage as the shape does.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, contrastOf, mix} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {rows} from '../runtime/rows';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {planMorph, morphPieces, shapeD, fitD, SHAPE_NAMES, type ShapeName} from '../runtime/pathMorph';

export const DURATION = 270; // 9s

const BG_D0 = '#0b1210', FG_D0 = '#eef4f0', DIM_D0 = '#8a9a92', ACC_D0 = '#62d6a0';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

export type FigureState = {
  /** what this stage is called — the film's word for it */
  label: string;
  /** a named outline… */
  shape?: ShapeName;
  /** …repeated side by side (a division: 1, then 2) */
  count?: number;
  /** …or the film's own outline, in a 0–1000 square (any SVG path commands) */
  d?: string;
};

const DEFAULT_TITLE = 'One becomes two';
const DEFAULT_STATES: FigureState[] = [
  {label: 'One cell', shape: 'circle'},
  {label: 'It stretches', shape: 'ellipse'},
  {label: 'Two cells', shape: 'circle', count: 2},
];

// one Kinetic row per state, at most four: hooks are called a fixed number of times
const MAX_STATES = 4;

export const GrowingFigure: React.FC<{
  kicker?: string;
  title?: string;
  /** 2–4 states of the one figure, in order */
  states?: FigureState[];
  /** fill the figure (default) or draw its outline only */
  filled?: boolean;
  accent?: string;
}> = ({kicker = 'CELL DIVISION', title: TITLE_IN, states: STATES_IN = DEFAULT_STATES, filled = true,
       accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const states = rows<FigureState>(STATES_IN, 'states', 'GrowingFigure');
  // the demo's title belongs to the demo's states (an omitted `states` IS the default array)
  const title = TITLE_IN ?? (STATES_IN === DEFAULT_STATES ? DEFAULT_TITLE : undefined);
  if (states.length < 2 || states.length > MAX_STATES) {
    throw new Error(`GrowingFigure carries one figure through 2–${MAX_STATES} states, got ${states.length}.`);
  }
  states.forEach((s, i) => {
    if (!s || !String(s.label ?? '').trim()) throw new Error(`GrowingFigure: state ${i + 1} has no \`label\` — the film names every stage.`);
    if (!s.d && !s.shape) throw new Error(`GrowingFigure: state ${i + 1} ("${s.label}") needs a \`shape\` or the film's own \`d\`.`);
    if (s.shape && !SHAPE_NAMES.includes(s.shape)) {
      throw new Error(`GrowingFigure: state ${i + 1}'s shape is one of ${SHAPE_NAMES.join(', ')}, got "${s.shape}".`);
    }
  });

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);

  const U = Math.min(W, H);
  const mx = Math.round(W * 0.07);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const KICK = Math.ceil(U * 0.028);
  const kickH = kicker ? Math.round(KICK * 1.25 + U * 0.022) : 0;
  const TITLE = Math.round(U * 0.058);
  const titleH = title ? Math.round(TITLE * 1.1 * 2 + U * 0.02) : 0;
  const top = zoneTop + kickH + titleH + U * 0.02;
  const n = states.length;
  // side by side while the frame is wide enough for a square figure AND a rail of readable rows; else stacked
  const side = W >= H * 0.95;
  const ROW = Math.round(U * 0.042);
  // stacked, the rail may take at most half the room under the heading: past that the figure — the thing the beat is
  // about — was squeezed to a sliver (seen at 1:1 before the side-by-side test moved there)
  const roomH = zoneBot - top;
  const rowH = Math.round(Math.min(ROW * 1.35 * 2 + U * 0.018, side ? Infinity : (roomH * 0.5) / n));
  if (rowH < ROW * 1.35 + U * 0.01) {
    throw new Error(`GrowingFigure: ${n} stage names do not fit under the figure at this aspect — use fewer states.`);
  }
  const railW = side ? Math.round((W - 2 * mx) * 0.36) : W - 2 * mx;
  const railH = rowH * n;
  const fig = side
    ? {x: mx, y: top, w: W - 2 * mx - railW - U * 0.05, h: zoneBot - top - U * 0.02}
    : {x: mx, y: top, w: W - 2 * mx, h: zoneBot - top - railH - U * 0.05};
  const railX = side ? W - mx - railW : mx;
  const railY = side ? fig.y + Math.max(0, (fig.h - railH) / 2) : fig.y + fig.h + U * 0.04;
  // the figure's own square-ish box, centred in its room, with air for the stroke
  // never larger than its room: a figure taller than the box it was given rides up into the heading
  if (Math.min(fig.w, fig.h) < U * 0.15) throw new Error('GrowingFigure: no room for the figure at this aspect.');
  const S = Math.min(fig.w, fig.h) * 0.86;
  // @fallback: a shape with no `count` is drawn once — how many copies, not a reading about the stage
  const anyCount = Math.max(...states.map((s) => (s.d ? 1 : s.count ?? 1)));
  const boxW = Math.min(fig.w * 0.94, S * Math.max(1, Math.min(2.1, anyCount * 0.8)));
  const box = {x: fig.x + (fig.w - boxW) / 2, y: fig.y + (fig.h - S) / 2, w: boxW, h: S};

  const kick = useKinetic({text: kicker || ' ', w: W - 2 * mx, nowrap: true, fit: 'box',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});
  const head = useKinetic({text: title || ' ', w: W - 2 * mx, h: titleH, fit: 'box', maxLines: 2, wrap: 'balance',
    font: {family: DISPLAY, weight: 640, size: TITLE, minSize: Math.ceil(U * 0.036), lineHeight: 1.06, tracking: -0.015}});
  const labW = railW - Math.round(U * 0.09);
  const rowSpec = (i: number) => ({text: i < n ? String(states[i].label) : ' ', w: labW, h: rowH - U * 0.018,
    fit: 'box' as const, maxLines: 2, wrap: 'balance' as const,
    font: {family: BODY, weight: 560, size: ROW, minSize: Math.ceil(U * 0.03), lineHeight: 1.3}});
  const r0 = useKinetic(rowSpec(0)), r1 = useKinetic(rowSpec(1)), r2 = useKinetic(rowSpec(2)), r3 = useKinetic(rowSpec(3));
  const rowK = [r0, r1, r2, r3];
  // @truncates: four row handles exist for at most four states (more throw above) — this drops unused HANDLES, never a state
  const usedRows = rowK.slice(0, n), spareRows = rowK.slice(n);

  // ── the outlines, in frame px ────────────────────────────────────────────────────────────────────────────────
  // @fallback: a shape with no `count` is drawn once — how many copies, not a reading about the stage
  const ds = React.useMemo(() => states.map((s) => (s.d ? fitD(s.d, box) : shapeD(s.shape!, box, s.count ?? 1))),
    [JSON.stringify(states), box.x, box.y, box.w, box.h]);    // eslint-disable-line
  const plans = React.useMemo(() => ds.slice(1).map((d, i) => planMorph(ds[i], d)), [ds]);

  // ── the timeline ─────────────────────────────────────────────────────────────────────────────────────────────
  const drawA = 0.05, drawB = 0.24;
  const endT = 0.9;
  const slot = (endT - drawB) / (n - 1);
  const morph = Array.from({length: n - 1}, (_, i) => [drawB + slot * i + slot * 0.4, drawB + slot * (i + 1)] as [number, number]);
  let stage = 0;
  morph.forEach(([a], i) => { if (t >= a) stage = i + 1; });
  let d = ds[0];
  let pieces: string[] = [ds[0]];
  let ghost: string | null = null, ghostOp = 0;
  let active = 0;                                   // the rail marker's position, in rows (fractional while moving)
  if (stage > 0) {
    const i = stage - 1;
    const p = easeInOutCubic(clamp01(seg(t, morph[i][0], morph[i][1])));
    pieces = morphPieces(plans[i], p);
    d = pieces.join('');
    active = i + p;
    ghost = ds[i];
    // the stage just left lingers through the morph and the next hold, then goes
    const holdEnd = i + 1 < morph.length ? morph[i + 1][0] : 1;
    ghostOp = 0.5 * (1 - clamp01(seg(t, morph[i][1], morph[i][1] + (holdEnd - morph[i][1]) * 0.7)));
  }
  const draw = easeOutCubic(clamp01(seg(t, drawA, drawB)));
  const fillOp = filled ? easeOutCubic(clamp01(seg(t, drawA + 0.08, drawB + 0.04))) : 0;
  // the body: the accent a fifth of the way up from the ground, opaque (see the outline note below)
  const BODY_INK = mix(ACC, BG, 0.8);
  // unique per mount: a seam mounts two beats at once, and two masks with one id mask each other's outline
  const uid = `gf${React.useId().replace(/[^A-Za-z0-9]/g, '')}`;
  const sw = Math.max(2, Math.round(U * 0.0055));
  const markR = Math.round(U * 0.011);
  const rowTop = (i: number) => railY + i * rowH;
  const markY = rowTop(active) + ROW * 0.68;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={mx} y={zoneTop} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.02, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.2}}} />
      ) : kick.anchor}
      {title ? (
        <KineticText k={head} x={mx} y={zoneTop + kickH} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.03}, enter: {by: 'line', at: 0.04, stagger: 0.12,
            dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.24}}} />
      ) : head.anchor}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {/* THE BODY: every piece in one path, so where two overlap the nonzero fill is laid once */}
        {filled ? <path d={d} fill={BODY_INK} opacity={fillOp} stroke="none" /> : null}
        {/* THE OUTLINE OF THE WHOLE, not of its pieces. A split draws the one cell twice over itself, and stroked
            piece by piece the copies' outlines cross inside the body (seen on the first render: two overlapping
            rings, not a cell parting). So each piece's stroke is masked by the interiors of the OTHER pieces: what
            is left is exactly the part of its edge on the outside — the union's outline. */}
        {pieces.map((pd, i) => (
          <React.Fragment key={i}>
            {pieces.length > 1 ? (
              <mask id={`${uid}m${i}`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
                <rect x={0} y={0} width={W} height={H} fill="#ffffff" />
                {pieces.map((qd, j) => (j === i ? null : <path key={j} d={qd} fill="#000000" />))}
              </mask>
            ) : null}
            <path d={pd} fill="none" stroke={ACC} strokeWidth={sw} strokeLinejoin="round" strokeLinecap="round"
              mask={pieces.length > 1 ? `url(#${uid}m${i})` : undefined}
              {...(stage === 0 && draw < 1 ? drawOn(draw) : {})} />
          </React.Fragment>
        ))}
        {/* the stage just left, over the body, so its old outline reads through the new shape */}
        {ghost && ghostOp > 0.01 ? (
          <path d={ghost} fill="none" stroke={mix(ACC, BG, 0.45)} strokeWidth={sw * 0.7} opacity={ghostOp}
            strokeDasharray={`${sw * 2.2} ${sw * 2.6}`} strokeLinejoin="round" />
        ) : null}
        {/* the rail: a spine, and the marker that rides it to the current stage */}
        <path d={`M${railX + markR} ${rowTop(0) + ROW * 0.68}L${railX + markR} ${rowTop(n - 1) + ROW * 0.68}`}
          stroke={mix(DIM, BG, 0.55)} strokeWidth={Math.max(1.5, sw * 0.45)} fill="none"
          {...drawOn(easeOutCubic(clamp01(seg(t, 0.06, 0.26))))} />
        {states.map((_, i) => (
          <circle key={i} cx={railX + markR} cy={rowTop(i) + ROW * 0.68} r={markR * 0.45}
            fill={i <= active + 0.5 ? ACC : mix(DIM, BG, 0.4)} opacity={clamp01(seg(t, 0.08 + i * 0.03, 0.2 + i * 0.03))} />
        ))}
        <circle cx={railX + markR} cy={markY} r={markR} fill="none" stroke={ACC} strokeWidth={Math.max(2, sw * 0.6)}
          opacity={clamp01(seg(t, 0.12, 0.24))} />
      </svg>
      {usedRows.map((k, i) => {
        const on = 1 - Math.min(1, Math.abs(active - i));
        return (
          <KineticText key={i} k={k} x={railX + Math.round(U * 0.06)} y={rowTop(i)} color={on > 0.5 ? FG : DIM}
            id={`state-${i}`} motion={{from: {opacity: 0, x: 0.3}, enter: {by: 'line', at: 0.1 + i * 0.04, stagger: 0.08,
              dur: 0.6, ease: 'power3', cueKeys: [`states.${i}.label`], until: 0.34}}} />
        );
      })}
      {spareRows.map((k, i) => <React.Fragment key={`a${i}`}>{k.anchor}</React.Fragment>)}
    </AbsoluteFill>
  );
};
export default GrowingFigure;
