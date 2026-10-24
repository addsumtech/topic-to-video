// OPTICS — what the lens does with the light that is in the frame. One optic per beat, and only where the
// frame has a reason for it.
//
// WHY THIS EXISTS. The finish layer (runtime/finish.tsx) gave every themed film a print characteristic — grain, a
// corner falloff, a key direction — and deliberately nothing that MOVES or that knows where anything is. What it
// cannot say is "this screen is on", "that is a star", "the glass caught the light as it turned": the optical
// response of a real lens to a real source. Measured beside the reference launch films (references/craft-
// research.md, references/launch-film-study.md), that response is what the flat-fill look is missing — and the
// effects research (2026-10-24) is equally clear about how it turns cheap: an effect menu-picked, stacked, or on
// a frame with no light source in it. So every optic here is anchored to something the register draws, and a beat
// gets AT MOST ONE.
//
// THE VOCABULARY (the research's measured recipes, the numbers its probes settled on):
//   bloom       a real light source scatters in the lens: a copy of the SOURCE, blurred 24-40 px, screen-
//               blended at <= 0.3. Bit-exact (measured), no measurable cost.
//   halation    a highlight bleeds red through the film base: the copy keeps only luminance above ~0.7, is
//               tinted #ff4a1c, blurred about twice the bloom, alpha <= 0.15.
//   sweep       ONE pass of light across a hero surface as it settles — 20-30 frames, the band tilted ~30
//               degrees, travelling from the DNA's key side. Never a loop: a looping sheen is a screensaver.
//   aberration  lateral chromatic aberration at the edge of a wide lens: red and blue images scaled about the
//               frame centre so the split is 0 at the centre and 1-2 px at the corners. Applied to the PICTURE
//               layer only, never to type.
//   leak        light leaking into the camera at a cut: a warm wash burning in at the TOP edge (left for a key
//               above, right for a key below) whose visible life is 8-12 frames, centred on the seam. Film-level
//               (the Film draws it over the seam INTO the beat that declares it). Never the bottom edge: the caption
//               band is there, and each beat's caption is on screen for half of its seam.
//
// HOW A BEAT GETS ONE. A beat declares `optic` (storyboard `slide.optic` -> scene.optic; a standalone still takes
// it as the composition prop `optic`). A register says which optics it can ANCHOR with
// `export const OPTICS = [...] as const` and asks `useBeatOptic(OPTICS)`; validate.py reads that export and
// refuses a beat whose optic its register cannot anchor, and the runtime throws on the same mismatch rather than
// drawing nothing in silence (E9). A DNA can opt in with `optics: 'auto'`: a beat that declares nothing then
// takes its register's FIRST anchored optic that the DNA's light key admits — a key light ('top'/'bottom')
// admits all four, an unlit field ('none': a CRT, an arcade cabinet — "the tube IS the light") admits only the
// emitted-light pair, bloom and halation, because there is no key light to sweep with. No preset sets it.
//
// WHAT "NO OPTIC" DRAWS. Exactly what the register drew before this file existed: every primitive returns its
// children unchanged (a fragment adds no DOM) or null, so a beat that declares nothing is byte-identical — the
// optics tests render the five registers that anchor one and compare their PNGs to the pre-optics source.
//
// DETERMINISM. Every route here is CSS or SVG: a pure function of the frame, no canvas, no WebGL, no state.
// scripts/determinism_qa.py renders OpticsProbe twice, at concurrency 1 and 3, and frame N cold vs warm, and the
// optics test holds it to <= 2/255 on <= 0.01% of the pixels.
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import type {DesignDNA} from './dna';
import {SceneDurationContext, ReducedMotionContext, SEAM_FRAMES, ENTRY_T, clamp01} from './motion';

export const OPTIC_KINDS = ['bloom', 'halation', 'sweep', 'aberration', 'leak'] as const;
export type OpticKind = (typeof OPTIC_KINDS)[number];
/** The optics a REGISTER anchors — everything but the film-level leak. */
export type AnchoredOptic = Exclude<OpticKind, 'leak'>;
export type OpticSpec = {kind: OpticKind; intensity: number};
/** What a beat may write: a kind, a kind with an intensity, or 'none' (explicitly nothing, even under `auto`). */
export type OpticDecl = OpticKind | {kind: OpticKind; intensity?: number} | 'none' | null | undefined;

