# Callback

**Identity:** the finale gathers what the film showed — 3–6 of its own earlier beats come back as cards and settle round the closing line, the way a launch event ends with everyone on stage. A recap you see, not one you are told.

**Use when:** the last beat closes a film of 6+ beats whose pictures are worth seeing again together; `shot_director.bookends` proposes it, gathering four beats that look different (one per family first). **Not when:** the close is one image or one sentence alone, the earlier beats are too alike to tell apart at card size, or the film is short.

**Motion core:** each card is a beat drawn by its own register on its own ground, frozen once landed (runtime/teaser), scaled to 22% of the frame (30% in portrait); the cards fly in from beyond the frame on staggered, bowed paths (runtime/layoutMorph) to an ellipse framing the centre, tilting from loose to a small settle; the closing line and its note rise in the space the ring leaves.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `beats` | 3–6 of the film's beat numbers (1-based), all EARLIER than this one | four reads as a gathering; six is busy, three is a triptych |
| `title` | the closing line | one sentence, the film's last claim |
| `note` | a quieter line under it | the call to action or the source, short |

**Known traps:**
- A beat built of other beats is refused as a card (it would loop).
- Cards render every named register each frame — six heavy registers make the beat slow to render, never wrong.

**Refuses:** fewer than 3 or more than 6 beats; a beat that is this one, later than this one, or a ColdOpen/Callback (validate.teaser_problems); an empty title.

**Reference:** `remotion/src/shots/Callback.tsx`, `remotion/src/runtime/teaser.tsx`
