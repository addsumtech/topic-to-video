// FILM · data-driven — sequences any list of bespoke shots into a narrated film. Each SCENE names a `shot`
// (looked up in REGISTRY), its topic `props`, a frame-length `durF`, an optional narration `mp3` (served from
// public/) and a `caption`. Scenes CROSS-DISSOLVE (overlapping ~0.4s to ride the narration breath). Captions
// ride a SINGLE top-level HUD track (a #hud sibling, per huashu's camera-rig discipline) that HARD-CUTS one
// caption at a time inside each scene's sole-visible window — so two captions can never overlap across a
// transition (the old A1 doubling bug) — and picks its ink CONTRAST against the scene's ground luminance.
// render_remotion.py drives this via --props; the WorkBuddy film is just the default. Deterministic.

import React from 'react';
import {AbsoluteFill, Audio, Freeze, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {wipe} from '@remotion/transitions/wipe';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {captionBandBare, CAPTION_SIZE_FRAC, CAPTION_MARGIN_FRAC, CAPTION_LINES,
        CAPTION_LEAD, CAPTION_LEAD_CJK, cjkAdvance, latinAdvance,
        CONTENT_TOP, contentBottom} from './runtime/layout';
import {ObjectIdleContext} from './runtime/objectSlot';
import {SceneDurationContext, ReducedMotionContext, clamp01, SEAM_FRAMES,
        easeOutCubic, setStyleEase} from './runtime/motion';
import {NarrationContext} from './runtime/voice';
import {CueContext, warpFrame} from './runtime/cue';
import {groundLum, dnaGroundLum, dnaGroundY, groundGap, HARSH_GROUND_GAP, lumValue, lumFromY, DNA_GROUND_TOKEN,
        type Lum, type GroundColors} from './runtime/shotLuma';
import {BeatGround, groundAt, captionInk, hexGround, LIGHT_KEY_Y, CAPTION_INK_DARK, CAPTION_INK_LIGHT,
        type SceneGroundDecl} from './runtime/light';
import {Atmosphere, type Atmo} from './runtime/atmosphere';
import {SceneCamera, bedPan, ACTION_SAFE_FRAC, cameraBudget, type CameraMove} from './runtime/depth';
import {phraseExtra} from './runtime/phrase';
import {FocusLayer} from './runtime/focusLead';
import {withCjkDisplay} from './runtime/cjkVoice';
import {WorldBackdrop} from './runtime/world';
import {handoffIn, handoffOut} from './runtime/handoff';
import {BASELINE_UNLOCK, BaselineUnlockContext, unlockCoverScale, useGlide} from './runtime/glide';
import {DesignDNAContext, type DesignDNA, dnaFromTemplate, coerceDna, TerminalChrome, useDNA} from './runtime/dna';
import {StyleContext, resolveStyle, useStyle, type StyleSpec} from './runtime/styleSpec';
import {stepFrame} from './runtime/styleMotion';
import {StyleLayer} from './runtime/style';
import {STYLE_HOOKS_BY_SHOT} from './runtime/styleHooks';
import {REGISTRY} from './registry';
import {STAGES, STAGE_GROUND} from './stage';
import {StageRunContext, type StageBeat} from './runtime/stageRun';
import {BlurFilter, blurOf} from './stage/surface';
import {TextSafeAudit, TypeGlideAudit} from './runtime/textSafe';
import {MediaResAudit} from './runtime/mediaRes';
import {TitleProbe} from './runtime/titleProbe';
import {safeProfile, SafeZoneContext, SafeProfile, registerFrame, captionBottomY, SAFE_CAPTION_SCALE} from './runtime/safeZone';
import {CAPTIONS} from './captions';
import {FilmMotifLayer} from './runtime/motif';
import {FilmFinishLayer} from './runtime/finish';
import {FilmDither} from './runtime/dither';
import {OpticContext, opticState, normalizeOptic, dnaLight, dnaOptics, SeamLeak, type OpticDecl, type OpticSpec} from './runtime/optics';
import {litMediumGround} from './runtime/material';
import {CarryContext} from './runtime/carry';
import {container, grow, throughWindow, punch, cut, SeamCopyContext} from './seams';
import {splitCaption, fitCaption, advanceFor, cjkCaptionLines, captionBox, CAP_PAD_X, litThrough, breaksAsCJK} from './captionBreak';

// The scene EDL. `bgLum` is the first of the shot-director-emitted continuity fields (an explicit ground-
// luminance override; falls back to the measured shotLuma map). Future phases grow this schema (accent,
// camera{}, carry{}, transitionIn{}, audioCues[]) — all OPTIONAL + remotion-only, so the html tier is untouched.
export type SceneSpec = SceneGroundDecl & {shot: string; props?: Record<string, unknown>; durF: number; mp3?: string;
  // `bgLum` DESCRIBES the ground this beat paints (a hint for the caption ink and the seam guard); the
  // `ground` / `key` fields it now sits beside COMMAND one (they repaint the frame — runtime/light.tsx).
  // Both are kept and the Film refuses a beat that declares two disagreeing answers, because a hint that
  // silently becomes a command is how `bgLum:'light'` came to mean "a still-dark frame".
  caption?: string; bgLum?: Lum; stageGround?: string;
  // THE VOICE'S OWN WORD TIMES, as character ranges into `caption` (scripts/cues.word_spans). Ranges rather
  // than word indices because this tier re-chunks the caption to fit its band, and an index into "word 3 of
  // chunk 2" means something different after every re-wrap while an offset into the string does not.
  capWords?: {t: number; a: number; b: number}[];
  // PHRASE STEPS (scripts/phrase_steps.py, runtime/phrase.ts): seconds on the beat's clock at which an AUTHORED push or
  // pull takes its next step, on the voice's next clause. Absent: the beat's camera is what it always was.
  phrase?: number[];
  // THE PLACE the beat happens in (runtime/world.tsx), named from its subject; drawn when the style asks for places.
  world?: string;
  // THE LEAD (scripts/focus_plan.py, runtime/focusLead.tsx): which listed item leads while the voice talks about it.
  focus?: {t: number; key: string | null}[];
  focusItems?: Record<string, string>;
  // TERMINAL CHROME per scene (remotion + DNA only): a command-path + status readout the Film frames every beat
  // with (see runtime/dna.tsx TerminalChrome). Optional; inert unless the active DNA speaks 'breadcrumb'.
  chrome?: {path?: string; status?: string; root?: string};
  // A MARKED seam (chapter break): the transition INTO this scene from the previous one. Optional +
  // remotion-only; unset = the luminance-safe default (a gentle cross-fade). A kinetic type is honored only
  // on a same/near-luminance seam — across a dark↔light gap it's suppressed back to fade (see pickPresentation).
  transitionIn?: {type: 'fade' | 'slide' | 'push' | 'lift' | 'wipe' | 'clock' | 'dissolve' | 'fadethrough'
    | 'drift' | 'blur' | 'carry' | 'focus' | 'through-dark' | 'portal' | 'return'
    | 'container' | 'grow' | 'through-window' | 'punch' | 'cut'; direction?: string;
    /** `return` only: the pan across the film's board, as fractions of the frame's LONG side. Computed by
     *  `scripts/film_board.py`, which is the one place that knows where two beats sit. */
    dx?: number; dy?: number;
    /** `container` / `grow` / `through-window`: the anchor the seam takes hold of (runtime/carry `data-carry`). One
     *  id names the same anchor in both beats; `{from, to}` names the leaving beat's and the arriving beat's. */
    carry?: string | {from: string; to: string};
    /** `container` by DECLARED rects instead of anchors — a board's `match_cut` (render_remotion maps it): [cx, cy, w,
     *  h] as fractions of the frame, the leaving beat's region and the arriving beat's; `shape` sets the corner. */
    from?: [number, number, number, number]; to?: [number, number, number, number];
    shape?: 'box' | 'bar' | 'line' | 'dot'};
  // A MOTIVATED camera move for THIS beat: `push` (look closer at what is here), `pull` (here is the whole
  // of it), `hold` (most beats). Optional; absent = hold. This is not the film-wide ambient drift below —
  // that one had no relationship to anything being said, which is precisely why it read as a wobble.
  camera?: {move?: CameraMove; amount?: number; pan?: [number, number];
    /** the move runs INTO the cut instead of coming to rest, and the next beat — a continuation, with no camera of
     *  its own — starts with this move's velocity and lets it decay (runtime/depth `handoff`) */
    handoff?: boolean};
  // THE BEAT'S CLOCK, WARPED ONTO ITS VOICE. Knots [[film frame, register frame], ...] on the beat's own clock,
  // strictly increasing in both: the register is handed `warpFrame(frame, warp)` instead of `frame`, so an
  // entrance it times as a fixed fraction of the beat lands on the word that names it — with no register file
  // touched. Derived by scripts/sync_qa.py from the type census of the un-warped film (render_remotion does it
  // before a render); absent = the register's own clock, and the beat renders exactly as it did before.
  warp?: [number, number][];
  // PER-ELEMENT CUES: {prop path: film second by which that item should read} — what the warp cannot do, since it
  // cannot reorder (runtime/cue.ts). Set by scripts/sync_qa.py `attach_cues` only for a register that imports
  // runtime/cue; read through CueContext, so a register that ignores it renders exactly as before.
  cues?: Record<string, number>;
  // THE HELD OBJECT'S IDLE CLOCK (runtime/objectSlot): on unless the storyboard sets `"object_idle": false` on
  // this beat — for a beat where a held object's own cycle would say something the narration does not.
  objectIdle?: boolean;
  // THE BEAT'S OPTIC (runtime/optics.tsx): at most one, anchored to a light the register draws — `bloom` | `halation` |
  // `sweep` | `aberration` (the register's own `OPTICS` export says which it can anchor), or `leak`, which the Film
  // draws over the seam INTO this beat. Absent = none (or the DNA's `optics: 'auto'`); the frame is then exactly what it
  // was before optics existed.
  optic?: OpticDecl;
  // A CONTINUOUS STAGE RUN (runtime/stageRun.tsx): consecutive beats naming the same run are ONE Sequence with no seam
  // between them, drawn by ONE stage component (remotion/src/stage/) that carries its actors from beat to beat.
  stage?: {run: string}};

// warpFrame lives in runtime/cue (a register's per-element cues convert through the same map); re-exported here.
export {warpFrame};

/** Refuses a cue that is not a second inside the beat — a NaN would silently pin nothing. */
const checkCues = (cues: Record<string, number>, i: number, shot: string) => {
  for (const [k, v] of Object.entries(cues)) {
    if (typeof v !== 'number' || !Number.isFinite(v) || v < 0) {
      throw new Error(`scene ${i} (${shot}) has cue ${JSON.stringify(k)} = ${JSON.stringify(v)} — a cue is the film ` +
        'second (inside the beat) at which that item should read; re-derive it (scripts/sync_qa.py attach_cues)');
    }
  }
};

/** Refuses a warp that is not a monotone map — a register run backwards or frozen is never what was meant. */
const checkWarp = (warp: [number, number][], i: number, shot: string) => {
  for (let k = 1; k < warp.length; k++) {
    if (!(warp[k][0] > warp[k - 1][0]) || !(warp[k][1] > warp[k - 1][1])) {
      throw new Error(`scene ${i} (${shot}) has a warp whose knots do not increase in both clocks at knot ${k} ` +
        `(${JSON.stringify(warp[k - 1])} -> ${JSON.stringify(warp[k])}) — re-derive it (scripts/sync_qa.py)`);
    }
  }
};

// Only the REGISTER is warped: the beat's camera, its chrome, its ground and its voice stay on the film's clock,
// which is why this wraps the register alone. With no warp it adds nothing to the tree's DOM, so an unwarped
// beat is pixel-identical to a film rendered before warps existed.
// A STEPPED STYLE (meta.style.motion.stepping) holds this clock on every 2nd or 3rd frame, AFTER the warp: the drawing
// moves on twos, the way drawn animation is drawn, while the caption, the voice, the camera and the seams — all outside
// this clock — stay on ones. Reduced motion never steps. With no warp and no stepping it still adds nothing to the tree.
const BeatClock: React.FC<{warp?: [number, number][]; children: React.ReactNode}> = ({warp, children}) => {
  const frame = useCurrentFrame();
  const style = useStyle();
  const reduced = React.useContext(ReducedMotionContext);
  const step = reduced || !style ? 1 : Number((style.motion as {stepping?: number}).stepping) || 1;
  const warped = !warp || warp.length < 2 ? null : warpFrame(frame, warp);
  if (warped === null && step === 1) return <>{children}</>;
  return <Freeze frame={stepFrame(warped ?? frame, step)}>{children}</Freeze>;
};

const TR = SEAM_FRAMES; // cross-dissolve length (frames) — rides the ~0.42s narration breath so speech barely
// overlaps. Shared with runtime/motion's useT, which holds each shot STILL for exactly these frames at both
// edges so a dissolve never runs over a moving shot.
/** The stage run a scene is on, or null. */
export const runOf = (sc?: SceneSpec): string | null =>
  sc && sc.stage && typeof sc.stage.run === 'string' && sc.stage.run.trim() ? sc.stage.run : null;
/** Scene i continues the stage run of scene i-1: the boundary between them is NOT a cut, so there is no seam. */
export const joinedAt = (scenes: SceneSpec[], i: number) =>
  i > 0 && runOf(scenes[i]) !== null && runOf(scenes[i]) === runOf(scenes[i - 1]);
/** The luminance of the ground a STAGE beat paints (stage/index.ts STAGE_GROUND), or null for any other beat — a stage
 *  has no measured row, so asking the register table about it answered "dark" for a light studio. */
/** The scaled register frame's edges, faded over the register's own action-safe border (both masks intersected): type
 *  is kept inside that border (frame_safe_qa, runtime/depth edge budget), so the fade can never thin a letter. It was
 *  7% across and 5% down — wider than the border, over type a register may set 3.5% from its edge. */
const SAFE_EDGE = `${(ACTION_SAFE_FRAC * 100).toFixed(1)}%`, SAFE_EDGE_FAR = `${(100 - ACTION_SAFE_FRAC * 100).toFixed(1)}%`;
const SAFE_FRAME_MASK = `linear-gradient(90deg, transparent 0%, #000 ${SAFE_EDGE}, #000 ${SAFE_EDGE_FAR}, transparent 100%), ` +
  `linear-gradient(180deg, transparent 0%, #000 ${SAFE_EDGE}, #000 ${SAFE_EDGE_FAR}, transparent 100%)`;
// THE MARGIN IS THE BEAT ITSELF. A platform-safe film draws every register in a frame scaled by k (0.8) with feathered
// edges, so on 9:16 every beat was a panel floating on the film's ground — "every beat becomes a panel on black", the
// first of a 9:16 launch benchmark's findings (2026-10-24), and the DNA's own gradient and vignette drew the panel's
// edge as a visible seam. The margin is now the beat's own ground carried to the canvas edge (below: never its content).
//
// IT IS NOT A SECOND BEAT TO ANY INSTRUMENT. `data-echo="margin"` + `aria-hidden`: every text gate already skips an
// echo (runtime/textSafe.tsx `isEcho` — safety, collisions, the glide and sync censuses; runtime/titleProbe.tsx), the
// seams' anchor lookups skip a margin echo (seams.tsx `anchorIn`), it mounts no optic (no BeatOptic) and plays no
// sound (SeamCopyContext: Film's beat voice reads it; every film video in runtime/screen.tsx is already muted). Inside a
// container seam's copy of the beat it is not drawn at all. Only a platform-safe film has one, so every other film's
// tree — and every pixel — is what it was (`safeEcho: false` keeps the ground token and drops the register's copy).
//
// THE UNLOCK GOES INSIDE THE FRAME'S MASK. Every motion above a beat — its camera, a hand-off, a seam's presentation,
// the whole-film drift — carries the baseline unlock (runtime/glide.ts), and on a 16:9 film it reaches the glyphs. On a
// platform-safe film the register is drawn inside a MASKED frame, and once anything in the register is composited (a
// Stage3D surface, a 3D card) Chrome draws that masked frame as a layer of its own, rasterised under the SCALE of the
// matrix above it only: the skew is applied to the finished layer and never reaches the type, which snaps again.
// Measured on CameraTypeProbe at 9:16 under a push: masked frame + a composited sibling, y residual 0.229-0.263px RMS
// with 0.89px jumps (the snapped signature); the same with no composited sibling, or with no mask, 0.011px; with the
// unlock written inside the mask, 0.025px. A validation film (擒纵, 9:16) shipped it: under a camera hand-off its beat-2
// kicker drifted smoothly and jumped back 0.92px at frames 244->245 (and 0.63px at 212->213) while the camera curve
// itself was smooth. So inside the mask the register carries its own unlock, sized for the frame's scale k (Skia
// judges the skew times the scale above it — `unlockFor`), on EVERY frame: its span is "whatever above it can move",
// which on a film with seams and cameras is the whole beat, and switching it on with each motion would itself pop
// (glide.ts). The skew's tilt (0.53px at the frame's far corners) sits under the mask's transparent feather.
// BaselineUnlockContext false (identity proofs) and reduced motion draw the frame exactly as before.
const FrameUnlock: React.FC<{k: number; on: boolean; children: React.ReactNode}> = ({k, on, children}) => {
  const glide = useGlide();
  const tf = glide(undefined, on, k);
  return tf ? <AbsoluteFill style={{transform: tf}}>{children}</AbsoluteFill> : <>{children}</>;
};

// THE MARGIN IS THE BEAT'S GROUND — NEVER A COPY OF ITS CONTENT. Two echoes were tried and both drew a second, blurred
// copy of the beat in the margin. The first scaled the register 1.36x about the frame's centre (1.7x the frame): the
// balance wheel as gold arcs in the top corners, the plate caption as a blob. The second drew it unscaled about the
// frame's fixed point with its type made transparent: a ghost iPhone with its home bar under the caption on the phone
// beat, a ghost of the gear-train slab beside its frame (2026-10-31, looked; frame_safe_qa margin_structure reads the
// phone 24 and the slab 39-56 where a plain ground reads <= 2.3). A viewer reads either as a duplicate object. And off,
// the margin was the film's FLAT root ground round a register's radial one: a lit panel.
//
// So the margin is ground only, in two layers:
//   · the beat's measured ground token (shotLuma DNA_GROUND_TOKEN, resolved in this beat's DNA: `bg` paints the DNA's
//     bgGrad when it has one, as the registers that read `bg` do) — always, and the whole margin when the echo is off;
//   · over it, the register's OWN ROOT GROUND: the register rendered once more, unscaled, with every element under its
//     root hidden — so the gradient, literal or prop colour it actually paints runs on to the canvas edge, evaluated on
//     the canvas, and nothing it draws on that ground can appear. A register whose root paints nothing leaves the token.
// The frame's feathered edge then dissolves the scaled ground into the same ground at full size: the residual is the
// ground's own slope across the gap (frame_safe_qa margin_seam).
//
// `meta.safe_echo: false` (Film `safeEcho`) keeps the token only and skips the second rendering of every register.
const ECHO_GROUND_ONLY = '[data-echo="margin"]>div>* *{visibility:hidden!important}' +
  '[data-echo="margin"]>div>*{color:transparent!important;-webkit-text-fill-color:transparent!important}';

/** The paint of a beat's measured ground token in its DNA (DNA_GROUND_TOKEN): a literal colour as it is; `bg` as the
 *  DNA's bgGrad when it has one (the registers that read `bg` paint `bgGrad ?? bg`); a two-token flood as a gradient of
 *  the two; null when nothing resolves (no DNA, no row) — the film's own root ground then shows, as before. */
const groundPaint = (shot: string, dna: DesignDNA | null): string | null => {
  const tok = DNA_GROUND_TOKEN[shot];
  if (typeof tok === 'string' && tok.charCodeAt(0) === 35) return tok;
  if (!dna) return null;
  const d = dna as unknown as Record<string, string | undefined>;
  const names = Array.isArray(tok) ? tok : [tok ?? 'bg'];
  if (names.length === 1 && names[0] === 'bg') return d.bgGrad ?? d.bg ?? null;
  const cols = names.map((n) => d[n]).filter((c): c is string => typeof c === 'string');
  if (!cols.length) return d.bgGrad ?? d.bg ?? null;
  return cols.length === 1 ? cols[0] : `linear-gradient(180deg, ${cols.join(', ')})`;
};

const SafeEcho: React.FC<{shot: string; rootGround: boolean; children: React.ReactNode}> = ({
  shot, rootGround, children}) => {
  const dna = useDNA();
  if (React.useContext(SeamCopyContext)) return null;
  const paint = groundPaint(shot, dna);
  return (
    <AbsoluteFill aria-hidden data-echo="margin" style={{overflow: 'hidden', pointerEvents: 'none',
      ...(paint ? {background: paint} : {})}}>
      {rootGround ? <style>{ECHO_GROUND_ONLY}</style> : null}
      {rootGround ? (
        <AbsoluteFill>
          <SeamCopyContext.Provider value={true}>{children}</SeamCopyContext.Provider>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

// A REGISTER WHOSE GROUND IS A PROP: its one measured row (shotLuma) describes its DEFAULT only. LitMedium paints its
// medium's colour, so a water beat read as the default paper and its caption was inked dark on dark water.
const PROP_GROUND: Record<string, (props: Record<string, unknown> | undefined, dna?: never) => string | null> = {
  LitMedium: litMediumGround as never,
};
const stageGroundY = (sc: SceneSpec, dna?: unknown): number | null => {
  // `stageGround` is the backdrop this beat of the run holds (render_remotion works it out from the run's beats)
  const tok = runOf(sc) ? (sc.stageGround ?? STAGE_GROUND[sc.shot]) : undefined;
  const c = tok && dna ? (dna as Record<string, unknown>)[tok] : undefined;
  if (typeof c === 'string') return lumValue(c);
  const own = !runOf(sc) && PROP_GROUND[sc.shot] ? PROP_GROUND[sc.shot](sc.props, dna as never) : null;
  return own ? lumValue(own) : null;
};
/** ONE definition of where each beat starts on the film's timeline: the next beat mounts TR frames before this one
 *  ends at a cut (the seam overlaps them), and on the frame after it ends inside a stage run. scripts/stage_runs.py
 *  and scripts/remotion_segments.py mirror it, and a test holds them to it. */
export const sceneStarts = (scenes: SceneSpec[]) => {
  let acc = 0;
  return scenes.map((sc, i) => {
    const s = acc;
    acc += Math.max(1, Math.round(sc.durF)) - (i + 1 < scenes.length && !joinedAt(scenes, i + 1) ? TR : 0);
    return s;
  });
};
export const filmDuration = (scenes: SceneSpec[]) => {
  const cuts = scenes.reduce((n, _s, i) => n + (i > 0 && !joinedAt(scenes, i) ? 1 : 0), 0);
  return Math.max(1, scenes.reduce((a, s) => a + Math.max(1, Math.round(s.durF)), 0) - cuts * TR);
};

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
  12: {type: 'carry'},                            // ChartLive → HandDrawn: the figure is carried into the human takeaway (crosses dark→light). No trend line: the 68× is one sourced number, and ChartLive draws a line only from a `series` it is given
};
// The default preview is SILENT (no demo audio ships with the skill) — a real film's per-scene narration is
// supplied by render_remotion.py from the out_dir (`sc.mp3`), served via --public-dir.
export const WORKBUDDY_SCENES: SceneSpec[] = WB_SHOTS.map((shot, i) => ({
  shot, props: WB_PROPS[i] ?? {}, durF: Math.round(WB_SEC[i] * 30), caption: CAPTIONS[i], transitionIn: WB_TRANS[i],
}));

// The caption's CHUNKS (splitCaption, fitCaption) and a CJK chunk's LINES live in captionBreak.ts, which the gate
// scripts/caption_breaks_qa.py runs in node — one definition for what is burned and what is checked.

const CAP_PAD = 4;   // clean-gap frames inside each scene's sole-visible window → guarantees exit-before-enter
const CAP_FADE = 3;  // tiny in/out ramp WITHIN the window (never across a transition, so captions never double)
// FRAME-CRAFT FLOOR. An earlier version scaled the WHOLE world to 0.86 to pull edge content inside action-safe —
// but that shrank each shot's OWN full-bleed background too, so a ~14% margin of the near-black atmosphere showed
// as BLACK BORDERS on the sides + bottom (the shot background must reach the frame edge). So the world now renders
// FULL-BLEED (no scale, no lift); edge-safety is a per-SHOT contract that frame_safe_qa verifies deterministically,
// and the bottom CAPTION_BAND is reserved by the SHOTS keeping content out of it — not by shrinking the picture.
// The band is NOT a number here any more. It lived as a literal 150 in this file, another literal in
// runtime/layout.ts, 0.135 in frame_safe_qa.py and a third copy in shot_still_qa.py — four places that had to
// agree and nothing that made them. It is derived from the caption's own type size in runtime/layout.ts now,
// and a test holds the Python copies to it.

// One global caption HUD. It shows AT MOST ONE caption — the one belonging to the scene whose sole-visible
// window (between its two transitions) contains this frame — hard-cut, contrast-picked against that scene's
// ground luminance. Because the windows are disjoint, two captions can never coexist across a dissolve.
const CaptionTrack: React.FC<{scenes: SceneSpec[]; groundBg?: string; dna?: DesignDNA | null;
  dnaFontBody?: string | null;
  // a UNIFORM-TYPE DNA sets every element to one face (terminal = all-mono), which changes the caption's
  // advance and so the number of lines it wraps to
  dnaUniform?: boolean;
  // the caption HUD is a sibling of the ReducedMotionContext provider (it must stay top-level so two
  // captions cannot coexist across a dissolve), so the flag is handed to it rather than read from context
  reduced?: boolean;
  // a 9:16 film for the platforms (runtime/safeZone): the caption sits above the platform's own UI, a size larger
  safe?: SafeProfile | null}> = ({scenes, groundBg, dna, dnaFontBody, dnaUniform, reduced, safe}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  // The caption used to be a flat 44px whatever the frame was: at 9:16 — where the frame is only 1080 wide —
  // the same 44px is proportionally half again as large. It is sized off the NARROW dimension now.
  //
  // It was then set a notch SMALLER to answer "subtitle is too close to the content", which worked (a shorter
  // bottom-anchored block starts lower) but bought the gap with legibility: measured on a delivered frame the
  // caption was 37px of ink, 3.4% of frame height, against a 5.2% floor for a 1080p film watched in a
  // phone-sized window. The gap is paid for out of the reserved BAND now instead of out of the type.
  // on a platform-safe film a size larger: vertical-video guidance starts captions around 55-65px at 1080 wide
  // (references/craft-research.md §2), and the caption no longer competes with the bottom of the picture
  const {capSize, capMeasure, capTextW} = captionBox(width, height, safe);
  const capMargin = Math.round(Math.min(width, height) * CAPTION_MARGIN_FRAC);
  const starts = sceneStarts(scenes);
  let active = -1, ws = 0, we = 0;
  for (let i = 0; i < scenes.length; i++) {
    const dur = Math.max(1, Math.round(scenes[i].durF));
    // HAND OFF AT THE MIDDLE OF THE DISSOLVE, not outside it. Clearing the WHOLE transition at both ends
    // plus CAP_PAD suppressed the caption for ~0.53s after every cut while the speech had already begun,
    // and dropped it ~0.2s before the line ended — measured at ~0.7s of uncaptioned speech per beat, about
    // 25s across a 37-beat film. Scene i+1 starts TR frames before scene i ends, so switching at the
    // dissolve's midpoint keeps the windows DISJOINT (the original reason for the guard: two captions must
    // never coexist) while making them GAPLESS — caption i ends on exactly the frame caption i+1 begins.
    const half = Math.floor(TR / 2);
    // inside a stage run there is no dissolve: a caption ends on the frame before the next beat starts
    const a = starts[i] + (i > 0 ? (joinedAt(scenes, i) ? 0 : half) : 14);
    const b = starts[i] + dur - (i < scenes.length - 1 ? (joinedAt(scenes, i + 1) ? 1 : TR - half) : 16);
    if (frame >= a && frame <= b) { active = i; ws = a; we = b; break; }
  }
  const sc = active >= 0 ? scenes[active] : undefined;
  if (!sc || !sc.caption) return null;
  // the measure the caption actually wraps in — must match the <div> below, or the fit is estimated against
  // a width the browser never used. The block is `capMeasure` wide border to border and its text wraps
  // INSIDE its side padding, so the lines are `capMeasure - 2 * CAP_PAD_X` long: fitted against the whole
  // block, a 68-glyph Chinese sentence passed as two lines of 35 and the browser set it in three lines of 32,
  // the third climbing out of the band onto the shot's own words.
  // on a platform-safe film the LINES end short of the button column (runtime/safeZone `right`), centred — a full
  // line of a 1080-wide caption ran to x 960, under the buttons from 929; 8 px of air
  const merged = fitCaption(splitCaption(sc.caption), capSize, capTextW, CAPTION_LINES, dnaFontBody, dnaUniform);
  // WEIGHT each chunk's on-screen time by its LENGTH (not equal slices) — else a 3-word chunk lingers while a
  // 20-word chunk races the voice. Advance idx by cumulative char-fraction of the caption.
  const lens = merged.map((c) => Math.max(1, c.length));
  const total = lens.reduce((a, b) => a + b, 0);
  const local = clamp01((frame - ws) / Math.max(1, we - ws));
  let idx = merged.length - 1, cum = 0;
  for (let i = 0; i < merged.length; i++) { cum += lens[i] / total; if (local <= cum) { idx = i; break; } }

  // WHERE EACH CHUNK SITS IN THE CAPTION. Every chunk is a trimmed slice of `caption` in order, so a moving
  // cursor locates them exactly — and that is what lets a word time, which is an offset into the whole
  // caption, be found inside whatever this tier happened to wrap the caption into.
  const at: {a: number; b: number}[] = [];
  { let cur = 0;
    for (const c of merged) {
      const f = sc.caption.indexOf(c, cur);
      const a = f >= 0 ? f : cur;
      at.push({a, b: a + c.length});
      cur = a + c.length;
    } }

  // THE CAPTION FOLLOWS THE VOICE WHEN THE VOICE SAID WHERE IT WAS. Without word times the chunk index comes
  // from the CHARACTER PROPORTION of the beat elapsed — a guess that a short clause and a long one are
  // spoken at the same rate, which they are not, so the caption drifts off the speech inside a single beat.
  // `tts.py` has written these times since edge-tts was adopted and only the html renderer ever read them.
  const spoken = sc.capWords ?? [];
  let lit = -1;                                  // char offset the voice has reached, -1 = not yet known
  if (spoken.length) {
    const t = (frame - starts[active]) / fps;
    let k = -1;
    for (let i = 0; i < spoken.length; i++) if (spoken[i].t <= t) k = i; else break;
    if (k >= 0) {
      lit = litThrough(sc.caption, spoken[k].b);   // a closing mark is said with its word (captionBreak.ts)
      // the chunk holding the word being spoken — the LAST one that starts at or before it, so a word in
      // the gap between two chunks (punctuation the wrap ate) stays on the chunk it was spoken in
      for (let i = 0; i < at.length; i++) if (at[i].a <= spoken[k].a) idx = i;
    } else {
      idx = 0;                                   // the voice has not reached the first word yet
    }
  }
  const op = Math.min(clamp01((frame - ws) / CAP_FADE), clamp01((we - frame) / CAP_FADE));
  // THE INK FOLLOWS THE GROUND THAT IS ACTUALLY ON THE FRAME, INCLUDING WITHIN A RAMP.
  // The DNA repaints most shots' grounds, so classify THIS frame's real ground (dnaGroundLum) — reading the
  // measured pre-DNA constant here is what put dark ink on a themed dark ground. A beat may now also re-ground
  // ITSELF, and may ramp its exposure across the dark/light boundary mid-shot, so the pick is re-resolved every
  // frame from the same pure function the beat's own provider uses. This HUD is a top-level sibling by
  // construction (that is what stops two captions coexisting across a dissolve), so it cannot read the beat's
  // context and has to ask the question rather than be told the answer — one definition, two callers.
  const beatG = groundAt(dna ?? null, sc, frame - starts[active], Math.max(1, Math.round(sc.durF)), sc.shot, reduced);
  // Which token this shot grounds on is MEASURED (DNA_GROUND_TOKEN), so an accent-flooded register is judged
  // on its flood and not on a `bg` it never paints; `g.y` is the fallback when that token is a gradient.
  // AND THE NUMBER IS ASKED FOR ON EVERY BEAT, not only on a re-grounded one. `captionInk` exists because
  // the three-bucket class picks the WRONG ink on any ground between Y=0.19 (where the two burned inks
  // cross over) and Y=0.5 (where the bucket's boundary sits) — its own docstring says so. But it was only
  // reached when a beat DECLARED a ground, and almost no beat does; every other frame fell through to the
  // bucket, which is the rule that was supposed to have been replaced. `dnaGroundY` resolves the film's own
  // DNA for 158 of the 160 registers with no declaration at all, so the measured path is the normal one now
  // and the bucket is the last resort it was meant to be. Measured on `KineticManifesto` under `product`
  // (its accent->accent2 flood resolves to Y=0.267): the bucket said `mid`, drew WHITE at 3.3:1, where the
  // dark ink measures 5.9:1 on the same pixels.
  const stY = stageGroundY(sc, dna);
  const beatY = stY ?? (beatG ? (dnaGroundY(sc.shot, beatG) ?? beatG.y) : dnaGroundY(sc.shot, dna));
  const lum = stY !== null ? lumFromY(stY) : dnaGroundLum(sc.shot, sc.bgLum, dna);
  const ink = beatY === null ? (lum === 'light' ? CAPTION_INK_DARK : CAPTION_INK_LIGHT) : captionInk(beatY);
  // The subtitle sits DIRECTLY on the frame's own background — there is NO scrim/bar rectangle behind it.
  // The shots reserve the bottom CAPTION_BAND (content never reaches it), so the caption's ground is the
  // frame's own clean atmosphere; the ink is contrast-picked (dark on light / white on dark). The only
  // separation is a SUBTLE text-shadow in the frame's OWN ground colour (never a white/black halo — the html
  // `overlay` mode had exactly that white-halo bug), just for anti-alias crispness where the ground varies.
  // ONE DEFINITION OF "A HEX GROUND" (light.tsx `hexGround`), because there were two and they disagreed:
  // this line tested six digits while the ground vocabulary accepted three-to-eight, so a beat grounded
  // `#fff` painted a white frame and then shadowed its caption in the FILM's near-black — measured at +77%
  // mid-grey fringe pixels against the identical `#ffffff` beat. It also canonicalises, which is what makes
  // the alpha concatenation below safe rather than lucky.
  const gbSrc = beatG ? beatG.bg : groundBg;
  const gb = hexGround(gbSrc) ?? (lum === 'light' ? '#f4f1ea' : '#05060a');
  const shadow = `0 1px 2px ${gb}e6, 0 0 1px ${gb}`;
  // CJK LINE-HEIGHT + TRACKING. 1.26 with -0.01em tracking is a Latin setting; Han glyphs fill a full
  // em-box, so screen-typesetting guidance for CJK puts line-height at >=1.7x (W3C clreq / Typotheque),
  // and NEGATIVE tracking on Han is wrong — it pulls square glyphs into each other. Decide per caption
  // from the text itself rather than from meta.language, so a mixed deck gets it right line by line.
  const capText = merged[idx] ?? '';
  const isCJK = breaksAsCJK(capText);   // captionBreak's one rule: the gate checks the lines this draws
  const capLead = isCJK ? CAPTION_LEAD_CJK : CAPTION_LEAD;
  const capTrack = isCJK ? '0' : '-0.01em';
  // THE CAPTION FITS THE BAND IT WAS GIVEN. The band is a static reserve every shot lays out against, and it
  // is sized on the LATIN leading — a shot cannot know what language will be spoken over it. CJK sets at 1.7
  // leading, so the identical two-line caption is 231px against a 227px reserve, and in portrait 326 against
  // 298: the subtitle climbs into the picture on every CJK film. Growing the band for the worst case would
  // take that space from every Latin film instead, so the CAPTION yields — its size is capped at whatever
  // fits, which is a guarantee rather than an estimate and holds for any language, length and aspect. In the
  // ordinary Latin two-line case the cap is well above the ideal size and nothing changes.
  // on a platform-safe film the band is the register frame's own band, scaled with it (runtime/safeZone)
  const capBand = safe ? Math.round(safe.k * captionBandBare(width, height)) : captionBandBare(width, height);   // the caption's own strip
  const capBottom = safe ? Math.round(height - captionBottomY(height, safe, capMargin)) : capMargin;
  const perLine = Math.max(8, Math.floor(capTextW / (capSize * advanceFor(capText, dnaFontBody, dnaUniform))));
  // A CJK CAPTION IS DRAWN IN THE LINES captionBreak DECIDES — at word boundaries, never in front of closing
  // punctuation, balanced — one block per line. The browser broke it between any two characters: 「交回成 / 片」.
  const cjkLines = isCJK ? cjkCaptionLines(capText, capSize, capTextW, dnaFontBody, dnaUniform) : null;
  const capLines = cjkLines ? Math.max(1, cjkLines.length) : Math.max(1, Math.ceil(capText.length / perLine));
  const fitSize = Math.max(12, Math.min(capSize, Math.floor((capBand - capMargin) / (capLead * capLines))));
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'relative', maxWidth: capMeasure, boxSizing: 'border-box', margin: `0 auto ${capBottom}px`,
        padding: `0 ${CAP_PAD_X}px`, textAlign: 'center',
        // WEIGHT 600, NOT 700. The caption is already in the DNA's body face, but at 700 it was the
        // heaviest thing on screen — heavier than the display headlines it sits under — so the frame's own
        // hierarchy read second to its subtitle. Its legibility floor is about SIZE (>=5% of frame height,
        // unchanged at 56px) and contrast (unchanged), not weight; 600 keeps both and stops the caption
        // out-shouting the picture it is describing.
        color: ink, font: `600 ${fitSize}px/${capLead} ${dnaFontBody ?? 'Inter, "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif'}`,
        // A single unbreakable token — a URL, a long compound, a hash — has no space to wrap at, so it ran
        // off BOTH frame edges. The off-frame gate cannot see it either: it excludes the caption band by
        // construction, which is the only place the caption is. Breaking anywhere is the lesser evil; a
        // guillotined word is at least still on the frame.
        overflowWrap: 'anywhere', wordBreak: 'break-word',
        letterSpacing: capTrack, textShadow: shadow}}>
        {/* WHAT HAS BEEN SAID IS DARKER THAN WHAT HAS NOT. The treatment is opacity on the caption's OWN
            ink rather than a second colour, which is the one version that cannot fail a contrast check on
            an unknown ground: the lit half is exactly the ink the pick above chose, and the half still to
            come is the same ink held back. A coloured highlight is offered on top of that, and only when
            the DNA's accent is actually readable on this frame's ground — never instead of it. */}
        {cjkLines && cjkLines.length ? (() => {
          // one block per decided line; the spoken/unspoken split is the same offset, found inside each line. A line
          // the advance estimate got too wide is the one case left to the browser: `keep-all` holds its words
          // together and only a line with no other way to fit breaks anywhere (the block's overflow-wrap)
          const cut = lit < 0 ? capText.length : Math.max(0, Math.min(capText.length, lit - at[idx].a));
          let cur = 0;
          return cjkLines.map((ln, li) => {
            const f = capText.indexOf(ln, cur);
            const a = f >= 0 ? f : cur;
            cur = a + ln.length;
            const c = Math.max(0, Math.min(ln.length, cut - a));
            return (
              <div key={li} style={{wordBreak: 'keep-all', lineBreak: 'strict'} as React.CSSProperties}>
                <span>{ln.slice(0, c)}</span>
                {c < ln.length ? <span style={{opacity: lit < 0 ? 1 : 0.42}}>{ln.slice(c)}</span> : null}
              </div>
            );
          });
        })() : lit < 0 ? capText : (() => {
          const cut = Math.max(0, Math.min(capText.length, lit - at[idx].a));
          return (<>
            <span>{capText.slice(0, cut)}</span>
            <span style={{opacity: 0.42}}>{capText.slice(cut)}</span>
          </>);
        })()}
      </div>
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
  // The collapse takes BOTH scenes to opacity 0 at the midpoint, so for a few frames the seam shows
  // whatever sits behind the TransitionSeries. That must be this film's own ground, painted here, and
  // never simply "whatever is behind" — which is how a cream film came to flash near-black at its
  // closing cut. Only the ENTERING half paints it, so the two halves cannot double-darken.
  const ground = (passedProps && passedProps.ground) || undefined;
  const isEnter = presentationDirection === 'entering';
  const ease = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const, easing: Easing.inOut(Easing.cubic)};
  const scaleY = isEnter ? interpolate(p, [0.5, 1], [0.006, 1], ease) : interpolate(p, [0, 0.5], [1, 0.006], ease);
  const clampBoth = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const op = isEnter ? interpolate(p, [0.46, 0.56], [0, 1], clampBoth) : interpolate(p, [0.44, 0.54], [1, 0], clampBoth);
  const lineOp = interpolate(p, [0.15, 0.5, 0.85], [0, 1, 0], clampBoth);
  const glide = useGlide();
  return (
    <>
      {ground && isEnter ? <AbsoluteFill style={{backgroundColor: ground}} /> : null}
      <AbsoluteFill style={{transform: glide(`scaleY(${scaleY})`, true), transformOrigin: 'center', opacity: op}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 2, marginTop: -1,
          background: line, opacity: lineOp, boxShadow: `0 0 18px 3px ${line}`}} />
      </AbsoluteFill>
    </>
  );
};
const carry = (line?: string, ground?: string): TransitionPresentation<any> =>
  ({component: CarryPresentation, props: {line, ground}});

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

