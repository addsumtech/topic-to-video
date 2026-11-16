# Video looks — what a film LOOKS like, in the categories video makers use

A video's look is a **production technique plus a vibe**: how the pictures are made (illustrated, typographic,
real screens, lit 3D, cut paper, archival photos, a drawn line) and the mood they carry. Studios and explainer
houses sort their work this way (2D/flat illustration, motion graphics, kinetic typography, screencast/UI, 3D,
isometric/2.5D, cut-out and collage, whiteboard, mixed media, live action), and 2026's motion roundups add the
directions now in demand: handmade imperfection and texture, type in motion, hybrid 2D/3D depth, retro grain,
vertical-first. Sources (practice roundups, not research; treat as the field's vocabulary): Yum Yum Videos "15 types
of explainer videos", Vmaker "Top 10 styles of animated explainer videos", ContentBeta "motion graphics styles",
Videobolt "Top motion graphics trends for 2026", Designity "2D animation trends 2026", Kapwing "How to make
informational videos like Vox", University of Michigan Arts "Simple, bright, beautiful: the work of Kurzgesagt".

**How to use this file (SKILL.md step 5).** Pick 2-3 LOOKS below that fit the subject and purpose; for each, pick
its palette and type from `visual-styles.md` (the listed sub-registers are the usual fits, not the only ones); render
one style frame per look of the film's real subject. Frames must differ as looks: the technique differs, not just
the colours. Never copy a specific studio's characters, mascots or signature art; take the genre, not the artist.

Each look: **what it is** · **made of** (palette, type, texture) · **moves like** · **best for** · **avoid when** ·
**sub-registers** (`visual-styles.md` keys for `theme.py --style`) · **engine**.

## 1. Flat illustrated explainer
- **What:** a world of bold flat vector shapes, rich saturated colour, soft glows, rounded geometry; the science-
  channel look. Objects are simplified to their meaning.
- **Made of:** a deep ground (navy, plum) with 3-5 saturated fills and one glow colour; a friendly geometric sans;
  no outlines or very soft ones; gentle gradients only for light.
- **Moves like:** layered parallax, things pop and settle with a small overshoot, continuous ambient life (stars
  drift, particles float), the camera glides through the world between ideas.
- **Best for:** science and nature 科普, abstract ideas made concrete, a general audience.
- **Avoid when:** the subject is a real product, real people or real data that must be seen as it is.
- **Sub-registers:** `cinematic` (dark, lit), `glassmorphism` (glow), `claymorphism` (softer, rounder).
- **Engine:** one HTML/SVG page; Remotion for heavy parallax.

## 2. Mathematical / diagrammatic animation
- **What:** the diagram IS the film: shapes, graphs and equations that transform continuously into each other on a
  dark ground; every motion is the argument (a curve bends because the formula changes).
- **Made of:** near-black ground, 3-4 clear stroke colours each bound to one quantity, a clean sans plus typeset
  maths; thin precise lines.
- **Moves like:** continuous morphs and draw-ons, no cuts inside an idea; the camera zooms into detail and out.
- **Best for:** maths, physics, algorithms, any mechanism with a formula or a geometry.
- **Avoid when:** the audience needs warmth or story more than precision.
- **Sub-registers:** `blueprint`, `terminal`, `swiss` (dark).
- **Engine:** HTML canvas/SVG computed per frame (the sky film computed its sky this way); Remotion's draw/morph
  runtime.

## 3. Editorial motion graphics (the news-explainer look)
- **What:** a designed page come alive: maps, charts, highlighted documents, photos with captions, arrows and
  circles drawn on, on paper or a neutral ground.
- **Made of:** off-white or paper ground with subtle texture, ink, ONE strong accent (highlighter yellow, red),
  a serif or grotesk for headlines, real sources shown as images.
- **Moves like:** quick, cut on the voice; zooms into a document's line; markers draw on; charts build.
- **Best for:** current affairs, data stories, economics, "why does X happen" with evidence.
- **Avoid when:** there is no evidence to show (then it becomes empty paper).
- **Sub-registers:** `editorial`, `swiss`, `cartographic`.
- **Engine:** HTML page.

## 4. Kinetic typography
- **What:** words are the picture: large type that builds, breaks, scales and replaces itself in time with the voice.
- **Made of:** one heavy display face, high contrast, one accent word per line; almost no imagery.
- **Moves like:** word-by-word, snapping to the voice's stresses; scale and position carry emphasis; fast.
- **Best for:** hooks, manifestos, quotes, a launch's problem/promise lines, short social videos.
- **Avoid when:** the content is a mechanism that needs a picture; a whole long film of type tires the eye. Use it as
  the type beats inside another look.
- **Sub-registers:** `swiss`, `brutalism`, `bauhaus`.
- **Engine:** HTML page.

## 5. Product UI launch
- **What:** the real product as hero: its real screens large in frame, soft depth and shadow on a calm brand
  ground, type beats between product beats, a closing lockup.
- **Made of:** the brand's own colours and logo, a clean sans, real screenshots/recordings within their pixel
  density, subtle glass or shadow for depth.
- **Moves like:** smooth 2.5D camera pushes onto the component the voice names, a cursor doing the action, quick
  rhythm, one small celebration.
- **Best for:** software and app launches, feature announcements, onboarding.
- **Avoid when:** there are no real screens (then show the outcome, not redrawn UI).
- **Sub-registers:** `glassmorphism`, `swiss`, `editorial`.
- **Engine:** HTML page; `promo-film.md`'s shot table when the user wants that form. SKILL.md's launch grammar applies.

## 6. Cinematic lit 3D
- **What:** real light and material: reflections, refraction, depth of field, objects you could touch.
- **Made of:** a dark or graded ground, one key light direction for the whole film, physical materials (glass,
  metal, liquid), restrained type.
- **Moves like:** slow orbiting and dolly moves, rack focus, light sweeping across surfaces.
- **Best for:** physical objects, optics, materials, hardware products, space, anything whose physicality is the
  content.
- **Avoid when:** the idea is abstract or the content is words and data.
- **Sub-registers:** `cinematic`, `noir`.
- **Engine:** Blender plates (`blender-plates.md`) and the Remotion lit stage/material runtime, placed as clips
  (`workshop.py <film_dir> clip`).

## 7. Isometric / 2.5D systems
- **What:** a miniature world seen from a fixed 30° angle: buildings, machines, networks, flows between them.
- **Made of:** a light ground, a coordinated palette of 4-6 mid-tones, crisp edges, small labels.
- **Moves like:** elements slide along the grid, flows travel along paths, the camera pans across the system.
- **Best for:** how a system works (a city, a factory, a data pipeline, a supply chain).
- **Avoid when:** the subject has no spatial structure.
- **Sub-registers:** `blueprint`, `bauhaus`, `swiss`.
- **Engine:** HTML/SVG page.

## 8. Paper cut-out and collage
- **What:** handmade: torn and cut paper, duotone photos, tape, grain, slightly imperfect motion; the 2026 return
  to visible craft.
- **Made of:** a paper ground, 3-4 print-like inks, halftone or duotone photography, rough edges, a hand or
  typewriter face for labels.
- **Moves like:** stepped, a little jerky on purpose (12 fps feel for the cut-outs, smooth camera), pieces slide in
  like paper on a table.
- **Best for:** history, culture, human stories, opinion, anything that should feel personal.
- **Avoid when:** precision data or a polished product is the point.
- **Sub-registers:** `risograph`, `memphis` (playful), `manga` (inked).
- **Engine:** HTML page with textures; stepped timing is a choice in the page's time function, not a dropped frame.

## 9. Documentary / archival
- **What:** real photographs, maps and footage carry the story; slow moves on stills, dates and places as titles.
- **Made of:** real images (`imagefetch.py`, the material's own), a restrained serif, a muted grade, film grain.
- **Moves like:** slow push and pan on stills, cross-dissolves between eras, maps that draw routes.
- **Best for:** history, real events and people, places, biography.
- **Avoid when:** there is no real imagery to show; never fake archival material.
- **Sub-registers:** `editorial`, `noir`, `cartographic`.
- **Engine:** HTML page.

## 10. Hand-drawn whiteboard / sketch
- **What:** a line drawn as it is spoken, on white or paper; diagrams appear stroke by stroke.
- **Made of:** a white or paper ground, one ink and one highlight colour, a handwritten-feel face.
- **Moves like:** draw-on strokes timed to the voice; the camera slides to fresh paper for the next idea.
- **Best for:** step-by-step teaching, how-tos, training, calm explanations.
- **Avoid when:** the brand or topic wants energy and polish.
- **Sub-registers:** `swiss` (light), `editorial`.
- **Engine:** HTML/SVG page (path draw-on).

## 11. Retro and subculture registers
- **What:** a bold period or scene look: Memphis (80s playful geometry), risograph zine, synthwave neon, terminal
  CRT, Bauhaus primaries.
- **Made of:** the register's own palette and type (as in `visual-styles.md`), strong texture.
- **Moves like:** the register's own rhythm: Memphis bounces, synthwave glides, terminal types.
- **Best for:** youth and gaming audiences, festivals, developer tools, brands that own that register.
- **Avoid when:** somber subjects, enterprise trust contexts (the vetoes in `visual-styles.md`).
- **Sub-registers:** `memphis`, `risograph`, `vaporwave`, `terminal`, `bauhaus`, `artdeco`.
- **Engine:** HTML page.

## Choosing (a quick map)
| purpose / subject | first looks to try |
|---|---|
| science 科普, nature | 1 flat illustrated · 2 mathematical · 6 lit 3D |
| maths, physics, algorithms | 2 mathematical · 7 isometric · 1 flat illustrated |
| news, data, economics | 3 editorial · 4 kinetic type beats · 9 documentary |
| software launch | 5 product UI · 4 kinetic type · 1 flat illustrated |
| hardware / physical product | 6 lit 3D · 5 product UI |
| history, culture, people | 9 documentary · 8 collage · 3 editorial |
| how-to, training | 10 whiteboard · 7 isometric · 5 product UI |
| youth, gaming, festival, dev tools | 11 retro registers · 4 kinetic type · 8 collage |

Offer looks that are genuinely different from each other (for a 科普 film: 1, 2 and 6, not three palettes of 1).
