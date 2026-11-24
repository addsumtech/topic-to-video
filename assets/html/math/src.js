// MATHS THAT MOVES, ON A FILM PAGE — the director path's typeset equations. Bundled by scripts/build_math_page.sh into
// assets/html/math.js (window.MathFilm), loaded from file:// with a plain <script>.
//
// ONE COPY OF THE CRAFT. The typesetting (scripts/tex_glyphs.mjs, MathJax 3.2.2 glyph outlines) and the animation
// (remotion/src/runtime/mathCore.ts: Manim's Write, TransformMatchingTex, Indicate, the live number) are the Remotion
// tier's, imported here as they are: their timings were tuned on rendered frames (a mid-transform frame "with holes in
// it", stroke widths on superscripts), and a re-implementation from their description would lose that. This file adds
// only what a page needs: the equations a film typeset (`_math/equations.js`, written by `scripts/mathtex.py
// <film_dir>` from the film's math.json), a timeline for a derivation, and an SVG renderer that is a pure function of
// its input, so `window.seek(t)` draws the same frame every time.
import {placeAll, matchGlyphs, writeState, transformState, stillState, indicate, unionBox, glyphsOf, liveDraws,
  liveText, parseLive, segOf, smooth, pivotX} from '../../../remotion/src/runtime/mathCore.ts';
import {parsePath, transformSegs, segsToD} from '../../../remotion/src/runtime/pathCore.ts';
import {mathKey, normTex, MATH_FORMAT} from '../../../remotion/src/runtime/mathKey.ts';

const NS = 'http://www.w3.org/2000/svg';

/** The typeset equation for `tex`, from `_math/equations.js`. Throws by name when the film never typeset it. */
export function eq(tex, display = true) {
  const t = normTex(tex);
  if (!t) throw new Error('MathFilm.eq: empty TeX');
  const e = (window.MATH_EQ || {})[mathKey(t, display)];
  if (!e) {
    throw new Error(`MathFilm: TeX not typeset: ${JSON.stringify(t)}${display ? '' : ' (inline)'} — list it in the film's ` +
      'math.json, run `python3 scripts/mathtex.py <film_dir>`, and load _math/equations.js before the page script');
  }
  if (e.v !== MATH_FORMAT || e.tex !== t) throw new Error(`MathFilm: _math holds ${JSON.stringify(e.tex)} for ` +
    `${JSON.stringify(t)} — stale or colliding; re-run scripts/mathtex.py`);
  return e;
}

const rising = (w, name) => {
  if (!Array.isArray(w) || w.length !== 2 || !(w[1] > w[0])) {
    throw new Error(`MathFilm.derivation: ${name} must be a [start, end] window in seconds, end after start; got ` +
      JSON.stringify(w));
  }
  return w;
};

// What travels from one form to the next. Measured on the first real derivation (quadratic formula, 2026-11-24):
// matching every shared character in reading order sent marks across the frame THROUGH other marks — the a of ax²
// sliding through x² to become a denominator — half a second of "glyph soup" per step. Limiting unnamed marks to short
// moves then left faint double images instead ("x x++", an x fading out beside the x fading in). What made the soup was
// the ORDER changing, not the distance. So by default ('named') a mark travels when it is the same named term in both
// forms (\class{name}{…}: it may change order, and lifts over the "=" as one piece), or when it keeps its reading order
// with the other travellers however far it goes; a mark that would pass through others fades out and in.
//   'named' (default) · 'all' (every shared mark travels: mathCore's own matching) · 'fade' (nothing travels)
const innermost = (g) => { for (let i = g.k.length - 1; i >= 0; i--) if (!/^live/.test(g.k[i])) return g.k[i]; return null; };
const filterMatch = (m, A, B, mode) => {
  if (mode === 'all') return m;
  if (mode !== 'named' && mode !== 'fade') throw new Error(`MathFilm: a step's match is 'named', 'all' or 'fade', got ${JSON.stringify(mode)}`);
  const keep = [], out = [...m.out], inn = [...m.in];
  for (const pr of m.pairs) {
    const ka = innermost(A.glyphs[pr.a]);
    const ok = mode === 'named' && ((ka && ka === innermost(B.glyphs[pr.b])) || pr.kind === 'stay');
    if (ok) keep.push(pr); else { out.push(pr.a); inn.push(pr.b); }
  }
  return {pairs: keep, out, in: inn};
};

