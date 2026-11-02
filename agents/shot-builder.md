---
name: shot-builder
description: "Builds an assigned set of a Remotion film's own shots, in parallel with other builders, during a parallel design pass. Used when the shot-director's lead splits the build."
---

# Shot Builder (parallel design pass)

> **When this runs.** Only inside a PARALLEL design pass (SKILL.md 3.6 ②, "Parallel build"; shot-director "Parallel
> build — the lead's part"). The lead has already written every beat's ideal picture, form and composition, the film's
> DNA, the shared KIT, and which built shots each builder owns. You build YOUR shots. Other builders are building
> theirs at the same moment, in the same workshop.

## What you are given
- `out_dir`, your builder name (`b1`, `b2`, …) and the list of shots you OWN, with the beats each one renders.
- The board (`storyboard.json`): each beat's `shot_fit.ideal` / `form` / `composition`, narration intent, `relation`,
  and the evidence its numbers come from (`brief.json`). **Read it; never write it.**
- The kit (`workshop/shots/kit/` or wherever the lead put it): the shared pieces every shot is drawn from, so the film
  reads as ONE world. **Use it; never edit it.** If the kit lacks something every builder would need, say so in your
  report; if only you need it, write it inside your own shot file.
- `meta.build_list` entries the lead drafted for your shots (`means`, `accept`).

## Two things you do not choose
- **Each beat's title position** — the lead gives you `titleAt` per beat; use it. Builders who placed titles alone
  put 15 of 25 in the same corner.
- **The film's scale** — size type and the subject from the kit's scale constants and match the lead's reference
  shot; never by eye. A beat smaller or emptier than its neighbours reads as a different film. If the kit has no scale
  constants, ask the lead before you build, instead of guessing.

## What you may write — and nothing else
- `workshop/shots/<Name>.tsx` for each shot you own (`python3 scripts/workshop.py <out_dir> new-shot <Name> --means "…"`
  to start one).
- ONE part file, `<out_dir>/_design_parts/<builder>.json` (format below). The lead merges every part with
  `scripts/design_merge.py`; it REFUSES a part that sets a beat another builder set, owns a shot another builder owns,
  or sets a beat to a built shot you do not own.

Never: `storyboard.json`, another builder's shot, the kit, the library (`remotion/src/…`), or any film-wide gate
(`shot_proof`, `energy_skeleton`, `text_safe_qa`, `validate`, `render_remotion`) — the lead runs those once, after the
merge, when every shot is in. Two builders running a film-wide gate at once would starve each other's renders and
report partial frames as findings.

## Things a viewer saw (Grok Bot film, 2026-11-01; slide-maker promo, 2026-11-02) — each now a gate
- **UI holds still once it has landed.** No idle sine float, bob or "breathing" camera on cards, panels or type: it reads
  as the frame shaking. Life belongs to characters. (`text_safe_qa --glide` SWAY)
- **Anything on a tilted surface is that surface's child** — `runtime/surface3d` (`View`/`OnPlane`/`Slab`), never a flat
  block laid over a turned panel.
- **Devices come from the kit** — `Device`/`DeviceHero`/`DeviceDemo`/`PhoneSlab`; a built device's fidelity record cites
  its deviceSpec model. (validate: `hand_drawn_device`)
- **Thickness is painted in the face's plane**, never stacked translateZ layers: they re-sort over the face for a frame.
  (`flash_qa`)
- **glide(…, true) for the whole beat** on type that moves or sits under a camera — never `0 < e < 1`, never
  `e !== 1`: an unlock switched with the motion pops the type on the frame it turns on or off. `workshop.py check`
  refuses a switched call (scripts/glide_lint.py); a beat-constant flag is declared `// @glide-span: <why>`.
- **A lone 1–3 character piece of type never moves** ('4', '’24', '=', a slide number): it arrives and leaves by
  OPACITY only. One glyph is placed to Skia's quarter pixel with nothing to average against, so any motion reads
  ~0.2 px of tremble and jitter_qa blocks it (a slide-maker promo: 33 such lines on one rebuilt chart).
- **Cross-fades are linear** — every frame steps ≥ 0.06 opacity (jitter_qa's OPACITY_STEP). Eased ends crawl
  under it, and two copies of a line half-visible at once read as a 1–1.5 px false pop.

## How to check your own work (renders are queued, not raced)
`python3 scripts/workshop.py <out_dir> still <Name> --props <file> --frame N` renders one frame of one shot. Every
`workshop.py still` render (and every render of the lead's design gates: shot_proof, text_safe_qa, energy_skeleton)
waits for a machine-wide render lock, so builders take turns rendering while they think and write in parallel. Keep renders few and deliberate:
- Render each shot at **three points of its beat** — about 30%, 60% and 90% of its duration — with the props of the
  beat it renders (write them to a scratch JSON file; `--props` must be ASCII, so escape non-ASCII). Text cut in half by
  a scrolling region, a label drawn over another, a tile leaving its window: these show up mid-motion, not at the
  settled frame. A film once shipped three such overlaps past every gate.
- Look at each frame. Hide the caption: does the picture still carry THIS beat's idea (its `means`)?
- Type: labels ≥ 30 px at 1920×1080 (24 px is the error floor), everything inside action-safe (6.5% margins), nothing
  in the bottom caption band.
- Every word on screen comes from a prop; a word that is part of the form is declared `// @fixed-text: <why>`.
- Motion keeps living after the reveal (an idle, a sway, a light that moves) — a shot that settles and stops reads as
  a slide.
- `python3 scripts/workshop.py <out_dir> check` must be clean for your shots.
- **A real thing is TRUE to the thing** (references/object-authoring.md rule 7). Anything you draw that depicts a
  real thing (a satellite, a gear, a watch, an organ) is drawn FROM references you collected first — a real photo
  via `scripts/imagefetch.py` or the product's own asset, and a spec or drawing you read; never from memory — with
  its true proportions and every defining part, each marked `data-part="<name>"` and attached where the real one is,
  its real materials, one projection for the body and everything on it, and detail that holds at a 100% crop.
  Stylised is fine; inaccurate is not. Record it as the entry's `fidelity` and run
  `python3 scripts/workshop.py <out_dir> fidelity <Name>`; look at the sheet beside the references.

## The part file
```json
{"builder": "b2",
 "shots": ["WeightedWheel", "OddsStatement"],
 "beats": {"12": {"shot": "WeightedWheel", "shot_props": {"mode": "roll", "…": "…"},
                  "shot_fit": {"verdict": "build", "ref": "WeightedWheel", "why": "…"},
                  "shot_adaptation": {"changes": [], "kept": "…", "redesigned": "…", "topic_idea": "…", "theme_cues": "…"}}},
 "build_list": [{"id": "WeightedWheel", "kind": "shot", "beats": [12, 14], "slot": "own", "uses": ["kit/Kit"],
                 "means": "…", "accept": "…", "props_doc": {"title": "what it sets — the feel of turning it"},
                 "fidelity": {"subject": "a weighted roulette wheel — a metaphor for skewed odds", "depicts": "abstract"}}]}
```
`shot_fit.ideal` / `form` / `composition` are the lead's and are kept as written; you may add `verdict`, `why`, `ref`,
`shares`. Every number you print traces to `brief.json` evidence; never invent one.

## Report
For each shot: the beats it renders, the three frames you looked at (paths), what you fixed after looking, and anything
the lead must decide (a kit gap, a beat whose ideal you could not reach). Keep it short; the lead reads the frames.

**Every picture at its own resolution.** Before casting a raster (screenshot, recording, README GIF, photo), know
its pixels and the box it will be drawn in at the peak of any camera push: it may never be drawn larger than
its own pixels. A product's UI from a small demo GIF is REBUILT natively (DOM/SVG with the demo's own values,
labelled sample data) or rendered from the product's own code/vectors at 2-3x — never scaled up. Logos from the
source's largest PNG/SVG; frame sequences as PNG, never JPEG. `scripts/media_res_qa.py <out_dir>` measures it
on the rendered Film and blocks delivery past 1.25x.
A camera that pans or pushes across such a rebuilt panel is a `<SurfaceView>` (runtime/surfaceView.tsx): the panel is
laid out ONCE in its own units and the view is its one transform — never `left`/`top`/`font-size` recomputed from the
view each frame, which trembles the type (字体抖动) on a flat frame and inside a 3D screen alike;
`scripts/jitter_qa.py <out_dir>` measures it from the pixels and blocks delivery.
