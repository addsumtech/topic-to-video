import React from 'react';
import {useCurrentFrame} from 'remotion';

// scene-local caption segments, in frames
export type CaptionSeg = {text: string; from: number; to: number};

// --- WCAG helpers so the Remotion caption matches the LOCAL tier's default `overlay` (render._draw_caption):
// NO background bar — the text sits flush at the bottom in the deck's ink (or a max-contrast flip) with a
// subtle OPPOSITE-luminance outline, so it reads over ANY ground (empty frame / tint / photo / 3D render) on
// any theme, without a heavy black strip. ---
const _rgb = (hex: string): [number, number, number] => {
  let h = (hex || '').replace('#', '').trim();
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  if (h.length !== 6) return [255, 255, 255];
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
};
const _relLum = ([r, g, b]: [number, number, number]): number => {
  const f = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const _contrast = (a: [number, number, number], b: [number, number, number]): number => {
  const l1 = _relLum(a);
  const l2 = _relLum(b);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
};
const _hex = ([r, g, b]: [number, number, number]): string =>
  '#' + [r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');

export const Captions: React.FC<{segments: CaptionSeg[]; fontPx?: number; theme?: {bg: string; fg: string}}> = ({
  segments,
  fontPx,
  theme,
}) => {
  const frame = useCurrentFrame();
  const seg = segments.find((s) => frame >= s.from && frame < s.to);
  if (!seg || !seg.text) return null;

  // base = the max-contrast pick among [--fg, --bg, near-black, near-white] vs the theme bg (the ground
  // proxy — a React overlay can't sample the pixels under it, matching the local fallback when nothing is
  // sampled). This KEEPS the deck ink when it reads and flips only when it must — the colour adaptation.
  const bg = _rgb(theme?.bg || '#0d1117');
  const fg = _rgb(theme?.fg || '#f0f3f8');
  const cands: [number, number, number][] = [fg, bg, [17, 17, 17], [245, 244, 240]];
  const base = cands.reduce((best, c) => (_contrast(c, bg) > _contrast(best, bg) ? c : best), cands[0]);
  // halo = the OPPOSITE luminance of the chosen ink (a light text gets a dark outline and vice-versa), so the
  // caption survives a bright patch under a dark theme (or a dark patch under a light one) with no bar.
  const halo = _relLum(base) < 0.45 ? _hex([245, 244, 240]) : _hex([12, 12, 12]);
  // an 8-direction 2px outline (the CSS analogue of the PIL _put halo offsets) + one soft drop for depth.
  const textShadow = [
    `-2px -2px 0 ${halo}`, `2px -2px 0 ${halo}`, `-2px 2px 0 ${halo}`, `2px 2px 0 ${halo}`,
    `0 -2px 0 ${halo}`, `0 2px 0 ${halo}`, `-2px 0 0 ${halo}`, `2px 0 0 ${halo}`,
    `0 3px 12px ${halo}99`,
  ].join(', ');

  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: '2.4%', display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          maxWidth: '86%',
          textAlign: 'center',
          color: _hex(base),
          fontSize: fontPx || 48, // canvas-derived (min(W,H)*0.045), like the local renderer
          fontWeight: 700, // a touch heavier than the boxed version — the outline, not a bar, carries legibility
          lineHeight: 1.3,
          // Latin first, then CJK system fonts so zh/ja/ko don't tofu in headless Chromium
          fontFamily: 'Helvetica, Arial, "PingFang SC", "Hiragino Sans", "Noto Sans CJK SC", sans-serif',
          padding: '0 24px', // horizontal breathing room only — NO background bar
          textShadow,
        }}
      >
        {seg.text}
      </div>
    </div>
  );
};
