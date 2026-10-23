// SHOT · Type on a Path — the beat's words travel a line that is the subject's own shape: a ring that turns for a
// cycle, a wave for a signal, a climb for growth, a figure-of-eight for a loop that feeds itself, or the film's own
// route. The words ride it letter by letter, each turned to the direction of travel, and come to rest on it.
//
// WHAT IT ARGUES. The shape is the claim. A cycle drawn as a ring of words that never stops turning says "this
// repeats" before anyone reads it; a phrase climbing a curve says "this rises". Hide the caption and the PATH still
// says which — which is why the path is chosen from the subject (`path`) or handed in as the film's own (`d`), never
// picked for looks. Not for a sequence of steps (a process register), not for one static claim (HeadlineReveal).
//
// HOW IT MOVES. Each glyph's centre is placed by arc length along the path at its own advance from the phrase's
// start (so the phrase keeps its kerning when it bends), rotated to the tangent there. The phrase travels in and
// eases onto its resting place; on a ring or a loop it keeps moving at a slow, constant speed the whole beat. The
// path itself draws on first, so the words have something to ride. A title — the one line that must be read —
// rises through its mask where the path leaves room.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, contrastOf, mix} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {useKinetic, KineticText, kineticPathLength} from '../runtime/kinetic';

export const DURATION = 180; // 6s

const BG_D0 = '#0b0e12', FG_D0 = '#eef1f5', DIM_D0 = '#8c94a4', ACC_D0 = '#5ee0b4';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

export type PathShape = 'orbit' | 'wave' | 'rise' | 'loop';
const SHAPES: PathShape[] = ['orbit', 'wave', 'rise', 'loop'];

/** The path for a shape, in frame px, inside the box [x0,x1]×[y0,y1]. */
const shapePath = (shape: PathShape, x0: number, x1: number, y0: number, y1: number, portrait: boolean): string => {
  const w = x1 - x0, h = y1 - y0, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  if (shape === 'orbit') {
    const R = Math.min(w, h) * 0.46;
    // from the left, clockwise: the words read upright across the TOP of the ring. FOUR quarter arcs, never two
    // halves: an exact half-circle arc names two possible semicircles, and @remotion/paths (which places the glyphs)
    // resolved it to the other one than the browser draws — the ring ran backwards, upside down across its top.
    return `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx} ${cy - R} A ${R} ${R} 0 0 1 ${cx + R} ${cy} ` +
      `A ${R} ${R} 0 0 1 ${cx} ${cy + R} A ${R} ${R} 0 0 1 ${cx - R} ${cy}`;
  }
  if (shape === 'wave') {
    // one wavelength on a narrow frame, one and a half on a wide one: the steepest tilt a word takes stays readable
    const periods = portrait ? 1 : 1.5, A = Math.min(h * 0.34, w * 0.075), n = 96;
    const pts: string[] = [];
    for (let k = 0; k <= n; k++) {
      const x = x0 + (w * k) / n;
      pts.push(`${k ? 'L' : 'M'} ${x.toFixed(2)} ${(cy - A * Math.sin((2 * Math.PI * periods * k) / n)).toFixed(2)}`);
    }
    return pts.join(' ');
  }
  if (shape === 'rise') {
    return `M ${x0} ${y1} C ${x0 + w * 0.45} ${y1}, ${x0 + w * 0.42} ${y0 + h * 0.1}, ${x1} ${y0}`;
  }
  // loop: a figure of eight (Bernoulli's lemniscate), sampled
  const a = Math.min(w * 0.48, h * 0.95), n = 160;
  const pts: string[] = [];
  for (let k = 0; k <= n; k++) {
    const th = (2 * Math.PI * k) / n;
    const den = 1 + Math.sin(th) * Math.sin(th);
    pts.push(`${k ? 'L' : 'M'} ${(cx + (a * Math.cos(th)) / den).toFixed(2)} ${(cy + (a * Math.sin(th) * Math.cos(th)) / den).toFixed(2)}`);
  }
  return pts.join(' ');
};

/** The film's own path, written in a 0..1000 square, scaled into the box. */
const scalePath = (d: string, x0: number, x1: number, y0: number, y1: number): string => {
  const s = Math.min((x1 - x0) / 1000, (y1 - y0) / 1000);
  const ox = (x0 + x1) / 2 - 500 * s, oy = (y0 + y1) / 2 - 500 * s;
  let i = 0;
  return d.replace(/-?\d*\.?\d+(?:e-?\d+)?/gi, (num) => {
    const v = parseFloat(num);
    const out = i % 2 === 0 ? ox + v * s : oy + v * s;
    i += 1;
    return out.toFixed(2);
  });
};

