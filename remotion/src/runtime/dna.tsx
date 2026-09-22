// DESIGN DNA — the GLOBAL visual system a remotion film is designed in. A shot LIBRARY entry contributes its
// STRUCTURE (composition + motion + information hierarchy); the DNA contributes the shared VISUAL IDENTITY
// (typography, palette, container/border style, motion personality, annotation grammar). One DNA per film,
// provided at the Film root and read by every shot via useDNA(), so "different compositions" still read as
// "one visual universe" (the remotion analogue of the html tier's theme.css semantic vars).
//
// BACKWARD-COMPATIBLE BY CONSTRUCTION: useDNA() returns null when no film provides one, so a migrated shot must
// read `dna?.token ?? <its original hardcoded value>` — with no DNA it renders byte-for-byte as before (the
// WorkBuddy default preview and any un-themed film are untouched). A shift happens ONLY when meta.design_dna is
// set and Film provides it.
//
// NOT a decorative theme: a DNA does NOT force every frame into a terminal window. It supplies a shared GRAMMAR
// (type/palette/container/motion/annotation vocabulary); a frame may still be a big metric, a diagram, a chart —
// it just inherits the grammar. Prefer subtle structural consistency over repetitive decoration.

import React from 'react';
import {useCurrentFrame} from 'remotion';
import {ReducedMotionContext} from './motion';
import {clamp01} from './motion';

export type DnaDecoration =
  | 'prompt' | 'status' | 'breadcrumb' | 'cursor' | 'scanline' | 'grid' | 'line-numbers';

// Which FORM this design system speaks for each content atom. Same idea as `decoration` — a DNA declares
// its vocabulary — extended from annotation cues to the parts a frame is built from. Every key is optional:
// an omitted (or unknown) form falls back to the atom's neutral form, which is what the library rendered
// before atoms existed. See runtime/atoms.tsx.
export type AtomForms = {
  bar?: 'block' | 'solid' | 'ruled' | 'pixel' | 'dimension';
  figure?: 'mono' | 'serif' | 'display' | 'segment';
  list?: 'tree' | 'ruled' | 'bullet' | 'numbered';
  label?: 'prompt' | 'kicker' | 'spec' | 'chip';
  divider?: 'scanline' | 'hairline' | 'dimension' | 'dotted';
  marker?: 'caret' | 'triangle' | 'crosshair' | 'arrow';
};

// A GROUND — one colour WORLD a film owns, as a beat can name it. Only `bg` is required: the film already
// owns its two inks and its two accents, so every other token is DERIVED from them for that ground
// (runtime/light.tsx `groundFrom`). That is deliberate — a ground has to be a one-word authoring decision
// ("this beat is on paper") and not a second palette that has to be kept in sync with the first.
export type GroundSpec = {
  bg: string;            // the solid ground. MUST be a hex: the caption ink, the seam luminance guard and
                         // the exposure key are all derived from its luminance, and light.tsx throws rather
                         // than let an unresolvable ground put them back to guessing.
  bgGrad?: string;       // an optional TREATMENT painted over it (a css background value), as `bgGrad` above
  fg?: string;           // ink override; default = whichever of the film's own fg/bg measures more contrast
  accent?: string;       // accent override; default = the film's accent, exposure-adjusted for this ground
  name?: string;         // authoring/debug label only — never rendered
};

export type DesignDNA = {
  id: string;
  // TYPOGRAPHY (css font shorthands / family lists)
  fontDisplay: string;   // headings / hero type
  fontMono: string;      // code / labels / metadata
  fontBody: string;      // running text
  // PALETTE
  bg: string;            // base page background (solid)
  bgGrad?: string;       // optional background TREATMENT (a css background value; overrides bg when a shot opts in)
  fg: string;            // primary ink
  dim: string;           // secondary ink / metadata
  accent: string;
  accent2: string;
  onAccent: string;      // ink ON an accent fill
  surface: string;       // container fill
  surfaceBorder: string; // container border colour
  line: string;          // grid / divider lines
  // SHAPE
  radius: number;        // container corner radius (px)
  borderWidth: number;   // container border width (px)
  // GRAMMAR
  motion: 'type' | 'execute' | 'smooth' | 'mechanical';  // reveal personality
  decoration: DnaDecoration[];   // which annotation cues this system speaks
  uppercaseLabels: boolean;      // kicker/label casing
  labelSpacing: string;          // letter-spacing for mono labels
  // GENERALIZATION: true = ONE font for the whole film (e.g. terminal = all-mono) → Film injects a global
  // font-family !important. false/absent = a MIXED-type style (display ≠ body, e.g. editorial serif + sans) →
  // registers use fontDisplay/fontBody per element and NO global override. So the DNA generalizes past terminal.
  uniformType?: boolean;
  atoms?: AtomForms;             // per-atom FORM this system speaks; omitted = the neutral form
  // THE FILM'S MATERIAL. One topic-derived surface stated once and inherited by every frame — masonry
  // coursing for a built subject, a waterline for a place made of water, a survey graticule for a mapped
  // one. Without it a themed film is a set of clean bare diagrams: right palette, right type, no material.
  // See runtime/motif.tsx; omitted = no motif, which is a legitimate choice for a deliberately austere film.
  motif?: {kind?: string; ink?: string; opacity?: number; scale?: number};
  // THE FILM'S NATIVE CUT. An unmarked seam becomes the design system's own action rather than a generic
  // cross-fade — the analogue of the surface/grammar split, applied to TIME. The presets get theirs from a
  // switch in Film.tsx (terminal = screen-clear, editorial = a sheet laid down), but a BESPOKE direction had
  // no way to declare one, so every topic-conceived film fell through to the same anonymous fade: a 35-beat
  // film shipped with all 34 of its cuts identical and belonging to nobody's design language.
  // Vocabulary: 'wipe' | 'slide' | 'clock' | 'dissolve' | 'screen-clear' | 'fade' (fade = deliberately plain).
  seam?: {type?: string; direction?: string};
  /**
   * The film's photographic finish (grain / vignette / key direction) — see runtime/finish.tsx. Preset-tuned,
   * with a mild default on NEUTRAL so every AUTHORED partial DNA inherits one through coerceDna's spread; a
   * film opts out with `'none'`. Only the UN-THEMED path has none at all — optics are part of a design
   * system's voice, and the null-DNA rule keeps machinery out of the original look.
   */
  finish?: import('./finish').FilmFinish | 'none';
  // THE FILM'S GROUNDS. A film had exactly one, and it was near-black in all eight presets (the brightest,
  // editorial, is Y=0.0053), so a 30-beat film painted one identical ground thirty times: measured library
  // luminance range 0.013 against Figma's 0.903. A beat names one of these by index and the whole frame
  // re-grounds, because 148 of the 149 registers paint from `bg` (shotLuma's DNA_GROUND_TOKEN). OMITTED is
  // not "no grounds": light.tsx `filmGrounds` then DERIVES a set from what the film already declares — its
  // native ground, its opposite exposure key, and a chromatic ground per accent — so every film has a
  // ground vocabulary with no authoring at all, and nothing here is a copy of a colour stated above.
  grounds?: GroundSpec[];
};

