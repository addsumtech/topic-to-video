// SHOT · Infinite Canvas — Miro/Figjam language: a boundless board of connected, colourful sticky notes;
// the camera flies over it and ZOOMS from the whole map down into one cluster (big-picture → detail). Light
// warm canvas, playful colour. Deep continuous zoom + parallax — a move the flat HTML tier can't make.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, easeInOutCubic, easeOutBack, seg, clamp01, hash01} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
// LEVEL-C: the Miro/Figjam board flips to a DARK canvas on a dark DNA (ground/grid/connectors/hub → DNA); the
// pastel STICKIES + their dark text stay (colourful stickies are the board's identity, and pop on any ground).
const STICKY = ['#FFD666', '#FFA8C5', '#8FC7FF', '#A9E5A0', '#C6B0FF', '#FFC48A'];
const WORLD_W = 3600, WORLD_H = 2200;

type Node = {x: number; y: number; w: number; h: number; text: string; c: string};

export const InfiniteCanvas: React.FC<{hub?: string; items?: string[]}> = ({
  hub: hubText = 'Q3 Board Deck',
  items: labels_IN = ['Market scan', 'Financials', 'Narrative', 'Slide design', 'Appendix', 'Review', 'Export', 'Sources']} = {}) => {
  const labels = rows<string>(labels_IN, 'items', 'InfiniteCanvas');
  const dna = useDNA();
  const BG = dna?.bg ?? '#f6f4ec', LINE = dna?.line ?? '#d8d2c2', LINE2 = dna?.line ?? '#c9c2b0';
  const SURF = dna?.surface ?? '#ffffff', SURFB = dna?.line ?? '#e3ddcb', FG = dna?.fg ?? '#1b2333';
  // A STICKY'S EDGE IS DRAWN, LIKE THE HUB'S ALREADY IS. The notes had no border at all — only a drop shadow
  // — which reads on a dark board and does not on a light one: the six pastels sit within a hair of a warm
  // white ground, so the note's boundary becomes paper on paper. Measured on a light ground (2026-09-21,
  // scripts/ink_contrast_qa.py): 29.8% of this register's ink under 3:1, chained into one region 0.80% of
  // the frame, and all of it note rims — the labels on them read (median 9.00:1), and the hub, which has
  // carried a border since it was written, is not in the finding. Inset, so the 300×180 note stays 300×180.
  const NOTEB = dna?.surfaceBorder ?? null;
  const noteShadow = `${NOTEB ? `inset 0 0 0 1px ${NOTEB}, ` : ''}0 14px 30px rgba(80,70,40,.18)`;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // a central hub + branches (a project mapped out); positions deterministic on the big world
  const hub: Node = {x: WORLD_W / 2 - 210, y: WORLD_H / 2 - 120, w: 420, h: 240, text: hubText, c: FG};
  const nodes: Node[] = labels.map((text, i) => {
    const ang = (i / labels.length) * Math.PI * 2 + 0.4;
    const rad = 620 + hash01(i) * 260;
    return {x: WORLD_W / 2 + Math.cos(ang) * rad - 150, y: WORLD_H / 2 + Math.sin(ang) * rad - 90, w: 300, h: 180, text, c: STICKY[i % STICKY.length]};
  });
  // camera: wide over the whole board → deep zoom into the hub (detail). z small→large.
  const zt = easeInOutCubic(clamp01((t - 0.12) / 0.78));
  const z = lerp(0.5, 1.35, zt);
  const fx = lerp(WORLD_W / 2, hub.x + hub.w / 2, zt), fy = lerp(WORLD_H / 2, hub.y + hub.h / 2, zt);
  const world: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: WORLD_W, height: WORLD_H,
    transformOrigin: '0 0', transform: `translate(${W / 2 - fx * z}px, ${H / 2 - fy * z}px) scale(${z})`};
  const cx = hub.x + hub.w / 2, cy = hub.y + hub.h / 2;
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* data-bleed: the WORLD is larger than the frame by definition — this shot is a viewport panning
          over a canvas, so nodes outside the viewport are the premise, not a layout that overflowed. */}
      <div data-bleed style={world}>
        {/* dot grid */}
        <svg width={WORLD_W} height={WORLD_H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
          {[...Array(45)].map((_, gx) => [...Array(28)].map((_, gy) => <circle key={`${gx}-${gy}`} cx={gx * 80 + 30} cy={gy * 80 + 30} r={2} fill={LINE} />))}
        </svg>
        {/* connectors hub→node */}
        <svg width={WORLD_W} height={WORLD_H} style={{position: 'absolute', inset: 0}}>
          {nodes.map((n, i) => {
            const grow = clamp01((zt - 0.05 - i * 0.02) / 0.3);
            return <line key={i} x1={cx} y1={cy} x2={lerp(cx, n.x + n.w / 2, grow)} y2={lerp(cy, n.y + n.h / 2, grow)} stroke={LINE2} strokeWidth={3} />;
          })}
        </svg>
        {/* branch stickies */}
        {nodes.map((n, i) => {
          const ap = easeOutBack(clamp01((zt - i * 0.03) / 0.3));
          return <div key={i} style={{position: 'absolute', left: n.x, top: n.y, width: n.w, height: n.h, background: n.c,
            borderRadius: 14, transform: `scale(${clamp01(ap)}) rotate(${(hash01(i + 3) - 0.5) * 6}deg)`, transformOrigin: 'center',
            boxShadow: noteShadow, display: 'flex', alignItems: 'center', justifyContent: 'center',
            font: '700 40px/1.15 var(--f-body, Inter,system-ui,sans-serif)', color: '#3a3320', textAlign: 'center', padding: 20}}>{n.text}</div>;
        })}
        {/* the hub */}
        <div style={{position: 'absolute', left: hub.x, top: hub.y, width: hub.w, height: hub.h, background: SURF,
          border: `2px solid ${SURFB}`, borderRadius: 18, boxShadow: '0 26px 60px rgba(80,70,40,.2)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', font: '800 56px/1.1 var(--f-body, Inter,system-ui,sans-serif)', color: hub.c, textAlign: 'center', padding: 24}}>{hub.text}</div>
      </div>
    </AbsoluteFill>
  );
};
export default InfiniteCanvas;
