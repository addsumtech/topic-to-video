# Device Layer · Frames, Screens and Gestures

**Date:** 2026-09-26 · **Status:** design approved in conversation; this written spec awaits review ·
**Scope:** remotion (bespoke-shot) tier · **Sub-project 1 of 3** of the "object layer"

## Problem

The library speaks 185 design languages and cannot draw a phone. Checked against the code, not recalled:

- **No physical device exists anywhere.** No phone, tablet, laptop, monitor, watch, headphones or speaker.
  The "3D" family is a metal ring, point clouds and cards; the "audio" family is waveforms and MRI physics;
  the one "hardware" register is an abstract circuit board. The `film_energy` gate calibrates against Apple's
  *Introducing iPhone 17 Pro* film, and the library cannot depict the object that film is about.
- **App interfaces are desktop SaaS idioms only** (family A: command palette, chat, IDE, terminal, answer
  engine, Loom-style screen, Notion-style blocks, bento). The one reusable interface, `runtime/uiSurface`,
  draws a window whose content is grey placeholder bars — it says "a program", not "this product".
- **Interaction is thin and duplicated.** Cursor-and-click is drawn separately in four registers
  (PointerTour, CollaborativeCursors, ScreenBubble, CursorStory). There is no tap, no swipe or momentum
  scroll, no drag. No register plays a screen recording (0 of 185 embed video).
- **A measured defect in the closest thing to a search bar.** CommandSummon's caret toggles on
  `Math.floor(t * 60) % 2` — a rate tied to the BEAT's length. Rendered at 5 s and measured frame by frame:
  5.6 flashes per second, and it blinks while typing. TermTable's `t * 24` is the same class. The terminal
  registers (TermLog, TermThink) use `frame / 16` — 0.53 s per phase — which is the house standard this
  spec adopts.

The user's request: common product objects — "手机，平板，电脑，耳机，一些app" — and interactions such as
clicking a calendar, typing into a search bar, scrolling content on a phone.

## Decomposition (agreed)

1. **Device frames + screen slot + gestures** — this spec.
2. **Common app templates** (calendar, search with results, chat, mail, settings, feed, player, cart,
   notifications — phone and desktop sizes, content from props only) — a separate spec, built on 1.
3. **Physical hardware** (headphones, speakers) through real photographs or licence-clean 3D models — a
   separate spec. Code-drawn industrial objects read as cartoons; generated images must never stand in for a
   real product.

## Decisions made with the user

Each was shown, not described — mockups rendered in the browser companion, then checked by screenshot:

| Question | Decision | Rejected |
|---|---|---|
| Device look | **A flat** (follows the DNA), **B realistic**, **C screen-only** — all three, switchable | D line-art |
| Screen content | real and code-drawn both supported, **real first** | — |
| How real UI arrives | **screenshots** and **screen recordings** | page URLs |
| Architecture | shared runtime blocks + a few composite registers | many single-purpose registers; any register inside a device |
| Small text in a screenshot | **camera push-in** to the target | magnifier bubble; no zoom |
| Tap / click style | **brand colour**: accent ring + expanding ripple | system style (grey dot, bare arrow) |

Reference renders of the approved choices: `assets/2026-09-26-device-layer/device-looks.jpg` and
`assets/2026-09-26-device-layer/push-in-and-brand-taps.jpg`.

## Non-goals

- **App templates** (sub-project 2). The screen slot defines a `page` source so templates can plug in later;
  no template is built here.
- **Hardware objects** (sub-project 3).
- **Watches.** A round or near-square screen with a crown and band is different geometry; deferred.
- **Rendering existing registers inside a device.** They are composed for a full 16:9 frame; squeezed into a
  phone screen their type becomes illegible and no existing gate would catch it (screenshot text is pixels).
- **Capturing live pages from URLs.** The user supplies screenshots and recordings. `capture_page.py` stays
  PageWrite's.
