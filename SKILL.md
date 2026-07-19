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
- `scripts/tts.py <out_dir> [--only N]` — narration → `audio/` + real durations. With edge-tts, also writes `audio/NN.words.json` (per-word start times), used for audio-synced HTML reveals; emits `.mp3`. With macOS `say`, emits `.aiff` (no words.json).
  **Every speech clip is MASTERED in place before its duration is measured:** loudness-normalised
  (EBU R128, I=-14) + trailing dead-air trimmed (tail-only — leading/internal timing untouched, so
  `words.json` word times stay valid), so levels are consistent across providers and the pacing gates
  see speech, not dead air. Opt out with `meta.audio_master: false`.
- `scripts/theme.py <out_dir> [--mode light|dark] [--accent #hex] [--accent2 #hex] [--bg #hex] [--style <key>]` —
  derive a topic-fitting palette from `frames/` (or the passed overrides) and write
  `<out_dir>/theme.css` (the HTML tier links it; the programmatic renderers parse the same
  semantic vars — one color world). Run before authoring pages OR programmatic scenes. Contrast is
  **gamma-correct WCAG** (true relative luminance): it enforces fg/bg ≥7:1, nudges a SAMPLED
  accent toward ≥3:1 on the bg (lightness only, capped ±0.15 to preserve the hue's character;
  an explicit `--accent` override is never touched), and picks `--on-accent` by whichever of
  black/white has the higher true contrast on the accent fill. An out_dir themed BEFORE this fix
  may carry a low-contrast `--on-accent` in its theme.css — re-run `theme.py` to regenerate. It also
  emits **`--grain-amount`** per style — a printed/filmic style (risograph/manga/watercolor/terminal/
  noir/cartographic) gets a subtle fixed-seed **film grain** (motifs.css `body::after`, auto-applied,
  FREE tier), clean styles stay crisp at 0; a data-heavy page opts out with `<body class="no-grain">`.
