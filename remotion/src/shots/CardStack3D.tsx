// SHOT · Card Stack 3D — cards spring up one by one and PILE at centre, then fan out into a 3D arc (each
// tilted on Y + rotated on Z), labels facing the camera. Pure CSS 3D (preserve-3d) — no WebGL. The "a deck of
// things → laid out in hand" register (family E). Deterministic (pile + fan = fn of t).

import React from 'react';
import {Icon, type IconName} from '../runtime/icons';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeInOutCubic, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, dnaPalette, surfaceOn, shade} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 155; // ~5.2s

/** Relative luminance of a #rgb/#rrggbb, used only to pick a depth cue that suits the card's own ground. */
function _lum(hex: string): number {
  const h = hex.replace('#', '');
  const f = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6);
  const n = parseInt(f, 16);
  if (!isFinite(n)) return 0;
  return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
}
// D0 — the no-DNA fallbacks. The card SURFACE used to be hardcoded here, which meant a light-ground film
// got navy cards on paper: 94% of the frame's chromatic ink outside the film's palette. A card is a
// container, so its fill, its border and its ink belong to the DNA exactly like any other surface.
const BG = '#090b12';
const CARD_D0 = '#1c2233', CARD2_D0 = '#0f1320', BORD_D0 = '#ffffff28';
const INK_D0 = '#f4f7ff', TITLE_D0 = '#dfe6ff';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1'];

export type StackItem = string | {label: string; icon?: IconName};

