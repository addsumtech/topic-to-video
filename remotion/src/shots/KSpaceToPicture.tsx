// SHOT · KSpaceToPicture — the raw data is written into k-space one row at a time while, beside it, the inverse
// Fourier transform of the rows written so far resolves into the picture. Two real panels joined by the
// transform: left the k-space (the 2-D Fourier transform of an image), right the reconstruction of exactly
// the rows that are lit on the left.
//
// THE ARGUMENT SHAPE: "the data is not the picture; the picture is computed from it, and every row of data
// sharpens the WHOLE picture, not one row of it." That is the misconception a k-space diagram exists to break,
// so the two panels change together: a row lands on the left and the entire image on the right steps toward
// sharp. A picture that resolved row by row from the top would teach the opposite.
//
// NOTHING IS DRAWN BY HAND. A film hands it `srcKspace`, a k-space magnitude image, and `srcFrames`, the partial
// reconstructions of that k-space in fill order (the last is the full image), computed from its own real image
// (scripts/kspace_frames.py writes both and the props that name them). Both are pictures, so both are `src` props:
// the library's sweeps feed copy to every other string prop. `order` says how those frames were filled
// ('centre': the middle row first, then alternately one above and one below; 'top': top to bottom), and the
// k-space reveal follows the SAME order, so the lit rows on the left are always the rows the right panel was
// computed from. `rows` is the k-space's row count; the reveal advances in whole rows.
//
// WITH NEITHER, IT COMPUTES ITS OWN: the modified Shepp–Logan head phantom, its 2-D FFT as the k-space, and the
// inverse FFT of the rows written so far as each frame — the same arithmetic a film's data comes from, checked
// (the full inverse must return the phantom) before anything is drawn. That is the library's standalone preview
// and what it is measured on; a film always hands its own data (REQUIRED_IN_FILM).
//
// The library's other k-space registers (KSpaceToImage, KSpaceReal, KSpaceAnatomy, PhaseEncodeStep) write
// English labels into their code; every word here is a prop, and with none nothing is written. Both panels keep
// a scan viewport's black on any ground. Content stays inside the content zone; the credit sits at its foot.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, bottomInset, fitTextPx, fitsBox} from '../runtime/layout';
import {useDNA} from '../runtime/dna';
import {rows as asRows} from '../runtime/rows';
import {drawOn} from '../runtime/draw';

export const DURATION = 270;
export const REQUIRED_IN_FILM = ['srcKspace', 'srcFrames'] as const;
export const MAX_FRAMES = 64;

const BG_D0 = '#0a0f16', FG_D0 = '#e6ecf2', DIM_D0 = '#7e8a97', ACC_D0 = '#ffb347', ACC2_D0 = '#5cc8e0';
const LINE_D0 = '#1c2631';
const VIEWPORT = '#000000';                // a scan viewport is black on every ground
const FILL_A = 0.14, FILL_B = 0.8;         // the rows are written across this part of the beat

// ── the register's own data: a computed phantom ──────────────────────────────────────────────────────────────
// The modified Shepp–Logan head phantom (Toft's intensities), the standard test object of tomographic
// reconstruction: ten ellipses in a [-1, 1]² field, y up — [intensity, semi-axis x, semi-axis y, centre x,
// centre y, rotation in degrees] — so the skull reads 1, the brain 0.2, the ventricles 0, the small features 0.3.
const SHEPP_LOGAN: ReadonlyArray<readonly [number, number, number, number, number, number]> = [
  [1, 0.69, 0.92, 0, 0, 0], [-0.8, 0.6624, 0.874, 0, -0.0184, 0],
  [-0.2, 0.11, 0.31, 0.22, 0, -18], [-0.2, 0.16, 0.41, -0.22, 0, 18],
  [0.1, 0.21, 0.25, 0, 0.35, 0], [0.1, 0.046, 0.046, 0, 0.1, 0], [0.1, 0.046, 0.046, 0, -0.1, 0],
  [0.1, 0.046, 0.023, -0.08, -0.605, 0], [0.1, 0.023, 0.023, 0, -0.606, 0], [0.1, 0.023, 0.046, 0.06, -0.605, 0],
];
export const PHANTOM_ROWS = 256;           // the phantom's matrix (rows = columns), a power of two for the FFT
export const PHANTOM_FRAMES = 24;          // reconstructions, evenly spaced in rows written, as a film's own are
const PHANTOM_SS = 4;                      // samples per pixel side when the ellipses are rasterised
const PHANTOM_WHITE = 0.5;                 // the display's white point: the tissue sits at 0.2-0.3 of the skull's 1

