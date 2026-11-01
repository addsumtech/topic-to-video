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

### `focusLead`
The listed item the voice names leads the frame and its peers recede — Film mounts it from a plan, a register never does.
**Reach for it:** nothing to import: give a beat a list prop (parts, steps, rows…) whose items the narration names;
`scripts/focus_plan.py` writes the plan and `FocusLayer` multiplies each peer's own opacity.
**Smallest real use:** `<FocusLayer plan={sc.focus} items={sc.focusItems}>{register}</FocusLayer>`
**Exports:** `FocusLayer`, `focusWeights`, `findContainers`, `FOCUS_RECEDE`, `FOCUS_EASE_S`.

### `phrase`
An authored push or pull delivered in steps on the voice's clauses (Film.tsx `PhraseCamera`), not a creep over the beat.
**Reach for it:** nothing to import: author `camera:{move:'push'}` on a beat of 10 s or more.
**Smallest real use:** `const done = phraseExtra(frame, fps, sc.phrase, 1)` — 0..1 of the beat's steps.
**Exports:** `phraseExtra`, `PHRASE_STEP_S`.

### `world`
The place a beat happens in, drawn behind its register from the beat's own subject (styled films, `surface.world: place`).
**Reach for it:** nothing to import: name `world` on the slide; Film mounts `WorldBackdrop`.
**Smallest real use:** `placeGround('orbit')` — the ground the place declares (`PLACES` lists them).
**Exports:** `WorldBackdrop`, `PLACES`, `placeGround`.

### `places.json`
The table of PLACES a beat can happen in, read by `world` (drawing), `render_remotion.py` and `validate.py` alike.
**Reach for it:** to learn what a place is for before naming it on a beat, or to add one (draw it in `world` too).
**Smallest real use:** `import placesTable from './places.json'; placesTable.orbit.ground`
**Exports:** `orbit`, `sky`, `field`, `room`.

### `stage3d`
Cards posed anywhere in 3D and a camera that flies to face any one of them, with type that stays type (CSS 3D, not
WebGL).
**Reach for it:** a space of panels the camera travels through.
**Smallest real use:** `<Stage3D cam={pose}><Surface pose={p} w={400} h={300}>…</Surface></Stage3D>`
**Exports:** `Stage3D`, `Surface`, `Pose`, `matrixOf`, `inverseOf`, `fitStage`, `fitSurfaces`, `projectPose`, `faceShade`, `useStage`.

### `surfaceView`
A camera over a panel — a screen, a page, a product's UI redrawn in DOM — on a flat frame or inside a 3D `Surface`:
the panel is laid out ONCE in its own units and the view is one transform carrying the baseline unlock, so its type
glides while the camera pans and pushes. Re-laying the panel out at the view's size every frame (`left: x*k`,
`font-size: size*k`) made a delivered film's type tremble 0.2-0.6px; `scripts/jitter_qa.py` measures it.
**Reach for it:** any shot whose camera moves ACROSS a panel (a screen you push into, a page you scroll over); a
device's live screen. Anything that moves INSIDE the panel moves by a transform (glide's place helper), never `left`/`top`.
**Smallest real use:** `<SurfaceView w={1000} h={486} k={innerW / (vw * 1000)} x={-u0 * imgW} y={-v0 * imgH}>…</SurfaceView>`
**Exports:** `SurfaceView`, `surfaceViewTransform`.

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

### `optics`
What the lens does with a light the register DRAWS — one optic per beat, never decoration: `bloom` (a source
scatters: copy + blur 24-40 px + screen, <= 0.3), `halation` (highlights over 0.7 luminance bleed red, <= 0.15),
`sweep` (ONE 20-30 frame pass across a hero surface, from the DNA's key side), `aberration` (red/blue scaled about
the frame centre: 0 at the centre, 1-2 px at the corners — on pictures of emitted light, never type) and `leak` (the
Film burns it over the seam INTO a beat, top edge only, 10 frames). CSS/SVG only, so frames stay a pure function of
their number (scripts/determinism_qa.py).
**Reach for it:** a register whose picture HAS a light — a lit screen, a star, a spotlight, a flame, a glass surface
turning. Export `OPTICS = [...] as const` (validate.py reads it), call `useBeatOptic(OPTICS)`, mount the primitive on
the light; pass the type's rects as `keepOut` so the glow stays off the words (measured: an unmasked bloom took a
title from 10.3:1 to 9.5:1).
**Smallest real use:** `const o = useBeatOptic(OPTICS); <OpticSource optic={ofKind(o, 'bloom')} keepOut={rects}>{lamp}</OpticSource>`
**Exports:** `OPTIC_KINDS`, `OPTIC_MAX`, `useBeatOptic`, `OpticSource`, `GlowCopy`, `LightSweep`, `Aberration`,
`SeamLeak`, `ofKind`, `useFrameAtT`, `normalizeOptic`, `OpticContext`.

### `material`
The topic's own MEDIUM as a lit ground — `paper`, `water`, `metal` (brushed), `clay`: a fixed-seed SVG height field
(feTurbulence) lit by feDiffuse/feSpecularLighting, the surface still and ONE light drifting across it over the beat.
Never under body type without the proof: `MATERIAL_SPAN` is the lit ground's measured 2nd-98th percentile under a
type column, and `materialShades` gives the two grounds an ink must read on.
**Reach for it:** a beat about what something is made of or where it lives (LitMedium is the register for it); a DNA
names the film's medium with `material: {kind}`.
**Smallest real use:** `<LitGround material="water" base="#173f5a" light={dnaLight(dna)} travel={[0.66, 0.96]} />`
**Exports:** `LitGround`, `MATERIALS`, `MATERIAL_BASE`, `MATERIAL_SPAN`, `materialShades`, `isMaterial`.

