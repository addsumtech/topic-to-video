# Director toolbox — the commands and kit behind SKILL.md's director path

SKILL.md says WHAT to do at each step; this file says HOW, with the exact commands. Everything here works in a
director-path film folder (no storyboard) and was verified there on 2026-11-17. None of it is required: it is the
vocabulary SKILL.md's "Design is judgement" refers to. The classic version's other tools are in
`pipeline-scripts.md` (any that takes a film folder or an mp4 is usable here too).

## Material (step 2)
- **A deck, PDF or image folder as source material:** `python3 scripts/ingest.py <deck> <film_dir>/deck` renders every
  page to `deck/frames/` and pulls its text and speaker notes into `deck/storyboard.json` (reading material only).
  Its figures and screenshots can appear in the film.
- **A real product page:** `python3 scripts/promo_capture.py <film_dir> <url> --name=<n>` and
  `python3 scripts/capture_page.py <page.html|url> --name <n>` capture at 2x.
- **A real, licensed image of a named subject:** `python3 scripts/imagefetch.py "<query>" out.jpg` (Wikimedia Commons,
  with its credit).

## Writing (step 3)
- `agents/scriptwriter.md` can draft the narration from the plan; one round of `agents/critic-narrative.md` on the draft
  catches what the ear misses. `references/narration-writing.md`, `references/anti-ai-voice.md`.
- `python3 scripts/pace.py --budget <seconds> --lang <lang>`: how much narration a span holds.

## Voice (step 4)
`python3 scripts/say.py --lines script.txt --out-dir <film_dir>/voice --voice edge:zh-CN-YunxiNeural [--speed 1.08]
[--lexicon lexicon.json]` (one line: `say.py "…" --out l01.mp3`). It runs the skill's voice layer (`tts.speak`):
- per-word timings in `<clip>.words.json`, in the WRITTEN words (the caption's spelling);
- a pronunciation lexicon `{written: spoken}` applied for the voice only (多音字, brand names, a misread term);
- initialisms spelled for a Chinese voice (AI as A-I);
- engines: `edge:<id>` (free), `minimax:<id>` / `openai:<id>` only with the user's own key, `say:<name>` offline;
- a transient edge failure retried; any other failure stops with its reason (never a silent different voice).

Voices: zh `zh-CN-YunxiNeural` / `zh-CN-XiaoxiaoNeural`; en `en-US-AndrewMultilingualNeural` /
`en-US-AvaMultilingualNeural` (`references/tts-voices.md`). A misreading is fixed in the lexicon, never in the caption.
Editing the clips: trim leading/trailing silence, cap pauses inside a line (~0.25 s), a longer breath (0.4-0.6 s) at
each sequence seam; no clipping, even loudness across lines.

## Look (step 5)
- `references/video-looks.md` (11 looks, a vocabulary) and `references/visual-styles.md` (palette and type
  sub-registers, with the vetoes).
- `python3 scripts/theme.py <film_dir> --style <key>` writes `theme.css`: the style's contrast-safe palette and type as
  CSS variables; `assets/html/base.css` is a typeset base that reads them.

## Building (step 6)
**Pages.** One `film.html`, every frame a pure function of time (`window.seek(t)`), captured with headless Chrome.
Icons: `references/icons.md` (one inline-SVG line family, Lucide). Captions: `python3 scripts/caption_words.py "…"`
shows where a CJK caption may break.

**Light, material, depth.** In Remotion: `runtime/material`, the lit stage, the craft kit's `surface`, `slide.optic`
(`references/building-blocks.md`). A lit film keeps one light direction and one material language throughout.

**Real 3D (Blender)** for what 3D physicality IS the content of (a real object, a material, optics, physics, a device).
Write a scene script in the plate API (`build(k)` / `pose(k, t)`, `references/blender-plates.md` "The scene-script
API"), using the kit: `studio.world` (the HDRI), `studio.softboxes(<position>)`, `studio.tune_cycles`, `stage.place`,
`materials`. Look at one frame first, then render the clip:

    python3 scripts/blender_clip.py <film_dir> scene.py --seconds S --still F            # one frame to look at
    python3 scripts/blender_clip.py <film_dir> scene.py --seconds S --engine cycles      # alpha PNGs + preview mp4

Output: `<film_dir>/clips/<name>/rgba/NNNN.png` (alpha, or opaque with `--env`) and `<name>.mp4`. Glass, gems, water
and metal show only what they refract or mirror: render them in Cycles with the kit's HDRI and soft boxes. In EEVEE
with no world a diamond came out flat grey; with them, a believable stone at 10 s a frame (640x360).

**Devices.** The product's real screen on a lit MacBook, the camera pushing in to what the voice names:
`python3 scripts/blender_clip.py <film_dir> blender/kit/scenes/laptop_screen.py --seconds S --engine cycles --screen
<folder of screen pictures, one per frame> [--params '{"focus": [0.3, 0.2]}']` (the params are in the scene file's
header; about 25 s a 1920x1080 frame).

**The library's shots and objects as parts.** The catalogue is `remotion/LIBRARY.md` (what each of the 227 shots is
and when to use it); the objects (devices, the Earth, satellites, clocks…) are in `references/building-blocks.md`.
Write a film's own shot or object in its workshop and let it wrap any library shot (`@shots/<Name>`, e.g.
`import {ChartRace} from '@shots/ChartRace'`) or runtime module (`@runtime/<module>`):

    python3 scripts/workshop.py <film_dir> new-shot <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <film_dir> new-object <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <film_dir> check
    python3 scripts/workshop.py <film_dir> still <Name>
    python3 scripts/workshop.py <film_dir> clip <Name> --props p.json --dna film_dna.json    # -> clips/<Name>.mp4
    python3 scripts/workshop.py <film_dir> fidelity <Name>    # a built object against its references (references/object-audit.md)

