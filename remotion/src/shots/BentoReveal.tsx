// SHOT · Bento Reveal — a modern bento grid (a big hero cell + smaller cells) whose tiles pop in one by one and
// assemble into a finished surface. The 2026 SaaS "product surface" register (family A). Deterministic.
//
// EVERY PICTURE IN A CELL IS ONE THE FILM CHOSE. This register used to fill each small cell with a mini-widget
// — bars / ring / sparkline / dots / avatars / toggle — picked by the cell's POSITION (`kind={(i - 1) % 6}`),
// with bar heights and a gauge fill computed from the index and the clock. No prop could reach them. A film
// about anime characters handed it six names and shipped a sparkline under one and a 70% gauge under another,
// and a user asked, correctly, what a sine wave has to do with 路飞. The widgets were not decoration: a bar
// chart under a label is a claim about that label, and nobody had made it. The labels also CYCLED
// (`ITEMS[(i - 1) % ITEMS.length]`), so a film that gave three items printed each of them twice.
//
// So a cell now draws exactly what its item carries: its `label`, the `icon` the film picked for it (an
// IconName — the icon rule in references/remotion-shot-authoring.md applies: pick by the role the item plays),
// and an optional `detail` line. A cell with no icon draws no picture and gives the label the room. The grid
// has as many cells as there are items (1-6), laid out for that count, so nothing is ever printed twice.
//
// THE CELLS STILL LIVE, and what moves now means something. A dashboard that freezes the instant it finishes
// assembling reads as a screenshot (measured by quarter this register once ran 0.0061 -> 0.0002). The widgets
// used to keep "reading", which was the invented data moving. What moves now is a slow FOCUS that walks the
// cells in reading order after they land — "this one, and this one, and this one" — which is the claim a grid
// of items actually makes. It drives CONTENT properties (a cell's edge and wash), never a transform of the
// frame, so scripts/shake_qa.py has nothing to see.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeInOutCubic} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, dnaPalette, mix} from '../runtime/dna';
import {Icon, type IconName} from '../runtime/icons';
import {CONTENT_TOP, contentBottom, fitTextPx, wrapLines, inkBlockH} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

const BG_D0 = '#0a0c12';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff'];
export const DURATION = 150; // 5s

export type BentoCell = {
  /** what this cell is */
  label: string;
  /** the picture that says what KIND of thing it is — chosen by the film, never by position */
  icon?: IconName;
  /** one short line under the label (a sourced figure belongs here as text, never as a drawn chart) */
  detail?: string;
};

export const MAX_BENTO_CELLS = 6;

// [col,row,wSpan,hSpan] on a 12x6 grid, index 0 is the hero, laid out PER COUNT so every item gets its own cell.
const LAYOUTS: Record<number, number[][]> = {
  1: [[0, 0, 7, 6], [7, 0, 5, 6]],
  2: [[0, 0, 7, 6], [7, 0, 5, 3], [7, 3, 5, 3]],
  3: [[0, 0, 6, 6], [6, 0, 6, 2], [6, 2, 6, 2], [6, 4, 6, 2]],
  4: [[0, 0, 6, 6], [6, 0, 3, 3], [9, 0, 3, 3], [6, 3, 3, 3], [9, 3, 3, 3]],
  5: [[0, 0, 6, 4], [6, 0, 3, 2], [9, 0, 3, 2], [6, 2, 6, 2], [0, 4, 6, 2], [6, 4, 6, 2]],
  6: [[0, 0, 6, 4], [6, 0, 3, 2], [9, 0, 3, 2], [6, 2, 6, 2], [0, 4, 3, 2], [3, 4, 3, 2], [6, 4, 6, 2]],
};

// Portrait gets its OWN layouts on a 6x12 grid rather than a transpose of the landscape ones: a transpose keeps
// the cells' areas but scrambles reading order (item 1 landed bottom-left), and the focus walk follows item
// order, so it hopped around the frame. These read top-to-bottom, left-to-right, like the landscape set.
const LAYOUTS_PORTRAIT: Record<number, number[][]> = {
  1: [[0, 0, 6, 7], [0, 7, 6, 5]],
  2: [[0, 0, 6, 6], [0, 6, 6, 3], [0, 9, 6, 3]],
  3: [[0, 0, 6, 6], [0, 6, 6, 2], [0, 8, 6, 2], [0, 10, 6, 2]],
  4: [[0, 0, 6, 6], [0, 6, 3, 3], [3, 6, 3, 3], [0, 9, 3, 3], [3, 9, 3, 3]],
  5: [[0, 0, 6, 4], [0, 4, 3, 3], [3, 4, 3, 3], [0, 7, 6, 2], [0, 9, 3, 3], [3, 9, 3, 3]],
  6: [[0, 0, 6, 4], [0, 4, 3, 3], [3, 4, 3, 3], [0, 7, 3, 3], [3, 7, 3, 3], [0, 10, 3, 2], [3, 10, 3, 2]],
};

