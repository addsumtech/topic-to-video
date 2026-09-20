# DataOrrery

**Identity:** a glowing core sits inside tilted elliptical orbits, one per item; a labelled node rides each orbit, passing in front of the core and behind it, receding while it is behind.

**Use when:** a hub and the few things that revolve around it — "your work in motion", an ecosystem around one centre. **Not when:** the relations between the items matter (KnowledgeGraph draws edges), or there are more than four.

**Motion core:** never still. The core pops in (0.02–0.20); the orbits draw in staggered (from 0.10, 0.08 apart); nodes, then labels, follow on the same stagger; the hub name fades up 0.18–0.34. Every node orbits for the whole clip — the inner orbit fastest, alternate orbits turning opposite ways. A node behind the core is dimmer, softer and smaller (the shared focus lens), never hidden.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one orbit and one labelled node per entry, inner to outer | 1–4; fewer items mean fewer rings, never repeated labels. Labels are single-line chips, not fitted |
| `hub` | the name under the core | fixed 40px, not fitted |

**Known traps:**
- `hub` defaults to 'WorkBuddy' — omit it and a product name prints under the core of any film.
- The orbits used to be filled by `labels[i % n]`, so two items each appeared twice and a fifth was dropped without a word; now there is one orbit per item and a fifth throws.
- Labels used to vanish whenever their node crossed behind the core, so at the settled frame one of four was drawn; they recede now instead.
- Only the ground reads the DNA; the ring colours, the core and the label chips are fixed blue, teal, violet and pink.
- The orbit scale budgets roughly a 90px chip at the outer ring and labels never wrap, so a long label can reach past a narrow frame's edge.

**Refuses:** no non-empty items; more than four items.

**Reference:** `remotion/src/shots/DataOrrery.tsx`
