# Kinetic typography — the narration as living type

The first **beyond-slides** archetype. Instead of a slide with staged reveals, the frame *is* the
narration: every word ignites at the moment it's spoken. It's a **timeline-driven** scene captured
every frame (continuous motion), riding the same `seek.js` clock + edge-tts per-word times the deck
already produces — so it stays deterministic, seekable, cache-safe, and A/V-gated like any scene.

Use it for a **short, punchy line** that deserves weight: a thesis, a turn, a payoff, a section
opener. NOT for a dense paragraph (kinetic type is a hero moment, not a body-copy tier).

## Author it

A storyboard scene:
```json
{ "index": 7, "type": "kinetic",
  "narration": "The mind that builds it is never the mind that grades it.",
  "props": { "emphasis": ["never"] },
  "duration": 5.2, "audio": "audio/07.mp3" }
```
- `type: "kinetic"`. The on-screen words come from the **narration** (or `props.text` to override the
  displayed line while the voice says something longer).
- `props.emphasis` (optional): words to mark `.key` — bigger, italic, held in `--accent` (the line's
  hero beat). Use ONE or two, not every word.
- Word onsets come from `audio/NN.words.json` (edge-tts) for **exact voice-sync**; with a non-edge
  voice, onsets are estimated from each word's position in the line (still speech-paced).
- Captions are **auto-suppressed** on a kinetic scene (the words already ARE the text). Force them
  with `slide.captions: true` if you truly want a redundant band.

## The motion language (huashu-informed — bake these in, don't reinvent)

- **Chunk reveal, never per-character.** A word is the unit; a letter-by-letter blink reads as
  old-movie-subtitle slop. (One `.kw` span per word — the renderer does this.)
- **Physical weight, not opacity-only.** A word lands by lifting + de-blurring + settling in scale on
  **expoOut** (`cubic-bezier(.16,1,.3,1)`), so it arrives with mass. Never a flat opacity fade.
- **The live word flares.** The word being spoken holds `--accent`, then settles to `--fg` as the next
  takes over — the accent travels the line like the composition is speaking. (Built into `.kw`.)
- **expoOut everywhere; overshoot for emphasis.** No `linear`/`ease`. `.key` words land on overshoot.
- **Warm/cool-neutral ground.** Inherits the deck `--bg` — never pure `#000`/`#fff`.
- **One focal line per scene.** Cover the words — the motion alone should still feel like *this* beat,
  not a generic text animation. Keep the line short so it fills a hero box, not the whole frame.

## Faithfulness still applies

The words are spoken claims — every figure/name traces to source (R0), same as any tier. Kinetic
motion makes a line *land harder*, which is exactly why an unsourced number here is more dangerous, not
less. No invented stat, even for punch (see the faithfulness gate + `references/html-pages.md`).

## Under the hood (why it's safe)

`scenes.render_kinetic` generates a self-contained HTML page (one cued `.kw` span per word) linking
`assets/html/kinetic.css` + `seek.js`, then captures **every frame** at `?p=` with the word onsets in
`?cues=`. seek.js freezes each word's entrance at the exact clock time — so the render is a pure
function of the frame index (cache-safe, `--reduced-motion` degrades to opacity cross-fades). It reuses
the true-W×H capture + the clip cache + `check_av` gate; nothing new to trust.