// A named term that changes sides of the relation sign (or changes order with another named term) LIFTS AS ONE PIECE:
// one arc from the term's own box, timed by its first glyph, over the "=" — instead of mathCore's per-glyph arc, which
// lifted a fraction's numerator but slid its bar and denominator straight through the "=" (the quadratic-formula proof
// film, 2026-11-24). Done here, on mathCore's output with its own arc off, so the Remotion tier's runtime (and the
// measurements taken of its registers) stays untouched. The term's glyphs are adjacent in the match's order, so their
// horizontal stagger differs by under a frame and they travel together.
const termLifts = (A, pa, B, pb, m) => {
  const side = (eq, pl, box) => {
    const pv = pivotX(eq);
    return pv === null ? null : Math.sign((box[0] + box[2]) / 2 - (pl.x + pv * pl.s));
  };
  const groups = new Map();
  m.pairs.forEach((pr, r) => {
    const k = innermost(A.glyphs[pr.a]);
    if (k && k === innermost(B.glyphs[pr.b])) groups.set(k, [...(groups.get(k) || []), r]);
  });
  const lifts = [];
  groups.forEach((rs) => {
    const ba = unionBox(A, rs.map((r) => m.pairs[r].a), pa), bb = unionBox(B, rs.map((r) => m.pairs[r].b), pb);
    const sa = side(A, pa, ba), sb = side(B, pb, bb);
    if (!(sa !== null && sb !== null && sa !== sb) && !rs.some((r) => m.pairs[r].kind === 'move')) return;
    lifts.push({ids: new Set(rs.map((r) => `p${m.pairs[r].a}_${m.pairs[r].b}`)), dx: (bb[0] + bb[2]) / 2 - (ba[0] + ba[2]) / 2,
      hgt: Math.max(ba[3] - ba[1], bb[3] - bb[1]), rank: Math.min(...rs)});
  });
  return lifts;
};
const lifted = (draws, lifts, nPairs, p, arcK = 0.35) => {
  if (!lifts.length) return draws;
  const n = Math.max(1, nPairs);
  return draws.map((d) => {
    const id = d.id.replace(/[AB]$/, '');
    const L = lifts.find((l) => l.ids.has(id));
    if (!L) return d;
    const u = smooth(segOf(p, 0.12 + 0.14 * (L.rank / n), 0.78 + 0.14 * (L.rank / n)));
    const dy = -Math.sign(L.dx || 1) * Math.min(Math.abs(L.dx) * arcK, L.hgt * 0.9) * Math.sin(Math.PI * u);
    return {...d, m: [d.m[0], d.m[1], d.m[2], d.m[3], d.m[4], d.m[5] + dy]};
  });
};

// \color{#rrggbb}{…} in the TeX keeps ITS colour (the glyph carries it); `accent` is for what the timeline picks out.
const colourDraws = (draws, A, B) => draws.map((d) => {
  const m = /^([swabp])(\d+)(?:_(\d+))?([AB])?$/.exec(d.id);
  if (!m) return d;
  const g = m[1] === 'a' ? A.glyphs[+m[2]] : m[1] === 'p' ? (m[4] === 'A' ? A.glyphs[+m[2]] : B.glyphs[+m[3]])
    : m[1] === 'b' ? B.glyphs[+m[2]] : A.glyphs[+m[2]];
  return g && g.col ? {...d, col: g.col} : d;
});

