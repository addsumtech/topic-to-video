// SHOT · Bento Reveal — a modern bento grid (a big hero cell + mixed small cells) whose tiles pop in one by
// one, each carrying a legible mini-widget (bars / ring / sparkline / dots / avatars / toggle), assembling
// into a finished dashboard. The 2026 SaaS "product surface" register (family A). Deterministic. No fabricated
// numbers — cells show qualitative motifs + labels; the hero cell carries the product/title, not a stat.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, life} from '../runtime/motion';
import {useDNA, dnaPalette, mix} from '../runtime/dna';

const BG_D0 = '#0a0c12';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff'];
export const DURATION = 150; // 5s

// THE CELLS KEEP READING. A dashboard that freezes the moment it finishes assembling is a screenshot of a
// product, not the product: measured by quarter of its own clip this register ran 0.0061 -> 0.0006 -> 0.0005
// -> 0.0002, i.e. a still photograph for three quarters of every beat it appears in. Each widget now keeps
// doing its own job — the bars re-read, the gauge drifts, the trace advances, the grid fills — at slow,
// mutually out-of-step periods, which is what a real dashboard looks like and is the opposite of a uniform
// wobble applied to make a number go up.
//
// It cannot shake: `life()` drives CONTENT properties, never a transform of the frame, so there is no global
// translation for scripts/shake_qa.py to see, and its period floor (3s) is enforced by a throw rather than
// left to a caller's judgement.
const Widget: React.FC<{kind: number; c: string; g: number; t: number; durF: number; fps: number}> =
  ({kind, c, g, t, durF, fps}) => {
  const L = (periodS: number, phase = 0) => life(t, durF, fps, periodS, phase);
  if (kind === 0) return (<svg width={180} height={92}>{[0, 1, 2, 3, 4].map((b) => {
    // each bar re-reads on its own beat, so the group breathes like five metrics rather than one animation
    const h = (24 + ((b * 29) % 58)) * clamp01(g * 1.4 - b * 0.06) * (0.9 + 0.2 * L(4.5 + b * 0.7, b * 0.17));
    return <rect key={b} x={b * 38} y={92 - h} width={26} height={h} rx={5} fill={c} />;
  })}</svg>);
  if (kind === 1) { const v = 0.7 * g * (0.94 + 0.12 * L(7));
    return (<svg width={110} height={110}><circle cx={55} cy={55} r={42} fill="none" stroke="#ffffff14" strokeWidth={11} />
    <circle cx={55} cy={55} r={42} fill="none" stroke={c} strokeWidth={11} strokeLinecap="round"
      strokeDasharray={2 * Math.PI * 42} strokeDashoffset={2 * Math.PI * 42 * (1 - v)} transform="rotate(-90 55 55)" /></svg>); }
  if (kind === 2) { const adv = L(9) * 2.4;   // the series advances: a live trace, not a drawn curve
    const pts = [...Array(28)].map((_, k) => `${(k / 27) * 460},${52 - Math.sin(k * 0.5 + adv) * 30 * clamp01(g * 1.3 - k / 45)}`).join(' ');
    return <svg width={460} height={100}><polyline points={pts} fill="none" stroke={c} strokeWidth={5} strokeLinecap="round" /></svg>; }
  if (kind === 3) { const fill = clamp01(g * (0.86 + 0.2 * L(6.5, 0.3)));
    return (<svg width={190} height={100}>{[...Array(15)].map((_, k) => (
    <circle key={k} cx={16 + (k % 5) * 42} cy={20 + Math.floor(k / 5) * 34} r={11} fill={k / 15 < fill ? c : '#ffffff14'} />))}</svg>); }
  if (kind === 4) return (<svg width={280} height={60}>{[0, 1, 2].map((a) => (
    <circle key={a} cx={34 + a * 44} cy={30} r={26} fill={c} opacity={clamp01(g * 1.5 - a * 0.2)} stroke="#0a0c12" strokeWidth={4} />))}
    <circle cx={34 + 3 * 44} cy={30} r={26} fill="#2a3048" opacity={clamp01(g * 1.5 - 0.6)} /></svg>);
  // toggle
  const on = g > 0.5;
  return (<svg width={140} height={64}><rect x={2} y={12} width={92} height={40} rx={20} fill={on ? c : '#2a3048'} />
    <circle cx={on ? 74 : 22} cy={32} r={16} fill="#fff" /></svg>);
};

