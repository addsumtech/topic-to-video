# ElasticType

**Identity:** a word's letters drop in one by one in a spread of colours, squash and stretch like jelly on impact, then keep a soft gummy wobble; a tracked tagline follows.

**Use when:** a playful, springy title — one short word that should feel alive. **Not when:** the word is longer than 16 characters (it refuses) or the tone is serious; for a soft-dimensional title use InflateType.

**Motion core:** character i starts dropping at 0.06 + step·i and lands 0.18 later, jiggles with a decaying squash-stretch, then wobbles gently for the rest of the clip; the tagline rises 0.66–0.86. The step is 0.08 for words up to eight characters and closes for longer ones, so the last character has always landed by 0.84 (just before the settled frame at 0.86).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the letters that drop, one element per character, 1–16 characters (spaces count) | fitted to the frame's width with room for the squash (at most 230px); a longer word is smaller — 16 Han glyphs set at about 40px on a 1080-wide portrait frame. Characters cycle through five palette tones derived from the DNA; a space is a fixed gap |
| `tagline` | the tracked uppercase mono line underneath | fixed 32px, not fitted |

**Known traps:**
- The drop stagger was once fixed per character, so only the first ten characters ever landed and a thirteenth never appeared. It is laid out for the word's length now; the last character still jiggles a little on the settled frame (it landed at 0.84), which is the register's motion, not a missing letter.
- The letter colours cycle by position and mean nothing; do not rely on them to group letters.
- The word was once a fixed 230px, which cut an eight-glyph Chinese phrase off both sides at 1:1; it is width-fitted now, but the tagline is not.
- Defaults print 'BOUNCE' / 'springy, gummy, alive'.

**Refuses:** a `word` with no visible character, or longer than 16 characters (spaces included).

**Reference:** `remotion/src/shots/ElasticType.tsx`
