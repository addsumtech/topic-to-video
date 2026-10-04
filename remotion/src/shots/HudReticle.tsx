// SHOT · Hud Reticle — a sci-fi FUI: corner brackets snap inward around a central subject, a dashed scan ring
// rotates, tick marks and status readouts type in, and the system LOCKS (ring goes solid + green). The
// "targeting / analysing / locked on" technical register (family D). Readouts are QUALITATIVE status words, not
// stats. Deterministic (ring angle + reveals = fn of t).
//
// EVERY READOUT IS IN BEFORE THE FRAME IS READ. Readout i used to slide in over `0.42 + i * 0.1 … 0.6 + i * 0.1`
// — a fixed step — so a fourth readout was still fading on the settled frame (t = 0.86, the frame every gate
// and the shot-critic read, and the one reduced motion freezes on), a sixth was half-faded on the last frame
// and a seventh started after the clip had ended. A film that listed seven status lines showed six and said
// nothing. The step is now laid out for the count — 0.1 stays the upper bound, so three readouts keep their
// exact rhythm — and closes until the last one is in by LAND_BY. Past MAX_READOUTS the column stops being a
// few status words, and the register refuses.
//
// AND THE LAYOUT REFLOWS INSTEAD OF COLLIDING. The ring (radius 300), the brackets and the readout column
// (x = 120) were fixed pixels composed for a 1920 frame: on a 1080-wide one the readouts sat ON the ring and
// ran through the target's name, and at 1:1 the ring itself reached past the content zone. The composition is
// the same one — ring centred, readouts to its left — wherever the column has room beside the ring; where it
// does not, the readouts stack UNDER the ring and the whole instrument scales (one factor, `s`) to fit the
// content zone. The target is fitted inside the ring, and the faint grid stops at the content zone's edges
// instead of running into the caption band. The 16:9 composition is unchanged.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic, REDUCED_MOTION_T} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {onLight} from '../runtime/light';
import {CONTENT_TOP, contentBottom, fitBlockPx, fitTextPx, textWidthPx, wrapLines} from '../runtime/layout';
import {ObjectSlot, type ObjectRef} from '../runtime/objectSlot';
import {useGlide} from '../runtime/glide';

// A reticle SCANS and then LOCKS: those two states are the form, not the topic — so they are
// declared here AND exposed as props, because a Chinese film should be able to say them in Chinese.
export const INTRINSIC_TEXT = ['SCANNING…', '● LOCKED'];

export const DURATION = 150; // 5s
const BG_D0 = '#070b0e', CYAN_D0 = '#37e0d4', GREEN_D0 = '#3affa0';

export const MAX_READOUTS = 6;
// Readout i slides in over [RD_START + i * step, … + RD_DUR]. RD_STEP is the original gap and only an upper
// bound; the real step is derived from the count so the last readout is in by LAND_BY.
const RD_START = 0.42, RD_STEP = 0.1, RD_DUR = 0.18;
const LAND_BY = REDUCED_MOTION_T - 0.02;
// The readouts are 26px mono with 0.08em tracking and a 3px rule + 14px pad; a Han glyph is two mono cells.
const RD_PX0 = 26, RD_GAP = 16, RD_RULE = 17;
const RD_ADV = {adv: 0.6 + 0.08, cjk: 1.2 + 0.08};

