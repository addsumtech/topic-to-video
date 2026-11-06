# Design craft: from "clear and correct" to "worth a second look"

The user's verdict on the films so far (2026-11-06): GPS "设计缺少美感"; ANC "还可以，但也达不到惊艳的程度". The bar they
named is industry launch films — Apple's product films; a 3D character hopping across a Mac while the Dock icon under
it rises to meet it; product intros (WorkBuddy) that weave real use into the story. They cannot hand over reference
videos, so the bar comes from research (references/craft-bar.md, written in A4) and the skill's own measured films.

Every past design correction came from the user, not from the skill: header titles ("视频不是 PPT"), one landscape behind
a satellite, a red "timetable" palette for satellites, the native-3D tier ("很烂"). Each became a one-off rule. The
skill has no memory of what it was taught, nothing that judges a picture before it is built, and no check that can tell
a crafted object from a line drawing. This spec adds those, in the user's order, and proves them on one new film.

Evidence corpus (our own films, never the user's materials): ~/Desktop/gps.mp4 + .superpowers/films/gps (the "lacks
beauty" anchor), films/https (line-drawn subjects, median ink 7.0 %), ~/code_project/film_work/anc (the "okay" anchor).

## A. Taste ledger — the skill remembers what it was taught (item 1)
- A1 **`scripts/taste_ledger.py`**, data at `~/.topic-to-video/taste-ledger.json` — the user's verbatim words, so never
  in this PUBLIC repo; the repo ships the schema and an empty example only (slide-maker's design, 2026-09-08). Entry:
  `{id, said, date, film, rule, stage: plan|design|build|render, status: active|retired, gate}`. Commands: `add`,
  `list`, `retire <id> --gate <gate>`, `brief --stage S` (the active rules a director must apply, one line each),
  `check <out_dir>`.
- A2 **Self-limiting.** An entry is RETIRED when a deterministic gate enforces it; the ledger holds only taught-but-
  ungated taste. Seeded from this user's recorded feedback: already-gated ones go in retired with their gate (no
  header titles → validate SLIDE TITLES; caption on the frame's own ground → keyframe_qa; never upscale a raster →
  media_res_qa; lining figures; hand-drawn device → validate); the rest stay active (environment per beat from its
  subject; contest heroes built with a subject palette; every element decodable in ~1 s; every visual encodes the
  beat's idea; tactile/lit over native wireframe 3D; the craft bar of A4).
- A3 **It is read and answered.** design-director, shot-director, shot-builder and shot-critic briefs include
  `brief --stage <theirs>`. `check <out_dir>` lists each active `look` rule for the film; `meta.taste_review` answers
  each with the artifact it was judged on (sha256 of the sheet or frame, as the review rule already requires).
  `critic_ledger --final` refuses an unanswered active rule; a user waiver by name passes it (`delivery_waivers`).
- A4 **`references/craft-bar.md`** — the research of 2026-11-06 as techniques, each naming the check or step that
  carries it, with sources: the hero → detail → context structure and restrained slow camera of Apple-style product
  films; a rim light behind the object separating it from a dark ground, soft key, no harsh shadows, environment
  reflections; anticipation, follow-through and volume-preserving squash for a character; real footage for the core
  demo with the zoom following the action and the valuable moment first; Kurzgesagt's sketch phase fixing each
  scene's visual metaphor before illustration. What the sources did NOT give (no studio published its rig) is said.

## B. Sketch before build (item 2)
- B1 **`slide.sketch`**, written by the design-director at 3.6 before any shot is built: `{metaphor` (one sentence: what
  the picture stands for), `hero` (the one thing the eye lands on), `layout` (2-6 named rects in content-zone
  fractions, the hero marked), `camera` (intent, see F2), `environment` (from the subject), `carries` (the tracked
  object it inherits, C1)`}`.
- B2 **`scripts/sketch_sheet.py <out_dir>`** draws every beat as a greybox tile with PIL — no Chrome, seconds: hero as a
  filled silhouette, other rects as tone blocks, labels as bars, the caption band shaded, a camera arrow, the metaphor
  under the tile, the through-object drawn as a ribbon across tiles — into `_sketch_review.png` on the Desktop.
- B3 **Measured on the sketch, before a line of TSX:** hero share of the frame; ink share (B-sheet version of the
  SPARSE floor); the same layout three beats running; more than one hero; a rect in the caption band; a beat with no
  metaphor. Findings print with the beat number.
- B4 **`meta.hero_moments`**: 1-3 beats named as the film's showpieces — the frames meant to stop the viewer. They get
  the budget (Blender plate, lit material, 3D camera, F2's grammar) and the strictest checks (D1). validate WARNS on a
  film of 8+ beats with none.
- B5 **Checkpoint order.** The user sees `_sketch_review.png` at 3.6 and approves it BEFORE building; the existing
  built `_design_review.png` stays as the second look. validate ERRORS on a built remotion beat with no `sketch`
  (a pre-rule board passes via the existing `--keep-design` route).

## C. One continuous world, for real (item 3)
- C1 **Object identity across beats.** `meta.through_object` stops being advisory: the tracked object's end pose in
  beat N (`x, y, scale, rotation, state` in frame fractions) is beat N+1's start pose; Film passes it in context
  (extending runtime/objectSlot.tsx). validate ERRORS on a declared pair that is neither handed on nor waived.
- C2 **The environment answers the object.** `runtime/reacts.ts`: an element declares a reaction (`rise`, `light`,
  `press`, `ripple`) to the tracked object's distance/contact, computed per frame from the object's path — a pure
  function of the frame, like every other motion. The proof register is generic: an object travels a row of
  real-looking items and each one reacts as it arrives (the user's Dock example, no brand drawn).
- C3 **Character motion.** `runtime/character.ts`: anticipation (squash before a jump), arc, landing squash with
  volume kept, follow-through stagger of parts — all through glide so no type trembles.

## D. Subject craft check (item 4)
- D1 **`scripts/subject_craft_qa.py <out_dir>`** reads each hero beat's SETTLED frame (~90 %, never mid-animation),
  locates the subject from its fidelity/data-part marks or the plate's ID pass, and measures: luminance range inside
  the silhouette (p95-p5), rim separation (subject edge band vs the ground just outside), highlight presence (small
  near-max regions), surface detail (edge density inside / area), flat-fill share (largest one-colour region).
- D2 **Calibrated on the corpus, not guessed:** a threshold ships only if it FAILS the HTTPS line subjects and the
  GPS shots the user found lacking, and PASSES the ANC plates. If no measure separates them, it does not ship and the
  finding is written down. ERROR on `hero_moments`, WARN elsewhere.
- D3 **Light to build with.** runtime lighting helpers for built shots (rim gradient following a silhouette, soft key
  falloff, contact shadow), and a three-point product rig in blender/kit/stage.py (key, fill, rim light-linked to the
  subject only — Blender 5.2 is installed and supports light linking).

## E. Density and real use (item 5)
- E1 **SPARSE becomes an ERROR** (film median ink < 14 % of the content zone) unless `meta.sparse_reason` names a
  minimal register on purpose; hero and title beats are excluded from the median.
- E2 **The planner asks "is there a real thing to show?"** per beat (footage, UI, the object itself) — content-planner
  rule beside 7b. On a launch/promo film at least a third of the beats show real use; validate WARNS below.
- E3 **The zoom follows the action.** FilmScreen accepts a focus track `[{t, box}]` (from a cursor/click log or
  authored) and moves its close-up along it on a smoothed path, never past the recording's own pixels (media_res_qa).
- E4 **Valuable moment first.** On launch/promo films a hero moment is previewed in the first 5 s (ColdOpen exists);
  validate WARNS otherwise.

## F. Camera language (item 6)
- F1 **A push is a dolly, not a zoom.** On 2D shots the camera moves layers at their declared depths (runtime/depth.tsx
  DEPTH), so perspective changes; on Blender beats the plate's own camera moves (camera.json is already exported).
- F2 **The hero grammar.** `slide.camera.move` gains `reveal` (light sweeps on, slow arc), `macro` (close, shallow
  depth of field, focus pulled onto one part) and `context` (pull back to the object in use) — Apple's hero → detail →
  context, for `hero_moments`.
- F3 **Type never rides the camera.** Labels sit on a fixed plane and appear when the camera settles (measured: type
  under a moving camera trembles 0.16 px and fails jitter_qa). A label tied to a moving part follows a projected
  anchor only during a hold.
- F4 **Depth of field** as per-layer blur by depth for `macro`; its cost is measured on one beat before it is
  offered.

## G. Proof: one new film
- One new film through the full pipeline, exercising A-F: sketch sheet approved before building, 1-3 hero moments, a
  tracked object handed across beats with an environment that answers it, a lit subject, real-use beats, F2 camera.
  Topic: the user's pick. Acceptance is the user's look; alongside it, measured against ANC with the same
  instruments: craft_qa, subject_craft_qa on the heroes, jitter_qa 0 ERROR, sketch findings 0 at build.
- Every new check is run over GPS, HTTPS and ANC before it ships (a measurement change is diffed on a corpus).

## Order
A → B → C → D → E → F, each its own commits and tests, then G. Full suite before any push; push only when told.

## Non-goals
No music changes; no cartoon style engine; no single decorative world for a film; no downloading reference videos;
no paid API; no library-wide restyle (the old library debt — type_debt, duplicate groups, near-empty registers — stays
parked).

## Anti-goals
- Gates that pass a film the user still finds plain: the user's look is the acceptance, not the exit code.
- Warnings nobody reads: a check ships only if it fired on a real old film and stayed quiet on ANC.
- A sketch stage that adds a round-trip without catching anything: if B3 finds nothing on GPS/HTTPS boards, the
  stage is cut back to the sheet alone.

## Calls I made (the user can overrule)
- The ledger lives outside the repo (it quotes the user), as slide-maker's does.
- The sketch sheet is PIL greyboxes, not rendered shots — cheap enough to redo per change.
- The sketch review comes before the built review instead of replacing it.
- SPARSE as ERROR with a named escape, not a silent floor.
- Labels wait for the camera to settle instead of riding it.

## Left to the builder
Exact measure formulas and thresholds (D2 sets the rule for choosing them), the tile layout of the sketch sheet, the
reaction curves of C2, and how the shot-builder brief phrases the ledger lines.
