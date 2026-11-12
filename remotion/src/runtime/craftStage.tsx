// CRAFT KIT · STAGE — the lit ground, the motifs and the material helpers every built shot uses
// (references/craft-standard.md §Look, §Light, §Material).
//
// WHY (2026-11-12): a flat fill is the one thing that most reads as "template". Measured with surface_qa on the peer's
// 150 redesigned shots, 25 % of frames are LIT (modelled regions); ours 0 %. Their stage is a tinted vertical gradient,
// one key light pool, a fill of the second accent, an optional horizon band and a vignette — and the subject stands
// OUTSIDE it (on top), so the vignette never dims the thing the beat is about. The SaaS launch films add ONE brand motif
// (Loom's pearls, Slack's sparkle, Perplexity's orbs) that recurs through the film.
// The film's finish layer (runtime/finish.tsx) owns grain; this owns light. Every function is a pure function of frame.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {mix} from './dna';

const hexA = (hex: string, a: number): string => {
  const h = hex.replace('#', '');
  const f = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6);
  const n = parseInt(f, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${Math.max(0, Math.min(1, a)).toFixed(3)})`;
};
export const rgba = hexA;

const lum = (hex: string): number => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6), 16);
  return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
};
export const isDark = (hex: string) => lum(hex) < 0.45;

const hash = (n: number): number => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/**
 * THE STAGE. `ground` is the beat's ground (the hex the caption ink and the seams read); the stage paints a tinted
 * gradient of it, a key light at `keyAt` in `light`, a fill of `fill` at `fillAt`, an optional horizon band, and a
 * vignette in the ground's own shade (never pure black). `breathe` (0–1) lets the key swell very slowly so a held
 * frame is never dead. Children are BACKGROUND decoration (Dust, Orbs, far planes); put the subject after the stage.
 */
export const LitStage: React.FC<{
  ground: string; light?: string; fill?: string | null; keyAt?: {x: number; y: number}; fillAt?: {x: number; y: number};
  horizon?: number; intensity?: number; breathe?: number; vignette?: number; children?: React.ReactNode;
}> = ({ground, light, fill = null, keyAt = {x: 0.5, y: 0.1}, fillAt = {x: 0.86, y: 0.92}, horizon, intensity = 1,
  breathe = 0.5, vignette, children}) => {
  const frame = useCurrentFrame();
  const dark = isDark(ground);
  const key = light ?? (dark ? mix(ground, '#ffffff', 0.55) : '#ffffff');
  const b = 1 + breathe * 0.08 * Math.sin(frame / 41);
  const top = dark ? mix(ground, key, 0.08) : mix(ground, '#ffffff', 0.55);
  const bottom = dark ? mix(ground, '#000000', 0.42) : mix(ground, '#000000', 0.06);
  const k = (dark ? 0.42 : 0.85) * intensity * b;
  const f = (dark ? 0.2 : 0.12) * intensity;
  const v = vignette ?? (dark ? 0.6 : 0.14);
  const shadeC = dark ? mix(ground, '#000000', 0.7) : mix(ground, '#1a2a24', 0.55);
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${top} 0%, ${ground} 50%, ${bottom} 100%)`, overflow: 'hidden'}}>
      <AbsoluteFill style={{background:
        `radial-gradient(ellipse 60% 64% at ${keyAt.x * 100}% ${keyAt.y * 100}%, ${hexA(key, k)} 0%, ${hexA(key, 0)} 70%)` +
        (fill ? `, radial-gradient(ellipse 48% 44% at ${fillAt.x * 100}% ${fillAt.y * 100}%, ${hexA(fill, f)} 0%, ${hexA(fill, 0)} 72%)` : '')}} />
      {horizon !== undefined ? (
        <div style={{position: 'absolute', left: '-10%', right: '-10%', top: `${horizon * 100 - 10}%`, height: '20%',
          background: `radial-gradient(ellipse 50% 50% at 50% 50%, ${hexA(key, dark ? 0.3 * intensity : 0.55)} 0%, ${hexA(key, 0)} 70%)`}} />
      ) : null}
      {children}
      <AbsoluteFill style={{background: `radial-gradient(ellipse 78% 74% at 50% 46%, ${hexA(shadeC, 0)} 52%, ${hexA(shadeC, v)} 100%)`}} />
    </AbsoluteFill>
  );
};

/** Deterministic floating bokeh: `n` soft discs drifting slowly upward, nearer ones larger and blurrier. */
export const Dust: React.FC<{n?: number; color?: string; seed?: number; opacity?: number; speed?: number}> =
  ({n = 26, color = '#ffffff', seed = 1, opacity = 0.5, speed = 1}) => {
    const frame = useCurrentFrame();
    const {width: W, height: H} = useVideoConfig();
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        {Array.from({length: n}, (_, i) => {
          const z = hash(seed * 97 + i * 3.1);
          const r = (2 + z * z * 12) * H / 1080;
          const x = hash(seed * 13 + i * 7.7) * W + Math.sin(frame / (90 + i * 3) + i) * 18 * z;
          const y = (((hash(seed * 31 + i * 5.3) * H - frame * speed * (0.2 + z * 0.6)) % H) + H) % H;
          return <div key={i} style={{position: 'absolute', left: x - r, top: y - r, width: r * 2, height: r * 2,
            borderRadius: '50%', background: color, opacity: opacity * (0.25 + 0.75 * (1 - z * 0.6)),
            filter: `blur(${(z * 3).toFixed(2)}px)`}} />;
        })}
      </AbsoluteFill>
    );
  };