// FOCUS RELAY — the cut happens at the FOCAL PLANE, not at the frame edge.
//
// WHY THIS SEAM EXISTS, and why it is the one worth borrowing. Measured against the video-shotcraft library
// (218 shots, same stack: Remotion 4 + React, CSS 3D), that library reaches for `blur()` in 35% of its shots
// and this one in 11%, and the difference is not decoration: three of its six documented hand-off recipes are
// built on DEPTH — through-dark flight, focus relay, portal wipe — and this tier had none of them. Every seam
// we ship (fade, dissolve, clock, wipe, carry) operates in the PLANE. A film whose cuts are all planar reads
// as pages replacing pages; the launch films it is measured against never cut that way.
//
// The move is one a camera makes and a page cannot: the outgoing beat slides OUT of the focal plane while the
// incoming beat pulls INTO it. What the eye tracks across the cut is the focus itself.
//
// THE PARAMETERS ARE THE BORROWED PART, and the stagger is the whole trick. From that library's case law:
// "前景 blur 0→8px 同时后景 8px→0，交叉窗口 10–16f；两景错开 2–4f 起跑" — and, as the recorded failure,
// "同帧起跑读作整屏糊掉": start both at the same frame and the audience sees one blurred screen instead of a
// hand-off. So the incoming beat starts sharpening AFTER the outgoing one has begun to soften (OFFSET), which
// is what makes it read as a relay. A scale pair rides with it — the leaving beat drifts back a touch, the
// arriving one comes forward — because a lens that racks focus also changes what fills the frame.
//
// LUMINANCE-SAFE BY CONSTRUCTION, so `pickPresentation`'s dark↔light guard never has to refuse it: nothing
// here brightens or darkens a frame; blur redistributes light, it does not add any.
const BLUR_MAX_PX = 9;                 // 8px in the source case law, scaled a touch for 1080p
const RELAY_OFFSET = 0.18;             // ~2-4 frames of a 12-frame seam — the anti "one blurred screen" rule
const FocusRelayPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const isEnter = presentationDirection === 'entering';
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  // The leaving beat softens from the first frame; the arriving one waits RELAY_OFFSET before it starts to
  // resolve, so at mid-seam one image is going and the other is coming rather than both being mush.
  const blur = isEnter
    ? interpolate(p, [RELAY_OFFSET, 1], [BLUR_MAX_PX, 0], c)
    : interpolate(p, [0, 1 - RELAY_OFFSET], [0, BLUR_MAX_PX], c);
  const scale = isEnter
    ? interpolate(p, [RELAY_OFFSET, 1], [1.045, 1], c)
    : interpolate(p, [0, 1 - RELAY_OFFSET], [1, 0.985], c);
  // Opacity crosses LATE and fast. The focus carries the hand-off; a long opacity cross on top of it would
  // make this an ordinary dissolve wearing a blur.
  const op = isEnter ? interpolate(p, [0.34, 0.68], [0, 1], c) : interpolate(p, [0.32, 0.66], [1, 0], c);
  // ...and the ground under the leaving half — see SeamGround below. This seam has faded both halves since it
  // was built, so on a light film it dipped toward black at mid-seam exactly as `fadethrough` did; it was
  // found by the instrument written for the new seams, not by the eye, and the fix is the same floor.
  //
  // THE UNLOCK GOES INSIDE THE BLUR. Type near the centre of a scale crawls, and a blur keeps only the scale of
  // the matrix above it (runtime/textSafe.tsx), so an unlock written beside the blur would never reach the glyphs.
  const glide = useGlide();
  return (
    <SeamGround bg={passedProps?.bg} show={!isEnter && p > 0}
      style={{opacity: op, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined,
        transform: `scale(${scale.toFixed(4)})`, transformOrigin: 'center'}}>
      <AbsoluteFill style={{transform: glide(undefined, true)}}>{children}</AbsoluteFill>
    </SeamGround>
  );
};
const focusRelay = (bg?: string): TransitionPresentation<any> => ({component: FocusRelayPresentation, props: {bg}});

