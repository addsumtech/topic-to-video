# Building blocks — what a film's code can draw with

Everything a register or an object in a film's workshop can import is here: the runtime (`@runtime/<module>` from a
workshop, `../runtime/<module>` in the library), React, Remotion, and the library's registers (`@shots/<Name>`).
Each module's own source header is the long form — this is the map. Objects are covered in
`references/object-authoring.md`; the frame-craft floor every register obeys is `references/remotion-shot-authoring.md`.

> **Designing a shot from nothing** — the per-beat method and the premium checklist (one idea, encoding, focal hierarchy, restraint, type hierarchy, colour that means, motion that reveals, a signature moment) live in ONE place: `agents/shot-director.md` Step 0.55. This file is what you assemble the result FROM.

## Time and motion

### `motion`
The clock and easing kit every register and object runs on — a pure function of the frame, settled at both edges of
a beat so a cross-dissolve never runs over something moving.
**Reach for it:** always. A register reads `useT()`; an object is handed `t`.
**Smallest real use:** `const on = easeOutCubic(clamp01(seg(t, 0.1, 0.4)));`
**Exports:** `useT`, `seg`, `clamp01`, `lerp`, `easeOutCubic`, `easeInOutCubic`, `easeOutExpo`, `easeOutBack`, `springAt`, `useSpringAt`, `useAnimSpan`, `cadence`, `stepped`, `speedRamp`, `hash01`, `life`, `SEAM_FRAMES`, `ENTRY_T`, `REDUCED_MOTION_T`.

### `cue`
Per-element cues: an item's entrance window, moved earlier so it reads when the narration names it — what the beat's
time warp cannot do, since one monotone clock cannot reorder. The render supplies the cues; without them it is a no-op.
**Reach for it:** any word that enters on its own — a label, callout, step, question, caption or note.
**Smallest real use:** `const cue = useCues(); const on = easeOutCubic(clamp01(seg(t, ...cue.win('labels.' + i, a, b, REACH_CUBIC))));`
**Exports:** `useCues`, `CueContext`, `warpFrame`, `REACH_CUBIC`, `REACH_EXPO`, `REACH_LINEAR`, `MIN_ENTRANCE_S`.

### `draw`
Draws a stroke on from its start without knowing its length (`pathLength = 1`), and slides a dashed stroke whose
dashes carry meaning.
**Reach for it:** a line, route, outline or ring that should draw itself.
**Smallest real use:** `<path d={d} fill="none" stroke={ink} {...drawOn(p)} />`
**Exports:** `drawOn`, `dashedStroke`, `boilPhase`.

### `alongPath`
Where a thing is when it travels along an SVG path, by arc length — so a travelling head stays welded to the line.
**Reach for it:** a drop, a packet, a marker or an object moving along a curve.
**Smallest real use:** `const p = pointAt(d, u); <circle cx={p.x} cy={p.y} r={6} />`
**Exports:** `pointAt`, `angleAt`, `pathLength`.

### `gesture`
The one implementation of typing, tapping, clicking and the caret, on frames or on a schedule — never on a
beat-relative rate.
**Reach for it:** an interface being operated (usually through `DeviceDemo`, which schedules these for you).
**Smallest real use:** `const shown = typedCount(t, step.ta, step.t1, typeChunks(text));`
**Exports:** `typeChunks`, `typedCount`, `caretOn`, `framesBetween`, `TapRipple`, `TouchPoint`, `CursorArrow`.

## Space, depth and camera

### `layout`
The frame-craft floor: the title band, the content zone, the caption band, and the text fitting that keeps type
inside its box in any script.
**Reach for it:** every layout decision — never hand-place against the frame.
**Smallest real use:** `const zTop = CONTENT_TOP, zBot = contentBottom(W, H); const px = fitTextPx(title, W * 0.8, 64);`
**Exports:** `CONTENT_TOP`, `TITLE_Y`, `contentBottom`, `captionBand`, `fitTextPx`, `fitBlockPx`, `wrapLines`, `textWidthPx`, `fitsBox`, `placeLabel`, `fitContentSquare`, `contentZoneBox`, `inkBlockH`, `bottomInset`.