/** A brand motif of soft lit spheres (the pearls / orbs device): each sphere is shaded by one gradient with a key
 *  highlight upper-left and a rim of the tint; they drift by depth. Positions are [x, y, r] in frame fractions. */
export const Orbs: React.FC<{orbs: [number, number, number][]; tint: string; light?: string; drift?: number}> =
  ({orbs, tint, light = '#ffffff', drift = 1}) => {
    const frame = useCurrentFrame();
    const {width: W, height: H} = useVideoConfig();
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        {orbs.map(([fx, fy, fr], i) => {
          const r = fr * H, dx = Math.sin(frame / 70 + i * 1.7) * 10 * drift * fr * 6, dy = Math.cos(frame / 83 + i) * 8 * drift * fr * 6;
          return <div key={i} style={{position: 'absolute', left: fx * W - r + dx, top: fy * H - r + dy, width: r * 2, height: r * 2,
            borderRadius: '50%', background: `radial-gradient(circle at 34% 30%, ${light} 0%, ${mix(tint, light, 0.55)} 22%, ${tint} 58%, ${mix(tint, '#000000', 0.35)} 100%)`,
            boxShadow: `0 ${r * 0.18}px ${r * 0.5}px ${hexA(mix(tint, '#000000', 0.5), 0.35)}`}} />;
        })}
      </AbsoluteFill>
    );
  };

/** One pass of light across an element (put it inside the element, which must clip: overflow hidden + its radius).
 *  Give it to the hero ONCE, never to everything. */
export const Sheen: React.FC<{from: number; to: number; strength?: number; angle?: number}> =
  ({from, to, strength = 0.45, angle = 115}) => {
    const frame = useCurrentFrame();
    const p = (frame - from) / Math.max(1, to - from);
    if (p <= 0 || p >= 1) return null;
    const pos = -40 + p * 180;
    return <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', background:
      `linear-gradient(${angle}deg, transparent ${pos - 18}%, rgba(255,255,255,${strength}) ${pos}%, transparent ${pos + 18}%)`}} />;
  };

/** A four-point sparkle (the "AI" star): a path in a 1-unit box, for an <svg viewBox="-1 -1 2 2">. */
export const SPARKLE_PATH = 'M0,-1 C0.08,-0.28 0.28,-0.08 1,0 C0.28,0.08 0.08,0.28 0,1 C-0.08,0.28 -0.28,0.08 -1,0 C-0.28,-0.08 -0.08,-0.28 0,-1 Z';
export const Sparkle: React.FC<{size: number; color: string; glowColor?: string; rotate?: number; style?: React.CSSProperties}> =
  ({size, color, glowColor, rotate = 0, style}) => (
    <svg width={size} height={size} viewBox="-1 -1 2 2" style={{overflow: 'visible', transform: `rotate(${rotate}deg)`,
      filter: glowColor ? `drop-shadow(0 0 ${size * 0.18}px ${glowColor})` : undefined, ...style}}>
      <path d={SPARKLE_PATH} fill={color} />
    </svg>
  );

/** text-shadow glow for the HERO word only. */
export const glow = (color: string, strength = 0.6): string =>
  `0 0 ${(6 * strength).toFixed(1)}px ${hexA(color, 0.55 * strength)}, 0 0 ${(24 * strength).toFixed(1)}px ${hexA(color, 0.4 * strength)}, 0 0 ${(64 * strength).toFixed(1)}px ${hexA(color, 0.26 * strength)}`;

/** Two-layer soft shadow (contact + ambient), tinted by the ground: depth 0..3. */
export const softShadow = (depth: number, tint = '#0b1a14'): string =>
  `0 ${(1 + depth).toFixed(1)}px ${(3 + depth * 2).toFixed(1)}px ${hexA(tint, 0.1 + 0.03 * depth)}, ` +
  `0 ${(8 + depth * 14).toFixed(1)}px ${(24 + depth * 34).toFixed(1)}px ${hexA(tint, 0.12 + 0.05 * depth)}`;

/** A panel's material: a faint vertical gradient, a hairline edge and a top inner highlight. */
export const surface = (base: string, opts: {line?: string; dark?: boolean; depth?: number; tint?: string} = {}): React.CSSProperties => {
  const dark = opts.dark ?? isDark(base);
  return {
    background: `linear-gradient(180deg, ${mix(base, '#ffffff', dark ? 0.05 : 0.6)} 0%, ${base} 60%)`,
    border: `1px solid ${opts.line ?? (dark ? 'rgba(255,255,255,0.09)' : 'rgba(15,30,25,0.09)')}`,
    boxShadow: `inset 0 1px 0 ${dark ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.9)'}, ${softShadow(opts.depth ?? 1, opts.tint ?? (dark ? '#000000' : '#0b1a14'))}`,
  };
};
