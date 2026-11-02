// OTHER BEATS OF THE SAME FILM, as pictures a beat can show — the cold open's flash of what is coming, the finale's
// gathering of what was seen. Film.tsx provides `TeaserContext`: `render(beat)` draws that beat's own register, with
// its own props and its own ground, FROZEN at its settled frame (the frame every visual gate judges). A register
// reads it with `useTeaser()`; with no provider (a still, a library sweep) it gets null and draws its stand-in.
//
// A register cannot import Film or the registry (the registry imports every register), so the film hands the
// pictures down instead. A beat that is itself built of teasers is refused as a teaser: a cold open showing a finale
// showing the cold open is a loop, not a picture.
import React from 'react';
import {SEAM_FRAMES, ENTRY_T} from './motion';

/** Draws film beat `beat` (1-based, as the board numbers them), frozen at its own `t`; null when there is none. */
export type TeaserRender = (beat: number, t?: number) => React.ReactNode | null;

export const TeaserContext = React.createContext<{render: TeaserRender; beats: number; self: number} | null>(null);

export const useTeaser = () => React.useContext(TeaserContext);

/** The registers built of other beats — never shown as a teaser themselves. */
export const TEASER_SHOTS = new Set(['ColdOpen', 'Callback']);

/** The t the teasers are frozen at: the beat LANDED. 0.88 (the frame the visual gates judge) caught a register whose
 *  last step lands late mid-move — Rearrange's ranking half-way into its groups; by 0.95 a register has landed and
 *  useT's held tail has not begun. */
export const SETTLED_T = 0.95;

/** The frame of a `dur`-frame beat at which runtime/motion's useT reads `t` (the inverse of useT's own map). */
export const frameAtT = (t: number, dur: number): number => {
  const pad = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, dur - 1) / 3));
  const span = Math.max(1, dur - 1 - 2 * pad);
  return Math.max(0, Math.min(dur - 1, Math.round(pad + ((t - ENTRY_T) / (1 - ENTRY_T)) * span)));
};

/** The board's beat numbers checked against the film: real beats, not this one, not a teaser-built beat. */
export const checkTeaserBeats = (beats: unknown, n: number, self: number, shots: string[], who: string,
  min: number, max: number): number[] => {
  if (!Array.isArray(beats) || beats.length < min || beats.length > max) {
    throw new Error(`${who} needs ${min}-${max} \`beats\` (the film's beat numbers it shows), got ${JSON.stringify(beats)}`);
  }
  return beats.map((b) => {
    if (!(Number.isInteger(b) && b >= 1 && b <= n)) throw new Error(`${who}: beat ${JSON.stringify(b)} is not one of the film's 1-${n}`);
    if (b === self) throw new Error(`${who}: beat ${b} is this beat — it cannot show itself`);
    if (TEASER_SHOTS.has(shots[b - 1])) throw new Error(`${who}: beat ${b} is a ${shots[b - 1]} — a beat built of other beats is not a picture to show`);
    return b as number;
  });
};
