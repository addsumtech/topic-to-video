// SHOT · ExtractionFlow — one setting set two to four ways, side by side, all started at the same instant: each
// column is the same thing the film drew (an OBJECT, in the case's own state), the stream it lets through, the
// vessel that stream fills, a time bar on a scale every column shares, and where the result lands on a scale
// between two named ends. The slow column is still running when the fast one has finished; when each one finishes,
// its time and its verdict appear.
//
// THE ARGUMENT SHAPE: "one setting decides how long it takes, and how long it takes decides the result" — any
// rate that sets an outcome: a grind and its extraction, a dose and its time to effect, a filter and its
// throughput. It was built for an espresso, where the puck's resistance is the setting: a coarse grind runs fast
// and thin, a fine one slow and dark, the one in between lands in the middle.
//
// `pace` is each case's duration relative to the slowest (a drawing ratio, not a measurement — the film writes the
// one real figure it has into that case's `time`); `lean` is where its result sits between `lowLabel` and
// `highLabel`, and also how strong its output is drawn (toward the film's pale end at 0, its deep end at 1, on
// either ground). Every word is a prop; with none, nothing is written. Content stays inside the content zone.
// Standalone it shows its own preview: three of the stages' wordless form, one setting stepped across them.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, lerp, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';
import {paleEnd, deepEnd} from '../runtime/light';
import {rows} from '../runtime/rows';
import {ObjectSlot, useObjectEntry, type ObjectRef} from '../runtime/objectSlot';

export const DURATION = 300;
export const REQUIRED_IN_FILM = ['object', 'cases'] as const;
export const MIN_CASES = 2, MAX_CASES = 4;

type Case = {label?: string; props?: Record<string, unknown>; pace?: number; lean?: number; time?: string;
  verdict?: string; target?: boolean};

const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8', LINE_D0 = '#d3d8df';
const PREVIEW: ObjectRef = {id: 'DemoForm'};                 // the stages' wordless preview form, standalone only
// the preview steps ONE setting of that form across the cases, so it shows the shape it argues
const PREVIEW_CASES: Case[] = [{pace: 0.35, lean: 0.1, props: {layers: 2}},
  {pace: 0.65, lean: 0.5, target: true, props: {layers: 3}}, {pace: 1, lean: 0.9, props: {layers: 4}}];
const START = 0.12;      // every column starts here, at once
const SPAN = 0.62;       // the slowest case (pace 1) finishes at START + SPAN
const SETTLE = 0.2;      // the share of an object's own clock spent before the water starts

