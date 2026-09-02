// LIGHT — the beat's GROUND, resolved per frame instead of once per film.
//
// WHY THIS FILE EXISTS. A film had exactly ONE ground and no beat could change it. Film.tsx resolved
// `theme?.bg ?? dna?.bg ?? '#05060a'` once for the whole TransitionSeries, and every one of the eight DNA
// presets grounds near-black — the brightest is editorial at Y=0.0053 (terminal 0.0033, neutral 0.0018,
// product 0.0021, blueprint 0.0048, cinematic 0.0023, data 0.0046, retro 0.0046). Measured over the 149
// registers rendered as VIDEO (scripts/register_energy.py, remotion/register_energy.json), 143 of 149 sit
// under the 0.135 luminance-range floor and the library median range is 0.013 against Figma's 0.903. A
// 30-beat film painted one identical near-black ground thirty times. `bgLum` looked like the escape hatch
// and is not one: it is a HINT read by the caption-ink pick and the seam guard and it never repaints a
// pixel, so an author who wrote `bgLum:'light'` still got a dark frame.
//
// THE LEVER, MEASURED. 148 of the 149 registers paint their ground from the single token `bg`
// (shotLuma's DNA_GROUND_TOKEN), 143 read the ground tokens directly and 149 call useDNA(). So handing a
// beat a different SET OF GROUND TOKENS — by providing DesignDNAContext inside the Sequence rather than
// outside the whole series — re-grounds the entire library with zero per-register edits. This file decides
// what those tokens are.
//
// EXPOSURE ONLY, NEVER HUE. A light key is not an inverted palette. The accents keep their hue exactly:
// shading toward black is a linear scale of r:g:b, which preserves hue and (while L<0.5) HSL saturation
// too, so only the exposure moves. Hue is the film's identity; a beat changes the light in the room, not
// the room. The one thing that is re-picked rather than kept is which INK reads on the new ground, and
// that is picked by measured contrast from the film's OWN two inks. On a ground far from anything the film
// was designed for, neither of them reads — a clay field gives the terminal preset 3.77:1 and 3.55:1 — so
// the winner is then moved along its own black↔white axis until it clears the body-text floor. Its HUE is
// still one the film declared; only its exposure is not.
//
// THE SECOND-ORDER DEFECT THIS FIXES. SHOT_LUMA counts 112 dark / 35 light / 2 mid, and every one of those
// 35 light registers grounds on `bg`, so applying a DNA — which every delivered film does — deleted the
// library's entire light half: SwissEditorial, whose identity is black type on cream, rendered
// white-on-near-black under dna=product (measured modal ground 7/255 over 86% of the frame). A light-key
// ground is derived from the film's own `fg`, so those 35 get their authored identity back without any of
// them being edited.

import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {mix, tint, shade, DesignDNAContext, type DesignDNA, type GroundSpec} from './dna';
import {lumValue, groundFollows, isRegisteredShot} from './shotLuma';
import {SEAM_FRAMES, REDUCED_MOTION_T, ReducedMotionContext, clamp01} from './motion';

/** The exposure boundary: a ground at or above this relative luminance is a LIGHT key. 0.35 sits above the
 *  brightest ground the eight presets can name (0.0053) by two orders of magnitude and below any paper, so
 *  no existing film moves across it. ONE definition with ONE reader — `keyFromY` — so a margin around the
 *  boundary (the key flip's, below) is expressed by moving the luminance rather than by a second copy of
 *  the number that would have to be kept in step with this one. */
export const LIGHT_KEY_Y = 0.35;

/** The burned caption's two inks. They lived as literals inside Film.tsx's CaptionTrack; a per-beat ground
 *  gave them a second caller (the resolved-ground pick below), which is exactly how the four disagreeing
 *  copies of the caption band happened. One definition, imported by both. */
export const CAPTION_INK_DARK = '#141414';
export const CAPTION_INK_LIGHT = '#ffffff';

// An accent is drawn as rules, fills and display type ON the beat's ground. 3.0 is WCAG's floor for
// non-text contrast (1.4.11) and for large text — below it a hairline in the accent simply disappears,
// which is what a mint-green terminal accent does on paper (measured contrast 1.41).
export const ACCENT_CONTRAST_MIN = 3.0;
// The INK is body copy, so it answers to WCAG 1.4.3 AA (4.5:1) rather than the graphics floor. Exported
// with the others because the tests measure the RESOLVED colours against these numbers, and a floor
// restated in the test is a floor that can be quietly lowered in the code.
export const INK_CONTRAST_MIN = 4.5;
// `dim` is metadata — a kicker, a unit, a timestamp. It is smaller than the ink and it is allowed to
// recede, but it is still meant to be READ, and the library's own eight presets put it at a median 2.52:1
// on their own grounds. 2.4 is the floor under that population; below it the metadata is decoration.
export const DIM_CONTRAST_MIN = 2.4;

// How far each derived token sits along the ground→ink axis. MEASURED off the eight presets rather than
// chosen: projecting every preset's own dim/surface/surfaceBorder/line onto its own bg→fg axis gives
// medians of 0.589 / 0.044 / 0.178 / 0.116 (spread per token: dim .48-.63, surface .02-.10, border
// .12-.25, line .08-.17). So a derived ground places its furniture exactly where this library already
// places it, and a light key and a chroma key are the same design decision at two exposures rather than
// two hand-tuned palettes that can drift apart. Hand-picking these put `dim` at 0.42 — dimmer than the
// library's own convention, which is precisely the metadata-you-cannot-read failure on a paper ground.
const TOKEN_MIX = {dim: 0.589, surface: 0.044, surfaceBorder: 0.178, line: 0.116};

/** WCAG contrast ratio between two relative luminances. */
const contrast = (a: number, b: number): number => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

