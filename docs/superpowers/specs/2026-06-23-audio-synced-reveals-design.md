# Design: audio-synced point reveals (general)

**Date:** 2026-06-23
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal
HTML-tier points currently reveal on a fixed time-stagger over `anim_seconds`, unrelated to when the
narration actually speaks each point. Make each point appear **at the moment its phrase is spoken**,
by deriving per-point reveal timestamps from the TTS audio's word boundaries — with a graceful
fallback to today's paced stagger when timings aren't available. Keep the single-page "build-up"
design, seek-safe (CSS-only, frozen per frame), general across topics/languages.

## Decisions (from brainstorming)
- **Word-timed reveals on one page** (not splitting into one-point sub-scenes).
- **Hybrid anchor:** auto-match each point's label keyword to the spoken words; an explicit per-point
  `cue` phrase overrides when the on-screen label isn't spoken verbatim.

## Data flow
edge-tts word timestamps (`audio/NN.words.json`) → `render_html` reads each point's anchor from the
page (`data-cue` / label) and resolves cue times via `cues.resolve_cues(words, anchors)` → captures
frames around each cue across the full scene + passes `?cues=…&dur=…&p=…` → `seek.js` overrides each
`[data-cue-index]` element's delay to its cue time and freezes per frame.

## Component 1 — `scripts/tts.py` (capture word timings)
- In `_edge`, add `--write-subtitles <out_dir>/audio/NN.<ext>` alongside `--write-media` (the mp3).
- New pure helper `_parse_subs(text) -> [{"w": str, "t": float}]` — parse edge-tts subtitle output
  (handles SRT `HH:MM:SS,mmm` and VTT `HH:MM:SS.mmm` cue timestamps; `t` = the cue START in seconds;
  one entry per cue word/group, in order). The implementer must inspect a REAL edge-tts subtitle file
  once to confirm the exact format before finalizing the parser.
- After a successful edge synth, write `audio/NN.words.json` = the parsed list. On `say`/openai, or if
  subtitle capture fails, write NO words file (→ fallback). Never breaks synthesis if subtitles fail.

## Component 2 — `scripts/cues.py` (new, pure, tested)
- `resolve_cues(words, anchors) -> list[float]`: `words` = `[{"w","t"}]`; `anchors` = ordered anchor
  phrases (one per point). For each anchor, find its phrase in the `words` stream **after the previous
  match** (monotonic, left-to-right), return the matched word's `t`. Normalize for matching (casefold,
  strip punctuation). Rules: an unmatched anchor → `None` placeholder, then post-pass replaces every
  `None`/out-of-order time with an **even spread** between its resolved neighbors (so cues are always
  monotonic non-decreasing and defined). Collisions (two anchors → same/earlier time) nudged ≥ a small
  epsilon apart. No I/O — unit-testable.
- Helper `_norm(s)` (casefold + strip non-alphanumerics) and `_find(words, phrase, start_idx)`.

## Component 3 — `assets/html/seek.js` (cue override)
- Parse `cues` (comma list of seconds) + `dur` (scene seconds) from the page URL query (alongside the
  existing `p`). When `cues` is present: for each element with `[data-cue-index=i]`, set its
  `animationDelay = cues[i]` seconds and treat the timeline total as `dur`; then the existing
  negative-delay freeze at `p` reveals it iff `p*dur >= cues[i]`. When `cues` is absent → current
  behavior unchanged. Non-cued elements (kicker/title) keep their authored stagger.

## Component 4 — `scripts/scenes.py` `render_html` (cue-aware capture)
- Compute `dur = frames / fps`. Look for `<out_dir>/audio/{index:02d}.words.json`. Parse the page
  `src` for point elements carrying `data-cue-index` (regex), reading each one's anchor = its
  `data-cue="…"` attribute if present else its visible label text; collect anchors in cue-index order.
- **If a words file AND ≥1 cued element exist:** `cues = cues.resolve_cues(words, anchors)`; build the
  capture so each cue gets a short reveal burst (`~0.5s` of frames at p around `cue/dur`) and frames in
  between are held copies — i.e., screenshot only at the moments the visible set changes, across the
  FULL duration; every `_chrome_shot` URL includes `&cues=<t0,t1,…>&dur=<dur>` in addition to `?p=`.
- **Else:** the current `anim_seconds` reveal-then-hold path (unchanged). This preserves heroes/title
  and any page without cued points.
- Keep it deterministic and seek-safe (only `_chrome_shot` at chosen `p` values; no wall-clock).

## Component 5 — authoring (`references/html-pages.md`, `agents/content-planner.md`)
- **html-pages.md:** document that a multi-point page tags each point's reveal element with
  `data-cue-index="0|1|2…"` (in spoken order) and, when the visible label differs from the spoken word,
  `data-cue="<the spoken anchor phrase>"`. Without `data-cue`, the element's text is the auto anchor.
  Note the fallback (no edge word timings → paced stagger) and that this is for multi-point pages only.
- **content-planner.md:** the planner may add an optional `cue` (anchor phrase) per point when the
  narration won't say the label verbatim; default is the label keyword.

## Faithfulness & invariants
CSS-only, frozen per frame (seek-safe). Reveal timing only — content unchanged. General/language-
agnostic (word boundaries work for any language edge-tts supports). The clip-cache fingerprint already
keys on the page file + audio stats; ADD the `words.json` stat to the html-scene fingerprint so a
re-synth that changes timings busts the cached clip.

## Error handling
| Condition | Behavior |
|---|---|
| `say`/openai voice (no boundaries) | No words.json → `render_html` uses the paced-stagger path. |
| Anchor not found in words | `resolve_cues` even-spreads that point between neighbors; others sync. |
| edge `--write-subtitles` errors | tts logs + skips the words file; synthesis still succeeds → fallback. |
| Page has no `data-cue-index` | Untouched (hero/title or a page that opted out). |
| `cues` malformed in URL | seek.js ignores `cues`, falls back to authored delays. |

## Testing (deterministic; Chrome/edge gated where needed)
- **`cues.resolve_cues` (pure):** in-order anchors → ascending word times; an explicit cue phrase
  matched over the label; a missing anchor → even-spread between neighbors; collision → nudged apart;
  result always monotonic non-decreasing, length == len(anchors).
- **`tts._parse_subs` (pure):** an SRT fixture and a VTT fixture → correct `[{w,t}]` (start seconds).
- **opt-in Chrome:** a page with two `data-cue-index` points rendered at `?cues=0.2,2.0&dur=4&p=0.1`
  shows point 0 but not point 1; at `p=0.6` shows both — proving the cue override gates reveals.
- **render_html fallback:** a page with no words.json still renders via the anim_seconds path (existing
  tests stay green). The html-scene fingerprint includes words.json (cache-bust test).
- Full suite stays green.

## Out of scope
Splitting scenes into one-point sub-scenes; sentence-level NLP beyond even-spread; per-word (sub-point)
sync; re-sync without re-running tts; word timings from non-edge engines.
