// THE MARKS AN EQUATION LEAVES IN THE DOM, AND THE ONLY THING THE GATES KNOW ABOUT IT.
//
// runtime/mathMorph.tsx draws an equation as glyph OUTLINES (SVG paths), so it has no text node for any type gate to
// find: a cut-off equation, an equation sitting in the caption band, a label set on top of one — all invisible. The
// root carries the TeX, each glyph is marked, and the census (textSafe.tsx) reads the root as ONE line whose text is
// its TeX and whose box is the union of its visible glyphs.
//
// Its own module, imported by both sides, so the writer and the reader cannot spell an attribute two ways — and NOT
// appended to kineticDom.ts, which every kinetic register reaches through runtime/kinetic: the library's measurements
// hash every module a register imports, and two new constants there marked four registers' energy rows stale whose
// pixels had not moved (scripts/register_energy.py --check, 2026-10-24).
/** On an equation's root: its TeX (the line's text for every gate). Its font-size is the equation's em in px. */
export const MATH_ROOT = 'data-math';
/** On each glyph path of an equation. */
export const MATH_GLYPH = 'data-mg';
