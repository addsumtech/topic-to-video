# Craft study — what 26 published brand films do, measured against ours (2026-11-10)

The user's verdict on our Remotion films was "差点意思" — close, not there. Instead of guessing, 26 official films were
downloaded from the brands' own channels and decomposed shot by shot (each shot's early and late frame side by side),
then measured with ONE instrument together with four of our films (fridge, keyboard, ANC, WorkBuddy). Read this before
designing a film's shots: it says which differences are real (measured), which are seen but not measured, and which
impressions turned out wrong.

**Corpus.** Teenage Engineering (OP–1 field, OP–XY, OB–4, OP–1 field overview) · Bang & Olufsen (Beosound Theatre,
Beolab 90, Theatre acoustics) · Nothing (Phone (3), Phone (3a) series, Ear (open)) · Apple (AirPods Pro 3, iPhone Air,
MacBook Pro, Watch Series 11, HomePod mini 2) · Dyson (V15 Detect, Flyaway) · Beolab 28 ×2 and TE field system / TP-7 (added 2026-11-11) · Linear Agent · Arc 1.0 · Raycast 2026 ·
Notion 3.0 · Framer 3.0 · OpenAI GPT-5 · Stripe Sessions 2024 · Kurzgesagt "How small is an atom". The videos and
frames stay on the machine that studied them (third-party work); this page keeps only what was learned.

**Evidence tags.** **[M]** measured and separates ours from theirs · **[O]** observed on the shot sheets, not measured ·
**[–]** measured and does NOT separate (a wrong impression, dropped).

## P0 · Surfaces are lit, not filled — the gap the eye sees first [M, added 2026-11-11]
The user's verdict after the first round ("设计上和之前没有太大区别") was right, and the phase-1 instrument had missed
it: tonal key measures the whole frame, not whether the SUBJECT is a surface the light has modelled. Measured with
one instrument (`craft_study/tools/surface.py`: a region of the subject whose luminance ramps >= 25 inside it counts
as modelled; a frame is LIT when such regions cover >= 5 % of it):
- **lit frames** — TE field system (TP-7) 0.87, B&O 0.70–0.87, Dyson 0.85–0.92, Nothing 0.58–0.90, Apple iPhone Air / MacBook Pro / Watch
  0.59–0.73, Raycast 0.89, Framer 0.70 · **ours: ANC 0.27, fridge 0.29, keyboard 0.25, WorkBuddy 0.10**.
- What does NOT separate: flat-graphic registers are flat by design — Kurzgesagt 0.22, Notion 0.00, Linear 0.00; and
  restraint films that live in black (OP–XY 0.23, OB–4 0.17) carry their form in tiny highlights instead.
  So this is a gap only where the subject is a PHYSICAL object (a product, a machine, a part).
- What closes it, tested (2026-11-11, ANC earbud plate): the same Blender model, the same camera — with
  `blender/kit/materials.py` finishes (gloss_plastic shell, silicone tip, brushed_steel cell, anodized_alu magnet)
  and `blender/kit/studio.product_light` (HDRI mirrored by gloss, broad key, two tall strip lights behind, an
  overhead strip) — went from a clay model to a product render. What did NOT close it: finishes painted onto 2D
  vector diagrams (`runtime/solid.ts`) — on the fridge's flow diagram the change was invisible beside the glowing
  refrigerant, on the earbud section modest. A diagram stays a diagram; a physical hero wants a rendered object.
→ For a physical subject, the hero beats are a Blender plate under `product_light` with each part's finish named
  (see "Design intelligence" below); 2D parts that remain take `runtime/solid` finishes so the film's objects share
  one lamp and one material vocabulary.

## Design intelligence — what the guide's design sources say, made usable [O + sources]
The guide asks for five lenses on every reference (form, material, craft, philosophy, presentation). Per brand, from
the films' own frames:
| | Form language | Material | Craft (made how) | Philosophy | Presentation |
|---|---|---|---|---|---|
| Teenage Engineering | rectilinear slabs with generous radii, ~30° diagonal in frame; round keys on a strict grid; tiny type as ornament | white/alu tone-on-tone, bead-blasted anodised grey (TP-7 field system); ONE accent per product (a red LED, orange caps) | machined chamfers, engraved legends, woven mesh grilles, visible Torx screws | function shown, playful restraint | macro fragments, whole only at the end; type alternates with product |
| B&O | lamellas, cylinders, one sculptural gesture | oak against aluminium against fabric; one warm element in a cool world | grinding, polishing, anodising shown as the story | material honesty, longevity | low key, raking light, violet cloth as the medium of sound |
| Nothing | transparent back showing the organised inside; dot-matrix glyph | clear polycarbonate over parts; LED light | internals laid out as a composition | the inside is the design | product's own light does the telling; diptych light/dark |
| Apple | one continuous form (unibody), edge-on thinness | anodised/titanium, glass; white gloss plastic | invisible seams, every edge finished | care, "as little design as possible" | white or black void, edge light, product huge in frame |
| Dyson | engineered parts on show (cyclones, translucent bin) | translucent coloured polycarbonate, nickel, gold anodised | cutaway of the real mechanism | engineering as the aesthetic | macro dive into the microscopic, data on the product's own screen |

