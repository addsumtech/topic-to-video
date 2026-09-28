# ObjectStage

**Identity:** a thing the film drew for itself (an object from its workshop) stands whole on a quiet floor and its name is set under it. What calls out its parts depends on the room: a wide frame (16:9, 4:3) runs leader lines out to unnumbered side labels; a portrait or square one puts numbered dots on the object with a numbered key under its name. The object owns the picture, the stage owns the words.

**Use when:** the beat says "this is the thing — look at it": the film has built an object no register draws (a coffee puck in section, a sensor, an artefact) and the argument names a few of its parts. **Not when:** the thing is a real photograph (`PhotoPlate`, `MuseumLabel`); the claim is a comparison (`ObjectCompare`), a process (`ObjectPath`) or the object's shape in the round (`ObjectTurntable`); the object is best read as a technical elevation (`TechnicalPlate` with `art`).

**Motion core:** the floor's shadow comes in over 0.03–0.2 while the object draws itself — its own t runs 0→1 over 0.06–0.6 and then holds. The callouts land one after another from 0.6, every one in by 0.84; the name and the note land over 0.62–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing the film drew — `{"id": …, "props": …}` from its workshop (`scripts/workshop.py`) | sized as large as the words leave room for, at its own aspect; required in a film (absent draws the stage's preview form) |
| `labels` | 0–6 callouts `{text, x, y, side?}` at points on the object (0..1 of its box) | wide frames run leaders to the side margins (`side` defaults to the half the point is in); portrait and square frames put numbered dots on the object and a numbered key under the name |
| `title` | what it is, set under the object | fitted to the width; long or Chinese names wrap, balanced |
| `note` | one line under the title | the place to say what the object's shape MEANS |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- The object is drawn by the film, so everything the stage cannot see — its words, its colours, its motion — is the object's to get right; the stage's gates (text-safe, CJK type, words-from-props) still run on the whole frame.
- A callout point is a fraction of the object's DRAWN box, not of the frame: a wide object leaves its box shorter, and the points move with it.
- Past six labels the columns overprint; the register refuses.
- The object is fitted at its own declared aspect (`META.aspect` — the workshop's `new-object` scaffold defaults it to 1, a square) and letterboxed inside the stage box; a wide or tall object leaves the box's spare width or height empty, and callout points still map through the FITTED box, not the room around it.
- An object whose own drawing does not reach its box's bottom edge reads as floating above the stage floor: the floor's shadow sits at the box's edge, not at the object's own silhouette, so an object with air under it (rather than one seated close to it, the way `DemoForm` is at its own default turn) looks like it is hovering.

**Refuses:** a malformed `labels` (not a list, more than six, a label with no `text`, without `x`/`y` in 0..1, or a `side` that is not `'left'`/`'right'`); an `object` that is not `{id, props?}`, names no object that exists, or sets `w`/`h`/`t`/`dna`/`yaw` in its props; a `title`/`note` (plus the key, in portrait or square) that cannot fit above the caption band even at half size — the message names the exact px it needed and the px the frame had, not just "too much text"; the same for a wide frame's side callouts, PER COLUMN — a short column is never refused (or shrunk) for a long one on the OTHER side, and a refusal names its own column's shortfall.

**Reference:** `remotion/src/shots/ObjectStage.tsx`

**Provenance:** motion-graphics (a beat holding an object is judged on the object's own world). **Family:** E.
