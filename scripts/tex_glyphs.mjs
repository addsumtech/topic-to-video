#!/usr/bin/env node
// TEX -> GLYPH PATHS, AT AUTHORING TIME — the typesetter behind runtime/mathMorph.tsx.
//
//   node scripts/tex_glyphs.mjs --out <dir> [--inline] -- '<tex>' ['<tex>' ...]   one file per equation, <dir>/<key>.json
//   node scripts/tex_glyphs.mjs --out <dir> --stdin          {"items":[{"tex": "...", "display": true}, ...]} on stdin
//   node scripts/tex_glyphs.mjs --library                    rebuild remotion/src/runtime/mathLibrary.json from
//                                                            remotion/src/runtime/mathLibrary.tex.json
//   node scripts/tex_glyphs.mjs --check '<tex>'              typeset, print a summary, write nothing
//   node scripts/tex_glyphs.mjs --svg '<tex>'                MathJax's own SVG markup (the fidelity test's reference)
//
// Prints {"written": [...], "cached": [...], "errors": [{"tex", "error"}]} and exits 2 when any TeX failed — the
// MathJax message is the error, verbatim ("Missing close brace", "Undefined control sequence \foo"). A TeX error is
// never drawn as red text the way a browser MathJax does: an equation the film did not write must not reach a frame.
//
// WHY AT AUTHORING TIME. The render is a pure function of its inputs. MathJax runs here, once per distinct TeX, and
// what the bundle reads is plain data — each glyph's outline, the matrix MathJax placed it with, its character and its
// MathML role — so a render is deterministic and offline and the bundle never carries a typesetter. The file is named
// by runtime/mathKey.ts (imported below, the same function the register looks it up by) and holds its own TeX, so a
// stale or colliding file is refused rather than drawn.
//
// MathJax: mathjax-full 3.2.2, Apache-2.0 (https://github.com/mathjax/MathJax-src), pinned in remotion/package.json.
// Its TeX fonts' outlines are what is drawn (the MathJax TeX fonts, SIL OFL 1.1 / Apache-2.0 as distributed in it).
//
// UNITS OF THE OUTPUT: 1/1000 em, y DOWN, origin at the equation box's top-left. `base` is the baseline's y.
import {createRequire} from 'module';
import fs from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
import {mathKey, normTex, MATH_FORMAT} from '../remotion/src/runtime/mathKey.ts';
import {parsePath, transformSegs, segsBBox, segsToD, flatten, matMul, ptsToD, IDENTITY} from
  '../remotion/src/runtime/pathCore.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REMOTION = path.resolve(HERE, '..', 'remotion');
const LIB_SRC = path.join(REMOTION, 'src', 'runtime', 'mathLibrary.tex.json');
const LIB_OUT = path.join(REMOTION, 'src', 'runtime', 'mathLibrary.json');
const require = createRequire(path.join(REMOTION, 'package.json'));
const MJ_VERSION = require('mathjax-full/package.json').version;
if (MJ_VERSION !== '3.2.2') {
  // the glyph outlines ARE the font: another MathJax draws different paths under the same keys
  throw new Error(`tex_glyphs.mjs is pinned to mathjax-full 3.2.2, found ${MJ_VERSION} — the cache keys assume it`);
}
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
// The TeX packages, loaded explicitly. NOT AllPackages: it carries `noundefined` (draws an unknown macro in red
// instead of failing), `noerrors` and `autoload`/`require` (which fetch extensions at run time) — each one a way for a
// film's typo to reach a frame or for a render to depend on something other than this list. `html` is here for
// \class{name}{...}: the handle a register addresses a term by (highlight, match, live number).
const PACKAGE_FILES = {base: 'Base', ams: 'Ams', newcommand: 'Newcommand', html: 'Html', boldsymbol: 'Boldsymbol',
  color: 'Color', cancel: 'Cancel', braket: 'Braket', mathtools: 'Mathtools', bbox: 'Bbox', enclose: 'Enclose',
  textmacros: 'TextMacros', unicode: 'Unicode', physics: 'Physics'};
