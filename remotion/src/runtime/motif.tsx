// FILM MOTIF — one topic-derived MATERIAL, drawn across the whole film.
//
// WHY THIS EXISTS. Every register draws its own structure and nothing else, so a themed film is a set of
// clean, correct, and slightly bare frames: the DNA gives them a shared palette and type, but no shared
// MATERIAL. A viewer reads that as "well-made diagrams", not as "a designed film". The html tier solved the
// same problem years earlier with motifs.css + a fixed-seed film grain; the shot tier had nothing.
//
// A motif is not decoration. It is the subject's own material stated once and inherited everywhere: brick
// coursing for a built city, a waterline for a place made of water, a survey graticule for a mapped subject,
// engraved hatching for a printed one, staff rules for music, contour for terrain. It sits ABOVE the scenes
// (a shot paints its own opaque ground, so a layer underneath would never be seen) and BELOW the caption,
// at an opacity low enough that it never competes with content — the test is that removing it should make
// the film look flatter without anyone being able to say which element left.
//
// Deterministic by construction: every motif is a function of position only, so it is seekable and identical
// on every render. No noise, no time term, nothing to desync at a seam.

import React from 'react';
import {AbsoluteFill} from 'remotion';
import type {DesignDNA} from './dna';

export type MotifKind =
  | 'none'
  | 'coursing'     // masonry courses — a built subject
  | 'waterline'    // a horizontal water band with a still ripple — a place made of water
  | 'graticule'    // a survey grid with tick crosses — a mapped or measured subject
  | 'hatch'        // engraved diagonal hatching — a printed / plate subject
  | 'deckle'       // paper tooth — a written subject
  | 'contour'      // nested contour lines — terrain, gradients, fields
  | 'staff';       // ruled staves — music, sequence, notation

export type FilmMotif = {
  kind?: MotifKind;
  ink?: 'line' | 'accent' | 'accent2' | 'dim' | 'fg';   // which DNA token draws it
  opacity?: number;   // default deliberately low; this is material, not content
  scale?: number;     // 1 = the default pitch for the kind
};

/** Whether the film's ground is dark, which decides how the material has to blend. */
const _isDark = (hex?: string): boolean => {
  if (!hex) return true;
  const h = hex.replace('#', '');
  const f = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6);
  const n = parseInt(f, 16);
  if (!isFinite(n)) return true;
  return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255 < 0.5;
};

const tokenOf = (dna: DesignDNA | null | undefined, ink: FilmMotif['ink']): string => {
  if (!dna) return '#8883';
  switch (ink) {
    case 'accent': return dna.accent;
    case 'accent2': return dna.accent2;
    case 'dim': return dna.dim;
    case 'fg': return dna.fg;
    default: return dna.line;
  }
};

