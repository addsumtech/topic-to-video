# Adaptive Build · A Film Makes What It Needs

**Date:** 2026-09-27 · **Status:** design approved in conversation; this written spec awaits review ·
**Scope:** both tiers; **this spec builds sub-project 1** (the shared build flow + the remotion tier) and outlines
sub-project 2 (the HTML tier), which gets its own spec.

## Problem

The user: a film needs objects and templates the library does not have — "你可以创作出相应的物件来与模版结合，
或者发挥你的创新能力来制作新的模版" — the skill must adapt on the fly, never assemble only from what exists, in the
remotion tier AND the HTML tier, and without losing any capability it has now.

Checked against the code (read-only survey, 2026-09-27):

- **The doctrine already says "build"; the machinery makes it expensive.** `agents/shot-director.md` Step 0.5 asks
  for a `meta.form_vocabulary` of which "at least half must be forms this library does NOT already have", and Rule
  0 records `shot_fit = {verdict: fit|adapt|build}` per beat; shot-critic S1/S10/S14 judge fit, meaning and growth.
  But a "build" today means writing a new register INTO THE SHARED LIBRARY mid-film: `register_shot.py` edits the
  tracked `registry.ts`, `Root.tsx`, `shotLuma.ts`, `LIBRARY.md`, the family tables — and full registration then
  needs the library measurements (register_energy, prop_reach, ground reach, luma: from minutes with `--only` to
  ~10 min for the full luma run). `register_shot.py`'s own header: "The library can grow... In practice it almost
  never did, and the reason was friction, not permission."
- **There is nowhere for a film's own thing to live.** No film-local register exists; the only `out_dir/bespoke/`
  machinery belongs to a renderer removed in the phase-3 cutover (validate.py still lints it; nothing renders it).
- **An object cannot be put into a template.** Registers are monolithic; none accepts a component from outside.
  "Keep this register's layout, draw THIS film's object in its hero area" is not expressible.
- **Half the building blocks are undocumented.** `references/remotion-shot-authoring.md` covers pageCam2D, icons,
  uiSurface, dna, layout, motion, atoms, depth, voice, focus, figure, shotLuma. Nothing an author reads mentions
  aimCamera, stage3d, device, screen, gesture, light, finish, draw, rows, evidence, alongPath, project3d, fitCamera,
  onAccent, atmosphere or cjkType — they are discoverable only from their own source headers.
- **The HTML tier invents compositions, never objects.** Pages may use only CSS animations (`assets/html/seek.js`
  freezes them for capture); there is no CSS 3D, no camera, no cursor/click; `references/html-pages.md` bans "SVG
  depicting realistic scenes/figures"; `references/html-templates.md` lists Sankey, heatmap, trees, pyramid, funnel
  as "not deliverable"; a bespoke composition lives in one page and is never reused.

## Decisions made with the user

1. **Film-local first, promotion by choice.** What a film builds belongs to that film (its out_dir); at delivery the
   user picks which built things are promoted into the shared library, and only those pay full registration.
2. **The HTML tier gains 3D, camera and click — in CSS only**, keeping the seekable CSS-animation contract (no JS
   timelines, no new dependencies). *(Sub-project 2.)*
3. **Approach A — a per-film workshop**, object slots, a building-block reference, the director/critic flow and
   promotion — over B (build straight into the library: contradicts 1, pollutes the library, re-measures often)
   and C (one object description language for both tiers: expressiveness capped by the language — the removed
   generic-scene renderer was removed for exactly that blandness).
4. **Two sub-projects**: 1 = shared flow + remotion tier (this spec); 2 = HTML tier (its own spec).
5. **Acceptance films**: MRI imaging principle, how a coffee machine extracts, a product launch (an app + a
   device), a city's change over time — 4–6 beats each, Chinese narration; sub-project 1 makes their remotion
   versions, sub-project 2 their HTML versions.
6. **No regression** (the user, in so many words: "不会降低当前的能力，更多是在当前基础进一步提升"): a film
   with no workshop renders exactly as before; every existing gate stays; the full suite stays green.

## Non-goals (this spec)

- The HTML tier (sub-project 2).
- Importing real 3D models (glTF) or photographing hardware — the device layer's sub-project 3.
- Automatic promotion into the library.
- Slots on every existing register (a curated set only, below).

## Design

### 1 · The flow (shared by both tiers)

