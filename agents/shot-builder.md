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

## The part file
```json
{"builder": "b2",
 "shots": ["WeightedWheel", "OddsStatement"],
 "beats": {"12": {"shot": "WeightedWheel", "shot_props": {"mode": "roll", "…": "…"},
                  "shot_fit": {"verdict": "build", "ref": "WeightedWheel", "why": "…"},
                  "shot_adaptation": {"changes": [], "kept": "…", "redesigned": "…", "topic_idea": "…", "theme_cues": "…"}}},
 "build_list": [{"id": "WeightedWheel", "kind": "shot", "beats": [12, 14], "slot": "own", "uses": ["kit/Kit"],
                 "means": "…", "accept": "…", "props_doc": {"title": "what it sets — the feel of turning it"}}]}
```
`shot_fit.ideal` / `form` / `composition` are the lead's and are kept as written; you may add `verdict`, `why`, `ref`,
`shares`. Every number you print traces to `brief.json` evidence; never invent one.

## Report
For each shot: the beats it renders, the three frames you looked at (paths), what you fixed after looking, and anything
the lead must decide (a kit gap, a beat whose ideal you could not reach). Keep it short; the lead reads the frames.
