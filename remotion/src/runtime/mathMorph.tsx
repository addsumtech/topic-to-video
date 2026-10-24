// TYPESET MATHS THAT MOVES — the equation a STEM beat is about, drawn from its real glyph outlines and animated in the
// ways a maths explainer needs: written on, transformed into its next form, a term picked out, a number running live.
//
// WHY THIS EXISTS. This library set its one equation register (`CompressedSensingEq`) as a hand-typed Unicode string —
// `min‖Ψx‖₁` in a text face — which is neither typeset maths (no real fractions, sums, roots, scripts) nor something
// that can move like maths: a derivation is a sequence of FORMS of one expression, and what teaches is watching the
// parts that stay travel to their new places while the rest changes. Manim built its whole vocabulary on that.
//
// THE PIPELINE. The film's TeX is typeset ONCE, before the render, by scripts/tex_glyphs.mjs (MathJax 3.2.2, its TeX
// fonts): every glyph's outline and the matrix MathJax set it with. The library's own equations ship in
// `mathLibrary.json` (bundled, so every library render is offline); a film's arrive as `<out_dir>/_math/<key>.json`
// (scripts/mathtex.py writes them; the film's renders serve its out_dir as the public dir). `useEquations` reads
// either, and a TeX nobody typeset fails the render by NAME rather than drawing nothing.
//
// THE ANIMATION is runtime/mathCore.ts — pure functions of the equation and a progress value, so a frame is a function
// of the frame. This file only fetches, bakes each glyph's matrix into its outline (so a stroke is the same width on a
// superscript as on a big operator, and the draw-on dash is measured on the real outline), and marks the DOM so the
// type gates can read an equation as the line it is (runtime/mathDom MATH_ROOT).
import React from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';
import LIBRARY from './mathLibrary.json';
import {MATH_FORMAT, mathKey, normTex} from './mathKey';
import {parsePath, transformSegs, segsToD, type Seg} from './pathCore';
import {kineticBusy} from './kineticDom';
import {MATH_GLYPH, MATH_ROOT} from './mathDom';
import {drawOn} from './draw';
import {mix} from './dna';
import type {Equation, GDraw, Mat6} from './mathCore';

export * from './mathCore';

const LIB = (LIBRARY as unknown as {eq: Record<string, Equation>}).eq;
const FETCHED = new Map<string, Equation>();

/** Where a film's typeset equations live, relative to its public dir (its out_dir). */
export const MATH_DIR = '_math';

const missing = (tex: string, key: string) => new Error(
  `TeX not typeset: ${JSON.stringify(tex)} (key ${key}). Run \`python3 scripts/mathtex.py <out_dir>\` — it typesets ` +
  `every equation the storyboard names into <out_dir>/${MATH_DIR}/ — or, for a library register's own default, add it ` +
  'to remotion/src/runtime/mathLibrary.tex.json and run `node scripts/tex_glyphs.mjs --library`.');

/** True when the library bundle already carries this TeX (a register's own defaults must). */
export const inLibrary = (tex: string, display = true): boolean => !!LIB[mathKey(tex, display)];

/**
 * The typeset forms of `texs`, in order — or null for the first frames while a film's files are fetched (the render
 * waits on them: a delayRender, and the same pending count every type audit awaits, so no audit walks a frame the
 * equations have not reached yet). Throws on an empty TeX; cancels the render on a TeX nobody typeset.
 */