// ── Presets ────────────────────────────────────────────────────────────────────────────────────────────────
// TERMINAL — a dark technical workspace: monospace everywhere, thin square-ish panels, green/blue accents,
// command→result→metadata hierarchy, typing/execution motion, prompt/cursor/status/scanline grammar.
export const TERMINAL_DNA: DesignDNA = {
  id: 'terminal',
  fontDisplay: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  bg: '#080b11',
  bgGrad: 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
  fg: '#cdd7e4',
  dim: '#5f6b80',
  accent: '#3dd6a4',
  accent2: '#4d8cff',
  onAccent: '#03130d',
  surface: '#0c1119',
  surfaceBorder: '#26324c',
  line: '#182234',
  radius: 6,
  borderWidth: 1,
  motion: 'type',
  decoration: ['prompt', 'status', 'breadcrumb', 'cursor', 'scanline', 'grid', 'line-numbers'],
  uppercaseLabels: false,
  labelSpacing: '0.02em',
  uniformType: true,   // terminal = all-mono
  atoms: {bar: 'block', figure: 'mono', list: 'tree', label: 'prompt', divider: 'scanline', marker: 'caret'},
  finish: {grain: 0.04, vignette: 0.3, light: 'none'},   // a CRT: strong edge falloff, no key — the tube IS the light
};

// NEUTRAL — approximates the library's CURRENT common look (dark, Inter display, mono code, blue accent, soft
// radius, smooth motion). Used as the explicit "no strong system" baseline; a migrated shot's `?? original`
// fallbacks already reproduce its own look, so this is mostly for reference / a mild default.
export const NEUTRAL_DNA: DesignDNA = {
  id: 'neutral',
  fontDisplay: 'Inter, "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: 'Inter, "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  bg: '#05060a',
  fg: '#e7ecf4',
  dim: '#8b93a8',
  accent: '#5b8cff',
  accent2: '#37d4a6',
  onAccent: '#04120d',
  surface: '#171b28',
  surfaceBorder: '#333a52',
  line: '#222a3d',
  radius: 16,
  borderWidth: 1,
  motion: 'smooth',
  decoration: [],
  uppercaseLabels: false,
  labelSpacing: '0',
  // The MILD default optics — and, because coerceDna spreads every authored PARTIAL DNA over this preset,
  // the finish every real film inherits unless it says otherwise. That routing is the point: the
  // shot-director writes meta.design_dna as an OBJECT, so a finish that lived only on the named presets
  // would ship on preset-string films (mostly tests) and never on an actual delivery.
  finish: {grain: 0.04, vignette: 0.18, light: 'top'},
};

// The following are TOKEN presets so `dnaFromTemplate` generalises past terminal — they give any topic ONE
// type + palette + motion world for a chosen style. NOTE: token consistency is only the FLOOR. A truly on-style
// film also wants STYLE-NATIVE components (like the terminal Term* family); until a style has its own family,
// its shots use the library registers reading these tokens + the three-layer discipline (§C2). Each is
// MIXED-type (uniformType unset) so Film does NOT force one font.

// EDITORIAL — a print/magazine world: serif display + clean sans body, warm paper-dark ground, ink + one hot
// accent, generous margins, rules/kickers/drop-caps grammar, smooth typographic reveals.
export const EDITORIAL_DNA: DesignDNA = {
  id: 'editorial',
  fontDisplay: '"Playfair Display", "Noto Serif SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", Georgia, serif',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: '"Source Serif 4", "Noto Serif SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", Georgia, serif',
  bg: '#12100e', bgGrad: 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)',
  fg: '#efe9df', dim: '#9a9084', accent: '#e2603f', accent2: '#c9a24b', onAccent: '#1a0f0b',
  surface: '#181512', surfaceBorder: '#33291f', line: '#2a2018',
  radius: 2, borderWidth: 1, motion: 'smooth', decoration: ['grid'], uppercaseLabels: true, labelSpacing: '0.18em',
  atoms: {bar: 'ruled', figure: 'serif', list: 'ruled', label: 'kicker', divider: 'hairline', marker: 'triangle'},
  finish: {grain: 0.07, vignette: 0.2, light: 'top'},    // paper tooth + a reading lamp from above
};
// PRODUCT — a clean Apple-like keynote world: geometric sans, near-black or soft-light ground, rounded glass
// panels, soft shadows, ONE vivid accent, gentle scale/parallax reveals.
export const PRODUCT_DNA: DesignDNA = {
  id: 'product',
  fontDisplay: '"Space Grotesk", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: 'Inter, "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  bg: '#060709', bgGrad: 'radial-gradient(120% 120% at 50% 0%, #14161d, #060709 72%)',
  fg: '#f2f5fb', dim: '#8a93a5', accent: '#5b8cff', accent2: '#a06bff', onAccent: '#050810',
  surface: '#12141c', surfaceBorder: '#262b3a', line: '#20242f',
  radius: 22, borderWidth: 1, motion: 'smooth', decoration: [], uppercaseLabels: false, labelSpacing: '0',
  atoms: {bar: 'solid', figure: 'display', list: 'bullet', label: 'chip', divider: 'hairline', marker: 'triangle'},
  finish: {grain: 0.05, vignette: 0.24, light: 'top'},   // keynote stage light: soft key, gentle falloff
};
// BLUEPRINT — an engineering-drawing world: mono/geometric type, deep blueprint-blue ground, thin cyan rules +
// crop-marks + dimension lines + a measured grid, precise draw-on reveals.
export const BLUEPRINT_DNA: DesignDNA = {
  id: 'blueprint',
  fontDisplay: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: '"IBM Plex Sans", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  bg: '#071018', bgGrad: 'radial-gradient(130% 120% at 50% -8%, #0b1c2b, #050b12 72%)',
  fg: '#cfe6f5', dim: '#5f7d92', accent: '#38b6ff', accent2: '#7fe0d0', onAccent: '#04121c',
  surface: '#0a1622', surfaceBorder: '#1d3a52', line: '#123048',
  radius: 3, borderWidth: 1, motion: 'mechanical', decoration: ['grid', 'line-numbers'], uppercaseLabels: true, labelSpacing: '0.12em',
  atoms: {bar: 'dimension', figure: 'mono', list: 'numbered', label: 'spec', divider: 'dimension', marker: 'crosshair'},
  finish: {grain: 0.04, vignette: 0.16, light: 'top'},   // a drawing board under an even lamp — barely lit, mostly flat
};

