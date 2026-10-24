# HeadlineReveal

**Identity:** the beat's headline arrives the way a launch site's hero does — each line rises a whole clip-height through its own mask (or each word does, or each letter blurs into focus), on the word the narration says it — and the run the film marked `*…*` then takes the accent and thickens, letter after letter, once its own line has landed. A spaced mono kicker blurs in above with a short rule; a supporting sentence follows word by word.

**Use when:** the headline IS the beat — one claim said in one breath, where the sentence's own rhythm is the design and one phrase in it carries the claim. **Not when:** the content is a list of peers (a list register), one enormous word (`CroppedType`, `VariableTypeMorph`), or a sentence with a slot that changes (`WordRoll`).

**Motion core:** `reveal: 'line'` (default) — a mask reveal, `ymask` 1.02 (GSAP SplitText's `yPercent: 100` on a clip) with linear.app's slight blur, 0.95 s on expo.out, 0.16 s between lines; `'word'` — the same per word, 0.07 s apart; `'char'` — Framer's per-character blur-in, 0.035 s apart (0.08 s for Chinese: a reveal faster than reading rate reads as a wipe). Every line is cued (`lines.N` moves EARLIER onto its word). The emphasis lands 0.18 s after its line: colour sweeps letter by letter and the weight goes 620 → 760, a reflow the primitive measures at five anchors so the rest of the line makes room smoothly. Sweeps that would overrun the beat are compressed so everything has landed by 0.72.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `lines` | the headline, one entry per line the film wants; `*…*` marks the emphasised run | 1–5 entries. Each entry stays whole down to a display floor (measured fit, not a guess); only past it may an entry wrap — at word boundaries, Chinese included |
| `kicker` | a small spaced label over the headline, mono | read as the headline's context, never a second claim; not held to a reading time |
| `note` | one supporting sentence under it | held to its reading time like the headline; balanced over up to three lines |
| `reveal` | what rises: `line`, `word` or `char` | line is the calmest and most premium; char is the most energetic and needs the most time |
| `align` | `left` (editorial, with the kicker's rule) or `center` | centred drops the rule |
| `hold` | what the landed type does while it holds: `alive` (default) — a breath of tracking and, every few seconds, a light passing along the line; `still` — nothing | alive keeps a held line from reading as a slide's hold; still is for a beat that must be utterly quiet |

**Known traps:**
- The emphasis was first an underline. At display size it ran straight through the descenders ("by", "pay") and read as a strike in the wrong place, so emphasis is colour and weight, which also cannot collide with the next line.
- Fitted only to its box, the largest size wins by wrapping: 「一行一行升起」 came out 「一行一 / 行升起」. The first fit tier keeps every entry whole; a Chinese entry that must wrap breaks at an Intl.Segmenter word, never between any two characters.
- The accent is kept only where it reads (3:1, large type): `readableOn(bg, accent, fg)` returns the most legible candidate, which on a dark ground is always the foreground — the first render drew the emphasised run white on white text.
- QUIET by construction: measured 0.0009 motion, 6.8% ink, 0.042 light (product DNA) against 0.0037 / 12% / 0.135 floors — a headline lands and holds. Intercut with a dense register.
- PACED IN SECONDS (`PACE = 'seconds'`): the reveals are durations and the beat's shares only bound when they start; validate no longer calls a 3 s beat "2x faster" — the hold gate measures what a short beat really costs (reading time).
- In a tall frame an entry is kept whole only down to U·0.11, then given ONE extra line at U·0.12, then any wrap: kept whole to the landscape floor, a nine-glyph end line came out ~100 px in a 1920-tall frame (bench-launch b8, 4.9% ink); with the tiers 「一个题目，/一条成片」 sets at display size and is never cut 一个/题目.
- HELD TYPE STAYS ALIVE (`hold: 'alive'`, the default): once a line lands, a breath of tracking (≤0.006 em) and a light passing along it every ~3.4 s (`runtime/kinetic` `idle`), with the baseline unlock on for the whole shot so it never steps a pixel; `hold: 'still'` is a slide's hold.
- The headline is the `word` carry anchor (`runtime/kineticWord`) — a glyph window when it is one line, so `through-window` looks through its letters.

**Refuses:** no headline (or only whitespace); more than `MAX_LINES` (5) entries — past that it is a paragraph, and a paragraph revealed line by line reads as a teleprompter; copy that cannot fit its room even at the display floor (the primitive names the measured size).

**Reference:** `remotion/src/shots/HeadlineReveal.tsx`

**Measured:** 6.8% ink (clip median) · 27.3% footprint · 0.0009 motion · reach 0.829. Holds (its own gate, `scripts/shot_proof.py`): clean at its own 5.5 s; at a 4 s beat the two-line block and the note fall under the must-read bar (warnings).

**Review:** NOT critic-reviewed — built and looked at by its author (contact sheets at 16:9 / 9:16 / 1:1, Latin and Chinese, product / editorial / terminal DNA).

**Provenance:** motion-graphics. **Family:** C.
