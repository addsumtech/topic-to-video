# SwissEditorial

**Identity:** a strict editorial poster (hairline rules, a wordmark, an `INDEX / 0n` counter) in which one massive flush-left word snaps through a sequence with a clip-rise reveal, its last character in the accent, over an accent ticker band scrolling sideways.

**Use when:** a bold brand or editorial beat carried by a few short words in sequence (WORK. SHIP. DONE.), where the typography is the design. **Not when:** the words need explaining, carry numbers, or form a sentence. The word is one line that cannot wrap.

**Motion core:** the words split 0.08–0.92 evenly. Each word snaps in by rising through a clipped box over the first 40% of its slot (easeOutExpo), then holds until the next replaces it, and the index counter and progress ticks switch with it. The ticker scrolls left at a constant rate for the whole clip. Rules, wordmark and colophon stand still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | the words, shown one at a time for an equal share of the clip | 2–3 words give each a long hold; more words make it a rapid-fire snap. All words share one size, measured in the DNA's display face so the **longest** fits across the frame (capped at 340px), so one long word shrinks them all. The last character is always drawn in the accent, which assumes each word ends in a full stop |
| `ticker` | the text in the accent band, repeated and scrolling | a slogan run. `''` removes the band completely. Leaving the demo in place prints `WORKBUDDY —— ON YOUR MACHINE —— …` |
| `wordmark` | the mono label top-left | a brand or section name. Leaving the demo in place prints `WORKBUDDY™` |
| `colophon` | an accent corner mark under the index counter | empty by default, which draws nothing. Pass one only if it means something |

**Known traps:**
- Omitting `wordmark` or `ticker` prints a product's demo copy onto any film. The colophon used to print the literal `©2026 · LOCAL` everywhere; it now defaults to nothing.
- The word used to be a fixed 340px inside a clipped box, so anything past about nine characters was cut with no ellipsis ("ONBOARDING." rendered as "ONBOARD"). It is measured now, which means long words come out smaller, never cut.
- A word without trailing punctuation gets its final letter (or final Han character) coloured as if it were the full stop.
- The progress ticks sit at a fixed `bottom: 300`, which at 16:9 is inside the ticker band, so they are hidden whenever a ticker is drawn.
- The ticker once sat inside the caption band under the subtitle. It now sits above the band and is drawn only when non-empty. Apart from the word size, the layout is fixed pixels: 120px margins, 26px labels and a 360px-tall word box.

**Refuses:** `items` empty or not a list, or any empty word (it used to crash on the missing word instead).

**Reference:** `remotion/src/shots/SwissEditorial.tsx`
