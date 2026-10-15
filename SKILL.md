---
name: topic-to-video
slug: topic-to-video
displayName: Topic to Video
version: 1.0.0
description: >-
  Turn ANY topic — or a slide deck — into a narrated explainer short video,
  automatically: researches the topic, writes and voices the script, designs and builds
  the visuals (cinematic Remotion tier or HTML pages; a deck's slides full-frame with
  gentle motion and timed callouts) and burns in captions. Any language; can voice a
  deck in a different language than its slides. Use whenever the user wants a short
  video about a subject or from slides — e.g. "make a video explaining how MRI works",
  "make a launch video for this product", "做一个讲解视频介绍X", "turn these slides into
  a video", "narrate my pptx", "add a voiceover to my slides", "把幻灯片做成视频",
  "把英文幻灯片配成中文解说视频". Accepts a topic, .pptx, .pdf, an image folder, or a
  hand-off from slide-maker. Free by default (edge-tts + ffmpeg); optional cloud TTS.
  Editable storyboard, a sample for sign-off, then the full video. Trigger even
  without the word "skill".
---

# Topic to Video

You turn a topic — or a slide deck — into a narrated short video. Source of truth is `storyboard.json` — you edit
text/timing; the scripts render the media.

## Tools (all free; verify with `scripts/_common.have_tool`)
`soffice` (pptx→pdf), PyMuPDF `fitz`, `python-pptx`, **edge-tts** (preferred neural voice, free, cross-platform — needs network), macOS `say` (offline fallback), `ffmpeg`, PIL.
Captions burn via PIL + a bundled font (no libass needed). Optional: OpenAI/ElevenLabs
TTS if the user gives an API key.

## Pipeline scripts

This is an index. Each line gives what a script is for, when to run it, and the rules that apply at the moment
you run it. The full entry for each script is in **`references/pipeline-scripts.md`**: every flag, what each
`meta.*`/`slide.*` field means in detail, the measured incident behind each rule, and the library-maintenance
tooling. **Open a script's entry there before you** set a field this index does not explain, pass a flag not
shown here, act on a gate finding you do not understand, or edit the library (a register, `runtime/`, a gate).

**Ingest, voice, palette**
- `scripts/doctor.py [--json]`: environment preflight, run once at the START (step 1). It exits non-zero only
  when a REQUIRED dependency (ffmpeg/ffprobe/PIL) is missing, and prints the stage each missing optional tool gates.
- `scripts/ingest.py <input> <out_dir>`: pptx/pdf/image folder → `frames/` + skeleton `storyboard.json` (pulls pptx speaker notes).
- `scripts/tts.py <out_dir> [--only N]`: narration → `audio/` + measured durations. edge-tts writes `.mp3` +
  `audio/NN.words.json` (per-word times, which karaoke, cues and the sync gate need); macOS `say` writes `.wav` and no
  word times. **`tts.py` REWRITES `storyboard.json`**, so run it (and any duration-editing pass of your own, e.g.
  tail-padding) **BEFORE you hand-set per-scene fields like `transition`**, or a later re-synth silently clobbers
  them. Order: finalize audio & durations → THEN set transitions/motion → validate → render (render only READS the board).
  Every clip is mastered in place (EBU R128 I=-14, trailing dead air trimmed, word times stay valid; `meta.audio_master: false` opts out).
  **`meta.scene_pause` (default 0.55 s) is the pause the viewer HEARS between scenes, not the pad.** `tts.py` converts
  it per tier (remotion adds the 0.40 s cross-dissolve overlap, so both tiers sound the same) and targets 1.7× the
  film's own 75th-percentile sentence pause, floored at `scene_pause` and capped at 1.5 s; it prints the number.
  `meta.audio_breath` sets a RAW pad, only for a board that deliberately wants one. **Keep `scene_pause` ≤ ~0.9 s**:
  it is a pause, not a reading buffer (a long tail reads as the video hanging); reading time goes into a slower `meta.tts_speed`.
- `scripts/theme.py <out_dir> [--mode light|dark] [--accent #hex] [--accent2 #hex] [--bg #hex] [--style <key>] [--brand-logo <png>]`:
  topic palette → `<out_dir>/theme.css`, which HTML pages link and the programmatic renderers parse (one colour world).
  **Run it before authoring pages OR programmatic scenes.** Contrast is gamma-correct WCAG: fg/bg ≥7:1, a SAMPLED accent
  nudged toward ≥3:1, an explicit `--accent` never touched. `--brand-logo`, or `meta.brand.logo` when no accent flag is
  passed, makes the logo's hue the accent. Re-run it on an out_dir themed before the contrast fix. Printed/filmic
  styles get fixed-seed grain; a data-heavy page opts out with `<body class="no-grain">`.
- `scripts/dna_from_deck.py <out_dir> [--pptx deck.pptx] [--mode light|dark] [--dry-run] [--force]`: remotion tier.
  Writes `meta.design_dna` (with a `provenance` block) from the deck's OWN pptx theme (`scripts/pptx_theme.py`) and frames.
  Run it after ingest and BEFORE the shot-director. It never overwrites an authored DNA without `--force` and fails
  loudly when there is nothing to derive from. The html tier's `theme.py` is untouched.

**Imagery**
- `scripts/imagegen.py <out_dir> [--key KEY]`: OPTIONAL **paid** step. Generates AI atmosphere art for scenes carrying
  an `image_prompt`, cached under `.assets/`. It acts only when `meta.image_source == "openai"` (`meta.image_provider`
  `auto`/`codex`/`openai`; the Codex CLI path needs no key). The images are backplanes BEHIND HTML pages: never a
  slideshow of generated stills, never text or data, never a stand-in for a real named subject (that is
  `documentary`). `validate.py` enforces all three.
- `scripts/imagefetch.py <query> <out_path> [--prefer W] [--duotone SHADOW HIGHLIGHT]`: the FREE `documentary` tier. Fetches a
  license-clean Wikimedia Commons image of the ACTUAL named subject and writes a `<out_path>.json` sidecar with licence
  + attribution. Helpers: `fetch()` returns None when nothing license-clean exists, `attribution_line()` gives the
  on-screen `.credit`, `duotone()` tones the image into the palette. Reach for it on CONCRETE topics; the design-director
  picks `media.treatment: none|atmosphere|documentary` per beat. **Take the credit FROM the sidecar, never from memory**:
  `validate.py` ERRORS when a beat shows a `media/*` file without crediting its sidecar's author.

**Render: html / image tier** (`scripts/render.py`)
- `scripts/render.py <out_dir> [--sample N] [--only N] [--vertical] [--reduced-motion] [--preview]`: storyboard → `out.mp4`
  + `out.srt`. `--preview` is the cheap iteration render (12 fps, its own cache, writes `preview.mp4`, never touches
  `out.mp4`). Use it while experimenting, and DELIVER the full render. The fields it reads:
  - **Transitions are SEMANTIC.** `meta.transition` (`dip`|`none`) + `meta.transition_seconds`; per scene `slide.transition`
    (`dip`|`in`|`out`|`none`) + `slide.transition_seconds`. Map the beat's `relation`: continuation → hard cut;
    new-topic/payoff/close → an in-edge on the opener PLUS an out-edge on the predecessor (a dip needs both sides;
    validate lints an unpaired edge). `meta.transition_style` (`dip`|`fadethrough`|`drift`|`push`|`lift`|`wipe`|`blur`)
    is chosen ONCE per deck from the register. A transition is a claim about how two beats relate, never decoration:
    budget ~2-3 marked seams per video, never random, no spins, `blur` once per film at most. Both tiers share one seam
    vocabulary, and **`validate.py` ERRORS on a seam word the renderer cannot resolve**
    (`references/motion-grammar.md` "Transition rhythm" / "Transition STYLE").
  - **Captions.** `meta.caption_mode` defaults to `overlay`: the subtitle sits directly on the frame's own ground, with no
    strip and no white/black halo. Its ink is the deck's own content colour for that ground, and its outline is the
    sampled ground. **Authors MUST keep content out of the bottom ~15%**; keyframe_qa gates it. `band` is the opt-in
    footer strip (canvas grows; `meta.caption_band` `flush`|`contrast`). `meta.caption_scale` defaults to 1.0. Karaoke
    `meta.captions_karaoke` (`auto`|`off`) needs edge word times (CJK matched by char-span) and falls back to line chunks
    without them. The remotion tier follows the same rule with no scrim (`references/captions.md`).
  - **Timed callouts.** A callout with a `cue` anchor phrase (or `at` 0..1) appears as its region is spoken and holds to
    the clip end. Untimed callouts show for the whole slide.
  - **Motion.** `meta.intensity` / `slide.intensity` (`subtle`|`balanced`|`bold` or a non-negative multiplier) scale the Ken
    Burns move, clamped under the zoom/pan caps. **`shot` is authoring shorthand: translate it into `motion.from/to/zoom`,
    because render reads `motion`, not `shot`.**
  - **`meta.audacity`** (`conservative`|`balanced`|`bold`|`experimental`) is the register's RISK BUDGET and the
    register-contest width (skip / 3 / 5 / 7 candidates). It **NEVER relaxes the floor**: clarity, faithfulness, WCAG and
    every gate are the same at every level. A register move that breaks one is redone in-bounds.
  - `--reduced-motion` / `meta.reduced_motion`: the accessibility variant (static frames, opacity-only reveals). It busts the clip cache.
