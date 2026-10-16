// SHOT · LightShellOrbit — a sunlit GPS satellite lets go of shells of light at a steady beat. Two views of the
// one argument shape, "a signal is a shell that grows at one speed from where it LEFT":
//
//   view 'range' (the hero) — over Earth's limb a listening phone notes when one followed shell arrives; the
//     straight run from where that shell left to the phone is drawn as a dimension (flight time × light speed),
//     and then that distance is shown for what it is: a whole SPHERE about the point of departure, the phone
//     somewhere on its surface. The other shells keep coming.
//   view 'wake' — the satellite runs along a straight stretch of orbit across the frame; every shell stays
//     centred on the mark where it left (the marks are left behind on the track), and all grow at the same rate:
//     the signal's speed does not take on the satellite's. The satellite's speed is EXAGGERATED here, by design
//     and only so the separation of the centres can be seen at all.
//
// What is drawn as true: shells are emitted on a steady beat and grow at one speed; each stays centred where it
// left; the phone never answers (it only lights as a shell passes, from this satellite or a further one). The
// satellite is the film's own object, passed in as `sat` (an ObjectRef) so its look and pose come from the beat;
// `nadirPoint` puts every shell's start on its antenna array. Every word is a prop; with none, nothing is written.
// Shells fade out through the caption band, so the subtitle sits on the film's own ground (no bar, no clutter).
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, lerp, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx, fitsBox} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {drawOn} from '../runtime/draw';
import {ObjectSlot, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {leading} from '../runtime/cjkType';
import {nadirPoint} from '../objects/GpsSatellite';
import {starField, earthDefs, earthDisc, phoneGlyph, TYPE} from '../kits/orbitKit';

export const DURATION = 150;

const BG_D0 = '#04060c', FG_D0 = '#e8eef8', ACC_D0 = '#f2c46b', ACC2_D0 = '#5db6ff';
const SUN_D0 = '#fff1d0';
const SAT_ASPECT = 2.3;      // GpsSatellite's own META.aspect — the box nadirPoint is measured in
const FOLLOW = 1;            // which shell of the hero satellite is followed and measured ('range')

type Pose = {yaw0?: number; pitch?: number; roll?: number; wingTilt?: number};

export const LightShellOrbit: React.FC<{
  sat?: ObjectRef;        // the broadcasting satellite (the film's GpsSatellite); its props carry look and pose
  view?: 'range' | 'wake';
  title?: string;         // the claim, in the title band
  sendLabel?: string;     // 'range': the stamp where the followed shell LEFT
  arriveLabel?: string;   // 'range': the stamp where it ARRIVED
  rangeLabel?: string;    // 'range': what the run between them is (flight time × light speed = distance)
  sphereLabel?: string;   // 'range': what that distance means — a sphere about the satellite, you on it
  phoneLabel?: string;    // 'range': what the phone does (listens, never sends)
  originLabel?: string;   // 'wake': what the marks left on the track are (where each shell started)
  speedLabel?: string;    // 'wake': what the equal growth means (one speed, whatever the satellite does)
  others?: number;        // 'range': how many further satellites also broadcast, 0-3
  limb?: string;          // the atmosphere's blue at Earth's limb (#hex)
  sun?: string;           // the sunlight on the foil (#hex)
}> = ({sat, view = 'range', title = '', sendLabel = '', arriveLabel = '', rangeLabel = '', sphereLabel = '',
  phoneLabel = '', originLabel = '', speedLabel = '', others = 3, limb = ACC2_D0, sun = SUN_D0} = {}) => {
  if (view !== 'range' && view !== 'wake') {
    throw new Error(`LightShellOrbit: \`view\` is 'range' or 'wake' — got ${JSON.stringify(view)}`);
  }
  if (!(Number.isInteger(others) && others >= 0 && others <= 3)) {
    throw new Error(`LightShellOrbit: \`others\` is 0-3 further satellites — got ${JSON.stringify(others)}`);
  }
  const dna = useDNA();
  const t = useT();
  const cue = useCues();
  const uid = React.useId().replace(/[^A-Za-z0-9]/g, '');
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bg ?? BG_D0, FG = dna?.fg ?? FG_D0, ACC = dna?.accent ?? ACC_D0;
  const sans = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
  const body = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
  const U = Math.min(W, H);
  const portrait = W < H;
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const lw = Math.max(1, U * 0.0018);
  const wake = view === 'wake';
  const satRef: ObjectRef = sat ?? {id: 'GpsSatellite', props: {look: 'lit'}};
  const pose = (satRef.props ?? {}) as Pose;

  // ── the Earth: 'range' — lower left, its sunlit limb toward the sun; 'wake' — only a sliver along the foot ──
  const R = wake ? Math.max(W, H) * 2.4 : portrait ? W * 1.15 : H * 1.0;
  const E = wake ? {x: W * 0.4, y: zBot + R * 0.985} : portrait ? {x: W * 0.5, y: H + R * 0.32} : {x: W * 0.27, y: H * 1.6};
  const limbAt = (x: number) => E.y - Math.sqrt(Math.max(0, R * R - (x - E.x) ** 2));
  const Px = portrait ? W * 0.36 : W * 0.33;
  const Py = limbAt(Px);
  const nrm = {x: (Px - E.x) / R, y: (Py - E.y) / R};               // the local up at the phone

  // ── the hero satellite; its antenna tip is where every shell starts ──
  const satW = wake ? (portrait ? W * 0.8 : W * 0.52) : portrait ? W * 0.78 : W * 0.4;   // 'wake' is a close-up: the craft fills the frame
  const box = fitAspect({x: 0, y: 0, w: satW, h: satW / SAT_ASPECT}, SAT_ASPECT);
  const satH = box.h;
  const trackY = zTop + zH * (portrait ? 0.3 : 0.36);
  // 'range': the orbit carries it left, slowly. 'wake': it runs right at a steady speed along a straight stretch —
  // about a sixth of the shells' speed, exaggerated from the real ratio so the centres can be seen to separate.
  const satC = (tt: number) => wake
    ? {x: lerp(W * (portrait ? 0.24 : 0.22), W * (portrait ? 0.5 : 0.4), clamp01(seg(tt, 0.02, 1))), y: trackY - satH * 0.42}
    : {x: (portrait ? W * 0.55 : W * 0.71) - W * 0.03 * tt, y: zTop + zH * (portrait ? 0.12 : 0.26)};
  const tip = nadirPoint(box.w, box.h, pose);
  const A = (tt: number) => ({x: satC(tt).x - box.w / 2 + tip.x, y: satC(tt).y - box.h / 2 + tip.y});

  // ── the further satellites ('range'): small, dimmer, each on its own beat ──
  const farPos = portrait ? [[0.12, 0.05], [0.86, 0.02], [0.92, 0.42]] : [[0.07, 0.36], [0.44, 0.08], [0.95, 0.66]];
  // @truncates: farPos is layout for up to three further satellites; `others` (0-3, checked above) is how many the film shows — nothing the film gave is dropped
  const far = (wake ? [] : farPos.slice(0, others)).map(([fx, fy], i) => {
    const w = satW * 0.3, hh = w / SAT_ASPECT;
    const c = {x: W * fx, y: zTop + zH * fy};
    const p = {yaw0: -0.4 + i * 0.5, pitch: 0.3, roll: 0.3 - i * 0.3, wingTilt: 0.4};
    const n = nadirPoint(w, hh, p);
    return {c, w, h: hh, p, a: {x: c.x - w / 2 + n.x, y: c.y - hh / 2 + n.y}, phase: 0.03 + i * 0.031};
  });

  // ── the shells ──
  const BEAT = wake ? 0.075 : 0.1;
  const v = wake ? W * 1.15 : Math.hypot(A(0).x - Px, A(0).y - Py) / 0.24;   // radius gained per unit of t
  const Rmax = Math.hypot(W, H) * 1.1;
  type Shell = {cx: number; cy: number; r: number; k: number; src: number};
  const shells: Shell[] = [];
  const origins: {x: number; y: number; k: number; tk: number}[] = [];
  const emit = (src: number, at: (tt: number) => {x: number; y: number}, phase: number) => {
    for (let k = 0; k < 16; k++) {
      const tk = 0.1 + phase + k * BEAT;
      if (t < tk) break;
      const c = at(tk);                                               // centred where it LEFT
      if (src === 0) origins.push({x: c.x, y: c.y, k, tk});
      const r = v * (t - tk);
      if (r > Rmax) continue;
      shells.push({cx: c.x, cy: c.y, r, k, src});
    }
  };
  emit(0, A, 0);
  far.forEach((f, i) => emit(i + 1, () => f.a, f.phase));
  let glow = 0;                                                       // the phone lights for every shell passing over it
  if (!wake) {
    for (const sh of shells) {
      const d = Math.abs(sh.r - Math.hypot(sh.cx - Px, sh.cy - Py));
      glow += Math.exp(-((d / (U * 0.03)) ** 2)) * (sh.src === 0 ? 1 : 0.6);
    }
  }
  glow = clamp01(glow);

  // the followed shell ('range'): when it left, when it arrives, and the sphere its distance stands for
  const tSend = 0.1 + FOLLOW * BEAT;
  const A1 = A(tSend);
  const run = Math.hypot(A1.x - Px, A1.y - Py);
  const tArrive = tSend + run / v;
  const sendOn = easeOutCubic(clamp01(seg(t, ...cue.win('sendLabel', tSend, tSend + 0.08, REACH_CUBIC))));
  const arriveOn = easeOutCubic(clamp01(seg(t, ...cue.win('arriveLabel', tArrive, tArrive + 0.08, REACH_CUBIC))));
  const dimDraw = easeInOutCubic(clamp01(seg(t, tArrive + 0.02, tArrive + 0.16)));
  const rangeOn = easeOutCubic(clamp01(seg(t, ...cue.win('rangeLabel', tArrive + 0.08, tArrive + 0.18, REACH_CUBIC))));
  const sphereIn = easeInOutCubic(clamp01(seg(t, tArrive + 0.2, tArrive + 0.38)));
  const sphereOn = easeOutCubic(clamp01(seg(t, ...cue.win('sphereLabel', tArrive + 0.3, tArrive + 0.42, REACH_CUBIC))));
  const titleOn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.02, 0.16, REACH_CUBIC))));
  const phoneOn = easeOutCubic(clamp01(seg(t, ...cue.win('phoneLabel', 0.08, 0.22, REACH_CUBIC))));
  const originOn = easeOutCubic(clamp01(seg(t, ...cue.win('originLabel', 0.3, 0.44, REACH_CUBIC))));
  const speedOn = easeOutCubic(clamp01(seg(t, ...cue.win('speedLabel', 0.5, 0.64, REACH_CUBIC))));
  const earthIn = easeOutCubic(clamp01(seg(t, 0, 0.14)));

  // the dimension: parallel to the run, set off to one side, with end ticks
  const ux = (Px - A1.x) / run, uy = (Py - A1.y) / run;
  const off = U * 0.045;
  const ox = -uy * off, oy = ux * off;
  const d0 = {x: A1.x + ox, y: A1.y + oy}, d1 = {x: Px + ox, y: Py + oy};
  const dmid = {x: lerp(d0.x, d1.x, 0.5), y: lerp(d0.y, d1.y, 0.5)};

  // ── words ──
  const titlePx = title ? fitTextPx(title, W * (portrait ? 0.84 : 0.5), Math.round(U * TYPE.title), {usable: 1}) : 0;
  const labPx = Math.round(U * TYPE.label);
  const labBox = W * (portrait ? 0.46 : 0.24);
  const ok = (s: string, bw = labBox) => !!s && fitsBox(s, labPx, bw, labPx * 3);
  const lh = (s: string) => leading(s, 1.3);

  const stars = starField(W, H, 160, FG, earthIn, U, (x, y) => Math.hypot(x - E.x, y - E.y) < R * 1.02);

  const ringStroke = (sh: Shell) => {
    const fade = 1 - sh.r / Rmax;
    const followed = !wake && sh.src === 0 && sh.k === FOLLOW;
    const base = sh.src === 0 ? 0.8 : 0.16;
    return {op: base * fade * fade * (followed ? 1.3 : 1), w: lw * (sh.src === 0 ? (followed ? 2.6 : 1.5) : 0.9), followed};
  };
  const phoneS = U * (portrait ? 0.11 : 0.13);
  const phoneDeg = (Math.atan2(nrm.y, nrm.x) * 180) / Math.PI + 90;
  // where the sphere's label sits: just outside the sphere's rim on the side that faces the phone (the rim the
  // viewer can see), a little above the line from the satellite to the phone, right-aligned to the rim
  const toPhone = Math.atan2(Py - A1.y, Px - A1.x);
  const sphA = toPhone + (Px < A1.x ? 0.55 : -0.55);
  const sphLab = {x: A1.x + Math.cos(sphA) * run, y: A1.y + Math.sin(sphA) * run};

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id={`${uid}sun`} cx={0} cy={0} r={Math.max(W, H) * 0.9} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={sun} stopOpacity={0.16} />
            <stop offset="1" stopColor={sun} stopOpacity={0} />
          </radialGradient>
          {earthDefs(uid, E, R, limb, BG)}
          {/* the caption band: everything the shells draw fades out through it */}
          <linearGradient id={`${uid}band`} x1={0} y1={0} x2={0} y2={H} gradientUnits="userSpaceOnUse">
            <stop offset={(zBot - U * 0.06) / H} stopColor="#fff" stopOpacity={1} />
            <stop offset={Math.min(1, (zBot + U * 0.05) / H)} stopColor="#fff" stopOpacity={0.12} />
            <stop offset={1} stopColor="#fff" stopOpacity={0.08} />
          </linearGradient>
          <mask id={`${uid}m`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
            <rect x={0} y={0} width={W} height={H} fill={`url(#${uid}band)`} />
          </mask>
          <radialGradient id={`${uid}sph`} cx={A1.x - run * 0.35} cy={A1.y - run * 0.35} r={run * 1.5} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={FG} stopOpacity={0.14} />
            <stop offset="0.7" stopColor={FG} stopOpacity={0.05} />
            <stop offset="1" stopColor={FG} stopOpacity={0.02} />
          </radialGradient>
          <filter id={`${uid}blur`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation={U * 0.006} /></filter>
          <filter id={`${uid}glow`} x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation={U * 0.014} /></filter>
        </defs>
        <rect x={0} y={0} width={W} height={H} fill={`url(#${uid}sun)`} />
        {stars}
        {earthDisc(uid, E, R, limb, lw, earthIn)}
        <g mask={`url(#${uid}m)`}>
          {/* 'wake': the stretch of orbit it runs along, and the mark each shell left from */}
          {wake ? (
            <g>
              <line x1={0} y1={A(0).y} x2={W} y2={A(0).y} stroke={FG} strokeWidth={lw * 0.8}
                strokeDasharray={`${lw * 2} ${lw * 6}`} opacity={0.35 * earthIn} />
              {origins.map((o) => (
                <g key={o.k} opacity={easeOutCubic(clamp01((t - o.tk) / 0.04))}>
                  <circle cx={o.x} cy={o.y} r={U * 0.0055} fill={FG} />
                  <line x1={o.x} y1={o.y - U * 0.014} x2={o.x} y2={o.y + U * 0.014} stroke={FG} strokeWidth={lw} />
                </g>
              ))}
            </g>
          ) : null}
          {/* 'range': the measured distance as what it is — every point that far from where the shell left */}
          {!wake && sphereIn > 0 ? (
            <g opacity={sphereIn}>
              <circle cx={A1.x} cy={A1.y} r={run} fill={`url(#${uid}sph)`} />
              <circle cx={A1.x} cy={A1.y} r={run} fill="none" stroke={FG} strokeWidth={lw * 1.6}
                strokeDasharray={`${lw * 7} ${lw * 5}`} opacity={0.85} />
              <ellipse cx={A1.x} cy={A1.y} rx={run} ry={run * 0.26} fill="none" stroke={FG} strokeWidth={lw}
                strokeDasharray={`${lw * 3} ${lw * 6}`} opacity={0.4} />
            </g>
          ) : null}
          {/* the shells: a soft halo under a fine line */}
          <g filter={`url(#${uid}blur)`}>
            {shells.map((sh, i) => {
              const st = ringStroke(sh);
              return <circle key={`b${i}`} cx={sh.cx} cy={sh.cy} r={sh.r} fill="none" stroke={ACC} strokeWidth={st.w * 4}
                opacity={st.op * 0.45} />;
            })}
          </g>
          {shells.map((sh, i) => {
            const st = ringStroke(sh);
            return <circle key={`s${i}`} cx={sh.cx} cy={sh.cy} r={sh.r} fill="none"
              stroke={st.followed ? mix(ACC, '#ffffff', 0.45) : ACC} strokeWidth={st.w} opacity={Math.min(1, st.op)} />;
          })}
        </g>
        {!wake ? (
          <g>
            {/* the followed shell's origin stays marked where it left, as the satellite moves on */}
            <circle cx={A1.x} cy={A1.y} r={U * 0.006} fill="none" stroke={FG} strokeWidth={lw} opacity={sendOn * 0.9} />
            {/* the dimension: flight time × light speed, the straight run from where it left to the phone */}
            <g opacity={dimDraw > 0 ? 1 : 0}>
              <path d={`M${d0.x} ${d0.y} L${d1.x} ${d1.y}`} stroke={FG} strokeWidth={lw * 1.5} fill="none" {...drawOn(dimDraw)} />
              <path d={`M${A1.x} ${A1.y} L${d0.x + ox * 0.25} ${d0.y + oy * 0.25}`} stroke={FG} strokeWidth={lw} opacity={0.7 * dimDraw} />
              <path d={`M${Px} ${Py} L${d1.x + ox * 0.25} ${d1.y + oy * 0.25}`} stroke={FG} strokeWidth={lw} opacity={0.7 * dimDraw} />
            </g>
            {/* the phone: it only listens — it lights as a shell passes */}
            <circle cx={Px} cy={Py} r={U * 0.07} fill={ACC} opacity={0.45 * glow} filter={`url(#${uid}glow)`} />
            <g opacity={earthIn}>
              {phoneGlyph('phone', {x: Px, y: Py}, phoneS, phoneDeg,
                {body: mix(BG, '#000000', 0.3), edge: FG, screen: mix(BG, limb, 0.25), lit: ACC}, glow, lw)}
            </g>
          </g>
        ) : null}
      </svg>

      {/* the further satellites, then the hero */}
      {far.map((f, i) => (
        <div key={i} style={{position: 'absolute', left: f.c.x - f.w / 2, top: f.c.y - f.h / 2, width: f.w, height: f.h, opacity: 0.8}}>
          <ObjectSlot object={{id: satRef.id, props: {...(satRef.props ?? {}), ...f.p}}} box={{x: 0, y: 0, w: f.w, h: f.h}}
            t={clamp01(seg(t, 0.02 + i * 0.03, 0.2 + i * 0.03))} />
        </div>
      ))}
      <ObjectSlot object={satRef} box={{x: satC(t).x - box.w / 2, y: satC(t).y - box.h / 2, w: box.w, h: box.h}}
        t={clamp01(seg(t, 0, 0.16))} />

      {/* words */}
      {/* the title sits low on the right, over the Earth's side of the frame, not in the top-left corner */}
      {title ? (
        <div style={{position: 'absolute', right: W * 0.05, top: zBot - titlePx * (wake ? 2.4 : 1.55), color: FG, opacity: titleOn,
          textAlign: 'right', font: `700 ${titlePx}px/1.2 ${sans}`, whiteSpace: 'nowrap', letterSpacing: '0.02em',
          textShadow: `0 0 ${U * 0.02}px ${BG}`}}>{title}</div>
      ) : null}
      {!wake && ok(sendLabel) ? (
        <div style={{position: 'absolute', left: A1.x - labBox / 2, top: A1.y + U * 0.05, width: labBox, textAlign: 'center',
          color: FG, font: `500 ${labPx}px/${lh(sendLabel)} ${body}`, opacity: sendOn}}>{sendLabel}</div>
      ) : null}
      {!wake && ok(arriveLabel) ? (
        <div style={{position: 'absolute', left: Px - labBox - phoneS * 0.5, top: Py - phoneS - labPx * 1.2, width: labBox,
          textAlign: 'right', color: FG, font: `500 ${labPx}px/${lh(arriveLabel)} ${body}`, opacity: arriveOn}}>{arriveLabel}</div>
      ) : null}
      {!wake && ok(rangeLabel, labBox * 1.3) ? (
        <div style={{position: 'absolute', left: dmid.x - labBox * 0.65, top: dmid.y - labPx * 3.4,
          width: labBox * 1.3, textAlign: 'center', color: ACC, font: `600 ${labPx}px/${lh(rangeLabel)} ${body}`,
          opacity: rangeOn}}>{rangeLabel}</div>
      ) : null}
      {!wake && ok(sphereLabel, labBox * 1.2) && sphLab.x > labBox * 1.25 && sphLab.y > zTop && sphLab.y < zBot - labPx * 3 ? (
        <div style={{position: 'absolute', left: sphLab.x - labBox * 1.2 - U * 0.02, top: sphLab.y - labPx * 0.7,
          width: labBox * 1.2, textAlign: 'right', color: FG, font: `600 ${labPx}px/${lh(sphereLabel)} ${body}`,
          opacity: sphereOn}}>{sphereLabel}</div>
      ) : null}
      {!wake && ok(phoneLabel) ? (
        <div style={{position: 'absolute', left: Px + phoneS * 0.45, width: labBox,
          top: Math.min(Py - labPx * 0.2, zBot - labPx * 2.8), color: FG, font: `500 ${labPx}px/${lh(phoneLabel)} ${body}`,
          opacity: phoneOn}}>{phoneLabel}</div>
      ) : null}
      {wake && ok(originLabel, labBox * 1.4) ? (
        <div style={{position: 'absolute', left: W * 0.06, top: A(0).y + U * 0.04, width: labBox * 1.4, color: FG,
          font: `500 ${labPx}px/${lh(originLabel)} ${body}`, opacity: originOn}}>{originLabel}</div>
      ) : null}
      {wake && ok(speedLabel, labBox * 1.4) ? (
        <div style={{position: 'absolute', right: W * 0.05, top: zBot - titlePx * 2.4 - labPx * 2.2, width: labBox * 1.4, textAlign: 'right',
          color: ACC, font: `600 ${labPx}px/${lh(speedLabel)} ${body}`, opacity: speedOn}}>{speedLabel}</div>
      ) : null}
    </AbsoluteFill>
  );
};