export function useEquations(texs: string[], display = true): Equation[] | null {
  const norm = texs.map((t) => normTex(t));
  norm.forEach((t, i) => {
    if (!t) throw new Error(`useEquations: equation ${i + 1} is empty — every form needs its TeX`);
  });
  const sig = `${display ? 'D' : 'T'}|${norm.join('\u0000')}`;
  const keys = React.useMemo(() => norm.map((t) => mathKey(t, display)), [sig]);    // eslint-disable-line
  const present = () => keys.every((k) => LIB[k] || FETCHED.has(k));
  const [ready, setReady] = React.useState(present);
  const [handle] = React.useState<number | null>(() => {
    if (present()) return null;
    kineticBusy(1);
    return delayRender(`typeset maths: ${norm[0].slice(0, 40)}`, {timeoutInMilliseconds: 30000});
  });
  const released = React.useRef(false);
  React.useEffect(() => {
    if (handle === null) return;
    let live = true;
    Promise.all(keys.map(async (k, i) => {
      if (LIB[k] || FETCHED.has(k)) return;
      const r = await fetch(staticFile(`${MATH_DIR}/${k}.json`));
      if (!r.ok) throw missing(norm[i], k);
      const j = (await r.json()) as Equation;
      if (j.v !== MATH_FORMAT || j.tex !== norm[i]) {
        throw new Error(`${MATH_DIR}/${k}.json holds ${JSON.stringify(j.tex)}, not ${JSON.stringify(norm[i])} — stale ` +
          'or colliding; re-run scripts/mathtex.py');
      }
      FETCHED.set(k, j);
    })).then(() => { if (live) setReady(true); }).catch((e) => cancelRender(e));
    return () => { live = false; };
  }, [handle, keys]);        // eslint-disable-line
  React.useEffect(() => {
    // released only once the glyphs are COMMITTED (this effect runs after the render that drew them)
    if (ready && handle !== null && !released.current) {
      released.current = true;
      kineticBusy(-1);
      continueRender(handle);
    }
  }, [ready, handle]);
  React.useEffect(() => () => {
    if (handle !== null && !released.current) { released.current = true; kineticBusy(-1); }
  }, [handle]);
  // `present()` too: a TeX that CHANGED after mount (a studio edit) has nothing fetched for it — draw nothing rather
  // than hand a register an undefined equation
  if (!ready || !present()) return null;
  return keys.map((k) => LIB[k] ?? FETCHED.get(k)!);
}

// Parsing an outline is the costly part and the outlines are a small fixed set per film; the matrix changes per frame.
const PARSED = new Map<string, Seg[]>();
const parsed = (d: string): Seg[] => {
  let s = PARSED.get(d);
  if (!s) {
    s = parsePath(d);
    if (PARSED.size > 4096) PARSED.clear();
    PARSED.set(d, s);
  }
  return s;
};
/** A glyph's outline with its matrix applied: frame px. */
export const bake = (d: string, m: Mat6): string => segsToD(transformSegs(parsed(d), m));

/**
 * The glyphs of one frame. `ink` / `accent` colour them (a glyph's `accent` 0..1 mixes between); `strokePx` is the
 * outline width a Write draws with. `tex` is the line's text for every gate; `emPx` its em in px (the gates' sense of
 * its size). The layer covers the frame and draws nothing outside its glyphs.
 */
export const MathLayer: React.FC<{draws: GDraw[]; tex: string; emPx: number; W: number; H: number; ink: string;
  accent: string; strokePx?: number; id?: string}> = ({draws, tex, emPx, W, H, ink, accent, strokePx, id}) => {
  const sw = strokePx ?? Math.max(1.2, emPx * 0.022);
  return (
    <div {...{[MATH_ROOT]: tex}} data-math-id={id ?? tex} aria-label={tex} style={{position: 'absolute', left: 0, top: 0,
      width: W, height: H, fontSize: emPx, pointerEvents: 'none'}}>
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {draws.map((g) => {
          const strokeVis = g.stroke > 0 ? g.strokeOp : 0;
          const vis = Math.max(g.fill, strokeVis);
          if (!(vis > 0.002)) return null;
          const col = g.accent >= 1 ? accent : g.accent <= 0 ? ink : mix(ink, accent, g.accent);
          return (
            <path key={g.id} {...{[MATH_GLYPH]: ''}} d={bake(g.d, g.m)} opacity={vis} fill={col}
              fillOpacity={Math.min(1, g.fill / vis)}
              {...(strokeVis > 0 ? {stroke: col, strokeOpacity: Math.min(1, strokeVis / vis), strokeWidth: sw,
                strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const,
                ...(g.stroke < 1 ? drawOn(g.stroke) : {})} : {})} />
          );
        })}
      </svg>
    </div>
  );
};

/** A rounded frame round a box (Circumscribe), as a path to draw on with `drawOn`. Frame px. */
export const frameAround = (box: [number, number, number, number], pad: number, radius: number): string => {
  const x0 = box[0] - pad, y0 = box[1] - pad, x1 = box[2] + pad, y1 = box[3] + pad;
  const r = Math.max(0, Math.min(radius, (x1 - x0) / 2, (y1 - y0) / 2));
  // starts top-centre and runs clockwise, so the draw-on closes where it began
  const cx = (x0 + x1) / 2;
  return `M${cx} ${y0}H${x1 - r}A${r} ${r} 0 0 1 ${x1} ${y0 + r}V${y1 - r}A${r} ${r} 0 0 1 ${x1 - r} ${y1}` +
    `H${x0 + r}A${r} ${r} 0 0 1 ${x0} ${y1 - r}V${y0 + r}A${r} ${r} 0 0 1 ${x0 + r} ${y0}H${cx}`;
};