/** ONE DEFINITION OF "A HEX GROUND", returning its CANONICAL six-digit form.
 *
 *  There were two, and they disagreed. This file accepted `/^#[0-9a-fA-F]{3,8}$/` and passed the string
 *  through verbatim; Film.tsx's caption code tested `/^#[0-9a-fA-F]{6}$/` and, when that failed, drew the
 *  caption's separation shadow in a colour computed from the FILM's DNA instead of the beat's. So a beat
 *  grounded `#fff` painted a white frame and then shadowed its dark caption in the film's near-black —
 *  measured at 77% more mid-grey fringe pixels than the identical `#ffffff` beat, which is the white-halo
 *  bug the caption comment forbids, inverted. Canonicalising here means the film tier never has to decide
 *  what a hex is: it gets six digits it can concatenate an alpha onto.
 *
 *  ALPHA IS NOT A GROUND, and is refused rather than silently dropped (see `groundHex`): a translucent
 *  ground composites over whatever happens to be behind it, so the luminance every consumer derives from
 *  it — caption ink, seam guard, exposure key — would be a number for a colour that is not on the frame. */
export const hexGround = (color: unknown): string | null => {
  if (typeof color !== 'string') return null;
  // The '#' is REQUIRED, not stripped. Accepting a bare six-character run made every ground NAME spelled
  // from hex letters silently become a colour: `ground: 'facade'` resolved to #facade and `'decade'` to
  // #decade, so a typo painted a plausible frame instead of failing. A name and a colour must not be the
  // same shape.
  const t = color.trim();
  if (!/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(t)) return null;
  const m = t.slice(1);
  return '#' + (m.length === 3 ? m.split('').map((c) => c + c).join('') : m).toLowerCase();
};

/** A ground's colour and luminance, canonical, or a throw. Used everywhere the value is REQUIRED to be
 *  resolvable — a declared ground, whose whole job is to be a luminance. A silently-unresolvable ground
 *  would put the caption ink and the seam guard back to guessing, which is the bug class this file exists
 *  to end. */
const groundHex = (color: unknown, what: string): {bg: string; y: number} => {
  const bg = hexGround(color);
  if (bg === null) {
    const alpha = typeof color === 'string' && /^#?([0-9a-fA-F]{4}|[0-9a-fA-F]{8})$/.test(color.trim());
    throw new Error(alpha
      ? `ground ${what} is TRANSLUCENT (${String(color)}) — a ground must be opaque. Its luminance is what ` +
        'the caption ink, the seam luminance guard and the exposure key are all derived from, and an alpha ' +
        'hex composites over whatever is behind it, so that number would describe a colour nothing paints. ' +
        'Drop the alpha, or name the colour you actually want on the frame.'
      : `ground ${what} must be a hex colour — #rgb or #rrggbb (got ${JSON.stringify(color)}). The caption ` +
        'ink, the seam luminance guard and the exposure key are all derived from it, so an unresolvable ' +
        'ground would silently fall back to guessing.');
  }
  return {bg, y: lumValue(bg) as number};       // canonical by construction, so this cannot be null
};

/** A ground the runtime has fully resolved: every token a register reads, plus the two facts the film tier
 *  needs about it (which exposure key it is, and its measured luminance). */
export type ResolvedGround = {
  bg: string; bgGrad?: string; fg: string; dim: string; surface: string; surfaceBorder: string;
  line: string; accent: string; accent2: string; onAccent: string;
  key: 'dark' | 'light';
  y: number;                 // relative luminance of `bg` — what `key` is derived from, kept so callers
};                           // that need the NUMBER (seam gap, ramp crossing) do not re-parse the hex

/** The exposure key of a luminance. Written out once: it had four callers within a page of each other
 *  (every resolved ground, the ramp's per-frame result, and the DNA's own class), which is how the caption
 *  band ended up with four copies of itself in four files. */
export const keyFromY = (y: number): 'dark' | 'light' => (y > LIGHT_KEY_Y ? 'light' : 'dark');

/** Which exposure a DNA's own tokens describe — DERIVED from `bg`, never stored. A stored `key` field would
 *  be a second copy of a fact `bg` already states, and the two would eventually disagree. */
export const keyOf = (dna: DesignDNA): 'dark' | 'light' => keyFromY(lumValue(dna.bg) ?? 0);

/** The POLARITY a register should branch on — "am I drawing on light?" — so a shadow/glow decision is a
 *  read rather than a guess. Total: no DNA means no re-grounding, which is the dark library default. */
export const onLight = (dna: DesignDNA | null): boolean => !!dna && keyOf(dna) === 'light';

/** The pure ink that MEASURES more on this ground — white's relative luminance is 1 and black's is 0 by
 *  definition, so the comparison needs no lookup. Every exposure ladder walks toward this end, and every
 *  ladder therefore terminates: the worse case over all grounds is Y=0.179, where the better pure ink still
 *  measures 4.58:1, above every floor in this file. */
const purest = (groundY: number): string => (contrast(1, groundY) >= contrast(0, groundY) ? '#ffffff' : '#000000');

/** Move a colour's EXPOSURE until it clears `floor` on this ground, keeping its hue. Deterministic: a fixed
 *  24-step ladder, not a solve, so the answer is identical on every machine and every frame. Anything
 *  unparseable passes through, which is this codebase's house rule for colour helpers (see dna.tsx `mix`).
 *
 *  IT WALKS TOWARD THE MEASURED END, NOT THE NAMED ONE. This read `keyFromY(groundY)` and walked toward
 *  black on a "light" ground and white on a "dark" one — but the key boundary is 0.35 while the crossover
 *  between the two pure inks is at Y=0.179, so on any ground in between the ladder climbed toward the
 *  WEAKER ink and stopped at its own fallback. Measured on #999999 (Y=0.319): every accent landed on
 *  #ffffff at 2.85:1, under this file's own 3.0 floor, on a ground where black measures 7.4:1. */