// ── the limits (the research's measured ranges; the CAPS are enforced, the defaults sit inside them) ──────────────
export const BLOOM_BLUR_PX = 32;            // inside the 24-40 px the research measured as reading as scatter
export const HALATION_BLUR_PX = 48;         // 2x the bloom's floor: halation travels further than lens scatter (at
                                            // 64 px a 12 px highlight spread to under 1% of its value — invisible)
export const HALATION_TINT = '#ff4a1c';
export const HALATION_THRESHOLD = 0.7;      // the luminance a highlight must exceed before it halates
export const SWEEP_FRAMES_MIN = 20;
export const SWEEP_FRAMES_MAX = 30;
export const SWEEP_ANGLE_DEG = 30;
export const LEAK_FRAMES = 10;              // the leak's visible life, inside the 8-12 the research measured
/** The intensity CAP per kind — opacity for bloom/halation/sweep/leak, the corner split in PIXELS for aberration. */
export const OPTIC_MAX: Record<OpticKind, number> = {bloom: 0.3, halation: 0.15, sweep: 0.3, aberration: 2, leak: 0.5};
export const OPTIC_DEFAULT: Record<OpticKind, number> = {bloom: 0.24, halation: 0.12, sweep: 0.22, aberration: 1.5,
  leak: 0.4};
/**
 * IMPLIED OPTICS, a DNA field that lives here rather than in runtime/dna.tsx (every register imports dna.tsx, and a
 * field added there re-keyed every register's measured manifest rows). `'auto'`: a beat that declares no `optic`
 * takes its register's first anchored optic that `finish.light` admits. Absent or `'none'`: only a beat's own
 * declaration draws one. NO preset sets it, so every preset film renders exactly what it rendered before optics.
 */
export type OpticsDNA = DesignDNA & {optics?: 'auto' | 'none'};
export const dnaOptics = (dna?: DesignDNA | null): 'auto' | 'none' | undefined => (dna as OpticsDNA | null | undefined)?.optics;

/** Which optics a DNA light key admits under `optics: 'auto'`. */
export const LIGHT_ADMITS: Record<'top' | 'bottom' | 'none', readonly OpticKind[]> = {
  top: ['bloom', 'halation', 'sweep', 'aberration'],
  bottom: ['bloom', 'halation', 'sweep', 'aberration'],
  none: ['bloom', 'halation'],
};

/** A beat's declaration, normalised — or a throw. Unknown kinds and intensities past the cap are refused: an optic
 *  past its cap stops being an optic and becomes the effect-menu look this file exists to avoid. */
export const normalizeOptic = (decl: OpticDecl, where = 'optic'): OpticSpec | null => {
  if (decl === undefined || decl === null || decl === 'none') return null;
  const kind = typeof decl === 'string' ? decl : decl.kind;
  if (!(OPTIC_KINDS as readonly string[]).includes(kind as string)) {
    throw new Error(`${where}: unknown optic ${JSON.stringify(kind)} — one of ${OPTIC_KINDS.join(', ')} or 'none'`);
  }
  const k = kind as OpticKind;
  const raw = typeof decl === 'string' ? undefined : decl.intensity;
  if (raw !== undefined && (typeof raw !== 'number' || !Number.isFinite(raw) || raw <= 0 || raw > OPTIC_MAX[k])) {
    throw new Error(`${where}: ${k} intensity must be in (0, ${OPTIC_MAX[k]}] (got ${JSON.stringify(raw)}) — ` +
      'past the cap it stops reading as light and starts reading as an effect');
  }
  return {kind: k, intensity: raw ?? OPTIC_DEFAULT[k]};
};

export type OpticState = {spec: OpticSpec | null; auto: boolean; light: 'top' | 'bottom' | 'none'; declared: boolean};
/** Provided per beat by the Film (and by a standalone register preview). Absent = no optic, exactly as before. */
export const OpticContext = React.createContext<OpticState | null>(null);