// CINEMATIC — an atmospheric, tactile film world: a serif/grotesk display over near-black, warm practical light,
// one amber key + a cool fill, soft filmic reveals. (direction: cinematic-craft)
export const CINEMATIC_DNA: DesignDNA = {
  id: 'cinematic',
  fontDisplay: '"Bodoni Moda", "Noto Serif SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", Georgia, serif',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: 'Inter, "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  bg: '#08070a', bgGrad: 'radial-gradient(90% 80% at 62% 42%, #241a12, #0c0a0d 52%, #050406 82%)',
  fg: '#f4efe6', dim: '#9a8f83', accent: '#e8a13c', accent2: '#7fa8c9', onAccent: '#1a1006',
  surface: '#141014', surfaceBorder: '#2c2320', line: '#241d1d',
  radius: 10, borderWidth: 1, motion: 'smooth', decoration: [], uppercaseLabels: false, labelSpacing: '0.06em',
  atoms: {bar: 'solid', figure: 'serif', list: 'bullet', label: 'kicker', divider: 'hairline', marker: 'triangle'},
  finish: {grain: 0.08, vignette: 0.34, light: 'top'},   // the most photographic system: real tooth, deep falloff
};
// DATA — an evidence-forward analyst world: tabular-friendly sans + mono figures, deep slate ground, a measured
// grid, one signal colour + a comparison colour, precise mechanical reveals. (direction: data-story)
export const DATA_DNA: DesignDNA = {
  id: 'data',
  fontDisplay: '"IBM Plex Sans", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  fontMono: '"IBM Plex Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: '"IBM Plex Sans", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  bg: '#0a0f16', bgGrad: 'radial-gradient(120% 110% at 50% 0%, #13202c, #080d13 74%)',
  fg: '#e8eef6', dim: '#7d8a9b', accent: '#3ddc97', accent2: '#f2b544', onAccent: '#04140d',
  surface: '#111823', surfaceBorder: '#22303f', line: '#1a2431',
  radius: 8, borderWidth: 1, motion: 'mechanical', decoration: ['grid'], uppercaseLabels: true, labelSpacing: '0.1em',
  atoms: {bar: 'ruled', figure: 'mono', list: 'numbered', label: 'spec', divider: 'hairline', marker: 'crosshair'},
  finish: {grain: 0.03, vignette: 0.14, light: 'none'},  // evidence wants the flattest field that still reads as printed
};
// RETRO — a nostalgic arcade/print world: chunky display face, deep plum ground, hot magenta + cyan, snappy
// stepped motion and scanline furniture. (direction: retro-playful)
export const RETRO_DNA: DesignDNA = {
  id: 'retro',
  fontDisplay: '"Baloo 2", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  fontMono: '"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", ui-monospace, monospace',
  fontBody: '"Baloo 2", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif',
  bg: '#140a1e', bgGrad: 'radial-gradient(120% 120% at 50% 100%, #37115a, #140a1e 62%, #0b0512 100%)',
  fg: '#ffeffb', dim: '#a78bbd', accent: '#ff2e88', accent2: '#22e3ff', onAccent: '#1a0410',
  surface: '#1e1030', surfaceBorder: '#40215f', line: '#2c1745',
  radius: 6, borderWidth: 2, motion: 'mechanical', decoration: ['scanline'], uppercaseLabels: true, labelSpacing: '0.14em',
  atoms: {bar: 'pixel', figure: 'segment', list: 'bullet', label: 'chip', divider: 'dotted', marker: 'arrow'},
  finish: {grain: 0.06, vignette: 0.3, light: 'none'},   // an arcade cabinet: tube falloff, phosphor grain, no key
};

export const DNA_PRESETS: Record<string, DesignDNA> = {
  'terminal-technical': TERMINAL_DNA,
  terminal: TERMINAL_DNA,
  neutral: NEUTRAL_DNA,
  editorial: EDITORIAL_DNA,
  'kinetic-editorial': EDITORIAL_DNA,
  product: PRODUCT_DNA,
  'product-demo': PRODUCT_DNA,
  apple: PRODUCT_DNA,
  blueprint: BLUEPRINT_DNA,
  // every one of shot_templates.TEMPLATES maps to a DNA, so picking ANY direction gets the global visual system
  // with zero authoring (tests/test_remotion.py asserts this stays true)
  'cinematic-craft': CINEMATIC_DNA,
  cinematic: CINEMATIC_DNA,
  'data-story': DATA_DNA,
  data: DATA_DNA,
  'retro-playful': RETRO_DNA,
  retro: RETRO_DNA,
};

// Expand a template id into a DNA preset (the fallback when meta.design_dna is not explicitly authored).
/** Normalise an AUTHORED `meta.design_dna` (hand-written JSON, unvalidated at the type level) into a complete DNA:
 *  missing tokens fall back to NEUTRAL_DNA rather than reaching a component as `undefined` (an `undefined` inside a
 *  `font:` shorthand or a colour paints nothing). Pair with validate.py's missing-key warning, which still tells the
 *  author what they left out — this only stops a partial DNA from breaking the render. */
export const coerceDna = (dna?: Partial<DesignDNA> | string | null): DesignDNA | null => {
  if (!dna) return null;
  // A STRING is a preset NAME. Spreading one produced {...NEUTRAL_DNA, '0':'t', '1':'e', ...}, so an authored
  // `design_dna: "terminal"` rendered the ENTIRE film in the neutral palette and said nothing — the failure
  // mode that hides longest. Resolve it, and fail loudly on a name that does not exist.
  if (typeof dna === 'string') {
    const preset = DNA_PRESETS[dna];
    if (!preset) {
      throw new Error(`unknown design_dna preset "${dna}" — expected one of: ${Object.keys(DNA_PRESETS).join(', ')}`);
    }
    return preset;
  }
  if (typeof dna !== 'object' || Array.isArray(dna)) {
    throw new Error('design_dna must be a preset name or an object, got ' + typeof dna);
  }
  return {...NEUTRAL_DNA, ...dna, decoration: Array.isArray(dna.decoration) ? dna.decoration : NEUTRAL_DNA.decoration};
};

