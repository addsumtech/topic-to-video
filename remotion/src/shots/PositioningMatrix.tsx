// SHOT · Positioning Matrix — a 2×2 map: X and Y axes draw through the centre, labelled at their ends, then
// item dots drift to their positions and a HERO dot (if the film marks one) lands with a ring + label, its
// quadrant tinted. The "where things sit / who leads" register (family H — comparison). Positions are
// QUALITATIVE; no numeric axis, so nothing is asserted as a stat. Deterministic.
//
// THE MAP DRAWS ONLY WHERE THE FILM PUT THINGS. Three defaults made claims of their own:
//   * the TOP-RIGHT quadrant was always tinted as the winning corner, even when the film's hero sat bottom-left
//     or there was no hero at all — the frame said "up and to the right wins" about any pair of axes;
//   * an item without coordinates was plotted with `x ?? 0.5`, `y ?? 0.5`: dead centre, a position the film
//     never gave, drawn as exactly as a real one (and a coordinate outside 0..1 was silently clamped to an edge);
//   * a label of one character was hidden (`label.length > 1`), which dropped a Chinese name like 「我」 while
//     still drawing its dot.
// Now the tint goes to the quadrant each hero actually sits in (none without a hero, none for a hero on an
// axis), x and y are required in 0..1 and anything else throws, and every label given is drawn.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

type Item = {label?: string; x?: number; y?: number; hero?: boolean};

export const DURATION = 150; // 5s
// Past eight dots the labels start landing on each other in the quadrants they share.
export const MAX_MATRIX_ITEMS = 8;

const normaliseItems = (items: unknown): (Item & {x: number; y: number})[] => {
  if (!Array.isArray(items) || items.length < 1 || items.length > MAX_MATRIX_ITEMS) {
    throw new Error(`PositioningMatrix needs 1-${MAX_MATRIX_ITEMS} \`items\` (got ${Array.isArray(items) ? items.length : typeof items}). ` +
      'Past eight the labels collide — keep the ones the comparison is about.');
  }
  return items.map((it: any, i: number) => {
    const label = it?.label == null ? undefined : String(it.label).trim() || undefined;
    const name = label ? `"${label}"` : `item ${i + 1}`;
    for (const k of ['x', 'y'] as const) {
      const v = it?.[k];
      if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 1) {
        throw new Error(`PositioningMatrix: ${name} needs \`${k}\` as a number from 0 to 1 (got ${JSON.stringify(v)}). ` +
          'A dot is a claim about where the thing sits; it is never placed at a default position.');
      }
    }
    return {label, x: it.x, y: it.y, hero: it?.hero === true};
  });
};

