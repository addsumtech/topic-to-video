# Design: educational content + informative visuals (Increment 1)

**Date:** 2026-06-20
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal

Today's videos narrate slides over **decorative AI photos**: of the 5-scene SpaceX demo, only the 2 charts carry information; scenes 1/4/5 are generic photoreal b-roll that teach nothing, and 4/5 even **mismatch** their narration (a generic satellite photo under "the market is mostly government orders"). The visual palette (`title · chart · timeline · slide/AI-image`) has no way to render a **conceptual** point informatively, so such beats fall back to empty imagery. The result reads as slides+mood, not a designed educational video.

**Goal (Increment 1):** make the skill design *content* before authoring, and give it **informative** visuals so every beat teaches. Specifically: a **content-planner director agent**, two new **informative visual renderers** (`keypoints`, `compare`), an **energetic many-beats pacing model**, an **informative-first** visual policy, and an **audio↔visual coherence** critic check. Re-prove on the SpaceX deck (rebuilt as ~12–15 informative beats). Everything stays **faithful** (no invented facts/numbers; data in real charts).

## Decisions (from brainstorming)
- **Informative-first:** every content beat uses a programmatic informative visual; photoreal AI demoted to rare atmosphere (opener/closer) or off.
- **Director planner:** the agent designs the storyboard skeleton (beats + per-beat visual + pacing); the assistant authors narration into it; the critic gates faithfulness.
- **Energetic pacing:** ~3–6s beats, many cuts, internal reveals (a ~60s video ≈ 12–15 beats).
- **Increment 1 scope:** planner + `keypoints` + `compare` + pacing + audio/subtitle QA. Later: `diagram`/flow renderer, more types, AI-demotion polish.

## Architecture & data flow
```
deep-understanding (comprehension brief)         [existing step 3]
  → content-planner agent → CONTENT PLAN (beats) [NEW step 3.5]
  → assistant builds storyboard scenes from the plan + authors short narration  [step 4]
  → critic: faithful + subtitle + audio↔visual match  [step 5]
  → edge-tts → sample sign-off → render            [steps 7–9]
```
The planner is a **prose subagent** (sibling to `critic.md`), dispatched on the comprehension brief; it returns a content plan the assistant turns into scenes. The two new renderers plug into the existing animated-scene path unchanged (`render._render_scene` → `getattr(scenes,"render_"+type)`; `_fingerprint` already hashes `type`+`props`; `_encode_frames_clip` muxes frames+audio+captions).

## Component 1 — content-planner agent (`agents/content-planner.md`, new)
A director/educator subagent. **Input:** the comprehension brief + ingested slide text + source material + `meta` (audience, goal, language, target pace). **Output:** a content plan:
```json
{ "arc": "hook → build → payoff → takeaway (one line)",
  "beats": [
    { "id": 1,
      "learning_point": "the ONE idea this beat teaches",
      "source_ref": "slide 2 / paper §3 / web-verified",
      "visual": { "type": "compare", "props": { ... } },
      "narration_intent": "what the line must convey (not final words)",
      "est_seconds": 5 } ] }
```
**Principles it must encode (its rubric):**
- **Deep-understanding-first:** every beat's `learning_point` traces to the material via `source_ref` — no beat without a source. Faithful: never invent facts/numbers.
- **Informative-visual selection:** pick the most informative `visual.type` for the point — a number/trend → `chart` (`kind` bars/line/counter); a decomposition/contrast → `compare`; a conceptual claim or list → `keypoints`; a sequence → `timeline`; a section/transition → `title`. (`visual.type ∈ {title, chart, timeline, keypoints, compare, slide}`; a big-number "counter" is `chart` with `kind:"counter"`.) **Never** assign decorative photoreal to a beat that states a fact; photoreal (`slide` + `image_prompt`) only for a rare atmospheric opener/closer, tagged `broll`.
- **Energetic pacing:** many short beats; one idea per beat; `est_seconds` 3–6; split a dense point into two beats rather than one long hold. Target beat count ≈ `target_video_seconds / 4`.
- **Earn its place:** every beat teaches something; cut filler.
The assistant maps each `beat.visual` to a storyboard scene and authors a short line from `narration_intent`. (The planner advises pacing/visuals; it does **not** write final narration — that stays a separate, critic-gated step.)

## Component 2 — `render_keypoints` (`scripts/scenes.py`, new; PIL, like `render_title`)
Conceptual beats shown as kinetic labeled points (replaces empty b-roll for "X *and* Y" claims).
- **props:** `{ "title": str?, "points": [ {"label": str, "sub": str?}, … ] (1–5), "accent": "#rrggbb"? }`
- **Visual:** optional title top-left; each point a row — accent marker (▸) + `label` (+ smaller `sub`); rows **reveal one-by-one**, staggered, each with a short fade/slide-in (deterministic by frame index, reusing `_ease`). Renders ONLY the given text (faithful-by-construction).
- **Signature:** `render_keypoints(props, meta, W, H, frames, workdir, index) -> pattern` via `_save_frames`; frames `scene_{index:02d}_%04d.png`.

