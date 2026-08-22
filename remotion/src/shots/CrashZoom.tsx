// SHOT · Crash Zoom — a wide overview grid holds, then the camera PUNCHES in on one target tile (radial speed
// lines, a touch of overshoot) until it fills the frame as a detail card. The "…and here's the one that
// matters" register (family B — camera). Deterministic (zoom scale = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 140; // ~4.7s
const BG_D0 = '#0a0c13', ACC_D0 = '#5b8cff';

export const CrashZoom: React.FC<{items?: string[]; label?: string; target?: number; title?: string}> = ({
  items: ITEMS = ['Inbox', 'Docs', 'Tasks', 'Chat', 'Focus', 'Data', 'Code', 'Team', 'Calls'],
  label: LABEL = 'One place for all of it', target: TARGET = 4, title: TITLE = 'Your workspace'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, ACC = dna?.accent ?? ACC_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cols = 3, rows = Math.ceil(ITEMS.length / cols);
  const gw = 1180, gh = 720, cw = gw / cols, ch = gh / rows;
  const gx = (W - gw) / 2, gy = (H - gh) / 2;
  const ti = Math.min(TARGET, ITEMS.length - 1);
  const tcol = ti % cols, trow = Math.floor(ti / cols);
  // target-tile centre in overview coords
  const tcx = gx + tcol * cw + cw / 2, tcy = gy + trow * ch + ch / 2;
  const z = easeInOutCubic(seg(t, 0.34, 0.74));               // the punch
  const over = 1 + 0.06 * easeOutBack(clamp01(seg(t, 0.68, 0.82))) * (1 - clamp01(seg(t, 0.82, 0.95)));
  const scale = lerp(1, (W / cw) * 0.98, z) * over;
  // translate so the target centre stays put while scaling from it
  const originX = tcx, originY = tcy;
  const speed = Math.sin(clamp01(seg(t, 0.34, 0.74)) * Math.PI);  // speed-lines intensity, rise+fall
  const detail = easeOutCubic(seg(t, 0.72, 0.9));
  const titleIn = easeOutCubic(seg(t, 0.04, 0.18));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #12162a, ${BG} 72%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 60, left: 0, right: 0, textAlign: 'center',
        opacity: titleIn * (1 - z), color: '#aeb6ca', font: '700 30px/1 "JetBrains Mono", monospace',
        letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <AbsoluteFill style={{transformOrigin: `${originX}px ${originY}px`, transform: `scale(${scale})`}}>
        {ITEMS.map((it, i) => {
          const c = i % cols, r = Math.floor(i / cols);
          const isT = i === ti;
          const enter = easeOutBack(clamp01(seg(t, 0.06 + i * 0.03, 0.28 + i * 0.03)));
          return (
            <div key={i} style={{position: 'absolute', left: gx + c * cw + 8, top: gy + r * ch + 8,
              width: cw - 16, height: ch - 16, opacity: clamp01(enter * 1.4) * (isT ? 1 : lerp(1, 0.15, z)),
              transform: `scale(${lerp(0.9, 1, enter)})`, borderRadius: 18,
              background: isT ? `linear-gradient(150deg, ${ACC}, #2c3ac0)` : 'linear-gradient(160deg, #14172480, #0d0f18)',
              border: `1px solid ${isT ? 'transparent' : '#20243a'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: isT ? `0 20px 60px ${ACC}44` : '0 12px 30px #0006'}}>
              <div style={{color: isT ? '#fff' : '#c7cee0', font: `800 ${isT ? 54 : 40}px/1 Inter, system-ui, sans-serif`,
                letterSpacing: '-0.02em', textAlign: 'center'}}>
                {isT && detail > 0.1 ? LABEL : it}
              </div>
            </div>
          );
        })}
      </AbsoluteFill>

      {/* radial speed lines during the punch */}
      {speed > 0.02 ? (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'screen'}}>
          {[...Array(28)].map((_, i) => {
            const a = (i / 28) * Math.PI * 2, r0 = 180 + (i % 3) * 40, r1 = r0 + 260;
            const cx = W / 2, cy = H / 2;
            return <line key={i} x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0}
              x2={cx + Math.cos(a) * r1} y2={cy + Math.sin(a) * r1} stroke="#ffffff" strokeWidth={3}
              opacity={speed * 0.5} strokeLinecap="round" />;
          })}
        </svg>
      ) : null}
    </AbsoluteFill>
  );
};
export default CrashZoom;
