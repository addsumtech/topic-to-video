---
name: slides-to-video
description: >-
  Turn a slide deck into a narrated instruction/explainer VIDEO — each slide shown
  full-frame with voiceover, gentle Ken Burns motion, timed callout highlights, and
  optional burned-in captions. Works in ANY language, and can voice a deck in a
  DIFFERENT language than its slides (e.g. a Chinese voice-over for an English deck).
  Use whenever the user wants to make a video / voiceover / narrated walkthrough /
  explainer FROM slides or a deck — e.g. "turn these slides into a video", "narrate my
  pptx", "make an explainer video from this deck", "add a voiceover to my slides",
  "video walkthrough of this presentation", "把幻灯片做成视频", "make a Chinese
  voice-over from my English slides", "把英文幻灯片配成中文解说视频".
  Accepts .pptx, .pdf, an image folder, or a hand-off from slide-maker. Free by default
  (neural edge-tts, needs network; macOS say offline fallback) + ffmpeg; optional cloud TTS. Generates an editable storyboard,
  lets the user edit the script, renders one sample slide for sign-off, then the full
  video. Trigger even without the word "skill".
---

# Slides to Video

You turn slides into a narrated video. Source of truth is `storyboard.json` — you edit
text/timing; the scripts render the media.

## Tools (all free; verify with `scripts/_common.have_tool`)
`soffice` (pptx→pdf), PyMuPDF `fitz`, `python-pptx`, **edge-tts** (preferred neural voice, free, cross-platform — needs network), macOS `say` (offline fallback), `ffmpeg`, PIL.
Captions burn via PIL + a bundled font (no libass needed). Optional: OpenAI/ElevenLabs
TTS if the user gives an API key.

## Pipeline scripts
- `scripts/ingest.py <input> <out_dir>` — pptx/pdf/image-folder → `frames/` + skeleton `storyboard.json` (pulls speaker notes from pptx).
- `scripts/tts.py <out_dir> [--only N]` — narration → `audio/` + real durations. With edge-tts, also writes `audio/NN.words.json` (per-word start times), used for audio-synced HTML reveals; emits `.mp3`. With macOS `say`, emits `.aiff` (no words.json). **`tts.py` REWRITES `storyboard.json`** (to store each clip's measured duration) — so run it (and any duration-editing pass of your own, e.g. tail-padding) **BEFORE you hand-set per-scene fields like `transition`**, or a later re-synth/duration pass that loads-then-saves the board will silently clobber those edits. Order: finalize audio & durations → THEN set transitions/motion → validate → render (render only READS the board, so it's safe after).
  **Every speech clip is MASTERED in place before its duration is measured:** loudness-normalised
  (EBU R128, I=-14) + trailing dead-air trimmed (tail-only — leading/internal timing untouched, so
  `words.json` word times stay valid), so levels are consistent across providers and the pacing gates
  see speech, not dead air. The re-padded tail carries the BETWEEN-SCENE PAUSE. Opt out of mastering
  with `meta.audio_master: false`.
  **`meta.scene_pause` (default 0.55s) is the pause the viewer HEARS between two scenes — not the pad.**
  The two are different on the remotion tier, and conflating them shipped a real defect: that tier
  cross-dissolves scene i+1 over the last `SEAM_FRAMES` (12 frames = 0.40s) of scene i, **audio
  included**, so a flat 0.42s pad left **0.18s** of silence at every one of a 37-beat film's 36 seams —
  *shorter than that film's own within-sentence comma pauses (up to 0.55s)*. The pause between two
  scenes was shorter than the pause between two clauses, which reads as the next scene cutting in
  before the sentence has landed. `tts.py` now converts `scene_pause` into a per-tier pad (remotion:
  `scene_pause + SEAM_FRAMES/fps`, parsed from `runtime/motion.ts` so the two cannot drift; html: the
  pause itself), so **both tiers sound the same**. `meta.audio_breath` still sets the RAW pad for a
  board that deliberately wants one.
  **The pause is MEASURED against the film's own full stop; `scene_pause` is only the FLOOR.** A fixed
  number cannot be right: how long a full stop lasts is a property of the voice, the language and the
  rate, none of which the skill chooses. Fixed at 0.55s it shipped a second, subtler version of the same
  defect — a seam of 0.72s against that film's own **0.57s within-beat sentence break**, only 27% longer
  for a change of picture, argument AND register, heard as each beat's last sentence being stopped rather
  than finished. So `tts.py` measures every clip's longest internal silence, takes the **75th percentile
  across the whole film** (`_film_sentence_pause` — the median lands between the one-sentence and
  two-sentence beats and describes neither; the max would let one dramatic pause set every seam) and
  targets **1.7×** that, floored at `scene_pause` and capped at `MAX_SCENE_PAUSE` (1.5s) so it stays a
  pause. The reference is film-wide on purpose: per clip, a two-sentence beat would get a ~1.0s seam and
  a one-sentence beat 0.55s — the rhythm would change for a reason no viewer can perceive. A film with no
  measurable full stop (every beat one unbroken clause) falls back to the floor. `tts.py` prints the
  number it derived.
  **`scene_pause` is a PAUSE, not a reading buffer — keep it ≤~0.9 s.** Padding it to 2–3 s to
  "give time to read" makes each scene end on a frozen, silent frame that reads as the video hanging;
  reading time belongs in a slower `meta.tts_speed`, not a long dead tail (see `tts_speed` below).
- `scripts/theme.py <out_dir> [--mode light|dark] [--accent #hex] [--accent2 #hex] [--bg #hex] [--style <key>] [--brand-logo <png>]` —
  derive a topic-fitting palette from `frames/` (or the passed overrides) and write
  `<out_dir>/theme.css` (the HTML tier links it; the programmatic renderers parse the same
  semantic vars — one color world). Run before authoring pages OR programmatic scenes. Contrast is
  **gamma-correct WCAG** (true relative luminance): it enforces fg/bg ≥7:1, nudges a SAMPLED
  accent toward ≥3:1 on the bg (lightness only, capped ±0.15 to preserve the hue's character;
  an explicit `--accent` override is never touched), and picks `--on-accent` by whichever of
  black/white has the higher true contrast on the accent fill. **`--brand-logo <png>`** samples the
  logo's dominant non-neutral hue as the accent source (priority over frames; the SAMPLED contrast
  nudge still applies; explicit `--accent` still wins outright) — and when `<out_dir>/storyboard.json`
  carries `meta.brand.logo` and no accent/brand-logo flag was passed, that logo is **auto-used** as
  the brand source, so a branded deck's accent follows its mark by default. An out_dir themed BEFORE this fix
  may carry a low-contrast `--on-accent` in its theme.css — re-run `theme.py` to regenerate. It also
  emits **`--grain-amount`** per style — a printed/filmic style (risograph/manga/watercolor/terminal/
  noir/cartographic) gets a subtle fixed-seed **film grain** (motifs.css `body::after`, auto-applied,
  FREE tier), clean styles stay crisp at 0; a data-heavy page opts out with `<body class="no-grain">`.