## Component 3 — `render_compare` (`scripts/scenes.py`, new; matplotlib Agg, like `render_chart`)
Decomposition / contrast shown as a labeled split or A-vs-B (turns "165 = 123 + 42" into a real breakdown).
- **props:** `{ "title": str?, "kind": "split"|"versus", "parts": [ {"label": str, "value": num, "note": str?}, … ] (≥2), "total": num?, "accent": "#rrggbb"? }`
- **Visual:** `split` = one horizontal 100%-bar segmented by part proportions, each segment labeled `label` + `value` (+ `note`), built left-to-right; `versus` = side-by-side bars. Bars **grow / segments wipe in** with progress (reuse the chart build/ease). Values come straight from `parts` (faithful).
- **Signature:** matches the renderer signature above; uses `_mpl_font(meta)` for CJK like `render_chart`.

## Component 4 — schema (`scripts/storyboard.py`)
- `VALID_SCENE_TYPES += {"keypoints", "compare"}`; `ANIMATED_TYPES += {"keypoints", "compare"}`.
- `_validate_props`: `keypoints` needs a non-empty `points` list, each item a dict with a non-empty string `label`; `compare` needs `kind ∈ {split,versus}` and a non-empty `parts` list, each item a dict with a string `label` and numeric `value`.
- `new_scene(index, scene_type, props, …)` already handles arbitrary animated types — no change.

## Component 5 — workflow (`SKILL.md`)
- **New step 3.5 — Content plan (director).** After the comprehension brief, dispatch `agents/content-planner.md` on the brief + material. It returns the ordered informative beats (learning point + visual type/data + pacing). Build the storyboard from the plan (**informative-first**); author the short per-beat narration in step 4. 🔴 **CHECKPOINT:** show the content plan (arc + beats + chosen visuals) for the user's OK before authoring narration.
- **Informative-first policy** (replaces the decorative default): conceptual beats use `keypoints`/`compare`/`chart`/`timeline`, **not** photoreal b-roll; AI imagery is rare atmosphere only.
- **Pacing model:** target many short beats (~3–6s; ≈ `video_seconds/4`); the new renderers' internal reveals keep the screen changing.
- **Audio↔visual:** each narration line must match what is on screen (the beat's visual).

## Component 6 — critic (`agents/critic.md`)
Add **R2 — Audio↔visual coherence & informative-first** (cross-refs R1d/R1e):
- Each scene's narration must **match its on-screen visual** — FAIL a mismatch (e.g., a generic photo or unrelated visual under a specific factual claim). 
- **Informative-first** — FAIL a conceptual/factual beat rendered as decorative photoreal b-roll where a `keypoints`/`compare`/`chart`/`timeline` should carry the point; photoreal allowed only as a rare atmospheric opener/closer (`broll`).
- Data stays in faithful charts (existing R1e). The planner's `source_ref` per beat is checkable against the material.

## Data contract example (SpaceX, abbreviated)
```json
{ "index": 4, "type": "keypoints",
  "props": { "title": "进入者能争的，其实很小",
             "points": [ {"label": "对外发射 ≈ 42 次 / 年", "sub": "可被争夺的部分"},
                         {"label": "且多为政府 / 国安订单"} ],
             "accent": "#4C9BE8" },
  "narration": "真正能争夺的，一年大约 42 次，而且多是政府和国安订单。" }

{ "index": 3, "type": "compare",
  "props": { "title": "2025 年的 165 次发射", "kind": "split", "total": 165,
             "parts": [ {"label": "自用 Starlink", "value": 123, "note": "不可争夺"},
                        {"label": "对外（可争夺）", "value": 42} ],
             "accent": "#E8590C" },
  "narration": "这 165 次里，123 次是自己打 Starlink，对外只有 42 次。" }
```

## Error handling
| Condition | Behavior |
|---|---|
| Planner returns a beat with no `source_ref` | Assistant drops/queries it (faithfulness); the critic also flags unsourced claims. |
| Beat assigns photoreal to a factual point | Assistant overrides to an informative type; critic R2 fails it if it slips through. |
| `keypoints` with >5 points | `_validate_props` caps/raises; planner told to split into two beats. |
| `compare` parts missing numeric `value` | `validate` raises `StoryboardError` before render. |
| New renderer throws | Same path as existing animated scenes — surfaces at render with the scene index. |

## Testing (deterministic; no network)
- **`render_keypoints` / `render_compare`:** produce exactly `frames` PNGs named `scene_NN_%04d.png`; handle min/max props (1 vs 5 points; split vs versus; CJK labels); pure function of props (faithful — no text beyond props). Mirror existing `scenes` tests.
- **schema:** `keypoints`/`compare` validate with good props; bad props (empty points, non-numeric value, bad `kind`) raise; existing types unchanged.
- **render integration:** a storyboard with a `keypoints` and a `compare` scene renders clips via the existing animated path (`_fingerprint` includes the new `props`).
- **critic / planner:** prose — grep R2 + the planner rubric; verified by reading + the SpaceX dry-run.
- Existing suite stays green.

## Out of scope (later increments)
A `diagram`/flow renderer (labeled boxes + arrows), additional visual types, automated AI-image demotion, and a machine-readable plan→storyboard compiler (Increment 1 maps the plan to scenes by hand/assistant). YAGNI for now.
