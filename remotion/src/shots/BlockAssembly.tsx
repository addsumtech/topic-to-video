// SHOT · Block Assembly — Notion language: a document BUILDS itself block by block. Each block snaps into
// the page (slide-up + settle) top-to-bottom — title, text, callout, to-dos, table. Warm off-white, calm,
// minimal ink (deliberately unlike the loud/dark shots). Deterministic staggered assembly.
//
// A TICK IS THE FILM'S, OR THERE IS NO TICK. The to-do block used to tick and strike through the first two
// items of whatever list it was handed (`k < 2 ? '✓'` plus `line-through`), so a film listing three steps it
// had not started shipped a page saying two of them were finished — and a film listing its three findings
// shipped the first two crossed out, as though they had been withdrawn. "Done" is a claim about an item and
// only the film can make it. Each item may now carry `done: true`; an item without it is an open to-do, and
// a list with no `done` anywhere is a list with nothing finished. The standalone demo keeps its two ticks by
// saying so in its own data.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {leading} from '../runtime/cjkType';
import {contentBottom, wrapLines} from '../runtime/layout';

export const DURATION = 165; // 5.5s
// LEVEL-C: the Notion-style light document flips with the DNA (page→bg, ink→fg, blocks/borders→line, accent) → a
// dark document on a dark DNA, the original warm off-white on null DNA.
const INK = '#37352f', DIM = '#e6e3dd', ACCENT = '#2E7BFF';

const Block: React.FC<{i: number; t: number; children: React.ReactNode}> = ({i, t, children}) => {
  const r = easeOutBack(seg(t, 0.14 + i * 0.13, 0.14 + i * 0.13 + 0.24));
  return <div style={{opacity: clamp01(r), transform: `translateY(${lerp(46, 0, clamp01(r))}px)`, marginBottom: 30}}>{children}</div>;
};

const DOC_H = 760;   // the composed stack's height at scale 1, measured from its top at 150, IN LATIN
const DOC_W = 1120;  // the document's own width at scale 1 — the measure every block wraps in

export type BlockTodo = {
  label: string;
  /** true only when the film says this item is finished: it is then ticked and struck through */
  done?: boolean;
};

// Past eight the page has to shrink below ~24px type at 1:1 to fit (it scales as a page, never clips), which
// is a list, not a document being assembled.
export const MAX_BLOCK_TODOS = 8;
const DEFAULT_TODOS: BlockTodo[] = [
  {label: 'Pull the financials', done: true}, {label: 'Draft the narrative', done: true}, {label: 'Design 24 slides'},
];

const normaliseTodos = (items: unknown): BlockTodo[] => {
  if (!Array.isArray(items) || items.length < 1 || items.length > MAX_BLOCK_TODOS) {
    throw new Error(
      `BlockAssembly needs 1-${MAX_BLOCK_TODOS} \`items\` (got ${Array.isArray(items) ? items.length : typeof items}). ` +
      'Each is one to-do on the page; past eight the page shrinks below readable type — split the list across ' +
      'two beats or cast a list register.');
  }
  return items.map((it: any, i: number) => {
    const label = String((typeof it === 'string' ? it : it?.label) ?? '').trim();
    if (!label) throw new Error(`BlockAssembly: item ${i + 1} has no label.`);
    const done = typeof it === 'string' ? undefined : it?.done;
    if (done != null && typeof done !== 'boolean') {
      throw new Error(`BlockAssembly: item ${i + 1} ("${label}") has \`done: ${JSON.stringify(done)}\` — pass true, ` +
        'false, or leave it out. Only a film that says an item is finished gets a tick.');
    }
    return {label, done: done === true};
  });
};

