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
  Accepts .pptx, .pdf, an image folder, or a hand-off from slide-maker. Local & free by
  default (macOS say + ffmpeg); optional cloud TTS. Generates an editable storyboard,
  lets the user edit the script, renders one sample slide for sign-off, then the full
  video. Trigger even without the word "skill".
---

# Slides to Video

You turn slides into a narrated video. Source of truth is `storyboard.json` — you edit
text/timing; the scripts render the media.

## Tools (all local & free; verify with `scripts/_common.have_tool`)
`soffice` (pptx→pdf), PyMuPDF `fitz`, `python-pptx`, **edge-tts** (preferred neural voice, free, cross-platform — needs network), macOS `say` (offline fallback), `ffmpeg`, PIL.
Captions burn via PIL + a bundled font (no libass needed). Optional: OpenAI/ElevenLabs
TTS if the user gives an API key.

## Pipeline scripts
- `scripts/ingest.py <input> <out_dir>` — pptx/pdf/image-folder → `frames/` + skeleton `storyboard.json` (pulls speaker notes from pptx).
- `scripts/tts.py <out_dir> [--only N]` — narration → `audio/` + real durations. With edge-tts, also writes `audio/NN.words.json` (per-word start times), used for audio-synced HTML reveals; emits `.mp3`. With macOS `say`, emits `.aiff` (no words.json).
- `scripts/theme.py <out_dir> [--mode light|dark] [--accent #hex] [--accent2 #hex] [--bg #hex]` —
  derive a topic-fitting palette from `frames/` (or the passed overrides) and write
  `<out_dir>/theme.css` (the HTML tier links it). Run before authoring HTML pages.
- `scripts/imagegen.py <out_dir> [--key KEY]` — OPTIONAL paid tier: generate AI scene images
  via OpenAI `gpt-image-2` for scenes that carry an `image_prompt`, cached under `.assets/`
  (re-runs are free). Auto-uses the Codex CLI (no key) when installed, else needs
  `OPENAI_API_KEY`/`~/.openai_key`; `meta.image_provider` (`auto`/`codex`/`openai`) selects
  the path. Only acts when `meta.image_source == "openai"`.
- `scripts/render.py <out_dir> [--sample N] [--only N] [--vertical]` — storyboard → `out.mp4` + `out.srt`.
- `scripts/cues.py` — pure anchor→cue-time resolver: reads per-scene `audio/NN.words.json` (edge-tts per-word timings) and resolves each `data-cue` anchor phrase to an absolute timestamp, used by `render_html` for audio-synced HTML reveals.
- `scripts/check_av.py <out_dir>` — deterministic A/V gate: probes `out.mp4` video-vs-audio duration + per-clip sample-rate uniformity across `.clips/`; exits non-zero on A/V drift above tolerance (0.3 s) or non-uniform rates. Run AFTER the full render (step 9) as a gate before delivery.
- `scripts/doctor.py [--json]` — environment preflight: reports which tools/libraries are present (ffmpeg/ffprobe/PIL required; PyMuPDF/python-pptx/edge-tts/soffice/Chrome/font optional) and, for each missing one, the stage it gates + the install hint. Exits non-zero only when a REQUIRED dep is missing. Run once at the START (step 1).
- `scripts/validate.py <out_dir> [--pre-tts] [--vertical] [--json]` — deterministic PRE-render gate on `storyboard.json` (runs in ~1s): structural contract, duplicate indices, every referenced image/audio/html-page/`file://` asset + `theme.css` exists on disk, caption craft (no wall of text, no widow, ≥0.7s on screen — see `references/captions.md`), motion sanity (zoom delta + zoom-past-1.25 + callout-framing — see `references/motion-grammar.md`), CJK-font/cue/pacing/anti-slop warnings. Exits non-zero on any ERROR. Run BEFORE every render (step 9); `--pre-tts` validates right after authoring (skips audio checks); `--vertical` mirrors render's 9:16 canvas (also auto from `meta.aspect`). Errors block; warnings don't.
- `scripts/scenes.py` — deterministic ANIMATED scene renderers (no slides): `title`/`keypoints`
  (PIL), `chart`/`timeline`/`compare` (matplotlib), `html` (headless Chrome). A storyboard scene
  with `type` `title`/`keypoints`/`chart`/`timeline`/`compare`/`html` (+ a typed `props` block)
  renders an animation instead of a slide image; `type` defaults to `slide` (unchanged). Animated
  scenes render ONLY their `props` (faithful by construction).
