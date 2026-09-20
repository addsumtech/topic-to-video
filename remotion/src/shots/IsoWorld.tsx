// SHOT · Iso World — an isometric diorama builds itself: a tiled ground grid draws in, then labelled BLOCKS
// (buildings) rise from it in an outward ripple, each a proper iso cube (shaded top/left/right faces). A
// little world / workspace-as-a-city (family N · isometric). Deterministic (rise = fn of t). True iso
// projection, painter's-ordered back-to-front.
//
// EVERY LABELLED BUILDING STANDS THE SAME HEIGHT. A block's height came from the same hash that decided whether
// its cell had a block (`hFrac: 0.5 + seed * 0.9`), so the film's labelled buildings ranged from 0.98 to 1.37 —
// "this item is 40% bigger than that one", about a list of names that says nothing of the kind. The labels
// also went to whichever hashed cells passed a second threshold, in scan order: there were thirteen such cells,
// so a fourteenth item was silently dropped, and the first five items all landed in the back rows where the
// chips collided ("Team" printed over "Code") above buildings hidden behind taller unlabelled ones.
//
// Now the film's items get their own cells, laid out for the count on a spread lattice (so no two chips share a
// row closer than two cells and no labelled block stands directly in front of another), every labelled
// building is one height, and the unlabelled filler — the city around them, which claims nothing — varies
// BELOW that height, so the film's buildings are never hidden. 1-9 items; more throws.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 165; // 5.5s
const BG_D0 = '#0a0d1a';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1'];
const G = 7, TW = 150, TH = 76;
export const MAX_ISO_ITEMS = 9;
const LABEL_H = 1.25;                         // every labelled building, as a fraction of the 150px unit
const FILLER_MIN = 0.3, FILLER_MAX = 0.85;    // the unlabelled city stays below the labelled buildings

// [i, j] grid cells per item count, on the odd lattice of the 7x7 ground. Screen x ~ (i - j), y ~ (i + j):
// cells on one screen row are >= 4 columns (300px) apart, adjacent rows are 2 steps (76px) apart. These are
// WHERE a building stands, chosen so no chip collides — not a reading about any item — hence the declarations
// for scripts/content_contract_qa.py, which reads a table of integer pairs as possibly-invented graph edges.
const SLOTS: Record<number, [number, number][]> = {
  1: [[3, 3]],  // @decor: layout cells, not data
  2: [[1, 5], [5, 1]],  // @decor: layout cells, not data
  3: [[1, 5], [3, 3], [5, 1]],  // @decor: layout cells, not data
  4: [[1, 3], [3, 1], [3, 5], [5, 3]],  // @decor: layout cells, not data
  5: [[1, 3], [3, 1], [3, 3], [3, 5], [5, 3]],  // @decor: layout cells, not data
  6: [[1, 3], [3, 1], [1, 5], [5, 1], [3, 5], [5, 3]],  // @decor: layout cells, not data
  7: [[1, 3], [3, 1], [1, 5], [3, 3], [5, 1], [3, 5], [5, 3]],  // @decor: layout cells, not data
  8: [[1, 1], [1, 3], [3, 1], [1, 5], [5, 1], [3, 5], [5, 3], [5, 5]],  // @decor: layout cells, not data
  9: [[1, 1], [1, 3], [3, 1], [1, 5], [3, 3], [5, 1], [3, 5], [5, 3], [5, 5]],  // @decor: layout cells, not data
};