export const BentoReveal: React.FC<{title?: string; hero?: string; items?: string[]; heroKicker?: string}> = ({
  title: TITLE = 'WorkBuddy', hero: HEROSUB = 'your workspace, assembled',
  // The hero cell's kicker used to be the literal string 'DASHBOARD', hardcoded — so every film that
  // reached for this register printed a product-demo word onto its own frame whatever it was about.
  heroKicker: HEROKICKER = 'DASHBOARD', items: ITEMS =
    ['Throughput', 'Coverage', 'Trend', 'Signals', 'Team', 'Auto-sync']} = {}) => {
  const dna = useDNA();
  const TONES = dnaPalette(dna, 5) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const pad = 120, gap = 22;
  const gw = (W - pad * 2), gh = (H - pad * 2), u = gw / 12, v = gh / 6;
  // [col,row,wSpan,hSpan] on a 12×6 grid; index 0 is the hero cell
  const layout = [[0, 0, 6, 4], [6, 0, 3, 2], [9, 0, 3, 2], [6, 2, 6, 2], [0, 4, 3, 2], [3, 4, 3, 2], [6, 4, 6, 2]];
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 30% 20%, ${dna ? mix(BG, dna.accent, 0.12) : '#12162a'}, ${BG} 72%)`}}>
      {layout.map((L, i) => {
        const [c, r, ws, hs] = L;
        const x = pad + c * u + gap / 2, y = pad + r * v + gap / 2;
        const w = ws * u - gap, h = hs * v - gap;
        const st = 0.06 + i * 0.1;
        const e = easeOutBack(clamp01(seg(t, st, st + 0.26)));
        const g = clamp01(seg(t, st + 0.05, st + 0.5));
        const hero = i === 0;
        const tone = TONES[i % TONES.length];
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: h,
            opacity: clamp01(e * 1.4), transform: `scale(${lerp(0.86, 1, e)})`, transformOrigin: 'center',
            background: hero ? `linear-gradient(150deg, ${tone}, ${dna ? mix(tone, BG, 0.55) : '#2c3ac0'})`
              : (dna ? `linear-gradient(160deg, ${mix(dna.surface, BG, 0.35)}, ${BG})` : 'linear-gradient(160deg, #14172480, #0d0f18)'),
            border: `1px solid ${hero ? 'transparent' : (dna?.line ?? '#20243a')}`, borderRadius: 22, overflow: 'hidden',
            padding: hero ? 54 : 34, display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
            boxShadow: '0 24px 60px #0006'}}>
            {hero ? (
              <>
                <div style={{color: dna?.onAccent ?? '#ffffffcc',
                  font: '600 24px/1 var(--f-mono, "JetBrains Mono", monospace)',
                  letterSpacing: dna?.labelSpacing ?? '0.14em'}}>{HEROKICKER}</div>
                <div>
                  <div style={{color: '#fff', font: '800 96px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em'}}>{TITLE}</div>
                  <div style={{color: '#ffffffdd', font: '500 32px/1.2 var(--f-body, Inter, system-ui, sans-serif)', marginTop: 16}}>{HEROSUB}</div>
                </div>
              </>
            ) : (
              <>
                <div style={{color: dna?.dim ?? '#8b93a8', font: '600 22px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.1em'}}>{ITEMS[(i - 1) % ITEMS.length]}</div>
                <div style={{alignSelf: 'flex-start'}}><Widget t={t} durF={durationInFrames} fps={fps} kind={(i - 1) % 6} c={tone} g={g} /></div>
              </>
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default BentoReveal;
