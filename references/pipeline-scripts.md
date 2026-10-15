# Pipeline scripts — full reference

Moved verbatim out of SKILL.md's "Pipeline scripts" section (2026-10-10). SKILL.md keeps a one-line index per
script plus every rule that binds at the moment a step runs; this file holds the full text: field semantics,
flags, the measured history behind each rule, and the library-maintenance tooling. Read the entry for a script
before you change how you call it, set a `meta.*` field it reads that the index does not explain, or act on a
finding it prints that you do not understand.

- `scripts/ingest.py <input> <out_dir>` — pptx/pdf/image-folder → `frames/` + skeleton `storyboard.json` (pulls speaker notes from pptx).
- `scripts/tts.py <out_dir> [--only N]` — narration → `audio/` + real durations. With edge-tts, also writes `audio/NN.words.json` (per-word start times), used for audio-synced HTML reveals; emits `.mp3`. With macOS `say`, emits `.wav` (rewrapped from say's AIFF, which the Remotion tier cannot read; no words.json). **`tts.py` REWRITES `storyboard.json`** (to store each clip's measured duration) — so run it (and any duration-editing pass of your own, e.g. tail-padding) **BEFORE you hand-set per-scene fields like `transition`**, or a later re-synth/duration pass that loads-then-saves the board will silently clobber those edits. Order: finalize audio & durations → THEN set transitions/motion → validate → render (render only READS the board, so it's safe after).
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
- `scripts/dna_from_deck.py <out_dir> [--pptx deck.pptx] [--mode light|dark] [--dry-run] [--force]` — the
  remotion tier's **Design DNA from the deck's OWN theme**: reads the pptx theme (`scripts/pptx_theme.py`:
  scheme colours with sysClr resolved, major/minor typefaces, the master ground through its clrMap, the master
  most slides use) and the rendered frames (pixel-weighted, spread through the deck), and writes a complete
  `meta.design_dna` object with a `provenance` block naming where each token came from. Ground from the
  frames, ink at WCAG 7:1, a custom theme's accents at 3:1 with the hue kept, typefaces classified onto the
  faces `runtime/fonts.ts` bundles (the deck's Calibri cannot ship, its class can), the form grammar following
  that class. An Office-default theme is detected and demoted so no film goes Office-blue by accident. Never
  overwrites an authored DNA object (`--force`); fails loudly with nothing to derive from. Run it after ingest
  and before the shot-director, which retunes the object; `validate.py` warns when a custom-themed pptx ships
  under a preset. The html tier's `theme.py` is untouched — its palette still comes from frames/logo/flags.
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
  "Transition rhythm". **A DEPTH seam — `transition_in:{type:'focus'}`:** the rack-focus hand-off, the only cut in this
  vocabulary that happens in DEPTH rather than in the plane. The leaving beat slides OUT of the focal
  plane while the arriving one pulls INTO it, STAGGERED (they must not start on the same frame — that
  reads as one blurred screen, not a hand-off), with the opacity crossing late so the focus carries the
  cut rather than a dissolve wearing a blur. It cannot flash — racking focus redistributes light rather
  than adding any — so it is one of the two seams (with `carry`) allowed across a dark↔light boundary,
  and `seam_plan` routes a CROSSING `payoff` to it. Borrowed, with its parameters, from the
  video-shotcraft library's hand-off case law.
  **The other two DEPTH seams — `transition_in:{type:'through-dark'}` and `{type:'portal'}`:** a FLIGHT
  through darkness (the leaving beat recedes and its light goes out, the frame passes through black, the
  next subject comes forward out of it) and a PORTAL (an aperture opens on the composition's own centre and
  the next beat is already behind it at full size while the leaving one scales past the lens). The flight is
  the THIRD seam allowed across a dark↔light boundary, and it earns it most strongly of the three: the two
  beats never carry light at the same time, so no bright frame is ever added to a dark one — `seam_plan`
  routes a CROSSING `new-topic` to it, because a bridge line claims continuity and a chapter break is
  claiming the opposite. The portal is deliberately NOT exempt: a bright aperture opening on a dark field is
  precisely the flash the guard refuses, so on a crossing seam it is rewritten to the fade. Only their NAMES
  were recorded in the peer study, so unlike the focus relay their parameters are derived here — see the
  headers in `Film.tsx`. Aliases for `transition_style`: `flight`/`through-black`, `aperture`.
  **BOTH TIERS SPEAK ONE SEAM VOCABULARY (2026-09-20).** `fadethrough` (the same reset as a fade with the
  emphasis on what ARRIVES — leaves in 30% of the seam, the new content gets 70%), `drift` (a cross-fade that
  also travels ~24px in the reading direction) and `blur` (a rack-defocus coda, both beats soft across the
  middle, budget ONE per film) had html pictures and no remotion ones; `push` and `lift` had remotion pictures
  (`slide`, in its two directions) and no remotion WORD, so `transition_in:{type:'push'}` fell through to an
  anonymous fade. All five are now reachable from either spelling through the single resolver
  `render_remotion.seam_type`, and **`validate.py` ERRORS on a seam word this renderer cannot resolve** rather
  than letting the seam go quiet. `drift` and `blur` cross a dark↔light boundary (a translation adds no light,
  a Gaussian redistributes it); `fadethrough` does not. Every seam that fades its LEAVING half — these three
  and the focus relay — paints the beat's own ground under it (E15: two faded layers over nothing composite
  onto BLACK, measured 222 → 13.5 → 222 between two cream beats).
  **Transition STYLE — `meta.transition_style`** (`dip` default | `fadethrough` studio-timed dip |
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
  **Caption placement — `meta.caption_mode` (DEFAULT `overlay`):** the subtitle sits directly on the frame's
  own ground — no strip, no white/black halo, ink = the deck's own content colour for that ground, outline =
  the sampled ground; authors MUST keep content out of the bottom caption band (`caption_band_px`: 200 px ≈ 18.5% at 16:9, 257 px on 9:16/1:1/4:5 — keyframe_qa's finding prints the exact edge). `band` is the opt-in footer strip
  (`meta.caption_band` `flush` | `contrast`). The full rule and both modes live in `references/captions.md`
  "Placement". `meta.caption_scale` (default 1.0) tunes the caption font. Same rule on the remotion
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
- `scripts/render_remotion.py <out_dir>` with **`meta.renderer:"remotion"`** — the **cinematic tier**
  (recommended for launch / promo / story — NOT for every video; `scripts/tier_advice.py` decides from the
  purpose and topic, see interview ③): a **bespoke-shot LIBRARY** where every beat is a hand-written, topic-driven design language (the
  registers catalogued in `remotion/LIBRARY.md`), sequenced into a narrated film with cross-dissolve
  transitions + scene-relative captions + per-scene edge-tts narration (served via `--public-dir=<out_dir>`).
  **IT RENDERS ONE BEAT AT A TIME AND KEEPS WHAT DID NOT CHANGE** (`scripts/remotion_segments.py`). Each beat's
  share of the timeline — from the seam into it to the frame before the next beat — is rendered from the SAME
  props with `--frames`, so it is the same film by construction, and kept in `<out_dir>/.remotion_segments/`
  under a key of everything those frames depend on (the beat and the one before it — its tail plays under the
  seam — the film-wide props, the content of every file a prop names, the absolute frames, the code). Video is
  joined by stream copy; audio travels as lossless PCM, joined sample-exact and encoded once. Measured on the
  37-beat job-hunt film: all 5362 frames ≥44 dB PSNR against a one-pass render, every beat's voice within
  ±0.33 ms of it (a one-pass render rounds each beat onto a whole millisecond and starts its whole track
  42.7 ms late — AAC priming it never trims; the joined film places each beat on its frame). What an edit
  costs: a **visual** edit (a prop, a register, a ground, a seam — the shot-critic loop) re-renders that beat
  and the next — **43 s** end to end, keyframes included, against **6:20** for the whole film; a **narration**
  edit changes that beat's length and re-renders **every later beat**, because the Atmosphere under the film
  pulses on the absolute frame and nothing guarantees it is covered (open-work D4). The first render is ~25%
  slower than one pass (**7:55 vs 6:20**: each segment pays a browser start-up; the bundle is built once). A
  render that dies keeps its finished beats — re-running is a resume. **`python3 scripts/remotion_segments.py
  <out_dir>`** lists which beats the next render would redo, read from the board as it is now. `--whole`,
  `meta.segment_cache: false` or `REMOTION_SEGMENTS=0` render in one pass as before; a disagreement between
  the segment model and the film is never shipped — it is reported and the film is rendered whole.
  **DEVICES AND THE PRODUCT'S OWN SCREENS.** `DeviceDemo` performs one operation — type, tap, scroll, drag — on
  a phone, tablet, laptop or monitor showing the user's own screenshots or recording, each step on the words
  the narration says; `DeviceHero` shows the product on its device with one screen whole. The step script is
  written in `shot_props.steps` and checked and scheduled by `scripts/device_script.py` (text targets are found
  in the screenshot on a Mac; too many steps for a beat is refused in seconds). The step format — targets as
  fractions of the visible screen or recognised words, cues, the time each step needs, what a recording allows —
  is the **Step script** section of `remotion/cards/DeviceDemo.md`. Spec:
  `docs/superpowers/specs/2026-09-26-device-layer-design.md`.
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
  **FOCUS is the depth cue that says which one matters (`runtime/focus.ts`).** `focusAt(d, U)` returns one
  recession — opacity, blur, brightness and scale together, blur as a fraction of the frame's short side — so a
  film's off-focus material recedes the same way in every shot instead of each one inventing three numbers;
  `focusFilter` returns NOTHING in focus, so sharp type is never promoted to a filter layer. Reach for it
  whenever a shot shows several things and means one: `SurfaceCarousel`'s corridor, and `PointerTour`, which
  needs it most — a flat interface under a moving camera reads as a page scrolling until the part the lens is
  not on goes soft.
  **SOUND — a register can read the film's own narration (`runtime/voice.tsx`).** `<Voice samples={n}>{({bars,
  level}) => …}</Voice>` analyses the BEAT's mp3 (the Film provides it; nothing to author), so an audio
  register goes quiet when the speaker does. Standalone stills and the energy sweep get a deterministic
  synthetic voice with the same shape, gaps included, so the still stays evidence about the film.
  `VoiceSignal` (a mirrored bank) and `SpectrumPulse` (a ring) are the worked examples.
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
  44px caption is 2.3% of a 1920-wide frame and 4.1% of a 1080-wide portrait one), plus **a prop the register
  declares and never reads** and **a prop default it also writes as a bare literal** — two shapes of the same
  lie, in which the film's copy is accepted and silently discarded while a hardcoded word draws instead.
  A test ratchets the count so the library cannot regrow it. **Never invent a number** — a readout comes from props or is
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
  **ICONS ARE THE DEFAULT ON A LABELLED LIST.** `remotion/src/runtime/icons.tsx` is one coherent line family
  (same 24-grid / 2-stroke / round caps as the html tier, so both read as one system). Before it, a register
  with a list drew an abstract mark chosen by INDEX — the same four shapes in the same order on every film,
  whatever the labels said. Pass `icon` per entry (`panels[].icon`, `items[].icon`); `shot_proof` WARNS on a
  labelled list of 2+ entries with none, and the reasons that survive are categorical (a headline figure the
  icon would compete with, a motif-dominant frame), never "it looked fine". See
  `references/remotion-shot-authoring.md` "Icons".
- **Editing the library itself** (a register, `runtime/`, or a gate) — walk
  `references/engineering-case-law.md` before committing: E-numbered case law, each rule carrying the commit
  that repaired the incident behind it, reported as `En ✓` / `En ✗ (where)`. `critic_ledger.py` parses the
  hashes and a test resolves every one against this repo's history, so a fabricated precedent cannot be
  committed.
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
  no-fabricated-stats). `validate.py` ERRORS on a missing/unknown `shot`, and on a partly-filled beat that leaves any copy prop
  to its demo default (the register's illustrative text renders as content — a real film shipped six English
  demo labels onto a Chinese frame with every gate green; `scripts/demo_copy_qa.py <out_dir>` lists them, and
  the FOUR evidence registers — PhotoPlate/ScanReconstruct/RealVersus/MuseumLabel — REFUSE to render without a
  real image rather than drawing an empty plate). Each shot is standalone-renderable
  (`cd remotion && npx remotion still src/index.ts <Id> out.png --frame=N --gl=angle`) and topic-driven via
  `--props='{...}'` (ASCII only — a multibyte `·` breaks the CLI arg). **`meta.sound_design:true`** (opt-in)
  adds a restrained SFX bed under the VO: transition whooshes pinned frame-exact to the marked seams, and the
  film's one **closing sentence — riser → impact → sparkle** (a 35-frame build that crosses the last cut, the
  landing on the close's arrival as the film's loudest SFX, a 25-frame afterglow), the shape a mature peer
  library pins its payoff with. Cues are chosen by PICTURE KIND (a move, a landing, a build, a glow), never by
  UI event — event-semantic clicks/bells read as a game, which is why the close no longer rings a bell. The
  impact's body lives under 110 Hz, so the SFX bus is split in-graph into a >800 Hz band and a <110 Hz band,
  both outside the voice's 300 Hz–3 kHz (measured: the low bus adds nothing there). `meta.bgm` (a path or
  `"auto"` synth pad) scores it, and a scored film also ships an `out.nobgm.mp4` twin — same cues, same
  frames, no music — so the user can score it themselves without a re-render. **Audition it before delivery
  (the pipeline can't hear it).** **"Frame-exact" is now MEASURED, not assumed:** the cue times were computed to the frame
  (a seam whoosh lands 2 frames EARLY on purpose) and then handed to an encoder nobody had checked, while the
  only audio gate (`check_av`) compares total stream durations with a 0.3s tolerance — nine frames, and blind
  to where a cue sits against its cut either way. `mix()` now sends a click through the real filtergraph
  before every mix and subtracts whatever it finds, so a different ffmpeg or an added filter is corrected for
  instead of silently shifting the bed; `python3 scripts/sfx.py --calibrate` prints the number and exits
  non-zero past half a frame. Measured on this chain it is **0.000 frames** — the reference implementation's
  1.27-frame AAC-priming compensation is THEIRS, and hardcoding it here would have introduced the error it
  was meant to remove. Needs the Node toolchain (one-time `cd remotion && npm install`); the html/local tier
  (`render.py`) is untouched by this path.
  **CAMERA BED (OFF by default — `meta.camera_bed: true` turns it on):** a beat with NO authored `camera` drifts gently instead of
  sitting dead — a slow, monotone lateral pan (`depth.tsx bedPan`; the Ken Burns floor the html tier has
  always had), edge-safe and caption-bounded by construction, at 45% of the camera cap so the seam_plan
  punctuation (push/pull with causes) stays legible above it. Measured: the reference 6-beat film went
  0.0035 -> 0.0042 motion_p75 (over the 0.0037 floor) with shake_qa wander 1.46 and local flicker DOWN.
  **That figure did not reproduce.** Re-measured as a controlled pair (the same six-beat cut of a real film,
  rendered twice, the bed flag the only difference) it is worth **+0.0001 on p75** — 0.0025 vs 0.0026, 4%
  not 20% — while drifting every beat that has no authored camera. Hence opt-in.
  An authored camera (even `hold`) wins outright; un-themed films are pixel-untouched (null-DNA rule);
  reduced motion zeroes it; it refuses to coexist with `meta.camera_drift`; **It is OFF by default** — shipped as the default it drifted 21 of a film's 25 beats and read as
  the type sliding sideways for the whole runtime (the motion number rose; the film looked worse). `meta.camera_bed: true` is the
  film-wide opt-IN (render_remotion passes `cameraBed` only when the board sets it to `true`).
  **FINISH (film optics, DEFAULT ON for themed films):** every themed film carries a photographic finish —
  deterministic grain, corner falloff, a key-light direction — from `design_dna.finish` (preset-tuned in
  `remotion/src/runtime/dna.tsx`; an authored partial DNA inherits the mild NEUTRAL default through coerceDna).
  It is STATIC by construction (not the withdrawn light ARC — nothing pumps or drifts), mounted below the
  caption; opt out with `design_dna.finish: "none"`; un-themed films get nothing (null-DNA rule). Costs ~12ms/frame.
  **Aspect:** the Film Composition is aspect-driven — `meta.aspect` (`16:9` default · `9:16` · `1:1` · `4:5` ·
  `4:3`) or `--vertical` renders portrait `1080×1920` etc. (Root.tsx `calculateMetadata`). Shots author in W/H
  FRACTIONS so they reflow; **on a non-16:9 film the shot-director must still-render each chosen shot at that
  aspect and fix/swap any that don't reflow** (multi-column must STACK in portrait; wide elements must not run
  off-frame) — see `references/remotion-shot-authoring.md` §A.9. Most centered/stacked/chart shots reflow as-is;
  the library's fixed multi-column + wide-horizontal registers need this per-shot pass.
  **That pass is now MECHANICAL, and it is not a rare problem.** `python3 scripts/text_safe_qa.py --library
  --aspect=9:16` measured **68 findings across 24 of 149 registers** where 16:9 reports zero — every one a
  LEFT/RIGHT cut, i.e. a 1920-wide layout that never narrows. About one register in six is unsafe in
  portrait, so "it reflows" is a claim to verify per beat, never a property of the library. Delivery is
  already covered — `text_safe_qa <out_dir>` audits each beat at the board's own `meta.aspect` — but run the
  library sweep BEFORE promising a vertical film, so the shot-director picks from the safe pool instead of
  discovering the cuts at the gate.
  **`meta.renderer:"remotion"` is an ALIAS for `remotion`** (both render the bespoke-shot library). The old
  generic-scene tier was REMOVED in the phase-3 cutover — `"remotion-legacy"` now errors with a migration hint.
- **Design-DNA tooling (remotion tier).** `python scripts/dna_audit.py [--depth]` — which registered shots read the
  film's Design DNA and HOW DEEPLY (deep / partial / ground-only); it also fails `--check` on a shot that calls
  `useDNA()` without importing it (a hard render crash a presence-grep would score as migrated).
  `python scripts/dna_smoke.py [--template <direction>]` — renders EVERY registered shot once in one themed film;
  the only gate that catches a hook inserted into the wrong scope, since the bundler strips types unchecked. Run it
  after any bulk shot change. `python3 scripts/measure_ground_luma.py --check` — verifies `shotLuma.ts`'s
  `DNA_GROUND_TOKEN` (WHICH DNA token each shot paints its ground from, so captions contrast-pick against the
  ground the frame ACTUALLY has) against 160 renders. `gen_dna_ground.py` is RETIRED and exits 2: it wrote a
  BOOLEAN set meaning "grounds on the DNA", which was then read as "…so its luminance is luminance(dna.bg)"
  — false for any shot grounded in another token, and its `--check` compared the file against its own
  detector, so a detection gap was invisible by construction. `scripts/dna_migrate.py` / `dna_migrate_bg.py` are the guarded migration codemods.
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
- **Before authoring or critiquing a remotion beat — and ALWAYS when a film measures as inert, when a gate blocks a full-bleed / cropped-type frame, or when you are about to argue about what "cinematic" means — read `references/launch-film-study.md`.** Four official launch films (Apple / OpenAI / Figma / Anthropic) downloaded and measured with one instrument against a film this skill delivered: which of them a DOM compositor can actually reach (Figma's — it is fully generative and tops the motion and light columns), the three moves to steal, why the old action-safe gate was inverted, and — the part that costs the most to relearn — the five ways a frame passes every energy floor and is still not finished.
- `scripts/text_safe_qa.py <out_dir>` (or `--library`) — the **TEXT-SAFE gate** (remotion tier): asks the DOM, at each beat's settled frame, whether any TYPE is cut off by the canvas. It replaces `frame_safe_qa`'s EDGE-BLEED **error**, which was measurably INVERTED — the three registers whose type is genuinely cut read 1.00%/1.45%/4.40%, all UNDER its 4.5% error floor, while four deliberately full-bleed registers (9.6–35.2%) were all blocked, as would be 100% of the sampled frames of OpenAI's launch film, 57% of Figma's and 57% of Anthropic's. Coverage runs OPPOSITE to the defect, so no threshold fixes it. A **deliberate** frame-break needs no waiver: text clipped by an `overflow:hidden` ancestor SMALLER than the frame (a marquee, a mask, a crop window) is the author's intent, and a travelling world or a character texture marks its layer `data-bleed` with a written `data-bleed:` reason beside it (a test requires the reason). Full-bleed GRAPHICS are never a finding — only type can be destroyed by an edge. **This is what makes Figma-grade framing legal here**: full-bleed, floods, and type cropped by a container are now shippable.
- `scripts/text_safe_qa.py <out_dir> --glide` (or `--library --glide`) — the **TYPE-GLIDE census** (remotion tier, runs in `critic_brief`'s machine gates): every frame is rendered with no picture taken and the DOM is read for type that crawls under an axis-aligned matrix, which Skia draws as a hold and then a whole-pixel jump (the "字体会有很轻微的抖动" on a camera push). ERROR at 3+ steps in one crawl, WARN at 1-2. Fix: pass the moving transform through `glide()` (`runtime/glide.ts`) over the span it moves in — inside any blur/drop-shadow. ~35 s on a 75 s film.
- `scripts/text_safe_qa.py <out_dir> --sync` — the **SYNC gate** (remotion tier, in `critic_brief`'s machine gates; the html tier runs the same audit inside `keyframe_qa`): the same census, read per beat for WHEN each on-screen text element first becomes readable (opacity ≥0.5, half its box visible, its words already typed) against when the narration first says it (`audio/NN.words.json`; CJK runs ≥2 content characters, Latin words, numbers — Chinese numerals read as numbers). LATE past 0.6 s is a WARN, past 1.5 s an ERROR; more than 3 s EARLY is a spoiler WARN. Text the voice never says is skipped. **The remotion fix is automatic:** `render_remotion` measures the film on its registers' own clocks and gives each beat a time WARP (`Film.tsx` `BeatClock`, knots in `sync_warp.json`) so a register's entrance lands on its word — register files untouched, seams and the opening never warped, speed held to 0.4–2.5x, identity when nothing is off, re-derived when anything it depends on changes. A board can say `"sync": "off"` (meta or slide) or give `"sync": {"anchors": [[voice_s, register_s], ...]}`; registers on the voice or a recording (`runtime/voice`, `runtime/screen`) and beats timed by `{"cue": ...}` props are never warped. **A warp cannot REORDER**, so an item the voice names before the ones the frame shows ahead of it is cued on its own: `film_props` hands each beat whose register imports `runtime/cue` its `cues` — every text item in its props (`caption`, `labels.0`, `parts.2`…) matched to the narration with the audit's own matching (`sync_qa.item_cues`) — and the register starts that item early enough to read on its word, never later than its own slot, through the warp (adopted by OpenQuestions, TechnicalPlate, ObjectStage, PhotoPlate, KSpaceToPicture and the workshop shot scaffold; not under `sync: off` or `sync.anchors`). What is still late stays an ERROR: time the item through `cue.win` (references/remotion-shot-authoring.md), time the register by a cue prop, or move the text.
- `scripts/density_advice.py <out_dir>` — **which beats are STARVED, and what the same family offers**. The density axis is the one that has not closed (a delivered film measured 5.2% median ink against Apple's 24.3%), and four candidate SHARED levers were built, measured and refuted — the container-fill token, more content per beat, and a divided ground painted either under the shot or through `bgGrad` (that last one worked on the number, 5.7%→14.4%, and was reverted after looking at it: the register's content ignores the boundary, so it renders as a coloured margin). Density is per-register work. What generalises is DIRECTION: every design family holds both starved and dense registers (family F spans 1.3%→63.9%, A 1.7%→47.9%), so a starved beat usually has a denser neighbour on the SAME shelf, which is the one substitution that does not change the film's visual language. **It names candidates, never instructions** — a register is chosen because it ENCODES the beat's idea, and swapping to whatever measures densest is how a film ends up carrying ink no viewer can decode. Run it after the shot-director, before the render.
- `scripts/clock_qa.py` — the **CLOCK diagnostic** (library-wide, no render needed). `useT()` returns 0→1
  across the WHOLE clip, so `Math.sin(t * 2)` is two radians in five seconds — a third of one cycle. The
  constant reads like radians per second and is not, so a register authored to keep breathing renders as a
  slow one-way drift. It reports the INTERSECTION of a stalled cyclic driver with a register measuring under
  the motion floor (a stalled driver alone is not a defect: 0.61 of a hue rotation is 220° of visible
  colour), tells `clamp01(t*4)` title fades apart from real oscillators, and reads the modulus (`(t*0.6) %
  (1/16)` is 9.6 cycles, not 0.6). The fix is `radians()` / `life()` in `runtime/motion.ts` — say the period
  in SECONDS; both enforce a 3s floor by throwing. **Its findings are CANDIDATES, not work orders**: render
  the register before and after and keep the change only where the settled-half motion moves (three of four
  were reverted this way). It is a FIDELITY fix, not the motion axis's lever — that is the camera bed.
- **ARRIVALS have weight — `springAt` / `useSpringAt` (`runtime/motion.ts`).** 160 registers animated with
  hand-rolled cubics, so every element in every shot landed on the same curve. Three presets name the three
  jobs — `SPRING_LAND` (arriving), `SPRING_SEAT` (taking its place in a row), `SPRING_POP` (appearing, and
  deliberately past 1.0) — and the OVERSHOOT is the point: a thing that settles past its mark has mass, one
  that eases into place has been faded in. They run on `useT`'s window via `useAnimSpan()`, so a spring is
  settled across the frames the cross-dissolve runs over, and freezes under reduced motion like every other
  clock here. In a stagger loop call the pure `springAt(t, span, fps, delay, config)` — hooks cannot be
  called per item. `SourceDeal` (pills dealt) and `PortRail` (modules seating) are the worked examples.
- **CJK TYPE — the renderer bundles a Chinese sans AND a Chinese serif** (`Noto Sans SC` / `Noto Serif SC`,
  SIL OFL, subset to GB2312 + kana: 2.2 MB and 3.0 MB). Before that, ten Latin faces were loaded and none
  carried a Han glyph, so every Chinese character was drawn by whatever the render machine had installed —
  the same determinism defect `runtime/fonts.ts` exists to end, left in place for CJK. Measured on one
  register across the two DNAs whose display faces differ most: **English 1480 px vs 1573 px, Chinese
  1383 px vs 1383 px** — the Design DNA's typography, the first token it declares, did nothing at all on a
  CJK film. (Width is the wrong metric for CJK, since every Han glyph is one em wide; the proof is shape —
  the same DNA's Chinese title changed at IoU 0.689 once the faces were bundled.) A character OUTSIDE the
  subset would be an empty box beside correct type, so `validate.py` refuses a board holding one and names
  it; Hangul and rare/classical Han are not covered (`assets/fonts/NOTO-SC-SUBSET-NOTE.txt`). The faces only
  do anything if a stack NAMES them: `validate.py` warns when a CJK film's `meta.design_dna` lists system
  families only, because then every Chinese glyph is drawn by whatever the render machine has installed and
  the film is not reproducible. `dna_from_deck.py` puts the subsets at the head of every chain it builds
  (the serif worlds take `Noto Serif SC`) — it did not, which made the one path a real Chinese film takes
  the one path that never reached them.
- `scripts/text_safe_qa.py --library --all-aspects` — the type sweep at **every aspect the renderer
  offers**, and `--only=Id,Id` to iterate on one finding without 160 renders. `--aspect` had existed since
  the portrait work and three of the five supported ratios had never been passed to it: the square sweep
  found **21 registers drawing into the caption band** (a 190px 'DONE!' by 81px; a whole recon panel and
  both its labels printed through the subtitle), 4:5 and 4:3 two more each. The aspect list is READ from
  `Root.tsx` ASPECTS, so a sixth ratio is swept by the run that adds it rather than the run that remembers.
  Looking at those frames also found what the gate cannot: `GaugeCluster` is 580px wide from its centre
  against a 540px half-frame at 1:1, so both side gauges hung off the edge — what is cut there is an ARC,
  and this instrument measures type.
- `scripts/measure_ground_luma.py --check` — the **GROUND-TOKEN gate** (library maintenance, ~15 min: 160
  renders). Which DNA token each register paints its ground from is what the caption ink and the seam guard
  both read, and it is MEASURED, not declared: every register is rendered under a probe DNA whose tokens sit
  far apart in luminance and the frame's border is matched against them. A `bg` ground is rendered again under
  a LIGHT probe: one that stays dark there (a `@dark-world` night) is recorded as the colour it keeps. Run it after changing any
  register's GROUND — the whole table is a claim about pixels, and a claim nobody re-measures is a
  declaration. It also judges the entries it cannot put a token on (a gradient flood, a split screen, a
  register that paints its own stock) by asking whether the DECLARED ground is anywhere near the pixels,
  at the seam guard's own `HARSH_GROUND_GAP` — because skipping those is how `PaperSlot` shipped declaring
  `bg` while printing on `#efe9dd`, and the caption drew #ffffff on it at 1.22:1 under every preset while
  the gate printed "matches the measured pixels (157 shots)" of a 160-shot library. A ground that is not a
  token at all is written as a literal (`PaperSlot: '#efe9dd'`) and checked as a luminance.
  `--luma --check` is the OTHER table (`SHOT_LUMA`, each register on its own defaults, no DNA); they answer
  different questions and both are run.
