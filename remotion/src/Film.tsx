// FILM · data-driven — sequences any list of bespoke shots into a narrated film. Each SCENE names a `shot`
// (looked up in REGISTRY), its topic `props`, a frame-length `durF`, an optional narration `mp3` (served from
// public/) and a `caption`. Scenes CROSS-DISSOLVE (overlapping ~0.4s to ride the narration breath). Captions
// ride a SINGLE top-level HUD track (a #hud sibling, per huashu's camera-rig discipline) that HARD-CUTS one
// caption at a time inside each scene's sole-visible window — so two captions can never overlap across a
// transition (the old A1 doubling bug) — and picks its ink CONTRAST against the scene's ground luminance.
// render_remotion.py drives this via --props; the WorkBuddy film is just the default. Deterministic.

import React from 'react';
import {AbsoluteFill, Audio, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {dissolve} from '@remotion/transitions/dissolve';
import {SceneDurationContext, ReducedMotionContext, clamp01} from './runtime/motion';
import {groundLum, dnaGroundLum, dnaGroundY, groundGap, type Lum, type GroundColors} from './runtime/shotLuma';
import {Atmosphere, type Atmo} from './runtime/atmosphere';
import {DesignDNAContext, type DesignDNA, dnaFromTemplate, coerceDna, TerminalChrome} from './runtime/dna';
import {REGISTRY} from './registry';
import {CAPTIONS} from './captions';

// The scene EDL. `bgLum` is the first of the shot-director-emitted continuity fields (an explicit ground-
// luminance override; falls back to the measured shotLuma map). Future phases grow this schema (accent,
// camera{}, carry{}, transitionIn{}, audioCues[]) — all OPTIONAL + remotion-only, so the html tier is untouched.
export type SceneSpec = {shot: string; props?: Record<string, unknown>; durF: number; mp3?: string;
  caption?: string; bgLum?: Lum;
  // TERMINAL CHROME per scene (remotion + DNA only): a command-path + status readout the Film frames every beat
  // with (see runtime/dna.tsx TerminalChrome). Optional; inert unless the active DNA speaks 'breadcrumb'.
  chrome?: {path?: string; status?: string; root?: string};
  // A MARKED seam (chapter break): the transition INTO this scene from the previous one. Optional +
  // remotion-only; unset = the luminance-safe default (a gentle cross-fade). A kinetic type is honored only
  // on a same/near-luminance seam — across a dark↔light gap it's suppressed back to fade (see pickPresentation).
  transitionIn?: {type: 'fade' | 'slide' | 'wipe' | 'clock' | 'dissolve' | 'carry'; direction?: string}};

const TR = 12; // cross-dissolve length (frames) — rides the ~0.42s narration breath so speech barely overlaps
export const filmDuration = (scenes: SceneSpec[]) =>
  Math.max(1, scenes.reduce((a, s) => a + Math.max(1, Math.round(s.durF)), 0) - Math.max(0, scenes.length - 1) * TR);

// The WorkBuddy film as DATA (the default) — 14 beats, families varied per LIBRARY.md; ChartLive shows the
// FAITHFUL sourced 68× Hy3 surge (never the shot's demo number).
const WB_SEC = [9.3, 9.075, 9.224, 11.495, 12.632, 10.538, 9.0, 10.41, 10.692, 15.363, 14.738, 11.311, 10.314, 4.624];
const WB_SHOTS = ['ChatThread', 'CinematicTitle', 'ExplodedSchematic', 'CollaborativeCursors', 'KnowledgeGraph',
  'BlockAssembly', 'BlueprintGrid', 'FocalIsolation', 'MapRoutes', 'MaterialHero', 'ParticleForm', 'ChartLive', 'HandDrawn', 'LiquidChrome'];
const WB_PROPS: Record<number, Record<string, unknown>> = {11: {endVal: 68, unit: '×', label: 'Hy3 call volume · first week'}};
// The ~3 MARKED seams (the rest ride the luminance-safe default fade) — each on a same-luminance boundary so
// the kinetic move can't flash, and each motivated by the two beats' relationship, never decoration:
const WB_TRANS: Record<number, NonNullable<SceneSpec['transitionIn']>> = {
  2: {type: 'clock'},                            // CinematicTitle → ExplodedSchematic: the title OPENS the mechanism
  9: {type: 'slide', direction: 'from-right'},   // MapRoutes → MaterialHero: the routes push forward into the hero
  10: {type: 'dissolve'},                         // MaterialHero → ParticleForm: the solid hero DISSOLVES to particles
  12: {type: 'carry'},                            // ChartLive → HandDrawn: the data COLLAPSES to a line, the human takeaway grows from it (crosses dark→light)
};
// The default preview is SILENT (no demo audio ships with the skill) — a real film's per-scene narration is
// supplied by render_remotion.py from the out_dir (`sc.mp3`), served via --public-dir.
export const WORKBUDDY_SCENES: SceneSpec[] = WB_SHOTS.map((shot, i) => ({
  shot, props: WB_PROPS[i] ?? {}, durF: Math.round(WB_SEC[i] * 30), caption: CAPTIONS[i], transitionIn: WB_TRANS[i],
}));

// Split a caption into progressively-shown chunks. Splits on sentence enders — ASCII (.!?) AND CJK (。！？) —
// so a 中文 caption chunks per sentence too (not one block). Short LATIN fragments merge into their neighbour
// (the 22-char floor is a Latin measure); CJK sentences each stand alone (a full sentence is few chars but a
// complete thought, and merging them by a Latin char-count would collapse them). Never empty. Deterministic.
const isCJKText = (s: string): boolean => /[㐀-鿿぀-ヿ가-힯]/.test(s);
const splitCaption = (text: string): string[] => {
  const chunks = text.match(/[^.!?。！？—]+[.!?。！？]?(\s*—)?/g)?.map((c) => c.trim()).filter(Boolean) ?? [text];
  const merged: string[] = [];
  for (const c of chunks) {
    const prev = merged[merged.length - 1];
    if (prev && !isCJKText(c) && !isCJKText(prev) && (prev.length < 22 || c.length < 22)) merged[merged.length - 1] += ' ' + c;
    else merged.push(c);
  }
  return merged;
};

const CAP_PAD = 4;   // clean-gap frames inside each scene's sole-visible window → guarantees exit-before-enter
const CAP_FADE = 3;  // tiny in/out ramp WITHIN the window (never across a transition, so captions never double)
// FRAME-CRAFT FLOOR. An earlier version scaled the WHOLE world to 0.86 to pull edge content inside action-safe —
// but that shrank each shot's OWN full-bleed background too, so a ~14% margin of the near-black atmosphere showed
// as BLACK BORDERS on the sides + bottom (the shot background must reach the frame edge). So the world now renders
// FULL-BLEED (no scale, no lift); edge-safety is a per-SHOT contract that frame_safe_qa verifies deterministically,
// and the bottom CAPTION_BAND is reserved by the SHOTS keeping content out of it — not by shrinking the picture.
const CAPTION_BAND = 150;    // px at the bottom reserved for the caption; shots keep text above (H - CAPTION_BAND)

// One global caption HUD. It shows AT MOST ONE caption — the one belonging to the scene whose sole-visible
// window (between its two transitions) contains this frame — hard-cut, contrast-picked against that scene's
// ground luminance. Because the windows are disjoint, two captions can never coexist across a dissolve.
const CaptionTrack: React.FC<{scenes: SceneSpec[]; groundBg?: string; dnaColors?: GroundColors | null;
  dnaFontBody?: string | null}> = ({scenes, groundBg, dnaColors, dnaFontBody}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  let acc = 0;
  const starts = scenes.map((sc) => { const s = acc; acc += Math.max(1, Math.round(sc.durF)) - TR; return s; });
  let active = -1, ws = 0, we = 0;
  for (let i = 0; i < scenes.length; i++) {
    const dur = Math.max(1, Math.round(scenes[i].durF));
    const a = starts[i] + (i > 0 ? TR : 14) + CAP_PAD;                       // clear the transition-in / intro
    const b = starts[i] + dur - (i < scenes.length - 1 ? TR : 16) - CAP_PAD; // clear the transition-out / outro
    if (frame >= a && frame <= b) { active = i; ws = a; we = b; break; }
  }
  const sc = active >= 0 ? scenes[active] : undefined;
  if (!sc || !sc.caption) return null;
  const merged = splitCaption(sc.caption);
  // WEIGHT each chunk's on-screen time by its LENGTH (not equal slices) — else a 3-word chunk lingers while a
  // 20-word chunk races the voice. Advance idx by cumulative char-fraction of the caption.
  const lens = merged.map((c) => Math.max(1, c.length));
  const total = lens.reduce((a, b) => a + b, 0);
  const local = clamp01((frame - ws) / Math.max(1, we - ws));
  let idx = merged.length - 1, cum = 0;
  for (let i = 0; i < merged.length; i++) { cum += lens[i] / total; if (local <= cum) { idx = i; break; } }
  const op = Math.min(clamp01((frame - ws) / CAP_FADE), clamp01((we - frame) / CAP_FADE));
  // The DNA repaints most shots' grounds, so classify THIS frame's real ground (dnaGroundLum) — reading the
  // measured pre-DNA constant here is what put dark ink on a themed dark ground.
  const lum = dnaGroundLum(sc.shot, sc.bgLum, dnaColors);
  const ink = lum === 'light' ? '#141414' : '#ffffff';
  // The subtitle sits DIRECTLY on the frame's own background — there is NO scrim/bar rectangle behind it.
  // The shots reserve the bottom CAPTION_BAND (content never reaches it), so the caption's ground is the
  // frame's own clean atmosphere; the ink is contrast-picked (dark on light / white on dark). The only
  // separation is a SUBTLE text-shadow in the frame's OWN ground colour (never a white/black halo — the html
  // `overlay` mode had exactly that white-halo bug), just for anti-alias crispness where the ground varies.
  const gb = groundBg && /^#[0-9a-fA-F]{6}$/.test(groundBg) ? groundBg : (lum === 'light' ? '#f4f1ea' : '#05060a');
  const shadow = `0 1px 2px ${gb}e6, 0 0 1px ${gb}`;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'relative', maxWidth: Math.min(1400, width - 80), margin: '0 auto 40px', padding: '0 60px', textAlign: 'center',
        color: ink, font: `700 44px/1.26 ${dnaFontBody ?? 'Inter, "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif'}`,
        letterSpacing: '-0.01em', textShadow: shadow}}>{merged[idx]}</div>
    </AbsoluteFill>
  );
};