/** The phantom rasterised at n×n, row 0 at the top (y = +1), each pixel the mean of ss×ss samples. */
export const phantomImage = (n: number, ss = PHANTOM_SS): Float64Array => {
  const img = new Float64Array(n * n);
  const ell = SHEPP_LOGAN.map(([A, a, b, x0, y0, deg]) => {
    const r = (deg * Math.PI) / 180;
    return {A, a2: a * a, b2: b * b, x0, y0, c: Math.cos(r), s: Math.sin(r)};
  });
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      let sum = 0;
      for (let si = 0; si < ss; si++) {
        const y = 1 - (2 * (i + (si + 0.5) / ss)) / n;
        for (let sj = 0; sj < ss; sj++) {
          const x = -1 + (2 * (j + (sj + 0.5) / ss)) / n;
          for (const e of ell) {
            const dx = x - e.x0, dy = y - e.y0;
            const u = dx * e.c + dy * e.s, v = dy * e.c - dx * e.s;
            if ((u * u) / e.a2 + (v * v) / e.b2 <= 1) sum += e.A;
          }
        }
      }
      img[i * n + j] = sum / (ss * ss);
    }
  }
  return img;
};

// a radix-2 FFT in place; the inverse divides by n
const fft1 = (re: Float64Array, im: Float64Array, inverse: boolean): void => {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      const tr = re[i], ti = im[i];
      re[i] = re[j]; im[i] = im[j]; re[j] = tr; im[j] = ti;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const half = len >> 1, ang = ((inverse ? 2 : -2) * Math.PI) / len;
    for (let k = 0; k < half; k++) {
      const wr = Math.cos(ang * k), wi = Math.sin(ang * k);
      for (let i = k; i < n; i += len) {
        const pr = re[i + half] * wr - im[i + half] * wi, pi = re[i + half] * wi + im[i + half] * wr;
        re[i + half] = re[i] - pr; im[i + half] = im[i] - pi;
        re[i] += pr; im[i] += pi;
      }
    }
  }
  if (inverse) for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
};

// the 1-D transform over every row (axis 'x') or every column (axis 'y') of an n×n complex array, in place
const fftAxis = (re: Float64Array, im: Float64Array, n: number, axis: 'x' | 'y', inverse: boolean): void => {
  const r = new Float64Array(n), q = new Float64Array(n);
  for (let a = 0; a < n; a++) {
    for (let b = 0; b < n; b++) { const at = axis === 'x' ? a * n + b : b * n + a; r[b] = re[at]; q[b] = im[at]; }
    fft1(r, q, inverse);
    for (let b = 0; b < n; b++) { const at = axis === 'x' ? a * n + b : b * n + a; re[at] = r[b]; im[at] = q[b]; }
  }
};

/** Which displayed k-space rows (row 0 at the top, the centre at n/2) are written when `m` of them are — the
 *  same rows the reveal lights. */
export const writtenRows = (m: number, n: number, order: 'centre' | 'top'): [number, number] => {
  if (order === 'top') return [0, m - 1];
  const c = Math.floor(n / 2);
  return [c - Math.floor(m / 2), c + Math.floor(Math.max(0, m - 1) / 2)];
};

