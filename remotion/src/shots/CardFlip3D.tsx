// SHOT · Card Flip 3D — a row of cards standing in perspective FLIP 180° on their Y axis (staggered), a
// light sheen sweeping the seam at the half-turn, revealing the payoff on the back. Pure CSS 3D
// (preserve-3d + backface-visibility) — no WebGL. The "question → answer, turned over" register. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette, shade} from '../runtime/dna';
import {fitTextOnNLines} from '@remotion/layout-utils';

export const DURATION = 150; // 5s
const BG = '#0a0c13', ACC0 = '#6ea8ff';

type Item = {front?: string; back?: string};

// Both faces take their fill from the DNA. The back used to blend the tone into a hardcoded #2c3ac0 and
// the front into a hardcoded near-black, so on a themed film the cards arrived in their own palette —
// teal and pink cards on a `data`-DNA deck. `?? <original>` keeps an un-themed render byte-identical.
const Face: React.FC<{children: React.ReactNode; back?: boolean; tone: string;
  faceBg?: string | null; faceEdge?: string | null}> = ({children, back, tone, faceBg, faceEdge}) => (
  <div style={{position: 'absolute', inset: 0, backfaceVisibility: 'hidden',
    transform: back ? 'rotateY(180deg)' : undefined, borderRadius: 26,
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40,
    background: back
      ? `linear-gradient(155deg, ${tone}, ${shade(tone, 0.45)})`
      : (faceBg ?? 'linear-gradient(155deg, #171a28, #0f1220)'),
    border: `1px solid ${back ? 'transparent' : (faceEdge ?? '#262a42')}`,
    boxShadow: '0 40px 90px #0008, inset 0 1px 0 #ffffff12'}}>{children}</div>
);

export const CardFlip3D: React.FC<{items?: Item[]; title?: string; backLabel?: string}> = ({
  items: ITEMS = [{front: 'Manual', back: 'Automated'}, {front: 'Hours', back: 'Seconds'}, {front: 'Guesswork', back: 'Grounded'}],
  title: TITLE = 'What changes', backLabel: BACKLABEL = '实际'
  } = {}) => {
  const t = useT();
  const dna = useDNA(); const ACC = dna?.accent ?? ACC0;
  // Four film-coherent hues instead of three hardcoded ones (pink/teal/amber), which is why a themed
  // deck's cards used to arrive in a palette that was not the film's. null DNA -> null -> the originals.
  const PAL = dnaPalette(dna, 4);
  const FACE_BG = dna ? `linear-gradient(155deg, ${dna.surface}, ${dna.bg})` : null;
  const FACE_EDGE = dna?.surfaceBorder ?? null;
  const INK = dna?.fg ?? '#eef2ff', DIM = dna?.dim ?? '#8b93a8', ON = dna?.onAccent ?? '#fff';
  const {width: W} = useVideoConfig();
  const dispFace = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';
  const cards = ITEMS.slice(0, 4);
  const n = cards.length;
  const cw = 440, ch = 430, gap = 56;   // ch 560 -> 430: a single short line left ~70% of the card void
  // Fit the real string in the real face inside the card, up to two lines, capped at the register's 64px.
  // A fixed 64 broke a Chinese label mid-word here ("...不会失/败"); short Latin copy still hits the cap
  // and renders exactly as before. validateFontIsLoaded so a measurement taken before the faces load
  // fails loudly instead of silently sizing for the fallback typeface.
  // ONE SIZE FOR ALL FACES. Fitting each string on its own made two PEER statements render at very
  // different sizes (~46px vs ~30px), so the flip read as primary-and-subordinate when both cards are
  // making the same kind of claim. Fit the LONGEST string and use that size everywhere.
  const faceSize = React.useMemo(() => {
    const all = cards.flatMap((c) => [String(c.front ?? ''), String(c.back ?? '')]).filter(Boolean);
    const sizes = all.map((txt) => fitTextOnNLines({
      text: txt, maxLines: 2, maxBoxWidth: cw - 80, fontFamily: dispFace,
      fontWeight: 800, maxFontSize: 64,
    }).fontSize);
    return sizes.length ? Math.min(...sizes) : 64;
  }, [cards, cw, dispFace]);
  const rowW = n * cw + (n - 1) * gap;
  const x0 = (W - rowW) / 2;
  const titleIn = easeOutCubic(seg(t, 0.04, 0.2));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 50% 40%, #12162b, ${BG} 68%)`}}>
      <div style={{position: 'absolute', top: 96, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#aeb6ca',
        font: '700 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.26em', textTransform: 'uppercase'}}>{TITLE}</div>

      {/* WIDTH-AWARE. Fixed 64px broke a Chinese label mid-word inside a card this narrow ("失/败").
          Measure the real string in the real face against the card's inner width; 64 stays the cap so
          short Latin copy is unchanged. Leading 1.02 -> 1.18: at 1.02 two CJK lines collide. */}
      <div style={{position: 'absolute', top: 300, left: 0, right: 0, height: ch, perspective: 1900}}>
        {cards.map((c, i) => {
          const st = 0.18 + i * 0.16;
          const r = clamp01(seg(t, st, st + 0.34));
          const rot = lerp(0, 180, easeInOutCubic(r));
          const rise = easeOutCubic(clamp01(seg(t, 0.06 + i * 0.06, 0.24 + i * 0.06)));
          const sheen = Math.max(0, 1 - Math.abs(r - 0.5) * 6); // flash at the half-turn
          const tone = (PAL ?? [ACC, '#ff7aa8', '#37d4a6', '#f7b955'])[i % 4];
          return (
            <div key={i} style={{position: 'absolute', left: x0 + i * (cw + gap), top: 0, width: cw, height: ch,
              transformStyle: 'preserve-3d', opacity: rise,
              transform: `translateY(${(1 - rise) * 60}px) rotateY(${rot}deg)`}}>
              <Face tone={tone}>
                <div style={{color: DIM, font: '600 22px/1 var(--f-mono, "JetBrains Mono", monospace)',
                  letterSpacing: '0.14em', marginBottom: 22}}>{String(i + 1).padStart(2, '0')}</div>
                <div style={{color: INK, font: `800 ${faceSize}px/1.18 ${dispFace}`,
                  textAlign: 'center', letterSpacing: '-0.02em'}}>{c.front}</div>
              </Face>
              <Face back tone={tone}>
                {/* was a bare ↓ pointing at nothing — undecodable furniture. A short label says what the back IS. */}
                <div style={{color: ON, opacity: .72, font: `700 20px/1 var(--f-mono, "JetBrains Mono", monospace)`,
                  letterSpacing: '.18em', marginBottom: 16}}>{BACKLABEL}</div>
                <div style={{color: ON, font: `800 ${faceSize}px/1.18 ${dispFace}`,
                  textAlign: 'center', letterSpacing: '-0.02em'}}>{c.back}</div>
              </Face>
              {sheen > 0.01 ? <div style={{position: 'absolute', inset: 0, borderRadius: 26, pointerEvents: 'none',
                background: 'linear-gradient(105deg, #fff0 40%, #ffffffcc 50%, #fff0 60%)',
                opacity: sheen * 0.8, transform: 'translateZ(2px)'}} /> : null}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export default CardFlip3D;
