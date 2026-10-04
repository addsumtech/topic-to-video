// SHOT · Collaborative Cursors — Figma's multiplayer product-film language, done AUTHENTICALLY LIGHT.
// A light-grey design CANVAS with white artboards. Multi-COLOUR named collaborator cursors glide in
// (superhuman slow→fast→slow ease) and REST where they work (no jitter); each builds a real deliverable —
// a chart grows, a doc types, a table fills — all in parallel, with Figma selection boxes in the
// collaborator's own colour. Light + colourful (deliberately NOT the dark/mono default). Deterministic.
//
// WHAT EACH BOARD HOLDS, AND WHETHER IT IS FINISHED, IS THE FILM'S. Three things here were decided by POSITION:
//   * the deliverable: `kinds = ['chart','chart','slide','doc','doc','table']`, so whatever name came first or
//     second got a CHART, the third a slide deck, the last a table. A film about a kitchen brigade gave six
//     stations and shipped the pastry chef building a bar chart;
//   * the chart itself: five invented heights (0.5 / 0.82 / 0.4 / 0.95 / 0.62) with the FOURTH bar in the
//     collaborator's colour — a quantity and an emphasis about a name, made by nobody;
//   * the ✓: every board got a done badge once its build ran, a claim that every piece of work was finished;
//   * and the camera ended dollied into the fifth board, so the last frame singled that name out (and with
//     fewer than five names it dollied into empty canvas).
// Each board is now `{name, kind?, done?}`: `kind` picks the deliverable (a board with none is a clean
// artboard with its name — no deliverable is invented), `done: true` earns the ✓, and a chart — which is
// never given numbers here — is a skeleton of equal, placeholder-toned bars with none singled out. The grid
// is laid out for the count (at most six; a name was silently dropped past it), and the camera settles on the
// whole grid, inside the content zone. The standalone demo keeps its kinds and ticks in its own data.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeCursor, easeOutCubic, easeInOutCubic, easeOutBack, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {camUnlock, pageCamTransform, useCamUnlock} from '../runtime/pageCam2D';
import {useGlide} from '../runtime/glide';

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

export type CollabKind = 'chart' | 'doc' | 'slide' | 'table';
type Kind = CollabKind;
export type CollabBoard = {
  name: string;
  /** what this collaborator is building — chosen by the film, never by position; absent → a clean artboard */
  kind?: CollabKind;
  /** true only when the film says this piece of work is finished: the board earns a ✓ once its build runs */
  done?: boolean;
};
const KINDS: Kind[] = ['chart', 'doc', 'slide', 'table'];
// Six boards is the 3x2 grid the canvas is composed for (2x3 standing up); past it a name was dropped silently.
export const MAX_COLLAB_BOARDS = 6;
type Board = {name: string; kind?: Kind; done: boolean; color: string; x: number; y: number; from: [number, number]; arrive: number};
const BUILD = 0.34;
const INK = '#1b2333', DIM = '#d7dde6', PANEL = '#ffffff';

// Figma multiplayer palette — bright, distinct per collaborator (colour IS the identity here).
const PALETTE = ['#2E7BFF', '#12B76A', '#7C5CFF', '#F79009', '#EC4899', '#06AED4'];

