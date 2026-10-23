// THE MARKS A KINETICTEXT LEAVES IN THE DOM, AND THE ONLY THING THE GATES KNOW ABOUT IT.
//
// runtime/kinetic.tsx draws type ONE GRAPHEME PER ELEMENT (kerning, CJK punctuation compression and kinsoku are
// kept by placing each glyph where one reference text node laid it out). Every type gate in this library walks
// the DOM element by element (runtime/textSafe.tsx, runtime/titleProbe.tsx), so without these marks a kinetic
// headline reads as forty one-letter "lines": a title that is the letter "S", a cut word reported forty times or
// shaved under the per-glyph floor, a sync audit that can match no word of it to the narration, and a collision
// test that compares letters with letters. The census groups the glyphs back into the LINES a reader sees.
//
// Its own module, imported by both sides, so the writer and the reader cannot spell an attribute two ways — and so
// the census (textSafe.tsx) does not import the primitive, whose source the library's measurements hash.

/** On the KineticText root. Its value is the id the census keys the text by. */
export const KIN_ROOT = 'data-kinetic';
/** On each glyph's TEXT holder (the element whose own text is the grapheme): the line it was laid out on. */
export const KIN_LINE = 'data-kl';
/** On each glyph's text holder: the grapheme's index in its text, so a line is read back in reading order. */
export const KIN_GLYPH = 'data-kg';
/** On each glyph's text holder of a SWAP: which alternative it belongs to. A line shows the most visible one. */
export const KIN_ALT = 'data-kalt';
/** On the root, "1" when the text must be READ (a gate holds its hold time to its reading time). */
export const KIN_READ = 'data-kinetic-read';
/** On the root: the alignment its lines were set with (left | center | right), for the title probe. */
export const KIN_ALIGN = 'data-kinetic-align';

/** Prefix on the hold report a still render cancels with (scripts/shot_proof.py reads it). */
export const KINETIC_HOLDS_TAG = 'KINETIC-HOLDS ';

// ── "IS ANY KINETICTEXT STILL MEASURING?" ────────────────────────────────────────────────────────────────
// The audits walk the DOM once the fonts are ready and a frame has passed. A KineticText draws nothing until its
// reference has been measured — after the faces load, in a promise — so an audit that does not wait walks a frame
// with no glyphs on it and reports it clean. That happened: the first cut-off probe came back with no finding.
// The hook raises this count when it starts measuring and lowers it only once its glyphs are COMMITTED; every audit
// awaits `kineticIdle()` before it reads the DOM. A global, not a context, because the audits mount beside the shot.
type KineticGlobal = {__kineticPending?: number};
const KG = globalThis as unknown as KineticGlobal;
export const kineticBusy = (delta: 1 | -1): void => {
  KG.__kineticPending = Math.max(0, (KG.__kineticPending ?? 0) + delta);
};
export const kineticIdle = async (maxMs = 60000): Promise<void> => {
  for (let waited = 0; (KG.__kineticPending ?? 0) > 0 && waited < maxMs; waited += 25) {
    await new Promise((res) => setTimeout(res, 25));
  }
  await new Promise((res) => requestAnimationFrame(() => res(null)));
  await new Promise((res) => setTimeout(res, 0));
};

/**
 * Resolves once the bundled faces are in `document.fonts` (runtime/fonts.ts publishes the promise). Where fonts.ts
 * never ran there is nothing of ours to wait for, and the browser's own `document.fonts.ready` is the answer.
 */
export const facesReady = (): Promise<unknown> => {
  const p = (globalThis as unknown as {__dnaFacesReady?: Promise<void>}).__dnaFacesReady;
  if (p) return p;
  const d = (globalThis as unknown as {document?: {fonts?: {ready: Promise<unknown>}}}).document;
  return d?.fonts?.ready ?? Promise.resolve();
};
