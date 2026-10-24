// LIT MATERIAL GROUNDS — the topic's own medium as a surface with a light moving across it.
//
// WHY. A ground in this library is a colour (runtime/light.tsx) with, at most, a gradient treatment and a static
// grain over it (runtime/finish.tsx). That is the right default and the wrong ceiling: a film about a letter, a
// coastline, a machine or a pot is about a MEDIUM, and the medium's tell is how it answers light — paper's tooth
// catching a raking lamp, water's glints, the long highlight on brushed metal, clay's soft matte relief. The effects
// research (2026-10-24) measured the route: an SVG height field (feTurbulence, fractalNoise, 0.012 / 4 octaves for
// the water probe) lit by feSpecularLighting at surfaceScale 6-9 and exponent 20-30 reads as water, paper or metal,
// is a pure function of the frame (no canvas, no WebGL), and costs nothing measurable beside the baseline probe.
//
// THE SURFACE NEVER MOVES; THE LIGHT DOES. The height field is a fixed seed — the same paper on every frame, as a
// real sheet would be — and only the light's position is a function of the frame, drifting slowly across the
// sheet over the beat. That is the whole animation, and it is what makes it read as a lit object rather than a
// moving texture (a texture that crawls reads as video noise).
//
// NEVER UNDER BODY TYPE WITHOUT A CONTRAST PROOF. The lighting adds highlights and the relief adds shadow, so the
// ground under a line of type spans a RANGE of luminance, not one value. `materialRange` states that range for each
// material (the composite's arithmetic, checked against rendered frames by tests/test_optics.py), and a register
// that sets type on a material reads its ink from the range's WORST end — see LitMedium.
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export const MATERIALS = ['paper', 'water', 'metal', 'clay'] as const;
export type MaterialKind = (typeof MATERIALS)[number];

type Recipe = {
  /** feTurbulence */
  freq: string; octaves: number; seed: number;
  /** the lighting: diffuse (matte media) multiplies the base, specular (wet, polished) adds highlights */
  diffuse?: {scale: number; elevation: number};
  specular?: {scale: number; exponent: number; constant: number; z: number};
  /** feComposite arithmetic over (lighting, base): k1*L*B + k2*L + k3*B */
  k: [number, number, number];
  /** how far the light travels across the frame over one beat, as a fraction of the frame's width */
  drift: number;
};

// The four media. Frequencies are per PIXEL at 1080 on the short side and scaled by the frame (E8), so a 9:16
// frame has the same paper as a 16:9 one, not a coarser one.
export const RECIPES: Record<MaterialKind, Recipe> = {
  // paper: a fine tooth under a low raking lamp — matte, so the light MULTIPLIES the sheet's own colour
  // (k1 = 0.84 / sin(elevation): a FLAT patch of sheet comes back at 0.96 of its base — the lamp reveals the tooth,
  // it does not dim the paper; a first cut with k1 = 0.9 rendered cream paper as grey asphalt, 0.7 of its base)
  paper: {freq: '0.42', octaves: 4, seed: 11, diffuse: {scale: 0.7, elevation: 38}, k: [1.364, 0, 0.12], drift: 0.25},
  // water: a slow swell (stretched across the frame) with tight specular glints riding on it
  water: {freq: '0.006 0.018', octaves: 4, seed: 7, specular: {scale: 8, exponent: 26, constant: 0.85, z: 260},
    k: [0, 0.7, 0.85], drift: 0.35},
  // brushed metal: streaks along x (a long, thin noise), one anisotropic highlight band sliding along them
  // (surfaceScale 3 / exponent 20 rendered a barcode — every streak its own hard highlight; brushed metal is fine
  // streaks under ONE broad band, so the relief is shallow and the highlight wide)
  metal: {freq: '0.0018 0.42', octaves: 2, seed: 5, specular: {scale: 1.2, exponent: 9, constant: 0.75, z: 320},
    k: [0, 0.5, 0.8], drift: 0.45},
  // clay: a soft hand-worked relief, matte, a warm base
  clay: {freq: '0.022', octaves: 3, seed: 3, diffuse: {scale: 3.2, elevation: 48}, k: [1.077, 0, 0.18], drift: 0.2},
};

/** The luminance multipliers a recipe can put on its base: [darkest, brightest] factor of the base's own
 *  luminance (before clamping), from the composite's arithmetic with the lighting term at 0 and 1. Specular media
 *  ADD up to k2 of white, which is why their bright end is stated separately. */
export const materialRange = (kind: MaterialKind): {dark: number; bright: number; addWhite: number} => {
  const [k1, k2, k3] = RECIPES[kind].k;
  return {dark: k3, bright: k1 + k3, addWhite: k2};
};

/** Each medium's own colour, for a beat that names the medium and not its colour. */
export const MATERIAL_BASE: Record<MaterialKind, string> = {paper: '#ece5d5', water: '#173f5a', metal: '#a3aab2',
  clay: '#93512f'};

/** THE LIT GROUND'S MEASURED SPAN under a register's type: the 2nd and 98th percentile of what the lighting does to
 *  the base, over LitMedium's type column on its own light path (LitMedium LIGHT_TRAVEL), at frames 0/30/60/89 of a
 *  90-frame drift, at 16:9 and 9:16 — the worse aspect kept. A diffuse medium MULTIPLIES its base (`mul`, measured on
 *  a #808080 base); a specular one keeps k3 of the base and ADDS white (`add`, measured on #000000).
 *  Measured 2026-10-24 (OpticsProbe materialFull); tests/test_optics.py re-measures and fails when the recipe moves
 *  them past these bounds. paper mul .727-1.156 · water add 0-.169 (9:16; .118 at 16:9) · metal add .004-.310
 *  (9:16; .263 at 16:9) · clay mul .867-1.070. */
