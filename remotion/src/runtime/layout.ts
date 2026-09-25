// layout.ts — the FRAME-CRAFT FLOOR, shared so every bespoke shot gets the safe zones for free instead of
// hand-guessing pixel positions (the source of a whole class of defects this tier kept hitting: an image sized
// to the FULL frame rode up UNDER the title; two edge-anchored labels COLLIDED when a panel shrank; a global
// downscale added BLACK BORDERS by shrinking each shot's own background). The rules:
//
//   • FULL-BLEED. A shot's root AbsoluteFill background MUST reach all four frame edges (opaque, no inset,
//     no wrapping scale). The Film composites shots edge-to-edge; never scale the whole shot to gain a margin
//     — that exposes the atmosphere behind as a border. Edge-safety is a per-ELEMENT contract, not a global squish.
//   • TITLE band at the top: the shot title sits at TITLE_Y; keep real content out of [0, CONTENT_TOP).
//   • CAPTION band at the bottom: the Film burns the narration caption in the bottom CAPTION_BAND px. Keep the
//     shot's OWN text/labels out of [H - CAPTION_BAND, H] (a small credit line at the very bottom is the only
//     allowed exception). Otherwise the shot text and the caption overlap.
//   • So the usable CONTENT ZONE is [CONTENT_TOP, H - CAPTION_BAND]. Center a hero image/panel THERE, not in the
//     whole frame, or it collides with the title. Use fitContentSquare() and it's automatic.
//
// These are the numbers the Film (src/Film.tsx) reserves; keep them in sync with its CAPTION_BAND + title.

import type React from 'react';

export const TITLE_Y = 92;              // title top (px) — the shared header position for a shot's title <div>
export const TITLE_BAND = 176;          // content must start BELOW this (title + a comfortable gap ~40px)
// The caption BAND is derived from the caption's own type size, not guessed. It has to hold two wrapped lines
// of `CAPTION_SIZE_FRAC` type plus the block's bottom margin plus a real GAP, or the caption reads as part of
// the content above it — which is exactly what a viewer reported: "subtitle is too close to the content".
// Shrinking the type closed that gap by starting the block lower, but it also dropped the caption to 3.4% of
// frame height, under the 5.2% floor that keeps a 1080p film readable in a phone-sized window. Both are fixed
// by paying for the gap out of the BAND instead of out of the type.
export const CAPTION_SIZE_FRAC = 0.042;   // caption type as a fraction of min(W,H) — 45px at 1080
// 0.052 (56px) was this tier's own number and an OUTLIER: the html tier had already deliberated its
// way down to 0.040, with the reason written beside it — "captions are a reading aid, not a headline;
// they should sit quietly". The two tiers were 30% apart on the same decision, and the louder one was
// the one nobody had revisited. Reported by a viewer as simply too large. Everything downstream is
// derived: the reserved band falls with it (227px -> 190px at 16:9), which hands the shots back the
// space rather than taking any away, and scripts/_caption_band.py parses this value so every Python
// gate follows without a second edit.
export const CAPTION_LINES = 2;           // the band must hold a two-line caption without touching content
export const CAPTION_LEAD = 1.26;
export const CAPTION_LEAD_CJK = 1.7;      // CJK needs more leading; the band is sized on the LATIN
                                          // lead and the caption fits itself to the band (Film.tsx)
