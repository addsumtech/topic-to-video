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