/** The film-wide material. Renders nothing at all when no motif is declared. */
export const FilmMotifLayer: React.FC<{motif?: FilmMotif; dna?: DesignDNA | null; W: number; H: number}> =
  ({motif, dna, W, H}) => {
    const kind = motif?.kind ?? 'none';
    if (!motif || kind === 'none') return null;
    const ink = tokenOf(dna, motif.ink);
    const op = motif.opacity ?? 0.07;
    const k = Math.max(0.4, Math.min(3, motif.scale ?? 1));
    const px = (n: number) => Math.max(1, Math.round(n));

    // MULTIPLY, not a plain overlay. Drawn straight, the material prints on the CONTENT too — a brick
    // course ran visibly through the middle of a hero figure. Multiply behaves like ink on paper: it darkens
    // the light ground and leaves dark ink essentially untouched, so the material sits under the type
    // instead of across it. A dark-ground film gets `screen` for the same reason, mirrored.
    const dark = _isDark(dna?.bg);
    const common: React.CSSProperties = {
      pointerEvents: 'none', opacity: op,
      mixBlendMode: dark ? 'screen' : 'multiply'};

    if (kind === 'coursing') {
      // courses of masonry: a horizontal rule per course, with every other course offset by half a brick
      const ch = px(H * 0.052 * k), bw = px(W * 0.085 * k), hair = px(W * 0.0011);
      const rows = Math.ceil(H / ch) + 1;
      return (
        <AbsoluteFill style={common}>
          {Array.from({length: rows}).map((_, r) => (
            <React.Fragment key={r}>
              <div style={{position: 'absolute', left: 0, right: 0, top: r * ch, height: hair, background: ink}} />
              {Array.from({length: Math.ceil(W / bw) + 1}).map((__, c) => (
                <div key={c} style={{position: 'absolute', top: r * ch, height: ch, width: hair,
                  left: c * bw + (r % 2 ? bw / 2 : 0), background: ink}} />
              ))}
            </React.Fragment>
          ))}
        </AbsoluteFill>
      );
    }

    if (kind === 'waterline') {
      // one band across the lower third, its surface a still standing wave rather than an animation
      const y = H * 0.62, hair = px(W * 0.0013);
      const steps = 96;
      return (
        <AbsoluteFill style={common}>
          <div style={{position: 'absolute', left: 0, right: 0, top: y, bottom: 0, background: ink,
            opacity: 0.35}} />
          {Array.from({length: steps}).map((_, i) => {
            const x = (i / steps) * W;
            const dy = Math.sin((i / steps) * Math.PI * 2 * 3 * k) * H * 0.006;
            return <div key={i} style={{position: 'absolute', left: x, top: y + dy,
              width: W / steps + 1, height: hair * 2, background: ink}} />;
          })}
          {[0.16, 0.30, 0.46].map((f, i) => (
            <div key={'r' + i} style={{position: 'absolute', left: 0, right: 0, top: y + H * f * 0.5,
              height: hair, background: ink, opacity: 0.5}} />
          ))}
        </AbsoluteFill>
      );
    }

    if (kind === 'graticule') {
      const step = px(Math.min(W, H) * 0.075 / k), hair = px(W * 0.0009);
      const tick = px(W * 0.005);
      const cols = Math.ceil(W / step) + 1, rows = Math.ceil(H / step) + 1;
      return (
        <AbsoluteFill style={common}>
          {Array.from({length: cols}).map((_, c) => (
            <div key={'c' + c} style={{position: 'absolute', top: 0, bottom: 0, left: c * step,
              width: hair, background: ink}} />
          ))}
          {Array.from({length: rows}).map((_, r) => (
            <div key={'r' + r} style={{position: 'absolute', left: 0, right: 0, top: r * step,
              height: hair, background: ink}} />
          ))}
          {Array.from({length: cols}).map((_, c) =>
            Array.from({length: rows}).map((__, r) => (
              <React.Fragment key={`t${c}-${r}`}>
                <div style={{position: 'absolute', left: c * step - tick, top: r * step,
                  width: tick * 2, height: hair * 2, background: ink}} />
                <div style={{position: 'absolute', left: c * step, top: r * step - tick,
                  width: hair * 2, height: tick * 2, background: ink}} />
              </React.Fragment>
            )))}
        </AbsoluteFill>
      );
    }

    if (kind === 'hatch') {
      const step = px(Math.min(W, H) * 0.026 / k), hair = px(W * 0.0009);
      const n = Math.ceil((W + H) / step);
      return (
        <AbsoluteFill style={{...common, overflow: 'hidden'}}>
          {Array.from({length: n}).map((_, i) => (
            <div key={i} style={{position: 'absolute', left: -H, top: i * step, width: W + H * 2,
              height: hair, background: ink, transformOrigin: '50% 50%', transform: 'rotate(-32deg)'}} />
          ))}
        </AbsoluteFill>
      );
    }

    if (kind === 'contour') {
      const rings = Math.round(11 * k), hair = px(W * 0.001);
      return (
        <AbsoluteFill style={{...common, overflow: 'hidden'}}>
          {Array.from({length: rings}).map((_, i) => {
            const f = (i + 1) / rings;
            const rw = W * 0.36 * f * 2.6, rh = H * 0.36 * f * 2.6;
            return <div key={i} style={{position: 'absolute', left: W * 0.34 - rw / 2, top: H * 0.55 - rh / 2,
              width: rw, height: rh, borderRadius: '50%', border: `${hair}px solid ${ink}`}} />;
          })}
        </AbsoluteFill>
      );
    }

    if (kind === 'staff') {
      const group = px(H * 0.20 / k), gap = px(H * 0.017 / k), hair = px(W * 0.0011);
      const groups = Math.ceil(H / group) + 1;
      return (
        <AbsoluteFill style={common}>
          {Array.from({length: groups}).map((_, g) =>
            [0, 1, 2, 3, 4].map((l) => (
              <div key={`${g}-${l}`} style={{position: 'absolute', left: 0, right: 0,
                top: g * group + l * gap, height: hair, background: ink}} />
            )))}
        </AbsoluteFill>
      );
    }

    // deckle — paper tooth: a fine, position-derived speckle that reads as grain, not noise.
    //
    // The first version kept 26% of cells and drew 1-3px dots, which measured 0.7% of pixels changed
    // against a no-motif render — visually nothing. A motif that claims to be there and is not is worse
    // than declaring none, because the film looks unmaterialled and the setting says otherwise. The grain
    // now covers most cells with a dot scaled to the cell, which measures in the same band as the other
    // kinds while still reading as tooth rather than as noise.
    const cell = px(Math.min(W, H) * 0.010 / k);
    const cols = Math.ceil(W / cell), rows = Math.ceil(H / cell);
    const dot = Math.max(2, Math.round(cell * 0.55));
    return (
      <AbsoluteFill style={{...common, overflow: 'hidden'}}>
        {Array.from({length: rows}).map((_, r) =>
          Array.from({length: cols}).map((__, c) => {
            // a deterministic hash of the cell, so the grain is identical on every render
            const h = ((c * 374761393 + r * 668265263) ^ 0x5bf03635) >>> 0;
            if ((h % 100) > 72) return null;
            const s = dot + (h % 2);
            return <div key={`${c}-${r}`} style={{position: 'absolute',
              left: c * cell + (h % Math.max(1, cell - dot)),
              top: r * cell + ((h >> 8) % Math.max(1, cell - dot)),
              width: s, height: s, background: ink, opacity: 0.5 + (h >> 16 & 63) / 128}} />;
          }))}
      </AbsoluteFill>
    );
  };
