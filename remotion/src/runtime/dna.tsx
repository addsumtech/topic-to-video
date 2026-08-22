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
import {clamp01} from './motion';

export type DnaDecoration =
  | 'prompt' | 'status' | 'breadcrumb' | 'cursor' | 'scanline' | 'grid' | 'line-numbers';

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
};

// ── Presets ────────────────────────────────────────────────────────────────────────────────────────────────
// TERMINAL — a dark technical workspace: monospace everywhere, thin square-ish panels, green/blue accents,
// command→result→metadata hierarchy, typing/execution motion, prompt/cursor/status/scanline grammar.
export const TERMINAL_DNA: DesignDNA = {
  id: 'terminal',
  fontDisplay: '"JetBrains Mono", ui-monospace, monospace',
  fontMono: '"JetBrains Mono", ui-monospace, monospace',
  fontBody: '"JetBrains Mono", ui-monospace, monospace',
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
};

// NEUTRAL — approximates the library's CURRENT common look (dark, Inter display, mono code, blue accent, soft
// radius, smooth motion). Used as the explicit "no strong system" baseline; a migrated shot's `?? original`
// fallbacks already reproduce its own look, so this is mostly for reference / a mild default.
export const NEUTRAL_DNA: DesignDNA = {
  id: 'neutral',
  fontDisplay: 'Inter, system-ui, sans-serif',
  fontMono: '"JetBrains Mono", ui-monospace, monospace',
  fontBody: 'Inter, system-ui, sans-serif',
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
  fontDisplay: '"Playfair Display", Georgia, serif', fontMono: '"JetBrains Mono", ui-monospace, monospace',
  fontBody: 'Inter, system-ui, sans-serif',
  bg: '#12100e', bgGrad: 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)',
  fg: '#efe9df', dim: '#9a9084', accent: '#e2603f', accent2: '#c9a24b', onAccent: '#1a0f0b',
  surface: '#181512', surfaceBorder: '#33291f', line: '#2a2018',
  radius: 2, borderWidth: 1, motion: 'smooth', decoration: ['grid'], uppercaseLabels: true, labelSpacing: '0.18em',
};
// PRODUCT — a clean Apple-like keynote world: geometric sans, near-black or soft-light ground, rounded glass
// panels, soft shadows, ONE vivid accent, gentle scale/parallax reveals.
export const PRODUCT_DNA: DesignDNA = {
  id: 'product',
  fontDisplay: '"Space Grotesk", Inter, system-ui, sans-serif', fontMono: '"JetBrains Mono", ui-monospace, monospace',
  fontBody: 'Inter, system-ui, sans-serif',
  bg: '#060709', bgGrad: 'radial-gradient(120% 120% at 50% 0%, #14161d, #060709 72%)',
  fg: '#f2f5fb', dim: '#8a93a5', accent: '#5b8cff', accent2: '#a06bff', onAccent: '#050810',
  surface: '#12141c', surfaceBorder: '#262b3a', line: '#20242f',
  radius: 22, borderWidth: 1, motion: 'smooth', decoration: [], uppercaseLabels: false, labelSpacing: '0',
};
// BLUEPRINT — an engineering-drawing world: mono/geometric type, deep blueprint-blue ground, thin cyan rules +
// crop-marks + dimension lines + a measured grid, precise draw-on reveals.
export const BLUEPRINT_DNA: DesignDNA = {
  id: 'blueprint',
  fontDisplay: '"JetBrains Mono", ui-monospace, monospace', fontMono: '"JetBrains Mono", ui-monospace, monospace',
  fontBody: 'Inter, system-ui, sans-serif',
  bg: '#071018', bgGrad: 'radial-gradient(130% 120% at 50% -8%, #0b1c2b, #050b12 72%)',
  fg: '#cfe6f5', dim: '#5f7d92', accent: '#38b6ff', accent2: '#7fe0d0', onAccent: '#04121c',
  surface: '#0a1622', surfaceBorder: '#1d3a52', line: '#123048',
  radius: 3, borderWidth: 1, motion: 'mechanical', decoration: ['grid', 'line-numbers'], uppercaseLabels: true, labelSpacing: '0.12em',
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
};

// Expand a template id into a DNA preset (the fallback when meta.design_dna is not explicitly authored).
export const dnaFromTemplate = (t?: string | null): DesignDNA | null =>
  (t ? DNA_PRESETS[t] ?? null : null);

// ── Context / hook ───────────────────────────────────────────────────────────────────────────────────────────
export const DesignDNAContext = React.createContext<DesignDNA | null>(null);
export const useDNA = (): DesignDNA | null => React.useContext(DesignDNAContext);
export const dnaHas = (dna: DesignDNA | null, d: DnaDecoration): boolean => !!dna && dna.decoration.includes(d);

// ── Reusable annotation cues (LEVEL-2 grammar) ───────────────────────────────────────────────────────────────
// A blinking block caret — the terminal cursor. Deterministic (blinks on frame parity, not wall-clock).
export const Caret: React.FC<{color?: string; h?: number; w?: number; style?: React.CSSProperties}> =
  ({color, h = 26, w = 12, style}) => {
    const frame = useCurrentFrame();
    const on = Math.floor(frame / 16) % 2 === 0;
    return <span style={{display: 'inline-block', width: w, height: h, marginLeft: 4, verticalAlign: 'text-bottom',
      background: color ?? '#3dd6a4', opacity: on ? 0.95 : 0.12, ...style}} />;
  };

// A mono breadcrumb / command line, e.g. "~/hermes ▸ open-weights" — a LEVEL-2 cue a shot can drop top-left to
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
  if (!dnaHas(dna, 'grid')) return null;
  const y = (frame * 2) % (h + 200) - 100;   // slow deterministic sweep
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
export const TerminalChrome: React.FC<{dna: DesignDNA | null; path?: string; status?: string; W: number; H: number}> =
  ({dna, path, status, W, H}) => {
    const frame = useCurrentFrame();
    if (!dnaHas(dna, 'breadcrumb')) return null;
    const on = Math.floor(frame / 16) % 2 === 0;
    const mono = dna!.fontMono, dim = dna!.dim, acc = dna!.accent, ls = dna!.labelSpacing;
    return (
      <>
        {path ? (
          <div style={{position: 'absolute', top: 42, left: 60, color: dim, opacity: 0.85,
            font: `600 22px/1 ${mono}`, letterSpacing: ls, whiteSpace: 'nowrap'}}>
            <span style={{color: acc}}>~/hermes</span> <span style={{opacity: 0.6}}>▸</span> {path}</div>
        ) : null}
        {status ? (
          <div style={{position: 'absolute', top: 42, right: 60, color: dim, opacity: 0.85,
            font: `600 20px/1 ${mono}`, letterSpacing: ls, whiteSpace: 'nowrap', display: 'flex', alignItems: 'center'}}>
            <span style={{color: acc, marginRight: 8}}>●</span>{status}
            <span style={{display: 'inline-block', width: 9, height: 17, marginLeft: 7,
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
      <div style={{width: 'min(84vw, 1320px)', fontFamily: mono, textAlign: align,
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