// ────────────────────────────────────────────────────────────────────────────────────────────────────────
// THE THREE SEAMS THIS TIER COULD NOT SAY. Measured against the peer library (references/launch-film-study.md)
// this tier shipped 9 seam words against their 18. The honest reading of that gap is NOT that nine more moves
// are missing — our own motion-grammar REFUSES the novelty half of any such list (iris, blinds, cube,
// checkerboard: "the audience notices the mechanism instead of the content"). It is that three RELATIONS this
// repo had already written down, and had already implemented on the html tier, had no remotion word at all:
// a reset whose emphasis belongs to the NEW content, a page that breathes away in the reading direction, and
// a reflective coda. A relation one tier can claim and the other cannot is a vocabulary hole, and a
// storyboard that asked for one of them here was silently answered with a plain cross-fade.
//
// `push` and `lift` are the fourth and fifth words, and they needed no new picture — Remotion's `slide` IS a
// push, and `lift` is that push turned through 90°. They were reachable only by their HTML spelling
// (`transition_style`), so `transition_in: {type: "push"}` fell through `_KINETIC_TYPES` to a fade. One
// relation, one word, both tiers.

// A SEAM THAT FADES BOTH HALVES MUST PAINT THE GROUND UNDER THEM, or it dips to whatever is behind the
// sequences — which is BLACK. Measured on two near-white beats (mean 222) with `fadethrough` between them:
// the seam went 222 → 13.5 → 222, a black hole between two cream frames. That is the same defect this file
// already records for @remotion/transitions/dissolve ("a full black hole where the seam should be"), arriving
// through a different door: Remotion's own `fade` never shows it because only the ENTERING half carries an
// opacity and the leaving one stays opaque underneath. Any seam that fades the leaving half too — this tier's
// focus relay, and the three seams below — has to supply that floor itself.
//
// It is painted under the EXITING half only. The entering half sits on top, so an opaque ground there would
// hide the beat being left behind for the whole seam.
//
// AND ONLY WHILE THAT HALF IS ACTUALLY LEAVING (progress above 0). A TransitionSeries wraps the WHOLE of each
// sequence in its exit presentation, at progress 0 until its seam begins — so the ground was painted under the beat
// for its entire length, including the frames in which that same beat was still ARRIVING over the one before it.
// There it is an opaque full-frame fill above the beat being left: measured on the seam probe, a paper beat cut to
// the next beat's near-black ground on the first frame of a plain dissolve (frame mean 205 -> 9.7), because that
// next beat's own exit was a whip. At progress 0 the leaving half is still fully opaque in every seam that uses
// this, so it needs no floor there.
const SeamGround: React.FC<{bg?: string; show: boolean; children: React.ReactNode; style?: React.CSSProperties}> =
  ({bg, show, children, style}) => (
    <>
      {show && bg ? <AbsoluteFill style={{background: bg}} /> : null}
      <AbsoluteFill style={style}>{children}</AbsoluteFill>
    </>
  );

