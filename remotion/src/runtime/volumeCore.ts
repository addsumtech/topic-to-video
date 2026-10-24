// VOLUME CORE — the pure half of runtime/volume.tsx: what a volume IS (its forms, its declared physics colours, the
// limits on how bright it may be), how a spec is checked, and the one projection a curtain and the ruler beside it
// share. No React, no DOM, no GL: tests/test_volume.py runs these under node against this very module.
//
// WHY A VOLUME AND NOT A STRIPE (bench-aurora, 2026-10-24): "the curtain still reads as a barcode on a flat wall after
// four rebuilds". A curtain built from SVG rects is N separate bars of light; a real curtain is ONE folded sheet of
// emitting gas seen through. What the eye reads as "a volume" is the LINE-OF-SIGHT INTEGRAL: where the sheet turns
// edge-on to the viewer the path through it is long and it is bright, where it faces the viewer it is faint, its lower
// edge is sharp and its top fades. The shader (runtime/volume.tsx) computes exactly that integral per pixel — the
// sheet's crossings of each pixel's line of sight, each weighted by 1/|dX/ds| — so the folds brighten themselves.
//
// EVERYTHING IS A FUNCTION OF (spec, seed, seconds). No state survives a draw (fx research 2026-10-24: a Canvas2D
// context that kept `globalCompositeOperation` between frames made 29 of 30 frames depend on render order).

export const VOLUME_FORMS = ['curtain', 'shafts', 'nebula', 'flame', 'layer'] as const;
export type VolumeForm = (typeof VOLUME_FORMS)[number];

/** How bright a volume may be driven: the exposure multiplier into the tone curve. Past ~1.6 every form clips to a
 *  white sheet over most of its body (looked at, VolumeProbe) — a volume past its cap is a wash, not light. */
export const VOLUME_MAX_INTENSITY = 1.6;
export const VOLUME_DEFAULT_INTENSITY = 1.0;
/** At most this many keep-out rects (the shader's uniform array). A register with more type than this has more type
 *  than a volume belongs under. */
export const VOLUME_MAX_KEEPOUT = 8;
/** How far past a kept-out rect the light takes to come back to full strength: at least runtime/optics
 *  KEEP_OUT_FEATHER_PX, and half the rect's long side for a big block of type. A volume fills the FRAME, so a 90 px
 *  feather round a headline cut a hard dark ellipse out of the sky (looked at, round-4 sheets) — a hole the eye reads
 *  as an object. The feather grows with the type so the clearing reads as the light thinning, not as a shape. */
export const VOLUME_KEEP_FEATHER_PX = 90;
export const VOLUME_KEEP_FEATHER_FRAC = 0.5;
/** The share of the light left INSIDE a kept rect: enough that the sky stays one sky behind the words, little enough
 *  that bold type keeps its contrast (tests/test_volume.py measures the title on the rendered frame). */
export const VOLUME_KEEP_FLOOR = 0.18;
/** The bands a curtain can carry (the shader's uniform array). */
export const VOLUME_MAX_BANDS = 6;

export type Band = {from: number; to: number; color: string; gain?: number};
export type Rect = {x: number; y: number; w: number; h: number};

// ── declared physics colours ────────────────────────────────────────────────────────────────────────────────────
/**
 * AURORAL EMISSION BY ALTITUDE — the curtain's default colour key when a film gives none.
 * Source: NASA Science, "Auroras" (captured in .superpowers/films/bench-aurora/sources/nasa-auroras.txt): red
 * >= 200 km (oxygen), green 100-200 km (oxygen, "the most common color"), blue 100-200 km (nitrogen), pink <= 100 km
 * (nitrogen: "the lower edge of the aurora a reddish-purple to pink glow"). Wikipedia "Aurora" (same folder): oxygen
 * 557.7 nm green, 630.0 nm red; the abrupt lower edge is atomic oxygen's rapid decrease below ~100 km; the faint top
 * is its low concentration up there. NOAA SWPC: "typically forms 80 to 500 km above Earth's surface".
 * The HEXES are display approximations of those emissions picked by eye (U) — sRGB cannot show 557.7 nm saturated —
 * not measurements. The top of the red band (320 km) is where this curtain stops drawing, not a physical limit.
 * Blue (nitrogen, the same altitudes as the green) is not a band here: two emissions at one altitude are a haze, not a
 * colour key, and a film that wants it says so in its own `bands`.
 */
export const AURORA_BANDS: Band[] = [
  {from: 80, to: 100, color: '#ff7ab8', gain: 0.55},      // N2, the pink lower fringe
  {from: 100, to: 200, color: '#5dff8e', gain: 1.0},      // O 557.7 nm
  {from: 200, to: 320, color: '#ff3d45', gain: 1.1},      // O 630.0 nm — faint, as in the sky
];
/** The altitude the sheet's lower border hangs at, km — where atomic oxygen falls off (Wikipedia, above). */
export const AURORA_LOWER_KM = 100;
/** The altitude the curtain is drawn up to, km (the top of AURORA_BANDS). */
export const AURORA_TOP_KM = 320;