// CARRY (a collapse-to-line match-cut) — the one transition that reads as CONTINUITY, not a swap. The exiting
// scene collapses vertically into a thin neutral line at center; the incoming scene expands back out from that
// same line. The eye tracks the shared line across the cut, so two unrelated shots read as one continuous move
// (huashu's collapse-to-line). Because the bridge line is a MID-neutral, it doubles as the luminance dip — this
// is the only marked transition allowed to cross a dark↔light gap (its bright line IS the through-gray moment,
// by design, not an accidental flash). Deterministic (pure fn of presentationProgress); works for ANY pair.
const CarryPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const line = (passedProps && passedProps.line) || '#9aa0aa';
  const isEnter = presentationDirection === 'entering';
  const ease = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const, easing: Easing.inOut(Easing.cubic)};
  const scaleY = isEnter ? interpolate(p, [0.5, 1], [0.006, 1], ease) : interpolate(p, [0, 0.5], [1, 0.006], ease);
  const clampBoth = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const op = isEnter ? interpolate(p, [0.46, 0.56], [0, 1], clampBoth) : interpolate(p, [0.44, 0.54], [1, 0], clampBoth);
  const lineOp = interpolate(p, [0.15, 0.5, 0.85], [0, 1, 0], clampBoth);
  return (
    <>
      <AbsoluteFill style={{transform: `scaleY(${scaleY})`, transformOrigin: 'center', opacity: op}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 2, marginTop: -1,
          background: line, opacity: lineOp, boxShadow: `0 0 18px 3px ${line}`}} />
      </AbsoluteFill>
    </>
  );
};
const carry = (line?: string): TransitionPresentation<any> => ({component: CarryPresentation, props: {line}});

