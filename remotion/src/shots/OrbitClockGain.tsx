// SHOT · OrbitClockGain — why a clock in orbit runs fast, and by how much. On the left, the cause in the world: the
// Earth's pull drawn as contours that thin out with height (far up, it is weak), and the satellite racing round
// its orbit high above them. On the right, the effect on one dial: the ground's clock is the reference hand, the
// orbiting clock its own hand, and the day's offset between them is built from two wedges — a large one forward
// (being far from the Earth makes the clock run fast) and a small one back (moving fast makes it run slow). The
// hand lands where their sum says: net fast. Each cause lights in the world as its wedge sweeps on the dial.
//
// THE ARGUMENT SHAPE: two opposing causes, one net effect, read as signed parts of one offset. The wedges are the
// film's figures drawn to their ratio (the film passes them as turns in proportion to its sourced values), and the
// hand is PLACED by their sum inside OffsetClock, so the picture cannot disagree with its parts. The satellite
// keeps going round for the whole beat; the dial's clock keeps running. Every word is a prop.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, seg, clamp01, lerp, easeOutCubic, radians} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx, fitsBox} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {ObjectSlot, idleSeconds, type ObjectRef} from '../runtime/objectSlot';
import {leading} from '../runtime/cjkType';
import {starField, earthDefs, earthDisc, TYPE} from '../kits/orbitKit';
import {nadirPoint} from '../objects/GpsSatellite';

export const DURATION = 210;

const BG_D0 = '#04060c', FG_D0 = '#e8eef8', ACC_D0 = '#f2c46b', ACC2_D0 = '#5db6ff', DIM_D0 = '#8a96ad';
const SAT_ASPECT = 2.3;
// the dial's own reveal, as a window of this shot's clock — OffsetClock sweeps wedge 1 over 0.40-0.61 of its t and
// wedge 2 over 0.65-0.86; so the causes below light on exactly those stretches
const DIAL_A = 0.06, DIAL_B = 0.7;
const atDial = (u: number) => DIAL_A + (DIAL_B - DIAL_A) * u;