export const dnaFromTemplate = (t?: string | null): DesignDNA | null =>
  (t ? DNA_PRESETS[t] ?? null : null);

// ── Context / hook ───────────────────────────────────────────────────────────────────────────────────────────
export const DesignDNAContext = React.createContext<DesignDNA | null>(null);
export const useDNA = (): DesignDNA | null => React.useContext(DesignDNAContext);
// TOTAL by construction: `decoration` is the only NESTED dereference of a DNA token in the tree, so a
// hand-authored meta.design_dna that omits it used to crash every scene (TerminalChrome calls this first).
// Every other token degrades to a fallback; this one must too.
export const dnaHas = (dna: DesignDNA | null, d: DnaDecoration): boolean =>
  !!dna && Array.isArray(dna.decoration) && dna.decoration.includes(d);

// ── Reusable annotation cues (LEVEL-2 grammar) ───────────────────────────────────────────────────────────────
// A blinking block caret — the terminal cursor. Deterministic (blinks on frame parity, not wall-clock).
export const Caret: React.FC<{color?: string; h?: number; w?: number; style?: React.CSSProperties}> =
  ({color, h = 26, w = 12, style}) => {
    const frame = useCurrentFrame();
    const reduced = React.useContext(ReducedMotionContext);      // accessibility: a frozen, settled frame
    const on = reduced ? true : Math.floor(frame / 16) % 2 === 0;
    return <span style={{display: 'inline-block', width: w, height: h, marginLeft: 4, verticalAlign: 'text-bottom',
      background: color ?? '#3dd6a4', opacity: on ? 0.95 : 0.12, ...style}} />;
  };

// A mono breadcrumb / command line, e.g. "~/project ▸ open-weights" — a LEVEL-2 cue a shot can drop top-left to
// belong to the terminal world without becoming a full terminal window. Renders nothing when the DNA has no
// 'breadcrumb' in its decoration (so it's inert under NEUTRAL/no DNA).
export const Breadcrumb: React.FC<{dna: DesignDNA | null; path: string; opacity?: number;
  style?: React.CSSProperties}> = ({dna, path, opacity = 0.72, style}) => {
  if (!dnaHas(dna, 'breadcrumb')) return null;
  return (
    <div style={{position: 'absolute', top: 40, left: 56, color: dna!.dim, opacity,
      font: `600 22px/1 ${dna!.fontMono}`, letterSpacing: dna!.labelSpacing, whiteSpace: 'nowrap', ...style}}>
      <span style={{color: dna!.accent}}>▸</span> {path}
    </div>
  );
};

// A faint terminal grid + a single soft scanline — a LEVEL-1 background cue. Inert unless the DNA speaks 'grid'.
export const ScanGrid: React.FC<{dna: DesignDNA | null; w: number; h: number}> = ({dna, w, h}) => {
  const frame = useCurrentFrame();
  const reduced = React.useContext(ReducedMotionContext);
  if (!dnaHas(dna, 'grid')) return null;
  const y = reduced ? h * 0.5 : (frame * 2) % (h + 200) - 100;   // slow deterministic sweep (parked when reduced)
  return (
    <svg width={w} height={h} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} aria-hidden>
      <defs>
        <pattern id="dnagrid" width="46" height="46" patternUnits="userSpaceOnUse">
          <path d="M46 0H0V46" fill="none" stroke={dna!.line} strokeWidth="1" opacity="0.5" />
        </pattern>
      </defs>
      <rect width={w} height={h} fill="url(#dnagrid)" opacity={0.5} />
      {dnaHas(dna, 'scanline')
        ? <rect x="0" y={y} width={w} height="2" fill={dna!.accent} opacity={0.05} /> : null}
    </svg>
  );
};

// TERMINAL CHROME — a per-scene UI FRAME that wraps ANY composition in the same terminal-session grammar: a
// command-path breadcrumb (top-left) + a live status readout with a blinking caret (top-right). Driven by a
// per-scene {path, status} so the text VARIES beat to beat (structural consistency, not repetitive decoration —
// docx §13). Sits in the TOP safe corners (clear of centred content + the bottom caption band). Inert unless the
// DNA speaks 'breadcrumb' — so it's on for terminal, off for a system that doesn't have CLI chrome.
export const TerminalChrome: React.FC<{dna: DesignDNA | null; path?: string; status?: string; root?: string;
  W: number; H: number}> = ({dna, path, status, root = '~', W, H}) => {
    const frame = useCurrentFrame();
    const reduced = React.useContext(ReducedMotionContext);
    if (!dnaHas(dna, 'breadcrumb')) return null;
    const on = reduced ? true : Math.floor(frame / 16) % 2 === 0;
    const mono = dna!.fontMono, dim = dna!.dim, acc = dna!.accent, ls = dna!.labelSpacing;
    // SCALE with the frame instead of assuming 1920×1080, and CLAMP each block to its half so a long path can
    // never run into the status readout (or off a 1080-wide portrait frame). The corners are shared furniture:
    // a shot that draws its own corner marks will sit under these, so keep them light and bounded.
    const u = Math.min(W, H) / 1080;
    const inset = Math.round(56 * u), top = Math.round(40 * u), fs = Math.max(14, Math.round(22 * u));
    const cap: React.CSSProperties = {maxWidth: W / 2 - inset - 20, overflow: 'hidden', textOverflow: 'ellipsis'};
    return (
      <>
        {path ? (
          <div style={{position: 'absolute', top, left: inset, color: dim, opacity: 0.85,
            font: `600 ${fs}px/1 ${mono}`, letterSpacing: ls, whiteSpace: 'nowrap', ...cap}}>
            <span style={{color: acc}}>{root}</span> <span style={{opacity: 0.6}}>▸</span> {path}</div>
        ) : null}
        {status ? (
          <div style={{position: 'absolute', top, right: inset, color: dim, opacity: 0.85,
            font: `600 ${Math.max(13, fs - 2)}px/1 ${mono}`, letterSpacing: ls, whiteSpace: 'nowrap',
            display: 'flex', alignItems: 'center', ...cap}}>
            <span style={{color: acc, marginRight: 8}}>●</span>{status}
            <span style={{display: 'inline-block', width: Math.round(9 * u), height: Math.round(17 * u), marginLeft: 7,
              background: acc, opacity: on ? 0.9 : 0.12}} /></div>
        ) : null}
      </>
    );
  };