// SCREEN-CLEAR — a TERMINAL-native seam (Motion grammar layer): the outgoing scene dips through the DNA bg while
// a bright accent scanline SWEEPS down (a CRT/console refresh), then the incoming scene resolves. Luminance-SAFE
// by construction (it dips through the bg, so a dark↔light pair never flashes). Subtle enough to be the DEFAULT
// seam of a terminal film — the cut reads as "the terminal redrawing between outputs", not a generic fade.
const ScreenClearPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const bg = passedProps?.bg ?? '#06080d', acc = passedProps?.accent ?? '#3dd6a4';
  const isEnter = presentationDirection === 'entering';
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const op = isEnter ? interpolate(p, [0.44, 0.62], [0, 1], c) : interpolate(p, [0.38, 0.56], [1, 0], c);
  const veil = interpolate(p, [0.22, 0.5, 0.82], [0, 0.82, 0], c);        // dip through bg at mid
  const sweepY = interpolate(p, [0.26, 0.74], [-0.08, 1.08], c);          // scanline sweeps top→bottom
  const sweepOp = interpolate(p, [0.24, 0.5, 0.78], [0, 0.55, 0], c);
  return (
    <>
      <AbsoluteFill style={{opacity: op}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{pointerEvents: 'none', background: bg, opacity: veil}} />
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div style={{position: 'absolute', left: 0, right: 0, top: `${(sweepY * 100).toFixed(2)}%`, height: 3,
          background: acc, opacity: sweepOp, boxShadow: `0 0 24px 4px ${acc}`}} />
      </AbsoluteFill>
    </>
  );
};
const screenClear = (bg?: string, accent?: string): TransitionPresentation<any> => ({component: ScreenClearPresentation, props: {bg, accent}});