### `volume`
Light IN a volume, drawn as the line-of-sight integral a real one is, by a WebGL fragment shader: `curtain` (an
aurora — one folded sheet; for each pixel the sheet's crossings of its column, each weighted by 1/|dX/ds|, so a fold
turned edge-on brightens itself; a sharp lower border where the emission stops, faint tops, field-aligned rays that
travel along the arc, the far end receding; coloured by ALTITUDE from `bands`), `shafts` (the sky round a source seen
through an occluder's gaps — `clouds` · `canopy` · `slats`, `open` 0..1 — averaged along each line toward it, so each
shaft IS a gap), `nebula` (domain-warped emission, H-alpha red to [O III] teal toward the ionising `star`, dust lanes,
stars), `flame` (heat advected up, a blackbody temperature ramp) and `layer` (one glowing stratum — WorldStage's
`band`). Physics colours are declared and sourced in `volumeCore` (AURORA_BANDS: NASA's 100-200 km oxygen green,
>=200 km oxygen red, <=100 km nitrogen pink; NEBULA_EMISSION; blackbody) — the hexes are display approximations.
WHY A SHADER: bench-aurora rebuilt an SVG curtain four times and shipped "barcode rays on a flat wall" — N rects are N
bars however soft; the integral is per pixel. DETERMINISM: ONE shared context per tab (a context per canvas meets
Chrome's live-context limit on a long film and the oldest goes blank), every uniform set on every draw (arrays
zero-padded — a uniform keeps the last volume's value), the 2D copy's state reset every draw, time = frame / fps.
Measured on `--gl=angle`: VolumeProbe (all five forms, one context, one frame) and AuroraCurtain / LightShafts /
NebulaField each bit-identical (0/255) twice, at concurrency 1 vs 3, and cold vs after their predecessors; the probe's
`stateLeak` control fails (cold and concurrency, up to 248/255) and is blamed on that layer. No WebGL context is a
loud error. NEVER OVER TYPE: `keepOut` rects clear the light to VOLUME_KEEP_FLOOR (18%) inside the type, feathering
back over max(90 px, half the rect's long side) — a 90 px feather alone cut a hard dark ellipse out of the sky.
**Reach for it:** the subject IS light in a volume — an aurora, a sunbeam, a nebula, fire, plasma. Not as a backdrop
to a beat about something else (the effect must encode the content). Registers: `AuroraCurtain`, `LightShafts`,
`NebulaField`; a world holds one as `{"kind": "volume", "form": …}` (references/stage-runs.md).
**Smallest real use:** `<Volume spec={{form: 'curtain', bands, seed: 7}} curtain={{yTop, yLow}} keepOut={[titleRect]} />`
(put it on a dark ground: the canvas is SCREEN-blended — light adds, it does not paint over). `curtainFit(yTop, yLow,
lowKm, topKm).yOf(km)` is the projection a ruler beside the curtain must use.
**Exports:** `Volume`, `drawVolume`, `VolumeDraw` (the pure maths and the sourced colour tables are `volumeCore`).
keepOutRows, keepOutAt, AURORA_BANDS, NEBULA_EMISSION, blackbody, VOLUME_MAX_INTENSITY.

### `volumeCore`
The pure half of `volume`, shared with tests and validate: the forms' parameter checks (`checkVolume`, `checkBands` — refuse an unknown form, out-of-range intensity, bands that overlap or leave the sourced altitude range), the curtain's fit to its box, the band weights and `colourAt`, the type keep-out rows, and the SOURCED physics colours (`AURORA_BANDS` from NASA's aurora page: green 100-200 km, red >=200 km, pink <=100 km; `NEBULA_EMISSION`; a `blackbody` ramp for flame) — the hexes are display approximations.
**Reach for it:** to check a volume spec before render, or to read a physics colour; registers draw with `volume`.
**Smallest real use:** `checkBands(bands); const c = colourAt(AURORA_BANDS, 150);`
**Exports:** `VOLUME_FORMS`, `AURORA_BANDS`, `AURORA_LOWER_KM`, `AURORA_TOP_KM`, `NEBULA_EMISSION`, `blackbody`, `FLAME_KELVIN`, `OCCLUDERS`, `checkVolume`, `checkBands`, `curtainFit`, `bandWeights`, `colourAt`, `keepOutRows`, `keepOutAt`, `linearRGB`, `isHex`, the `VOLUME_*` limits, types `VolumeSpec`/`VolumeForm`/`Band`/`Rect`.

### `sound`
SHOT-OWNED SOUND: a register declares the sounds its own picture makes, as a LITERAL
`export const SOUNDS = [{kind, at, to?, each?, gain?}] as const` — `kind` one of `SOUND_KINDS` (click · tick · strike ·
whoosh · chime · swell, each synthesised in scripts/sfx.py), `at` a point on the register's clock (0..1) or the NAME of
a prop holding one (no prop: no event — and that prop has no default, so no picture event either), `each` a list prop
(one per item, spread from `at` to `to`). scripts/shot_sounds.py reads it (no render: chosen over a DOM census
because a census is a full extra pass, the segment cache would skip reused beats, and a static declaration is checked
by validate before anything renders), maps each t to the frame useT reaches it on and through the beat's sync warp,
and sfx.plan_cues mixes it peak-aligned, gain-staged under the voice, thinned to one per 0.12 s and inside the density
cap. The register times its picture FROM the same declaration (`soundT` / `soundTs`), so the two cannot drift.
A board adds its own: `slide.sounds: [{kind, at: <seconds> | {"cue": "<words>"}, gain?}]` (never dropped) or `"none"`
(nothing under that beat); a stage step: `"sound": "chime"`. They ride with `meta.sound_design`, or alone with
`meta.shot_sounds: true`. THE CLOSE: `meta.close_sound` — `full` (riser → impact → sparkle), `soft` (one low settle),
`none`; default from `seam_plan.film_tempo` (calm → soft, kinetic / scored → full).
**Reach for it:** a picture that makes a sound when it acts — a needle landing on a station, a stamp, a pencil strike,
a substorm brightening (`AuroraCurtain.surgeAt`), light breaking through (`LightShafts.breakAt`). Restraint: a sound
per meaning, not per element.
**Smallest real use:** `export const SOUNDS = [{kind: 'strike', at: 'landAt'}] as const;` then
`const landT = soundT(SOUNDS, 'strike', {landAt});` drives the landing.
**Exports:** `SOUND_KINDS`, `soundTs`, `soundT`, `SoundDecl`.

### `fonts`
Loads the DNA's typefaces for the Film and for every standalone still — the reason the faces a DNA names are the
faces that render.
**Reach for it:** never directly; `var(--f-display)`, `var(--f-body)`, `var(--f-mono)` are what you write.
**Smallest real use:** `font: \`700 ${px}px/1.1 var(--f-display, Inter, sans-serif)\``
**Exports:** `FACES`, `Face`, `FACES_READY` (the load, for code that measures type — `kinetic` waits on it through
`kineticDom`). IBM Plex Sans declares its real width range, 75-100%, so a width morph reaches the `wdth` axis.

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
The phone, watch, tablet, laptop or monitor a device beat is performed on — its geometry and its three looks. A
`model` (deviceSpec.json's models table: Apple's published pixels, ppi and case) draws THAT device: its screen is its own
pixels, its bezel the published case around them, every corner concentric (case = screen + bezel), with the parts
no spec publishes — crown, band, buttons, Dynamic Island, notch — under `design`.
**Reach for it:** through `DeviceDemo` / `DeviceHero`; a film's own shot that shows a device's capture uses `Device`
directly — never a hand-drawn slab (validate warns: scripts/device_fidelity_qa.py).
**Smallest real use:** `const g = deviceGeometry('watch', 'real', W, H, 'center', false, 'watch-s12-46'); <Device g={g} dna={dna}>…</Device>`
**Exports:** `Device`, `deviceGeometry`, `deviceFace`, `defaultLook`, `isTouch`, `proportions`, `roundRectPath`,
`modelNames`, `DeviceKind`, `DeviceLook`, `DeviceGeom`, `Rect`. A laptop turns by `pose` (its own camera, `laptop3d`);
a slab the caller turns with a CSS rotate passes `turned={{yaw, pitch}}` so its case's edge shows on the near side.

### `laptop3d`
A laptop as ONE 3D object: lid and base joined at the hinge, one camera for the deck (keys, trackpad, speaker grilles,
thumb scoop, chamfered aluminium edge), the hinge, the lid's edge and the screen on it. `Device` draws every laptop
through it; at rest the lid faces the camera square, so the screen is exactly the device geometry's screen rect. To TURN a
laptop, pass `pose={{yaw, pitch, open}}` to `Device` — never a CSS rotate of its picture (that slanted the lid over a
front-on base). Measured deck layout: deviceSpec.json `models.*.body3d`.
**Reach for it:** a shot that turns a laptop toward something; `laptopCamera(g, pose)` + `laptopBounds` to place a
label or a light on the turned machine (its `screenQuad`, its projection, its `lid` points).
**Smallest real use:** `<Device g={g} dna={dna} pose={{yaw: -24, pitch: 15}}>{screen}</Device>`
**Exports:** `laptopCamera`, `laptopBounds`, `laptopScreenTransform`, `laptopScreenFrameTransform`, `laptopDims`,
`LaptopBody`, `LaptopDefs`, `LaptopPose`, `L3D`.

### `deviceSpec.json`
The device layer's numbers, read by the TypeScript and the Python alike: the real `models` (each with its source
URL and date; `derived` and `design` values said as such), the generic `kinds`, screen ratios, `parts`, minimum
step times.
**Reach for it:** never to change a number for one film; read it to know the limits (`screenRatio`, `minSeconds`)
and which captures name a model (`models.*.published.px`; `python3 scripts/device_models.py <image>`).
**Smallest real use:** `import spec from '@runtime/deviceSpec.json'; const [rw, rh] = spec.screenRatio.phone;`
**Exports:** `models`, `kinds`, `parts`, `screenRatio`, `minSeconds`, `maxZoom`.

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

### `safeZone`
Where a portrait film posted to Xiaohongshu / Douyin / TikTok / Reels / Shorts is covered by the platform's own UI,
and the `social` profile that keeps what must be read out of it: the caption above the bottom 19%, a register drawn
in a frame scaled so its own caption band lands on the caption, a stage laid out in the safe area directly
(references/craft-research.md §2).
**Reach for it:** only in Film.tsx and a stage component — a register never reads it (it is drawn in the frame).
**Smallest real use:** `const safeP = React.useContext(SafeZoneContext);`
**Exports:** `SafeZoneContext`, `SafeProfile`, `SOCIAL`, `SAFE_MIN_TALL`, `safeProfile`, `registerFrame`, `captionBottomY`, `SAFE_CAPTION_SCALE`. The profile applies to a full-screen vertical (9:16) frame only.

### `stageRun`
The continuous stage: consecutive beats naming one `stage.run` are ONE scene drawn by one stage component. Each beat's
props and each of its `steps` is a keyframe that says what changes (objects merge, `null` removes); a step arrives on
its phrase. The stage at any frame is a pure function of the keyframes and the frame (references/stage-runs.md).
**Reach for it:** only in a stage component (`remotion/src/stage/`) — never in a register, which is one beat on its own
clock.
**Smallest real use:** `const now = useStageRun(); const cursor = actor<Cursor>(now, 'cursor');`
**Exports:** `useStageRun`, `actor`, `springSum`, `moveShare`, `sinceEvent`, `lerpState`, `mergeState`, `buildKeys`, `morphFrames`, `STEP_MOVE_S`, `StageRunContext`, `StageBeat`, `StageKey`, `StageNow`, `Normalize`. Spatial actors move on `springSum` (springs that add up across keyframes, landing exactly on target); `stage/surface.tsx` lights a stage's surfaces (layered key-light shadow, turn sheen, rim) and blurs what moves fast.

### `carry`
The elements a seam can take hold of: `data-carry="<id>"` on the element (no pixel changes), or `<CarryAnchor>` when the
thing is drawn in pieces (`data-carry-part` on the siblings); `data-carry-glyph` makes a text anchor a window of
letterforms. Shared ids: `screen`, `window`, `hero`, `figure`, `card:<id>`, `word`. The `container`, `grow` and
`through-window` seams (seams.tsx) refuse an anchor they cannot find; `scripts/carry_anchors.py` reads them from source
for the planner and validate.
**Reach for it:** in a register whose main element should be carried across a cut; an anchor with its own entrance
reads `useCarried(id)` and draws itself in place when a container brings it in.
**Smallest real use:** `<div data-carry="screen" style={...}>…</div>`
**Exports:** `CarryContext`, `useCarried`, `CarryAnchor`.

### `handoff`
The camera hand-off: on a `continuation` cut a push or pull runs into the cut at velocity v and the next beat (no camera
of its own) inherits v and lets it decay — the move survives the edit. Pure curves; Film's HandoffCamera drives
SceneCamera with them; one camera channel per beat (Film and validate refuse a pan beside it).
**Reach for it:** never directly — `slide.camera: {move, handoff: true}`, set by seam_plan on a planned push/pull before
a continuation.
**Smallest real use:** `const {extra, v} = handoffOut(f, durF, amp, 'push');`
**Exports:** `handoffOut`, `handoffIn`, `HANDOFF_SETTLE`.

### `geo`
Offline vector geography: Natural Earth (public domain) from `world-atlas` 2.0.2 at 1:110m/1:50m, decoded with
`topojson-client`, projected in code (orthographic globe, Equal Earth flat map), great-circle arcs, region lookup by
Natural Earth name or ISO code (an unknown name throws with the nearest names), framing on a region's main body.
Nothing is fetched at render time; licences in `remotion/THIRD_PARTY.json`.
**Reach for it:** any beat about where, a route or a scale on Earth — GlobeFocus and FlightArcs are built on it.
**Smallest real use:** `const r = findRegion('Japan'); const view = regionFrame(r, W, H);`
**Exports:** `atlas`, `findRegion`, `regionFrame`, `orthoProjection`, `orthoXY`, `flatProjection`, `greatCircle`,
`lerpView`, `radiusFor`, `validLonLat`, `lonLatOf`, `pointsFrame`, `meanLon`, `wrapDelta`, `arcDeg`, `viewVec`, types.

### `earth`
The one globe the geography registers draw: an orthographic sphere lit from the upper left, Natural Earth land and
borders, a hairline graticule, an atmosphere rim, the film's regions lit in its accent — a pure function of the view.
**Reach for it:** draw the planet in a geography register; the register owns the camera (`geo.lerpView`) and every name.
**Smallest real use:** `<Earth view={view} W={W} H={H} lit={['Japan']} />`
**Exports:** `Earth`, `earthPalette`, `EarthInk`.

### `labelPlace`
Labels beside their points with no two labels — and no label and another point — overlapping: eight positions round
each point, nearest first, then further out; throws when a label cannot be placed rather than overlapping.
**Reach for it:** any register that names several points (maps, scatters, networks).
**Smallest real use:** `const placed = placeLabels(reqs, {W, H});`
**Exports:** `placeLabels`, `overlaps`, `Rect`, `LabelReq`, `Placed`.

### `labelWidths`
How wide each label really is in the face the shot resolves, measured by the browser through `kinetic`'s reference
node — a chip sized from the advance estimate was half again too wide and collision checks refused layouts that fit.
**Reach for it:** before placing labels or sizing chips.
**Smallest real use:** `const widths = useLabelWidths(labels, font);`
**Exports:** `useLabelWidths`.

### `sankey`
A flow layout from the film's own nodes and links, every ribbon's width its quantity; REFUSES a node whose inflow and
outflow differ (relative 1e-9), loops and dangling links — a loss is a link to a node named for it.
**Reach for it:** where a quantity goes and is conserved (FlowSankey).
**Smallest real use:** `const lay = layoutSankey(nodes, links, box);`
**Exports:** `layoutSankey`, `validateSankey`, `ribbonPath`, `stackLabels`, `SANKEY_TOL`, types.

### `dither`
The film's delivery dither: a static, seeded triangular dither of ±2 code values over the whole frame, painted last so x264 cannot keep a dark gradient's 8-bit steps as rings (CAMBI 12-22 on this tier's own films without it, 0.0 with it; `scripts/banding_qa.py` measures the delivered file).
**Reach for it:** never — Film.tsx draws it when render_remotion asks (`dither`, on unless `meta.dither: false`); a gate's still and a register's own still go without it.
**Smallest real use:** `{dither ? <FilmDither /> : null}`
**Exports:** `FilmDither`, `ditherTile`, `DITHER_TILE`, `DITHER_AMP`.

## Type that moves

### `kinetic`
Type animated by the letter, word or line that is still the text it animates: the copy is laid out ONCE by the browser
in a reference node (same face, size, axes, tracking, ligatures off), each grapheme's box is read with
`Range.getClientRects()`, and every glyph is drawn on its own exactly there — so kerning, a Chinese line's punctuation
compression and its kinsoku line breaks are the browser's (measured 0 px against one text node, both scripts). The face
is resolved off an in-tree anchor (a DNA's variables, a terminal DNA's monospace) and measured in an untransformed node,
so a camera or the platform-safe frame cannot move a measurement. Lines are fitted by MEASURING (`fit: 'box'`, with
`fitTiers` to keep the film's lines whole before allowing a wrap); a weight or width morph is measured at five anchors
and re-flowed. Motion is a pure function of the shot's clock in the After Effects model (one coverage per unit drives every
property): staggers, an AE range selector, line/word/glyph masks, swaps (roll / scramble / flip), text on an SVG path
(placed by arc length, turned to the tangent), a continuous drift, an emphasised `*run*` that takes colour and weight
as it lands. Moving glyphs carry the baseline unlock inside any blur. Every type gate reads a KineticText as its LINES.
**Reach for it:** any type that enters, swaps, travels or morphs by the unit — and never hand-roll a per-character
split again (`display: inline-block` per letter measured 8.1% wider than the text it splits, 11% for Chinese).
**Smallest real use:** `const h = useKinetic({text: lines, font: {family: DISPLAY, size: U * 0.12, minSize: U * 0.05}, w, h: room, fit: 'box'}); <KineticText k={h} x={x} y={y} color={ink} motion={{mask: 'line', from: {ymask: 1.02}, enter: {by: 'line', at: 0.1, stagger: 0.16, dur: 0.9, ease: 'expo', cueKeys: lines.map((_, i) => 'lines.' + i)}}} />`
**Exports:** `useKinetic`, `KineticText`, `KSpec`, `KFont`, `KMotion`, `KState`, `KTiming`, `KSwap`, `KPath`, `KLayout`, `KineticHandle`, `emphBoxes`, `kineticPathLength`, `KineticHoldContext`, `KineticHoldAudit`, `HoldReport`, `HoldRecord`, `KIdle`, `KineticTextProps`.
**Held type stays alive** — `motion.idle` (`KIdle`): once a LINE has landed (the latest of its glyphs), a micro tracking
`breathe` (em at the peak; 0.004–0.012 reads as breath), a `light` passing along it in a colour every few seconds, and a
`drift` whose velocity eases in — each eased in over 0.8 s, continuous in time, and with the baseline unlock on for the
whole shot when anything moves (the span rule), so a held line never steps a pixel. The kinetic registers turn it on with
`hold: 'alive'` (their default); `'still'` is a slide's hold. **A scramble never spells a word**: its stand-ins are a
block drawn as a box or the right glyph at another weight for CJK, a symbol for everything else (kineticCore's
scrambleGlyph) — drawn from the copy's own glyphs, 大模型 flashed 大模刑 (bench-launch).
The register must render the handle's KineticText (or `handle.anchor`) in the same commit as the hook — the face is
read off it; without it the render cancels at once, naming the hook. Two KineticTexts take two handles (a cache hit).
`read={false}` marks type that is texture (a ring of repeated words, cropped big type) rather than copy that must be
read: everything else is held to its reading time by `scripts/shot_proof.py` (see `KineticHoldAudit`).

### `kineticCore`
The pure half of `kinetic`, with no DOM and no React, runnable in node: the AE range selector (`rangeCoverage`, shapes
square / ramp / triangle / round / smooth, ease high/low, amount, seeded `permutation`), stagger order (`orderRank`),
the measured eases (`EASES`: CSS `ease` as linear.app runs it, stripe's roller, GSAP's expo/power), Intl.Segmenter
graphemes and words (zh/ja segmented), the `*…*` emphasis markup (`parseRuns`), the swap schedule (`swapTimes`), and
`readingSeconds` from the shared reading table.
**Reach for it:** a register that must reason about the same schedule its KineticText runs (WordRoll's underline
follows `swapTimes`), or needs a reading time.
**Smallest real use:** `const T = swapTimes(options.length, 0.3, 0.74, cued, times);`
**Exports:** `rangeCoverage`, `RangeSelector`, `orderRank`, `permutation`, `EASES`, `cubicBezier`, `easeOf`, `graphemes`, `wordIds`, `wordCount`, `langOf`, `parseRuns`, `plainText`, `swapTimes`, `scrambleGlyph`, `ScrambleGlyph`, `SCRAMBLE_SYMBOLS`, `SCRAMBLE_BLOCKS`, `SCRAMBLE_WEIGHTS`, `readingSeconds`, `secToT`, `tToSec`, `tAtFrame`, `longestRun`.

### `kineticMove`
MAGIC MOVE: a list of SETTINGS (each a useKinetic handle with its own copy, box, size and place), and at each move
the glyphs two consecutive settings share TRAVEL from where the first set them to where the second does — leaving
glyphs lift and fade first, travellers cross on arcs (rightward over the line, leftward under it, at most
`MOVE_ROOM_EM` off it) word by word in landing order, arrivals rise in last. The first setting may assemble out of a
seeded `scatter` or rise in glyph by glyph. Every glyph is drawn where `kinetic`'s reference node laid it out and carries
its DOM marks (each setting an alternative), so the type gates read it as lines and the hold gate gets one record per
setting through `KineticHoldContext`. Its root is the `word` carry anchor, boxed on the LAST setting (a glyph window
when that is one line).
**Reach for it:** one statement becoming another made of the same letters — a kept word, an anagram, a reorder, a
layout (a stack of words) becoming a line. Not for two statements that share nothing (that is a cross-fade).
**Smallest real use:** `<KineticMove settings={[{k: a, x, y}, {k: b, x, y}]} starts={moveSchedule(need, spanS, 1, 0.9)} dur={1} color={FG} />`
**Exports:** `KineticMove`, `KineticMoveProps`, `MoveSetting`, `moveSchedule`, `MOVE_ROOM_EM`.

### `kineticMoveCore`
The pure half of `kineticMove`: `matchGlyphs` (the longest common subsequence first, so a shared word travels as a
body; the rest by identity, nearest first; spaces never travel), `arcAt` (the bowed path, capped), `scatterOf` (a
seeded start), and the move's timing (`moveTiming`, `travelWindow`, `leaveWindow`, `arriveWindow`, seconds from the
move's start).
**Reach for it:** a register that reasons about the same pairing or schedule the move runs.
**Smallest real use:** `const {pairs, leave, arrive} = matchGlyphs(Array.from(a), Array.from(b));`
**Exports:** `matchGlyphs`, `Match`, `arcAt`, `scatterOf`, `Scatter`, `MoveTiming`, `MOVE_DEFAULT`, `moveTiming`, `travelWindow`, `leaveWindow`, `arriveWindow`.

### `kineticWord`
A KineticText a seam can take hold of: wrapped in an element marked `data-carry="word"` whose box is the type's own
measured extent (the last alternative's lines, for a swap), with `data-carry-glyph` when the copy is one line — so a
`through-window` looks through the letterforms (`seams.tsx` reads every drawn glyph holder, one clip run per
grapheme) and a `container` / `grow` takes hold of the type itself. It moves nothing: the glyphs land where they would
unwrapped. `carry_anchors.py` credits `word` to any register that draws `<KineticWord`.
**Reach for it:** the line in a kinetic register that a seam should be able to carry or push into.
**Smallest real use:** `<KineticWord k={head} x={x} y={y} color={FG} motion={m} id="headline" />`
**Exports:** `KineticWord`, `kineticExtent`.

### `kineticDom`
The attributes a KineticText writes and the census reads, in one module both import — so a writer and a reader
cannot spell one two ways — plus `kineticIdle()`, which every DOM audit awaits so it never walks a frame whose glyphs
are still being measured (the first cut-off probe came back clean for exactly that reason), and `facesReady()`, the
bundled faces' load published by `fonts` without importing it.
**Reach for it:** never in a register; know it is how `textSafe` and `titleProbe` find kinetic lines.
**Smallest real use:** (written by `kinetic`, read by the census)
**Exports:** `KIN_ROOT`, `KIN_LINE`, `KIN_GLYPH`, `KIN_ALT`, `KIN_READ`, `KIN_ALIGN`, `KINETIC_HOLDS_TAG`, `kineticBusy`, `kineticIdle`, `facesReady`.

### `readingSpec.json`
How long words take to read, each figure with its source inside it: characters per second per script (zh 9, ja 4,
Latin 20 — the Netflix timed-text guides), the 5/6 s floor, and ~0.6 s a word for copy that must be taken in. ONE
table, read by the TypeScript that paces kinetic type and by the Python that judges it.
**Reach for it:** pacing anything that must be read (through `kineticCore`); never restate a number.
**Smallest real use:** `const need = READING.cps.zh;` (`import READING from '@runtime/readingSpec.json'`)
**Exports:** `cps`, `minSeconds`, `mustReadSecondsPerWord`, `sources`.

## Maths and figures that transform

### `mathMorph`
Typeset maths that moves — the film's TeX drawn from its real glyph outlines (MathJax 3.2.2's TeX fonts, typeset
ahead of the render by `scripts/tex_glyphs.mjs`, never at render time) and animated the way a maths explainer needs:
written on (outline, then fill), carried into its next form (shared marks travel, the rest leave and arrive), a term
picked out, a number running live. `useEquations` reads the library's equations from the bundle and a film's from
`<out_dir>/_math/` (written by `scripts/mathtex.py`, which `render_remotion.py` runs before its first render); a TeX
nobody typeset cancels the render by name. `MathLayer` bakes each glyph's matrix into its outline (so a stroke is
the same width on a superscript as on a big operator) and marks the root so every type gate reads the equation as ONE
line named by its TeX. Re-exports the whole of `mathCore`.
**Reach for it:** any beat whose content IS an equation or a derivation — never set maths as a Unicode string in a
text face (`CompressedSensingEq` did; it can neither typeset a fraction nor move like maths).
**Smallest real use:** `const eqs = useEquations([texA, texB]); if (eqs) { const {pl} = placeAll(eqs, box, U * 0.11);
const m = matchGlyphs(eqs[0], eqs[1], pl[0], pl[1]); return <MathLayer draws={transformState(eqs[0], pl[0], eqs[1],
pl[1], m, p)} tex={texB} emPx={pl[0].s * 1000} W={W} H={H} ink={fg} accent={acc} />; }`
**Exports:** `useEquations`, `MathLayer`, `bake`, `frameAround`, `inLibrary`, `MATH_DIR`.
A TeX error is MathJax's own message at prep time ("Missing close brace"); CJK inside the maths is refused (it would
be set in whatever face the browser finds) — words go in the register's label props. `\class{name}{…}` names a term:
the same name in two forms is matched as the same term, and it is how a register addresses a term to highlight or a
`live…` slot to run a number in.

### `mathCore`
The pure half of `mathMorph`, no DOM, runnable in node. Manim's ideas reimplemented from their behaviour: `writeState`
(Write / DrawBorderThenFill, staggered — the settled frame is the plain typeset equation), `matchGlyphs` +
`transformState` (TransformMatchingTex: named terms first, then the longest run of shared marks in reading order with
ties broken by travel MEASURED WHERE THE GLYPHS ARE DRAWN; two differently named terms never trade a glyph; any pair
whose left-to-right order flips against another travels on an ARC, over the equals sign, not through it), `indicate`
(swell and take the accent; held), `placeAll` (one scale and one baseline for every form; relation signs on one
vertical when the box allows), `liveText` / `liveDraws` (a ValueTracker: the film's `from` and `to` printed exactly at
the ends, digits from the font's own atlas, decimal points on one vertical; a value wider than its template slot
throws).
**Reach for it:** a register that composes its own timeline of writes, transforms and highlights.
**Smallest real use:** `const draws = indicate(stillState(eq, pl, 's'), ids, unionBox(eq, glyphsOf(eq, 'root'), pl)!, p);`
**Exports:** `matchGlyphs`, `transformState`, `writeState`, `stillState`, `indicate`, `placeAll`, `pivotX`, `liveText`, `liveDraws`, `parseLive`, `glyphsOf`, `classesOf`, `unionBox`, `screenMat`, `screenBox`, `scaleAbout`, `lerpMat`, `mul`, `smooth`, `thereAndBack`, `segOf`, `Equation`, `MGlyph`, `GDraw`, `Placement`, `Match`, `Pair`, `Mat6`.

### `mathKey`
The name a typeset equation is filed under — one function, imported by the bundle AND by the node typesetter (which
loads this file directly), so the key a film's prep writes and the key a register fetches cannot be computed two ways.
**Reach for it:** never in a register; the equation hook in `mathMorph` calls it.
**Smallest real use:** `mathKey(tex, true)`
**Exports:** `mathKey`, `normTex`, `MATH_FORMAT`.

### `mathLibrary.json`
The library's own typeset equations (every register default and probe), bundled so a library render is offline. Built
from `mathLibrary.tex.json` by `node scripts/tex_glyphs.mjs --library`; a test rebuilds it and compares the bytes.
**Reach for it:** never by hand — add a register's default TeX to `mathLibrary.tex.json` and rebuild.
**Smallest real use:** (read by `mathMorph`)
**Exports:** `v`, `mathjax`, `eq`.

### `mathLibrary.tex.json`
The list the library cache is built from: `{tex, display, for}` per equation, `for` naming what draws it.
**Reach for it:** when a register's DEFAULT copy is TeX.
**Smallest real use:** `{"tex": "y = e^{-x/2}\\cos 2x", "display": true, "for": "FunctionPlot default"}`
**Exports:** `_why`, `equations`.

### `mathDom`
The two attributes an equation writes and the census reads (`mathMorph` writes them, `textSafe` reads an equation as one
line whose text is its TeX) — its own module rather than more of `kineticDom`, because a constant appended there
re-hashes every kinetic register's measured rows.
**Reach for it:** never in a register.
**Smallest real use:** (written by `mathMorph`, read by the census)
**Exports:** `MATH_ROOT`, `MATH_GLYPH`.

### `pathCore`
Path geometry with no imports: parse any SVG `d` (relative, H/V/S/T and arcs reduced to absolute M/L/Q/C/Z), transform
it, its EXACT bounding box (curve extrema, not the control hull), flatten to polylines, resample by arc length
(monotone by construction), align one loop to another (same winding, least travel). Shared by the bundle and the
typesetter, so a glyph's box and a morph's outline are one geometry.
**Reach for it:** any register that reasons about an outline it was handed.
**Smallest real use:** `const box = segsBBox(parsePath(d));`
**Exports:** `parsePath`, `transformSegs`, `segsToD`, `segsBBox`, `flatten`, `polyLength`, `resample`, `alignTo`, `signedArea`, `centroidOf`, `ptsToD`, `matMul`, `apply`, `IDENTITY`, `Seg`, `Pt`, `Mat`, `Poly`.

### `pathMorph`
One figure becoming the next. `planMorph` resamples both outlines to the same points and aligns them before anything
is lerped; a side with more pieces shares the pieces before it, so one cell drawn twice over itself parts into two.
Measured against `@remotion/paths`' interpolatePath on the same shapes (half-way signed area, 400 px box):
circle→triangle 4,932 there against 90,848 here (endpoints 125,686 · 57,288); a split it refuses outright.
`shapeD` draws a named shape into a box (`count` repeats it side by side); `fitD` scales the film's own 0–1000
outline into one.
**Reach for it:** a diagram that grows, divides, merges or turns into something else.
**Smallest real use:** `const plan = useMemo(() => planMorph(shapeD('circle', box), shapeD('circle', box, 2)), [box]); <path d={morphAt(plan, p)} />`
**Exports:** `planMorph`, `morphAt`, `morphPieces`, `shapeD`, `fitD`, `SHAPE_NAMES`, `ShapeName`, `MorphPlan`.
A split's pieces overlap at its start: draw the body as one path (the fill is laid once) and stroke each piece masked
by the others' interiors, or the copies' outlines cross inside the body (`GrowingFigure` does this).

## The gates' own eyes

### `textSafe`
The audit a standalone render runs when a gate asks: type off the canvas, type in the caption band, type colliding,
copy that never arrived — and words on the frame no prop supplied.
**Reach for it:** never in a register; know it is what `text_safe_qa.py`, `cjk_type_qa.py` and `shot_proof.py` see.
**Smallest real use:** (rendered with `textSafe: true` by `scripts/text_safe_qa.py`)
**Exports:** `TextSafeAudit`, `auditTextSafety`, `auditTypeCollisions`, `auditFedText`, `auditUnfedText`, `UNFED_TEXT_TAG`, `kineticGroups`, `isKineticGlyph`.
A KineticText draws one element per grapheme; every walk here skips those (`isKineticGlyph`) and reads each line once
(`kineticGroups`), so a cut line is one finding named by its text, a block set into itself is one leading finding,
and the type-glide census lists the line with each glyph's own track for the judge to fold back into one run.

### `titleProbe`
Where a settled frame's title sits: its largest type that is not a figure, placed by the edge the line is set from, so
a film's titles can be compared beat to beat (a repeated position is a `text_safe_qa` error).
**Reach for it:** never in a register; know that a big printed figure is not your title and a left-aligned title is
read by its left edge.
**Smallest real use:** (rendered with `titleProbe: true` by `scripts/text_safe_qa.py` `title_of`)
**Exports:** `TitleProbe`, `pickTitle`, `isReadout`, `TITLE_PROBE_TAG`.

### `mediaRes`
How far each raster on a frame (img, video, canvas) is drawn past its own pixels, read from the DOM: natural size
against the drawn box, by object-fit, with the CSS blur and opacity it is seen through.
**Reach for it:** never in a register (no register may import it — it would re-key the measured manifests); know
that every picture you place is judged by it at the peak of any camera push, so draw rasters at or below their own
pixels and rebuild UI natively instead of scaling a small screenshot up.
**Smallest real use:** (rendered with `mediaRes: true` on the Film by `scripts/media_res_qa.py`)
The same census reports every OBJECT's box (`censusObjects`: each kit device, each screen on one, each element marked
`data-object="<name>"`) for `scripts/object_closeups.py`'s 100% close-up sheet — mark every built thing a shot draws.
**Exports:** `MediaResAudit`, `censusMedia`, `censusObjects`, `MEDIA_RES_TAG`.