### `pageCam2D`
A camera over a page bigger than the frame: keys it moves between, and where a page point lands on screen.
**Reach for it:** a tour across a document, a map, a long interface.
**Smallest real use:** `const cam = camAt(keys, t); const unlock = useCamUnlock(camUnlock(keys)); const s = pageToScreen(cam, W, H, px, py, unlock);`
**Exports:** `PageCam2D`, `camAt`, `pageToScreen`, `pageCamTransform`, `camUnlock`, `useCamUnlock`, `camMoves`, `clampToPage`, `fitScale`.

### `glide`
Type that MOVES glides with its drawing instead of stepping a whole pixel at a time: the 1/1024 skew Skia needs to
place a moving line to the quarter pixel, added only over the span the motion runs.
**Reach for it:** every transform or layout position that moves type — a reveal, a drift, a scroll, a camera. Below a
blur or drop-shadow, never above it (those filters keep only the scale of the matrix above them).
**Smallest real use:** ``const glide = useGlide(); … transform: glide(`translateY(${(1 - e) * 20}px)`, e !== 1)``
**Exports:** `glide`, `useGlide`, `unlockFor`, `unlockSkewFor`, `BASELINE_UNLOCK`, `BASELINE_UNLOCK_SKEW`, `BaselineUnlockContext`, `baselineUnlockOverscan`, `unlockCoverScale`.

### `depth`
Planes at depth and a motivated camera (push, pull, hold, dolly), drawn in 2D so type stays sharp.
**Reach for it:** foreground and background that mean near and far; a camera move with a cause.
**Smallest real use:** `<Plane depth={DEPTH.context}>…</Plane>`
**Exports:** `DEPTH`, `Plane`, `SceneCamera`, `cameraAt`, `dollyAt`, `useCamera`, `panAt`, `clampPan`.

### `focus`
Depth of field as a signal — how far a thing is from what the shot is about, said in blur and dimming.
**Reach for it:** pulling attention to one element among several.
**Smallest real use:** `const f = focusAt(dist, U); <div style={{filter: focusFilter(f), opacity: f.opacity}} />`
**Exports:** `focusAt`, `focusFilter`, `focusDist`.

### `stage3d`
Cards posed anywhere in 3D and a camera that flies to face any one of them, with type that stays type (CSS 3D, not
WebGL).
**Reach for it:** a space of panels the camera travels through.
**Smallest real use:** `<Stage3D cam={pose}><Surface pose={p} w={400} h={300}>…</Surface></Stage3D>`
**Exports:** `Stage3D`, `Surface`, `Pose`, `matrixOf`, `inverseOf`, `fitStage`, `fitSurfaces`, `projectPose`, `faceShade`, `useStage`.

### `project3d`
Projects a 3D point to the frame — the arithmetic for drawing your own 3D (an object that turns) or for anchoring real
type to a thing in space.
**Reach for it:** an object with `META.turns` (see objects/DemoForm); a label on a WebGL object.
**Smallest real use:** `const q = project(yawPoint(p, yaw), CAM, AIM, 30, w, h);`
**Exports:** `project`, `yawPoint`, `onRing`, `Vec3`.

### `fitCamera`
Frames a 3D scene at the aspect it was given by asking the projection how far the camera must stand.
**Reach for it:** a 3D register or object that must fit at 16:9 and 9:16 alike.
**Smallest real use:** `const dist = fitDistance(corners, AIM, DIR, 30, W, H, box, 8);`
**Exports:** `fitDistance`, `fitDistanceMulti`, `frameCamera`, `screenBounds`, `boxCorners`.