export const CAPTION_MARGIN_FRAC = 0.037; // the block's own bottom margin
export const CAPTION_GAP_FRAC = 0.042;    // clear air between the content zone and the caption block
// (The old flat `CAPTION_BAND = 150` export is gone. It had no importers left and sat in the one file every
// register author reads before deciding where their content ends — the literal that produced the whole
// class of "cleared a 150px band, sat inside the grown one" defects, still on offer.)
export const CONTENT_TOP = TITLE_BAND;  // top of the usable content zone
// ASPECT-AWARE caption band: a NARROW frame (portrait/square/4:5) wraps the caption to more lines, so it needs a
// TALLER reserved band. Shots + the Film should reserve `captionBand(W,H)`, not the fixed CAPTION_BAND, so content
// clears the caption at every aspect. `contentBottom(W,H)` is the bottom of the usable content zone.
// The line count the band reserves for. A NARROW frame wraps the same sentence to more lines, so it
// reserves one extra. Exported because `maxCameraPush` below has to subtract the SAME block: it used
// CAPTION_LINES flat while the band reserved one more, so at 9:16 it believed there was 2.6x the headroom
// there is (12.1% against a true 4.7%) and would have let an authored camera push content onto the
// subtitle. Two places deriving the same quantity from the same fractions and disagreeing on the count is
// the shape this file exists to prevent.
export const CAPTION_NARROW_W = 1400;   // below this the caption wraps to one more line
export const captionLines = (W: number) => CAPTION_LINES + (W < CAPTION_NARROW_W ? 1 : 0);
export const captionBlockH = (W: number, H: number) =>
  Math.min(W, H) * (CAPTION_SIZE_FRAC * CAPTION_LEAD * captionLines(W) + CAPTION_MARGIN_FRAC);

export const captionBand = (W: number, H: number) =>
  Math.round(captionBlockH(W, H) + Math.min(W, H) * CAPTION_GAP_FRAC);
export const contentBottom = (W: number, H: number) => H - captionBand(W, H);

/**
 * The smallest bottom inset a shot's own closing line may use — its floor, not its position.
 *
 * WHY THIS EXISTS. Swept at the settled frame, 32 of 152 registers set copy INSIDE the strip the renderer
 * reserves for the burned caption: 'All of it, in hand', 'built, piece by piece', 'soft power, in motion' —
 * taglines the caption then draws straight through. Exactly ONE of them used `contentBottom`. The rest wrote
 * a number: `bottom: 96`, `bottom: H * 0.12`, `bottom: 150`. Every one of those numbers is smaller than the
 * 227px band at 1080, and none of them is wrong in a way its author could see, because the caption is burned
 * later by a different program.
 *
 * `bottomInset(W, H, wanted)` keeps the author's intent when it already clears the band and raises it when it
 * does not, so the fix is one call rather than a re-derivation — and it holds at aspects the number was never
 * checked against, where the band is a different size entirely.
 *
 * ONE TRAP, learned the expensive way: Remotion's `AbsoluteFill` sets `height: '100%'` alongside its four
 * insets, so a `bottom` passed to it is silently ignored — the box stays full height and a passed `top` only
 * pushes it DOWN. Constraining an AbsoluteFill means setting `height`. The symptom is a re-measurement
 * identical to the pixel, which is what a change having no effect looks like.
 */
export const BOTTOM_GAP_FRAC = 0.02;
export const bottomInset = (W: number, H: number, wanted = 0) =>
  Math.max(wanted, captionBand(W, H) + Math.round(Math.min(W, H) * BOTTOM_GAP_FRAC));

/**
 * The lowest BASELINE an `<svg><text>` may sit on — `bottomInset`'s counterpart for SVG.
 *
 * Half this library's diagram registers hang a line of explanation under the figure at an authored `y` like
 * `H * 0.84` or `oy + L * 0.5 + 40`. Those are all fine numbers for the picture and all below the caption
 * band, because the band did not exist in the author's head — it is applied later, by the renderer. Wrapped
 * in `Math.min(authored, bottomTextY(W, H))` the relationship survives wherever it fits and yields where it
 * does not. The offset is a descender's worth of room, not a guess: a baseline exactly on the boundary puts
 * the glyph tails inside it.
 */
