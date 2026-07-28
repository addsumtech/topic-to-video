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
- **Image** — Full-bleed or contained photo plane
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

```json
{
  "props": {
    "stage": {
      "elements": [
        {
          "id": "title-card",
          "kind": "panel",
          "position": [0, 0, -500],
          "title": "Shot-Based Design",
          "kicker": "REMOTION",
          "align": "center"
        },
        {
          "id": "bg-grid",
          "kind": "grid",
          "position": [0, -400, -800]
        }
      ]
    },
    "shot": {
      "type": "MEDIUM",
      "motion": "PUSH_IN",
      "target": "title-card",
      "duration": 90,
      "easing": "out"
    }
  }
}
```

## Camera Targeting

Camera can target:
- **Element ID** — frames the element's position (auto-calculates camera position)
- **Manual lens** — explicit dolly/pitch/yaw/zoom keyframes (existing behaviour)
- **Preset shot** — shot type generates initial frame, motion pattern generates move

## Backward Compatibility

Legacy scenes with `camera`/`lens`/`layers` continue to work via Camera.tsx (unchanged). New shot-based scenes use `stage`+`shot` and dispatch to SceneStage.tsx. No scene is forced to migrate.

## P2 Implementation Scope

- `remotion/src/stage/SceneStage.tsx` — shot interpreter + element renderer
- `remotion/src/stage/shots.ts` — shot type → camera position calculator
- `remotion/src/stage/motions.ts` — motion pattern → lens keyframe generator
- `remotion/src/stage/elements.tsx` — element primitive components
- `scripts/render_remotion.py` — detect `stage`+`shot` and dispatch to SceneStage
- `scripts/validate.py` — validate shot schema in `_cinematic_fields`
- `tests/test_remotion_shots.py` — shot registry + motion generation tests

## Design Principles (from guide + huashu-design)

- **Motivated motion** — Every move serves the narrative (push in = intensify, pull out = contextualize)
- **Clear composition** — Subject in focal plane, rule-of-thirds, safe margins
- **Depth hierarchy** — Foreground/midground/background separation via z-placement + DoF
- **Temporal pacing** — Static holds for comprehension, motion for transitions
- **Style consistency** — Editorial = gentle organic, Technical = precise mechanical, Minimal = restrained linear