### `aimCamera`
Points a react-three-fiber camera where the label arithmetic thinks it points (r3f aims at the origin otherwise).
**Reach for it:** any WebGL register that also places DOM labels.
**Smallest real use:** `<AimCamera at={[0, 0, 0]} from={[0, 2, 8]} />`
**Exports:** `AimCamera`.

## The design system, light and colour

### `dna`
The film's Design DNA — type, palette, surfaces, motion personality — and the colour arithmetic every register uses
so a film is one visual system.
**Reach for it:** every colour and face. `useDNA()` in a register; an object is handed `dna`.
**Smallest real use:** `const ink = dna?.fg ?? INK_D0, paper = mix(dna?.surface ?? SURF_D0, ink, 0.08);`
**Exports:** `useDNA`, `DesignDNA`, `mix`, `tint`, `shade`, `readableOn`, `contrastOf`, `dimOn`, `surfaceOn`, `separatedPair`, `dnaHas`, `coerceDna`, `DNA_PRESETS`.

### `hexColor`
Normalises a DNA token's hex colour to plain 6-digit form before `dna`'s luminance reader sees it — the 3-/4-/8-digit
shorthands it alone reads as maximally dark regardless of what colour they actually name.
**Reach for it:** testing whether a colour that might not already be 6-digit hex (a DNA's `bg`, `fg`, any token the
film authored, not a fixed constant you already know is 6-digit) reads as light or dark.
**Smallest real use:** `const groundLight = relLum(hex6(dna?.bg ?? BG_D0)) > 0.5;`
**Exports:** `hex6`.

### `light`
The beat's ground, resolved per frame — what a declared `ground` paints and which caption ink it deserves.
**Reach for it:** a register that must keep reading when a film grounds it light, or dark.
**Smallest real use:** `const lit = onLight(dna); const stroke = lit ? ink : glow;`
**Exports:** `onLight`, `groundFrom`, `readsOn`, `captionInk`, `useGround`, `paleEnd`, `deepEnd`, `GROUND_PRESETS`.

### `onAccent`
The ink for type set on a solid accent block — and the one place a DNA's second accent can speak.
**Reach for it:** a button, chip or badge filled with the accent.
**Smallest real use:** `color: onAccentInk(acc, dna?.accent2, dna?.onAccent, dna?.fg)`
**Exports:** `onAccentInk`, `ON_ACCENT_MIN`.

### `shotLuma`
The measured ground of every library register — what the burned caption and the seam guard read. A film's own shot
declares its `GROUND` instead (scripts/workshop.py), and the declaration is merged here at load.
**Reach for it:** rarely by hand; know it exists when a caption's ink looks wrong.
**Smallest real use:** `const y = dnaGroundY(shot, dna);`
**Exports:** `DNA_GROUND_TOKEN`, `SHOT_LUMA`, `dnaGroundY`, `dnaGroundLum`, `groundGap`, `HARSH_GROUND_GAP`, `GroundSpec`.

### `atmosphere`
The per-topic background world behind every beat — one low-contrast motif under the whole film.
**Reach for it:** from the film (meta.theme), not from a register.
**Smallest real use:** `<Atmosphere motif="grid" accent={acc} bg={bg} />`
**Exports:** `Atmosphere`, `Atmo`, `Motif`.

### `motif`
One topic-derived material drawn across the whole film, so a themed film is more than a set of registers.
**Reach for it:** from the Design DNA's `motif`; a register rarely draws it itself.
**Smallest real use:** `<FilmMotifLayer motif={dna?.motif} dna={dna} W={W} H={H} />`
**Exports:** `FilmMotifLayer`, `FilmMotif`, `MotifKind`.

### `finish`
The photographic layer between rendered and shot — grain, bloom, a vignette — from the DNA's `finish`.
**Reach for it:** from the film; a register never adds its own.
**Smallest real use:** `<FilmFinishLayer dna={dna} finish={dna?.finish} />`
**Exports:** `FilmFinishLayer`, `FilmFinish`.