/**
 * How much INK a `line-height: 1` text block actually occupies, from the top of its box to the bottom of
 * its deepest glyph.
 *
 * A 1em line box is SMALLER than the face's own ascent+descent, so with `line-height: 1` the glyphs hang
 * BELOW the box: the half-leading is `(1 - (asc + desc)) / 2`, negative, so the ink runs to
 * `(1 + asc + desc) / 2` em below the box top. That gap is why "the box ends above the band" and "the type
 * is out of the band" are different statements, and the registers that place a closing line with `top:`
 * were all clamping — where they clamped at all — against the box.
 *
 * THE FACTOR IS THE WORST BUNDLED FACE, AND IT HAS TO BE. The first version of this carried 1.13, measured
 * off textSafe's report for ONE label in ONE typeface (Space Grotesk, which is 1.138). Eight of the
 * fourteen bundled faces are above that — Baloo 2 is 1.301, Bodoni Moda 1.262, and BOTH Chinese faces are
 * ~1.22, so every CJK film was under-reserved by ~9% of its type size at the exact boundary this exists to
 * protect. And a register cannot pick per-face: the DNA supplies the family through `var(--f-display)`, so
 * the call site does not know what it will be set in. The only sound bound is the maximum over every face
 * a DNA stack can name. `tests/test_remotion.py` reads the font files and fails if a newly bundled face
 * exceeds it — the numbers come from each face's metrics (OS/2 typo when USE_TYPO_METRICS is set, hhea
 * otherwise), which is what the browser lays out with.
 *
 * Over-reserving costs a few pixels of clearance; under-reserving ships type under the subtitle.
 *
 * `bottomInset` is still the better tool where an element can be anchored from the bottom — then the
 * browser measures the type and nothing here has to estimate it. This is for the ones that cannot.
 */
export const INK_BLOCK_FACTOR = 1.31;
export const inkBlockH = (fontPx: number, lines = 1) =>
  Math.ceil(fontPx * (lines - 1 + INK_BLOCK_FACTOR));

/**
 * Can this text be READ in a box this size? — the honest alternative to a fixed width floor.
 *
 * WHY IT EXISTS. A register whose boxes change width cannot gate its labels on a constant: a floor is a
 * floor for one string at one size and nothing else. `SameStuffChanged` gated its cell names on
 * `w > U * 0.05`, and a 70px sliver mid-split kept its seven-glyph name — which the browser then set one
 * glyph per line, a vertical column of characters that reads as decoration rather than as a word. Both
 * settled frames were fine; only the frames in between were wrong, which is how it survived being looked at.
 *
 * TWO GLYPHS IS THE WIDTH FLOOR, and it is asked of THIS string's own first glyphs through `wrapLines` —
 * the same model, the same kinsoku — so full-width CJK and half-width Latin each get their own answer
 * instead of sharing a guess. Below two glyphs across, every line break is forced and there is no setting
 * of the text that reads. The height is then checked against the wrapped block, so a box that is wide
 * enough and too short is refused as well.
 *
 * Returning false means DRAW NOTHING THERE. A label that does not fit is not a label made smaller; the
 * caller decides what to do with the room, and this only answers the question it was asked.
 */
export const fitsBox = (
  text: string, fontPx: number, boxW: number, boxH: number, padX = 0, padY = 0,
): boolean => {
  // TRIMMED, AND A BLANK IS NOT A LABEL. `'   '` is a truthy string that wraps to one line and fits any
  // box, so the first version answered TRUE for it and the caller drew a padded ground with nothing on it —
  // on `SameStuffChanged`, a solid rectangle where a name should be. Whitespace is also what the browser
  // collapses at the ends, so measuring the trimmed text is the more accurate question as well as the
  // safer one.
  const s = String(text ?? '').trim();
  const inner = boxW - padX;
  if (!s || !(fontPx > 0) || inner <= 0) return false;
  if (wrapLines([...s].slice(0, 2).join(''), fontPx, inner) > 1) return false;
  return inkBlockH(fontPx, wrapLines(s, fontPx, inner)) <= boxH - padY;
};

export const bottomTextY = (W: number, H: number) =>
  contentBottom(W, H) - Math.round(Math.min(W, H) * 0.012);

/**
 * The largest font size at which `text` fits the frame's WIDTH — the missing constraint behind most of the
 * portrait findings.
 *
 * A display title sized `900 210px` fits 'WORKBUDDY' at 1920 wide and loses 107px off EACH edge at 1080,
 * because the size was chosen for the text and the frame it was authored on, and nothing related it to the
 * width it actually ships at. Swept at 9:16, twenty-three registers were cutting type this way.
 *
 * Estimated, not measured — a DOM measure cannot run at style-computation time — so the advance is a
 * deliberate overestimate (better a hair small than clipped), and CJK counts at full width: geometry that
 * assumes Latin advances is how a Chinese deck once measured 46% short (the slide-maker's CJK bug, re-learned
 * here on purpose). Tracking is part of width: a 0.42em-tracked tagline is half tracking by length.
 */