/** A k-space and its reconstructions, computed: `kspace` is |FFT| with the zero frequency at the centre (row
 *  and column n/2), and `reconstruct(m)` is |inverse FFT| of the k-space with only the first `m` rows of `order`
 *  written. Throws when the full inverse does not return the image — a transform that cannot round-trip would
 *  draw a k-space and a picture that are not each other's. */
export const fourierPair = (img: Float64Array, n: number) => {
  if (!(n >= 8 && (n & (n - 1)) === 0 && img.length === n * n)) {
    throw new Error(`KSpaceToPicture: the computed k-space needs an n×n image with n a power of two — got n=${n}`);
  }
  const re = Float64Array.from(img), im = new Float64Array(n * n);
  fftAxis(re, im, n, 'x', false);
  fftAxis(re, im, n, 'y', false);
  const kspace = new Float64Array(n * n);
  const h = n / 2;
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) kspace[y * n + x] = Math.hypot(re[((y + h) % n) * n + ((x + h) % n)], im[((y + h) % n) * n + ((x + h) % n)]);
  }
  // every row's inverse transform along x, once: a reconstruction is then one inverse transform per column over
  // the written rows alone (a row that is not written is all zero, so its row transform is too)
  fftAxis(re, im, n, 'x', true);
  const reconstruct = (m: number, order: 'centre' | 'top'): {re: Float64Array; im: Float64Array} => {
    const [lo, hi] = writtenRows(m, n, order);
    const r = new Float64Array(n * n), q = new Float64Array(n * n);
    for (let d = lo; d <= hi; d++) {                         // displayed row d is frequency row (d + n/2) % n
      const ky = (d + h) % n;
      r.set(re.subarray(ky * n, ky * n + n), ky * n);
      q.set(im.subarray(ky * n, ky * n + n), ky * n);
    }
    fftAxis(r, q, n, 'y', true);
    return {re: r, im: q};
  };
  const full = reconstruct(n, 'top');
  let err = 0;
  for (let i = 0; i < n * n; i++) err = Math.max(err, Math.abs(full.re[i] - img[i]), Math.abs(full.im[i]));
  if (!(err < 1e-9)) {
    throw new Error(`KSpaceToPicture: the inverse transform of the full k-space missed the image by ${err} — the ` +
      'computed k-space and picture would not be a Fourier pair.');
  }
  return {kspace, reconstruct};
};

// numpy's default percentile: linear between the two nearest ranks
const percentile = (v: Float64Array, q: number): number => {
  const s = Float64Array.from(v).sort();
  const at = (q / 100) * (s.length - 1), lo = Math.floor(at), hi = Math.min(s.length - 1, lo + 1);
  return s[lo] + (s[hi] - s[lo]) * (at - lo);
};

const toByte = (v: number): number => Math.round(Math.min(1, Math.max(0, v)) * 255);

// an 8-bit grey BMP as a data URI, rows top-down — the cheapest picture <Img> can be handed without a file
const bmpUri = (px: Uint8Array, n: number): string => {
  const head = 14 + 40 + 1024, b = new Uint8Array(head + n * n), dv = new DataView(b.buffer);
  b[0] = 0x42; b[1] = 0x4d;
  dv.setUint32(2, b.length, true); dv.setUint32(10, head, true);
  dv.setUint32(14, 40, true); dv.setInt32(18, n, true); dv.setInt32(22, -n, true);
  dv.setUint16(26, 1, true); dv.setUint16(28, 8, true); dv.setUint32(34, n * n, true); dv.setUint32(46, 256, true);
  for (let i = 0; i < 256; i++) { b[54 + 4 * i] = i; b[55 + 4 * i] = i; b[56 + 4 * i] = i; }
  b.set(px, head);
  let s = '';
  for (let i = 0; i < b.length; i += 0x2000) s += String.fromCharCode(...Array.from(b.subarray(i, i + 0x2000)));
  return 'data:image/bmp;base64,' + btoa(s);
};

