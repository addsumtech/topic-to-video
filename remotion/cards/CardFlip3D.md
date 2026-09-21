# CardFlip3D

**Identity:** a mono kicker fades in at the top; then up to four numbered cards rise into a row in perspective and flip 180° about their vertical axes one after another. A sheen flashes across each card at the half-turn, revealing a coloured back with a small label and the payoff word.

**Use when:** each of 1–4 items turns from one state into another, as in "question → answer" or "old way → new way", and the pairs are peers. **Not when:** there are more than four pairs, or the back isn't a transformation of the front (use a list or grid register).

**Motion core:** the kicker fades 0.04–0.20; card i rises 0.06 + i·0.06 → 0.24 + i·0.06; card i flips 0.18 + i·0.16 → +0.34 with an ease in-out, and a sheen peaks at its half-turn. With four cards, the last flip ends on the clip's final frame.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one card each: `front` and `back`, both required | cards narrow as the count rises, and one shared face size is the smallest two-line fit across every front and back (capped at 64px). A single long string shrinks every card's type, so peers stay equal |
| `title` | the spaced mono kicker above the row | fixed 32px, uppercased, with wide tracking, not fitted |
| `backLabel` | the small label above every back's word | the same on every card; says what the back IS (e.g. `NOW`, `实际`) |

**Known traps:**
- `backLabel` defaults to the Chinese `实际`, which prints on English films unless it's passed.
- Omitting `items` or `title` prints the demo `Manual→Automated`, `Hours→Seconds`, `Guesswork→Grounded` and `What changes`.
- A fixed 64px broke a Chinese label mid-word (`失/败`), and fitting each string on its own made peer cards read as primary and subordinate. There is now one width-aware size for all of them.
- The back used to show a bare `↓` pointing at nothing; `backLabel` replaced it. The card fills used to be hardcoded; faces and tones now come from the DNA — though the FRONT face's DNA fill was computed and never passed to the face that draws it, so it stayed a literal near-black on every film, which on a light one is `dna.fg` (near-black) printed on a near-black card. It is wired.
- The kicker over the row was a literal `#aeb6ca` — the beat's own title, white-on-warm-paper and the whole of `ink_contrast_qa`'s 0.29%-of-frame hole (14.7% of the marks under 3:1). It is the film's ink at its metadata tier now. The cards' `0 40px 90px #0008` shadow went with it: authored against a void, where it is the only thing separating a card from the frame, it pooled three grey washes across the lower half of a page. On a light film it is the paper's own shade, closer in and half as far.

**Refuses:** no `items`, or more than four (a fifth card would still be mid-turn at the last frame, its back never shown — split the pairs across two beats); a card missing `front` or `back`.

**Reference:** `remotion/src/shots/CardFlip3D.tsx`
