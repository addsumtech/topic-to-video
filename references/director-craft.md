# Director craft — the principles behind a film that reads as made, not assembled

The director path's working knowledge, condensed from the established canon of editing, explainer teaching, graphic
design and motion. Each principle says what usually works and why; they are defaults for judgement, not laws
(SKILL.md "Design is judgement, not a menu"): break one when the film is better for it, and say why in NOTES.md.
Where this skill measured something itself, it says so.
Deeper skill-specific studies: `motion-grammar.md` (camera and transition grammar), `launch-film-study.md` (20
official product films, measured), `craft-standard.md` (the product-film grammar), `narration-writing.md` and
`anti-ai-voice.md` (the spoken script), `visual-styles.md` (the named looks).

## 1. Editing — the cut serves the viewer's mind
- **Priority when rules conflict** (Walter Murch, *In the Blink of an Eye*, "rule of six"): emotion first, then story,
  then rhythm, then eye-trace, then the 2D plane, then 3D continuity. A cut that keeps the idea flowing beats a cut
  that is merely tidy.
- **Cut on the voice.** The narration is the A-roll; pictures are cut to it. A picture change lands a few frames
  BEFORE the word it illustrates (~0.1-0.2 s), never after: the eye arrives first, the ear confirms.
- **J and L cuts.** Let the next idea's voice start under the current picture (J), or let a picture hold while the
  voice moves on (L). Hard cuts exactly on sentence boundaries everywhere read mechanical.
- **Vary shot length.** A film of identical 4-second shots is a slideshow. Short shots (1-2 s) accelerate a list
  or a montage; a long hold (5-8 s) lets a key image land. The climax gets the longest hold of the act.
- **Sequences, not slides.** Group 3-6 shots into a sequence that keeps ONE world: the same subject, the same
  camera language, the same ground. Change the world only at a section seam, and make that change felt (a
  colour shift, a pull-back, a beat of silence).
- **Match the cut.** Carry a shape, position or motion across a cut (the QR code shrinks into the next shot's
  corner; the file card the voice names is the card that fills). Continuity of the SUBJECT is what makes a film
  feel like one thing; this is the single largest difference the 2026-11-16 blind tests showed.
- **Eye-trace.** Put the next shot's focal point where the eye already is, or move it there on purpose.
- **Breathe at seams.** A short pause in the voice (0.3-0.6 s) at a section change, with the picture settling,
  is how a viewer knows a part has ended.

## 2. Teaching — how people learn from narrated pictures (Mayer, *Multimedia Learning*)
- **Coherence:** cut every picture, word and sound that does not serve the point. Decoration costs understanding.
- **Signalling:** show the viewer where to look: highlight, arrow, isolate, dim the rest, at the moment it is said.
- **Redundancy:** do not print the narration on screen as body text; on-screen words are labels, numbers and
  keywords. Captions are the only full text, and they sit in their own band.
- **Spatial contiguity:** a label sits ON or next to the thing it names, never in a legend across the frame.
- **Temporal contiguity:** a picture appears WHILE its words are spoken, not a sentence earlier or later.
- **Segmenting:** one idea per shot; a complex process is shown in steps the viewer can follow one at a time.
- **Pre-training:** name the parts before the process that uses them (the finder squares before "finding").
- **Concrete first:** a real example (one real code, one real task, one real number) before the abstraction.
- **Voice:** a natural human-sounding voice, conversational ("you"), not a lecture.

## 3. Design — one look, held
- **One look per film.** Choose a named style from `visual-styles.md` (its selection rules and vetoes apply) and
  hold its palette, type and surface from the first frame to the last. Variety comes from composition and
  scale, never from changing the look.
- **Hierarchy:** one focal point per frame, then at most two supporting levels. Achieve it with size, contrast and
  position before colour. Squint test: blur the frame; the focal point must still win.
- **Colour:** a neutral ground, ink, and ONE accent that means "what the voice is pointing at". A second accent
  only for a real second meaning (good vs bad). Colour carries meaning across the whole film: the same thing is
  the same colour every time.
