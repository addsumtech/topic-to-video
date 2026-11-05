# After the ANC film: speed, sound as content, one continuous world, visible progress

Evidence is the ANC film (2026-11-05, ~/code_project/film_work/anc): 24 beats, 3 Blender plates, 14 hand-built
shots, delivered after ~6 h with two stalls the user felt ("感觉有些慢"). Each item names what it costs today, the
change, and the test that pins it.

## A. Speed — never pay twice, and say how long
- A1 **A plate keys on its own code only.** Today plate_key hashes EVERY .py under the film's blender/: one edit to
  explode.py rebuilt all three plates (~11 min, twice). Key = the scene + the modules it imports inside blender/
  (AST import closure) + the skill kit. Test: two scenes sharing budkit.py — editing one scene leaves the other's
  key; editing budkit changes both.
- A2 **The estimate learns reuse.** Today 4.6 s a frame assumes every frame whole: 61 min estimated, 12.7 actual, and
  a needless over-budget prompt. Estimate from the plate's own last run.json (whole/patched/copied counts and times)
  when there is one; otherwise a reuse-aware default calibrated on the five measured plates. Test: a recorded
  run.json drives the estimate; the default lands within 2x of the five measured builds.
- A3 **Delivery gates run in parallel.** critic_brief --gates runs 18 gates one after another (~20 min). Independent
  gates run in a small pool (renders still queue on the render lock). Measured before/after on the ANC film.
- A4 **Tests cannot hang the suite.** test_kinetic's `remotion still` sat 24 min at 0% CPU, and an orphaned one burned
  66% CPU for 50 min. Test-side renders go through watched_run (fatal lines, idle, cap), and a session-end fixture
  kills strays the session started.

## B. Sound as content — a film about sound lets you hear it
- B1 **The planner asks "can the viewer hear or see the real thing?"** content-planner emits `demo` on a beat whose
  point is a sound (or real footage): an A/B the viewer hears, cued by the voice ("listen: off… on"). Industry demos
  do exactly this: a matched-level comparison with the feature toggled.
- B2 **`slide.audio_demo`** {clip, level_db, at: cue, label}: the renderer mixes the clip at its own loudness (not
  ducked under the voice), the caption shows a [listen] cue, and the voice pauses for it (a tts gap). A synthesized
  clip says so on screen ("synthesized"); a recorded one carries a CC0/CC-BY sidecar like images.
- B3 **The ANC film gets its demo:** beat 5 plays the hum, then hum + its inverted copy scaled 0.94 and a hair late —
  the SAME residual the scope draws — so what you hear matches what you see (sourced: the waves "largely cancel").

## C. One continuous world — the earbud the camera travels through
- C1 What the references do: Manim keeps an object's identity and MORPHS it (Transform) instead of cutting to a new
  drawing; Kurzgesagt weighs visual metaphors in sketches before illustrating, and is dense (secondary sources: 200+
  panels for ~9 min, ~22 a minute; ANC had ~9 a minute); Motion Canvas times animation to the voice with editable
  time events. ANC drew the earbud six different ways in six shots.
- C2 **The shot-director names the film's through-object** (here: the earbud); the beats that live on it are one
  continuous stage, or carried across `container` seams — the object keeps its place, size and identity between
  beats. validate (advisory) counts beats that redraw the through-object from scratch.
- C3 **A density floor in the kit:** every built kit exports its scale (main type, label floor, subject fill) and a
  "second read" layer per beat; shot_proof's SPARSE warning names the beats to fill first.
- C4 **The ANC film, rebuilt on it** (the user's decision): beats 8–14 become one earbud — the 3D exploded plate
  closes, cuts in section and stays put while the mics and the signal path light on it.

## D. Visible progress and quieter gates
- D1 **_progress.json + a progress page.** Every long script (plates, render, gates, suite) writes phase, item i/n,
  elapsed and an ETA from measured per-item times; `progress.py <out_dir>` prints one line and writes a
  self-refreshing local HTML page; monitors read it instead of log text (a buffered log looked dead).
- D2 **Fewer false alarms:** the hand-drawn-device check matches device words (phone/tablet/laptop/watch), not
  "microphone"; warnings are grouped by kind with a count and the worst five shown; a jitter finding carries its
  size and says how to waive it.

## Order
A1, A2, D2 (small, certain) → A3, A4, D1 → B1–B2 → C2–C3 → B3/C4 on the ANC film after the user picks.