// TERMFRAME — the SURFACE-vs-GRAMMAR switch + the command→result MOTION (Terminal Design System, three-layer
// model). `framed` = an explicit terminal WINDOW (traffic dots + panel border) — use on only 2-3 anchor beats
// (a boot, code, an ending). DEFAULT (open) = NO window box: a typed command line on the OPEN dark canvas, then
// the RESULT (children) "executes" and grows out below. Both keep the terminal GRAMMAR (mono, $ / ❯, cursor,
// dark). This is what stops every frame being the same terminal box — most beats inherit the grammar without a
// window, only a few show one. `align` varies the open layout so beats don't all center.
export const TermFrame: React.FC<{dna: DesignDNA | null; cmd?: string; t: number; framed?: boolean;
  align?: 'center' | 'left'; runAt?: number; children?: React.ReactNode}> =
  ({dna, cmd = '', t, framed = false, align = 'center', runAt = 0.2, children}) => {
    const frame = useCurrentFrame();
    const d = dna ?? NEUTRAL_DNA;
    const mono = d.fontMono, acc = d.accent, dim = d.dim, fg = d.fg;
    const on = Math.floor(frame / 16) % 2 === 0;
    // the command TYPES over [0.05, runAt-0.04], then EXECUTES; the result reveals just after.
    const chars = [...cmd];
    const typed = Math.round(chars.length * clamp01((t - 0.05) / Math.max(0.06, runAt - 0.09)));
    const shown = chars.slice(0, typed).join('');
    const running = typed >= chars.length;
    // MOTION grammar: the result reveals in the DNA's motion CHARACTER — a terminal 'type'/'execute' result POPS
    // out (snappy settle, like a command finishing), 'mechanical' steps in, 'smooth' eases (product/editorial).
    const raw = clamp01((t - runAt) / 0.12);
    const resIn = d.motion === 'type' || d.motion === 'execute' ? 1 - Math.pow(1 - raw, 4)
      : d.motion === 'mechanical' ? Math.round(raw * 5) / 5 : 1 - Math.pow(1 - raw, 3);

    // TermFrame's unframed box was a FIXED min(84vw, 1320px). With align='left', short content hugged
    // ITS left edge, so a centred box left a large void on the right — measured at 22% content width
    // sitting 23% off the frame's centre. The box now fits its content, which keeps terminal text
    // left-aligned (it must be) while the block itself sits centred in the frame.
    if (framed) {
      return (
        <div style={{width: 'min(80vw, 1180px)', background: d.surface, border: `1px solid ${d.surfaceBorder}`,
          borderRadius: d.radius, boxShadow: '0 30px 90px #0009', overflow: 'hidden', fontFamily: mono}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 10, padding: '16px 22px',
            borderBottom: `1px solid ${d.surfaceBorder}`, background: '#0000002e'}}>
            {['#ff5f56', dim, acc].map((c, i) => <div key={i} style={{width: 12, height: 12, borderRadius: '50%', background: c, opacity: 0.8}} />)}
            <div style={{marginLeft: 10, color: dim, font: `600 22px/1 ${mono}`}}><span style={{color: acc}}>$</span> {cmd}</div>
          </div>
          <div style={{padding: '30px 34px 34px'}}>{children}</div>
        </div>
      );
    }
    // OPEN — command line on the open canvas, result grows out below. No window box.
    return (
      <div style={{width: 'fit-content', maxWidth: 'min(84vw, 1320px)', fontFamily: mono, textAlign: align,
        display: 'flex', flexDirection: 'column', alignItems: align === 'left' ? 'flex-start' : 'center'}}>
        <div style={{color: dim, font: `600 30px/1 ${mono}`, letterSpacing: d.labelSpacing, marginBottom: 40,
          opacity: clamp01(t / 0.06)}}>
          <span style={{color: acc}}>$</span> {shown}
          <span style={{display: 'inline-block', width: 14, height: 26, marginLeft: 6, verticalAlign: 'text-bottom',
            background: acc, opacity: running ? (on ? 0.5 : 0.1) : 0.9}} />
        </div>
        <div style={{opacity: resIn, transform: `translateY(${(1 - resIn) * 26}px)`, width: '100%',
          display: 'flex', flexDirection: 'column', alignItems: align === 'left' ? 'flex-start' : 'center'}}>{children}</div>
      </div>
    );
  };

/**
 * The width TermFrame's children actually get.
 *
 * Exported because a register that sizes its own type to the frame otherwise restates these numbers, and a
 * restated number is a second answer: TermGitLog set a fixed 38px row against a width it had guessed and
 * ran a Chinese commit message 345px past the frame edge, with `white-space: pre` guaranteeing it could
 * not wrap out of the problem. Framed subtracts its own 34px padding on each side.
 */
export const termInnerW = (W: number, framed?: boolean): number =>
  framed ? Math.min(W * 0.80, 1180) - 68 : Math.min(W * 0.84, 1320);

// EDFRAME — the EDITORIAL analogue of TermFrame (proves the three-layer model generalises past terminal). Its
// grammar is print, not CLI: a small uppercase letter-spaced KICKER + a hairline RULE + a serif headline zone,
// generous margins, smooth typographic reveals. `framed` = a heavier "cover/spread" surface (a ruled border) for
// the 2-3 anchor beats; default = OPEN (kicker + rule + content on the paper-dark ground). Reveals ease (the
// editorial DNA's motion is 'smooth'), never type/execute. Use it exactly like TermFrame, for editorial shots.
export const EdFrame: React.FC<{dna: DesignDNA | null; kicker?: string; t: number; framed?: boolean;
  align?: 'center' | 'left'; children?: React.ReactNode}> =
  ({dna, kicker = '', t, framed = false, align = 'left', children}) => {
    const d = dna ?? NEUTRAL_DNA;
    const disp = d.fontDisplay, acc = d.accent, dim = d.dim, ls = d.labelSpacing || '0.18em';
    const kIn = clamp01(t / 0.14), ruleIn = clamp01((t - 0.08) / 0.18), bodyIn = 1 - Math.pow(1 - clamp01((t - 0.16) / 0.24), 3);
    const inner = (
      <div style={{width: 'min(84vw, 1300px)', display: 'flex', flexDirection: 'column',
        alignItems: align === 'left' ? 'flex-start' : 'center', textAlign: align,
        padding: framed ? '60px 72px' : 0, border: framed ? `1px solid ${d.surfaceBorder}` : 'none',
        background: framed ? d.surface : 'transparent'}}>
        {kicker ? <div style={{color: acc, font: `700 26px/1 ${d.fontBody}`, letterSpacing: ls,
          textTransform: d.uppercaseLabels ? 'uppercase' : 'none', opacity: kIn,
          transform: `translateY(${(1 - kIn) * -8}px)`}}>{kicker}</div> : null}
        <div style={{height: 2, background: acc, width: `${ruleIn * (align === 'left' ? 120 : 90)}px`,
          margin: `${kicker ? 22 : 0}px 0 40px`, opacity: 0.9}} />
        <div style={{opacity: bodyIn, transform: `translateY(${(1 - bodyIn) * 20}px)`, width: '100%',
          fontFamily: disp}}>{children}</div>
      </div>
    );
    return inner;
  };

