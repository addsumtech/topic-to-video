# TaskFold

**Identity:** beside a companion, a small panel lists only the MAIN tasks; each task's background work first appears as rows of its own, then slides up under its parent and leaves a count; a list longer than the panel scrolls.

**Use when:** the claim is a subtraction of slots — only the top level is shown and the rest folds in (a companion's task list, a job queue that groups retries, an inbox that threads replies), and "when there are many, it scrolls". **Not when:** the sub-items matter individually (use a list or tree register), or the tasks are a sequence (`InOrder`).

**Motion core:** the tasks land top to bottom (staggered over ~0.05–0.4, laid out for the count); the background rows open their own slots (0.30–0.42); they slide up under their parents and give the slots back while the "↳ N" count fades in (0.48–0.62); if the list is longer than the panel it scrolls to the end (0.66–0.92). The companion breathes while any task is `working`.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `tasks` | the main tasks, top to bottom: `label`, optional `state` (`working` / `waiting`), optional `subtasks` | 1–10 tasks; a label fits the card's width by shrinking one size for all cards. A task's subtasks (0–4) are the rows that fold; the count it leaves is exactly how many the film listed |
| `stateLabels` | the words beside each state dot, `[working, waiting]` | the product's own words for its two states; a task with no `state` shows an empty dot and no word |
| `foldLabel` | what the folded count is called, printed after the number | `个后台子任务` reads "↳ 2 个后台子任务"; empty prints the arrow and number only |
| `note` | one dim line under the panel | fades in with the fold |
| `src` | the companion's own picture from the film's folder | a real character reads as the product; omitted, an abstract sitting shape |
| `visible` | how many tasks the panel holds before it scrolls (2–10, default 4) | fewer than the tasks given makes the panel scroll and shows a sliver of the next card; equal or more and the list simply holds |

**Known traps:**
- Scrolling only happens when `tasks` outnumber `visible`; a beat whose sentence says "it scrolls" must give more tasks than the panel holds.
- Subtask names should not invent work the film cannot source — a generic "后台子任务" is honest when the point is the fold, not the task.

**Refuses:** 0 or more than 10 tasks; a task with no label, an unknown `state`, an empty subtask, or more than 4 subtasks; `visible` outside 2–10.

**Reference:** `remotion/src/shots/TaskFold.tsx`