- **HTML pages tier** (optional, free): `scenes.py:render_html` screenshots bespoke designed
  HTML pages (authored on `assets/html/base.css`, see `references/html-pages.md`) via headless
  **Google Chrome** — no new dependency. Each page's paused CSS reveals are captured frame-by-frame.
  **Audio-synced reveals:** tag each point's reveal element `data-cue-index="N"` (spoken order) and
  `data-cue="<spoken anchor>"`. When edge-tts `audio/NN.words.json` exists, `render_html` resolves
  each anchor's timestamp via `cues.py` and reveals each point exactly when its phrase is spoken;
  falls back to the paced `anim_seconds` stagger otherwise (macOS `say` or missing anchor).
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
   Then a **compact AskUserQuestion**: the deck/PDF/image-folder to narrate;
   **source material to ground the narration** — the paper PDF, the code repo, a report or
   notes (slides alone rarely say enough to narrate *well*); audience & goal; **video
   language**; voice — **edge-tts** (natural neural, free, needs network; then pick **accent** + **gender**
   from `references/tts-voices.md`) by default, with macOS `say` as the offline fallback, or a
   **paid cloud voice if they want the most natural result** — **MiniMax** (`minimax:<voice_id>`,
   needs `MINIMAX_API_KEY`; markedly more natural, especially Chinese) or OpenAI (`openai:<voice>`).
   Note the tradeoff: only edge-tts emits per-word timings, so MiniMax/OpenAI/say HTML reveals use
   the paced fallback, not exact audio-synced cues.
   **If they choose MiniMax (or an OpenAI voice), ASK for the API key when they pick it** — MiniMax
   T2A is key-authenticated; there is **no key-free "subscription/plan" path** (unlike Codex
   image-gen, which can use the Codex plan without a key), so a key is required to synthesize.
   **Get the key WITHOUT leaking it:** have them provide it OUT OF BAND — either `export
   MINIMAX_API_KEY=…` in their own shell (they can type `! export MINIMAX_API_KEY=…` in this
   session) or put it in `~/.minimax_key`. Do **NOT** ask them to paste it into the chat; if they
   paste it anyway, warn that it lands in the transcript and tell them to **rotate it** afterward.
   Never write the key into `storyboard.json`, a script, a log, or any committed file — `tts.py`
   reads it from the env / `~/.minimax_key` only. captions on/off; aspect (16:9 default / 9:16);
   target pace (a seconds-per-slide ceiling); **image source** — **Free** (programmatic animation / slides, the default) vs **gpt-image**
   (OpenAI `gpt-image-2`, **paid**, needs `OPENAI_API_KEY`). If gpt-image: ask for the key
   **fresh, each run** (env var or pasted — never reuse a stored one; if pasted, warn it lands
   in the transcript and tell them to rotate it afterward), and ask a **style** (photoreal ·
   cinematic · editorial illustration · 3D render · watercolor · blueprint/diagram · minimal
   flat · or free-text) + a **focus** (subject emphasis).
   Set `meta.image_source`/`image_quality`(default medium)/`image_size`(default
   1536x1024). Default stays Free — AI imagery is opt-in and costs money.
   A third visual mode is **HTML pages** — bespoke, designed pages (`type:"html"`) rendered by
   headless Google Chrome (free, no dependency; needs Chrome installed). Choose it for a
   "designed deck" look. The content-planner designs the beats; you author one
   `pages/scene_NN.html` per beat on `assets/html/base.css` (faithful — real content only),
   following `references/html-pages.md`. Set `meta.chrome_path` if Chrome isn't at the default
   macOS location.
   **Image provider:** if the **`codex` CLI is installed**, generate via Codex's native
   image-generation (NO key — it uses your Codex plan; slower, ~minutes/image). Otherwise ask for
   the OpenAI key (`OPENAI_API_KEY` or `~/.openai_key`). If neither, fall back to the free
   programmatic / HTML tier. `meta.image_provider` is `auto` (default — Codex-first when installed),
   `codex`, or `openai` to force one.
   If the user has no material, tell them you'll
   web-research the topic to ground the script instead.
   - **Language**: default the narration to the **slides' own language** (detect it from the
     ingested text), but always confirm it as an option — users often want a video in a
     *different* language than the deck (e.g. Chinese slides, English voice-over for an
     international audience). Whatever they pick, set `meta.language` to its code (`en`, `zh`,
     `ja`, `ko`, `es`, `fr`, `de`, …). This drives the **caption font** (CJK needs a system
     font — the bundled Latin one tofus) and the **default TTS voice**, so getting it right
     here prevents mojibake captions and mispronounced audio downstream.
