# Motion research — kinetic type, camera & transitions, music & rhythm (2026-10-23)

Four passes (three web-research agents and one repository inventory), each told to read this skill's references first
and report only what is new. Numbers are SOURCED unless marked (U) — a suggestion or derivation — or (measured) — run
on this machine. Read this before building kinetic type, a new seam or camera move, or anything that times picture to
music. The remotion tier is for ANY video — creativity, craft and design, never "slides" (user, 2026-10-23).

## 0. What the library has (inventory, verified by search; updated 2026-10-24)

This section first listed the GAPS the research found (2026-10-23). Most are filled now; each line says what exists,
and what is still open. Every capability below is offered to the director by the reach table
(`references/remotion-shot-authoring.md` §F, `scripts/shot_director.py` `REACH`), because a tool nothing proposes is
built but unreachable — three benchmark films (2026-10-24) found the kinetic registers barely used and camera space
never reached.

- **Type** — `runtime/kinetic.tsx` (one shared primitive: one reference text node, per-grapheme
  `Range.getClientRects()`, measured 0 px from a text node in Latin and Chinese; the census reads it as lines;
  `shot_proof` holds must-read lines to reading time from `runtime/readingSpec.json`). Registers on it: HeadlineReveal,
  WordRoll, TypeOnPath, CroppedType, and the maths and data registers below set their copy with it (12 registers import
  it, counted by `grep "runtime/kinetic'" remotion/src/shots`). Bundled variable fonts: Space Grotesk, Playfair,
  JetBrains Mono, Inter (wght, opsz 14-32), Source Serif 4 (wght, opsz 8-60), IBM Plex Sans (the only wdth, 75-100,
  now declared in `FACES`), Bodoni Moda (opsz 6-96), Baloo 2, Noto Sans/Serif SC subsets (wght). **v2 (2026-10-24):**
  a scramble whose stand-ins can never spell (blocks / the right glyph at another weight for CJK, symbols otherwise),
  `KMotion.idle` (held type stays alive), the magic move (`runtime/kineticMove`, register `MagicMoveType`), `word`
  carry anchors (`runtime/kineticWord`) on the kinetic registers, pacing in SECONDS with reading floors paid first (a
  4 s beat reads), and `LandscapeWell` for a product's own 16:9 picture in a 9:16 film. **Still open:** the eight
  hand-rolled per-character registers (VariableTypeMorph, InflateType, ElasticType, RansomZine, ClothWave,
  OdometerRoll, AsciiField, SplitFlap) are not migrated.