export const BlockAssembly: React.FC<{title?: string; callout?: string; items?: (string | BlockTodo)[]; tableHeaders?: string[]}> = ({
  title = 'Q3 Board Deck', callout = 'Goal: a board-ready deck from the Q3 numbers, by Friday.',
  items: ITEMS = DEFAULT_TODOS,
  tableHeaders: TABLE_HEADERS = ['', '', '']} = {}) => {
  const todos = normaliseTodos(ITEMS);
  const items = todos.map((d) => d.label);
  const dna = useDNA();
  const BG = dna?.bg ?? '#faf9f7', FG = dna?.fg ?? INK, ACC = dna?.accent ?? ACCENT, GOOD = dna?.accent2 ?? '#12b76a';
  const MUTE = dna?.line ?? DIM, SURF = dna?.surface ?? '#fff', DIMc = dna?.dim ?? '#8b877d', ON = dna?.onAccent ?? '#fff';
  // per-element fallbacks: these two had their OWN originals, so a null DNA must restore exactly those
  const CHECK_EDGE = dna?.line ?? '#c9c5bc', DONE_INK = dna?.dim ?? '#9b968c';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE STACK'S HEIGHT IS A CONSTANT OF THE COMPOSITION — IN LATIN. `DOC_H` was measured once, from the
  // demo copy, and the page is scaled to fit the caption band by dividing by it. Every block in it wraps: a
  // Han glyph is a full em, so the title, the callout, each to-do and each table header take more lines in
  // Chinese than the number the constant was measured at, the page is scaled as though they did not, and
  // the table's em-dash row lands in the band (35px, at 16:9 and 1:1 alike).
  //
  // A DELTA OFF THE CONSTANT WAS NOT ENOUGH — it closed 8 findings to 3 and left 25px, because the growth
  // is not only the wrapped lines: `leading()` lifts EVERY CJK line by at least 6% whether it wraps or not,
  // and the cells grow with their own padding. So the page is summed from first principles instead, block
  // by block, and the constant is kept as a floor: Latin resolves to `DOC_H` exactly and nothing that ships
  // today moves, while Chinese gets a height derived from the copy it actually has.
  const lead = 1.06;                                   // what `leading()` floors CJK to; Latin stays at 1
  const blockH = (text: string, px: number, measure: number, lh = 1) =>
    wrapLines(text, px, measure) * px * Math.max(lh, /[\u4e00-\u9fff\u3000-\u303f]/.test(text) ? lead : lh);
  const GAP = 30;                                      // Block's own marginBottom
  const hTitle = blockH(title, 92, DOC_W);
  const hRules = 3 * 20 + 2 * 16;                      // three placeholder rules — never copy, never wraps
  const hCallout = 30 * 2 + Math.max(40, blockH(callout, 36, DOC_W - 34 * 2 - 22 - 40, 1.35));
  const hItems = items.reduce((a, s2) => a + Math.max(34, blockH(String(s2 ?? ''), 38, DOC_W - 54)), 0)
    + Math.max(0, items.length - 1) * 20;
  const hTable = 3 * (22 * 2) + 2
    + blockH(String(TABLE_HEADERS.reduce((w, h) => (String(h ?? '').length > String(w ?? '').length ? h : w), '') ?? ''),
             30, DOC_W / 3 - 52) + 2 * 30;             // row 0 wraps; rows 1-2 hold an em-dash, one line
  const docH = Math.max(DOC_H, hTitle + hRules + hCallout + hItems + hTable + 4 * GAP);
  const line = (w: string, c = MUTE) => <div style={{height: 20, borderRadius: 6, background: c, width: w}} />;
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* The document is a fixed stack of blocks, so its height is a constant of the composition rather than
          something the component can measure. At full size the table's last row sat 13px inside the strip the
          renderer burns the caption over — em-dash placeholders under a subtitle. The page yields as a PAGE,
          keeping every block's rhythm, instead of one row being nudged away from its table. */}
      <div style={{position: 'absolute', left: (W - DOC_W) / 2, top: 150, width: DOC_W,
        transform: `scale(${Math.min(1, (contentBottom(W, H) - 150) / docH, (W * 0.94) / DOC_W)})`, transformOrigin: '50% 0'}}>
        <Block i={0} t={t}><div style={{font: `800 92px/${leading(title, 1)} var(--f-display, Inter,system-ui,sans-serif)`, textWrap: 'balance', color: FG}}>{title}</div></Block>
        <Block i={1} t={t}><div style={{display: 'flex', flexDirection: 'column', gap: 16}}>{line('96%')}{line('88%')}{line('72%')}</div></Block>
        <Block i={2} t={t}>
          <div style={{display: 'flex', gap: 22, padding: '30px 34px', borderRadius: 14, background: `${ACC}22`, borderLeft: `5px solid ${ACC}`}}>
            <div style={{font: '700 40px/1 var(--f-body, Inter)', color: ACC}}>i</div>
            <div style={{font: '600 36px/1.35 var(--f-body, Inter,system-ui,sans-serif)', textWrap: 'balance', color: FG}}>{callout}</div>
          </div>
        </Block>
        <Block i={3} t={t}>
          <div style={{display: 'flex', flexDirection: 'column', gap: 20}}>
            {todos.map(({label: s, done}, k) => (
              <div key={k} style={{display: 'flex', alignItems: 'center', gap: 20}}>
                <div style={{width: 34, height: 34, borderRadius: 7, background: done ? GOOD : SURF, border: `2px solid ${done ? GOOD : CHECK_EDGE}`, color: ON, font: '700 20px/30px var(--f-body, Inter)', textAlign: 'center'}}>{done ? '✓' : ''}</div>
                <div style={{font: `600 38px/${leading(s, 1)} var(--f-body, Inter,system-ui,sans-serif)`, textWrap: 'balance', color: done ? DONE_INK : FG, textDecoration: done ? 'line-through' : 'none'}}>{s}</div>
              </div>
            ))}
          </div>
        </Block>
        <Block i={4} t={t}>
          <div style={{border: `1px solid ${MUTE}`, borderRadius: 12, overflow: 'hidden'}}>
            {[0, 1, 2].map(r => <div key={r} style={{display: 'flex', borderBottom: r < 2 ? `1px solid ${MUTE}` : 'none'}}>
              {[0, 1, 2].map(c => <div key={c} style={{flex: 1, padding: '22px 26px', borderRight: c < 2 ? `1px solid ${MUTE}` : 'none',
                font: `${r === 0 ? 700 : 500} 30px/${leading(TABLE_HEADERS[c], 1)} var(--f-body, Inter)`, textWrap: 'balance', color: r === 0 ? FG : DIMc}}>{r === 0 ? (TABLE_HEADERS[c] ?? '') : '—'}</div>)}
            </div>)}
          </div>
        </Block>
      </div>
    </AbsoluteFill>
  );
};
export default BlockAssembly;
