// SHOT · Analog Tape — the 2026 "authenticity / analog revival" register: a warm VHS/CRT treatment — tungsten
// gradient, scanlines, RGB chromatic split, a rolling tracking band, grain, barrel vignette, and a retro OSD
// (● REC, timestamp, ▶ PLAY). Nostalgic, textured, human — the anti-slick shot. Deterministic (jitter = fn t).
//
// THE DATE IN THE CORNER IS THE FILM'S. The OSD printed `SP · AUG 12 2026` as a literal — a recording date,
// which is a claim about WHEN something was recorded, stamped onto every film that reached for the tape look
// whatever its subject or era. A film about a 1994 home video showed a 2026 date and nothing could change
// it. It is `date` now, defaulting to the words it replaced, so the original film renders identically and
// the demo-copy gate lists it when a film omits it; '' leaves just the tape-speed mark `SP`, which, like REC
// and ▶ PLAY, is the deck describing itself.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, clamp01, seg, lerp} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {bottomInset, fitTextPx} from '../runtime/layout';

export const DURATION = 160; // ~5.3s
// @dark-world: a CRT tube shot off the glass. The wordmark is three copies composited with
// `mixBlendMode: 'screen'` — pure ADDITIVE light, which on a white ground is arithmetically a no-op — and the
// tracking band, the scanlines and the barrel vignette are all shaping a lit phosphor screen rather than
// colouring a surface. On a warm-white film the register measured a median 1.26:1 with 100% of its marks
// under 3:1 (scripts/ink_contrast_qa.py): the red and cyan split copies vanished outright and the frame was
// flat grey with an OSD outline on it. Nothing here can be inverted, because what would invert is the beam.
const OWN_NIGHT = 'radial-gradient(120% 120% at 50% 42%, #4a2f18 0%, #241408 46%, #0b0704 100%)';
const OWN_NIGHT_FLAT = '#241408';                 // the same tube-dark as one colour, for darkGround to judge

// The running timecode below is the TAPE DECK DEPICTING ITSELF — a counter on a transport counts transport
// time, the way a REC light is lit. It is not a measurement of any topic, so it is declared rather than
// left to look like a fabricated figure.
export const INTRINSIC_READOUT = true;

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'REC',
  '▶ PLAY',
  'SP',
];

export const AnalogTape: React.FC<{title?: string; tagline?: string; date?: string}> = ({title: TITLE = 'WorkBuddy',
  tagline: TAGLINE = 'ON YOUR MACHINE', date = 'AUG 12 2026'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const jit = Math.sin(frame * 0.9) * 1.6 + Math.sin(frame * 2.3) * 0.8; // tape wobble (px)
  const split = 3 + Math.abs(Math.sin(frame * 0.14)) * 4;                // RGB split amount
  const trackY = ((t * 1.4) % 1.25 - 0.12) * H;                         // rolling tracking band
  const recOn = frame % 40 < 26;                                         // blinking REC dot
  const inT = clamp01(seg(t, 0.06, 0.4));
  // THE WORDMARK IS FITTED TO THE FRAME. 168px is a size chosen for the fallback named in the shorthand
  // below — Antonio, a very condensed face — and the face that actually renders is the DNA's display stack.
  // Under `cinematic` that is Bodoni Moda, and the same nine letters were cut off on BOTH sides, about 85px
  // each, on all three of the RGB-split copies. The split itself is part of the width: the copies ride
  // +-`split` px, so the fit is given the frame minus the widest excursion it can make.
  const SPLIT_MAX = 7;
  // the OSD stamp: 60px margins, and ~260px held for the REC light and its word at the left
  const stampPx = Math.min(40, fitTextPx(`SP · ${date}`, W - 120 - 260, 40, {usable: 1, adv: 0.62, cjk: 1.24}));
  const titlePx = Math.min(168, fitTextPx(TITLE, W * 0.92 - SPLIT_MAX * 2, 168, {usable: 1, track: 0.02}));

  const Title: React.FC<{dx: number; color: string; blend?: string}> = ({dx, color, blend}) => (
    <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', transform: `translate(${dx + jit}px, ${jit * 0.4}px)`, mixBlendMode: (blend as any) || 'normal'}}>
      <div style={{color, font: `800 ${titlePx}px/${leading(TITLE, 0.95)} var(--f-display, "Antonio", "Oswald", Impact, sans-serif)`, letterSpacing: '0.02em',
        textTransform: 'uppercase', opacity: inT}}>{TITLE}</div>
      <div style={{color, font: '600 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.34em', marginTop: 22,
        opacity: clamp01(seg(t, 0.4, 0.7))}}>{TAGLINE}</div>
    </div>
  );

  // the film's ground while the film's ground is dark (all eight presets), this register's own tube-dark when
  // it is not. The branch is on what `darkGround` RETURNED, so a dark film grounded on exactly this colour
  // still gets its own `bgGrad` treatment rather than ours.
  const night = darkGround(dna?.bg, OWN_NIGHT_FLAT);
  const ground = night === dna?.bg ? (dna?.bgGrad ?? night) : OWN_NIGHT;

  return (
    <AbsoluteFill style={{background: ground, overflow: 'hidden'}}>
      {/* content with RGB chromatic split (three offset copies) */}
      <Title dx={-split} color="#ff3b3b" blend="screen" />
      <Title dx={split} color="#38f0ff" blend="screen" />
      <Title dx={0} color="#fff3df" />

      {/* scanlines */}
      <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.5,
        background: 'repeating-linear-gradient(#0000 0px, #0000 2px, #00000066 3px, #00000066 4px)'}} />

      {/* rolling tracking band */}
      <div style={{position: 'absolute', left: 0, right: 0, top: trackY, height: 60, pointerEvents: 'none',
        background: 'linear-gradient(#0000, #ffffff22 40%, #ffffff33 50%, #0000)', filter: 'blur(1px)'}} />

      {/* grain */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, mixBlendMode: 'overlay', opacity: 0.5}}>
        <filter id="tg"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" seed={frame % 8} /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width={W} height={H} filter="url(#tg)" />
      </svg>

      {/* OSD — retro on-screen display */}
      <div style={{position: 'absolute', left: 60, top: 48, display: 'flex', alignItems: 'center', gap: 16,
        font: '700 40px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0', letterSpacing: '0.06em'}}>
        <span style={{width: 22, height: 22, borderRadius: 11, background: '#ff2b2b', opacity: recOn ? 1 : 0.15}} />REC
      </div>
      {/* one line, as the &nbsp;s in the old literal kept it — and fitted to the room right of REC, so a long
          date steps down in size instead of running into the REC light */}
      <div style={{position: 'absolute', right: 60, top: 48, font: `700 ${stampPx}px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)`, color: '#eafff0', whiteSpace: 'pre'}}>SP{date ? ` · ${date}` : ''}</div>
      <div style={{position: 'absolute', left: 60, bottom: bottomInset(W, H, 48), font: '700 44px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0', letterSpacing: '0.1em'}}>▶ PLAY</div>
      <div style={{position: 'absolute', right: 60, bottom: bottomInset(W, H, 48), font: '700 40px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0'}}>{String(Math.floor(t * 12)).padStart(2, '0')}:{String(Math.floor((t * 12 * 60) % 60)).padStart(2, '0')}</div>

      {/* CRT barrel vignette */}
      <AbsoluteFill style={{background: 'radial-gradient(110% 100% at 50% 50%, #0000 56%, #000000cc 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default AnalogTape;
