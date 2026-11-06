# The craft bar — what a frame worth a second look is made of

The user's verdict (2026-11-06): the GPS film "lacks beauty", the ANC film is "okay but not stunning". The bar they
named is industry launch films: Apple's product films; a 3D character hopping across a Mac while the Dock icon under
it rises to meet it; product intros that weave real use into the story. They could not hand over reference videos, so
this page is the research of 2026-11-06, each technique with the step or check that carries it in this skill.

**What the research did NOT give.** No studio has published the rig, lights or render settings of a specific Apple
film; two of the most relevant articles refused automated reads (HTTP 429 and 403), and most of what is public is
tutorials and tool-vendor blogs. Treat the techniques below as working practice, not measured fact. Thresholds in
this skill come from our OWN films (GPS, HTTPS, ANC), never from these pages.

## Product films (the hero)
- **Three sections: the hero reveal, the details, the product in context.** → `meta.hero_moments` + the camera moves
  `reveal` / `macro` / `context` (validate, Film).
- **A rim light behind the subject traces its silhouette and separates it from a dark ground**; the key is soft, no
  harsh shadows; reflections come from an environment, not from nothing. In Blender, light linking keeps the rim on
  the subject only. → `blender/kit/stage.py product_rig`, `runtime/lighting.tsx`, and `subject_craft_qa.py` measures
  rim separation and highlight range on the hero frames.
- **Restraint: slow orbits, one subject, negative space as a choice.** → the hero camera grammar; the sketch sheet
  measures one hero per frame.
- **A dolly changes perspective; a zoom only changes framing.** A 2D push is a zoom, which is why it reads flat. →
  the hero moves move layers by depth (parallax), and Blender beats move the plate's own camera.

## Characters and objects in a world
- **The object drives the environment**: a character SDK answers app events with motion and expression; the Dock
  example is the reverse — where the object lands, the item under it answers. → `runtime/reacts.ts`, `slide.track`
  and `meta.through_object` (the object's end pose is the next beat's start pose).
- **Anticipation before an action, follow-through after it, squash and stretch with the volume kept.** →
  `runtime/character.ts`.

## Real use
- **Real footage for the core demo, motion graphics for the hook**; the zoom follows the clicks and the cursor path is
  smoothed; the most valuable moment comes first. → FilmScreen `focusTrack`, the real-use share on launch/promo films,
  a hero moment previewed in the first 5 s.

## Before illustration
- **Kurzgesagt settles the visual metaphor of each scene in a sketching phase before illustration** (their own process
  page); an educational-animation maker describes concept → AV script → rough storyboards. → `slide.sketch` and
  `scripts/sketch_sheet.py`, approved by the user before any shot is built.

## A shared visual language
- **Linear hires a "motion storyteller" to keep one visual language across its video content.** → the taste ledger:
  each film inherits what the user already taught instead of starting over.

## Sources
- Apple-style 3D animation guide — https://renderedgestudio.com/what-is-apple-style-3d-animation/
- Product lighting in Blender (rim light, light linking) — https://cgiacademyhub.com/blog/iluminacion-producto-blender
- Product animations in Blender — https://www.skillshare.com/en/classes/create-product-animations-in-blender/80097829
- Cinematic tech videos like Apple (search summary only; the page refused the read) —
  https://www.manfrotto.com/global-en/stories/how-to-shoot-cinematic-tech-videos-like-apple/
- Apple Watch faces shot practically — https://appleinsider.com/articles/18/09/20/apple-watch-series-4-new-watch-faces-shot-with-practical-effects-not-cgi
- Kurzgesagt's process — https://kurzgesagt.org/youtube/
- Linear, Motion Storyteller role — https://linear.app/careers/2cf28db7-821f-44a0-99ee-ee0b7b7581af
- Masko mascot SDK — https://mcpservers.org/tr/servers/masko-ai
- Disney's principles applied to UI — https://ixdf.org/literature/article/ui-animation-how-to-apply-disney-s-12-principles-of-animation-to-ui-design
- Auto zoom in screen recordings — https://www.docsie.io/blog/glossary/auto-zoom/
- Product launch videos — https://focusee.imobie.com/product-demo/product-launch-video.htm
- Negative space — https://www.studiobinder.com/camera-shots/composition/negative-space-in-film/

## Calibration (filled in as each check is measured on GPS / HTTPS / ANC)

### Sketch sheet on the GPS board (2026-11-06)
GPS sketches were back-filled by eye from its `_design_review.png` (rects are estimates, ±5 % of the frame), then
`sketch_sheet.py` was run: 6 findings. Five are hero size — the phone in beat 1 (6 %), the flash-to-bang bars (10 %),
the phone clock (10 %), the fix point (4 %) and the closing title (10 %) — beats whose subject sits small in a large
dark frame, which fits the user's "lacks beauty" verdict. The sixth (beat 12's clock reaching the caption band at 82 %)
is an artefact of eyeballing: the built frame passed keyframe_qa. HERO_MIN (12 %) is set from this one board and has
NOT been checked against ANC; it stays a sheet finding for the user to judge, never a delivery gate.

### Subject craft on GPS and ANC (2026-11-06)
`subject_craft_qa.py` on settled proof frames (boxes by eye, except ANC 8/9/20 from the plates' own boxes; HTTPS is no
longer on disk, so the corpus is two films). Numbers in `tests/fixtures/subject_craft_corpus.json`.

| film | beat | subject | light range | rim | highlight | flat fill |
|---|---|---|---|---|---|---|
| GPS | 3 | satellite | 0.59 | 0.21 | 0.49 | 0.16 |
| GPS | 5 | satellite | 0.58 | 0.21 | 0.53 | 0.08 |
| GPS | 1 | phone | 0.46 | 0.05 | 0.26 | 0.61 |
| GPS | 14 | map circle | 0.53 | 0.13 | 0.02 | 0.76 |
| ANC | 8 | parts (Blender) | 0.44 | 0.24 | 0.04 | 0.63 |
| ANC | 9 | earbud (Blender) | 0.12 | 0.18 | 0.05 | 0.75 |
| ANC | 20 | tip seal (Blender) | 0.20 | 0.22 | 0.13 | 0.40 |
| ANC | 11 | earbud section | 0.64 | 0.33 | 0.23 | 0.29 |

**No measure separates the film the user found lacking from the one they found okay.** GPS's foil satellites are
the most lit, highlighted and detailed subjects of either film; ANC's Blender plates are soft, low-contrast matte
objects. So the GPS verdict is not about the subject's lighting. What the sketch sheet found on the same board — the
hero small in a large dark frame on five beats — and the one dark ground repeated across thirteen of fifteen beats
fit it better. THRESHOLDS stays empty: the tool REPORTS the hero's numbers (and fails a hero it cannot locate), and
the judgement stays with the user. ANC's plates also show what "Apple-like" would add that they lack: a highlight
(0.04-0.13) and a rim — the three-point rig of `blender/kit/stage.py product_rig` is aimed at exactly that.