- **Migrating the four cursor registers to the shared gestures.** Later, when someone is working in them.
  The one exception is the caret: CommandSummon and TermTable adopt the shared caret here.
- **HTML-tier parity.** Not in this spec.

## Design

### 1 · Runtime modules

Three modules, one job each. Every one is a pure function of the frame (frame-seekable; no `Math.random`,
no wall clock), themed only through DNA tokens, and null-DNA-safe like the rest of the runtime.

**`runtime/device.tsx` — draws the device and exports where its screen is.**

- `DeviceKind = 'phone' | 'tablet' | 'laptop' | 'monitor'`; `DeviceLook = 'flat' | 'real' | 'screen'`.
- `deviceGeometry(kind, look, W, H, placement)` returns the body rect, the **screen rect**, the screen's
  corner radius and any cut-outs (the phone's island). The drawing and every consumer that aims at the screen
  — the camera, the gestures, the gates — call this ONE function, the same principle `uiSurface` already
  follows ("a second copy of a rectangle is a second answer, and it goes stale").
- Screen proportions: phone 9:19.5 (portrait), tablet 3:4 portrait or 4:3 landscape, laptop 16:10, monitor
  16:9. The device is placed inside the content zone above the caption band (`contentBottom`) at 16:9,
  9:16, 1:1 and 4:5; at 9:16 a phone fills that zone.
- `<Device kind look placement tilt?>{screen}</Device>` renders the body and clips its children to the
  screen rect and radius.
- Looks:
  - **flat** — body in the DNA's ink/surface tokens, a solid bezel, one soft shadow; the laptop base is a
    trapezoid; the phone has an island. Follows the DNA completely.
  - **real** — a metallic rim and base from gradients over DNA-derived neutrals, a STATIC glass reflection
    (it must not move or flicker), a soft contact shadow, an optional 3/4 tilt via CSS 3D.
  - **screen** — no body: the screen as a rounded, elevated panel; laptop and monitor carry a thin window
    strip. Proportion and radius say which device it is.
- **Default look** when a beat names none: `real` on a dark-keyed beat, `flat` on a light one (the realistic
  body reads heavy on a light ground — noted when the mockups were compared). `screen` is always an explicit
  choice. The default rule is a starting point and can be changed at review.

**`runtime/screen.tsx` — what the screen shows.**

- Sources:
  - `{"image": "ui/01.png"}` — a screenshot, fitted to the screen's WIDTH. Taller than the screen means a
    long screenshot, and it can scroll.
  - `{"video": "rec/demo.mp4", "from": 3.2, "to": 11.0}` — a recording via `OffthreadVideo`, muted by
    default, trimmed, speed-mapped onto the beat (see §3).
  - `{"page": ...}` — a code-drawn page (sub-project 2's templates plug in here).
- Scroll offsets are clamped to `[0, contentH − screenH]` computed from the image's real height. A scroll
  can never reveal blank past the last row except as the end-of-scroll overshoot. (The mockup shipped the
  opposite twice: once scrolling a percentage of the wrong box, once with the list pinned to one screen's
  height by a shared `inset: 0`.)

**`runtime/gesture.tsx` — the gestures, one implementation.**

- **Caret** — solid while keystrokes arrive; after the last keystroke it blinks on the FRAME, 16 frames per
  phase (the TermLog/TermThink standard). Reduced motion: solid, no blink. It sits at the typing HEAD — the
  right edge of the glyphs already typed. Un-typed glyphs take no width. (The mockup's caret sat where the
  whole word would end, because invisible glyphs still took space.)
- **Type** — Latin one character per keystroke; CJK committed a word at a time, as an input method commits.
  There is no word segmenter in the runtime (`cjkType.ts` has none), so CJK text is chunked into two-glyph
  words by default, or exactly as the author wrote it when `type` is given as an array
  (`["上周", "的", "客户", "反馈"]`). Keystroke intervals vary by a deterministic, hash-seeded jitter.
- **Tap** (phone, tablet) and **click** (laptop, monitor) — ONE step with two spellings; what is drawn
  follows the device kind, never the word the author used. Accent ring plus one expanding ripple; on a
  laptop or monitor the cursor also travels there on an eased path and presses.
- **Scroll** — momentum (fast start, eased stop), a short overshoot at either end and a spring back.
- **Drag** — from one point to another, finger or cursor by device kind.

**Camera push-in (legibility).** The camera moves over the device using `pageCam2D`'s key interpolation
(`camAt`, `clampToPage`): it eases in to the active target before the gesture, holds through it, and eases
out. The zoom is COMPUTED: the smallest zoom at which the text at the target is as tall, in rendered frame
pixels, as the film's own caption glyphs — INK height, measured once per film from a caption line rendered at
the film's caption size (`CAPTION_SIZE_FRAC`) in the film's language. It is capped at **4×** by default: past
that the viewer loses where on the screen the action is. The cap is a design choice to tune on real films, not
a measured fact. `"camera": "still"` turns the push-in off.

### 2 · Registers

- **`DeviceDemo`** — one operation, as a script of steps (§3). The device arrives on the first `screen`
  step, each gesture happens on its cue, the camera pushes in where the text would be too small.
- **`DeviceHero`** — the "this is the product" beat: the device enters, turns slightly and settles; its screen
  shows one screenshot or recording. No gestures.

Both join family A in `LIBRARY.md` and go through everything a new register already goes through: a shot
card, the `Root` composition, `register_energy`, `prop_reach`, ground reach and luma rows, the content
contract (every picture element from props; refuse past capacity or when a piece is missing), the signature
table, and the caption-band and text-safe gates.

### 3 · The step script, and the Python side

```json
{"shot": "DeviceDemo", "shot_props": {
  "device": "phone", "look": "real",
  "steps": [
    {"screen": {"image": "ui/01-home.png"}},
    {"type": "上周的客户反馈", "into": [0.5, 0.11], "at": {"cue": "搜索"}},
    {"tap": {"text": "反馈汇总"}, "at": {"cue": "点开"}},
    {"screen": {"image": "ui/02-list.png"}, "via": "push"},
    {"scroll": 0.6, "at": {"cue": "往下看"}}
  ]}}
```

- **Step kinds:** `screen` (with `via`: `push` | `fade`), `type` (+ `into`), `tap` / `click`, `scroll`
  (fraction of the long screenshot's overflow), `drag` (`from`, `to`), and on recordings `mark` (a ring and a
  push-in on a point — a recording already contains its own cursor or finger, so no gesture is drawn on it).
- **Targets:** `[x, y]` as fractions of the screen, or `{"text": "反馈汇总", "nth": 2}` found by text
  recognition at build time (below).
- **Timing:** `at` names words the narration says (`{"cue": ...}`, the existing convention). Steps without
  `at` are spread evenly across the beat, in order. Each step has a minimum duration by kind, and the beat's
  capacity follows from its length. Initial values — design choices to tune on real renders, not measurements:
  tap/click 0.6 s (arrive, ripple, read), a Latin keystroke 0.15 s, a CJK word commit 0.35 s, scroll 0.9 s,
  a screen change 0.5 s.
- **Cues inside the script.** `resolve_cue_props` resolves only TOP-LEVEL props today. It is generalised to
  any `{"cue": ...}` anywhere in the props, and the cues inside one script resolve IN ORDER — each search
  starts after the previous step's match, so a phrase spoken twice lands on two successive steps.
- **Text targets.** Resolved in Python at build time and written back as coordinates, so the per-beat cache
  keys pick them up. Recognition uses macOS Vision through a small Swift helper when on macOS (Chinese and
  English), tesseract when installed elsewhere; results are cached per screenshot content hash. Nothing is
  guessed: see §4.
- **Media facts are read, not declared.** Screenshot dimensions come from the file (as PhotoPlate's
  `imageAspect` already does); recording duration, frame rate and size from `ffprobe`.
- **Recordings map onto the beat.** `from`–`to` is spread across the beat; if `mark` steps carry cues, the
  mapping is piecewise-linear between them. The rate is capped at 2× by default.

### 4 · Errors — refuse, never guess

Pre-render, from `validate.py`, each message naming the beat, the step and the measured shortfall:

- a script that does not open with a `screen` step (the device would arrive showing nothing);
- a missing screenshot or recording; a target outside `[0, 1]`;
- a cue the narration does not say; cues resolving out of order;
- steps that cannot fit the beat (the time each needs against the time there is);
- `from`/`to` outside the recording; a recording that needs more than 2× to fit;
- a screenshot WIDER than its screen's proportion allows (a desktop capture in a phone). Taller is fine —
  it becomes a long screenshot;
- a text target that is not found, or is found more than once without `nth` — the message lists the text
  that WAS recognised; a text target on a machine with no recogniser — the message says to give coordinates.

At render time the registers throw past capacity or on a missing piece, as the library already does.

### 5 · Checks and tests

- **Legibility gate (warning).** At each gesture's moment, the text under the target, in rendered frame
  pixels after the push-in, against the film's caption glyph height (the same measure §1 zooms to). Text height comes from
  recognition boxes when available, else from the screenshot's pixels (the band of ink rows under the target
  point). *Amended in implementation (rulings R21, R22): a recognition box is the recogniser's LINE box, 1.1–1.6× the
  ink and different for identical rows, so the height is the INK of the target's line, looked for inside its
  recognition box; a line whose ink cannot be isolated from its neighbour falls back to the box height and is
  reported.* If the capped zoom cannot reach it, a warning with both numbers. It reports how many targets it
  actually measured, so an unmeasured target is never read as a passing one.
- **The three traps from the mockups, as render assertions on real frames:** the tap ripple's centre lands
  inside the target's box; the caret's x equals the typed glyphs' right edge (±2 px); a settled scroll shows
  no blank beyond the last row.
- **Unit tests:** device geometry (every kind × look × aspect keeps the device above the caption band); target
  conversion; nested, in-order cue resolution including a repeated phrase; capacity; one test per error in §4;
  recognition with a stubbed recogniser, and the real macOS helper skipped where it cannot run.
- **Render tests:** real screenshot fixtures — tap position, post-zoom text height, caret position, scroll end,
  and a recording frame at a known time.
- **Mutation checks** on targeting and timing, each test shown to fail against a mutant.
- **The caret fix:** CommandSummon and TermTable render through the shared caret; a render test measures the
  blink rate (solid while typing, 16-frame phases after).
- **A contact sheet** for review: the three looks × 16:9 and 9:16.

### 6 · Integration

- `agents/shot-director.md` learns when a beat is a device beat (the narration describes doing something in
  the product) and how to write the step script.
- The interview's grounding question (⑥) names screenshots and recordings as material a product-demo film can
  use, so they are asked for when the purpose is a how-to or a launch.
- `SKILL.md`: the two registers in the tools list, and the step-script format.

## Risks

- **Recognition is macOS-first.** Elsewhere, without tesseract, text targets must be coordinates. Stated in
  the error, not hidden.
- **The pixel-based text-height fallback is a heuristic.** Busy backgrounds can mislead it; that is why the
  legibility gate warns and never blocks, and reports its coverage.
- **Recording decode cost.** `OffthreadVideo` adds decode time per frame; measured during implementation, and
  the per-beat cache limits it to beats that changed.
- **The realistic look on light films.** Mitigated by the default rule in §1; the author can always choose.

## Success criteria

- A `DeviceDemo` beat in a real film: a device, the product's real screenshots, type → tap → scroll on the
  narration's words, readable at every tap, passing every existing gate, cached per beat.
- Measured on renders: taps land on their targets, the caret stays at the typing head, a scroll ends exactly,
  and CommandSummon's caret no longer blinks at 5.6 per second.
