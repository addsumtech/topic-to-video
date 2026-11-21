# Promo shotcraft — techniques that make a product film look crafted, and how to apply them

Studied 2026-11-17 from video-shotcraft (github.com/Vincentwei1021/video-shotcraft, Apache-2.0: 124 shot recipes, 150
motion samples, aesthetic rules each backed by a user's ruling). Restated here in this skill's words and adapted to its
engine and checks; no code is copied. Since 2026-11-21 the moves this file describes that matter most (the press, the
in-place dim, become, demote, change, slot/reel, lead word, marker, scan, brackets, lift, type/retype, list, strip,
line carry) are CODE in `assets/html/moments.js` with their tuned starting values (adapted with attribution, NOTICE);
build with those rather than from these descriptions. Use it for launch, promo and product-explainer films (SKILL.md step 6). It is a
vocabulary for judgement (SKILL.md "Design is judgement"): pick what serves the moment, skip the rest.
It is a technique stack, not a taste: knowing these moves lets you execute any idea; which idea the film should be
is yours to find (SKILL.md "You are the film's designer"). The best moments in this skill's films came from no
library — §7.

## 1. What makes these films look premium
- **The product's UI is a physical object in a lit space**, not a flat screenshot on a gradient. Cards and windows have
  thickness, a contact shadow that grows and softens as they lift, a rim or key light; they sit at 3D angles on a
  stage (dark brushed metal, a spotlit table) and the camera moves around them. This one move separates a crafted
  launch film from a slideshow of screens.
- **One light, used with intent.** A spotlight that finds the hero, a single sheen across it once. Light shows only on
  dark: to play with light, go dark first (brightening is invisible on white).
- **Results land as huge numbers** (−41 %, 3.2×, 0.2 s) in the product's type, often inside four corner brackets.
- **The film's look grows from the product's own design system**: its fonts, type scale, spacing, radii, colours and
  materials (read from its site or screens: computed styles via headless Chrome, or measured off the screenshots). A
  technique donates its structure, motion and timing; it is re-skinned in the product's look, never the reverse.

## 2. The method (how techniques get applied well)
1. **List the product's features and map each to one shot.** A core feature with no shot is a hole; two shots telling
   the same thing, one goes. Each shot carries ONE main motion.
2. **Each technique is the star once per film.** A fly-in, a stack, a flip, a crash-zoom: once as the hero move. A
   second use is fine only as background or a quieter variant. At most two kinds of title entrance per film.
3. **Shape the energy:** a low, focused opening (one hero, a complete action arc of ≥3 s: found by light, pushed in,
   lifted, returned) → feature segments alternating with breathing beats → the highest energy at the close.
4. **A motion voice, one per film**, chosen from the brand on two axes, energy (calm/premium ↔ sporty/startup) and tone
   (serious ↔ playful), and used for EVERY entrance, transition and hold. Starting points (30 fps):

   | brand | main move | entrance easing | overshoot | squash |
   |---|---|---|---|---|
   | trusted / enterprise / fintech | ~21 f | cubic-bezier(0,0,0.2,1) | none | 0 |
   | refined / luxury | ~48 f | cubic-bezier(0.4,0,0.6,1) | ≤ 1.02 | 0 |
   | bold / startup / sport | ~18 f | cubic-bezier(0.16,1,0.3,1) | 1.12 | 0.25 |
   | playful / consumer / social | ~27 f | cubic-bezier(0.34,1.56,0.64,1) | 1.08 | 0.18 |
   | calm / health / education | ~42 f | symmetric ease-in-out | none | ≤ 0.04 |
   | friendly / community | ~26 f | cubic-bezier(0.25,0.46,0.45,0.94) | 1.04 | 0.08 |

   Check: three words for the film's motion should match three words for the brand. In this skill a landing
   overshoot must not shrink back past full size on a big element (rewind_qa reads it as the picture going back);
   keep overshoot on small elements, or land with a settle instead.
5. **Holds are designed, and the first cut is always too fast.** A brand wordmark or key number holds ≥1 s still; a
   batch entrance ends with 0.5 s of stillness; a simulated interaction runs at human speed (the viewer could follow
   along). Budget these frames in the plan before animating.
6. **Speed comes from acceleration, not from fast constant motion.** A batch of elements arrives faster and faster
   (dealing cards), ideally behind a physical metaphor, then rests. Nothing important moves linearly, except machines
   (a scan line, a spotlight sweep, a progress fill), which SHOULD move at constant speed so they read as mechanical.
7. **No bare cuts between scenes.** Choose the seam by meaning: the next scene already exists inside this one (a window,
   a letterform, a circle) → travel into it; a handoff → hide the cut in a white flash, a whip-pan blur, a passing
   foreground card, or a light peak; something finishes (a progress bar) → let its line carry the eye into the next
   frame with no cut at all; a chapter change → the new chapter's ground pushes the old one out.
8. **Interactions are causal chains.** Cursor arrives → press (one darker "pressed" frame) → the state changes → a small
   reward appears. Options that are not chosen dim but do not move (moving reads as a page refresh). Typed text comes
   at human pace; a word turning into an object is a 1-frame hard cut ("done"), not a fade.
9. **Text is either read or texture.** Words meant to be read meet the size floor (captions ≥ ~56 px at 1080p, labels
   ≥ ~32 px, measured on the rendered frame including every scale); small UI text not meant to be read is visibly
   softened or dimmed. Nothing in between.
10. **Copy is rewritten against the locked picture**; taglines name a real feature and a concrete benefit, never an
    abstract metaphor; no animated stretch over ~3 s goes without a line (the closing brand frame excepted).
11. **Beat-locked films:** cuts land on beats, but whole-frame hits (frame pulse, shake, flash) at most 3 per film, on
    the strongest hits, 16+ beats apart; other beats move only elements.

## 3. Techniques by the job of the moment
Each: what it says → its critical point. Durations at 30 fps.
**Open (one per film)**
- Spotlight hero: a light finds one card, it lifts with a growing shadow, a rim light traces it, it returns → ONE
  subject, a complete arc, ≥3 s.
- Crane rise: tight on one real data row, the camera rises and pulls back until the whole product fills the frame
  ("this row is one tile of a wall") → never pair with its mirror (dive from overview to detail) in one film.
- Text as mask: a huge word cut out of a clean stage with the live product moving inside it, then the word swells
  and the product takes over the frame → the product inside must really be moving.
- Ink/letter-press wordmark: crosshairs draw, the name stamps in, a subtitle types, ≥1 s still → for brand-first opens.
- Suspense build: the title appears as unreadable stroke segments that complete into the word at the end → use ≤1.

**Say a line (titles and claims)**
- Blur-slide is the default reveal: per word, y-offset, blur and opacity share ONE progress and ONE easing, words
  ~4 f apart. Use it whenever another shot nearby is the star.
- Lead-word zoom: the key word first, huge and still pushing in, then it shrinks into its place as the sentence forms
  → pin the scaling pivot to the word's own centre and baseline, or the baseline jitters.
- Slot cycle ("One tool to ___"): the sentence stem stays pixel-still while a pill or a vertical roll cycles the
  options (neighbours blurred and grey, the landed word takes the accent) → if the stem moves, the list reads as noise.
- Marker underline / circle on the key word: 8-12 frames, hugging the glyphs, following an italic's slant → slower
  reads as a loading bar.
- Typewriter retype: types a plain word, hesitates, deletes it, types the real claim faster.
- A number with its range: a dial sweeps past large values and stops on the small one, which slides into the headline
  as its first character.
- Title demotes to label: the big title shrinks into a corner and becomes the section's label (free spatial memory) — for that section only, then it goes; never a running label over the film.

**Show the product (screens and content)**
- Real screens, captured at 2x (`capture_page.py`, `promo_capture.py`), as physical cards (section 1).
- A wall of content either SURGES in (cards dealt, accelerating, into a running grid: volume) or LIGHTS UP in place
  (cells or a blueprint line revealing in sequence: dignity, process). Decide which the moment means.
- Lists: items land one by one while the whole container drifts slowly, so no frame is dead between items.
- A stack, then a fan: first one heavy pile (quantity), then it spreads (variety).
- Fly-ins land in REAL layout slots and stay there; nothing is left hovering above a page.
- Hovering elements cast a matching soft shadow that shrinks as they land; without it the depth does not read.
- A detail card assembles field by field ahead of a "fill cursor"; one field CHANGES (a price struck through, a new
  value springing in): the only semantic event, placed mid-shot.
- Source stays visible: a document parks to the left and keeps scrolling while conclusions are dealt on the right.

**Demonstrate a feature**
- Cursor tour: from an overview the camera flies to each area in turn, the cursor arriving first and clicking with
  a ripple; one continuous move, so the areas' positions are learned too.
- Type and filter at human speed; the grid converges to one card; a click goes through to its detail.
- Single select: press frame, then the chosen chip turns solid; others dim to ~20 % without moving.
- Mode switch: an oversized segmented control as the whole shot; cursor, press, thumb slides ~8 f, new icon pops.
- Before / after: the slider flings fast (announces the change) then sweeps slowly (proves where).
- Machine reading: a scan line moves at constant speed; each region is bracketed and labelled only AFTER it passes.
- Many sources → one: sources draw curves to one point, slide along them and are swallowed, the curves erase back.

**Camera**
- Crash-zoom (6 f, from wide to the target, then a hard or elastic stop) means "look at THIS"; a slow push means
  "please look". Hold ≥1 s before (establish) and after (read).
- Depth layers: three speeds of parallax under a lateral move; the hero lifts when the move settles.
- Graze tour: a low, steep angle skimming the UI as landscape; text hovers above it with shadows and lands as the
  camera passes.
- Steep-tilt glide: the camera stays still at a 60° angle and the PAGE slides past it.
- Big spatial moves (exploded view, dive from overview) at most 2 per film; emotional moves (freeze-orbit,
  pull-back isolation) at most once each. Information-dense shots are framed straight on; a tilt needs a reason.

**Data and results**
- Card flip: a feature card flips to its result (the big number) on its back; a row flips in sequence ~10 f apart.
- Gauge self-test: needles sweep the full arc, then settle on the true values; or a tape scrolls past a fixed needle.
- Axis rescale: a new value breaks the chart's ceiling, pauses, the axis rescales and the old line flattens.
- Scroll brake: a year of changes blurs past and brakes exactly on today's release, which lifts; the rest dims.

**Emphasis (sparingly)**
- Four corner brackets fly in and lock onto the target with a small overshoot: "look here" without freezing.
- One sheen across the hero card, once, clipped to its rounded corners; never a glint on every card.
- Impact ladder for a landing: a few frames' hold with a number (lightest) → shockwave pushing neighbours → a
  3-frame impact frame (heaviest, most stylised). Pick by how hard the moment should hit.
- A key word charged by a fast light sweep (15-20 f, brightest at the wave front), then breathing.

**Rhythm**
- Hard-cut bursts as percussion: three white-flash cuts on one subject (wide → card → detail), intervals tightening,
  then a LONGER hold than usual.
- Freeze and annotate: the flow stops, a marker circles the point, the flow resumes.
- Cold-open hook: three of the best shots cut fast (~9 f each), one beat of black, then the title.
- Theme-cycle on the beat: the list steps, the centre pill recolours and the ground changes on the same frame.

**Close (the energy peak, the brand holds ≥1 s)**
- Group photo: one element from every feature shown flies in around the wordmark (addition: "all one product").
- Strip-away: after the final click the UI evaporates from the edges inward, layer by layer; the clicked button alone
  travels to the centre and hands off to the wordmark (subtraction: "complexity gone").
- UI becomes brand: the input box or icon used all film morphs into the logo ("what you used IS the brand").

## 4. Sound for product films
- **Film-type vocabulary**: whoosh (camera moves), impact (landings), riser (build-ups), sparkle (light), transition
  sounds; under a strong, rhythmic electronic bed. Visible actions get REAL foley (a shutter click, keys, paper,
  glass) cut to the action's length. No game-feedback timbres (cartoon bloops, synth confirmation tones): the
  bundled `assets/sfx/kenney/` UI sounds are of that family, so prefer real-world takes for a product film.
- **Rapid-fire runs** (six cards landing): alternate two samples, step the volume down along the run, tighten the
  intervals with the motion; never the same sample at the same level repeated.
- **Sound after picture lock**; any timing change re-pins every cue.
- **Measure the A/V offset of the pipeline** (encoder priming makes the audio lag by about a frame); compensate in one
  place, not per cue.

## 5. Building these in this skill's engine
- 3D UI in a page: CSS `perspective` on the stage, `transform: rotateX/rotateY/translateZ` per card, a contact shadow
  whose blur and size follow the card's height, a rim light as an inset gradient. Use the 2x captures; for close
  pushes, give the hero a separate higher-resolution capture and scale it DOWN. Do not animate CSS `zoom` per frame
  (in this skill's capture it re-lays out text and makes pictures step; picture_glide_qa catches it).
- Deterministic everything (seeded randomness, pure functions of time): `assets/html/accents.js` has `blurSlide`
  (the default reveal) and `dealTimes` (an accelerating batch schedule ending in a rest), next to the accents.
- For lit 3D of a physical product, `scripts/blender_clip.py` (devices: `laptop_screen`).

## 6. Craft review before delivery (look at the frames, answer each with evidence)
- Every feature in the plan is on screen, each in its own shot; no two shots say the same thing.
- The opening is one hero with a complete arc (≥3 s); the close is the energy peak and the brand holds ≥1 s still.
- Each technique stars once; the motion voice is one voice (three words for the motion match three for the brand).
- Pause on any frame of a feature shot: is the UI an object in a lit space, or a flat screenshot on a gradient?
- Every scene change is carried or hidden (`seam_qa` agrees with the plan); hard cuts are beat-cuts, match cuts or UI
  states by design.
- Holds: the key number, the claim and the wordmark each sit still long enough to read twice; batches rest at the end.
- Text: captions pass `caption_size_qa`; every word meant to be read reads at phone size; texture text is softened.
- Light: at most one sheen or glint per shot, on the hero, clipped to its corners.
- Sound: film vocabulary and real foley, cut to each action; no game tones; nothing out of sync at a cut.
- Copy: every line names a real feature or a concrete benefit and matches its picture.
- The signature idea lands: the moment a viewer would describe to a friend.

## 7. Our own way: craft that is also true
video-shotcraft makes product films beautiful; this skill's films are beautiful and true, and that is where its
signature moments come from. Bring both.
- **Motion that is the evidence.** Choose the move by the claim, then build it from the real thing: the diamond's fire
  rendered at its real red, green and blue refractive indices; the sky computed by the scattering law the film
  explains; the QR code that viewers can scan, decoded on the film's own frames; real numbers counting to their sourced
  values. A technique borrowed from a library becomes ours when the content drives it.
- **Cut to meaning, voice first.** The narration's timeline is the clock: a technique lands on the word it proves. A
  scored promo also lands its big moments on the beat, but never at the cost of the sentence.
- **Physical truth in 3D.** Real light, material and optics from Blender where physicality is the content
  (`scripts/blender_clip.py`); devices that show the product's real screen.
- **Sourced, never invented.** The product's own docs and screens for a product film; research with captured sources
  for an explainer; a number on screen is a claim.
- **Measured, not eyeballed.** Flash, rewind, glide, empty frames, shake, caption size, seams and the plan are checked
  on the pixels; a disputed red is proved with a control, never silenced.
- **Invent past the library.** Read the subject until a move appears that belongs only to it: a torn QR corner
  scattering as codewords, a lens's rays fanning from the candle, the prompt line dealing out the files. One such idea
  per film is the signature (SKILL.md); everything else serves it.

