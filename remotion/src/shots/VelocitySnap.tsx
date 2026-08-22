// SHOT · Velocity Snap — Linear/Stripe language: a UI ASSEMBLES in a blink, each element flying in and
// SNAPPING into place with a micro-bounce + a motion-blur streak on arrival. Signals raw speed / "instant".
// Dark premium + Linear-purple (adds a snappy dark language). Deterministic (blur ∝ per-element velocity).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {Figure} from '../runtime/atoms';

export const DURATION = 120; // 4s — snappy
const PUR0 = '#7C89FF', BG = '#0c0d14';

type Piece = {x: number; y: number; w: number; h: number; dx: number; dy: number; at: number; c?: string};

export const VelocitySnap: React.FC<{label?: string; metric?: string; unit?: string}> = ({
  label = 'Done.', metric = '0', unit = 'ms'} = {}) => {
  const t = useT();
  const dna = useDNA(); const PUR = dna?.accent ?? PUR0;
  const {width: W} = useVideoConfig();
  // UI sits in the LEFT band; the big "0ms" gets a clear RIGHT band (no overlap).
  const cx = 130, cy = 300;
  const pieces: Piece[] = [
    {x: cx, y: cy, w: 1240, h: 90, dx: 0, dy: -120, at: 0.06},
    {x: cx, y: cy + 120, w: 360, h: 480, dx: -220, dy: 0, at: 0.12},
    {x: cx + 390, y: cy + 120, w: 500, h: 300, dx: 0, dy: 160, at: 0.18, c: PUR},
    {x: cx + 390, y: cy + 450, w: 500, h: 150, dx: 0, dy: 200, at: 0.26},
    {x: cx + 920, y: cy + 120, w: 320, h: 220, dx: 220, dy: 0, at: 0.22},
    {x: cx + 920, y: cy + 360, w: 320, h: 240, dx: 220, dy: 120, at: 0.30},
  ];
  const doneAll = t > 0.44;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 100% at 50% 30%, #14162a, ${BG} 62%)`}}>
      {pieces.map((p, i) => {
        const r = clamp01(seg(t, p.at, p.at + 0.14));
        const e = easeOutBack(r);
        const vel = 1 - easeOutCubic(r);
        const blur = r < 0.75 ? 22 * vel : 0;
        const tx = lerp(p.dx, 0, e), ty = lerp(p.dy, 0, e);
        const pulse = doneAll ? 1 + 0.012 * Math.max(0, Math.sin((t - 0.44) * 30)) * Math.exp(-(t - 0.44) * 6) : 1;
        return <div key={i} style={{position: 'absolute', left: p.x, top: p.y, width: p.w, height: p.h,
          opacity: clamp01(r * 2), transform: `translate(${tx}px, ${ty}px) scale(${pulse})`,
          filter: blur > 0.5 ? `blur(${blur}px)` : undefined,
          background: p.c ? `linear-gradient(150deg, ${p.c}, #5a63d8)` : '#161826',
          border: `1px solid ${p.c ? 'transparent' : '#242741'}`, borderRadius: 16,
          boxShadow: '0 20px 50px rgba(0,0,0,.4)'}}>
          {p.c && <div style={{position: 'absolute', left: 30, bottom: 26, font: '800 66px/1 var(--f-display, Inter,system-ui,sans-serif)', color: '#fff'}}>{label}</div>}
        </div>;
      })}
      <div style={{position: 'absolute', right: 150, top: 150, textAlign: 'right', opacity: easeOutCubic(seg(t, 0.4, 0.55))}}>
        {/* fallbackForm/fallbackFamily make explicit what previously worked only because NEUTRAL_DNA.fontDisplay
            happens to match this shot's hardcoded Inter stack — a coincidence, not a contract, until now. */}
        <div><Figure value={metric} unit={unit} ink="#fff" tone={PUR} size={120} unitScale={1}
          fallbackForm="display" fallbackFamily="Inter, system-ui, sans-serif" /></div>
      </div>
    </AbsoluteFill>
  );
};
export default VelocitySnap;