2. **Ingest** — run `ingest.py`. Report slide count and whether speaker notes were found.
3. **Understand the material DEEPLY — never narrate from the slides alone.** A good
   voice-over explains *why*, connects ideas, and is precise — that requires real
   understanding the bullets don't carry. This step is what makes the script good.
   - **Material provided** → read it properly, not skimmed: a paper end-to-end (intro →
     method → *every* results figure/table → conclusion); a codebase via its README + the
     key modules; a doc in full. Then write a short **comprehension brief**: the
     one-sentence message, the key contributions, the method essence, and — per slide —
     what it is *really* showing and the point to land. Narrate from this brief.
   - **No material** → `WebSearch`/`WebFetch` the topic to ground and enrich: confirm the
     facts, numbers, names and framing the slides imply, and fold in current context.
     **Research the LATEST, up to today** — put the current year / "latest" in your queries,
     prefer the most recent sources, and verify every figure is current *as of today's date*
     (not a stale older number); for a time-sensitive fact, note its as-of date. Treat
     it as a **fact-check**, not flavour — with no source, you are the only thing standing
     between a confident-sounding wrong claim and the viewer.
   - **Either way, stay faithful:** every claim and number in the narration must trace to the
     material or a verified source — never invent results, numbers, or citations the
     slide/paper doesn't support. A forward-looking aside is fine only if flagged as your
     own addition.
3.5. **Content plan (director) — design the video as CONTENT before authoring.** Dispatch
     `agents/content-planner.md` on the comprehension brief + material. It returns an ordered set
     of **informative beats** — each with a learning point (traced to the material), the most
     informative visual (`chart`/`compare`/`keypoints`/`timeline`/`title`/`html`, NOT decorative photos),
     a narration intent, and a short `est_seconds`. The planner may also emit `climax: true` (one beat
     ~75–80% through — the payoff), `hold: true` (final beat, sparse), and per-point `cue` arrays
     (one anchor phrase per point, in spoken order, for audio-synced HTML reveals). Build the storyboard
     scenes from the plan (**informative-first**); author the short per-beat narration in step 4.
- **Theme (HTML tier):** run `scripts/theme.py <out_dir>` AFTER the content plan and BEFORE
  authoring any HTML page — it samples `frames/` for a curated light/dark palette fitting the topic
  (or pass `--mode/--accent/--accent2/--bg` from the planner's `theme` suggestion when there are no
  frames). Pages link `base.css` → `theme.css` → `motifs.css`. 🔴 the plan checkpoint now also shows
  the palette + mode.
- **Re-conceive, don't mirror:** the content-planner designs a video arc (hook + throughline +
  resequencing), not the slide order — faithful to the substance.
