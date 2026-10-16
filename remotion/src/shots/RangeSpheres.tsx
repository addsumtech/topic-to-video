// SHOT · RangeSpheres — where several measured ranges agree. Satellites in the black sky over Earth's limb each
// swing a range sphere (drawn as its circle); the fix is where they meet. Two modes of that one argument shape:
//
//   mode 'two'  — THREE ranges, measured with a perfect clock: three spheres meet in exactly two points. The
//     drawing is made true by construction, not by placement: the satellites stand on one line L, the fix P sits
//     on the Earth, the second point Q is P mirrored across L, and every circle's radius is that satellite's
//     distance to P — so all three pass through P and Q exactly, at every frame. As the satellites move on
//     between measurements (the idle clock tilts L a few degrees), P stays put on the ground while Q swings far
//     through space: the source's own point that "the other moves rapidly in successive measurements".
//   mode 'bias' — FOUR ranges read on the phone's own clock: each leg is ruled in equal ticks of flight time
//     and every measured radius overshoots its true one by the SAME bracket — the phone's clock error, in the
//     ground's blue — so the four arcs miss one another. Taken off all four together (the fourth unknown,
//     solved), they close on one point. The uncorrected arcs stay as dotted ghosts, so the settled frame still
//     shows what was corrected. Afterwards each satellite keeps broadcasting: a bead runs down every leg.
//
// Restyled into this film's orbit-light direction from the star-plate direction's RangeArcPlate (its argument
// kept, its plate and engraving dropped). The satellites are the film's object, passed in as `sat`; their poses
// vary a little by position only so a row of them does not read as one sprite copied. Every word is a prop.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, seg, clamp01, lerp, easeOutCubic, easeInOutCubic, easeOutBack, cadence} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx, fitsBox} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {ObjectSlot, idleSeconds, type ObjectRef} from '../runtime/objectSlot';
import {leading} from '../runtime/cjkType';
import {starField, earthDefs, earthDisc, phoneGlyph, TYPE} from '../kits/orbitKit';

export const DURATION = 180;

const BG_D0 = '#04060c', FG_D0 = '#e8eef8', ACC_D0 = '#f2c46b', ACC2_D0 = '#5db6ff', DIM_D0 = '#8a96ad';
const SAT_ASPECT = 2.3;

