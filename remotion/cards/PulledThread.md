# PulledThread

**Identity:** a cloth of threads, each named at its left end. One is pulled, and the ones the film says it drags follow it into the same dip; the rest lie flat. The cross-threads bend with them, because they pass through the same cloth.

**Use when:** the beat is that changing one thing REQUIRES moving others — not later, not downstream, but at the same instant, because they pass through each other. "You cannot touch this without touching those" is the sentence every dependency conversation is actually about. **Not when:** the relation is a CHAIN, one turning the next in order (`GearTrain`); not when it is a HIERARCHY, a thing on top and the broader reasons under it (`RestsOn`). Both of those are directed and both are about structure holding still.

**Why a weave and not a graph:** a dependency graph draws the coupling as an EDGE — a line you add between two things that are otherwise separate, which quietly says they could be separated by deleting the line. In cloth the coupling is not drawn at all: it is the material. Nothing is added to connect the threads and nothing can be removed to disconnect them, so the picture cannot be misread as "we could decouple this" — there is no coupling object to delete.

**Motion core:** the cloth draws in 0.02–0.26, the hand closes on the thread 0.10–0.22, and the pull begins at 0.26 on a SEATED spring (`springAt` + `SPRING_SEAT`) — cloth takes up and holds, it does not oscillate, and a bouncing weave would read as elastic rather than as woven. Each follower is released 0.035–0.055 of the clip after the pulled thread, which is the whole of how consequence is expressed here: in time, never in amplitude. The note fades 0.84–0.94.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `threads` | the threads in the order the film lays them out — 3 to `MAX_THREADS` (7), `{label, moves}` | `moves` is the FILM's claim about what the pull drags. It is never inferred from where a thread sits |
| `pulled` | the index of the thread that was pulled | **REQUIRED once a film supplies its own `threads`.** Which one moved first is the cause the beat is about; the demo keeps its own index so the preview still renders |
| `kicker` | the spaced label over the cloth | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the cloth, in the film's voice | where to say what the coupling MEANS |

**Known traps:**
- **What follows, follows in TIME — never in amplitude.** A dragged thread could be drawn displaced by less the further it sits from the pull: it looks physical, and it is the register inventing DEGREES of coupling the film never gave. They move by the same amount, staggered slightly in time, so the frame says "these came with it" and declines to say how much.
- **Adjacency is not coupling.** A register that decided "the neighbours move" would be asserting the very thing the beat exists to state. Only `moves` decides.
- **At least one OTHER thread must move, and that is a refusal.** With everything else flat the frame says the thread came away clean — the opposite beat, drawn convincingly, passing every gate.
- The cross-threads BEND with the threads they pass through. Drawn straight they read as a grid the named lines happen to lie over, and the register's whole premise is that the coupling is not laid on top but is the material. A warp that dips where the weft was dragged is the same fact seen from ninety degrees, and it is what makes the picture cloth instead of a chart.
- Labels live in their own column, never on the cloth. A label that travels with the thread it names is unreadable exactly when that thread is doing the thing the register is about.
- The pull eases to nothing at both selvedges. A thread pinned at its ends is what makes a pull a CURVE rather than a translation — untethered, the whole row would simply slide down and the cloth would read as a list scrolling.

**Refuses:** fewer than 3 `threads`; more than `MAX_THREADS`; a thread with no `label`; a missing `pulled` once the film supplies its own threads; a `pulled` outside the list; and no other thread marked `moves`.

**Reference:** `remotion/src/shots/PulledThread.tsx`