const DEFAULT_ITEMS: BentoCell[] = [
  {label: 'Docs', icon: 'file'}, {label: 'Sheets', icon: 'table'}, {label: 'Search', icon: 'search'},
  {label: 'Team', icon: 'users'}, {label: 'Messages', icon: 'message'}, {label: 'Code', icon: 'code'},
];

const normalise = (items: (string | BentoCell)[]): BentoCell[] => {
  if (!Array.isArray(items) || items.length < 1 || items.length > MAX_BENTO_CELLS) {
    throw new Error(
      `BentoReveal needs 1-${MAX_BENTO_CELLS} \`items\` (got ${Array.isArray(items) ? items.length : typeof items}). ` +
      'Each item gets its own cell; the grid is laid out for the count, and it never repeats an item to fill ' +
      'a slot. More than six is a list, not a bento — use a list register.');
  }
  return items.map((it, i) => {
    const cell: BentoCell = typeof it === 'string' ? {label: it} : {...(it ?? {label: ''})};
    cell.label = String(cell.label ?? '').trim();
    if (!cell.label) throw new Error(`BentoReveal: item ${i + 1} has no label.`);
    cell.detail = String(cell.detail ?? '').trim() || undefined;
    return cell;
  });
};

export const BentoReveal: React.FC<{title?: string; hero?: string; items?: (string | BentoCell)[]; heroKicker?: string}> = ({
  title: TITLE = 'WorkBuddy', hero: HEROSUB = 'your workspace, assembled',
  // The hero cell's kicker used to be the literal string 'DASHBOARD', hardcoded — so every film that
  // reached for this register printed a product-demo word onto its own frame whatever it was about.
  heroKicker: HEROKICKER = 'DASHBOARD', items: ITEMS = DEFAULT_ITEMS} = {}) => {
  const cells = normalise(ITEMS);
  const n = cells.length;
  const dna = useDNA();
  const TONES = dnaPalette(dna, 5) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const BG = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? '#eef1f8';
  const DIM = dna?.dim ?? '#8b93a8';
  const EDGE = dna?.line ?? '#20243a';
  const MONO = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", monospace)';
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const U = Math.min(W, H);
  const portrait = H > W * 1.1;

  // The grid lives in the CONTENT ZONE, so the bottom row never sits in the burned caption band.
  const padX = Math.round(W * 0.0625);
  const top = Math.max(CONTENT_TOP, Math.round(U * 0.09));
  const bot = contentBottom(W, H) - Math.round(U * 0.02);
  const gap = Math.round(U * 0.02);
  const gw = W - padX * 2, gh = Math.max(U * 0.4, bot - top);
  const cols = portrait ? 6 : 12, rows = portrait ? 12 : 6;
  const u = gw / cols, v = gh / rows;
  const layout = (portrait ? LAYOUTS_PORTRAIT : LAYOUTS)[n];

  // THE FOCUS WALK. Cells land by ~0.06 + n*0.1 + 0.26; after that one cell at a time is lit, in reading
  // order, with an eased hand-off. Deterministic in t. A single cell has no walk: it simply stays lit.
  const landed = 0.06 + n * 0.1 + 0.2;
  const seconds = Math.max(0, t - landed) * (durationInFrames / Math.max(1, fps));
  const DWELL_S = 1.1;
  const pos = seconds / DWELL_S;
  const focusOf = (k: number) => {
    if (t < landed) return 0;
    if (n === 1) return clamp01(seconds / 0.6);
    const d = ((pos - k) % n + n) % n;               // how far past cell k the walk is, in cells
    const on = easeInOutCubic(clamp01(d / 0.35));      // hand-on
    const off = easeInOutCubic(clamp01((d - 1) / 0.35)); // hand-off to the next cell
    return clamp01(on - off);
  };

  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 30% 20%, ${dna ? mix(BG, dna.accent, 0.12) : '#12162a'}, ${BG} 72%)`}}>
      {layout.map((L, i) => {
        const [c, r, ws, hs] = L;
        const x = padX + c * u + gap / 2, y = top + r * v + gap / 2;
        const w = ws * u - gap, h = hs * v - gap;
        const st = 0.06 + i * 0.1;
        const e = easeOutBack(clamp01(seg(t, st, st + 0.26)));
        const hero = i === 0;
        const tone = TONES[i % TONES.length];
        const pad = Math.round(Math.max(16, Math.min(w * 0.08, h * 0.12, hero ? U * 0.05 : U * 0.032)));
        const common: React.CSSProperties = {position: 'absolute', left: x, top: y, width: w, height: h,
          boxSizing: 'border-box', opacity: clamp01(e * 1.4), transform: glide(`scale(${lerp(0.86, 1, e)})`, e !== 1),
          transformOrigin: 'center', borderRadius: Math.round(U * 0.02), overflow: 'hidden', padding: pad,
          display: 'flex', flexDirection: 'column', boxShadow: '0 24px 60px #0006'};

        if (hero) {
          const kickPx = Math.round(U * 0.022);
          const subPx = fitTextPx(HEROSUB, w - 2 * pad, Math.round(U * 0.03), {usable: 0.95});
          const titleCap = Math.round(Math.min(U * 0.09, h * 0.3));
          const titlePx = fitTextPx(TITLE, w - 2 * pad, titleCap, {usable: 0.95});
          return (
            <div key={i} style={{...common, justifyContent: 'space-between', border: '1px solid transparent',
              background: `linear-gradient(150deg, ${tone}, ${dna ? mix(tone, BG, 0.55) : '#2c3ac0'})`}}>
              <div style={{color: dna?.onAccent ?? '#ffffffcc', font: `600 ${kickPx}px/1 ${MONO}`,
                letterSpacing: dna?.labelSpacing ?? '0.14em'}}>{HEROKICKER}</div>
              <div>
                <div style={{color: '#fff', textWrap: 'balance', letterSpacing: '-0.03em',
                  font: `800 ${titlePx}px/${leading(TITLE, 1)} var(--f-display, Inter, system-ui, sans-serif)`}}>{TITLE}</div>
                <div style={{color: '#ffffffdd', marginTop: Math.round(U * 0.015), textWrap: 'balance',
                  font: `500 ${subPx}px/${leading(HEROSUB, 1.2)} var(--f-body, Inter, system-ui, sans-serif)`}}>{HEROSUB}</div>
              </div>
            </div>
          );
        }

        const cell = cells[i - 1];
        const lit = focusOf(i - 1);
        const innerW = w - 2 * pad, innerH = h - 2 * pad;
        // Sizes come from the cell: the icon takes up to ~45% of the cell's height, the label fits the width
        // on at most two lines, and without an icon the label is given the room the picture would have had.
        const hasIcon = !!cell.icon;
        const detailPx = cell.detail ? Math.max(12, Math.round(Math.min(U * 0.019, innerH * 0.12))) : 0;
        const detailH = cell.detail ? inkBlockH(detailPx, Math.min(2, wrapLines(cell.detail, detailPx, innerW))) : 0;
        const labelCap = Math.round(Math.min(hasIcon ? U * 0.048 : U * 0.06, innerH * (hasIcon ? 0.22 : 0.34)));
        let labelPx = Math.max(14, labelCap);
        while (labelPx > 14 && wrapLines(cell.label, labelPx, innerW) > 2) labelPx -= 1;
        const labelH = inkBlockH(labelPx, Math.min(2, wrapLines(cell.label, labelPx, innerW)));
        const iconPx = hasIcon ? Math.max(18, Math.round(Math.min(innerH - labelH - detailH - U * 0.02, innerH * 0.45, innerW * 0.5, U * 0.14))) : 0;
        return (
          <div key={i} style={{...common, justifyContent: hasIcon ? 'space-between' : 'flex-end',
            background: dna ? `linear-gradient(160deg, ${mix(mix(dna.surface, BG, 0.35), tone, 0.10 * lit)}, ${BG})`
              : `linear-gradient(160deg, ${mix('#141724', tone, 0.10 * lit)}, #0d0f18)`,
            border: `1px solid ${mix(EDGE, tone, lit)}`}}>
            {hasIcon ? (
              <div style={{height: iconPx, flex: 'none', opacity: 0.72 + 0.28 * lit}}>
                <Icon name={cell.icon as IconName} size={iconPx} ink={tone} weight={1.9} />
              </div>
            ) : null}
            <div style={{flex: 'none'}}>
              <div style={{color: mix(DIM, FG, 0.55 + 0.45 * lit), textWrap: 'balance',
                font: `700 ${labelPx}px/${leading(cell.label, 1.2)} var(--f-display, Inter, system-ui, sans-serif)`}}>{cell.label}</div>
              {cell.detail ? (
                <div style={{color: DIM, marginTop: Math.round(U * 0.006), textWrap: 'balance',
                  font: `500 ${detailPx}px/${leading(cell.detail, 1.3)} ${MONO}`}}>{cell.detail}</div>
              ) : null}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default BentoReveal;
