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
import {captionBand, CAPTION_SIZE_FRAC, CAPTION_MARGIN_FRAC, CAPTION_LINES,
        CAPTION_LEAD, CAPTION_LEAD_CJK, CJK_ADVANCE, latinAdvance} from './runtime/layout';
import {SceneDurationContext, ReducedMotionContext, clamp01, SEAM_FRAMES} from './runtime/motion';
import {groundLum, dnaGroundLum, dnaGroundY, groundGap, lumValue, lumFromY, type Lum, type GroundColors} from './runtime/shotLuma';
import {BeatGround, groundAt, captionInk, hexGround, LIGHT_KEY_Y, CAPTION_INK_DARK, CAPTION_INK_LIGHT,
        type SceneGroundDecl} from './runtime/light';
import {Atmosphere, type Atmo} from './runtime/atmosphere';
import {SceneCamera, type CameraMove} from './runtime/depth';
import {DesignDNAContext, type DesignDNA, dnaFromTemplate, coerceDna, TerminalChrome} from './runtime/dna';
import {REGISTRY} from './registry';
import {TextSafeAudit} from './runtime/textSafe';
import {CAPTIONS} from './captions';
import {FilmMotifLayer} from './runtime/motif';

// The scene EDL. `bgLum` is the first of the shot-director-emitted continuity fields (an explicit ground-
// luminance override; falls back to the measured shotLuma map). Future phases grow this schema (accent,
// camera{}, carry{}, transitionIn{}, audioCues[]) — all OPTIONAL + remotion-only, so the html tier is untouched.
export type SceneSpec = SceneGroundDecl & {shot: string; props?: Record<string, unknown>; durF: number; mp3?: string;
  // `bgLum` DESCRIBES the ground this beat paints (a hint for the caption ink and the seam guard); the
  // `ground` / `key` fields it now sits beside COMMAND one (they repaint the frame — runtime/light.tsx).
  // Both are kept and the Film refuses a beat that declares two disagreeing answers, because a hint that
  // silently becomes a command is how `bgLum:'light'` came to mean "a still-dark frame".
  caption?: string; bgLum?: Lum;
  // TERMINAL CHROME per scene (remotion + DNA only): a command-path + status readout the Film frames every beat
  // with (see runtime/dna.tsx TerminalChrome). Optional; inert unless the active DNA speaks 'breadcrumb'.
  chrome?: {path?: string; status?: string; root?: string};
  // A MARKED seam (chapter break): the transition INTO this scene from the previous one. Optional +
  // remotion-only; unset = the luminance-safe default (a gentle cross-fade). A kinetic type is honored only
  // on a same/near-luminance seam — across a dark↔light gap it's suppressed back to fade (see pickPresentation).
  transitionIn?: {type: 'fade' | 'slide' | 'wipe' | 'clock' | 'dissolve' | 'carry'; direction?: string};
  // A MOTIVATED camera move for THIS beat: `push` (look closer at what is here), `pull` (here is the whole
  // of it), `hold` (most beats). Optional; absent = hold. This is not the film-wide ambient drift below —
  // that one had no relationship to anything being said, which is precisely why it read as a wobble.
  camera?: {move?: CameraMove; amount?: number}};

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
// it was supposed to be guaranteed to fit. CJK measures 0.995, so 1.0 was already right.
const advanceFor = (text: string, fontStack?: string, uniform?: boolean): number =>
  isCJKText(text) ? CJK_ADVANCE : latinAdvance(fontStack, uniform);

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
  const {width, height} = useVideoConfig();
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
  // a width the browser never used
  const capMeasure = Math.min(1600, width - 120);
  const merged = fitCaption(splitCaption(sc.caption), capSize, capMeasure, CAPTION_LINES, dnaFontBody, dnaUniform);
  // WEIGHT each chunk's on-screen time by its LENGTH (not equal slices) — else a 3-word chunk lingers while a
  // 20-word chunk races the voice. Advance idx by cumulative char-fraction of the caption.
  const lens = merged.map((c) => Math.max(1, c.length));
  const total = lens.reduce((a, b) => a + b, 0);
  const local = clamp01((frame - ws) / Math.max(1, we - ws));
  let idx = merged.length - 1, cum = 0;
  for (let i = 0; i < merged.length; i++) { cum += lens[i] / total; if (local <= cum) { idx = i; break; } }
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
  const beatY = beatG ? (dnaGroundY(sc.shot, beatG) ?? beatG.y) : null;
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
  const perLine = Math.max(8, Math.floor(capMeasure / (capSize * advanceFor(capText, dnaFontBody, dnaUniform))));
  const capLines = Math.max(1, Math.ceil(capText.length / perLine));
  const fitSize = Math.max(12, Math.min(capSize, Math.floor((capBand - capMargin) / (capLead * capLines))));
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'relative', maxWidth: capMeasure, margin: `0 auto ${capMargin}px`, padding: '0 60px', textAlign: 'center',
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
        letterSpacing: capTrack, textShadow: shadow}}>{capText}</div>
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
  return (
    <>
      {ground && isEnter ? <AbsoluteFill style={{backgroundColor: ground}} /> : null}
      <AbsoluteFill style={{transform: `scaleY(${scaleY})`, transformOrigin: 'center', opacity: op}}>{children}</AbsoluteFill>
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
                          prevG: GroundColors | null, nextG: GroundColors | null): TransitionPresentation<any> => {
  const dLum = Math.abs(LUM_RANK[dnaGroundLum(next.shot, next.bgLum, nextG)] - LUM_RANK[dnaGroundLum(prev.shot, prev.bgLum, prevG)]);
  const want = next.transitionIn?.type ?? 'fade';
  // luminance guard: a dark↔light gap forces the gentle fade — EXCEPT carry, whose neutral bridge line IS the dip.
  // PERCEPTUAL guard. The bucket gap alone missed the real flashes: a near-black ground cutting to an
  // accent flood scores dark->mid (gap 1) while the frame goes from ~20 to ~150 in display terms. Judge on
  // the display-encoded distance when both grounds resolve, and keep the bucket rule as the fallback.
  const gap = groundGap(dnaGroundY(prev.shot, prevG), dnaGroundY(next.shot, nextG));
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
const cameraTransform = (frame: number, amp: number): string => {
  if (amp <= 0) return 'none';
  const s = 1 + amp * (0.035 + 0.010 * Math.sin((frame / 720) * TWO_PI));     // breathe, ~24s period
  const x = amp * 6 * Math.sin((frame / 930) * TWO_PI + 1.3);                  // float — offset periods so it never repeats
  const y = amp * 4 * Math.sin((frame / 810) * TWO_PI + 0.4);
  return `scale(${s.toFixed(5)}) translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
};

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

export const Film: React.FC<{scenes?: SceneSpec[]; camera?: number; reducedMotion?: boolean; theme?: Atmo; captions?: boolean; brand?: any; dna?: DesignDNA | null; template?: string; textSafe?: boolean}> =
  ({scenes = WORKBUDDY_SCENES, camera = 0, reducedMotion = false, theme, captions = true, brand, dna, template, textSafe = false}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const total = filmDuration(scenes);
  const cam = cameraTransform(frame, reducedMotion ? 0 : Math.max(0, camera));
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
                {/* THE GROUND IS RESOLVED HERE, PER BEAT. This provider is the whole mechanism: the design
                    DNA used to be provided once OUTSIDE the TransitionSeries, so `bg` was a film-wide
                    constant and no beat could change the light. Providing it inside the Sequence — with
                    this beat's ground over the film's system — re-grounds every register that reads those
                    tokens, measured at 148 of 149, with no per-register edit. The outer provider is kept
                    for the film-level furniture that sits outside every Sequence (caption HUD, motif,
                    brand); this one shadows it for the beat. A beat that declares no ground provides the
                    film DNA object itself, so this is a no-op and the frame is bit-for-bit unchanged. */}
                <BeatGround dna={activeDna} scene={sc} durF={durF} shot={sc.shot}>
                  <SceneCamera move={sc.camera?.move} amount={sc.camera?.amount}
                               driftExtra={(reducedMotion ? 0 : Math.max(0, camera)) * DRIFT_MAX_EXTRA}
                               driftTranslate={(reducedMotion ? 0 : Math.max(0, camera)) * DRIFT_MAX_TRANSLATE_Y}>
                    <AbsoluteFill>{C ? <C {...(sc.props ?? {})} /> : <Missing id={sc.shot} />}</AbsoluteFill>
                  </SceneCamera>
                  <BeatChrome chrome={sc.chrome} W={width} H={height} />
                </BeatGround>
              </SceneDurationContext.Provider>
              {sc.mp3 ? <Audio src={staticFile(sc.mp3)} /> : null}
            </TransitionSeries.Sequence>
          );
          if (i === scenes.length - 1) return [seq];
          return [seq, (
            <TransitionSeries.Transition key={`t${i}`}
              presentation={pickPresentation(sc, scenes[i + 1], width, height, activeDna,
                edgeGround(sc, 'out') ?? activeDna, edgeGround(scenes[i + 1], 'in') ?? activeDna)}
              timing={linearTiming({durationInFrames: TR})} />
          )];
        })}
      </TransitionSeries>
      </AbsoluteFill>
      </ReducedMotionContext.Provider>
      {/* the film's MATERIAL — above the shots (each paints its own opaque ground) and below the caption,
          so it never competes with the words the viewer is reading */}
      <FilmMotifLayer motif={activeDna?.motif as any} dna={activeDna} W={width} H={height} />
      <AbsoluteFill style={{backgroundColor: veilBg, opacity: Math.max(intro, outro), pointerEvents: 'none'}} />
      {captions ? <CaptionTrack scenes={scenes} groundBg={theme?.bg ?? activeDna?.bg} dna={activeDna} dnaFontBody={activeDna?.fontBody} dnaUniform={activeDna?.uniformType} reduced={reducedMotion} /> : null}
      <BrandMark brand={brand} />
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default Film;
