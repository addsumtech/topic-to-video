// CJK TYPE FLOOR — the leading a line of Chinese needs, derived from the copy rather than assumed.
//
// WHY THIS EXISTS. A display face set at `line-height: 0.82` is confident Latin typography: capitals have no
// descenders and Latin glyphs sit well inside their em box, so the lines close up and nothing touches. CJK
// glyphs FILL the em box by design — there is no side-bearing to borrow — so the same 0.82 puts strokes on
// top of strokes. Measured on a real Chinese film in one evening: `BrutalistType` (0.82) laid its two title
// blocks into each other, and `MagazineSpread` (0.98) wrapped a headline to three lines with line 2 inside
// line 1 and the standfirst buried underneath. Nothing was cut off, so `text_safe_qa` passed both, correctly
// — it asks a different question. `scripts/cjk_type_qa.py` asks this one.
//
// WHY IT IS DERIVED FROM THE TEXT, NOT SET GLOBALLY. Raising every register's leading to 1.15 would flatten
// the Latin typography the library was designed with: a 0.82 stack is the POINT of a brutalist title. So the
// floor applies only when the string it is setting actually contains CJK, which is a property of the film's
// copy, not of the register. An English film renders byte-for-byte what it rendered before.
//
// THE NUMBER. 1.06 is the floor, not a target. At exactly 1.0 the em boxes abut and dense strokes at the top
// and bottom of adjacent glyphs (、 and 一, or a 3-part radical) still visually merge; 1.06 gives that a few
// pixels of air while staying tight enough to read as display type. Registers wanting real prose leading
// pass their own larger value and keep it — `leading` only ever RAISES.

/** Any Han, kana, Hangul or CJK punctuation. */
export const hasCJK = (s: unknown): boolean =>
  typeof s === 'string' &&
  /[ᄀ-ᇿ⺀-〿぀-ヿ㄰-㆏㐀-䶿一-鿿가-힯豈-﫿︰-﹏＀-￯]/.test(s);

/** The floor a CJK line needs. Exported so a gate and a register cannot drift apart. */
export const CJK_MIN_LEADING = 1.06;

/**
 * The line-height to actually set: the author's own value for Latin copy, raised to the floor for CJK.
 *
 * `text` may be a string, an array of them, or anything else — a register usually has the copy right there.
 * Pass everything that shares the line box; one CJK string in the block raises the whole block, which is
 * correct, because that is the line that would collide.
 */
export const leading = (text: unknown, latin: number): number => {
  const any = Array.isArray(text) ? text.some((t) => hasCJK(t)) : hasCJK(text);
  return any ? Math.max(latin, CJK_MIN_LEADING) : latin;
};

/**
 * `font:` shorthand is where the library actually sets leading (`900 ${size}px/0.82 var(--f-display…)`), so
 * this builds that string with the floor already applied. Keeps a register's edit to one call.
 */
export const fontWithLeading = (
  weight: string | number,
  sizePx: number,
  latinLeading: number,
  family: string,
  text: unknown,
): string => `${weight} ${sizePx}px/${leading(text, latinLeading)} ${family}`;

/**
 * Fit a size ONLY when the copy is CJK; Latin keeps the size the register was designed at.
 *
 * The distinction matters and the first version got it wrong. A register's Latin headline is often MEANT to
 * wrap — a giant feature headline in a narrow column is the composition — so fitting it to one line would
 * quietly redesign every English film to fix a Chinese one. A CJK headline of the same sense is far wider
 * and wraps into whatever sits below it, so there the fit is the repair. Same call, two behaviours, decided
 * by the copy rather than by a flag someone has to remember.
 */
export const fitIfCJK = (
  text: unknown,
  base: number,
  fit: (t: string, base: number) => number,
): number => (hasCJK(text) ? fit(String(text ?? ''), base) : base);
