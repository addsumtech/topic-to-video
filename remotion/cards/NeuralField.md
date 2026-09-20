# NeuralField

**Identity:** a four-column neural network (5 · 8 · 8 · 3 nodes) is wired up and an activation front sweeps it left to right, swelling the nodes and pulsing along the strongest connections until the output head locks bright; optionally a dashed, unlit second output slot hangs below it with no edges reaching it at all — the channel the network was never wired for.

**Use when:** an AI or model beat — input → model → output — and above all the claim "the model cannot know this", which `absentOutput` draws as an absence. **Not when:** the beat is about numbers, benchmarks or a specific architecture (the layer sizes are fixed and the strong edges are hash-picked, so it encodes no real model), or the relation is not input-to-output.

**Motion core:** the title fades in over 0.03–0.16; the input label and (with an absent channel) both output slots appear over 0.1–0.3, before any signal arrives; the activation front travels across the layers over 0.14–0.86, each connection pulsing as it passes and the traversed strong ones keeping a low resting glow; the live output label fades in over 0.68–0.84 and the ghost label over 0.72–0.86, so the frame is settled by 0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | a small tracked mono line at the top | fitted to one line and capped small — it is a header, not a headline; long text shrinks |
| `input` | the label under the input column | fitted to two lines in a box that stops short of the next column and the frame edge, so long copy (e.g. Chinese) shrinks rather than colliding |
| `output` | the live head's label | without `absentOutput` it hangs under the output column with a glow; with it, it moves to a right-hand label column at the live slot's height |
| `absentOutput` | the label of a channel the network was never wired for | set, the network gives up width for a label column, rises in the zone, and a dashed, unlit, edge-less slot appears below the live one; both head labels share one size; empty or whitespace draws nothing extra |
| `tone` | which DNA accent the live path wears (`'accent'` or `'accent2'`) | default is `accent2` when an absent channel is declared (the film's primary accent is then the ghost) and `accent` otherwise; flipping it swaps which hue computes and which is missing |

**Known traps:**
- Omitting the text props prints demo copy: "It reasons", "your prompt", "the answer".
- `tone` only acts under a DNA: with no DNA the path and head keep the register's fallback cyan and green whatever `tone` says.
- It used to paint itself cyan and spring-green on every film, handing a green film's SUCCESS colour to a merely plausible head; colour now comes from the DNA, so pick `tone` deliberately when success/failure hues matter.
- The old fixed 110px row pitch pushed the tallest column's bottom node into the caption band, and portrait rendered a tall tangle; the graph is now proportioned to the zone — don't expect it to fill a portrait frame.

**Reference:** `remotion/src/shots/NeuralField.tsx`