const exposeTo = (c: string, groundY: number, floor: number): string => {
  const y = lumValue(c);
  if (y === null || contrast(y, groundY) >= floor) return c;
  const toward = purest(groundY);
  for (let i = 1; i <= 24; i++) {
    const out = mix(c, toward, i / 24);
    const oy = lumValue(out);
    if (oy !== null && contrast(oy, groundY) >= floor) return out;
  }
  return toward;   // a colour that cannot clear the floor at all becomes ink — visible beats in-palette
};
const expose = (c: string, groundY: number): string => exposeTo(c, groundY, ACCENT_CONTRAST_MIN);

/** Whichever of the film's own two inks reads better on this ground — verbatim when one of them reads, and
 *  EXPOSED toward the ground's own contrast end when neither does. Both candidates are colours the film
 *  already declared, and the exposure only moves that colour along its own black↔white axis, so a
 *  re-grounded beat still never introduces a HUE the film has not named.
 *
 *  Picking alone was not enough: on the chromatic end of the vocabulary NEITHER ink reaches 4.5:1 by itself
 *  — a clay ground (Y=0.142) gives the terminal preset 3.77:1 from its lighter ink and 3.55:1 from its
 *  darker one, and body copy at 3.7:1 is the "metadata you cannot read" failure one token over.
 *
 *  It exposes the ink that is ALREADY on the side the exposure walks toward. Exposing the higher-contrast
 *  one instead drags it across the ground's own luminance and out the far end: on a #737373 ground the
 *  film's near-black ink measured 4.09:1, lost to the floor, and walked all the way to #ffffff — legible,
 *  and no longer the film's ink at all. Exposing the LIGHT ink instead lands on #f7f8fb, four steps from
 *  where it started. */
const inkOn = (groundY: number, a: string, b: string): string => {
  const ya = lumValue(a) ?? 0, yb = lumValue(b) ?? 0;
  const ca = contrast(ya, groundY), cb = contrast(yb, groundY);
  if (Math.max(ca, cb) >= INK_CONTRAST_MIN) return ca >= cb ? a : b;
  return exposeTo((purest(groundY) === '#ffffff') === (ya >= yb) ? a : b, groundY, INK_CONTRAST_MIN);
};

/** `dim` placed where this library places it (TOKEN_MIX.dim), and SOLVED toward the ink when that place is
 *  unreadable. The fixed mix is a median off the eight presets, so it is right for a ground like theirs and
 *  wrong for a ground far from theirs: on the shipped `clay` preset it lands at 2.18:1 on terminal and
 *  2.37:1 on blueprint, under this file's own metadata floor — the same fixed-constant failure `expose`
 *  already solves for the accent, one token over. Deterministic ladder, first rung = TOKEN_MIX.dim, so a
 *  ground where the library's own placement already reads gets exactly that colour. */
const dimOn = (bg: string, ink: string, groundY: number): string => {
  for (let i = 0; i <= 24; i++) {
    const out = mix(bg, ink, TOKEN_MIX.dim + (1 - TOKEN_MIX.dim) * (i / 24));
    const y = lumValue(out);
    if (y === null || contrast(y, groundY) >= DIM_CONTRAST_MIN) return out;
  }
  return ink;
};

/** The DNA's OWN ground, verbatim. Declaring `key:'dark'` on a dark film must be the same pixels as
 *  declaring nothing at all — so this copies the tokens rather than deriving them. */
const nativeGround = (dna: DesignDNA): ResolvedGround => {
  const {bg, y} = groundHex(dna.bg, 'bg');
  return {bg, bgGrad: dna.bgGrad, fg: dna.fg, dim: dna.dim, surface: dna.surface,
    surfaceBorder: dna.surfaceBorder, line: dna.line, accent: dna.accent, accent2: dna.accent2,
    onAccent: dna.onAccent, key: keyFromY(y), y};
};

/** Every token a register reads, derived from one `bg`. Only `bg` is required: the film ALREADY owns the
 *  rest — its two inks and its two accents — so a ground is a one-word authoring decision ("this beat is on
 *  paper") and not a second palette to keep in sync with the first. Split from `groundFrom` because
 *  `flipKeySpec` has to ASK whether a candidate ground would be legible without that question throwing. */
const buildGround = (dna: DesignDNA, spec: GroundSpec): ResolvedGround => {
  const {bg, y} = groundHex(spec.bg, `"${spec.name ?? spec.bg}"`);
  // An AUTHORED ink is exposed like a derived one. Respecting it verbatim would make the one path an author
  // can reach the one path with no floor under it, which is the shape of every defect in this file.
  const ink = spec.fg ? exposeTo(spec.fg, y, INK_CONTRAST_MIN) : inkOn(y, dna.fg, dna.bg);
  const accent = expose(spec.accent ?? dna.accent, y);
  const accent2 = expose(dna.accent2, y);
  return {
    bg, bgGrad: spec.bgGrad, fg: ink,
    dim: dimOn(bg, ink, y),
    surface: mix(bg, ink, TOKEN_MIX.surface),
    surfaceBorder: mix(bg, ink, TOKEN_MIX.surfaceBorder),
    line: mix(bg, ink, TOKEN_MIX.line),
    accent, accent2,
    // The ink ON an accent fill has to be re-picked too: the accent may have been exposed for this ground,
    // and the DNA's own `onAccent` is dark in all eight presets, so a shaded accent could end up dark ink
    // on a dark chip. Picked from the film's own two inks, against the accent that will actually be painted.
    onAccent: inkOn(lumValue(accent) ?? 0, dna.fg, dna.bg),
    key: keyFromY(y), y,
  };
};

