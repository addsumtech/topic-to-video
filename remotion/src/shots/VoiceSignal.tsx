// SHOT · Voice Signal — audio-reactive language (a 2026 trend + a true Remotion edge): a live voice waveform
// IS the visual. In the demo the signal is a deterministic pseudo-voice; wired into the pipeline it reads the
// real narration via @remotion/media-utils visualizeAudio. Dark + a bright signal accent. Deterministic.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const ACC_D0 = '#3FE0FF';
const DEFAULT_PHASES = [{at: 0.05, label: 'Listening…'}, {at: 0.34, label: 'Working…'}, {at: 0.74, label: 'Done ✓'}];

// deterministic pseudo-voice envelope + per-bar amplitude (stands in for real getAudioData in the demo)
function amp(i: number, frame: number, env: number): number {
  const s = Math.abs(Math.sin(i * 0.34 + frame * 0.22) + 0.6 * Math.sin(i * 0.71 - frame * 0.16) + 0.35 * Math.sin(i * 1.3 + frame * 0.31));
  return env * (0.12 + s / 2.2);
}

export const VoiceSignal: React.FC<{phases?: {at: number; label: string}[]}> = ({phases: PHASES = DEFAULT_PHASES} = {}) => {
  const dna = useDNA();
  const ACC = dna?.accent ?? ACC_D0;
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const N = 72, midY = H / 2, maxH = 380;
  // speech envelope: swells while "listening/working", drops to a held tone at "done"
  const talking = t < 0.72;
  const env = talking ? 0.55 + 0.45 * Math.abs(Math.sin(t * 26)) : lerp(0.5, 0.12, easeOutCubic(seg(t, 0.72, 0.9)));
  const phase = [...PHASES].reverse().find((p) => t > p.at) || PHASES[0];
  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 46%, #0e1826, #05080f 72%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8af0ff" /><stop offset="1" stopColor={ACC} /></linearGradient>
          <filter id="g"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <g filter="url(#g)">
          {[...Array(N)].map((_, i) => {
            const x = (W - (N - 1) * 22) / 2 + i * 22;
            const h = amp(i, frame, env) * maxH;
            return <rect key={i} x={x - 6} y={midY - h} width={12} height={h * 2} rx={6} fill="url(#bar)"
              opacity={0.55 + 0.45 * (h / maxH)} />;
          })}
        </g>
        <line x1={0} y1={midY} x2={W} y2={midY} stroke={ACC} strokeWidth={1.5} opacity={0.25} />
      </svg>
      {/* phase label */}
      <div style={{position: 'absolute', left: 0, right: 0, top: midY + 260, textAlign: 'center',
        font: '800 66px/1 var(--f-display, Inter,system-ui,sans-serif)', color: t > 0.74 ? '#59f0b0' : '#dffaff'}}>{phase.label}</div>
    </AbsoluteFill>
  );
};
export default VoiceSignal;