1. **Need first.** For each beat the director first writes the IDEAL picture — the specific thing a viewer must see
   (an object, a mechanism, a relation) — and only then searches the library. Each beat resolves to one of:
   - **fit** — a library register carries it as it is;
   - **object** — a library template (a register with an object slot, or a stage register) plus a new object;
   - **shot** — a new film-local register (a new template).
   (`adapt` keeps its current meaning: a library register re-sized and re-worded for the beat, its structure
   unchanged.) The existing `form_vocabulary` rule stays, and stops being only a warning: every form the library lacks becomes
   an entry of the film's **build list** (`meta.build_list`):
   ```json
   {"id": "EspressoPuck", "kind": "object", "beats": [3, 4],
    "means": "water forced through a compacted puck — the resistance is the point",
    "slot": "ObjectStage", "uses": ["draw", "alongPath", "light"],
    "accept": "caption hidden, a viewer still sees water pushed through a packed bed"}
   ```
   `kind` is `object` or `shot`; `slot` names the template (a slotted register, a stage register, or `own` for a
   shot). A beat that uses a built item says so: `shot_fit = {verdict: "build", ref: "<id>", why: "..."}`.
2. **Build.** Each entry is written in the film's workshop (§2), composed from the runtime building blocks, with the
   building-block reference (§4) open. Its standalone settled frame is rendered and looked at before it enters the
   film.
3. **Check.** Every built item passes the gates a library register passes when a film uses it: type-check, the
   content contract (text only from props, no invented numbers), text-safe, caption band, CJK type, shot_proof —
   then the film renders. The critic judges each built item on its rendered frames (§5).
4. **Promote.** At delivery the skill lists the film's built items with their settled frames and gate results and
   asks the user (selectable options) which to promote; `scripts/promote.py` moves each chosen one into the library
   and runs its full registration and measurements.

### 2 · The workshop (remotion tier)

**Layout** — per film, all optional:
```
<out_dir>/workshop/
  objects/<Name>.tsx   export const <Name>: React.FC<ObjectProps & {...}>, export const META = {...}
  shots/<Name>.tsx     a film-local register: export const <Name>, export const DURATION
  assets/...           imported by the tsx, so the bundler carries them
  index.ts             GENERATED by scripts/workshop.py from the two folders — never hand-edited
```
Workshop code imports `react`, `remotion`, the runtime as `@runtime/<module>`, and library registers as
`@shots/<Name>` (a film-local shot may wrap a library register and add to it).

**Into the bundle without touching tracked files.** `remotion/remotion.config.ts` gains a webpack override:
alias `@workshop` → the directory in env `SLIDES_WORKSHOP` when set, else a tracked stub `src/workshop/none.ts`
(empty maps); aliases `@runtime`, `@shots`; and `resolve.modules` puts `remotion/node_modules` first so bare
imports from outside the project resolve. `registry.ts` merges `WORKSHOP_SHOTS`; `Root.tsx` adds one composition
per workshop shot (the gates render beats by composition id). A workshop name equal to a library name is refused.
*Verified in a throwaway spike (2026-09-27, remotion 4.0.486): with the env unset the workshop composition does not
exist and library compositions are unchanged; with it set, a `.tsx` outside the project importing
`react`/`remotion`/`@runtime/motion` rendered through `npx remotion still` with its props, and a library shot still
rendered.* The `npx remotion bundle` (per-beat segments) path must be proven the same way (plan, first task).

**One way in.** `scripts/workshop.py` owns the workshop: `prepare(out_dir)` regenerates `index.ts` and returns
the environment for any remotion call scoped to that film (`SLIDES_WORKSHOP` set only when the workshop exists).
Every film-scoped remotion call goes through it: whole-film and per-beat renders (`render_remotion.py`,
`remotion_segments.py`) and the film-mode gates (`text_safe_qa.py`, `shot_proof.py`, `cjk_type_qa.py`).
Library-mode sweeps (register_energy, prop_reach, ground reach, luma) run without it — the stub — so library
measurements never see a film's workshop. Two films rendering at once each bundle their own workshop.

**The cache sees the workshop.** `remotion_segments.code_files()` adds every file under the film's workshop when
one is in use, so editing a built item re-renders the beats that could show it.

**validate.py** accepts a beat's `shot` from the library OR the workshop; checks `meta.build_list` both ways (every
entry exists in the workshop and is used by a beat; every `shot_fit.ref` names an entry); and runs `workshop.py
check`: a type-check of the workshop against a generated tsconfig (the project's own settings, the workshop
included, the three aliases as `paths`) and the content-contract scan over workshop files.

### 3 · Object slots

**The contract** — `remotion/src/runtime/objectSlot.tsx`:
```ts
export type ObjectRef = {id: string; props?: Record<string, unknown>};
export type ObjectProps = {w: number; h: number; t: number; dna: DesignDNA | null};
export const ObjectSlot: React.FC<{object: ObjectRef; box: Rect}>;
```
`ObjectSlot` resolves `id` in the workshop's objects, then in the library's promoted objects
(`remotion/src/objects/`), and draws it at the box's size with the beat's clock and Design DNA. An unknown id
throws with the ids that exist — never a blank. Objects take every word from props; sizing follows the box.