- `scripts/imagegen.py <out_dir> [--key KEY]` — OPTIONAL paid tier: generate AI scene images
  via OpenAI `gpt-image-2` for scenes that carry an `image_prompt`, cached under `.assets/`
  (re-runs are free). Auto-uses the Codex CLI (no key) when installed, else needs
  `OPENAI_API_KEY`/`~/.openai_key`; `meta.image_provider` (`auto`/`codex`/`openai`) selects
  the path. Only acts when `meta.image_source == "openai"`. This is the **`atmosphere`/broll** class —
  generic, no facts.
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
- `scripts/render.py <out_dir> [--sample N] [--only N] [--vertical] [--reduced-motion]` — storyboard → `out.mp4` + `out.srt`.
  **Scene transitions:** a gentle dip-to-theme-bg at clip edges (video only — audio/durations
  untouched, so cache + `-c copy` concat + A/V gate still hold). `meta.transition` (`dip` default |
  `none`), `meta.transition_seconds` (0.2). **Per-scene override — the transition is SEMANTIC:**
  `slide.transition` (`dip` both edges · `in`/`out` one edge · `none`) + `slide.transition_seconds`
  override the meta default per scene; the design plan maps the beat's `relation` to it (continuation →
  hard cut; new-topic/payoff/close → an in-edge on the opener PLUS an out-edge on the predecessor —
  a dip needs both sides, validate lints unpaired edges) — see `references/motion-grammar.md`
  "Transition rhythm". Never random; no wipes/spins. **Karaoke captions:** when edge-tts `audio/NN.words.json`
  exists (space-delimited languages), the burned caption highlights the word being spoken, timed to the
  real word times; falls back to line-level chunks for MiniMax/say and CJK. `meta.captions_karaoke`
  (`auto` default | `off`). The highlight colour is **contrast-picked per scene** against the caption band's
  ground (prefers `--accent`, else `--accent2`/gold/high-contrast b/w) AND kept distinct from the
  neighbouring words — so the spoken word never vanishes into an accent-fill / same-colour band.
  **Caption placement — `meta.caption_mode`:** `overlay` (default) burns the caption with **NO background
  bar** — the text sits flush at the very bottom in the deck's `--fg` ink with a subtle opposite-luminance
  **outline**, so it reads over ANY ground (empty frame, a tint, a photo) on any theme + aspect without a
  heavy/ugly strip; the karaoke word is contrast-picked vs the frame's own `--bg`. Content must stay clear
  of the bottom ~15%. `band` draws the caption in a
  dedicated strip BELOW the content so it NEVER overlaps the slide — the canvas grows to `W×(H+~138px)`
  (1920×1218 at 1080p). `meta.caption_band` picks the strip's look: `flush` (default) SAMPLES each
  scene's own bottom-edge colour and continues it (seamless on off-white, a tint, a red accent-fill, or a
  photo; text auto-flips to contrast); `contrast` = a fixed dark `--fg` strip + `--bg` text (subtitle bar). `meta.caption_scale` (default 1.0) tunes the caption
  font (band face is a touch smaller). Reach for `band` on dense decks or when a clean content frame
  matters more than exact 16:9 output dims (see `references/captions.md`).
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
- `scripts/render_remotion.py <out_dir> [--sample N] [--vertical] [--reduced-motion]` — **OPTIONAL
  cinematic render tier** (opt-in via `meta.renderer:"remotion"`; the local ffmpeg+Chrome path stays the
  free default). Renders the same `storyboard.json` through **Remotion** (React/Node): per scene a
  full-bleed **image** with Ken Burns, the synthesized narration, subtitles, timed **callouts**, and an
  optional lower-third `props.title`/`kicker` — the **story/cinematic** look. **Parity with the local
  tier:** it honours the SAME per-scene fields — `motion` (Ken Burns from/to `[x,y,zoom]`, can zoom out),
  `fit` (contain/cover), `callouts` (cue/at timing), `transition` (dip/in/out/none → scene-edge fades),
  `reduced_motion`, canvas-derived caption size — reusing `render._captions_for`/`_canvas`/`_write_srt`/
  `_callout_time` so captions + srt are byte-parity. It does NOT reproduce the HTML slide archetypes
  (kicker/cards/charts): a deck with **html/chart/timeline/keypoints/compare** scenes **fails loud**
  (both `render_remotion` and `validate.py` ERROR, listing the offending indices) rather than silently
  rendering blank — use the local renderer for a designed/html deck, or give those scenes an `image`.
  `render.py --renderer remotion` (or `meta.renderer`) dispatches here; **`--sample N` renders one scene
  to `sample.mp4`** for the step-8 sign-off (critic-av reviews it exactly as for the local tier). Needs
  the Node toolchain + a one-time `cd remotion && npm install` (doctor.py reports availability;
  `node_modules` is gitignored). Writes `out.mp4` + `out.srt`; the post-render `check_av.py` A/V gate
  still guards delivery (it degrades cleanly with no `.clips/`). When to reach for it: Remotion's real
  edge is fast/kinetic motion + motion-blur + eased cross-scene transitions — worth it for a cinematic
  **story** video, not for a calm explainer deck (where it's pixel-identical to local).
- `scripts/cues.py` — pure anchor→cue-time resolver: reads per-scene `audio/NN.words.json` (edge-tts per-word timings) and resolves each `data-cue` anchor phrase to an absolute timestamp, used by `render_html` for audio-synced HTML reveals.
- `scripts/check_av.py <out_dir>` — deterministic A/V gate: probes `out.mp4` video-vs-audio duration + per-clip sample-rate uniformity across `.clips/`; exits non-zero on A/V drift above tolerance (0.3 s) or non-uniform rates. Run AFTER the full render (step 9) as a gate before delivery.
- `scripts/doctor.py [--json]` — environment preflight: reports which tools/libraries are present (ffmpeg/ffprobe/PIL required; PyMuPDF/python-pptx/edge-tts/soffice/Chrome/font optional) and, for each missing one, the stage it gates + the install hint. Exits non-zero only when a REQUIRED dep is missing. Run once at the START (step 1).
- `scripts/validate.py <out_dir> [--pre-tts] [--vertical] [--json]` — deterministic PRE-render gate on `storyboard.json` (runs in ~1s): structural contract, duplicate indices, every referenced image/audio/html-page/`file://` asset + `theme.css` exists on disk, caption craft (no wall of text, no widow, ≥0.7s on screen — see `references/captions.md`), motion sanity (zoom delta + zoom-past-1.25 + callout-framing — see `references/motion-grammar.md`), per-point reveal↔voice alignment (each point spoken-% vs shown-% → leads/lags warning, cued or paced), a **hardcoded-hex lint** (WARN on a raw `#hex` in a `style=`/SVG-`fill`/`<style>` color — pages must use semantic vars), figure-traceability (a stat on screen/voice must trace to the brief; **UI-idiom chrome text opts out via `data-ui`** on the leaf element — never mutate chrome text to dodge the lint), CJK-font/cue/pacing/anti-slop warnings. Exits non-zero on any ERROR. Run BEFORE every render (step 9); `--pre-tts` validates right after authoring (skips audio checks); `--vertical` mirrors render's 9:16 canvas (also auto from `meta.aspect`). Errors block; warnings don't.
- `scripts/rhythm_qa.py <out_dir> [--json]` — deterministic PRE-render VIDEO-RHYTHM gate: the
  video-native complement to the layout-diversity gate. Reads `storyboard.json` (real `duration`s after
  tts, else estimates from narration) and flags flat pacing — durations too uniform (monotone), a climax
  not at ~70–85% (or none on a >75s video), a non-sparse closer, a static image held too long, and no
  attention reset for >~35s. Advisory (warnings) except ONE hard defect — a MEASURED static frame held
  past ~16s → non-zero exit; a missing climax is only a WARNING (an estimate never gates a render). Run
  after tts, before the full render.
- `scripts/brief_qa.py <out_dir> [--json]` — deterministic PRE-plan gate on the **comprehension brief**:
  reads `<out_dir>/brief.json` and ERRORs on a missing/empty required key (`thesis`/`mechanism`/`evidence`/
  `why_it_matters`/`the_one_thing`/`source_health`), a non-singular `the_one_thing`, or a
  `source_health:contradictory` with no resolved conflicts; WARNs on a verbless (topic-label) thesis or an
  evidence item with no `source_ref`. The STRUCTURAL floor so a hollow brief can't reach the planner —
  run at step 3.5 BEFORE dispatching `content-planner`. The SEMANTIC depth audit is `critic-content` C0.
- `scripts/pedagogy_qa.py <out_dir> [--json]` — deterministic PRE-render **teaching-order** gate: walks
  the concept-dependency DAG in `<out_dir>/content_plan.json` (`introduces`/`builds_on`/`stage` +
  `meta.assumed_known`) and ERRORs on a **concept used before it is introduced**; WARNs on an `introduces`
  that's a list (>1 new idea/beat), no `ground` before the first `build`, or a `build` with no `why`/`land`
  within one beat. The mechanical backstop for `critic-content`'s prerequisite gate — run at step 9
  alongside `validate.py`/`rhythm_qa.py`. No-ops when `content_plan.json` isn't persisted.
- `scripts/keyframe_qa.py <out_dir> [--p N] [--json]` — cheap PRE-render VISUAL QA for the HTML tier:
  screenshots every `html` page at N `?p=` values, montages per-scene + a master contact sheet under
  `<out_dir>/_keyframes/` (open `all.png` to eyeball tofu / off-theme / mistimed reveals), and — via
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
  order discipline"); and, on a 9:16 deck, on any page filling <60% of the vertical zone (the
  "fill the column" rule — heroes with a full-bleed `.bg-photo` are exempt). Exits non-zero on a
  blank / overflow / clip / caption-occlusion (advisories don't block). Run after
  authoring the pages, BEFORE the full render — a ~1-minute catch of the exact failures that would
  otherwise silently ship in a multi-minute render. (No CDP → screenshots + blank-check only.)
- `scripts/snapshot.py <page.html> <out.png> [--p 1.0] [--vertical] [--no-captions] [--json]` — render
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
   the tiers available — fold them into the interview (e.g. no Chrome → drop the HTML tier).
   Then run the **interview** — a small set of selectable questions that capture the
   user's whole intention up front. **Rendering rule for options:** `AskUserQuestion` shows at
   most **4 selectable buttons per question**; when a menu is richer, spell out the FULL menu in
   the question text, make the most-common items the ≤4 buttons, and let the automatic **"Other"**
   free-text accept any listed item by name — a menu that is naturally ≤4 shows every item as a
   button. Ask the **core screen (Batch 1) always**; fire Batches 2–3 **only when a prior answer
   triggers them**. A common free/default run finishes in the single Batch-1 screen.

   **Batch 1 — core intent + essentials (ask every run; 5 core questions).** `AskUserQuestion`
   shows ≤4 buttons/call, so fire Batch 1 as **two calls: screen A = ①–④, screen B = ⑤ Voice**.
   **No-deck (make-from-scratch) runs — capture the topic FIRST:** if the user has a deck
   (pptx/pdf/images) SKIP this (the deck IS the topic); with **no** input deck, before screen A ask a
   plain prompt (not buttons) for the **topic + goal/takeaway** — it becomes the source the
   content-planner + design-director build the deck from (with the grounding material below).
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
     Set `meta.language` to the resolved code (never leave it `"auto"` at render). The narration
     **voice engine** is the separate question **⑤** below.
   - **③ Look / template — and whether to use the image generator** *(→ `meta.image_source` + the
     per-beat scene tier)* — the deck's visual world. **This question IS the explicit
     image-generation decision:** the two "free" tiers use **NO** image generator
     (`image_source:none`); the two "AI" tiers turn on the OpenAI `gpt-image-2` generator
     (`image_source:openai`, **paid** — Batch 3 then confirms the spend). Make that free-vs-paid split
     visible in every option label; never enable image generation without the user picking an AI tier
     here. Menu (4 tiers): **Flat/clean — FREE, no AI images** — theme's flat programmatic surfaces, no
     API (`image_source:none`, the default) · **Designed HTML deck — FREE, no AI images** — bespoke
     full-screen pages rendered by headless Chrome, needs Chrome (per-beat `type:"html"`) · **AI cover
     + soft bg — PAID, uses image generation** — a generated full-bleed cover + on-topic textures
     behind pages at low opacity (`image_source:openai`) · **HTML + AI backdrops — PAID, uses image
     generation** — designed HTML pages WITH generated soft backgrounds behind glass cards
     (`image_source:openai`). (Other → a mix of tiers, or a brand/theme/CSS to match.) **Real
     (documentary) images — FREE, no API:** independently of the tier above, for a **CONCRETE** topic
     (a city, place, real system/product/organism/event) the design-director may pull REAL license-clean
     photos/maps/diagrams from Wikimedia Commons (`scripts/imagefetch.py`) to DEMONSTRATE the subject
     directly (a real rail map, a real cityscape) — treated to match the deck. It's decided per-beat, not
     asked here; mention it when the topic is concrete (an abstract topic stays typographic/atmosphere).
     The
     **per-beat template FORMS** (hero-stat, before/after, timeline rail, system map, metric wall,
     results table, figure focus, funnel, dashboard, case story, flywheel — see
     `references/html-templates.md`) are chosen by the design-director per beat, NOT asked here.
     **Audacity (optional, defaults `balanced`):** independently of the tier, `meta.audacity`
     (`conservative`/`balanced`/`bold`/`experimental`) is the RISK BUDGET for the video's whole-video
     expressive register — how far its look + MOTION + type push. Default `balanced` (solid base + one
     register that genuinely carries the video) is right for most runs; mention it only if the user wants
     a bolder or more restrained feel — the floor (clarity/faithfulness/AV/gates) is identical at every
     level. Set it here or leave the default; the design-director commits the register accordingly.
     **Cinematic story option (Remotion):** if the deck is a **story/cinematic** piece of full-bleed
     IMAGE scenes (not data cards/charts) — e.g. a historical story — and the Remotion tier is installed
     (doctor.py reports it), offer it as a look and set `meta.renderer:"remotion"`; it renders images +
     Ken Burns + narration + captions + callouts via `render_remotion.py`. It does NOT render the HTML
     archetypes, so keep a designed/html/chart deck on the default local renderer (`meta.renderer:"local"`).
   - **④ Length** *(→ `meta.target_seconds` AND `meta.aspect` — one decision)* — the finished
     runtime, which also fixes orientation/platform. Menu: **Vertical short ~30–45s** (9:16 —
     Shorts/Reels/TikTok) · **Quick explainer ~60–90s** (16:9) · **Standard ~2–3 min** (16:9) ·
     **In-depth ~5 min+** (16:9) · Vertical long-form (9:16, longer) · Custom exact. Map the pick to
     `meta.target_seconds` (~40 / ~75 / ~150 / ~300; an explicit "4 minutes"→240 via Other) and
     `meta.aspect` (9:16 for a vertical option, else 16:9). **Captions are burned in by default**
     (`captions:true`); (Other → captions OFF, per-word karaoke highlight, or a reduced-motion
     accessibility variant). `meta.target_seconds` is exactly the field the **content-planner** turns
     into beat count (**beats ≈ target_seconds/4**, with per-beat `est_seconds` summed to the target)
     and the design-director reads to scale hero/climax cadence — so it SUBSUMES the old per-slide
     pace ask (a per-slide ceiling, if ever wanted, is just `target_seconds / beats`).
   - **⑤ Voice engine** *(→ `meta.voice`; its own screen B, since screen A already holds 4 buttons)* —
     the narration engine. Menu: **edge-tts** (free **default**, natural, needs network, accent-matched;
     the ONLY engine that emits per-word timings for word-exact caption/reveal sync) · **MiniMax**
     (paid, most natural, esp. **Chinese**; needs a key) · **OpenAI** (paid, premium neural; needs a
     key) · **macOS `say`** (offline, robotic fallback). (Other → an accent or gender preference.)
     State the tradeoff aloud: only edge-tts gives per-word timings, so say/MiniMax/OpenAI HTML reveals
     use the text-position estimate (tracks the voice's pacing, not word-exact). A cloud engine
     (MiniMax/OpenAI) then triggers **Batch 2** (key setup out-of-band + a voice-sample pick).
   - **+ Grounding material** *(a plain prompt, NOT a selectable question — it doesn't fit 2–4
     options)*: ask for **source material to ground the narration** — the paper PDF, the code repo,
     a report or notes. Slides alone rarely say enough to narrate *well* (this is what step 3
     depends on). If they have none, tell them you'll **web-research the topic** (the latest, as of
     today) to ground and fact-check the script instead.

   **Batch 2 — cloud-voice setup (ONLY if Batch 1 ⑤ Voice engine = MiniMax or OpenAI).** First get the API key
   **OUT OF BAND** — have them `export MINIMAX_API_KEY=…` / `export OPENAI_API_KEY=…` in their own
   shell (they can type `! export …` in this session) or put it in `~/.minimax_key` /
   `~/.openai_key`. Do **NOT** ask them to paste it into chat; if they paste it anyway, warn it lands
   in the transcript and tell them to **rotate it** afterward. Never write a key into
   `storyboard.json`, a script, a log, or any committed file — `tts.py` reads it from env / the key
   file only. Then, **by provider:**
   - **MiniMax** → ask **gender** (Female / Male / Either — it selects which samples to synthesize).
     Once the key is set, run `python scripts/voice_sample.py <out_dir> --gender <female|male>` — it
     synthesizes a short sample per curated human-sounding candidate (natural/conversational, never
     theatrical) into `<out_dir>/voice_samples/`. Have the user **listen and pick**, then set
     `meta.voice = "minimax:<the pick>"` (and `meta.voice_gender`). Bare `minimax` uses the catalog
     default for the gender. **Do NOT show OpenAI voice names to a MiniMax user.**
   - **OpenAI** → pick a **preset voice** directly (gender is implicit in the pick — don't ask it):
     buttons **Nova** · **Onyx** · **Shimmer** · **Alloy**; Echo · Fable via Other → set
     `meta.voice = "openai:<name>"`.

   **Batch 3 — AI imagery (ONLY if Batch 1 ③ = "AI cover + soft bg" or "HTML + AI backdrops",
   i.e. `image_source:openai`).** Confirm the spend first, then ask:
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
   - **Image cost** (`meta.image_quality`): **Low** ~$0.01/img · **Medium** ~$0.04 (default) ·
     **High** ~$0.17 (worth it for a hero cover). Set **`meta.image_size` FROM the aspect** — 9:16 →
     `1024x1536`, else `1536x1024` — so a vertical deck gets portrait imagery, not landscape.
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
     ① Dispatch `agents/design-director.md` in **CONTEST mode** → `register_candidates` (forced-divergent
     angles; see its "Register CONTEST — Phase A"). ② Per candidate `<key>`: make `<out>/_contest/<key>/`,
     run `python scripts/theme.py <out>/_contest/<key> --style <its visual_style> [--accent …]` for its
     own theme.css, author ONE representative page from its `frame_spec` — **linking
     `<out>/_contest/<key>/theme.css`, NOT `<out_dir>/theme.css`** (which doesn't exist yet; the
     html-pages boilerplate's theme link is substituted with the candidate's) — then
     `python scripts/snapshot.py <page> <out>/_contest/<key>/frame.png` (**add `--vertical` when
     `meta.aspect` is 9:16, `--no-captions` when captions are off or `caption_mode` is `band`** — the
     same exemptions keyframe_qa reads from the meta)
     — exit 2 = floor issues: repair ONCE in-register or disqualify; exit 3 = rendered but floor NOT
     probed (CDP unavailable): do NOT record a `rendered` floor verdict — fix Chrome/CDP or drop the
     whole contest to paper mode. ③ Dispatch `agents/design-critic.md`
     in **judge mode** (give it the PNG paths + specs + `meta.audacity`): floor-breakers out, survivors
     ranked, ONE winner (or REDIVERGE once — never twice). ④ Surface the winner + runner-up to the USER
     via `AskUserQuestion` (winner first with "(Recommended)"; include the frame paths so they can look) —
     their pick is FINAL: record it as `register_contest.winner` (+ `user_pick: true`). ⑤ Continue to the
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
     judges them. **Build the storyboard by MERGING the two plans:** the design's `visual.type`+`props`
     become each scene; its `transition` becomes the per-scene edges; a `climax` beat's scene carries
     `props.climax:true` — the climax MARKER (`rhythm_qa` reads it); it also drives the key-number landing
     hold only on a `chart` counter (a harmless no-op on any other form); its `icons`/`media`/`cue` shape the authored page (`.icon-tile`
     rows per `references/icons.md`). **Copy the content plan's `arc_kind` to `meta.arc_kind`** so
     `rhythm_qa` relaxes the persuasive-arc checks on an expository (tutorial/reference) video.
     **Also persist the interview's audacity into `meta.audacity`** — `validate.py`'s register-contest
     lints read it from the storyboard meta; left unset it defaults to `balanced` and a bold run's
     missing-contest warning would silently never fire. **Keep BOTH plan files** — the critic
     panel (step 5) receives them: `critic-content`/`critic-narrative` audit the content plan (continuity,
     relation, faithfulness); the **design-critic** audits the design plan (motif, form diversity,
     transitions, icons, whitespace, rhythm, colour, motion).
- **Theme:** run `scripts/theme.py <out_dir> [--style <meta.visual_style>]` AFTER the design plan and BEFORE
  authoring pages or programmatic scenes — it samples `frames/` for a curated light/dark palette fitting the
  topic (or pass `--mode/--accent/--accent2/--bg` from the **design-director's** `theme` when there are no
  frames). **Pass `--style <the deck's visual_style>`** (from `references/visual-styles.md`) so the chosen
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
4b. **Image prompts (gpt-image tier only).** If `meta.image_source == "openai"`: for each
    VISUAL/conceptual scene, author a grounded `image_prompt` from the narration + the chosen
    style, tagged `image_tag:"broll"` and `fit:"cover"`; keep DATA in `chart` scenes (never AI).
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
    **Pace the cuts:** a static AI image drags even with Ken Burns — keep each image scene's
    narration short so it holds only ~5–8s, and prefer MORE, SHORTER b-roll cuts over a few
    long holds (a 12s hold on one frame reads as sluggish; two 6s cuts feel alive).
    The critic panel (step 5, R1e via `critic-content`) reviews the prompts.
    🔴 **CHECKPOINT · 🛑 STOP:** present every prompt + the estimated cost
    (`imagegen.cost_estimate(n, quality)`) and get sign-off BEFORE spending. Then run
    `imagegen.py <out_dir>` (the paid step; cached after). No key / API error → fall back to the
    free tier (drop `image_prompt`, use programmatic/slide) and tell the user.
    **HTML-tier per-beat `media` images:** generate each by calling imagegen directly —
    `imagegen.generate(prompt, out_path, key)` (key path) or `imagegen._generate_codex(prompt, out_path)`
    (Codex) — then reference the file by `file://` in the page. The storyboard `image_source:"openai"`
    CLI path of `imagegen.py` drives the non-HTML tiers, not these.
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
     UP and never overrides a floor)**, transition rhythm vs `relation` (D3), icons (D4),
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
   catches in ~1s what would otherwise waste a multi-minute render); skim the warnings too.
   **Also run `python scripts/rhythm_qa.py <out_dir>`** (needs the real durations, so after tts) — it
   flags flat pacing: uniform scene lengths, a mis-placed or missing climax, a non-sparse closer, an
   over-held static image, or no attention reset for >~35s. Fix the ERRORs; treat the WARNs as
   direction (vary `est_seconds`, place the climax at ~75–80%, split a long image hold).
   **And run `python scripts/pedagogy_qa.py <out_dir>`** — the teaching-order gate: it ERRORs on a
   concept used before it is introduced (walks `content_plan.json`'s concept DAG). Fix every ERROR;
   it no-ops if `content_plan.json` wasn't persisted.
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
   re-render) before delivering. Deliver `out.mp4`, `out.srt`, and the editable `storyboard.json`
   only after both `validate.py` and `check_av.py` exit 0.
10. **Iterate** — any change = edit `storyboard.json`, then re-run render (the per-slide
    clip cache re-renders only changed slides) and tts (`--only N`). Never hand-edit the video.

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
  stay in sync. Reach for it (e.g. `1.2–1.3`) when a faithful script overruns the target runtime.
- `meta.image_source` is `none` (default, free) or `openai` (gpt-image-2, paid). AI images are
  generated once by `imagegen.py` and CACHED under `.assets/` — re-renders are free + offline.
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
DATA always stays in faithful `chart` scenes — never render numbers/figures as an AI image.
The full-AI escape hatch (`image_source:"openai"` with data as AI) is the user's call, but the
`critic-content` flags every data-bearing AI scene.

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
| Captions/text look wrong or font missing | render.py falls back to PIL's default font (still draws) | Confirm `assets/fonts/DejaVuSans.ttf` and `DejaVuSerif.ttf` exist (the serif silently degrades to sans if absent) |
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