/**
 * One derivation: `forms` (TeX, in order) set at ONE scale (the widest form decides it for all) on ONE baseline in
 * `box` (frame px), relation signs on one vertical when they fit (`align: 'equals'`; 'center'; 'left'). A form whose
 * layout should differ is the start of another derivation. Times are the film's seconds, from the voice's word times
 * (`Moments.wordTime(timeline, word)`):
 *   write      [a, b]   form 1 is written on (omit: it is there from the start)
 *   steps      one per later form: [a, b], or {at: [a, b], match: 'named' | 'all' | 'fade'} (see above)
 *   highlight  {term, at: [a, b], swell = 1.16, pad = 0.14}  a \class{term} of the LAST form ('*': the whole form)
 *              swells, takes the accent and keeps it; a frame (pad in em, clear of the swell) is drawn round it
 *   live       {term, from, to, at: [a, b]}  a \class{live…}{00.0} slot of the last form runs from one value to the other
 * Name a term the same in two forms and it travels as one piece (one arc over the "=" when it changes sides); names
 * nest, and the INNERMOST name is the one that matches, so the term a highlight needs can wrap terms that travel.
 * Returns {at(t) -> state, eqs, pl, emPx, box, tex}: `eqs[i]` the typeset forms, `pl[i]` their placements
 * ({x, y, s}: px per 1/1000 em). A state is {draws, frame, tex, emPx}; MathFilm.render(target, state) draws it.
 */
export function derivation({forms, box, em = 96, align = 'equals', display = true, write = null, steps = [],
  highlight = null, live = null}) {
  if (!Array.isArray(forms) || !forms.length) throw new Error('MathFilm.derivation: no forms');
  if (steps.length !== forms.length - 1) {
    throw new Error(`MathFilm.derivation: ${forms.length} forms need ${forms.length - 1} step(s), got ${steps.length}`);
  }
  const win = steps.map((st) => (Array.isArray(st) ? st : st && st.at));
  const mode = steps.map((st) => (Array.isArray(st) ? 'named' : (st && st.match) || 'named'));
  const eqs = forms.map((f) => eq(f, display));
  const {pl} = placeAll(eqs, box, em, align);
  const matches = eqs.slice(1).map((B, i) =>
    filterMatch(matchGlyphs(eqs[i], B, pl[i], pl[i + 1]), eqs[i], B, mode[i]));
  const lifts = matches.map((m, i) => (mode[i] === 'named' ? termLifts(eqs[i], pl[i], eqs[i + 1], pl[i + 1], m) : null));
  let prev = -Infinity;
  [write, ...win].forEach((w, i) => {
    if (!w && i === 0) return;
    rising(w, i === 0 ? 'write' : `step ${i}`);
    if (w[0] < prev - 1e-9) throw new Error('MathFilm.derivation: the write and step windows must follow each other in time');
    prev = w[1];
  });
  if (highlight) rising(highlight.at, 'highlight.at');
  if (live) rising(live.at, 'live.at');
  const last = eqs.length - 1;
  const hlIdx = highlight ? (highlight.term === '*' ? eqs[last].glyphs.map((_, i) => i) : glyphsOf(eqs[last], highlight.term)) : [];
  if (highlight && !hlIdx.length) {
    throw new Error(`MathFilm.derivation: no \\class{${highlight.term}}{…} in the last form ${JSON.stringify(forms[last])}`);
  }
  if (live) { parseLive(live.from); parseLive(live.to); }
  const emPx = pl[0].s * 1000;
  return {
    eqs, pl, box, tex: normTex(forms[last]), emPx,
    at(t) {
      let cur = 0;
      win.forEach((w, i) => { if (t >= w[1]) cur = i + 1; });
      const active = win.findIndex((w) => t >= w[0] && t < w[1]);
      let draws;
      if (active >= 0) {
        const p = segOf(t, win[active][0], win[active][1]), L = lifts[active];
        draws = transformState(eqs[active], pl[active], eqs[active + 1], pl[active + 1], matches[active], p,
          L ? {arc: 0} : {});
        if (L) draws = lifted(draws, L, matches[active].pairs.length, p);
        draws = colourDraws(draws, eqs[active], eqs[active + 1]);
      } else if (write && cur === 0 && t < write[1]) {
        draws = colourDraws(writeState(eqs[0], pl[0], segOf(t, write[0], write[1])), eqs[0], eqs[0]);
      } else {
        draws = colourDraws(stillState(eqs[cur], pl[cur], 's'), eqs[cur], eqs[cur]);
      }
      let frame = null;
      if (active < 0 && cur === last) {
        if (live) {
          const slot = new Set(glyphsOf(eqs[last], live.term).map((i) => `s${i}`));
          draws = draws.filter((d) => !slot.has(d.id))
            .concat(liveDraws(eqs[last], pl[last], live.term, liveText(live.from, live.to, segOf(t, live.at[0], live.at[1]))));
        }
        if (highlight && t >= highlight.at[0]) {
          const b = unionBox(eqs[last], hlIdx, pl[last]);
          const p = segOf(t, highlight.at[0], highlight.at[1]);
          const swell = highlight.swell ?? 1.16;
          draws = indicate(draws, new Set(hlIdx.map((i) => `s${i}`)), b, p, swell);
          // the frame clears the term at its largest, not at rest (it cut through x and 4ac on the proof film)
          const gx = (b[2] - b[0]) * (swell - 1) / 2, gy = (b[3] - b[1]) * (swell - 1) / 2;
          frame = {box: [b[0] - gx, b[1] - gy, b[2] + gx, b[3] + gy], p: smooth(segOf(p, 0, 0.7)),
            pad: (highlight.pad ?? 0.14) * emPx};
        }
      }
      // the form on screen (while one becomes the next, the one it is becoming): what the page checks name
      return {draws, frame, tex: normTex(forms[active >= 0 ? active + 1 : cur]), emPx};
    },
  };
}