/** EMISSION-NEBULA colours: H-alpha 656.3 nm (hydrogen, the red of an H II region) and [O III] 500.7 nm (doubly
 *  ionised oxygen, the blue-green near the hot stars). The lines are textbook; the hexes are display approximations
 *  (U). A film's own `colors` replace them. */
export const NEBULA_EMISSION = {halpha: '#ff4a6a', oiii: '#3fe3d2', dust: '#1a0f12'};

/** BLACKBODY colour at a temperature, sRGB hex — Tanner Helland's fit to Mitchell Charity's blackbody table (a
 *  published approximation, 1000-40000 K, within a few % of the table). A flame's colour ramp is a temperature ramp:
 *  dull red (~1000 K), orange (~1500-2000 K), yellow-white (~3000 K+) — the ordering is physics, the fit is cited. */
export const blackbody = (kelvin: number): string => {
  const t = Math.max(1000, Math.min(40000, kelvin)) / 100;
  const r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
  const g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
  const b = t >= 66 ? 255 : t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  const h = (v: number) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0');
  return `#${h(r)}${h(g)}${h(b)}`;
};
/** The flame's temperature stops, K: ember, flame body, hot core. Order is physics (blackbody); the numbers are the
 *  ramp's design (U). */
export const FLAME_KELVIN = [1100, 1700, 2600];

// ── colour ──────────────────────────────────────────────────────────────────────────────────────────────────────
const HEX = /^#[0-9a-fA-F]{6}$/;
export const isHex = (v: unknown): v is string => typeof v === 'string' && HEX.test(v);
/** #rrggbb -> linear-light rgb (sRGB EOTF), so light ADDS the way light does before it is tone-mapped back. */
export const linearRGB = (hex: string, where = 'volume'): [number, number, number] => {
  if (!isHex(hex)) throw new Error(`${where}: colour must be #rrggbb, got ${JSON.stringify(hex)}`);
  return [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }) as [number, number, number];
};

// ── the spec ────────────────────────────────────────────────────────────────────────────────────────────────────
export type VolumeSpec = {
  form: VolumeForm;
  /** exposure into the tone curve, (0, VOLUME_MAX_INTENSITY] */
  intensity?: number;
  seed?: number;
  /** colours: a curtain's are its `bands`; the others take one to three #rrggbb */
  colors?: string[];
  bands?: Band[];
  /** curtain: how many parallel sheets (1-3) */
  sheets?: number;
  /** shafts: where the light is, as fractions of the box (may lie outside 0..1 — a sun above the frame) */
  source?: [number, number];
  /** shafts: what the light comes through */
  occluder?: 'clouds' | 'canopy' | 'slats';
  /** shafts: how open the occluder is, 0 (shut) .. 1 (clear sky) */
  open?: number;
  /** nebula: where the ionising star sits (fractions of the box) */
  star?: [number, number];
  /** flame: where the base of the fire is, and how wide it is (fractions of the box) */
  base?: [number, number];
  spread?: number;
  /** how fast the volume moves, x its natural rate (0 holds it still: a reduced-motion render) */
  speed?: number;
};

