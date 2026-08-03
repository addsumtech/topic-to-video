# Camera design & diegetic bridges (cinematic tier)

The grammar of HOW the virtual camera frames/moves, and HOW one scene hands off to the next. Grounded in
cinematography + motion-design research (shot sizes, safe areas, motivated movement, Murch's Rule of Six,
diegetic/interface transitions). Read this when authoring a `renderer:"remotion"` film's shots or seams.
The **operational floor** (the numbers + the two rules that fail silently) is inline in SKILL.md; this is
the fuller catalogue + the why + the impl sketches.

## 1. Camera — the shot rules (LEGIBILITY is the top constraint)

A read-card is INFORMATION; the camera's first job is to keep it legible, not to be dramatic.

- **MEDIUM is home base.** A content beat opens and rests at MEDIUM — the read-card ~60–75% of frame,
  centered, with breathing room. `ESTABLISH` is reserved for section/title openers and is only ONE step
  wider (still readable), never a tiny 20% speck. Every shot must read at BOTH its widest and its tightest.
- **One legible size band per scene.** The widest:tightest content-size ratio across a scene stays ~≤1.25×.
  The framing ladder is now compressed into that band (see the numbers below) so a scene can NEVER go
  tiny→huge. This is the cure for "opened tiny then pushed in so close it overflowed/cropped."
- **Frontal & eye-level on read-cards** (0° pitch/yaw/roll). Eye-level is neutral and never keystones type;
  high/low/dutch editorialize AND skew geometry. Put any tilt/dutch/aggressive parallax on BACKGROUND
  layers or on a transition — never the plane being read.
- **Perspective distortion is a lens+distance thing, not a content thing.** In CSS-3D the rig `perspective`
  IS the camera-to-plane distance: small (200–800px) is a fisheye that keystones; distortion explodes as a
  plane's translateZ approaches the perspective value. Default `perspective` is **2000px** (a long flat
  lens); keep `|dolly|` a small fraction of it and get "push" from a small clamped zoom, not deep Z.
- **Every move is MOTIVATED, or HOLD.** One reason per shot: push=intensify · pull=contextualize/relate ·
  pan=reveal-next · tilt=scale · rack=redirect-attention. If none applies (a definition, a quote, a dense
  block), HOLD. Never move because the previous beat moved. A diegetic gesture (a bridge) is the strongest
  motivation for a push.
- **Hold is the default; movement is a budget.** Lock at the resting framing for most of each beat; spend
  ≤1 small motivated accent move per key beat. A small move after stillness reads big (the Godfather move).
  Hold ~0.5–1s at readable size before AND after any move. Don't move during the primary READ, and don't
  stack camera-move + card-move + text-reveal at once (comprehension collapses past ~3 concurrent).
- **Ease + settle, never linear.** Every camera keyframe uses the house expo-out settle
  (`cubic-bezier(0.16,1,0.3,1)`); end on a brief hold. Guard spring overshoot so a settle can't bounce past
  the safe frame.
- **Bounded amplitude.** A push's zoom delta stays ~8–15%. The amplitude stack (energy × motion_personality)
  is clamped so even a bold push (≈13% zoom) keeps its ENDPOINT inside the readable band.
- **Safe areas** (broadcast-standard, the deterministic guard): readable text within title-safe (≤90% of
  frame; dense text ≤80%); at the CLOSEST frame of any push the read-card bbox must still fit action-safe
  (≤93%). Never an unclamped move that keeps growing past its endpoint — clamp every camera `interpolate()`.

**What this means in the renderer (already retuned — `remotion/src/stage/shots.ts`, `motions.ts`,
`SceneStage.tsx`, `Camera.tsx`):** the framing ladder is ESTABLISH ~0.95 / MEDIUM 1.0 / HERO ~1.06 /
CLOSEUP ~1.10 (down from 0.85/1.3/1.5); all read shots are frontal (0°); the old oblique `REVEAL`
(pitch 10 / yaw −15 / zoom 1.8 — the main distortion culprit) is recast as a FRONTAL soft arrival the
motion reveals; rig `perspective` default is 2000 with a centered origin; the move amplitude is clamped.
So a deck that just uses the natural shot types now frames comfortably by default — no per-deck tuning.

## 2. Transitions — pick the device from the RELATION, spend a small budget

A transition is a CLAIM about how two beats relate — choose it from the relation, not an effects menu.
Emotion/argument outrank geometric continuity (Murch): does the seam serve the felt point → the logic →
the rhythm.

| relation of B to A | device |
|---|---|
| equivalence / analogy | graphic-match / shared-element morph |
| cause→effect, sequential step | match-on-action / motion handoff — or a **diegetic bridge** (§3) |
| drill-down (parent→child) | iris/portal, or click-to-fly push INTO the element |
| sibling in a sequence (list/steps/chapters) | shared-axis slide, consistent direction (forward=advance) |
| contrast / pivot / reveal | smash cut |
| time passing / gentle blend | dissolve (rationed) |
| minor beat, same idea | plain hard cut or an audio-led J/L cut |

- **The default is an invisible cut; MARKED transitions are scarce** — budget ~1 marked seam per ~4 beats
  (~2–3 per 12-beat film). The `terminal collapse→aperture` match-cut, a graphic-match at the thesis, one
  smash at the key reveal. Everything else is a plain or audio-led cut.