const Artifact: React.FC<{kind: Kind; p: number; color: string}> = ({kind, p, color}) => {
  const dna = useDNA();
  const DIMc = dna?.line ?? DIM;                 // placeholder fills follow the DNA's line tone
  if (kind === 'chart') {
    // a SKELETON chart: the film gave a name, not numbers, so every bar is the same height and the same
    // placeholder tone — it says "a chart is being built", never what the chart says
    return <svg width="340" height="176" style={{position: 'absolute', left: 22, top: 52}}>
      <line x1={6} y1={151} x2={330} y2={151} stroke={DIMc} strokeWidth={2} />
      {[0, 1, 2, 3, 4].map((i) => {
        const bh = 140 * 0.6 * easeOutCubic(clamp01((p - i * 0.12) / 0.4));
        return <rect key={i} x={14 + i * 64} y={150 - bh} width={44} height={bh} rx={5} fill={DIMc} />;
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
  // A doc the film named only by its kind: four placeholder lines, all in the placeholder tone. The second line
  // used to be painted in the collaborator's colour — a highlight on a line with nothing in it, singled out by
  // its index, the same move the chart made with its fourth bar. The ragged lengths stay: they are what make
  // four bars read as a paragraph of text rather than as a table or a chart.
  // @decor: ragged line lengths of a placeholder paragraph — texture that says "text", not a reading of anything the film named
  const ws = [0.92, 0.78, 0.86, 0.6];
  return <div style={{position: 'absolute', left: 26, top: 58, right: 26, display: 'flex', flexDirection: 'column', gap: 17}}>
    {ws.map((w, i) => <div key={i} style={{height: 13, borderRadius: 7, background: DIMc,
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
  // the name tag rides the cursor's glide inside a drop-shadow, and a drop-shadow keeps only the scale of the
  // matrix above it (runtime/textSafe.tsx) — so the tag carries its own unlock, raised for the widest zoom (0.66)
  const glide = useGlide();
  return <>
    <div style={{position: 'absolute', left: b.x, top: b.y, width: w, height: h, opacity: clamp01(appear),
      transform: `scale(${0.92 + 0.08 * appear})`, transformOrigin: 'center', background: PANELc,
      border: `1px solid ${BORD}`, borderRadius: 16, boxShadow: '0 22px 50px rgba(30,45,80,.16)'}}>
      <div style={{position: 'absolute', left: 22, top: 18, font: '700 22px/1 var(--f-body, Inter,system-ui,sans-serif)', color: INKc}}>{b.name}</div>
      {b.kind ? <Artifact kind={b.kind} p={p} color={b.color} /> : null}
      {done && b.done && <div style={{position: 'absolute', right: 18, top: 16, width: 26, height: 26, borderRadius: 13,
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
          color: '#fff', font: '700 21px/1 var(--f-body, Inter,system-ui,sans-serif)', whiteSpace: 'nowrap',
          transform: glide(undefined, true, 0.66)}}>{b.name}</div>
      </div>
    )}
  </>;
};

const DEFAULT_BOARDS: CollabBoard[] = [
  {name: 'Market Research', kind: 'chart', done: true}, {name: 'Financial Analysis', kind: 'chart', done: true},
  {name: 'Slide Design', kind: 'slide', done: true}, {name: 'Legal Drafting', kind: 'doc', done: true},
  {name: 'Copywriting', kind: 'doc', done: true}, {name: 'Data Cleanup', kind: 'table', done: true},
];

const normaliseBoards = (names: unknown): CollabBoard[] => {
  if (!Array.isArray(names) || names.length < 1 || names.length > MAX_COLLAB_BOARDS) {
    throw new Error(`CollaborativeCursors needs 1-${MAX_COLLAB_BOARDS} \`names\` (got ${Array.isArray(names) ? names.length : typeof names}). ` +
      'Each collaborator gets one artboard on a 3x2 canvas; past six, group the work or cast a grid register.');
  }
  return names.map((it: any, i: number) => {
    const name = String((typeof it === 'string' ? it : it?.name) ?? '').trim();
    if (!name) throw new Error(`CollaborativeCursors: board ${i + 1} has no name.`);
    const kind = typeof it === 'string' ? undefined : it?.kind;
    if (kind != null && !KINDS.includes(kind)) {
      throw new Error(`CollaborativeCursors: board ${i + 1} ("${name}") has kind ${JSON.stringify(kind)} — use one of ` +
        `${KINDS.join(', ')}, or leave it out for a clean artboard.`);
    }
    const done = typeof it === 'string' ? undefined : it?.done;
    if (done != null && typeof done !== 'boolean') {
      throw new Error(`CollaborativeCursors: board ${i + 1} ("${name}") has \`done: ${JSON.stringify(done)}\` — pass true, false, or leave it out.`);
    }
    return {name, kind: kind ?? undefined, done: done === true};
  });
};

export const CollaborativeCursors: React.FC<{names?: (string | CollabBoard)[]}> = ({
  names = DEFAULT_BOARDS,
} = {}) => {
  const items = normaliseBoards(names);
  const n = items.length;
  // LEVEL-C: the Figma canvas flips to a DARK board on a dark DNA (ground/dots/panels/ink → DNA); the multi-colour
  // collaborator cursors + selection boxes stay (colour IS each collaborator's identity — they pop on any ground).
  const dna = useDNA();
  const BG = dna?.bg ?? '#eef1f5', DOT = dna?.line ?? '#c7cedb';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // An aligned grid on a LARGE world (bigger than the frame, so the camera has canvas to fly over), laid out for
  // the count: three across (two standing up), a short last row centred under the rest.
  const BW = 380, BH = 250, GUT = 260;
  const COLS = Math.min(H > W * 1.15 ? 2 : 3, n), ROWS = Math.ceil(n / COLS);
  const gridW = COLS * BW + (COLS - 1) * GUT, gridH = ROWS * BH + (ROWS - 1) * GUT;
  const ox = (WORLD_W - gridW) / 2, oy = (WORLD_H - gridH) / 2;
  // EVERY BOARD IS AT REST BEFORE THE CLIP ENDS. At a fixed 0.11 pitch the sixth board was still mid-build at
  // t=1, with its selection box and cursor on it: the last frame showed the LAST NAME as the one still being
  // worked on — a status picked by position. The pitch now closes up with the count so the last cursor leaves
  // (arrive + BUILD + 0.22) by t=0.94; up to three boards keep the original 0.11.
  const pitch = Math.min(0.11, 0.24 / Math.max(1, n - 1));
  const boards: Board[] = items.map((it, i) => {
    const row = Math.floor(i / COLS), inRow = Math.min(COLS, n - row * COLS);
    return {
      name: it.name, kind: it.kind, done: !!it.done, color: PALETTE[i % PALETTE.length],
      x: ox + ((COLS - inRow) * (BW + GUT)) / 2 + (i % COLS) * (BW + GUT), y: oy + row * (BH + GUT),
      from: [hash01(i + 1) * WORLD_W, hash01(i + 9) < 0.5 ? -120 : WORLD_H + 120], arrive: 0.14 + i * pitch,
    };
  });
  // camera: establish the whole canvas wide → sweep down-right + push in as the work builds → settle on the
  // WHOLE GRID, centred on the content zone and sized to it, so no one board is where the shot ends up.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const zEnd = Math.min(1.04, ((zBot - zTop) * 0.96) / gridH, (W * 0.96) / gridW);
  const cyEnd = WORLD_H / 2 - ((zTop + zBot) / 2 - H / 2) / zEnd;
  const camKeys: Cam[] = [
    {at: 0.0, cx: WORLD_W / 2, cy: WORLD_H / 2, z: Math.min(0.66, zEnd)},
    {at: 0.20, cx: WORLD_W / 2, cy: WORLD_H / 2, z: Math.min(0.70, zEnd)},
    {at: 0.60, cx: WORLD_W / 2 + 240, cy: WORLD_H / 2 + 150, z: lerp(Math.min(0.70, zEnd), zEnd, 0.75)},
    {at: 1.0, cx: WORLD_W / 2, cy: cyEnd, z: zEnd},
  ];
  const cam = camAt(t, camKeys);
  // the fly-over is a page camera, and carries its baseline unlock for the whole beat (runtime/pageCam2D): the
  // boards' type would otherwise step a pixel at a time against the boards it is printed on
  const unlock = useCamUnlock(camUnlock(camKeys.map((k) => ({at: k.at, x: k.cx, y: k.cy, s: k.z})), false));
  const world: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: WORLD_W, height: WORLD_H,
    transformOrigin: '0 0', transform: pageCamTransform({x: cam.cx, y: cam.cy, s: cam.z}, W, H, unlock)};
  const dots = [];
  for (let gx = 0; gx < 33; gx++) for (let gy = 0; gy < 20; gy++) dots.push(<circle key={`${gx}-${gy}`} cx={gx * 80 + 30} cy={gy * 80 + 30} r={1.8} fill={DOT} />);
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* data-bleed: the camera flies over a canvas larger than the frame, so during the sweep boards are
          cropped by the frame edge. At rest it has settled on the whole grid, inside the content zone. */}
      <div data-bleed style={world}>
        <svg width={WORLD_W} height={WORLD_H} style={{position: 'absolute', inset: 0, opacity: 0.7}}>{dots}</svg>
        {boards.map((b, i) => <Artboard key={i} b={b} t={t} />)}
      </div>
      {/* screen-fixed HUD — rides the frame, not the canvas */}
    </AbsoluteFill>
  );
};
export default CollaborativeCursors;
