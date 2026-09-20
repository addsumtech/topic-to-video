// SHOT · TaskFold — beside the companion, only the MAIN tasks hold a place. Each task's background work shows
// for a moment as rows of its own, then folds up into its parent and leaves a count behind; a list longer than
// the view scrolls rather than shrinking every card to fit.
//
// WHY IT WAS BUILT. A film about a desktop companion had a beat whose whole sentence was a subtraction —
// 「桌宠旁边只显示主任务，后台的子任务不单独占一个位置」 — and cast it on RackFocus: two lines of type at two
// focus depths. An independent reviewer hid the caption and found a frame that would look identical on any
// topic, under a declared form (「桌边的任务列表」) the library did not hold. The claim has a MECHANISM in it:
// rows that could have had their own slot and fold into their parent instead, and a list that scrolls. Drawn,
// the viewer sees the slots being given back, which is the subtraction; told, they only read about it.
//
// AND IT IS A FORM, NOT A PRODUCT. Any "only the top level is shown, the rest folds in" claim uses it: a job
// queue that groups retries under their job, an inbox that threads replies, a build that folds its steps.
// Every word arrives through props; a task's state is its own (`working` / `waiting`, or none); the count on a
// folded task is the number of subtasks the FILM listed under it, never a number this register makes up.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 210; // 7s

export type FoldTask = {
  /** the main task, as the companion lists it */
  label: string;
  /** its state — drawn only when given; `working` takes the accent, `waiting` the dim ink */
  state?: 'working' | 'waiting';
  /** the background work under it: shown as rows for a moment, then folded into this task */
  subtasks?: string[];
};

export const MAX_FOLD_TASKS = 10;
export const MAX_SUBTASKS = 4;

const DEMO_TASKS: FoldTask[] = [
  {label: 'Refactor the login flow', state: 'working', subtasks: ['run the tests', 'read the config']},
  {label: 'Write the release notes', state: 'waiting'},
  {label: 'Fix the flaky upload test', state: 'working', subtasks: ['retry the job']},
  {label: 'Answer the review', state: 'waiting'},
  {label: 'Clean up the old branch', state: 'working'},
];

