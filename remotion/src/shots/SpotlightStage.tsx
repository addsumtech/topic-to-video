// SHOT · Spotlight Stage — a theatrical chiaroscuro register: a single warm spotlight sweeps a black stage and
// REVEALS words in sequence (PLAN → BUILD → SHIP) as the light lands on each, then widens to light the whole
// stage + the wordmark. Premium, dramatic, high-contrast. Deterministic (spotlight path + reveal = fn of t).
//
// THE ARROWS JOIN THE FILM'S WORDS, ALL OF THEM AND ONLY THEM. The connecting arrows were exactly two
// (`[0, 1].map`) drawn at a fixed ±130px from each word's centre — a three-step chain hardcoded into a register
// that takes any number of words. With two words the second arrow ran from word 2 to the clamped "word 3"
// (word 2 again): a reversed stray arrow printed straight across the last word. With four or five words the
// later ones had no arrow, so the chain the frame asserted stopped half way. And ±130px is narrower than a
// 132px word, so even the demo's arrows ran through PLAN and BUILD. The spotlight had the same shape: it visited
// the first three slots and never lit a fourth word before the widen.
// Now there are items.length - 1 arrows, each running from one word's right edge to the next word's left edge,
// the type size is chosen so every gap leaves room for an arrow, the light visits every word in turn, and a
// count or a word length the frame cannot hold throws instead of drawing words over each other.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {textWidthPx} from '../runtime/layout';

export const DURATION = 175; // ~5.8s
const DEFAULT_WORDS = ['PLAN', 'BUILD', 'SHIP'];
// Five words is where the 70%-wide band leaves a 16:9 gap narrower than a four-letter word plus an arrow.
export const MAX_SPOTLIGHT_WORDS = 5;
const ADV = 0.68, CJK = 1.05;            // a bold display serif's cap advance, generous so an arrow never touches ink
const ARROW_MIN = 64;                    // 18px of air either side + the shortest shaft that still reads as an arrow
const FS_MIN = 38;

export const SpotlightStage: React.FC<{items?: string[]; wordmark?: string}> = ({
  items: WORDS = DEFAULT_WORDS, wordmark: WORDMARK = 'WORKBUDDY'} = {}) => {
  if (!Array.isArray(WORDS) || WORDS.length < 1 || WORDS.length > MAX_SPOTLIGHT_WORDS) {
    throw new Error(`SpotlightStage needs 1-${MAX_SPOTLIGHT_WORDS} \`items\` (got ${Array.isArray(WORDS) ? WORDS.length : typeof WORDS}). ` +
      'The light reveals one word at a time along a single line with an arrow between each; past five, shorten the ' +
      'chain or cast a timeline register.');
  }
  WORDS.forEach((w, i) => {
    if (!String(w ?? '').trim()) throw new Error(`SpotlightStage: item ${i + 1} is empty.`);
  });
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const wy = H / 2 - 30;
  // WIDTH-AWARE layout: spread the band + scale the font so words never overlap, whatever their count/length.
  const n = WORDS.length;
  const spread = n <= 1 ? 0 : Math.min(0.7, 0.3 + 0.1 * n); // cap so outer words stay on-frame
  const bandA = 0.5 - spread / 2, bandB = 0.5 + spread / 2;
  const wordX = (i: number) => (n <= 1 ? 0.5 : lerp(bandA, bandB, i / (n - 1))) * W;
  const gap = n <= 1 ? W * 0.6 : ((bandB - bandA) * W) / (n - 1);
  // THE SIZE IS THE LARGEST THAT LEAVES EVERY GAP AN ARROW and keeps the outer words inside the frame, from each
  // word's own width (CJK glyphs at a full em) rather than the longest word's letter count.
  const w1 = WORDS.map((w) => textWidthPx(String(w), 1, {adv: ADV, cjk: CJK}));   // width at 1px
  const pairFS = n <= 1 ? (gap * 0.8) / w1[0]
    : Math.min(...w1.slice(0, -1).map((a, i) => (gap - ARROW_MIN) / ((a + w1[i + 1]) / 2)));
  const edgeFS = Math.min((wordX(0) - W * 0.03) / (w1[0] / 2), (W * 0.97 - wordX(n - 1)) / (w1[n - 1] / 2));
  const FS = Math.min(132, pairFS, edgeFS);
  if (FS < FS_MIN) {
    throw new Error(`SpotlightStage: ${n} words this long do not fit one line with arrows between them at this aspect ` +
      `(they would need ${Math.floor(FS)}px type, below ${FS_MIN}px). Shorten the words or pass fewer of them.`);
  }
  const halfW = (i: number) => (w1[i] * FS) / 2;

  // spotlight visits every word's slot in turn (0.08 → 0.56), then centres (→ 0.74) and widens
  const stops = WORDS.map((_, i) => wordX(i));
  const moveEnd = 0.56, segW = seg(t, 0.76, 0.94);
  let sx = stops[0];
  for (let k = 1; k < n; k++) {
    const a = 0.08 + ((k - 1) * (moveEnd - 0.08)) / (n - 1), b = 0.08 + (k * (moveEnd - 0.08)) / (n - 1);
    const p = seg(t, a, b);
    if (p > 0) sx = lerp(stops[k - 1], stops[k], easeInOutCubic(p));
  }
  const toCentre = seg(t, moveEnd, 0.74);
  if (toCentre > 0) sx = lerp(stops[n - 1], W / 2, easeInOutCubic(toCentre));
  const rx = lerp(300, 1300, easeOutCubic(segW)); // widen at the end
  const ry = lerp(300, 820, easeOutCubic(segW));

  return (
    // @dark-world: the REVEAL here is brightness — each word is drawn from near-black up to cream as the
    // beam reaches it, so on paper the words the light has found are the invisible ones and the sequence
    // runs backwards; and a spotlight is additive light, which has no mark on white (measured before this:
    // median 1.14:1 with 100% of the marks under 3:1, the beam and its cone gone entirely).
    <AbsoluteFill style={{background: darkGround(dna?.bg, '#040404')}}>
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
            font: `800 ${FS}px/1 var(--f-display, "Playfair Display", Georgia, serif)`, letterSpacing: '0.01em', whiteSpace: 'nowrap',
            color: `rgba(${lerp(40, 250, b)},${lerp(36, 240, b)},${lerp(30, 222, b)},1)`,
            textShadow: b > 0.5 ? `0 0 60px rgba(255,220,150,${(b - 0.5) * 0.9})` : 'none'}}>{w}</div>
        );
      })}
      {/* connecting arrows between words, revealed at the widen */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: easeOutCubic(seg(t, 0.8, 0.95))}}>
        {WORDS.slice(0, -1).map((_, i) => {
          const x1 = wordX(i) + halfW(i) + 18, x2 = wordX(i + 1) - halfW(i + 1) - 18;
          return <g key={i} stroke="#c7a86e" strokeWidth={3} strokeLinecap="round" fill="none">
            <line x1={x1} y1={wy} x2={x2} y2={wy} /><path d={`M${x2 - 18},${wy - 12} L${x2},${wy} L${x2 - 18},${wy + 12}`} /></g>;
        })}
      </svg>

      {/* wordmark appears at the widen */}
      <div style={{position: 'absolute', left: 0, right: 0, top: wy + 210, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.84, 0.98)), color: '#f0e6d2',
        font: '600 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.4em', paddingLeft: '0.4em'}}>{WORDMARK}</div>

      {/* heavy vignette to hold the black stage */}
      <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 46%, #0000 40%, #000000ee 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default SpotlightStage;