/** THE LEGIBILITY FLOORS, CHECKED ON EVERY GROUND THIS FILE HANDS OUT, not asserted for one path in one
 *  test. `key:'light'` had the floors under it and the identical `groundFrom` code path — the four named
 *  presets, every `#hex`, every index into the derived vocabulary — had none, and the shipped `clay` preset
 *  broke the very floor the light key was measured against (dim 2.18:1 on terminal). Returns the fault so
 *  `flipKeySpec` can use it as a ladder's stop condition rather than a crash.
 *
 *  It is a POSTCONDITION, not a filter: `inkOn`, `dimOn` and `expose` each solve their own floor, and every
 *  ladder terminates (see `purest`), so on parseable tokens this cannot fire. It fires when a token is not
 *  a colour at all — a DNA whose `fg` is a css name or a gradient — which is the one case no ladder can fix
 *  and the one this file must never resolve by guessing.
 *
 *  WHAT IT DOES NOT COVER: the frames INSIDE a ramp. `mixGround` interpolates two resolved grounds, and the
 *  crossing passes through mid luminances where nothing in either palette clears these floors — measured at
 *  1.0:1 for dim halfway across a #05060a→paper ramp. That is a transient the caption ink follows per frame
 *  (`captionInk` re-picks every frame), not a state any beat parks in, and asserting on it would refuse the
 *  one move this whole file exists to make. */
const legibilityFault = (g: ResolvedGround): string | null => {
  const checks: Array<[string, string, string, number]> = [
    ['fg (the ink)', g.fg, g.bg, INK_CONTRAST_MIN],
    ['dim (metadata)', g.dim, g.bg, DIM_CONTRAST_MIN],
    ['accent', g.accent, g.bg, ACCENT_CONTRAST_MIN],
    ['accent2', g.accent2, g.bg, ACCENT_CONTRAST_MIN],
    ['onAccent', g.onAccent, g.accent, INK_CONTRAST_MIN],
  ];
  for (const [name, c, on, floor] of checks) {
    // OPACITY FIRST. lumValue drops an alpha channel, so `fg: '#00000000'` — ink that is not there at all —
    // measured as pure black and cleared the 4.5:1 floor this function exists to enforce. You cannot measure
    // the legibility of a colour that is partly absent; refuse it instead of scoring it.
    for (const [label, colour] of [[name, c], [`the colour under ${name}`, on]] as Array<[string, string]>) {
      if (typeof colour === 'string' && /^#([0-9a-fA-F]{4}|[0-9a-fA-F]{8})$/.test(colour.trim())) {
        return `${label} is ${JSON.stringify(colour)}, which is TRANSLUCENT — a ground's tokens must be ` +
          'opaque, because what shows through them is not knowable here';
      }
    }
    const y = lumValue(c), oy = lumValue(on);
    if (y === null) {
      return `${name} is ${JSON.stringify(c)}, which is not a hex colour, so nothing about its ` +
        'legibility can be measured';
    }
    if (oy === null) {
      return `the colour under ${name} is ${JSON.stringify(on)}, which is not a hex colour, so nothing ` +
        `about ${name}'s legibility can be measured`;
    }
    const m = contrast(y, oy);
    if (m < floor) return `${name} ${c} measures ${m.toFixed(2)}:1 on ${on} — under the ${floor}:1 floor`;
  }
  return null;
};

/** A GroundSpec resolved, or a refusal. The one entry point every declared and derived ground goes
 *  through, so the floors above hold for all of them. */
export const groundFrom = (dna: DesignDNA, spec: GroundSpec): ResolvedGround => {
  const g = buildGround(dna, spec);
  const fault = legibilityFault(g);
  if (fault) {
    throw new Error(`ground "${spec.name ?? spec.bg}" cannot be lit from this film's palette: ${fault}. ` +
      'Every token but the ground itself is derived from the film\'s own ink and accents, so a film whose ' +
      'palette is not made of hex colours has nothing to derive from — fix the DNA token this names, or ' +
      'declare the ground\'s own `fg`/`accent`.');
  }
  return g;
};

// The first rung of the flip ladder, and how far past the key boundary the result has to land. 0.30 is
// where this started and where every one of the eight presets still lands (their flips measure Y=0.76 to
// 0.94), so the ladder's first rung reproduces them exactly. The MARGIN is what makes the flip a room and
// not a technicality: a ground one thousandth above the boundary is a mid grey that answers to the name
// "light key" while reading as neither exposure. Expressed through `keyFromY` rather than as a second
// comparison against LIGHT_KEY_Y, so the boundary still has exactly one reader.
const KEY_FLIP_MIX = 0.30;
const KEY_FLIP_STEPS = 16;
const KEY_FLIP_MARGIN = 0.25;
const clearsKey = (y: number, want: 'dark' | 'light'): boolean =>
  keyFromY(want === 'light' ? y - KEY_FLIP_MARGIN : y + KEY_FLIP_MARGIN) === want;

/** The film's OPPOSITE exposure, derived from what it already owns. A film states both ends of its own
 *  light: `fg` is its light ink and `bg` its dark ground. The flip makes the ink the FIELD — lifted toward
 *  white, because an ink is chosen to read ON a ground and so is a little grey to be a paper — and lets
 *  `groundFrom` pick the rest. Symmetric: a LIGHT film flips to a dark ground built from its dark ink.
 *  Derived rather than authored so it holds for a bespoke DNA too, not only for the eight presets.
 *
 *  IT IS A LADDER BECAUSE ONE FIXED LIFT IS NOT A DERIVATION. `tint(dna.fg, 0.30)` and nothing checking the
 *  result was `bgLum:'light'` reintroduced one layer up: the author asks for a light beat and gets a dark
 *  one, silently. Measured through this file: for a DNA with a mid-grey ink, every `fg` from #555555 to
 *  #757575 produced a ground whose own key was 'dark' — #6d6d6d gave #999999 at Y=0.319 — and immediately
 *  above that boundary it produced a mid grey nothing in the palette could be read on. So the lift walks up
 *  until the ground is on the requested side WITH margin and everything derived from it clears its floor,
 *  the way `expose` already walks until the accent clears its own. The last rung is the pure ink (f=1), on
 *  which every floor is met, so the throw below is reachable only from a DNA whose `fg`/`bg` are not
 *  colours — the one thing no ladder can fix. */
