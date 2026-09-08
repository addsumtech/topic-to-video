// SHOT · Voice Signal — the film's own narration IS the picture: a spectrum that rises on a stressed syllable
// and falls flat in the gaps between phrases, with a phase label naming what is happening while it speaks.
//
// WHAT IT ARGUES. That something is being SAID — a system listening, thinking, answering. Any register can put
// the words on screen; this one puts the speaking on screen, which is why it belongs on a beat about a voice
// interface, a live agent, a call, a moment of attention.
//
// THE CORRECTION THIS SHOT IS. Its header used to claim it read "the real narration via @remotion/media-utils
// visualizeAudio". It did not: the package was not a dependency and the bars were three sines of the frame
// number. The tell was that it never went quiet — nothing it drew had any relation to whether anyone was
// speaking, so it was a screensaver wearing an instrument's label, and on a beat whose whole subject is speech
// that is the one lie the viewer can catch. It now reads the beat's own mp3 through `runtime/voice`, so the
// gaps between phrases are gaps on screen. Rendered standalone it gets that module's synthetic voice — which
// has gaps too, for exactly this reason.
//
// LOW FREQUENCIES IN THE MIDDLE. An FFT hands back bins low→high, and drawn in that order a voice is a slope
// falling to the right — a decay curve, not a signal. Mirroring the spectrum about the centre is what makes it
// read as a voice: the fundamental is the tall middle, the sibilants are the flutter at both edges.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {Voice} from '../runtime/voice';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 150; // 5s
const ACC_D0 = '#3FE0FF';
const DEFAULT_PHASES = [{at: 0.05, label: 'Listening…'}, {at: 0.34, label: 'Working…'}, {at: 0.74, label: 'Done ✓'}];

export const VoiceSignal: React.FC<{phases?: {at: number; label: string}[]}> = ({phases: PHASES = DEFAULT_PHASES} = {}) => {
  const dna = useDNA();
  const ACC = dna?.accent ?? ACC_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  // The ground follows the film's DNA, so the INK cannot be a literal. Fixed at '#dffaff' this register was
  // legible on the dark ground it was drawn against and invisible the first time a light-paper DNA supplied
  // its own `bg` — the same failure the bgGrad→bg chain exists to prevent, one layer further in. Measured
  // against the solid `bg` rather than the gradient, because a gradient string has no luminance to read.
  const GROUND = dna?.bg ?? '#05080f';
  const INK = readableOn(GROUND, '#dffaff', '#0c141c');
  const DONE_INK = readableOn(GROUND, '#59f0b0', '#0a5c3d');

  const list = (PHASES ?? []).filter((p) => p && String(p.label ?? '').trim());
  if (!list.length) {
    throw new Error(
      'VoiceSignal needs at least one `phases` entry — a {at, label} naming what is being said while the ' +
      'waveform runs. The waveform alone is a level meter; the label is what makes it an account of a ' +
      'conversation.');
  }
  const phase = [...list].reverse().find((p) => t > (p.at ?? 0)) || list[0];

  // ROOM FIRST. Everything here was once a literal — 22px pitch, 380px amplitude, a label at midY+260 in 66px
  // type — which meant 72 bars spanned 1562px and ran off both edges of a 1080-wide portrait frame, and the
  // label sat wherever it landed relative to a subtitle it knew nothing about. Sized from the frame and the
  // reserved caption band instead, the same composition holds at 16:9, 9:16, 1:1 and 4:5.
  const band = H - captionBand(W, H);
  const labelPx = fitTextPx(String(phase.label ?? ''), W * 0.86, Math.round(U * 0.062), {usable: 1.0});
  const labelH = Math.round(labelPx * 1.5);
  const gap = Math.round(U * 0.05);
  const zoneTop = CONTENT_TOP;
  const zoneH = Math.max(Math.round(U * 0.18), band - zoneTop - labelH - gap);
  const midY = Math.round(zoneTop + zoneH / 2);
  const maxH = zoneH * 0.46;

  // The pitch is chosen so the bank fills the frame's width at any aspect; the bar is a fixed fraction of the
  // pitch, so a portrait frame gets fewer, not thinner, bars.
  const pitch = Math.max(6, Math.round(U * 0.0205));
  const N = Math.max(9, Math.floor((W * 0.90) / pitch) | 1);   // odd, so one bar sits exactly on the centre
  const barW = Math.max(2, Math.round(pitch * 0.66));   // a bank, not a picket fence
  const x0 = (W - (N - 1) * pitch) / 2;

  // The shot's own arc still belongs to the shot: the signal is loudest while the phases run and settles to a
  // held tone at the end, so the beat lands rather than simply stopping. Multiplying the live level (rather
  // than replacing it) keeps every gap in the real speech intact.
  const settle = lerp(1, 0.34, easeOutCubic(seg(t, 0.78, 0.95)));
  const done = t > (list[list.length - 1].at ?? 1);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 46%, #0e1826, #05080f 72%)'}}>
      <Voice samples={Math.min(128, N)}>
        {({bars, level}) => (
          <>
            <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
              <defs>
                <linearGradient id="vsbar" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#8af0ff" /><stop offset="1" stopColor={ACC} />
                </linearGradient>
                <filter id="vsglow">
                  <feGaussianBlur stdDeviation={Math.max(2, U * 0.006)} result="b" />
                  <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>
              <g filter="url(#vsglow)">
                {Array.from({length: N}).map((_, i) => {
                  // mirrored about the centre: distance from the middle picks the frequency bucket
                  const d = Math.abs(i - (N - 1) / 2) / Math.max(1, (N - 1) / 2);
                  const v = bars[Math.min(bars.length - 1, Math.round(d * (bars.length - 1)))] ?? 0;
                  // a floor, so the bank never disappears in a silence — the LINE stays, the signal is what
                  // moves. Without it a pause reads as the shot having failed to render.
                  const h = Math.max(U * 0.006, v * settle * maxH);
                  return (
                    <rect key={i} x={x0 + i * pitch - barW / 2} y={midY - h} width={barW} height={h * 2}
                      rx={barW / 2} fill="url(#vsbar)" opacity={0.5 + 0.5 * Math.min(1, h / maxH)} />
                  );
                })}
              </g>
              <line x1={0} y1={midY} x2={W} y2={midY} stroke={ACC} strokeWidth={Math.max(1, U * 0.0014)}
                opacity={0.25} />
            </svg>
            <div style={{position: 'absolute', left: 0, right: 0, top: midY + zoneH / 2 + gap * 0.4,
              textAlign: 'center', whiteSpace: 'pre-wrap',
              font: `800 ${labelPx}px/${leading(String(phase.label), 1.15)} var(--f-display, Inter,system-ui,sans-serif)`,
              // the label brightens with the voice, so the two read as one event rather than as a caption
              // pasted over a graphic
              color: done ? DONE_INK : INK, opacity: 0.72 + 0.28 * level}}>
              {phase.label}
            </div>
          </>
        )}
      </Voice>
    </AbsoluteFill>
  );
};
export default VoiceSignal;