- `scripts/scenes.py`: animated programmatic scenes (`type` `title`/`keypoints`/`chart`/`timeline`/`compare`/`html` +
  a typed `props`; `type` defaults to `slide`). They render ONLY their `props`, so they are faithful by construction,
  and they read `theme.css`. `props.climax:true` lands a counter at ~68% and holds it. `props.cue` (one anchor phrase per
  element, in spoken order) lands each bar/node/row as it is spoken. Cues change only WHEN an element appears, never the final frame.
- HTML pages tier: `scenes.py:render_html` captures pages authored on `assets/html/base.css` (`references/html-pages.md`)
  in headless Chrome. For audio-synced reveals, tag each point `data-cue-index="N"` (spoken order) + `data-cue="<spoken anchor>"`.
  `scripts/cues.py` resolves the anchors from edge word times, or estimates them from text position when there are
  none. Capture runs over CDP (`scripts/_cdp.py`) and falls back to per-frame screenshots on its own; tune it with
  `meta.capture` (`cdp`|`screenshot`), `meta.chrome_workers`, `meta.jpeg_quality`.

**Render: remotion cinematic tier** (`meta.renderer:"remotion"`)
- `scripts/tier_advice.py`: decides from purpose + topic whether a film warrants this tier (interview ③). Remotion is for
  launch / promo / story films, NOT every video.
- `scripts/render_remotion.py <out_dir>`: renders the bespoke-shot library (`remotion/LIBRARY.md`) one beat at a time and
  keeps unchanged beats in `.remotion_segments/`. `python3 scripts/remotion_segments.py <out_dir>` lists which beats the
  next render would redo. A visual edit re-renders that beat and the next; a narration edit re-renders every later
  beat. A render that dies resumes; `--whole`, `meta.segment_cache: false` or `REMOTION_SEGMENTS=0` render in one pass.
  `"remotion-legacy"` errors (that tier was removed). Run `cd remotion && npm install` once. Rules on this tier:
  - **The cut has to be authored.** No seam reaches a film unless something writes `transition_in`, so run
    `python3 scripts/seam_plan.py <out_dir>`. From each beat's `relation` it derives ~2-3 MARKED seams (≥5 beats apart,
    luminance-safe) and ~2-4 motivated `slide.camera` moves. An authored `transition_in` always wins. validate WARNS on a
    ≥12-beat film with no mark, or more than ~1-in-8 marked. Only `carry`, `focus`, `through-dark`, `drift` and `blur` may
    sit on a dark↔light seam; any other mark there (`portal` included) is silently forced to a fade. A bespoke direction
    must declare `meta.design_dna.seam` (e.g. `{type:'wipe',direction:'from-bottom'}` or `{type:'fade'}`), or its
    unmarked seams fall through to an anonymous cross-fade.
  - **Camera** is per beat and motivated: `slide.camera:{move:'push'|'pull'|'hold'}` (payoff → push, close/opener → pull,
    else hold). `meta.camera_drift` stays off. The camera bed is OFF by default (`meta.camera_bed: true` opts in) and
    never coexists with `camera_drift`.
  - **Forms come from the subject, not the catalogue.** The shot-director derives 6–10 forms BEFORE opening `LIBRARY.md`
    (`meta.form_vocabulary`). Each beat names its form in `shot_fit.form`, and `meta.idiom_world` declares the provenance
    worlds the film may draw from. validate ERRORS on a missing or undeclared form or world. A derived form with no
    register gets BUILT (`register_shot.py`, the workshop), not approximated.
  - **Only the film's own content goes on screen.** Every word and every number comes from a prop, or is declared part of
    the form (`INTRINSIC_TEXT`, `INTRINSIC_READOUT`). **Never invent a number**: a measurement prop has NO default. A
    register that shows a NUMBER (ChartLive/BeforeAfterSlider/VelocitySnap) MUST get a SOURCED figure. validate ERRORS on a
    missing/unknown `shot`, and on a partly-filled beat that leaves a copy prop at its demo default
    (`scripts/demo_copy_qa.py <out_dir>` lists them). The evidence registers PhotoPlate/ScanReconstruct/RealVersus/MuseumLabel
    refuse to render without a real image. A label beside a point is clamped into its box with `placeLabel()` (`runtime/layout`).
  - **Authoring.** Each scene gets `shot` (a register id) + `shot_props` + `shot_adaptation` `{kept, redesigned, topic_idea,
    theme_cues}`. The adaptation note is REQUIRED: keep the register's style, redesign its modules for THIS topic, never a
    raw text-swap. Vary the FAMILY: no two adjacent beats should read as one look. The deterministic fallback is
    `python scripts/shot_director.py <out_dir>`. On a concrete topic, `PhotoPlate` gives a real photograph the whole frame.
    Icons are the default on a labelled list (`icon` per entry; shot_proof WARNS when there are none). A shot is
    standalone-renderable with `cd remotion && npx remotion still src/index.ts <Id> out.png --frame=N --gl=angle`, and
    `--props` must be ASCII only. Authoring detail: `references/remotion-shot-authoring.md`.
  - **Design DNA** (`meta.design_dna`) is the film's whole visual system. The shot-director expands it first, or a
    preset-mapped `shot_template` auto-applies one. Only 2-3 ANCHOR beats show the style container, and every shot is
    ASSIMILATED into the DNA. `design_dna.motif` is the subject's material: keep it near 0.05. `design_dna.finish` is on by
    default for themed films; `"none"` turns it off.
  - **CJK.** The renderer bundles Noto Sans SC / Noto Serif SC (a GB2312 subset). validate refuses a board holding a
    character outside the subset, and warns when a CJK film's DNA lists system families only. The stack must NAME the Noto faces.
  - **Aspect.** Set `meta.aspect` (`16:9`|`9:16`|`1:1`|`4:5`|`4:3`) or pass `--vertical`. On a non-16:9 film the shot-director
    MUST still-render each chosen shot at that aspect and fix or swap what does not reflow. About one register in six is
    unsafe in portrait, so run `python3 scripts/text_safe_qa.py --library --aspect=9:16` (or `--all-aspects`, `--only=Id,Id`)
    BEFORE promising a vertical or square film.
  - **Sound.** `meta.sound_design:true` is an opt-in SFX bed. `meta.bgm` (a path or `"auto"`) scores the film, and a scored
    film also ships `out.nobgm.mp4`. The pipeline cannot hear, so **audition it before delivery**.
    `python3 scripts/sfx.py --calibrate` measures the cue offset through the real filtergraph and exits non-zero past half a frame.
  - **Devices.** `DeviceDemo`/`DeviceHero` show the product's own screens. The step script goes in `shot_props.steps` and is
    checked by `scripts/device_script.py` (format: `remotion/cards/DeviceDemo.md` "Step script").
  - **Sync.** `render_remotion` warps each beat so register entrances land on their words (`sync_warp.json`). A board or slide
    can set `"sync": "off"` or `{"anchors": [[voice_s, register_s], …]}`.
- **Before authoring or critiquing a remotion beat — and ALWAYS when a film measures as inert, when a gate blocks a
  full-bleed / cropped-type frame, or when you are about to argue about what "cinematic" means — read
  `references/launch-film-study.md`.**
