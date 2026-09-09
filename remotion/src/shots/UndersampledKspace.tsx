// UndersampledKspace — what "4–8× too sparsely" actually means: a full Cartesian k-space (every phase-encode
// line) has most of its lines REMOVED, keeping only every 6th — the measurements you skip to go faster. A deep
// network (trained on the fastMRI scale, 167k slices) reconstructs the image from what's left. The vanishing
// lines + the surviving sparse subset ARE the idea. Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY} from '../runtime/layout';

export const DURATION = 180; // 6s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'k-space · phase-encode lines',
  'lines acquired',
  '~4–8× undersampled',
];

export const UndersampledKspace: React.FC<{accent?: string; accent2?: string; label?: string; keep?: number;
  method?: string; unit?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Reconstruct from far fewer lines', keep = 6,
  // A CLAIM ABOUT A METHOD, written straight into the JSX: `deep network · trained on {scans}k scans`
  // printed on every film that ever reached for this register, whatever the film's method actually was,
  // and the count beside it is the register's own. Both halves are props now, each defaulting to the words
  // it replaced, so existing films render identically and a film that trains on something else can say so.
  method = 'deep network · trained on', unit = 'k scans',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const gx = W * 0.16, gw = W * 0.68, gy = H * 0.2;
  // the acquired-lines counter sits to the grid's right when the room exists; on a narrow frame it steps
  // UNDER the grid (the sweep caught '~4-8x undersampled' 135px off a portrait edge)
  const cRoom = W - (gx + gw) - 40;
  const cUnder = cRoom < 240;   // 16:9 leaves 267px and has always fit; 9:16 leaves 133 and never can
  // AND THE ROOM IT STEPS INTO HAS TO EXIST. Stepping under was checked at 9:16, where the frame is 1920
  // tall and the block lands 108px clear. It was never checked at the three aspects nobody had swept: the
  // block is 160px deep below the grid, `gh` is a flat 0.52 of the height, and at 1:1 that put its last
  // line 128px INSIDE the caption band (52px at 4:5, 71px at 4:3) — the burned subtitle drawn straight
  // through the number the shot exists to show. The grid yields the room instead, because it is the
  // element that can: 42 lines read the same at 434px as at 562px, and a reading missing its label does
  // not. 16:9 (never under) and 9:16 (already clear) are untouched by construction.
  const CBLOCK = 64 + 96;       // first baseline below the grid, plus the block's own last baseline
  const gh = cUnder ? Math.min(H * 0.52, bottomTextY(W, H) - gy - CBLOCK) : H * 0.52;
  const cX = cUnder ? gx : gx + gw + 40;
  const cY = (line: number) => (cUnder ? gy + gh + 64 + line * 46 : gy + gh * 0.42 + line * 46);
  const nLines = 42;
  const drop = clamp01(seg(t, 0.15, 0.75));                 // how far the removal has progressed

  const lines: React.ReactNode[] = [];
  for (let i = 0; i < nLines; i++) {
    const y = gy + (i + 0.5) * (gh / nLines);
    const kept = i % keep === 0;
    // kept lines stay bright; the rest FADE OUT as `drop` advances
    const op = kept ? 0.95 : lerp(0.6, 0.06, drop);
    const col = kept ? accent : accent2;
    lines.push(<line key={i} x1={gx} y1={y} x2={gx + gw} y2={y} stroke={col} strokeWidth={kept ? 2.6 : 1.2} opacity={op} />);
  }

  // counters
  const total = nLines, acquired = Math.round(nLines / keep);
  const shownAcq = Math.round(lerp(total, acquired, drop));
  const scans = Math.round(lerp(0, 167, clamp01(seg(t, 0.2, 0.85))));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 40%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <rect x={gx - 14} y={gy - 14} width={gw + 28} height={gh + 28} rx={10} fill="none" stroke={accent} strokeWidth={1.4} opacity={0.35} />
        {lines}
        <text x={gx - 14} y={gy - 26} fill="#9fb4cc" fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" letterSpacing="1">k-space · phase-encode lines</text>
        {/* live count of acquired lines */}
        <text x={cX} y={cY(0)} fill="#eaf6ff" fontSize="72" fontFamily="var(--f-display, Inter, sans-serif)" fontWeight={800}>
          {shownAcq}<tspan fill={accent} fontSize="40">/{total}</tspan></text>
        <text x={cX + 4} y={cY(0) + 40} fill="#8aa" fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">lines acquired</text>
        <text x={cX + 4} y={cY(0) + 96} fill={accent2} fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>~4–8× undersampled</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        <div style={{marginTop: 8, font: "600 22px/1 var(--f-mono, 'JetBrains Mono', monospace)", color: '#8aa', letterSpacing: '0.1em'}}>
          {method} {scans}{unit}</div>
      </div>
    </AbsoluteFill>
  );
};
export default UndersampledKspace;