const CJK_CH = /[\u2e80-\u9fff\uf900-\ufaff\uff01-\uff60\u3000-\u303f]/;

/**
 * The Han advance the FITTERS below use, in ems. The TYPE ADVANCE section at the foot of this file carries
 * the measured pair for PREDICTING a wrap (0.995, rounded to CJK_ADVANCE); a fitter wants a little margin
 * over the measurement, because under-measuring clips the text and over-measuring only sets it slightly
 * smaller. Kept apart from CJK_ADVANCE on purpose — same fact, different tolerance.
 */
export const CJK_FIT_ADVANCE = 1.05;

/**
 * The advance pair a MONOSPACE caller hands the fitters, because a Han glyph is TWO CELLS there.
 *
 * The advance is a property of the FACE, not of the character, and every fitter here had one number for
 * both: 1.05, the proportional answer. In a monospace face a Han glyph occupies two cells — 1.2em at a
 * 0.6em cell, 14% more — so every Chinese terminal string came out under-measured. TermGitLog ran a commit
 * message 345px off the frame, TensionScale centred a note that was 68px too wide on BOTH sides, and
 * BlueprintGrid clipped a spec by 288px. The ×2 lives here once: no register writes 1.2.
 */
export const monoFit = (cell = 0.6) => ({adv: cell, cjk: cell * 2});

/** How many MONOSPACE CELLS a string occupies. A Han glyph is FULL-WIDTH — two cells — so counting
 *  characters under-reports a Chinese line by half, and a terminal register that sizes itself from a
 *  character count then picks a size that runs the line off the frame (TermTree: 2086px past the right
 *  edge). Exported because three terminal registers ask the same question. */
export const monoCells = (text: string): number =>
  [...String(text ?? '')].reduce((n, ch) => n + (CJK_CH.test(ch) ? 2 : 1), 0);

/** `text` cut to fit `cells` monospace columns, with an ellipsis when it was cut.
 *
 *  A terminal truncates — `ls` does, `git log --oneline` does — so a listing whose note is longer than its
 *  column is not a layout emergency, it is the form. What IS an emergency is sizing the whole tree down
 *  until one long note fits: a 35-glyph Chinese note drove TermTree's type to 18px and still ran 20px off
 *  the frame, because the line cannot wrap (`white-space: pre`) and the fit has nothing left to give. A
 *  bounded column makes the size solvable for any input instead of only for short ones. */
export const clipCells = (text: string, cells: number): string => {
  const chars = [...String(text ?? '')];
  let used = 0;
  for (let i = 0; i < chars.length; i++) {
    const w = CJK_CH.test(chars[i]) ? 2 : 1;
    if (used + w > cells) return chars.slice(0, i).join('') + '…';
    used += w;
  }
  return chars.join('');
};

/**
 * How wide one line of `text` runs at `px`, in the SAME advance model the fitters use.
 *
 * Exported because a caller that needs a width — how much of the frame to reserve for a column of labels —
 * would otherwise restate the model, and a second copy of an estimate is a second answer. Reserving a
 * fixed fraction instead is what pushed PortRail's standing rail into the left quarter of a square frame:
 * a 324px column held for labels that ran 140px.
 */
export const textWidthPx = (
  text: string, px: number, opts: {adv?: number; track?: number; cjk?: number} = {},
): number => {
  const {adv = 0.72, track = 0, cjk = CJK_FIT_ADVANCE} = opts;
  const units = [...String(text || ' ')].reduce((n, ch) => n + (CJK_CH.test(ch) ? cjk : adv) + track, 0);
  return units * px;
};

export const fitTextPx = (
  text: string, W: number, base: number,
  opts: {usable?: number; adv?: number; track?: number; cjk?: number} = {},
): number => {
  // The DEFAULT advance is deliberately generous, and callers should rarely lower it: the face that
  // actually renders is the DNA's display font, not whatever the register's fallback stack names — a call
  // tuned to condensed Antonio (0.52) shipped Space Grotesk and still clipped 85px per edge.
  const {usable = 0.9, adv = 0.72, track = 0, cjk = CJK_FIT_ADVANCE} = opts;
  const wLen = textWidthPx(text, 1, {adv, track, cjk});
  return Math.max(12, Math.min(base, Math.floor((W * usable) / Math.max(0.1, wLen))));
};