- **In the film's look:** the DNA file gives the WHOLE palette (`bg`, `fg`, `dim`, `accent`, `accent2`, `onAccent`,
  `surface`, `surfaceBorder`, `line`, and the fonts `fontDisplay`, `fontBody`, `fontMono`); a partial one is filled
  from a DARK default (`runtime/dna.tsx` NEUTRAL_DNA).
- **On a light look, LOOK at the part before using it:** render one frame in the film's DNA (`workshop.py <film_dir>
  clip <Name> --props p.json --dna film_dna.json --frames 90-90`) and read every word on it. Some library shots were
  built for dark grounds and hard-code light ink; `python3 scripts/ink_contrast_qa.py --only <Name>` catches a shot
  whose ink is mostly near-white, but NOT a few labels beside large coloured shapes: ChartRace passed it while its
  labels vanished on paper (fixed 2026-11-17: it now takes the film's `fg`/`dim`). A part whose words do not read is
  restyled in the workshop or swapped.
- **Placing a clip:** extract it to PNGs and let the page draw frame N at its time, so the page stays a pure function
  of time. Rendering: ChartRace with real rows took 45 s for 4 s.

**Generated imagery** (atmosphere only, never a fact): `python3 scripts/imagegen.py --prompt "…" --out bg.png` draws
through the Codex subscription with the no-text/no-invented-facts tail added; `--key` (the paid API) only after the
user agreed to pay.

**Accents.** `assets/html/accents.js`, each a pure function of (t, seed):
`burst` (confetti), `ring` (an expanding shockwave), `rays` (short radiating lines), `sparkle`, `pop` (arrival, no
overshoot), `drawOn` (a stroke drawing itself), `countUp`, and `drawParticles` for a canvas. A celebration is `burst` +
`ring` + `rays` started on the same frame, drawn BEHIND the element it celebrates. Tuned on a rendered sheet: at the
first defaults the confetti stayed a puff on the card; drawn over the card it crossed the text. Accent lines last 4-10
frames. Never `Math.random` in a film page; never grow past full size and shrink back (rewind_qa reads it as the
picture going back, as on a Memphis film's label pops).

## Launch and product films (step 6)
A starting point measured on 20 official launch films (`references/craft-standard.md` "A product film",
`references/launch-film-study.md`); the WorkBuddy blind rounds (2026-11-16/17) chose the film that followed it:
- the real product is the hero, at size: its real screens fill most of the frame (about 55 % of the width or more), or
  a crop pushes onto the exact component the voice names, within the screenshot's pixel density; a redrawn icon, card
  or device outline is a stand-in, used only where no real screen shows the idea;
- one hero object persists: the product's window stays, and the beats are its states, not new scenes;
- type beats alternate with product beats: one short display line on the brand ground (the problem, the promise, the
  payoff), the key word in the brand accent;
- the brand early (the real logo within ~10 s) and a closing lockup (mark + line);
- one small celebration (a task completing) and a quick rhythm: few shots hold still past 1 s.

## Sound (step 7)
- Score: `python3 scripts/score.py --bpm 112 --seconds S [--climax T] score.wav` (a generated score on a beat grid).
- SFX: `python3 scripts/sfx.py --cues cues.json --seconds S --out sfx.wav`, cues `[{"t": s, "cue": name, "gain": 0..1}]`
  from 15 synthesised, deterministic sounds (`sfx.py --list`: click, key, tick, focus, whoosh, pop, riser, impact,
  sparkle, strike, chime, swell, settle, reveal); recorded takes in `assets/sfx/kenney/` (click, select, drop, glass:
  UI-game timbres; a product film prefers real-world foley, `promo-shotcraft.md` §4).
- Mix: music well under the voice and ducked while it speaks; SFX short and high-passed; master to about -14 LUFS
  integrated with true peak at or under -2 dBTP: ffmpeg `loudnorm=I=-14:TP=-2:LRA=11`.

## Checks (step 8)
`python3 scripts/film_qc.py <film_dir>`: flash, rewind (against `_plan.json`'s cuts), picture glide, empty frames,
shake and caption size (`caption_size_qa`: the burned caption line ≥ 4.6 % of the frame height in glyph ink, i.e. a
~54-56 px font at 1080p) on `final.mp4`; exit 1 on any red. `_plan.json`:
`{"video": "final.mp4", "fps": 30, "frames": N, "cuts": [...], "segments": [{"start", "end", "kind": "shot"|"loop"}]}`,
the cuts computed by the same rule the renderer uses to switch shots (a plan that rounded differently put a cut one
frame off and rewind_qa reported a replay). Known blind spot of picture_glide_qa: a sky or light whose colours change
with nothing moving, and a fast move over a near-textureless gradient (proved on the sky film, 2026-11-16); and
captions changing inside a shot under a slow push read as extra motion (the diamond film, 2026-11-17: 0.128 px with
captions, 0.080 without). A turning object that repeats by design is a `kind: "loop"` segment in `_plan.json`, with
the seam proved (the wrap frame differs no more than consecutive frames).
picture_glide_qa is slow when several films render at once; on a busy machine run it per shot (`--clip --from --to`).

## Why these rules (the incidents behind SKILL.md)
- Style frames must differ as looks: the first end-to-end run (2026-11-16) offered one picture with three borders.
- Non-interactive runs still compare frames: two runs of the same sky request chose very different looks; the one
  that skipped the frames chose without ever comparing.
- Every drawn thing is correct: a Memphis film drew the physics model's two body halves as two cats' worth of legs.
- Fit beats habit: a blueprint cat film was well made and still the wrong look for a cat's playful physics (the user).