export const IsoWorld: React.FC<{items?: string[]; title?: string}> = ({
  items: ITEMS = ['Docs', 'Chat', 'Data', 'Code', 'Team'], title: TITLE = 'Your world, built'} = {}) => {
  if (!Array.isArray(ITEMS) || ITEMS.length < 1 || ITEMS.length > MAX_ISO_ITEMS) {
    throw new Error(`IsoWorld needs 1-${MAX_ISO_ITEMS} \`items\` (got ${Array.isArray(ITEMS) ? ITEMS.length : typeof ITEMS}). ` +
      'Each item is one labelled building on a 7x7 ground; past nine the labels crowd each other — group them, ' +
      'or use a list register.');
  }
  const labels = ITEMS.map((x, k) => {
    const s = String(x ?? '').trim();
    if (!s) throw new Error(`IsoWorld: item ${k + 1} is empty.`);
    return s;
  });
  const dna = useDNA();
  const TONES = dnaPalette(dna, 6) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  // The blocks are the film's palette already; the CITY AROUND them was not. The empty ground diamonds and
  // the plinth under each block were two navy literals and the title a near-grey one, so on a film grounded
  // paper a dark checkerboard sat on white and the title measured 1.83:1. The chip under each label carries
  // its own dark fill and white ink, which is why the labels still read on paper — by accident, not design;
  // they take the film's surface and ink so the chip belongs to the film at either exposure.
  const TITLE_INK = dna?.dim ?? '#aeb6ca';
  const PLOT = dna?.surface ?? '#18203a';      // an empty tile
  const PLINTH = dna?.surface ?? '#141b32';    // the tile a block stands on
  const TILE_EDGE = dna?.line ?? '#26304f';
  const CHIP = dna?.surface ?? '#0e1426';
  const CHIP_INK = dna?.fg ?? '#eef2ff';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H * 0.4;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const pt = (sx: number, sy: number) => `${sx.toFixed(1)},${sy.toFixed(1)}`;

  const slotOf = new Map<string, number>();
  SLOTS[labels.length].forEach(([i, j], k) => slotOf.set(`${i},${j}`, k));

  type Cell = {i: number; j: number; sx: number; sy: number; block: boolean; hFrac: number; tone: string; label?: string};
  const cells: Cell[] = [];
  for (let i = 0; i < G; i++) for (let j = 0; j < G; j++) {
    const sx = cx + (i - j) * (TW / 2), sy = cy + (i + j) * (TH / 2);
    const seed = hash01(i * 12.7 + j * 31.3);
    const k = slotOf.get(`${i},${j}`);
    const tone = TONES[(i * 3 + j) % TONES.length];
    if (k != null) {
      cells.push({i, j, sx, sy, block: true, hFrac: LABEL_H, tone, label: labels[k]});
    } else {
      const block = seed > 0.52;
      // filler texture: its height is the seed rescaled into a band BELOW the labelled buildings
      // @decor: an unlabelled block names no item, so its height is texture, not a reading
      cells.push({i, j, sx, sy, block, hFrac: lerp(FILLER_MIN, FILLER_MAX, (seed - 0.52) / 0.48), tone});
    }
  }
  cells.sort((a, b) => a.i + a.j - (b.i + b.j)); // back-to-front
  const chipPx = Math.round(Math.min(26, ...labels.map((l) => fitTextPx(l, 250, 26, {usable: 1}))));

  return (
    // ...and the ground's lift followed nothing: only its outer stop read the DNA.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg
        ?? `radial-gradient(120% 100% at 50% 34%, #131a33, ${BG_D0} 74%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 76, left: 0, right: 0, textAlign: 'center', opacity: titleIn, zIndex: 5,
        color: TITLE_INK, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {cells.map((c, idx) => {
          const wave = (c.i + c.j) / (2 * G);
          const tileIn = easeOutCubic(clamp01(seg(t, 0.06 + wave * 0.3, 0.28 + wave * 0.3)));
          const {sx, sy} = c;
          // ground diamond
          const ground = `${pt(sx, sy - TH / 2)} ${pt(sx + TW / 2, sy)} ${pt(sx, sy + TH / 2)} ${pt(sx - TW / 2, sy)}`;
          if (!c.block) {
            return <polygon key={idx} points={ground} fill={PLOT} stroke={TILE_EDGE} strokeWidth={1}
              opacity={tileIn * 0.9} style={{transformBox: 'fill-box', transformOrigin: 'center', transform: `scale(${lerp(0.7, 1, tileIn)})`}} />;
          }
          const rise = easeOutBack(clamp01(seg(t, 0.2 + wave * 0.32, 0.5 + wave * 0.32)));
          const h = 150 * c.hFrac * rise;
          const T2 = sy - TH / 2 - h, Ry = sy - h, B2 = sy + TH / 2 - h, Ly = sy - h;
          const top = `${pt(sx, T2)} ${pt(sx + TW / 2, Ry)} ${pt(sx, B2)} ${pt(sx - TW / 2, Ly)}`;
          const leftF = `${pt(sx - TW / 2, sy)} ${pt(sx, sy + TH / 2)} ${pt(sx, B2)} ${pt(sx - TW / 2, Ly)}`;
          const rightF = `${pt(sx, sy + TH / 2)} ${pt(sx + TW / 2, sy)} ${pt(sx + TW / 2, Ry)} ${pt(sx, B2)}`;
          return (
            <g key={idx} opacity={clamp01(tileIn * 1.4)}>
              <polygon points={ground} fill={PLINTH} stroke={TILE_EDGE} strokeWidth={1} />
              <polygon points={leftF} fill={c.tone} style={{filter: 'brightness(0.6)'}} />
              <polygon points={rightF} fill={c.tone} style={{filter: 'brightness(0.82)'}} />
              <polygon points={top} fill={c.tone} style={{filter: 'brightness(1.15)'}} stroke="#ffffff44" strokeWidth={1} />
            </g>
          );
        })}
      </svg>

      {/* floating labels above the labelled buildings */}
      {cells.filter((c) => c.label).map((c, k) => {
        const wave = (c.i + c.j) / (2 * G);
        const rise = easeOutBack(clamp01(seg(t, 0.2 + wave * 0.32, 0.5 + wave * 0.32)));
        const h = 150 * c.hFrac * rise;
        const on = clamp01(seg(t, 0.5 + wave * 0.2, 0.7 + wave * 0.2));
        return (
          <div key={k} style={{position: 'absolute', left: c.sx, top: c.sy - TH / 2 - h - 54,
            transform: 'translate(-50%, 0)', opacity: on, zIndex: 4,
            padding: '8px 18px', borderRadius: 10, background: CHIP,
            border: `1px solid ${c.tone}`, color: CHIP_INK,
            font: `700 ${chipPx}px/${leading(c.label ?? '', 1)} var(--f-body, Inter, system-ui, sans-serif)`,
            whiteSpace: 'nowrap', boxShadow: '0 8px 24px #0008'}}>{c.label}</div>
        );
      })}
    </AbsoluteFill>
  );
};
export default IsoWorld;
