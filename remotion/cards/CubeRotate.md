# CubeRotate

**Identity:** a slightly tilted 3D cube turns a quarter at a time to present each side face — a colour chip over a statement — with the held face's edge lit in its tone.

**Use when:** one subject has several sides, or a loop of up to four stages that returns to its start. **Not when:** there are more than four faces (it refuses them), or the steps are a chain that does not close (GearTrain, InOrder).

**Motion core:** the clip is split into one equal slot per face; in each slot the cube turns 90° over the first 45% and holds the face for the rest, its border and glow taking its tone once it has mostly arrived. The title rises 0.03–0.16.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `faces` | one statement per face, up to four | a face written "A - B" (hyphen, en or em dash) puts A in the chip and B as the statement; without a dash the chip shows the face's number. Every face's statement shares one size — the smallest that fits two lines — so peers read as peers. A face that repeats an earlier face's statement takes that face's tone, so a closing loop reads as a return |
| `title` | the spaced heading above the cube | fitted to one line within 72% of the width; uppercase unless the DNA says otherwise |

**Known traps:**
- The chip used to blend toward a hardcoded blue, so a green/amber film shipped teal-to-blue chips. Each chip is now a tint-to-shade of its own DNA tone, with its ink flipped on luminance.
- The type was tuned on four-letter English words and a fixed 52px ran real Chinese clauses to the face edge; it is width-fitted now.
- On a narrow frame the cube is capped by WIDTH, because mid-turn the assembly is wider than one face.

**Refuses:** no `faces`, or more than four (a cube has four sides and each is presented once — use GearTrain or InOrder for a longer loop); an empty face.

**Reference:** `remotion/src/shots/CubeRotate.tsx`