/**
 * One equation placed at a POINT (a label on a picture): `x, y` is where its baseline starts (`anchor: 'left'`), or
 * its centre on the baseline (`'center'`), at `em` px. `write: [a, b]` writes it on. Returns {eq, pl, emPx, at(t)};
 * render it into its OWN target (one equation per <svg> or <g>).
 */
export function label(tex, {x, y, em = 64, anchor = 'left', display = false, write = null} = {}) {
  const e = eq(tex, display);
  const s = em / 1000;
  if (!(s > 0)) throw new Error('MathFilm.label: em must be positive');
  if (anchor !== 'left' && anchor !== 'center') throw new Error(`MathFilm.label: anchor is 'left' or 'center'`);
  const x0 = anchor === 'left' ? x - e.ink[0] * s : x - ((e.ink[0] + e.ink[2]) / 2) * s;
  const pl = {x: x0, y: y - e.base * s, s};
  if (write) rising(write, 'write');
  return {
    eq: e, pl, emPx: em, tex: normTex(tex),
    at(t) {
      const draws = write && t < write[1] ? writeState(e, pl, segOf(t, write[0], write[1])) : stillState(e, pl, 's');
      return {draws: colourDraws(draws, e, e), frame: null, tex: normTex(tex), emPx: em};
    },
  };
}