- **Editing the library itself** (a register, `runtime/`, or a gate): walk `references/engineering-case-law.md` before
  committing, reported as `En ✓` / `En ✗ (where)`. Runtime helpers a register author reaches for (`glide()`, `springAt`,
  `radians()`/`life()`, `<Plane>`, `focusAt`, `<Voice>`) are described in the reference and `references/remotion-shot-authoring.md`.

**Pre-render gates and helpers**
- `scripts/validate.py <out_dir> [--pre-tts] [--vertical] [--json]`: the ~1 s storyboard gate (contract, assets, caption
  craft, motion sanity, reveal↔voice alignment, figure traceability, CJK/cue/pacing/anti-slop). Run it BEFORE every
  render, and with `--pre-tts` right after authoring. Errors block; warnings don't. Its animation-TRUNCATION check is the
  ONLY gate that sees a cued animation cut mid-flight, so set the duration it reports. Keep each element to one `style=`
  (a second is silently discarded), and use semantic vars, not raw `#hex`. UI chrome text opts out of figure
  traceability via `data-ui`; never mutate chrome text to dodge the lint. **Before you dispatch an agent to re-pick
  registers, run `validate.py` and read it**: it names the beats cast on resemblance rather than meaning.
- `scripts/rhythm_qa.py <out_dir> [--json]`: pacing gate. Run after tts, before the full render. It is advisory except
  for a MEASURED static frame held past ~16 s.
- `scripts/pedagogy_qa.py <out_dir> [--json]`: teaching-order gate over `content_plan.json`. It ERRORs on a concept used
  before it is introduced. Run at step 9 alongside validate and rhythm_qa.
- `scripts/voice_qa.py <out_dir> [--json]`: narration voice signals (AI-slop vocabulary + rhythm). It is advisory and always
  exits 0. Run it after the script step and after any rewrite, in every language, and read `references/anti-ai-voice.md`
  before writing narration. The last pass is always a human read-aloud.
- `scripts/sources.py add|list|verify <out_dir>`: captures the source text behind each claim into `sources/`, so a
  `source_ref` (`<sid>#<literal quote>`) resolves. `--tier primary|secondary|community|self` (default `secondary`) records
  where the support comes from; `--as-of` dates a time-sensitive fact.
- `scripts/brief_qa.py <out_dir> [--json]`: structural gate on `brief.json`. It ERRORs on a missing required key, a
  `source_ref` that does not resolve, or a non-singular `the_one_thing`, and WARNs on evidence hardness. Run it at step 3.5,
  BEFORE dispatching `content-planner`.
- `scripts/keyframe_qa.py <out_dir> [--p N] [--json]`: HTML-tier visual QA over each page's real cue timeline (filmstrip
  sheets, `_keyframes/all.png`). It blocks a blank opening, a blank page, canvas overflow, in-box clipping and
  caption-zone occlusion; its layout notes are advisory. A scene it could not probe is UNVERIFIED, never `ok`. Run it after
  authoring the pages, BEFORE the full render.
- `scripts/snapshot.py <page.html> <out.png> [--p 1.0] [--vertical] [--no-captions] [--motion clip.mp4]`: renders one page
  and runs keyframe_qa's floor probe; this is the register-contest primitive. Exit 0 clean · 2 floor issues · 3 rendered
  but NOT probed (unusable as a contest verdict) · 1 could not render.
- `scripts/contest_diversity.py <frameA.png> <frameB.png> …`: flags two contest candidates that are "two skins of one idea"
  (exit 2). A flag means rediverge OR keep with a NAMED justification; it never auto-kills a topically right pair.
- `scripts/register_ledger.py record <out_dir> | show`: cross-deck register memory. The contest reads it; the delivery step records it.
- Remotion pre-render, all run after the shot-director and before the render:
  `scripts/shot_proof.py <out_dir> [--no-stills]` is the proof sheet (demo defaults, duplicate pictures, overflow, caption-band
  ink, off-palette colour, dead frames, unreadable captions). Fix everything it reports; passing is a FLOOR, not a verdict.
  `scripts/energy_skeleton.py <out_dir>` checks declared energy against measured register motion.
  `scripts/cjk_type_qa.py <out_dir>` is required on a CJK film; **run it serially**, because parallel shards report
  false failures. `scripts/density_advice.py <out_dir>` names starved beats and denser same-family registers; these are
  candidates, never instructions. `scripts/text_safe_qa.py <out_dir>` is the TEXT-SAFE gate (type cut by the canvas;
  full-bleed graphics and container-cropped type are legal; an intentional bleed layer carries `data-bleed` with a written
  reason). It also runs as `--glide` (type crawling in whole-pixel jumps; fix through `glide()`) and `--sync` (text
  readable late vs. its spoken word; ERROR past 1.5 s).
- `scripts/critic_brief.py <out_dir>`: assembles `_critic_brief.md` + `_contact_sheet.png` for the shot-critic. **Run it
  before dispatching the critic.** `scripts/contact_sheet.py` builds the sheet alone.
- `scripts/settled_frame.py <clip.mp4|out_dir> <out.png|dir/> [--at 0.90] [--beat N]`: the frame to JUDGE a design on.
  Always sample late at a fixed fraction, because mid-clip grabs show animation in flight and produce confident wrong
  readings. Use `--beat N`, since the board's running duration is not the film's clock.

**Post-render gates and delivery**
- `scripts/check_av.py <out_dir>`: A/V gate (duration drift > 0.3 s, non-uniform clip rates). Run AFTER the full render,
  before delivery.
- `scripts/film_energy_qa.py <out_dir>`: remotion FILM-ENERGY gate (motion p75, ink, luminance span against floors derived
  from four launch films). A deliberately quiet film declares `meta.energy_waiver` with a REASON. The waiver is PER-AXIS:
  an object waives only the axis it names; a plain string waives all four and says so. Waive the axis you actually
  reasoned about. A `COVERAGE` error (the file was decoded short) is never waivable: re-render or repair the file.
- `scripts/shake_qa.py <out_dir>`: remotion SHAKE gate (travelling vs vibrating camera). It is paired with film_energy_qa,
  because jitter is the cheapest way to clear the motion floor. A frame it cannot lock onto is UNJUDGED.
- `scripts/critic_ledger.py <out_dir> --final`: the independent-review gate (workflow step 9).
- `scripts/deliver.py <out_dir>` is the hand-off, for EVERY render the user is asked to watch (sample, preview, final
  cut). It copies `out.mp4` + `out.srt` to `~/Desktop` (else `~/Downloads`) and prints the path. Give the user THAT
  path, never one inside this skill, `~/.claude`, or a temp folder.

**Library maintenance** (not part of a film run; full entries in the reference)
- `scripts/register_shot.py <Id> <Family> --use-when "…"` scaffolds a new register at every sync point (`--check` verifies
  one). A new register carries an ARGUMENT SHAPE with the topic arriving through props.
- `scripts/onscreen_text_qa.py` reports hardcoded text, unfed numbers, dead props and literal-duplicated defaults. It
  always exits 0, and tests hold the counts at zero.
- `scripts/measure_ground_luma.py --check` is the GROUND-TOKEN gate (~15 min, 160 renders). Run it after changing any
  register's ground. Also run `--luma --check` for `SHOT_LUMA`, which must be MEASURED, never guessed. `gen_dna_ground.py` is RETIRED and exits 2.
