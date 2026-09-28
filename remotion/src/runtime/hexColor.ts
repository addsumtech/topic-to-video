// `runtime/dna.tsx`'s relLum (not edited — every register imports that file, so a line added there stales
// the whole measured manifest) reads a plain 6-digit hex only and reports 0 (reads as maximally DARK) for
// anything else — so a DNA authored with the 3-digit shorthand (`fg: '#fff'`), or a 4-/8-digit form with an
// alpha channel (`'#ffff'`, `'#ffffffff'`), relLum's as dark regardless of what colour it actually names. A
// caller that reads a DNA token's polarity (is this face's ground light or dark?) needs the colour NORMALISED
// to plain 6-digit hex first. Alpha is dropped, not composited: relLum measures the colour AS PAINTED on
// whatever already sits behind it, which this module has no way to know.
const HEX = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

/** `c`, as a plain 6-digit `#rrggbb` — 3-digit expanded, 4-/8-digit expanded/kept with alpha dropped, 6-digit
 *  unchanged. Anything else this cannot read as hex (a gradient, `var(...)`, malformed input) comes back
 *  exactly as given, for the caller's own fallback to decide. */
export const hex6 = (c: string): string => {
  const m = HEX.exec(c);
  if (!m) return c;
  const h = m[1];
  if (h.length === 6) return c;
  if (h.length === 3 || h.length === 4) return '#' + [...h.slice(0, 3)].map((ch) => ch + ch).join('');
  return '#' + h.slice(0, 6);          // 8 digits: rrggbbaa, alpha dropped
};