const PACKAGES = Object.keys(PACKAGE_FILES);
for (const p of PACKAGES) require(`mathjax-full/js/input/tex/${p}/${PACKAGE_FILES[p]}Configuration.js`);

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
// formatError THROWS: the default draws the error message into the equation in red
const texIn = new TeX({packages: PACKAGES, formatError: (_jax, err) => { throw err; }});
const svgOut = new SVG({fontCache: 'none'});
const doc = mathjax.document('', {InputJax: texIn, OutputJax: svgOut});

const R = (v) => {
  const x = Math.round(v * 1e4) / 1e4;
  return Object.is(x, -0) ? 0 : x;
};
const num = (s, what) => {
  const v = parseFloat(String(s));
  if (!isFinite(v)) throw new Error(`MathJax emitted a non-numeric ${what}: ${s}`);
  return v;
};
const attrs = (n) => {
  const a = {};
  for (const x of adaptor.allAttributes(n)) a[x.name] = x.value;
  return a;
};
/** translate(), scale(), matrix() — the three MathJax writes; anything else is refused by name. */
const parseTransform = (s) => {
  let m = IDENTITY;
  const re = /(\w+)\(([^)]*)\)/g;
  let hit;
  while ((hit = re.exec(s))) {
    const v = hit[2].split(/[\s,]+/).filter(Boolean).map((x) => num(x, 'transform'));
    let t;
    if (hit[1] === 'translate') t = [1, 0, 0, 1, v[0], v[1] ?? 0];
    else if (hit[1] === 'scale') t = [v[0], 0, 0, v[1] ?? v[0], 0, 0];
    else if (hit[1] === 'matrix') t = v;
    else throw new Error(`MathJax emitted a ${hit[1]}() transform this reader does not handle`);
    m = matMul(m, t);
  }
  return m;
};

/** Sutherland–Hodgman against an axis-aligned rect, one ring at a time (holes are rings too). */
const clipRing = (pts, [x0, y0, x1, y1]) => {
  const edges = [
    [(p) => p[0] >= x0, (a, b) => [x0, a[1] + ((b[1] - a[1]) * (x0 - a[0])) / (b[0] - a[0])]],
    [(p) => p[0] <= x1, (a, b) => [x1, a[1] + ((b[1] - a[1]) * (x1 - a[0])) / (b[0] - a[0])]],
    [(p) => p[1] >= y0, (a, b) => [a[0] + ((b[0] - a[0]) * (y0 - a[1])) / (b[1] - a[1]), y0]],
    [(p) => p[1] <= y1, (a, b) => [a[0] + ((b[0] - a[0]) * (y1 - a[1])) / (b[1] - a[1]), y1]],
  ];
  let out = pts;
  for (const [inside, cut] of edges) {
    const src = out;
    out = [];
    for (let i = 0; i < src.length; i++) {
      const p = src[i], q = src[(i + 1) % src.length];
      const pi = inside(p), qi = inside(q);
      if (pi) out.push(p);
      if (pi !== qi) out.push(cut(p, q));
    }
    if (!out.length) return [];
  }
  return out;
};

/** An outline (filled) for a stroke MathJax draws with stroke-width: a box frame, a cancel line. */
const rectOutline = (x, y, w, h, sw) => {
  const o = sw / 2;
  // outer clockwise, inner counter-clockwise: the hole survives the default nonzero fill rule
  return `M${R(x - o)} ${R(y - o)}H${R(x + w + o)}V${R(y + h + o)}H${R(x - o)}Z` +
    `M${R(x + o)} ${R(y + o)}V${R(y + h - o)}H${R(x + w - o)}V${R(y + o)}Z`;
};
const lineOutline = (x1, y1, x2, y2, sw) => {
  const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, nx = (-dy / L) * sw / 2, ny = (dx / L) * sw / 2;
  return `M${R(x1 + nx)} ${R(y1 + ny)}L${R(x2 + nx)} ${R(y2 + ny)}L${R(x2 - nx)} ${R(y2 - ny)}L${R(x1 - nx)} ${R(y1 - ny)}Z`;
};
const ellipseOutline = (cx, cy, rx, ry, sw) => {
  const o = sw / 2, a = rx + o, b = ry + o, c = Math.max(0, rx - o), d = Math.max(0, ry - o);
  return `M${R(cx - a)} ${R(cy)}A${R(a)} ${R(b)} 0 1 1 ${R(cx + a)} ${R(cy)}A${R(a)} ${R(b)} 0 1 1 ${R(cx - a)} ${R(cy)}Z` +
    `M${R(cx - c)} ${R(cy)}A${R(c)} ${R(d)} 0 1 0 ${R(cx + c)} ${R(cy)}A${R(c)} ${R(d)} 0 1 0 ${R(cx - c)} ${R(cy)}Z`;
};