export const flipKeySpec = (dna: DesignDNA): GroundSpec => {
  const want: 'dark' | 'light' = keyOf(dna) === 'dark' ? 'light' : 'dark';
  const toward = want === 'light' ? tint : shade;
  for (let i = 0; i <= KEY_FLIP_STEPS; i++) {
    const spec: GroundSpec = {bg: toward(dna.fg, KEY_FLIP_MIX + (1 - KEY_FLIP_MIX) * (i / KEY_FLIP_STEPS)),
                              name: want + '-key'};
    const y = lumValue(spec.bg);
    if (y === null || !clearsKey(y, want)) continue;
    if (legibilityFault(buildGround(dna, spec)) === null) return spec;
  }
  throw new Error(`this film cannot be re-lit to a ${want} key: its ink ${JSON.stringify(dna.fg)} and its ` +
    `ground ${JSON.stringify(dna.bg)} produce no ${want} field that anything in the palette reads on. The ` +
    'opposite exposure is built by lifting the film\'s own ink into a field, so a DNA whose `fg` is not a ' +
    'hex colour (or is the same value as `bg`) has nothing to lift — declare the beat\'s `ground` ' +
    'explicitly, or give the film two inks.');
};

/** NAMED grounds any film can reach by name. These are the moves Figma's launch film makes that this library
 *  could not: a light paper field, a gallery white, and a SATURATED chromatic ground that is neither neutral
 *  nor an accent laid on top — warm and cool (references/launch-film-study.md; its sampled beats jump up to
 *  0.85 between neighbours, against this library's median film-wide range of 0.013).
 *  Only `bg` is declared; the ink and the accents come from the film, so a named ground still belongs to
 *  whichever film uses it. */
export const GROUND_PRESETS: Record<string, GroundSpec> = {
  paper: {bg: '#f4f0e6', name: 'paper'},        // Y=0.86 — warm stock, the light half of the library's own
  gallery: {bg: '#fafafa', name: 'gallery'},    // Y=0.95 — a neutral white wall
  // clay is the ground that found the fixed-mix defect: at Y=0.14 the library's own `dim` placement lands
  // at 2.18:1 on terminal and 2.37:1 on blueprint, under DIM_CONTRAST_MIN. `dimOn` solves it for clay and
  // for every other ground far from the presets, rather than this one colour being nudged until it passes.
  clay: {bg: '#b8412e', name: 'clay'},          // Y=0.14 — a saturated chromatic ground (Figma scene_04)
  olive: {bg: '#4d5b2a', name: 'olive'},        // Y=0.09 — the same move on the cool side
};

/** How a beat NAMES a ground: an index into `dna.grounds`, a GROUND_PRESETS name, or a spec written inline. */
export type GroundRef = number | string | GroundSpec;
/** A ground that RAMPS within the beat — the study's own "let the light carry the argument": a before/after
 *  or covered/uncovered beat makes one side lit ground and the other dark and moves the boundary, so the
 *  luminance arc and the meaning become the same fact. `at` is a window in the shot's own settled time. */
export type GroundRamp = {from: GroundRef; to: GroundRef; at?: [number, number]};
export type SceneGround = GroundRef | GroundRamp;
/** The ground half of a scene's EDL entry. Declared here rather than in Film.tsx so this file owns the whole
 *  ground vocabulary and Film.tsx composes it into SceneSpec. */
export type SceneGroundDecl = {
  ground?: SceneGround;
  // WHICH EXPOSURE this beat is lit at, when the beat does not name a specific ground. This is a DIRECTIVE
  // that repaints, which is what separates it from `bgLum` — that one is a DESCRIPTION of what the beat
  // already paints, consumed by the caption pick and the seam guard. Both are kept: a description of a
  // ground the runtime cannot resolve is still useful, and merging them would let a hint silently become a
  // command. Film.tsx throws when a beat declares both and they disagree.
  key?: 'dark' | 'light';
};

const isRamp = (g: SceneGround): g is GroundRamp =>
  typeof g === 'object' && g !== null && 'from' in g && 'to' in g;

/** Resolve one ground REFERENCE. Fails loudly on every reference it cannot honour — an out-of-range index,
 *  an unknown preset name, an object with no `bg` — because the alternative is a beat that silently keeps
 *  the film's ground and looks exactly like a beat that was never authored. */