- `scripts/imagegen.py <out_dir> [--key KEY]` — OPTIONAL paid step: generate AI **background/atmosphere
  art** via OpenAI `gpt-image-2` for scenes/pages that carry an `image_prompt`, cached under `.assets/`
  (re-runs are free). Auto-uses the Codex CLI (no key) when installed, else needs
  `OPENAI_API_KEY`/`~/.openai_key`; `meta.image_provider` (`auto`/`codex`/`openai`) selects
  the path. Only acts when `meta.image_source == "openai"`. This is the **`atmosphere`/broll** class —
  generic, no facts — and it lives **behind HTML pages** (soft `.bg-soft` textures / a hero cover),
  never a standalone slideshow of generated stills (data stays in real HTML/charts — the "AI =
  background, code = data" split). `validate.py` enforces the three bright lines on such a background
  (backplane-only, no text/data, never a stand-in for a real named subject → that's `documentary`).
- `scripts/imagefetch.py <query> <out_path> [--prefer W] [--duotone SHADOW HIGHLIGHT]` — the
  **`documentary` (REAL-image) tier**, FREE + no key: search **Wikimedia Commons** for a
  license-clean (CC / Public-Domain) real photo/map/diagram of the ACTUAL named subject, download it,
  and write a sidecar `<out_path>.json` with the license + attribution. Unlike `imagegen` (generic
  atmosphere), this DEPICTS the real thing, so it can demonstrate the point directly (a real
  rail-network map, a real cityscape) — a FAITHFUL class (real + sourced + credited). API helpers:
  `search(query)`, `fetch(query,out,prefer=)` → attribution dict (or None if nothing license-clean),
  `attribution_line(meta)` for the on-screen `.credit`, and `duotone(in,out,shadow,highlight,mid=)`
  to tone a real image into the deck's palette ("treated to match" a styled deck). The design-director
  picks `media.treatment: none|atmosphere|documentary` per beat (see its agent + the Imagery
  faithfulness section); reach for `documentary` on CONCRETE topics (a city, place, real system).
- `scripts/render.py <out_dir> [--sample N] [--only N] [--vertical] [--reduced-motion] [--preview]` — storyboard → `out.mp4` + `out.srt`.
  **`--preview`** = the cheap ITERATION tier (~1.4–2× wall-clock; 2.5× fewer captured frames — per-scene fixed overheads eat part of the gain): 12fps captures + lighter JPEG, its own
  clip cache (`.clips_preview`) and `preview.mp4` output — temporally identical (captions/cues/word-sync
  are time-based), just choppier; never touches `out.mp4`/`.clips`. Use it while experimenting with
  design/register changes so iteration cost never argues against boldness; deliver with the full render.
  **Scene transitions:** a gentle dip-to-theme-bg at clip edges (video only — audio/durations
  untouched, so cache + `-c copy` concat + A/V gate still hold). `meta.transition` (`dip` default |
  `none`), `meta.transition_seconds` (0.2). **Per-scene override — the transition is SEMANTIC:**
  `slide.transition` (`dip` both edges · `in`/`out` one edge · `none`) + `slide.transition_seconds`
  override the meta default per scene; the design plan maps the beat's `relation` to it (continuation →
  hard cut; new-topic/payoff/close → an in-edge on the opener PLUS an out-edge on the predecessor —
  a dip needs both sides, validate lints unpaired edges) — see `references/motion-grammar.md`
  "Transition rhythm". **Transition STYLE — `meta.transition_style`** (`dip` default | `fadethrough` studio-timed dip |
  `drift` breath-with-direction | `push` horizontal page-push | `lift` vertical page-turn | `wipe`
  bg-sheet sweep | `blur` rack-defocus coda): what a seam LOOKS like, chosen ONCE per deck from the
  register's motion personality — a transition is a CLAIM about how two beats relate, never decoration
  (semantics + taste/rhythm rules + the doc-only match-cut/jump-cut/verbal-J-cut techniques:
  `references/motion-grammar.md` "Transition STYLE"). Each half is self-contained per clip so `-c copy`
  concat still holds; motion is eased and rides the audio-breath silence. Budget ~2-3 marked seams per
  video; never random; no spins. **Karaoke captions:** when edge-tts `audio/NN.words.json`
  exists, the burned caption highlights the word being spoken, timed to the real word times — for
  space-delimited languages by word index, and for **CJK by CHAR-SPAN** (each edge token is located as a
  substring of the caption, so 中文 gets the same word-level highlight as English); falls back to
  line-level chunks for MiniMax/say (no word timings) or when token matching is too weak. `meta.captions_karaoke`
  (`auto` default | `off`). The highlight colour is **contrast-picked per scene** against the caption band's
  ground (prefers `--accent`, else `--accent2`/gold/high-contrast b/w) AND kept distinct from the
  neighbouring words — so the spoken word never vanishes into an accent-fill / same-colour band.
  **Caption placement — `meta.caption_mode` (DEFAULT `overlay`):** the caption requirement is: the FRAME'S
  OWN BACKGROUND fills the whole frame and the subtitle sits DIRECTLY on it — **no separate solid strip/bar
  for the caption, and no white/black halo** — in a colour that CONTRASTS the frame's real bottom ground,
  with the LAYOUT keeping content clear of the caption zone so they never conflict, AND the subtitle TEXT in
  the SAME colour the frame's own content uses on that ground. `overlay` delivers this: it keeps `W×H` (no
  canvas growth, exact 16:9), burns the caption flush at the very bottom, and — keyed off each scene's
  sampled bottom ground — the ink is **the deck's OWN content colour for that ground** (`--fg` on a
  light/neutral page, `--on-accent` on a saturated/colored/dark fill — e.g. a red accent-fill flood gets
  WHITE caption text to match its white content, NOT an independent max-contrast dark), the per-glyph
  OUTLINE is **the frame's OWN sampled ground colour** (invisible on the clean caption zone, never a white
  bar), and the karaoke word is a distinct contrasting accent. Authors MUST keep content out of the bottom
  ~15% (keyframe_qa gates it) so the zone stays the frame's own clean ground. `band` is the OPT-IN alternative — a dedicated strip BELOW the content
  (canvas grows to `W×(H+~126–138px)`) for when you deliberately want a separate footer region rather than
  the caption on the frame; `meta.caption_band` `flush` (samples the scene's edge colour) | `contrast`
  (fixed `--fg` bar). `meta.caption_scale` (default 1.0) tunes the caption font. Same rule on the remotion
  tier: the caption draws on the frame's ground (NO scrim rectangle), contrast-picked, shots reserve the
  band so nothing is occluded (see `references/captions.md`).
  **Timed callouts:** a callout carrying a `cue` anchor phrase (or an explicit `at` 0..1 fraction)
  appears at the moment its region is spoken — resolved via `cues` (edge word-times, else text-position
  estimate) — and holds to the clip end (a vanishing highlight reads as a glitch); untimed callouts
  show for the whole slide (unchanged). The Ken Burns camera is NOT re-aimed mid-clip. Off by default.
  **Motion intensity:** `meta.intensity` (`subtle`|`balanced` default|`bold`) + a per-scene
  `slide.intensity` (the design-director derives it from the beat's `energy`) scale the Ken Burns
  **move** (zoom-delta + pan) so a bold beat pushes harder and a subtle one drifts — the deck builds an
  energy arc (calm intro → bold payoff) instead of a uniform push (see `references/motion-grammar.md`
  "Shot grammar" + "Motion INTENSITY"). balanced/absent = unchanged; reduced-motion still wins. It's a
  gentle DIAL — `validate.py` accepts `intensity` (a tier or a non-negative multiplier) as a known field,
  and the render **clamps** the amplified move back under the zoom-delta/absolute-zoom/pan caps so a
  `bold` beat can never lurch past the gate. `shot` is authoring shorthand: the director must translate it
  into `motion.from/to/zoom` (render reads `motion`, not `shot`).
  **Audacity dial:** `meta.audacity` (`conservative`|`balanced` default|`bold`|`experimental`) is the
  RISK BUDGET for the video's `design_register` (its whole-video expressive identity — see the
  design-director step) — it scales how far the register/motion-personality/type push, so `bold` commits a
  vivid unmistakable register and `experimental` (opt-in) pushes hard and accepts a beat may be sent back.
  It is NOT a render knob and NEVER relaxes the floor: clarity, faithfulness, WCAG, and the
  keyframe/caption/overflow/AV gates are identical at every level — a register move that breaks one is
  redone in-register but in-bounds. `validate.py` accepts it as a known field (warns on a typo);
  design-director honours it when committing the register, design-critic (D2e) judges against it. It
  also sets the **register-contest width** (workflow 3.55): `conservative` skips the contest ·
  `balanced` 3 candidates · `bold` 5 · `experimental` 7 — and validate warns when a bold/experimental
  deck ships a register with no contest recorded.
  **Reduced motion:** `--reduced-motion` (or `meta.reduced_motion`) emits an accessibility variant —
  the image tier holds a static frame (to==from, no zoom/pan) and HTML reveals become opacity-only
  cross-fades (a `reduced-motion.css` linked last), still deterministic + seekable. It's an
  authoring-time opt-in variant (a baked mp4 can't read the viewer's OS setting), and it busts the
  clip cache.
- `scripts/render_remotion.py <out_dir>` with **`meta.renderer:"remotion"`** — the **RECOMMENDED cinematic
  tier**: a **bespoke-shot LIBRARY** where every beat is a hand-written, topic-driven design language (the
  registers catalogued in `remotion/LIBRARY.md`), sequenced into a narrated film with cross-dissolve
  transitions + scene-relative captions + per-scene edge-tts narration (served via `--public-dir=<out_dir>`).
  **THE CUT IS PART OF THE DESIGN — and it has to be authored, not assumed.** The tier implements five seams:
  `clock` `slide` `wipe` `dissolve` and **`carry`**, a collapse-to-line match-cut that reads as CONTINUITY
  rather than a swap and is the one seam allowed to cross a dark↔light boundary (its neutral bridge line IS
  the luminance dip; every other kinetic mark placed on such a boundary is silently forced back to a fade by
  `Film.tsx`'s guard). **None of that reaches a film unless something writes `transition_in`.** A delivered
  35-beat film shipped with all 34 cuts identical because the key was never in the storyboard at all — the
  capability was complete and unreached, which is indistinguishable from absent. Two things close it:
  **`python3 scripts/seam_plan.py <out_dir>`** derives ~2-3 MARKED seams from the `relation` each beat already
  declares (`new-topic` → `clock`, the frame opens onto a different subject · `payoff` → `dissolve`, setup and
  result share the screen · `close` → `carry`; `continuation` is never marked, because most cuts should be
  invisible and a mark only reads as punctuation while it stays rare), keeping them ≥5 beats apart and
  luminance-safe; and `validate.py` WARNS when a film of ≥12 beats carries no mark at all, or when more than
  ~1-in-8 are marked. An explicit authored `transition_in` always wins over the plan.
  **REAL IMAGERY IS EVIDENCE, SO GIVE IT THE FRAME.** `imagefetch.py` returns license-clean photographs of
  the ACTUAL subject, and the tier used to spend them as insets: measured on a delivered film about a
  physical city, the real images occupied 5.3%, 8.5% and 16.3% of the frame — the evidence was a footnote in
  a film of drawings. **`PhotoPlate`** is the shape that was missing: the photograph mounted as a plate that
  IS the frame (~32%+, aspect-capped so an arbitrary image is not cropped to a slit), with the film's own
  numbered marks placed at points in it and arriving as the narration names them. Reach for it on a CONCRETE
  topic whenever the claim is "look at the actual thing"; the library's other image registers answer
  different questions (ScanReconstruct = revealed by its process, MuseumLabel = cited beside a catalogue
  label, RealVersus = A against B).
  **Attribution is a licence condition, not a caption.** `validate.py` now ERRORS when a beat shows a
  `media/*` file whose sidecar names an author the beat does not credit — matched on name TOKENS, because
  Commons writes 'Koning, J.P. de (fotograaf)' where a credit reads 'J.P. de Koning'. This caught a credit
  naming the wrong photographer entirely. Take the credit FROM the sidecar; never type it from memory.
  **SPACE — depth and a motivated camera (`remotion/src/runtime/depth.tsx`).** Two things, and both are
  measured rather than assumed. **Depth is 2D on purpose:** a text-dense shot under
  `perspective(1200px) translateZ(50px)` loses 38% of its glyph edge strength and is plainly fuzzy, because a
  3D-composited layer is promoted, rasterized once at layout size and GPU-upscaled; the same shot under a
  plain 2D `scale` is indistinguishable from the baseline. (video-shotcraft answers this with layout-level
  CSS `zoom`; the answer here is not to put text on a Z plane.) So `<Plane depth={DEPTH.behind}>` builds depth
  from the cues that survive — SIZE, FOCUS, SHADOW, PARALLAX — and the type stays sharp. Use it only where it
  ENCODES the beat: `PlanPalimpsest` puts the earlier survey one plane back because "two plans in register on
  the same ground" is the register's whole claim and a flat drawing can only assert it. A shot that scatters
  things across planes for the look of it is decoration.
  **The camera is per-BEAT and motivated.** The film-wide sinusoidal drift (`meta.camera_drift`) has no
  relationship to anything being said, which is exactly why it reads as a wobble once noticed — it stays off
  by default. `slide.camera:{move:'push'|'pull'|'hold'}` moves for a reason: `payoff` → push (look closer at
  what is here), `close`/opener → pull (here is the whole of it), everything else holds. `seam_plan.py` derives
  ~2-4 moving beats from `relation` alongside the seams. Moves ride `useT()`, so a cut never happens over a
  moving camera, and the amount is clamped by `maxCameraPush()` — a push scales about the CONTENT zone, and
  without that clamp it would drive the lowest content down onto the burned caption.
  **`meta.design_dna.seam`** sets the film's NATIVE cut — what an *unmarked* seam becomes. The five shipped
  presets get theirs from a switch (terminal → screen-clear, editorial/blueprint → a sheet laid down), but a
  **bespoke direction matched no case and fell through to an anonymous cross-fade**, so declare it:
  `seam:{type:'wipe',direction:'from-bottom'}` for a sheet-over-sheet world, or `{type:'fade'}` to say plainly
  that a plain cut is the intent.
  **GLOBAL VISUAL SYSTEM (Design DNA):** the chosen template is NOT a set of reusable frames — it is the film's
  whole visual system. The **shot-director** FIRST expands it into an explicit **`meta.design_dna`** (an artifact:
  type / palette / container / motion / annotation grammar — `remotion/src/runtime/dna.tsx` `DesignDNA`, terminal
  preset `TERMINAL_DNA`). The DNA is provided to the Film at render (a `DesignDNAContext`) and every DNA-migrated
  register READS it via `useDNA()`, so a library register contributes only its STRUCTURE and the DNA contributes
  the VISUAL IDENTITY — 19 different compositions read as ONE visual universe (the remotion analogue of the html
  tier's `theme.css`; reuse the structural idea, NOT the visual identity). No explicit `design_dna` + a preset-mapped
  `shot_template` → `render_remotion.py` auto-applies the preset; neither → shots render their original hardcoded
  looks (`validate.py` warns). **Three-layer model + Style Assimilation (style-AGNOSTIC — see references/remotion-
  shot-authoring.md §C2 + shot-director Step 0.7):** consistency ≠ repetition. Only 2-3 ANCHOR beats show the
  explicit style CONTAINER (terminal window / glass hero / drawing sheet); every OTHER beat inherits the DNA
  grammar on OPEN canvas with a per-content layout, and reveals via the style's native action→result MOTION. Each
  shot is ASSIMILATED into the DNA (≥2-3 of type/layout/components/motion/transition/metaphor); a shot that could
  move to a different style unnoticed is rejected. This holds for ANY template — `runtime/dna.tsx` ships DNA
  presets (terminal / editorial / product-apple / blueprint / neutral) + the reusable `TermFrame` (surface-vs-open
  + action→result); terminal's `Term*` family is the worked example of style-native components. shot-critic **S11**
  audits per-frame DNA coverage + monotony + the "remove the themed shots — can you still infer the design
  language?" final test.
  **FORMS COME FROM THE SUBJECT, NOT FROM THE CATALOGUE.** A design language has two layers: the ATMOSPHERE
  (palette/type/motion — the direction contest conceives that from the topic) and the **FORM VOCABULARY**,
  meaning what kind of OBJECT each frame is: a dictionary entry, a stratigraphic column, a ledger, a
  departure board, a score, a docket, a patent plate. That second layer used to arrive from `LIBRARY.md`,
  which meant **whatever the catalogue was mostly made of became every film's vocabulary** — a city
  documentary came out of this library speaking developer-tool (six terminal shots, a SaaS dashboard under a
  children's book character, a factory conveyor belt for people cycling to a station: 16 of 35 beats, every
  one passing its own gates). So the director now DERIVES 6–10 forms from the subject BEFORE opening the
  catalogue (`agents/shot-director.md` step 0.5), records them as `meta.form_vocabulary`, and each beat names
  the one it realises in `shot_fit.form`. Two gates make it stick: `validate.py` ERRORS on a beat with no
  `shot_fit.form` or one outside the derivation, and — because every register carries a `PROVENANCE`, the
  world its idiom comes from (`product-ui`, `developer-tooling`, `print-editorial`, `survey-archive`,
  `industrial`, `scientific`, `photographic`, `craft-handmade`, …; `scripts/shot_director.PROVENANCE`) — it
  ERRORS on a beat drawing from a world the film did not declare in `meta.idiom_world`. **What that cannot
  catch:** one beat misusing an IN-world idiom (an industrial belt is fine in a harbour film and still wrong
  for people cycling to a station). That stays the shot-critic's S10 meaning judgement. When a derived form
  has no register, **BUILD it** — the normal case on a subject the library has not met, and how families J
  (survey: map plate, strata column, plan palimpsest, growth profile, technical plate) and JA (archive:
  gazetteer entry, tally ledger, museum label, inscription) came to exist.
  **A register may only put on screen what the FILM supplied.** Four times in one review a viewer found
  words that had nothing to do with the subject — `WORKBUDDY` on a title card, `©2026 · LOCAL` in a corner,
  `DASHBOARD` over a children's book character, `x:960 y:540` (the centre of a 1920×1080 frame) beside a
  cathedral as though it measured it. Every gate was green each time, for one reason: `shot_proof`'s
  demo-default check compares a beat's props against the register's prop DEFAULTS, so a string literal
  written into the JSX is invisible to it — there is no default to differ from, and it prints on every film
  that ever uses that register. So: **every word comes from a prop**, or is declared as belonging to the
  form (`export const INTRINSIC_TEXT = ['REC', '▶ PLAY']` — an axis label, a status light).
  The same rule binds NUMBERS, and there a word-scan is blind: `BlueprintGrid` rendered `{specN}`, where
  `specN` counted `0 → 100` off the clock, so it printed a confident **100%** over a beat whose claim was
  that the cathedral's nave was *never finished* — and would have printed one over any topic that reached
  for the register. `100%` has no letters in it. So the check follows PROVENANCE instead of shape: a
  rendered value must trace back to a prop, or the readout is not drawn at all. **A measurement gets a prop
  with NO default** — unlike copy, where the literal becomes the default — because a defaulted number is
  still a fabricated number on every film that omits it.
  A number that belongs to the FORM rather than the topic — a tape deck's running timecode, a frame counter
  — is declared like intrinsic text: `export const INTRINSIC_READOUT = true;`. And **`SHOT_LUMA` in
  `shotLuma.ts` must be MEASURED, never guessed**: `register_shot.py` writes `'dark'` as a placeholder for
  every new register and nothing used to come back for it, so nine cream-coloured registers all declared
  themselves dark and the luminance guard that exists to stop a bright-over-dark flash was reading the
  opposite of the truth. The placeholder is marked `PROVISIONAL` now and
  **`python3 scripts/measure_ground_luma.py --luma [--emit|--check]`** renders each shot on its own defaults
  and derives the value from the pixels. (`SHOT_LUMA` describes a register on its OWN palette — under a film's
  DNA the same register may paint an entirely different ground, which is why the seam guard resolves through
  `DNA_GROUND_TOKEN` first and falls back to this bucket only when it cannot.)
  `python3 scripts/onscreen_text_qa.py` reports all three, plus type sized in bare px (which does not scale: a
  44px caption is 2.3% of a 1920-wide frame and 4.1% of a 1080-wide portrait one). A test ratchets the
  count so the library cannot regrow it. **Never invent a number** — a readout comes from props or is
  absent. And **a label beside a point is clamped into its box** with `placeLabel()` from `runtime/layout`:
  choosing a side by `x > 0.5` reads the point's half rather than the room left, so a point near an edge
  pushes its label out of the container — two city names crossed a map plate's border that way. No raster
  check can catch that one, because text crossing a drawn border and a full-bleed field reaching the frame
  edge are the same pixels; it is prevented at the source instead.
    **`meta.design_dna.motif` — the film's MATERIAL.** Every register draws its own structure and nothing else,
  so a themed film is a set of clean but bare frames: right palette, right type, no material. A motif states
  the subject's own surface once and every frame inherits it — `coursing` (a built subject) · `waterline` ·
  `graticule` (mapped/measured) · `hatch` (printed) · `deckle` (written) · `contour` · `staff` (notation) —
  drawn by `runtime/motif.tsx` above the shots and below the caption, blended as ink on paper (`multiply` on
  a light ground, `screen` on a dark one) so it never prints across the type. Keep it near 0.05: removing it
  should make the film look flatter without anyone being able to name what left.
  **Authoring:** the shot-director (`agents/shot-director.md`) reads `content_plan.json` +
  `remotion/LIBRARY.md` and writes, per scene, `shot` (a register id) + `shot_props` (the beat's topic copy)
  + `shot_adaptation` (a REQUIRED `{kept, redesigned, topic_idea, theme_cues}` note — KEEP the register's style,
  REDESIGN its modules/components + content for THIS topic, never a raw text-swap, and name the 2-3 `theme_cues`
  tying the shot to the Design DNA; `validate.py` warns on empty props / a missing note / missing theme_cues,
  shot-critic S10+S11 check it against the render — see `references/remotion-shot-authoring.md` §B2)
  — matching the beat's intent to a register's "use when" and **varying the FAMILY across the film** (no two
  adjacent beats read as one look). Deterministic fallback: `python scripts/shot_director.py <out_dir>`.
  **Faithfulness:** a register that shows a NUMBER (ChartLive/BeforeAfterSlider/VelocitySnap) MUST be given a
  SOURCED figure in `shot_props` — never its illustrative demo default (`validate.py` warns; see
  no-fabricated-stats). `validate.py` ERRORS on a missing/unknown `shot`. Each shot is standalone-renderable
  (`cd remotion && npx remotion still src/index.ts <Id> out.png --frame=N --gl=angle`) and topic-driven via
  `--props='{...}'` (ASCII only — a multibyte `·` breaks the CLI arg). **`meta.sound_design:true`** (opt-in)
  adds a restrained SFX bed (transition whooshes pinned frame-exact to the cross-dissolves + a closing reveal)
  under the VO, plus `meta.bgm` (a path or `"auto"` synth pad) — **audition it before delivery (the pipeline
  can't hear it)**. Needs the Node toolchain (one-time `cd remotion && npm install`); the html/local tier
  (`render.py`) is untouched by this path.
  **Aspect:** the Film Composition is aspect-driven — `meta.aspect` (`16:9` default · `9:16` · `1:1` · `4:5` ·
  `4:3`) or `--vertical` renders portrait `1080×1920` etc. (Root.tsx `calculateMetadata`). Shots author in W/H
  FRACTIONS so they reflow; **on a non-16:9 film the shot-director must still-render each chosen shot at that
  aspect and fix/swap any that don't reflow** (multi-column must STACK in portrait; wide elements must not run
  off-frame) — see `references/remotion-shot-authoring.md` §A.9. Most centered/stacked/chart shots reflow as-is;
  the library's fixed multi-column + wide-horizontal registers need this per-shot pass.
  **`meta.renderer:"remotion"` is an ALIAS for `remotion`** (both render the bespoke-shot library). The old
  generic-scene tier was REMOVED in the phase-3 cutover — `"remotion-legacy"` now errors with a migration hint.
- **Design-DNA tooling (remotion tier).** `python scripts/dna_audit.py [--depth]` — which registered shots read the
  film's Design DNA and HOW DEEPLY (deep / partial / ground-only); it also fails `--check` on a shot that calls
  `useDNA()` without importing it (a hard render crash a presence-grep would score as migrated).
  `python scripts/dna_smoke.py [--template <direction>]` — renders EVERY registered shot once in one themed film;
  the only gate that catches a hook inserted into the wrong scope, since the bundler strips types unchecked. Run it
  after any bulk shot change. `python scripts/gen_dna_ground.py` — regenerates `shotLuma.ts DNA_GROUND` (which
  shots take their ground from the DNA, so captions contrast-pick against the ground the frame ACTUALLY has); a
  test fails when it is stale. `scripts/dna_migrate.py` / `dna_migrate_bg.py` are the guarded migration codemods.
  `remotion/src/runtime/atoms.tsx` — the content atoms (bar / figure / list / label / divider / marker) whose FORM
  follows the DNA; a shot declares the part, never the form. **Type** — a shot's face comes from `var(--f-display|
  body|mono, <original list>)`, never a bare family name (`references/remotion-shot-authoring.md` §C3). Loading
  these faces was a one-time, deliberate visual change to EXISTING un-themed films too: before this layer,
  `fonts.ts` loaded nothing, so declared families (including a shot's own un-themed fallback names) silently
  rendered whatever the render host had installed; now they render the real bundled fonts (~42,779 px differ on
  `EdStat` un-themed, pre-layer vs. now — see `remotion/LIBRARY.md`). `python scripts/font_gate.py` proves each
  declared face actually loads (not a silent fallback to its generic — known blind spot: a family whose name
  matches a font already on the render host, see the script's docstring); `python scripts/dna_migrate_type.py
  [--report|--apply]` is the codemod that rewrote hardcoded families onto those variables; `python
  scripts/null_dna_pixel_gate.py --save/--check <hashes.json>` is a ONE-SHOT migration-verification instrument
  (not a standing CI gate — no baseline is committed to the repo) that proves an un-themed render stays
  pixel-identical across a change you make: run `--save` yourself against the tree BEFORE your change, then
  `--check` after; `python scripts/type_specimens.py <out_dir>` renders a per-direction specimen sheet so a
  human can confirm the directions actually read as different typographic systems; `python scripts/dna_audit.py
  --type` reports per-role (display/body/mono) reach across the library, the same tracked-metric discipline as
  `--depth`.
- `scripts/render_remotion.py <out_dir>` — the render CLI for the **remotion bespoke-shot tier** (see the bullet above). The legacy generic-scene Remotion tier (atmospheres / cinematic templates / TRUE-3D archetypes / `type:"cinematic"` scenes) was REMOVED in the phase-3 cutover — its scripts, reference docs, and tests were deleted; `meta.renderer:"remotion-legacy"` errors with a re-author hint.
- `scripts/cues.py` — pure anchor→cue-time resolver: reads per-scene `audio/NN.words.json` (edge-tts per-word timings) and resolves each `data-cue` anchor phrase to an absolute timestamp, used by `render_html` for audio-synced HTML reveals.
- `scripts/check_av.py <out_dir>` — deterministic A/V gate: probes `out.mp4` video-vs-audio duration + per-clip sample-rate uniformity across `.clips/`; exits non-zero on A/V drift above tolerance (0.3 s) or non-uniform rates. Run AFTER the full render (step 9) as a gate before delivery.
- `scripts/doctor.py [--json]` — environment preflight: reports which tools/libraries are present (ffmpeg/ffprobe/PIL required; PyMuPDF/python-pptx/edge-tts/soffice/Chrome/font optional) and, for each missing one, the stage it gates + the install hint. Exits non-zero only when a REQUIRED dep is missing. Run once at the START (step 1).
- `scripts/validate.py <out_dir> [--pre-tts] [--vertical] [--json]` — deterministic PRE-render gate on `storyboard.json` (runs in ~1s): structural contract, duplicate indices, every referenced image/audio/html-page/`file://` asset + `theme.css` exists on disk, caption craft (no wall of text, no widow, ≥0.7s on screen — see `references/captions.md`), motion sanity (zoom delta + zoom-past-1.25 + callout-framing — see `references/motion-grammar.md`), per-point reveal↔voice alignment (each point spoken-% vs shown-% → leads/lags warning, cued or paced), an **animation-TRUNCATION gate** (a cued element starts at its cue and runs for its own `animation-duration`; when `cue + duration > scene duration` the render freezes it mid-flight and hard-cuts — a connector stopping in mid-air. ERROR under ~90% complete, WARN above, reporting the exact duration to set. `.draw` at 1.4s is the usual casualty, double the `--dur` .7s every other reveal uses; durations are parsed from base.css/motifs.css so they can't drift. **This is the ONLY gate that sees it** — `keyframe_qa`'s `?p=` sheet renders in blind-envelope mode where p=1.0 means "every animation finished" by construction), a **composition-gate ABSTENTION** (anchor/balance are read off the `.stage`'s flex signature + a few
layout classes; an absolute-positioned page has neither, so the gate now says it cannot measure instead of
reporting the defaults as a finding — it once reported "0% break the centered column" for a deck the DOM
measured at 12-left/8-mid/7-right, a confident false verdict that hid the real defect), a **dead-backdrop
lint** (a backdrop painted BEFORE an opaque full-bleed `.world`/`.near-black` layer is fully occluded and
renders as NOTHING; and an undeclared `inset:0` background-image div is invisible to the flatness gate and
the opacity cap — together these once let five PAID generated images ship contributing literally zero), a **duplicate-`style` lint** (HTML keeps the FIRST `style=` on an element and DISCARDS a second — an element that already carried its position and then gained `style="animation-duration:…"` silently lost the position and collapsed onto its neighbours; the resulting pile is inside the canvas, not blank and not overflowing, so no geometry gate can see it), a **hardcoded-hex lint** (WARN on a raw `#hex` in a `style=`/SVG-`fill`/`<style>` color — pages must use semantic vars), figure-traceability (a stat on screen/voice must trace to the brief; **UI-idiom chrome text opts out via `data-ui`** on the leaf element — never mutate chrome text to dodge the lint), CJK-font/cue/pacing/anti-slop warnings. Exits non-zero on any ERROR. Run BEFORE every render (step 9); `--pre-tts` validates right after authoring (skips audio checks); `--vertical` mirrors render's 9:16 canvas (also auto from `meta.aspect`). Errors block; warnings don't.
- `scripts/rhythm_qa.py <out_dir> [--json]` — deterministic PRE-render VIDEO-RHYTHM gate: the
  video-native complement to the layout-diversity gate. Reads `storyboard.json` (real `duration`s after
  tts, else estimates from narration) and flags flat pacing — durations too uniform (monotone), a climax
  not at ~70–85% (or none on a >75s video), a non-sparse closer, a static image held too long, and no
  attention reset for >~35s. Advisory (warnings) except ONE hard defect — a MEASURED static frame held
  past ~16s → non-zero exit; a missing climax is only a WARNING (an estimate never gates a render). Run
  after tts, before the full render.
- `scripts/sources.py add|list|verify <out_dir>` — capture the SOURCE TEXT behind each claim into
  `<out_dir>/sources/` (extract verbatim + origin + kind + fetch date), so `source_ref` becomes a
  pointer a critic can follow rather than a string nobody reads. Refs are `<sid>#<literal quote>`;
  matching ignores whitespace/punctuation so a hand-typed citation still resolves. Without it a
  web-researched brief is unverifiable after the fact — the single point where a wrong input
  produces a fully-green output. Each source also carries **`--tier`** — *how hard the evidence is*:
  `primary` (the thing itself: official doc, paper, repo, spec) · `secondary` (reporting ABOUT it) ·
  `community` (forum posts, tutorials, "I tested it") · `self` (material the user handed over).
  Tier is NOT a quality score — a forum post can be right and a vendor page stale; it records WHERE
  the support comes from, so "this number rests only on tutorials" is visible to a critic instead of
  living in your head. **`--as-of`** dates a TIME-SENSITIVE fact (distinct from `--fetched`: a page
  pulled today can itself be out of date). Defaults to `secondary` deliberately — an unlabelled
  source is not assumed to be the thing itself.
- `scripts/brief_qa.py <out_dir> [--json]` — deterministic PRE-plan gate on the **comprehension brief**:
  reads `<out_dir>/brief.json` and ERRORs on a missing/empty required key (`thesis`/`mechanism`/`evidence`/
  `why_it_matters`/`the_one_thing`/`source_health`), an evidence `source_ref` that does not RESOLVE against the captured
`sources/` (unknown source id, or a quote absent from the extract — this is what stops an invented
figure), a non-singular `the_one_thing`, or a
  `source_health:contradictory` with no resolved conflicts; WARNs on a verbless (topic-label) thesis or an
  evidence item with no `source_ref`. It also grades **evidence HARDNESS** off the source tiers (WARN,
  never blocking): a claim backed by **no primary source**, a claim resting on a **single non-primary
  source** (no corroboration), and a **time-sensitive** claim (price / version / count / "currently")
  whose sources carry **no `as_of`**. Resolving a ref proves the quote EXISTS in what you read — these
  three say how much that is worth. `source_ref` may be a **string or a list** (every ref in the list
  is still resolved; cross-sourcing a claim clears the corroboration warning). The STRUCTURAL floor so a hollow brief can't reach the planner —
  run at step 3.5 BEFORE dispatching `content-planner`. The SEMANTIC depth audit is `critic-content` C0.
- `scripts/critic_brief.py <out_dir>` — assembles ONE file (`_critic_brief.md`) plus a CONTACT SHEET
  (`_contact_sheet.png`, every beat numbered in a single image) for the shot-critic: the machine verdicts
  already run with an explicit list of what NOT to re-judge, the catalogue entries for only the registers
  this film uses, and the repetition / family / library-growth facts computed rather than eyeballed.
  **Run it before dispatching the critic.** A review used to open 37 keyframes one at a time and re-read a
  1200-line contract to re-derive things a script had already decided; the mechanical half is gated before
  the render now, so the critic's pass is spent on meaning, faithfulness, register fit and the film's shape.
  `scripts/contact_sheet.py` builds the sheet alone if you want it without the brief.
- `scripts/register_shot.py <Id> <Family> --use-when "…"` — scaffold and register a NEW shot at every
  sync point in ONE command (`src/shots/<Id>.tsx` stub + `registry.ts` + `Root.tsx` + `shotLuma.ts` +
  `shot_director.FAMILY` + `LIBRARY.md`), `--check` verifies an existing one. **The library is meant to
  GROW**: when a beat's argument has a shape no register carries, the director BUILDS one (shot-director
  rule 0, `shot_fit.verdict == "build"`) instead of settling for the closest match. That never happened
  in practice for a simple reason — registering by hand meant five files, four of which fail silently —
  so the cost is now one command. A new register must be REUSABLE: it carries an ARGUMENT SHAPE with the
  topic arriving through props (`shot_proof.py` ERRORS if a register hardcodes a film's own prose), so
  the library compounds instead of filling with one-offs.
- `scripts/shot_proof.py <out_dir> [--no-stills]` — the **PROOF SHEET** for a `remotion` deck: the
  mechanical half of a shot review, run BEFORE the full render. A shot-critic pass over a finished
  37-beat film cost a render plus a long review and filed 15 findings; more than half were things a
  script can decide. Static (~1s): a register's **demo default** left in `shot_props` (a card's
  `backLabel` still reading the sample word on the film's closing frame), and **two beats rendering
  the same picture** (same register, same prop shape, words swapped — reported grouped per register).
  With `--stills` (~5s/beat) it renders each beat's shot at its settled frame INSIDE the film's DNA
  (`--props='{"dna":"…"}'`) and adds: action-safe overflow, ink in the caption band, **colour
  outside the film's palette** (the arc BETWEEN its two accents — a blend of the two is in-system by
  construction), and a **dead frame** (content spanning <45% of the width). Run it after the
  shot-director step and fix everything before rendering; the critic's pass is then spent on the half
  a script cannot judge — meaning, content-fit, faithfulness, register fit. Passing is a FLOOR, not a
  verdict.
- `scripts/voice_qa.py <out_dir> [--json]` — deterministic **VOICE** gate on the narration: does it read
  like a person or like a machine imitating one. Two families — the well-known zh/en AI-slop VOCABULARY
  (随着…的不断发展 / 赋能 / 值得一提的是 / delve / "not just X, but Y"), and the RHYTHM tells every
  checklist misses. The second family is why this exists: a delivered 37-beat Chinese explainer scored
  **zero** on every vocabulary list and still read as machine-written, because the signature had moved —
  sentence-length CV 0.30 (every sentence the same length), 40% of beats an `A。B。` balanced pair, only
  11% carrying any connective at all. Read once that is punchy; read 37 times it is a template.
  **Run it right after the script step and again after any rewrite, in EVERY language**, and read
  `references/anti-ai-voice.md` before writing or revising narration. Its numbers mark where to LOOK —
  published practice says rules remove only ~40–50% of AI flavour and that over-applying them produces
  its own "rule voice", so the last pass is always a human read-aloud.
- `scripts/pedagogy_qa.py <out_dir> [--json]` — deterministic PRE-render **teaching-order** gate: walks
  the concept-dependency DAG in `<out_dir>/content_plan.json` (`introduces`/`builds_on`/`stage` +
  `meta.assumed_known`) and ERRORs on a **concept used before it is introduced**; WARNs on an `introduces`
  that's a list (>1 new idea/beat), no `ground` before the first `build`, or a `build` with no `why`/`land`
  within one beat. The mechanical backstop for `critic-content`'s prerequisite gate — run at step 9
  alongside `validate.py`/`rhythm_qa.py`. No-ops when `content_plan.json` isn't persisted.
- `scripts/keyframe_qa.py <out_dir> [--p N] [--json]` — cheap PRE-render VISUAL QA for the HTML tier:
  sweeps every cued `html` page across its **REAL cue timeline** (`?p=`+`?cues=`+`?dur=`) at N points,
  so each per-scene sheet `scene_NN.png` is an actual **FILMSTRIP**: leftmost tile = the frame at t=0
  (what the viewer sees while the narration's first words play), rightmost = the frame that ships at
  the cut. Previously the sweep ran BLIND (no `?cues=`), where seek.js sets `total = max(delay +
  animation-duration)` — a timeline that never ships, in which `p=1.0` means "every animation has
  finished" BY CONSTRUCTION, so a truncated animation was not representable and a blank opening was
  invisible. Same shot count as the blind sweep; strictly more information. `all.png` is built from
  the shipped frames. Two checks fall out of it: an **OPENING gate** (a page still blank a quarter of
  the way in has held the viewer on black for seconds → blocks; blank only at t=0 is a legitimate beat
  of black → advisory), and **`scene_NN_resting.png`**, one blind shot kept so the geometry probe still
  measures the AUTHORED layout rather than a mid-flight entrance. A scene whose probe could not run is
  reported **UNVERIFIED**, never `ok` — an unmeasured scene is not a passing scene. It also — via
  CDP DOM measurement — flags any BLANK page (a reveal that never fired) or content mis-PLACED three
  ways: OVERFLOWING the 1920×1080 canvas (full-bleed backdrops are correctly ignored); text CLIPPED
  INSIDE a card/box (a fixed-height / `overflow:hidden` box slicing its own content — the box fits so
  the canvas check can't see it; fill/bar components that legitimately clip a `.fill` are excluded);
  and content reaching into the bottom **caption zone** (the lowest ~14% where an overlay subtitle
  burns — it would sit under the caption; `caption_mode:band` and captions-off decks are exempt).
  It also advises (non-blocking) on any
  CENTERED multi-line running paragraph (body text should be left-aligned to scan; display/diagram
  classes are excluded); on **mystery furniture** (an empty bordered box with no text and no
  `data-role` — every element must be viewer-decodable in ~1s, see html-pages.md "Decodability rule");
  on **near-miss alignment** (sibling edges off by 5–22px — snap to a shared guide, see "Alignment &
  order discipline"); on **silhouette repetition** (deck-level clustering of the **area-weighted** content centroid — weighting each ink-carrying box by its area, because the bbox MIDPOINT it replaced sits at ~0.5 for any page whose content spans the frame, and so reported 23-of-29 pages "centred" on a deck measuring 10-left/9-mid/10-right by visual weight); on **enclosure containment** (text overlapping a `.ring` without being inside it — an enclosure asserts “these ones, not the others”, and text crossing its edge breaks the claim invisibly to every other check); on **content-band uniformity** (the deck-level check the centroid can't make: when
  >60% of pages start or end their content on the SAME line, the pages differ but the ENVELOPE doesn't —
  which is what actually reads as templated. A deck measured 12-left/8-mid/7-right horizontally still
  felt like one page because 21/29 of its pages ended at ~0.82 frame-height); and, on a 9:16 deck, on any page filling <60% of the vertical zone (the
  "fill the column" rule — heroes with a full-bleed `.bg-photo` are exempt). Exits non-zero on a
  blank / overflow / clip / caption-occlusion (advisories don't block). Run after
  authoring the pages, BEFORE the full render — a ~1-minute catch of the exact failures that would
  otherwise silently ship in a multi-minute render. (No CDP → screenshots + blank-check only.)
- `scripts/register_ledger.py record <out_dir> | show [-n N] [--json]` — cross-deck REGISTER MEMORY
  (`~/.slides-to-video/recent.json`): records each delivered deck's expressive identity (register name,
  style, mode, accent, motion, angle) so consecutive videos don't silently converge on one look. The
  contest reads it (Phase A avoid-list + the user's distinct-vs-house pick); the delivery step records it.
- `scripts/contest_diversity.py <frameA.png> <frameB.png> … [--json]` — MECHANICAL divergence check for
  contest candidate frames (mode / palette distance / 16×9 ink-silhouette hamming): a pair that matches
  mode AND clusters on both metrics is flagged as "two skins of one idea" (exit 2). Semantics:
  **flag = rediverge OR keep with a NAMED justification** — it complements the judge's semantic
  anti-collapse; it never auto-kills a topically-right pair.
- `scripts/snapshot.py <page.html> <out.png> [--p 1.0] [--vertical] [--no-captions] [--json]
  [--motion clip.mp4 [--mseconds 2] [--mfps 12]]` — render
  ONE designed HTML page frozen at `?p=` to a PNG and run the SAME box-geometry floor probe keyframe_qa
  gates on (canvas overflow / intra-box clip / caption-zone) — no storyboard.json needed. Exit 0 =
  clean · 2 = floor issues (printed) · 3 = rendered but floor NOT probed (no CDP — screenshot only;
  unusable as a contest verdict, drop to paper mode) · 1 = could not render; `--no-captions` skips the
  caption-zone check (band/captions-off decks). The **register-contest** primitive (every candidate gets
  real pixels + a deterministic floor verdict before any style points); also handy while authoring any page.
- `scripts/scenes.py` — deterministic ANIMATED scene renderers (no slides): `title`/`keypoints`
  (PIL), `chart`/`timeline`/`compare` (matplotlib), `html` (headless Chrome). A storyboard scene
  with `type` `title`/`keypoints`/`chart`/`timeline`/`compare`/`html` (+ a typed `props` block)
  renders an animation instead of a slide image; `type` defaults to `slide` (unchanged). Animated
  scenes render ONLY their `props` (faithful by construction). **Theme-aware palette:** the
  programmatic renderers read the SAME `theme.css` semantic vars the HTML tier uses (via `meta._out`),
  so charts/titles/timelines match a light-or-dark deck instead of always rendering dark — one color
  world across both tiers; falls back to the dark palette when no `theme.css`. **Type contrast:**
  editorial roles (title/kicker) use a bundled serif, data/labels stay sans/mono. **Key-number
  landing:** a `counter`/hero-stat scene flagged `props.climax:true` reaches its final value at ~68%
  then holds it static (no overshoot) so the key figure registers. **Word-synced chart builds:** a
  `chart` scene may carry a `props.cue` array (one anchor phrase per bar, in spoken order — the same
  anchors the HTML tier uses); when it resolves (edge `audio/NN.words.json`, else a narration
  text-position estimate via `cues.py`), each **bar grows** and its value label fades in exactly when
  the narrator speaks that figure, and a **counter counts up to land** on the spoken number — instead of
  the blind frame timer. No `cue` ⇒ the blind build (unchanged). Turns a narrated chart into a data video.
  The SAME `props.cue` word-sync now drives **`timeline`** (each node lands as its date/label is spoken),
  **`compare`** (each bar/segment grows on its part's cue), and **`keypoints`** (each row reveals on its
  phrase) — one anchor per element in spoken order; cues change only WHEN an element appears, never the
  faithful final frame. So "the element lands as it is spoken" is no longer chart-only.
- **HTML pages tier** (optional, free): `scenes.py:render_html` screenshots bespoke designed
  HTML pages (authored on `assets/html/base.css`, see `references/html-pages.md`) via headless
  **Google Chrome** — no new dependency. Each page's paused CSS reveals are captured frame-by-frame.
  **Audio-synced reveals:** tag each point's reveal element `data-cue-index="N"` (spoken order) and
  `data-cue="<spoken anchor>"`. When edge-tts `audio/NN.words.json` exists, `render_html` resolves
  each anchor's timestamp via `cues.py` and reveals each point exactly when its phrase is spoken.
  With NO per-word timings (MiniMax/say/openai) it **estimates cues from the anchor's position in the
  narration text** (`cues.estimate_cues_from_text`) — reveals still track the voice's pacing; only if
  a scene has no anchors/narration does it fall back to the blind `anim_seconds` stagger.
  **Fast capture (default):** frames are grabbed from ONE persistent Chrome over the DevTools
  Protocol as JPEG (`scripts/_cdp.py`) — one launch + many fast grabs instead of a cold Chrome per
  frame (~18× faster on a full render; ~5–7× per scene). If CDP can't run (no Chrome, old build,
  any error) it falls back automatically to the per-frame `--headless --screenshot` path (thread-
  pooled across cores). Tunables in `meta`: `capture` (`cdp` default | `screenshot` to force the
  fallback), `chrome_workers` (parallel Chromes; default ≈ cores−1, capped 8), `jpeg_quality`
  (default 90). render prints a per-scene progress line + an in-place frame bar.

## Workflow (follow in order)

1. **Preflight + Interview.** First run `python scripts/doctor.py` once: it reports any
   missing tool/library and the stage it gates. A REQUIRED dep missing (ffmpeg/ffprobe/PIL)
   → stop and have the user install it; optional gaps (edge-tts/soffice/Chrome/…) just narrow
   the tiers available — fold them into the interview (e.g. no Chrome → the promoted HTML tier is
   unavailable and the deck falls back to the flat programmatic renderers, the no-Chrome safety net).
   Then run the **interview** — a small set of selectable questions that capture the
   user's whole intention up front.
   **OPTIONS-FIRST (the interview's prime directive).** EVERY ask is an `AskUserQuestion` menu by
   default — issue it as an actual `AskUserQuestion` tool CALL, never as a question typed into your
   chat reply. A menu = 2–4 labeled options + the automatic **"Other"**. The ONLY asks that may be a
   plain prompt are ones whose ANSWER is an irreducible free-text VALUE with no decision wrapped around
   it: **the topic sentence, a file/dir PATH, an API key.** Everything else — including *do you have
   source material?* and *do you have brand assets?* — is a DECISION, therefore a menu; the free-text
   VALUE it then needs (a path, a hex) is a follow-up you collect ONLY AFTER the option is picked. If
   you are about to type a `?` into your reply instead of calling `AskUserQuestion`, stop and convert
   it to a menu.
   **Rendering rule for options:** `AskUserQuestion` shows at most **4 selectable buttons per question**
   (and up to **4 questions per call**); when a menu is richer, spell out the FULL menu in the question
   text, make the most-common items the ≤4 buttons, and let the automatic **"Other"** free-text accept
   any listed item by name — a menu that is naturally ≤4 shows every item as a button. Ask the **core
   screens (Batch 1) always** — TWO `AskUserQuestion` calls (screen A = ①–④, screen B = ⑤ Voice +
   ⑥ Grounding, plus ⑦ Brand when triggered); fire Batches 2–3 **only when a prior answer triggers
   them**. A common free/default run finishes in those **two option screens**, with zero mandatory
   free-text beyond the single topic line on a no-deck run.

   **Batch 1 — core intent + essentials (ask every run).** Fire it as **two `AskUserQuestion` calls:
   screen A = ①–④, screen B = ⑤ Voice + ⑥ Grounding (+ ⑦ Brand when triggered)** — per the batching
   note above.
   **No-deck (make-from-scratch) runs — capture the topic FIRST:** if the user has a deck
   (pptx/pdf/images) SKIP this (the deck IS the topic); with **no** input deck, before screen A ask ONE
   plain-text line for the **topic sentence** — a plain prompt ONLY because the topic is an irreducible
   free-text VALUE (like a path or a key), not a decision. Keep it to that one line: the goal/takeaway
   is captured by the **① Purpose** menu (don't re-ask it as free-text here), and the sentence becomes
   the source the content-planner + design-director build the deck from. (If the conversation has
   ALREADY surfaced candidate topics/angles, offer THEM as an `AskUserQuestion` menu with "Other" for
   the user's own — only a contextless from-scratch run needs the bare plain line.)
   - **① Purpose** *(→ `arc_kind` + the planner's tone/audience `director_note`)* — what the video
     is for, and roughly who watches. Menu: **Teach/explain** (expository) · **Pitch/persuade**
     (narrative) · **How-to/walkthrough** (howto → expository) · **Research briefing** (reference →
     expository) · Overview/intro (→ expository) · Launch/announcement (→ narrative) · Promo/hype (→
     narrative). Every Purpose maps to an `arc_kind` (narrative = builds to a payoff; expository =
     even-weight walkthrough) — never leave it undefined. (Other → another goal, or a specific
     audience/register note the planner should honour.)
   - **② Language** *(→ `meta.language`)* — **ALWAYS ask this explicitly; never silently default the
     language.** The language the narration AND captions are written in (it drives the caption font +
     the default TTS voice). Menu: **Match the slides** (auto-detect the deck's language — the safe
     default) · **English** (`en`) · **中文** (`zh`) · plus **any BCP-47 via Other** (`ja`/`ko`/`es`/
     `fr`/`de`/… — or a *cross-language* voiceover where the narration language ≠ the slide language).
     Set `meta.language` to the resolved code (never leave it `"auto"` at render). On a **no-deck** run
     'Match the slides' has nothing to detect — default the highlighted option to the **topic
     sentence's own language** instead. The narration **voice engine** is the separate question **⑤**
     below.
   - **③ Look / tier** *(→ `meta.image_source` + `meta.renderer`)* — the deck's visual world, as a clean
     TIER menu (this menu decides ONLY the tier; everything else below rides alongside it). Options:
     **Designed HTML — FREE, no AI images** (bespoke full-screen pages rendered by headless Chrome;
     `image_source:none` + `renderer:local`, the default) · **HTML + AI backdrops — PAID** (the SAME
     designed pages WITH a generated hero cover + soft on-topic textures behind the glass cards at low
     opacity; `image_source:openai` + `renderer:local` — Batch 3 then confirms the spend + style) ·
     **Cinematic (Remotion) — FREE** (a kinetic, bespoke-DESIGNED film — each beat its OWN hand-written
     design language from the register library `remotion/LIBRARY.md`, narrated, with luminance-safe seams
     + a carry match-cut; each shot is FULL-BLEED (edge-to-edge, no borders) and the camera is LOCKED by
     default — the shots animate themselves, so a whole-film drift is OFF unless `meta.camera_drift` opts in
     (a global float on top of self-animating shots reads as a per-frame SHAKE); `renderer:remotion` — the
     shot-director assigns each beat a `shot`+`shot_props`, it renders via `render_remotion.py`, reviewed by
     the shot-critic).
     **Show the Cinematic button ONLY when `doctor.py` reports the remotion tier installed**; otherwise
     the two HTML options are the whole menu. Make the FREE-vs-PAID split visible in every label; never
     enable the generator without the user picking the AI tier here. (Other → a brand/theme/CSS to
     match.) The three tiers are three distinct LOOKS, not interchangeable.
     **These ride ALONGSIDE the tier — NOT menu items (don't cram them into the option prompt):**
     • **Image doctrine (paid tier):** the generator only ever makes **backgrounds/atmosphere behind
       HTML pages** — never a bare slideshow of generated stills; DATA always stays in real HTML/charts
       (the "AI = background, code = data" split).
     • **No Chrome?** the HTML tiers are unavailable; the deck falls back automatically to the flat
       **programmatic** renderers (`title`/`chart`/`timeline`/`compare`/`keypoints`, `scripts/scenes.py`)
       — a no-Chrome SAFETY NET, NOT a promoted look, so never offer it as a menu option.
     • **Real (documentary) images — FREE, no API:** independently of the tier, for a **CONCRETE** topic
       (a city, place, real system/product/organism/event) the design-director may pull REAL license-clean
       photos/maps/diagrams from Wikimedia Commons (`scripts/imagefetch.py`) to DEMONSTRATE the subject
       directly (a real rail map, a real cityscape) — treated to match the deck. Decided PER-BEAT, not
       asked here; mention it when the topic is concrete (an abstract topic stays typographic/atmosphere).
     • **Per-beat template FORMS** (hero-stat, before/after, timeline rail, system map, metric wall,
       results table, figure focus, funnel, dashboard, case story, flywheel — `references/html-templates.md`)
       are chosen by the design-director per beat, NOT asked here.
     • **Audacity** (`meta.audacity` `conservative`/`balanced` default/`bold`/`experimental`) — the RISK
       BUDGET for the video's whole-video expressive register (how far look + MOTION + type push).
       `balanced` (solid base + one register that genuinely carries the video) is right for most runs;
       raise or lower it ONLY if the user asks for a bolder/more restrained feel — the floor
       (clarity/faithfulness/AV/gates) is identical at every level. Set it from a stated preference or
       leave the default; NOT a menu item here.
   - **④ Length** *(→ `meta.target_seconds` AND `meta.aspect` — one decision)* — the finished
     runtime, which also fixes orientation/platform. Menu: **Vertical short ~30–45s** (9:16 —
     Shorts/Reels/TikTok) · **Quick explainer ~60–90s** (16:9) · **Standard ~2–3 min** (16:9) ·
     **In-depth ~5 min+** (16:9) · Vertical long-form (9:16, longer) · Custom exact. Map the pick to
     `meta.target_seconds` (~40 / ~75 / ~150 / ~300; an explicit "4 minutes"→240 via Other) and
     `meta.aspect` (9:16 for a vertical option, else 16:9). **Captions are burned in by default**
     (`captions:true`, `caption_mode:"overlay"` — the subtitle sits on the frame's own background, no strip,
     no white halo, content kept clear of the bottom ~15%; see "Caption placement" above); (Other →
     captions OFF, per-word karaoke highlight, `caption_mode:"band"` for a separate footer strip, or a
     reduced-motion accessibility variant). `meta.target_seconds` is exactly the field the **content-planner** turns
     into beat count (**beats ≈ target_seconds/4**, with per-beat `est_seconds` summed to the target)
     and the design-director reads to scale hero/climax cadence — so it SUBSUMES the old per-slide
     pace ask (a per-slide ceiling, if ever wanted, is just `target_seconds / beats`).
   - **⑤ Voice engine** *(→ `meta.voice`; on screen B, since screen A already holds ①–④)* —
     the narration engine. Menu: **edge-tts** (free **default**, natural, needs network, accent-matched;
     the ONLY engine that emits per-word timings for word-exact caption/reveal sync) · **MiniMax**
     (paid, most natural, esp. **Chinese**; needs a key) · **OpenAI** (paid, premium neural; needs a
     key) · **macOS `say`** (offline, robotic fallback). (Other → an accent or gender preference.)
     State the tradeoff aloud: only edge-tts gives per-word timings, so say/MiniMax/OpenAI HTML reveals
     use the text-position estimate (tracks the voice's pacing, not word-exact). A cloud engine
     (MiniMax/OpenAI) then triggers **Batch 2** (key setup out-of-band + a voice-sample pick).
   - **⑥ Grounding material** *(→ how step 3 gets its facts; a MENU on screen B next to Voice)* — how to
     ground + fact-check the narration (slides/topic alone rarely say enough to narrate *well* — step 3
     depends on this). Menu: **I'll share source material** (a paper/PDF, a code repo, a report, notes) ·
     **Web-research it for me** (no material — I confirm the facts/numbers/names from the latest sources,
     as of today, and fact-check the script) · **Both** (I have some — research the rest) · *(deck runs
     only)* **The deck is enough** (rare; say the script will be thinner). Other → describe what
     grounding exists. On **"I'll share"/"Both"**, the ONLY surviving free-text is the file/repo
     **PATH(s)** — a one-line follow-up asked AFTER that option is picked (the path is an irreducible
     value, not a decision).
   - **⑦ Brand assets** *(a MENU on screen B; asked ONLY when the topic is company/institution/
     product-related or the user mentions a logo)* — "有品牌资产吗？/ Any brand to match?" Menu: **Yes —
     logo + brand colour** · **Accent colour only** (no logo) · **No brand** (default; never fabricate a
     `brand` block). Other → usage rules / light-dark variants. On **"Yes"/"Accent"**, the ONLY surviving
     free-text follow-up is the logo file **PATH(s)** and/or the brand **hex**: copy the logo file(s) to
     **`<out_dir>/assets/brand/`** (so the `meta.brand` paths stay out_dir-relative), record them as
     `meta.brand` (block in Guardrails; doctrine split in the "Brand assets" section), and feed a stated
     brand colour to `theme.py --accent` (an explicit accent is never nudged) — with NO stated colour,
     `theme.py` auto-samples the accent from `meta.brand.logo` (see its `--brand-logo` entry), so just
     recording the block is enough. No assets ⇒ no `brand` block — never fabricate one.

   **Batch 2 — cloud-voice setup (ONLY if Batch 1 ⑤ Voice engine = MiniMax or OpenAI).** First get the API key
   **OUT OF BAND** — have them `export MINIMAX_API_KEY=…` / `export OPENAI_API_KEY=…` in their own
   shell (they can type `! export …` in this session) or put it in `~/.minimax_key` /
   `~/.openai_key`. Do **NOT** ask them to paste it into chat; if they paste it anyway, warn it lands
   in the transcript and tell them to **rotate it** afterward. Never write a key into
   `storyboard.json`, a script, a log, or any committed file — `tts.py` reads it from env / the key
   file only. Then, **by provider:**
   - **MiniMax** → ask **gender** as an `AskUserQuestion` menu (**Female · Male · Either** — it selects
     which samples to synthesize). Once the key is set, run `python scripts/voice_sample.py <out_dir>
     --gender <female|male>` — it synthesizes a short sample per curated human-sounding candidate
     (natural/conversational, never theatrical) into `<out_dir>/voice_samples/`. The user LISTENS
     out-of-band, then PICKS via an `AskUserQuestion` menu whose buttons are the candidate NAMES (≤4 as
     buttons, the full list in the question text, "Other" accepts any name); set `meta.voice =
     "minimax:<the pick>"` (and `meta.voice_gender`). Bare `minimax` uses the catalog default for the
     gender. **Do NOT show OpenAI voice names to a MiniMax user.**
   - **OpenAI** → pick a **preset voice** directly (gender is implicit in the pick — don't ask it):
     buttons **Nova** · **Onyx** · **Shimmer** · **Alloy**; Echo · Fable via Other → set
     `meta.voice = "openai:<name>"`.

   **Batch 3 — AI imagery (ONLY if Batch 1 ③ = "HTML + AI backdrops", i.e. `image_source:openai`).**
   The spend is confirmed by the **Image cost** menu itself — one of its options is **"Use free HTML
   instead"** (flip ③ back to `image_source:none`, no spend), so PICKING a paid tier IS the go-ahead.
   Never confirm the spend with a free-text "proceed?" prompt. Ask (one `AskUserQuestion` call, two
   questions):
   - **Visual style** *(→ `meta.visual_style`; sets the whole deck's aesthetic register — see
     `references/visual-styles.md`)*. First DERIVE the most suitable style for THIS topic (the selection
     contest: domain · data-dense vs narrative · audience · purpose, minus the guardrail vetoes), then offer
     the FULL menu in the question text — **Swiss · Editorial · Bauhaus · Brutalism · Glassmorphism ·
     Claymorphism · Manga · Risograph · Memphis · Noir · Cyberpunk · Vaporwave · Watercolor · Art-Deco ·
     Cinematic · Blueprint · Terminal · Cartographic** — with the ≤4 buttons = your recommended pick + the 3
     next-best FOR THIS TOPIC (so the default is topic-derived, not a hardcoded "Editorial"). Other → a
     free-text brief (`"custom"`) or any listed style by name. If the user picks a style that COLLIDES with a
     somber/sensitive topic, don't silently render it — surface the restrained alternative via a follow-up
     question. Persists as `meta.visual_style` and overrides the director's auto-pick.
   - **Image cost + spend gate** (`meta.image_quality`) — the menu that CONFIRMS the spend. Options:
     **Low** ~$0.01/img · **Medium** ~$0.04 (default) · **High** ~$0.17 (worth it for a hero cover) ·
     **Use free HTML instead** (declines the spend → set `image_source:none`, drop Batch 3). Picking a
     paid tier is the go-ahead; there is no separate "proceed?" ask. Set **`meta.image_size` FROM the
     aspect** — 9:16 → `1024x1536`, else `1536x1024` — so a vertical deck gets portrait imagery, not
     landscape.
   **Imagery doctrine:** generated imagery is **generic b-roll** — no logos, faces, named things, or
   in-image text; it NEVER carries a fact (real content stays text/charts). **BUT generic ≠
   topic-neutral: every cover/background MUST visually evoke the VIDEO'S OWN SUBJECT** — a database-
   index talk gets abstract index/lookup imagery, a reef talk gets reef imagery, a slide-design deck
   gets blank panels/layout grids; a pretty-but-unrelated texture (random paper, generic gradient,
   stock desk) is a MISS. Derive the prompt's motif from the topic + comprehension brief.
   **Visual style:** the deck's chosen `meta.visual_style` (`references/visual-styles.md`) is applied
   UNIFORMLY as an atmosphere treatment — `imagegen._apply_style` prepends `meta.style_preamble` to EVERY
   generated prompt (sandwiched subject → style → hard faithfulness tail), so all images read as one coherent
   style and the style can NEVER leak into the data. It doesn't change the generic/no-text/topical rules
   above; it's HOW the atmosphere looks, not WHAT is shown.
   **Provider:** if the **`codex` CLI is installed**, generate via Codex's native image-gen (NO key —
   uses the user's Codex plan; slower, ~min/image); else the OpenAI key (`OPENAI_API_KEY` /
   `~/.openai_key`, requested out-of-band). `meta.image_provider` is `auto` (default, Codex-first),
   `codex`, or `openai`. The skill-wide default stays **flat/free** — AI imagery is opt-in.

   **After the look is chosen (HTML tiers):** the content-planner plans the beats and the
   design-director designs each beat's visual (form, motif, icons, motion); you author one
   `pages/scene_NN.html` per beat on `assets/html/base.css` (faithful — real content only), starting
   from a verified form in `references/html-templates.md` (don't reinvent the composition), following
   `references/html-pages.md`. A full-bleed backdrop may gently **breathe** (seek-frozen
   `.bg-live`/`.bg-drift` on a sparse hero/hold beat; deterministic, off under reduced motion).
   Immediately after authoring, run `python scripts/keyframe_qa.py <out_dir>` (~1 min, no audio) to
   catch a blank page / canvas overflow while it's a one-edit fix, then hand `_keyframes/all.png` to
   `agents/design-critic.md` for its **D11 rendered pass** (focal dominance, repeated layout,
   crowding, figure-ground) — fix what it flags while pages are cheap to edit. Set `meta.chrome_path`
   if Chrome isn't at the default macOS location.

   **Notes.** **Reduced motion** (accessibility variant — no zoom/pan, opacity-only reveals) is off
   by default; only set `meta.reduced_motion` if the audience needs it or the user asks via Batch 1
   ④ Other. **Language** drives the caption font (CJK needs a system font — the bundled Latin one
   tofus) and the default voice, so a wrong code here yields mojibake captions or mispronounced audio
   downstream; set `meta.language` to the code (`en`/`zh`/`ja`/`ko`/`es`/`fr`/`de`/…), defaulting to
   the slides' own detected language but always confirmed (voice-over may differ from the deck).
2. **Ingest** — run `ingest.py`. Report slide count and whether speaker notes were found.
   **SKIP on a no-deck / from-scratch run** (`ingest.py` requires an input deck): just create
   `<out_dir>`; `storyboard.json` is built at step 3.6 by merging the two plans — and remember to
   write the interview's meta (language/voice/aspect/audacity/…) into it there.
3. **Understand the material DEEPLY — never narrate from the slides alone.** A good
   voice-over explains *why*, connects ideas, and is precise — that requires real
   understanding the bullets don't carry. This step is what makes the script good.
   - **Material provided** → read it properly, not skimmed: a paper end-to-end (intro →
     method → *every* results figure/table → conclusion); a codebase via its README + the
     key modules; a doc in full. Then write a **structured comprehension brief** and SAVE it to
     `<out_dir>/brief.json` (mirror a readable `brief.md`). It's the most decision-carrying artifact in
     the pipeline, so it must be **understanding-shaped, not summary-shaped**. Required keys:
     - `thesis` — the ONE claim the material argues, a full sentence **with a verb + object**
       ("X cuts Y by Z via M"), never a topic label ("about X").
     - `mechanism` — the causal **how/why**: ≥1 because/therefore chain, the load-bearing reason it
       works, in your OWN words (not copied verbatim off one slide — that's paraphrase, not understanding).
     - `evidence` — array: each thesis/contribution → the specific figure/table/number/result that
       proves it, each with a `source_ref`.
     - `why_it_matters` — the stakes the hook will use · `the_one_thing` — a **single** sentence the
       viewer must leave with (the whole arc serves IT) · `misconceptions` — what a smart viewer would
       get wrong / what the material is NOT claiming.
     - `per_unit` — per slide: what it is *really* showing + the point to land · `unknowns` — what you
       couldn't determine (flag for extra fact-check) · `source_health` — `coherent|thin|contradictory`
       + a `conflicts` array of `{what, resolution}`.
     `brief_qa.py` gates this structurally before planning; `critic-content` **C0** audits it for DEPTH.
   - **CAPTURE THE SOURCE TEXT as you read — `scripts/sources.py`.** For every passage a claim will
     rest on, persist the extract verbatim:
     `python scripts/sources.py add <out_dir> --sid <slug> --origin <url|path> --kind web|pdf|doc|code|notes|transcript --title … --tier primary|secondary|community|self --fetched <today> [--as-of <date>] --text-file <extract>`
     Then write each evidence `source_ref` as **`<sid>#<a literal quote from that extract>`** — or a
     **list** of such refs when a claim is cross-sourced.
     **Tier every source as you capture it**, and reach for the PRIMARY one on anything load-bearing:
     the real failure this catches is a figure every third-party guide repeats while the official
     page says something else — both quotes resolve, only the tier separates them. Put `--as-of` on
     any price / version / count / "currently" claim: it dates the FACT, where `--fetched` only dates
     your reading, and a page fetched today can still be quoting last quarter.
     Why this is not optional on a WEB-RESEARCHED deck: the brief is otherwise the only record of
     what the material said, and **nothing downstream can verify it** — a content critic reviewing a
     real deck could audit `brief.json` as an artifact but could not re-verify its web-sourced
     figures. That is the one place a wrong INPUT yields a fully-green output: the gates check the
     brief's internal consistency, the plans inherit it, and every beat carries the error. With
     extracts captured, `brief_qa` ERRORs on a ref whose quote is absent from the text or whose
     source was never captured — an invented figure is stopped at step 3.5 instead of shipping.
     **Know the boundary:** the match proves the passage EXISTS in what you read, not that the
     source ASSERTS it (a quote lifted out of a negation still resolves), and not that the source is
     RIGHT. The mechanical gates stop fabrication and surface weak sourcing; whether the source
     actually claims the thing, and whether it deserved to be believed, remain `critic-content`'s
     judgement — which is why the extract, not just the citation, is what gets persisted. When a
     hardness warning fires and you cannot find a primary source, the honest fix is usually to
     **say it as reported** ("据报道…") or cut the number, not to silence the warning.
   - **Record `coverage`** in the brief: `read_in_full` / `sampled` / `skipped`. `unknowns` says what
     you could not determine; coverage says what you never opened — the more dangerous of the two,
     because nothing else in the brief reveals that a chapter was skipped.
   - **Before you plan — comprehension self-check** (record PASS/FAIL per gate in the brief): ①
     **explain-back** — state thesis+mechanism from memory, slides closed; if you can only reword the
     bullets, re-read. ② **causal** — the mechanism has ≥1 because/therefore link not printed verbatim on
     any slide. ③ **evidence-map** — every thesis/contribution maps to a specific evidence item. ④
     **one-thing** — you can state `the_one_thing` in ONE sentence and the arc serves it. ⑤ **confusion**
     — you actively looked for a contradiction (slides vs source, source vs source) and named+resolved it
     in `source_health.conflicts` (or flagged it).
   - **No material** → `WebSearch`/`WebFetch` the topic to ground and enrich: confirm the
     facts, numbers, names and framing the slides imply, and fold in current context.
     **Research the LATEST, up to today** — put the current year / "latest" in your queries,
     prefer the most recent sources, and verify every figure is current *as of today's date*
     (not a stale older number); for a time-sensitive fact, note its as-of date. Treat
     it as a **fact-check**, not flavour — with no source, you are the only thing standing
     between a confident-sounding wrong claim and the viewer.
   - **Material provided but confusing / thin / contradictory** → (i) resolve internal contradictions by
     deferring to the primary source (paper > slides > notes), recording each in `source_health.conflicts`;
     (ii) when slides and source disagree, narrate the more authoritative source and NOTE the discrepancy —
     never silently pick one; (iii) when the source is too thin to reveal the mechanism, `WebSearch` to
     fill the gap and mark it your own verified addition; (iv) when a load-bearing contradiction can't be
     resolved, **STOP and ask the user** (AskUserQuestion). Never narrate over an unresolved contradiction.
   - **Either way, stay faithful:** every claim and number in the narration must trace to the
     material or a verified source — never invent results, numbers, or citations the
     slide/paper doesn't support. A forward-looking aside is fine only if flagged as your
     own addition. (Faithfulness is TRACE-TO-SOURCE; the brief above is the orthogonal
     UNDERSTANDING layer — a script can be 100% faithful and still shallow.)
3.5. **Content plan (director) — design the video as CONTENT before design/authoring.** Dispatch
     `agents/content-planner.md` on the comprehension brief + material **AND pass the interview's
     Purpose→`arc_kind` + `director_note` (tone/audience)** — the planner ADOPTS that arc_kind (it may
     override only with a one-line justification in `director_note`), so the user's Purpose choice isn't
     silently re-derived. It returns an ordered set of
     **content beats** — each with a learning point (traced to the material), a COARSE `visual_intent`
     (`metric`/`contrast`/`sequence`/`list`/`structure`/`statement`/`section` — NOT a concrete layout),
     a narration intent, `est_seconds`, per-beat `continuity` (inherits-from / hooks-into) and
     `relation`, and the narrative markers `climax: true` (one beat ~75–80% through — the payoff) and
     `hold: true` (final beat, sparse). Plus top-level `arc`, `director_note`, `anti_slop` (faithfulness
     bans), and `rhythm` (the pacing arc). It designs WHAT the video teaches — not how it looks.
     **Concept ledger (build understanding, not just tension):** each beat also carries `introduces` (the
     single NEW concept it teaches, or null — never a list), `builds_on` (already-introduced concepts it
     depends on), and a learning `stage` (`hook|ground|build|why|land`); plus top-level `assumed_known`.
     **Save the returned plan to `<out_dir>/content_plan.json`** — `pedagogy_qa.py` walks the ledger for a
     concept-used-before-introduced ERROR, and `critic-content` reads it for the prerequisite gate.
3.55. **Register CONTEST — the divergence half (designed decks; audacity-gated).** A register written
     once regresses to the safe mean: the register system (D2e) can REFUSE blandness, but only sampling
     several genuinely different registers and SELECTING can produce the striking one. So on a
     from-scratch **designed** deck (HTML or AI tier — skip when an ingested pptx/pdf already owns the
     look, and skip at `meta.audacity: conservative`), run the contest BEFORE the full design plan.
     Width by audacity: `balanced` 3 candidates · `bold` 5 · `experimental` 7. Bounded cost: ONE authored
     page + ONE snapshot per candidate — never a full render. Procedure:
     ⓪ **Read the register ledger first**: `python scripts/register_ledger.py show` — pass any recent
     registers into the Phase A dispatch ("recent decks used: 「…」— do NOT clone them by default") so
     consecutive videos don't converge on one look. ① Dispatch `agents/design-director.md` in
     **CONTEST mode** → `register_candidates` (forced-divergent
     angles; see its "Register CONTEST — Phase A"). ② Per candidate `<key>`: make `<out>/_contest/<key>/`,
     run `python scripts/theme.py <out>/_contest/<key> --style <its visual_style> [--accent …]` for its
     own theme.css (**branded deck: pass the brand hue as `--accent` for EVERY candidate** — the
     `_contest` dirs have no storyboard so the auto-seed can't fire there; candidates diverge on style
     family/motion/type/silhouette, never on the mark's colour), author ONE representative page from its `frame_spec` — **linking
     `<out>/_contest/<key>/theme.css`, NOT `<out_dir>/theme.css`** (which doesn't exist yet; the
     html-pages boilerplate's theme link is substituted with the candidate's) — then
     `python scripts/snapshot.py <page> <out>/_contest/<key>/frame.png` (**add `--vertical` when
     `meta.aspect` is 9:16, `--no-captions` when captions are off or `caption_mode` is `band`** — the
     same exemptions keyframe_qa reads from the meta)
     — exit 2 = floor issues: repair ONCE in-register or disqualify; exit 3 = rendered but floor NOT
     probed (CDP unavailable): do NOT record a `rendered` floor verdict — fix Chrome/CDP or drop the
     whole contest to paper mode. **②b Mechanical diversity check:**
     `python scripts/contest_diversity.py <out>/_contest/*/frame.png` — a flagged pair (same mode +
     clustered palette + clustered silhouette) means the divergence was theater: REDIVERGE the pair, or
     keep it ONLY with a named justification recorded in the contest notes ("brand-locked accent" is
     PRE-AUTHORIZED on a `meta.brand` deck — the shared palette is a mandate; a flag there means look
     at mode+silhouette, which must still diverge). ③ Dispatch `agents/design-critic.md`
     in **judge mode** (give it the PNG paths + specs + `meta.audacity`): floor-breakers out, survivors
     ranked, ONE winner (or REDIVERGE once — never twice). **③b Motion snippets for the finalists:**
     re-run snapshot with `--motion <out>/_contest/<key>/motion.mp4` for the winner + runner-up (~2s
     each) — the judge CONFIRMS its ranking against the moving frames (a motion-led register may
     overtake a still-photogenic one), and the user gets the clips to watch. ④ Surface the winner + runner-up to the USER
     via `AskUserQuestion` (winner first with "(Recommended)"; include the frame paths so they can look) —
     their pick is FINAL: record it as `register_contest.winner` (+ `user_pick: true`). **When the
     ledger has a recent register, the pick MUST also offer a house option** ("延续上一条的 register" —
     continuity is a legitimate choice, distinctness is never auto-imposed) and name what the last
     deck(s) looked like so the user chooses distinct-vs-house consciously. ⑤ Continue to the
     design plan (3.6) with the director committed to the selected register, recording
     `register_contest {mode: "rendered", candidates, winner, user_pick}` in `design_plan.json` —
     `validate.py` warns at bold/experimental when a register ships with NO contest recorded, and when the
     committed `design_register.name` isn't the recorded winner's. **No Chrome / no HTML pages:** run the
     contest on PAPER (judge mode ranks the specs; record `mode: "paper"`) — weaker than pixels, say so,
     but still divergence+selection.
3.6. **Design plan (art director) — give the content its visual language.** Dispatch
     `agents/design-director.md` on the content plan + comprehension brief + `meta`. It returns a
     SEPARATE **design plan** keyed by beat id: top-level `motif` (the CONCEPT motif — one topic-derived
     visual idea), `theme` (mode/accent/accent2/bg), `design_anti_slop`; and per beat the concrete
     `visual.type` + `props` + `form` (the form ledger, via its Concept→Visual dictionary — deliverable
     forms only, no un-renderable Sankey/heatmap/pyramid), `motion_intent`, `transition` (mapped from the
     beat's `relation`; see `references/motion-grammar.md` "Transition rhythm"), `icons`, `media`
     (`image_prompt` + `motion`: kenburns/bg-live/bg-drift), and a `cue` anchor array for any multi-point
     `html` beat AND any programmatic multi-element beat (`chart`/`timeline`/`compare`/`keypoints` —
     one anchor per element in spoken order, so the build is word-synced, not a blind timer). It also carries a per-beat **reasoning trace** (`narrative_job`/`content_shape`/
     `rejected_default`), a deck **`rhythm_map`**, and a **`color_ledger`** — the operational design
     intelligence (block-dependency audit, expanded concept→visual dictionary with use/avoid/failure,
     evenness penalty, minimum deck-level variation) lives in `references/design-intelligence-addendum.md`,
     which both the design-director and the design-critic apply. It also carries a top-level
     **`signature_concept`** (ONE named, apt-but-unexpected content→visual encoding — the deck's creative
     idea, realized in a named beat with deliverable primitives) and **`style_thesis`** (the deck's
     distinctive aesthetic POV that fits THIS subject); and a top-level **`design_register`** — the ONE
     whole-video expressive IDENTITY the video is designed in (`name` + `motion_personality` +
     `type_attitude` + `how_distinct` + `carried_by`), which BINDS visual_style/style_thesis/motif/
     signature into a single register and, crucially, commits the video's MOTION character (not the default
     uniform whisper-zoom — two registers must MOVE differently). A coherent whole-video register is where
     the video's **差异感 (distinctiveness)** lives; because it's ONE committed language carried across
     every beat, it's both bolder AND lower-variance than a single wild beat. Its risk budget is the
     **`meta.audacity`** dial (`conservative`|`balanced` default|`bold`|`experimental`) — which scales how
     far the register/motion/type push but NEVER relaxes the floor. **Save the design plan to
     `<out_dir>/design_plan.json`** — `validate.py` flags a content_shape↔form mismatch + a missing
     `signature_concept`/`style_thesis`/`design_register` (and an invalid `meta.audacity`), and the
     **design-critic** (D1 fit, D2c creativity floor, **D2e whole-video register + motion personality**)
     judges them. **CINEMATIC decks (`meta.renderer:"remotion"`, alias `"remotion"` — the bespoke-shot film
     tier):** the design step is NOT this file — dispatch **`agents/shot-director.md`** instead. It runs in
     TWO parts. **① The shot-template CONTEST — full divergence+selection, the remotion analogue of 3.55:**
     a *direction* is a whole-film ATMOSPHERE (a named look + a lean toward certain register FAMILIES + a hero;
     each beat is still its own language). WIDTH scales by `meta.audacity` (`conservative` skips · `balanced` 3 ·
     `bold` 5 · `experimental` 7): `python scripts/shot_templates.py --route "<topic>" --audacity <a> --out <out>`.
     The 6 templates are SEEDS — the shot-director must **CONCEIVE bold, topic-specific directions** (not just
     route the 6) to reach the width, forcing real divergence. **Render a short SAMPLE VIDEO per direction so the
     user can SEE its look + MOTION** (a text pitch or a single still can't convey a design language — motion IS
     the language): `python scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out> --render` →
     `_contest_<key>.mp4` (~6s each, hero + 2 representative registers through the real Film). Also render one
     still per direction at **`--frame=110`** for the **diversity gate** `scripts/contest_diversity.py
     <out>/_contest_*.png` (rediverge a clustered pair); **JUDGE** with `agents/shot-critic.md` in judge mode
     (floor-break + rank → winner+runner-up); surface the judged finalists — **the sample videos** — to the USER
     via `AskUserQuestion`; record `meta.shot_template` + `meta.shot_template_contest {candidates, winner,
     user_pick, width, audacity, judge_ranked}`. `validate.py` ERRORS a bold/experimental film with NO contest
     and checks width-vs-audacity.
     **② The per-beat assignment:** **read `references/remotion-shot-authoring.md` FIRST** (the frame-craft floor +
     the meaning mandate + the real-imagery tier + the anti-pattern catalogue — this is where future films fail
     silently). Run `python scripts/shot_director.py <out_dir> --template <seed-key>` for a
     deterministic family-varied skeleton BIASED to the direction, then the shot-director agent fills each beat's
     `shot` + faithful `shot_props` + `shot_adaptation` (keep the register's STYLE, REDESIGN its modules/components
     + content for THIS topic — never a raw text-swap; §B2), keeping family-variety AND **boldness** (reach past
     the obvious register, scaled by audacity; note each beat's `rejected_default`), AND ensuring every shot
     ENCODES its beat (hide the caption — does the visual still carry THIS idea?) and COHERES with the chosen
     direction (palette/motion/motif, not a random stack). When no register encodes a topic-specific idea, BUILD a bespoke shot (real imagery where
     the topic is concrete) rather than force a near-miss. SKIP the HTML design plan (no `design_plan.json`).
     **③ Then run `python scripts/seam_plan.py <out_dir>` — the film's CUTS and CAMERA.** It is a
     verify-and-fill pass, not a competitor: it SKIPS every beat the shot-director already marked, so
     authored intent always wins. What it adds is the half an author cannot do by reading — it mirrors the
     renderer's luminance guard, which silently downgrades a kinetic mark placed across a dark↔light
     boundary (a mark spent there simply vanishes), and it derives 2-4 MOTIVATED camera beats from the
     `relation` each beat already declares (payoff → push, close/opener → pull, everything else holds).
     Skipping this step is how a 35-beat film shipped with all 34 of its cuts identical and a camera that
     never moved, while every gate stayed green: the capability was complete, tested, documented — and
     unreached, which on screen is the same as absent. `validate.py` warns when a film of ≥12 beats carries
     no marked seam at all, and warns the other way when a declared `design_dna.seam` makes so many cuts
     kinetic that the marks stop being punctuation.
     After the render, the review gate is **`agents/shot-critic.md`** (the design-critic analogue): S1 fit · S2
     variety · S3 faithfulness · S4 decodability · S6 A/V **+ the deterministic `keyframe_qa_remotion.py` blank-
     frame backstop** · **S8 boldness (audacity-scaled)** · **S10 meaning + content-fit (the `shot_adaptation`
     note checked against the pixels — was the register redesigned, not text-swapped?)** · S7 direction-adherence — from `_keyframes/scene_NN.png`
     + `check_av`; it REVISEs failing beats (re-assign, re-render). A `shot`-based scene on the local renderer is a validate ERROR.
     **The critic's verdict is a LEDGER, and the delivery pass is a fresh subagent.** Every dimension gets a
     row in `<out>/_critic_ledger.json` — the clean ones too, each citing the keyframe or brief line it rests
     on — and `python3 scripts/critic_ledger.py <out_dir>` must exit 0. Reporting only the FLAGGED beats made
     a dimension nobody looked at indistinguishable from one checked and found clean. Then, before delivery,
     dispatch `agents/shot-critic.md` as a subagent whose ENTIRE input is the `<out_dir>` path — no rationale,
     no summary of what you fixed, no steer about where to look — and gate on
     `python3 scripts/critic_ledger.py <out_dir> --final`, which REFUSES a ledger the film's own maker wrote.
     The maker holds the intent, and the intent is what makes a wrong frame look right.
     **Build the storyboard by MERGING the two plans:** the design's `visual.type`+`props`
     become each scene; its `transition` becomes the per-scene edges; a `climax` beat's scene carries
     `props.climax:true` — the climax MARKER (`rhythm_qa` reads it); it also drives the key-number landing
     hold only on a `chart` counter (a harmless no-op on any other form); its `icons`/`media`/`cue` shape the authored page (`.icon-tile`
     rows per `references/icons.md`). **Copy the content plan's `arc_kind` to `meta.arc_kind`** so
     `rhythm_qa` relaxes the persuasive-arc checks on an expository (tutorial/reference) video.
     **Also persist the interview's audacity into `meta.audacity`** — `validate.py`'s register-contest
     lints read it from the storyboard meta; left unset it defaults to `balanced` and a bold run's
     missing-contest warning would silently never fire. **Persist the interview's brand assets into
     `meta.brand` at this merge too** (and copy the files to `assets/brand/` if not already) — the
     theme auto-seed, the render bug, and every brand lint read the STORYBOARD meta; a brand recorded
     only in conversation notes never reaches any of them. **Keep BOTH plan files** — the critic
     panel (step 5) receives them: `critic-content`/`critic-narrative` audit the content plan (continuity,
     relation, faithfulness); the **design-critic** audits the design plan (motif, form diversity,
     transitions, icons, whitespace, rhythm, colour, motion).
- **Theme:** run `scripts/theme.py <out_dir> [--style <meta.visual_style>]` AFTER the design plan and BEFORE
  authoring pages or programmatic scenes — it samples `frames/` for a curated light/dark palette fitting the
  topic (or pass `--mode/--accent/--accent2/--bg` from the **design-director's** `theme` when there are no
  frames — **EXCEPT the accent on a branded deck**: when `meta.brand` is set, OMIT `--accent` so the
  brand auto-seed fires, or pass the brand hue itself; the director's topic-derived accent would
  silently override the mark's colour — the exact deck class the seed exists for is the from-scratch
  designed one with no frames). **Pass `--style <the deck's visual_style>`** (from `references/visual-styles.md`) so the chosen
  style seeds the palette + emits style-hint vars. **base.css/motifs.css AUTO-consume** `--radius` (card +
  data-component corners), `--font-display`/`--font-body` (the style's bundled TYPE — see below),
  `--border-weight`+`--border-ink` (the `--hairline` border), `--grid-strength` (`.bg-grid` density) — so
  every HTML frame follows the style with no per-page effort; `--motif-ink` is an author hint for the
  `.bg-motif` linework. **Style TYPE:** the style maps to a bundled SIL-OFL FACE (Bangers for comic/manga,
  Space Grotesk for grotesque/geometric, Playfair Display for serif/editorial, JetBrains Mono for
  mono/technical — `@font-face`'d from `assets/fonts/`, CJK+generic fallback) on `--font-display` (every
  headline + hero-number/value role) and a readable `--font-body`, so a comic deck reads comic and a Swiss
  deck reads grotesque; `--font-kind` lets the programmatic tier use the same face. An explicit
  `--accent`/`--mode` (and a frame-sampled BRAND palette) still win, and the WCAG floors run after, so a style
  can never make an unreadable palette. The style applies on EVERY tier (flat/HTML + the programmatic
  renderers read `--font-kind` to pick the same bundled title face), not just AI imagery. Pages link `base.css` →
  `theme.css` → `motifs.css`; the programmatic renderers parse the same vars. 🔴 the plan checkpoint now also
  shows the palette + mode + **visual style**.
- **Re-conceive, don't mirror:** the content-planner designs a video arc (hook + throughline +
  resequencing), not the slide order — faithful to the substance.
- **Illustrated pages:** build a beat's design-plan `media` as a `.split` page (text + a STATIC image panel,
  see `references/html-pages.md`; Ken-Burns is disabled inside `.split` so it doesn't compete with
  revealing bullets — Ken-Burns is for full-bleed hero `.bg-photo` only); generate the image via
  `imagegen` (codex/key); keep it a generic broll. Most pages stay typographic.
     🔴 **CHECKPOINT · 🛑 STOP:** show the content plan (arc + beats + coarse visual intents + the
     continuity through-line) AND the design plan (**motif** + theme palette + per-beat forms), and get
     the user's OK before authoring narration. If the user changes the register/style HERE (after a
     contest), re-record `register_contest.winner` (`user_pick: true`) to match — the committed
     register and the recorded winner must agree.
4. **Write the manuscript — dispatch `agents/scriptwriter.md` (the WRITE specialist).** Give it
   the content plan + the design plan (`motion_intent` lives in the design plan now; `est_seconds` /
   `continuity` in the content plan) — or, with no plan, the per-slide intent + slide text — the
   comprehension brief + material, `meta.language`, and the pace ceiling. It returns the final spoken line per
   beat (`{id → narration}`) + a `flags` list of any beat it could not source. Write those lines
   into each scene's `narration`; **resolve every flag** (drop or repair the unsourced beat)
   before proceeding. It may also return `duration_estimate` (if a beat's estimate exceeds its
   `est_seconds` budget, swap in its `too_dense` fallback line or tighten it) and `pronunciation_notes`
   (already folded into how a term is SPELLED in the line — the renderer has no SSML). The scriptwriter follows `references/narration-writing.md` (the style
   basis). The on-screen **captions are auto-derived from the narration**, so its words are also
   the subtitle. (PLAN → **DESIGN** → **WRITE** → CHECK: content-planner plans, design-director designs, scriptwriter writes, the parallel critic panel — `critic-narrative` + `critic-content` + `design-critic` — checks in parallel.)
4b. **Image prompts (AI-backdrop look only — `image_source:"openai"`).** The generated art is
    ALWAYS a background/atmosphere layer behind an HTML page (a soft `.bg-soft` texture or a hero
    `.bg-photo`/`.split` cover), never a standalone image scene: for each page that wants a backdrop,
    author a grounded `image_prompt` from the narration + the chosen style, tagged `image_tag:"broll"`
    and `fit:"cover"`; keep DATA in real HTML/`chart` components (never AI).
    Generic/atmospheric prompts only — no real logos, faces, named vehicles, or text in-image.
    **Topical AND (for image-forward media) on-beat, not decorative:** the prompt's central motif MUST
    come from the VIDEO'S subject (derive it from the comprehension brief). For an **image-forward**
    scene (the image carries the beat — a cover/`.split`/`kenburns`), the motif must ALSO fit THIS
    beat's point — through an **abstract quality** (sparseness, motion, density), NEVER by depicting the
    beat's literal named subject (the generic rule still binds). Litmus: *"hide the caption — (a) can a
    viewer sense what the VIDEO is about, and (b) does the image fit what THIS beat says?"* — rewrite the
    motif from the brief + narration if either fails. **The low-opacity `.bg-soft` textures rotated
    behind content pages are deck-level atmosphere and MEANT to be reused** — only litmus (a) applies to
    them. (`critic-content` R1e enforces this split.)
    The critic panel (step 5, R1e via `critic-content`) reviews the prompts.
    🔴 **CHECKPOINT · 🛑 STOP:** present every prompt + the estimated cost
    (`imagegen.cost_estimate(n, quality)`) and get sign-off BEFORE spending. Then run
    `imagegen.py <out_dir>` (the paid step; cached after). No key / API error → fall back to the
    free HTML tier (drop the `image_prompt` backdrop, keep the page on its flat theme surface) and
    tell the user.
    **HTML-tier per-beat `media` images:** generate each by calling imagegen directly —
    `imagegen.generate(prompt, out_path, key)` (key path) or `imagegen._generate_codex(prompt, out_path)`
    (Codex) — then reference the file by `file://` in the page. The `imagegen.py <out_dir>` CLI path
    generates any deck-level `image_prompt` backdrops/cover in one pass; these direct calls cover the
    per-beat page media.
4c. **Documentary (REAL-image) fetch — FREE, no key.** For every beat the design plan marks
    `media.treatment:"documentary"` (the design-director's per-beat imagery DECISION — see its "IMAGERY
    TREATMENT" procedure: `none` for data beats, `atmosphere` for mood, `documentary` to SHOW a real
    concrete subject), fetch the real image at authoring time:
    `imagefetch.fetch(doc_query, out_path, prefer=doc_prefer)` → returns an attribution dict (or **None**
    if nothing license-clean matched). Then: **treat it to match the deck** on a non-photographic style —
    `imagefetch.duotone(raw, out_path, shadow=<--fg rgb>, mid=<--accent rgb>, highlight=<--bg rgb>)`;
    reference it as a full-bleed `.bg-photo` (+ `.scrim`) or a `.split` panel; and **add a `.credit` line**
    with `imagefetch.attribution_line(meta)` — placed as a DIRECT CHILD of `<body>` (a sibling of
    `.stage`, NOT inside it, so it can't trip `keyframe_qa`'s content-overflow probe). **Fallback:** if
    `fetch` returns None, degrade per the design plan — `atmosphere` if the beat wanted mood, else `none`
    (never ship a blank). No spend + no checkpoint (it's free + real), but the critic panel (R1e) still
    checks the query matched the subject and the credit is present. Keep it to the 2–4 most physical beats.
4d. **Author the pages (HTML tiers).** This is where the deck's `pages/scene_NN.html` are actually
    written — one page per beat from the design plan (form + props + cue anchors + media), on
    `base.css` + `theme.css` (+ `motifs.css`; `vertical.css` last on 9:16), per
    `references/html-pages.md`. The full authoring procedure (including the archetype and cue-anchor
    rules) is the "After the look is chosen (HTML tiers)" passage in step 1's interview notes — follow
    it HERE in the sequence, then run `keyframe_qa` on the authored pages before the critic panel.
5. **Parallel critic panel — narration + content + design (REQUIRED, not optional).** Dispatch
   `agents/critic-narrative.md`, `agents/critic-content.md`, AND `agents/design-critic.md`
   **concurrently — in ONE message with three Agent calls** — on the storyboard **plus the comprehension
   brief / source material AND both plans** (the content plan carries `continuity`/`relation`/faithfulness;
   the design plan carries `motif` + `form` + `theme` + the `relation`→`transition` mapping — each critic
   needs the plan that owns what it checks), so the panel checks facts, structure, AND design, not just style.
   - `critic-narrative` verifies: narration is **precise and faithful** (no wrong, vague, or
     invented facts/numbers); subtitle text matches spoken words, segments into clean readable
     lines, fits on screen, no typos or garbled text; narration is in **`meta.language`** and
     **`meta.voice` matches that language** (a wrong-language voice would garble the audio).
   - `critic-content` verifies: audio↔visual alignment per beat (R2), script faithfulness and
     claims traceability (R1d/R1e including AI image prompts), scene/visual selection quality
     (R3/R5/R6), continuity, pace and cuts.
   - `design-critic` verifies: form fit + layout diversity (D1), the concept-motif swap test (D2),
     creativity floor (D2c) + named visual style (D2d) + **whole-video register & motion personality
     (D2e — the up-pushing 差异感 axis: name the register in one phrase, is it CARRIED across the video,
     does the motion actually vary, did it survive build/fix; blandness = a finding, but it only pushes
     UP and never overrides a floor)**, **per-beat MEANING (D2f — hide the caption: does the design ENCODE THIS
     idea, not just decorate on-topic? applies to conceptual/statement beats too)**, transition rhythm vs `relation` (D3), icons (D4),
     composition/whitespace (D5), visual rhythm + a WOW beat (D6), squint/cover-text (D7), semantic
     colour (D8), motion discipline / no-GIF (D9), visual anti-slop (D10).
   **Overall PASS only when ALL THREE critics return PASS.** Apply the **UNION** of their required
   EDITS to the storyboard, then re-dispatch the critics (or just the failing one) until all
   return PASS. THEN:
   🔴 **CHECKPOINT · 🛑 STOP:** present the full, critic-panel-passed script and get the user's
   edits/approval BEFORE any TTS. Do not synthesize audio until they sign off.
6. **Motion** — read `references/motion-grammar.md`. Default motion is a gentle centered
   zoom `from:[0.5,0.5,1.0] → to:[0.5,0.5,1.12]` (keep zoom delta ≤0.20). **Callouts are OFF
   by default** — do NOT add emphasis boxes. They are easy to mis-place and a translucent
   box over a dark slide reads as a muddy coloured blob; the slide already shows the content.
   Add a callout ONLY if the user explicitly asks to emphasise a named region — then exactly
   one, tightly placed on that region, and confirm its position from the rendered sample.
   **Timed callout (opt-in):** to sync the highlight with the narration, give the callout a
   `cue` (a phrase the narration says) — it appears when that phrase is spoken and holds to the
   clip end — or an explicit `at` (0..1 fraction) override. Leave both off for a whole-slide
   highlight. `validate.py` warns if a `cue` isn't found in the narration or lands past ~85%.
7. **TTS** — optionally first catch structural problems early with
   `python scripts/validate.py <out_dir> --pre-tts` (skips the audio checks, so it's safe to run
   before synth): a missing image/page/asset or a wall-of-text caption is cheaper to fix now than
   after rendering. Then, before synth, if `meta.voice` is `auto` or `edge:*`, check edge-tts is
   installed: `python -c "import edge_tts"`. If it's missing, **offer to install it once**
   (`pip install edge-tts`) for natural neural voices; if the user declines, set
   `meta.voice` to a `say:` fallback and continue. Then run `tts.py` (use `--only N` while
   iterating on one slide). edge-tts emits `.mp3`; `say` emits `.aiff` — both fine.
8. **Sample sign-off** — `render.py <out_dir> --sample N`. Then:
   a. **AV critic:** dispatch `agents/critic-av.md` on the sample frames. It verifies
      burned-in caption legibility, font/glyph correctness, R7-rendered visual quality,
      and the squint/player-chrome checks. Require its **PASS** before the sign-off.
      NOTE: do NOT run `check_av.py` on the sample — `check_av.py` probes `out.mp4` and
      `.clips/`, which exist only after the FULL render (step 9).
   Show `sample.mp4` to the user only after the critic passes.
   🔴 **CHECKPOINT · 🛑 STOP:** get explicit approval of the style (voice/pace/motion/
   captions) BEFORE the full render. Iterate on the sample until they approve — never
   batch-render all slides unsigned-off.
9. **Full render** — first the PRE-render gate: `python scripts/validate.py <out_dir>`. A
   non-zero exit means a referenced image/audio/page/asset is missing, an index is duplicated,
   `theme.css` is absent, or a caption is a wall of text — fix every ERROR before rendering (it
   catches in ~1s what would otherwise waste a multi-minute render).
   **WARNING TRIAGE — required, not "skim the warnings too".** Warnings do not block the render, which
   is exactly why they get shipped: a deck once delivered "all green" carrying **94** of them, including
   28 pages flagged FLAT on a PAID image tier and every reveal-choreography defect on the deck. An exit
   code of 0 is a floor, not a verdict. So before delivering, GROUP the warnings by kind (they repeat —
   94 collapsed to ~10 kinds) and put every kind in one of three buckets: **fix** · **accept, with a
   one-line reason** · **can't fix here**. Then TELL THE USER the accepted ones and why. A warning
   silently swallowed is a defect you chose and hid; a warning accepted out loud is a design decision.
   **Also run `python scripts/rhythm_qa.py <out_dir>`** (needs the real durations, so after tts) — it
   flags flat pacing: uniform scene lengths, a mis-placed or missing climax, a non-sparse closer, an
   over-held static image, or no attention reset for >~35s. Fix the ERRORs; treat the WARNs as
   direction (vary `est_seconds`, place the climax at ~75–80%, split a long image hold).
   **And run `python scripts/pedagogy_qa.py <out_dir>`** — the teaching-order gate: it ERRORs on a
   concept used before it is introduced (walks `content_plan.json`'s concept DAG). Fix every ERROR;
   it no-ops if `content_plan.json` wasn't persisted.
   **On a `meta.renderer:"remotion"` deck, run `python scripts/shot_proof.py <out_dir>`
   BEFORE the full render** — it catches, in ~3 minutes, the mechanical findings that otherwise cost
   a 15-minute render plus a shot-critic pass to discover: a leftover register default, two beats
   rendering the same picture, action-safe overflow, ink in the caption band, an off-palette colour,
   a dead frame. Fix every ERROR and triage the warnings out loud, exactly as with validate.
   **And run `python scripts/voice_qa.py <out_dir>`** — the VOICE gate (see `references/anti-ai-voice.md`).
   It reports the vocabulary tells AND the rhythm distribution (sentence-length CV, balanced-pair share,
   connective share, antithesis share). Treat each number as a place to look, not a target: fix the beats
   that genuinely read as template, leave the ones that trip a check and still sound like a person, and
   say out loud which you accepted. Then READ THE WHOLE SCRIPT ALOUD — the metrics catch distribution,
   only the read catches deadness.
   **For an HTML-tier deck, also run `python scripts/keyframe_qa.py <out_dir>`** — it screenshots
   every page at several reveal states into `<out_dir>/_keyframes/` and flags any BLANK page or
   content overflowing the 1080 canvas (open `_keyframes/all.png` and eyeball for tofu / off-theme /
   mistimed reveals). Fix any FAIL before the full render — cheaper than finding it in `out.mp4`. Then
   `render.py <out_dir>` (for 9:16 set `meta.aspect:"9:16"` — render and validate both honor it,
   captions auto-scale off the narrow dimension, and HTML pages must be RE-AUTHORED vertically —
   top-anchored, single-column restacks, vertical timeline rail; see `references/html-pages.md`
   "9:16 vertical pages";
   the `--vertical` flag also forces it on both), and the POST-render A/V gate:
   `python scripts/check_av.py <out_dir>`. A non-zero exit means A/V drift or non-uniform clip
   rates — fix the root cause (clear `.clips/`, fix audio or regenerate failing clips, and
   re-render) before delivering.
   **For a `meta.renderer:"remotion"` deck** (the bespoke-shot tier), `render_remotion.py` writes `out.srt`
   + `_keyframes/scene_NN.png` itself; the html-only `keyframe_qa.py` (which returns 0 on a remotion deck) is
   replaced by its remotion twin **`keyframe_qa_remotion.py <out_dir>`** (a deterministic blank-frame backstop on
   the keyframes) PLUS **`frame_safe_qa.py <out_dir>`** — the FRAME-CRAFT gate: it ERRORs on on-frame content
   bleeding off the action-safe edge (text/graphics OFF-FRAME) and WARNs on a brightness OUTLIER scene (a
   white/bright shot in a dark film = palette clash). These are the exact failures eyeballing missed — a shot that
   overflows or clashes now blocks. `rhythm_qa`/`pedagogy_qa` still apply (they read `content_plan.json`). At the
   DESIGN layer, dispatch **`agents/shot-critic.md`** on those keyframes + the `check_av` + `keyframe_qa_remotion`
   + `frame_safe_qa` reports: it judges register fit, family variety, faithful copy (no demo-number/WorkBuddy-
   leftover), decodability, **MEANING (S10 — does each shot's design ENCODE its beat's idea, not just look good?)**,
   and **boldness (S8, audacity-scaled)**, and REVISEs failing beats (the shot-director re-assigns → re-render).
   Deliver only after **shot-critic PASSES and `check_av` + `keyframe_qa_remotion` + `frame_safe_qa` exit 0**
   — and that PASS must be an INDEPENDENT one: re-dispatch the critic as a fresh subagent given only the
   `<out_dir>` path, then `python3 scripts/critic_ledger.py <out_dir> --final` (exit 0 required; it refuses an
   in-context ledger, a ledger missing any dimension, and one pinned to a different render's contact sheet).
   **DELIVERY CRITERION — every gate, not two.** Deliver `out.mp4`,
   `out.srt`, and the editable `storyboard.json` only after **`validate.py`, `check_av.py`,
   `keyframe_qa.py`, `rhythm_qa.py` and `pedagogy_qa.py` ALL exit 0** (`voice_qa.py` is ADVISORY and always
   exits 0 — read its signals and say which you accepted; failing a build on them would produce the
   "rule voice" its reference warns about) (on a `meta.renderer:"remotion"` deck,
   `keyframe_qa_remotion.py` + `frame_safe_qa.py` + shot-critic PASS REPLACE `keyframe_qa.py`, which no-ops there).
   Naming only the first two is
   how a deck shipped "all green" while the gates that actually look at the pages were never
   consulted. Also read `keyframe_qa`'s **deck advisories** (silhouette repetition, content-band
   uniformity) and any scene reported **UNVERIFIED** — an unverified scene is not a passing scene, it
   is a scene nothing measured. Then record the deck's register into the
   cross-deck ledger: `python scripts/register_ledger.py record <out_dir>` (feeds the next video's
   contest with "what the last decks looked like").
10. **Iterate** — any change = edit `storyboard.json`, then re-run render (the per-slide
    clip cache re-renders only changed slides) and tts (`--only N`). For DESIGN experiments
    (register/theme/caption changes that bust many clips), iterate with `render.py --preview`
    (12fps, own cache, `preview.mp4`) and only run the full render once the look is settled.
    Never hand-edit the video.

## Guardrails
- `duration` always comes from rendered audio (tts.py sets it) — never guess timings.
- Set `meta.voice`, `meta.captions`, `meta.language`, and `meta.audacity` in the storyboard, not via flags.
  `meta.voice` is one of: `auto` (default — tts.py prefers edge-tts, else `say`),
  `edge:<id>` (e.g. `edge:en-GB-SoniaNeural`), `say:<voice>`, `openai:<voice>`, or
  `minimax:<voice_id>` (or bare `minimax` → a catalog voice by `meta.language`+`meta.voice_gender`).
  MiniMax **region is auto-detected** (tries international `api.minimax.io` then mainland
  `api.minimax.chat`, caches the one that works) — an int'l or mainland key just works. Tunables:
  `meta.tts_model` (default `speech-02-hd`), `meta.minimax_base` (pin one host, disables auto-retry),
  `meta.minimax_group_id` (only if a mainland setup needs it); key via `MINIMAX_API_KEY` / `~/.minimax_key`.
- **`meta.tts_speed`** (default `1.0`) tightens or loosens the narration PACE without cutting content —
  a multiplier applied to BOTH edge-tts (mapped to its `rate` `±%`, e.g. `1.25` → `+25%`) and MiniMax
  (its `speed`). Clamped `[0.5, 2.0]`; for edge, keep within **~±30%** (`0.8–1.3`) — beyond that the
  neural voice sounds unnatural. Per-word timings scale WITH the rate, so captions + audio-synced reveals
  stay in sync. Reach for `1.2–1.3` when a faithful script overruns the target runtime.
  **The knob is BIDIRECTIONAL, and slowing DOWN is the fix for a video that feels rushed or whose
  scene-ends read as abrupt.** The instinct — "give the viewer more time to read" — must NOT be paid
  for by padding a long SILENT, STATIC tail onto each clip via `audio_breath`: a frame frozen and
  silent for 2–3 s then hard-cut reads as the video HANGING, not as breathing room (a real deck shipped
  this and the viewer called every scene-end "a stiff obvious gap"). Reading time belongs INSIDE the
  narration — set `tts_speed` to ~`0.9–0.92` so the whole delivery is unhurried and the reveals land
  leisurely — leaving only a SHORT natural breath (`audio_breath` ~0.4–0.5, or a per-scene tail of
  ≤~1 s) after the last word. Slow-voice + short-breath + a gentle seam beats fast-voice + long-dead-tail
  at the same total runtime, every time. (Rule of thumb: if any page's on-screen text exceeds ~28
  characters/second of its own duration it will feel too fast — lower `tts_speed` or split the page,
  don't just freeze the tail.)
- `meta.image_source` is `none` (default, free) or `openai` (gpt-image-2, paid). AI images are
  generated once by `imagegen.py` and CACHED under `.assets/` — re-renders are free + offline.
- **`meta.brand`** (OPTIONAL — user-supplied REAL assets; the mirror of the no-fabricated-logos
  imagery doctrine, which stays untouched):
  `{"logo": "assets/brand/logo.png", "logo_dark": "assets/brand/logo_dark.png",
  "name": "ACME Institute", "placement": ["cover","endcard"],
  "bug": {"corner":"tr","opacity":0.5,"height_frac":0.045,"margin_frac":0.02}}`.
  `logo` is REQUIRED when `brand` is present — path relative to out_dir (svg ok for HTML lockups;
  the render bug needs raster — and since it picks its variant BY THEME GROUND, **every declared
  variant** must be raster when "bug" ∈ placement); `logo_dark` is an OPTIONAL variant for dark
  grounds (falls back to `logo`); `name` is the OPTIONAL end-card byline; `placement` is a subset of
  {"cover","endcard","bug"} — DEFAULT when absent: `["cover","endcard"]`; `bug` is read only when
  "bug" ∈ placement (defaults as shown). **Semantics:** "cover"/"endcard" lockups are AUTHORED into
  the first/last HTML pages (design-director doctrine — `render.py` does NOT draw them; the pages
  fingerprint themselves). "bug" is the RENDER-level persistent corner mark: drawn on EVERY scene
  EXCEPT scene 1 when "cover" ∈ placement and the last scene when "endcard" ∈ placement (double-brand
  on one frame is a craft fail). Top corners only (`"tr"`/`"tl"` — the bottom is the caption zone);
  height = `height_frac`·H (default 4.5%), margin = `margin_frac`·W, opacity via alpha; uses
  `logo_dark` when the parsed theme bg's relative luminance < 0.5, else `logo`; height scales by
  the NARROW canvas dimension (so 9:16 doesn't balloon it) and a banner wordmark is clamped to
  ~35% of the frame width (aspect kept); OVERLAID onto the composite (not baked into the frame — it
  must not ride the Ken Burns move) BEFORE the edge/transition filter so it dips with the seam (a
  bug floating over a bg dip is wrong). **The remotion tier ALSO draws the logo** — as a persistent corner bug
  (`Film.tsx` BrandMark, on every scene subject to `placement`), served from the out_dir; it has no AUTHORED
  cover/endcard lockup page (that's an html-tier concept), so a remotion `brand` shows only the bug. The logo is NEVER stretched (preserve
  aspect), never recolored, no effects.
- **HTML pages tier:** `type:"html"` scenes render an authored page via headless Chrome
  (`render_html`), captured as seekable CSS reveals. Pages render only real content (faithful);
  the per-clip cache busts when the page file, `theme.css` (re-theming), or `audio/NN.words.json`
  (new edge run) changes. Locate Chrome via `meta.chrome_path` if needed.
- **Anti-slop (design-critic D10 / AV-critic):** no emoji in titles; no hardcoded hex — use semantic vars
  (`var(--bg)`, `var(--accent)`, etc.; `validate.py` lints raw `#hex` in style/SVG colors,
  `design-critic` D10 fails it); no gradient-mesh backgrounds; no player-chrome / progress
  bars / timecodes / page counters; no more than 2 consecutive beats with the same `visual.type`
  among the PROGRAMMATIC types (`html` scenes are exempt — vary those by **form family**, not type).
- **Layout diversity (HTML tier):** no single form family (cards/flow/scorecard/quadrant/hubspoke/
  blocks/timeline/compare) above ~45% of html scenes — `validate.py` warns, `design-critic` D1 fails it.
- **Concept (design-critic D2) + continuity (critic-content).** The video must express THIS topic — the
  DESIGN plan carries the top-level `motif` (the CONCEPT motif — distinct from the `image_tag: motif`
  imagery class); a **name-swappable** design (swap the topic → still works) is a template, not a design,
  and gets revised (design-critic D2). And beats must **connect** (each `continuity`: inherits from the
  prior, hooks into the next) so the video argues a case rather than listing slides (critic-content).
- **Audio-synced reveals (HTML tier) — content must not lead the voice.** Make multi-point pages
  audio-synced by DEFAULT: tag each point `data-cue-index="N"` (spoken order) + `data-cue="<spoken
  anchor>"` (a phrase the narration says); the design-director emits a per-beat `cue` array for this.
  When edge `audio/NN.words.json` exists, `render_html` reveals each point exactly when its phrase is
  spoken. If a page is NOT cued, LEAVE `anim_seconds` unset — `render_html` defaults it to spread the
  reveals across ~0.7× the scene (tracking the speaking pace) instead of cramming them at the start; a
  small `anim_seconds` on a long content page makes content appear before it's spoken. `validate.py`
  warns on that, and `critic-content` (R2) fails an uncued multi-point page whose reveals lead the audio.
  **Per-point alignment (leads/lags).** `validate.py` also estimates, for each point, WHEN it is spoken
  (its `data-cue` anchor's position in the narration) vs WHEN it is shown (the resolved word-cue time if
  edge `words.json` exists, else the paced stagger) and warns `point N spoken at ~X% but shown at ~Y% —
  reveal leads/lags the voice by ~Ns`. This catches misalignment in **both** directions and for **both**
  audio paths — important for a **paced** voice (say/openai/**MiniMax**, no per-word timings): a linear
  stagger only aligns if the narration introduces the points at roughly even intervals; otherwise cue it
  with edge-tts, restructure the narration, or tune `anim_seconds`. `critic-content` R2 confirms the fix.
- **Theming:** `theme.py` → `theme.css` (semantic `:root` vars) themes BOTH tiers — the `html`
  pages link it, and the programmatic scenes (`title`/`chart`/`keypoints`/`compare`/`timeline`)
  parse the SAME vars (one color world), falling back to the dark palette only when no `theme.css`
  exists. Pick a palette/mode that fits the TOPIC (not always dark); author pages with the vars,
  never raw hex. Mixing html + programmatic scenes in one deck is fine — they share the palette.
  Re-running `theme.py` busts ALL cached clips (both tiers read it).
- **Image provider:** `imagegen.py` auto-detects the `codex` CLI and uses its native image-gen
  (no key, Codex-plan-billed, slower) when present; else the OpenAI key (`OPENAI_API_KEY` /
  `~/.openai_key`). `meta.image_provider` (`auto`/`codex`/`openai`) overrides. Codex and OpenAI
  images cache separately (keyed by provider).
- **API key — never persist it.** Applies to the OpenAI key (gpt-image / openai TTS) AND the
  **MiniMax key** (`MINIMAX_API_KEY` / `~/.minimax_key`). Request it fresh each run and pass it ONLY
  via the env var (or `imagegen.py --key`) for that one call. NEVER write any key into
  `storyboard.json`, any script, the `.assets/` manifest, a log, or any committed file — the scripts
  keep it only in the request header, nowhere on disk. If the user pasted a key into the chat, remind
  them to rotate it (the transcript retains it).
- **Pacing — keep cuts moving.** Don't let one frame linger: aim for roughly ≤8s per scene,
  especially image/b-roll (a held static image reads as sluggish even with Ken Burns). If a
  scene's narration runs long, split it into shorter beats/cuts rather than holding one frame.
- **Informative-first visuals.** A beat that states a fact or concept uses an INFORMATIVE
  visual — `chart`, `compare` (split/versus breakdown), `keypoints` (kinetic labeled points),
  or `timeline` — never a decorative photoreal image. AI photoreal (`image_prompt`/`broll`) is
  allowed as a rare atmospheric opener/closer OR as illustrative accompaniment on a content beat
  where the fact stays as on-page text (e.g. a `.split` page); never as the sole carrier of a claim.
- **Energetic pacing.** Prefer MANY short beats (~3–6s, one idea each; ≈ `video_seconds/4`
  beats) over a few long holds; the animated renderers' internal reveals keep the screen moving.
- **Audio↔visual.** Each narration line must MATCH what is on screen (its beat's visual) — the
  `critic-content` (R2) fails a mismatch.
- **Language is set once, in `meta.language`** — write the narration in that language, and
  let `meta.voice` match it. tts.py auto-picks a matching `say` voice when the language is
  non-English and you left the default (see `references/tts-voices.md` for the per-language
  table). render.py auto-swaps to a system CJK font for Chinese/Japanese/Korean captions;
  if a glyph still tofus, set `meta.font` to a `.ttc`/`.ttf` that covers the script. Confirm
  the captions look right on the rendered **sample** (step 8) — that's where mojibake shows.

## Imagery faithfulness (AI / b-roll / documentary)
Every on-screen visual is one of four classes; `critic-content` (R1e) enforces them:
- **`motif`** — a generic programmatic vector. Always allowed; asserts no fact.
- **`broll`** — a generic illustrative image, including an AI-generated one (`image_prompt`).
  Allowed ONLY as generic/atmospheric backdrop — no real logos, faces, named vehicles, or
  in-image text, and it must not sit as "evidence" beside a specific factual claim. **It must
  also be TOPICALLY RELEVANT to the video** — its motif evokes the subject (the "generic" rule
  forbids fabricated *specifics*, not the subject itself). Topic-neutral filler (random paper,
  a generic gradient, an unrelated stock scene) is a defect even though it is "faithful"; the
  imagery should look like it belongs to *this* video, not any video.
- **`documentary`** — a REAL, license-clean image (photo/map/diagram) of the ACTUAL named subject,
  fetched from Wikimedia Commons via `scripts/imagefetch.py` (CC/Public-Domain only). BECAUSE it is
  real + sourced, it is allowed to DEPICT the real thing and demonstrate the point directly (a real
  rail-network map, a real cityscape, a real crowded station) — the one image class that may show a
  named real subject. Requirements: (1) a genuine `doc_query` naming the subject (a wrong image is a
  faithfulness break); (2) an on-screen **`.credit`** attribution line (CC-BY requires it; the sidecar
  `.json` carries license/artist); (3) numbers/claims still live in on-page TEXT — the image shows the
  subject, the text asserts the fact. Reach for it on CONCRETE topics; treat it to match the deck
  (`imagefetch.duotone`) on a non-photographic style. Not for abstract topics (use `broll`/`none`).
- **`asserted`** — an AI image FABRICATING a specific named vehicle/mission/person/event/figure. NOT
  allowed (that's precisely what `documentary` exists for — fetch the real one instead of inventing it).
DATA always stays in faithful HTML/`chart` components — never render numbers/figures as an AI image.
The full-AI escape hatch (`image_source:"openai"` with data as AI) is the user's call, but the
`critic-content` flags every data-bearing AI scene.

## Brand assets (user-supplied real logos — the DOCTRINE SPLIT)
`meta.brand` (Guardrails has the block) places the user's OWN real logo. Two complementary rules,
not in tension: **user-supplied real logos are placed VERBATIM** — never stretched (preserve
aspect), never recolored, no shadows/effects, clear space respected — while **generated imagery
still NEVER fabricates a logo** (broll stays logo-free, exactly as the imagery doctrine says).
Cover/endcard lockups are authored into the first/last HTML pages (`references/html-pages.md`
"Brand lockups"; the design-director owns placement); the corner `bug` is the only render-drawn
brand mark. **Slide-image tier (pptx ingest):** master-slide logos arrive already baked into
`frames/` — render adds NO cover/endcard branding there; the `bug` is the only brand path render
adds on that tier.

## When a step fails (if → then → still-failing)

| Trigger | First fix | If it still fails |
|---|---|---|
| `ingest.py`: `soffice` missing / hangs | Kill stale `soffice`; ask user to export the deck to PDF and feed the `.pdf` | Feed a folder of exported slide PNGs instead |
| pptx has no speaker notes | Generate narration from visible slide content + any source docs | Ask the user for the deck's intent per section |
| `tts.py`: cloud voice errors / no `OPENAI_API_KEY` | It auto-falls back to the language-matched say voice (e.g. say:Tingting for zh) and prints a notice — continue | Set `meta.voice` to an explicit local `say:` voice |
| `tts.py`: MiniMax error / no `MINIMAX_API_KEY` | It auto-falls back to the language-matched say voice and prints a notice — continue | Verify `MINIMAX_API_KEY` (region is auto-detected across both hosts); `2054`=voice_id not on account, `1008`=no balance (top up), `2049`=key invalid on both regions; check `voice_id`/`tts_model` exist for your account |
| `tts.py`: **⚠️ MIXED-VOICE RUN** warning (cloud/edge engine fell back to `say` on SOME scenes) | A systemic mid-run failure (MiniMax `1008`, expired key, network) split the deck between two voices — do NOT ship it. Fix the engine and re-run `tts.py`, OR set `meta.voice` to `edge:<id>` (free, consistent) / `say:<voice>` so EVERY scene uses one engine | If the cloud engine can't be fixed, switch `meta.voice` to `edge:*` and re-run so the whole deck is one voice (`meta._tts_mixed_voice` records which scenes fell back) |
| `tts.py`: edge-tts not installed | The workflow offers `pip install edge-tts` once; on decline, set `meta.voice` to a `say:` fallback | tts.py auto-falls back to `say` at synth time and prints a notice — continue |
| `tts.py`: edge-tts network error / endpoint down | tts.py catches it and falls back to the language-matched say voice (e.g. say:Tingting for zh) and prints a notice — continue | Switch `meta.voice` to an explicit `say:` voice (fully offline) |
| `imagegen.py`: no `OPENAI_API_KEY` | It prints a notice and leaves those scenes for free-tier fallback — convert them to programmatic/slide and continue | Set the key (`export OPENAI_API_KEY=...`) and re-run `imagegen.py` |
| `imagegen.py`: image API error / rate limit | Per-scene catch → free-tier fallback for that scene; cached scenes unaffected | Retry later; cached images never re-charge |
| `imagegen.py`: Codex run fails / makes no image | `_generate_codex` raises → that scene falls back to the free tier; other cached scenes unaffected | Force `meta.image_provider:"openai"` + provide a key, or use the free programmatic/HTML tier |
| Image tier on but no codex AND no key | Each scene falls back to the free tier with a notice | Install `codex`, or set `OPENAI_API_KEY` / `~/.openai_key`, then re-run `imagegen.py` |
| `render.py`: concat `-c copy` errors (codec/timestamp) | Re-encode the concat (`-c:v libx264 -c:a aac`) — see `references/ffmpeg-recipes.md` | Render per-slide with `--only N` and report the failing slide |
| Captions/text look wrong or font missing | render.py falls back to PIL's default font (still draws) | Confirm the bundled faces exist — `DejaVuSans.ttf`/`DejaVuSerif.ttf` AND the style faces (`SpaceGrotesk-VF`/`JetBrainsMono-VF`/`PlayfairDisplay-VF`/`Bangers-Regular`, which a themed deck's captions now use; a missing one silently falls back to DejaVu) |
| Captions show tofu boxes / □□□ (non-Latin language) | Set `meta.language` so render.py picks a system CJK font (zh→PingFang, ja→Hiragino, ko→AppleSDGothicNeo) | Set `meta.font` to an explicit `.ttc`/`.ttf` that covers the script |
| Narration mispronounced / wrong-language voice | Set `meta.language`; tts.py auto-picks a matching `say` voice (zh→Tingting, ja→Kyoko, …) when you left the English default | Set `meta.voice` explicitly to an installed voice for that language (`say -v '?'` lists them) |
| Narration overruns the beat's `est_seconds` budget (≈ `target_seconds / beats`) | Tighten wording (`references/narration-writing.md`) | 🔴 STOP and propose splitting the dense slide |
| A/V out of sync (one slide) | Never guess timing — `duration` comes from ffprobe; re-run `tts.py --only N` | Re-render that slide with `--only N` |
| A/V drift across the WHOLE video (audio runs longer than the video, worse later) | Mixed audio sample rates across clips (e.g. a partial edge-tts run left some scenes as `say` .aiff @22050 and others edge .mp3 @24000) → the `-c copy` concat desyncs. render.py pins `-ar 48000 -ac 1` per clip to prevent this; clear `<out_dir>/.clips/` and re-render so every clip re-encodes uniformly | Regenerate ALL audio with one engine (delete `audio/`, re-run `tts.py`) so the voice is consistent too, then clear `.clips/` and re-render |
| step 8 critic-av returns REVISE | Read the issue (illegible/mistimed burned caption / off-theme or tofu render / player-chrome) → fix the cause (fix the page/theme, clear `.clips/`, re-render sample) and re-dispatch `critic-av` until it passes, before the 🔴 sample sign-off |
| step 1 `doctor.py` reports a REQUIRED dep missing (ffmpeg/ffprobe/PIL) | Install it (e.g. `brew install ffmpeg`, `pip install pillow`) before proceeding | Optional gaps (edge-tts/soffice/Chrome) only narrow the tiers — adjust the interview, don't block |
| step 9 gate fails: `validate.py` exits non-zero before render | Read each ERROR (missing image/audio/page/`file://` asset, duplicate index, absent `theme.css`) → fix in `storyboard.json` / regenerate the missing asset (run `theme.py`/`imagegen.py`/`tts.py`) | Re-run `python scripts/validate.py <out_dir>` until exit 0 before calling `render.py` |
| step 9 gate fails: `check_av.py` exits non-zero after full render | Read the issue (A/V drift / non-uniform clip rates) → fix the cause (clear `.clips/`, regenerate audio with ONE engine, re-render) | Re-run `python scripts/check_av.py <out_dir>` until exit 0 before delivering `out.mp4` |
| `keyframe_qa.py` exits non-zero (BLANK page / canvas overflow) | Open `_keyframes/scene_NN.png` — BLANK → the reveal never fired (broken page / cue never resolves); OVERFLOW → shorten the text or split the beat | Re-run until exit 0; the centered-paragraph advisory never blocks |
| `validate.py`: "only ~N% complete when the render cuts" (a connector/bar frozen mid-flight) | The element's cue fires too late for its `animation-duration` to finish. Set the inline duration validate prints (= remaining − 0.15s), e.g. `style="animation-duration:1.1s"` on that `.draw` path — prefer this to re-anchoring, since a connector drawn BEFORE its phrase spoils the payoff | If the shortfall is large (<60%), the beat is over-stuffed: move the anchor phrase earlier in the narration so the line still has ~1s to run after it. Confirm on `_keyframes/scene_NN_shipped.png`, NOT the `?p=` sheet — the blind sheet always shows animations complete |
| Timed callout appears at the wrong moment / never appears | Check validate.py's cue warnings — the `cue` must be a phrase the narration says (with a non-edge voice the time is a text-position estimate); `at` ≥ 1.0 puts it exactly at clip end (invisible) | Set an explicit `at` fraction, or drop `cue`/`at` for a whole-slide highlight |
| Reduced-motion render flagged as static / tools still assume zoom | Set `meta.reduced_motion: true` in the storyboard (the CLI flag isn't persisted) and STATE the mode when dispatching critic-av — static frames are correct there, not a defect | validate.py skips its zoom warnings when the meta flag is set |
| Slide "shivers"/jitters during the zoom | zoompan runs supersampled (`meta.motion_ss`, default 2) then downscales; a `scale` filter must precede zoompan or the frame shrinks. Keep ss≥2 | Raise `motion_ss` to 3 (smoother, slower) |
| Caption is one static line per slide | Captions auto-derive from `narration` — split into sentence chunks timed across the slide; a single full-span entry in `captions` is overridden by the narration track | For custom timing, supply a multi-segment `captions` array |
| `render.py`: no Chrome for an `html` scene | `render_html` errors clearly; set `meta.chrome_path`, or switch those scenes to the free programmatic tier (title/chart/keypoints/compare) | Install Google Chrome, then re-render |
| `html` page renders blank / unstyled | Confirm the page links `assets/html/base.css` + `theme.css` (from `out_dir`) + `seek.js` by ABSOLUTE `file://` path; no external/network assets | Open the page in a browser to debug, then re-render (the cache busts on edit) |

For anything else, read `references/troubleshooting.md` before guessing.

## Red lights — never do this

- ❌ Render audio/video before the user signs off script/sample (honor the 🔴 checkpoints).
- ❌ Narrate from the slides alone, or invent facts/numbers — ground in the material (or a
  web fact-check) and stay strictly faithful (step 3).
- ❌ Skip the critic panel — the parallel `critic-narrative` + `critic-content` + `design-critic` check (step 5) is REQUIRED; ship only when ALL THREE return PASS.
- ❌ Read slide bullets aloud verbatim — write *spoken* narration (`references/narration-writing.md`).
- ❌ Guess a slide's `duration` — it must come from ffprobe via `tts.py`.
- ❌ Hand-edit `out.mp4`; change `storyboard.json` and re-render (`--only N`).
- ❌ Add callouts/emphasis boxes by default — they're OFF unless the user asks; never stack them.
- ❌ Write the OpenAI API key into the storyboard, a script, the manifest, or any persisted/
  committed file — request it fresh each run, pass it only via `OPENAI_API_KEY`/`--key`, and
  remind the user to rotate a key they pasted into the chat.
- ❌ Let a single static frame linger (one long held image reads as sluggish) — keep cuts
  moving (~≤8s/scene), splitting a long scene into shorter beats rather than over-holding.
