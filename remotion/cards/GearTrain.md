# GearTrain

**Identity:** a row of interlocking gears engages one after another, each turning opposite to its neighbour with its step label upright on the hub; the last gear locks and a payoff badge pops above it.

**Use when:** a mechanism — "one turn drives the next" — two to four steps where the last delivers the payoff. **Not when:** there are more than four steps, or the steps are a list rather than a causal chain (InOrder).

**Motion core:** the title rises (0.03–0.16); gear i engages from 0.12 + 0.12·i and every gear turns until 0.86 (later gears spin faster to arrive together); hub labels fade in on the same stagger; at 0.82 the last label brightens and the payoff badge pops (0.82–0.98).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one gear per step, left to right | 2–4. Gears are a fixed size; when the train is wider than the frame it scales down as a whole to fit. Hub labels are a fixed 40px in a hub-wide column and wrap |
| `label` | the payoff badge above the last gear | one line (never wraps), not fitted; '' draws no badge |
| `title` | the spaced caps above | fixed 30px, not fitted |

**Known traps:**
- `items` used to be cut to four, so a five-step mechanism lost its last step and the payoff was credited to the wrong gear. Past four now throws.
- The badge never wraps; a long payoff runs wide from the last gear's centre.
- The badge's green gradient and its dark ink are fixed — that pair carries its own fill and reads on either ground, so it is left alone. Everything else follows the film: the teeth take the DNA's palette, and the gear BODY is now a measured step off the film's ground with its step name picked against that body, so a light-key film gets machined plates with dark labels instead of three private black discs.
- Defaults print 'Trigger / Process / Deliver', 'Automatic', 'How it runs'.

**Refuses:** `items` that is not an array, or has fewer than 2 or more than 4 entries.

**Reference:** `remotion/src/shots/GearTrain.tsx`