- **Illustrated pages:** build a beat's `media` as a `.split` page (text + a STATIC image panel,
  see `references/html-pages.md`; Ken-Burns is disabled inside `.split` so it doesn't compete with
  revealing bullets — Ken-Burns is for full-bleed hero `.bg-photo` only); generate the image via
  `imagegen` (codex/key); keep it a generic broll. Most pages stay typographic.
     🔴 **CHECKPOINT · 🛑 STOP:** show the content plan (arc + beats + chosen visuals) and the
     derived theme palette (mode + colors), and get the user's OK before authoring narration.
4. **Write the manuscript — dispatch `agents/scriptwriter.md` (the WRITE specialist).** Give it
   the content plan (or, with no plan, the per-slide intent + slide text), the comprehension
   brief + material, `meta.language`, and the pace ceiling. It returns the final spoken line per
   beat (`{id → narration}`) + a `flags` list of any beat it could not source. Write those lines
   into each scene's `narration`; **resolve every flag** (drop or repair the unsourced beat)
   before proceeding. The scriptwriter follows `references/narration-writing.md` (the style
   basis). The on-screen **captions are auto-derived from the narration**, so its words are also
   the subtitle. (PLAN → **WRITE** → CHECK: planner designs, scriptwriter writes, the parallel critic panel — `critic-narrative` + `critic-content` — checks in parallel.)
4b. **Image prompts (gpt-image tier only).** If `meta.image_source == "openai"`: for each
    VISUAL/conceptual scene, author a grounded `image_prompt` from the narration + the chosen
    style, tagged `image_tag:"broll"` and `fit:"cover"`; keep DATA in `chart` scenes (never AI).
    Generic/atmospheric prompts only — no real logos, faces, named vehicles, or text in-image.
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
5. **Parallel critic panel — narration + subtitle (REQUIRED, not optional).** Dispatch
   `agents/critic-narrative.md` AND `agents/critic-content.md` **concurrently — in ONE
   message with two Agent calls** — on the storyboard **plus the comprehension brief /
   source material**, so both critics can check facts, not just style.
   - `critic-narrative` verifies: narration is **precise and faithful** (no wrong, vague, or
     invented facts/numbers); subtitle text matches spoken words, segments into clean readable
     lines, fits on screen, no typos or garbled text; narration is in **`meta.language`** and
     **`meta.voice` matches that language** (a wrong-language voice would garble the audio).
   - `critic-content` verifies: audio↔visual alignment per beat (R2), script faithfulness and
     claims traceability (R1d/R1e including AI image prompts), scene/visual selection quality
     (R3/R5/R6), pace and cuts.
   **Overall PASS only when BOTH critics return PASS.** Apply the **UNION** of their required
   EDITS to the storyboard, then re-dispatch both critics (or just the failing one) until both
   return PASS. THEN:
   🔴 **CHECKPOINT · 🛑 STOP:** present the full, critic-panel-passed script and get the user's
   edits/approval BEFORE any TTS. Do not synthesize audio until they sign off.
6. **Motion** — read `references/motion-grammar.md`. Default motion is a gentle centered
   zoom `from:[0.5,0.5,1.0] → to:[0.5,0.5,1.12]` (keep zoom delta ≤0.20). **Callouts are OFF
   by default** — do NOT add emphasis boxes. They are easy to mis-place and a translucent
   box over a dark slide reads as a muddy coloured blob; the slide already shows the content.
   Add a callout ONLY if the user explicitly asks to emphasise a named region — then exactly
   one, tightly placed on that region, and confirm its position from the rendered sample.
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
   catches in ~1s what would otherwise waste a multi-minute render); skim the warnings too. Then
   `render.py <out_dir>` (for 9:16 set `meta.aspect:"9:16"` — render and validate both honor it;
   the `--vertical` flag also forces it on both), and the POST-render A/V gate:
   `python scripts/check_av.py <out_dir>`. A non-zero exit means A/V drift or non-uniform clip
   rates — fix the root cause (clear `.clips/`, fix audio or regenerate failing clips, and
   re-render) before delivering. Deliver `out.mp4`, `out.srt`, and the editable `storyboard.json`
   only after both `validate.py` and `check_av.py` exit 0.