- `scripts/dna_audit.py [--depth|--type] [--check]` reports DNA reach. `scripts/dna_smoke.py`: run it after any bulk shot
  change. `scripts/font_gate.py` proves declared faces load. `scripts/clock_qa.py` lists stalled cyclic drivers; these are
  candidates, and a fix is kept only if a render shows it.
  `scripts/null_dna_pixel_gate.py`: run `--save` BEFORE your change and `--check` after. `scripts/type_specimens.py`,
  `scripts/dna_migrate.py` / `dna_migrate_bg.py` / `dna_migrate_type.py` are codemods and specimens.

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
   any listed item by name — a menu that is naturally ≤4 shows every item as a button. **Ask a question
   at the moment the user can actually answer it.** Screen A (①–④) is asked every run; screen B carries
   ONLY what is genuinely undetermined — ⑥ Grounding when a deck is the only material, ⑦ Brand when the
   topic triggers it — and is skipped when both are settled; **⑤ Voice is asked at the script audition**,
   where the user HEARS the voice instead of choosing an engine in the abstract. Batches 2–3 still fire
   only when an answer triggers them. A common free/default run is ONE option screen, with zero mandatory
   free-text beyond the single topic line on a no-deck run (why: `references/engineering-case-law.md` W1).

   **Batch 1 — core intent + essentials.** Screen A = ①–④, every run. Screen B = ⑥ Grounding (only when
   undetermined) + ⑦ Brand (only when triggered) — skip it when neither applies. ⑤ Voice is asked at the
   script audition (step 5).
   **No-deck (make-from-scratch) runs — capture the topic FIRST:** if the user has a deck
   (pptx/pdf/images) SKIP this (the deck IS the topic); with **no** input deck, before screen A ask ONE
   plain-text line for the **topic sentence** — a plain prompt ONLY because the topic is an irreducible
   free-text VALUE (like a path or a key), not a decision. Keep it to that one line: the goal/takeaway
   is captured by the **① Purpose** menu (don't re-ask it as free-text here), and the sentence becomes
   the source the content-planner + design-director build the deck from. (If the conversation has
   ALREADY surfaced candidate topics/angles, offer THEM as an `AskUserQuestion` menu with "Other" for
   the user's own — only a contextless from-scratch run needs the bare plain line.)
   - **① Purpose** *(→ `arc_kind` + `meta.purpose` + the planner's tone/audience `director_note`)* — what the video
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
     sentence's own language** instead. The narration **voice engine** is question **⑤**, asked at the
     script audition below.
   - **③ Tier** *(→ `meta.renderer` + `meta.image_source`, and whether pages are authored at all)* — which
     renderer makes THIS video. **It is recommended from the PURPOSE and the TOPIC, not offered as three
     looks** — the tiers are three different trade-offs, every one of them measured:

     | tier | what it is best FOR | what you give up |
     |---|---|---|
     | **原样配音 / Voice my deck as-is** — FREE | a finished deck that just needs a voice; nothing redesigned | no new design; points do not appear as they are spoken |
     | **Designed HTML** — FREE (+AI backdrops: PAID) | explainers, how-tos, research briefings, data-heavy material: each point appears **the moment it is said** (`data-cue` on the spoken word) and any table/chart/code/equation is laid out as the content needs; **editing one beat re-renders one beat**; needs only Chrome | less cinematic motion |
     | **Cinematic (Remotion)** — FREE of money, NOT of machine | launches, promos, story and brand: 185 hand-designed shot languages, cinematic seams, one design DNA | points animate on the shot's own clock, not the voice (0 of 185 registers read word timings); **a visual edit re-renders that beat and the next** (43 s on a 37-beat film, against 6:20 for the whole film) but **a narration edit re-renders every later beat**; the first render costs ~25% more than one pass (7:55 vs 6:20); needs Node + its own Chrome + real memory (the same film's one-pass render failed repeatedly at ~1 GB free — per beat, a failure keeps the finished beats) |

     **How to recommend (do this before showing the menu):** ① is on the same screen, so infer the likely
     purpose from the user's request and material, then ask the rule rather than restating it:
     `python3 scripts/tier_advice.py --purpose <p> [--deck] [--data-dense yes|no] [--no-remotion]`.
     Put **"(Recommended)"** on the tier it returns, and its `why` in that option's description. When the
     user's ① answer is a different purpose, re-run with it; if the tier they picked then fights the
     purpose, say the `trade` ONCE, in their words, and let them keep it — this is advice, never an
     override. Record the purpose as **`meta.purpose`** (the ① key: teach/howto/research/overview/pitch/
     launch/promo); `validate.py` repeats the trade-off once as a `tier:` warning if the two disagree.
     Options, in this order (max four): **原样配音** (ONLY when the user supplied a deck — `--keep-deck`;
     the board keeps `type:"slide"` and step 4d is skipped entirely) · **Designed HTML — FREE**
     (`image_source:none` + `renderer:local`) · **HTML + AI backdrops — PAID** (`image_source:openai` +
     `renderer:local`; Batch 3 then confirms the spend + style) · **Cinematic (Remotion)** (`renderer:
     remotion`; the shot-director assigns each beat a `shot`+`shot_props`, reviewed by the shot-critic —
     **show it ONLY when `doctor.py` reports the remotion tier installed**). Make FREE-vs-PAID visible in
     every label and never enable the generator without the user picking the AI tier here. (Other → a
     brand/theme/CSS to match.)
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
     no white halo, content kept clear of the bottom ~15%; see "Captions" under Pipeline scripts and `references/pipeline-scripts.md` "Caption placement"); (Other →
     captions OFF, per-word karaoke highlight, `caption_mode:"band"` for a separate footer strip, or a
     reduced-motion accessibility variant). `meta.target_seconds` is exactly the field the **content-planner** turns
     into beat count (**beats ≈ target_seconds/4**, with per-beat `est_seconds` summed to the target)
     and the design-director reads to scale hero/climax cadence — so it SUBSUMES the old per-slide
     pace ask (a per-slide ceiling, if ever wanted, is just `target_seconds / beats`).
   - **⑤ Voice engine** *(→ `meta.voice`; asked AT THE SCRIPT AUDITION, step 5, where its menu lives)* —
     until then `meta.voice` stays `"auto"`, which resolves to a language-matched edge-tts voice (free), so
     the audition has a voice to speak in; at the audition the user has just heard one and can say "keep it"
     or "try another". A cloud engine (MiniMax/OpenAI) picked there triggers **Batch 2**.
   - **⑥ Grounding material** *(→ how step 3 gets its facts; ASKED ONLY WHEN UNDETERMINED)* — how to
     ground + fact-check the narration (slides/topic alone rarely say enough to narrate *well* — step 3
     depends on this). Most runs already answer it: the user supplied source files/paths/a repo → use
     them, do not ask; ONLY a topic line, no deck → web research is the only way to narrate it well, so
     do not ask — SAY you will research it and that anything they send takes precedence; a deck and
     nothing else → ASK, because "the deck is enough" vs "research the rest" is a real choice. Menu: **I'll share source material** (a paper/PDF, a code repo, a report, notes) ·
     **Web-research it for me** (no material — I confirm the facts/numbers/names from the latest sources,
     as of today, and fact-check the script) · **Both** (I have some — research the rest) · *(deck runs
     only)* **The deck is enough** (rare; say the script will be thinner). When the purpose is a how-to
     or a launch of a real product, ask for screenshots or a screen recording of the flow the film
     describes — the device registers draw the product's OWN screens and will not invent one. Other →
     describe what grounding exists. On **"I'll share"/"Both"**, the ONLY surviving free-text is the file/repo
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

   **Batch 2 — cloud-voice setup (ONLY if the voice picked at the audition ⑤ is MiniMax or OpenAI).**
   First get the API key **OUT OF BAND** — have them `export MINIMAX_API_KEY=…` / `export OPENAI_API_KEY=…` in their own
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

   **Notes.** **Reduced motion** (accessibility variant — no zoom/pan, opacity-only reveals) is off
   by default; only set `meta.reduced_motion` if the audience needs it or the user asks via Batch 1
   ④ Other. **Language** (②) drives the caption font (CJK needs a CJK font — the bundled Latin one
   tofus) and the default voice, so a wrong code yields mojibake captions or mispronounced audio
   downstream.
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
     from-scratch **designed** deck (HTML or AI tier — skip on the **原样配音** tier, where the ingested
     pptx/pdf already owns the look, and skip at `meta.audacity: conservative`), run the contest BEFORE the full design plan.
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
3.6. **Design plan (art director) — give the content its visual language.** **Skip on the 原样配音 tier** (the user's own slides, `type:"slide"` — the deck IS the design). Dispatch
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
     judges them.
     **CINEMATIC films (`meta.renderer:"remotion"` — the bespoke-shot tier): the design step is
     `agents/shot-director.md`, not the design-director**, and there is no `design_plan.json`. When the film
     came from a pptx whose theme is not Office's default, first run `python3 scripts/dna_from_deck.py <out_dir>`
     so the film carries the deck's own brand rather than a direction's preset (`validate.py` warns when it did
     not). The shot-director's file holds each procedure; the sequence is:
     **① The shot-template CONTEST — divergence + selection, the remotion analogue of 3.55.** A *direction* is a
     whole-film ATMOSPHERE (a named look + a lean toward certain register FAMILIES + a hero; each beat is still
     its own language). Width by `meta.audacity` (`conservative` skips · `balanced` 3 · `bold` 5 · `experimental`
     7): `python scripts/shot_templates.py --route "<topic>" --audacity <a> --out <out>`. The 6 templates are
     SEEDS: the router returns only genuine keyword matches and PRINTS the shortfall, and the shot-director
     **CONCEIVES bold, topic-specific directions** to reach the width (why: case-law W6). A conceived direction
     reaches the same render path via `contest_sample.py --conceived <file.json>` —
     `[{key, pitch, dna, seam, shots: [[ShotId, {props}], ...]}]`, a direction stated as FRAMES. **Render a short
     SAMPLE VIDEO per direction so the user can SEE its look + MOTION** (motion IS the language; a pitch or a
     still cannot show it): `python scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out>
     --render` → `_contest_<key>.mp4` (~6s each, hero + 2 representative registers through the real Film). Render
     one still per direction at **`--frame=110`** for the **diversity gate** `scripts/contest_diversity.py
     <out>/_contest_*.png` (rediverge a clustered pair); **JUDGE** with `agents/shot-critic.md` in judge mode
     (floor-break + rank → winner+runner-up); surface the finalists' **sample videos** to the USER via
     `AskUserQuestion`; record `meta.shot_template` + `meta.shot_template_contest {candidates, winner,
     user_pick, width, audacity, judge_ranked}`. `validate.py` ERRORS a bold/experimental film with NO contest
     and checks width-vs-audacity.
     **② The per-beat assignment — DESIGN FIRST; the library is material, not a menu** (the one flow, defined
     in shot-director Step 0.55). **Read `references/remotion-shot-authoring.md` FIRST** (the frame-craft floor,
     the meaning mandate, the real-imagery tier, the anti-pattern catalogue — where films fail silently). Run
     `python scripts/shot_director.py <out_dir> --template <seed-key>` for a deterministic family-varied skeleton
     biased to the direction; then per beat the shot-director writes the ideal picture (`shot_fit.ideal`, no
     register named), then a route — BUILD (an object in a template's slot, or a film-local shot), ADAPT
     (layout/encoding/structure changed, recorded in `shot_adaptation.changes`), or AS-IS only when the register
     already IS the ideal (`shot_fit.shares` names the encoding it shares) — then assembles from runtime blocks
     and checks. Each beat gets `shot` + faithful `shot_props` + `shot_adaptation` (never a raw text-swap),
     ENCODES its beat (hide the caption — does the visual still carry THIS idea?), coheres with the direction
     (palette/motion/motif, not a random stack), keeps family variety, and reaches past the obvious register as audacity allows (note its `rejected_default`). `validate.py`
     ERRORs when fewer than HALF of the non-exempt beats are adapted or built, or none is built (the film's
     signature beat, designed to surprise); half is the floor, a strong film is mostly adapted or built. Every
     built thing goes on `meta.build_list` with its `means` and `accept`, is written in the film's own workshop
     (`scripts/workshop.py new-object | new-shot | still | check`; what to build with:
     `references/building-blocks.md`; how to make it mean something: `references/object-authoring.md`) and never
     touches the library. Real imagery where the topic is concrete stays the documentary tier's. A `shot`-based
     scene on the local renderer is a validate ERROR.
     **③ Then run `python scripts/seam_plan.py <out_dir>` — the film's CUTS and CAMERA.** A verify-and-fill pass,
     not a competitor: it SKIPS every beat the shot-director already marked, so authored intent always wins. It
     adds what an author cannot do by reading — it mirrors the renderer's luminance guard (a kinetic mark across a
     dark↔light boundary is silently downgraded, so a mark spent there vanishes) and derives 2-4 MOTIVATED camera
     beats from each beat's `relation` (payoff → push, close/opener → pull, else hold). Never skip it (why:
     case-law W2). `validate.py` warns when a film of ≥12 beats carries no marked seam at all, and when a
     declared `design_dna.seam` makes so many cuts kinetic that the marks stop being punctuation.
     The review after the render (`agents/shot-critic.md`, its ledger, `critic_ledger.py --final`) and
     promotion of built things are steps 9d–9f.
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
     only in conversation notes never reaches any of them. **Keep BOTH plan files** — the script
     critic (step 5) receives them: the `critic-content`/`critic-narrative` lenses audit the content plan
     (continuity, relation, faithfulness); the **design-critic** lens audits the design plan (motif, form diversity,
     transitions, icons, whitespace, rhythm, colour, motion).
     - **Theme (HTML and programmatic tiers):** run `scripts/theme.py <out_dir> [--style <meta.visual_style>]` AFTER the design plan and BEFORE
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
       `theme.css` → `motifs.css`; the programmatic renderers parse the same vars. The plan checkpoint below
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
   the subtitle. (PLAN → **DESIGN** → **WRITE** → CHECK: content-planner plans, design-director designs, scriptwriter writes, the script critic of step 5 checks.)
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
    The script critic (step 5; `critic-content` R1e) reviews the prompts.
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
4c. **Documentary (REAL-image) fetch — FREE, no key.** **Skip on the 原样配音 tier** (see 3.6). For every beat the design plan marks
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
    (never ship a blank). **A `FetchError` (the CLI's exit 2) is NOT that case:** Commons did not answer — a
    rate limit, a server error, the network — after the retries. It says nothing about which images exist, so
    run it again after a minute; never degrade the beat on it. No spend + no checkpoint (it's free + real), but the script critic (R1e) still
    checks the query matched the subject and the credit is present. Keep it to the 2–4 most physical beats.
4d. **Author the pages (HTML tiers).** **Skip on the 原样配音 tier** (see 3.6). This is where the deck's `pages/scene_NN.html` are actually
    written — one page per beat from the design plan (form + props + cue anchors + media), on
    `base.css` + `theme.css` (+ `motifs.css`; `vertical.css` last on 9:16), per
    `references/html-pages.md`, faithful (real content only), each starting from a verified form in
    `references/html-templates.md` (don't reinvent the composition). A full-bleed backdrop may gently
    **breathe** (seek-frozen `.bg-live`/`.bg-drift` on a sparse hero/hold beat; deterministic, off under
    reduced motion). Set `meta.chrome_path` if Chrome isn't at the default macOS location.
    Immediately after authoring, run `python scripts/keyframe_qa.py <out_dir>` (~1 min, no audio) to
    catch a blank page / canvas overflow while it's a one-edit fix, then hand `_keyframes/all.png` to
    `agents/design-critic.md` for its **D11 rendered pass** (focal dominance, repeated layout,
    crowding, figure-ground) — fix what it flags while pages are cheap to edit, before the script critic.
    **BUILD what base.css lacks — the same build-list step as the Remotion tier.** For each beat, write the
    ideal picture first; when no base.css form carries it (a coffee puck in section, a scale's load cell), build
    a COMPONENT — a custom element in the film's own workshop — instead of hand-drawing it into one page: add
    its `meta.build_list` entry (`kind: "component"`, `id` = its PascalCase name, `beats`, `means` that holds
    with the caption covered, `accept`, `slot: "page"`), then `python3 scripts/workshop.py <out_dir>
    new-component <Name> --means "…"`, draw it per `references/html-pages.md` "Building a component", look at
    it (`workshop.py <out_dir> still <Name>`), and `workshop.py <out_dir> check` must be clean before the page
    uses it. `validate.py` holds the build list and the pages to each other. Promotion into the library is
    the user's choice at delivery (step 9f).
5. **Script critic — ONE combined critic, ONE round, by default.** Dispatch ONE subagent carrying all three
   lenses — hand it `agents/critic-narrative.md`, `agents/critic-content.md` and `agents/design-critic.md` as its
   brief (on the **原样配音** tier, the first two only: there is no authored design to judge) — for ONE round,
   reporting the top issues by impact; apply its EDITS and go on. The user's own script + audition checkpoint
   below is what follows it, and that checkpoint never moves.
   **The full 3-critic PANEL instead** (the loop below, until all three PASS) when EITHER the user has asked
   for a careful or thorough review by this point (the post-render review-depth question of step 9d has not
   been asked yet, so this is only what they volunteered), OR the stakes are high — a defense, a launch the user
   called important, an external/paying audience, or anything they said must not go wrong. Decide it from what
   the user SAID (interview answers, the purpose they gave), record it as `meta.script_review = {"mode":
   "combined"|"panel", "why": "..."}`, and say which you ran at the checkpoint. Never fewer than the combined
   critic; the floors below (faithfulness, sourcing, the human checkpoint) are the same either way.
   The panel: dispatch `agents/critic-narrative.md`, `agents/critic-content.md`, AND `agents/design-critic.md`
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
   **Panel mode: overall PASS only when ALL THREE critics return PASS.** Apply the **UNION** of their
   required EDITS to the storyboard, then re-dispatch the critics (or just the failing one) until all
   return PASS. **Either mode — a faithfulness or sourcing finding is never "top issues only": every one is
   fixed before the checkpoint.** THEN:
   **BOTH TIERS — THEN MAKE IT AUDIBLE, BEFORE the checkpoint — `python3 scripts/script_audition.py <out_dir>`.**
   It speaks five beats (hook, climax, close and two consecutive middles) through the board's OWN voice,
   joined by the film's own measured pause, into `audition.mp3` in seconds. **Listen to it in order, and
   send it to the user with the script.**
   Never skip it: every check in this pipeline READS the narration, and the defect that ships is AUDIBLE
   (why: `references/engineering-case-law.md` W1). Auditioning five beats is not the full synth; the full run
   still waits for approval.
   **Ask ⑤ Voice HERE**, right after they have heard it. Menu: **keep this voice** (edge-tts, the free
   default — natural, needs network, accent-matched, and the ONLY engine with per-word timings, so html
   reveals and karaoke captions land on the exact word) · **MiniMax** (paid, most natural, especially
   Chinese; needs a key) · **OpenAI** (paid, premium neural; needs a key) · **macOS `say`** (offline, robotic
   fallback). (Other → an accent or gender preference.) State the trade-off aloud: with say/MiniMax/OpenAI,
   HTML reveals use the text-position estimate (tracks the voice's pacing, not word-exact). A paid pick
   triggers Batch 2 (key + a voice-sample pick), then re-run `script_audition.py <out_dir> --allow-paid` in
   the new voice before sign-off — the user signs off on the voice they will actually get. (The flag is
   the consent: without it the audition refuses a paid engine and says how many characters it would
   send, so a board that merely CARRIES a paid voice never spends on a key nobody chose.) The audition
   speaks through the film's own voice path (`tts.film_voice` + `tts.speak`): same language detection,
   same pronunciation layer, no silent fallback — what is heard here is what the film will say.
   🔴 **CHECKPOINT · 🛑 STOP:** present the full, critic-reviewed script **and the audition audio**,
   and get the user's edits/approval before the full TTS run. A script nobody has HEARD has not been
   checked, whatever the metrics say.
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
   iterating on one slide). edge-tts emits `.mp3`; `say` emits `.wav` — both fine.
8. **Sample sign-off** — `render.py <out_dir> --sample N`, then show `sample.mp4` to the user
   (`deliver.py`). No critic runs on the sample: the A/V review (`agents/critic-av.md`) moved to the review
   depth the user picks after the first clean full render (step 9). Look at the sample frames yourself first
   — caption legibility, glyphs, nothing cut off — before you hand it over.
   🔴 **CHECKPOINT · 🛑 STOP:** get explicit approval of the style (voice/pace/motion/
   captions) BEFORE the full render. Iterate on the sample until they approve — never
   batch-render all slides unsigned-off.
9. **Full render — gate, render, review, deliver**, in this order (9a → 9f).
   **9a · Pre-render gates.** First `python scripts/validate.py <out_dir>`. A non-zero exit means a referenced
   image/audio/page/asset is missing, an index is duplicated, `theme.css` is absent, or a caption is a wall of
   text — fix every ERROR before rendering (it catches in ~1s what would otherwise waste a multi-minute render).
   **WARNING TRIAGE — required, not "skim the warnings too".** An exit code of 0 is a floor, not a verdict:
   GROUP the warnings by kind (they repeat) and put every kind in one of three buckets — **fix** · **accept,
   with a one-line reason** · **can't fix here** — then TELL THE USER the accepted ones and why. A warning
   silently swallowed is a defect you chose and hid; one accepted out loud is a design decision (why: case-law W3).
   **BOTH TIERS — also run `python scripts/rhythm_qa.py <out_dir>`** (needs the real durations, so after tts) — it
   flags flat pacing: uniform scene lengths, a mis-placed or missing climax, a non-sparse closer, an
   over-held static image, or no attention reset for >~35s. Fix the ERRORs; treat the WARNs as
   direction (vary `est_seconds`, place the climax at ~75–80%, split a long image hold).
   **BOTH TIERS — and run `python scripts/pedagogy_qa.py <out_dir>`** — the teaching-order gate: it ERRORs on a
   concept used before it is introduced (walks `content_plan.json`'s concept DAG). Fix every ERROR;
   it no-ops if `content_plan.json` wasn't persisted.
   **BOTH TIERS — run `python scripts/voice_qa.py <out_dir>`** — the VOICE gate (see
   `references/anti-ai-voice.md`); the narration is the one thing the two tiers share outright (why this says
   BOTH TIERS: case-law W4). It reports the vocabulary tells AND the rhythm distribution (sentence-length CV,
   balanced-pair share, connective share, antithesis share, and how many beats hold a single sentence). Treat
   each number as a place to look, not a target: fix the beats that genuinely read as template, leave the ones
   that trip a check and still sound like a person, and say out loud which you accepted. Then READ THE WHOLE
   SCRIPT ALOUD — the metrics catch distribution, only the read catches deadness.
   **Remotion film — three more, none of which costs a render of the film:**
   • `python scripts/shot_proof.py <out_dir>` — catches in ~3 minutes the mechanical findings that otherwise
     cost a full render (6–8 minutes for a 37-beat film) plus a shot-critic pass: a leftover register default,
     two beats rendering the same picture, action-safe overflow, ink in the caption band, an off-palette
     colour, a dead frame. Fix every ERROR and triage the warnings out loud, exactly as with validate.
   • `python3 scripts/energy_skeleton.py <out_dir>` — reads the plan's declared `energy` per beat against each
     register's measured motion (a climax on a register UNDER the delivery motion floor is the defect it
     catches). Fix the beats it names or re-declare them.
   • `python3 scripts/cjk_type_qa.py <out_dir>` — **required when `meta.language` is CJK**; run it serially.
     The library is authored with short English demo copy, and a face set at `line-height: 0.82` is confident
     Latin typography and a collision in Chinese. `text_safe_qa` cannot see it (nothing is cut off — the copy
     sits inside the frame and is unreadable).
   **HTML-tier deck — also run `python scripts/keyframe_qa.py <out_dir>`**: it screenshots every page at
   several reveal states into `<out_dir>/_keyframes/` and flags any BLANK page or content overflowing the 1080
   canvas (open `_keyframes/all.png` and eyeball for tofu / off-theme / mistimed reveals). Fix any FAIL before
   the full render — cheaper than finding it in `out.mp4`.
   **9b · Render.** `render.py <out_dir>` (HTML/image tiers) or `render_remotion.py <out_dir>` (remotion; it
   writes `out.srt` + `_keyframes/scene_NN.png` itself). For 9:16 set `meta.aspect:"9:16"` — render and validate
   both honor it, captions auto-scale off the narrow dimension, and HTML pages must be RE-AUTHORED vertically
   (top-anchored, single-column restacks, vertical timeline rail; `references/html-pages.md` "9:16 vertical
   pages"); the `--vertical` flag also forces it on both.
   **9c · Post-render gates.** `python scripts/check_av.py <out_dir>` on both tiers: a non-zero exit means A/V
   drift or non-uniform clip rates — fix the root cause (clear `.clips/`, fix audio or regenerate failing
   clips, and re-render) before delivering. On a remotion film the html-only `keyframe_qa.py` (which returns 0
   there) is replaced by: **`keyframe_qa_remotion.py <out_dir>`** (a deterministic blank-frame backstop on the
   keyframes) · **`text_safe_qa.py <out_dir>`** — the FRAME-CRAFT gate: it ERRORs when any TYPE is cut off by
   the canvas, asked of the DOM rather than inferred from border ink (its entry in
   `references/pipeline-scripts.md`) · **`film_energy_qa.py <out_dir>`** — the FILM-ENERGY gate: motion,
   density and light measured against real launch films, the only gate that judges the FILM rather than a
   frame, so the only one that catches a delivery correct in every frame and inert as a film · **`shake_qa.py
   <out_dir>`** — paired with film_energy_qa: the first refuses a film that does not move, the second one that
   moves without going anywhere, and passing the first by tripping the second is a failure this tier has
   shipped. **`frame_safe_qa.py <out_dir>`** is an ADVISORY read — a flooded border and a brightness OUTLIER
   scene (a white/bright shot in a dark film = palette clash) are worth seeing, never worth blocking; say
   which of its warnings you accepted. `rhythm_qa`/`pedagogy_qa` still apply (they read `content_plan.json`).

   **9d · 🔴 THE REVIEW-DEPTH QUESTION — asked after the FIRST clean render, with the film in front of the user**
   (modelled on slide-maker's post-build review question). When every machine gate is green (validate,
   text_safe incl. `--glide`/`--sync`, keyframe_qa / keyframe_qa_remotion, check_av, shot_proof, cjk_type_qa,
   film_energy_qa, shake_qa, rhythm_qa, pedagogy_qa), FIRST hand the film over — `python3 scripts/deliver.py
   <out_dir>` and give the user that path — THEN ask ONE question (`AskUserQuestion`; on a host with no choice UI,
   one typed question in the user's language, listing the four options with their text below):

   | option | what runs | rough cost (qualitative — no measured numbers exist for this skill) |
   |---|---|---|
   | **`fast`** (default) | ONE combined critic (`shot-critic` carrying `critic-av`'s lens; HTML tier: `critic-av` + `design-critic`'s D-checks in one pass), ONE round, top issues by impact; the rest recorded `declined` | one subagent pass + one re-render if it finds something |
   | `standard` | `shot-critic` + `critic-av` (HTML: `critic-av` + `design-critic`), up to TWO rounds, round 2 a full fresh review | about two to four subagent passes + re-renders |
   | `thorough` | the full loop: REVISE → fix → re-render → fresh independent review, until PASS | open-ended; each round is a re-render plus a fresh review |
   | `none` | no critic — the user's own viewing is the review, recorded as user-waived | nothing further |

   **Pre-select `fast`** when the plan/design self-checks and every machine gate came back clean. **Pre-select
   `standard`, and say why in the question,** when a gate needed a waiver or an accepted warning you had to argue
   for, or the design self-check flagged issues. `none` is NEVER pre-selected and never inferred from silence,
   a "looks fine", or a green gate — only the user's explicit pick. Record the answer as `meta.review` in
   `storyboard.json`:

   ```json
   "review": {"tier": "fast", "user_answer": "<the option or words the user gave>",
              "preselected": "fast", "render_sha256": "<sha256 of _contact_sheet.png — required for none>"}
   ```

   `critic_ledger.py --final` reads it: a capped tier (`fast` 1 round, `standard` 2) whose last round said REVISE
   closes when every failed row records `applied` (what changed) or `declined` (why not), and the film is marked
   "reviewed at <tier>, not re-reviewed" — never a PASS; no `meta.review` at all means `thorough`. **What never
   moves with the tier:** every machine gate above, the faithfulness and sourcing rules (a sourcing or
   faithfulness finding is always fixed, never `declined`), the human script/audition checkpoint, an independent
   reviewer, every ledger row, and the render pin.

   **`none` waives the review — and only the user may choose it.** `meta.review = {"tier": "none",
   "user_answer": ..., "render_sha256": ...}` (the older `meta.review_waiver` form is still read the same way):

   ```json
   "review_waiver": {"reason": "<what the user actually said>",
                     "render_sha256": "<sha256 of _contact_sheet.png, which you compute>"}
   ```

   `critic_ledger.py --final` then exits 0 without a ledger, says REVIEW WAIVED on every run, and rewrites
   `NOT_DELIVERED.md` into a record that the film shipped unreviewed and why — a waiver is **not** a PASS,
   and `ls` must keep answering "was this ever looked at?" truthfully.

   Three things bind you here:
   - **Never author it on your own behalf.** Not to save time, not because the gates are green, not because
     you think the film is good. It is the one judgement in this pipeline you are structurally the wrong
     party to make (`critic_ledger.py`'s own header: the maker has confirmation bias about their own output).
     If the user has not said it, there is no waiver.
   - **It expires with the render.** The pin covers the cut the user actually watched. Change one beat, one
     colour, one line of narration, re-render — the sha moves, the waiver stops applying, and the gate asks
     again. That is deliberate: "fine once" must not become a licence over everything changed afterwards.
     When that happens, show the user the NEW cut and ask again; do not re-stamp the pin.
   - **It waives taste, not correctness.** `check_av`, `keyframe_qa_remotion`, `text_safe_qa`, `cjk_type_qa`,
     `film_energy_qa`, `shake_qa` and `validate.py` all still run and still gate delivery. A waived film is
     one nobody judged for register fit, meaning, frame-craft or boldness — not one nobody checked plays.

   **9e · The review, at the depth chosen.** On a remotion film, run `python3 scripts/critic_brief.py <out_dir>`,
   then dispatch **`agents/shot-critic.md`** on the keyframes + the `check_av` + `keyframe_qa_remotion` +
   `text_safe_qa` + `film_energy_qa` + (advisory) `frame_safe_qa` reports. It judges register fit, family
   variety, faithful copy (no demo-number/WorkBuddy leftover), decodability, **MEANING (S10 — does each shot's
   design ENCODE its beat's idea, not just look good?)**, **boldness (S8, audacity-scaled)** and direction
   adherence, and REVISEs failing beats (the shot-director re-assigns → re-render). Its verdict is a LEDGER:
   every dimension gets a row in `<out>/_critic_ledger.json` — the clean ones too, each citing the keyframe or
   brief line it rests on — and `python3 scripts/critic_ledger.py <out_dir>` must exit 0. The delivery pass is a
   fresh subagent whose ENTIRE input is the `<out_dir>` path — no rationale, no summary of what you fixed, no
   steer about where to look — then `python3 scripts/critic_ledger.py <out_dir> --final` (exit 0 required; it
   refuses an in-context ledger, a ledger missing any dimension, and one pinned to a render this film never
   had) (why: case-law W7). On the HTML tier the same depth applies to `critic-av` + `design-critic` (table
   above).
   **9f · DELIVERY CRITERION — every gate, not two** (why: case-law W5). Deliver `out.mp4`, `out.srt`, and the
   editable `storyboard.json` only after **`validate.py`, `check_av.py`, `keyframe_qa.py`, `rhythm_qa.py` and
   `pedagogy_qa.py` ALL exit 0** (`voice_qa.py` is ADVISORY and always exits 0 — read its signals and say which
   you accepted; failing a build on them would produce the "rule voice" its reference warns about). On a
   remotion film, `keyframe_qa_remotion.py` + `text_safe_qa.py` + `cjk_type_qa` (CJK film) + `film_energy_qa.py`
   + `shake_qa.py` exit 0 and the review at the user's chosen depth (`critic_ledger.py --final`) REPLACE
   `keyframe_qa.py`, which no-ops there; `frame_safe_qa.py` is advisory. Also read `keyframe_qa`'s **deck
   advisories** (silhouette repetition, content-band uniformity) and any scene reported **UNVERIFIED** — an
   unverified scene is not a passing scene, it is a scene nothing measured. Then record the deck's register
   into the cross-deck ledger: `python scripts/register_ledger.py record <out_dir>` (feeds the next video's
   contest with "what the last decks looked like").
   **PROMOTION IS THE USER'S CHOICE, AT DELIVERY** (both tiers). List the film's built things (`meta.build_list`)
   — each with its settled frame (`workshop/_stills/`) and its gate results — and ask the user with
   `AskUserQuestion` (multiSelect) which, if any, to promote into the library. For each one chosen:
   `python3 scripts/promote.py <out_dir> <Name>` (an object or an HTML component: it joins the library and the
   catalogue) or `... --family <X> --use-when "…" --motion "…"` (a remotion shot: registered at every sync point
   and measured in the right order). Nothing is promoted without the user's pick; nothing a film builds reaches
   another film until it is.
   **Then hand the user the video WHERE THEY LOOK FOR IT — always, for every render they are asked to
   watch (a sample, a preview, the final cut):** `python3 scripts/deliver.py <out_dir>` copies `out.mp4`
   (and `out.srt` beside it, same name) to `~/Desktop`, or to `~/Downloads` when the Desktop cannot be
   written, and prints the path — give the user THAT path, and send the file too when the session can.
   Never point the user at a file inside this skill's folder, `~/.claude`, a `.superpowers/` or other
   hidden work folder, or a temp directory: nobody browses there. If neither folder can be written (macOS can
   withdraw access mid-session), ask the user for a folder and pass `--to`.
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
- **Write English terms as they are READ, not spelled for the voice.** `tts.py` sends a Chinese edge voice
  "A-I" / "T-T-S" for a standalone 2-3 letter initialism (measured: without it the voice drags the syllable
  before the letters and pauses) and maps the word timings back, so the caption and karaoke keep "AI". Never
  hand-write "A G P L" / "T T S". Anything else pronounced wrong goes in **`meta.tts_lexicon`**
  (`{"AgentHalo": "Agent Halo"}` — spoken text only); `meta.tts_spell_initialisms: false` turns the spelling off.
- **The film opens and closes on a held picture:** `tts.py` makes the first word wait `meta.open_hold`
  (default 1.0s) and the last word end `meta.close_hold` (1.2s) before the film does, shifting the first
  clip's word times with it; 0 turns either off.
- **`meta.tts_speed`** (default `1.0`) tightens or loosens the narration PACE without cutting content —
  a multiplier applied to BOTH edge-tts (mapped to its `rate` `±%`, e.g. `1.25` → `+25%`) and MiniMax
  (its `speed`). Clamped `[0.5, 2.0]`; for edge, keep within **~±30%** (`0.8–1.3`) — beyond that the
  neural voice sounds unnatural. Per-word timings scale WITH the rate, so captions + audio-synced reveals
  stay in sync. Reach for `1.2–1.3` when a faithful script overruns the target runtime.
  **The knob is BIDIRECTIONAL, and slowing DOWN is the fix for a video that feels rushed or whose
  scene-ends read as abrupt.** The instinct — "give the viewer more time to read" — must NOT be paid
  for by padding a long SILENT, STATIC tail onto each clip: a frame frozen and silent for 2–3 s then
  hard-cut reads as the video HANGING, not as breathing room (a viewer called every such scene-end "a stiff
  obvious gap"). Reading time belongs INSIDE the narration — set `tts_speed` to ~`0.9–0.92` so the whole
  delivery is unhurried and the reveals land leisurely — leaving only the SHORT heard pause of
  `meta.scene_pause` (default 0.55 s, keep ≤ ~0.9 s; see `tts.py` under Pipeline scripts) after the last
  word. `meta.audio_breath` is a RAW pad that overrides it — set it only deliberately. Slow-voice + short-breath + a gentle seam beats fast-voice + long-dead-tail
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
- **HTML pages tier cache:** a page's clip re-renders when the page file, `theme.css` (re-theming), or
  `audio/NN.words.json` (new edge run) changes.
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
- **Theming:** one colour world — html pages link `theme.css` and the programmatic scenes parse the SAME
  vars (dark palette only when no `theme.css` exists), so mixing the two in one deck is fine. Pick a
  palette/mode that fits the TOPIC (not always dark); never raw hex. Re-running `theme.py` busts ALL cached
  clips. (When to run it: step 3.6 "Theme".)
- **Image provider:** Codex-first, else the OpenAI key (Batch 3 "Provider"); Codex and OpenAI images
  cache separately (keyed by provider).
- **API key — never persist it.** Applies to the OpenAI key (gpt-image / openai TTS) AND the
  **MiniMax key** (`MINIMAX_API_KEY` / `~/.minimax_key`). Request it fresh each run and pass it ONLY
  via the env var (or `imagegen.py --key`) for that one call. NEVER write any key into
  `storyboard.json`, any script, the `.assets/` manifest, a log, or any committed file — the scripts
  keep it only in the request header, nowhere on disk. If the user pasted a key into the chat, remind
  them to rotate it (the transcript retains it).
- **Pacing — keep cuts moving.** Prefer MANY short beats (~3–6s, one idea each; ≈ `target_seconds/4`
  beats) and roughly ≤8s per scene, especially image/b-roll (a held static image reads as sluggish even
  with Ken Burns). If a scene's narration runs long, split it into shorter beats rather than holding one
  frame; the animated renderers' internal reveals keep the screen moving.
- **Informative-first visuals.** A beat that states a fact or concept uses an INFORMATIVE
  visual — `chart`, `compare` (split/versus breakdown), `keypoints` (kinetic labeled points),
  or `timeline` — never a decorative photoreal image. AI photoreal (`image_prompt`/`broll`) is
  allowed as a rare atmospheric opener/closer OR as illustrative accompaniment on a content beat
  where the fact stays as on-page text (e.g. a `.split` page); never as the sole carrier of a claim.
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
| Text trembles / steps a pixel at a time during a slow camera move, drift or reveal (remotion / HTML) | Skia snaps a moving line's baseline to whole pixels under a plain scale/translate — NOT the image tier's zoompan; `text_safe_qa.py <out_dir> --glide` names the beat and the line | Pass the moving transform through `glide()` (runtime/glide.ts) over its span, inside any blur/drop-shadow; the HTML reveal/float classes already carry it |
| Slide "shivers"/jitters during the zoom | zoompan runs supersampled (`meta.motion_ss`, default 2) then downscales; a `scale` filter must precede zoompan or the frame shrinks. Keep ss≥2 | Raise `motion_ss` to 3 (smoother, slower) |
| Caption is one static line per slide | Captions auto-derive from `narration` — split into sentence chunks timed across the slide; a single full-span entry in `captions` is overridden by the narration track | For custom timing, supply a multi-segment `captions` array |
| `render.py`: no Chrome for an `html` scene | `render_html` errors clearly; set `meta.chrome_path`, or switch those scenes to the free programmatic tier (title/chart/keypoints/compare) | Install Google Chrome, then re-render |
| `html` page renders blank / unstyled | Confirm the page links `assets/html/base.css` + `theme.css` (from `out_dir`) + `seek.js` by ABSOLUTE `file://` path; no external/network assets | Open the page in a browser to debug, then re-render (the cache busts on edit) |

For anything else, read `references/troubleshooting.md` before guessing.

## Red lights — never do this

- ❌ Render audio/video before the user signs off script/sample (honor the 🔴 checkpoints) — but
  the five-beat `script_audition.py` proof is REQUIRED before that sign-off, not forbidden by it:
  the checkpoint is a listen, and a script nobody heard has not been checked.
- ❌ Narrate from the slides alone, or invent facts/numbers — ground in the material (or a
  web fact-check) and stay strictly faithful (step 3).
- ❌ Skip the script critic (step 5) — the combined critic runs on every run (the 3-critic panel when step 5 calls for it, shipping only when all three PASS), and every faithfulness or sourcing finding is fixed, never cut to the top few.
- ❌ Read slide bullets aloud verbatim — write *spoken* narration (`references/narration-writing.md`).
- ❌ Guess a slide's `duration` — it must come from ffprobe via `tts.py`.
- ❌ Hand-edit `out.mp4`; change `storyboard.json` and re-render (`--only N`).
- ❌ Tell the user to watch a file inside this skill's folder, `~/.claude`, a hidden work folder or a
  temp directory — run `scripts/deliver.py <out_dir>` and give them the Desktop/Downloads path it prints.
- ❌ Add callouts/emphasis boxes by default — they're OFF unless the user asks; never stack them.
- ❌ Write the OpenAI API key into the storyboard, a script, the manifest, or any persisted/
  committed file — request it fresh each run, pass it only via `OPENAI_API_KEY`/`--key`, and
  remind the user to rotate a key they pasted into the chat.
- ❌ Let a single static frame linger (one long held image reads as sluggish) — keep cuts
  moving (~≤8s/scene), splitting a long scene into shorter beats rather than over-holding.
