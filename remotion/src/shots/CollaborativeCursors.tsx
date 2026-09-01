// SHOT · Collaborative Cursors — Figma's multiplayer product-film language, done AUTHENTICALLY LIGHT.
// A light-grey design CANVAS with white artboards. Multi-COLOUR named collaborator cursors glide in
// (superhuman slow→fast→slow ease) and REST where they work (no jitter); each builds a real deliverable —
// a chart grows, a doc types, a table fills — all in parallel, with Figma selection boxes in the
// collaborator's own colour. Light + colourful (deliberately NOT the dark/mono default). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeCursor, easeOutCubic, easeInOutCubic, easeOutBack, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

// A virtual camera over a LARGE canvas: interpolate {cx,cy,z} keyframes so the lens sweeps + dollies across
// the board (the Miro/Figma "fly over the canvas" feel) instead of a flat, static, head-on grid.
type Cam = {at: number; cx: number; cy: number; z: number};
function camAt(t: number, ks: Cam[]): {cx: number; cy: number; z: number} {
  let a = ks[0], b = ks[ks.length - 1];
  for (let i = 0; i < ks.length - 1; i++) if (t >= ks[i].at && t <= ks[i + 1].at) {a = ks[i]; b = ks[i + 1]; break;}
  const lt = easeInOutCubic(clamp01((t - a.at) / Math.max(1e-6, b.at - a.at)));
  return {cx: lerp(a.cx, b.cx, lt), cy: lerp(a.cy, b.cy, lt), z: lerp(a.z, b.z, lt)};
}
const WORLD_W = 2560, WORLD_H = 1500;

export const DURATION = 180; // 6s @30

type Kind = 'chart' | 'doc' | 'slide' | 'table';
type Board = {name: string; kind: Kind; color: string; x: number; y: number; from: [number, number]; arrive: number};
const BUILD = 0.34;
const INK = '#1b2333', DIM = '#d7dde6', PANEL = '#ffffff';

// Figma multiplayer palette — bright, distinct per collaborator (colour IS the identity here).
const PALETTE = ['#2E7BFF', '#12B76A', '#7C5CFF', '#F79009', '#EC4899', '#06AED4'];

const Artifact: React.FC<{kind: Kind; p: number; color: string}> = ({kind, p, color}) => {
  const dna = useDNA();
  const DIMc = dna?.line ?? DIM;                 // placeholder fills follow the DNA's line tone
  if (kind === 'chart') {
    const hs = [0.5, 0.82, 0.4, 0.95, 0.62];
    return <svg width="340" height="176" style={{position: 'absolute', left: 22, top: 52}}>
      {hs.map((h, i) => {
        const bh = 140 * h * easeOutCubic(clamp01((p - i * 0.12) / 0.4));
        return <rect key={i} x={14 + i * 64} y={150 - bh} width={44} height={bh} rx={5} fill={i === 3 ? color : DIMc} />;
      })}
    </svg>;
  }
  if (kind === 'table') {
    const cells = [];
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
      const on = clamp01((p - (r * 4 + c) * 0.05) / 0.2);
      cells.push(<rect key={`${r}-${c}`} x={18 + c * 82} y={54 + r * 38} width={70} height={26} rx={5}
        fill={r === 0 ? color : DIMc} opacity={r === 0 ? 0.3 + 0.7 * on : 0.4 + 0.6 * on} />);
    }
    return <svg width="360" height="190">{cells}</svg>;
  }
  if (kind === 'slide') {
    return <div style={{position: 'absolute', left: 24, top: 54, right: 24}}>
      <div style={{height: 24, width: `${70 * easeOutCubic(clamp01(p / 0.3))}%`, background: color, borderRadius: 6}} />
      <div style={{height: 88, marginTop: 16, width: `${100 * easeOutCubic(clamp01((p - 0.25) / 0.5))}%`,
        background: DIMc, borderRadius: 8}} />
    </div>;
  }
  const ws = [0.92, 0.78, 0.86, 0.6];
  return <div style={{position: 'absolute', left: 26, top: 58, right: 26, display: 'flex', flexDirection: 'column', gap: 17}}>
    {ws.map((w, i) => <div key={i} style={{height: 13, borderRadius: 7, background: i === 1 ? color : DIMc,
      width: `${w * 100 * easeOutCubic(clamp01((p - i * 0.14) / 0.3))}%`}} />)}
  </div>;
};

