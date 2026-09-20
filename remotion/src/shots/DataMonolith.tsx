// SHOT · Data Monolith — a nighttime skyline of glowing data TOWERS rises from a perspective grid floor, each
// with a bright cap + a mirrored reflection. Data as architecture — bold, cinematic scale (family E · 3D /
// spatial). Deterministic (tower growth = fn of t).
//
// A TOWER'S HEIGHT IS A CLAIM ABOUT ITS LABEL. Heights came from `0.4 + hash01(i * 4.7) * 0.6` — a number
// hashed from the tower's POSITION — standing over the film's own labels under a default title that says
// "Everything, to scale". A film naming seven teams shipped a ranked bar chart of them that nobody measured,
// and `hero` defaulted to 3, so the fourth name was also forced to at least 90% height and pulsed as the
// winner. Labels past the ninth were dropped by `.slice(0, 9)` without a word.
//
// Now each item is `{label, value?, display?}` (or a bare label). With values, heights are drawn from zero in
// proportion to them (the film's figure strings are read through figureValue, and every value must be in the
// same unit), and the value is written above its tower so the scale is never left to be inferred. With no
// values every tower stands the SAME height — a skyline of equals, which is all a list of names says. `hero`
// defaults to none; a film that names one gets the accent and the pulse. 2-9 items; anything else throws.
//
// THE SKYLINE STILL LIVES. Without a hero nothing pulsed after the towers landed, and a still skyline reads as
// a screenshot. What moves is a slow band of light that crosses the caps in reading order, lighting every tower
// the same — it passes, it does not pick.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, inkBlockH, wrapLines, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {parseFigure, figureText} from '../runtime/figure';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#06070e', ACC_D0 = '#4db8ff', ACC2_D0 = '#a06bff';

export type MonolithItem = {
  label: string;
  /** the SOURCED quantity (a number or the film's figure string, e.g. "1.2M"); heights are drawn from zero */
  value?: number | string;
  /** how the value is written above the tower (defaults to the film's own figure text) */
  display?: string;
};

export const MIN_MONOLITH_TOWERS = 2;
export const MAX_MONOLITH_TOWERS = 9;

// The standalone preview only: illustrative values so the demo still reads as a skyline.
const DEFAULT_ITEMS: MonolithItem[] = [
  {label: 'Docs', value: 42}, {label: 'Chat', value: 65}, {label: 'Tasks', value: 38}, {label: 'Data', value: 90},
  {label: 'Code', value: 57}, {label: 'Calls', value: 30}, {label: 'Team', value: 48},
];

type Tower = {label: string; value: number | null; text: string | null};

const normalise = (items: unknown): Tower[] => {
  if (!Array.isArray(items) || items.length < MIN_MONOLITH_TOWERS || items.length > MAX_MONOLITH_TOWERS) {
    throw new Error(
      `DataMonolith needs ${MIN_MONOLITH_TOWERS}-${MAX_MONOLITH_TOWERS} \`items\` (got ` +
      `${Array.isArray(items) ? items.length : typeof items}). One tower is not a skyline — use a hero-number ` +
      'register; past nine the towers are too thin to label — group them or use a list register.');
  }
  const rows = items.map((it: any, i: number) => {
    const o = typeof it === 'string' ? {label: it} : (it ?? {});
    const label = String(o.label ?? '').trim();
    if (!label) throw new Error(`DataMonolith: item ${i + 1} has no label.`);
    return {label, raw: o.value, display: o.display == null ? null : String(o.display).trim() || null};
  });
  const valued = rows.filter((r) => r.raw != null && String(r.raw).trim() !== '');
  if (valued.length === 0) return rows.map((r) => ({label: r.label, value: null, text: null}));
  if (valued.length !== rows.length) {
    const missing = rows.filter((r) => !valued.includes(r)).map((r) => `"${r.label}"`).join(', ');
    throw new Error(`DataMonolith: some items have a value and ${missing} do not. Heights are drawn in proportion, ` +
      'so every tower needs its value — or pass none and every tower stands the same height.');
  }
  let unit: string | null = null;
  const out = rows.map((r) => {
    const fig = parseFigure(r.raw);
    if (fig.num == null || fig.num < 0) {
      throw new Error(`DataMonolith: "${r.label}" needs one number >= 0 as its value, got ${JSON.stringify(r.raw)}.`);
    }
    const u = `${fig.prefix.trim()}|${fig.suffix.trim()}`;
    if (unit != null && u !== unit) {
      throw new Error(`DataMonolith: values are in different units (${JSON.stringify(r.raw)} vs the first item's). ` +
        'Heights compare the numbers as written, so "1.2M" and "800k" would be drawn as 1.2 and 800 — convert them to one unit.');
    }
    unit = u;
    return {label: r.label, value: fig.num, text: r.display ?? figureText(r.raw)};
  });
  if (!out.some((r) => (r.value as number) > 0)) throw new Error('DataMonolith: every value is 0, so there is no height to draw.');
  return out;
};

