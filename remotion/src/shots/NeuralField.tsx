// SHOT · Neural Field — a neural network THINKS: layered nodes and their edges light up as an activation front
// sweeps left→right, signals pulsing along the strongest connections until the output head locks. An AI-native
// register (family R · AI/neural). Deterministic (activation front = fn of t; edge strengths from hash01).
// No fabricated stats — labels are layer names, never numbers.
//
// Two things this register can do beyond "a network glows":
//
//  • THE MISSING HEAD (`absentOutput`). A network only computes the channels it was WIRED for, and a beat about
//    what a model CANNOT know has to draw that absence or it argues the opposite. Given `absentOutput` the shot
//    puts a SECOND output slot beside the live one: dashed, unlit, carrying its own label, and — the whole point
//    — with NO incoming edges at all. Every edge in the frame converges on the live head; the ghost slot hangs in
//    empty space. Hide the caption and the frame still says "that channel was never connected". Without the prop
//    nothing extra is drawn and the shot is the plain network it has always been.
//  • COLOUR IS THE FILM'S, NOT THE SHOT'S. Every hue is read from the Design DNA (the *_D0 constants are only the
//    no-DNA fallback). This register used to paint itself cyan + spring-green, which on a green/amber film was a
//    palette nobody declared, and handed the film's SUCCESS colour to the head that is merely plausible. So when
//    an absent channel is declared, the live path takes the SECONDARY accent and the film's primary accent shows
//    up only as the unlit ghost — the correctness hue is present exactly as the thing that is missing. `tone`
//    overrides that pairing when a film wants it the other way round.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, mix, tint} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
// NO-DNA FALLBACK ONLY — these are the register's original hues, kept so an un-themed render is unchanged.
// Never reference one of these next to a DNA token in the same expression.
const BG_D0 = '#060a16', GLOW_D0 = '#0c1430', EDGE_D0 = '#1c2f57', FLOW_D0 = '#37e0ff', OUT_D0 = '#3affa0';
const INK_D0 = '#8fb6d8', DIM_D0 = '#9fb2c8', SURF_D0 = '#1a2340', SURFB_D0 = '#2a3760', GHOST_D0 = '#3b4a6b';
const LAYERS = [5, 8, 8, 3];