export const resolveRef = (dna: DesignDNA, ref: GroundRef): ResolvedGround => {
  if (typeof ref === 'number') {
    const set = filmGrounds(dna);
    // The two faults are different faults and used to share one message: `ground: 1.5` was reported as
    // "outside this film's 4 grounds (0..3)", which is a lie about a number that is inside that range and
    // sends the author to add grounds they already have.
    if (!Number.isInteger(ref)) {
      throw new Error(`ground index ${ref} is not a whole number — an index NAMES one of this film's ` +
        `${set.length} grounds (0..${set.length - 1}); it is not a position along them. For a ground ` +
        'BETWEEN two, declare a ramp: `ground: {from: a, to: b}`.');
    }
    if (ref < 0 || ref >= set.length) {
      throw new Error(`ground index ${ref} is outside this film's ${set.length} grounds ` +
        `(0..${set.length - 1}) — declare more in dna.grounds, or name a preset: ` +
        Object.keys(GROUND_PRESETS).join(', '));
    }
    return groundFrom(dna, set[ref]);
  }
  if (typeof ref === 'string') {
    const hex = hexGround(ref);
    if (hex) return groundFrom(dna, {bg: hex});
    // An ALPHA hex is a hex that this file refuses on purpose — route it to the refusal that says why
    // rather than to "unknown ground", which would send the author looking for a typo in a preset name.
    // (`groundHex` throws for everything `hexGround` declined, so this call never returns.)
    if (/^#?([0-9a-fA-F]{4}|[0-9a-fA-F]{8})$/.test(ref.trim())) groundHex(ref, `"${ref}"`);
    const preset = GROUND_PRESETS[ref];
    if (!preset) {
      throw new Error(`unknown ground "${ref}" — expected a #hex, an index into dna.grounds, or one of: ` +
        Object.keys(GROUND_PRESETS).join(', '));
    }
    return groundFrom(dna, preset);
  }
  if (!ref || typeof ref !== 'object' || typeof (ref as GroundSpec).bg !== 'string') {
    throw new Error('a ground object must declare a `bg` hex colour, got ' + JSON.stringify(ref));
  }
  return groundFrom(dna, ref);
};

/** The film's own set of grounds: what the author declared, else a DERIVED default — its native ground, its
 *  opposite key, and a chromatic ground per accent. Derived rather than eight hand-written literals so every
 *  film (preset or bespoke) has a ground vocabulary with zero authoring, and so no colour in it is a copy of
 *  a colour stated elsewhere. */
export const filmGrounds = (dna: DesignDNA): GroundSpec[] => {
  const declared: unknown = dna.grounds;
  if (declared !== undefined) {
    // A MALFORMED `grounds` USED TO FALL THROUGH TO THE DERIVED SET, which is the worst of both: `ground: 0`
    // resolved to the film's own ground, the author's colour was never painted anywhere, and the frame
    // looked exactly like a beat nobody had authored. The whole point of the field is that it is the film's
    // own vocabulary — if it is present and unusable, say so.
    if (!Array.isArray(declared) || declared.length === 0) {
      throw new Error(`dna.grounds must be a non-empty ARRAY of ground specs (got ` +
        `${JSON.stringify(declared)}). It was silently ignored, so every \`ground: <index>\` resolved to a ` +
        'DERIVED vocabulary and the colours declared here were never painted. Omit `grounds` entirely to ' +
        'get that derived set on purpose: the film\'s native ground, its opposite key, and one chromatic ' +
        'ground per accent.');
    }
    declared.forEach((g, i) => {
      if (!g || typeof g !== 'object' || typeof (g as GroundSpec).bg !== 'string') {
        throw new Error(`dna.grounds[${i}] must declare a \`bg\` hex colour, got ${JSON.stringify(g)} — ` +
          'every other token of a ground is derived from the film, but the ground itself is the one thing ' +
          'only the author can state.');
      }
    });
    return declared as GroundSpec[];
  }
  return [{bg: dna.bg, bgGrad: dna.bgGrad, name: 'native'}, flipKeySpec(dna),
          chromaSpec(dna, dna.accent), chromaSpec(dna, dna.accent2)];
};

/** A saturated CHROMATIC ground carrying one of the film's own hues — the Figma move (an olive field, a
 *  peach field) done inside the film's palette. The accent is DEEPENED until it is a field rather than a
 *  highlight: painted full-bleed at its highlight exposure it leaves nothing to draw on it (a #3dd6a4 mint
 *  ground has no ink in the film's palette that reads on it).
 *
 *  Deepened toward BLACK, not toward the film's ground. Mixing toward a coloured ground drifts the hue — on
 *  the retro preset, pressing the cyan accent2 into its plum bg landed 5.9 degrees off — and the promise
 *  this file makes is that only exposure ever moves. Shading is a linear scale of r:g:b, so the hue is
 *  preserved exactly, and it needs no dark-end special case for a film that is already light. */
const CHROMA_TARGET_Y = 0.13;
const chromaSpec = (_dna: DesignDNA, accent: string): GroundSpec => {
  const base = lumValue(accent);
  if (base === null || base <= CHROMA_TARGET_Y) return {bg: accent, name: 'chroma'};
  for (let i = 1; i <= 24; i++) {
    const out = shade(accent, i / 24);
    const y = lumValue(out);
    if (y !== null && y <= CHROMA_TARGET_Y) return {bg: out, name: 'chroma'};
  }
  return {bg: '#000000', name: 'chroma'};
};

/** Interpolate two resolved grounds. Every token is mixed, so a ramp moves the whole world's exposure and
 *  not just the backdrop — a register reading `dim` or `line` ramps with it. */
export const mixGround = (a: ResolvedGround, b: ResolvedGround, p: number): ResolvedGround => {
  if (p <= 0) return a;
  if (p >= 1) return b;
  const bg = mix(a.bg, b.bg, p);
  const y = lumValue(bg) ?? a.y;
  return {
    bg,
    // A RAMPING beat is a SOLID-ground beat, for the whole beat including its parked ends. Two css gradient
    // strings cannot be interpolated, so carrying either endpoint's treatment would POP the moment the ramp
    // started. One decision per beat, taken here rather than at the crossing.
    bgGrad: undefined,
    fg: mix(a.fg, b.fg, p), dim: mix(a.dim, b.dim, p), surface: mix(a.surface, b.surface, p),
    surfaceBorder: mix(a.surfaceBorder, b.surfaceBorder, p), line: mix(a.line, b.line, p),
    accent: mix(a.accent, b.accent, p), accent2: mix(a.accent2, b.accent2, p),
    onAccent: mix(a.onAccent, b.onAccent, p),
    key: keyFromY(y), y,
  };
};

/** The ramp's default window, in the beat's own 0→1 time. It PARKS the ground for the frames a
 *  cross-dissolve is running over this shot at each end — the same discipline motion.ts's `useT` applies to
 *  the shot itself (a cut must land on a settled state, never mid-move). SEAM_FRAMES is imported, so the
 *  two cannot drift on the number that matters. */
const rampWindow = (durF: number): [number, number] => {
  const hold = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, durF - 1) / 3)) / Math.max(1, durF);
  return [hold, 1 - hold];
};