export type PhantomSeries = {kspace: Uint8Array; frame: (j: number) => Uint8Array; kspaceUri: string;
  frameUri: (j: number) => string};

/** The phantom's k-space and its `count` reconstructions as displayed bytes and as pictures, each frame j holding
 *  round(n·(j+1)/count) rows of `order` — the k-space as log magnitude above its median (the energy at the
 *  centre reads as light on black), the frames on one white point so a frame's brightness says how much is
 *  there. Computed once per order and kept: a pure function of its arguments. */
export const phantomSeries = (order: 'centre' | 'top', n = PHANTOM_ROWS, count = PHANTOM_FRAMES): PhantomSeries => {
  const key = `${order}:${n}:${count}`;
  const kept = SERIES.get(key);
  if (kept) return kept;
  const {kspace, reconstruct} = fourierPair(phantomImage(n), n);
  const mag = kspace.map((v) => Math.log1p(v));
  const floor = percentile(mag, 50), top = percentile(mag, 99.95);
  const kBytes = Uint8Array.from(mag, (v) => toByte((v - floor) / (top - floor)));
  const frames: Uint8Array[] = [], uris: string[] = [];
  const frame = (j: number): Uint8Array => {
    if (!(Number.isInteger(j) && j >= 0 && j < count)) throw new Error(`KSpaceToPicture: no phantom frame ${j}`);
    if (!frames[j]) {
      const r = reconstruct(Math.round((n * (j + 1)) / count), order);
      frames[j] = Uint8Array.from(r.re, (v, i) => toByte(Math.hypot(v, r.im[i]) / PHANTOM_WHITE));
    }
    return frames[j];
  };
  const series: PhantomSeries = {kspace: kBytes, frame, kspaceUri: bmpUri(kBytes, n),
    frameUri: (j) => uris[j] || (uris[j] = bmpUri(frame(j), n))};
  SERIES.set(key, series);
  return series;
};
const SERIES = new Map<string, PhantomSeries>();

