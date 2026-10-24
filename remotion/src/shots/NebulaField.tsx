// SHOT · NebulaField — a glowing cloud of gas in deep space: emission stirred into filaments, turning from hydrogen red
// to oxygen teal toward the hot star that lights it, with dust in front of it in dark lanes. Family V (cosmic / space).
// @dark-world: an emission nebula is light on the black of space — under a light DNA the register paints the DNA's own
// dark end; a nebula on a cream page is not a picture of one.
//
// WHAT IT ARGUES. "Where stars are born" / "the gas glows because a star lights it" / "vast, and slow". The cloud is
// runtime/volume's warped emission field, not a gradient: hide the caption and the frame still says nebula; the slow
// push and the gas's own slow evolution say scale and time. A `star` places the ionising star the colour is graded
// from — the gas is teal near it, red away from it, which is the physics of an H II region, so a film that names the
// star gets that relation drawn, not decorated.
//
// THE COLOURS are the film's `colors` ([outer, inner]) or the declared emission lines (volumeCore.NEBULA_EMISSION:
// H-alpha 656.3 nm, [O III] 500.7 nm, display approximations). No ITS OWN SOUND: a nebula is silent and slow.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, readableOn, mix} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {Volume, isHex, NEBULA_EMISSION, type Rect} from '../runtime/volume';

export const DURATION = 180; // 6s

const DISPLAY = 'var(--f-display, "Source Serif 4", "Noto Serif SC", Georgia, serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

export const NebulaField: React.FC<{
  title?: string;
  kicker?: string;
  note?: string;
  /** [outer emission, inner emission] #rrggbb — the film's, else H-alpha and [O III] */
  colors?: string[];
  /** where the ionising star sits, as fractions of the frame */
  star?: [number, number];
  seed?: number;
}> = ({title = 'Where stars are born', kicker = '', note = '', colors, star, seed = 11} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H), portrait = W < H;
  if (colors !== undefined && !(Array.isArray(colors) && colors.length >= 1 && colors.length <= 2 && colors.every(isHex))) {
    throw new Error('NebulaField: colors is [outer, inner] — one or two #rrggbb');
  }
  const ground = darkGround(dna?.bg, '#020309');
  const ink = readableOn(ground, dna?.fg ?? '#f1f3f8', '#f1f3f8', '#0b0d12');
  const dim = mix(ink, ground, 0.35);
  const c = colors ?? [NEBULA_EMISSION.halpha, NEBULA_EMISSION.oiii];
  const st: [number, number] = star ?? (portrait ? [0.6, 0.38] : [0.66, 0.42]);

  // ── the type: top left, the cloud's quiet side ──
  const x0 = Math.round(W * (portrait ? 0.08 : 0.07));
  const colW = Math.round(W * (portrait ? 0.84 : 0.42));
  const titlePx = fitBlockPx(title, colW, U * 0.22, Math.round(U * (portrait ? 0.08 : 0.066)), {usable: 0.95, leading: 1.1,
    min: Math.round(U * 0.036)});
  const kickPx = Math.round(U * 0.026), notePx = Math.round(U * 0.032);
  const lines = title ? wrapLines(title, titlePx, colW * 0.95) : 0;
  const noteLines = note ? wrapLines(note, notePx, colW * 0.95) : 0;
  const top = TITLE_Y;
  const blockH = (kicker ? kickPx * 1.8 : 0) + lines * titlePx * 1.1 + (note ? U * 0.02 + noteLines * notePx * 1.35 : 0);
  if (top + blockH > contentBottom(W, H)) throw new Error('NebulaField: the title and note do not fit above the caption band');
  const typeRect: Rect = {x: x0 - U * 0.01, y: top - U * 0.01, w: colW + U * 0.02, h: blockH + U * 0.02};

  // ── a slow push: the scale of the thing, a pure function of the beat ──
  const push = 1 + 0.06 * t;
  const sx = st[0] * W, sy = st[1] * H;
  const lit = easeOutCubic(clamp01(seg(t, 0.0, 0.3)));
  const tin = easeOutCubic(clamp01(seg(t, 0.1, 0.32))), nin = easeOutCubic(clamp01(seg(t, 0.28, 0.5)));
  return (
    <AbsoluteFill style={{background: ground, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${push.toFixed(5)})`,
        transformOrigin: `${st[0] * 100}% ${st[1] * 100}%`}}>
        {/* the type's keep-out, carried into the PUSHED canvas's own coordinates (the push scales about the star), so
            the gas stays off the words on every frame of the push */}
        <Volume spec={{form: 'nebula', colors: [c[0], c[1] ?? c[0], mix(c[0], '#000000', 0.8)], star: st, seed,
          intensity: 1.1, speed: 1.6}} fade={lit} res={0.6} where="NebulaField"
          keepOut={[{x: sx + (typeRect.x - sx) / push, y: sy + (typeRect.y - sy) / push, w: typeRect.w / push,
            h: typeRect.h / push}]} />
      </div>
      <div style={{position: 'absolute', left: x0, top, width: colW}}>
        {kicker ? <div style={{color: dna?.accent ?? c[1] ?? c[0], font: `600 ${kickPx}px/1.2 ${MONO}`, letterSpacing: '0.16em',
          textTransform: 'uppercase', marginBottom: kickPx * 0.6, opacity: tin}}>{kicker}</div> : null}
        <div style={{color: ink, font: `700 ${titlePx}px/1.1 ${DISPLAY}`, letterSpacing: '-0.01em', textWrap: 'balance',
          opacity: tin, transform: `translateY(${Math.round((1 - tin) * U * 0.02)}px)`} as React.CSSProperties}>{title}</div>
        {note ? <div style={{color: dim, font: `500 ${notePx}px/1.35 ${BODY}`, marginTop: U * 0.02, textWrap: 'balance',
          opacity: nin} as React.CSSProperties}>{note}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
export default NebulaField;