export const NeuralField: React.FC<{
  title?: string; input?: string; output?: string;
  /** Label for a channel the network was NEVER wired for — draws a dashed, edge-less second output slot. */
  absentOutput?: string;
  /** Which DNA accent the LIVE path wears. Default: accent2 when an absent channel is declared, else accent. */
  tone?: 'accent' | 'accent2';
}> = ({
  title: TITLE = 'It reasons', input: INLABEL = 'your prompt', output: OUTLABEL = 'the answer',
  absentOutput: ABSENT, tone: TONE} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  // An empty/whitespace string must NOT summon a label-less ghost slot — that would draw an absence the film
  // never asked for and the viewer cannot name.
  const ABS = typeof ABSENT === 'string' ? ABSENT.trim() : '';
  const hasAbs = ABS.length > 0;

  // ── PALETTE ─────────────────────────────────────────────────────────────────────────────────────────────
  const BG = dna?.bg ?? BG_D0;
  const A1 = dna?.accent ?? FLOW_D0;                 // the film's PRIMARY accent
  const A2 = dna?.accent2 ?? OUT_D0;                 // the film's SECONDARY accent
  const secondaryLive = TONE ? TONE === 'accent2' : hasAbs;
  const LIVE = secondaryLive ? A2 : A1;              // hue of everything that actually computes
  const GHOSTHUE = secondaryLive ? A1 : A2;          // hue reserved for the channel that does not exist
  const FLOW = dna ? LIVE : FLOW_D0;                 // travelling activation (edges + hidden nodes)
  const OUT = dna ? tint(LIVE, 0.22) : OUT_D0;       // the live output head, one step brighter than the path
  const GHOST = dna ? mix(GHOSTHUE, BG, 0.56) : GHOST_D0;          // unlit outline — reads as "not there"
  const GHOST_INK = dna ? mix(GHOSTHUE, dna.dim, 0.5) : GHOST_D0;  // its label, legible but never lit
  const SLOT = dna ? mix(LIVE, BG, 0.45) : SURFB_D0;               // the LIVE slot's frame — the ghost's twin
  const EDGE = dna ? mix(dna.line, dna.fg, 0.24) : EDGE_D0;        // dormant connection
  const NODE_FILL = dna?.surface ?? SURF_D0;
  const NODE_EDGE = dna?.surfaceBorder ?? SURFB_D0;
  const INK = dna?.fg ?? INK_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const monoFace = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const track = dna?.labelSpacing ?? '0.3em';
  const bgCss = dna
    ? `radial-gradient(120% 100% at 50% 44%, ${mix(BG, LIVE, 0.09)}, ${BG} 74%)`
    : `radial-gradient(120% 100% at 50% 44%, ${GLOW_D0}, ${BG_D0} 74%)`;

  // ── GEOMETRY (fractions of the CONTENT ZONE, so the shot reflows at every aspect) ───────────────────────
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const zoneH = Math.max(1, zBot - zTop);
  // NARROW, not merely taller-than-wide: 1:1 is 1080 across too, so a W-derived type scale goes tiny and a
  // W-derived label column goes thin on a square frame exactly as it does at 9:16. Same threshold layout.ts
  // uses for the taller caption band, so the two always agree about which frames are the cramped ones.
  const narrow = W < 1400;
  const L = LAYERS.length, outN = LAYERS[L - 1];
  // With an absent channel the frame also has to carry two head LABELS, which live in a right-hand column;
  // the network gives up that width. A narrow frame needs a wider label column (fewer chars fit per line).
  const edgePad = W * 0.045;                                  // clears the 3.5% action-safe border
  const labelW = hasAbs ? W * (narrow ? 0.3 : 0.22) : 0;
  const labelLeft = W - edgePad - labelW;
  const x0 = W * 0.17;
  const x1 = hasAbs ? labelLeft - W * (narrow ? 0.075 : 0.05) : W * 0.83;
  const colGap = (x1 - x0) / (L - 1);
  // A 4-column graph is a WIDE-HORIZONTAL element, so on a narrow frame it must be re-proportioned, not just
  // squeezed: the row pitch is capped against the network's own WIDTH (never just the zone height), or portrait
  // renders an 865px-tall tangle inside a 426px-wide graph at 9:16. Node radius is then capped by BOTH pitches, so the
  // dots shrink with the frame instead of touching. (The old fixed 110px row pitch also pushed the tallest
  // column's bottom node straight into the burned-caption band at 16:9.)
  const rowSpan = Math.min(zoneH * (hasAbs ? 0.56 : 0.66), (x1 - x0) * (narrow ? 1.25 : 1.15));
  const nodeGap = rowSpan / (Math.max(...LAYERS) - 1);
  const rBase = Math.min(nodeGap * 0.17, colGap * 0.1, zoneH * 0.021);
  const rHot = rBase * 1.75;
  // The whole network sits high when a ghost slot has to hang below it; centred in the zone otherwise.
  const colCy = zTop + zoneH * (hasAbs ? 0.38 : 0.5);
  const absCy = zTop + zoneH * 0.74;
  const nodeX = (li: number) => lerp(x0, x1, li / (L - 1));
  const nodeY = (li: number, ni: number) => colCy + (ni - (LAYERS[li] - 1) / 2) * nodeGap;
  const absY = (ni: number) => absCy + (ni - (outN - 1) / 2) * nodeGap;
  const slotW = rBase * 5, slotH = (outN - 1) * nodeGap + rBase * 5.4;
  // A column label is centred on its column, so its BOX has to be clamped twice or it walks into the frame's
  // action-safe border on one side and into the NEXT column's nodes on the other (both happen at 9:16, where
  // the columns sit ~150px apart). colGap*1.35 leaves ~0.15·colGap of air before the neighbouring dots.
  const inBoxW = Math.min(W * 0.26, colGap * 1.35, 2 * (x0 - edgePad));
  const outBoxW = Math.min(W * 0.24, colGap * 1.35, 2 * (W - edgePad - x1));

  // ── TIME ────────────────────────────────────────────────────────────────────────────────────────────────
  const front = clamp01(seg(t, 0.14, 0.86)) * (L - 1);        // activation front position (in layer units)
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const nodeAct = (li: number) => clamp01((front - (li - 0.5)) * 2.2);
  const slotIn = easeOutCubic(seg(t, 0.1, 0.28));             // the architecture (both slots) exists BEFORE the
  const inIn = clamp01(seg(t, 0.1, 0.3));                     // signal arrives, so the contrast can land
  const outIn = clamp01(seg(t, 0.68, 0.84));                  // …and both reveals finish by the reduced-motion
  const absIn = clamp01(seg(t, 0.72, 0.86));                  //    freeze at t=0.86, so that frame is settled

  // ── TYPE (width-fitted: real copy is Chinese and far longer than the English demo words) ─────────────────
  const fit = (text: string, box: number, cap: number, lines = 2, weight = 700, ls?: string) =>
    (text ? fitTextOnNLines({
      text, maxLines: lines, maxBoxWidth: Math.max(40, box), fontFamily: monoFace,
      fontWeight: weight, maxFontSize: cap, letterSpacing: ls,
    }).fontSize : cap);
  const titleSize = React.useMemo(
    () => fit(String(TITLE ?? ''), W * 0.84, W * (narrow ? 0.024 : 0.017), 1, 700, track),
    [TITLE, W, narrow, monoFace, track]);
  const inSize = React.useMemo(
    () => fit(String(INLABEL ?? ''), inBoxW, W * (narrow ? 0.02 : 0.0145), 2, 600),
    [INLABEL, W, inBoxW, narrow, monoFace]);
  // ONE size for BOTH heads: they are peers (one wired, one not) and must not read as primary + footnote.
  const headSize = React.useMemo(() => {
    const box = hasAbs ? labelW : outBoxW;
    // A narrow frame makes W-derived type tiny next to nodes whose size comes from the (tall) content zone —
    // so the type scale gets its own narrow step, or the labels read as footnotes on a 9:16 / 1:1 render.
    const cap = W * (narrow ? 0.026 : 0.019);
    return Math.min(fit(String(OUTLABEL ?? ''), box, cap), hasAbs ? fit(ABS, box, cap) : cap);
  }, [OUTLABEL, ABS, hasAbs, labelW, outBoxW, W, narrow, monoFace]);

  // A head label sits at its OWN slot's height, one gap to the right of it — adjacency does the labelling, so
  // there is no extra rule/underline furniture for the viewer to decode.
  const headLabel = (text: string, cy: number, color: string, opacity: number) => (
    // `balance` because Chinese breaks between ANY two glyphs: a head label one unit too wide for its box
    // drops a single character onto a line of its own, which reads as a typo rather than a wrap. One call
    // site serves the live head and the ghost slot, so both are covered here.
    <div style={{position: 'absolute', left: labelLeft, top: cy, width: labelW, transform: 'translateY(-50%)',
      opacity, color, textWrap: 'balance',
      font: `700 ${headSize}px/1.32 ${monoFace}`, letterSpacing: '0.06em'}}>{text}</div>
  );

  return (
    <AbsoluteFill style={{background: bgCss, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: zTop * 0.42, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: INK, font: `700 ${titleSize}px/1.1 ${monoFace}`, letterSpacing: track,
        padding: `0 ${edgePad}px`}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* EDGES — every connection in the frame lands on the LIVE head. Nothing reaches the ghost slot. */}
        {LAYERS.slice(0, -1).map((cnt, li) => (
          [...Array(cnt)].map((_, a) => (
            [...Array(LAYERS[li + 1])].map((_, b) => {
              const strong = hash01(li * 31 + a * 7 + b * 3) > 0.62;
              const pulse = clamp01((front - li) * 3) * (1 - clamp01((front - li - 1) * 3));
              // A traversed connection keeps a low resting glow, so the settled frame reads as a WIRED network
              // rather than three unconnected columns with one lit fan.
              const lit = strong ? Math.max(pulse, clamp01((front - li - 1) * 2) * 0.36) : 0;
              const on = lit > 0.05;
              return <line key={`${li}-${a}-${b}`} x1={nodeX(li)} y1={nodeY(li, a)} x2={nodeX(li + 1)} y2={nodeY(li + 1, b)}
                stroke={on ? FLOW : EDGE} strokeWidth={on ? Math.max(1.6, rBase * 0.2) : Math.max(1, rBase * 0.09)}
                opacity={on ? 0.3 + 0.6 * lit : 0.2} />;
            })
          ))
        ))}

        {/* THE OUTPUT INTERFACE — one slot that exists, one that does not. Same size, same pitch, same column. */}
        {hasAbs ? (
          <g opacity={slotIn}>
            <rect x={x1 - slotW / 2} y={colCy - slotH / 2} width={slotW} height={slotH} rx={dna?.radius ?? 8}
              fill="none" stroke={SLOT} strokeWidth={1.5} />
            <rect x={x1 - slotW / 2} y={absCy - slotH / 2} width={slotW} height={slotH} rx={dna?.radius ?? 8}
              fill="none" stroke={GHOST} strokeWidth={1.5} strokeDasharray={`${rBase * 0.9} ${rBase * 0.8}`} />
            {/* Same radius as a SETTLED live head node: the same kind of head, simply never lit and never wired. */}
            {[...Array(outN)].map((_, ni) => (
              <circle key={ni} cx={x1} cy={absY(ni)} r={rHot} fill="none" stroke={GHOST} strokeWidth={2}
                strokeDasharray={`${rHot * 0.42} ${rHot * 0.46}`} />
            ))}
          </g>
        ) : null}

        {/* NODES */}
        {LAYERS.map((cnt, li) => (
          [...Array(cnt)].map((_, ni) => {
            const act = nodeAct(li);
            const isOut = li === L - 1;
            const col = isOut && act > 0.5 ? OUT : FLOW;
            const r = lerp(rBase, rHot, act);
            return <g key={`${li}-${ni}`}>
              <circle cx={nodeX(li)} cy={nodeY(li, ni)} r={r + rBase * 0.55} fill={col} opacity={0.18 * act} />
              <circle cx={nodeX(li)} cy={nodeY(li, ni)} r={r} fill={act > 0.1 ? col : NODE_FILL}
                stroke={act > 0.1 ? col : NODE_EDGE} strokeWidth={2}
                style={{filter: act > 0.4 ? `drop-shadow(0 0 ${rBase * 0.55}px ${col})` : undefined}} />
            </g>;
          })
        ))}
      </svg>

      {/* INPUT LABEL — hung directly under its own column so it stays attached to it at every aspect. */}
      <div style={{position: 'absolute', left: nodeX(0), top: colCy + ((LAYERS[0] - 1) / 2) * nodeGap + rHot + zoneH * 0.06,
        transform: 'translateX(-50%)', width: inBoxW, textAlign: 'center',
        opacity: inIn, color: DIM, font: `600 ${inSize}px/1.32 ${monoFace}`, letterSpacing: '0.06em'}}>{INLABEL}</div>

      {/* OUTPUT LABELS. Without a ghost slot the live label hangs under its column, exactly as this register
          always did. With one, both heads are labelled in a right-hand column at their own height, so the pair
          reads as two slots of one interface instead of a caption for the whole graph. */}
      {hasAbs ? (
        <>
          {headLabel(OUTLABEL, colCy, OUT, outIn)}
          {headLabel(ABS, absCy, GHOST_INK, absIn)}
        </>
      ) : (
        <div style={{position: 'absolute', left: nodeX(L - 1),
          top: colCy + ((outN - 1) / 2) * nodeGap + rHot + zoneH * 0.06, transform: 'translateX(-50%)',
          width: outBoxW, textAlign: 'center', opacity: outIn, color: OUT,
          font: `700 ${headSize}px/1.32 ${monoFace}`, letterSpacing: '0.06em',
          textShadow: `0 0 ${Math.round(W * 0.008)}px ${OUT}`}}>{OUTLABEL}</div>
      )}
    </AbsoluteFill>
  );
};
export default NeuralField;