const UNSUPPORTED_TEXT = (s, tex) => new Error(
  `TeX "${tex}" draws characters MathJax's TeX font has no outline for (${JSON.stringify(s)}) — they would be set in ` +
  'whatever system face the renderer finds, which is neither deterministic nor this font. Put words (and any CJK) in ' +
  "the register's label props, not inside \\text{} or the math.");

/** Walk MathJax's SVG tree into glyphs, composing every transform. */
const collect = (node, M, ctx, out, tex) => {
  const kind = adaptor.kind(node);
  if (kind === '#text' || kind === '#comment') {
    const s = adaptor.value(node) ?? '';
    if (s.trim() && kind === '#text') throw UNSUPPORTED_TEXT(s.trim(), tex);
    return;
  }
  const a = attrs(node);
  let m = a.transform ? matMul(M, parseTransform(a.transform)) : M;
  let clip = ctx.clip;
  if (kind === 'svg' && ctx.depth > 0) {
    // a nested viewport: MathJax slices a stretchy extender out of a glyph this way, and the viewport CLIPS it
    const x = num(a.x ?? 0, 'svg x'), y = num(a.y ?? 0, 'svg y'), w = num(a.width, 'svg width'), h = num(a.height, 'svg height');
    const vb = String(a.viewBox ?? `0 0 ${w} ${h}`).split(/[\s,]+/).map((v) => num(v, 'viewBox'));
    const sx = w / vb[2], sy = h / vb[3];
    m = matMul(m, [sx, 0, 0, sy, x - vb[0] * sx, y - vb[1] * sy]);
    // the clip rect in EQUATION units (the viewport's corners, through the composed matrix)
    const c0 = [M[0] * x + M[2] * y + M[4], M[1] * x + M[3] * y + M[5]];
    const c1 = [M[0] * (x + w) + M[2] * (y + h) + M[4], M[1] * (x + w) + M[3] * (y + h) + M[5]];
    const box = [Math.min(c0[0], c1[0]), Math.min(c0[1], c1[1]), Math.max(c0[0], c1[0]), Math.max(c0[1], c1[1])];
    clip = clip ? [Math.max(clip[0], box[0]), Math.max(clip[1], box[1]), Math.min(clip[2], box[2]), Math.min(clip[3], box[3])] : box;
  }
  const classes = a.class ? [...ctx.classes, ...String(a.class).split(/\s+/).filter(Boolean)] : ctx.classes;
  const color = a.fill && a.fill !== 'currentColor' && a.fill !== 'none' ? a.fill : ctx.color;
  const role = a['data-mml-node'] ?? ctx.role;
  const parentRole = a['data-mml-node'] ? ctx.role : ctx.parentRole;
  const push = (d, mat, c) => {
    let segs = transformSegs(parsePath(d), mat);
    let outD, outM;
    if (clip) {
      const rings = flatten(segs, 16).map((p) => clipRing(p.pts, clip)).filter((r) => r.length > 2);
      if (!rings.length) return;
      outD = rings.map((r) => ptsToD(r, true)).join('');
      outM = [1, 0, 0, 1, 0, 0];
      segs = parsePath(outD);
    } else {
      outD = d;
      outM = mat.map(R);
    }
    const b = segsBBox(segs);
    if (!b) return;
    out.push({d: outD, m: outM, c, n: role ?? '', p: parentRole ?? '', k: classes, ...(color ? {col: color} : {}),
      b: b.map(R)});
  };
  if (kind === 'path') {
    if (!a.d) return;
    push(a.d, m, a['data-c'] ? String(a['data-c']).toUpperCase() : 'path');
    return;
  }
  if (kind === 'rect') {
    const x = num(a.x ?? 0, 'rect x'), y = num(a.y ?? 0, 'rect y'), w = num(a.width, 'rect width'), h = num(a.height, 'rect height');
    if (a.fill === 'none') {
      push(rectOutline(x, y, w, h, num(a['stroke-width'] ?? 0, 'stroke-width')), m, `frame:${role ?? ''}`);
    } else {
      // a RULE (fraction bar, vinculum): the unit square under a scale, so a rule morphs into a rule of another
      // length by lerping its matrix
      push('M0 0H1V1H0Z', matMul(m, [w, 0, 0, h, x, y]), `rule:${role ?? ''}`);
    }
    return;
  }
  if (kind === 'line') {
    push(lineOutline(num(a.x1, 'x1'), num(a.y1, 'y1'), num(a.x2, 'x2'), num(a.y2, 'y2'),
      num(a['stroke-width'] ?? 0, 'stroke-width')), m, `stroke:${role ?? ''}`);
    return;
  }
  if (kind === 'ellipse') {
    push(ellipseOutline(num(a.cx ?? 0, 'cx'), num(a.cy ?? 0, 'cy'), num(a.rx, 'rx'), num(a.ry, 'ry'),
      num(a['stroke-width'] ?? 0, 'stroke-width')), m, `ring:${role ?? ''}`);
    return;
  }
  if (kind === 'text') throw UNSUPPORTED_TEXT(adaptor.textContent(node), tex);
  if (kind !== 'g' && kind !== 'svg') throw new Error(`MathJax emitted <${kind}>, which this reader does not handle (TeX "${tex}")`);
  for (const ch of adaptor.childNodes(node)) {
    collect(ch, m, {classes, color, role, parentRole, clip, depth: ctx.depth + 1}, out, tex);
  }
};