export const HudReticle: React.FC<{target?: string; readouts?: string[]; title?: string; scanLabel?: string; lockLabel?: string; object?: ObjectRef}> = ({
  target: TARGET = 'WorkBuddy', readouts: READOUTS = ['SIGNAL · strong', 'SCOPE · full workspace', 'STATUS · ready'],
  title: TITLE = 'Locking on',
  scanLabel: SCAN_LABEL = 'SCANNING…', lockLabel: LOCK_LABEL = '● LOCKED', object: OBJECT} = {}) => {
  if (!Array.isArray(READOUTS) || READOUTS.length > MAX_READOUTS) {
    throw new Error(
      `HudReticle takes 0-${MAX_READOUTS} \`readouts\` (got ${Array.isArray(READOUTS) ? READOUTS.length : typeof READOUTS}). ` +
      'Each slides in one after another and must be in before the settled frame; past ' +
      `${MAX_READOUTS} the column is no longer a few status words beside a lock. Keep the qualitative ones.`);
  }
  READOUTS.forEach((r, i) => {
    if (typeof r !== 'string' || !r.trim()) {
      throw new Error(`HudReticle: readout ${i + 1} is empty (got ${JSON.stringify(r)}). Pass a short status ` +
        'word for each, or leave it out.');
    }
  });
  const nR = READOUTS.length;
  const rdStep = nR > 1 ? Math.min(RD_STEP, (LAND_BY - RD_START - RD_DUR) / (nR - 1)) : RD_STEP;

  const dna = useDNA();
  const CYAN = dna?.accent ?? CYAN_D0, GREEN = dna?.accent2 ?? GREEN_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;

  // ── LAYOUT ────────────────────────────────────────────────────────────────────────────────────────────
  // The readouts' own size: the longest line decides it (fitted in the mono advance, tracking included).
  const longest = READOUTS.reduce((a, r) => (textWidthPx(r, 1, RD_ADV) > textWidthPx(a, 1, RD_ADV) ? r : a), '');
  const rdPxFor = (w: number) => (nR ? Math.min(RD_PX0, fitTextPx(longest, w - RD_RULE, RD_PX0, {usable: 1, ...RD_ADV})) : RD_PX0);
  const rdLead = leading(READOUTS, 1);
  const rdBlockH = (px: number, w: number) => READOUTS.reduce(
    (h, r, i) => h + (i ? RD_GAP : 0) + wrapLines(r, px, w - RD_RULE, RD_ADV) * px * rdLead, 0);

  // SIDE — the original composition: the ring centred, the column to its left. It holds when the column
  // between the frame's margin and the brackets can carry the longest readout at 20px or more on one line.
  const Rside = Math.min(300, zH / 2 - 4);
  const colL = Math.min(120, Math.round(W * 0.0625));
  const colW = W / 2 - Rside * 1.2 - 40 - colL;          // the brackets stand R + 60·s = 1.2R from the centre
  const rdSidePx = rdPxFor(colW);
  const side = nR === 0 || (colW >= 240 && rdSidePx >= 20);

  // STACKED — the ring above, the readouts under it, the pair centred in the content zone and the ring
  // scaled so both fit (and so the brackets, 1.2R out, stay inside the frame's width).
  const gapS = Math.round(U * 0.045);
  const rdColW = Math.min(W * 0.84, 1100);
  const rdStackPx = rdPxFor(rdColW);
  const rdStackH = nR ? rdBlockH(rdStackPx, rdColW) : 0;
  const Rstack = Math.min(300, ((zH - (nR ? gapS + rdStackH : 0)) / 2) * 0.96, (W * 0.92) / 2 / 1.2);

  const R = side ? Rside : Rstack;
  const s = R / 300;                                     // the one scale every drawn length follows
  const cx = W / 2;
  const cy = side
    ? Math.max(zTop + R, Math.min(zBot - R, H / 2 + 10))
    : zTop + (zH - (2 * R + (nR ? gapS + rdStackH : 0))) / 2 + R;
  const rdPx = side ? rdSidePx : rdStackPx;

  const brackets = easeOutExpo(seg(t, 0.1, 0.4));       // corner brackets snap in
  const ringAng = t * 300;                              // continuous scan rotation (deg)
  const locked = t > 0.76;
  const col = locked ? GREEN : CYAN;
  // A GLOW IS EMITTED LIGHT, AND PAPER DOES NOT EMIT. The ring's `drop-shadow(0 0 8px)` and the target's
  // 40px bloom are what an instrument looks like on a black field. On a light film the same two spray the
  // accent out into a halo that is neither the ring nor the ground, and the halo is the whole finding:
  // 8.3% of this register's ink under 3:1 on a light ground (2026-09-21, scripts/ink_contrast_qa.py), in
  // one connected region 0.75% of the frame, ring-shaped, while the ring's own stroke reads and the
  // register's median mark is 5.33:1. On paper the instrument is DRAWN rather than lit: the stroke, the
  // brackets and the crosshair are hairlines in the film's own accent and carry it without the bloom.
  const emits = !onLight(dna);
  const lockIn = easeOutExpo(seg(t, 0.76, 0.9));
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const bo = lerp(120, 0, brackets) * s; // bracket offset from target (px)
  const half = R + 60 * s;
  // THE TARGET IS FITTED INSIDE THE RING. It was a bare 84px, which holds 'WorkBuddy' in a 300px ring and
  // wraps a long name out across the ring's edge. The box is set on the element so the browser wraps in the
  // same measure the fit used.
  const innerR = R - 26 * s;
  const targetW = Math.round(2 * innerR * 0.92);
  const targetLead = leading(TARGET, 1);
  const targetPx = fitBlockPx(TARGET, targetW, innerR * 0.9, Math.round(84 * s), {usable: 1, leading: targetLead});
  // WITH AN OBJECT the reticle locks onto a THING the film drew (runtime/objectSlot): it sits in the upper part of
  // the inner ring and the name moves under it, smaller, still inside the ring (every corner of the box is about
  // 0.971 of the inner radius — hypot(0.55, 0.8); the name's block ends by 0.7 of it). The object's clock is the
  // scan, 0.1–0.6, so it is whole well before the lock at 0.76.
  const objSide = innerR * 1.1;
  const objBox = {x: cx - objSide / 2, y: cy - innerR * 0.8, w: objSide, h: objSide};
  const nameW = Math.round(innerR * 1.3);
  const namePx = fitBlockPx(TARGET, nameW, innerR * 0.22, Math.round(40 * s), {usable: 1, leading: targetLead});
  // the grid is faint, but it is still ink: it stops at the content zone rather than running under the caption
  const gy0 = Math.max(zTop, cy - 360 * s), gy1 = Math.min(zBot, cy + 360 * s);
  return (
    // THE LIFT IN THE GROUND FOLLOWED NOTHING. Only the OUTER stop of this well read the DNA, so a film
    // grounded warm white got a teal-black pool in the middle of the frame with the film's paper around it —
    // and the HUD's own ink, authored to sit on that pool, then had no ground it was designed for. The film's
    // treatment first, its flat ground next, and the original two-stop well only when there is no DNA at all.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg
        ?? `radial-gradient(120% 100% at 50% 45%, #0c151a, ${BG_D0} 74%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 66, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: dna?.dim ?? '#7fb6b2', font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* faint grid */}
        <g opacity={0.12 * brackets}>
          {[...Array(9)].map((_, i) => <line key={'v' + i} x1={cx + (i * 100 - 400) * s} y1={gy0} x2={cx + (i * 100 - 400) * s} y2={gy1} stroke={CYAN} strokeWidth={1} />)}
          {[...Array(7)].map((_, i) => <line key={'h' + i} x1={cx - 400 * s} y1={cy + (i * 100 - 300) * s} x2={cx + 400 * s} y2={cy + (i * 100 - 300) * s} stroke={CYAN} strokeWidth={1} />)}
        </g>
        {/* rotating dashed scan ring */}
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={col} strokeWidth={locked ? 5 : 2}
          strokeDasharray={locked ? undefined : '18 22'} opacity={0.85}
          transform={`rotate(${ringAng} ${cx} ${cy})`} style={{filter: emits ? `drop-shadow(0 0 8px ${col})` : undefined}} />
        <circle cx={cx} cy={cy} r={innerR} fill="none" stroke={col} strokeWidth={1} opacity={0.3}
          transform={`rotate(${-ringAng * 0.6} ${cx} ${cy})`} strokeDasharray="4 14" />
        {/* crosshair */}
        <g opacity={brackets}>
          <line x1={cx - 60 * s} y1={cy} x2={cx + 60 * s} y2={cy} stroke={col} strokeWidth={2} />
          <line x1={cx} y1={cy - 60 * s} x2={cx} y2={cy + 60 * s} stroke={col} strokeWidth={2} />
        </g>
        {/* corner brackets */}
        {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map((sg, i) => {
          const bx = cx + sg[0] * (half + bo), by = cy + sg[1] * (half * 0.72 + bo), L = 54 * s;
          return <g key={i} stroke={col} strokeWidth={4} fill="none" opacity={brackets}>
            <line x1={bx} y1={by} x2={bx - sg[0] * L} y2={by} /><line x1={bx} y1={by} x2={bx} y2={by - sg[1] * L} />
          </g>;
        })}
      </svg>

      {/* central subject — the film's object when it gives one, else its name */}
      {OBJECT ? (
        <>
          <ObjectSlot object={OBJECT} box={objBox} t={clamp01(seg(t, 0.1, 0.6))}
            style={{transform: `scale(${lerp(0.9, 1, brackets)})`, transformOrigin: '50% 50%'}} />
          <div style={{position: 'absolute', left: cx, top: cy + innerR * 0.36, width: nameW,
            transform: 'translate(-50%, 0)', textAlign: 'center'}}>
            <div style={{color: dna?.fg ?? '#eafffb', font: `800 ${namePx}px/${targetLead} var(--f-display, Inter, system-ui, sans-serif)`,
              letterSpacing: '-0.01em', textWrap: 'balance'}}>{TARGET}</div>
            <div style={{marginTop: Math.round(10 * s), color: col, font: `700 ${Math.round(22 * s)}px/1 var(--f-mono, "JetBrains Mono", monospace)`,
              letterSpacing: '0.3em', opacity: locked ? lockIn : 0.6 * clamp01(seg(t, 0.4, 0.6))}}>{locked ? LOCK_LABEL : SCAN_LABEL}</div>
          </div>
        </>
      ) : (
        <div style={{position: 'absolute', left: cx, top: cy, width: targetW,
          transform: glide(`translate(-50%,-50%) scale(${lerp(0.9, 1, brackets)})`, brackets !== 1), textAlign: 'center'}}>
          <div style={{color: dna?.fg ?? '#eafffb', font: `800 ${targetPx}px/${targetLead} var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
            textWrap: 'balance', textShadow: emits ? `0 0 40px ${col}66` : undefined}}>{TARGET}</div>
          <div style={{marginTop: Math.round(14 * s), color: col, font: `700 ${Math.round(26 * s)}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.3em',
            opacity: locked ? lockIn : 0.6 * clamp01(seg(t, 0.4, 0.6))}}>{locked ? LOCK_LABEL : SCAN_LABEL}</div>
        </div>
      )}

      {/* readouts: a column left of the ring (side), or a block centred under it (stacked) */}
      <div style={side
        ? {position: 'absolute', left: colL, top: cy - Math.max(60, rdBlockH(rdPx, colW) / 2), width: colW,
           display: 'flex', flexDirection: 'column', gap: RD_GAP}
        : {position: 'absolute', left: (W - rdColW) / 2, top: cy + R + gapS, width: rdColW,
           display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{display: 'flex', flexDirection: 'column', gap: RD_GAP, alignItems: 'flex-start', maxWidth: '100%'}}>
          {READOUTS.map((rd, i) => {
            const on = clamp01(seg(t, RD_START + i * rdStep, RD_START + i * rdStep + RD_DUR));
            return <div key={i} style={{opacity: on, transform: `translateX(${(1 - on) * -16}px)`,
              color: dna?.dim ?? '#9fd6d0', font: `600 ${rdPx}px/${rdLead} var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.08em',
              borderLeft: `3px solid ${col}`, paddingLeft: 14}}>{rd}</div>;
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
export default HudReticle;
