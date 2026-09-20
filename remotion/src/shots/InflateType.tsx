// SHOT · Inflate Type — big puffy BALLOON letters inflate into place with an over-bounce, glossy shaded
// fills + specular highlights + soft contact shadows, then a gentle breathing wobble. The 2026 inflated
// typography trend (family P · dimensional type).
//
// THE TECHNIQUE IS 2D SHADING, and the header used to say "3D" — which is the claim that made a viewer
// look for 3D in this library and not find it. There is no camera, no perspective and no depth buffer
// here: the volume is gradients, highlights and a contact shadow, done well. That is a real technique and
// worth naming as itself.) Deterministic (inflate + wobble = fn of t).
//
// EVERY LETTER INFLATES BEFORE THE FRAME IS READ. Letter i used to start at `0.08 + i * 0.09` and take 0.34 —
// a fixed step per letter — so the eleventh was still a small faint blob on the LAST frame and the twelfth
// onward started after the clip had ended: a film's twelve-character name lost its tail with no error. The
// step is now laid out for the word — 0.09 stays the upper bound, so a word of up to five letters keeps its
// exact rhythm — and closes until the last letter has inflated by LAND_BY, just before the frame `useT` calls
// settled. Past MAX_INFLATE_CHARS the balloons would shrink below a hero word, so the register refuses. The
// specular blob now scales with the letters; at a fixed 46px it was a highlight bigger than a small glyph.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, REDUCED_MOTION_T} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {fitTextPx} from '../runtime/layout';

export const DURATION = 150; // 5s
const BG_D0 = '#0e1030';
const TONES0 = ['#ff6f9d', '#5b8cff', '#ffd24d', '#37e0c8', '#c07bff', '#ff8a4d'];
export const MAX_INFLATE_CHARS = 16;
// Letter i inflates over [INF_START + i * step, … + INF_DUR]; INF_STEP is the original gap and only an upper
// bound — the real step is derived from the word's length so the last letter has landed by LAND_BY.
const INF_START = 0.08, INF_STEP = 0.09, INF_DUR = 0.34;
const LAND_BY = REDUCED_MOTION_T - 0.02;

export const InflateType: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'PUFFY', tagline: TAG = 'soft, bold, dimensional'} = {}) => {
  // One balloon per CHARACTER (code point, so an astral glyph is not split into two halves).
  const letters = [...String(WORD ?? '')];
  const n = letters.length;
  if (!String(WORD ?? '').trim() || n > MAX_INFLATE_CHARS) {
    throw new Error(
      `InflateType needs a \`word\` of 1-${MAX_INFLATE_CHARS} characters, spaces included (got ` +
      `${String(WORD ?? '').trim() ? n : 'no visible character'}). Each letter inflates on its own beat and ` +
      'must have landed before the settled frame, on one row at hero size; a longer phrase belongs in a ' +
      'headline register.');
  }
  const step = n > 1 ? Math.min(INF_STEP, (LAND_BY - INF_START - INF_DUR) / (n - 1)) : INF_STEP;
  const dna = useDNA();
  const TONES = dnaPalette(dna, 6) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE WORD IS FITTED TO THE FRAME. 240px holds 'PUFFY' on a 1920 frame and four Han glyphs on a 1080 one
  // — and the CJK fixture happens to hand this register exactly four, so the sweep proved it survives four
  // and nothing more. A real film writes the phrase its topic needs: at eight glyphs the word was sliced
  // 450px on the left and 461px on the right at 1:1.
  // The glyphs are a flex ROW that cannot wrap, each with a fixed 6px margin either side and a soft-body
  // scale that breathes out past 1 — so the fit is given the room the widest moment of that breath needs.
  const GLYPH_MARGIN = 12, SX_MAX = 1.05;
  const wordPx = Math.min(240, fitTextPx(WORD,
    Math.max(60, (W * 0.94) / SX_MAX - n * GLYPH_MARGIN), 240, {usable: 1, track: -0.01}));
  const tagIn = easeOutCubic(seg(t, 0.66, 0.86));
  // 3D extrusion via stacked shadows, glossy top-light gradient, specular blob
  const extrude = (c: string) => {
    let s = '';
    for (let k = 1; k <= 10; k++) s += `${k * 2}px ${k * 3}px 0 rgba(0,0,0,${0.06}), `;
    return s + `0 30px 50px rgba(0,0,0,.4)`;
  };
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 34%, #1a1c50, ${BG} 74%)`, overflow: 'hidden',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'center'}}>
        {letters.map((ch, i) => {
          const st = INF_START + i * step;
          const inf = easeOutBack(clamp01(seg(t, st, st + INF_DUR)));    // inflate with overshoot
          const settle = t > st + INF_DUR;
          const wob = settle ? 1 + 0.03 * Math.sin(t * 4 - i * 0.6) : 1; // breathing
          const sx = lerp(0.2, 1, inf) * (settle ? wob : 1);
          const sy = lerp(0.2, 1, inf) * (settle ? 2 - wob : 1);         // squash-counter for a soft-body feel
          const tone = TONES[i % TONES.length];
          if (ch === ' ') return <div key={i} style={{width: 60}} />;
          return (
            <div key={i} style={{position: 'relative', opacity: clamp01(inf * 1.6),
              transform: `translateY(${(1 - inf) * 40}px) scale(${sx}, ${sy})`, transformOrigin: 'center bottom',
              margin: '0 6px'}}>
              <span style={{display: 'block',
                fontFamily: 'var(--f-display, "Baloo 2", Inter, system-ui, sans-serif)', fontWeight: 900, fontSize: wordPx, lineHeight: 1,
                letterSpacing: '-0.01em', color: tone,
                background: `linear-gradient(180deg, #ffffff, ${tone} 42%, ${tone})`,
                WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent',
                filter: `drop-shadow(6px 10px 0 rgba(0,0,0,.18)) drop-shadow(0 26px 34px rgba(0,0,0,.45))`,
                textShadow: extrude(tone)} as React.CSSProperties}>{ch}</span>
              {/* specular highlight */}
              <div style={{position: 'absolute', left: '24%', top: '14%', width: Math.round(46 * wordPx / 240),
                height: Math.round(30 * wordPx / 240), borderRadius: '50%',
                background: '#ffffff', opacity: 0.55 * inf, filter: 'blur(4px)'}} />
            </div>
          );
        })}
      </div>
      <div style={{opacity: tagIn, transform: `translateY(${(1 - tagIn) * 12}px)`, marginTop: 54, color: '#c7d0ff',
        font: '700 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default InflateType;