/** The light key a DNA states (finish.light), 'top' when it states none. */
export const dnaLight = (dna?: DesignDNA | null): 'top' | 'bottom' | 'none' => {
  const f = dna?.finish;
  return f && f !== 'none' && f.light ? f.light : 'top';
};

/** The state a beat provides: its own declaration, and whether the DNA opted into implied optics. */
export const opticState = (decl: OpticDecl, dna?: DesignDNA | null, where?: string): OpticState => ({
  spec: normalizeOptic(decl, where), auto: dnaOptics(dna) === 'auto', light: dnaLight(dna),
  declared: decl !== undefined && decl !== null,
});

/**
 * THE OPTIC THIS REGISTER DRAWS ON THIS BEAT, or null. `offered` is the register's own `OPTICS` export.
 * A declared optic the register cannot anchor THROWS — validate.py refuses the same board first; a leak is the
 * Film's to draw and the register draws nothing for it. Under `auto` the first offered optic the light admits.
 */
export const useBeatOptic = (offered: readonly AnchoredOptic[]): OpticSpec | null => {
  const st = React.useContext(OpticContext);
  if (!st) return null;
  if (st.spec) {
    if (st.spec.kind === 'leak') return null;
    if (!(offered as readonly string[]).includes(st.spec.kind)) {
      throw new Error(`this beat declares optic '${st.spec.kind}', which its register cannot anchor (it offers ` +
        `${offered.length ? offered.join(', ') : 'none'}). An optic encodes where the light is; a register with no ` +
        'such light has nothing for it to act on. Pick one it offers, or a register whose picture has that light.');
    }
    return st.spec;
  }
  if (st.declared || !st.auto) return null;            // 'none' stays none, even under auto
  const k = offered.find((o) => LIGHT_ADMITS[st.light].includes(o));
  return k ? {kind: k, intensity: OPTIC_DEFAULT[k]} : null;
};

/** `o` when it is of kind `k`, else null — for a register that anchors two optics on two different layers. */
export const ofKind = (o: OpticSpec | null, k: OpticKind): OpticSpec | null => (o && o.kind === k ? o : null);

/** The beat frame at which `useT()` reaches `T` — the frame a register's own clock calls "landed", so a sweep can be
 *  timed to the moment the surface settles rather than to a fixed second (useT holds the pads at both edges). */
export const useFrameAtT = (T: number): number => {
  const {durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const dur = sceneDur ?? durationInFrames;
  const pad = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, dur - 1) / 3));
  const span = Math.max(1, dur - 1 - 2 * pad);
  return Math.round(pad + span * clamp01((T - ENTRY_T) / (1 - ENTRY_T)));
};

/** The light key in force for this beat ('top' with no context) — a sweep or a leak enters from it. */
export const useOpticLight = (): 'top' | 'bottom' | 'none' => React.useContext(OpticContext)?.light ?? 'top';

// ── the shared SVG filters (identical content wherever they are mounted, so a duplicate id is harmless) ───────────
const lum = '0.2126 0.7152 0.0722';
const tint = (hex: string) => [1, 2, 3].map((i) => (parseInt(hex.slice(2 * i - 1, 2 * i + 1), 16) / 255).toFixed(4));
const [HR, HG, HB] = tint(HALATION_TINT);
// alpha -> 0 below the threshold, 1 by threshold + 0.25: slope 4, intercept -4*threshold
const HAL_SLOPE = 4, HAL_INTERCEPT = -(4 * HALATION_THRESHOLD);
export const OpticDefs: React.FC = () => (
  <svg width={0} height={0} style={{position: 'absolute', width: 0, height: 0}} aria-hidden data-echo="">
    <defs>
      <filter id="t2v-halation" x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values={`0 0 0 0 ${HR}  0 0 0 0 ${HG}  0 0 0 0 ${HB}  ${lum} 0 0`} />
        <feComponentTransfer><feFuncA type="linear" slope={HAL_SLOPE} intercept={HAL_INTERCEPT} /></feComponentTransfer>
      </filter>
      <filter id="t2v-ch-r" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" />
      </filter>
      <filter id="t2v-ch-g" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" />
      </filter>
      <filter id="t2v-ch-b" colorInterpolationFilters="sRGB">
        <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" />
      </filter>
    </defs>
  </svg>
);

