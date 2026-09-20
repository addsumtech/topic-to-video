# SpatialSlides

**Identity:** up to five cards hang at different positions and angles in a 3D space; the camera flies from one to the next, swinging round until each card is square to the lens, then pulls back so the whole route is seen at once — each card's word lying flat on its own tilted surface.

**Use when:** the argument is a JOURNEY through places — stages you travel between, where the space between them matters — rather than a list. **Not when:** the items are parallel with no route (a list or grid register), or several features on one screen (use `PointerTour`).

**Motion core:** the tour runs 0–0.78: the camera holds on a card, then swings (eased) to the next, the legs spread evenly across the tour, the current card's border lit in the accent. From 0.78 to 0.94 it pulls back to a fitted overview of every card; the overview line fades in 0.82–0.96. With one step it simply holds, then pulls back.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `steps` | the places, one card each, in route order | 1–5; the route is as long as the list (more steps = shorter legs, a busier tour). All labels share one size fitted to the card width, so one long word shrinks every card's label. Past five, the rest are dropped. Omitted, the demo `Collect / Plan / Act / Verify / Deliver` prints |
| `notes` | a small dim line under each step's label, matched by position | empty for a step draws nothing; the note rides the card's plane with its label |
| `overview` | a spaced mono line above the content zone, shown during the pull-back | empty draws nothing; one short line names the whole route |

**Known traps:**
- Type pushed onto the 3D plane measured 38% softer (rasterised once and upscaled), so the words are 2D elements laid onto each card's projected plane. Don't put text inside the `Surface`.
- Labels used to stay level while their card tilted; they now take the card's plane. The card's rules used to cross the centred label; furniture stays above and below the word.
- A label is hidden whenever its card leaves the frame or its type would enter the caption band — a card mid-flight can show no word.
- More than five steps are dropped without an error; the five poses are hand-set, and a sixth stop would be invented.

**Refuses:** no non-empty `steps` entry.

**Reference:** `remotion/src/shots/SpatialSlides.tsx`