// FADE-THROUGH — the same reset as a dip, with the emphasis moved onto what ARRIVES.
// Material's 30/70: the outgoing image leaves FAST and the incoming one takes the rest of the seam. A
// symmetric cross-fade splits the viewer's attention evenly between a thing that is over and a thing that is
// starting; this one does not. It is the upgraded default for a precise register, and it is NOT exempt from
// the luminance guard: leaving fast is exactly how a dark ground becomes a light one in 0.15s.
const FadeThroughPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const isEnter = presentationDirection === 'entering';
  const op = isEnter
    ? interpolate(p, [0.34, 1], [0, 1], c)          // 70% of the seam belongs to the new content
    : interpolate(p, [0, 0.30], [1, 0], c);         // 30%, and the old content is gone
  return <SeamGround bg={passedProps?.bg} show={!isEnter && p > 0} style={{opacity: op}}>{children}</SeamGround>;
};
const fadeThrough = (bg?: string): TransitionPresentation<any> => ({component: FadeThroughPresentation, props: {bg}});

// DRIFT — a cross-fade that also MOVES, ~24px in the reading direction. Direction without loudness: the page
// breathes away rather than being pushed off. The travel is small on purpose — past about 3% of the frame it
// stops reading as a breath and starts reading as a failed push.
//
// It is luminance-SAFE by construction, so it joins the seams the harsh-gap guard lets through: every pixel
// it draws is one of the two beats at some opacity, exactly as `fade` does, and a translation adds no light.
const DRIFT_FRAC = 0.022;              // of the frame's long side — ~24px at 1080p, the html tier's number
// THE ONE SEAM THAT CLAIMS A PLACE. Every other word in this vocabulary says something about the
// RELATIONSHIP between two beats — continuity, arrival, a chapter break, a hand-off. None of them can say
// "this is where we were", and a film that reaches back to an earlier idea had no way to show it.
//
// It is a PAN, so both halves travel together in the same direction and at the same rate: the leaving beat
// slides out by the whole vector while the arriving one comes in from the far side of it, which is what a
// camera crossing a board actually does. Drawn as two independently sliding pages it would read as a push.
//
// THE VECTOR IS NOT COMPUTED HERE. It arrives in `passedProps` from `scripts/film_board.py`, which knows
// where both beats sit; deriving board geometry in two languages is how the two drift apart. It is a UNIT
// step along one axis — never a diagonal and never a fraction — because two full-frame pictures tile only
// when they are exactly one frame apart, and a diagonal offset leaves two corners bare.
//
// NO PERSPECTIVE, ON PURPOSE. `runtime/depth.tsx` measured what a Z plane costs this renderer — glyph edge
// strength 91 flat against 56 under `perspective(1200px) translateZ(50px)`, a 38% loss — so a "space" built
// that way would soften every word in the film. A pure 2D translate has no such cost, and at both ends of
// the seam the transform is exactly identity, so no beat is ever READ through a transform at all.
// (Drawn by WhipPresentation below — the return is a push along its own vector.)
// the return is geometrically a push along its own vector, so it is drawn by the push's presentation (below): the
// same ease, the same shutter, and — tests/test_film_board.py — the same picture as a push in the matching direction
const travelBack = (dx: number, dy: number, W: number, H: number, bg?: string): TransitionPresentation<any> =>
  ({component: WhipPresentation, props: {dx, dy, W, H, n: TR, bg}});

// THE PUSH MOVES LIKE A CAMERA. `push`/`slide`/`lift` were Remotion's own slide on a linear timing: a whole frame
// crossed the screen at a constant 160 px a frame (1920 wide, 12 frames), starting and stopping dead, and every frame
// of it was razor sharp — the largest movement in a film, and the one that strobed. A camera that pans that far
// eases in and out of it, and its shutter smears what passes it. Here both halves travel together on a sine ease (the
// fastest frame is the middle one, where sfx.py lands the whoosh's peak) and each is blurred along the travel by what
// a 180-degree shutter would smear at that frame's speed (stage/surface blurOf), so the blur grows from nothing and
// returns to nothing. The halves still tile at every instant, so no ground ever shows between them.
const WhipPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const isEnter = presentationDirection === 'entering';
  const {dx = 0, dy = 0, W = 1920, H = 1080, n = TR, reduced = false} = passedProps ?? {};
  const q = clamp01(p);
  const e = (1 - Math.cos(Math.PI * q)) / 2;
  const kk = isEnter ? e - 1 : e;
  const vx = dx * W, vy = dy * H;
  // the travel this frame: the ease's slope times the whole vector, over the seam's frames
  const per = (Math.PI / 2) * Math.sin(Math.PI * q) / Math.max(1, n);
  const blur = reduced ? null : blurOf(vx * per, vy * per);
  const id = `whip-${React.useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const glide = useGlide();
  const t = `translate(${(vx * kk).toFixed(2)}px, ${(vy * kk).toFixed(2)}px)`;
  return (
    <>
      {blur ? <BlurFilter id={id} blur={{sx: Math.min(blur.sx, WHIP_BLUR_MAX), sy: Math.min(blur.sy, WHIP_BLUR_MAX)}}
        edge="duplicate" /> : null}
      {/* the filter on the still OUTER layer, the move (with its type unlock) inside it: a blur on the moving element
          itself rasterised it whole-pixel, and a slow-drifting film's type stepped under it (text_safe --glide) */}
      <SeamGround bg={passedProps?.bg} show={!isEnter && p > 0} style={{filter: blur ? `url(#${id})` : undefined}}>
        <AbsoluteFill style={{transform: glide(t, true)}}>{children}</AbsoluteFill>
      </SeamGround>
    </>
  );
};
const WHIP_BLUR_MAX = 40;
/** A push in a direction ('from-right': the new beat comes in from the right, the old one leaves to the left). */
const whip = (direction: string | undefined, W: number, H: number, bg?: string): TransitionPresentation<any> => {
  const d = direction ?? 'from-right';
  const [dx, dy] = d === 'from-left' ? [1, 0] : d === 'from-bottom' ? [0, -1] : d === 'from-top' ? [0, 1] : [-1, 0];
  return {component: WhipPresentation, props: {dx, dy, W, H, n: TR, bg}};
};

const DriftPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const isEnter = presentationDirection === 'entering';
  const dir: string = passedProps?.direction ?? 'from-right';
  const vertical = dir === 'from-bottom' || dir === 'from-top';
  const sign = (dir === 'from-left' || dir === 'from-top') ? -1 : 1;
  const d = (passedProps?.px ?? 24) * sign;
  // eased on both halves so neither edge of the seam has a corner in it
  const travel = isEnter ? interpolate(p, [0, 1], [d, 0], c) : interpolate(p, [0, 1], [0, -d], c);
  const op = isEnter ? interpolate(p, [0.18, 0.82], [0, 1], c) : interpolate(p, [0.18, 0.82], [1, 0], c);
  const t = vertical ? `translateY(${travel.toFixed(2)}px)` : `translateX(${travel.toFixed(2)}px)`;
  const glide = useGlide();
  return <SeamGround bg={passedProps?.bg} show={!isEnter && p > 0} style={{opacity: op, transform: glide(t, true)}}>{children}</SeamGround>;
};
const drift = (direction: string | undefined, W: number, H: number, bg?: string): TransitionPresentation<any> =>
  ({component: DriftPresentation, props: {direction, bg, px: Math.round(Math.max(W, H) * DRIFT_FRAC)}});

// DEFOCUS — the reflective coda. Both beats go soft at the middle of the seam and the new one resolves out of
// it: attention lets go of one thing and settles on another. Budget ONE per film (a quote, a closer).
//
// It is NOT the focus relay, and the difference is the whole reason both exist. The relay STAGGERS — the
// leaving beat softens first and the arriving one waits, so the eye is handed from one subject to another and
// something is always sharp. This one is SYMMETRIC and holds both images soft across the middle: nothing is
// sharp for a moment, which is what makes it read as a pause for thought rather than a hand-off.
// Luminance-safe for the same reason the relay is: a Gaussian blur redistributes light, it does not add any,
// and the opacity pair is an ordinary cross-fade.
const DEFOCUS_MAX_PX = 14;             // deeper than the relay's 9px — this seam is meant to be felt
const DefocusPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const isEnter = presentationDirection === 'entering';
  // both sides reach full softness at mid-seam; the entering beat resolves out of it
  const blur = isEnter
    ? interpolate(p, [0, 0.5, 1], [DEFOCUS_MAX_PX, DEFOCUS_MAX_PX, 0], c)
    : interpolate(p, [0, 0.5, 1], [0, DEFOCUS_MAX_PX, DEFOCUS_MAX_PX], c);
  const op = isEnter ? interpolate(p, [0.38, 0.72], [0, 1], c) : interpolate(p, [0.28, 0.62], [1, 0], c);
  return (
    <SeamGround bg={passedProps?.bg} show={!isEnter && p > 0}
      style={{opacity: op, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined}}>
      {children}
    </SeamGround>
  );
};
const defocus = (bg?: string): TransitionPresentation<any> => ({component: DefocusPresentation, props: {bg}});

