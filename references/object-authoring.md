# Object authoring — building a thing a film needs

A film builds an OBJECT when its beat needs a thing no register draws: a coffee puck in section, a sensor, a street's
strata, an interface that does not exist yet. The object lives in the film's workshop
(`python3 scripts/workshop.py <out_dir> new-object <Name> --means "<what the viewer must see>"`), goes into a register
that has a slot for one — `ObjectStage`, `ObjectCompare`, `ObjectPath`, `ObjectTurntable`, `TechnicalPlate` (`art`),
`HudReticle` (`object`), a device's `screen` — and is named on the film's `meta.build_list`. What to draw it WITH is
`references/building-blocks.md`.

> **Designing a shot from nothing** — the per-beat method and the premium checklist (one idea, encoding, focal hierarchy, restraint, type hierarchy, colour that means, motion that reveals, a signature moment) live in ONE place: `agents/shot-director.md` Step 0.55. This file is what you assemble the result FROM.

## The rules

1. **It ENCODES its beat.** Hide the caption: the object must still carry THIS beat's idea — the build-list entry's
   `means`, tested by its `accept`. On topic by colour or subject is not enough (see SwirlOfCoffee below).
2. **It is a designed diagram, not an imitation of a photograph.** When a beat needs the thing as it LOOKS, the
   documentary tier composites a real, credited image (`scripts/imagefetch.py`, `PhotoPlate`, `MuseumLabel`); an
   object shows how a thing WORKS or what it MEANS — a section, a flow, a state, a count.
3. **Every word comes from props, and no figure is invented.** The film writes its words in its own language; an
   object that writes its own prints them in every film (`workshop.py check` and `shot_proof.py` both refuse it). A
   word that genuinely belongs to the form — a unit symbol, an axis letter — is declared `// @fixed-text: <why>`. A
   quantity the object shows comes from a prop the film sourced; texture is declared `// @decor: <why>`.
4. **It sizes to its box.** It is drawn at `w × h`, whatever those are; `META.aspect` says the shape it wants and the
   slot letterboxes it. No fixed pixels, nothing outside the box unless it is meant to overhang.
5. **It is a pure function of `t`.** `t` runs 0 → 1 over the part of the beat its host gives it and then holds; at
   any frame the object is fully determined — no `Math.random`, no `Date`. What its host does with `t` is on the
   host's card (ObjectPath hands it the object's progress along the route; TechnicalPlate its drawing phase).
   **Moving type glides:** a transform or position that moves words goes through `glide()` from `@runtime/glide`
   over the span it moves in, or Skia steps the type a pixel at a time — `text_safe_qa.py <out_dir> --glide` refuses it.
6. **A natural cycle keeps running on `idle`.** Once a stage's reveal is over it HOLDS `t` at 1 until the cut, and
   a frame frozen for a third of its beat is a slideshow. So the slot also hands `idle`: seconds held since the
   host's reveal ended, easing up from rest and back down before the cut (0 under reduced motion, on a beat whose
   storyboard sets `"object_idle": false`, and for an object whose `META` says `idle: false`). An object whose thing
   genuinely cycles — water flowing, a precession turning, a wheel spinning — keeps that cycle going from it
   (`phi = phiSettled + 2π·rate·idle`), with the settled `t = 1` picture as its starting state, and keeps words
   off whatever moves. An object with no cycle ignores it; never invent one. A stage's callout stays where the
   SETTLED part was, so a callout that names a part the cycle carries away (the tip of a precessing arrow) ends
   up pointing at empty space: label what holds still, or set `"object_idle": false` on that beat.