/** The digit set a live number is drawn from: the TeX font's upright glyphs, with their advances (1/1000 em). */
const atlas = () => {
  const out = {};
  for (const ch of '0123456789.,−') {
    const g = svgOut.font.getChar('normal', ch.codePointAt(0));
    if (!g || !g[3] || !g[3].p) throw new Error(`the TeX font has no outline for ${JSON.stringify(ch)}`);
    // the font stores the outline without its moveto and close — MathJax's own Wrapper writes 'M' + p + 'Z' — and in
    // y UP; stored here y DOWN like everything else
    out[ch] = {d: segsToD(transformSegs(parsePath('M' + g[3].p + 'Z'), [1, 0, 0, -1, 0, 0])), adv: R(g[2] * 1000)};
  }
  return out;
};

export const typeset = (texRaw, display = true) => {
  const tex = normTex(texRaw);
  if (!tex) throw new Error('empty TeX');
  const node = doc.convert(tex, {display, em: 16, ex: 8, containerWidth: 80 * 16});
  const svg = adaptor.childNodes(node).find((n) => adaptor.kind(n) === 'svg');
  if (!svg) throw new Error(`MathJax produced no <svg> for "${tex}"`);
  const vb = String(attrs(svg).viewBox).split(/[\s,]+/).map((v) => num(v, 'viewBox'));
  const glyphs = [];
  const M0 = [1, 0, 0, 1, -vb[0], -vb[1]];
  for (const ch of adaptor.childNodes(svg)) collect(ch, M0, {classes: [], color: null, role: null, parentRole: null,
    clip: null, depth: 1}, glyphs, tex);
  if (!glyphs.length) throw new Error(`TeX "${tex}" draws nothing`);
  const ink = glyphs.reduce((b, g) => [Math.min(b[0], g.b[0]), Math.min(b[1], g.b[1]), Math.max(b[2], g.b[2]),
    Math.max(b[3], g.b[3])], [Infinity, Infinity, -Infinity, -Infinity]).map(R);
  const usesLive = glyphs.some((g) => g.k.some((k) => /^live/.test(k)));
  return {v: MATH_FORMAT, key: mathKey(tex, display), tex, display, mathjax: MJ_VERSION, w: R(vb[2]), h: R(vb[3]),
    base: R(-vb[1]), ink, glyphs, ...(usesLive ? {atlas: atlas()} : {})};
};