/**
 * The largest size at which a WRAPPED block still fits a W×H box — the two-dimensional `fitTextPx`.
 *
 * `fitTextPx` fits one line to a width, which is the wrong question for a headline: a feature headline is
 * MEANT to wrap, and what goes wrong is that it wraps one line too many and lands on whatever sits below.
 * `MagazineSpread` shipped exactly that on its own English demo copy — a three-line headline whose last
 * line sat on the standfirst — and the CJK repair fitted the Chinese path only, so the register was fixed
 * in the language it had been reported in and broken in the one it was written in.
 *
 * The line count is estimated from the same advance model `fitTextPx` uses, so both agree about how wide
 * a character is. `usable` carries the safety margin: Latin cannot break inside a word, so a line packs a
 * little less than the estimate says.
 */
/**
 * How many LINES `text` takes at `px` in a `width` measure — counted by breaking it, not by dividing.
 *
 * THE RATIO IS WRONG WHEREVER A GLYPH IS BIG RELATIVE TO THE MEASURE, and for CJK that is everywhere: a Han
 * glyph is a full em, so a 766px measure at 198px holds THREE of them, not 3.87. `ceil(totalWidth / width)`
 * counted eleven glyphs as three lines; the browser drew four, so the fit believed it fitted and the fourth
 * line went into the caption band. Measured on `KineticManifesto` at 1:1, 117px in. The ratio is only right
 * when the quantisation error is small — which is the Latin case it was written for.
 *
 * So the line is filled the way the browser fills it: CJK breaks between any two glyphs, Latin at the last
 * space before the overrun. A label is a handful of characters; walking them costs nothing.
 */
/**
 * Characters that may not BEGIN a line — the common half of CJK kinsoku shori (禁則処理).
 *
 * `wrapLines` breaks CJK between any two glyphs, which is what the script allows and NOT what a browser
 * does: a line may not open with a closing mark, so the browser carries the preceding glyph down with it
 * and the block takes one line more than a naive per-glyph fill predicts. Measured on `RealVersus` at 4:5,
 * whose label carries four such marks: the settle reserved four lines and ended 22px clear of the caption
 * band, and the rendered label took FIVE and closed 13px inside it — one line, to the half-pixel.
 *
 * So each glyph is glued to any closing marks that follow it and the pair is measured as one unbreakable
 * unit. That can only ever predict the same number of lines or more, never fewer, which is the safe
 * direction for anything sizing a reserve from it.
 */
