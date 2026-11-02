# ColdOpen

**Identity:** the film opens on ITSELF — 2–4 of its own later beats flash past in 9-frame hard cuts, each leaning in a little, then a beat of dark and the title card. A trailer's bumper, made of the film's own pictures.

**Use when:** a launch or promo film (meta.purpose) wants to promise what is coming before it says what it is; `shot_director.bookends` proposes it for such a film of 6+ beats, flashing its three most energetic later beats. **Not when:** an explainer (open on the first idea), the opening line must be read at once, or the film has too few distinct pictures to flash.

**Motion core:** after the seam's held edge, each named beat is shown full frame for 9 frames (drawn by its own register on its own ground, frozen once it has landed — runtime/teaser), pushing 1.00 → 1.07; then 12 frames of the film's ground darkened; then the kicker, title and a short rule rise in. No white frames between cuts: three flashes inside a second is the photosensitivity pattern (ITU-R BT.1702).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `beats` | 2–4 of the film's beat numbers (1-based), all LATER than this one | three is the trailer rhythm; two reads as a pause, four starts to feel like a montage |
| `title` | the card the flashes lead to | the film's name or its claim, short |
| `kicker` | the small caps line above the title | a category word; leave it out rather than fill it |

**Known traps:**
- Teasers are frozen at t = 0.95: at the 0.88 the visual gates use, a register whose last step lands late (Rearrange) was caught mid-move.
- A beat built of other beats (ColdOpen, Callback) is refused as a teaser — it would loop.

**Refuses:** fewer than 2 or more than 4 beats; a beat that is this one, earlier than this one, or itself a ColdOpen/Callback (validate.teaser_problems); an empty title.

**Reference:** `remotion/src/shots/ColdOpen.tsx`, `remotion/src/runtime/teaser.tsx`