7. **It is TRUE to the thing, and finely made.** Anything an object draws that depicts a real thing — a satellite,
   a gear train, an espresso puck, an organ, a vehicle, a building, a plant, a tool, a device — is held to the
   thing itself, and declares how in `META.fidelity` (a workshop SHOT that draws a real thing inline declares the
   same record on its `meta.build_list` entry, and a LIBRARY register does as `export const FIDELITY = {…}` beside its
   `DURATION` — `references/object-audit.md` is the library's triage of which registers owe one):
   ```ts
   fidelity: {subject: 'GPS Block IIF satellite', depicts: 'real',          // 'abstract': a chart, a metaphor shape
     references: [{kind: 'drawing', source: 'refs/gps-iif.jpg', note: '…'},  // photo | spec | drawing | asset
                  {kind: 'spec', source: 'https://…', note: 'span 43.1 ft'}],
     proportions: {span_to_body_width: {value: 5.3, source: 'https://…'}},  // each cites a reference's source
     parts: ['bus', 'solar-array', 'wing-boom', 'helix-array'],            // each drawn on data-part="<name>"
     materials: ['gold insulation foil', 'dark-blue solar cells']}
   ```
   - **References first, before drawing:** a real photo via `scripts/imagefetch.py` (it writes the licence sidecar
     the check requires) or the product's own asset (`asset`), AND a spec, drawing or diagram from a source you
     actually READ. Never fill a source from memory. A film's paths are relative to its out_dir.
   - **Proportions from the references:** record the key ratios, each with the reference it came from (`drawn` may
     say what the drawing has, so a gap is visible on the sheet).
   - **Defining parts:** the parts without which it is not that thing — the crown and band of a watch, the helix
     array of a GPS satellite, the portafilter basket of a puck. Each is attached where the real one is: no
     floating or detached part, no part larger than the whole. Mark each on the node that draws it,
     `data-part="crown"` (several nodes may share a name: two wings, twelve helices).
   - **Materials as the real thing has them,** lit consistently with the film (one light for the object and its
     ground).
   - **One geometry:** one projection and one transform for the object and everything on it — no level text on a
     skewed body; consistent symmetry, concentric radii and edge thickness.
   - **Detail that holds at the size it is shown,** checked at a 100% crop.

   **Stylised ≠ inaccurate.** Rule 2 still holds — an object is a designed diagram, not an imitation of a photograph
   — and it may be engraved, flat or schematic. But a diagram keeps the TRUE proportions and EVERY defining part: a
   two-tone satellite with the wrong number of panels per wing is not stylised, it is wrong. `depicts: 'abstract'`
   is for what has no real referent; never use it to skip the references of a real thing.
   `workshop.py check` and `validate.py` refuse a real thing with no reference (or no reference image), a
   proportion without a source, empty `parts`, a reference file that does not exist and a photo without its
   imagefetch sidecar. `workshop.py <out_dir> fidelity <Name>` renders the **fidelity sheet**
   (`<out_dir>/_fidelity/<Name>.png`): the reference images beside the hero-size render with every part outlined,
   the frame as the film shows it, and a 100% crop of every part. It reads the parts from the DOM and refuses a
   declared part that is not drawn (MISSING) or that touches no other part (DETACHED; `exploded: true` for an
   exploded view). The critic judges every real built thing on that sheet (`agents/shot-critic.md` S16). A
   device's sourced spec table (`runtime/deviceSpec.json`) is the device-shaped instance of this record.

`META` carries `aspect`, `provenance` (the idiom world its look comes from — the film's `idiom_world` is judged on
it), for an object that draws its own 3D from `yaw`, `turns: true` (objects/DemoForm is the reference), and for a
static diagram the idle clock must never move, `idle: false`, and always `fidelity` (rule 7).

## Three good objects

### A mechanism in cutaway — `PuckInSection`
![PuckInSection on ObjectStage](object-examples/PuckInSection.png)

Drops enter at the top and fight down through a packed bed; the more `packed`, the thinner and denser the bed and
the fewer drops get through. Caption hidden, the beat's claim — resistance is the point — is on the frame. It draws
no words: the stage's labels name the bed and the water. Source: `object-examples/PuckInSection.tsx`.

### Layered strata — `StrataOverTime`
![StrataOverTime on ObjectStage](object-examples/StrataOverTime.png)

A column grows layer by layer, each as thick as the film's numbers say, the newest on top in the accent. The eras'
names are the stage's labels; the object draws only what the numbers say. Source: `object-examples/StrataOverTime.tsx`.

### An interface being operated — `ComposeScreen`
![ComposeScreen on DeviceHero's screen](object-examples/ComposeScreen.png)

A screen that does not exist yet, drawn for a device (`{"screen": {"object": …}}`): the draft types itself in and
the send button lights when it is done. The recipient, the draft and the button are props. Source:
`object-examples/ComposeScreen.tsx`.

## Three bad objects — and which of them the gates catch

### An imitation of a photograph — `ChromeMachine`
![ChromeMachine on ObjectStage](object-examples/ChromeMachine.png)

Gradients and a highlight dressing up an espresso machine. It is clip-art, it shows no mechanism, and it competes
with the real machine a documentary image would show. **It passed every gate until rule 7:** its record says it
depicts an espresso machine and names no reference, so `workshop.py check` now refuses it — but references alone
would not make it a mechanism; that stays the critic's.

### Words written into the object — `LabeledPuck`
![LabeledPuck on ObjectStage](object-examples/LabeledPuck.png)

The bed and the water are named in Chinese in the code, so every film prints Chinese there and no prop can change it.
**`workshop.py check` refuses it** (and `shot_proof.py` names the words on the frame).

### Decoration that carries nothing — `SwirlOfCoffee`
![SwirlOfCoffee on ObjectStage](object-examples/SwirlOfCoffee.png)

A turning spiral in coffee colours: on topic by colour and by nothing else. Hide the caption — it says nothing about
extraction. **It passes every gate.**

One of the three bad objects (SwirlOfCoffee) still passes every machine check. A gate measures type, words and geometry; it cannot measure
meaning. That is why the shot-critic judges every built thing on its rendered frames (`agents/shot-critic.md` S15),
and why the build list states `means` and `accept` before anything is drawn.

## The loop

1. Write the build-list entry first: `means` (what the viewer must see) and `accept` (how it is judged). If it
   depicts a real thing, collect its references NOW (rule 7) and write its `fidelity` record before drawing.
2. `workshop.py <out_dir> new-object <Name> --means "…"`, draw it, `workshop.py <out_dir> still <Name>` — LOOK at the
   settled frame, caption hidden. A screen on a device is previewed with `--host DeviceDemo` (or `DeviceHero`):
   the still takes the beat that shows it and prepares its step script the way the film plays it; `--frame N`
   looks at a tap's moment. `still` writes one `_stills/<Name>.png` per name, so copy it aside before a second host.
3. `workshop.py check` until it is clean; for a real thing, `workshop.py <out_dir> fidelity <Name>` until its sheet
   has no problem — and LOOK at the sheet beside the references; then `validate.py`, render, and the film gates.
4. The critic judges it against `means` and `accept` (S15), and a real thing against its fidelity sheet (S16). At delivery the user decides whether it is promoted
   (`scripts/promote.py`).