export const ExtractionFlow: React.FC<{
  object?: ObjectRef;     // the thing in every column (runtime/objectSlot); each case's `props` are merged over its own
  cases?: Case[];         // 2-4 columns, left to right: label, the object's props, pace, lean, time, verdict, target
  lowLabel?: string;      // the result scale's low end
  highLabel?: string;     // the result scale's high end
  title?: string;         // the claim, in the title band
  kicker?: string;        // a small spaced label above the title
}> = ({object: OBJECT = PREVIEW, cases: CASES_IN = PREVIEW_CASES, lowLabel = '', highLabel = '', title = '',
  kicker = ''} = {}) => {
  const CASES = rows<Case>(CASES_IN, 'cases', 'ExtractionFlow');
  const n = CASES.length;
  if (n < MIN_CASES || n > MAX_CASES) {
    throw new Error(`ExtractionFlow takes ${MIN_CASES}-${MAX_CASES} \`cases\` — got ${n}`);
  }
  CASES.forEach((c, i) => {
    if (!(typeof c.pace === 'number' && c.pace > 0.05 && c.pace <= 1)) {
      throw new Error(`ExtractionFlow: cases[${i}].pace is its duration relative to the slowest, (0.05, 1] — got ` +
        `${JSON.stringify(c.pace)}`);
    }
    if (!(typeof c.lean === 'number' && c.lean >= 0 && c.lean <= 1)) {
      throw new Error(`ExtractionFlow: cases[${i}].lean is where its result sits between the two ends, 0..1 — got ` +
        `${JSON.stringify(c.lean)}`);
    }
  });
  useObjectEntry(OBJECT);                                   // refuses an unknown or malformed object before drawing
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bg ?? BG_D0, FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const portrait = W < H;

  // ── the grid: one column per case ──
  const x0 = W * (portrait ? 0.04 : 0.07), x1 = W * (portrait ? 0.96 : 0.93);
  const cw = (x1 - x0) / n;
  const cx = (i: number) => x0 + cw * (i + 0.5);
  const labelPx = Math.round(U * 0.03), timePx = Math.round(U * 0.026), verdictPx = Math.round(U * 0.03);
  const endPx = Math.round(U * 0.022);
  const s = Math.max(U * 0.08, Math.min(cw * (portrait ? 0.82 : 0.6), zH * 0.38));   // the object's square
  const yPuck = zTop + labelPx * 1.7;
  const cupW = s * 0.46, cupH = s * 0.3;
  const yCup = yPuck + s + zH * 0.045;
  const barMax = cw * 0.78, barH = Math.max(6, U * 0.011);
  const yBar = yCup + cupH + zH * 0.05;
  const yTime = yBar + barH + U * 0.012;
  const yVerdict = yTime + timePx * 1.5 + zH * 0.018;
  const yScale = Math.min(zBot - endPx * 1.2, yVerdict + verdictPx * 1.5 + zH * 0.04);
  const scaleW = cw * 0.5;
  const kickerPx = Math.round(U * 0.02);
  const titlePx = title ? fitTextPx(title, W * 0.84, Math.round(U * 0.05), {usable: 1}) : 0;
  const titleIn = easeOutCubic(clamp01(seg(t, 0.02, 0.14)));
  const gridIn = easeOutCubic(clamp01(seg(t, 0.03, 0.12)));
  // the film's own pale and deep ends, whichever its ground is: on a dark film the pale end is its ink, on a paper
  // one its ground — reading `fg` as "pale" would draw a strong result weak on paper
  const PALE = paleEnd(dna, BG_D0), DEEP = deepEnd(dna, FG_D0);
  const pale = mix(ACC, PALE, 0.35), dark = mix(ACC, DEEP, 0.82);
  const china = mix(PALE, DEEP, 0.08);
  const fit = (text: string | undefined, px: number, maxW: number) =>
    (text ? fitTextPx(text, maxW, px, {usable: 1}) : 0);

  const cols = CASES.map((c, i) => {
    const pace = c.pace as number, lean = c.lean as number;
    const end = START + SPAN * pace;
    // the object's own clock: everyone settles together, then each runs its water at its own pace
    const tObj = t < START ? SETTLE * seg(t, 0, START) : SETTLE + (1 - SETTLE) * clamp01(seg(t, START, end));
    const fillCup = clamp01(seg(tObj, 0.84, 1));
    const elapsed = clamp01((Math.min(t, end) - START) / SPAN);
    const done = easeOutCubic(clamp01(seg(t, end, end + 0.06)));
    const brew = mix(pale, dark, lean);
    const ink = c.target ? ACC : FG;
    const ref: ObjectRef = {id: OBJECT.id, props: {...(OBJECT.props ?? {}), ...(c.props ?? {})}};
    const flowW = lerp(U * 0.013, U * 0.004, pace);           // a fast case pours a thick stream, a slow one a thread
    const streaming = clamp01(seg(tObj, 0.86, 0.9));
    const level = yCup + cupH - (cupH * 0.82) * fillCup;
    const lx = cx(i) - cupW / 2, rx = cx(i) + cupW / 2;
    const cup = `M${lx} ${yCup} L${rx} ${yCup} L${rx - cupW * 0.08} ${yCup + cupH} L${lx + cupW * 0.08} ${yCup + cupH} Z`;
    const clip = `ef-cup-${i}`;
    const barX = cx(i) - barMax / 2;
    return (
      <React.Fragment key={i}>
        {c.target ? (
          <div style={{position: 'absolute', left: cx(i) - cw * 0.47, top: zTop, width: cw * 0.94,
            height: Math.min(zBot, yScale + endPx * 1.6) - zTop, borderRadius: dna?.radius ?? 6,
            background: mix(BG, FG, 0.045), border: `1px solid ${mix(BG, ACC, 0.35)}`, opacity: gridIn}} />
        ) : null}
        {c.label ? (
          <div style={{position: 'absolute', left: cx(i) - cw * 0.45, width: cw * 0.9, top: zTop + U * 0.004,
            textAlign: 'center', font: `700 ${fit(c.label, labelPx, cw * 0.9)}px/1.25 ${bodyF}`, color: ink,
            opacity: gridIn}}>{c.label}</div>
        ) : null}
        <ObjectSlot object={ref} box={{x: cx(i) - s / 2, y: yPuck, w: s, h: s}} t={tObj} />
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <defs><clipPath id={clip}><path d={cup} /></clipPath></defs>
          {streaming > 0 ? (
            <line x1={cx(i)} y1={yPuck + s} x2={cx(i)} y2={lerp(yPuck + s, level, streaming)} stroke={brew}
              strokeWidth={flowW} strokeLinecap="round" />
          ) : null}
          <path d={cup} fill={china} opacity={gridIn} />
          <g clipPath={`url(#${clip})`}>
            <rect x={lx} y={level} width={cupW} height={yCup + cupH - level + 1} fill={brew} />
          </g>
          <path d={cup} fill="none" stroke={mix(FG, BG, 0.25)} strokeWidth={Math.max(1.5, U * 0.003)}
            strokeLinejoin="round" opacity={gridIn} />
          {/* the shared time scale: a faint track the full width of the slowest case, the bar as long as this one ran */}
          <rect x={barX} y={yBar} width={barMax} height={barH} rx={barH / 2} fill={LINE} opacity={gridIn} />
          {elapsed > 0 ? (
            <rect x={barX} y={yBar} width={Math.max(barH, barMax * elapsed)} height={barH} rx={barH / 2}
              fill={c.target ? ACC : mix(FG, BG, 0.3)} />
          ) : null}
          {/* the result scale: a line between the two named ends, a tick at its middle, a dot where this lands */}
          <line x1={cx(i) - scaleW / 2} y1={yScale} x2={cx(i) + scaleW / 2} y2={yScale} stroke={DIM}
            strokeWidth={Math.max(1.5, U * 0.003)} opacity={gridIn} />
          <line x1={cx(i)} y1={yScale - U * 0.008} x2={cx(i)} y2={yScale + U * 0.008} stroke={DIM}
            strokeWidth={Math.max(1.5, U * 0.003)} opacity={gridIn} />
          <circle cx={cx(i) - scaleW / 2 + scaleW * lean} cy={yScale} r={U * 0.011} fill={ink} opacity={done} />
        </svg>
        {c.time ? (
          <div style={{position: 'absolute', left: barX, width: barMax, top: yTime, textAlign: 'center',
            font: `600 ${fit(c.time, timePx, barMax)}px/1.2 ${bodyF}`, color: ink, opacity: done}}>{c.time}</div>
        ) : null}
        {c.verdict ? (
          <div style={{position: 'absolute', left: cx(i) - cw * 0.45, width: cw * 0.9, top: yVerdict,
            textAlign: 'center', font: `700 ${fit(c.verdict, verdictPx, cw * 0.9)}px/1.25 ${disp}`, color: ink,
            opacity: done}}>{c.verdict}</div>
        ) : null}
        {lowLabel ? (
          <div style={{position: 'absolute', left: cx(i) - scaleW / 2 - cw * 0.2, width: cw * 0.2 - U * 0.012,
            top: yScale - endPx * 0.62, textAlign: 'right',
            font: `600 ${fit(lowLabel, endPx, cw * 0.2 - U * 0.012)}px/1.2 ${bodyF}`, color: DIM,
            opacity: gridIn}}>{lowLabel}</div>
        ) : null}
        {highLabel ? (
          <div style={{position: 'absolute', left: cx(i) + scaleW / 2 + U * 0.012, width: cw * 0.2 - U * 0.012,
            top: yScale - endPx * 0.62, textAlign: 'left',
            font: `600 ${fit(highLabel, endPx, cw * 0.2 - U * 0.012)}px/1.2 ${bodyF}`, color: DIM,
            opacity: gridIn}}>{highLabel}</div>
        ) : null}
      </React.Fragment>
    );
  });

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y - kickerPx * 1.9, textAlign: 'center',
          font: `600 ${kickerPx}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          opacity: titleIn}}>{kicker}</div>
      ) : null}
      {title ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
          font: `700 ${titlePx}px/1.15 ${disp}`, color: FG, opacity: titleIn}}>{title}</div>
      ) : null}
      {cols}
    </AbsoluteFill>
  );
};