export const DataMonolith: React.FC<{items?: (string | MonolithItem)[]; title?: string; hero?: number | null}> = ({
  items: ITEMS = DEFAULT_ITEMS,
  title: TITLE = 'Everything, to scale', hero: HERO = null} = {}) => {
  const towers = normalise(ITEMS);
  const n = towers.length;
  if (HERO != null && !(Number.isInteger(HERO) && HERO >= 0 && HERO < n)) {
    throw new Error(`DataMonolith: \`hero\` must be an index into \`items\` (0-${n - 1}) or omitted, got ${JSON.stringify(HERO)}.`);
  }
  const heroIdx = HERO;
  const valued = towers[0].value != null;
  const vmax = valued ? Math.max(...towers.map((w) => w.value as number)) : 1;
  const dna = useDNA();
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  // THE SKYLINE KEPT ITS BARS AND LOST ITS CATEGORIES. The towers are drawn in the film's accents, but every
  // word around them was a literal — the title (#aeb6ca), each value (#e6ecf8) and each tower's LABEL, which
  // is the only thing saying which bar is which. On a film grounded paper those labels sit on the paper and
  // measured 1.83:1 and below: a chart of six unnamed columns. The cap light on each tower was a flat
  // #ffffff, which is a lit edge on a dark skyline and nothing at all on white.
  const TITLE_INK = dna?.dim ?? '#aeb6ca';
  const VALUE_INK = dna?.fg ?? '#e6ecf8';
  const HERO_INK = dna?.fg ?? '#fff';
  const LABEL_INK = dna?.fg ?? '#aeb6ca';      // no hero named: every label is a full-strength label
  const MUTED_INK = dna?.dim ?? '#8b93a8';     // a hero IS named: the rest recede
  const CAP = dna?.fg ?? '#ffffff';
  const GRID = dna?.line ?? '#2b3a6e';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE FLOOR YIELDS TO THE LABELS UNDER IT. `H * 0.72` is a flat fraction and the labels hang 22px below
  // it, so the reserve is one line of type — in Chinese each band's label wraps in a column only
  // `min(150, (W-320)/n)` wide and the second line lands in the caption band (24px of it at 1:1). Counted by
  // breaking the copy in the band's own measure, so Latin is one line and the floor does not move.
  const bandW0 = Math.min(150, (W - 320) / Math.max(1, n));
  const labelBlock = 22 + inkBlockH(22, Math.max(1, ...towers.map((b) =>
    wrapLines(b.label, 22, bandW0))));
  const floorY = Math.min(H * 0.72, contentBottom(W, H) - labelBlock);
  const bandW = Math.min(150, (W - 320) / n), gap = 30;
  const rowW = n * bandW + (n - 1) * gap;
  const x0 = (W - rowW) / 2;
  const titleIn = easeOutCubic(seg(t, 0.04, 0.2));
  const VALUE_PX = 22, VALUE_ROOM = valued ? VALUE_PX + 14 : 0;
  const maxH = floorY - 150 - VALUE_ROOM;
  // the passing light: a soft band that crosses the row of caps left to right, the same for every tower
  const sweepOn = heroIdx == null ? clamp01(seg(t, 0.62, 0.72)) : 0;
  // one full pass, left to right, between the last tower landing and the end of the shot (row fractions -0.2..1.2)
  const sweepX = ((Math.max(0, t - 0.62) * 3.7) % 1.4) - 0.2;
  return (
    // ...AND THE GROUND'S LIFT FOLLOWED NOTHING: only the outer stop read the DNA, so a paper film got a navy
    // pool under its skyline with its own paper around the edge. The film's treatment, then its ground, then
    // the original well.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg
        ?? `radial-gradient(120% 90% at 50% 30%, #10162e, ${BG_D0} 72%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 74, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: TITLE_INK, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em',
        textTransform: 'uppercase', zIndex: 3}}>{TITLE}</div>

      {/* perspective floor grid */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g opacity={0.28}>
          {[...Array(13)].map((_, i) => {
            const fx = (i / 12) * W;
            return <line key={'v' + i} x1={lerp(W / 2, fx, 0.2)} y1={floorY} x2={fx} y2={H} stroke={GRID} strokeWidth={1} />;
          })}
          {[...Array(6)].map((_, i) => {
            const yy = lerp(floorY, H, (i / 5) ** 1.7);
            return <line key={'h' + i} x1={0} y1={yy} x2={W} y2={yy} stroke={GRID} strokeWidth={1} />;
          })}
        </g>
      </svg>

      {towers.map((tw, i) => {
        // the film's value in proportion, or the same height for every tower when the film gave none
        const hFrac = valued ? (tw.value as number) / vmax : 0.8;
        const isHero = i === heroIdx;
        const grow = easeOutExpo(clamp01(seg(t, 0.14 + i * 0.06, 0.5 + i * 0.06)));
        const th = maxH * hFrac * grow;
        const x = x0 + i * (bandW + gap);
        // ONE tone for every non-hero tower. Alternating two tones by index (`i % 2`) split any list into two
        // groups nobody named, and the even towers took the DNA's DIM ink — half the film's items de-emphasised.
        const tone = isHero ? ACC : heroIdx == null ? ACC : ACC2;
        const pulse = isHero && t > 0.6 ? 1 + 0.04 * Math.max(0, Math.sin((t - 0.6) * 9)) : 1;
        const centre = n === 1 ? 0.5 : i / (n - 1);
        const lit = sweepOn * Math.exp(-(((centre - sweepX) / 0.16) ** 2));
        return (
          <div key={i}>
            {/* tower */}
            <div style={{position: 'absolute', left: x, top: floorY - th, width: bandW, height: th,
              transform: `scaleY(${pulse})`, transformOrigin: 'bottom',
              background: `linear-gradient(${tone}, ${tone}22)`, borderRadius: '6px 6px 0 0',
              boxShadow: `0 0 ${Math.round(30 + 40 * lit)}px ${tone}${lit > 0.5 ? '99' : '55'}, inset 0 0 20px ${tone}44`,
              borderTop: `4px solid ${CAP}`, opacity: clamp01(grow * 1.4) * (th > 0 ? 1 : 0),
              filter: lit > 0.01 ? `brightness(${(1 + 0.25 * lit).toFixed(3)})` : undefined}} />
            {/* reflection */}
            <div style={{position: 'absolute', left: x, top: floorY, width: bandW, height: th * 0.5,
              background: `linear-gradient(${tone}55, #0000)`, borderRadius: '0 0 6px 6px',
              transform: 'scaleY(-1)', transformOrigin: 'top', opacity: 0.3 * grow, filter: 'blur(2px)'}} />
            {/* the value, written above its tower — only when the film supplied one */}
            {tw.text != null ? (
              <div style={{position: 'absolute', left: x - gap / 2, width: bandW + gap, textAlign: 'center',
                top: floorY - th * pulse - VALUE_ROOM, opacity: clamp01(seg(t, 0.4 + i * 0.06, 0.56 + i * 0.06)),
                color: VALUE_INK, whiteSpace: 'nowrap',
                font: `700 ${Math.max(12, Math.min(VALUE_PX, fitTextPx(tw.text, bandW + gap * 0.8, VALUE_PX, {usable: 1})))}px/1 ` +
                  'var(--f-mono, "JetBrains Mono", monospace)'}}>{tw.text}</div>
            ) : null}
            {/* label */}
            <div style={{position: 'absolute', left: x, top: floorY + 22, width: bandW, textAlign: 'center',
              opacity: clamp01(seg(t, 0.3 + i * 0.05, 0.5 + i * 0.05)),
              color: isHero ? HERO_INK : heroIdx == null ? LABEL_INK : MUTED_INK,
              font: `${isHero ? 800 : 600} 22px/${leading(tw.label, 1)} var(--f-body, Inter, system-ui, sans-serif)`}}>{tw.label}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default DataMonolith;