// ── THROUGH-DARK FLIGHT — the second of the peer library's three DEPTH hand-offs ────────────────────────
//
// The leaving beat recedes and the light goes out of it; the frame passes through black; the arriving beat
// comes forward out of that dark. What the eye follows across the cut is one continuous flight through an
// unlit space, which is a thing a camera does and a page cannot.
//
// WHAT WAS BORROWED AND WHAT WAS NOT. The peer study recorded this seam's NAME and nothing else: the focus
// relay's parameters were quoted verbatim in that study ("前景 blur 0→8px…两景错开 2–4f 起跑") and these
// were not, and the library is no longer on disk to re-read. So the numbers below are DERIVED here, and the
// derivation is the argument — not a figure presented as if it had been measured somewhere else.
//
// THE DEFINING PROPERTY, from which everything else follows: the two beats never carry light at the same
// time. A cross-fade superimposes two images; a portal shows both at once through a hole. Here, at every
// instant, at most one of them is lit. That is what makes it the one kinetic seam that is safe across a
// dark/light gap — it cannot flash, because there is no moment where a bright frame is added to a dark one.
// It is also why the two ramps OVERLAP by a hair rather than leaving a gap: with an overlap the frame is
// fully black for about one frame of a twelve-frame seam, which reads as passing through darkness; with a
// gap it would HOLD on black, and a held black frame in four tenths of a second is a dropout, not a flight.
const FLIGHT_CROSS = 0.52;             // the leaving beat is dark by here; the arriving one starts at 1 - it
const FLIGHT_AWAY = 0.82;              // how far the leaving beat recedes
const FLIGHT_TOWARD = 1.26;            // how far out the arriving beat starts
const ThroughDarkPresentation = ({presentationProgress: p, presentationDirection, children}: any) => {
  const isEnter = presentationDirection === 'entering';
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  // Eased in on the way out (accelerating away into the dark) and eased out on the way in (decelerating into
  // place) — the shape of one move seen from two ends, rather than two fades pointed at each other.
  // `easeInCubic` is written out rather than imported: `runtime/motion` has the OUT curve and not the IN
  // one, and adding an export there marks all 104 registers that import it stale in `register_energy`
  // (open-work D1) — half an hour of re-measuring for a one-line curve that only this file uses.
  const raw = isEnter
    ? interpolate(p, [1 - FLIGHT_CROSS, 1], [0, 1], c)
    : interpolate(p, [0, FLIGHT_CROSS], [0, 1], c);
  const q = isEnter ? easeOutCubic(raw) : raw * raw * raw;
  const bright = isEnter ? q : 1 - q;
  const scale = isEnter ? FLIGHT_TOWARD + (1 - FLIGHT_TOWARD) * q : 1 + (FLIGHT_AWAY - 1) * q;
  // brightness() is a colour filter: it passes an unlock written beside it through to the glyphs
  const glide = useGlide();
  return (
    <AbsoluteFill style={{filter: `brightness(${bright.toFixed(4)})`,
      transform: glide(`scale(${scale.toFixed(4)})`, true), transformOrigin: 'center'}}>
      {children}
    </AbsoluteFill>
  );
};
const throughDark = (): TransitionPresentation<any> => ({component: ThroughDarkPresentation, props: {}});

// ── PORTAL WIPE — the third of the three, and the one that is NOT luminance-safe ────────────────────────
//
// An aperture opens where the beat was looking and the next beat is already behind it, at full size, while
// the leaving beat scales past the lens. The camera goes THROUGH the frame rather than replacing it.
//
// THE MASK IS THE REVEAL, AND THE ARRIVING BEAT NEVER FADES. An opacity ramp under an opening aperture is a
// dissolve with a shape on it; what makes this read as a portal is that the incoming frame is fully present
// from the first pixel the aperture uncovers.
//
// IT OPENS ON THE CONTENT ZONE'S CENTRE, NOT THE FRAME'S. Every register in this library composes inside
// `CONTENT_TOP..contentBottom` because the strip below belongs to the burned caption, so the frame's own
// centre sits low of everything a viewer is looking at — by 90px at 16:9 and 190px at 9:16. An aperture
// opening from there starts on the caption band and grows off-centre against the composition.
//
// AND IT IS DELIBERATELY NOT IN `CANNOT_FLASH`. A bright disc opening on a dark field is precisely the
// brightness jump the luminance guard exists to refuse, so on a dark/light seam this is rewritten to the
// gentle fade like every other kinetic seam. Only the through-dark flight earns the exemption, and it earns
// it by never lighting both beats at once.
const PORTAL_PUSH = 1.4;               // how far the leaving beat scales as the camera passes through it
const PortalPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const isEnter = presentationDirection === 'entering';
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const W = Number(passedProps?.W) || 1920, H = Number(passedProps?.H) || 1080;
  const cy = (CONTENT_TOP + contentBottom(W, H)) / 2;
  // The radius that covers the whole frame from that centre: the furthest corner, which is the bottom one
  // because the centre sits above the middle. Measured rather than assumed — a radius taken from the frame
  // centre leaves an uncovered sliver along the bottom edge at 9:16.
  const far = Math.hypot(Math.max(W - W / 2, W / 2), Math.max(H - cy, cy));
  const r = easeOutCubic(p) * far;
  const glide = useGlide();
  if (!isEnter) {
    // The leaving beat holds its light until the aperture has taken most of the frame; a long fade under an
    // opening portal is the dissolve this seam exists not to be.
    const op = interpolate(p, [0.62, 0.96], [1, 0], c);
    const scale = 1 + (PORTAL_PUSH - 1) * p * p * p;
    return (
      <AbsoluteFill style={{opacity: op, transform: glide(`scale(${scale.toFixed(4)})`, true),
        transformOrigin: `50% ${((cy / H) * 100).toFixed(2)}%`}}>{children}</AbsoluteFill>
    );
  }
  // A 1.5% feather on the aperture's edge: a hard stop aliases into a visibly stepped circle at 1080, and
  // this edge is the one thing on the frame the eye is following.
  const soft = Math.max(1, r * 0.015);
  const mask = `radial-gradient(circle ${(r + soft).toFixed(1)}px at 50% ${cy.toFixed(1)}px, `
    + `#000 ${Math.max(0, r - soft).toFixed(1)}px, transparent ${(r + soft).toFixed(1)}px)`;
  return (
    <AbsoluteFill style={{WebkitMaskImage: mask, maskImage: mask}}>{children}</AbsoluteFill>
  );
};
const portal = (W: number, H: number): TransitionPresentation<any> =>
  ({component: PortalPresentation, props: {W, H}});

// DNA-native DEFAULT seam (Motion grammar): an UNMARKED seam on a themed film becomes the STYLE's native action
// instead of a generic fade — the analogue of the surface/grammar split for TIME. terminal → screen-clear;
// product → a soft push; editorial/blueprint → a directional wipe (a page/sheet turn); else the gentle fade.
const dnaDefaultSeam = (dna: DesignDNA | null, W: number, H: number): TransitionPresentation<any> | null => {
  if (!dna) return null;
  // A DECLARED seam wins over the preset switch below. Without this a bespoke `id` — which is what every
  // topic-conceived direction has — matched no case and fell through to the anonymous cross-fade, so the
  // native-cut idea only ever worked for the five shipped presets.
  const d = dna.seam?.type;
  if (d && d !== 'fade') {
    const dir = dna.seam?.direction;
    if (d === 'screen-clear') return screenClear(dna.bg, dna.accent);
    if (d === 'slide') return whip(dir, W, H, dna.bg);
    if (d === 'wipe') return wipe({direction: (dir as any) ?? 'from-bottom'});
    if (d === 'clock') return clockWipe({width: W, height: H});
    if (d === 'dissolve') return fade();
    // a world whose native cut is the plain hard cut — every unmarked seam changes picture on one frame
    if (d === 'cut') return cut();
  }
  if (dna.seam?.type === 'fade') return null;      // an explicit, deliberate plain cut
  switch (dna.id) {
    case 'terminal': return screenClear(dna.bg, dna.accent);
    case 'product': case 'apple': return whip('from-right', W, H, dna.bg);
    case 'editorial': case 'blueprint': return wipe({direction: 'from-bottom'});
    case 'data': return wipe({direction: 'from-left'});             // a measured sweep, like a chart redrawing
    case 'retro': return whip('from-bottom', W, H, dna.bg);         // an arcade screen push
    // 'cinematic' (and any unknown id) keep the gentle cross-fade — the filmic seam IS a dissolve.
    default: return null;
  }
};

// The colour of the carry's bridge line, picked against the ground it is drawn on rather than assumed dark.
// Takes the BEAT's resolved ground when there is one (the film DNA otherwise): the bridge line is the thing
// the eye tracks across the cut, and a pale neutral drawn on a beat that re-grounded to paper is a collapse
// to nothing — the same defect the cream-film fix below already caught once at the film level.
type SeamColors = {bg?: string | null; accent?: string | null; fg?: string | null; line?: string | null};
const carryLine = (g: SeamColors | null): string | undefined => {
  const y = g ? lumValue(g.bg) : null;
  if (y === null) return g?.line ?? undefined;
  return y > LIGHT_KEY_Y ? (g?.accent ?? g?.fg ?? undefined) : '#e8edf5';
};

const LUM_RANK: Record<Lum, number> = {dark: 0, mid: 1, light: 2};

/** The anchors a seam takes hold of: one id for both beats, or `{from, to}`. Null when the board named none. */
export const carryIds = (ti?: SceneSpec['transitionIn']): {from: string; to: string} | null => {
  const c = ti?.carry;
  if (typeof c === 'string' && c.trim()) return {from: c, to: c};

// The seam GRAMMAR. A seam is luminance-SAFE by default and SEMANTIC when marked. A ground-luminance gap of
// ≥2 (a dark↔light cut) FORCES a gentle cross-fade — it blends through mid-gray so there's no brightness
// flash, and a hard kinetic edge (a bright scene sliding over a dark one) is exactly what we suppress there.
// On a same/near-luminance seam the EDL may MARK a kinetic move (slide/wipe/clock/dissolve) for a chapter
// break; unmarked seams stay a fade. Every seam holds at TR frames so it rides the audio-breath silence
// (A/V stays in sync); no spins, ever. Deterministic — pure fn of the two scenes' declared ground.
// `prevG`/`nextG` are the grounds the two beats paint AT THE SEAM — the leaving beat's last frame and the
// entering beat's first. They are the film DNA for a beat that declares no ground of its own, which is what
// keeps every existing film's seam decisions identical; for a re-grounded beat they are the only honest
// input, since the film-wide ground the guard used to read is no longer what is on either frame.
  if (c && typeof c === 'object' && typeof c.from === 'string' && typeof c.to === 'string' && c.from && c.to) {
    return {from: c.from, to: c.to};
  }
  return null;
};

// The seam the cut ACTUALLY draws once reduced motion and the luminance guard have had their say. Two callers must
// agree on it: the presentation picked below, and the arriving beat's carry provider — a register draws a container's
// anchor already in place only when a container is really what arrives, never when the guard turned it into a fade.
const seamDrawn = (prev: SceneSpec, next: SceneSpec, dna: DesignDNA | null,
                   prevG: GroundColors | null, nextG: GroundColors | null,
                   reducedMotion = false): {t: string; harsh: boolean} => {
  if (reducedMotion) return {t: 'fade', harsh: false};
  const lumOf = (sc: SceneSpec, g: typeof nextG) => {
    const y = stageGroundY(sc, g);
    return y !== null ? lumFromY(y) : dnaGroundLum(sc.shot, sc.bgLum, g);
  };
  const dLum = Math.abs(LUM_RANK[lumOf(next, nextG)] - LUM_RANK[lumOf(prev, prevG)]);
  const want = next.transitionIn?.type ?? 'fade';
  // luminance guard: a dark↔light gap forces the gentle fade — EXCEPT the two seams that cannot flash.
  // `carry`'s neutral bridge line IS the dip. `focus` cannot flash at all: racking focus redistributes light
  // rather than adding any, so the frame's mean luminance is untouched by definition. That property was
  // written in the presentation's own header and NOT told to this guard, so the seam was silently rewritten
  // to a fade on exactly the crossing cuts it exists to serve — three renders measured byte-for-byte
  // identical luminance, sharpness and motion before this line was found.
  // PERCEPTUAL guard. The bucket gap alone missed the real flashes: a near-black ground cutting to an
  // accent flood scores dark->mid (gap 1) while the frame goes from ~20 to ~150 in display terms. Judge on
  // the display-encoded distance when both grounds resolve, and keep the bucket rule as the fallback.
  const gap = groundGap(dnaGroundY(prev.shot, prevG), dnaGroundY(next.shot, nextG));
  const harsh = gap === null ? dLum >= 2 : gap >= HARSH_GROUND_GAP;
  // `through-dark` earns the same exemption for a third reason, and the strongest of the three: the two
  // beats never carry light at the same time, so there is no instant where a bright frame is added to a
  // dark one. `portal` is deliberately NOT here — a bright aperture opening on a dark field is precisely
  // the brightness jump this guard exists to refuse.
  // `drift` and `blur` join them, each for a reason that can be checked rather than asserted: `drift` draws
  // exactly what `fade` draws and then translates it, and a translation adds no light; `blur` is a Gaussian
  // over a cross-fade, and a Gaussian redistributes light without adding any. `fadethrough` is deliberately
  // NOT here — leaving fast is how a dark ground becomes a light one in 0.15s, which is this guard's case.
  // `return` is deliberately NOT here, and the reason is consistency rather than doubt: it is geometrically
  // the same move as `push` — two full frames tiling past each other — and `push` is not exempt either.
  // Both may well deserve the exemption (nothing is ever uncovered, so no ground can flash through), but
  // that is a claim to EARN with three measured renders the way `focus` earned its, and for both words at
  // once. Giving my own new word an exemption its twin does not have would be special pleading.
  // `container` (seams.tsx) earns it the way `drift` did, and it was MEASURED before it was granted: outside the
  // container every pixel is exactly what `fade` draws (the arriving beat at opacity p over the opaque leaving one),
  // and inside it the two beats' own pixels cross later in the seam. Rendered between a dark phone beat and the
  // same beat re-keyed light (mean 17.4 / 237.9): the frame mean ran monotone between the two in both directions
  // (one 0.2-level wobble on the first frame), never outside them, within 17 levels of the fade on the same frame,
  // with a steepest step of 27 levels a frame against the fade's 19 — and 24.5 against 18.5 on the probe film's
  // dark stage card carried into a light figure. A fade with an element in it, not a flash. `grow`, `through-window` and `punch` are
  // deliberately NOT here: a growing shape or a window of a bright beat opening on a dark one is the portal's
  // brightness jump, and a punch is a hard cut with a flash on it.
  // `cut` (seams.tsx) earns it by the through-dark's own argument taken to its limit: the two beats never share a
  // frame at all, so no frame can add a bright picture to a dark one or move a bright edge across a dark field — the
  // two things this guard exists to refuse. What a crossing cut DOES is a step: measured on a dark beat cut to a light
  // one (tests/test_hard_cut.py), the frame mean holds the dark beat's value to the cut's frame and the light beat's
  // from it — one step, inside both beats' range, never back. A step is half of what photosensitivity guidance calls a
  // flash (ITU-R BT.1702: a PAIR of opposing changes, harmful past three in one second); a cut every beat cannot make
  // three in a second. Whether a dark/light smash cut suits THIS film is the planner's call (seam_plan.py plans cuts
  // only on films whose energy asks for them), not this guard's.
  const CANNOT_FLASH = new Set(['carry', 'focus', 'through-dark', 'drift', 'blur', 'container', 'cut']);
  const t = (harsh && !CANNOT_FLASH.has(want)) ? 'fade' : want;
  return {t, harsh};
};