### `fonts`
Loads the DNA's typefaces for the Film and for every standalone still — the reason the faces a DNA names are the
faces that render.
**Reach for it:** never directly; `var(--f-display)`, `var(--f-body)`, `var(--f-mono)` are what you write.
**Smallest real use:** `font: \`700 ${px}px/1.1 var(--f-display, Inter, sans-serif)\``
**Exports:** `FACES`, `Face`.

### `cjkType`
The leading a line of Chinese needs, derived from the copy — a Latin leading makes wrapped CJK collide with itself.
**Reach for it:** every block of type that may carry Chinese.
**Smallest real use:** `const lh = leading(title, 1.12);`
**Exports:** `leading`, `hasCJK`, `CJK_MIN_LEADING`, `fontWithLeading`, `fitIfCJK`.

## Content

### `atoms`
The parts a frame is built from — a bar, a figure, a list, a label — rendered in the FORM the Design DNA speaks.
**Reach for it:** a number, a scale, a list that should look like this film's system.
**Smallest real use:** `<Bar value={0.62} />`
**Exports:** `Bar`, `Figure`, `List`, `Label`, `Divider`, `Marker`.

### `figure`
The film's number printed as the film wrote it — never stripped to digits and re-typed.
**Reach for it:** any on-screen figure that came from the film (and from its sources).
**Smallest real use:** `const f = parseFigure(props.value); <span>{figureText(props.value)}</span>`
**Exports:** `parseFigure`, `figureText`, `figureAt`, `figureValue`, `Figure`.

### `icons`
One coherent line-icon family, so a category names what it is instead of pointing at a block.
**Reach for it:** a list of kinds, a legend, a row of features.
**Smallest real use:** `<Icon name="send" size={32} ink={ink} />`
**Exports:** `Icon`, `ICON_NAMES`, `IconName`.

### `rows`
A list prop, normalised — or a refusal that names what was actually sent.
**Reach for it:** every list prop, before `.map`.
**Smallest real use:** `const items = rows<Item>(props.items, 'items', 'MyShot');`
**Exports:** `rows`.

### `evidence`
For registers whose premise is a real artefact: refuses to draw without the image rather than drawing a stand-in.
**Reach for it:** a register or object that must show a real, credited image.
**Smallest real use:** `requireEvidence('MyShot', 'src', src, 'the real object');`
**Exports:** `requireEvidence`.

### `uiSurface`
The product itself as furniture: an application window a shot can put on screen, its copy from props.
**Reach for it:** an interface in a register (as opposed to on a device).
**Smallest real use:** `<UiSurface page="cards" W={w} H={h} dna={dna} content={content} />`
**Exports:** `UiSurface`, `UiPage`, `UiContent`, `uiCardRects`, `uiChromeH`.

### `voice`
The film's own narration as a signal a shot can draw — real levels from the beat's audio.
**Reach for it:** an audio-reactive element that must follow what is actually said.
**Smallest real use:** `<Voice samples={48} />`
**Exports:** `Voice`, `NarrationContext`, `VoiceLevels`.

## Devices

### `device`
The phone, tablet, laptop or monitor a device beat is performed on — its geometry and its three looks.
**Reach for it:** through `DeviceDemo` / `DeviceHero`; a film's own device shot can use `Device` directly.
**Smallest real use:** `const g = deviceGeometry('phone', 'flat', W, H, 'center', false); <Device g={g} dna={dna}>…</Device>`
**Exports:** `Device`, `deviceGeometry`, `deviceFace`, `defaultLook`, `isTouch`, `DeviceKind`, `DeviceLook`, `Rect`.

### `deviceSpec.json`
The device layer's numbers, read by the TypeScript and the Python alike: screen ratios, bezels, minimum step times.
**Reach for it:** never to change a number for one film; read it to know the limits (`screenRatio`, `minSeconds`).
**Smallest real use:** `import spec from '@runtime/deviceSpec.json'; const [rw, rh] = spec.screenRatio.phone;`
**Exports:** `screenRatio`, `minSeconds`, `maxZoom`.