export const TaskFold: React.FC<{
  /** the main tasks, top to bottom (1-10) */
  tasks?: FoldTask[];
  /** the words for the two states, as the product says them: [working, waiting] — drawn beside each dot */
  stateLabels?: [string, string];
  /** what a folded count is called — `3 subtasks`, `3 个后台子任务` — printed after the count */
  foldLabel?: string;
  /** one line under the list */
  note?: string;
  /** the companion's own picture (a path in the film's folder); omitted = an abstract sitting shape */
  src?: string;
  /** how many tasks the panel holds before it scrolls — a companion's list is a small panel, not a page */
  visible?: number;
}> = ({
  tasks: TASKS = DEMO_TASKS, stateLabels: SL = ['working', 'waiting'], foldLabel: FOLD = 'in the background',
  note: NOTE = '', src: SRC = '', visible: VISIBLE = 4,
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const portrait = H > W * 1.1;

  if (!Array.isArray(TASKS) || TASKS.length < 1 || TASKS.length > MAX_FOLD_TASKS) {
    throw new Error(`TaskFold needs 1-${MAX_FOLD_TASKS} \`tasks\` (got ${Array.isArray(TASKS) ? TASKS.length : typeof TASKS}). ` +
      'Past ten the list is an inventory rather than what sits beside a companion; every task given is drawn.');
  }
  const tasks = TASKS.map((k, i) => {
    const label = String(k?.label ?? '').trim();
    if (!label) throw new Error(`TaskFold: task ${i + 1} has no label.`);
    if (k?.state != null && k.state !== 'working' && k.state !== 'waiting') {
      throw new Error(`TaskFold: task ${i + 1} ("${label}") has state ${JSON.stringify(k.state)}; use "working", "waiting" or omit it.`);
    }
    const subs = (Array.isArray(k?.subtasks) ? k.subtasks : []).map((x) => String(x ?? '').trim());
    if (subs.some((x) => !x)) throw new Error(`TaskFold: task ${i + 1} ("${label}") has an empty subtask.`);
    if (subs.length > MAX_SUBTASKS) {
      throw new Error(`TaskFold: task ${i + 1} ("${label}") lists ${subs.length} subtasks; at most ${MAX_SUBTASKS} can show before they fold.`);
    }
    return {label, state: k?.state, subs};
  });
  const visible = Number(VISIBLE);
  if (!(Number.isInteger(visible) && visible >= 2 && visible <= MAX_FOLD_TASKS)) {
    throw new Error(`TaskFold: \`visible\` must be a whole number of tasks from 2 to ${MAX_FOLD_TASKS}, got ${JSON.stringify(VISIBLE)}.`);
  }
  const labels = (Array.isArray(SL) ? SL : []).map((x) => String(x ?? '').trim());
  const fold = String(FOLD ?? '').trim();
  const note = String(NOTE ?? '').trim();
  const src = String(SRC ?? '').trim();

  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 40% 38%, #141a26, #080a0f 74%)';
  const FG = dna?.fg ?? '#eef2f8';
  const DIM = dna?.dim ?? '#7c8699';
  const ACC = dna?.accent ?? '#3dd6a4';
  const SURF = dna?.surface ?? '#131a26';
  const LINE = dna?.surfaceBorder ?? dna?.line ?? '#243149';
  const MONO = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const toneOf = (s?: string) => (s === 'working' ? ACC : s === 'waiting' ? DIM : LINE);
  const wordOf = (s?: string) => (s === 'working' ? labels[0] : s === 'waiting' ? labels[1] : '') || '';

  // ── THE MOMENTS: the tasks land; their background work appears as rows of its own (the slot it could have
  // had); the rows fold into their parents (the slot given back); then, if the list is longer than the view,
  // it scrolls. A list that fits simply holds — it has nothing to scroll.
  const n = tasks.length;
  const landStep = Math.min(0.05, 0.2 / Math.max(1, n));
  const landOf = (i: number) => easeOutCubic(clamp01(seg(t, 0.05 + i * landStep, 0.2 + i * landStep)));
  const show = easeOutCubic(clamp01(seg(t, 0.3, 0.42)));
  const collapse = easeInOutCubic(clamp01(seg(t, 0.48, 0.62)));

  // ── GEOMETRY. The panel lives in the content zone; cards are one height; a subtask row is a smaller height.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const notePx = Math.round(U * 0.02);
  const noteH = note ? inkBlockH(notePx) + Math.round(U * 0.02) : 0;
  const PET = Math.round(U * (src ? 0.2 : 0.12));
  const panelW = Math.round(W * (portrait ? 0.8 : 0.46));
  const panelLeft = portrait ? Math.round((W - panelW) / 2) : Math.round((W - panelW) / 2 + PET * 0.55);
  // THE GROUP IS CENTRED IN THE ZONE, and the cards take the room it has. Top-aligned with the note pinned to
  // the zone's floor, a three-task panel sat in the top 40% of the frame over an empty band — the first render
  // of this register read as a list that had not finished loading.
  const petBlock = portrait ? PET + Math.round(U * 0.03) : 0;
  const zoneRoom = Math.max(U * 0.25, zBot - zTop - noteH - petBlock - Math.round(U * 0.04));
  const slots = Math.min(n, visible) + (n > visible ? 0.4 : 0);
  const gap = Math.round(U * 0.016);
  const cardH = Math.round(Math.max(U * 0.07, Math.min(U * 0.115, (zoneRoom - gap * slots) / Math.max(1, slots + 0.5))));
  const subH = Math.round(cardH * 0.58);
  // the panel shows `visible` tasks and a sliver of the next, so a list that continues LOOKS like it continues
  const viewH = Math.min(zoneRoom, visible * (cardH + gap) + (n > visible ? cardH * 0.4 : -gap));
  const groupH = petBlock + viewH + noteH;
  const groupTop = Math.round(zTop + Math.max(0, (zBot - zTop - groupH) / 2));
  const petTop0 = groupTop;
  const viewTop = groupTop + petBlock;
  const pad = Math.round(U * 0.022);
  const labCap = Math.round(cardH * 0.36);
  const labPx = Math.min(labCap, ...tasks.map((k) => fitTextPx(k.label, panelW * 0.58, labCap, {usable: 1})));
  const subPx = Math.round(subH * 0.4), chipPx = Math.round(cardH * 0.21), statePx = Math.round(cardH * 0.22);

  // each task's own height at this frame: its card, plus its subtask rows while they are out
  const heights = tasks.map((k) => cardH + gap + k.subs.length * subH * show * (1 - collapse));
  const tops = heights.reduce<number[]>((acc, _h, i) => acc.concat(i ? acc[i - 1] + heights[i - 1] : 0), []);
  const total = heights.reduce((a, b) => a + b, 0) - gap;
  const settledTotal = n * (cardH + gap) - gap;
  const overflow = Math.max(0, settledTotal - viewH);
  const scroll = overflow > 0 ? easeInOutCubic(clamp01(seg(t, 0.66, 0.92))) * overflow : 0;
  const alive = tasks.some((k) => k.state === 'working') ? 0.5 - 0.5 * Math.cos(t * Math.PI * 2 * 3) : 0;

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* THE COMPANION — what the list sits beside */}
      <div style={{position: 'absolute', width: PET, height: PET, opacity: landOf(0),
        left: portrait ? panelLeft : Math.round(panelLeft - PET * 1.2),
        top: portrait ? petTop0 : Math.round(viewTop + Math.min(viewH, total) / 2 - PET / 2)}}>
        {src ? (
          <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'contain',
            transform: `scale(${1 + alive * 0.02})`, transformOrigin: '50% 100%'}} />
        ) : (
          <div style={{position: 'absolute', inset: 0, borderRadius: '46% 46% 38% 38% / 52% 52% 32% 32%',
            background: `linear-gradient(170deg, ${SURF}, ${dna?.bg ?? '#0b1018'})`, border: `1px solid ${LINE}`,
            boxShadow: `inset 0 ${Math.round(PET * 0.1)}px ${Math.round(PET * (0.22 + 0.14 * alive))}px ${ACC}2a`}} />
        )}
      </div>

      {/* THE LIST — clipped to its view, so a long list scrolls instead of shrinking */}
      <div style={{position: 'absolute', left: panelLeft, top: viewTop, width: panelW, height: viewH,
        overflow: 'hidden',
        ...(overflow > 0 ? (() => {
          const f = Math.max(2, Math.round(cardH * 0.34));
          const grad = `linear-gradient(to bottom, transparent 0px, #000 ${f}px, #000 ${Math.max(f, viewH - f)}px, transparent ${viewH}px)`;
          return {maskImage: grad, WebkitMaskImage: grad};
        })() : {})}}>
        <div style={{position: 'absolute', left: 0, top: -scroll, width: panelW, height: total}}>
          {tasks.map((k, i) => {
            const land = landOf(i);
            const tone = toneOf(k.state);
            const word = wordOf(k.state);
            return (
              <div key={i} style={{position: 'absolute', left: 0, top: tops[i], width: panelW,
                opacity: land, transform: `translateY(${(1 - land) * U * 0.02}px)`}}>
                <div style={{position: 'relative', zIndex: 1, height: cardH, boxSizing: 'border-box', borderRadius: Math.round(U * 0.014),
                  background: SURF, border: `1px solid ${LINE}`, padding: `0 ${pad}px`,
                  display: 'flex', alignItems: 'center', gap: Math.round(U * 0.014)}}>
                  <span style={{width: Math.round(statePx * 0.55), height: Math.round(statePx * 0.55), flex: 'none',
                    borderRadius: '50%', background: k.state ? tone : 'transparent', border: k.state ? 'none' : `1px solid ${LINE}`}} />
                  <span style={{flex: '1 1 auto', minWidth: 0, color: FG, whiteSpace: 'nowrap',
                    overflow: 'hidden', textOverflow: 'ellipsis',
                    font: `700 ${labPx}px/${leading(k.label, 1.2)} var(--f-display, Inter, system-ui, sans-serif)`}}>{k.label}</span>
                  {/* the folded count: exactly the subtasks the film listed under this task */}
                  {k.subs.length ? (
                    <span style={{flex: 'none', color: DIM, opacity: collapse, whiteSpace: 'nowrap',
                      font: `500 ${chipPx}px/1.2 ${MONO}`}}>↳ {k.subs.length}{fold ? ` ${fold}` : ''}</span>
                  ) : null}
                  {word ? (
                    <span style={{flex: 'none', color: tone, whiteSpace: 'nowrap',
                      font: `600 ${statePx}px/1.2 ${MONO}`}}>{word}</span>
                  ) : null}
                </div>
                {/* the background work as rows of its own — then sliding UP UNDER the card and gone: the
                    slot it held is given back. Rows keep their size (squashing them overprinted the text). */}
                {k.subs.map((sub, j) => (
                  <div key={j} style={{position: 'absolute', left: Math.round(pad * 2.2), right: pad, zIndex: -1,
                    top: cardH + (j * subH) * (1 - collapse) - (cardH * 0.6 + j * subH * 0) * collapse,
                    height: subH, opacity: show * (1 - collapse),
                    display: 'flex', alignItems: 'center', gap: Math.round(U * 0.01),
                    color: DIM, font: `500 ${subPx}px/${leading(sub, 1.2)} ${MONO}`}}>
                    <span style={{opacity: 0.6}}>└</span><span style={{whiteSpace: 'nowrap'}}>{sub}</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
        {/* the scroll track: present only when there is something to scroll */}
        {overflow > 0 ? (
          <div style={{position: 'absolute', right: 0, top: 0, width: Math.max(2, Math.round(U * 0.003)),
            height: viewH, background: LINE, opacity: 0.5}}>
            <div style={{position: 'absolute', left: 0, right: 0, background: DIM,
              height: viewH * (viewH / settledTotal), top: (viewH - viewH * (viewH / settledTotal)) * (scroll / overflow)}} />
          </div>
        ) : null}
      </div>

      {note ? (
        <div style={{position: 'absolute', left: panelLeft, width: panelW, top: viewTop + viewH + Math.round(U * 0.02),
          color: DIM, opacity: collapse, textWrap: 'balance',
          font: `500 ${notePx}px/${leading(note, 1.35)} var(--f-body, system-ui, sans-serif)`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default TaskFold;