- **J-cut is the house connective tissue:** offset the narration boundary from the picture cut so audio
  leads/lingers ~0.4–1.0s; never land picture-cut and narration-boundary on the same frame every time.
- **Every transition RESOLVES to the safe frame** — a bridge/whip/portal ends at the same comfortable
  medium, frontal, uncropped framing the shot rules mandate; its momentum may never overshoot into crop.

## 3. Diegetic BRIDGES — the world advances itself (the innovation)

A **bridge** is an in-world "advance gesture" — the interface/world itself carries the film to the next
beat (type-a-command-and-Enter, click-a-control, turn-a-page) instead of an editorial cut. It generalises
because it keys off the deck's AESTHETIC, not its subject: **ONE advance-gesture per film**, chosen from
`theme.style`/`theme.fontKind`, used consistently on MEANINGFUL seams (a new section, cause→effect,
drill-in), with plain/audio-led cuts on minor beats. A cursor-click on a terminal deck, or a page-turn on
a live dashboard, reads as a costume — so match the gesture to the look.

**Author API (storyboard):**
- `meta.bridge`: `"none"` (default) · `"auto"` (derive from the deck's aesthetic) · or an explicit gesture
  (`"type-enter"`, …). `"auto"` picks `type-enter` for a mono/terminal deck.
- `scene.bridge_label`: the command/phrase for THIS scene's hand-off (e.g. `"plan --message"`). ONLY a
  scene with a `bridge_label` gets the gesture; it plays over that scene's **tail** (~last 1.4s, over the
  narration's end + breath), then the ordinary cut reveals the next scene as the "output."
  Optional `scene.bridge_at_frame` to place the gesture start explicitly.

**Why the tail, not a transition-overlap:** a cross-scene transition overlap is clamped to the audio-breath
(~0.42s) so it can't double-audio — too short for a real gesture. Playing the gesture as a **screen-fixed
overlay on the outgoing scene's own tail** needs no overlap, never eats live narration, and works on ANY
scene type. (This is the same pattern as the `terminal` element's collapse-to-line tail.)

**Frame-safe (hard):** everything is a pure function of `useCurrentFrame()` — typed substring
(`label.slice(0,n)`), caret blink, Enter flash, cursor xy, ripple scale. NO CSS transition/@keyframes,
`setInterval`, `Date.now`. Reduced-motion drops the gesture (plain cut). Renderer:
`remotion/src/BridgeOverlay.tsx`, wrapped over every scene in `Scene.tsx`.

### The bridge menu (map ONE to the deck's aesthetic)

| gesture | the in-world action | fits (theme.style) | status |
|---|---|---|---|
| **type-Enter** | a command types char-by-char in a mono prompt; Return fires; the next plane is the output | terminal / dev-tools / infra / data-pipeline / security (mono) | **implemented** |
| **cursor-click** | an animated cursor travels to a button/tab, presses (squeeze+ripple); the next screen loads | product / SaaS / app-tour / dashboard-as-product (UI chrome) | designed |
| **click-to-fly** | a click LAUNCHES a clamped camera dolly INTO the clicked element (drill-down) | hub→detail, portals, overview→detail (any UI look) | designed |
| **page-turn / swipe** | a page peels about a spine (rotateY) or a card swipes off | reports / editorial / portfolio / gallery (print-adjacent) — pairs with the `lift` seam | designed |
| **control-toggle** | a slider/segmented-control flips and the chart re-renders as the next view | analytics / dashboards / data stories / before-after | designed |
| **media-scrub** | a playhead crosses a chapter marker and the beat advances | media/AV / timelines / staged processes | designed |
| **device-switch** | an in-world device changes state (power/lever/lights) and flips the scene | atmospheric / hardware / IoT / mood intros | designed |
| **shared-element morph** | one recurring token (a number, logo, shape) is carried continuously across the seam while the rest cross-fades | **any** deck — the universal fallback (the existing authored match-cut) | via match-cut |

**Impl sketches (for the designed ones), all frame-safe custom overlays / `TransitionPresentation`s:**
- *cursor-click:* a `Cursor` overlay, `left/top = spring(start→target, {damping:200})`; ~0.2–0.3s pre-click
  hold; press = scale dip to 0.88 + `back.out` release; ripple = `interpolate(f,[click,click+R],[0,1],clamp)`;
  the next screen pre-built at final values beneath.
- *click-to-fly:* a `camPush` presentation — clamped `translateZ/scale` toward the clicked target's [x,y],
  `springTiming({durationInFrames:~40, overshootClamping:true})`; lands at the safe MEDIUM pose; wrap fast
  moves in `CameraMotionBlur` (call `useCurrentFrame()` INSIDE the wrapper).
- *page-turn:* exiting page `rotateY 0→−100°` about a left spine with an edge shadow; entering page beneath;
  keep `perspective ≥1800` so the turn doesn't fisheye.
- *control-toggle / media-scrub:* a frame-driven track+thumb / playhead; at the seam frame the incoming
  chart (pre-built at final values) cross-fades in — animate the LENS/control, never the STATE.

**Discipline:** one gesture per film; reserve bridges for meaningful seams; every advance control must be
viewer-decodable in ~1s AND legible at the held medium framing (which reinforces the anti-over-zoom rule);
every bridge resolves to the safe frame.