export const OCCLUDERS = ['clouds', 'canopy', 'slats'] as const;

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** The spec, checked — or a throw that names what is wrong (E9: never a silent default into the shader). */
export const checkVolume = (spec: VolumeSpec, where = 'volume'): Required<Pick<VolumeSpec, 'form' | 'intensity' |
  'seed' | 'speed'>> & VolumeSpec => {
  if (!spec || typeof spec !== 'object') throw new Error(`${where}: a volume needs a spec {form, ...}`);
  if (!(VOLUME_FORMS as readonly string[]).includes(spec.form as string)) {
    throw new Error(`${where}: unknown volume form ${JSON.stringify(spec.form)} — one of ${VOLUME_FORMS.join(', ')}`);
  }
  const intensity = spec.intensity ?? VOLUME_DEFAULT_INTENSITY;
  if (!finite(intensity) || intensity <= 0 || intensity > VOLUME_MAX_INTENSITY) {
    throw new Error(`${where}: intensity must be in (0, ${VOLUME_MAX_INTENSITY}] (got ${JSON.stringify(spec.intensity)}) ` +
      '— past it the volume clips to a white sheet: a wash, not light');
  }
  const seed = spec.seed ?? 1;
  if (!finite(seed)) throw new Error(`${where}: seed must be a number`);
  const speed = spec.speed ?? 1;
  if (!finite(speed) || speed < 0 || speed > 4) throw new Error(`${where}: speed must be in [0, 4] (got ${JSON.stringify(spec.speed)})`);
  if (spec.colors !== undefined) {
    if (!Array.isArray(spec.colors) || spec.colors.length < 1 || spec.colors.length > 3) {
      throw new Error(`${where}: colors is one to three #rrggbb`);
    }
    spec.colors.forEach((c) => linearRGB(c, where));
  }
  if (spec.form === 'curtain' || spec.form === 'layer') {
    if (spec.bands !== undefined) checkBands(spec.bands, where);
    const sh = spec.sheets ?? 2;
    if (!Number.isInteger(sh) || sh < 1 || sh > 3) throw new Error(`${where}: sheets is 1, 2 or 3 (got ${JSON.stringify(spec.sheets)})`);
  }
  if (spec.form === 'shafts') {
    if (spec.occluder !== undefined && !(OCCLUDERS as readonly string[]).includes(spec.occluder)) {
      throw new Error(`${where}: occluder ${JSON.stringify(spec.occluder)} — one of ${OCCLUDERS.join(', ')}`);
    }
    if (spec.open !== undefined && (!finite(spec.open) || spec.open < 0 || spec.open > 1)) {
      throw new Error(`${where}: open is 0 (shut) .. 1 (clear), got ${JSON.stringify(spec.open)}`);
    }
  }
  for (const k of ['source', 'star', 'base'] as const) {
    const v = spec[k];
    if (v !== undefined && !(Array.isArray(v) && v.length === 2 && v.every(finite) && v.every((x) => Math.abs(x) <= 3))) {
      throw new Error(`${where}: ${k} is [u, v], fractions of the volume's box (|u|, |v| <= 3), got ${JSON.stringify(v)}`);
    }
  }
  if (spec.spread !== undefined && (!finite(spec.spread) || spec.spread <= 0 || spec.spread > 1)) {
    throw new Error(`${where}: spread is the fire's width as a share of the box, (0, 1]`);
  }
  return {...spec, intensity, seed, speed};
};

/** Bands: 1..VOLUME_MAX_BANDS, each a [from, to) km span with a colour; sorted by altitude; never overlapping (two
 *  emissions at one altitude are a haze, not a key — the colour of a height must be ONE colour). */
export const checkBands = (bands: Band[], where = 'volume'): Band[] => {
  if (!Array.isArray(bands) || bands.length < 1 || bands.length > VOLUME_MAX_BANDS) {
    throw new Error(`${where}: bands is 1-${VOLUME_MAX_BANDS} altitude spans {from, to, color}`);
  }
  const s = [...bands].sort((a, b) => a.from - b.from);
  s.forEach((b, i) => {
    if (!finite(b.from) || !finite(b.to) || !(b.to > b.from) || b.from < 0) {
      throw new Error(`${where}: band ${i + 1} needs from < to, both altitudes >= 0 (got ${JSON.stringify(b)})`);
    }
    linearRGB(b.color, where);
    if (b.gain !== undefined && (!finite(b.gain) || b.gain <= 0 || b.gain > 3)) {
      throw new Error(`${where}: band gain is (0, 3]`);
    }
    if (i > 0 && b.from < s[i - 1].to - 1e-9) {
      throw new Error(`${where}: bands ${s[i - 1].from}-${s[i - 1].to} and ${b.from}-${b.to} overlap — one altitude, ` +
        'one colour (draw a second emission at the same height as its own volume)');
    }
  });
  return s;
};

// ── the curtain's projection (shared by the shader and anything drawn beside it) ──────────────────────────────────
/**
 * WHERE AN ALTITUDE LANDS ON SCREEN. A curtain seen from the ground: the sheet stands at a distance, so altitude a km
 * lands at y = yHorizon - a * k, where k (px per km) is the screen's scale at the sheet's distance. A fold that swings
 * nearer is taller and hangs lower (k grows), one that swings away is shorter — the depth the old barcode never had.
 * `fit` returns the k and the horizon that put [lowKm, topKm] between screen ys [yLow, yTop] at the sheet's MEAN
 * distance — the scale a ruler beside the curtain uses, so the ruler and the light agree.
 */
export const curtainFit = (yTop: number, yLow: number, lowKm = AURORA_LOWER_KM, topKm = AURORA_TOP_KM) => {
  if (!(yLow > yTop)) throw new Error(`curtainFit: the lower border (${yLow}) must be below the top (${yTop})`);
  if (!(topKm > lowKm) || lowKm < 0) throw new Error(`curtainFit: topKm (${topKm}) must exceed lowKm (${lowKm}) >= 0`);
  const k = (yLow - yTop) / (topKm - lowKm);
  return {k, yHorizon: yLow + lowKm * k, yOf: (km: number) => yLow + lowKm * k - km * k};
};

