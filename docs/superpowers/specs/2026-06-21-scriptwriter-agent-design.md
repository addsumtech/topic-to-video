# Design: scriptwriter agent (the WRITE specialist)

**Date:** 2026-06-21
**Skill:** slides-to-video
**Status:** approved (brainstorming) → implement (prose-only, proportionate)

## Problem & goal

The skill splits scripting into three roles but only staffs two. The **content-planner**
(`agents/content-planner.md`) does PLAN — beats with `learning_point`, `source_ref`,
`narration_intent`, `est_seconds`. The **critic** (`agents/critic.md`) does CHECK — R0 factual
fidelity + subtitle correctness. The middle role, **WRITE** (the manuscript), has no specialist:
narration is authored inline by the assistant following `references/narration-writing.md`. Result:
the manuscript is the weak link. **Add `agents/scriptwriter.md`** — a dedicated WRITE specialist —
so the pipeline becomes PLAN → WRITE → CHECK.

## Decisions (from brainstorming)
- Works **with OR without** a content plan (non-director decks still benefit — it writes from the
  comprehension brief + per-slide intent when no plan exists).
- **Prose-only, proportionate process:** one new agent + SKILL.md step-4 rewiring + a one-line
  critic cross-ref. No code, no test cycle → implement + single review pass + merge (no full SDD).

## The agent — `agents/scriptwriter.md` (new)

**Role:** turn the plan + material into a polished, connected, faithful SPOKEN manuscript.

**Inputs** (whatever is available):
- The **content plan** (ordered beats: `id`, `learning_point`, `source_ref`, `narration_intent`,
  `est_seconds`) — or, if absent, the per-slide intent/notes.
- The **comprehension brief** + the **source material** (for grounding + verification).
- `meta.language` (write in this language) + the target pace ceiling (seconds-per-slide).

**Output:** `{ id → narration }` (the final spoken line per beat) **plus** a `flags` list naming any
beat it could NOT fully source (never paper over a gap — surface it).

**Rubric (its quality bar — draws on + extends `references/narration-writing.md`):**
1. **Whole-script pass, not beat-by-beat.** See the full arc first; write a real **hook**, genuine
   **beat-to-beat transitions**, and a landing **takeaway**. (This is what inline authoring does
   weakly.)
2. **Spoken, not bullets.** One idea per sentence; address the viewer ("you"); expand acronyms on
   first use; never read slide bullets verbatim.
3. **Concision to the pace ceiling.** Fit each line to its `est_seconds` using the guide's rate
   math — CJK ~4–6 chars/s (8 s ≈ 35–45 chars); Latin ~2.5 words/s. Prefer shorter.
4. **Anti-AI-slop.** Ban filler/restatement: 换句话说 / 说白了 / 首先其次综上 / "in conclusion" /
   "as we can see" and similar throat-clearing.
5. **Strictly faithful.** Every claim & number traces to `source_ref` or the material. Invent
   nothing (no numbers, names, citations the source doesn't support). A forward-looking aside is
   allowed only if explicitly flagged as the author's own. Anything unsourceable → **flag it**.
6. **Audio↔visual aware.** The words match what is on screen for that beat (so the critic's R2
   passes) — describe/support the beat's visual, don't drift.
7. **Draft → tighten.** Write a first pass, then cut every word that doesn't earn its place before
   returning. Return ONLY the narration JSON (+ flags), no commentary.

## Workflow rewiring (`SKILL.md` step 4)
Step 4 "Author narration" changes from *the assistant writes it inline* to:
> **Dispatch `agents/scriptwriter.md`** on the content plan (or per-slide intent) + the
> comprehension brief + material + `meta.language` + pace. Write the returned lines into each
> scene's `narration`. Resolve any `flags` (drop/repair the unsourced beat) before proceeding.

Then steps 5+ are unchanged: the **critic** checks faithfulness + subtitles, the 🔴 script sign-off
gate, then TTS. `references/narration-writing.md` stays the style basis the scriptwriter uses.

## Critic cross-ref (`agents/critic.md`)
A one-line note that the narration now comes from `agents/scriptwriter.md` (PLAN → WRITE → CHECK),
and the critic remains the independent CHECK — unsourced/AI-slop/over-long lines are still failed
here regardless of who wrote them.

## Error handling
| Condition | Behavior |
|---|---|
| A beat cannot be sourced | Scriptwriter returns it in `flags`; the assistant drops/repairs it; the critic also fails unsourced claims. |
| No content plan (simple deck) | Scriptwriter writes from the comprehension brief + per-slide notes/intent. |
| Line overruns the pace ceiling | Scriptwriter tightens to the char/word budget; if still dense, it flags the beat to split. |

## Out of scope
Rewriting `references/narration-writing.md` (the scriptwriter references it as-is); any code or
test changes; multi-voice/dialogue scripts. The scriptwriter writes single-narrator narration.

## Validation
Prose-only: a single review pass on the diff (contract aligns with content-planner output + critic
R0; SKILL.md step 4 correctly rewired; no contradiction). Then re-prove qualitatively by
regenerating a demo's manuscript via the agent. Existing test suite unaffected (no code change).