**Where slots go:**
- **Device screens** — DeviceDemo's `screen` steps and DeviceHero's `screen` accept `{"object": {"id": ...}}`:
  a film-drawn interface or scene on the device. Text targets need a screenshot, so steps on an object screen
  target coordinates.
- **Existing registers with a natural hero area** — a curated set chosen by a survey in the plan (criteria: one
  dominant figure region, props-driven, not type-led). Each gains an optional `object?: ObjectRef` drawn in that
  region. **Absent, the register renders pixel-identically to before** — a test per slotted register.
- **New stage registers** (library, fully registered and measured), built to hold an object: `ObjectStage` (one
  hero object with its labels), `ObjectCompare` (two objects, one difference named), `ObjectPath` (an object moved
  through named stations), `ObjectTurntable` (an object turned in 3D). An object that wants to be exploded or
  cut away implements that itself, driven by its `t` — the stage frames it.

### 4 · Documentation the builder reads

- **`references/building-blocks.md`** (new): every runtime module — what it does, when to reach for it, the
  smallest real use — including the undocumented half listed in Problem; plus **recipes** for the objects films
  keep needing: a mechanism in cutaway, liquid or particles moving through a path, a turntable, layered strata, a
  route on a map, an interface being operated.
- **`references/object-authoring.md`** (new): an object ENCODES its beat (hide the caption — it still carries the
  idea); it is a designed diagram, not a code-drawn imitation of a photograph (when realism is needed the existing
  documentary tier composites a real image); words only from props, no invented figures; it sizes to its box; it
  is a function of `t`, frozen at any frame; three good and three bad examples, each rendered.
- **SKILL.md** (cinematic-tier workflow) and **`agents/shot-director.md`**: the need-first step and the build
  list; **`remotion/cards/`** for the new stage registers; LIBRARY.md via `register_shot.py` as today.

### 5 · The critic

`agents/shot-critic.md` gains **S15 · BUILT THINGS**: for every build-list entry, on its settled frame and in the
film's frame — does it carry its beat's `means`; can a first-time viewer name it in about a second; does it belong
to this film's Design DNA; is it better than the library's nearest register would have been. And the existing
"should have built" check (S1/S14) must name, per beat, why a library register's structure — not just its words —
carries that beat.

### 6 · Promotion

`scripts/promote.py <out_dir> <Name>`:
- a shot → copied into `remotion/src/shots/` with its aliases rewritten to relative imports, wired by
  `register_shot.py`, then measured in the order the device layer taught (ground reach before energy and prop
  reach, then the full luma run, then CJK), with a card written from its build-list entry;
- an object → copied into `remotion/src/objects/`, added to the library object index, catalogued in LIBRARY.md.
Refused when the item has not passed the film's gates or its name exists in the library.

## Errors — refuse, never guess

A workshop name equal to a library name; an `object` id nobody defines; a build-list entry with no file, or a file
no beat uses; a type error or a baked string in workshop code; a `verdict: build` without a `ref` — each is a
validate error naming the beat and the fix. `workshop.py` never writes outside the film's workshop.

## Risks

- **Bundler behaviour outside the project** (module resolution, fonts, assets) — proven for `still`; the plan
  proves `bundle` + per-beat render first, before anything depends on it.
- **Built things that are ugly or say nothing** — the object-authoring doctrine, S15, and the acceptance films
  looked at frame by frame are the defence; a gate cannot measure meaning.
- **Longer films to make** — building costs time; each acceptance film reports its build time.
- **Retrofit regressions** — every slot is optional and pixel-tested absent; the library stays measured.

## Success criteria

1. A film with no workshop renders frame-identically to before (an existing film re-rendered before and after, every
   decoded frame equal), and the full suite passes.
2. The four acceptance films (remotion versions) each build at least two items — objects and templates both
   across the set — pass validate, text_safe_qa, shot_proof, cjk_type_qa and the critic, and are looked at frame by
   frame; their contact sheets and videos are delivered.
3. At least one built item is promoted with `promote.py` and ends fully registered and measured.
4. The building-block reference covers every runtime module.

## Sub-project 2 (HTML tier) — outline for its own spec

A CSS-only kit under `assets/html/`: a 3D stage (perspective, preserve-3d, turntable/explode keyframes), a page
camera (a transformed wrapper moved between cue-timed poses), and cursor / tap / typing (keyframed, cue-timed) —
all seekable by `seek.js`; film-local HTML objects and page templates in the film's workshop, included into pages
and reused across beats; the "no realistic SVG" rule redefined as "designed, decodable objects"; the same build
list, S15-equivalent in design-critic, and the four acceptance films' HTML versions.