export const TypeOnPath: React.FC<{
  kicker?: string;
  /** the one line that must be read */
  title?: string;
  /** the words that travel the path */
  phrase?: string;
  /** the subject's own shape: a cycle, a signal, growth, a loop that feeds itself */
  path?: PathShape;
  /** or the film's own path, absolute commands only (M L C Q), in a 0-1000 square */
  d?: string;
  accent?: string;
}> = ({kicker = 'ALONG THE LINE', title = 'Words that follow the shape', phrase = 'riding the shape',
       path = 'wave', d, accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  if (!d && !SHAPES.includes(path)) {
    throw new Error(`TypeOnPath's \`path\` is one of ${SHAPES.join(', ')}, got "${String(path)}" — or pass the film's own \`d\`.`);
  }
  if (d !== undefined && (typeof d !== 'string' || !/^\s*M/i.test(d) || /[a-z]/.test(d.replace(/e-?\d/gi, '')))) {
    throw new Error('TypeOnPath\'s `d` must be an SVG path of ABSOLUTE commands (M, L, C, Q) in a 0-1000 square — ' +
      'relative commands and arcs cannot be scaled into the frame by their numbers.');
  }
  if (!String(phrase ?? '').trim()) throw new Error('TypeOnPath needs a `phrase` to travel the path.');
  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);

  const U = Math.min(W, H);
  const portrait = W < H;
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H), zoneH = zoneBot - zoneTop;
  const mx = Math.round(W * 0.07);
  const KICK = Math.ceil(U * 0.028);
  const ring = !d && (path === 'orbit');
  const moving = !d && (path === 'orbit' || path === 'loop');

  // ── the title: inside the ring, or above the path ───────────────────────────────────────────────────────
  const titleW = ring ? Math.round(Math.min(W - 2 * mx, zoneH) * 0.5) : W - 2 * mx;
  // THE TITLE'S ROOM IS RESERVED, NOT MEASURED, because the path is laid out below it and the phrase is fitted to
  // the path's length: a path that waited on the title's measured height re-specced the phrase after the first
  // measurement, which is a second measurement the frame has to wait for and nothing gained.
  const titleH = Math.round(zoneH * (ring ? 0.3 : 0.24));
  const head = useKinetic({text: title || ' ', w: titleW, h: titleH, fit: 'box', valign: ring ? 'middle' : 'top',
    maxLines: 3, align: ring ? 'center' : 'left', wrap: 'balance',
    fitTiers: [{maxLines: ring ? 3 : 2, minSize: Math.round(U * 0.05)}],
    font: {family: DISPLAY, weight: 620, size: Math.round(U * (ring ? 0.075 : 0.105)), minSize: Math.ceil(U * 0.04),
      lineHeight: 1.04, tracking: -0.02}});
  const kick = useKinetic({text: kicker || ' ', w: W - 2 * mx, nowrap: true, fit: 'box', align: ring ? 'center' : 'left',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});
  const kickH = kicker ? Math.round(KICK * 1.25 + U * 0.025) : 0;

  // ── the path's box: the room the title leaves ───────────────────────────────────────────────────────────
  const pTop = ring ? zoneTop + kickH + U * 0.02 : zoneTop + kickH + titleH + U * 0.06;
  const pBot = zoneBot - U * 0.06;
  const PD = d ? scalePath(d, mx, W - mx, pTop, pBot) : shapePath(path, mx, W - mx, pTop, pBot, portrait);

  // the same arc length the glyphs are placed by (runtime/kinetic's own walk of the path)
  const len = React.useMemo(() => kineticPathLength(PD), [PD]);
  // the phrase: one line, fitted to the PATH's length — not the frame's width; a wave is longer than the frame is
  // wide and a ring longer still (a fixed fraction of the width refused a 26-glyph phrase at 9:16 that its path
  // could carry). A ring keeps a gap for its separator; an open path, margins at both ends.
  const words = useKinetic({text: String(phrase), w: Math.round(len * (ring ? 0.94 : 0.84)), nowrap: true, fit: 'box',
    font: {family: ring ? MONO : DISPLAY, weight: ring ? 600 : 580, size: Math.round(U * (ring ? 0.042 : 0.088)),
      minSize: Math.ceil(U * 0.03), lineHeight: 1.15, tracking: ring ? 0.12 : -0.01}});
  const textW = words.layout?.width ?? 0;
  // resting place: centred along an open path; a ring starts the phrase at the top and turns it once a ~24s cycle
  const rest = ring ? len * 0.25 - textW / 2 : Math.max(0, (len - textW) / 2);
  const speed = ring ? len / 24 : !d && path === 'loop' ? len / 9 : 0;

  // the title sits centred in the ring, or above the path
  const cxRing = W / 2, cyRing = (pTop + pBot) / 2;
  const headX = ring ? Math.round(cxRing - titleW / 2) : mx;
  const headY = ring ? Math.round(cyRing - titleH / 2) : zoneTop + kickH;

  const drawIn = easeOutCubic(clamp01(seg(t, 0.08, 0.34)));
  const ruleW = Math.max(2, Math.round(U * 0.0032));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        <path d={PD} fill="none" stroke={mix(ACC, BG, 0.55)} strokeWidth={ruleW} strokeLinecap="round"
          {...drawOn(drawIn)} />
      </svg>
      {kicker ? (
        <KineticText k={kick} x={mx} y={ring ? zoneTop : zoneTop} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.06, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.36}}} />
      ) : kick.anchor}
      {title ? (
        <KineticText k={head} x={headX} y={headY} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.03}, enter: {by: 'line', at: 0.12, stagger: 0.14,
            dur: 0.9, ease: 'expo', cueKeys: ['title'], until: 0.5}}} />
      ) : head.anchor}
      {/* the words on the path: placed by arc length at their own advances, turned to the tangent */}
      <KineticText k={words} x={0} y={0} color={ring ? DIM : ACC} id="phrase" read={!moving}
        motion={{from: {opacity: 0, blur: 0.12},
          enter: {by: 'grapheme', at: 0.16, stagger: 0.03, dur: 0.5, ease: 'power3', cueKeys: ['phrase'], until: 0.5},
          path: {d: PD, at: rest, travel: moving ? 0 : Math.min(len * 0.45, Math.max(0, rest + textW)),
            enter: {at: 0.14, dur: 2.2, ease: 'power3'}, speed, repeatGap: ring ? KICK * 2.5 : undefined,
            lift: -Math.round((words.layout?.size ?? U * 0.07) * 0.18)}}} />
    </AbsoluteFill>
  );
};
export default TypeOnPath;
