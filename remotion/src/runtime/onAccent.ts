// THE INK FOR TYPE SET ON A SOLID `accent` BLOCK — and the one place a system's SECOND accent can speak.
//
// A DNA's `accent2` is frequently the colour it cannot set anywhere. Measured on a light-stock film whose two
// brand colours are a navy and a teal: the teal reads **1.59:1 on the paper** — under any floor, so it can
// only ever be a fill there — and **5.29:1 on its own navy**. That asymmetry is not that film's accident; a
// second accent is usually chosen for chroma against the FIRST accent, not for value against the ground. So
// the rule this encodes is: the second accent is the VOICE on the first accent's block, and a fill everywhere
// else.
//
// It is a MEASUREMENT, not a preference. `accent2` wins only when it actually clears the floor on `accent`,
// so a system whose two accents sit at the same value never gets a label nobody can read — it falls back to
// the DNA's own `onAccent`, then `fg`, then the poles. Callers pass the block colour they ACTUALLY painted
// (which may itself have been pushed to be readable by `readableOn`), never the raw token.
//
// WHY THIS IS ITS OWN MODULE AND NOT A LINE IN `dna.tsx`. `register_energy.source_hash` hashes each shot's
// .tsx together with the runtime modules it imports, and every register in the library imports `dna.tsx` —
// so one line added there marks all 170 measured rows stale and switches the energy-skeleton gate off until
// someone spends the full sweep re-rendering them. A new shared rule that only new shots consume belongs in
// a module only they import. Move it into `dna.tsx` when the next full sweep is being run anyway.

import {contrastOf, readableOn} from './dna';

/** WCAG's floor for large text and non-text contrast. Below it a reversed label is a colour, not a word. */
export const ON_ACCENT_MIN = 4.5;

export const onAccentInk = (
  accent: string, accent2?: string | null, onAccent?: string | null, fg?: string | null,
): string => {
  if (accent2 && contrastOf(accent2, accent) >= ON_ACCENT_MIN) return accent2;
  return readableOn(accent, onAccent ?? '', fg ?? '', '#ffffff', '#0a0d14');
};