const writeAtomic = (file, text) => {
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, text);
  fs.renameSync(tmp, file);       // content-addressed: two writers of one key write the same bytes
};

const main = () => {
  const argv = process.argv.slice(2);
  const flag = (f) => argv.includes(f);
  const opt = (f) => { const i = argv.indexOf(f); return i >= 0 ? argv[i + 1] : undefined; };
  const report = {written: [], cached: [], errors: []};
  if (flag('--svg')) {
    // MathJax's OWN markup for one TeX — the reference tests/test_math_morph.py rasterises beside the glyph layer
    const i = argv.indexOf('--svg');
    const node = doc.convert(normTex(argv[i + 1]), {display: !flag('--inline'), em: 16, ex: 8, containerWidth: 80 * 16});
    const svg = adaptor.childNodes(node).find((n) => adaptor.kind(n) === 'svg');
    process.stdout.write(adaptor.outerHTML(svg) + '\n');
    process.exit(0);
  }
  if (flag('--library')) {
    const src = JSON.parse(fs.readFileSync(LIB_SRC, 'utf8')).equations;
    if (!Array.isArray(src)) throw new Error(`${LIB_SRC} must hold \`equations\`: a list of {tex, display}`);
    const eq = {};
    for (const it of src) {
      try {
        const g = typeset(it.tex, it.display !== false);
        eq[g.key] = g;
        report.written.push(g.key);
      } catch (e) { report.errors.push({tex: it.tex, error: String(e.message ?? e)}); }
    }
    if (!report.errors.length) {
      const keys = Object.keys(eq).sort();
      const sorted = {};
      keys.forEach((k) => { sorted[k] = eq[k]; });
      // --library-out <file>: the same build somewhere else (the freshness test compares it with the committed file)
      writeAtomic(opt('--library-out') ?? LIB_OUT, JSON.stringify({v: MATH_FORMAT, mathjax: MJ_VERSION, eq: sorted}) + '\n');
    }
  } else {
    let items = [];
    if (flag('--stdin')) {
      const j = JSON.parse(fs.readFileSync(0, 'utf8'));
      items = (j.items ?? []).map((it) => ({tex: it.tex, display: it.display !== false}));
    } else {
      const dd = argv.indexOf('--');
      items = (dd >= 0 ? argv.slice(dd + 1) : []).map((tex) => ({tex, display: !flag('--inline')}));
    }
    if (flag('--check')) {
      const i = argv.indexOf('--check');
      items = [{tex: argv[i + 1], display: !flag('--inline')}];
    }
    const out = opt('--out');
    if (!flag('--check') && !out) throw new Error('--out <dir> is required (or --library / --check)');
    if (out) fs.mkdirSync(out, {recursive: true});
    for (const it of items) {
      try {
        if (typeof it.tex !== 'string' || !normTex(it.tex)) throw new Error('empty TeX');
        const key = mathKey(it.tex, it.display);
        const file = out ? path.join(out, `${key}.json`) : null;
        if (file && fs.existsSync(file)) {
          const have = JSON.parse(fs.readFileSync(file, 'utf8'));
          if (have.tex === normTex(it.tex) && have.v === MATH_FORMAT && have.mathjax === MJ_VERSION) {
            report.cached.push(key);
            continue;
          }
        }
        const g = typeset(it.tex, it.display);
        if (flag('--check')) {
          report.written.push({key, glyphs: g.glyphs.length, w: g.w, h: g.h});
          continue;
        }
        writeAtomic(file, JSON.stringify(g) + '\n');
        report.written.push(key);
      } catch (e) { report.errors.push({tex: it.tex, error: String(e.message ?? e)}); }
    }
  }
  process.stdout.write(JSON.stringify(report) + '\n');
  process.exit(report.errors.length ? 2 : 0);
};

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