// A small status tag, e.g. "PASS" / "DONE" — a LEVEL-2 cue for a shot's result state.
export const StatusTag: React.FC<{dna: DesignDNA | null; text: string; style?: React.CSSProperties}> =
  ({dna, text, style}) => (
    <span style={{font: `700 18px/1 ${(dna ?? NEUTRAL_DNA).fontMono}`, letterSpacing: '0.08em',
      color: (dna ?? NEUTRAL_DNA).accent, border: `1px solid ${(dna ?? NEUTRAL_DNA).accent}`, borderRadius: 4,
      padding: '4px 9px', ...style}}>{text}</span>
  );

// ── Colour utilities — DERIVE a palette from the DNA ──────────────────────────────────────────────────────────
// Some registers are ILLUSTRATION: their look is carried by a whole multi-hue palette (a cartoon's sky/grass/
// mascot, clay blocks, cut-paper depth planes, comic POP flats, a maximalist clash). Level-A token swaps can't
// serve those — they need a FAMILY of colours generated from the DNA's two accents, keeping the technique (thick
// ink outlines, matte clay shading, layered paper depth, Ben-Day flats) while re-hueing the world. These helpers
// do that. All of them PASS THROUGH any value they can't parse (a gradient string, a css colour name, rgba()),
// so a shot that feeds them a non-hex simply keeps its original colour instead of rendering black.

