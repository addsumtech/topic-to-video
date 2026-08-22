// SHOT · Timeline Travel — roadmap/journey language: a horizontal timeline the camera TRAVELS along, each
// dated milestone lighting up as it passes. Clean light rail (a calm, temporal look). Deterministic camera
// pan over a world wider than the frame — a travelling reveal the flat tier can't do.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
// LEVEL-C: the timeline UI flips with the DNA (rail, nodes, ink, accent) → a dark-mode timeline on a dark DNA, the
// original light rail on null DNA.
const ACCENT0 = '#2E7BFF', INK0 = '#1b2333';
const DEFAULT_NODES = [
  {time: '9:00', label: 'You brief it'},
  {time: '9:02', label: 'It plans'},
  {time: '9:18', label: 'Experts work'},
  {time: '9:41', label: 'You review'},
  {time: '9:45', label: 'Shipped'},
];

export const TimelineTravel: React.FC<{nodes?: {time: string; label: string}[]}> = ({nodes: NODES = DEFAULT_NODES} = {}) => {
  const dna = useDNA();
  const ACCENT = dna?.accent ?? ACCENT0, INK = dna?.fg ?? INK0, BG = dna?.bg ?? '#f4f6fa';
  const RAIL = dna?.line ?? '#d8dee8', SURF = dna?.surface ?? '#fff', BORD = dna?.line ?? '#c7cedb', DIM = dna?.dim ?? '#9aa3b2';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const gap = 720, x0 = 520, railY = H / 2;
  const worldW = x0 * 2 + (NODES.length - 1) * gap;
  // camera travels along the rail left→right
  const camX = lerp(W / 2, worldW - W / 2, easeInOutCubic(seg(t, 0.1, 0.92)));
  const wx = W / 2 - camX;
  const passedX = camX; // nodes to the left of the lens centre are "done"
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: wx, top: 0, width: worldW, height: H}}>
        {/* the rail: a dim base + a bright progress fill up to the camera */}
        <div style={{position: 'absolute', left: x0, top: railY - 3, width: worldW - x0 * 2, height: 6, background: RAIL, borderRadius: 3}} />
        <div style={{position: 'absolute', left: x0, top: railY - 3, width: Math.max(0, Math.min(worldW - x0 * 2, passedX - x0)), height: 6, background: ACCENT, borderRadius: 3}} />
        {NODES.map((n, i) => {
          const nx = x0 + i * gap;
          const done = passedX > nx - 30;
          const pop = easeOutBack(clamp01((passedX - (nx - 260)) / 240));
          const up = i % 2 === 0;
          return (
            <div key={i}>
              <div style={{position: 'absolute', left: nx - 16, top: railY - 16, width: 32, height: 32, borderRadius: 16,
                background: done ? ACCENT : SURF, border: `3px solid ${done ? ACCENT : BORD}`,
                boxShadow: done ? `0 0 0 8px ${ACCENT}22` : 'none', transform: `scale(${done ? 1.1 : 1})`}} />
              <div style={{position: 'absolute', left: nx - 190, top: up ? railY - 200 : railY + 70, width: 380,
                textAlign: 'center', opacity: clamp01(pop), transform: `translateY(${lerp(up ? 20 : -20, 0, clamp01(pop))}px)`}}>
                <div style={{font: '800 40px/1 Inter,system-ui,sans-serif', color: done ? ACCENT : DIM}}>{n.time}</div>
                <div style={{font: '600 46px/1.15 Inter,system-ui,sans-serif', color: INK, marginTop: 12}}>{n.label}</div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export default TimelineTravel;
