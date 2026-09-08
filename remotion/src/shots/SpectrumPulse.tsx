// SHOT · Spectrum Pulse — a circular spectrum around a wordmark: the beat's own voice radiating from the
// centre, the ring breathing with it.
//
// WHAT IT ARGUES. That something is ALIVE and playing — a launch, a brand moment, a product that sounds like
// something. The circle is the point: a bar bank along the bottom reads as an instrument, a ring reads as an
// object, and a wordmark inside a ring that is moving is a logo with a pulse.
//
// IT NOW LISTENS. The spectrum used to be three sines of `t` and a kick every half second, which the header at
// least admitted — "a visual style, not tied to the real VO". Honest, and still a loss: on a beat where the
// narration is saying the brand's name, a ring that dances to an imaginary metronome is out of time with the
// only sound in the room. It reads `runtime/voice` now, so it is in time by construction, and a standalone
// render gets that module's synthetic voice — which has the syllable rhythm the hand-rolled kick was imitating.
//
// LOW FREQUENCIES AT TOP AND BOTTOM. The bucket is picked by distance from the vertical axis, so the ring is
// symmetric left-to-right. Walking the spectrum once around the circle instead puts the loud end and the quiet
// end next to each other, and the ring reads as a comma rather than as a rig.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {Voice} from '../runtime/voice';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#080611';

export const SpectrumPulse: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'On beat', tagline: TAG = 'it moves with you', accent: ACC = '#ff3b8b', accent2: ACC2 = '#41b8ff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // the ACCENTS follow the film's system, the TYPE does not: this register paints its own dark ground, so a
  // light film's `fg`/`dim` tokens would be white-on-white here. Ink stays fixed to the ground the shot draws.
  const A1 = dna?.accent ?? ACC, A2 = dna?.accent2 ?? ACC2;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  // ROOM FIRST — the ring was a 180px radius with 240px bars and a 112px wordmark, all literals, so at 9:16 it
  // spanned 1200px of a 1080-wide frame and the spectrum ran off both sides. Sized from the content zone, the
  // same rig fits every aspect and never reaches into the caption band.
  const band = H - captionBand(W, H);
  const zoneH = Math.max(U * 0.3, band - CONTENT_TOP);
  const cx = W / 2, cy = CONTENT_TOP + zoneH / 2;
  // `ring` is the rig's OUTER radius and nothing may exceed it: R0 + LEN is exactly ring, and the bar length
  // below is clamped rather than multiplied, so a loud syllable cannot push the spectrum through the caption
  // band. Written as a multiplier the beat term reached 1.22x — a 22% overshoot of the zone the shot had just
  // measured, which is the kind of overflow that only shows up on the one frame nobody renders.
  const ring = Math.min(W * 0.47, zoneH * 0.5);
  const R0 = ring * 0.44;
  const LEN = ring * 0.56;
  // The bar COUNT follows the ring's circumference, not the frame: a fixed 72 that looked right at one radius
  // is a picket fence at a smaller one and a comb at a larger. Even, so the vertical axis falls between two
  // bars and the rig stays mirror-symmetric.
  const BARS = Math.max(24, Math.round((2 * Math.PI * R0) / (U * 0.0155) / 2) * 2);

  const rev = easeOutCubic(seg(t, 0.04, 0.4));                    // the ring reveals
  const titleIn = easeOutCubic(seg(t, 0.3, 0.55));
  const tagIn = easeOutCubic(seg(t, 0.6, 0.82));
  const titlePx = fitTextPx(String(TITLE ?? ''), Math.min(W * 0.7, R0 * 1.55),
    Math.round(U * 0.104), {usable: 1.0});
  const tagPx = fitTextPx(String(TAG ?? ''), Math.min(W * 0.7, R0 * 1.6),
    Math.round(U * 0.028), {usable: 1.0});

  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 48%, #16091f, ${BG} 76%)`, overflow: 'hidden'}}>
      <Voice samples={Math.min(128, BARS / 2)}>
        {({bars, level}) => {
          // the ring breathes with the VOICE rather than with a metronome — one number, so the wordmark, the
          // core glow and the bar length all swell on the same syllable and read as one object reacting.
          const beat = level;
          return (
            <>
              <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
                <defs>
                  <radialGradient id="spcore">
                    <stop offset="0" stopColor="#fff" stopOpacity="0.4" />
                    <stop offset="1" stopColor="#fff" stopOpacity="0" />
                  </radialGradient>
                </defs>
                <g transform={`translate(${cx} ${cy})`}>
                  {Array.from({length: BARS}).map((_, i) => {
                    const ang = (i / BARS) * Math.PI * 2 - Math.PI / 2;
                    // 0 (the low, loud end of the spectrum) at 12 o'clock, 1 at 6 o'clock. Written the other
                    // way round the rig grows its longest bars downward and reads as melting rather than as a
                    // crown — and it collides with the caption band it was just sized to clear.
                    const d = 1 - Math.abs(i - BARS / 2) / (BARS / 2);
                    const amp = bars[Math.min(bars.length - 1, Math.round(d * (bars.length - 1)))] ?? 0;
                    // a floor so the rig is always a RING: with nothing being said the bars collapse to a
                    // corona rather than vanishing, and the wordmark is never left floating in the dark.
                    const len = LEN * clamp01(0.12 + amp * 0.88 * (0.75 + 0.5 * beat)) * rev;
                    const x1 = Math.cos(ang) * R0, y1 = Math.sin(ang) * R0;
                    const x2 = Math.cos(ang) * (R0 + len), y2 = Math.sin(ang) * (R0 + len);
                    const col = i % 2 ? A1 : A2;
                    return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={col}
                      strokeWidth={Math.max(2, U * 0.0065)} strokeLinecap="round"
                      opacity={0.5 + 0.5 * amp} style={{filter: `drop-shadow(0 0 ${U * 0.006}px ${col})`}} />;
                  })}
                  <circle r={R0 - U * 0.013} fill="none" stroke="#ffffff22" strokeWidth={Math.max(1, U * 0.0019)} />
                  <circle r={R0 - U * 0.013} fill="url(#spcore)" opacity={0.14 + 0.2 * beat} />
                </g>
              </svg>
              <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', top: CONTENT_TOP, height: zoneH, textAlign: 'center'}}>
                <div style={{opacity: titleIn, transform: `scale(${1 + beat * 0.03})`, color: '#fff',
                  font: `800 ${titlePx}px/${leading(String(TITLE), 1.05)} var(--f-display, Inter, system-ui, sans-serif)`,
                  letterSpacing: '-0.03em', textShadow: `0 0 ${U * 0.037}px ${A1}66`}}>{TITLE}</div>
                <div style={{opacity: tagIn, marginTop: U * 0.017, color: '#c9b6e6',
                  font: `600 ${tagPx}px/${leading(String(TAG), 1.2)} var(--f-mono, "JetBrains Mono", monospace)`,
                  letterSpacing: '0.18em'}}>{TAG}</div>
              </AbsoluteFill>
            </>
          );
        }}
      </Voice>
    </AbsoluteFill>
  );
};
export default SpectrumPulse;