10. **Iterate** — any change = edit `storyboard.json`, then re-run render (the per-slide
    clip cache re-renders only changed slides) and tts (`--only N`). Never hand-edit the video.

## Guardrails
- `duration` always comes from rendered audio (tts.py sets it) — never guess timings.
- Set `meta.voice`, `meta.captions`, and `meta.language` in the storyboard, not via flags.
  `meta.voice` is one of: `auto` (default — tts.py prefers edge-tts, else `say`),
  `edge:<id>` (e.g. `edge:en-GB-SoniaNeural`), `say:<voice>`, `openai:<voice>`, or
  `minimax:<voice_id>` (or bare `minimax` → a catalog voice by `meta.language`+`meta.voice_gender`).
  MiniMax tunables: `meta.tts_model` (default `speech-02-hd`), `meta.minimax_base` (mainland host),
  `meta.minimax_group_id` (mainland only); key via `MINIMAX_API_KEY` / `~/.minimax_key`.
- `meta.image_source` is `none` (default, free) or `openai` (gpt-image-2, paid). AI images are
  generated once by `imagegen.py` and CACHED under `.assets/` — re-renders are free + offline.
- **HTML pages tier:** `type:"html"` scenes render an authored page via headless Chrome
  (`render_html`), captured as seekable CSS reveals. Pages render only real content (faithful);
  the per-clip cache busts when the page file, `theme.css` (re-theming), or `audio/NN.words.json`
  (new edge run) changes. Locate Chrome via `meta.chrome_path` if needed.
- **Anti-slop (critic R8 / AV-critic):** no emoji in titles; no hardcoded hex — use semantic vars
  (`var(--bg)`, `var(--accent)`, etc.); no gradient-mesh backgrounds; no player-chrome / progress
  bars / timecodes; no more than 2 consecutive beats with the same `visual.type`.
- **Audio-synced reveals (HTML tier) — content must not lead the voice.** Make multi-point pages
  audio-synced by DEFAULT: tag each point `data-cue-index="N"` (spoken order) + `data-cue="<spoken
  anchor>"` (a phrase the narration says); the content-planner emits a per-beat `cue` array for this.
  When edge `audio/NN.words.json` exists, `render_html` reveals each point exactly when its phrase is
  spoken. If a page is NOT cued, LEAVE `anim_seconds` unset — `render_html` defaults it to spread the
  reveals across ~0.7× the scene (tracking the speaking pace) instead of cramming them at the start; a
  small `anim_seconds` on a long content page makes content appear before it's spoken. `validate.py`
  warns on that, and `critic-content` (R2) fails an uncued multi-point page whose reveals lead the audio.
- **Theming:** the HTML tier is themeable via `theme.py` → `theme.css` (semantic `:root` vars);
  pick a palette/mode that fits the TOPIC (not always dark). Author pages with the vars, never raw hex.
  `theme.py`/`theme.css` themes ONLY the `html` tier. The programmatic scenes (`title`/`chart`/
  `keypoints`/`compare`/`timeline`) always render on the dark palette — do NOT mix a light-theme
  HTML deck with programmatic scenes expecting them to match; keep all programmatic scenes or all
  HTML scenes if a consistent look matters.
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

## Imagery faithfulness (AI / b-roll)
Every on-screen visual is one of three classes; `critic-content` (R1e) enforces them:
- **`motif`** — a generic programmatic vector. Always allowed; asserts no fact.
- **`broll`** — a generic illustrative image, including an AI-generated one (`image_prompt`).
  Allowed ONLY as generic/atmospheric backdrop — no real logos, faces, named vehicles, or
  in-image text, and it must not sit as "evidence" beside a specific factual claim.
- **`asserted`** — imagery standing in for a specific named vehicle/mission/person/event/figure.
  For an AI image this is FABRICATION (the model invents it) and is NOT allowed.
