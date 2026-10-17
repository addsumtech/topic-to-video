// SHOT · Card Flip 3D — a row of cards standing in perspective FLIP 180° on their Y axis (staggered), a
// light sheen sweeping the seam at the half-turn, revealing the payoff on the back. Pure CSS 3D
// (preserve-3d + backface-visibility) — no WebGL. The "question → answer, turned over" register. Deterministic.
//
// EVERY PAIR IS TURNED, OR THE REGISTER SAYS IT CANNOT. It used to take `items.slice(0, 4)`, so a film that
// handed it five before/after pairs shipped four cards and the fifth pair — often the one the narration was
// building to — never appeared, with nothing anywhere saying so. Four is a real limit, not a taste: the flips
// are staggered 0.16 of the clip apart and each takes 0.34, so the fourth card finishes turning on the last
// frame and a fifth would still be mid-turn, its back (the payoff) never shown. So 1-4 pairs draw, and a fifth
// THROWS naming the maximum. A pair missing either face throws too: a card with no back turns over onto
// nothing, and one with no front has nothing to turn from — both read as finished cards that say half a claim.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, dnaPalette, mix, shade, contrastOf, readableOn} from '../runtime/dna';
import {onLight} from '../runtime/light';
import {useGlide} from '../runtime/glide';
import {fitTextOnNLines} from '@remotion/layout-utils';

export const DURATION = 150; // 5s
const BG = '#0a0c13', ACC0 = '#6ea8ff';
// The kicker over the row. A literal near-white-blue: `ink_contrast_qa` on a light film reported 14.7% of
// the marks under 3:1 and a hole of 0.29% of the frame, and the hole was this whole line — the beat's own
// title, white-on-warm-paper. The same literal is on record in `readableOnAll`'s header, where it measured
// 1.07:1 on VersusSplit's light half.
const TITLE_D0 = '#aeb6ca';
// The cards' drop shadow, authored against a void: on a near-black ground `#0008` at 90px is the only thing
// separating a card from the frame, and on paper three of them pool into one grey wash across the lower
// half. On a light film the shadow is the PAPER's own shade, close in and half as far.
const SHADOW_D0 = '0 40px 90px #0008, inset 0 1px 0 #ffffff12';

type Item = {front: string; back: string};

export const MAX_FLIP_CARDS = 4;

// Both faces take their fill from the DNA. The back used to blend the tone into a hardcoded #2c3ac0 and
// the front into a hardcoded near-black, so on a themed film the cards arrived in their own palette —
// teal and pink cards on a `data`-DNA deck. `?? <original>` keeps an un-themed render byte-identical.
const Face: React.FC<{children: React.ReactNode; back?: boolean; tone: string;
  faceBg?: string | null; faceEdge?: string | null; shadow?: string}> = ({children, back, tone, faceBg, faceEdge,
  shadow = SHADOW_D0}) => (
  <div style={{position: 'absolute', inset: 0, backfaceVisibility: 'hidden',
    transform: back ? 'rotateY(180deg)' : undefined, borderRadius: 26,
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40,
    background: back
      ? `linear-gradient(155deg, ${tone}, ${shade(tone, 0.45)})`
      : (faceBg ?? 'linear-gradient(155deg, #171a28, #0f1220)'),
    border: `1px solid ${back ? 'transparent' : (faceEdge ?? '#262a42')}`,
    boxShadow: shadow}}>{children}</div>
);