### `fidelity`
Whether a built thing that depicts a real thing is TRUE to it (references/object-authoring.md rule 7): the
`Fidelity` record's type (`META.fidelity` — subject, references, sourced proportions, parts, materials), the probe
that reads every `data-part="<name>"` node's box and its drawn leaves from the DOM, and the hero composition the
fidelity sheet renders an object alone in.
**Reach for it:** a workshop object types its META with `FidelityMeta`, and marks each defining part
`data-part="crown"` on the node that draws it; never import it into a library register (it would re-key the measured
manifests).
**Smallest real use:** `export const META: FidelityMeta = {aspect: 1, provenance: 'industrial', fidelity: {subject: 'a gear pump', depicts: 'real', references: [...], proportions: {...}, parts: ['housing', 'gear'], materials: ['cast iron']}};`
(the sheet: `python3 scripts/workshop.py <out_dir> fidelity <Name>`)
**Exports:** `Fidelity`, `FidelityReference`, `FidelityMeta`, `FidelityProbe`, `FidelityHero`, `FIDELITY_TAG`, `PART_ATTR`, `PartReport`.

### `styleSpec`
The film's drawing style (`meta.style`, references/style-engine.md) as the renderer reads it: the axis defaults filled
in, plus the generated medium's tiles when the render resolved them.
**Reach for it:** a register that draws an axis itself (a hook) reads the resolved spec; nothing else needs it.
**Smallest real use:** `const style = useStyle(); const boils = (style?.line.boil_hz ?? 0) > 0;`
**Exports:** `StyleSpec`, `ResolvedStyle`, `AXIS_DEFAULTS`, `resolveStyle`, `StyleContext`, `useStyle`.