/** The ramp's window, VALIDATED. `const [t0, t1] = g.at ?? rampWindow(durF)` destructured whatever it was
 *  given: `at: "0.2"` (a JSON string) unpacked to t0='0', t1='.', `at: [0.2]` left t1 undefined, and either
 *  way `t1 - t0` was NaN — so `clamp01(NaN)` was NaN, `mixGround` mixed at NaN, and `Math.round(NaN)
 *  .toString(16)` made every token of the ground the string `#NaNNaNNaN`. The frame then rendered with an
 *  invalid colour for bg, fg, dim, surface, border, line and both accents; `lumValue` returned null for all
 *  of them, so the beat reported y=0 and key='dark' and the caption confidently picked ink for a ground
 *  nothing painted. Rendered: SwissEditorial black on black, every headline and rule invisible, no error.
 *  An INVERTED window is refused too — it used to be silently reinterpreted as a hard step at t0. */
const rampAt = (at: unknown, durF: number): [number, number] => {
  if (at === undefined) return rampWindow(durF);
  const ok = Array.isArray(at) && at.length === 2 &&
    at.every((v) => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1) && at[1] > at[0];
  if (!ok) {
    throw new Error(`a ground ramp's \`at\` must be [start, end] — two NUMBERS in the beat's own 0..1 time ` +
      `with end > start (got ${JSON.stringify(at)}). Every token of the ground is interpolated across that ` +
      'window, so a window that is not two numbers makes every one of them the invalid colour #NaNNaNNaN ' +
      'and the frame paints nothing readable. Omit `at` to ramp across the whole beat, parked at the seams.');
  }
  return at as [number, number];
};

/** The ground this beat paints at this frame — the ONE definition, called both by the provider inside the
 *  Sequence and by the caption HUD outside it (the HUD is a top-level sibling by construction — that is what
 *  stops two captions coexisting across a dissolve — so it cannot read the beat's context and must ask the
 *  same question of the same function).
 *
 *  Returns null when the beat declares no ground: that is the LEGACY path, and it must stay bit-for-bit what
 *  it was, so nothing is resolved, nothing is provided and nothing is painted. */
export const groundAt = (dna: DesignDNA | null, scene: SceneGroundDecl,
                         localFrame: number, durF: number, shot?: string | null,
                         reduced?: boolean): ResolvedGround | null => {
  const g = scene.ground;
  // AN UNKNOWN `key` USED TO MEAN "THE OPPOSITE EXPOSURE". The decision below is `scene.key === keyOf(dna)`,
  // so every truthy string that is not the film's own key re-lit the beat: 'ligth', 'Light', 'bright' and
  // 'dark ' all flipped it, and nothing else validates the field (validate.py does not know it, and the
  // bgLum cross-check only fires when the beat ALSO declares bgLum). A typo that silently repaints the
  // largest area on the frame is the loudest possible bug and it made no sound. Every other unknown token
  // in this runtime already fails here — an unknown icon name, an unknown preset, an unknown ground.
  // (typed `unknown` on purpose: the type says it is one of two strings, and the whole defect is that the
  // value arrives from a JSON props file that the type never saw.)
  const declaredKey: unknown = scene.key;
  if (declaredKey !== undefined && declaredKey !== 'dark' && declaredKey !== 'light') {
    throw new Error(`beat declares key: ${JSON.stringify(declaredKey)} — the only exposures are 'dark' and ` +
      "'light'. Anything else used to be read as \"the opposite of this film's own key\", so a typo re-lit " +
      'the beat instead of failing. To name a specific ground rather than an exposure, use `ground`.');
  }
  if (g === undefined && !scene.key) return null;
  if (!dna) {
    throw new Error('a beat declares a ground but the film has no design DNA — every register reads its ' +
      'ground and its ink from the DNA tokens, so there is nothing to re-ground. Give the film a ' +
      'design_dna (or a template), or drop the beat\'s ground.');
  }
  // THE NO-OP FIRST. `key:'dark'` on a dark film is documented as the same pixels as declaring nothing, and
  // it has to hold for EVERY register — including the twelve the refusal below rejects, which used to throw
  // on a declaration that changes not one pixel of theirs. The obvious next step for this vocabulary is an
  // EDL pass that stamps a key on every beat; that pass would have crashed the film on those twelve.
  if (g === undefined && scene.key === keyOf(dna)) return nativeGround(dna);
  // THE GROUND HAS TO REACH THE PIXELS, and for some registers it does not: they paint their own ground
  // (ExplodedSchematic's hardcoded navy), keep dark furniture through it (MaterialHero's 3D floor stays
  // black under a paper key) or hold hardcoded white type that vanishes on paper (GlitchDatamosh's display
  // word measures 1.14:1 there). The caption's ink is picked from the ground the beat DECLARES, so on those
  // the subtitle turns dark over pixels that are still black — the exact defect this whole change exists to
  // stop, reintroduced from the other side. The runtime cannot see the canvas, so it asks the measurement
  // (shotLuma's GROUND_FOLLOWS_MEASURED, scripts/measure_ground_reach.py) and refuses what it cannot honour.
  if (shot !== undefined && shot !== null && !groundFollows(shot)) {
    // "does not follow one" is the wrong answer for an id that is not a register at all — it sends the
    // author to re-measure the reach table for a shot that does not exist.
    if (!isRegisteredShot(shot)) {
      throw new Error(`beat names an unknown register "${shot}" — it is in neither the registry nor the ` +
        'ground measurements, so nothing can be said about whether a ground would reach it. Check the ' +
        'spelling against remotion/src/registry.ts.');
    }
    const what = g === undefined ? `key: '${String(scene.key)}'` : 'a ground';
    throw new Error(`beat "${shot}" declares ${what}, but this register does not follow one: rendered ` +
      'under a declared ground its own content keeps its luminance, so the frame would be part the ground ' +
      'the beat asked for and part the register\'s own — and the burned caption would pick ink for the ' +
      'half that is not there. Either drop it on this beat, or make the register paint from the DNA tokens ' +
      'and re-measure: python3 scripts/measure_ground_reach.py --emit');
  }
  if (g === undefined) {
    // `key` alone, and it is the exposure the film is NOT in: its opposite, derived.
    return groundFrom(dna, flipKeySpec(dna));
  }
  if (isRamp(g)) {
    const from = resolveRef(dna, g.from), to = resolveRef(dna, g.to);
    const [t0, t1] = rampAt(g.at, durF);
    // REDUCED MOTION freezes the ground exactly where it freezes the shot (motion.ts `useT` holds every
    // register at REDUCED_MOTION_T). A ground that kept ramping under the accessibility mode would be the
    // one thing still moving on a frame the whole point of which is that nothing moves — and the largest
    // moving area on it.
    const t = reduced ? REDUCED_MOTION_T : (durF > 1 ? localFrame / (durF - 1) : 1);
    const raw = clamp01((t - t0) / Math.max(1e-6, t1 - t0));
    // smoothstep: light that eases in and out reads as light changing, a linear one reads as a fader
    return mixGround(from, to, raw * raw * (3 - 2 * raw));
  }
  return resolveRef(dna, g);
};

