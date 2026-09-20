# LiquidMorph

**Identity:** one iridescent blob breathes and wobbles at centre while the film's forms fade through it one after another — each form's icon glowing on the blob, its word underneath.

**Use when:** the claim is "one thing, many shapes" — a single material, tool or idea taking 2–6 successive roles or stages. **Not when:** the stages must be seen side by side or compared (use a list or flow register), or there is only one form.

**Motion core:** the blob outline wobbles on every frame for the whole clip; the forms cross-fade evenly across 0.06–0.96, each icon peaking at its own slot and the words cross-fading a little more sharply than the icons. There is no build-up and no settle — the morph is the whole motion.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `forms` | the sequence: each a label string or `{label, icon?}` with a runtime/icons name | 2 forms give long, slow cross-fades; 6 put each form on screen for under a second (the header's reason for the cap). A form with an `icon` draws that white glyph on the blob; without one the blob and the word carry it alone. Every label is set at ONE size (at most 64px) — the longest label, fitted on a single line to the frame's width, sets it for all, so one long word shrinks every word |

**Known traps:**
- It used to take no props and printed "Ask. Draft. Analyse. Done." on every film (a product workflow whatever the topic); that sequence is still the default, so omitting `forms` prints it.
- The old "analyse" glyph was a three-bar chart with invented bar heights; icons must be picked for the role the form plays, never by position (the icon rule in references/remotion-shot-authoring.md).
- The blob's radius shrinks on short frames: at a flat 300px the label landed ~70px inside the caption band at 1:1, so on square/short frames the blob is smaller by design.
- The form's word hangs BELOW the blob, on the film's own ground, so it is set in the film's ink. The icon riding the blob stays white, because the blob is a saturated iridescent fill on any ground. The blob's three gradient stops are fixed.

**Refuses:** `forms` that is not an array or has fewer than 2 or more than 6 entries; a form with an empty label.

**Reference:** `remotion/src/shots/LiquidMorph.tsx`
