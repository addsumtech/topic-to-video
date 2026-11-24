# Shot language — coverage inside a sequence

A working vocabulary for planning the shots of ONE sequence (SKILL.md step 5, the treatment; step 6, the build).
A toolkit, not a checklist: choose a shot for what it tells the viewer, never for coverage's sake. The editing
principles (J/L cuts, match cuts, cutting on the voice, eye-trace) are `director-craft.md` §1; the seams BETWEEN
sequences are `promo-shotcraft.md` §2 and `shot_plan_qa.py`. This page is what happens INSIDE a sequence.

**Why it matters here.** One beat = one sentence = one shot made our films a metronome: shot lengths spread 1.6-1.9x
(p90/p10) against 2.7-37x in 26 published films, 0 % of shots under 1.5 s against 7-68 % (`craft-study.md` P1); the
17 director-path plans of 2026-11 still averaged 3-10 s a shot, with no straight cut between framings. The fix is
not more transitions: it is cutting between framings of the SAME world on the voice — a straight cut, which a
sequence allows (`"seam_out": "cut"` between two shots naming one `sequence`).

## Roles
- **A-roll** is the narration: the voice carries the argument and the pictures are cut to it. Every picture is
  B-roll in function: it illustrates, proves, contrasts or sets the mood of what the voice says. A-roll/B-roll are
  roles, not two visual styles or two tracks; what carries a moment (the product's real screen, a diagram, a real
  photograph, type, a 3D object, a character acting) is the register's choice (film-designer §1b).
- **Establishing (wide)**: the world before its detail — where we are, how big, what connects to what. For a
  process or a place, orient first; for a hero object, withhold the whole and go fragments-first (macro before the
  reveal, `craft-study.md` P2). Choose one on purpose.
- **Insert**: a close detail the claim rests on: the button the voice names, the number, the part of the mechanism,
  the line of the document. Readable details stay true (a real screen is pushed within its pixels, never redrawn).
- **Cutaway**: leave the main subject briefly for something related (the place it is used, the thing it replaces).
  It must add information or feeling; a cutaway that only hides an edit is filler.
- **Reaction**: a character answering what just happened (the mascot looks at the result, the user's cursor pauses):
  `Stage3D.look` / `Stage3D.blink` on a page, `runtime/reacts.ts` in Remotion. It gives a moment its meaning.
- **POV / over-the-shoulder**: what the character or operator sees, from behind it onto the screen it works on; use
  it when the experience of using the thing is the point.
- **Top-down**: layout, a process on a table, a comparison laid side by side.

## Framing (`framing` in `shot_plan.json`)
`wide` (context, geography, scale) · `medium` (the subject and what it acts on) · `close` (one element: a component,
a face, a word) · `macro` (a texture, an edge, one digit). A straight cut should change the size by at least a step
(wide to close is the classic punch-in); a cut between two shots of one framing reads as a jump cut and the plan check
warns, unless the jump is the point (compressing a process in steps). Range across the film too: a film that lives at
`medium` is flat (`craft-study.md` P2: our scale spread 0.18-0.26 of the frame, theirs 0.45-0.68).

## Camera moves in this engine
A move has a job: reveal, follow, connect, or shift emphasis; one camera language per sequence.
- **Push / pull**: on a flat picture this is a zoom, which reads flat; with two or more depth planes moving by depth it
  is a dolly, which changes perspective (`craft-bar.md`). A screenshot is never pushed past its own pixels.
- **Truck / pan**: travel along a process, a row, a map; ends where the next idea is.
- **Orbit / arc**: around a 3D subject (the 3D stage or Blender), to show its form or a relation change.
- **Static hold**: when the image or the information deserves attention; the climax gets the longest hold.
- **Handheld**: not used. Every frame is a pure function of time with no randomness, and a constant drift on fine
  detail shimmers (`picture_glide_qa`).

## Editing inside a sequence
- **Straight cut**: the default between framings of one world. Build the sequence as one stage in `film.html` and a
  new framing is the same scene from another camera: light, props and state carry over by construction.
- **Jump cut**: time removed at one framing; compresses a process (a file filling in three steps).
- **Montage**: many short shots building breadth or progression (`promo-film.md`: cuts of 0.3-0.8 s, each landing
  and holding).
- **Cross-cut**: alternate two things happening at once (the request sent / the agent working).
- **Match cut**: a shape, position or motion carried across (`"seam_out": "match"`, between sequences too).

## Continuity across a straight cut
Keep identity, prop and UI state, screen direction, eyeline, action phase, geography, light direction and timing,
unless the change itself says something. Time runs one way: a state reached in the wide is still reached in the
close (`rewind_qa`). Cut on the action or on the voice (~0.1-0.2 s before the word), and keep the eye where the last
shot left it.

## In the plan
Each shot of `shot_plan.json` may carry `sequence` (one id per world) and `framing`; a straight cut is
`"seam_out": "cut"` inside one sequence, and a seam between sequences is still carried, hidden or a hard cut by design
(beat-cut, match, state: `shot_plan_qa.py`). The
opening's 3 s arc is counted over its whole first sequence. Angle, move and continuity notes go in the treatment's
line for the shot, only where they matter; the treatment and the plan stay the source of truth.