export const RangeSpheres: React.FC<{
  sat?: ObjectRef;         // the satellites (the film's GpsSatellite); its props carry look and base pose
  mode?: 'bias' | 'two';   // the default first: the library sweep measures the first mode a type lists
  title?: string;          // the claim, in the title band
  kicker?: string;         // a premise or a note, under the title
  sats?: string[];         // the satellites' names, in order — at most 3 ('two') or 4 ('bias'); fewer leave the rest unnamed
  points?: [string, string]; // 'two': the two crossings' names — the one on the ground first, then the one in space
  rangeLabel?: string;     // 'bias': what a leg measures (flight time × light speed)
  biasLabel?: string;      // 'bias': what the shared bracket is (the phone's clock error)
  here?: string;           // 'bias': what is solved at the fix
  bias?: number;           // 'bias': the shared bracket, as a fraction of the content zone's height — a drawing ratio
  limb?: string;           // the atmosphere's blue at Earth's limb (#hex)
}> = ({sat, mode = 'bias', title = '', kicker = '', sats: satsIn = [], points: pointsIn = [], rangeLabel = '',
  biasLabel = '', here = '', bias: biasIn = 0.07, limb = ACC2_D0} = {}) => {
  if (mode !== 'two' && mode !== 'bias') throw new Error(`RangeSpheres: \`mode\` is 'two' or 'bias' — got ${JSON.stringify(mode)}`);
  const N = mode === 'two' ? 3 : 4;
  // FEWER IS FINE, MORE IS REFUSED. The film that built this demanded exactly N names, and the library's measuring
  // sweep feeds a generic list — so promotion stopped at prop_reach. Fewer names leave the last satellites
  // unnamed, which drops nothing the film gave; a name past the satellites drawn would vanish in silence, so it
  // throws with the maximum (the content contract's rule). The bracket is clamped into its drawable range.
  const sats = Array.isArray(satsIn) ? satsIn : [];
  const points = Array.isArray(pointsIn) ? pointsIn : [];
  if (sats.length > N) throw new Error(`RangeSpheres draws ${N} satellites in mode '${mode}' — got ${sats.length} ` +
    `\`sats\`; name at most ${N}`);
  if (points.length > 2) throw new Error(`RangeSpheres marks two crossings — got ${points.length} \`points\``);
  const bias = typeof biasIn === 'number' && isFinite(biasIn) ? Math.min(0.2, Math.max(0.01, biasIn)) : 0.07;
  const dna = useDNA();
  const t = useT();
  const cue = useCues();
  const span = useAnimSpan();
  const uid = React.useId().replace(/[^A-Za-z0-9]/g, '');
  const {width: W, height: H, fps, durationInFrames} = useVideoConfig();
  const BG = dna?.bg ?? BG_D0, FG = dna?.fg ?? FG_D0, ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const sans = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
  const body = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
  const U = Math.min(W, H);
  const portrait = W < H;
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const lw = Math.max(1, U * 0.0018);
  const satRef: ObjectRef = sat ?? {id: 'GpsSatellite', props: {look: 'lit'}};
  const base = (satRef.props ?? {}) as {yaw0?: number; pitch?: number; roll?: number; wingTilt?: number};

  // ── the Earth: a wide limb across the foot of the frame; the fix stands on it ──
  const R = Math.max(W, H) * 2.1;
  const limbTop = zBot - zH * (portrait ? 0.14 : 0.12);
  const E = {x: W / 2, y: limbTop + R};
  const limbY = (x: number) => E.y - Math.sqrt(Math.max(0, R * R - (x - E.x) ** 2));
  const P = {x: W * 0.5, y: limbY(W * 0.5)};
  const earthIn = easeOutCubic(clamp01(seg(t, 0, 0.16)));

  // the idle clock: seconds since the construction settled — the satellites move on between measurements
  const settleAt = mode === 'two' ? 0.62 : 0.86;
  const idle = idleSeconds(t, settleAt, span, fps);

  // ── the satellites ──
  const satW = portrait ? W * 0.34 : W * (mode === 'two' ? 0.2 : 0.17), satH = satW / SAT_ASPECT;
  // where a satellite's range starts: its antenna array, at the bottom-centre of its box
  const NADIR = satH * 0.34;
  let foot: {x: number; y: number}[];
  let Q: {x: number; y: number} | null = null;
  if (mode === 'two') {
    // the ranges' CENTRES (the antenna arrays) stand on one line L through C0 at angle phi; Q = P mirrored
    // across L, so every circle through P passes through Q as well — exactly, at every frame
    const C0 = {x: W * 0.5, y: zTop + zH * (portrait ? 0.46 : 0.5)};
    const phi = 0.07 * Math.sin((idle / 5.2) * 2 * Math.PI);      // a few degrees, a slow swing
    const dir = {x: Math.cos(phi), y: Math.sin(phi)};
    const along = portrait ? [-0.36, 0, 0.36] : [-0.32, 0, 0.32];
    foot = along.map((a) => ({x: C0.x + dir.x * a * W, y: C0.y + dir.y * a * W}));
    const d = (P.x - C0.x) * dir.x + (P.y - C0.y) * dir.y;
    const proj = {x: C0.x + dir.x * d, y: C0.y + dir.y * d};
    Q = {x: 2 * proj.x - P.x, y: 2 * proj.y - P.y};
  } else {
    // @positional: four stations spread across the sky, left to right — layout, not a reading about any one
    const pos = portrait ? [[0.22, 0.12], [0.72, 0.06], [0.28, 0.4], [0.78, 0.34]] : [[0.12, 0.24], [0.33, 0.08], [0.67, 0.1], [0.88, 0.26]];
    foot = pos.map(([fx, fy]) => ({x: W * fx, y: zTop + zH * fy + satH * 0.5 + NADIR}));
  }
  const S = foot.map((f) => ({x: f.x, y: f.y - NADIR}));

  // ── ranges ──
  const B = zH * bias;
  const corr = mode === 'bias' ? easeInOutCubic(clamp01(seg(t, 0.62, 0.8))) : 1;
  const ranges = foot.map((f, i) => {
    const dx = P.x - f.x, dy = P.y - f.y;
    const r = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
    const [a, b] = mode === 'two' ? [0.2 + i * 0.09, 0.38 + i * 0.09] : [0.3 + i * 0.07, 0.44 + i * 0.07];
    const swing = easeOutCubic(cadence(clamp01(seg(t, a, b)), 3));    // a range is swung out in three steps
    return {f, r, ang, swing, i};
  });
  const arcPath = (cx: number, cy: number, r: number, a0: number, a1: number) => {
    const p0 = {x: cx + r * Math.cos(a0), y: cy + r * Math.sin(a0)};
    const p1 = {x: cx + r * Math.cos(a1), y: cy + r * Math.sin(a1)};
    const large = Math.abs(a1 - a0) > Math.PI ? 1 : 0;
    return `M${p0.x.toFixed(1)} ${p0.y.toFixed(1)} A${r.toFixed(1)} ${r.toFixed(1)} 0 ${large} 1 ${p1.x.toFixed(1)} ${p1.y.toFixed(1)}`;
  };
  const fixIn = easeOutBack(clamp01(seg(t, mode === 'two' ? 0.5 : 0.78, mode === 'two' ? 0.62 : 0.88)));
  const qIn = mode === 'two' ? easeOutBack(clamp01(seg(t, 0.54, 0.66))) : 0;

  // ── words ──
  const titlePx = title ? fitTextPx(title, W * (portrait ? 0.84 : 0.5), Math.round(U * TYPE.title), {usable: 1}) : 0;
  const kickPx = Math.round(U * TYPE.note), labPx = Math.round(U * TYPE.label);
  // the title's place follows the frame: 'two' keeps the upper left clear for the circles and sets it right;
  // 'bias' sets it centred, between the second and third satellites
  const centred = mode === 'bias' && !portrait;
  const titleOn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.02, 0.16, REACH_CUBIC))));
  const kickOn = easeOutCubic(clamp01(seg(t, ...cue.win('kicker', 0.06, 0.2, REACH_CUBIC))));
  const rangeOn = easeOutCubic(clamp01(seg(t, ...cue.win('rangeLabel', 0.36, 0.5, REACH_CUBIC))));
  const biasOn = easeOutCubic(clamp01(seg(t, ...cue.win('biasLabel', 0.5, 0.62, REACH_CUBIC))));
  const hereOn = easeOutCubic(clamp01(seg(t, ...cue.win('here', 0.8, 0.9, REACH_CUBIC))));
  const lh = (s: string) => leading(s, 1.3);
  // the range label rides the second leg (the steep one), set to its left; the bias note sits in the clear sky
  // under the first leg; the solution sits under the fix, on the ground
  const legR = ranges[Math.min(1, ranges.length - 1)];
  const midLeg = {x: lerp(legR.f.x, P.x, 0.5), y: lerp(legR.f.y, P.y, 0.5)};

  const stars = starField(W, H, 150, FG, earthIn, U, (x, y) => Math.hypot(x - E.x, y - E.y) < R * 1.01);
  // ('bias') every satellite broadcasts the whole time: faint shells from each array, each on its own beat — an arc
  // on the frame is exactly where one of these shells is when it reaches the phone
  const shellMax = Math.hypot(W, H) * 0.9;
  const shells: {x: number; y: number; r: number}[] = [];
  const secs = t * durationInFrames / fps;
  if (mode === 'bias') {
    foot.forEach((f, i) => {
      for (let k = 0; k < 10; k++) {
        const r = (secs - 0.3 - k * 0.6 - i * 0.15) * Math.hypot(W, H) * 0.42;
        if (r > 0 && r < shellMax) shells.push({x: f.x, y: f.y, r});
      }
    });
  }
  const tickLen = U * 0.008;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          {earthDefs(uid, E, R, limb, BG, {x: 0, y: -1})}
          <linearGradient id={`${uid}band`} x1={0} y1={0} x2={0} y2={H} gradientUnits="userSpaceOnUse">
            <stop offset={(zBot - U * 0.04) / H} stopColor="#fff" stopOpacity={1} />
            <stop offset={Math.min(1, (zBot + U * 0.06) / H)} stopColor="#fff" stopOpacity={0.1} />
            <stop offset={1} stopColor="#fff" stopOpacity={0.06} />
          </linearGradient>
          <mask id={`${uid}m`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
            <rect x={0} y={0} width={W} height={H} fill={`url(#${uid}band)`} />
          </mask>
          <filter id={`${uid}soft`} x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation={U * 0.005} /></filter>
        </defs>
        {stars}
        {earthDisc(uid, E, R, limb, lw, earthIn)}
        <g mask={`url(#${uid}m)`}>
          {shells.map((sh, k) => (
            <circle key={`sh${k}`} cx={sh.x} cy={sh.y} r={sh.r} fill="none" stroke={ACC} strokeWidth={lw * 1.2}
              opacity={0.26 * (1 - sh.r / shellMax) * earthIn} />
          ))}
          {ranges.map(({f, r, ang, swing, i}) => {
            const rr = r + B * (mode === 'bias' ? 1 - corr : 0);
            if (mode === 'two') {
              // the whole sphere's circle, swung out from the ground point both ways
              const half = Math.PI * swing;
              return (
                <g key={i}>
                  <line x1={f.x} y1={f.y} x2={f.x + Math.cos(ang) * r * swing} y2={f.y + Math.sin(ang) * r * swing}
                    stroke={ACC} strokeWidth={lw * 0.8} strokeDasharray={`${lw * 6} ${lw * 4}`} opacity={0.6} />
                  {swing > 0 ? (
                    <g>
                      <path d={arcPath(f.x, f.y, r, ang, ang + half)} fill="none" stroke={ACC} strokeWidth={lw * 4}
                        opacity={0.25} filter={`url(#${uid}soft)`} />
                      <path d={arcPath(f.x, f.y, r, ang - half, ang)} fill="none" stroke={ACC} strokeWidth={lw * 4}
                        opacity={0.25} filter={`url(#${uid}soft)`} />
                      <path d={arcPath(f.x, f.y, r, ang, ang + half)} fill="none" stroke={ACC} strokeWidth={lw * 1.5} opacity={0.9} />
                      <path d={arcPath(f.x, f.y, r, ang - half, ang)} fill="none" stroke={ACC} strokeWidth={lw * 1.5} opacity={0.9} />
                    </g>
                  ) : null}
                </g>
              );
            }
            const legEnd = {x: f.x + Math.cos(ang) * rr * swing, y: f.y + Math.sin(ang) * rr * swing};
            const nT = 14;
            const ticks = Array.from({length: nT}, (_, k) => {
              const u = (k + 1) / (nT + 1);
              if (u * rr > rr * swing) return null;
              const px = f.x + Math.cos(ang) * r * u, py = f.y + Math.sin(ang) * r * u;
              const nx = -Math.sin(ang) * tickLen, ny = Math.cos(ang) * tickLen;
              return <line key={k} x1={px - nx} y1={py - ny} x2={px + nx} y2={py + ny} stroke={ACC} strokeWidth={lw} opacity={0.8} />;
            });
            const arcHalf = portrait ? 0.2 : 0.14;
            const a0 = ang - arcHalf * swing, a1 = ang + arcHalf * swing;
            const tr = {x: f.x + Math.cos(ang) * r, y: f.y + Math.sin(ang) * r};
            const mr = {x: f.x + Math.cos(ang) * rr, y: f.y + Math.sin(ang) * rr};
            const brOn = swing >= 0.999 ? 1 - corr : 0;
            const nx = -Math.sin(ang) * tickLen * 1.8, ny = Math.cos(ang) * tickLen * 1.8;
            const ghostOn = corr > 0 ? Math.min(1, corr * 3) : 0;
            const ring = easeInOutCubic(clamp01(seg(t, 0.36 + i * 0.07, 0.6 + i * 0.07)));
            const half = Math.PI * ring;
            // after the fix, the satellite keeps broadcasting: a bead runs down its leg, on its own beat
            const beadU = idle > 0 ? ((idle / 1.6 + i * 0.23) % 1) : -1;
            return (
              <g key={i}>
                <line x1={f.x} y1={f.y} x2={legEnd.x} y2={legEnd.y} stroke={ACC} strokeWidth={lw * 0.8}
                  strokeDasharray={`${lw * 6} ${lw * 4}`} opacity={0.85} />
                {ticks}
                {ring > 0 ? (
                  <g opacity={0.4}>
                    <path d={arcPath(f.x, f.y, rr, ang, ang + half)} fill="none" stroke={ACC} strokeWidth={lw * 0.9} />
                    <path d={arcPath(f.x, f.y, rr, ang - half, ang)} fill="none" stroke={ACC} strokeWidth={lw * 0.9} />
                  </g>
                ) : null}
                <path d={arcPath(f.x, f.y, r + B, ang - arcHalf, ang + arcHalf)} fill="none" stroke={FG}
                  strokeWidth={lw * 1.3} strokeDasharray={`${lw * 1.4} ${lw * 3.5}`} opacity={0.6 * ghostOn} />
                <path d={arcPath(f.x, f.y, rr, a0, a1)} fill="none" stroke={ACC} strokeWidth={lw * 4.5} opacity={swing > 0 ? 0.25 : 0}
                  filter={`url(#${uid}soft)`} />
                <path d={arcPath(f.x, f.y, rr, a0, a1)} fill="none" stroke={ACC} strokeWidth={lw * 2.4} opacity={swing > 0 ? 1 : 0} />
                {/* what was taken off stays on the leg, dashed: the same stretch on all four */}
                <line x1={tr.x} y1={tr.y} x2={f.x + Math.cos(ang) * (r + B)} y2={f.y + Math.sin(ang) * (r + B)} stroke={ACC2}
                  strokeWidth={lw * 3.2} strokeDasharray={`${lw * 2.4} ${lw * 2.2}`} opacity={0.95 * ghostOn} />
                {/* the shared clock-error bracket, in the ground's blue: the same length on every leg */}
                <g opacity={brOn}>
                  <line x1={tr.x} y1={tr.y} x2={mr.x} y2={mr.y} stroke={ACC2} strokeWidth={lw * 4} />
                  <line x1={tr.x - nx} y1={tr.y - ny} x2={tr.x + nx} y2={tr.y + ny} stroke={ACC2} strokeWidth={lw * 1.6} />
                  <line x1={mr.x - nx} y1={mr.y - ny} x2={mr.x + nx} y2={mr.y + ny} stroke={ACC2} strokeWidth={lw * 1.6} />
                </g>
                {beadU >= 0 ? (
                  <circle cx={lerp(f.x, P.x, beadU)} cy={lerp(f.y, P.y, beadU)} r={U * 0.005} fill={mix(ACC, '#ffffff', 0.4)}
                    opacity={clamp01(idle * 1.5) * (1 - beadU * 0.4)} />
                ) : null}
              </g>
            );
          })}
        </g>
        {/* the crossings */}
        <g opacity={clamp01(fixIn * 2)}>
          <circle cx={P.x} cy={P.y} r={U * 0.024 * Math.max(0.001, fixIn)} fill="none" stroke={FG} strokeWidth={lw * 1.6} />
          <line x1={P.x - U * 0.042} y1={P.y} x2={P.x - U * 0.03} y2={P.y} stroke={FG} strokeWidth={lw * 1.2} />
          <line x1={P.x + U * 0.03} y1={P.y} x2={P.x + U * 0.042} y2={P.y} stroke={FG} strokeWidth={lw * 1.2} />
          <line x1={P.x} y1={P.y - U * 0.042} x2={P.x} y2={P.y - U * 0.03} stroke={FG} strokeWidth={lw * 1.2} />
        </g>
        {Q ? (
          <g opacity={clamp01(qIn * 2)}>
            <circle cx={Q.x} cy={Q.y} r={U * 0.024 * Math.max(0.001, qIn)} fill="none" stroke={FG} strokeWidth={lw * 1.6}
              strokeDasharray={`${lw * 3} ${lw * 3}`} />
            <circle cx={Q.x} cy={Q.y} r={U * 0.005} fill={FG} />
          </g>
        ) : null}
        <g opacity={earthIn}>
          {phoneGlyph('phone', {x: P.x, y: P.y + U * 0.002}, U * 0.05, 0,
            {body: mix(BG, '#000000', 0.3), edge: FG, screen: mix(BG, limb, 0.3), lit: ACC}, fixIn, lw)}
        </g>
      </svg>

      {/* the satellites */}
      {S.map((p, i) => (
        <ObjectSlot key={i} object={{id: satRef.id, props: {...(satRef.props ?? {}),
          // @positional: each station's own small turn, so the row reads as several craft rather than one copied
          yaw0: (base.yaw0 ?? -0.55) + (i - (N - 1) / 2) * 0.16, roll: (base.roll ?? 0) + (i - (N - 1) / 2) * -0.05}}}
          box={{x: p.x - satW / 2, y: p.y - satH / 2, w: satW, h: satH}}
          t={clamp01(seg(t, 0.06 + i * 0.04, 0.32 + i * 0.04))} />
      ))}

      {/* words */}
      {title ? (
        <div style={{position: 'absolute', ...(centred ? {left: 0, width: W, textAlign: 'center' as const} : {right: W * 0.05, textAlign: 'right' as const}),
          top: TITLE_Y - titlePx * 0.15, color: FG, opacity: titleOn, font: `700 ${titlePx}px/1.2 ${sans}`, whiteSpace: 'nowrap'}}>{title}</div>
      ) : null}
      {kicker && fitsBox(kicker, kickPx, W * 0.5, kickPx * 3) ? (
        <div style={{position: 'absolute', ...(centred ? {left: W * 0.25, textAlign: 'center' as const} : {right: W * 0.05, textAlign: 'right' as const}),
          top: TITLE_Y + titlePx * 1.15, width: W * 0.5, color: DIM, font: `500 ${kickPx}px/${lh(kicker)} ${body}`, opacity: kickOn}}>{kicker}</div>
      ) : null}
      {sats.map((name, i) => {
        if (!fitsBox(name, labPx, satW * 1.1, labPx * 2.4)) return null;
        const on = easeOutCubic(clamp01(seg(t, ...cue.win('sats.' + i, 0.16 + i * 0.04, 0.3 + i * 0.04, REACH_CUBIC))));
        return (
          <div key={i} style={{position: 'absolute', left: S[i].x - satW * 0.55, width: satW * 1.1, textAlign: 'center',
            top: S[i].y - satH / 2 - labPx * 1.5, color: FG, font: `500 ${labPx}px/1.2 ${body}`, opacity: on}}>{name}</div>
        );
      })}
      {points.map((name, i) => {
        const at = i === 0 ? P : Q;
        if (!at || !name || !fitsBox(name, labPx, W * 0.26, labPx * 3)) return null;
        const on = easeOutCubic(clamp01(seg(t, ...cue.win('points.' + i, 0.58 + i * 0.05, 0.7 + i * 0.05, REACH_CUBIC))));
        // @positional: `points` is ordered ground-first; the second crossing is the one out in space, so its name sits beside it rather than above the Earth
        const above = i === 1;
        return (
          <div key={i} style={{position: 'absolute', left: at.x + U * 0.04, width: W * 0.26,
            top: above ? at.y - labPx * 0.65 : at.y - U * 0.075, color: FG, font: `600 ${labPx}px/${lh(name)} ${body}`,
            opacity: on}}>{name}</div>
        );
      })}
      {mode === 'bias' && rangeLabel && fitsBox(rangeLabel, labPx, W * 0.2, labPx * 3) ? (
        <div style={{position: 'absolute', left: midLeg.x - W * 0.2 - U * 0.055, top: midLeg.y - labPx * 0.7, width: W * 0.2,
          textAlign: 'right', color: ACC, font: `500 ${labPx}px/${lh(rangeLabel)} ${body}`, opacity: rangeOn}}>{rangeLabel}</div>
      ) : null}
      {mode === 'bias' && biasLabel && fitsBox(biasLabel, labPx, W * (portrait ? 0.4 : 0.25), labPx * 3.2) ? (
        <div style={{position: 'absolute', left: W * (portrait ? 0.08 : 0.045), top: portrait ? P.y - zH * 0.3 : zTop + zH * 0.62,
          width: W * (portrait ? 0.4 : 0.25), color: ACC2, font: `600 ${labPx}px/${lh(biasLabel)} ${body}`,
          opacity: biasOn, borderLeft: `${Math.max(2, lw * 2)}px solid ${ACC2}`, paddingLeft: U * 0.012}}>{biasLabel}</div>
      ) : null}
      {mode === 'bias' && here && fitsBox(here, Math.round(U * 0.044), W * 0.4, U * 0.07) ? (
        <div style={{position: 'absolute', left: P.x + U * 0.08, top: P.y - U * 0.03, width: W * 0.4,
          color: FG, font: `800 ${Math.round(U * 0.044)}px/1.2 ${sans}`, whiteSpace: 'nowrap', opacity: hereOn,
          textShadow: `0 0 ${U * 0.02}px ${BG}`}}>{here}</div>
      ) : null}
    </AbsoluteFill>
  );
};