// DNA-native DEFAULT seam (Motion grammar): an UNMARKED seam on a themed film becomes the STYLE's native action
// instead of a generic fade — the analogue of the surface/grammar split for TIME. terminal → screen-clear;
// product → a soft push; editorial/blueprint → a directional wipe (a page/sheet turn); else the gentle fade.
const dnaDefaultSeam = (dna: DesignDNA | null, W: number, H: number): TransitionPresentation<any> | null => {
  if (!dna) return null;
  switch (dna.id) {
    case 'terminal': return screenClear(dna.bg, dna.accent);
    case 'product': case 'apple': return slide({direction: 'from-right'});
    case 'editorial': case 'blueprint': return wipe({direction: 'from-bottom'});
    case 'data': return wipe({direction: 'from-left'});             // a measured sweep, like a chart redrawing
    case 'retro': return slide({direction: 'from-bottom'});         // an arcade screen push
    // 'cinematic' (and any unknown id) keep the gentle cross-fade — the filmic seam IS a dissolve.
    default: return null;
  }
};

const LUM_RANK: Record<Lum, number> = {dark: 0, mid: 1, light: 2};

// The seam GRAMMAR. A seam is luminance-SAFE by default and SEMANTIC when marked. A ground-luminance gap of
// ≥2 (a dark↔light cut) FORCES a gentle cross-fade — it blends through mid-gray so there's no brightness
// flash, and a hard kinetic edge (a bright scene sliding over a dark one) is exactly what we suppress there.
// On a same/near-luminance seam the EDL may MARK a kinetic move (slide/wipe/clock/dissolve) for a chapter
// break; unmarked seams stay a fade. Every seam holds at TR frames so it rides the audio-breath silence
// (A/V stays in sync); no spins, ever. Deterministic — pure fn of the two scenes' declared ground.
const pickPresentation = (prev: SceneSpec, next: SceneSpec, W: number, H: number, dna: DesignDNA | null): TransitionPresentation<any> => {
  const dLum = Math.abs(LUM_RANK[dnaGroundLum(next.shot, next.bgLum, dna)] - LUM_RANK[dnaGroundLum(prev.shot, prev.bgLum, dna)]);
  const want = next.transitionIn?.type ?? 'fade';
  // luminance guard: a dark↔light gap forces the gentle fade — EXCEPT carry, whose neutral bridge line IS the dip.
  // PERCEPTUAL guard. The bucket gap alone missed the real flashes: a near-black ground cutting to an
  // accent flood scores dark->mid (gap 1) while the frame goes from ~20 to ~150 in display terms. Judge on
  // the display-encoded distance when both grounds resolve, and keep the bucket rule as the fallback.
  const gap = groundGap(dnaGroundY(prev.shot, dna), dnaGroundY(next.shot, dna));
  const harsh = gap === null ? dLum >= 2 : gap >= 0.34;
  const t = (harsh && want !== 'carry') ? 'fade' : want;
  const dir = next.transitionIn?.direction;
  // MOTION GRAMMAR: an UNMARKED (default) seam becomes the DNA's native action on a luminance-safe cut (a themed
  // film's cuts belong to its world — terminal = screen-clear, etc.); explicit marks + the dark↔light fade win.
  if (t === 'fade' && !harsh) { const s = dnaDefaultSeam(dna, W, H); if (s) return s; }
  switch (t) {
    case 'slide': return slide({direction: (dir as any) ?? 'from-right'});
    case 'wipe': return wipe({direction: (dir as any) ?? 'from-bottom'});
    case 'clock': return clockWipe({width: W, height: H});
    case 'dissolve': return dissolve();
    case 'carry': return carry();
    default: return fade();
  }
};