export const CardStack3D: React.FC<{items?: StackItem[]; title?: string}> = ({
  items: ITEMS = ['Docs', 'Chat', 'Tasks', 'Code', 'Data', 'Calls'], title: TITLE = 'All of it, in hand'} = {}) => {
  const t = useT();
  const {width: WIDTH} = useVideoConfig();
  const dna = useDNA(); const TONES = dnaPalette(dna, 6) ?? TONES0;
  // The card is a CONTAINER, and the token it is painted from is invisible on its own ground: all eight
  // presets define `surface` within 0.083 of their `bg` in the density model (product: 0.052), so a
  // stack of six cards measured 2.9% ink while spanning 57% of the frame. `surfaceOn` keeps the
  // system's own hue and pushes it off the ground far enough to be a card. Un-themed is untouched.
  const CARD = dna ? surfaceOn(dna.bg, dna.surface) : CARD_D0;
  const BORD = dna?.surfaceBorder ?? BORD_D0;
  // The gradient's SECOND stop was a hardcoded near-black, which pulled the card back to the ground
  // whatever the first stop became: fixing only `CARD` moved this register 2.9% -> 3.0%. Derived from
  // the card itself, the whole face stays a surface. Un-themed keeps the original literal.
  // BOTH stops are pushed clear, not just the first. Deriving only `CARD` and then shading the second
  // stop 16% darker put most of each card's face back under the threshold — 2.9% -> 3.1%. A gradient
  // is a surface only where all of it is one.
  const CARD2 = dna ? surfaceOn(dna.bg, shade(CARD, 0.16)) : CARD2_D0;
  const INK = dna?.fg ?? INK_D0, ONACC = dna?.onAccent ?? '#fff';
  const RAD = dna?.radius ?? 24;
  // On a light surface the original heavy black shadows read as grime, so the depth cue scales with how
  // dark the card actually is rather than being a fixed near-black.
  const deep = !dna || _lum(CARD) < 0.5;
  const SHADOW = deep ? '0 40px 90px #0009, inset 0 1px 0 #ffffff14, 0 0 0 1px #0006'
                      : '0 26px 54px #1f180e26, inset 0 1px 0 #ffffff80';
  const {width: W, height: H} = useVideoConfig();
  const cards = ITEMS.slice(0, 7);
  const n = cards.length;
  const mid = (n - 1) / 2;
  // CARD WIDTH FOLLOWS THE COUNT, because two constraints have to hold at once and a fixed 360 could not
  // satisfy both. The label sits at a card's bottom-left, so the next card must land clear of it: spacing
  // >= 0.92*cw. And the whole fan has to stay inside the frame: (n-1)*spacing + cw <= 0.9*W. Solve them
  // together and the width falls out — cw <= 0.9W / (0.92(n-1)+1). At three cards that is 608, so the 360
  // cap holds; at six it is 308 and at seven 265.
  // Both failures were real: at 300 fixed spacing a 360 card overlapped its neighbour by 60 and the middle
  // label of a three-card stack read 「据汇总」 with its first character behind the front card; widening the
  // spread alone then pushed the outermost of six cards off the frame edge.
  // THE VERTICAL BUDGET, which this register did not have. Its title was pinned at `bottom: 96` in a frame
  // whose caption band is 227px, so the title sat WHOLLY inside the strip the renderer burns the caption
  // over — 79px in, measured on the DOM — and the two pieces of copy drew on top of each other. Moving the
  // title alone would have traded that collision for one with the cards, which were centred in the FRAME
  // rather than in the zone the shot actually owns. So both come off the same budget.
  const base = Math.min(WIDTH, H);
  const titleSize = Math.round(base * 0.0574);              // 62 @1080 — a FRACTION, so portrait cannot blow it up
  const titleH = Math.round(titleSize * 1.15);
  const gap = Math.round(base * 0.028);
  const zoneBottom = contentBottom(WIDTH, H);
  const titleTop = zoneBottom - titleH;
  const fanBottom = titleTop - gap;                          // the fan's floor: clear of its own title
  const fanH = Math.max(120, fanBottom - CONTENT_TOP);
  // A FAN REACHES BELOW ITS OWN BOX, and centring the box is what put six card labels back in the caption
  // band after the title moved out of it. Two terms, both already in this component's own geometry: the arc
  // dip the end cards take (`ty`), and the swing of a card rotated about its BOTTOM CENTRE. Computed rather
  // than guessed, so a three-card stack and a seven-card stack each get the room they actually need.
  const spreadDrop = mid * 26;
  const fanAngle = (mid * 13 * Math.PI) / 180;
  // and the HEIGHT constraint, which was missing: sized on width alone, a six-card fan is 411px tall plus
  // ~148px of reach and simply overran a shorter zone (every portrait aspect, and 16:9 once the title
  // claimed its own room). Solving ch + spreadDrop + (cw/2)sin(angle) <= fanH for cw:
  const cwByHeight = (fanH - spreadDrop) / (480 / 360 + 0.5 * Math.sin(fanAngle));
  const cw = Math.round(Math.min(360, (WIDTH * 0.9) / (0.92 * Math.max(1, n - 1) + 1), cwByHeight));
  const ch = Math.round(cw * (480 / 360));
  const fanReach = spreadDrop + (cw / 2) * Math.sin(fanAngle);
  const fan = easeInOutCubic(seg(t, 0.58, 0.92));
  const titleIn = easeOutCubic(seg(t, 0.66, 0.86));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 50% 38%, #12162b, ${BG} 72%)`, overflow: 'hidden'}}>
      {/* HEIGHT, not `bottom`. Remotion's AbsoluteFill sets `height: '100%'` as well as the four insets, so
          a passed `bottom` is simply ignored — the box stayed 1080 tall, `top` pushed it DOWN, and the fan
          sank further into the caption band than before the fix. The measurement was identical to the
          pixel: 98/60/18/44px, which is what a change having no effect looks like. */}
      <AbsoluteFill style={{top: CONTENT_TOP, height: Math.max(120, fanBottom - fanReach - CONTENT_TOP),
        display: 'flex', alignItems: 'center', justifyContent: 'center', perspective: 1800}}>
        <div style={{position: 'relative', width: cw, height: ch, transformStyle: 'preserve-3d',
          transform: `translateY(${lerp(40, -30, fan)}px)`}}>
          {cards.map((raw, i) => {
            // A card may arrive as a bare string (every film before icons existed) or as {label, icon}.
            const label = typeof raw === 'string' ? raw : raw?.label ?? '';
            const icon = typeof raw === 'string' ? undefined : raw?.icon;
            const st = 0.06 + i * 0.07;
            const rise = easeOutBack(clamp01(seg(t, st, st + 0.24)));    // spring up into the pile
            const pileY = -i * 10, pileR = (hash01(i * 5) - 0.5) * 5;    // slight messy stack
            const ang = (i - mid) * 13;                                  // fan spread angle
            // SPACING MUST CLEAR THE CARD, not a fixed 300. A card is 360 wide, so at 300 every neighbour
            // overlapped its predecessor by 60px — and the label sits at the card's bottom-left, exactly
            // where the next card lands. With three cards the middle label read 「据汇总」 with its first
            // character behind the front card. It was as wrong with the ordinal chips, just harder to
            // notice. Widen with the count so a short stack fans as clearly as a full one.
            const tx = fan * (i - mid) * (cw * 0.92);
            const ty = lerp(pileY, Math.abs(i - mid) * 26, fan);         // arc dip at the ends
            const rz = lerp(pileR, ang, fan);
            const ry = fan * (i - mid) * 7;
            const tone = TONES[i % TONES.length];
            return (
              <div key={i} style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, opacity: clamp01(rise * 1.5),
                transformStyle: 'preserve-3d', transformOrigin: 'bottom center',
                transform: `translate3d(${tx}px, ${lerp(120, 0, rise) + ty}px, ${i * 2}px) rotateZ(${rz}deg) rotateY(${ry}deg)`,
                borderRadius: RAD, background: `linear-gradient(160deg, ${CARD}, ${CARD2}), linear-gradient(160deg, ${tone}1c, #0000)`,
                border: `1px solid ${BORD}`, boxShadow: SHADOW,
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 34}}>
                {/* the second stop used to be a fixed blue, which put an off-system colour on every card
                    however the film was themed; it now runs to the DNA's own second accent. */}
                <div style={{width: 60, height: 60, borderRadius: Math.min(16, RAD * 8),
                  background: `linear-gradient(150deg, ${tone}, ${dna?.accent2 ?? '#2b3ac6'})`,
                  boxShadow: `0 0 26px ${tone}66`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: ONACC, font: `800 30px/1 var(--f-body, Inter, system-ui, sans-serif)`}}>
                  {/* AN ICON WHERE THE CARD NAMES A THING. The chip used to carry the card's INDEX — a
                      coloured square with a number on it, which tells a viewer nothing about the card it
                      sits on and looks identical on every film. The ordinal survives only when no icon is
                      given, so nothing authored before this moves. */}
                  {icon ? <Icon name={icon} size={32} ink={ONACC} weight={2.1} /> : i + 1}
                </div>
                <div style={{color: INK, font: `800 46px/1 var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
                  textShadow: deep ? '0 2px 10px #000' : 'none'}}>{label}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <div style={{position: 'absolute', top: titleTop, height: titleH, left: 0, right: 0, textAlign: 'center',
        opacity: titleIn, display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
        transform: `translateY(${(1 - titleIn) * 16}px)`, color: dna?.fg ?? TITLE_D0,
        font: `800 ${titleSize}px/1 var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
        textShadow: deep ? '0 8px 30px #000' : 'none'}}>{TITLE}</div>
    </AbsoluteFill>
  );
};
export default CardStack3D;