// ── RENDER ───────────────────────────────────────────────────────────────────────────────────────────────────────
const PARSED = new Map();
const bake = (d, m) => {
  let s = PARSED.get(d);
  if (!s) { s = parsePath(d); PARSED.set(d, s); }
  return segsToD(transformSegs(s, m));
};
const HEX = /^#([0-9a-f]{6})$/i;
const mixHex = (a, b, u) => {
  if (!HEX.test(a) || !HEX.test(b)) return `color-mix(in srgb, ${b} ${(u * 100).toFixed(1)}%, ${a})`;   // a named colour
  const A = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16)), B = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return '#' + A.map((v, i) => Math.round(v + (B[i] - v) * u).toString(16).padStart(2, '0')).join('');
};
const frameD = (box, pad, r0) => {
  const x0 = box[0] - pad, y0 = box[1] - pad, x1 = box[2] + pad, y1 = box[3] + pad;
  const r = Math.max(0, Math.min(r0, (x1 - x0) / 2, (y1 - y0) / 2)), cx = (x0 + x1) / 2;
  return `M${cx} ${y0}H${x1 - r}A${r} ${r} 0 0 1 ${x1} ${y0 + r}V${y1 - r}A${r} ${r} 0 0 1 ${x1 - r} ${y1}` +
    `H${x0 + r}A${r} ${r} 0 0 1 ${x0} ${y1 - r}V${y0 + r}A${r} ${r} 0 0 1 ${x0 + r} ${y0}H${cx}`;
};

/**
 * Draw a state into `svg` (an <svg> covering the frame, in frame px, or a <g> inside one; one equation per target). Every attribute is set from the state each call,
 * so the frame depends on nothing but its input. The glyphs sit in one <g data-math="<tex>">: the page checks read it
 * as a line of text (page_overlap_qa), its box the union of the glyphs.
 */
export function render(svg, state, {ink = '#111111', accent = '#e8590c', strokePx = null} = {}) {
  let g = svg.__mathG;
  if (!g) { g = document.createElementNS(NS, 'g'); svg.appendChild(g); svg.__mathG = g; svg.__mathPaths = new Map(); }
  g.setAttribute('data-math', state.tex);
  g.setAttribute('aria-label', state.tex);
  const paths = svg.__mathPaths, seen = new Set();
  const sw = strokePx ?? Math.max(1.2, state.emPx * 0.022);
  const put = (id, attrs) => {
    let p = paths.get(id);
    if (!p) { p = document.createElementNS(NS, 'path'); paths.set(id, p); }
    for (const k of ['stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray', 'stroke-dashoffset', 'pathLength',
      'stroke-linejoin', 'stroke-linecap', 'fill', 'fill-opacity', 'opacity']) p.removeAttribute(k);
    for (const [k, v] of Object.entries(attrs)) p.setAttribute(k, String(v));
    g.appendChild(p);                       // re-appended in draw order every frame: the order is part of the state
    seen.add(id);
  };
  for (const d of state.draws) {
    const strokeVis = d.stroke > 0 ? d.strokeOp : 0;
    const vis = Math.max(d.fill, strokeVis);
    if (!(vis > 0.002)) continue;
    const hi = d.col || accent;            // a glyph the TeX coloured keeps its colour; the timeline's accent otherwise
    const col = d.accent >= 1 ? hi : d.accent <= 0 ? ink : mixHex(ink, hi, d.accent);
    const a = {d: bake(d.d, d.m), fill: col, 'fill-opacity': Math.min(1, d.fill / vis), opacity: vis};
    if (strokeVis > 0) {
      Object.assign(a, {stroke: col, 'stroke-opacity': Math.min(1, strokeVis / vis), 'stroke-width': sw,
        'stroke-linejoin': 'round', 'stroke-linecap': 'round'});
      if (d.stroke < 1) Object.assign(a, {pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 1 - d.stroke});
    }
    put(d.id, a);
  }
  if (state.frame && state.frame.p > 0) {
    const pad = state.frame.pad ?? state.emPx * 0.14;
    put('frame', {d: frameD(state.frame.box, pad, pad), fill: 'none', stroke: accent, 'stroke-width': sw * 1.6,
      'stroke-linecap': 'round', pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 1 - state.frame.p});
  }
  for (const [id, p] of paths) if (!seen.has(id) && p.parentNode) p.parentNode.removeChild(p);
}

/** The raw moves, for a film that composes its own (each a pure function of its inputs; see mathCore.ts). */
export const core = {placeAll, matchGlyphs, writeState, transformState, stillState, indicate, unionBox, glyphsOf,
  liveDraws, liveText, segOf, smooth};
