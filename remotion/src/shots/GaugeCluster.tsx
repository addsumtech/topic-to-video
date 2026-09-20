// SHOT · Gauge Cluster — a dashboard of circular gauges: the satellites sweep their arcs first, then the HERO
// gauge sweeps a 270° arc, its needle rising to the readout, and the big value counts up + locks. The
// "instrument panel / live status" register (family D). The value is number-bearing → a real film passes a
// SOURCED figure (see NUM guard). Deterministic.
//
// EVERY ARC IS A FRACTION THE FILM STATED, AND EVERY GAUGE IS ONE THE FILM GAVE. Four things were drawn here
// that no film supplied:
//  • the readout was `Math.round(parseFloat(value.replace(/[^\d.]/g, '')) * sweep)`: '4.2' printed 4, '99.9'
//    printed 100, '-12' printed 12 and '1.5k' printed 2. It now goes through runtime/figure.ts — the settled
//    frame is the film's string, and only a string that is exactly one number counts up.
//  • the hero arc ALWAYS read the value as a percentage of 100, so '350' ms drew a full gauge and '0.8' s an
//    empty one. The arc now comes from `fill` (a stated 0-1 fraction), or from the value itself only when the
//    film wrote it AS a percentage (unit '%' or a '%' suffix) between 0 and 100 — a percentage is by definition a
//    fraction of 100, anything else has no full scale this register could know. Otherwise there is no fill arc
//    and no needle: an empty track with the figure in it, never a needle pointing at a made-up position.
//  • a satellite with no `fill` swept to an invented 60% / 50% (`SATS[0]?.fill ?? 0.6`), and a film with fewer
//    than two gauges still got two, unlabelled, sweeping. The cluster now draws exactly the gauges passed (0-2),
//    laid out for that count; a gauge without a label or a fraction THROWS.
//  • the demo value/unit ('98' '%') completed films that passed only a title or gauges. The illustrative
//    98% uptime appears only when the register receives none of its content props at all.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY, fitTextPx, textWidthPx} from '../runtime/layout';
import {parseFigure, figureAt, figureText, figureValue} from '../runtime/figure';

const BG = '#0a0c13', ACC0 = '#37d4a6';
export const DURATION = 145; // ~4.8s
export const MAX_SATELLITE_GAUGES = 2;

type GaugeSpec = {label?: string; fill?: number};

const DEFAULT_GAUGES: GaugeSpec[] = [{label: 'latency', fill: 0.62}, {label: 'load', fill: 0.44}];

