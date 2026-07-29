# Shot Vocabulary

Shot-based paradigm for the Remotion cinematic tier. A **shot** is the atomic unit: framing + subject + motion, not a slide with motion added. The scene-space staging decouples content placement from camera framing.

## Core Concepts

### Scene Stage
A 3D scene-space coordinate system where elements are placed at absolute positions/depths. The camera moves through this space to frame shots. Stage dimensions are consistent across a deck (e.g., 4000×3000×2000 unit space).

- **Origin:** center of the stage (0, 0, 0)
- **Z-axis:** negative = away from camera (background), positive = toward camera (foreground)
- **Stage bounds:** typical range -2000 to +2000 on each axis for elements

### Shot Types (Framing)

Derived from cinematography grammar, parameterized for 3D scene-space:

1. **ESTABLISH** — Wide, shows full context. Camera far back (z: -800 to -1200), low zoom (0.8-1.0).
2. **MEDIUM** — Balanced framing. Camera mid-distance (z: -400 to -600), neutral zoom (1.0-1.2).
3. **CLOSEUP** — Tight on subject. Camera close (z: -200 to -400) or high zoom (1.3-1.8).
4. **OVER_SHOULDER** — Partial foreground element (z: -100) + background subject (z: -600).
5. **REVEAL** — Starts obscured (high zoom or blocked), camera pulls/pans to reveal.
6. **HERO** — Isolated subject, dramatic lighting/depth. Subject at z: -300, strong DoF (focusZ).

### Camera Motion Patterns

Pre-built motivated moves mapped to narrative beats:

1. **STATIC** — No camera move. Clean hold on composed frame.
2. **PUSH_IN** — Dolly forward (z increases). Intensifies, draws focus.
3. **PULL_OUT** — Dolly backward (z decreases). Reveals context, releases tension.
4. **PAN** — Horizontal yaw. Surveys, connects elements.
5. **TILT** — Vertical pitch. Reveals hierarchy (tilt up = awe, down = intimacy).
6. **ORBIT** — Yaw + dolly arc. Explores subject from multiple angles.
7. **RACK_FOCUS** — Static camera, focusZ pulls from bg to fg or vice versa.

### Element Primitives

Pre-composed content blocks placed in scene-space:

- **Panel** — Floating glass card (existing, from Camera.tsx PlaneContent)
- **Image** — a screenshot/photo plane. `size:[w,h]` frames it (default 1600×1000, NOT full-frame, so it
  reads as a floated panel). `frame:"browser"` wraps it in a **browser/device chrome** (traffic-light dots
  + `frameLabel` address bar) — the standard way to show product UI in a product film. `fit:cover|contain`.
- **TextBlock** — Typeset heading/body/caption
- **Callout** — Animated label/annotation
- **Grid** — Reference floor/wall
- **Hero** — Large typographic backdrop (existing)

## Shot Composition Flow

1. **Stage elements** — Place primitives at (x, y, z) in scene-space
2. **Define shot** — Pick shot type → sets initial camera position/angle
3. **Add motion** — Pick motion pattern → generates lens keyframes
4. **Tune timing** — Set easing, hold frames, motion amplitude

## Data Schema (storyboard.json extension)

A cinematic scene is a **SET** (`stage.elements`, placed ONCE) plus an ordered **LIST of shots** the
camera moves between over that set. This is the paradigm — NOT one move per scene. Author `stage` +
`shots` at the scene top-level (or under `props`).

```json
{
  "type": "cinematic",
  "duration": 12.0,
  "stage": {
    "perspective": 1300,
    "elements": [
      {"id": "grid",    "kind": "grid",  "position": [0, 0, -1200]},
      {"id": "gateway", "kind": "panel", "position": [-120, -30, 120],
       "kicker": "MEET SLIDE-MAKER", "title": "A team of agents", "sub": "It reads your real work."},
      {"id": "db",      "kind": "hero",  "position": [1180, 0, -360], "heroText": "EDITABLE"}
    ]
  },
  "shots": [
    {"type": "ESTABLISH", "duration": 4.0, "target": "grid",    "motion": "STATIC"},
    {"type": "MEDIUM",    "duration": 4.0, "target": "gateway", "motion": "PUSH_IN", "carry": true},
    {"type": "HERO",      "duration": 4.0, "target": "db",      "motion": "PUSH_IN"}
  ]
}
```

