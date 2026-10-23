# Continuous stage runs

A run of consecutive beats that is ONE scene: no cut between them, one stage component drawing all of them, its
actors keeping their identity from beat to beat. It is the shape of a product promo that keeps acting on one hero
object — the deck page that turns, splits into its parts, gets clicked, and reflows — which a row of separate shots,
each with its own seam, cannot draw.

Reach for it when several beats are about THE SAME OBJECT being shown one more way. Do not use it to avoid choosing
shots: a run is one picture held across its beats, so every beat of it must still earn its own change.

## Declaring a run

```json
{"shot": "CardStage", "stage": {"run": "deck"}, "shot_props": {…what this beat changes…}}
```

- Consecutive beats with the same `stage.run` are one run. The id must not appear twice in a film.
- Every beat of a run names the same `shot`, and it must be a stage (`remotion/src/stage/`; today: `CardStage`).
- Inside a run there is no seam, so a joined beat may not declare `transition_in`. No beat of a run may declare
  `camera` (the stage moves its own camera). `ground`/`key` belong to the run's first beat.
- `stage_runs.check` enforces all of this in `validate.py` and refuses it again in `render_remotion.py`.

Every Python mirror of the film's timeline asks `scripts/stage_runs.py` whether a boundary is a cut: the segment
cache, the subtitle file and caption windows, the SFX cue map, the TTS tail pad, `seam_plan`, `sync_qa` (run beats are
never warped), `pace`, `film_energy_qa` and `settled_frame`.

## The model: keyframes that say what changes

Each beat's `shot_props` is a keyframe at the beat's start. Each of its `steps` is a keyframe inside the beat, timed to
the narration. A keyframe states WHAT CHANGES: the state after it is the state before it with those values merged in
(objects field by field; `null` removes a key). The stage at any frame is a pure function of that list and the frame,
which is why the per-beat segment render still works and a run is deterministic.

- A beat's own keyframe moves in over its first 0.8 s (never more than 40% of the beat).
- A step ARRIVES on its phrase: its move runs over the `move` seconds before it (0.45 s by default), so a click lands on
  the word that names it. A step whose phrase comes while an earlier move is still under way starts from wherever that
  move has got to.

```json
"steps": [
  {"at": {"cue": "文本框"}, "lift": [{"rect": [0.30, 0.05, 0.70, 0.165]}, {"rect": [0.03, 0.165, 0.34, 0.62]}]},
  {"at": {"cue": "点开"}, "cursor": {"u": 0.2, "v": 0.38, "click": true}, "camera": {"zoom": 1.7, "u": 0.19, "v": 0.4},
   "move": 0.6},
  {"at": 0.75, "marks": [{"rect": [0.03, 0.165, 0.34, 0.62], "label": "可编辑"}]}
]
```

`at` is `{"cue": "<words the narration says>"}` (resolved on the voice's own word times, the same ordered search a
device script uses) or a 0..1 share of the beat. Steps must be in the order the voice reaches them. A cue the
narration does not say is an error.

## CardStage

One card — a deck page, a screenshot, a document — on a lit stage, with the beat's title above it (one place and one
size for the whole run, up to two lines, the `highlight` word marked).

Everything that points at the card names a place ON ITS FACE: `(u, v)`, 0..1 across and down the face, or a rect
`[u0, v0, u1, v1]`. The stage carries that place through the card's 3D pose, so a cursor stays on the part it clicked
while the card turns. To author the places, look at the face image and read the fractions off it.

| state | what it does |
|---|---|
| `image` / `page`, `fit` | the face: a file the film serves, or a page the card draws (`kicker`, `title`, `lines`, `code` — a command set in the mono face exactly as written, `tone: accent` to flood it in the accent). Set `image: null` to switch to a page. `fit: contain` letterboxes. A STEP may change the face too: a run of looks flicked through on one card (each swap lands at the middle of its move). |
| `backdrop` | the DNA colour the stage is lit in (`bg` by default; `fg`, `accent`, `surface`…), set on a beat, carried across its move. A run that never changes it has no light arc (`film_energy_qa` fails a one-exposure film): darken it for a showroom beat, close on the accent. The title, its marked word and the captions are inked for it (`render_remotion` writes each beat's `stageGround`). |
| `title`, `highlight` | the title line and the word of it to mark |
| `card {x, y, s, rx, ry, rz, aspect}` | the pose. The card is sized to the content zone after projecting its turned corners, so it never runs into the title or the caption band. With no `aspect`, the card takes its face's shape; a keyframe that changes the face without saying `aspect` drops the old shape. |
| `cursor {u, v, click}` | a pointer on the face. It comes in from below-right. `click: true` presses as it arrives, with a ripple, and a click SOUND at the same moment. |
| `marks [{rect, label?}]` | a box on a part of the face, with an optional name in a pill beside it. The pill takes the first place that stays in the frame and off the part. A box inside a lifted part rises with it. |
| `lift [{rect, z?}]` | parts of the face lifted off it in depth (`z` 1 = the default height), leaving their places dimmed. Turn the card (`rx`/`ry`) so the depth reads. A point on a lifted part (a cursor, a mark) projects at its height. |
| `camera {zoom, u, v}` | lean in on a place of the face. By zoom 2 that place sits at the middle of the content zone. While zoomed, the picture is held inside the content zone, so the title and caption stay clear. `camera: null` settles back. |
| `count {value, from?, label?, u?, v?}` | a figure counting to `value` in a pill beside a place of the face. **A sourced figure only** — never invent one. |

When a keyframe changes the face, whatever sits on the old face (lifted parts, marks) goes before the swap, and the
new face's arrives after it.

## Sound

A step's `cursor.click` is a click in the film's sound, on the frame the picture clicks (`stage_runs.sound_events` →
`sfx.plan_cues` events, never dropped by the density cap). A film with stage clicks gets them even without
`meta.sound_design` (no score, no other cues); `meta.stage_sounds: false` turns them off. The pipeline cannot hear:
audition it.

## How the gates measure a run

A stage component cannot render alone, so the per-beat gates measure a run on the FILM's frames of it
(`scripts/stage_frames.py`): the frame of each keyframe's HELD state (just before the next move) and the MIDDLE of
each move, with the captions off as a register still has none, the same audit switches armed (`Film.tsx` forwards
`textSafe`, `typeSize`, `typeCollisions`, `titleProbe`), and one bundle for all of them.

- `text_safe_qa`: type cut off / in the caption band / too small, on every held and moving frame; ONE title per run
  in the title-placement census (a run is one composition, its title in one place by design).
- `cjk_type_qa`: CJK collisions on every held frame of the stage's beats.
- `shot_proof`: each beat's last held frame is its proof still (caption band, palette, empty or dead frame, ink, the
  design sheet). The source checks (wrong props, demo copy, icons, welded copy) are n/a — a stage has no demo content.
- `text_safe_qa --glide/--sync`, `film_energy_qa`, `shake_qa`, `check_av` already read the whole Film.
- `validate`: a run carrying the film's own image is exempt from the design-first floor (the product's real
  picture, like a device's screens); one drawing a page is adapted when its beats pose or act on the card, as-is when
  they only re-title it. The energy skeleton leaves run beats to `film_energy_qa` (no motion of their own outside the
  film).

Look at the rendered frames anyway — the settled frame of each beat AND the middle of each move: gates measure type,
not whether the move means what the beat says.