// #camera — a subtle whole-film DRIFT (a slow breathing zoom + float) applied to the WORLD only; the HUD
// (captions + the intro/outro veil) stays OUTSIDE it, immune (huashu's camera-rig discipline). Low amplitude
// over a generous overscan (min scale ~1.025) so a pan can never reveal an edge; deterministic (pure fn of
// frame, sin never Math.random). amp scales with meta.motion_personality; amp 0 disables (reduced-motion).
const TWO_PI = Math.PI * 2;
const cameraTransform = (frame: number, amp: number): string => {
  if (amp <= 0) return 'none';
  const s = 1 + amp * (0.035 + 0.010 * Math.sin((frame / 720) * TWO_PI));     // breathe, ~24s period
  const x = amp * 6 * Math.sin((frame / 930) * TWO_PI + 1.3);                  // float — offset periods so it never repeats
  const y = amp * 4 * Math.sin((frame / 810) * TWO_PI + 0.4);
  return `scale(${s.toFixed(5)}) translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
};

// visible fallback if a storyboard names an unknown shot id (fail loud, never a silent blank)
const Missing: React.FC<{id: string}> = ({id}) => (
  <AbsoluteFill style={{background: '#2a0a0a', alignItems: 'center', justifyContent: 'center',
    color: '#ff8a8a', font: '700 44px/1.4 monospace', textAlign: 'center'}}>unknown shot:<br />{id}</AbsoluteFill>
);

// #brand — the user's REAL logo as a persistent corner BUG, drawn OUTSIDE the camera/shot layer on every scene, so
// a branded remotion film actually carries the mark (the html tier's render-level bug, ported — remotion has no
// separate cover/endcard PAGES, so a corner mark is how the logo appears at all). Top corners only (bottom = the
// caption band). Prefers the dark-ground variant since the bespoke shots are mostly dark. placement:[] opts out.
const BrandMark: React.FC<{brand?: any}> = ({brand}) => {
  const {width, height} = useVideoConfig();
  if (!brand || !brand.logo) return null;
  const placement: string[] = Array.isArray(brand.placement) ? brand.placement : ['cover', 'endcard'];
  if (!placement.length) return null;
  const bug = brand.bug || {};
  const src = brand.logo_dark || brand.logo;
  const h = Math.max(24, (bug.height_frac ?? 0.045) * Math.min(width, height));
  const m = (bug.margin_frac ?? 0.02) * width;
  const side = bug.corner === 'tl' ? {left: m} : {right: m};
  // A plain <img> (NOT remotion's <Img>) for the decorative bug: <Img> uses delayRender() which TIMES OUT + crashes
  // the whole render on a wrong/removed logo path (28s), even with onError. A plain <img> just renders nothing on a
  // 404 (onError hides it) — a persistent DOM element stays loaded across frames after the first paint. validate.py
  // still ERRORs on a missing brand asset pre-render; this is the runtime safety net (the html tier degrades too).
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <img src={staticFile(src)} onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
        style={{position: 'absolute', top: m, height: h, maxWidth: width * 0.35, objectFit: 'contain',
          opacity: bug.opacity ?? 0.55, ...side}} />
    </AbsoluteFill>
  );
};

export const Film: React.FC<{scenes?: SceneSpec[]; camera?: number; reducedMotion?: boolean; theme?: Atmo; captions?: boolean; brand?: any; dna?: DesignDNA | null; template?: string}> =
  ({scenes = WORKBUDDY_SCENES, camera = 0, reducedMotion = false, theme, captions = true, brand, dna, template}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const total = filmDuration(scenes);
  const cam = cameraTransform(frame, reducedMotion ? 0 : Math.max(0, camera));
  const intro = interpolate(frame, [0, 12], [1, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const outro = interpolate(frame, [total - 16, total - 1], [0, 1], {extrapolateLeft: 'clamp'});
  // ONE Design DNA for the whole film (null = un-themed → every shot renders its original hardcoded look).
  const activeDna = coerceDna(dna) ?? dnaFromTemplate(template) ?? null;   // an authored DNA may be partial — normalise it
  const bg = theme?.bg ?? activeDna?.bg ?? '#05060a';

  return (
    <AbsoluteFill style={{backgroundColor: bg}}>
      <DesignDNAContext.Provider value={activeDna}>
      <Atmosphere {...(theme ?? {})} intensity={reducedMotion ? 0.55 : (theme?.intensity ?? 1)} />
      <ReducedMotionContext.Provider value={reducedMotion}>
      {/* GLOBAL TYPE — for a UNIFORM-TYPE DNA (e.g. terminal = all-mono) inject one font-family !important so
          every shot speaks the type with zero per-shot edits (overrides inline family, keeps size/weight; scoped
          to .dna-film so captions keep their own font). A MIXED-type style (editorial serif+sans, etc.) sets no
          uniformType → NO override, and its registers pick fontDisplay vs fontBody per element. Generalizes. */}
      {/* TYPE VARIABLES — the DNA's three faces, published to the shots as CSS custom properties.
          Shots read them as `var(--f-body, <their original list>)`, so with NO DNA the variables are
          unset, the original list applies, and the frame is pixel-identical to before this layer
          existed (scripts/null_dna_pixel_gate.py proves it on real renders). A uniformType DNA's
          `!important` rule below still wins, so terminal is unchanged. */}
      {activeDna ? <style>{`.dna-film { --f-display: ${activeDna.fontDisplay}; --f-body: ${activeDna.fontBody}; --f-mono: ${activeDna.fontMono}; }`}</style> : null}
      {activeDna?.uniformType ? <style>{`.dna-film, .dna-film * { font-family: ${activeDna.fontMono} !important; }`}</style> : null}
      <AbsoluteFill className="dna-film" style={cam === 'none' ? undefined : {transform: cam}}>
      <TransitionSeries>
        {scenes.flatMap((sc, i) => {
          const C = REGISTRY[sc.shot];
          const durF = Math.max(1, Math.round(sc.durF));
          const seq = (
            <TransitionSeries.Sequence key={`s${i}`} durationInFrames={durF}>
              <SceneDurationContext.Provider value={durF}>
                <AbsoluteFill>{C ? <C {...(sc.props ?? {})} /> : <Missing id={sc.shot} />}</AbsoluteFill>
                <TerminalChrome dna={activeDna} path={sc.chrome?.path} status={sc.chrome?.status} root={sc.chrome?.root} W={width} H={height} />
              </SceneDurationContext.Provider>
              {sc.mp3 ? <Audio src={staticFile(sc.mp3)} /> : null}
            </TransitionSeries.Sequence>
          );
          if (i === scenes.length - 1) return [seq];
          return [seq, (
            <TransitionSeries.Transition key={`t${i}`}
              presentation={pickPresentation(sc, scenes[i + 1], width, height, activeDna)}
              timing={linearTiming({durationInFrames: TR})} />
          )];
        })}
      </TransitionSeries>
      </AbsoluteFill>
      </ReducedMotionContext.Provider>
      <AbsoluteFill style={{backgroundColor: bg, opacity: Math.max(intro, outro), pointerEvents: 'none'}} />
      {captions ? <CaptionTrack scenes={scenes} groundBg={theme?.bg ?? activeDna?.bg} dnaColors={activeDna} dnaFontBody={activeDna?.fontBody} /> : null}
      <BrandMark brand={brand} />
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default Film;