export const MATERIAL_SPAN: Record<MaterialKind, {mul: [number, number]; add: [number, number]}> = {
  paper: {mul: [0.72, 1.16], add: [0, 0]},
  water: {mul: [0.85, 0.85], add: [0, 0.17]},
  metal: {mul: [0.8, 0.8], add: [0, 0.31]},
  clay: {mul: [0.86, 1.07], add: [0, 0]},
};

const hex2 = (v: number) => Math.round(Math.max(0, Math.min(255, v * 255))).toString(16).padStart(2, '0');
/** The darkest and brightest ground the lit `base` puts under type — the two an ink must read on. */
export const materialShades = (kind: MaterialKind, base: string): [string, string] => {
  const c = [1, 3, 5].map((i) => parseInt(base.slice(i, i + 2), 16) / 255);
  const {mul, add} = MATERIAL_SPAN[kind];
  const at = (m: number, a: number) => '#' + c.map((x) => hex2(x * m + a)).join('');
  return [at(mul[0], add[0]), at(mul[1], add[1])];
};

export const isMaterial = (v: unknown): v is MaterialKind =>
  typeof v === 'string' && (MATERIALS as readonly string[]).includes(v);

/**
 * The lit ground: a full-frame SVG rect of `base`, its height field lit by a light that drifts across it with the
 * beat's frame. `light` is the DNA's key ('top' / 'bottom'); 'none' still lights the surface — a material with no
 * light is just its base colour — but holds the light still overhead instead of travelling it.
 */
export const LitGround: React.FC<{material: MaterialKind; base: string; light?: 'top' | 'bottom' | 'none';
  durF?: number;
  /** where along the key edge the light travels, as fractions of the frame's width [from, to]. Default: across the
   *  middle by the medium's own drift. A register with type on one side sends the light along the OTHER side, so the
   *  glints of a specular medium (which cluster under a low point light) stay out from under its words. */
  travel?: [number, number]}> = ({material, base, light = 'top', durF, travel}) => {
  if (!isMaterial(material)) {
    throw new Error(`LitGround: unknown material ${JSON.stringify(material)} — one of ${MATERIALS.join(', ')}`);
  }
  if (!/^#[0-9a-fA-F]{6}$/.test(base)) {
    throw new Error(`LitGround: base must be a #rrggbb colour (got ${JSON.stringify(base)}) — its luminance is what ` +
      'the ink on it is measured against');
  }
  const frame = useCurrentFrame();
  const {width: W, height: H, durationInFrames} = useVideoConfig();
  const r = RECIPES[material];
  const k = 1080 / Math.min(W, H);                    // the same grain per physical inch at every aspect
  const freq = r.freq.split(' ').map((f) => (Number(f) * k).toPrecision(4)).join(' ');
  const span = Math.max(1, durF ?? durationInFrames);
  const p = light === 'none' ? 0.5 : Math.min(1, frame / span);
  // the light rides the key edge and travels across it: from the left third toward the right over the beat
  const [t0, t1] = travel ?? [0.5 - r.drift / 2, 0.5 + r.drift / 2];
  if (!(Number.isFinite(t0) && Number.isFinite(t1))) throw new Error('LitGround: travel must be two numbers');
  const lx = W * (t0 + (t1 - t0) * p);
  const ly = light === 'bottom' ? H * 0.92 : H * 0.08;
  const id = `t2v-mat-${material}`;
  // a DISTANT light for the matte media: its azimuth turns with the drift (0 deg = from the right)
  const az = 200 - 40 * p;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}} aria-hidden data-material={material}>
      <defs>
        <filter id={id} x={0} y={0} width={W} height={H} filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={r.octaves} seed={r.seed}
            stitchTiles="stitch" result="h" />
          {r.diffuse ? (
            <feDiffuseLighting in="h" surfaceScale={r.diffuse.scale} diffuseConstant={1} lightingColor="#ffffff"
              result="L">
              <feDistantLight azimuth={az} elevation={r.diffuse.elevation} />
            </feDiffuseLighting>
          ) : (
            <feSpecularLighting in="h" surfaceScale={r.specular!.scale} specularConstant={r.specular!.constant}
              specularExponent={r.specular!.exponent} lightingColor="#ffffff" result="L">
              <fePointLight x={lx} y={ly} z={r.specular!.z} />
            </feSpecularLighting>
          )}
          {/* a specular map carries its own alpha (its highlight); flatten it onto black first so the arithmetic
              below adds LIGHT, not a translucent white sheet */}
          <feFlood floodColor="#000000" result="black" />
          <feComposite in="L" in2="black" operator="over" result="Lo" />
          <feComposite in="Lo" in2="SourceGraphic" operator="arithmetic" k1={r.k[0]} k2={r.k[1]} k3={r.k[2]} k4={0} />
        </filter>
      </defs>
      <rect x={0} y={0} width={W} height={H} fill={base} filter={`url(#${id})`} />
    </svg>
  );
};