- **Type:** one or two families; three or four sizes in a clear ratio; lining figures for numbers; short lines.
  Text in a video is read in the time it is on screen: under ~7 words per label, and on screen long enough to
  read twice.
- **Grid and margins:** a consistent grid and generous margins (title-safe ~5-10 % from each edge); keep the
  caption band clear of pictures. Alignment is what makes a frame look designed.
- **Gestalt:** proximity groups, similarity relates, a shared region binds. Use them instead of boxes and lines.
- **White space is a choice.** A sparse frame is strong when its one object is the point; a frame left nearly
  empty while the voice goes on is a hole (`empty_frame_qa` reports holds of 1 s or more).
- **Show the thing itself:** the product's real screens, the real object, the mechanism drawn correctly. Never
  draw a raster beyond its native pixels; a real screenshot is cropped and pushed within its density.
- **Light, material and depth** belong to the look, not to one shot: if the film is lit, every shot shares one
  light direction and one material language (the kit: section 6 of SKILL.md).

## 4. Motion — physics the eye believes
- **Easing:** nothing starts or stops at full speed. Entrances decelerate (ease-out), exits accelerate (ease-in),
  moves between states ease in-out. Linear motion only for continuous processes (a conveyor, a scan line).
- **Durations:** small UI-scale changes 0.2-0.4 s; an element entering 0.4-0.8 s; a camera move 1-3 s. Faster
  reads nervous, slower reads sluggish.
- **Stagger** related elements by ~0.05-0.12 s so a group reads as a group arriving, not a block appearing.
- **Anticipation and settle** (the Disney principles that transfer): a small wind-up before a big move, a slight
  overshoot and settle at the end. Use sparingly; on every element it reads cartoonish.
- **Motion has a job:** reveal, connect, compare, transform or direct attention. Motion for its own sake (a
  constant drift, a wobble) is noise, and on fine detail it shimmers (`picture_glide_qa` catches it).
- **Time runs one way.** A state that was reached stays reached unless the story undoes it; a picture that jumps
  back after a cut reads as a mistake (`rewind_qa`).
- **Camera:** a push-in to focus, a pull-out to give context, a pan to follow a process. One camera language per
  sequence.

### Accents (moved here verbatim from SKILL.md, 2026-11-18)
**Accents** — small motion effects that make a moment FELT, drawn as motion, not as emoji glyphs. Where they
go is your judgement, not a mapping: find the moments the viewer should feel something — an answer landing, a
reveal, a turn in the argument, a number that surprises, the product finishing the job, a joke, the payoff — and
design the motion that fits that moment, subject and look: a burst of confetti with a ring and rays, a sparkle, a
glow pulse, a shockwave, a stroke drawing itself, a number counting up, a short pop-up caption phrase popping in, or one built
from the subject itself (a torn QR corner scattering as fragments). No effect belongs to a particular element.
Under a second, trailing what it marks; sparing (roughly one per 15-30 s in an explainer, more in a playful or
launch film, none on a somber subject); energy matched to the look; drawn BEHIND what it celebrates so its text
stays readable. `assets/html/accents.js` gives them as pure functions of time, with no overshoot.

## 5. Sound
- **Voice is king:** the mix serves intelligibility. Music sits ~18-24 dB under the voice and ducks while it speaks.
- **Music follows purpose:** an explainer can do without; a launch or promo film is scored, and its hits land on
  cuts. A track that fights the voice is worse than none.
- **SFX are punctuation:** a few, on real events (a tear, a click, a card landing, the final lockup), short and
  high-passed so they do not mask speech. Not every cut gets a sound.
- **Silence** before the payoff line makes it land.

## 6. Structure — what every short film needs
- **Hook in the first 3-5 s:** a question, a surprising demonstration, or a tension the viewer wants resolved.
  Show it; do not announce it.
- **One message.** Every sequence serves `the_one_thing` from the brief; anything that does not is cut.
- **Arc:** hook, setup, build (each step earns the next), payoff (the climax ~75-80 % through), a short ending
  that restates the one thing in new words, or for a launch, a call to action and the brand.
- **Concrete stakes:** why the viewer should care, said early and paid off at the end.