/** How much nearer/farther the sheet swings, as a share of its mean distance: k varies by (1 +- DEPTH_SWING). Kept
 *  small so a ruler at the mean distance is right to within this share. */
export const CURTAIN_DEPTH_SWING = 0.12;

/** The weight each band has at an altitude — the curtain shader's bandColour, line for line: each BOUNDARY blends over
 *  a quarter of the thinner band beside it (at most 30 km either side), so the green turns red through the 200 km line
 *  rather than switching, and a thin band (the 20 km pink fringe) keeps its colour. The lowest band's floor is a cut
 *  (6 km below it): below the curtain's lower border there is no emission at all. */
export const bandWeights = (bands: Band[], km: number): number[] => {
  const s = [...bands].sort((a, b) => a.from - b.from);
  const sm = (e0: number, e1: number, x: number) => { const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };
  return s.map((b, i) => {
    const th = b.to - b.from, thP = i > 0 ? s[i - 1].to - s[i - 1].from : th, thN = i + 1 < s.length ? s[i + 1].to - s[i + 1].from : th;
    const blL = Math.min(30, 0.25 * Math.min(th, thP)), blH = Math.min(30, 0.25 * Math.min(th, thN));
    const hi = 1 - sm(b.to - blH, b.to + blH, km);
    return i === 0 ? hi * (km >= b.from - 6 ? 1 : 0) : sm(b.from - blL, b.from + blL, km) * hi;
  });
};

/** The emission colour at an altitude (the weighted mix of `bandWeights`, in linear light), or null where no band
 *  emits. */
export const colourAt = (bands: Band[], km: number): string | null => {
  const s = [...bands].sort((a, b) => a.from - b.from);
  const w = bandWeights(s, km);
  const sum = w.reduce((a, b) => a + b, 0);
  if (sum < 1e-4) return null;
  const lin = [0, 1, 2].map((c) => s.reduce((a, b, i) => a + linearRGB(b.color)[c] * w[i], 0) / sum);
  const enc = (v: number) => (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
  return '#' + lin.map((v) => Math.round(Math.max(0, Math.min(1, enc(v))) * 255).toString(16).padStart(2, '0')).join('');
};

// ── keep-out ────────────────────────────────────────────────────────────────────────────────────────────────────
/**
 * THE LIGHT STAYS OFF THE TYPE. Each rect the register's type occupies becomes an ellipse that clears the rect's
 * corners and feathers back to full light over VOLUME_KEEP_FEATHER_PX — the geometry runtime/optics' keepOutMask uses,
 * so the two keep type clear alike. Returned as the shader's uniform rows: [cx, cy, rx, ry] plus the inner radius `q`
 * (the rect's corner on the ellipse's own scale), in the volume box's px with y DOWN. More than VOLUME_MAX_KEEPOUT
 * rects throws rather than leaving some type under the light.
 */
export const keepOutRows = (rects: Rect[] | undefined, origin = {x: 0, y: 0}, scale = 1, where = 'volume') => {
  const rs = rects ?? [];
  if (rs.length > VOLUME_MAX_KEEPOUT) {
    throw new Error(`${where}: ${rs.length} keep-out rects — at most ${VOLUME_MAX_KEEPOUT}; merge the type's boxes`);
  }
  return rs.map((r) => {
    if (![r.x, r.y, r.w, r.h].every(finite) || r.w < 0 || r.h < 0) throw new Error(`${where}: keep-out rect ${JSON.stringify(r)}`);
    const a = r.w / 2, b = r.h / 2;
    const fe = Math.max(VOLUME_KEEP_FEATHER_PX, VOLUME_KEEP_FEATHER_FRAC * Math.max(r.w, r.h));
    const rx = a * Math.SQRT2 + fe, ry = b * Math.SQRT2 + fe;
    const q = Math.min(0.98, Math.hypot(a / rx, b / ry));
    return {cx: (r.x + a - origin.x) * scale, cy: (r.y + b - origin.y) * scale, rx: rx * scale, ry: ry * scale, q};
  });
};

/** How much light the keep-out lets through at (x, y) (same px as the rows): 0 inside a kept rect, 1 past its
 *  feather — the shader's own expression, here so a test can hold the shader's arithmetic to it. */
export const keepOutAt = (rows: ReturnType<typeof keepOutRows>, x: number, y: number,
  floor = VOLUME_KEEP_FLOOR): number => {
  let a = 1;
  for (const r of rows) {
    const d = Math.hypot((x - r.cx) / r.rx, (y - r.cy) / r.ry);
    const u = Math.max(0, Math.min(1, (d - r.q) / Math.max(1e-6, 1 - r.q)));
    a *= u * u * (3 - 2 * u);
  }
  return floor + (1 - floor) * a;
};
