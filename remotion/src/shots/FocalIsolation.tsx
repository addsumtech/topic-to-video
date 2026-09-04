// SHOT · Focal Isolation — Vercel/Linear language: out of a whole field, ONE thing is isolated. The
// periphery blurs + a vignette darkens the edges + a spotlight lands on the focal item, which sharpens,
// rings, and rises. Mid-dark SLATE (distinct from the near-black Command palette + the light shots).
// Real DoF-style blur on the non-focal planes — the flat HTML tier cannot pull focus like this.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 135; // 4.5s
const ACCENT0 = '#2E7BFF', SPOT = '#ffe6ad';

export const FocalIsolation: React.FC<{focalLabel?: string; items?: string[]}> = ({
  focalLabel = 'Your files · on your machine',
  items = ['Cloud drive', 'Shared server', 'Email', 'Someone’s laptop', 'YOUR MACHINE', 'A vendor', 'Chat export', 'Backup', 'The internet'],
}) => {
  const t = useT();
  const dna = useDNA(); const ACCENT = dna?.accent ?? ACCENT0;
  const {width: W, height: H} = useVideoConfig();
  const iso = easeOutCubic(seg(t, 0.32, 0.66)); // isolation progress
  const focal = 4; // centre item
  // The grid is fitted to the CONTENT ZONE. Three 220px rows and two 90px gutters are 840px tall and the
  // grid was centred in the frame, so the bottom row — 'The internet' among them — sat in the strip the
  // renderer burns the caption over. The row height yields; the gutters and the column rhythm do not.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const cols = 3, cw = 380, gx = 90, gy = 90;
  const ch = Math.min(220, ((zBot - zTop) - 2 * gy) / 3);
  const gridW = cols * cw + (cols - 1) * gx, gridH = 3 * ch + 2 * gy;
  const ox = (W - gridW) / 2, oy = zTop + ((zBot - zTop) - gridH) / 2;
  const fx = ox + (focal % cols) * (cw + gx) + cw / 2, fy = oy + Math.floor(focal / cols) * (ch + gy) + ch / 2;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 45%, #1b2434, #0d131d)'}}>
      {/* spotlight that lands on the focal item */}
      <div style={{position: 'absolute', left: fx - 520, top: fy - 520, width: 1040, height: 1040,
        background: `radial-gradient(closest-side, ${SPOT}${Math.round(28 * iso).toString(16).padStart(2, '0')}, transparent)`,
        filter: 'blur(20px)', opacity: iso}} />
      {items.map((label, i) => {
        const isF = i === focal;
        const col = i % cols, row = Math.floor(i / cols);
        const x = ox + col * (cw + gx), y = oy + row * (ch + gy);
        const appear = easeOutCubic(seg(t, i * 0.03, i * 0.03 + 0.2));
        const blur = isF ? 0 : 9 * iso;
        const op = (isF ? 1 : lerp(0.9, 0.18, iso)) * clamp01(appear);
        const sc = isF ? lerp(1, 1.12, easeOutBack(clamp01(iso))) : lerp(1, 0.96, iso);
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: cw, height: ch, opacity: op,
            transform: `scale(${sc})`, transformOrigin: 'center', filter: blur > 0.5 ? `blur(${blur}px)` : undefined,
            background: isF ? 'linear-gradient(160deg,#223049,#18212f)' : '#161d29',
            border: `${isF ? 2 : 1}px solid ${isF ? ACCENT : '#26303f'}`, borderRadius: 16,
            boxShadow: isF ? `0 0 0 6px ${ACCENT}22, 0 30px 70px rgba(0,0,0,.5)` : 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <div style={{font: `${isF ? 700 : 500} ${isF ? 40 : 32}px/1.15 var(--f-body, Inter,system-ui,sans-serif)`,
              color: isF ? '#eaf1ff' : '#7f8da3', textAlign: 'center', padding: '0 24px'}}>{label}</div>
          </div>
        );
      })}
      {/* vignette darkening the edges as isolation lands */}
      <AbsoluteFill style={{background: 'radial-gradient(70% 70% at 50% 46%, transparent 55%, #060910 100%)', opacity: 0.85 * iso, pointerEvents: 'none'}} />
      {/* focal label */}
      {iso > 0.4 && (
        <div style={{position: 'absolute', left: 0, right: 0, top: fy + ch / 2 + 40, textAlign: 'center',
          opacity: easeOutCubic(seg(t, 0.5, 0.7)), font: '700 44px/1 var(--f-body, Inter,system-ui,sans-serif)', color: '#eaf1ff'}}>{focalLabel}</div>
      )}
    </AbsoluteFill>
  );
};
export default FocalIsolation;