Round 5 (2026-11-11, the guide's remaining sources): TE EP–40 names each feature by freezing the hands into a
two-tone still in the product's OWN colours with a hand-lettered label ("DUB SIREN"); TE EP–1320 builds a whole world
and shows the product last, small, on an altar; TE's ten years of PO ties B&W footage, cut-out product and doodles
with one flat palette; Herman Miller × Fukasawa tells material by CMF SAMPLES in macro (fabric layers edge-on, chips
fanned in a hand); NPD lays the finish trials out in a row as the process made visible.

Principles distilled for a film's OBJECTS (sources below):
- **Proportion before polish** (Eric Strebel): an object reads as designed when its masses rank — one DOMINANT, one
  SUB-DOMINANT, one SUBORDINATE — never two equal masses fighting; their axes give the eye a path ("gesture"); a cube
  is the dull extreme. Check a drawn object's three biggest parts for that ranking.
- **Every part has a finish and a process** (Strebel's "design guide": material, thickness, finish, how it is made,
  corners softened). Name each part's finish (`materials.FINISHES` / `solid.FINISHES`) before drawing it; a part
  without one is drawn as a fill.
- **Minimalism needs perfect execution** (Design Theory on Rams): with few elements every detail is under a spotlight
  — "simple and elegant versus boring and basic". Our frames were minimal in COUNT but basic in EXECUTION.
- **Rams' ten principles** (Vitsœ): innovative, useful, aesthetic, understandable, unobtrusive, honest, long-lasting,
  thorough down to the last detail, environmentally friendly, as little design as possible. For a film: honest =
  the object's real parts and real finish; thorough = chamfers, seams, the reflection on the back side too.
- **Fukasawa's "without thought" / Super Normal**: the ordinary object, quietly right; no decoration that the object
  would not have. **Ive**: "the most important thing is that you actually care"; materials are a big part of the
  experience of an object (Core77).
- **Simplicity is not removing clutter; care reaches the inside** (Ive, Stripe 2024): removing clutter alone gives
  "an uncluttered but desiccated, soulless product"; people sense care through an object, and he "felt passionately
  about finishing the inside of products". In a CUTAWAY or EXPLODED film the inside IS the product on screen — an
  internal part drawn as a placeholder (a flat board, a grey block) is the unfinished inside.
- **The parting line is designed, not hidden** (Fukasawa on Asari: "two shells … one parting line, that's a strong
  feature"); **the outline comes from the medium** (Fukasawa, MUJI talk: "the outline of the surrounding medium rather
  than the outline of the thing" — show an object with what surrounds it and the behaviour around it).
- **One central idea decides everything, down to the reveal's tempo** (NPD, Zebel: "tech that doesn't feel like
  tech" chose the finish trials, the display that appears on a tap, and packaging that "comes up very slowly … a
  calming product"). A film's tempo of reveal belongs to the product's character, not to a house rhythm.
- **The light moves on a still object** (B&O raking light along the lamellas, Apple's strip reflections sliding down
  an edge): a travelling highlight is what reads as a hard, finished surface; a still render never shows one.
  `kit.studio.turn_light` swings the product studio per frame with the camera fixed, so a registered plate stays
  registered (fridge film, 2026-11-11).
- **Character and universe** (Sam Does Design): a design is given a character (joyful, rugged, wise) and its parts
  belong to one universe; a film's objects must all come from the same one (the same lamp, the same finishes).

## What did not separate us [–]
- **Tonal key.** Ours are high-key (highlight share 0.58–0.87) like Apple, Notion and Kurzgesagt; the fridge film is
  low-key like B&O. "Our films look grey and flat" was an impression the pixels did not support.
- Colourfulness, the spread of luminance across shots, the change inside a shot: overlapping ranges.
- Bookends: ours already close on their opening image, as MacBook Pro (its "V" of light) and Watch (the headline) do.

## P1 · Rhythm has contrast — bursts and holds [M]
p90/p10 of shot lengths: **ours 1.6–1.9**, every reference with cuts **2.7–37** (most 4–8). Shots under 1.5 s: **ours
0 %**, theirs 7–68 %. Nothing (3) accelerates 1.3 → 0.6 s into its climax and releases on a 3.5 s wide; MacBook Pro cuts
its UI demos at 0.9–1.5 s and holds hero + type for 7–9 s; Arc cuts archival "1.0s" at 0.7 s between 1.2 s word cards.
**Why ours was a metronome:** one beat = one sentence = one shot, and nothing cut inside a beat.
→ **coverage** (`scripts/coverage_plan.py`, `runtime/coverage.tsx`): a beat is cut between framings on its voice — a
listed item the voice names gets a close-up, a long beat a punch-in on a clause — and `scripts/cut_rhythm_qa.py`
reports the delivered film's numbers beside this band.

## P2 · Scale has range; fragments come before the whole [M on explainers, O on product films]
Foreground share p90−p10: ANC 0.19, fridge 0.18, keyboard 0.26 against Kurzgesagt 0.51 and the product films 0.45–0.68;
a big subject running off two or more edges: ours 0–0.21, hardware films 0.2–0.82. TE shows keycap, chamfer, port and
engraving in macro and the whole product only at the end; B&O keeps the Theatre mostly in shadow, lamellas in raking
light, and gives the room at 26 s; OP–XY is black on black, its form only rim and pin highlights.
→ coverage's item close-ups end on the WHOLE; on a hero object, plan the reveal fragments-first (`hero_moments`:
`macro` before `reveal`/`context`); `shot_fit.composition` should range from `macro` to `wide` across the film.

## P3 · Type is designed, not appended [O]
Type and product take turns rather than share a frame (TE, iPhone Air, Watch, HomePod, Arc). Text builds in place
("thinner," → "thinner, louder, better."; "Knows you by" → "Knows you by heart"); key words dark or coloured, the rest
grey; the scale goes to extremes — TE at ~2 % of the frame height in a sea of white, Notion's prompt at ~25 % with the
camera on the caret; the device can sit inside the sentence ("for smarter [phone] group selfies").
→ a **type beat as punctuation** between subject beats: `HeadlineReveal` (`reveal: "word"`, `*emphasis*` for the dark
words, `size: "whisper"` for one quiet line in a sea of ground), `MagicMoveType` for a phrase that becomes the next.
When the headline IS the spoken line the burned caption yields to it (`captionOnScreen`; out.srt keeps the line).

## P4 · One signature material makes the invisible visible — and carries the film [O]
AirPods Pro 3: sound = refractive glass rings with spectral edges around black silhouettes. B&O Theatre: sound = violet
cloth; an eye morphs into a cloth canyon and the cloth carries every transition. Framer 3.0: "new" = refractive light
ribbons that carry the words. Dyson V15: the green laser reveals the dust and leads into the microscopic world.
Kurzgesagt: a multitude = a particle field. One material per film, recurring, and the medium of its transitions.
Ours: ANC's particle field (good, never a transition), fridge's thermal false colour (a good signature), WorkBuddy's
blank paper cards (weak, unnamed).
→ `meta.signature_material = {name, shows, beats}` (validate asks for one on a film of 8+ beats); derive it from the
subject (a satellite's is not a forest); let a seam carry it (`optic: leak`, `runtime/material` grounds, a `container`
seam on it).

## P5 · An interface is a lit object in space, not a screenshot [O]
Linear Agent: one 45 s glide over the real UI laid on a tilted plane, falloff into darkness, focus where the action is,
no cut and no overlay. Raycast: one component per shot, oversized and cropped off the edge, shallow depth of field,
satin abstract ground. Framer: UI parts lifted out and glowing. Nothing (3a): the UI full-screen in the phone, then its
elements leave the device and float beside it. Notion: the app window inset on a saturated brand matte. Ours
(WorkBuddy): flat front-on windows at medium scale on light grey.
→ the tools exist — reach for them: `surface3d` (`View`/`Slab`: the UI ON a tilted surface, sharing its vanishing
point), `lighting` (`keyFalloff` as the light pool over that surface), `focus` (`focusAt`/`focusFilter`: blur and dim
by distance from the action), FilmScreen `focusTrack` (the close-up that follows the action), `stage3d` (panels the
camera flies between). Three recipes:
  1. **Tilted plane** — the real UI on a `Slab` at 18–28°, a `keyFalloff` pool on the action, the far edge falling to
     the ground; the camera glides on the action, nothing overlaid.
  2. **Oversized component** — one component at 2–3× its UI size, cropped by the frame, everything but its active
     part through `focusFilter`; one feature per shot.
  3. **Lift-out** — the element the voice names rises off the window (`carry` anchor) and floats beside it.
  Two things the WorkBuddy redesign (2026-11-10) learned the hard way: a lit staging moves the beat onto a DARK ground,
  and a shot's ground is its static `GROUND` export (the caption's ink and the seams read it, and a register that does
  not follow `slide.ground` refuses one) — so give the lit staging its own film-local shot that declares the night
  ground and renders the window with the staging; and a beat that already frames one component oversized sets
  `"coverage": false`, or the punch-in lands on a close-up.