### `screen`
What a device's screen shows: a screenshot (a long one scrolls), a recording, with the scroll bounded by the image's
real height.
**Reach for it:** through the device registers; a screen the film draws instead is an object (`objectSlot`).
**Smallest real use:** `<ScreenImage src={src} imageW={iw} imageH={ih} w={s.w} h={s.h} />`
**Exports:** `ScreenImage`, `ScreenVideo`, `scrollRangePx`, `flingAt`, `VideoSpan`.

## Objects

### `objectSlot`
The contract between a register with room for a thing and the film that draws the thing: the object's props, its
META, and the slot that finds it by id and draws it at its box's size.
**Reach for it:** every object (its props type) and every register or film shot that holds one.
**Smallest real use:** `<ObjectSlot object={props.object} box={{x, y, w, h}} t={objT} />`
**Exports:** `ObjectSlot`, `ObjectRef`, `ObjectProps`, `ObjectMeta`, `ObjectEntry`, `fitAspect`, `useObjectEntry`, `resolveObject`, `ObjectsContext`, `SLOT_KEYS`.

## The gates' own eyes

### `textSafe`
The audit a standalone render runs when a gate asks: type off the canvas, type in the caption band, type colliding,
copy that never arrived — and words on the frame no prop supplied.
**Reach for it:** never in a register; know it is what `text_safe_qa.py`, `cjk_type_qa.py` and `shot_proof.py` see.
**Smallest real use:** (rendered with `textSafe: true` by `scripts/text_safe_qa.py`)
**Exports:** `TextSafeAudit`, `auditTextSafety`, `auditTypeCollisions`, `auditFedText`, `auditUnfedText`, `UNFED_TEXT_TAG`.

## Recipes

### A mechanism in cutaway
Draw the section as SVG (walls, the part that does the work), give the working part a STATE prop from the film, and
let the mechanism act on `t` — flows along paths (`alongPath`), a part that moves (`seg`, `easeOutCubic`). Texture is
`// @decor:`. Reference: `references/object-examples/PuckInSection.tsx`. Host: `ObjectStage` (name the parts with
its labels) or `ObjectCompare` (the same object in two states).

### Liquid or particles along a path
One `d` per stream; each particle `pointAt(d, u)` with its own staggered window `seg(t, a + k * step, b + k * step)`;
how MANY pass is a prop, which ones is layout (`// @positional:`); a jitter from `hash01` is `// @decor:`. Draw the
stream's path with `drawOn` first so the particles have something to ride.

### A turntable
Draw the object in 3D: corners → `yawPoint(p, yaw)` → `project(...)` into the object's own box; cull faces whose normal
points away; paint far to near; set `META.turns = true`. Host: `ObjectTurntable`, which hands it `yaw`. Reference:
`remotion/src/objects/DemoForm.tsx`. A flat object turns as a card, at most ±60°.

### Layered strata
A list of thicknesses from the film, oldest first; stack rects bottom-up, reveal each on its own window, the newest in
the accent (`// @positional:` — the order is time). Reference: `references/object-examples/StrataOverTime.tsx`. Host:
`ObjectStage` with labels at each layer.

### A route on a map
The ROUTE is drawn (`drawOn` on its path, a marker at `pointAt`); the GEOGRAPHY is never invented — a real map is a
documentary image (`scripts/imagefetch.py`) under it, passed in as a prop and credited, or the route stands on its own
as a schematic with no coastline. Host: a film-local shot with the image, or `ObjectPath` when the route is a
sequence of named stations.

### An interface being operated
A screen that does not exist yet is an object drawn for a device: `DeviceDemo` `{"screen": {"object": {"id": …}}}`
with taps and drags at coordinates, and the typing and scrolling done inside the object from its `t` (a progressive
slice is `// @truncates:`). Every word — labels, the typed text, the button — is a prop. Reference:
`references/object-examples/ComposeScreen.tsx`. A REAL product's screens are screenshots, not objects.