/** The anchor pair of a seam that must have one — a board that asks for it with none is refused, loudly. */
const needAnchor = (next: SceneSpec, word: string): {from: string; to: string} => {
  const ids = carryIds(next.transitionIn);
  if (!ids) {
    throw new Error(`scene ${next.shot} asks for a '${word}' seam and names no anchor (\`carry\`) — this seam takes ` +
      'hold of one marked element (runtime/carry data-carry), and a seam with nothing to hold is not drawn as a fade ' +
      'in its place. Name the anchor, or choose another seam (validate.py lists each register\'s anchors).');
  }
  return ids;
};

// The corner a DECLARED container rect is drawn with (a board's match_cut `shape`): a box takes the film's own card
// radius; a bar, a line and a dot are fully rounded (the clip clamps the radius to half the short side).
const SHAPE_RADIUS_FULL = 1e6;
const containerSpec = (next: SceneSpec, W: number, H: number, seam: string, dna: DesignDNA | null) => {
  const ti = next.transitionIn ?? {type: 'container' as const};
  const quad = (q: unknown): [number, number, number, number] | undefined =>
    Array.isArray(q) && q.length === 4 && q.every((v) => typeof v === 'number' && Number.isFinite(v))
      ? q as [number, number, number, number] : undefined;
  const fromQuad = quad(ti.from), toQuad = quad(ti.to);
  if (fromQuad && toQuad) {
    const shape = ti.shape ?? 'box';
    const radius = shape === 'box' ? (typeof dna?.radius === 'number' ? dna.radius : 12) : SHAPE_RADIUS_FULL;
    return {seam, fromQuad, toQuad, radius, W, H};
  }
  const ids = needAnchor(next, 'container');
  return {seam, from: ids.from, to: ids.to, W, H};
};

const groundFill = (g: GroundColors | null): string | undefined => g?.bgGrad ?? g?.bg ?? undefined;

/** The film's PAPER — the lightest of its ground, surface and ink — which a punch flashes for two frames. */
const paperOf = (dna: DesignDNA | null, g: GroundColors | null): string | undefined => {
  const cands = [g?.bg, g?.surface, dna?.bg, dna?.surface, dna?.fg].filter((c): c is string => typeof c === 'string');
  let best: string | undefined, bestY = -1;
  for (const c of cands) { const y = lumValue(c); if (y !== null && y > bestY) { best = c; bestY = y; } }
  return best;
};

const pickPresentation = (prev: SceneSpec, next: SceneSpec, W: number, H: number, dna: DesignDNA | null,
                          prevG: GroundColors | null, nextG: GroundColors | null,
                          reducedMotion = false, seam = 'seam', lead = 0): TransitionPresentation<any> => {
  // REDUCED MOTION REACHES THE SEAMS, WHICH IT DID NOT. Everything else in this tier honoured it — `useT()`
  // freezes every register's animation at REDUCED_MOTION_T, the ambient camera is zeroed, the finish layer
  // drops to 0.55 — and then the film slid a WHOLE FRAME across the screen at every marked seam, which is
  // the largest single movement in it. Measured by rendering the same mid-seam frame both ways: the tile
  // boundary sat at column 889 against 889, the only difference being the 10px of ambient drift that was
  // already being switched off. The accessibility variant was leaving the biggest motion untouched.
  //
  // A cross-fade is the answer the html tier already gives ("HTML reveals become opacity-only
  // cross-fades"), it is what this function's own luminance guard already falls back to, and it carries no
  // movement at all. One rule, both tiers.
  if (reducedMotion) return fade();
  const {t, harsh} = seamDrawn(prev, next, dna, prevG, nextG, reducedMotion);
  const dir = next.transitionIn?.direction;
  // The seams that fade their LEAVING half need a floor to fade onto. `carry` already asked for this ground
  // by name; the others took whatever was behind the sequences, which is black.
  const seamBg = nextG?.bg ?? prevG?.bg ?? undefined;
  // MOTION GRAMMAR: an UNMARKED (default) seam becomes the DNA's native action on a luminance-safe cut (a themed
  // film's cuts belong to its world — terminal = screen-clear, etc.); explicit marks + the dark↔light fade win.
  // ...except a cut a camera HAND-OFF carries (runtime/handoff): the push running through it is that cut's motion,
  // and the product DNA's native whip on top of it was measured on the seam probe as two moves at once — the frame
  // sliding sideways under a blur while it zoomed. One motion per cut: the hand-off rides the plain cross-fade.
  if (t === 'fade' && !harsh && !prev.camera?.handoff) { const s = dnaDefaultSeam(dna, W, H); if (s) return s; }
  switch (t) {
    // One relation, one word, on both tiers: `push` is Remotion's own slide (the incoming page pushes the
    // outgoing one off), and `lift` is that move turned through 90° — a reading-flow progression down a page.
    case 'slide': case 'push': return whip(dir ?? 'from-right', W, H, seamBg);
    case 'lift': return whip(dir ?? 'from-bottom', W, H, seamBg);
    // the ground the seam dips THROUGH is the film's own, never the black behind the sequences
    case 'fadethrough': return fadeThrough(seamBg);
    case 'drift': return drift(dir, W, H, seamBg);
    case 'return': return travelBack(next.transitionIn?.dx ?? 0, next.transitionIn?.dy ?? 0, W, H, seamBg);
    case 'blur': return defocus(seamBg);
    case 'wipe': return wipe({direction: (dir as any) ?? 'from-bottom'});
    case 'clock': return clockWipe({width: W, height: H});
    // `dissolve` is a CROSS-DISSOLVE — setup and result share the screen for a moment. It is NOT
    // @remotion/transitions/dissolve, which despite the name is a WebGL FILM-BURN (red/yellow flame
    // colours, and it renders through html-in-canvas). Measured on this renderer: a dissolve seam
    // between two cream shots rendered at mean luminance 11 on frames whose scenes measure 226 — a
    // full black hole where the seam should be. It also meant `dissolve` named two different things
    // depending on which path reached it, since dnaDefaultSeam already mapped the word to fade().
    // One word, one meaning, and the meaning is the film one.
    case 'dissolve': return fade();
    // The bridge line is the thing the eye TRACKS across the cut, so it has to be visible against this
    // film's ground — `dna.line` is a hairline grey chosen to sit quietly inside a drawing, and on a
    // cream ground it disappeared entirely, leaving a collapse to nothing. Contrast-picked: the accent
    // on a light ground (it is the film's own emphasis colour), a pale neutral on a dark one.
    case 'carry': return carry(carryLine(nextG as SeamColors | null), nextG?.bg ?? undefined);
    // the three seams that happen in DEPTH rather than in the plane — see their own headers above
    case 'focus': return focusRelay(seamBg);
    case 'through-dark': return throughDark();
    case 'portal': return portal(W, H);
    // the four that take hold of ONE thing (seams.tsx). An anchor the board did not name is refused here as well as
    // in validate.py: a container with nothing to carry is not a seam that can quietly become a fade
    // `lead` (the leaving unit's length) and `n` (the seam's) let each half tell its seam frames from the rest of its
    // beat — a TransitionSeries wraps the WHOLE sequence in its presentation (seams.tsx useInSeam)
    case 'container': return container({...containerSpec(next, W, H, seam, dna), lead, n: TR});
    // the arriving beat's GROUND, gradient and all — measured on the first grow, a flat `bg` under a beat that paints
    // `bgGrad` showed as a flat-edged panel across the frame until the beat came in over it
    case 'grow': return grow({seam, from: needAnchor(next, 'grow').from, ground: groundFill(nextG), W, H, lead, n: TR});
    case 'through-window': return throughWindow({seam, from: needAnchor(next, 'through-window').from,
      ground: groundFill(nextG), W, H, lead, n: TR});
    case 'punch': return punch({paper: paperOf(dna, nextG), W, H, n: TR, seam, lead});
    // the hard cut: the picture changes on the seam's middle frame, both voices keep the seam's overlap (seams.tsx)
    case 'cut': return cut();
    default: return fade();
  }
};

// the camera hand-off's curves live in runtime/handoff.ts (pure, so a test can run them)
type CamPlan = {out?: {amp: number; move: 'push' | 'pull'}; in?: {rate: number; limit: number}};

/** The beat's camera: SceneCamera exactly as before, or — on a beat in a hand-off — HandoffCamera. */
const BeatCamera: React.FC<React.ComponentProps<typeof SceneCamera> & {plan: CamPlan | null; phrase?: number[]}> =
  ({plan, phrase, ...rest}) =>
  plan ? <HandoffCamera plan={plan} {...rest} />
    : phrase && phrase.length && !rest.pan && (rest.move === 'push' || rest.move === 'pull')
      ? <PhraseCamera phrase={phrase} {...rest} />
    : <SceneCamera {...rest} />;

/** An AUTHORED push or pull delivered in phrase steps (runtime/phrase.ts): the author's direction and amount, the same
 *  budget SceneCamera gives the move, arriving clause by clause instead of as a creep spread over the beat — measured
 *  on espresso, a push over 18.8 s and a pull over 15.2 s moved under what a viewer sees and the beats held still
 *  9.8 s and 8.2 s.
 *
 *  ONLY AUTHORED MOVES. Steps on beats nobody gave a camera were built and measured, as a scale and as a travel, and
 *  withdrawn: jitter_qa found type trembling on registers that had been still (TechnicalPlate's callout digits
 *  0.19-0.22 px; gps's BroadcastStream and TwoClocksApart up to 0.47 px — 6 failing lines became 17). A camera added to
 *  a beat re-positions every glyph in it, and which registers survive that is not knowable before rendering. */
const PhraseCamera: React.FC<React.ComponentProps<typeof SceneCamera> & {phrase: number[]}> = ({phrase, ...rest}) => {
  const f = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  const unlockAllowed = React.useContext(BaselineUnlockContext);
  const {amp} = cameraBudget({W, H, move: rest.move === 'pull' ? 'pull' : 'push', amount: rest.amount,
    driftExtra: rest.driftExtra ?? 0, driftTranslate: rest.driftTranslate ?? 0, reduced, unlockAllowed, driven: true});
  const done = phraseExtra(f, fps, phrase, 1);                      // 0..1 of the beat's steps
  const extra = rest.move === 'pull' ? amp * (1 - done) : amp * done;
  return <SceneCamera {...rest} drive={{extra, moving: true}} />;
};

/** SceneCamera driven by the hand-off's curves on this beat's own clock. */
const HandoffCamera: React.FC<React.ComponentProps<typeof SceneCamera> & {plan: CamPlan}> = ({plan, ...rest}) => {
  const f = useCurrentFrame();
  const dur = React.useContext(SceneDurationContext) ?? 1;
  const extra = plan.out ? handoffOut(f, dur, plan.out.amp, plan.out.move).extra
    : plan.in ? handoffIn(f, dur, plan.in.rate, plan.in.limit) : 0;
  return <SceneCamera {...rest} drive={{extra, moving: true}} />;
};