const arcPath = (cx: number, cy: number, r: number, a0: number, a1: number) => {
  const p = (a: number) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${x0} ${y0} A${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
};

const readFraction = (v: unknown, what: string): number => {
  const n = typeof v === 'number' ? v : NaN;
  if (!Number.isFinite(n) || n < 0 || n > 1) {
    throw new Error(`GaugeCluster: ${what} needs \`fill\` as a fraction 0-1 of the gauge's full scale (got ` +
      `${JSON.stringify(v)}). A gauge arc is a claim about how full something is; pass the sourced fraction ` +
      '(0.62, not 62), or leave the gauge out.');
  }
  return n;
};

// `fill` = null draws the empty track only: no arc, no needle.
// THE DIAL'S OWN INK IS THE FILM'S. The track, the needle, its hub, the readout and the label were five
// literals, and four of them were near-white — so on a film grounded paper the NUMBER this register exists to
// show (#fff, 1.11:1) and the needle pointing at it (#e7ebf7, 1.08:1) were both drawn white on white, leaving
// a coloured arc with nothing in it. They are passed in rather than read here so the Gauge stays a pure
// function of its props.
const Gauge: React.FC<{cx: number; cy: number; r: number; fill: number | null; tone: string; label: string;
  labelPx: number; big?: string; bigPx?: number; unit?: string;
  track: string; ink: string; meta: string; bigInk?: string}> = ({
  cx, cy, r, fill, tone, label, labelPx, big, bigPx, unit, track, ink, meta, bigInk}) => {
  const START = Math.PI * 0.75, SWEEP = Math.PI * 1.5; // 270°, bottom gap
  const a1 = fill == null ? START : START + SWEEP * clamp01(fill);
  const needle = a1;
  const numPx = bigPx ?? r * 0.42;
  return (
    <g>
      <path d={arcPath(cx, cy, r, START, START + SWEEP)} fill="none" stroke={track} strokeWidth={r * 0.16} strokeLinecap="round" />
      {fill == null ? null : (
        <>
          <path d={arcPath(cx, cy, r, START, a1)} fill="none" stroke={tone} strokeWidth={r * 0.16} strokeLinecap="round"
            style={{filter: `drop-shadow(0 0 ${r * 0.06}px ${tone})`}} />
          <line x1={cx} y1={cy} x2={cx + r * 0.72 * Math.cos(needle)} y2={cy + r * 0.72 * Math.sin(needle)}
            stroke={ink} strokeWidth={r > 130 ? 6 : 4} strokeLinecap="round" />
          <circle cx={cx} cy={cy} r={r * 0.09} fill={ink} />
        </>
      )}
      {big ? (
        <text x={cx} y={cy + r * 0.42} textAnchor="middle" fill={bigInk ?? ink}
          style={{font: `800 ${numPx}px var(--f-display, Inter, system-ui, sans-serif)`}}>{big}<tspan fill={tone} style={{font: `800 ${numPx * 0.24 / 0.42}px var(--f-display, Inter)`}}>{unit}</tspan></text>
      ) : null}
      <text x={cx} y={cy + r * 1.42} textAnchor="middle" fill={meta}
        style={{font: `600 ${labelPx}px var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.1em'}}>{label}</text>
    </g>
  );
};

export const GaugeCluster: React.FC<{value?: string; unit?: string; label?: string; fill?: number;
  gauges?: GaugeSpec[]; title?: string}> = ({
  // `label`, `title` and `gauges` are each bound twice: the `*Given` names are what the film actually passed
  // (undefined when it passed nothing), the defaulted names carry the preview copy the demo-copy gate lists.
  // Only "nothing passed at all" unlocks the preview's illustrative 98% uptime.
  value, unit, fill, label: labelGiven, label: LABEL = 'uptime', title: titleGiven, title: TITLE = 'System health',
  gauges: gaugesGiven, gauges: SATS = DEFAULT_GAUGES} = {}) => {
  const t = useT();
  const dna = useDNA(); const ACC = dna?.accent ?? ACC0;   // inherit the film's Design DNA (else original look)
  // Each literal keeps its OWN fallback — the readout's #fff and the needle's #e7ebf7 were two different
  // whites and collapsing them onto one would move the un-themed render.
  const TRACK = dna?.line ?? '#20263a';        // the empty scale: furniture, so it follows `line`
  const INK = dna?.fg ?? '#e7ebf7';            // needle + hub
  const BIG_INK = dna?.fg ?? '#fff';           // the figure itself
  const META = dna?.dim ?? '#8b93a8';          // each gauge's label
  const TITLE_INK = dna?.dim ?? '#aeb6ca';
  const {width: W, height: H} = useVideoConfig();

  const standalone = [value, unit, fill, labelGiven, titleGiven, gaugesGiven].every((v) => v === undefined);
  const VALUE = standalone ? '98' : figureText(value);
  const UNIT = standalone ? '%' : (unit ?? '');
  if (!Array.isArray(SATS) || SATS.length > MAX_SATELLITE_GAUGES) {
    throw new Error(`GaugeCluster draws the hero plus at most ${MAX_SATELLITE_GAUGES} satellite \`gauges\` (got ` +
      `${Array.isArray(SATS) ? SATS.length : typeof SATS}). More readings than that is a table or a bar list — ` +
      'use TermBars; pass [] for a hero gauge alone.');
  }
  const sats = SATS.map((g, i) => {
    const glabel = String(g?.label ?? '').trim();
    if (!glabel) throw new Error(`GaugeCluster: gauge ${i + 1} has no \`label\` — an unlabelled dial says nothing.`);
    return {label: glabel, fill: readFraction(g?.fill, `gauge ${i + 1} ("${glabel}")`)};
  });

  // THE HERO'S ARC: a stated fraction, else a stated percentage, else none (see header).
  let heroTarget: number | null = null;
  if (fill !== undefined) heroTarget = readFraction(fill, 'the hero gauge');
  else {
    const fig = parseFigure(VALUE);
    const pctUnit = /^[%％]$/.test(UNIT.trim()) || (!UNIT.trim() && /^[%％]$/.test(fig.suffix.trim()));
    const pct = pctUnit ? figureValue(VALUE) : null;
    if (pct != null && pct >= 0 && pct <= 100) heroTarget = pct / 100;
  }

  // EVERY OFFSET IN THIS CLUSTER WAS A 1920-WIDE NUMBER. It is 580px from the centre to the outer edge of a
  // side gauge (470 to its centre, plus its 110 radius) against a 540px half-frame at 1:1 — so both side
  // gauges hung off the edge with their labels cut, at 1:1, 4:5 AND 9:16. The type gate never said so
  // because what is cut is an ARC, and it measures text. Scale the cluster to the room it has.
  const HALF = 470 + 110;                                  // the cluster's half-width as drawn
  const S = Math.min(1, (W / 2 - 40) / HALF);
  const rHero = 210 * S, rSide = 110 * S, off = 470 * S;
  // and the hero's label is a BASELINE r*1.42 below the centre, so the centre yields where the band is
  // taller — 31px of 'uptime' was inside it at 1:1.
  const cy = Math.min(H / 2 + 20, bottomTextY(W, H) - rHero * 1.42);
  // LAID OUT FOR THE COUNT: two satellites flank the hero; one sits to its right with the pair centred as a
  // group; none leaves the hero alone in the middle.
  const heroX = sats.length === 1 ? W / 2 - (off + rSide - rHero) / 2 : W / 2;
  const satX = sats.length === 1 ? [heroX + off] : [heroX - off, heroX + off];
  const satTone = [dna?.accent2 ?? '#5b8cff', dna?.dim ?? '#f6a531'];

  // The sweep settles by t = 0.5, so the true figure is on screen for the back half of the beat — including the
  // mid-scene frame the delivery gate captures (it used to be mid-count there, reading a number nobody gave).
  const heroP = easeOutExpo(seg(t, 0.26, 0.5));
  const shown = VALUE ? figureAt(parseFigure(VALUE), heroP) : '';
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));

  // type fitted to the film's copy — a Chinese label or a long figure ran out of its gauge
  const satLabelPx = Math.max(12, Math.min(...sats.map((g) => fitTextPx(g.label, rSide * 2.6, 24, {usable: 1, track: 0.1})), 24));
  const heroLabelPx = fitTextPx(LABEL, rHero * 2.8, 24, {usable: 1, track: 0.1});
  const bigPer = textWidthPx(VALUE, 1) + (UNIT ? textWidthPx(UNIT, 0.24 / 0.42) : 0);
  const bigPx = Math.max(16, Math.min(rHero * 0.42, Math.floor((rHero * 1.5) / Math.max(0.1, bigPer))));
  const titlePx = fitTextPx(TITLE, W * 0.9, 30, {usable: 1, track: 0.3});

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 50% 40%, #12182c, ${BG} 72%)`}}>
      {TITLE ? <div style={{position: 'absolute', top: 74, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: TITLE_INK, font: `700 ${titlePx}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div> : null}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {sats.map((g, i) => (
          <Gauge key={i} cx={satX[i]} cy={cy} r={rSide} labelPx={satLabelPx}
            fill={easeOutExpo(seg(t, 0.1 + i * 0.06, 0.36 + i * 0.06)) * g.fill}
            tone={satTone[i]} label={g.label} track={TRACK} ink={INK} meta={META} />
        ))}
        <Gauge cx={heroX} cy={cy} r={rHero} labelPx={heroLabelPx}
          fill={heroTarget == null ? null : heroP * heroTarget}
          tone={ACC} label={LABEL} big={shown} bigPx={bigPx} unit={UNIT}
          track={TRACK} ink={INK} meta={META} bigInk={BIG_INK} />
      </svg>
    </AbsoluteFill>
  );
};
export default GaugeCluster;
