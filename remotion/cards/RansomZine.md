# RansomZine

**Identity:** a word spelled as a ransom note — each character a torn paper scrap in its own colour and typeface drops in askew, some held by tape strips, over photocopy grain — then a marker scrawl underlines it and a spaced tagline appears.

**Use when:** a loud, DIY, anti-slick statement — a short slogan, a rallying word, a punk or zine mood (family L, editorial). **Not when:** the copy is longer than 16 characters (it refuses), must be read quickly, or the tone is sober.

**Motion core:** letters drop one after another from above, settling with an overshoot into a tilt, from 0.06, each drop taking 0.28. The stagger is 0.07 per character for up to eight characters and closes for longer words, so the last scrap has settled by 0.84 (just before the settled frame at 0.86). The marker underline draws left to right 0.60–0.86; the tagline fades in 0.66–0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the text spelled in scraps, one scrap per character (spaces become narrow gaps), 1–16 characters | shown exactly as typed (case kept). A short word gets big scraps; a longer one shrinks every scrap (with its tape and the marker's distance) so the row fits the frame width — 15 Han glyphs are about 62px scraps on a 1080-wide frame. Paper colour, ink, typeface and tilt per scrap are fixed by position, so the same word always looks the same. Omitted, the demo `STAY WEIRD` prints |
| `tagline` | the spaced uppercase mono line near the bottom | fixed size, not fitted: a few words read as a zine footer; omitted, the demo `cut · paste · repeat` prints |

**Known traps:**
- The drop stagger was once a fixed 0.07 per character, so only about ten characters had landed by the end of the clip and from the fifteenth on they never appeared (the demo's own tenth scrap was still overshooting on the settled frame). It is laid out for the word's length now.
- The scraps' seven paper colours and five typefaces are the register's identity and do not follow the DNA; only the ground, the marker (accent) and the tagline (fg) do.

**Refuses:** a `word` with no visible character, or longer than 16 characters (spaces included).

**Reference:** `remotion/src/shots/RansomZine.tsx`
