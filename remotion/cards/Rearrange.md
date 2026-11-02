# Rearrange

**Identity:** the same 2–12 items moved between arrangements, each a claim — a grid of peers, one hero that matters, full-width rows ranked by a sourced value, columns of what belongs together — every item travelling to its new place so the eye keeps it. An optional title opens centred and demotes itself to the beat's label as the items arrive.

**Use when:** the beat looks at ONE set again and changes its mind about it: "all of these… but this one… and in this order… and in these two camps". **Not when:** the order changes over time (RankRace), there is one quantity (FlowCounter), or a whole and its parts (MadeOf).

**Motion core:** items pop in (staggered, slight overshoot) into the first arrangement; each later step re-arranges them over ~0.13 of the beat on staggered, slightly bowed paths, the furthest-travelling item first (runtime/layoutMorph). A card and a row are two drawings of one item, chosen by the two arrangements it moves between; a rank row's bar grows inside it as the ranking arrives.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the beat's label, shown large first | a short phrase demotes cleanly; a sentence turns the open into a slide |
| `items` | `label`, optional `icon`, `value` (sourced), `display` (how the value is printed), `group` | 3–6 items read best; 10–12 make small cards and thin rows |
| `steps` | `[{layout, hero?, at?}]`, layouts `grid` `hero` `rank` `groups`; `at` a t or `{cue}` | two re-arrangements in a beat is calm; three is the most a beat of ~8 s can hold with rests between |
| `unit` | appended to a value with no `display` | `%`, ` TWh` — kept short |

**Known traps:**
- A box-shape test for "card or row" drew both when a settled box sat near the threshold (portrait groups printed each value twice); the choice is made from the arrangements, not the box.
- A rank row whose WIDTH carried the value left a 6% item no room for its own name; rows are full width and the bar lives inside.
- The hero takes the box's long side — the top in portrait, never a tall strip.

**Refuses:** fewer than 2 or more than 12 items; `rank` with an item that has no `value`; `groups` with an item that has no `group`; steps closer than ~0.12 of the beat; a count a layout cannot hold at a readable size.

**Reference:** `remotion/src/shots/Rearrange.tsx`, `remotion/src/runtime/layoutMorph.ts`