## P6 · The product's own signature element does the telling [O]
Nothing's Glyph Matrix plays spin-the-bottle; Dyson draws the data on its own screen, not as an overlay; HomePod mini
seen from above becomes coloured dots that choreograph; the Watch's own face is the feature card.
→ before drawing a chart over a device, ask whether the device can show it (`DeviceDemo` screens, an object's own
readout).

## P7 · Restraint [O]
One line of type and one to three objects per frame (HomePod, TE, iPhone Air); one warm element in a cool world (B&O's
oak in violet); the brand colour as LIGHT, not as boxes (Stripe, Framer).

## P8 · Objects are built like products — form, material, craft [O + earlier M]
Edges catch light: chamfers and pin highlights (OP–XY's keys), the lid's edge light (MacBook Pro), brushed aluminium in
every Beolab 90 frame; materials contrast (aluminium + wood, glass + fabric). Lighting practice (tutorial sources, not
studio disclosures): a rim/back light separates the silhouette, a gradient sweep is a soft light falling off across
the surface, hard-edged highlights show which surfaces are polished and which matte. Measured earlier
(`craft-bar.md`): ANC's Blender earbud highlight 0.04–0.13 — matte, unlit plastic.
→ `blender/kit/stage.py product_rig` (three-point, rim linked to the subject), `runtime/lighting` (rim, key falloff,
contact shadow), `subject_craft_qa.py` (light range, rim separation, highlight on the settled hero frame). An object
the film draws should have: a chamfer or edge that catches a highlight, a seam where its parts meet, at least two
materials that differ in roughness.

## P9 · Explanation runs on continuity [O]
Kurzgesagt: five minutes without a cut — scale journeys and morphs (fist → marble → atom), an object becoming the
container of the next scene; a fixed chapter tab and tag-chip labels. Linear / TE overview: one locked or gliding take
in which the product's own state is the animation. → `WorldStage` (scale-zoom between named framings), stage runs,
anchored seams — capability the library has; the gap was reaching for it.

## Sources (web — used only where noted; the films themselves are the primary source)
- Dieter Rams, ten principles for good design — https://www.vitsoe.com/gb/about/good-design
- Naoto Fukasawa, "without thought" / Super Normal — https://en.wikipedia.org/wiki/Naoto_Fukasawa
- Jony Ive on care and materials — https://appleinsider.com/articles/13/10/10/apples-jony-ive-on-design-the-most-important-thing-is-that-you-care ;
  https://core77.com/posts/22519/Jonathan-Ive-Talks-Design
- Eric Strebel, "Understanding Basic PROPORTIONS" (YouTube 05noF6uuzK8), "Sketch to Functional Prototype" (xnLTS6vjkoY),
  "Why you need a Design Guide to manufacture a product" (0DR8MN7uKZo) — transcripts read 2026-11-11
- Design Theory, "Minimalism is Getting Absurd: Updating Dieter Rams' 10 Principles" (p5InhRf2JrU)
- Sam Does Design, "What do Industrial Designers Actually Do?" (2e7DSZzKK0A)
- B&O Beolab 28 official films (YouTube bZ60CQ43OuE, AF35ExsNOOE) — the ManvsMachine cut the guide names is on Vimeo
  behind a login and was not used
- B&O Beolab 28 brand film, "inside out" approach — https://www.stashmedia.tv/?p=79583
- Product lighting practice (rim, gradient falloff, hard-edged highlights) —
  https://petapixel.com/how-to-create-gradients-of-light-product-photography/ ;
  https://lightmap.co.uk/learning/easy-product-lighting-tutorial
- Linear reels: one job per reel, minimal narration — https://www.moonb.io/blog/product-launch-video