const _hex = (c: string): [number, number, number] | null => {
  if (typeof c !== 'string') return null;
  const m = c.trim().replace(/^#/, '');
  if (!/^[0-9a-fA-F]{3,8}$/.test(m)) return null;
  const h = m.length === 3 || m.length === 4
    ? m.slice(0, 3).split('').map((ch) => ch + ch).join('')
    : m.length >= 6 ? m.slice(0, 6) : null;
  if (!h) return null;
  const n = parseInt(h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};
const _out = (r: number, g: number, b: number) =>
  '#' + [r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');

/** Blend two colours: f=0 → a, f=1 → b. Unparseable input passes `a` through. */
export const mix = (a: string, b: string, f: number): string => {
  const A = _hex(a), B = _hex(b);
  if (!A || !B) return a;
  return _out(A[0] + (B[0] - A[0]) * f, A[1] + (B[1] - A[1]) * f, A[2] + (B[2] - A[2]) * f);
};
/** Toward white (a lighter tint of the same hue) — clay highlights, paper lifts. */
export const tint = (c: string, f: number): string => mix(c, '#ffffff', f);
/** Toward black (a deeper shade) — clay contact shadow, receding paper planes. */
export const shade = (c: string, f: number): string => mix(c, '#000000', f);

/** The colour model the DENSITY instrument measures in (PIL 'L' = 0.299R+0.587G+0.114B), which is NOT the
 *  sRGB relative luminance `lumValue` answers with. Two different questions — "how light does this look to
 *  an eye" and "will a difference here be counted as content" — with different weights. */
export const pilL = (hex: string): number => {
  const m = hex.replace('#', '');
  if (m.length !== 6) return 0;
  const v = [0, 2, 4].map((i) => parseInt(m.slice(i, i + 2), 16));
  return (0.299 * v[0] + 0.587 * v[1] + 0.114 * v[2]) / 255;
};

/** A PLANE OF THE SAME MATERIAL, set one step off the tone it is cut from — the film's own paper in
 *  shadow, or its own dark given a lift. For a card, a dressed face, a recessed well: anything the eye
 *  should read as MORE OF THE SAME SURFACE at another depth, rather than as a different material.
 *
 *  Registers derived these by mixing the surface TOWARD THE INK, which stays in the palette only while
 *  ground and ink share a temperature. They usually do not, and then the two cancel: measured on a
 *  cream/navy film, `mix('#FBF8F1', '#101A33', 0.16)` came out (213,212,211) — 12° off the paper's hue
 *  with 76% of its saturation gone, the one neutral mass on a page whose every other tone is one hue's
 *  tints and shades. Exposure moves; hue does not.
 *
 *  The direction is asked of the TONE ITSELF, not of the film: a dark plate on a light film is still set
 *  back rather than pushed past white, and the step stays visible at either end. This is the plane rule —
 *  a FAINT INK MARK (an inactive rule, a disabled glyph) is not a plane and is still derived toward the
 *  ink, because it really is ink. */
export const plane = (tone: string, step: number): string =>
  (pilL(tone) > 0.5 ? shade(tone, step) : tint(tone, step));

/** The step a filled region must clear to READ as a region rather than as the ground. */
export const TONE_MIN_STEP = 0.10;

/**
 * A filled region derived from the ground toward `toward`, mixed far enough to actually separate.
 *
 * WHY THIS IS DERIVED AND NOT A CONSTANT. Registers pick a mix fraction by eye and it is systematically too
 * small: measured on the six sparsest registers a delivered film used, two of them (VersusSplit, CardStack3D)
 * span more than half the frame and still ink at 3% — every region they paint sits within 0.10 of the ground,
 * so the composition is there and invisible. VersusSplit's own comment records the reasoning that produced
 * it: a mix of 0.22 was cut to 0.11 because it "lit the whole frame far brighter than the rest of a dark
 * film". That premise is now false — the reference launch films span 0.270 to 0.903 in luminance, this
 * runtime gives every beat its own ground, and the delivery gate REWARDS a film whose light moves.
 *
 * So the fraction is walked up a ladder until the result is measurably a different surface, and no further:
 * `minStep` in the instrument's own colour model, never a number chosen by eye. Hue comes from `toward`, so
 * a register keeps its own colour argument; only separation is enforced.
 */
/** sRGB relative luminance — the EYE's model, for legibility decisions. Distinct from `pilL`, which is the
 *  density instrument's model; using the instrument's weights to pick ink would optimise for the gate. */
export const relLum = (hex: string): number => {
  const m = hex.replace('#', '');
  if (m.length !== 6) return 0;
  const c = [0, 2, 4].map((i) => parseInt(m.slice(i, i + 2), 16) / 255);
  const f = c.map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
};

/**
 * The most legible of `candidates` ON `bg`, by MEASURED contrast.
 *
 * WHY MEASURED AND NOT THRESHOLDED. The tempting shortcut is to branch on how far a fill was mixed — "if the
 * overlay alpha is past half, use the dark ink". A review of this codebase caught exactly that in another
 * register: an ink picked from an overlay's alpha rather than from the composited luminance left two of
 * three labels unreadable, because alpha is not tone. This asks the only question that matters.
 */
export const readableOn = (bg: string, ...candidates: string[]): string => {
  // A CALL WITH NO CANDIDATES RETURNED `undefined`, AND `undefined` IS SILENT. React drops a style property
  // whose value is undefined, so the element inherits — which for a bare `color` is BLACK. SourceDeal wrote
  // `readableOn(SURF)` as the repair for conclusions that were black on a dark surface, and the repair
  // reproduced the defect it was fixing: 1.14:1, measured off the rendered frame. A picker that cannot
  // answer must not answer with nothing, so a caller that names no candidates gets the light/dark pair it
  // plainly meant.
  const list = candidates.length ? candidates : ['#ffffff', '#0b0f17'];
  const b = relLum(bg);
  let best = list[0], bestC = -1;
  for (const c of list) {
    const y = relLum(c);
    const ratio = (Math.max(y, b) + 0.05) / (Math.min(y, b) + 0.05);
    if (ratio > bestC) { bestC = ratio; best = c; }
  }
  return best;
};

/** WCAG contrast between two colours. */
export const contrastOf = (a: string, b: string): number => {
  const x = relLum(a), y = relLum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

/**
 * The ink most legible across SEVERAL grounds at once — for an element that straddles a division.
 *
 * `readableOn` maximises contrast against one surface, which is the wrong question for a centred title over
 * a diptych: it will happily pick an ink that is excellent on one half and invisible on the other. Measured
 * on VersusSplit, whose title is centred across its seam, a literal `#aeb6ca` read 2.51:1 on the dark key
 * and 1.07:1 on the light one. This maximises the WORST case instead, which is the only one a viewer sees.
 */
export const readableOnAll = (bgs: string[], ...candidates: string[]): string => {
  let best = candidates[0], bestWorst = -1;
  for (const c of candidates) {
    const worst = Math.min(...bgs.map((b) => contrastOf(c, b)));
    if (worst > bestWorst) { bestWorst = worst; best = c; }
  }
  return best;
};

/**
 * A SECOND ink tier on `bg` — dimmer than `ink`, but never below `minRatio`.
 *
 * WHY A FLOOR AND NOT A FRACTION. A fixed mix toward the ground is a contrast bet that depends on how light
 * the ground is, and it loses on exactly the grounds this work is introducing: mixing a strong ink 28%
 * toward a mid-blue half took a register's secondary text from 4.54:1 to 2.57:1, measured on the render.
 * This dims as far as the floor allows and stops there, so "secondary" never becomes "unreadable" on a
 * surface the author has not seen yet.
 */
export const dimOn = (bg: string, ink: string, minRatio: number = 4.5): string => {
  let best = ink;
  for (let f = 0.06; f <= 0.7 + 1e-9; f += 0.04) {
    const c = mix(ink, bg, f);
    if (contrastOf(c, bg) < minRatio) break;
    best = c;
  }
  return best;
};

/**
 * A CONTAINER FILL that keeps its hue and is guaranteed to be a surface.
 *
 * The failure this fixes is library-wide, not per-register: all eight DNA presets define `surface` — the
 * documented container fill — within 0.083 of their own `bg` in the density instrument's colour model, and
 * `editorial` within 0.020. Every panel, card and plate painted straight from that token is a container the
 * measurement cannot see, and mostly one an eye cannot either.
 *
 * The token is NOT simply raised — that was tried and rejected: a global step of 0.16 moved four
 * container-bearing registers by +0.0 to +0.8 points, because the shift is wrong for a light film, wrong
 * for a chromatic ground, and changes every existing frame. This derives the fill from the ground the
 * container is ACTUALLY on, pushing `hint` away along whichever pole has room so the hue survives and the
 * step is met. A register asks for it where it paints; nothing changes underneath one that does not.
 */
export const SURFACE_HEADROOM = 1.5;

/** ...with HEADROOM by default, because the reference drifts. The step is measured against a ground TOKEN,
 *  while the instrument measures against the rendered frame's own median — and those differ: a register
 *  painting `bgGrad` (a radial field, not a flat fill) had a median of 0.067 where its `bg` token is 0.027,
 *  and the median then rose again as the cards themselves lifted it. Derived to exactly 0.10, a card face
 *  covering 26% of the frame missed being counted by 0.007. A container should clear the line, not sit on
 *  it. */
export const surfaceOn = (ground: string, hint: string,
                          minStep: number = TONE_MIN_STEP * SURFACE_HEADROOM): string => {
  const g = pilL(ground);
  if (Math.abs(pilL(hint) - g) >= minStep) return hint;      // already a surface — leave the author's colour
  const pole = readableOn(ground, '#ffffff', '#05070c');
  for (let f = 0.06; f <= 0.9 + 1e-9; f += 0.03) {
    const c = mix(hint, pole, f);
    if (Math.abs(pilL(c) - g) >= minStep) return c;
  }
  // ...and SAY WHICH of the two is the problem. This blamed the ground in every case, so a caller handed a
  // non-solid `surface` — `rgba(255,255,255,0.05)`, which looks exactly like this library's glass panels —
  // read it as "your ground is at the pole" and went looking in the wrong place.
  const solid = /^#([0-9a-f]{3,8})$/i.test(hint.trim());
  throw new Error(`surfaceOn(): ${hint} cannot be pushed off ${ground} by ${minStep} — `
    + (solid ? 'the ground is at the pole, so a container needs a different colour, not more of this one.'
             : 'that is not a solid colour. A container fill is mixed toward a pole, which a translucent '
               + 'rgba()/hsla() cannot be; give the DNA a hex `surface`.'));
};

/**
 * TWO filled regions that separate FROM EACH OTHER, for a shot whose argument is a division.
 *
 * WHY A SECOND FUNCTION. Ink is measured against the frame's OWN median, so when two regions cover the whole
 * frame the median lands between them and each is only half the pair's difference away from it. Deriving
 * both from the ground therefore changes nothing: VersusSplit spans 53% of the frame, and separating each
 * half from the ground moved it from 3.2% to 3.3%. What has to separate is the PAIR — by twice the step, so
 * each side clears it against the midpoint they create.
 */
export const separatedPair = (ground: string, towardA: string, towardB: string,
                              minStep: number = TONE_MIN_STEP): [string, string] => {
  const a = separated(ground, towardA, minStep * 0.8);
  const need = minStep * 2.2;
  try {
    return [a, separated(a, towardB, need)];
  } catch {
    // HUE CANNOT ALWAYS CARRY THE SEPARATION, so exposure does. Measured: on #0a0c12 the first half lands
    // at #18223a and the second accent #b8412e is only 0.21 away at full mix — under the 0.22 two regions
    // covering a frame need. Rather than throw on a legitimate pair of accents, separate by LIGHTNESS
    // toward whichever pole has headroom and put the hue back as a light tint, so the register keeps its
    // colour argument and the two sides still read as two.
    // ...AND ON A LIGHT GROUND THE TINT IS WHERE THE FILM'S PALETTE LEAKS. This path lifts toward a pole
    // and puts the hue back as a 12% wash, which on a dark ground reads as "the accent, dimmed". On PAPER
    // the two accents sit on OPPOSITE sides of the ground by construction (measured on a real film: 深蓝
    // 8.41:1 and 青绿 1.59:1 on #F2EDE3), so the normal path cannot separate them and every light film
    // lands here — where a grey lifted toward the ground plus 12% of a hue is neither accent. Measured on
    // that film: cold grey + sage green, two hues its DNA never declares, across the only three non-paper
    // frames it had. So on a light ground the pair separates by EXPOSURE ALONG ONE HUE — the same accent,
    // near and far — which keeps both halves inside the palette and still reads as two regions.
    const light = pilL(ground) > 0.5;
    if (light) {
      // ...AND THE NEAR HALF IS THE PAPER, not a short step toward the accent. Walking 8% from a WARM
      // ground toward a COLD accent does not read as "a little of the accent" — it passes straight
      // through neutral and stops there: measured on a cream/navy film the near half landed at
      // (215,216,218), hue 220° with CHROMA 3, a dead cold grey covering half the frame while the page
      // under it is hue 40° chroma 15. Two small steps toward the same accent cannot both stay in the
      // palette, because the first one is spent crossing the ground's own hue.
      // So the near region is a `plane` of the ground — exposure moves, hue does not — and the accent
      // is carried by the FAR one alone. Measured after: near (223,218,209) hue 38.6° chroma 14 (the
      // page's own cast), far (150,161,189) hue 223° — and the two are still 0.226 of PIL L apart,
      // marginally MORE than the 0.223 the neutral pair had, so they read as two regions exactly as
      // before. Same rule as `plane`'s own header: a region cut from a surface keeps that surface's hue.
      const near = plane(ground, minStep * 0.8);
      const far = separated(near, towardA, need);          // the accent, carried by ONE half
      return [near, far];
    }
    const pole = readableOn(a, '#ffffff', '#05070c');
    const b0 = separated(a, pole, need);
    const tinted = mix(b0, towardB, 0.12);
    return [a, Math.abs(pilL(tinted) - pilL(a)) >= need ? tinted : b0];
  }
};

export const separated = (ground: string, toward: string,
                          minStep: number = TONE_MIN_STEP, max: number = 0.85): string => {
  const g = pilL(ground);
  for (let f = 0.08; f <= max + 1e-9; f += 0.03) {
    const c = mix(ground, toward, f);
    if (Math.abs(pilL(c) - g) >= minStep) return c;
  }
  // The ladder ran out: `toward` is the ground's own value. Fail loud — a register asking for a second
  // surface and silently getting the ground back is the invisible-container failure this exists to end.
  throw new Error(`separated(): mixing ${ground} toward ${toward} never reaches a ${minStep} step in the `
    + 'density model — they are the same tone, so this would paint a region that is not there.');
};

/** Rotate a colour's HUE by `deg`, keeping its saturation/lightness — how a one-accent DNA grows a whole
 *  illustration palette that still belongs to the film. */
export const rotate = (c: string, deg: number): string => {
  const P = _hex(c);
  if (!P) return c;
  const [r, g, b] = P.map((v) => v / 255) as [number, number, number];
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
  let h = 0;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  if (d !== 0) {
    h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    h *= 60;
  }
  h = (((h + deg) % 360) + 360) % 360;
  const C = (1 - Math.abs(2 * l - 1)) * s, X = C * (1 - Math.abs(((h / 60) % 2) - 1)), m2 = l - C / 2;
  const seg6 = Math.floor(h / 60) % 6;
  const rgb: [number, number, number] = [[C, X, 0], [X, C, 0], [0, C, X], [0, X, C], [X, 0, C], [C, 0, X]][seg6] as [number, number, number];
  return _out((rgb[0] + m2) * 255, (rgb[1] + m2) * 255, (rgb[2] + m2) * 255);
};

/** N distinct, film-coherent hues for an illustration register: the DNA's two accents first (they ARE the film's
 *  identity), then hue-rotations of the accent that stay in its saturation/lightness world. `null` DNA → null, so
 *  a shot keeps its own hand-picked palette when no DNA is active (backward compatible). */
// Extra tones step along the ladder BETWEEN the two DNA hues, light and dark — never outside them.
// (mix ratio across the accent→accent2 arc, lightness delta: + tints, − shades.)
const _PAL_LADDER: [number, number][] = [
  [0.30, 0.44], [0.70, -0.38], [0.50, 0.70], [0.50, -0.62], [0.15, 0.14], [0.85, -0.14],
];
export const dnaPalette = (dna: DesignDNA | null, n: number): string[] | null => {
  if (!dna) return null;
  const seed = [dna.accent, dna.accent2].filter(Boolean) as string[];
  if (!seed.length) return null;
  const out: string[] = [];
  for (let i = 0; i < n; i++) {
    if (i < seed.length) { out.push(seed[i]); continue; }
    // A film's palette IS its two DNA hues. Growing it by rotating hue (the old rotate(base, 47°)) walked
    // straight out of the system: on the green+amber `data` DNA tone 3 landed on cyan-blue (197°), which is
    // how a blue tile turned up in a green/amber film. Derive inside the seeds instead — a category stays
    // distinguishable without introducing a colour the film never declared.
    const [ratio, dl] = _PAL_LADDER[(i - seed.length) % _PAL_LADDER.length];
    const base = seed.length > 1 ? mix(seed[0], seed[1], ratio) : seed[0];
    // Lift toward the film's own INK and press toward its own GROUND — not pure white/black. A tone shaded
    // to black on a dark film is invisible; this keeps every derived tone inside the system AND legible on
    // the ground it will be drawn on (measured: >=88 RGB from bg on every preset).
    out.push(dl >= 0 ? mix(base, dna.fg, dl) : mix(base, dna.bg, -dl));
  }
  return out;
};