export const OrbitClockGain: React.FC<{
  clock?: ObjectRef;      // the dial (the film's OffsetClock): ground clock as reference, the orbit clock as its hand
  sat?: ObjectRef;        // the satellite (the film's GpsSatellite)
  title?: string;         // the claim, in the title band
  farLabel?: string;      // the first cause: far from the Earth
  farFigure?: string;     // its effect, the film's sourced figure
  fastLabel?: string;     // the second cause: moving fast
  fastFigure?: string;    // its effect, the film's sourced figure
  netLabel?: string;      // the net, set large
  refName?: string;       // the reference hand: the ground's clock
  ownName?: string;       // the dial's own hand: the clock in orbit
  limb?: string;          // the Earth's blue (#hex)
}> = ({clock, sat, title = '', farLabel = '', farFigure = '', fastLabel = '', fastFigure = '', netLabel = '',
  refName = '', ownName = '', limb = ACC2_D0} = {}) => {
  const dna = useDNA();
  const t = useT();
  const cue = useCues();
  const uid = React.useId().replace(/[^A-Za-z0-9]/g, '');
  const {width: W, height: H, fps, durationInFrames} = useVideoConfig();
  const BG = dna?.bg ?? BG_D0, FG = dna?.fg ?? FG_D0, ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const display = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
  const body = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
  const U = Math.min(W, H);
  const portrait = W < H;
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const lw = Math.max(1, U * 0.0018);
  const satRef: ObjectRef = sat ?? {id: 'GpsSatellite', props: {look: 'lit'}};

  // ── the world: the Earth low on the left, its pull as contours thinning with height, the orbit far above ──
  const R = portrait ? W * 0.7 : H * 0.62;
  const E = portrait ? {x: W * 0.3, y: zBot + R * 0.55} : {x: W * 0.12, y: zBot + R * 0.42};
  // the orbit passes through a point in the left sky; the satellite goes round it the whole beat, at one rate
  const satHome = portrait ? {x: W * 0.62, y: zTop + zH * 0.5} : {x: W * 0.28, y: zTop + zH * 0.14};
  const orbitR = Math.hypot(satHome.x - E.x, satHome.y - E.y);
  const ang0 = Math.atan2(satHome.y - E.y, satHome.x - E.x) - 0.16;   // it runs from here through satHome and on, short of the dial
  const ang = ang0 + 0.047 * radians(t, durationInFrames, fps, 6.5);    // steady and quick — the second cause is its speed
  const satP = {x: E.x + Math.cos(ang) * orbitR, y: E.y + Math.sin(ang) * orbitR};
  const satW = W * (portrait ? 0.3 : 0.15), satH = satW / SAT_ASPECT;
  // it keeps broadcasting while it races: shells from its array, each centred where it left, at one speed
  const satAt = (aa: number) => ({x: E.x + Math.cos(aa) * orbitR, y: E.y + Math.sin(aa) * orbitR});
  const tipOff = nadirPoint(satW, satH, (satRef.props ?? {}) as {yaw0?: number; pitch?: number; roll?: number; wingTilt?: number});
  const shellV = Math.hypot(W, H) * 0.9, shellMax = Math.hypot(W, H) * 1.2;
  const shells: {x: number; y: number; r: number}[] = [];
  for (let k = 0; k < 14; k++) {
    const tk = 0.04 + k * 0.08;
    if (t < tk) break;
    const aa = ang0 + 0.047 * radians(tk, durationInFrames, fps, 6.5), c = satAt(aa);
    const r = shellV * (t - tk);
    if (r < shellMax) shells.push({x: c.x - satW / 2 + tipOff.x, y: c.y - satH * 0.9 + tipOff.y, r});
  }
  const inOn = easeOutCubic(clamp01(seg(t, 0, 0.12)));
  // the two causes light as their wedges sweep
  const farLit = clamp01(seg(t, atDial(0.38), atDial(0.5))) * (1 - 0.45 * clamp01(seg(t, atDial(0.66), atDial(0.8))));
  const fastLit = clamp01(seg(t, atDial(0.62), atDial(0.74)));

  // ── the dial, large, on the right ──
  const dS = portrait ? W * 0.9 : zH * 0.94;
  const dC = portrait ? {x: W * 0.5, y: zTop + zH * 0.3} : {x: W * 0.585, y: zTop + zH * 0.48};
  const Rd = dS * 0.36;                                              // OffsetClock's own dial radius in its box
  // where the two wedges sit on the dial (for the leaders): OffsetClock lays them from the reference, outer band first
  const wedgeTurns = ((clock?.props as {wedges?: {turns: number}[]} | undefined)?.wedges ?? []).map((w) => w.turns);
  // the clocks keep running once the wedges are in: the dial turns its hands and wedges together (OffsetClock `run`),
  // so the leaders follow their wedges round on the same idle clock the slot hands the dial
  const span = useAnimSpan();
  const runRate = Number((clock?.props as {run?: number} | undefined)?.run ?? 0);
  const refTurn = Number((clock?.props as {against?: number} | undefined)?.against ?? 0) + runRate * idleSeconds(t, DIAL_B + 0.02, span, fps);
  const onDial = (turns: number, r: number) => ({x: dC.x + r * Math.sin(turns * 2 * Math.PI), y: dC.y - r * Math.cos(turns * 2 * Math.PI)});
  const w1mid = wedgeTurns.length > 0 ? onDial(refTurn + wedgeTurns[0] / 2, Rd * 0.86) : null;
  const w2mid = wedgeTurns.length > 1 ? onDial(refTurn + wedgeTurns[0] + wedgeTurns[1] / 2, Rd * 0.72) : null;

  // ── words ──
  const titleOn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.02, 0.14, REACH_CUBIC))));
  const farOn = easeOutCubic(clamp01(seg(t, ...cue.win('farLabel', atDial(0.38), atDial(0.5), REACH_CUBIC))));
  const farFigOn = easeOutCubic(clamp01(seg(t, ...cue.win('farFigure', atDial(0.5), atDial(0.6), REACH_CUBIC))));
  const fastOn = easeOutCubic(clamp01(seg(t, ...cue.win('fastLabel', atDial(0.62), atDial(0.72), REACH_CUBIC))));
  const fastFigOn = easeOutCubic(clamp01(seg(t, ...cue.win('fastFigure', atDial(0.74), atDial(0.84), REACH_CUBIC))));
  const netOn = easeOutCubic(clamp01(seg(t, ...cue.win('netLabel', atDial(0.88), atDial(0.88) + 0.08, REACH_CUBIC))));
  const refOn = easeOutCubic(clamp01(seg(t, ...cue.win('refName', 0.16, 0.28, REACH_CUBIC))));
  const ownOn = easeOutCubic(clamp01(seg(t, ...cue.win('ownName', 0.22, 0.34, REACH_CUBIC))));
  const titlePx = title ? fitTextPx(title, W * (portrait ? 0.84 : 0.42), Math.round(U * TYPE.title), {usable: 1}) : 0;
  const labPx = Math.round(U * TYPE.label), figPx = Math.round(U * 0.05), legPx = Math.round(U * TYPE.note);
  const netPx = netLabel ? fitTextPx(netLabel, W * (portrait ? 0.84 : 0.36), Math.round(U * 0.075), {usable: 1}) : 0;
  // the causes stand to the right of the dial, beside the quadrant their wedges sweep
  const colX = portrait ? W * 0.08 : dC.x + Rd + W * 0.025, colW = portrait ? W * 0.84 : W * 0.975 - (dC.x + Rd + W * 0.025);
  const farY = portrait ? zTop + zH * 0.62 : zTop + zH * 0.04, fastY = portrait ? zTop + zH * 0.74 : zTop + zH * 0.3;
  const stars = starField(W, H, 160, FG, inOn, U, (x, y) => Math.hypot(x - E.x, y - E.y) < R * 1.02);

  // the pull's contours: closer together near the surface, wider and fainter with height
  const contours = Array.from({length: 7}, (_, k) => R * (1.07 + 0.11 * k + 0.035 * k * k));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          {earthDefs(uid, E, R, limb, BG)}
          <linearGradient id={`${uid}band`} x1={0} y1={0} x2={0} y2={H} gradientUnits="userSpaceOnUse">
            <stop offset={(zBot - U * 0.05) / H} stopColor="#fff" stopOpacity={1} />
            <stop offset={Math.min(1, (zBot + U * 0.05) / H)} stopColor="#fff" stopOpacity={0.12} />
            <stop offset={1} stopColor="#fff" stopOpacity={0.08} />
          </linearGradient>
          <mask id={`${uid}m`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
            <rect x={0} y={0} width={W} height={H} fill={`url(#${uid}band)`} />
          </mask>
          <filter id={`${uid}soft`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation={U * 0.006} /></filter>
        </defs>
        {stars}
        <g mask={`url(#${uid}m)`}>
          {/* the Earth's pull: strong near the ground, weak far up — it lights while that cause is on the dial */}
          {contours.map((r, k) => (
            <circle key={k} cx={E.x} cy={E.y} r={r} fill="none" stroke={limb} strokeWidth={lw * (1.6 - k * 0.15)}
              opacity={(0.32 - k * 0.035) * inOn + 0.4 * farLit * (1 - k / 8)} />
          ))}
          {/* the orbit, far above the contours */}
          {shells.map((sh, i) => (
            <circle key={`sh${i}`} cx={sh.x} cy={sh.y} r={sh.r} fill="none" stroke={ACC} strokeWidth={lw * 1.4}
              opacity={0.34 * (1 - sh.r / shellMax) * inOn} />
          ))}
          {/* the orbit: its marks stream along with the satellite, so the speed is on the frame even where it is not */}
          <circle cx={E.x} cy={E.y} r={orbitR} fill="none" stroke={FG} strokeWidth={lw * 1.2} strokeDasharray={`${lw * 3} ${lw * 6}`}
            strokeDashoffset={-(ang - ang0) * orbitR} opacity={0.4 * inOn} />
          {/* moving fast: streaks behind the satellite along its orbit — they light while that cause is on the dial */}
          {Array.from({length: 5}, (_, k) => {
            const a1 = ang - 0.012 - k * 0.006, a0 = a1 - 0.11 - k * 0.02;
            const r = orbitR + (k - 2) * U * 0.012;
            const p0 = {x: E.x + Math.cos(a0) * r, y: E.y + Math.sin(a0) * r}, p1 = {x: E.x + Math.cos(a1) * r, y: E.y + Math.sin(a1) * r};
            return <path key={`k${k}`} d={`M${p0.x} ${p0.y} A${r} ${r} 0 0 1 ${p1.x} ${p1.y}`} fill="none" stroke={ACC2}
              strokeWidth={lw * 2} strokeLinecap="round" opacity={(0.25 + 0.6 * fastLit) * inOn * (1 - k * 0.12)} />;
          })}
        </g>
        {earthDisc(uid, E, R, limb, lw, inOn)}
        {/* leaders from each cause to its wedge on the dial */}
        {w1mid ? <path d={`M${colX - U * 0.01} ${farY + labPx * 0.7} L${w1mid.x} ${w1mid.y}`} stroke={ACC} strokeWidth={lw}
          strokeDasharray={`${lw * 3} ${lw * 3}`} fill="none" opacity={0.75 * farOn} /> : null}
        {w2mid ? <path d={`M${colX - U * 0.01} ${fastY + labPx * 0.7} L${w2mid.x} ${w2mid.y}`} stroke={ACC2} strokeWidth={lw}
          strokeDasharray={`${lw * 3} ${lw * 3}`} fill="none" opacity={0.75 * fastOn} /> : null}
        {/* the dial's legend: which hand is which */}
        <g opacity={refOn}>
          <line x1={dC.x - Rd * 0.9} y1={dC.y + Rd + U * 0.07} x2={dC.x - Rd * 0.72} y2={dC.y + Rd + U * 0.07} stroke={ACC2}
            strokeWidth={lw * 1.6} strokeDasharray={`${lw * 4} ${lw * 3}`} />
        </g>
        <g opacity={ownOn}>
          <line x1={dC.x + Rd * 0.05} y1={dC.y + Rd + U * 0.07} x2={dC.x + Rd * 0.23} y2={dC.y + Rd + U * 0.07} stroke={ACC}
            strokeWidth={lw * 4} strokeLinecap="round" />
        </g>
      </svg>

      <ObjectSlot object={satRef} box={{x: satP.x - satW / 2, y: satP.y - satH / 2, w: satW, h: satH}} t={clamp01(seg(t, 0, 0.16))} />
      {clock ? <ObjectSlot object={clock} box={{x: dC.x - dS / 2, y: dC.y - dS / 2, w: dS, h: dS}}
        t={clamp01(seg(t, DIAL_A, DIAL_B))} idleFrom={DIAL_B + 0.02} /> : null}

      {title ? (
        <div style={{position: 'absolute', left: portrait ? W * 0.08 : W * 0.04, top: (portrait ? zTop + zH * 0.86 : zTop + zH * 0.6) - titlePx * 1.35,
          color: FG, opacity: titleOn, font: `700 ${titlePx}px/1.2 ${display}`, whiteSpace: 'nowrap',
          textShadow: `0 0 ${U * 0.02}px ${BG}`}}>{title}</div>
      ) : null}
      {farLabel && fitsBox(farLabel, labPx, colW, labPx * 3) ? (
        <div style={{position: 'absolute', left: colX, width: colW, top: farY, color: ACC,
          font: `600 ${labPx}px/${leading(farLabel, 1.35)} ${body}`, opacity: farOn}}>{farLabel}</div>
      ) : null}
      {farFigure && fitsBox(farFigure, figPx, colW, figPx * 1.5) ? (
        <div style={{position: 'absolute', left: colX, width: colW, top: farY + labPx * 1.6, color: ACC,
          font: `700 ${figPx}px/1.2 ${display}`, whiteSpace: 'nowrap', opacity: farFigOn}}>{farFigure}</div>
      ) : null}
      {fastLabel && fitsBox(fastLabel, labPx, colW, labPx * 3) ? (
        <div style={{position: 'absolute', left: colX, width: colW, top: fastY, color: ACC2,
          font: `600 ${labPx}px/${leading(fastLabel, 1.35)} ${body}`, opacity: fastOn}}>{fastLabel}</div>
      ) : null}
      {fastFigure && fitsBox(fastFigure, figPx, colW, figPx * 1.5) ? (
        <div style={{position: 'absolute', left: colX, width: colW, top: fastY + labPx * 1.6, color: ACC2,
          font: `700 ${figPx}px/1.2 ${display}`, whiteSpace: 'nowrap', opacity: fastFigOn}}>{fastFigure}</div>
      ) : null}
      {netLabel ? (
        <div style={{position: 'absolute', left: portrait ? W * 0.08 : W * 0.04, top: portrait ? zTop + zH * 0.86 : zTop + zH * 0.6,
          color: FG, opacity: netOn, font: `800 ${netPx}px/1.15 ${display}`, whiteSpace: 'nowrap',
          textShadow: `0 0 ${U * 0.03}px ${mix(ACC, BG, 0.5)}`}}>{netLabel}</div>
      ) : null}
      {refName && fitsBox(refName, legPx, Rd * 0.9, legPx * 1.5) ? (
        <div style={{position: 'absolute', left: dC.x - Rd * 0.68, width: Rd * 0.9, top: dC.y + Rd + U * 0.07 - legPx * 0.65, color: DIM,
          font: `500 ${legPx}px/1.2 ${body}`, whiteSpace: 'nowrap', opacity: refOn}}>{refName}</div>
      ) : null}
      {ownName && fitsBox(ownName, legPx, Rd * 0.9, legPx * 1.5) ? (
        <div style={{position: 'absolute', left: dC.x + Rd * 0.27, width: Rd * 0.9, top: dC.y + Rd + U * 0.07 - legPx * 0.65, color: DIM,
          font: `500 ${legPx}px/1.2 ${body}`, whiteSpace: 'nowrap', opacity: ownOn}}>{ownName}</div>
      ) : null}
    </AbsoluteFill>
  );
};
