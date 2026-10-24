// SHOT · LightShafts — light arriving: a source behind an occluder (clouds, a canopy, the slats of a blind), and the
// shafts its gaps send through the air toward the lens. Family X (weather / atmosphere).
// @dark-world: shafts are light scattered in air, visible only against shade — under a light DNA the register paints
// the DNA's own dark end, because a shaft of light on a white page is not visible.
//
// WHAT IT ARGUES. "The light gets through" / "a gap is enough" / "it breaks through". The shafts are runtime/volume's
// scattering march (the sky round the source seen through the occluder's gaps, averaged along each line toward it), so
// each shaft IS a gap: hide the caption and the frame still says light breaking through. `breakAt` opens the occluder
// at that point of the beat — the clouds part, the blind tilts open — and the shafts strengthen with it.
//
// THE COLOUR is the film's `color`, else the DNA's accent warmed toward daylight — never a hue picked for the look.
// ITS OWN SOUND (runtime/sound.ts): `breakAt` makes a `swell` as the light comes through. No breakAt, no sound.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, readableOn, mix} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {Volume, isHex, OCCLUDERS, type Rect} from '../runtime/volume';
import {soundT, type SoundDecl} from '../runtime/sound';

export const DURATION = 165; // 5.5s
export const SOUNDS: readonly SoundDecl[] = [
  {kind: 'swell', at: 'breakAt'},
] as const;

const DISPLAY = 'var(--f-display, "Source Serif 4", "Noto Serif SC", Georgia, serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';
/** daylight through a gap, low sun — a display colour, warm white (U) */
const DAYLIGHT = '#ffe2b8';

export const LightShafts: React.FC<{
  title?: string;
  kicker?: string;
  note?: string;
  /** what the light comes through */
  occluder?: (typeof OCCLUDERS)[number];
  /** where the light is, as fractions of the frame (may be above it: a sun over the top edge) */
  source?: [number, number];
  /** the light's colour (#rrggbb) */
  color?: string;
  /** a point of the beat (0..1) at which the occluder opens — the light breaks through, and its swell sounds */
  breakAt?: number;
  seed?: number;
}> = ({title = 'A gap is enough', kicker = '', note = '', occluder = 'clouds', source, color, breakAt, seed = 5} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H), portrait = W < H;
  if (!(OCCLUDERS as readonly string[]).includes(occluder)) {
    throw new Error(`LightShafts: occluder ${JSON.stringify(occluder)} — one of ${OCCLUDERS.join(', ')}`);
  }
  if (color !== undefined && !isHex(color)) throw new Error('LightShafts: color is #rrggbb');
  const ground = darkGround(dna?.bg, '#06070b');
  const ink = readableOn(ground, dna?.fg ?? '#f4efe6', '#f4efe6', '#0b0d12');
  const dim = mix(ink, ground, 0.35);
  const light = color ?? (dna?.accent && isHex(dna.accent) ? mix(DAYLIGHT, dna.accent, 0.25) : DAYLIGHT);
  // the light enters from the top, on the side AWAY from the type (the type column is on the left at 16:9)
  const src: [number, number] = source ?? (portrait ? [0.7, -0.06] : [0.8, -0.1]);

  // ── the type: lower left, clear of the source ──
  const x0 = Math.round(W * (portrait ? 0.08 : 0.07));
  const colW = Math.round(W * (portrait ? 0.84 : 0.44));
  const bot = contentBottom(W, H);
  const titlePx = fitBlockPx(title, colW, U * 0.24, Math.round(U * (portrait ? 0.08 : 0.07)), {usable: 0.95, leading: 1.1,
    min: Math.round(U * 0.036)});
  const kickPx = Math.round(U * 0.026), notePx = Math.round(U * 0.034);
  const lines = title ? wrapLines(title, titlePx, colW * 0.95) : 0;
  const noteLines = note ? wrapLines(note, notePx, colW * 0.95) : 0;
  const blockH = (kicker ? kickPx * 1.8 : 0) + lines * titlePx * 1.1 + (note ? U * 0.02 + noteLines * notePx * 1.35 : 0);
  const top = Math.max(TITLE_Y, Math.round(bot - U * 0.06 - blockH));
  const typeRect: Rect = {x: x0 - U * 0.01, y: top - U * 0.01, w: colW + U * 0.02, h: blockH + U * 0.02};

  // ── the break: the occluder opens round breakAt; without it, it stays as it is ──
  const bT = soundT(SOUNDS, 'swell', {breakAt});
  // shafts NEED the occluder — a clear sky has none — so the break widens the gaps from nearly shut to half open,
  // never to clear (looked at: open past ~0.6 washed the frame to one beige haze)
  const open = bT === null ? 0.42 : 0.16 + 0.34 * easeInOutCubic(clamp01((t - (bT - 0.12)) / 0.16));
  const lit = easeOutCubic(clamp01(seg(t, 0.0, 0.3)));
  const tin = easeOutCubic(clamp01(seg(t, 0.12, 0.34))), nin = easeOutCubic(clamp01(seg(t, 0.3, 0.52)));
  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse 120% 90% at ${src[0] * 100}% 0%, ${mix(ground, light, 0.06)} 0%, ${ground} 60%, ${mix(ground, '#000000', 0.3)} 100%)`}}>
      <Volume spec={{form: 'shafts', source: src, occluder, open, seed, colors: [light, mix(light, '#ff9a5a', 0.35)],
        intensity: 1.2}} fade={lit} keepOut={[typeRect]} res={0.5} where="LightShafts" />
      <div style={{position: 'absolute', left: x0, top, width: colW}}>
        {kicker ? <div style={{color: dna?.accent ?? light, font: `600 ${kickPx}px/1.2 ${MONO}`, letterSpacing: '0.16em',
          textTransform: 'uppercase', marginBottom: kickPx * 0.6, opacity: tin}}>{kicker}</div> : null}
        <div style={{color: ink, font: `700 ${titlePx}px/1.1 ${DISPLAY}`, letterSpacing: '-0.01em', textWrap: 'balance',
          opacity: tin, transform: `translateY(${Math.round((1 - tin) * U * 0.02)}px)`} as React.CSSProperties}>{title}</div>
        {note ? <div style={{color: dim, font: `500 ${notePx}px/1.35 ${BODY}`, marginTop: U * 0.02, textWrap: 'balance',
          opacity: nin} as React.CSSProperties}>{note}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
export default LightShafts;
