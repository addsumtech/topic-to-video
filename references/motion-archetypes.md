# Motion archetypes — HTML-native video beyond the slide sequence

A slide deck answers "what's next?" with "the next slide." These archetypes answer a different
question: **what SPACE does this content live in, and how does time move through it?** Instead of
full-frame slides in sequence, the content becomes a *place you fly through*, a *system that runs*, an
*object that transforms*, or a *surface you travel* — and the **camera + clock narrate it**.

They're not a replacement for slides — they're a wider vocabulary. Reach for one when a beat's *shape*
(a process, a transformation, a set of related ideas, a vertical journey, a line that deserves weight)
has a better motion metaphor than "show a slide."

## The shared primitive (why they're safe)

Every archetype is a **timeline-driven HTML scene captured every frame** on the `seek.js` clock: each
element that changes over time carries **one** CSS animation spanning the whole scene, with the full
timeline in its keyframes; seek.js freezes them all at `t = p·dur` per frame. So the render is a pure
function of the frame index — **deterministic, seekable, cache-safe, A/V-gated**, exactly like any
scene. Under `--reduced-motion` these hold the **composed final state** (a static variant — no camera
move / morph), consistent with the image tier's reduced-motion. **One rule when authoring bespoke pages:
ALL css + `@keyframes` go in ONE `<style>` — a nested `<style>` silently voids the keyframes.**

Captions auto-suppress on these scenes (they carry their own on-screen text); force a band with
`slide.captions: true`.

## Which archetype for which content

| The beat is… | Reach for | Because |
|---|---|---|
| a short **line** that deserves weight (thesis, turn, payoff, opener) | **`kinetic`** | the voice *is* the motion — each word ignites as spoken |
| a **process / pipeline / mechanism / dataflow / architecture** | **`system`** | show it *running* — a token flows through stages that light up |
| a **transformation / before→after / "X becomes Y"** / a hero opener | **`morph`** | one thing *becoming* another beats a cut — pure continuity |
| an **overview** relating several ideas / "what makes this different" | **`conceptmap`** | ideas as a constellation the camera *travels*, then reveals whole |
| a vertical (9:16) **story / arc** as one continuous descent | **`scroll`** | the camera glides *down* one surface; sections ignite in frame |
| a single fact, image, chart, or dense body | a **slide** / `chart` / `html` | not everything wants a camera — a clean frame is often right |

Don't overuse them: a deck that's ALL camera-films is as monotonous as one that's all slides. Vary —
a motion archetype for the beats whose *shape* calls for it, slides/charts for the rest.

## The archetypes

### `system` — the pipeline runs
A row of `stations` a token flows through, each lighting as it arrives, then a caption lands.
```json
{ "type": "system", "narration": "…", "props": {
  "stations": [ {"k":"PLANNER","d":"writes the slide"}, {"k":"CRITIC","d":"judges it","kind":"critic"},
                {"k":"YOUR DECK","d":"ships"} ],
  "kicker": "THE PIPELINE, RUNNING", "caption": "Five agents. One job each." } }
```
`kind` in `critic`/`risk`/`judge` tints a station `--accent2`.

### `morph` — one object becomes another
A single shape transforms **dot → prompt bar → slide card → stacked deck**, no cuts. `props.labels` are
the three captions that ride the states.
```json
{ "type": "morph", "narration": "…", "props": {
  "labels": ["type one line…", "it drafts, designs, critiques — a real slide", "…the whole editable deck"] } }
```

### `conceptmap` — fly the constellation
A `hub` wired to `nodes`; the camera lands on each, then pulls back to the whole map. Positions
auto-place on an ellipse if omitted (pass `x`/`y` in node coords to art-direct).
```json
{ "type": "conceptmap", "narration": "…", "props": {
  "hub": "slide-maker",
  "nodes": [ {"label":"Reads your source"}, {"label":"A real editable .pptx"},
             {"label":"An independent critic","kind":"critic"}, {"label":"Any language"} ] } }
```

### `scroll` — the vertical journey (9:16)
The camera glides down one tall canvas; each `section` centers as it's reached. Best on a 9:16 deck.
```json
{ "type": "scroll", "narration": "…", "props": { "sections": [
  {"k":"ONE","t":"It reads your actual source."}, {"k":"TWO","t":"A team of agents."},
  {"k":"THREE","t":"An independent critic reviews it first.","kind":"critic"} ] } }
```

### `kinetic` — the line as living type
See `references/kinetic-typography.md`. The narration renders as type, each word igniting as spoken.

## Faithfulness still applies

Camera + motion make a claim *land harder* — so the R0 rule (every figure/name/quote traces to source;
no invented stats, even for punch) matters MORE here, not less. See the faithfulness gate.
