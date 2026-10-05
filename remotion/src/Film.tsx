// FILM · data-driven — sequences any list of bespoke shots into a narrated film. Each SCENE names a `shot`
// (looked up in REGISTRY), its topic `props`, a frame-length `durF`, an optional narration `mp3` (served from
// public/) and a `caption`. Scenes CROSS-DISSOLVE (overlapping ~0.4s to ride the narration breath). Captions
// ride a SINGLE top-level HUD track (a #hud sibling, per huashu's camera-rig discipline) that HARD-CUTS one
// caption at a time inside each scene's sole-visible window — so two captions can never overlap across a
// transition (the old A1 doubling bug) — and picks its ink CONTRAST against the scene's ground luminance.
// render_remotion.py drives this via --props; the WorkBuddy film is just the default. Deterministic.

import React from 'react';
import {AbsoluteFill, Audio, Freeze, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {captionBand, CAPTION_SIZE_FRAC, CAPTION_MARGIN_FRAC, CAPTION_LINES,
        CAPTION_LEAD, CAPTION_LEAD_CJK, cjkAdvance, latinAdvance,
        CONTENT_TOP, contentBottom} from './runtime/layout';
import {SceneDurationContext, ReducedMotionContext, clamp01, SEAM_FRAMES,
        easeOutCubic} from './runtime/motion';
import {NarrationContext} from './runtime/voice';
import {groundLum, dnaGroundLum, dnaGroundY, groundGap, HARSH_GROUND_GAP, lumValue, lumFromY,
        type Lum, type GroundColors} from './runtime/shotLuma';
import {BeatGround, groundAt, captionInk, hexGround, LIGHT_KEY_Y, CAPTION_INK_DARK, CAPTION_INK_LIGHT,
        type SceneGroundDecl} from './runtime/light';
import {Atmosphere, type Atmo} from './runtime/atmosphere';
import {SceneCamera, bedPan, type CameraMove} from './runtime/depth';
import {BASELINE_UNLOCK, BaselineUnlockContext, unlockCoverScale, useGlide} from './runtime/glide';
import {DesignDNAContext, type DesignDNA, dnaFromTemplate, coerceDna, TerminalChrome} from './runtime/dna';
import {REGISTRY} from './registry';
import {TextSafeAudit, TypeGlideAudit} from './runtime/textSafe';
import {CAPTIONS} from './captions';
import {FilmMotifLayer} from './runtime/motif';
import {FilmFinishLayer} from './runtime/finish';

// The scene EDL. `bgLum` is the first of the shot-director-emitted continuity fields (an explicit ground-
// luminance override; falls back to the measured shotLuma map). Future phases grow this schema (accent,
// camera{}, carry{}, transitionIn{}, audioCues[]) — all OPTIONAL + remotion-only, so the html tier is untouched.
export type SceneSpec = SceneGroundDecl & {shot: string; props?: Record<string, unknown>; durF: number; mp3?: string;
  // `bgLum` DESCRIBES the ground this beat paints (a hint for the caption ink and the seam guard); the
  // `ground` / `key` fields it now sits beside COMMAND one (they repaint the frame — runtime/light.tsx).
  // Both are kept and the Film refuses a beat that declares two disagreeing answers, because a hint that
  // silently becomes a command is how `bgLum:'light'` came to mean "a still-dark frame".
  caption?: string; bgLum?: Lum;
  // THE VOICE'S OWN WORD TIMES, as character ranges into `caption` (scripts/cues.word_spans). Ranges rather
  // than word indices because this tier re-chunks the caption to fit its band, and an index into "word 3 of
  // chunk 2" means something different after every re-wrap while an offset into the string does not.
  capWords?: {t: number; a: number; b: number}[];
  // TERMINAL CHROME per scene (remotion + DNA only): a command-path + status readout the Film frames every beat
  // with (see runtime/dna.tsx TerminalChrome). Optional; inert unless the active DNA speaks 'breadcrumb'.
  chrome?: {path?: string; status?: string; root?: string};
  // A MARKED seam (chapter break): the transition INTO this scene from the previous one. Optional +
  // remotion-only; unset = the luminance-safe default (a gentle cross-fade). A kinetic type is honored only
  // on a same/near-luminance seam — across a dark↔light gap it's suppressed back to fade (see pickPresentation).
  transitionIn?: {type: 'fade' | 'slide' | 'push' | 'lift' | 'wipe' | 'clock' | 'dissolve' | 'fadethrough'
    | 'drift' | 'blur' | 'carry' | 'focus' | 'through-dark' | 'portal' | 'return'; direction?: string;
    /** `return` only: the pan across the film's board, as fractions of the frame's LONG side. Computed by
     *  `scripts/film_board.py`, which is the one place that knows where two beats sit. */
    dx?: number; dy?: number};
  // A MOTIVATED camera move for THIS beat: `push` (look closer at what is here), `pull` (here is the whole
  // of it), `hold` (most beats). Optional; absent = hold. This is not the film-wide ambient drift below —
  // that one had no relationship to anything being said, which is precisely why it read as a wobble.
  camera?: {move?: CameraMove; amount?: number; pan?: [number, number]};
  // THE BEAT'S CLOCK, WARPED ONTO ITS VOICE. Knots [[film frame, register frame], ...] on the beat's own clock,
  // strictly increasing in both: the register is handed `warpFrame(frame, warp)` instead of `frame`, so an
  // entrance it times as a fixed fraction of the beat lands on the word that names it — with no register file
  // touched. Derived by scripts/sync_qa.py from the type census of the un-warped film (render_remotion does it
  // before a render); absent = the register's own clock, and the beat renders exactly as it did before.
  warp?: [number, number][]};

/** The register frame a beat with knots `warp` sees at its film frame `f`: piecewise linear between knots, the
 *  identity outside them (the seams' held edges are never warped). Mirrors scripts/sync_qa.py `warp_frame`. */
export const warpFrame = (f: number, warp?: [number, number][] | null): number => {
  if (!warp || warp.length < 2 || f <= warp[0][0] || f >= warp[warp.length - 1][0]) return f;
  for (let k = 1; k < warp.length; k++) {
    const [f0, g0] = warp[k - 1];
    const [f1, g1] = warp[k];
    if (f <= f1) return g0 + ((g1 - g0) * (f - f0)) / (f1 - f0);
  }
  return f;
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
const BeatClock: React.FC<{warp?: [number, number][]; children: React.ReactNode}> = ({warp, children}) => {
  const frame = useCurrentFrame();
  if (!warp || warp.length < 2) return <>{children}</>;
  return <Freeze frame={warpFrame(frame, warp)}>{children}</Freeze>;
};

const TR = SEAM_FRAMES; // cross-dissolve length (frames) — rides the ~0.42s narration breath so speech barely
// overlaps. Shared with runtime/motion's useT, which holds each shot STILL for exactly these frames at both
// edges so a dissolve never runs over a moving shot.
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
  12: {type: 'carry'},                            // ChartLive → HandDrawn: the figure is carried into the human takeaway (crosses dark→light). No trend line: the 68× is one sourced number, and ChartLive draws a line only from a `series` it is given
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
  // A DECIMAL POINT is not a sentence end. The splitter treats `.` as a terminator, so "19.3 到 28.9%"
  // broke into "19." / "3 到 28." / "9%。" and the caption on screen read 「pass@k 最多掉 19.」 — a
  // number cut in half, on the beat carrying the film's headline figure. Shield digit-dot-digit behind a
  // sentinel for the split, then restore it. Applies to any figure: 0.833, 2.39, 19.3.
  const DEC = '\u0000';
  const guarded = text.replace(/(\d)\.(\d)/g, `$1${DEC}$2`);
  const chunks = guarded.match(/[^.!?。！？—]+[.!?。！？]?(\s*—)?/g)
    ?.map((c) => c.trim().split(DEC).join('.')).filter(Boolean) ?? [text];
  const merged: string[] = [];
  for (const c of chunks) {
    const prev = merged[merged.length - 1];
    if (prev && !isCJKText(c) && !isCJKText(prev) && (prev.length < 22 || c.length < 22)) merged[merged.length - 1] += ' ' + c;
    else merged.push(c);
  }
  return merged;
};

// FIT THE CAPTION TO THE BAND IT WAS GIVEN — not the other way round.
//
// The band reserves CAPTION_LINES lines. A single long SENTENCE is one chunk however long it is, so a
// 100-character line wrapped to THREE lines, overflowed the two-line reserve, and climbed into the picture:
// a delivered frame had the caption printed straight through the shot's own subtitle. Widening the measure
// alone does not fix it, because there is always a longer sentence.
//
// So an over-long chunk is split at its best CLAUSE boundary (comma / semicolon / dash — a place a reader
// already pauses), nearest the middle so neither half is a scrap. Capacity is estimated from the type size
// and the measure: Latin advance averages ~0.52em, CJK is monospaced at 1em. The estimate is calibrated
// against real renders — a 100-char Latin caption at 56px in a 1400px measure is predicted 3 lines and
// rendered 3 lines. Deterministic, and it degrades to the original chunk when there is no boundary to cut on.
// THE ADVANCE BELONGS TO THE FONT, not to one font. Both estimates below were calibrated on Inter and
// then applied to whatever face the film's DNA supplies. Measured on this renderer at 56px: this film's
// IBM Plex Sans averages 0.452-0.478 em on real prose — so 0.52 is conservative and safe — but the
// `terminal` DNA sets ALL type to JetBrains Mono, where the same sentence measures 0.588. There the
// estimate UNDER-counts, the caption wraps to more lines than the fit assumed, and it overflows the band
// it was supposed to be guaranteed to fit. CJK measures 0.995 in a PROPORTIONAL face, so 1.0 was right for
// the faces this was written against — and wrong for a terminal DNA, whose caption is set in the mono
// stack, where a Han glyph is two cells. `cjkAdvance` asks the face, exactly as `latinAdvance` does.
const advanceFor = (text: string, fontStack?: string, uniform?: boolean): number =>
  isCJKText(text) ? cjkAdvance(fontStack, uniform) : latinAdvance(fontStack, uniform);

const CLAUSE = /[,;，；、]|\s—\s/g;
const fitCaption = (chunks: string[], size: number, measure: number, lines: number,
                    fontStack?: string, uniform?: boolean): string[] => {
  const out: string[] = [];
  const cap = (t: string) => Math.max(8, Math.floor(measure / (size * advanceFor(t, fontStack, uniform))));
  const split = (t: string, depth: number): void => {
    const budget = cap(t) * lines;
    if (t.length <= budget || depth > 2) { out.push(t); return; }
    const mid = t.length / 2;
    let best = -1;
    CLAUSE.lastIndex = 0;
    for (let m = CLAUSE.exec(t); m; m = CLAUSE.exec(t)) {
      // A SEPARATOR INSIDE A NUMBER IS NOT A CLAUSE BOUNDARY. `378,140` and `19.3` carry a thousands
      // separator and a decimal point, and cutting there guillotines the figure across two lines —
      // "the register today counts 378," / "140 residents". This is the same defect as the one already
      // guarded in splitCaption above, reproduced here because the two functions scan for different
      // things and only one of them knew. A digit on both sides means it belongs to the number.
      if (/\d/.test(t[m.index - 1] ?? '') && /\d/.test(t[m.index + m[0].length] ?? '')) continue;
      const at = m.index + m[0].length;
      if (at > 4 && at < t.length - 4 && (best < 0 || Math.abs(at - mid) < Math.abs(best - mid))) best = at;
    }
    if (best < 0) { out.push(t); return; }          // nothing to cut on — better one long chunk than a word sliced
    split(t.slice(0, best).trim(), depth + 1);
    split(t.slice(best).trim(), depth + 1);
  };
  chunks.forEach((c) => split(c, 0));
  return out;
};

const CAP_PAD = 4;   // clean-gap frames inside each scene's sole-visible window → guarantees exit-before-enter
const CAP_PAD_X = 60; // the caption block's own side padding, inside its measure (border-box)
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
  reduced?: boolean}> = ({scenes, groundBg, dna, dnaFontBody, dnaUniform, reduced}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  // The caption used to be a flat 44px whatever the frame was: at 9:16 — where the frame is only 1080 wide —
  // the same 44px is proportionally half again as large. It is sized off the NARROW dimension now.
  //
  // It was then set a notch SMALLER to answer "subtitle is too close to the content", which worked (a shorter
  // bottom-anchored block starts lower) but bought the gap with legibility: measured on a delivered frame the
  // caption was 37px of ink, 3.4% of frame height, against a 5.2% floor for a 1080p film watched in a
  // phone-sized window. The gap is paid for out of the reserved BAND now instead of out of the type.
  const capSize = Math.round(Math.min(width, height) * CAPTION_SIZE_FRAC);
  const capMargin = Math.round(Math.min(width, height) * CAPTION_MARGIN_FRAC);
  let acc = 0;
  const starts = scenes.map((sc) => { const s = acc; acc += Math.max(1, Math.round(sc.durF)) - TR; return s; });
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
    const a = starts[i] + (i > 0 ? half : 14);
    const b = starts[i] + dur - (i < scenes.length - 1 ? TR - half : 16);
    if (frame >= a && frame <= b) { active = i; ws = a; we = b; break; }
  }
  const sc = active >= 0 ? scenes[active] : undefined;
  if (!sc || !sc.caption) return null;
  // the measure the caption actually wraps in — must match the <div> below, or the fit is estimated against
  // a width the browser never used. The block is `capMeasure` wide border to border and its text wraps
  // INSIDE its side padding, so the lines are `capMeasure - 2 * CAP_PAD_X` long: fitted against the whole
  // block, a 68-glyph Chinese sentence passed as two lines of 35 and the browser set it in three lines of 32,
  // the third climbing out of the band onto the shot's own words.
  const capMeasure = Math.min(1600, width - 120);
  const capTextW = capMeasure - 2 * CAP_PAD_X;
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
      lit = spoken[k].b;
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
  const beatY = beatG ? (dnaGroundY(sc.shot, beatG) ?? beatG.y) : dnaGroundY(sc.shot, dna);
  const lum = dnaGroundLum(sc.shot, sc.bgLum, dna);
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
  const cjkChars = (capText.match(/[\u3040-\u9fff\uac00-\ud7af]/g) ?? []).length;
  const isCJK = cjkChars * 2 >= capText.length && cjkChars > 0;
  const capLead = isCJK ? CAPTION_LEAD_CJK : CAPTION_LEAD;
  const capTrack = isCJK ? '0' : '-0.01em';
  // THE CAPTION FITS THE BAND IT WAS GIVEN. The band is a static reserve every shot lays out against, and it
  // is sized on the LATIN leading — a shot cannot know what language will be spoken over it. CJK sets at 1.7
  // leading, so the identical two-line caption is 231px against a 227px reserve, and in portrait 326 against
  // 298: the subtitle climbs into the picture on every CJK film. Growing the band for the worst case would
  // take that space from every Latin film instead, so the CAPTION yields — its size is capped at whatever
  // fits, which is a guarantee rather than an estimate and holds for any language, length and aspect. In the
  // ordinary Latin two-line case the cap is well above the ideal size and nothing changes.
  const capBand = captionBand(width, height);
  const perLine = Math.max(8, Math.floor(capTextW / (capSize * advanceFor(capText, dnaFontBody, dnaUniform))));
  const capLines = Math.max(1, Math.ceil(capText.length / perLine));
  const fitSize = Math.max(12, Math.min(capSize, Math.floor((capBand - capMargin) / (capLead * capLines))));
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'relative', maxWidth: capMeasure, boxSizing: 'border-box', margin: `0 auto ${capMargin}px`,
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
        {lit < 0 ? capText : (() => {
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
    <SeamGround bg={passedProps?.bg} show={!isEnter}
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
  return <SeamGround bg={passedProps?.bg} show={!isEnter} style={{opacity: op}}>{children}</SeamGround>;
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
const ReturnPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const c = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const isEnter = presentationDirection === 'entering';
  // EACH AXIS SCALES BY ITS OWN DIMENSION, so the two halves tile at every aspect. Against the long side
  // they tile only at 16:9; at 9:16 a horizontal return would overshoot by the whole difference and open
  // the band this seam was rebuilt to close.
  const vx = (passedProps?.dx ?? 0) * (passedProps?.W ?? 1920);
  const vy = (passedProps?.dy ?? 0) * (passedProps?.H ?? 1080);
  // both halves move by the SAME vector in the same direction; the arriving beat simply starts a whole
  // vector behind, which is where it sits on the board relative to the one being left
  // ONE ramp, shared: the leaving half runs 0 -> 1 of the vector and the arriving half -1 -> 0, so at every
  // instant they are exactly one vector apart and travelling together. Linear, like every other seam here —
  // the timing curve belongs to `linearTiming`, not to each presentation.
  const kk = isEnter ? interpolate(p, [0, 1], [-1, 0], c) : interpolate(p, [0, 1], [0, 1], c);
  // AND NO CROSS-FADE. A pan does not dissolve; it moves. Measured on the first build, which faded both
  // halves over [0.18, 0.82] the way `drift` does: at a quarter through the seam the arriving beat was at
  // 10% opacity, so the strip it occupied showed bare ground and the frame read left-edge 9.5 against a
  // centre of 74.6 — a hard dark band sweeping across, which is a curtain and not a camera. Both halves
  // stay fully opaque and the offsets tile, exactly as `slide` does, so every pixel is always covered by
  // one beat or the other.
  const t = `translate(${(vx * kk).toFixed(2)}px, ${(vy * kk).toFixed(2)}px)`;
  const glide = useGlide();
  return <SeamGround bg={passedProps?.bg} show={!isEnter} style={{transform: glide(t, true)}}>{children}</SeamGround>;
};
const travelBack = (dx: number, dy: number, W: number, H: number, bg?: string): TransitionPresentation<any> =>
  ({component: ReturnPresentation, props: {dx, dy, W, H, bg}});

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
  return <SeamGround bg={passedProps?.bg} show={!isEnter} style={{opacity: op, transform: glide(t, true)}}>{children}</SeamGround>;
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
    <SeamGround bg={passedProps?.bg} show={!isEnter}
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
    if (d === 'slide') return slide({direction: (dir as any) ?? 'from-right'});
    if (d === 'wipe') return wipe({direction: (dir as any) ?? 'from-bottom'});
    if (d === 'clock') return clockWipe({width: W, height: H});
    if (d === 'dissolve') return fade();
  }
  if (dna.seam?.type === 'fade') return null;      // an explicit, deliberate plain cut
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
const pickPresentation = (prev: SceneSpec, next: SceneSpec, W: number, H: number, dna: DesignDNA | null,
                          prevG: GroundColors | null, nextG: GroundColors | null,
                          reducedMotion = false): TransitionPresentation<any> => {
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
  const dLum = Math.abs(LUM_RANK[dnaGroundLum(next.shot, next.bgLum, nextG)] - LUM_RANK[dnaGroundLum(prev.shot, prev.bgLum, prevG)]);
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
  const CANNOT_FLASH = new Set(['carry', 'focus', 'through-dark', 'drift', 'blur']);
  const t = (harsh && !CANNOT_FLASH.has(want)) ? 'fade' : want;
  const dir = next.transitionIn?.direction;
  // The seams that fade their LEAVING half need a floor to fade onto. `carry` already asked for this ground
  // by name; the others took whatever was behind the sequences, which is black.
  const seamBg = nextG?.bg ?? prevG?.bg ?? undefined;
  // MOTION GRAMMAR: an UNMARKED (default) seam becomes the DNA's native action on a luminance-safe cut (a themed
  // film's cuts belong to its world — terminal = screen-clear, etc.); explicit marks + the dark↔light fade win.
  if (t === 'fade' && !harsh) { const s = dnaDefaultSeam(dna, W, H); if (s) return s; }
  switch (t) {
    // One relation, one word, on both tiers: `push` is Remotion's own slide (the incoming page pushes the
    // outgoing one off), and `lift` is that move turned through 90° — a reading-flow progression down a page.
    case 'slide': case 'push': return slide({direction: (dir as any) ?? 'from-right'});
    case 'lift': return slide({direction: (dir as any) ?? 'from-bottom'});
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
    default: return fade();
  }
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

export const Film: React.FC<{scenes?: SceneSpec[]; camera?: number; cameraBed?: boolean; reducedMotion?: boolean; theme?: Atmo; captions?: boolean; brand?: any; dna?: DesignDNA | null; template?: string; textSafe?: boolean;
  typeGlide?: boolean}> =
  ({scenes = WORKBUDDY_SCENES, camera = 0, cameraBed = true, reducedMotion = false, theme, captions = true, brand, dna, template, textSafe = false,
    typeGlide = false}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const total = filmDuration(scenes);
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
  const activeDna = coerceDna(dna) ?? dnaFromTemplate(template) ?? null;   // an authored DNA may be partial — normalise it
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
  scenes.forEach((sc, i) => { if (sc.warp) checkWarp(sc.warp, i, sc.shot); });
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

  return (
    <AbsoluteFill style={{backgroundColor: rootBg}}>
      {/* Opt-in DOM audit — inert without the prop. Mounted on the FILM as well as on each shot preview so
          the caption HUD and the film's own furniture are audited too, not only the registers. */}
      <TextSafeAudit enabled={Boolean(textSafe)} />
      {/* The type-glide census (runtime/textSafe.tsx): per frame, every line of type that can snap, with its true
          position — read across frames by scripts/text_safe_qa.py --glide. Absent unless asked for. */}
      {typeGlide ? <TypeGlideAudit /> : null}
      <DesignDNAContext.Provider value={activeDna}>
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
      <AbsoluteFill className="dna-film" style={cam === 'none' ? undefined : {transform: cam}}>
      <TransitionSeries>
        {scenes.flatMap((sc, i) => {
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
                  {/* the camera BED: a beat nobody authored a camera for drifts gently instead of sitting
                      dead — see bedPan's header for the measurements and the guarantees. An authored camera
                      (even 'hold') wins outright; un-themed films and drifting films get none. */}
                  <SceneCamera move={sc.camera?.move} amount={sc.camera?.amount}
                    pan={sc.camera?.pan ?? bedPan(i, !!activeDna, ambient, sc.camera, cameraBed)?.pan}
                    bed={!sc.camera && !!bedPan(i, !!activeDna, ambient, sc.camera, cameraBed)}
                               driftExtra={driftExtraFor(ambient, width, height, unlockAllowed)}
                               driftTranslate={(reducedMotion ? 0 : Math.max(0, camera)) * DRIFT_MAX_TRANSLATE_Y}>
                    {/* `data-beat` marks THIS beat's register for the sync audit (scripts/sync_qa.py reads it from the
                        type census): the caption, the chrome and the other beat of a seam carry none of it. */}
                    <AbsoluteFill data-beat={String(i)}>
                      <BeatClock warp={sc.warp}>{C ? <C {...(sc.props ?? {})} /> : <Missing id={sc.shot} />}</BeatClock>
                    </AbsoluteFill>
                  </SceneCamera>
                  <BeatChrome chrome={sc.chrome} W={width} H={height} />
                </BeatGround>
                </NarrationContext.Provider>
              </SceneDurationContext.Provider>
              {sc.mp3 ? <Audio src={staticFile(sc.mp3)} /> : null}
            </TransitionSeries.Sequence>
          );
          if (i === scenes.length - 1) return [seq];
          return [seq, (
            <TransitionSeries.Transition key={`t${i}`}
              presentation={pickPresentation(sc, scenes[i + 1], width, height, activeDna,
                edgeGround(sc, 'out') ?? activeDna, edgeGround(scenes[i + 1], 'in') ?? activeDna,
                reducedMotion)}
              timing={linearTiming({durationInFrames: TR})} />
          )];
        })}
      </TransitionSeries>
      </AbsoluteFill>
      </ReducedMotionContext.Provider>
      {/* the film's MATERIAL — above the shots (each paints its own opaque ground) and below the caption,
          so it never competes with the words the viewer is reading */}
      <FilmMotifLayer motif={activeDna?.motif as any} dna={activeDna} W={width} H={height} />
      {/* the film's OPTICS — grain, corner falloff, a key direction — above the material, below the caption:
          grain over burned type reads as compression, and the caption's contrast maths assume the ground it
          measured. Static by construction (runtime/finish.tsx), so nothing here can pump or drift. */}
      <FilmFinishLayer dna={activeDna} />
      <AbsoluteFill style={{backgroundColor: veilBg, opacity: Math.max(intro, outro), pointerEvents: 'none'}} />
      {captions ? <CaptionTrack scenes={scenes} groundBg={theme?.bg ?? activeDna?.bg} dna={activeDna} dnaFontBody={activeDna?.fontBody} dnaUniform={activeDna?.uniformType} reduced={reducedMotion} /> : null}
      <BrandMark brand={brand} />
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default Film;
