// THE NAME A TYPESET EQUATION IS FILED UNDER — one function, read by the bundle and by the node typesetter.
//
// NO IMPORTS: scripts/tex_glyphs.mjs imports this file directly (node strips the types), so the key a film's prep step
// writes a file under and the key the register fetches it by cannot be computed two ways. A key collision is not
// trusted either: every typeset file carries its own TeX, and runtime/mathMorph refuses a file whose TeX is not the
// one it asked for.

/** Bump when the glyph file's shape changes: every key changes with it, so a stale cache is never read as current. */
export const MATH_FORMAT = 1;

/** The TeX as it is keyed and typeset: trimmed, nothing else (TeX's own whitespace rules handle the rest). */
export const normTex = (tex: string): string => String(tex ?? '').trim();

/** 64-bit FNV-1a over the UTF-16 code units, as 16 hex digits, salted with the format and the display mode. */
export const mathKey = (tex: string, display = true): string => {
  const s = `${MATH_FORMAT}|${display ? 'D' : 'T'}|${normTex(tex)}`;
  let h1 = 0x811c9dc5, h2 = 0x050c5d1f;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 0x01000193) >>> 0;
    h2 = Math.imul(h2 ^ c, 0x01000193) >>> 0;
    h2 = (h2 ^ (h1 >>> 15)) >>> 0;
  }
  return h1.toString(16).padStart(8, '0') + h2.toString(16).padStart(8, '0');
};