**Shot fields:** `type` (framing) · `target` (a staged element `id` — the shot moves to frame it) or
`targetPos` `[x,y,z]` · `motion` (pattern) · `easing` · `energy` (`subtle|balanced|bold` — motion
AMPLITUDE: a bold beat pushes harder, a subtle one drifts) · `duration` (SECONDS; optional — see tiling) ·
`carry` · `lens` (manual keyframe override, advanced).

**Kinetic typography (automatic).** Each element's text (kicker → title → sub, or a textblock's lines)
reveals unit-by-unit with a restrained spring settle, timed to the moment the camera FIRST frames that
element (the start of the shot that targets it) — so text animates in on arrival, not while it's a speck
in the wide establish. Set `enterAtFrame` on an element to override the reveal timing. Frozen under
reduced motion.

**Move diversity (gate).** `validate.py` warns when ≥3 shots share the same framing+motion — the shots
should reframe (different subject/scale/angle/move); three identical shots is a template, not a film (D12g).

**Motion blur — RESERVED (not built).** `@remotion/motion-blur` composites its samples with an
opacity/blend `filter` on an ancestor, which silently FLATTENS the CSS-3D rig (the same footgun the whole
tier guards against). Real per-sample motion blur therefore waits for the R3F/`@remotion/three` hero tier
where 3D motion blur is native. Keep fast moves eased + amplitude-controlled instead.

**`carry` = continuity.** A `carry` shot GLIDES from the previous shot's end pose to this shot's framing
(a continuous move to the new subject — the eye tracks one space across the cut). A non-`carry` shot CUTS
to its framing. This is the thing the old one-move-per-scene model could not express.

**Frame-window auto-tiling (A/V-safe).** `duration` is in seconds; `render_remotion._clean_shots` converts
each to frames and scales them so the shots tile the scene's total frames EXACTLY — so authored shot
durations can never desync the narration/captions. Omit `duration` on some/all shots to split evenly.

## Camera Targeting

Camera can target:
- **Element ID** — frames the element's position (auto-calculates camera position)
- **Manual lens** — explicit dolly/pitch/yaw/zoom keyframes (existing behaviour)
- **Preset shot** — shot type generates initial frame, motion pattern generates move

## Backward Compatibility

Legacy scenes with `camera`/`lens`/`layers` continue to work via Camera.tsx (unchanged). New shot-based scenes use `stage`+`shots` (list) and dispatch to SceneStage.tsx. A legacy singular `shot` object is still accepted (wrapped into a one-shot list). No scene is forced to migrate.

## P2 Implementation Scope

- `remotion/src/stage/SceneStage.tsx` — the SET renderer (perspective rig + elements + Finish)
- `remotion/src/stage/camera.ts` — shots LIST → continuous pose timeline (carry continuity)
- `remotion/src/stage/shots.ts` — shot type → target framing (camera position calculator)
- `remotion/src/stage/motions.ts` — motion pattern → lens keyframe generator
- `remotion/src/stage/elements.tsx` — element primitive components
- `scripts/render_remotion.py` — `_clean_stage`/`_clean_shots` (fail-loud + frame-window tiling) + dispatch
- `scripts/validate.py` — `_shot_stage_fields` pre-render gate (in `_cinematic_fields`)
- `tests/test_remotion_shots.py` — schema tiling, fail-loud, back-compat, validate-gate tests

## Design Principles (from guide + huashu-design)

- **Motivated motion** — Every move serves the narrative (push in = intensify, pull out = contextualize)
- **Clear composition** — Subject in focal plane, rule-of-thirds, safe margins
- **Depth hierarchy** — Foreground/midground/background separation via z-placement + DoF
- **Temporal pacing** — Static holds for comprehension, motion for transitions
- **Style consistency** — Editorial = gentle organic, Technical = precise mechanical, Minimal = restrained linear
