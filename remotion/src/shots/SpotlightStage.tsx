// SHOT · Spotlight Stage — a theatrical chiaroscuro register: a single warm spotlight sweeps a black stage and
// REVEALS words in sequence (PLAN → BUILD → SHIP) as the light lands on each, then widens to light the whole
// stage + the wordmark. Premium, dramatic, high-contrast. Deterministic (spotlight path + reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';

export const DURATION = 175; // ~5.8s
const DEFAULT_WORDS = ['PLAN', 'BUILD', 'SHIP'];

export const SpotlightStage: React.FC<{items?: string[]; wordmark?: string}> = ({
  items: WORDS = DEFAULT_WORDS, wordmark: WORDMARK = 'WORKBUDDY'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const wy = H / 2 - 30;
  // WIDTH-AWARE layout: spread the band + scale the font so words never overlap, whatever their count/length.
  const n = WORDS.length;
  const maxLen = Math.max(...WORDS.map((w) => w.length), 1);
  const spread = n <= 1 ? 0 : Math.min(0.7, 0.3 + 0.1 * n); // cap so outer words stay on-frame
  const bandA = 0.5 - spread / 2, bandB = 0.5 + spread / 2;
  const wordX = (i: number) => (n <= 1 ? 0.5 : lerp(bandA, bandB, Math.min(i, n - 1) / (n - 1))) * W;
  const gap = n <= 1 ? W * 0.6 : ((bandB - bandA) * W) / (n - 1);
  const FS = Math.max(38, Math.min(132, (gap * 0.8) / (maxLen * 0.62))); // shrink so a word fits its slot (Playfair ~0.62 char-w)

  // spotlight visits each word's slot (first three stops), then centres + widens
  const seg1 = seg(t, 0.08, 0.34), seg2 = seg(t, 0.34, 0.56), seg3 = seg(t, 0.56, 0.74), segW = seg(t, 0.76, 0.94);
  const wx0 = wordX(0), wx1 = wordX(Math.min(1, n - 1)), wx2 = wordX(Math.min(2, n - 1));
  let sx = wx0;
  sx = lerp(wx0, wx1, easeInOutCubic(seg1));
  if (seg2 > 0) sx = lerp(wx1, wx2, easeInOutCubic(seg2));
  if (seg3 > 0) sx = lerp(wx2, W / 2, easeInOutCubic(seg3));
  if (seg1 <= 0) sx = wx0;
  const rx = lerp(300, 1300, easeOutCubic(segW)); // widen at the end
  const ry = lerp(300, 820, easeOutCubic(segW));

  return (
    <AbsoluteFill style={{background: '#040404'}}>
      {/* floor sheen */}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: H * 0.4,
        background: 'linear-gradient(#0000, #0d0d10)'}} />

      {/* the spotlight (soft warm ellipse) */}
      <div style={{position: 'absolute', left: sx - rx, top: wy - ry / 2, width: rx * 2, height: ry,
        background: `radial-gradient(ellipse at center, #fbe7c266 0%, #6b5a3a22 34%, #0000 66%)`, pointerEvents: 'none'}} />
      {/* light cone from above */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe9c0" stopOpacity="0.16" /><stop offset="1" stopColor="#ffe9c0" stopOpacity="0" /></linearGradient></defs>
        <path d={`M${sx - 60},-20 L${sx + 60},-20 L${sx + rx * 0.7},${wy + ry / 2} L${sx - rx * 0.7},${wy + ry / 2} Z`} fill="url(#cone)" opacity={1 - easeOutCubic(segW) * 0.4} />
      </svg>

      {/* words — lit by proximity of the spotlight centre */}
      {WORDS.map((w, i) => {
        const d = Math.abs(sx - wordX(i));
        const lit = clamp01(1 - d / 360); // brightness falloff
        const finalLit = easeOutCubic(segW); // all lit at the end
        const b = Math.max(lit, finalLit * 0.9);
        return (
          <div key={i} style={{position: 'absolute', left: wordX(i), top: wy, transform: 'translate(-50%,-50%)',
            font: `800 ${FS}px/1 "Playfair Display", Georgia, serif`, letterSpacing: '0.01em', whiteSpace: 'nowrap',
            color: `rgba(${lerp(40, 250, b)},${lerp(36, 240, b)},${lerp(30, 222, b)},1)`,
            textShadow: b > 0.5 ? `0 0 60px rgba(255,220,150,${(b - 0.5) * 0.9})` : 'none'}}>{w}</div>
        );
      })}
      {/* connecting arrows between words, revealed at the widen */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: easeOutCubic(seg(t, 0.8, 0.95))}}>
        {[0, 1].map((i) => {
          const x1 = wordX(i) + 130, x2 = wordX(i + 1) - 130;
          return <g key={i} stroke="#c7a86e" strokeWidth={3} strokeLinecap="round" fill="none">
            <line x1={x1} y1={wy} x2={x2} y2={wy} /><path d={`M${x2 - 18},${wy - 12} L${x2},${wy} L${x2 - 18},${wy + 12}`} /></g>;
        })}
      </svg>

      {/* wordmark appears at the widen */}
      <div style={{position: 'absolute', left: 0, right: 0, top: wy + 210, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.84, 0.98)), color: '#f0e6d2',
        font: '600 34px/1 "JetBrains Mono", monospace', letterSpacing: '0.4em', paddingLeft: '0.4em'}}>{WORDMARK}</div>

      {/* heavy vignette to hold the black stage */}
      <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 46%, #0000 40%, #000000ee 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default SpotlightStage;
