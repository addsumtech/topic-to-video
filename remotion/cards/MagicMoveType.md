# MagicMoveType

**Identity:** one phrase BECOMES the next. The letters two phrases share travel from where the first set them to where the second does — a word both share travels as one body — while the letters only the first has lift away and the ones only the second has rise in. The first phrase can rise in as a line, stand as a stack of its words that becomes the line, or assemble out of its own letters scattered across the frame.

**Use when:** two statements are made of the same material and that IS the claim — "what stays, moves" → "what moves, stays", 少，但更好 → 更好，但更少, a word kept across a rewrite, an anagram, a slogan that is its predecessor re-ordered. With the caption hidden a viewer still sees which words survived and where they went. **Not when:** the phrases share nothing (it refuses: every glyph would only leave and arrive — use `HeadlineReveal`), or one slot in a fixed sentence changes (`WordRoll`).

**Motion core:** (`runtime/kineticMove`) the longest common subsequence pairs the glyphs first, then the rest by identity, nearest first; spaces never travel. A move is 1.15 s at its natural pace (shrunk on a short beat to 20% of the span, never under 0.6 s): leaving letters lift 0.32 em and fade, the travellers cross on arcs word by word in landing order (a word moving right passes over the line, one moving left under it, at most 0.55 em off — so two words that swap never cross), arrivals rise in last. Each glyph is drawn where `runtime/kinetic`'s reference node set it, at the destination's size scaled from the source's. The kicker and note are set 0.55 em clear of the line so nothing travels through them.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `phrases` | 2–4 phrases in order; each becomes the next. `*…*` marks a run in the accent | every pair must share at least one letter. All are set at ONE size (fitted on the widest), so a kept word does not change size as it travels |
| `first` | `line` (rises in), `stack` (one word per line, which becomes the line), `scatter` (its letters fly in from seeded places) | stack argues "these words become one statement"; scatter "out of the parts, the whole" |
| `kicker` | a small spaced mono label over the type | not held to a reading time |
| `note` | one supporting sentence under it | held to its reading time |
| `align` | `center` (default) or `left` | |

**Schedule — in seconds:** each phrase holds in proportion to its must-read time (`runtime/readingSpec.json`), after an entrance of 0.45–0.9 s (scatter 0.7–1.4 s); `phrases.N` may bring a move EARLIER onto its word, never before the phrase it replaces has been held its read-once time. `PACE = 'seconds'`: validate does not call a short beat "N x faster"; `shot_proof` measures each phrase's readable stretch through the component's own state function.

**Sizes:** in a tall frame the fit prefers two big lines (floor U·0.19) to one small one — 少，但更好 sets 「少，/但更好」 at display size instead of one ~150 px line in an empty 1920-tall frame.

**Known traps:**
- Staggered glyph by glyph, a word moving left spread into "m o v e s" mid-flight (its first letter left first and pulled ahead). The stagger is per WORD.
- A glyph crossing a whole line on an uncapped arc rose ~120 px into the kicker. The bow is capped at 0.55 em and the room is kept.

**Refuses:** fewer than 2 or more than 4 phrases; an empty phrase; two consecutive phrases with no letter in common.

**Reference:** `remotion/src/shots/MagicMoveType.tsx` · runtime: `runtime/kineticMove.tsx`, `runtime/kineticMoveCore.ts`

**Measured:** see LIBRARY.md (register_energy row).

**Review:** NOT critic-reviewed — built and looked at by its author (line / stack / scatter; 16:9, 9:16, 1:1; Latin and Chinese).

**Provenance:** motion-graphics. **Family:** C.
