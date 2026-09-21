// KSpaceAnatomy — how to READ k-space, encoded on the real data: the CENTER of k-space (low spatial frequency)
// holds the overall contrast, the EDGES (high spatial frequency) hold the fine detail. Proven by the two partial
// reconstructions — center-only k-space inverse-FFTs to a blurry contrast image, edge-only to pure outlines. A
// generic 2x2 "four ways it wins" grid showed none of this (and its bottom row collided with the caption). All
// three images are props → generalises to any modality. Deterministic; credit for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA, tint} from '../runtime/dna';
import {ACCENT_CONTRAST_MIN, onLight, readsOn} from '../runtime/light';
import {CONTENT_TOP, bottomInset, contentBottom} from '../runtime/layout';

export const DURATION = 175; // ~5.8s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'edges = detail',
  'high spatial frequency',
  'low spatial frequency',
  'one point = a wave across the whole image',
];

export const KSpaceAnatomy: React.FC<{srcK?: string; srcLow?: string; srcHigh?: string;
  accent?: string; accent2?: string; label?: string; credit?: string}> = ({
  srcK, srcLow, srcHigh, accent: ACC, accent2: ACC2, label = 'Reading k-space', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // THE TYPE IS THE FILM'S; THE THREE PANELS KEEP THEIR NIGHT. Every label here was a literal picked for a
  // near-black ground, and all eight DNA presets are near-black, so on a film whose DNA came from a
  // warm-white deck the whole reading — the title, both annotations and the line under the data — drew
  // white on white (measured median 1.63:1 over 100% of the marks, `scripts/ink_contrast_qa.py`). Those are
  // ink and they read from the DNA. The PANELS are not ink: they hold a k-space magnitude and two partial
  // reconstructions, and a scan viewport is black in every reader that has ever shown one — a panel that
  // took the film's paper would put a dark scan on a white square and leave the empty case invisible. They
  // paint this register's own darkest stop when the film's ground is light, and nothing at all otherwise,
  // so an un-themed render is unchanged.
  const accent = ACC ?? dna?.accent ?? '#22d3ee';
  const accent2 = ACC2 ?? dna?.accent2 ?? '#a78bfa';
  const ink = dna?.fg ?? '#dfe8f5';          // the title
  const inkK = dna?.fg ?? '#c9d6ea';         // the name of the data panel
  const meta = dna?.dim ?? '#9fb4cc';        // 'low/high spatial frequency'
  const meta2 = dna?.dim ?? '#8aa';          // the line under the k-space panel
  const metaCredit = dna?.dim ?? '#5f6b7d';  // the CC-BY credit
  const night = onLight(dna);
  const plateBg = night ? '#05060a' : undefined;
  const plateGround = night ? '#05060a' : (dna?.bg ?? '#05060a');
  // A DROP SHADOW TUNED FOR A DARK GROUND IS A SMUDGE ON PAPER. `#000a` is black at two-thirds alpha
  // blurred 40px, which is invisible under a plate on near-black and, measured on a warm-white film, takes
  // the paper directly beneath the plate from 246 to 135 — the line under the k-space panel is then read
  // against a grey stain rather than against the page. The shadow itself is
  // right; its weight is not, so it lightens on a light ground and is untouched everywhere else.
  const plateShadow = night ? '#0003' : '#000a';
  // The two rings are drawn INSIDE the k-space panel, so they answer to that night and not to the paper:
  // a light film's accent is chosen to read on paper, which on the panel is the same disappearance one
  // layer in. The mapping arrows are not here — they spend most of their length on the film's ground.
  const ringInk = (c: string) =>
    readsOn(c, plateGround, ACCENT_CONTRAST_MIN);   // a ladder, not a fixed tint — see runtime/light.tsx
  // phase A (center→contrast) then phase B (edges→detail)
  const pA = clamp01(seg(t, 0.12, 0.34));
  const pB = clamp01(seg(t, 0.5, 0.72));
  const K = 400, kx = W * 0.09, ky = H * 0.30;                 // the k-space panel (left)
  const px = W * 0.56;
  // Each recon panel's annotation sits to its RIGHT — when the room for it exists. Decided by the room, not
  // by naming aspects: a 1080-wide portrait frame leaves 156px where the labels need ~260, and the sweep
  // caught 'center = contrast' 65px off the edge. With no side room the labels drop UNDER their panel,
  // which a portrait frame has the height to afford.
  const sideRoom = W - (px + 300) - 24;
  const under = sideRoom < 270;
  // AND WHEN THEY DROP UNDER, THEY NEED THE ROOM THEY TAKE. The stacked branch kept the side-by-side
  // spacing — 40px between panels — while putting two label rows 30 and 60 below the first one, so panel
  // one's labels were drawn ON panel two at 9:16, and at 1:1 the second panel and both its labels ran past
  // the caption band entirely ('edges = detail' printed through the subtitle). The column is sized from the
  // content zone in that branch: two panels, each with its label block, and one gap.
  const LBL = 70;                                   // rows at +30 and +60 below a panel, to the deepest ink
  const GAPV = 26;
  const zoneBot = contentBottom(W, H);
  const P = under ? Math.min(300, Math.floor((zoneBot - CONTENT_TOP - 2 * LBL - GAPV) / 2)) : 300;
  const py1 = under ? Math.min(H * 0.28, zoneBot - (2 * P + 2 * LBL + GAPV)) : H * 0.28;
  const py2 = under ? py1 + P + LBL + GAPV : H * 0.28 + P + 40;
  const kcx = kx + K / 2, kcy = ky + K / 2;
  const lx = () => (under ? px : px + P + 24);
  const ly1 = (line: number) => (under ? py1 + P + 30 + line * 30 : py1 + 34 + line * 32);
  const ly2 = (line: number) => (under ? py2 + P + 30 + line * 30 : py2 + 34 + line * 32);

  const panel = (x: number, y: number, s: number, src: string | undefined, ring: string, op: number) => (
    <div style={{position: 'absolute', left: x, top: y, width: s, height: s, borderRadius: 6, overflow: 'hidden',
      background: plateBg, boxShadow: `0 0 0 1.5px ${ring}, 0 14px 40px ${plateShadow}`, opacity: op}}>
      {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
    </div>
  );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      {/* k-space (grayscale FFT magnitude) */}
      {panel(kx, ky, K, srcK, `${accent}66`, 1)}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        {/* center zone = low spatial frequency → contrast */}
        <circle cx={kcx} cy={kcy} r={K * 0.1} fill="none" stroke={ringInk(accent)} strokeWidth={3}
          opacity={0.35 + 0.6 * pA} />
        {/* outer ring = high spatial frequency → detail */}
        <circle cx={kcx} cy={kcy} r={K * 0.46} fill="none" stroke={ringInk(accent2)} strokeWidth={2.5} strokeDasharray="6 8"
          opacity={0.3 + 0.6 * pB} />
        <text x={kx} y={ky - 16} fill={inkK} fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">k-space (spatial frequencies)</text>
        {/* mapping arrows */}
        <line x1={kcx} y1={kcy} x2={px - 24} y2={py1 + P / 2} stroke={accent} strokeWidth={2} opacity={pA * 0.8} markerEnd="url(#kaA)" />
        <line x1={kx + K * 0.94} y1={kcy} x2={px - 24} y2={py2 + P / 2} stroke={accent2} strokeWidth={2} opacity={pB * 0.8} markerEnd="url(#kaB)" />
        <defs>
          <marker id="kaA" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto"><path d="M0,0 L7,5 L0,10 Z" fill={accent} /></marker>
          <marker id="kaB" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto"><path d="M0,0 L7,5 L0,10 Z" fill={accent2} /></marker>
        </defs>
      </svg>
      {/* the two partial reconstructions */}
      {panel(px, py1, P, srcLow, `${accent}88`, 0.25 + 0.75 * pA)}
      {panel(px, py2, P, srcHigh, `${accent2}88`, 0.25 + 0.75 * pB)}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        <text x={lx()} y={ly1(0)} fill={accent} fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} opacity={pA}>center = contrast</text>
        <text x={lx()} y={ly1(1)} fill={meta} fontSize="19" fontFamily="var(--f-body, Inter, sans-serif)" opacity={pA}>low spatial frequency</text>
        <text x={lx()} y={ly2(0)} fill={accent2} fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} opacity={pB}>edges = detail</text>
        <text x={lx()} y={ly2(1)} fill={meta} fontSize="19" fontFamily="var(--f-body, Inter, sans-serif)" opacity={pB}>high spatial frequency</text>
        <text x={kx} y={ky + K + 40} fill={meta2} fontSize="19" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t, 0.06, 0.3))}>one point = a wave across the whole image</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: bottomInset(W, H, 8), color: metaCredit, font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default KSpaceAnatomy;
