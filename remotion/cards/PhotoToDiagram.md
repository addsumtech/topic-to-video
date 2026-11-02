# PhotoToDiagram

**Identity:** a REAL photograph turns into its own line drawing and is then labelled — the beat moves from "this is the real thing" to "this is how it works" without ever leaving the thing. The outlines are the photograph's own edges, computed (scripts/photo_lines.py), never drawn by anyone.

**Use when:** a concrete subject with a real, licence-clean photograph, whose parts the narration then explains — a machine, an instrument, a building, a specimen. **Not when:** the photograph is the evidence and must stay a photograph (PhotoPlate), the subject has no visible edges (a cloud, a face in soft light), or the parts to explain are not visible in the picture.

**Motion core:** the photograph holds, then greys and dims (t 0.20–0.42); its outlines draw on in the film's accent outward from the first point the film names (radial reveal, 0.26–0.58); the photograph fades to a ghost under the drawing (0.50–0.64); each mark's dot, leader and label arrive in order (from 0.60, cue-able per mark), the label on the nearest side of the plate.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the photograph (evidence: required, with its sidecar) | a subject on a plain ground traces cleanly; busy texture traces as clutter |
| `lines` | the traced outlines — filled by render_remotion (`photo_lines.ensure`, cached by content) | — set by the render |
| `imageAspect` | the photograph's proportions — filled from the file | — set by the render |
| `imageW` | its pixel width — the plate is never drawn past 1.15x of it | — set by the render |
| `marks` | 0–5 `{x, y, label}`, fractions of the photograph | 2–4 marks explain; 5 crowds the sides |
| `title` | a short label over the plate | the subject's name |
| `credit` | the photograph's licence line (from its sidecar) | required whenever the photograph needs one |

**Known traps:**
- Outline specks (stars, grain) are dropped as short runs — measured on runs GROUPED within a few pixels; labelling the bare ridges deleted a whole satellite (non-maximum suppression leaves a diagonal outline as fragments).
- A 1-px ridge softened by half a pixel fell under half alpha; strokes are at least 2 px.
- A label placed by a fixed threshold sent its leader across the whole drawing; labels go to the nearest side.

**Refuses:** no `src`; no `lines` in a standalone still (run `python3 scripts/photo_lines.py <photo>`); a mark outside 0..1 or with no label; more than 5 marks; a photograph with no outlines to trace (photo_lines says how much would have been drawn).

**Reference:** `remotion/src/shots/PhotoToDiagram.tsx`, `scripts/photo_lines.py`, `scripts/render_remotion.py` `photo_diagram_props`