### `styleAxes.json`
The ONE table of drawing axes — groups `line`, `fill`, `shade`, `shadow`, `form`, `surface`, `type`, `motion` — read by
the renderer and by scripts/style_spec.py alike. A new style is new values here, never a new axis named after a style.

### `style`
The style engine: wraps each beat's register and restyles what it drew, per frame — put back, read, write, so it is
idempotent and order-free. Film and a shot rendered alone mount it; with no style it is its children.
**Reach for it:** never from a register; it is mounted for you.
**Smallest real use:** `<StyleLayer beat={i}>{register}</StyleLayer>` (Film.tsx); `applyDomPass` is what it runs.
**Exports:** `StyleLayer`, `applyDomPass`, `DomPassReport`.

### `styleClassify`
What an element IS to the engine (`classify`: text, shape, box, image, canvas, echo, caption) and the colour arithmetic
it draws with: `inkFor` (an outline that contrasts with what it bounds), `meanColor` (alpha-weighted),
`quantizeStops` / `quantizeAlphas` / `steppedGradient` (cel bands), `toHex`.
**Exports:** `classify`, `Role`, `inkFor`, `meanColor`, `quantizeStops`, `quantizeAlphas`, `steppedGradient`, `toHex`.

### `styleFilters`
The per-pixel half of the engine, built into the layer's own defs: wobble and boil (`wobbleSeed`, a pure function of
the beat clock), the outer ring, hatching, the medium (`SURFACE_NOISE`, `toothMatrix`, a generated tile at `TILE_PX`).
**Exports:** `wobbleSeed`, `Recipe`, `recipeKey`, `buildFilter`, `SURFACE_NOISE`, `toothMatrix`, `TILE_PX`.

### `styleSurface`
The medium as a background layer a box paints beneath its own content, so the type set on it stays clean.
**Exports:** `surfaceTile`.

### `styleMotion`
Drawn motion: `stepFrame` (on twos/threes, applied after the sync warp by Film's BeatClock) and `squashAt`
(squash-and-stretch with the area kept).
**Exports:** `stepFrame`, `squashAt`.

### `styleHooks`
Axes a register draws itself: `STYLE_HOOKS_BY_SHOT` (Film reads it) and `withoutAxes` (the spec without them).
**Reach for it:** a register that exports `STYLE_HOOKS` is listed here, or the engine restyles it anyway.
**Exports:** `STYLE_HOOKS_BY_SHOT`, `withoutAxes`.

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