export const KSpaceToPicture: React.FC<{
  srcKspace?: string;       // the k-space magnitude image (public-dir path) — absent with `srcFrames`: the computed phantom's
  srcFrames?: string[];     // the partial reconstructions, in fill order; the last is the whole image — more read as smoother
  order?: 'centre' | 'top'; // the order the rows were filled in when `srcFrames` were computed
  rows?: number;            // the k-space's row count
  kspaceLabel?: string;     // the left panel's name
  kspaceNote?: string;      // one line under it
  transformLabel?: string;  // the arrow's name
  imageLabel?: string;      // the right panel's name
  imageNote?: string;       // one line under it
  credit?: string;          // the source image's attribution
  title?: string;           // a line in the title band
  kicker?: string;          // a small spaced label above it
}> = ({srcKspace, srcFrames, order = 'centre', rows = 256, kspaceLabel = '', kspaceNote = '', transformLabel = '',
  imageLabel = '', imageNote = '', credit = '', title = '', kicker = ''} = {}) => {
  if (order !== 'centre' && order !== 'top') {
    throw new Error(`KSpaceToPicture: \`order\` is 'centre' or 'top' — got ${JSON.stringify(order)}`);
  }
  if (!(Number.isInteger(rows) && rows >= 8 && rows <= 4096)) {
    throw new Error(`KSpaceToPicture: \`rows\` is the k-space's whole number of rows, 8-4096 — got ${JSON.stringify(rows)}`);
  }
  // a film's own data comes as a pair, or not at all: half of it would light rows of one image beside the
  // reconstructions of another
  const own = srcKspace === undefined && srcFrames === undefined;
  const FRAMES = own ? [] : asRows<string>(srcFrames, 'srcFrames', 'KSpaceToPicture');
  if (!own) {
    if (typeof srcKspace !== 'string' || !srcKspace.trim() || !FRAMES.length) {
      throw new Error('KSpaceToPicture: a film hands `srcKspace` (the k-space of its real image) and `srcFrames` (that ' +
        'k-space\'s reconstructions, in fill order) together — both computed from the image by ' +
        'scripts/kspace_frames.py — or neither, for the register\'s own computed phantom. Got srcKspace=' +
        `${JSON.stringify(srcKspace)}, ${FRAMES.length} frame(s).`);
    }
    if (FRAMES.length > MAX_FRAMES) {
      throw new Error(`KSpaceToPicture takes at most ${MAX_FRAMES} \`srcFrames\` (got ${FRAMES.length}) — every one is an ` +
        'image the render loads; a few dozen already read as continuous.');
    }
    FRAMES.forEach((f, i) => {
      if (typeof f !== 'string' || !f.trim()) {
        throw new Error(`KSpaceToPicture: srcFrames[${i}] is a reconstruction image's path — got ${JSON.stringify(f)}`);
      }
    });
  }
  const phantom = own ? phantomSeries(order) : null;
  const kSrc = phantom ? phantom.kspaceUri : staticFile(srcKspace as string);
  const frameSrc = (j: number): string => (phantom ? phantom.frameUri(j) : staticFile(FRAMES[j]));
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  const LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const portrait = W < H;

  // ── words, sized first; the panels take the room they leave ──
  const labelPx = Math.round(U * 0.034), notePx = Math.round(U * 0.024), creditPx = Math.max(12, Math.round(U * 0.014));
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H) - (credit ? creditPx * 2.2 : 0);
  const labelRoom = kspaceLabel || imageLabel ? labelPx * 1.6 : 0;
  const noteRoom = kspaceNote || imageNote ? notePx * 1.9 : 0;
  const gapMid = portrait ? U * 0.12 : Math.max(U * 0.2, W * 0.13);
  // wide: the two panels side by side; tall: one above the other, the transform between them
  const S = portrait
    ? Math.max(40, Math.min(W * 0.78, (zBot - zTop - 2 * (labelRoom + noteRoom) - gapMid) / 2))
    : Math.max(40, Math.min((W * 0.86 - gapMid) / 2, zBot - zTop - labelRoom - noteRoom - U * 0.02));
  const blockW = portrait ? S : 2 * S + gapMid;
  const blockH = portrait ? 2 * (S + labelRoom + noteRoom) + gapMid : S + labelRoom + noteRoom;
  const bx = (W - blockW) / 2, by = zTop + Math.max(0, (zBot - zTop - blockH) / 2);
  const kPanel = {x: bx, y: by + labelRoom, s: S};
  const iPanel = portrait
    ? {x: bx, y: by + S + labelRoom + noteRoom + gapMid + labelRoom, s: S}
    : {x: bx + S + gapMid, y: by + labelRoom, s: S};

  // ── the clock: how many rows are written, and which ──
  const panelsIn = easeOutCubic(clamp01(seg(t, 0.02, 0.14)));
  const arrowIn = clamp01(seg(t, 0.08, 0.22));
  const fill = easeInOutCubic(clamp01(seg(t, FILL_A, FILL_B)));
  const n = Math.round(fill * rows);                      // rows written so far — whole rows only
  const c = Math.floor(rows / 2);
  const above = order === 'centre' ? Math.floor(n / 2) : 0;
  const below = order === 'centre' ? Math.floor(Math.max(0, n - 1) / 2) : 0;
  const firstRow = order === 'centre' ? c - above : 0;
  const lastRow = order === 'centre' ? c + below : n - 1;   // inclusive; lastRow < firstRow when nothing is written
  const rowPx = S / rows;
  const bandTop = n ? firstRow * rowPx : S / 2, bandBot = n ? (lastRow + 1) * rowPx : S / 2;
  const writing = n > 0 && n < rows;
  const done = easeOutCubic(clamp01(seg(t, FILL_B + 0.02, FILL_B + 0.12)));
  // the reconstruction of the rows written so far: frame j holds (j + 1) / N of them; between two frames, both
  const N = phantom ? PHANTOM_FRAMES : FRAMES.length;
  const pos = (n / rows) * N - 1;                          // -1 .. N-1
  const j0 = Math.max(0, Math.min(N - 1, Math.floor(pos))), j1 = Math.min(N - 1, j0 + 1);
  const mixF = pos < 0 ? 0 : clamp01(pos - j0);
  const firstIn = pos < 0 ? clamp01(pos + 1) : 1;          // before the first frame's rows are in, it fades up

  const lblPx = (text: string) => (text ? fitTextPx(text, S, labelPx, {usable: 1}) : 0);
  const nPx = (text: string) => (text ? fitTextPx(text, S, notePx, {usable: 1}) : 0);
  const labelsIn = easeOutCubic(clamp01(seg(t, 0.06, 0.2)));
  const notesIn = easeOutCubic(clamp01(seg(t, 0.2, 0.34)));
  const trPx = transformLabel ? fitTextPx(transformLabel, portrait ? W * 0.8 : gapMid * 0.92, Math.round(U * 0.03), {usable: 1}) : 0;
  const trOk = !!transformLabel && fitsBox(transformLabel, trPx, portrait ? W * 0.8 : gapMid * 0.92, trPx * 2);

  // the arrow between the panels
  const ax0 = portrait ? W / 2 : kPanel.x + S + gapMid * 0.12, ax1 = portrait ? W / 2 : iPanel.x - gapMid * 0.12;
  const ay0 = portrait ? kPanel.y + S + noteRoom + gapMid * 0.15 : kPanel.y + S / 2;
  const ay1 = portrait ? iPanel.y - labelRoom - gapMid * 0.15 : kPanel.y + S / 2;
  const headL = U * 0.022;
  const arrowHead = portrait
    ? `M${ax1} ${ay1} l${-headL * 0.55} ${-headL} l${headL * 1.1} 0 Z`
    : `M${ax1} ${ay1} l${-headL} ${-headL * 0.55} l0 ${headL * 1.1} Z`;

  // the rows still waiting: faint rules over the unwritten part of the table, so it reads as rows to fill
  const ruleEvery = Math.max(1, Math.round(rows / 16));
  const waiting: React.ReactNode[] = [];
  for (let r = ruleEvery; r < rows; r += ruleEvery) {
    if (n && r >= firstRow && r <= lastRow + 1) continue;
    waiting.push(<line key={r} x1={0} y1={r * rowPx} x2={S} y2={r * rowPx} stroke={DIM} strokeWidth={1} opacity={0.28} />);
  }

  const panelFrame = (p: {x: number; y: number; s: number}, glow: number) => ({
    position: 'absolute' as const, left: p.x, top: p.y, width: p.s, height: p.s, overflow: 'hidden' as const,
    background: VIEWPORT, borderRadius: Math.max(2, (dna?.radius ?? 6) * 0.8),
    boxShadow: `0 0 0 ${Math.max(1, U * 0.0015)}px ${glow > 0 ? ACC : LINE}`, opacity: panelsIn,
  });

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: title ? TITLE_Y - U * 0.04 : TITLE_Y,
          textAlign: 'center', font: `600 ${Math.round(U * 0.022)}px/1.2 ${mono}`, color: ACC2,
          letterSpacing: dna?.labelSpacing ?? '0.14em', opacity: labelsIn}}>{kicker}</div>
      ) : null}
      {title ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
          font: `700 ${fitTextPx(title, W * 0.8, Math.round(U * 0.045), {usable: 1})}px/1.15 ${disp}`, color: FG,
          opacity: labelsIn}}>{title}</div>
      ) : null}

      {/* the k-space: the rows written so far, lit; the rest still black */}
      <div style={panelFrame(kPanel, 0)}>
        <Img src={kSrc} style={{position: 'absolute', left: 0, top: 0, width: S, height: S,
          clipPath: `inset(${bandTop.toFixed(2)}px 0 ${(S - bandBot).toFixed(2)}px 0)`, imageRendering: 'pixelated'}} />
        <svg width={S} height={S} style={{position: 'absolute', left: 0, top: 0}}>
          {waiting}
          {writing ? (
            <g>
              <line x1={0} y1={bandTop} x2={S} y2={bandTop} stroke={ACC2} strokeWidth={Math.max(2, U * 0.003)} />
              {order === 'centre' ? (
                <line x1={0} y1={bandBot} x2={S} y2={bandBot} stroke={ACC2} strokeWidth={Math.max(2, U * 0.003)} />
              ) : null}
            </g>
          ) : null}
        </svg>
      </div>

      {/* the picture: the inverse transform of exactly the rows lit on the left */}
      <div style={panelFrame(iPanel, done)}>
        <Img src={frameSrc(j0)} style={{position: 'absolute', left: 0, top: 0, width: S, height: S,
          opacity: firstIn * (j1 === j0 ? 1 : 1 - mixF)}} />
        {j1 !== j0 ? (
          <Img src={frameSrc(j1)} style={{position: 'absolute', left: 0, top: 0, width: S, height: S,
            opacity: mixF}} />
        ) : null}
      </div>

      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <path d={`M${ax0} ${ay0} L${ax1} ${ay1}`} stroke={ACC2} strokeWidth={Math.max(2, U * 0.004)} fill="none"
          {...drawOn(arrowIn)} />
        {arrowIn > 0.98 ? <path d={arrowHead} fill={ACC2} /> : null}
      </svg>
      {trOk ? (
        <div style={{position: 'absolute', left: portrait ? 0 : ax0, width: portrait ? W : ax1 - ax0,
          top: portrait ? (ay0 + ay1) / 2 - trPx * 0.6 : ay0 - trPx * 1.9, textAlign: 'center',
          font: `600 ${trPx}px/1.2 ${bodyF}`, color: ACC2, opacity: labelsIn}}>{transformLabel}</div>
      ) : null}

      {kspaceLabel ? (
        <div style={{position: 'absolute', left: kPanel.x, width: S, top: kPanel.y - labelRoom, textAlign: 'center',
          font: `700 ${lblPx(kspaceLabel)}px/1.2 ${disp}`, color: FG, opacity: labelsIn}}>{kspaceLabel}</div>
      ) : null}
      {imageLabel ? (
        <div style={{position: 'absolute', left: iPanel.x, width: S, top: iPanel.y - labelRoom, textAlign: 'center',
          font: `700 ${lblPx(imageLabel)}px/1.2 ${disp}`, color: FG, opacity: labelsIn}}>{imageLabel}</div>
      ) : null}
      {kspaceNote ? (
        <div style={{position: 'absolute', left: kPanel.x, width: S, top: kPanel.y + S + notePx * 0.5,
          textAlign: 'center', font: `400 ${nPx(kspaceNote)}px/1.2 ${bodyF}`, color: DIM, opacity: notesIn}}>{kspaceNote}</div>
      ) : null}
      {imageNote ? (
        <div style={{position: 'absolute', left: iPanel.x, width: S, top: iPanel.y + S + notePx * 0.5,
          textAlign: 'center', font: `400 ${nPx(imageNote)}px/1.2 ${bodyF}`, color: DIM, opacity: notesIn}}>{imageNote}</div>
      ) : null}
      {credit ? (
        <div style={{position: 'absolute', left: W * 0.04, right: W * 0.04, bottom: bottomInset(W, H, 8),
          textAlign: 'center', color: DIM, font: `400 ${creditPx}px/1.3 ${bodyF}`, opacity: panelsIn}}>{credit}</div>
      ) : null}
    </AbsoluteFill>
  );
};
