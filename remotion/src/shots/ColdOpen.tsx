// SHOT · Cold Open — the film opens on ITSELF: three of its own later beats flash past in short hard cuts, each
// pushing in a little, then a beat of dark and the title. A trailer's bumper: it promises what is coming with the
// film's own pictures before it says what it is. (Peer: video-shotcraft's trailer-grammar-moves — "three 9-frame
// rapid cuts, a beat of black silence, then the opening title card" — reviewed 2026-11-02.)
//
// The pictures are the film's: `beats` names which of its beats to show (1-based), and Film.tsx hands each one down
// (runtime/teaser) drawn by its own register on its own ground, frozen at its settled frame. Standalone — a still, a
// library sweep, no film around it — each flash is a neutral stand-in panel instead.
//
// No flash frames between the cuts: three white frames inside a second is the photosensitivity pattern (ITU-R
// BT.1702: harmful past three flashes in one second); the cuts themselves are the punctuation.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp01, easeOutCubic, lerp} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useGlide} from '../runtime/glide';
import {useTeaser} from '../runtime/teaser';

export const DURATION = 120; // 4 s

/** frames each flash holds — the peer's 9 — and the dark after them */
export const FLASH_F = 9;
export const DARK_F = 12;
const LEAD_F = 12;                 // the seam's held edge: the first flash starts after it

export const ColdOpen: React.FC<{beats?: number[]; title?: string; kicker?: string; place?: 'centre' | 'lower-left'}> = ({
  beats = [2, 3, 4], title = 'Demo title', kicker = '', place = 'centre'} = {}) => {
  // `place`: the title card centred, or set lower-left over the dark like a film's opening credit — a composition the
  // film chooses against its other beats (text_safe_qa names a film whose titles all sit in one place)
  const low = place === 'lower-left';
  if (!Array.isArray(beats) || beats.length < 2 || beats.length > 4) {
    throw new Error(`ColdOpen needs 2-4 \`beats\` (the film's own beats to flash), got ${JSON.stringify(beats)}`);
  }
  if (!String(title ?? '').trim()) throw new Error('ColdOpen needs a `title` — the card the flashes lead to');
  const dna = useDNA();
  const teaser = useTeaser();
  const frame = useCurrentFrame();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const BG = dna?.bg ?? '#07080b', FG = dna?.fg ?? '#f3f4f7', DIM = dna?.dim ?? '#8a909c', ACC = dna?.accent ?? '#7cc4ff';
  const DISPLAY = 'var(--f-display, Inter, system-ui, sans-serif)';
  const MONO = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", monospace)';

  const flashEnd = LEAD_F + beats.length * FLASH_F;
  const k = Math.floor((frame - LEAD_F) / FLASH_F);
  const inFlash = frame >= LEAD_F && k < beats.length;
  const titleStart = flashEnd + DARK_F;
  const darkGround = mix(BG, '#000000', 0.6);

  if (inFlash) {
    const local = (frame - LEAD_F - k * FLASH_F) / FLASH_F;
    const push = lerp(1.0, 1.07, easeOutCubic(clamp01(local)));    // each flash leans in, a camera moving through
    const pic = teaser ? teaser.render(beats[k]) : null;
    return (
      <AbsoluteFill style={{background: darkGround, overflow: 'hidden'}}>
        <AbsoluteFill style={{transform: glide(`scale(${push})`, true), transformOrigin: '50% 45%'}}>
          {pic ?? (
            <AbsoluteFill style={{background: `linear-gradient(${120 + k * 70}deg, ${mix(BG, ACC, 0.25 + 0.15 * k)}, ${BG})`}} />
          )}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  // before the first flash (the seam's hold) and through the dark: the film's ground, darkened
  const on = easeOutCubic(clamp01((frame - titleStart) / 14));
  const top = Math.max(CONTENT_TOP, Math.round(U * 0.08)), bottom = contentBottom(W, H);
  const titlePx = fitTextPx(title, W * 0.8, Math.round(U * 0.12), {usable: 0.95});
  const kickPx = Math.max(Math.round(U * 0.028), Math.round(titlePx * 0.22));   // the label floor (30 px at 1080)
  return (
    <AbsoluteFill style={{background: frame < titleStart ? darkGround : `radial-gradient(90% 80% at 50% 45%, ${mix(BG, ACC, 0.08 * on)}, ${darkGround} 75%)`}}>
      {frame >= titleStart ? (
        <div style={{position: 'absolute', left: 0, right: 0, top, height: bottom - top, display: 'flex', flexDirection: 'column',
          alignItems: low ? 'flex-start' : 'center', justifyContent: low ? 'flex-end' : 'center', opacity: on,
          paddingLeft: low ? Math.round(W * 0.07) : 0, paddingBottom: low ? Math.round(U * 0.04) : 0, boxSizing: 'border-box',
          transform: glide(`translateY(${(1 - on) * U * 0.02}px)`, true)}}>
          {kicker ? <div style={{color: ACC, font: `600 ${kickPx}px/1 ${MONO}`, letterSpacing: dna?.labelSpacing ?? '0.16em',
            textTransform: 'uppercase', marginBottom: Math.round(U * 0.025)}}>{kicker}</div> : null}
          <div style={{color: FG, font: `800 ${titlePx}px/${leading(title, 1.05)} ${DISPLAY}`, textAlign: low ? 'left' : 'center',
            letterSpacing: '-0.02em', textWrap: 'balance', maxWidth: W * 0.84}}>{title}</div>
          <div style={{width: Math.round(U * 0.08 * on), height: Math.max(2, Math.round(U * 0.004)),
            background: mix(DIM, ACC, 0.6), marginTop: Math.round(U * 0.03)}} />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ColdOpen;
