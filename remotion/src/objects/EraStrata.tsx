// OBJECT · EraStrata — eras laid down like strata: each layer exactly as thick as the years it lasted, the oldest
// at the bottom, the newest span (the last one in `years`) in the accent on top. Built for a city's history (a
// border town, its county seat, then the city); it carries any run of eras whose lengths are the point.
//
// IT ENCODES "how long each era lasted, and how recent the last one is". Caption hidden, a viewer sees a column
// build up from the bottom layer by layer — thick old layers first, then thinner ones — and, when the film lays
// it, one thin bright layer on top. Time is drawn as depth of deposit. The thickness is the ONLY quantity it
// draws and it is the film's own: `years` are the boundaries, oldest first; layer i runs years[i] → years[i+1].
//
// IT DRAWS NO WORDS. The eras' names and years are the host's labels (ObjectStage); the object owns the picture,
// the stage owns the words. To land a label on a layer, use COLUMN (fractions of the object's box): the boundary
// for year Y sits at COLUMN.bottom − (COLUMN.bottom − COLUMN.top) · (Y − years[0]) / (years[last] − years[0]) of
// the box height, and the column's sides are COLUMN.left / COLUMN.right of its width.
//
// THE CLOCK. `t` runs 0 → 1 over the window its host gives it and then holds. Layers below `from` are in place at
// t = 0 (a later beat continuing an earlier one); layers from `from` up to `laid` are deposited in order — grains
// fall onto the stack while the layer rises to its full thickness, then its top edge is ruled. The newest span
// glows once it is laid. Everything is settled by t = 1.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '../runtime/objectSlot';
import {clamp01, seg, easeOutCubic, easeInOutCubic, hash01, lerp} from '../runtime/motion';
import {mix} from '../runtime/dna';
import {drawOn} from '../runtime/draw';

export const META: ObjectMeta = {aspect: 0.85, provenance: 'survey-archive'};

// The column inside the object's box. The top leaves headroom for the grains of the newest layer to fall through.
export const COLUMN = {top: 0.1, bottom: 0.97, left: 0.16, right: 0.84};

const INK_D0 = '#1b2230', EARTH_D0 = '#cbbda6', ACC_D0 = '#c43f28', ON_ACC_D0 = '#fbf6ee';
const DEPOSIT_END = 0.88;     // the last deposit lands by here; the newest span's glow fills the rest
const GRAINS = 30;            // grains per deposited layer

type Props = ObjectProps & {
  years?: number[];   // era boundaries, oldest first — n + 1 numbers make n layers, each years[i] → years[i+1]
  laid?: number;      // how many layers (from the bottom) stand by the end; default all
  from?: number;      // how many of those are already in place at t = 0; default 0
  ghost?: boolean;    // outline the slots still to be laid, faintly
};

const isInt = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v);