- **Maths and morphs** (built 2026-10-24): TeX typeset ahead of the render by MathJax 3.2.2
  (`scripts/tex_glyphs.mjs`; a film's equations by `scripts/mathtex.py`, which `render_remotion.py` runs first),
  drawn from its glyph outlines by `runtime/mathMorph` — Manim's Write, TransformMatchingTex, Indicate/Circumscribe
  and ValueTracker reimplemented from their behaviour — and `runtime/pathMorph` for shapes that become shapes
  (resampled and aligned — measured half-way through circle→triangle in a 400 px box, interpolatePath's outline
  encloses 4,932 px² against endpoints of 125,686 and 57,288; this one 90,848). Registers: `EquationMorph`,
  `FunctionPlot` (MA), `GrowingFigure` (S).
- **Data and geography** (built 2026-10-24): `FlowSankey`, `RankRace`, `FlowCounter` (D) and `GlobeFocus`,
  `FlightArcs` (GE) — offline Natural Earth projected in code (`runtime/geo`, `earth`, `labelPlace`, `sankey`).
- **Seams**: `render_remotion` resolves 19 seam types besides the default fade (`_KINETIC_TYPES`). Since the research:
  the anchored seams `container` / `grow` / `through-window` / `punch` (`remotion/src/seams.tsx`) on carry anchors a
  register marks with `data-carry` (`runtime/carry.tsx`, listed by `scripts/carry_anchors.py`); `match_cut` is no
  longer a dead spec — it is the container by declared rects; and the hard `cut` (the picture changes on the seam's
  middle frame), which `seam_plan.py` plans on unmarked seams by the film's tempo (kinetic / scored / calm). `seam_plan`
  proposes the anchored seams too. `@remotion/transitions` 4.0.486 also ships iris, flip and 11 shader presentations
  (HtmlInCanvas — measured non-deterministic here), unused. **Still open:** a content match-cut between two
  photographs that share no anchor
  (bench-aurora), and the 6 still frames after a cut (`useT` holds `ENTRY_T` through the seam — a `runtime/motion.ts`
  change).
- **Camera**: per-beat push/pull/hold (runtime/depth SceneCamera, edge-budgeted), `Plane` depth planes, stage3d,
  pageCam2D; **camera continuity across a cut** — `camera.handoff` (`runtime/handoff.ts`: a push that runs into its cut,
  the next beat inherits the velocity); and **`WorldStage`** (references/stage-runs.md) — one world across a run of
  beats, a camera that dollies, cranes, tilts, orbits and scale-zooms (exponential, fixed point held, nested layers
  handed over) between framings of named objects, parallax by real depth, focus by distance, blur by speed.
- **Light and material**: `slide.optic` (`runtime/optics.tsx`: bloom / halation / sweep / aberration on a light the
  register draws, `leak` over a seam INTO a beat; one per beat, capped by `OPTIC_MAX`, refused by validate on a register
  that does not export it) and lit material grounds (`runtime/material.tsx`: paper / water / metal / clay; the
  `LitMedium` register; a DNA's `material`).
- **Music**: answered — `scripts/beatgrid.py` (a beat grid, cuts snapped to it at the tts/pad stage) and
  `scripts/score.py` (a generated score on that grid), §3 "Built". **Still open:** tier 3 (a tempo map); whether it
  sounds acceptable is unmeasured; and the 2026-10-23 inventory found focus/pop/tick/reveal cues never planned on the
  remotion path (not re-checked in this update).
- **Portrait and gates**: on 9:16 the platform-safe frame's margin is the beat itself, blurred (the safe echo;
  `meta.safe_echo: false` refuses it); `scripts/determinism_qa.py` (is a frame the same however and whenever it is
  asked for), `scripts/caption_breaks_qa.py` (CJK caption lines broken at words, kinsoku held), `scripts/banding_qa.py`
  (CAMBI on the delivered file).

## 1. Kinetic typography

- **Live launch sites** (measured from `Element.animate`/`getAnimations()`, one day's snapshot): Linear H1 64px wght
  510, tracking -0.022em, lh 1.0, split by LINE: opacity + blur 10px→0 + translateY 20%→0, 1000 ms, CSS ease, 33 ms per
  line. Framer per CHARACTER blur 10px→0 + opacity, 400 ms each, 50 ms per letter, a sampled spring (50% at 0.18).
  Stripe digit roller translateY(-100%) strips, 325 ms (.33,1,.68,1), staggered 0-500 ms.
- **GSAP SplitText** demo staggers chars 0.04 s : words 0.15 s : lines 0.25 s (gsap.com/docs/v3/Plugins/SplitText);
  mask reveal = per-unit overflow-clip wrapper, yPercent 100, 0.6 s expo.out.
- **After Effects range selectors** (Skia Skottie RangeSelector.cpp): based on chars / chars-excl-spaces / words /
  lines; start/end/offset; shape square/ramp/triangle/round/smooth; ease high/low; amount; seeded randomise. One
  coverage value per unit drives every property. The model to copy.
- **Reading**: Netflix English ≤20 chars/s, ≤42/line; Simplified Chinese ≤9 chars/s, ≤16/line; Japanese ≤4/s
  (partnerhelp.netflixstudios.com style guides). Must-read text: ~0.6 s a word (read twice at 200 wpm). Apple "Don't
  Blink": most words held 5-7 frames — single-pass, short words only. A per-character reveal faster than reading rate
  reads as a wipe: ~50 ms Latin, ~110 ms zh (U).
- **Kerning-safe glyphs (measured, Inter 500 100px)**: per-char `inline-block` +8.1% width; per-char `inline` keeps
  it (no transforms); **one reference text node, per-grapheme `Range.getClientRects()`, glyphs placed absolutely →
  0 px difference**, 0.127 ms/frame (prefix `measureText` 1.5 ms). Force `font-variant-ligatures: none` on reference
  and glyphs (letter-spacing ≠ 0 drops ligatures anyway). Split with `Intl.Segmenter` (zh/ja word segmentation works).
- **CJK**: Chrome's `text-spacing-trim` compresses punctuation (needs `halt`/`chws`; the bundled Noto subsets keep
  them); per-char inline-blocks lose it (+11%); Range rects report the compressed widths; let the reference node do
  line breaking (kinsoku held).
- **Variable axes**: a weight/width morph reflows the line (Inter wght 100→900 +21%; Plex wdth 75→100 +11%) — measure
  per axis value (piecewise-linear, 5 anchors ≈1 px). No CJK font has a width axis. `fitText` measures once at 100px
  and scales — wrong below the font's opsz max (measured); re-measure at the real size or turn optical sizing off.
- **Subsetting** (measured, fontTools): deterministic; default features DROP tnum/ss/cv/palt — pass
  `--layout-features+=tnum,...` explicitly.

## 2. Camera and transitions

- **Match cut**: cut at the fastest movement ("12-frame move, cut on 6, pick up on 7" — schoolofmotion.com match
  cuts); hold the focal point in the same screen zone (eye-trace, Murch).
- **Container transform** (Material): the container persists while size/position/shape animate; 300 ms standard,
  content swap ~30/70.
- **Zoom-through**: 150-200%, ~10 frames, aligned focal points; constant perceived zoom needs EXPONENTIAL scale.
- **Whip**: blur 0→peak→0 over ±5 frames, cut at peak; matched direction and brightness. `blurSlide`/`pushCut` are
  4.0.500+/4.0.523 (not installed); pushCut: hard cut at 5/11, scale 1.04→1.07, a 2-frame 0.2 flash.
- **Premium vs cheap**: hard cut by default, few moves mastered, cut at peak velocity, sound on the peak; flashes and
  leaks read cheap when menu-picked or unmotivated.
- **Parallax/dolly**: layer scale (p−z)/p; a 200 px dolly at p=2000 grows near/plane/far 14.3/11.1/7.7% (U) — the
  differential is what reads as a camera; a zoom has none. Handheld: don't (shake_qa flags 0.5 px jitter).
- **Continuity**: colour scripts and a shared motion language (Pixar, Ordinary Folk × SoM, Buck).
- **Engineering**: custom presentations get both scenes; `useTransitionProgress()` + `none()` for shared elements;
  measure rects with getBoundingClientRect / useCurrentScale (FLIP); SVG clipPath ids unique (both scenes mounted);
  opacity/filter/clip/mask/overflow/blend flatten preserve-3d — put them ABOVE the perspective element.
- **Recommended (U)**: `container` seam from `data-carry` anchors (consumes the dead match_cut spec); `grow` (a disc
  from the anchor in the next ground, luminance-guarded like portal); `through-window` (exponential zoom into an anchor,
  may be a glyph via SVG clipPath text); `punch` (once, payoff); camera hand-off on continuation cuts (B starts with A's
  end velocity); `dolly` only with ≥2 depth planes; one camera channel per beat.

## 3. Music and rhythm

- **Picture vs sound**: editors cut picture 1-2 frames BEFORE the beat (craft lore); ITU-R BT.1359: sound early
  detectable at +45 ms, sound late −125 ms. Visual hits on music go picture-early (the SFX peak rule stays).
- **Structure**: beat = motion, phrase (4/8 bars) = shape, event = meaning; cutting on every beat reads hectic; a
  vendor heuristic: corporate every 8 beats, playful 4, energetic 1-2 at the climax only.
- **Under a voice**: steady pulse, controlled dynamics, mid-range clear; duck pad/pluck under speech, keep a quiet kick
  and hat (U).
- **Tempo**: no authoritative explainer range; 90-125 BPM (U). Frame-locked tempos at 30 fps: 90, 100, 112.5, 120,
  128.6 BPM (60·fps/n).
- **Detection offline (measured, numpy+scipy; librosa absent)**: Ellis 2007 onset envelope (8 kHz, 32 ms window, 4 ms
  hop, 40 mel, rectified flux, smoothed, normalised) → tempo by weighted autocorrelation (τ0 0.5 s, σ 0.9 oct,
  TPS2) limited to 70-145 BPM → DP beat search (α 680). Synthetic beds 54/54 tempo, ~2 ms median beat error; 254
  real drum loops 78% within 3% (misses mostly ×4/3 swing); timestamp each flux frame at window end − hop or beats
  come out ~30 ms early. Prototype: the research scratchpad (beat_proto2.py).
- **Generated bed**: kick = falling-pitch sine (45+110e^(−t/30ms) Hz, 120 ms decay); pluck = Karplus-Strong; pad =
  detuned oscillators + slow filter; humanise velocity by accent, not random jitter; sidechain from the kick times
  directly; changes on 8-bar boundaries; riser = noise sweep 150 Hz→10 kHz, 1-2 beats in a short film; I-V-vi-IV.
- **Licensing**: Kenney, OpenGameArt and Freesound CC0 may be vendored (manifest per file); FMA only CC0 tracks;
  never vendor Pixabay or the YouTube Audio Library.
- **Snapping without breaking narration** (simulated 400 films): tts.py only appends silence after a clip, so moving
  a pad keeps words.json valid. Tier 1 — fit BPM/offset to the cuts (mean cut-to-beat 146 → 60 ms); tier 2 — stretch
  pads to the nearest beat (+0.16 s a scene at the fitted tempo; a bar costs 0.7 s — too much); tier 3 — a tempo map
  with ≤4% steps, generated bed only. Must run at the tts/pad stage, before render.
- **Built (2026-10-23; `scripts/beatgrid.py`, `scripts/score.py`, references/pipeline-scripts.md)**: tiers 1 and 2;
  tier 3 not built. Tier 2's window is +0.30 s / −0.10 s a pad (U), never under the `scene_pause` floor; a cut's
  picture moment is its seam's middle frame (a stage run: the beat's first frame; a scored film's close: its arrival,
  where the closing impact lands). Detection as above, plus a confidence gate the prototype lacked (measured): beats
  steady ≤20 ms, robust phase contrast ≥3, onset level ≥2.5 σ — synthetic beds and swing kept (2.3–3.2 ms early),
  noise/drone/speech-like refused; on the 254 loops it keeps 139 of 198 right grids and 9 of 56 wrong ones. A
  generated bed re-detects 4.3 ms worst median (48 beds), 3.7–5.3 ms through the real mix chain. Promo copy (7
  boundaries): tier 1 alone 81 ms mean cut-to-beat; tier 2 105 → 24 ms, 6/7 on the beat, +0.43 s; the score sits
  15.5 LU under the voice while it speaks, 9.8 LU in its pauses. Whether it sounds acceptable is unmeasured: listen.