DATA always stays in faithful `chart` scenes — never render numbers/figures as an AI image.
The full-AI escape hatch (`image_source:"openai"` with data as AI) is the user's call, but the
`critic-content` flags every data-bearing AI scene.

## When a step fails (if → then → still-failing)

| Trigger | First fix | If it still fails |
|---|---|---|
| `ingest.py`: `soffice` missing / hangs | Kill stale `soffice`; ask user to export the deck to PDF and feed the `.pdf` | Feed a folder of exported slide PNGs instead |
| pptx has no speaker notes | Generate narration from visible slide content + any source docs | Ask the user for the deck's intent per section |
| `tts.py`: cloud voice errors / no `OPENAI_API_KEY` | It auto-falls back to the language-matched say voice (e.g. say:Tingting for zh) and prints a notice — continue | Set `meta.voice` to an explicit local `say:` voice |
| `tts.py`: MiniMax error / no `MINIMAX_API_KEY` | It auto-falls back to the language-matched say voice and prints a notice — continue | Verify `MINIMAX_API_KEY`; on the mainland host set `meta.minimax_group_id` + `meta.minimax_base`; check the `voice_id`/`tts_model` exist for your account |
| `tts.py`: edge-tts not installed | The workflow offers `pip install edge-tts` once; on decline, set `meta.voice` to a `say:` fallback | tts.py auto-falls back to `say` at synth time and prints a notice — continue |
| `tts.py`: edge-tts network error / endpoint down | tts.py catches it and falls back to the language-matched say voice (e.g. say:Tingting for zh) and prints a notice — continue | Switch `meta.voice` to an explicit `say:` voice (fully offline) |
| `imagegen.py`: no `OPENAI_API_KEY` | It prints a notice and leaves those scenes for free-tier fallback — convert them to programmatic/slide and continue | Set the key (`export OPENAI_API_KEY=...`) and re-run `imagegen.py` |
| `imagegen.py`: image API error / rate limit | Per-scene catch → free-tier fallback for that scene; cached scenes unaffected | Retry later; cached images never re-charge |
| `imagegen.py`: Codex run fails / makes no image | `_generate_codex` raises → that scene falls back to the free tier; other cached scenes unaffected | Force `meta.image_provider:"openai"` + provide a key, or use the free programmatic/HTML tier |
| Image tier on but no codex AND no key | Each scene falls back to the free tier with a notice | Install `codex`, or set `OPENAI_API_KEY` / `~/.openai_key`, then re-run `imagegen.py` |
| `render.py`: concat `-c copy` errors (codec/timestamp) | Re-encode the concat (`-c:v libx264 -c:a aac`) — see `references/ffmpeg-recipes.md` | Render per-slide with `--only N` and report the failing slide |
| Captions/text look wrong or font missing | render.py falls back to PIL's default font (still draws) | Confirm `assets/fonts/DejaVuSans.ttf` exists |
| Captions show tofu boxes / □□□ (non-Latin language) | Set `meta.language` so render.py picks a system CJK font (zh→PingFang, ja→Hiragino, ko→AppleSDGothicNeo) | Set `meta.font` to an explicit `.ttc`/`.ttf` that covers the script |
| Narration mispronounced / wrong-language voice | Set `meta.language`; tts.py auto-picks a matching `say` voice (zh→Tingting, ja→Kyoko, …) when you left the English default | Set `meta.voice` explicitly to an installed voice for that language (`say -v '?'` lists them) |
| Narration overruns the seconds-per-slide ceiling | Tighten wording (`references/narration-writing.md`) | 🔴 STOP and propose splitting the dense slide |
| A/V out of sync (one slide) | Never guess timing — `duration` comes from ffprobe; re-run `tts.py --only N` | Re-render that slide with `--only N` |
| A/V drift across the WHOLE video (audio runs longer than the video, worse later) | Mixed audio sample rates across clips (e.g. a partial edge-tts run left some scenes as `say` .aiff @22050 and others edge .mp3 @24000) → the `-c copy` concat desyncs. render.py pins `-ar 48000 -ac 1` per clip to prevent this; clear `<out_dir>/.clips/` and re-render so every clip re-encodes uniformly | Regenerate ALL audio with one engine (delete `audio/`, re-run `tts.py`) so the voice is consistent too, then clear `.clips/` and re-render |
| step 8 critic-av returns REVISE | Read the issue (illegible/mistimed burned caption / off-theme or tofu render / player-chrome) → fix the cause (fix the page/theme, clear `.clips/`, re-render sample) and re-dispatch `critic-av` until it passes, before the 🔴 sample sign-off |
| step 1 `doctor.py` reports a REQUIRED dep missing (ffmpeg/ffprobe/PIL) | Install it (e.g. `brew install ffmpeg`, `pip install pillow`) before proceeding | Optional gaps (edge-tts/soffice/Chrome) only narrow the tiers — adjust the interview, don't block |
| step 9 gate fails: `validate.py` exits non-zero before render | Read each ERROR (missing image/audio/page/`file://` asset, duplicate index, absent `theme.css`) → fix in `storyboard.json` / regenerate the missing asset (run `theme.py`/`imagegen.py`/`tts.py`) | Re-run `python scripts/validate.py <out_dir>` until exit 0 before calling `render.py` |
| step 9 gate fails: `check_av.py` exits non-zero after full render | Read the issue (A/V drift / non-uniform clip rates) → fix the cause (clear `.clips/`, regenerate audio with ONE engine, re-render) | Re-run `python scripts/check_av.py <out_dir>` until exit 0 before delivering `out.mp4` |
| Slide "shivers"/jitters during the zoom | zoompan runs supersampled (`meta.motion_ss`, default 2) then downscales; a `scale` filter must precede zoompan or the frame shrinks. Keep ss≥2 | Raise `motion_ss` to 3 (smoother, slower) |
| Caption is one static line per slide | Captions auto-derive from `narration` — split into sentence chunks timed across the slide; a single full-span entry in `captions` is overridden by the narration track | For custom timing, supply a multi-segment `captions` array |
| `render.py`: no Chrome for an `html` scene | `render_html` errors clearly; set `meta.chrome_path`, or switch those scenes to the free programmatic tier (title/chart/keypoints/compare) | Install Google Chrome, then re-render |
| `html` page renders blank / unstyled | Confirm the page links `assets/html/base.css` + `theme.css` (from `out_dir`) + `seek.js` by ABSOLUTE `file://` path; no external/network assets | Open the page in a browser to debug, then re-render (the cache busts on edit) |

For anything else, read `references/troubleshooting.md` before guessing.

## Red lights — never do this

- ❌ Render audio/video before the user signs off script/sample (honor the 🔴 checkpoints).
- ❌ Narrate from the slides alone, or invent facts/numbers — ground in the material (or a
  web fact-check) and stay strictly faithful (step 3).
- ❌ Skip the critic panel — the parallel `critic-narrative` + `critic-content` check (step 5) is REQUIRED; ship only when BOTH return PASS.
- ❌ Read slide bullets aloud verbatim — write *spoken* narration (`references/narration-writing.md`).
- ❌ Guess a slide's `duration` — it must come from ffprobe via `tts.py`.
- ❌ Hand-edit `out.mp4`; change `storyboard.json` and re-render (`--only N`).
- ❌ Add callouts/emphasis boxes by default — they're OFF unless the user asks; never stack them.
- ❌ Write the OpenAI API key into the storyboard, a script, the manifest, or any persisted/
  committed file — request it fresh each run, pass it only via `OPENAI_API_KEY`/`--key`, and
  remind the user to rotate a key they pasted into the chat.
- ❌ Let a single static frame linger (one long held image reads as sluggish) — keep cuts
  moving (~≤8s/scene), splitting a long scene into shorter beats rather than over-holding.