export const EraStrata: React.FC<Props> = ({w, h, t, dna, years = [], laid, from = 0, ghost = false}) => {
  if (!Array.isArray(years) || years.length < 2 ||
      years.some((v) => typeof v !== 'number' || !Number.isFinite(v))) {
    throw new Error('EraStrata: `years` is the list of era boundaries, oldest first — at least two finite numbers ' +
      '(n + 1 boundaries make n layers). Got ' + JSON.stringify(years));
  }
  for (let i = 1; i < years.length; i++) {
    if (!(years[i] > years[i - 1])) {
      throw new Error(`EraStrata: \`years\` must rise — ${years[i - 1]} is followed by ${years[i]}, which would ` +
        'give a layer no thickness or a negative one. Got ' + JSON.stringify(years));
    }
  }
  const n = years.length - 1;
  const L = laid === undefined ? n : laid;
  if (!isInt(L) || L < 0 || L > n) {
    throw new Error(`EraStrata: \`laid\` is how many of the ${n} layers stand by the end, a whole number 0-${n} — ` +
      'got ' + JSON.stringify(laid));
  }
  if (!isInt(from) || from < 0 || from > L) {
    throw new Error(`EraStrata: \`from\` is how many layers are already in place at the start, a whole number ` +
      `0-${L} (no more than \`laid\`) — got ` + JSON.stringify(from));
  }

  const uid = React.useId().replace(/[^A-Za-z0-9_-]/g, '');
  // the old layers are earth: the DNA's warm border tone deepened toward its ink; the accent is kept for the
  // newest span alone, so it means one thing
  const INK = dna?.fg ?? INK_D0, EARTH = dna?.surfaceBorder ?? EARTH_D0, ACC = dna?.accent ?? ACC_D0;
  const ON_ACC = dna?.onAccent ?? ON_ACC_D0;
  const U = Math.min(w, h);
  const x0 = w * COLUMN.left, x1 = w * COLUMN.right, colW = x1 - x0;
  const yTop = h * COLUMN.top, yBot = h * COLUMN.bottom;
  const span = years[n] - years[0];
  const yOf = (year: number) => yBot - (yBot - yTop) * (year - years[0]) / span;
  const stroke = Math.max(1, U * 0.004);

  // which layers deposit now, and when
  const K = L - from;
  const win = (i: number): [number, number] => {
    const k = i - from;
    return [(k / K) * DEPOSIT_END, ((k + 1) / K) * DEPOSIT_END];
  };
  const progress = (i: number) => (i < from ? 1 : i >= L ? 0 : clamp01(seg(t, ...win(i))));

  // a layer's own fill: the older, the deeper — a stack of earth under the newest span
  const oldFill = (i: number) => mix(EARTH, INK, 0.06 + 0.24 * ((n - 2 - i) / Math.max(1, n - 2)));
  const newest = (i: number) => i === n - 1;
  // lit once the newest span is laid — already lit when a beat opens with every layer in place
  const glow = L < n ? 0 : from === n ? 1 : easeOutCubic(clamp01(seg(t, DEPOSIT_END, 1)));

  // @decor: each old layer's engraved texture — a stratigraphic log's stipple, dashes and courses
  const textures = ['dots', 'dash', 'course'] as const;
  const pitch = Math.max(5, U * 0.032);

  const layers: React.ReactNode[] = [];
  const grains: React.ReactNode[] = [];
  for (let i = 0; i < L; i++) {
    const p = progress(i);
    if (p <= 0) continue;
    const yb = yOf(years[i]), yt = yOf(years[i + 1]), th = yb - yt;
    const rise = easeOutCubic(clamp01(seg(p, 0.1, 0.92)));
    const hNow = th * rise;
    const fill = newest(i) ? ACC : oldFill(i);
    // @cycles: which engraving an old layer wears is texture so neighbours differ; it states nothing about the era
    const tex = newest(i) ? `es-blocks-${uid}` : `es-${textures[i % textures.length]}-${uid}`;
    layers.push(
      <g key={`l${i}`}>
        <rect x={x0} y={yb - hNow} width={colW} height={hNow} fill={fill} />
        <rect x={x0} y={yb - hNow} width={colW} height={hNow} fill={`url(#${tex})`} />
        {/* the ruled top edge, drawn once the layer has risen */}
        <path d={`M${x0} ${yt} L${x1} ${yt}`} stroke={INK} strokeWidth={stroke} fill="none"
          {...drawOn(easeInOutCubic(clamp01(seg(p, 0.86, 1))))} />
      </g>,
    );
    // the grains this layer is laid from: each falls onto the stack in its own slice of the layer's window
    if (p < 1) {
      for (let j = 0; j < GRAINS; j++) {
        // @decor: where and when each grain falls is texture; how many layers and how thick is the film's
        const gx = x0 + colW * (0.04 + 0.92 * hash01(i * 131 + j * 7 + 3));
        const a = 0.72 * hash01(i * 71 + j * 13 + 5), b = a + 0.26;
        const q = clamp01(seg(p, a, b));
        if (q <= 0 || q >= 1) continue;
        const drop = Math.min(yt, h * 0.09) * (0.55 + 0.45 * hash01(i * 17 + j * 29));
        const landY = yb - hNow;
        const gy = lerp(landY - drop, landY, q * q);
        const r = Math.max(1.2, U * 0.0065) * (0.7 + 0.6 * hash01(i * 11 + j * 3));
        grains.push(<circle key={`g${i}-${j}`} cx={gx} cy={gy} r={r} fill={newest(i) ? ACC : mix(fill, INK, 0.45)}
          opacity={1 - q * 0.6} />);
      }
    }
  }

  // the slots still to be laid, outlined faintly when asked for
  const slots: React.ReactNode[] = [];
  if (ghost) {
    for (let i = L; i < n; i++) {
      const yb = yOf(years[i]), yt = yOf(years[i + 1]);
      slots.push(<rect key={`s${i}`} x={x0} y={yt} width={colW} height={yb - yt} fill="none" stroke={INK}
        strokeWidth={stroke} strokeDasharray={`${stroke * 3} ${stroke * 3}`} opacity={0.3} />);
    }
  }

  // the outline of what stands so far, and the newest span's glow
  const standTop = (() => {
    let y = yBot;
    for (let i = 0; i < L; i++) {
      const p = progress(i);
      if (p > 0) y = yOf(years[i]) - (yOf(years[i]) - yOf(years[i + 1])) * easeOutCubic(clamp01(seg(p, 0.1, 0.92)));
    }
    return y;
  })();
  const nTop = yOf(years[n]), nBot = yOf(years[n - 1]);

  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <defs>
        {/* @decor: stipple — the long, quiet bottom layer */}
        <pattern id={`es-dots-${uid}`} width={pitch} height={pitch} patternUnits="userSpaceOnUse">
          <circle cx={pitch * 0.3} cy={pitch * 0.35} r={Math.max(0.8, pitch * 0.07)} fill={INK} opacity={0.32} />
          <circle cx={pitch * 0.8} cy={pitch * 0.85} r={Math.max(0.6, pitch * 0.05)} fill={INK} opacity={0.24} />
        </pattern>
        {/* @decor: short dashes — a fine-grained layer */}
        <pattern id={`es-dash-${uid}`} width={pitch * 1.6} height={pitch * 0.8} patternUnits="userSpaceOnUse">
          <path d={`M${pitch * 0.15} ${pitch * 0.4} L${pitch * 0.85} ${pitch * 0.4}`} stroke={INK}
            strokeWidth={Math.max(0.8, pitch * 0.06)} opacity={0.3} />
        </pattern>
        {/* @decor: courses — a built layer */}
        <pattern id={`es-course-${uid}`} width={pitch * 1.4} height={pitch * 0.7} patternUnits="userSpaceOnUse">
          <path d={`M0 ${pitch * 0.69} L${pitch * 1.4} ${pitch * 0.69} M${pitch * 0.7} 0 L${pitch * 0.7} ${pitch * 0.69}`}
            stroke={INK} strokeWidth={Math.max(0.7, pitch * 0.045)} opacity={0.28} fill="none" />
        </pattern>
        {/* @decor: lit blocks — the newest span, lit up */}
        <pattern id={`es-blocks-${uid}`} width={pitch * 0.9} height={pitch * 0.9} patternUnits="userSpaceOnUse">
          <rect x={pitch * 0.12} y={pitch * 0.12} width={pitch * 0.42} height={pitch * 0.3} fill={ON_ACC} opacity={0.42} />
          <rect x={pitch * 0.58} y={pitch * 0.5} width={pitch * 0.22} height={pitch * 0.28} fill={ON_ACC} opacity={0.3} />
        </pattern>
        <filter id={`es-glow-${uid}`} x="-30%" y="-200%" width="160%" height="500%">
          <feGaussianBlur stdDeviation={Math.max(2, U * 0.02)} />
        </filter>
      </defs>
      {slots}
      {glow > 0 ? (
        <rect x={x0} y={nTop} width={colW} height={nBot - nTop} fill={ACC} opacity={0.55 * glow}
          filter={`url(#es-glow-${uid})`} />
      ) : null}
      {layers}
      {L > 0 && standTop < yBot - 0.5 ? (
        <rect x={x0} y={standTop} width={colW} height={yBot - standTop} fill="none" stroke={INK}
          strokeWidth={stroke * 1.2} />
      ) : null}
      {grains}
    </svg>
  );
};
