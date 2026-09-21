# IsometricAssembly

**Identity:** an isometric factory diorama. Grey blocks ride a conveyor into a dark machine, vanish inside while its intake slot glows, and come out taller and coloured onto a green delivery pad, where they stay, lined up against the end. Three labels name the intake, the machine (beside its top) and the pad.

**Use when:** a pipeline told as objects: raw input → one processor → finished output. **Not when:** there are more or fewer than three stations (the labels are a fixed triple), many items go through a stamp press (ConveyorBelt), or the beat is a multi-stage technical pipeline (MRIPipeline).

**Motion core:** part `i` sets off at 0.06 + 0.14·i and rides at the belt speed (the whole belt in 0.8 of the clip) until it reaches its own slot on the pad: the first against the far end, the others queued behind it. It is hidden inside the machine and comes out coloured and taller. The intake glows in the accent while any part is inside. The last part lands at about 0.91; from then on the intake is dark and the frame holds three finished parts on the pad.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | exactly three labels: intake (dim), machine (large, to the right of its top face), pad (in the second accent). Anything other than three non-empty labels throws | each wraps, balanced, in a fixed 200–260px column; the intake and pad labels are kept above the caption band. Short labels sit on one line; long ones stack |

**Known traps:**
- Leaving out `items` prints the demo `Raw work / WorkBuddy / Delivered ✓`, which puts the demo product name on the machine.
- Two labels, four labels or a blank label throws. (It used to leave the pad unlabelled or drop the fourth silently.) For another number of stages use `InOrder` or `ExplodedSchematic`.
- The whole scene, labels included, is scaled to the content zone and to the width, so on a 9:16 frame everything is drawn smaller. With a fixed origin, the pad's label once sat inside the caption band; the scene constants were measured off a render.
- The three parts are anonymous units of work in a fixed palette (blue, violet, green); they are not the film's items and carry no count. The settled frame shows three because the diorama always runs three. Those colours, the green pad and the dark machine are semantic and are kept on any ground.
- The raw side of the diorama is not: belt, intake pad and unfinished block are greys because the work is not coloured yet, and three light greys on a light film are three shades of the page. Measured on a light film: 35.0% of this register's ink under 3:1, and the largest hole — 0.38% of the frame — is the conveyor's own silhouette, the thing every other object in the picture rides on. On a light ground the three are taken from the film's own paper→ink axis, in the same order and spacing (belt nearest the page, intake pad furthest).
- Parts used to vanish at the end of the belt, and the third was still inside the machine on the last frame, so the pad labelled 'Delivered' ended empty. They now stay on the pad. Upstream parts are drawn behind the machine (they used to be pasted over its front face for the last stretch before the intake).
- The machine label used to sit across the machine's top edge, dark on dark, readable only while the intake glowed. It now sits on open ground to the right of the top face.
- At 9:16 the scene is scaled to about 0.57 and hangs from the top of the content zone, leaving the lower half empty. The SVG used to clip the pad and the delivered parts at x = W there; it no longer does.

**Reference:** `remotion/src/shots/IsometricAssembly.tsx`