const COPY: React.CSSProperties = {position: 'absolute', inset: 0, pointerEvents: 'none'};

export type Rect = {x: number; y: number; w: number; h: number};
/** How far past a kept-out rect the glow takes to come back to full strength. */
export const KEEP_OUT_FEATHER_PX = 90;

/**
 * KEEP THE GLOW OFF THE TYPE. A lens really does veil type in front of a bright source — and that is exactly what
 * a film cannot afford: measured on StarfieldWarp's settled frame, a bloom at 0.24 over the core behind the title
 * took the title's contrast from 10.34:1 to 9.53:1 (92%), and SpotlightStage's from 11.68 to 10.93 (94%). So a glow
 * is masked out of each rect the register's type occupies, by an ellipse that clears the rect's corners and feathers
 * back to full strength over KEEP_OUT_FEATHER_PX. A CSS gradient mask, not an image: it is painted with the frame
 * (no decode to wait for), so the frame stays a pure function of its number. `origin` is the copy's own top-left.
 */
const keepOutMask = (rects: Rect[] | undefined, origin = {x: 0, y: 0}): React.CSSProperties => {
  if (!rects || !rects.length) return {};
  const layers = rects.map((r) => {
    const a = r.w / 2, b = r.h / 2;
    const rx = a * Math.SQRT2 + KEEP_OUT_FEATHER_PX, ry = b * Math.SQRT2 + KEEP_OUT_FEATHER_PX;
    const q = Math.min(0.98, Math.hypot(a / rx, b / ry));          // the rect's corner, on the ellipse's own scale
    return `radial-gradient(${rx.toFixed(1)}px ${ry.toFixed(1)}px at ${(r.x + a - origin.x).toFixed(1)}px ` +
      `${(r.y + b - origin.y).toFixed(1)}px, transparent ${(q * 100).toFixed(1)}%, black 100%)`;
  });
  const m = layers.join(', ');
  return {WebkitMaskImage: m, maskImage: m, WebkitMaskComposite: 'source-in', maskComposite: 'intersect',
    WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat'} as React.CSSProperties;
};

/** The bloom/halation look of a copy: blur, blend, capped opacity. */
const glowStyle = (optic: OpticSpec, blur?: number): React.CSSProperties => {
  if (optic.kind === 'bloom') {
    return {filter: `blur(${Math.max(24, Math.min(40, blur ?? BLOOM_BLUR_PX))}px)`, mixBlendMode: 'screen',
      opacity: Math.min(OPTIC_MAX.bloom, optic.intensity)};
  }
  return {filter: `url(#t2v-halation) blur(${blur ? Math.max(48, Math.min(80, blur * 2)) : HALATION_BLUR_PX}px)`,
    mixBlendMode: 'screen', opacity: Math.min(OPTIC_MAX.halation, optic.intensity)};
};

/**
 * ONLY the glow of a source the register draws ELSEWHERE — inside a clip it cannot spill out of (a device's screen
 * behind its bezel). The copy is clipped to the source's own shape at `rect`, then blurred, so the light spills past
 * the shape the way a lit screen's does. Nothing without a bloom/halation optic.
 */
export const GlowCopy: React.FC<{optic: OpticSpec | null; rect: Rect;
  radius?: number | string; blur?: number; keepOut?: Rect[]; children: React.ReactNode}> = ({optic, rect, radius = 0, blur,
  keepOut, children}) => {
  if (!optic || (optic.kind !== 'bloom' && optic.kind !== 'halation')) return null;
  return (
    <>
      {optic.kind === 'halation' ? <OpticDefs /> : null}
      {/* the keep-out mask sits on a full-frame wrapper: on the blurred element itself it would also clip the spill.
          The BLEND goes on the wrapper too — a mask makes its element an isolated group, so a screen inside it would
          blend with nothing and land on the frame as a plain over */}
      <div aria-hidden data-echo="" style={{...COPY, ...keepOutMask(keepOut), mixBlendMode: 'screen'}}>
        <div data-optic={optic.kind} style={{position: 'absolute', left: rect.x, top: rect.y,
          width: rect.w, height: rect.h, pointerEvents: 'none', ...glowStyle(optic, blur), mixBlendMode: 'normal'}}>
          <div style={{position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: radius}}>{children}</div>
        </div>
      </div>
    </>
  );
};

/**
 * BLOOM / HALATION around a light SOURCE. `children` must be a layer positioned against the same box as this
 * element's container (an absolutely positioned layer: the copy is laid over it at `inset: 0`). With no optic, or
 * an optic of another kind, the children come back untouched.
 */
export const OpticSource: React.FC<{optic: OpticSpec | null; children: React.ReactNode; blur?: number;
  /** the rects the register's TYPE occupies (frame px): the glow is masked out of them (see keepOutMask) */
  keepOut?: Rect[]}> = ({optic, children, blur, keepOut}) => {
  if (!optic || (optic.kind !== 'bloom' && optic.kind !== 'halation')) return <>{children}</>;
  const masked = !!(keepOut && keepOut.length);
  // masked: the blend moves to the masked wrapper (a mask isolates its element, so a screen inside it would blend
  // with nothing and land as a plain over)
  const copy = <div aria-hidden data-echo="" data-optic={optic.kind} style={{...COPY, ...glowStyle(optic, blur),
    ...(masked ? {mixBlendMode: 'normal' as const} : {})}}>{children}</div>;
  return (
    <>
      {children}
      {optic.kind === 'halation' ? <OpticDefs /> : null}
      {masked ? <div aria-hidden data-echo="" style={{...COPY, ...keepOutMask(keepOut), mixBlendMode: 'screen'}}>{copy}</div>
        : copy}
    </>
  );
};

/** The sweep's position along its travel at `frame` (beat-relative): null before it starts and after it ends. */
export const sweepAt = (frame: number, start: number, frames: number): number | null => {
  const n = Math.max(SWEEP_FRAMES_MIN, Math.min(SWEEP_FRAMES_MAX, Math.round(frames)));
  const p = (frame - start) / (n - 1);
  if (p < 0 || p > 1) return null;
  return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;      // easeInOutCubic: arrives, crosses, leaves
};

/**
 * ONE PASS OF LIGHT across a hero surface. Mount it INSIDE the surface (a positioned element); it clips itself to
 * the surface's box and corner radius. `start` is the beat frame the surface settles on — the moment a real
 * surface turning into its rest catches the key. Draws nothing outside its 20-30 frames, so every other frame of
 * the beat is the register's own.
 */
export const LightSweep: React.FC<{optic: OpticSpec | null; start: number; frames?: number; radius?: number | string}> = ({
  optic, start, frames = 24, radius = 0,
}) => {
  const frame = useCurrentFrame();
  const light = useOpticLight();
  const reduced = React.useContext(ReducedMotionContext);
  if (!optic || optic.kind !== 'sweep' || reduced) return null;      // a travelling light is motion
  const e = sweepAt(frame, start, frames);
  if (e === null) return null;
  // the band travels from the key side: from top-left for a key above, from bottom-right for a key below
  const p = light === 'bottom' ? 1 - e : e;
  const at = -25 + 150 * p;                                     // % along the gradient line: fully off at both ends
  const a = Math.min(OPTIC_MAX.sweep, optic.intensity);
  return (
    <div aria-hidden data-optic="sweep" style={{...COPY, overflow: 'hidden', borderRadius: radius,
      mixBlendMode: 'screen',
      background: `linear-gradient(${90 + SWEEP_ANGLE_DEG}deg, rgba(255,255,255,0) ${at - 14}%, ` +
        `rgba(255,255,255,${(a * 0.35).toFixed(3)}) ${at - 5}%, rgba(255,255,255,${a.toFixed(3)}) ${at}%, ` +
        `rgba(255,255,255,${(a * 0.35).toFixed(3)}) ${at + 5}%, rgba(255,255,255,0) ${at + 14}%)`}} />
  );
};

/**
 * LATERAL CHROMATIC ABERRATION on a PICTURE layer of emitted light (stars, a phosphor field): the layer is drawn as
 * three channel images added onto what is below it, red scaled up and blue scaled down about the frame centre, so
 * the split is zero at the centre and `intensity` px at the far corners. Adding is what emitted light does; it is
 * why this optic is offered only by registers whose picture IS light on a dark ground. Type never goes inside it.
 */
export const Aberration: React.FC<{optic: OpticSpec | null; children: React.ReactNode}> = ({optic, children}) => {
  const {width: W, height: H} = useVideoConfig();
  if (!optic || optic.kind !== 'aberration') return <>{children}</>;
  const half = Math.hypot(W, H) / 2;
  const s = Math.min(OPTIC_MAX.aberration, optic.intensity) / half;
  const ch = (c: 'r' | 'g' | 'b', k: number, echo: boolean) => (
    <div key={c} {...(echo ? {'aria-hidden': true, 'data-echo': ''} : {})} data-optic={`aberration-${c}`}
      style={{...COPY, filter: `url(#t2v-ch-${c})`, mixBlendMode: 'plus-lighter',
        transform: k === 1 ? undefined : `scale(${k.toFixed(6)})`, transformOrigin: '50% 50%'}}>{children}</div>
  );
  return (
    <>
      <OpticDefs />
      {ch('r', 1 + s, false)}
      {ch('g', 1, true)}
      {ch('b', 1 - s, true)}
    </>
  );
};

/** The leak's envelope at seam frame `f` (0 = the seam's first frame of `seam`): 0 outside its LEAK_FRAMES life. */
export const leakAt = (f: number, seam: number): number => {
  const lead = Math.max(0, Math.round((seam - LEAK_FRAMES) / 2));
  const x = (f - lead) / (LEAK_FRAMES - 1);
  if (x < 0 || x > 1) return 0;
  return Math.sin(Math.PI * x) ** 2;                              // rises, peaks mid-seam, gone before the seam ends
};

/**
 * A LIGHT LEAK over a seam: warm light entering at the key edge, drifting along it. `f` is the frame within the
 * seam. Drawn by the Film above the beats and below the finish and the caption HUD.
 */
export const SeamLeak: React.FC<{optic: OpticSpec; f: number; seam: number; light: 'top' | 'bottom' | 'none'}> = ({
  optic, f, seam, light,
}) => {
  const {width: W, height: H} = useVideoConfig();
  const e = leakAt(f, seam);
  if (e <= 0) return null;
  const a = Math.min(OPTIC_MAX.leak, optic.intensity) * e;
  // ALWAYS THE TOP EDGE: the caption band is at the bottom, and a leak at the bottom edge would brighten the ground
  // under the caption the burned ink was picked against. A key from below mirrors it to the top-right instead.
  const along = 18 + 24 * (f / Math.max(1, seam - 1));            // drifts along the edge as it burns
  const x = light === 'bottom' ? 100 - along : along;
  const y = 2;
  const big = Math.max(W, H);
  return (
    <div aria-hidden data-optic="leak" style={{...COPY, mixBlendMode: 'screen', opacity: a,
      // a hot core JUST INSIDE the key edge falling through orange to a red fringe. Over a dark frame a screen layer at
      // opacity a can reach only a x its own colour, so the first cut (0.22, its core above the frame) read as a brown
      // smudge; with the core inside the edge and the cap at 0.5 it reads as light burning in at the corner
      background: `radial-gradient(${Math.round(big * 0.42)}px ${Math.round(big * 0.3)}px at ${x}% ${y}%, ` +
        `#fff1dc 0%, #ffb067 22%, rgba(255,106,48,0.75) 44%, rgba(255,60,40,0) 72%), ` +
        `radial-gradient(${Math.round(big * 0.26)}px ${Math.round(big * 0.2)}px at ${light === 'bottom' ? x - 30 : x + 30}% ${y}%, ` +
        `rgba(255,214,150,0.9) 0%, rgba(255,150,80,0) 70%)`}} />
  );
};