const NO_LINE_START = /[、。，．：；！？）〕］｝〉》」』】〙〗〟'"｠»ー―‐–—～〜?!,.:;]/;

/**
 * Characters that may not END a line — the other half of the same rule, and it was left out for a session
 * because it could not then be verified.
 *
 * It can now. Measured in the real browser, on the real bundled face (Noto Sans SC, 30px, a box exactly five
 * glyphs wide), by asking Chrome where each glyph actually landed:
 *
 *     一二三四五六七八九      -> 2 lines:  一二三四五 / 六七八九
 *     一二三四「五六七八九     -> 3 lines:  一二三四 / 「五六七八 / 九
 *
 * The same nine glyphs take one line MORE when an opening bracket falls where a line would have ended: the
 * browser refuses to leave it there and carries it down onto the next line, and the glyph count no longer
 * fits. Straight ASCII quotes are deliberately NOT here — measured on the same page, `一二三四"五六七"八九`
 * breaks mid-run, because a straight quote can open or close and the rule does not apply to it.
 *
 * So an opening mark is glued to the glyph AFTER it, the mirror of the closing rule above. Like that one it
 * can only ever predict the same number of lines or more, never fewer, which is the safe direction for
 * anything sizing a reserve from it.
 */
const NO_LINE_END = /[（〔［｛〈《「『【〖〘｟«‘“([{]/;

export const wrapLines = (
  text: string, px: number, width: number, opts: {adv?: number; track?: number; cjk?: number} = {},
): number => {
  const {adv = 0.72, track = 0, cjk = CJK_FIT_ADVANCE} = opts;
  const w = Math.max(1, width);
  const chars = [...String(text ?? '')];
  if (!chars.length) return 1;
  // KINSOKU, BOTH HALVES. A closing mark is glued to the glyph BEFORE it and an opening mark to the glyph
  // AFTER it, so each pair breaks as one unit — see NO_LINE_START / NO_LINE_END. Checked against the
  // browser's own breaks on the real face: the model now reproduces its line CONTENTS, not only its count.
  const units: string[] = [];
  let open = '';                                   // opening marks waiting for the glyph they open
  for (const ch of chars) {
    if (NO_LINE_END.test(ch)) { open += ch; continue; }
    if (open) { units.push(open + ch); open = ''; }
    else if (units.length && NO_LINE_START.test(ch)) units[units.length - 1] += ch;
    else units.push(ch);
  }
  // A string that ENDS on an opening mark has nothing to glue it to; it still has to be measured.
  if (open) units.push(open);
  // AND KINSOKU YIELDS TO OVERFLOW, which is what a browser does and what this function did not. A glued
  // pair is an unbreakable unit only while the box can hold it: in a column narrower than two glyphs the
  // browser has no legal break left and breaks inside the pair anyway. Measured before this line existed,
  // on the fixture strings at px=18 in a 36px column: gluing turned 25 predicted lines into 24 — the glued
  // pair overflowed an empty line and was counted as ONE. Predicting FEWER lines is the one direction a
  // reserve must never be wrong in, and the comment above this block claimed it could not happen.
  const room = w;
  for (let i = units.length - 1; i >= 0; i--) {
    const u = units[i];
    if ([...u].length < 2) continue;
    const uw = [...u].reduce((n, c) => n + (CJK_CH.test(c) ? cjk : adv) * px + track * px, 0);
    if (uw > room) units.splice(i, 1, ...[...u]);
  }
  let lines = 1, used = 0, lastBreak = -1, sinceBreak = 0;
  for (const unit of units) {
    const ch = unit[0];
    const cw = [...unit].reduce((n, c) => n + (CJK_CH.test(c) ? cjk : adv) * px + track * px, 0);
    if (used + cw > w && used > 0) {
      if (CJK_CH.test(ch) || lastBreak < 0) {          // break here: CJK breaks anywhere, and so does a
        lines += 1; used = cw; lastBreak = -1; sinceBreak = 0;   // Latin run with no space to fall back to
      } else {
        lines += 1; used = sinceBreak + cw; lastBreak = -1; sinceBreak = 0;
      }
    } else {
      used += cw;
      sinceBreak += cw;
    }
    if (unit === ' ') { lastBreak = 1; sinceBreak = 0; }
  }
  return lines;
};

export const fitBlockPx = (
  text: string, W: number, H: number, base: number,
  opts: {usable?: number; adv?: number; track?: number; cjk?: number; leading?: number; min?: number} = {},
): number => {
  const {usable = 0.92, adv = 0.72, track = 0, cjk = CJK_FIT_ADVANCE, leading: lh = 1.1, min = 12} = opts;
  const width = Math.max(1, W * usable);
  for (let px = Math.floor(base); px >= min; px--) {
    const lines = wrapLines(text, px, width, {adv, track, cjk});
    if (lines * px * lh <= H) return px;
  }
  return min;
};

// The largest camera push that CANNOT drive a shot's lowest content into the caption band.
//
// A scene camera scales the shot about the centre of the content zone, so the zone's bottom edge travels
// down by half the zone's height times the push. The band holds the caption block plus a gap of clear air;
// as long as that travel stays inside the gap, the burned subtitle never has shot content sitting on it.
// Derived rather than chosen, so a change to the caption's type size moves this with it instead of leaving
// a stale constant that used to be safe.
// `driftExtra` is the largest EXTRA scale the film-wide ambient drift adds on top of this. The two camera
// layers multiply, and the per-beat cap could not see the other one: with the drift at full amplitude a
// per-beat push of 8% already drives the lowest content 51px down into a 46px gap. Measured, not guessed.
// The drift scales about the FRAME centre, so its travel is H/2 x driftExtra; the beat scales about the
// content zone, so its travel is zoneH/2 x amount. The beat gets whatever the drift has not already spent.
// `driftTranslate` is the film-wide drift's downward y-amplitude in px (Film.DRIFT_MAX_TRANSLATE_Y scaled
// by the drift amount). It spends the same headroom the scale does and was simply not counted.
/** The vertical slack, in px, between the reserved caption band and the block the caption actually needs —
 *  the room a camera has to move content DOWN before it starts pushing it under the burned subtitle.
 *
 *  `maxCameraPush` already derives a zoom cap from this number; a PAN needed the same protection and did not
 *  have it. Measured on a delivered film: a beat panned downward put its register's own title on top of the
 *  caption, both unreadable. A pan's overscan budget guarantees no frame EDGE is revealed; it says nothing
 *  about the one band that is reserved for something else. */
export const captionSlackPx = (W: number, H: number, driftExtra = 0, driftTranslate = 0) =>
  Math.max(0, Math.max(0, captionBand(W, H) - captionBlockH(W, H))
              - (H / 2) * Math.max(0, driftExtra) - Math.max(0, driftTranslate));

export const maxCameraPush = (W: number, H: number, driftExtra = 0, driftTranslate = 0) => {
  const band = captionBand(W, H);
  const gap = Math.max(0, band - captionBlockH(W, H))
            - (H / 2) * Math.max(0, driftExtra) - Math.max(0, driftTranslate);
  const zoneH = Math.max(1, H - CONTENT_TOP - band);
  return Math.max(0, (gap / (zoneH / 2)) * 0.75);   // 3/4 of the headroom — the last quarter is not worth spending
};

/**
 * The font size at which a MONOSPACE block fills its box — the "small" half of the density diagnosis.
 *
 * Ink and footprint separate the two ways a frame is empty, and they need opposite fixes: measured on the
 * registers a delivered film was starved by, TermTree spans 9.0% of the frame, QuadSplit 11.3%,
 * TimelineTravel 14.4% — composed at a ninth of the picture, with a type size written as a literal that does
 * not move when the frame does. A terminal tree set at 40px on a 1920-wide frame is not restraint, it is a
 * size chosen once at one resolution.
 *
 * Monospace is exactly solvable, which is why this is a helper and not a guess: every glyph advances the
 * same fraction of the size (~0.6 for the JetBrains/ui-monospace stack this runtime uses) and the line box
 * is the leading. So the size that fills a box is a division, not a measurement pass — deterministic, and
 * therefore frame-seekable like everything else here.
 *
 * `fill` leaves air on purpose: 1.0 would put the block against the box's edges.
 */
export const MONO_ADVANCE = 0.6;

/** The box a shot may compose in: below the title band, above the caption band. The exclusion constants
 *  already exist as CONTENT_TOP and captionBand(); this is the same two numbers stated as the POSITIVE
 *  answer, because "where may I not be" is what every helper here answered and it is not what a register
 *  composing to fill needs to ask. */
export const contentZoneBox = (W: number, H: number): {width: number; height: number; top: number} => ({
  width: W, top: CONTENT_TOP, height: Math.max(1, H - CONTENT_TOP - captionBand(W, H)),
});

export function fitMono(
  chars: number, lines: number, box: {width: number; height: number},
  {fill = 0.86, lead = 1.6, min = 18, max = 200}: {fill?: number; lead?: number; min?: number; max?: number} = {},
): number {
  const c = Math.max(1, chars), l = Math.max(1, lines);
  const byWidth = (box.width * fill) / (c * MONO_ADVANCE);
  const byHeight = (box.height * fill) / (l * lead);
  return Math.max(min, Math.min(max, Math.floor(Math.min(byWidth, byHeight))));
}

// The shared title style — use for a shot's top title so every shot's header reads identically (position,
// size, weight, tracking). Spread it onto the title <div>; override `color`/`opacity` as needed.
export const titleStyle: React.CSSProperties = {
  position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
  color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
};

// fitContentSquare — the correct box for a hero IMAGE/panel: a square CENTERED in the content zone (below the
// title, above the caption band), never the whole frame. Pass `bottomReserve` when the shot draws its OWN labels
// UNDER the image (ticks, a caption line) so the square shrinks to leave room and those labels stay out of the
// caption band. hFrac/wFrac cap the size (leave hFrac<1 for breathing room around a big image).
export function fitContentSquare(
  W: number, H: number,
  {hFrac = 0.86, wFrac = 0.5, bottomReserve = 0}: {hFrac?: number; wFrac?: number; bottomReserve?: number} = {},
): {S: number; left: number; top: number} {
  const top0 = CONTENT_TOP;
  const bottom0 = H - captionBand(W, H) - bottomReserve;
  const zoneH = Math.max(1, bottom0 - top0);
  // On a PORTRAIT frame the caller's landscape wFrac (often ~0.44) would leave a tiny square in a wide-open
  // column — boost it so a hero image fills the portrait width, while landscape keeps the caller's value.
  const wf = W < H ? Math.max(wFrac, 0.9) : wFrac;
  const S = Math.min(zoneH * hFrac, W * wf);
  const top = top0 + (zoneH - S) / 2;          // centered in the content zone → a balanced gap above + below
  const left = (W - S) / 2;
  return {S, left, top};
}

/** Where a label goes beside a point, WITHOUT leaving the box it belongs to.
 *
 * The recurring bug this exists for: a label is placed by `mark.x > 0.5 ? right : left` and given a fixed
 * width. That reads the point's HALF, not the room actually left, so any point near an edge gets a label
 * pushed straight out of its container — two city names crossed a map plate's border in a delivered film,
 * and a flap board's rows ran off the frame the same way. No raster check can catch it: text crossing a
 * DRAWN border and a full-bleed field reaching the frame edge are the same pixels.
 *
 * So the fix is at the source. Pass the point, the box it must stay inside, and the label's width; get back
 * a left edge that is clamped into the box and the side the text should align to.
 *
 * @param x     the point the label annotates, in px
 * @param x0,x1 the box the label must stay inside, in px
 * @param labelW the label's width in px
 * @param gap   clearance between the point and the label
 */
export function placeLabel(x: number, x0: number, x1: number, labelW: number, gap: number):
  {left: number; align: 'left' | 'right'} {
  const roomRight = (x1 - x) - gap;
  // side by ROOM, not by which half of the box the point sits in
  const align: 'left' | 'right' = (roomRight >= labelW || (x - x0) < labelW) ? 'left' : 'right';
  const raw = align === 'left' ? x + gap : x - gap - labelW;
  return {left: Math.max(x0, Math.min(raw, x1 - labelW)), align};
}

// ── TYPE ADVANCE ────────────────────────────────────────────────────────────────────────────────────────
// How wide a character is, as a fraction of the type size. Measured, not guessed: IBM Plex Sans averages
// 0.452-0.478 em on real prose so 0.52 is conservative; JetBrains Mono measures 0.588 on the same sentence,
// so a mono face needs 0.62 or every fit-estimate under-counts and the text overflows what it was promised.
// CJK measures 0.995.
//
// It lives HERE because two files were predicting the same wrap with different numbers. Film.tsx had the
// measured pair; PhotoPlate's callouts had a third value, 0.54, applied to a MONOSPACE chip — so the chip's
// own layout pass predicted two lines where three were drawn, and the third line was cut off by the box
// height derived from the same count. A duplicated constant is a bug with a delay.
export const MONO_FACE = /mono|code|consol|courier|menlo|iosevka/i;
export const CJK_ADVANCE = 1.0;
export const latinAdvance = (fontStack?: string, uniform?: boolean) =>
  (uniform || (fontStack && MONO_FACE.test(fontStack))) ? 0.62 : 0.52;
/** The same question for a Han glyph, and it has the same answer shape: a property of the FACE. In a
 *  proportional face it is CJK_ADVANCE; in a MONOSPACE one it is two cells. `PhotoPlate` predicted the
 *  wrap of a mono chip with the proportional 1.0 and under-counted its Chinese lines by a fifth. Callers
 *  that already ask `latinAdvance(x)` ask `cjkAdvance(x)` with the same argument. */
export const cjkAdvance = (fontStack?: string, uniform?: boolean) =>
  (uniform || (fontStack && MONO_FACE.test(fontStack))) ? 2 * latinAdvance(fontStack, uniform) : CJK_ADVANCE;
