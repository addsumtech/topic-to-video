// GFactorNoise — why parallel imaging can't go much faster. As the acceleration factor R rises, unfolding the
// aliased signal AMPLIFIES noise (the g-factor): the reconstructed tile gets grainier, and past R≈3 it's too noisy
// to use — so clinical R caps at 2–3 (and can never exceed the coil count). The covarying "R up ⇒ noise up ⇒ cap"
// IS the idea; red marks the unusable zone (viz-semantics: red = bad). Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom} from '../runtime/layout';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'R = 2–3 max · never beyond the coil count',
  'g-factor noise →',
];
const WARN = '#ff5d6c';

// `factor` is the amplification the FILM measured. No default: the read-out used to count 1.0x -> 3.0x off
// the clock and print the result as though it had been measured, on whatever topic reached for the register.
// The grain still grows either way — that is the illustration; the NUMBER is a claim and needs a source.
export const GFactorNoise: React.FC<{accent?: string; label?: string; factor?: number | null}> = ({
  accent = '#22d3ee', label = 'Unfolding amplifies noise', factor = null,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // R rises to the supplied factor (or, with none, to the illustrative cap that drives the grain only)
  const R = lerp(1, factor == null ? 3 : factor, clamp01(seg(t, 0.12, 0.8)));
  const noise = clamp01((R - 1) / 2.6);                     // noise grows with R

  // a small reconstructed tile that gets grainier as R rises
  const tx = W * 0.5 - 200, ty = H * 0.26, tw = 400, th = 300;
  const grain: React.ReactNode[] = [];
  const n = Math.round(40 + noise * 520);
  for (let i = 0; i < n; i++) {
    grain.push(<circle key={i} cx={tx + hash01(i * 2 + 1) * tw} cy={ty + hash01(i * 2 + 7) * th}
      r={0.8 + hash01(i * 3) * 1.6} fill={hash01(i) > 0.7 ? WARN : '#ffffff'} opacity={0.15 + noise * 0.5} />);
  }

  // the R track: green usable zone (≤3) then a red g-factor zone
  // the track's tick labels hang below it; both come off the content zone's floor rather than 78% of a frame
  const by = Math.min(H * 0.78, contentBottom(W, H) - 78);
  const bx = W * 0.24, bw = W * 0.52, capFrac = 3 / 5;   // track spans R = 1..5
  const rFrac = (R - 1) / 4;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #0b1120, #05060a)')}}>
      {/* the noisy reconstructed tile */}
      <div style={{position: 'absolute', left: tx, top: ty, width: tw, height: th, borderRadius: 12,
        border: `2px solid ${noise > 0.75 ? WARN : accent}`, background: 'linear-gradient(160deg,#0e1b30,#0a1424)', overflow: 'hidden'}}>
        <svg width={tw} height={th}><g>{grain}</g></svg>
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* track */}
        <rect x={bx} y={by} width={bw * capFrac} height={12} rx={6} fill={accent} opacity={0.28} />
        <rect x={bx + bw * capFrac} y={by} width={bw * (1 - capFrac)} height={12} rx={6} fill={WARN} opacity={0.3} />
        <rect x={bx} y={by} width={bw * rFrac} height={12} rx={6} fill={R > 3.02 ? WARN : accent} />
        <line x1={bx + bw * capFrac} y1={by - 20} x2={bx + bw * capFrac} y2={by + 32} stroke={WARN} strokeWidth={2} strokeDasharray="4 4" />
        <text x={bx + bw * capFrac} y={by - 28} fill={WARN} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" textAnchor="middle">g-factor noise →</text>
        {[1, 2, 3, 4, 5].map((v) => (
          <text key={v} x={bx + bw * ((v - 1) / 4)} y={by + 52} fill="#8aa" fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" textAnchor="middle">{v}×</text>
        ))}
        {/* the live R read-out — drawn only when the film supplied a measured factor */}
        {factor == null ? null : (
          <text x={bx + bw * rFrac} y={by - 22} fill="#eaf6ff" fontSize="40" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} textAnchor="middle">
            {R.toFixed(1)}×</text>
        )}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        <div style={{marginTop: 8, font: "600 22px/1 var(--f-mono, 'JetBrains Mono', monospace)", color: WARN, letterSpacing: '0.12em'}}>
          R = 2–3 max · never beyond the coil count</div>
      </div>
    </AbsoluteFill>
  );
};
export default GFactorNoise;