// `numbered: false` drops the 01/02/03 on each face — for items with no order, where a number would claim one
export const CardFlip3D: React.FC<{items?: Item[]; title?: string; backLabel?: string; numbered?: boolean}> = ({
  items: ITEMS = [{front: 'Manual', back: 'Automated'}, {front: 'Hours', back: 'Seconds'}, {front: 'Guesswork', back: 'Grounded'}],
  title: TITLE = 'What changes', backLabel: BACKLABEL = '实际', numbered = true
  } = {}) => {
  const t = useT();
  const glide = useGlide();
  const dna = useDNA(); const ACC = dna?.accent ?? ACC0;
  // Four film-coherent hues instead of three hardcoded ones (pink/teal/amber), which is why a themed
  // deck's cards used to arrive in a palette that was not the film's. null DNA -> null -> the originals.
  const PAL = dnaPalette(dna, 4);
  // …and these two were COMPUTED AND NEVER PASSED: `<Face>` was rendered without `faceBg`/`faceEdge`, so
  // the front kept its literal near-black whatever the film said. It read on night and nowhere else — on a
  // light film the front word is `dna.fg`, which is near-black, printed on a near-black card. Wired.
  const FACE_BG = dna ? `linear-gradient(155deg, ${dna.surface}, ${dna.bg})` : null;
  const FACE_EDGE = dna?.surfaceBorder ?? null;
  const INK = dna?.fg ?? '#eef2ff', DIM = dna?.dim ?? '#8b93a8', ON = dna?.onAccent ?? '#fff';
  // THE BACK OF A CARD IS FLOODED WITH ITS TONE, AND THE PAYOFF IS WRITTEN ON THAT FLOOD. `onAccent` is the
  // DNA's ink for its FIRST accent, and `dnaPalette`'s second entry is the raw `accent2` — a colour chosen
  // for chroma against the first accent, not for value against anything. On a light-stock film whose second
  // accent is a teal, card 2's back measured `onAccent` at **1.69:1** while card 1's measured 8.93:1: the
  // whole payoff of one flip in two was invisible, on a register whose entire form is the payoff. Ask the
  // tone. `onAccent` wins wherever it already clears the floor — which is every dark preset, so nothing that
  // renders today moves — and the film's own ink takes over where it does not.
  const backInk = (tone: string) =>
    contrastOf(ON, tone) >= 4.5 ? ON : readableOn(tone, INK, ON, '#ffffff', '#0a0d14');
  // The kicker is on the film's GROUND, not on a card, so it is the film's ink at its metadata tier.
  const TITLE_INK = dna ? mix(dna.fg, dna.dim, 0.4) : TITLE_D0;
  // …and the cards' shadow is scaled to the ground it falls on (see SHADOW_D0). The inset highlight goes
  // with it: a 7%-white top edge is a lit rim on a dark card and nothing at all on a pale one.
  const CARD_SHADOW = dna && onLight(dna)
    ? `0 18px 34px ${shade(dna.bg, 0.34)}55` : SHADOW_D0;
  const {width: W} = useVideoConfig();
  const dispFace = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';
  // Every pair the film gave, each once — see the header for why four is the ceiling and why it throws.
  if (!Array.isArray(ITEMS) || ITEMS.length < 1 || ITEMS.length > MAX_FLIP_CARDS) {
    throw new Error(
      `CardFlip3D turns 1-${MAX_FLIP_CARDS} cards (got ${Array.isArray(ITEMS) ? ITEMS.length : typeof ITEMS}). ` +
      `The flips are staggered so the fourth lands on the last frame; a fifth would never show its back. ` +
      `Split the pairs across two beats, or use a list/table register for more.`);
  }
  const cards = ITEMS.map((c, i) => {
    const front = String(c?.front ?? '').trim(), back = String(c?.back ?? '').trim();
    if (!front || !back) {
      throw new Error(
        `CardFlip3D: card ${i + 1} needs both \`front\` and \`back\` (got front=${JSON.stringify(c?.front ?? null)}, ` +
        `back=${JSON.stringify(c?.back ?? null)}). The card IS the turn from one to the other.`);
    }
    return {front, back};
  });
  const n = cards.length;
  const gap = 56;
  // the card yields to the frame: three fixed 440s + gaps are 1432px, wider than a portrait frame
  const cw = Math.min(440, Math.floor((W * 0.94 - (cards.length - 1) * gap) / Math.max(1, cards.length)));
  const ch = Math.round(cw * (430 / 440));   // ch 560 -> 430: a single short line left ~70% of the card void
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
        transform: glide(`translateY(${(1 - titleIn) * 14}px)`, titleIn !== 1), color: TITLE_INK,
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
              <Face tone={tone} shadow={CARD_SHADOW} faceBg={FACE_BG} faceEdge={FACE_EDGE}>
                {numbered ? <div style={{color: DIM, font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)',
                  letterSpacing: '0.14em', marginBottom: 24}}>{String(i + 1).padStart(2, '0')}</div> : null}
                <div style={{color: INK, font: `800 ${faceSize}px/1.18 ${dispFace}`,
                  textAlign: 'center', letterSpacing: '-0.02em'}}>{c.front}</div>
              </Face>
              <Face back tone={tone} shadow={CARD_SHADOW}>
                {/* was a bare ↓ pointing at nothing — undecodable furniture. A short label says what the back IS. */}
                <div style={{color: backInk(tone), opacity: .72, font: `700 30px/${leading(BACKLABEL, 1)} var(--f-mono, "JetBrains Mono", monospace)`,
                  letterSpacing: '.18em', marginBottom: 20, textAlign: 'center', textWrap: 'balance'}}>{BACKLABEL}</div>
                <div style={{color: backInk(tone), font: `800 ${faceSize}px/1.18 ${dispFace}`,
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