const Artboard: React.FC<{b: Board; t: number}> = ({b, t}) => {
  const dna = useDNA();
  const PANELc = dna?.surface ?? PANEL, INKc = dna?.fg ?? INK, BORD = dna?.line ?? '#e5e9ef', GROUND = dna?.bg ?? '#fff';
  const w = 380, h = 250;
  const p = seg(t, b.arrive, b.arrive + BUILD);
  const active = t > b.arrive - 0.02 && t < b.arrive + BUILD + 0.14;
  const done = t > b.arrive + BUILD;
  const appear = easeOutBack(seg(t, b.arrive - 0.06, b.arrive + 0.06));
  // cursor GLIDES from its off-canvas start to a RESTING corner of the artboard, then holds still (no jitter)
  const restX = b.x + w * 0.66, restY = b.y + h * 0.44;
  const march = easeCursor(seg(t, Math.max(0, b.arrive - 0.30), b.arrive));
  const cx = lerp(b.from[0], restX, march), cy = lerp(b.from[1], restY, march);
  const cursorShown = t > Math.max(0, b.arrive - 0.30) && t < b.arrive + BUILD + 0.22;
  return <>
    <div style={{position: 'absolute', left: b.x, top: b.y, width: w, height: h, opacity: clamp01(appear),
      transform: `scale(${0.92 + 0.08 * appear})`, transformOrigin: 'center', background: PANELc,
      border: `1px solid ${BORD}`, borderRadius: 16, boxShadow: '0 22px 50px rgba(30,45,80,.16)'}}>
      <div style={{position: 'absolute', left: 22, top: 18, font: '700 22px/1 var(--f-body, Inter,system-ui,sans-serif)', color: INKc}}>{b.name}</div>
      <Artifact kind={b.kind} p={p} color={b.color} />
      {done && <div style={{position: 'absolute', right: 18, top: 16, width: 26, height: 26, borderRadius: 13,
        background: b.color, color: '#fff', font: '700 18px/26px var(--f-body, Inter,sans-serif)', textAlign: 'center'}}>✓</div>}
      {active && <>
        <div style={{position: 'absolute', inset: -3, border: `2px solid ${b.color}`, borderRadius: 18}} />
        {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([hx, hy], k) =>
          <div key={k} style={{position: 'absolute', left: hx ? w - 6 : -6, top: hy ? h - 6 : -6, width: 12, height: 12,
            background: GROUND, border: `2px solid ${b.color}`, borderRadius: 3}} />)}
      </>}
    </div>
    {cursorShown && (
      <div style={{position: 'absolute', left: cx, top: cy, filter: 'drop-shadow(0 6px 12px rgba(30,45,80,.28))'}}>
        <svg width="30" height="36" viewBox="0 0 22 26"><path d="M2,2 L2,22 L7,17 L10,24 L13,23 L10,16 L17,16 Z" fill={b.color} stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" /></svg>
        <div style={{position: 'absolute', left: 24, top: 20, padding: '6px 13px', borderRadius: 8, background: b.color,
          color: '#fff', font: '700 21px/1 var(--f-body, Inter,system-ui,sans-serif)', whiteSpace: 'nowrap'}}>{b.name}</div>
      </div>
    )}
  </>;
};

export const CollaborativeCursors: React.FC<{names?: string[]}> = ({
  names = ['Market Research', 'Financial Analysis', 'Slide Design', 'Legal Drafting', 'Copywriting', 'Data Cleanup'],
}) => {
  // LEVEL-C: the Figma canvas flips to a DARK board on a dark DNA (ground/dots/panels/ink → DNA); the multi-colour
  // collaborator cursors + selection boxes stay (colour IS each collaborator's identity — they pop on any ground).
  const dna = useDNA();
  const BG = dna?.bg ?? '#eef1f5', DOT = dna?.line ?? '#c7cedb';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const kinds: Kind[] = ['chart', 'chart', 'slide', 'doc', 'doc', 'table'];
  // Aligned 3×2 grid on a LARGE world (bigger than the frame, so the camera has canvas to fly over).
  const BW = 380, BH = 250, GUT = 260, COLS = 3, ROWS = 2;
  const gridW = COLS * BW + (COLS - 1) * GUT, gridH = ROWS * BH + (ROWS - 1) * GUT;
  const ox = (WORLD_W - gridW) / 2, oy = (WORLD_H - gridH) / 2;
  const boards: Board[] = names.slice(0, 6).map((name, i) => ({
    name, kind: kinds[i], color: PALETTE[i % PALETTE.length],
    x: ox + (i % COLS) * (BW + GUT), y: oy + Math.floor(i / COLS) * (BH + GUT),
    from: [hash01(i + 1) * WORLD_W, hash01(i + 9) < 0.5 ? -120 : WORLD_H + 120], arrive: 0.14 + i * 0.11,
  }));
  // camera: establish the whole canvas wide → sweep down-right + push in as the work builds → settle on a board.
  const cam = camAt(t, [
    {at: 0.0, cx: WORLD_W / 2, cy: WORLD_H / 2, z: 0.66},
    {at: 0.20, cx: WORLD_W / 2, cy: WORLD_H / 2, z: 0.70},
    {at: 0.60, cx: WORLD_W / 2 + 240, cy: WORLD_H / 2 + 150, z: 0.90},
    {at: 1.0, cx: ox + BW + GUT + BW / 2, cy: oy + BH + GUT + BH / 2, z: 1.04}, // dolly into the middle-bottom board
  ]);
  const world: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: WORLD_W, height: WORLD_H,
    transformOrigin: '0 0', transform: `translate(${W / 2 - cam.cx * cam.z}px, ${H / 2 - cam.cy * cam.z}px) scale(${cam.z})`};
  const dots = [];
  for (let gx = 0; gx < 33; gx++) for (let gy = 0; gy < 20; gy++) dots.push(<circle key={`${gx}-${gy}`} cx={gx * 80 + 30} cy={gy * 80 + 30} r={1.8} fill={DOT} />);
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* data-bleed: the camera DOLLIES IN to the middle-bottom board by the end, so the outer boards are
          cropped by the frame at rest. That is the move, not a layout that overflowed. */}
      <div data-bleed style={world}>
        <svg width={WORLD_W} height={WORLD_H} style={{position: 'absolute', inset: 0, opacity: 0.7}}>{dots}</svg>
        {boards.map((b, i) => <Artboard key={i} b={b} t={t} />)}
      </div>
      {/* screen-fixed HUD — rides the frame, not the canvas */}
    </AbsoluteFill>
  );
};
export default CollaborativeCursors;
