# NeonTickerWall

**Identity:** a night-city signage wall — LED ticker strips scroll the film's headlines at different speeds and in alternating directions above and below a big neon-bordered marquee that pops in at centre with the main message, everything flickering like real signage.

**Use when:** a busy "all of this is happening at once" beat — 1–6 short headlines around one big message, with urban, electric energy. **Not when:** the headlines must be read carefully (they scroll and flicker), there are more than six, or the film is calm.

**Motion core:** the strips are on from the first frame and scroll for the whole clip, each at its own speed and direction, with a stepped flicker; the marquee scales up from 0.8 with an overshoot over 0.24–0.5 and keeps flickering after it lands.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `headline` | the white marquee text at centre | a fixed 128px with no fit: one or two words fill the sign; a longer line widens the marquee toward the frame edges and, once it wraps, grows it taller than the gap the strips were laid out around |
| `tickers` | one scrolling strip per entry, repeated end to end along its strip | 1 gives a single strip above the marquee; 6 gives three above and three below. The first half sit above, the rest below, spaced into the bands the marquee leaves; each strip takes the next colour of the DNA palette |
| `accent` | the marquee's border and glow | the sign's colour; unset it is hot pink on every film |

**Known traps:**
- The wall used to fill six fixed strips by cycling the tickers, so four headlines printed two of them twice and one headline covered all six; now it draws exactly one strip per ticker — don't pad `tickers` to fill the wall.
- A ticker is repeated end to end with nothing added between copies, so end each one with its own separator (the defaults end in ` · `) or the repeats run together.
- The strip layout assumes a one-line marquee; a headline that wraps covers the strips nearest it.
- Omitting `headline` / `tickers` prints demo copy: `NOW SHIPPING` and "BREAKING · IT WORKS", "LIVE NOW", "ALL SYSTEMS GO", "SOLD OUT · ENCORE".
- The lower strips used to run through the caption band; they are now pinned to the content zone's floor.
- The wall is a declared `@dark-world`: an LED panel and a neon tube are emitted light, so on a light film it keeps its own night instead of inverting onto paper. Taking the night was only half of it — the lamps are grown and exposed against the PANEL as well. Grown from the film's page they arrived as near-black type on a black strip: `ink_contrast_qa` measured 37.9% of the marks under 3:1, a median of 3.22:1 and a 0.38%-of-frame hole, and that hole was one whole ticker, a near-black blue printed on a black panel. Resolved over the eight shipped presets, seven come out byte-identical under this; `product`'s fourth tone lifts from about 2.7:1 to just over the floor, which it was under on a dark film too.
- The LED panel and the marquee box stay this register's own literals, and the marquee's tube stays the `accent` prop's hot pink unless a film passes one. That is what the declaration buys: the wall's night is the wall's, not the film's.

**Refuses:** `tickers` that is not an array or has fewer than 1 or more than 6 entries; an empty ticker.

**Reference:** `remotion/src/shots/NeonTickerWall.tsx`