export const PositioningMatrix: React.FC<{
  title?: string; xAxis?: [string, string]; yAxis?: [string, string]; items?: Item[]}> = ({
  title: TITLE = 'The landscape', xAxis: XA = ['Simple', 'Powerful'], yAxis: YA = ['Manual', 'Automated'],
  items: ITEMS = [{label: 'A', x: 0.28, y: 0.34}, {label: 'B', x: 0.4, y: 0.6}, {label: 'C', x: 0.56, y: 0.3},
    {label: 'Us', x: 0.8, y: 0.82, hero: true}]} = {}) => {
  const items = normaliseItems(ITEMS);
  const n = items.length;
  const t = useT();
  const dna = useDNA();
  // A MATRIX IS ALL INK AND IT WAS ALL LITERAL. The hero's label (#eef2ff), the title (#aeb6ca), the axis end
  // labels and every other item's label (#8b93a8) were near-white or near-grey, so on a film grounded paper
  // 98% of this register's marks fell under 3:1 — measured — and the one thing it exists to say, WHICH DOT IS
  // US, had no name beside it. Each literal keeps its own fallback: the hero's white and the metadata grey are
  // two different decisions and collapsing them would move the un-themed render.
  const TITLE_INK = dna?.dim ?? '#aeb6ca';
  const AXIS_INK = dna?.dim ?? '#8b93a8';
  const AXIS_LINE = dna?.line ?? '#39405c';
  const HERO_TONE = dna?.accent ?? '#5b8cff';
  const REST_TONE = dna?.dim ?? '#5a6478';
  const HERO_INK = dna?.fg ?? '#eef2ff';
  const REST_INK = dna?.dim ?? '#8b93a8';
  const HERO_RING = dna?.fg ?? '#cdd8ff';
  const {width: W, height: H} = useVideoConfig();
  // Centred on the CONTENT ZONE, not the frame, and scaled to it. Centred on H/2 with a fixed radius the
  // lowest node landed inside the strip the renderer burns the caption over, so a node label and a subtitle
  // drew on top of each other. Deriving both from the zone also makes the layout right at aspects the fixed
  // radius was never checked against.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const AXIS_ROOM = 52;                                      // the axis end label under the plot
  const PLOT = Math.min(760, (zBot - zTop) - AXIS_ROOM * 2);
  const cx = W / 2, cy = (zTop + zBot) / 2;
  const x0 = cx - PLOT / 2, y0 = cy - PLOT / 2;
  const px = (x: number) => x0 + clamp01(x) * PLOT;
  const py = (y: number) => y0 + (1 - clamp01(y)) * PLOT; // y up
  const axis = easeOutCubic(seg(t, 0.08, 0.4));
  const titleIn = easeOutCubic(seg(t, 0.02, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 100% at 50% 42%, #12162a, #090b12 72%)'}}>
      <div style={{position: 'absolute', top: 62, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: TITLE_INK, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* the quadrant each HERO sits in — never a fixed corner; none without a hero or for a hero on an axis */}
        {Array.from(new Set(items.filter((it) => it.hero && it.x !== 0.5 && it.y !== 0.5)
            .map((it) => `${it.x > 0.5 ? 1 : 0}${it.y > 0.5 ? 1 : 0}`))).map((q) => (
          <rect key={q} x={q[0] === '1' ? cx : x0} y={q[1] === '1' ? y0 : cy} width={PLOT / 2} height={PLOT / 2}
            fill={`${HERO_TONE}10`} opacity={clamp01(seg(t, 0.5, 0.7))} />
        ))}
        {/* axes */}
        <line x1={x0} y1={cy} x2={x0 + PLOT * axis} y2={cy} stroke={AXIS_LINE} strokeWidth={2} />
        <line x1={cx} y1={y0 + PLOT} x2={cx} y2={y0 + PLOT - PLOT * axis} stroke={AXIS_LINE} strokeWidth={2} />
        {/* arrowheads */}
        <path d={`M${x0 + PLOT} ${cy} l-16 -8 l0 16 z`} fill={AXIS_LINE} opacity={axis} />
        <path d={`M${cx} ${y0} l-8 16 l16 0 z`} fill={AXIS_LINE} opacity={axis} />
      </svg>

      {/* axis end labels */}
      {([[XA[1], px(1) + 6, cy - 12, 'left'], [XA[0], x0 - 6, cy - 12, 'right'],
         [YA[1], cx + 16, y0 - 4, 'left'], [YA[0], cx + 16, y0 + PLOT + 6, 'left']] as const).map((L, i) => (
        <div key={i} style={{position: 'absolute', left: L[1], top: L[2], transform: L[3] === 'right' ? 'translateX(-100%)' : undefined,
          opacity: clamp01(seg(t, 0.3, 0.5)), color: AXIS_INK, font: '600 24px/1 var(--f-mono, "JetBrains Mono", monospace)',
          letterSpacing: '0.1em'}}>{L[0]}</div>
      ))}

      {/* item dots */}
      {items.map((it, i) => {
        // the stagger closes up with the count so the last dot has landed by the end (four keep 0.1)
        const st = 0.42 + i * Math.min(0.1, 0.3 / Math.max(1, n - 1));
        const r = easeOutBack(clamp01(seg(t, st, st + 0.24)));
        const X = px(it.x), Y = py(it.y);
        const hero = !!it.hero;
        const size = hero ? 34 : 20;
        const col = hero ? HERO_TONE : REST_TONE;
        const pulse = hero && t > st + 0.24 ? 1 + 0.12 * Math.max(0, Math.sin((t - st - 0.24) * 10)) * Math.exp(-(t - st - 0.24) * 3) : 1;
        return (
          <div key={i} style={{position: 'absolute', left: X, top: Y, transform: `translate(-50%,-50%) scale(${r * pulse})`}}>
            <div style={{width: size, height: size, borderRadius: '50%', background: col,
              boxShadow: hero ? `0 0 30px ${col}` : 'none', border: hero ? `3px solid ${HERO_RING}` : 'none'}} />
            {it.label ? (
              <div style={{position: 'absolute', left: size / 2 + 14, top: -4, whiteSpace: 'nowrap',
                color: hero ? HERO_INK : REST_INK, font: `${hero ? '800' : '600'} ${hero ? 32 : 22}px/1 var(--f-body, Inter, system-ui, sans-serif)`}}>{it.label}</div>
            ) : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default PositioningMatrix;