- `scripts/onscreen_text_qa.py` — library hygiene, exit 0 always. Text a register prints that no film
  supplied, NUMBERS no prop feeds, **props a register DECLARES and never reads**, and **a prop default the
  register also writes as a bare literal** (which makes the prop look wired when it is not). The last two
  were added after `MagazineSpread` declared `sectionLabel`, printed the word FEATURE into its JSX instead,
  and put an English word on a Chinese film's frame that no prop could reach — `validate.py` warns about
  EMPTY props and `shot_proof` compares props with defaults, and a dead prop passes both. Both classes are
  held at zero by `tests/test_remotion.py`.
- `scripts/cjk_type_qa.py --library` (or `<out_dir>`) — the **CJK TYPE gate** (remotion tier, pre-render).
  Renders each register with CHINESE copy shaped to its own prop signature and asks the DOM whether the type
  collides: `leading` (one element's own wrapped lines overlapping — never intentional, an ERROR),
  `overlap` (two elements' type crossing — sometimes the technique, so a candidate), `tight` (wrapped
  Chinese below the library's own `CJK_MIN_LEADING` — nothing collides and there is no air either, a
  report), `orphan` (a wrapped Chinese label whose LAST LINE holds one character — Chinese breaks between
  any two glyphs, so a label a unit too wide for its box drops one onto a line of its own; fix it with
  `textWrap: 'balance'` on that element), and `unmeasured` (drawn on a tilt and unreadable by the orientation-free instrument — an ERROR,
  because nothing is known about it either way). Type drawn on a TILT is measured from font metrics, not
  from client rects: a rect is axis-aligned, so a rotated line's rect is its bounding box, and the rect
  instrument was wrong in BOTH directions on tilted type (a well-set block read as a 148px collision, a
  mis-set one read as clean). A frame that draws almost nothing is arbitrated by asking the DOM which of
  the strings it was fed actually reached the screen, never by comparing its ink with the register's
  demo defaults — and HOW MUCH of the copy vanished decides which of two things it says: half or more gone
  is `unfed` (the fixture never reached the register, an ERROR), a few gone is `dropped` (the register was
  reached and capped a list or hid a conditional panel, a report). **Run it serially.** Four concurrent
  shards reported five registers as render failures that render fine alone, called twelve "drew almost
  nothing" that draw fine alone, and MISSED findings the serial run then reported: a starved render makes a
  partial frame, and every measurement here is of a frame. It exists because a
  delivered Chinese film had two registers set their copy into an unreadable pile while every gate was
  green: `text_safe_qa` asks whether type falls OFF the canvas, and this copy stayed inside the frame. The
  cause is one thing — the library is authored with short English demo strings, and `line-height: 0.82` is
  confident Latin display typography and a collision in Chinese, because Latin glyphs sit inside their em
  box and CJK glyphs fill it. The fix lives in `remotion/src/runtime/cjkType.ts`: `leading(text, latin)`
  raises the leading to `CJK_MIN_LEADING` **only when the copy is actually CJK**, and `fitIfCJK` shrinks a
  size only then — so an English film renders exactly as it did. **Run it before authoring a CJK film**, and
  when adding a register that sets tight leading on author-supplied text. Its positive control is synthetic
  and permanent (`TypeCollisionProbe`), because the first controls were two real registers and stopped
  working the moment both were repaired.
- `scripts/energy_skeleton.py <out_dir>` — the **ENERGY-SKELETON check** (remotion tier, pre-render, no render
  needed). The content-planner declares an `energy` per beat and the library sweep measures a motion per
  register; this prints the declared skeleton against the measured curve and names each beat whose register
  contradicts its energy — a HIGH/PEAK beat on the stillest third, the PEAK under the delivery motion floor, a
  LOW hold on the liveliest third, three kinetic beats in a row, the film's summit off its peak — with in-band,
  unused alternatives from the beat's own intent pool. Learned from a mature peer library's rule "fill the
  skeleton first, then pick the cards": on a delivered film the picker that could not see energy put the plan's
  climax on a register UNDER the motion floor. `validate.py` repeats the findings as warnings; the deterministic
  `shot_director.py` prefers an in-band register and gives the peak the liveliest one (on that film's plan: 5
  hard findings → 0, family variety unchanged). Findings are candidates: a beat's real motion also depends on
  props, ground, camera and length.
- `scripts/shake_qa.py <out_dir>` — the **SHAKE gate** (remotion tier, post-render), and the precondition for
  any work on the motion axis. `film_energy_qa`'s motion score is the p75 frame difference, which rises for a
  push, for a reveal, **and for a frame vibrating in place** — measured on this repo's own renders, a locked
  film scores 0.0036 and the same film with 3px of per-frame jitter scores 0.0077, i.e. shake is the cheapest
  way to clear a 0.0037 floor. This gate separates them by RATIO, not magnitude: it estimates the global
  translation per frame (phase correlation, sub-pixel) and asks, over half-second windows, whether the frame
  is TRAVELLING (path ≈ net displacement, wander ≈ 1) or VIBRATING (long path, no net, wander ≫ 1). Calibrated
  on eight rendered controls — locked / smooth pan / chaotic content / minimal title card all pass; 0.5px,
  1px, 3px jitter and a shaken title card all fail. Content moving INSIDE a still frame is deliberately
  invisible to it (it is about the CAMERA), so animating a register to raise motion can never trip it. A frame
  with no structure to lock onto is reported UNJUDGED, never guessed at.
- `scripts/film_energy_qa.py <out_dir>` — the **FILM-ENERGY gate** (remotion tier, post-render): measures `out.mp4`'s frame-diff p75, median ink coverage and luminance span, and ERRORs under floors set at HALF the lowest of four measured official launch films (Apple / OpenAI / Figma / Anthropic — the table and the derivation are in the script). It answers the one question no other gate asks: **does this film use the fact that it is a film?** Every other gate judges a frame; a 30-beat film once passed all of them while measuring 3.3x under the quietest reference on motion, 5.6x on density and 3.4x on light — i.e. something the html tier could have rendered for a fraction of the cost. A deliberately quiet film declares `meta.energy_waiver` with a REASON (the numbers stay printed as warnings); silence is not a waiver. Its headline leads with COVERAGE — `measured 88.8s of the 88.9s out.mp4 claims` — because the numbers describe the frames ffmpeg handed back and that is not always the file: a truncated delivery once read as a 31s film, `OK 0 error(s)`, exit 0. A short decode is a `COVERAGE` ERROR no waiver can absolve (a waiver is a judgement about a film someone watched; this says the film was never read) — re-render or repair the file rather than reaching for the waiver.
  **`meta.energy_waiver` is PER-AXIS.** It used to be one string that switched off all four floors at once,
  and that shipped a hole within a day of being used: a waiver reasoning about DENSITY silently excused a
  MOTION failure that appeared later from an unrelated change. An OBJECT waives only what it names —
  `{"density": "…"}` leaves motion gated — and a plain string still waives everything but now says so.
  Waive the axis you actually reasoned about.
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
- `scripts/settled_frame.py <clip.mp4|out_dir> <out.png|dir/> [--at 0.90] [--beat N]` — the frame worth
  JUDGING a design on. Every register animates in: type sets word by word, a plate draws on, a stamp lands
  at 0.62–0.78, a counter rolls toward its final string. A frame grabbed mid-clip shows that machinery
  in flight, and produces confident wrong readings — measured on one review pass, from mid-clip grabs:
  "MagazineSpread drops the `deck`" (it fades in at 0.72–0.90), "the climax bar is 3.36:1, under the ink
  floor" (settled: 10.94:1), "StatedBy never draws its stamp" (it lands last, by design). Two of those
  nearly bought a "fix" to correct code. Sample late, at a fixed fraction, every time; `--beat N` finds
  the beat's window in `out.mp4` itself, because the renderer compresses every cut and the board's running
  duration is not the film's clock.

**BEFORE you dispatch an agent to re-pick registers, run `validate.py` and read it.** It answers, in about
a second and in any script, the two questions such a task is usually about: *one register drawing more than
one FORM* names the beats that were cast on resemblance rather than on meaning, and the catalogue-shopping
line reports which declared forms were BUILT versus drawn by a register the library already had. On the film
that motivated this, a 49-minute agent explored five beats and had three of its picks rejected; the gate
names the two that were actually miscast. Diagnose with the cheap deterministic instrument, then spend the
agent on the beats it points at.

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
  construction), a **dead frame** (content spanning <45% of the width), and a **caption that will not read**
  (the film inks a library beat's caption for the ground `DNA_GROUND_TOKEN` resolves to, so a row naming the wrong
  ground inks a caption that will not read; a `@dark-world` register's row is the night it keeps on a light film,
  measured under a light probe). Run it after the
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
  and content reaching into the bottom **caption zone** (`caption_band_px` — 200 px ≈ 18.5% at 16:9 — where an overlay subtitle
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