/** The caption ink for a ground the runtime actually resolved: whichever of the two burned inks MEASURES
 *  more contrast on it. The old rule asked the three-bucket Lum class instead (`light` → dark ink, else
 *  white), whose boundary sits at Y=0.5 while the crossover between these two inks is at Y=0.19 — so on a
 *  ground anywhere in 0.19..0.5 it chose the less legible ink (white on Y=0.40 measures 2.33:1; the dark ink
 *  measures 8.1:1). That band is empty for a film-wide preset ground and is exactly where a RAMP spends its
 *  crossing, which is why the ink has to follow the number and not the bucket. */
export const captionInk = (groundY: number): string =>
  contrast(lumValue(CAPTION_INK_DARK) ?? 0, groundY) >= contrast(lumValue(CAPTION_INK_LIGHT) ?? 1, groundY)
    ? CAPTION_INK_DARK : CAPTION_INK_LIGHT;

/** The DNA a beat's children see: the film's system with this beat's ground tokens over it. A beat that
 *  declares nothing gets the film DNA object ITSELF (not a copy), so the provider below is a no-op. */
export const dnaWithGround = (dna: DesignDNA | null, ground: ResolvedGround | null): DesignDNA | null => {
  if (!dna || !ground) return dna;
  return {...dna, bg: ground.bg, bgGrad: ground.bgGrad, fg: ground.fg, dim: ground.dim,
    surface: ground.surface, surfaceBorder: ground.surfaceBorder, line: ground.line,
    accent: ground.accent, accent2: ground.accent2, onAccent: ground.onAccent};
};

/** The resolved ground, published to the shots. A register that wants to know what it is standing on
 *  (a shadow vs a glow, a scrim's direction) reads this instead of assuming the library's dark default. */
export const GroundContext = React.createContext<ResolvedGround | null>(null);
export const useGround = (): ResolvedGround | null => React.useContext(GroundContext);

/** Paints the beat's ground behind the shot. Renders NOTHING when the beat declares no ground: the film
 *  root is already painted in the film's ground, and an extra identical fill is a chance to differ for no
 *  gain. It earns its place on a re-grounded beat — the one register in 149 that does not paint an opaque
 *  ground of its own, and every register with a transparent margin, would otherwise show the FILM's
 *  near-black through a paper beat. */
export const Ground: React.FC<{ground: ResolvedGround | null}> = ({ground}) =>
  ground ? <AbsoluteFill style={{background: ground.bgGrad ?? ground.bg}} /> : null;

/** THE BEAT'S GROUND, provided. This is the whole mechanism the file exists for: the DesignDNAContext used
 *  to be provided ONCE outside the TransitionSeries, so `bg` was a film-wide constant and no beat could
 *  change it. Providing it HERE — inside each Sequence, with this beat's ground tokens over the film's
 *  system — re-grounds every register that reads those tokens, which measured is 148 of 149.
 *
 *  Backward-compatible by construction: with no declared ground `groundAt` returns null, `dnaWithGround`
 *  returns the film DNA object itself, `<Ground>` renders nothing, and a React provider emits no DOM — so
 *  the frame is bit-for-bit what it was. */
export const BeatGround: React.FC<{dna: DesignDNA | null; scene: SceneGroundDecl; durF: number;
  shot?: string; children?: React.ReactNode}> = ({dna, scene, durF, shot, children}) => {
  const frame = useCurrentFrame();
  const reduced = React.useContext(ReducedMotionContext);
  const ground = groundAt(dna, scene, frame, durF, shot, reduced);
  return (
    <DesignDNAContext.Provider value={dnaWithGround(dna, ground)}>
      <GroundContext.Provider value={ground}>
        <Ground ground={ground} />
        {children}
      </GroundContext.Provider>
    </DesignDNAContext.Provider>
  );
};