// #camera — a subtle whole-film DRIFT (a slow breathing zoom + float) applied to the WORLD only; the HUD
// (captions + the intro/outro veil) stays OUTSIDE it, immune (huashu's camera-rig discipline). Low amplitude
// over a generous overscan (min scale ~1.025) so a pan can never reveal an edge; deterministic (pure fn of
// frame, sin never Math.random). amp scales with meta.motion_personality; amp 0 disables (reduced-motion).
const TWO_PI = Math.PI * 2;
// The largest EXTRA scale the drift can add (0.035 + 0.010 at the sine's peak). Named so the per-beat
// camera's budget can subtract it instead of the two layers silently multiplying past what the caption
// band can absorb — and so it cannot drift from the expression below.
export const DRIFT_MAX_EXTRA = 0.045;
// The drift also TRANSLATES, and downward translation eats the same headroom the scale does. The per-beat
// budget subtracted only the scale, so the two layers together could travel ~4px further toward the caption
// than the cap believed. Small, but it is the difference between a derived bound and an approximate one —
// and this is the third time in this file a budget was computed from part of what spends it.
export const DRIFT_MAX_TRANSLATE_Y = 4;
// THE DRIFT MOVES EVERY FRAME OF EVERY BEAT, so it carries the baseline unlock (runtime/glide.ts) for the whole
// film — without it every line of type in a drifting film steps a pixel at a time against its own drawing, on
// the beats whose own camera holds as much as on any other. The skew tilts the layer's top and bottom edges, so
// the scale is held at least at the size that still covers the frame (`unlockCoverScale`); the drift's own
// breathing scale already clears that except at the smallest amplitudes.
const cameraTransform = (frame: number, amp: number, W: number, H: number, unlock: boolean): string => {
  if (amp <= 0) return 'none';
  const s = 1 + amp * (0.035 + 0.010 * Math.sin((frame / 720) * TWO_PI));     // breathe, ~24s period
  const x = amp * 6 * Math.sin((frame / 930) * TWO_PI + 1.3);                  // float — offset periods so it never repeats
  const y = amp * 4 * Math.sin((frame / 810) * TWO_PI + 0.4);
  if (!unlock) return `scale(${s.toFixed(5)}) translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
  const sc = Math.max(s, unlockCoverScale(H / 2, W / 2, y));
  return `scale(${sc.toFixed(5)}) translate(${x.toFixed(2)}px, ${y.toFixed(2)}px) ${BASELINE_UNLOCK}`;
};
// The most EXTRA scale the drift can reach with the unlock's cover counted — what the per-beat camera's budget
// must subtract. Usually DRIFT_MAX_EXTRA; at a very small amplitude the cover is the larger of the two.
const driftExtraFor = (amp: number, W: number, H: number, unlock: boolean): number =>
  amp <= 0 ? 0 : Math.max(amp * DRIFT_MAX_EXTRA,
    unlock ? unlockCoverScale(H / 2, W / 2, amp * DRIFT_MAX_TRANSLATE_Y) - 1 : 0);

// The terminal chrome drawn in THIS BEAT's ground tokens. It used to be handed the film DNA directly, so on a
// beat that re-grounds to paper the breadcrumb kept the dark film's `dim` grey and vanished. It reads the DNA
// from context instead — which inside a Sequence is the beat's — so it re-exposes with everything else. With
// no per-beat ground the context value IS the film DNA object, so this renders exactly what it did before.
const BeatChrome: React.FC<{chrome?: SceneSpec['chrome']; W: number; H: number}> = ({chrome, W, H}) => {
  const dna = React.useContext(DesignDNAContext);
  return <TerminalChrome dna={dna} path={chrome?.path} status={chrome?.status} root={chrome?.root} W={W} H={H} />;
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
const BrandMark: React.FC<{brand?: any; safe?: SafeProfile | null}> = ({brand, safe}) => {
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
        // on a platform-safe film below the platform's tabs (runtime/safeZone `top`)
        style={{position: 'absolute', top: safe ? Math.max(m, safe.top * height) : m, height: h, maxWidth: width * 0.35, objectFit: 'contain',
          opacity: bug.opacity ?? 0.55, ...side}} />
    </AbsoluteFill>
  );
};

/** A beat's voice — except inside a seam's second rendering of the beat (seams.tsx container), where it would play
 *  twice over its own first words. The same <Audio> element otherwise, so a film's sound is what it was. */
const BeatAudio: React.FC<{src: string}> = ({src}) =>
  React.useContext(SeamCopyContext) ? null : <Audio src={staticFile(src)} />;

/** Marks a stage run's frame with the beat on screen (`data-beat`), as each single beat's wrapper does, so the sync
 *  audit can still attribute what it reads to a beat. */
const StageBeatMark: React.FC<{first: number; beats: StageBeat[]; children: React.ReactNode}> = ({first, beats, children}) => {
  const frame = useCurrentFrame();
  let k = beats.findIndex((b) => frame < b.start + b.durF);
  if (k < 0) k = beats.length - 1;
  return <AbsoluteFill data-beat={String(first + k)} data-stage-run="1">{children}</AbsoluteFill>;
};

// THE BEAT'S OPTIC, offered to its register (runtime/optics useBeatOptic). With nothing declared and no `auto` DNA no
// provider is mounted at all — a context provider draws nothing either way, but this keeps the no-optic tree the tree
// it always was.
const BeatOptic: React.FC<{decl: OpticDecl; dna: DesignDNA | null; where: string; children: React.ReactNode}> = ({
  decl, dna, where, children}) => {
  if (decl === undefined && dnaOptics(dna) !== 'auto') return <>{children}</>;
  return <OpticContext.Provider value={opticState(decl, dna, where)}>{children}</OpticContext.Provider>;
};

export const Film: React.FC<{scenes?: SceneSpec[]; camera?: number; cameraBed?: boolean; autospace?: boolean; cjkDisplay?: string | null; reducedMotion?: boolean; theme?: Atmo; captions?: boolean; brand?: any; dna?: DesignDNA | null; template?: string; textSafe?: boolean;
  typeGlide?: boolean; typeSize?: boolean; typeCollisions?: boolean; titleProbe?: boolean; safe?: string;
  mediaRes?: boolean;
  // the delivery dither (runtime/dither): render_remotion asks for it; a still for a gate or a test does not
  dither?: boolean;
  // `safeEcho: false`: a platform-safe film's margin is its ground TOKEN only, without the register's own root ground drawn
  // a second time (SafeEcho) — the second rendering of every register is the cost it saves (meta.safe_echo: false).
  safeEcho?: boolean;
  // `frameUnlock: false` draws a platform-safe film's register frame without its own unlock (FrameUnlock) — the film
  // as it was before, for the proofs that the frame needs it. Never set by a film.
  frameUnlock?: boolean;
  // `optics: false` switches every beat's optic off — for scripts/determinism_qa.py's layer attribution and the
  // optics identity proofs. Never set by a film.
  optics?: boolean;
  // the film's drawing style (meta.style, runtime/styleSpec.ts) — null draws every register exactly as it is
  style?: StyleSpec | null;
  // a GENERATED medium's tiles for that style (render_remotion.style_texture_props); absent: the procedural medium
  styleTexture?: {light: string; dark: string} | null}> =
  ({scenes = WORKBUDDY_SCENES, camera = 0, cameraBed = true, autospace = false, cjkDisplay = null, reducedMotion = false, theme, captions = true, brand, dna, template, textSafe = false,
    typeGlide = false, typeSize = false, typeCollisions = false, titleProbe = false, mediaRes = false, safe, dither = false, optics = true,
    safeEcho = true, frameUnlock = true, style = null, styleTexture = null}) => {
  const activeStyle = React.useMemo(() => (style ? resolveStyle(style, styleTexture) : null), [style, styleTexture]);
  setStyleEase(activeStyle ? (activeStyle.motion as {easing?: string}).easing : null);
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const total = filmDuration(scenes);
  const safeP = safeProfile(safe, width, height);
  const regFrame = safeP ? registerFrame(width, height, safeP) : null;
  // NO SHAKE, structurally. `cameraTransform` is three sines with different periods on scale, x and y —
  // an OSCILLATION, which is why it was made opt-in and defaults to still after repeated complaints. A
  // beat's `pan` is monotone by construction (runtime/depth.tsx panAt: a ramp that only ever advances), so
  // a pan alone cannot shake. Travel PLUS oscillation can, and that combination is refused rather than
  // rendered: the two are different intentions and a film should pick one.
  const ambient = reducedMotion ? 0 : Math.max(0, camera);
  if (ambient > 0 && (scenes || []).some((s) => s && s.camera && s.camera.pan)) {
    throw new Error(
      'this film declares BOTH a whole-film camera drift (meta.camera_drift) and a per-beat camera pan. ' +
      'The drift oscillates and the pan travels; together they read as shake, which this project has ' +
      'already shipped once and had reported. Keep the per-beat pans and drop meta.camera_drift, or keep ' +
      'the drift and drop the pans.');
  }
  const unlockAllowed = React.useContext(BaselineUnlockContext);
  const cam = cameraTransform(frame, ambient, width, height, unlockAllowed);
  const intro = interpolate(frame, [0, 12], [1, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const outro = interpolate(frame, [total - 16, total - 1], [0, 1], {extrapolateLeft: 'clamp'});
  // ONE Design DNA for the whole film (null = un-themed → every shot renders its original hardcoded look).
  const baseDna = coerceDna(dna) ?? dnaFromTemplate(template) ?? null;   // an authored DNA may be partial — normalise it
  // the film's CJK display voice (runtime/cjkVoice) set into the TITLE stack only — body text and captions stay on Noto
  const activeDna = baseDna && cjkDisplay ? {...baseDna, fontDisplay: withCjkDisplay(baseDna.fontDisplay, cjkDisplay)}
    : baseDna;
  const bg = theme?.bg ?? activeDna?.bg ?? '#05060a';
  // THE GROUND EACH BEAT ACTUALLY PAINTS, at the frame the film tier needs it: 'in' = its first frame, 'out'
  // = its last. Those are the two frames a seam is really cutting between, and the two ends the intro/outro
  // veil has to match. A beat that declares nothing resolves to null and every caller falls back to the
  // film-wide DNA, which is what it read before this existed.
  const edgeGround = (sc: SceneSpec | undefined, edge: 'in' | 'out') => {
    if (!sc) return null;
    const d = Math.max(1, Math.round(sc.durF));
    return groundAt(activeDna, sc, edge === 'in' ? 0 : d - 1, d, sc.shot, reducedMotion);
  };
  // A beat may DESCRIBE its ground (`bgLum` — the hint the caption pick and the seam guard read) and also
  // COMMAND one (`ground`/`key` — which repaints). When the two disagree the film is telling itself two
  // stories and the one on screen is not the one the caption believes: exactly the staleness that put dark
  // ink on a dark themed ground. Refuse it here, once per frame over the whole EDL, rather than let a hint
  // quietly outvote the pixels. Checked in both directions (in/out) so a ramp cannot start honest and end wrong.
  scenes.forEach((sc, i) => {
    if (sc.warp) checkWarp(sc.warp, i, sc.shot);
    if (sc.cues) checkCues(sc.cues, i, sc.shot);
    // an optic is checked on every frame (normalizeOptic throws on an unknown kind or an intensity past its cap); a
    // LEAK burns over the seam INTO the beat, so a beat with no seam before it has nowhere to draw one
    const o = normalizeOptic(sc.optic, `scene ${i} (${sc.shot}) optic`);
    if (o && (i === 0 || joinedAt(scenes, i)) && o.kind === 'leak') {
      throw new Error(`scene ${i} (${sc.shot}) declares optic 'leak', which burns over the seam INTO a beat — and ` +
        `${i === 0 ? 'the first beat has no seam before it' : 'a beat that continues a stage run has no seam'}.`);
    }
    if (o && o.kind !== 'leak' && runOf(sc) !== null) {
      throw new Error(`scene ${i} (${sc.shot}) is on a stage run and declares optic '${o.kind}': a stage draws the whole ` +
        'run and anchors no optic. Drop it, or take the beat off the run.');
    }
  });
  scenes.forEach((sc, i) => {
    if (!sc.bgLum || (sc.ground === undefined && !sc.key)) return;
    for (const edge of ['in', 'out'] as const) {
      const g = edgeGround(sc, edge);
      if (g && lumFromY(g.y) !== sc.bgLum) {
        throw new Error(`scene ${i} (${sc.shot}) declares bgLum:'${sc.bgLum}' but the ground it paints at its ` +
          `${edge === 'in' ? 'first' : 'last'} frame is ${g.bg} (${lumFromY(g.y)}, Y=${g.y.toFixed(3)}). ` +
          'A description that disagrees with what is painted sends the caption ink and the seam guard to the ' +
          'wrong answer — drop the bgLum, or name the ground you meant.');
      }
    }
  });
  // The root fill and the intro/outro veil are the FIRST and LAST beat's grounds, not one film-wide colour.
  // A film that opens on paper used to fade in from the film's near-black — a flash of a ground the film
  // never shows, which is the same defect the atmosphere fix below was written for, one layer up.
  const firstBg = edgeGround(scenes[0], 'in')?.bg;
  const lastBg = edgeGround(scenes[scenes.length - 1], 'out')?.bg;
  const rootBg = theme?.bg ?? firstBg ?? bg;
  const veilBg = outro > intro ? (theme?.bg ?? lastBg ?? bg) : rootBg;

  const beatSeq = (sc: SceneSpec, i: number) => {
    const C = REGISTRY[sc.shot];
    const durF = Math.max(1, Math.round(sc.durF));
    const seq = (
      <TransitionSeries.Sequence key={`s${i}`} durationInFrames={durF}>
        <SceneDurationContext.Provider value={durF}>
          {/* THE BEAT'S OWN VOICE, offered to whatever wants to draw it. `<Audio>` below plays this same
              file; providing the path here is what lets an audio-reactive register analyse exactly what
              the viewer is hearing, with no prop the shot-director has to know about. A beat with no
              narration provides null and those registers fall back to their synthetic voice, which is
              also what a standalone still gets — see runtime/voice.tsx. */}
          <NarrationContext.Provider value={sc.mp3 ?? null}>
          {/* THE GROUND IS RESOLVED HERE, PER BEAT. This provider is the whole mechanism: the design
              DNA used to be provided once OUTSIDE the TransitionSeries, so `bg` was a film-wide
              constant and no beat could change the light. Providing it inside the Sequence — with
              this beat's ground over the film's system — re-grounds every register that reads those
              tokens, measured at 148 of 149, with no per-register edit. The outer provider is kept
              for the film-level furniture that sits outside every Sequence (caption HUD, motif,
              brand); this one shadows it for the beat. A beat that declares no ground provides the
              film DNA object itself, so this is a no-op and the frame is bit-for-bit unchanged. */}
          <BeatGround dna={activeDna} scene={sc} durF={durF} shot={sc.shot}>
            <WorldBackdrop place={sc.world} safe={safeP} />
            {/* the camera BED: a beat nobody authored a camera for drifts gently instead of sitting
                dead — see bedPan's header for the measurements and the guarantees. An authored camera
                (even 'hold') wins outright; un-themed films and drifting films get none. */}
            {/* a beat in a camera HAND-OFF is driven by its curves (HandoffCamera); every other beat by its own move */}
            <BeatCamera plan={camPlan[i]} phrase={sc.phrase} move={sc.camera?.move} amount={sc.camera?.amount}
              pan={sc.camera?.pan ?? (camPlan[i] ? undefined : bedPan(i, !!activeDna, ambient, sc.camera, cameraBed)?.pan)}
              bed={!sc.camera && !camPlan[i] && !!bedPan(i, !!activeDna, ambient, sc.camera, cameraBed)}
                         driftExtra={driftExtraFor(ambient, width, height, unlockAllowed)}
                         driftTranslate={(reducedMotion ? 0 : Math.max(0, camera)) * DRIFT_MAX_TRANSLATE_Y}>
              {/* `data-beat` marks THIS beat's register for the sync audit (scripts/sync_qa.py reads it from the
                  type census): the caption, the chrome and the other beat of a seam carry none of it. */}
              {/* on a platform-safe film the register is drawn in its scaled frame (runtime/safeZone): its own caption
                  band lands where the caption is, above the platform's UI, and nothing in it is re-laid-out */}
              {/* …and its edges dissolve into the beat's ground: a register that paints its own atmosphere showed the
                  scaled frame as a hard-edged panel */}
              {regFrame ? (
                <StyleLayer beat={i} skip={STYLE_HOOKS_BY_SHOT[sc.shot]}>
                <SafeEcho shot={sc.shot} rootGround={safeEcho}>
                  <CueContext.Provider value={sc.cues ? {at: sc.cues, warp: sc.warp ?? null} : null}>
                    <ObjectIdleContext.Provider value={sc.objectIdle !== false}>
                      <CarryContext.Provider value={arrived[i] ?? null}>
                        <BeatClock warp={sc.warp}>{C ? <C {...(sc.props ?? {})} /> : null}</BeatClock>
                      </CarryContext.Provider>
                    </ObjectIdleContext.Provider>
                  </CueContext.Provider>
                </SafeEcho>
                </StyleLayer>
              ) : null}
              <AbsoluteFill data-beat={String(i)} style={regFrame ? {transformOrigin: '0 0',
                transform: `translate(${regFrame.x0}px, ${regFrame.y0}px) scale(${regFrame.k})`,
                WebkitMaskImage: SAFE_FRAME_MASK, maskImage: SAFE_FRAME_MASK,
                WebkitMaskComposite: 'source-in', maskComposite: 'intersect'} : undefined}>
                <FrameUnlock k={regFrame ? regFrame.k : 1} on={Boolean(regFrame) && frameUnlock && !reducedMotion}>
                <CueContext.Provider value={sc.cues ? {at: sc.cues, warp: sc.warp ?? null} : null}>
                  <ObjectIdleContext.Provider value={sc.objectIdle !== false}>
                    {/* the anchor a container carried INTO this beat, which the register then draws in place */}
                    <CarryContext.Provider value={arrived[i] ?? null}>
                      <BeatOptic decl={optics ? sc.optic : undefined} dna={activeDna} where={`scene ${i} (${sc.shot}) optic`}>
                        <StyleLayer beat={i} skip={STYLE_HOOKS_BY_SHOT[sc.shot]}>
                          <FocusLayer plan={sc.focus} items={sc.focusItems}>
                            <BeatClock warp={sc.warp}>{C ? <C {...(sc.props ?? {})} /> : <Missing id={sc.shot} />}</BeatClock>
                          </FocusLayer>
                        </StyleLayer>
                      </BeatOptic>
                    </CarryContext.Provider>
                  </ObjectIdleContext.Provider>
                </CueContext.Provider>
                </FrameUnlock>
              </AbsoluteFill>
            </BeatCamera>
            <BeatChrome chrome={sc.chrome} W={width} H={height} />
          </BeatGround>
          </NarrationContext.Provider>
        </SceneDurationContext.Provider>
        {sc.mp3 ? <BeatAudio src={sc.mp3} /> : null}
      </TransitionSeries.Sequence>
    );
    return seq;
  };
  // A STAGE RUN: one Sequence over all its beats (no seam inside), one stage component drawing them, each beat's voice
  // placed at the beat's own start. The run takes its ground from its first beat (scripts/stage_runs.py refuses a
  // ground declared later in the run) and moves its own camera, so no per-beat camera wraps it.
  const runSeq = (first: number, last: number) => {
    const runScenes = scenes.slice(first, last + 1);
    const durs = runScenes.map((x) => Math.max(1, Math.round(x.durF)));
    const offs: number[] = [];
    durs.reduce((acc, d) => { offs.push(acc); return acc + d; }, 0);
    const runDur = durs.reduce((a, d) => a + d, 0);
    const head = runScenes[0];
    const S = STAGES[head.shot];
    const beats: StageBeat[] = runScenes.map((x, k) => ({index: first + k, start: offs[k], durF: durs[k],
      props: (x.props ?? {}) as Record<string, unknown>, cues: x.cues, caption: x.caption}));
    return (
      <TransitionSeries.Sequence key={`r${first}`} durationInFrames={runDur}>
        <SceneDurationContext.Provider value={runDur}>
          <BeatGround dna={activeDna} scene={head} durF={runDur} shot={head.shot}>
            <StageBeatMark first={first} beats={beats}>
              <StageRunContext.Provider value={{run: runOf(head) ?? '', beats, runDur}}>
                {/* a stage lays itself out in the platform-safe area directly (runtime/safeZone) */}
                <SafeZoneContext.Provider value={safeP}>
                  <CarryContext.Provider value={arrived[first] ?? null}>
                    {S ? <S {...(head.props ?? {})} /> : <Missing id={head.shot} />}
                  </CarryContext.Provider>
                </SafeZoneContext.Provider>
              </StageRunContext.Provider>
            </StageBeatMark>
          </BeatGround>
        </SceneDurationContext.Provider>
        {runScenes.map((x, k) => (x.mp3 ? (
          <Sequence key={`a${k}`} from={offs[k]} durationInFrames={durs[k]}><BeatAudio src={x.mp3} /></Sequence>
        ) : null))}
      </TransitionSeries.Sequence>
    );
  };
  const units: {first: number; last: number; run: boolean}[] = [];
  scenes.forEach((sc, i) => {
    if (joinedAt(scenes, i)) units[units.length - 1].last = i;
    else units.push({first: i, last: i, run: runOf(sc) !== null});
  });
  // the grounds a cut sits between, and the anchor a CONTAINER cut carries into the beat after it — read from the
  // seam the cut actually draws (seamDrawn), so a container the guard turned into a fade carries nothing in
  const cutGrounds = (a: SceneSpec, b: SceneSpec) =>
    [edgeGround(a, 'out') ?? activeDna, edgeGround(b, 'in') ?? activeDna] as const;
  const arrived: (string | null)[] = scenes.map(() => null);
  // the seams a LEAK burns over: the seam INTO a unit whose first beat declares one (runtime/optics SeamLeak) — read
  // from that beat, which is the segment's own `cur` (remotion_segments.plan), so the per-beat cache keys it
  const leaks: {first: number; optic: OpticSpec}[] = [];
  units.forEach((u, ui) => {
    if (ui === 0) return;
    const prev = scenes[units[ui - 1].last], next = scenes[u.first];
    const lo = optics && !reducedMotion ? normalizeOptic(next.optic) : null;   // a flash is no reduced-motion frame
    if (lo && lo.kind === 'leak') leaks.push({first: u.first, optic: lo});
    const [pg, ng] = cutGrounds(prev, next);
    if (seamDrawn(prev, next, activeDna, pg, ng, reducedMotion).t === 'container') {
      arrived[u.first] = carryIds(next.transitionIn)?.to ?? null;
    }
  });
  // the frames a CONTAINER seam is on screen (the film layer is isolated for them — see the AbsoluteFill below)
  const filmStarts = sceneStarts(scenes);
  const inContainer = units.some((u, ui) => ui > 0 && seamDrawn(scenes[units[ui - 1].last], scenes[u.first], activeDna,
    ...cutGrounds(scenes[units[ui - 1].last], scenes[u.first]), reducedMotion).t === 'container'
    && frame >= filmStarts[u.first] && frame < filmStarts[u.first] + TR);
  // THE HAND-OFFS (see HandoffCamera): which beat runs its move into its cut, and what the next beat inherits
  const driftX = driftExtraFor(ambient, width, height, unlockAllowed), driftT = ambient * DRIFT_MAX_TRANSLATE_Y;
  const camPlan: (CamPlan | null)[] = scenes.map(() => null);
  units.forEach((u, ui) => {
    const a = scenes[u.last];
    if (!a.camera?.handoff) return;
    const where = `scene ${u.last} (${a.shot}) hands its camera off`;
    const move = a.camera.move;
    if (move !== 'push' && move !== 'pull') {
      throw new Error(`${where}, but its move is ${JSON.stringify(move)} — only a push or a pull has a velocity to hand on.`);
    }
    if (a.camera.pan) throw new Error(`${where} and also pans — one camera channel per beat; drop the pan or the hand-off.`);
    if (u.run || ui === units.length - 1) {
      throw new Error(`${where}, but ${u.run ? 'it is a stage run, which moves its own camera' : 'it is the last beat'}.`);
    }
    const nu = units[ui + 1], b = scenes[nu.first];
    if (nu.run) throw new Error(`${where} into a stage run, which moves its own camera.`);
    if (b.camera) {
      throw new Error(`${where} into scene ${nu.first} (${b.shot}), which declares a camera of its own — one channel per ` +
        'beat: the inheriting beat moves with what it is handed, so drop its camera.');
    }
    if (reducedMotion) return;
    const bA = cameraBudget({W: width, H: height, move, amount: a.camera.amount, driftExtra: driftX, driftTranslate: driftT,
      unlockAllowed});
    const durA = Math.max(1, Math.round(a.durF));
    const {v} = handoffOut(durA - 1, durA, bA.amp, move);
    // the RELATIVE zoom rate on screen at A's last frame, re-expressed on B's own scale (its unlock overscan)
    const rel = v / (1 + bA.unlock + (move === 'push' ? bA.amp : 0));
    const bB = cameraBudget({W: width, H: height, driven: true, driftExtra: driftX, driftTranslate: driftT, unlockAllowed});
    camPlan[u.last] = {...(camPlan[u.last] ?? {}), out: {amp: bA.amp, move}};
    camPlan[nu.first] = {...(camPlan[nu.first] ?? {}),
      in: {rate: (move === 'push' ? 1 : -1) * rel * (1 + bB.unlock), limit: bB.cap - bB.unlock}};
  });
  return (
    <AbsoluteFill style={{backgroundColor: rootBg}}>
      {/* Opt-in DOM audit — inert without the prop. Mounted on the FILM as well as on each shot preview so
          the caption HUD and the film's own furniture are audited too, not only the registers. */}
      {/* The same questions a register's preview can be asked (Root.tsx DnaPreview) — a stage run cannot render alone,
          so the per-beat gates ask them of the FILM's frames of it (scripts/stage_frames.py). */}
      <TextSafeAudit enabled={Boolean(textSafe || typeCollisions)} mode={typeCollisions ? 'collisions' : 'safe'}
                     typeSize={Boolean(typeSize)} />
      {titleProbe ? <TitleProbe /> : null}
      {/* The type-glide census (runtime/textSafe.tsx): per frame, every line of type that can snap, with its true
          position — read across frames by scripts/text_safe_qa.py --glide. Absent unless asked for. */}
      {typeGlide ? <TypeGlideAudit /> : null}
      {/* The media-resolution census (runtime/mediaRes.tsx): per frame, every raster and how far it is magnified
          past its own pixels — judged by scripts/media_res_qa.py. Absent unless asked for. */}
      {mediaRes ? <MediaResAudit /> : null}
      <DesignDNAContext.Provider value={activeDna}>
      <StyleContext.Provider value={activeStyle}>
      {/* THE ATMOSPHERE MUST BELONG TO THIS FILM. With no explicit `theme` it fell back to its own
          defaults — a near-black field with a cyan/violet dot lattice, the palette of the MRI films this
          component was written for. On a cream survey film that is another film's world sitting under
          every frame, invisible only because the shots above it are opaque. The moment anything went
          transparent it appeared: the `carry` seam at the closing cut measured mean luminance 226 -> 14
          -> 229 in a third of a second, a black flash of a palette this film has never used. A themed
          film now derives its atmosphere from its own DNA, so there is nothing foreign to reveal. */}
      <Atmosphere
        {...(theme ?? (activeDna
          ? {bg: activeDna.bg, accent: activeDna.accent, accent2: activeDna.accent2, motif: 'plain' as const}
          : {}))}
        intensity={reducedMotion ? 0.55 : (theme?.intensity ?? 1)} />
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
      {/* THE GAP BETWEEN HAN AND LATIN OR DIGITS, set by the browser (Chrome's text-autospace): 手机的GPS reads 手机的 GPS
          without the author typing the space — about an eighth of an em, the spacing W3C's Chinese layout requirements
          (clreq) ask for between Han and Western letters and numerals. `normal` is the only value this Chrome accepts
          (measured: `ideograph-alpha` is refused, and a refused value silently does nothing). On the beats only — the
          caption sits outside .dna-film, and its lines are broken by a canvas measure that knows nothing of the gap.
          `autospace: false` (meta.cjk_autospace) leaves it out. */}
      {autospace ? <style>{`.dna-film { text-autospace: normal; }`}</style> : null}
      {/* ISOLATED WHILE A CONTAINER IS ON SCREEN, and only then: a container's copy is lifted over both beats with a
          z-index (seams.tsx), and without a stacking context of its own here it would rise over the caption and the
          finish too. Every other frame carries no isolation, so it draws exactly what it drew before. */}
      <AbsoluteFill className="dna-film" style={cam === 'none' ? (inContainer ? {isolation: 'isolate'} : undefined)
        : {transform: cam, ...(inContainer ? {isolation: 'isolate' as const} : {})}}>
      <TransitionSeries>
        {units.flatMap((u, ui) => {
          // ONE UNIT is a single beat — rendered exactly as before stage runs existed — or a whole stage run
          const seq = u.run ? runSeq(u.first, u.last) : beatSeq(scenes[u.first], u.first);
          if (ui === units.length - 1) return [seq];
          const sc = scenes[u.last], next = scenes[units[ui + 1].first];
          return [seq, (
            <TransitionSeries.Transition key={`t${u.last}`}
              presentation={pickPresentation(sc, next, width, height, activeDna,
                ...cutGrounds(sc, next), reducedMotion, `t${u.last}`,
                scenes.slice(u.first, u.last + 1).reduce((a, x) => a + Math.max(1, Math.round(x.durF)), 0))}
              timing={linearTiming({durationInFrames: TR})} />
          )];
        })}
      </TransitionSeries>
      </AbsoluteFill>
      {/* THE LEAK is in the lens, not the scene: outside the camera layer, above both beats of its seam, below the
          material, the finish and the caption. Nothing is mounted on a frame outside a leaking seam. */}
      {leaks.map(({first, optic}) => {
        const f = frame - filmStarts[first];
        return f >= 0 && f < TR
          ? <SeamLeak key={`leak${first}`} optic={optic} f={f} seam={TR} light={dnaLight(activeDna)} /> : null;
      })}
      </ReducedMotionContext.Provider>
      {/* the film's MATERIAL — above the shots (each paints its own opaque ground) and below the caption,
          so it never competes with the words the viewer is reading */}
      <FilmMotifLayer motif={activeDna?.motif as any} dna={activeDna} W={width} H={height} />
      {/* the film's OPTICS — grain, corner falloff, a key direction — above the material, below the caption:
          grain over burned type reads as compression, and the caption's contrast maths assume the ground it
          measured. Static by construction (runtime/finish.tsx), so nothing here can pump or drift. */}
      <FilmFinishLayer dna={activeDna} />
      <AbsoluteFill style={{backgroundColor: veilBg, opacity: Math.max(intro, outro), pointerEvents: 'none'}} />
      {captions ? <CaptionTrack scenes={scenes} groundBg={theme?.bg ?? activeDna?.bg} dna={activeDna} dnaFontBody={activeDna?.fontBody} dnaUniform={activeDna?.uniformType} reduced={reducedMotion} safe={safeP} /> : null}
      <BrandMark brand={brand} safe={safeP} />
      {dither ? <FilmDither /> : null}
      </StyleContext.Provider>
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default Film;
