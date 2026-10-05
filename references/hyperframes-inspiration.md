# HyperFrames — design reference & improvement backlog

> **Maintainer-facing only.** This file is NOT loaded by any agent, step, or runtime reference — it is a
> design-inspiration + roadmap doc for whoever evolves the skill. It contains other-engine ideas and some
> unimplemented `(open)` backlog, so it must NOT be cited as an authoring instruction during a run.

Source: [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) (Apache-2.0),
HeyGen's open-source **HTML-native, seekable-timeline video engine** — *"Write HTML. Render
video. Built for agents."* Compositions are plain HTML with `data-start`/`data-duration`/
`class="clip"` timing attributes; one paused GSAP timeline per composition is **seeked
frame-by-frame** in headless Chrome and encoded with FFmpeg → deterministic MP4. Around the
engine sit 19 agent skills (a `/hyperframes` router → creation workflows → on-demand domain
skills), a catalog of reusable blocks, and `frame.md` design presets.

**Why it's relevant here:** `topic-to-video` is a smaller, opinionated cousin of the same
architecture (headless-Chrome HTML tier + ffmpeg + sub-agents + `references/` progressive
disclosure). Most of HyperFrames' best ideas transfer. This file records the analysis so the
backlog isn't lost — it is a reference, not part of the runtime pipeline.

## Already adopted
- **Pre-render `validate.py` + `doctor.py` gates** (Tier-1 #2). `doctor.py` is an environment
  preflight (step 1); `validate.py` is a ~1s pre-render correctness gate (step 9 / `--pre-tts`
  after authoring) mirroring `check_av.py`'s pure-`evaluate` + exit-non-zero contract. Catches a
  missing asset / duplicate index / wall-of-text caption in seconds instead of after a render.
- **Coordinate-target zoom** (Tier-1 #3). `motion-grammar.md` documents deriving `motion.to`'s
  anchor from a target box center (so the push frames the region) and the motivated-motion rule;
  `validate.py` warns when a callout is off-center but the camera stays centered, and when a zoom
  ends past 1.25× (text-softening limit).
- **Caption craft** (Tier-2 #7). `validate.py` warns on widows (lone-word last line), too-fast
  (< 0.7 s) segments, and > 3 wrapped lines; `captions.md` formalises the rules and corrects the
  stale "one block per slide" note (render burns timed multi-segment captions); `critic-narrative`
  R7 checks them at the script stage.
- **Beat direction + rhythm + density + motion verbs** (Tier-2 #4/#5). `content-planner` gained an
  optional per-beat `motion_intent` verb, a "direct each beat — concept before layout" rule, a
  named `rhythm` field, and html-beat composition-density guidance; `motion-grammar.md` carries the
  shared motion-verb vocabulary; `scriptwriter` aligns spoken emphasis to the motion verb. (Kept
  honest to the free tiers — verbs must be deliverable by the existing renderers, not arbitrary
  keyframing.)

## Backlog — ranked, filtered to the free/local single-skill constraint

### Tier 1 — highest impact
1. **Seekable paused-timeline rendering (the headline idea).** Today the HTML tier authors N
   discrete CSS reveal-states and screenshots each (`scenes.py:render_html`). HyperFrames
   registers ONE `gsap.timeline({paused:true})` at `window.__timelines["<id>"]` and seeks it per
   frame — same headless-Chrome+ffmpeg stack, no React/paid deps, but you get eased
   interpolation for free, coordinate-target zoom, dynamic content sequencing, and richer
   transitions, with *less* authored code per scene. It dovetails with the existing `data-cue`
   word-timings (they become timeline labels/absolute starts). **Biggest lift** — changes the
   `cues.py`/reveal model and `render_html`; prototype on ONE scene before committing. Pair with
   a short **determinism contract** (their `determinism-rules.md`): animate only
   `opacity/x/y/scale/rotation/color`; no `Date.now()`/unseeded `Math.random()`/event state;
   measure `getBoundingClientRect()` once at setup — which also makes `check_av.py` drift more
   reliable. Refs: `skills/hyperframes-core/SKILL.md`,
   `skills/hyperframes-animation/adapters/gsap-timeline-and-labels.md`.
2. **Pre-render validation gate.** ✅ Done — see "Already adopted".
3. **Coordinate-target zoom replaces blind Ken Burns.** ✅ Done — see "Already adopted". (Note:
   the slide tier frames via the zoompan anchor, not GSAP's inverse-translate; the full
   measure-once-and-translate version arrives with #1.) Ref:
   `skills/hyperframes-animation/rules/coordinate-target-zoom.md`.

### Tier 2 — creative quality
4. **Experiential beat direction + named rhythm in `content-planner`.** ✅ Done — see "Already
   adopted". Future: lift the `mood_refs` field and the 32–48px→64–120px scale table into the
   html authoring guidance. Refs: `skills/hyperframes-creative/references/beat-direction.md`,
   `.../video-composition.md`.
5. **Motion-verb vocabulary.** ✅ Done — see "Already adopted".
6. **`frame.md`-style design presets.** Beyond `theme.py`'s sampled palette, ship 3–4 vetted
   presets (each a `FRAME.md`: palette + type scale + spacing + composition treatments + a
   pre-render self-audit). Refs: `skills/hyperframes-creative/frame-presets/*/FRAME.md`. **(open)**
7. **Caption-craft rules.** ✅ Done — see "Already adopted". (Phrase-grouping by intonation
   remains a future refinement of `_split_caption_chunks`.) Ref:
   `skills/embedded-captions/references/composition-craft.md`.

### Tier 3 — new capabilities (optional)
8. **Background music + ducking** (`mix.py`): a real gap — no BGM/SFX today. Their model writes
   separate VO/BGM/SFX tracks and ducks BGM ~8 dB under speech. Ref: `skills/hyperframes-media/`.
9. **Media ledger** (`manifest.jsonl`) recording source/license/prompt for AI/stock assets.
   Ref: `skills/media-use/SKILL.md`.
10. **Whisper transcription** as the caption-timing fallback when `words.json` is absent (the
    `say`-engine / non-English path).

## Deliberately NOT adopting
- **Multi-skill router split** — `topic-to-video` already has `references/` progressive
  disclosure + an `agents/` panel; staying one skill is correct.
- **AWS Lambda rendering, registry/catalog blocks, multi-provider paid TTS chains** — out of
  scope for a free/local tool.
- **HTML-in-canvas WebGL/Three.js bloom** — fragile and heavy in headless Chrome for marginal
  gain.
- **Persuasion/marketing beat taxonomy** — HyperFrames optimizes for *selling*; these decks are
  *explanatory*, so adopt the rhythm/density ideas (#4) but skip the FOMO/CTA framing.
