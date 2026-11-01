// THE CJK DISPLAY VOICE — which face a Chinese film's TITLES are set in (meta.cjk_display; validate asks for it).
//
// Every DNA stack names a Latin face and then Noto, so a Chinese title fell to Noto whatever the film was; the two
// display faces bundled beside Noto (assets/fonts/TTV-SC-SUBSET-NOTE.txt) were unreachable. The voice is inserted
// AFTER the stack's first family and BEFORE the rest: Latin letters stay in the stack's Latin face, Han takes the
// voice, and a character the voice lacks falls back to the Noto face after it. Its own module, not runtime/dna:
// a change to dna.tsx re-keys every register's measured source.

export const CJK_VOICES = ['noto', 'TTV Display', 'TTV Kai'] as const;
export type CjkVoice = typeof CJK_VOICES[number];

/** `stack` with the voice placed after its first family; unchanged for 'noto', an absent voice, or one already in. */
export const withCjkDisplay = (stack: string, voice?: string | null): string => {
  if (!voice || voice === 'noto' || !stack) return stack;
  if (stack.includes(`"${voice}"`)) return stack;
  const parts = stack.split(',').map((p) => p.trim()).filter(Boolean);
  return [parts[0], `"${voice}"`, ...parts.slice(1)].join(', ');
};
