// SHOT · Rearrange — the SAME items, moved from one arrangement to another, and each arrangement is a claim:
// `grid` (these are peers), `hero` (this one matters), `rank` (this is their order, by a sourced value), `groups`
// (these belong together). The beat changes its mind on screen and the viewer keeps track of every item, because
// it TRAVELS to its new place instead of being redrawn there (runtime/layoutMorph: deterministic layouts, a
// staggered morph on slightly bowed paths). A `title` opens the beat centred and large, then demotes itself to the
// beat's label at the top left as the items arrive under it.
//
// Peer: video-shotcraft's mosaic-reframe / title-demote-to-label / canvas-materialize (reviewed 2026-11-02). Their
// tiles re-frame for the look of it; here the layouts are the argument, so a step names WHICH claim it makes.
//
// EVERY WORD AND NUMBER IS THE FILM'S. Items carry their own `label`, `icon`, `value` (a sourced figure — it is
// printed as written in `display`, or as the number with `unit`) and `group`. `rank` refuses an item with no value,
// `groups` one with no group, and every layout refuses a count its box cannot hold at a readable size.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutBack, easeInOutCubic, lerp} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, dnaPalette, mix} from '../runtime/dna';
import {Icon, type IconName} from '../runtime/icons';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';
import {grid, hero, rank, groups, groupHeads, groupOrder, morph, shares, type Rect} from '../runtime/layoutMorph';

export const DURATION = 240; // 8 s: an entrance and two re-arrangements, each held long enough to read
export const MAX_ITEMS = 12;

export type RearrangeItem = {
  label: string;
  icon?: IconName;
  /** a sourced figure: what `rank` orders by */
  value?: number;
  /** how the value is printed (as written); else the number and `unit` */
  display?: string;
  /** which group it belongs to: what `groups` gathers by */
  group?: string;
};

export type RearrangeStep = {
  layout: 'grid' | 'hero' | 'rank' | 'groups';
  /** for `hero`: which item (index) */
  hero?: number;
  /** the beat's t (0..1) at which this arrangement starts — or `{cue}` on the board (render_remotion resolves it) */
  at?: number;
};

const DEFAULT_ITEMS: RearrangeItem[] = [
  {label: 'Item one', icon: 'file', value: 3, group: 'Group A'},
  {label: 'Item two', icon: 'table', value: 8, group: 'Group B'},
  {label: 'Item three', icon: 'search', value: 5, group: 'Group A'},
  {label: 'Item four', icon: 'users', value: 2, group: 'Group B'},
  {label: 'Item five', icon: 'message', value: 6, group: 'Group A'},
];
const DEFAULT_STEPS: RearrangeStep[] = [{layout: 'grid'}, {layout: 'hero', hero: 1, at: 0.4}, {layout: 'rank', at: 0.7}];

/** seconds a re-arrangement takes, as a share of the beat */
const MOVE = 0.13;

export const Rearrange: React.FC<{title?: string; items?: RearrangeItem[]; steps?: RearrangeStep[]; unit?: string}> = ({
  title = '', items = DEFAULT_ITEMS, steps = DEFAULT_STEPS, unit = ''} = {}) => {
  if (!Array.isArray(items) || items.length < 2 || items.length > MAX_ITEMS) {
    throw new Error(`Rearrange needs 2-${MAX_ITEMS} items (got ${Array.isArray(items) ? items.length : typeof items})`);
  }
  if (!Array.isArray(steps) || !steps.length) throw new Error('Rearrange needs at least one step');
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const BG = dna?.bg ?? '#0c0f14', FG = dna?.fg ?? '#eef1f6', DIM = dna?.dim ?? '#8d95a5';
  const EDGE = dna?.line ?? '#262c38', SURF = dna?.surface ?? '#161b23';
  const TONES = dnaPalette(dna, 5) ?? ['#5b8cff', '#ff8a5b', '#37d4a6', '#f6c431', '#c07bff'];
  const DISPLAY = 'var(--f-display, Inter, system-ui, sans-serif)';
  const MONO = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", monospace)';
  const floor = Math.round(U * 0.028);            // ~30 px at 1080: the library's label floor

  // ---- the zone: a label band at the top for the demoted title, the items under it ----
  const padX = Math.round(W * 0.07);
  const top = Math.max(CONTENT_TOP, Math.round(U * 0.08));
  const bottom = contentBottom(W, H) - Math.round(U * 0.02);
  const labelPx = Math.round(U * 0.036);
  const band = title ? Math.round(labelPx * 1.6) : 0;
  const box = {x: padX, y: top + band, w: W - 2 * padX, h: bottom - top - band};

  const layoutOf = (s: RearrangeStep): Rect[] => {
    if (s.layout === 'grid') return grid(items.length, box);
    if (s.layout === 'hero') return hero(items.length, box, s.hero ?? 0);
    if (s.layout === 'rank') {
      const miss = items.findIndex((it) => typeof it.value !== 'number');
      if (miss >= 0) throw new Error(`Rearrange: rank orders by value, and item ${miss + 1} (${items[miss].label}) has none`);
      return rank(items.map((it) => it.value as number), box, {rowMax: Math.round(U * 0.11)});
    }
    if (s.layout === 'groups') {
      const miss = items.findIndex((it) => !String(it.group ?? '').trim());
      if (miss >= 0) throw new Error(`Rearrange: groups gathers by group, and item ${miss + 1} (${items[miss].label}) has none`);
      return groups(items.map((it) => String(it.group)), box, {head: Math.round(U * 0.07)});
    }
    throw new Error(`Rearrange: unknown layout ${JSON.stringify((s as {layout: unknown}).layout)} — grid, hero, rank, groups`);
  };
  const layouts = steps.map(layoutOf);
  const starts = steps.map((s, k) => (k === 0 ? 0 : clamp01(s.at ?? k / steps.length)));
  for (let k = 1; k < starts.length; k++) {
    if (!(starts[k] > starts[k - 1] + MOVE * 0.9)) {
      throw new Error(`Rearrange: step ${k + 1} starts at ${starts[k]} — each re-arrangement needs ~${MOVE} of the beat ` +
        'after the one before it, or the items never come to rest in between');
    }
  }
  // which arrangement the items are in now, and how far into the move toward it
  let k = 0;
  while (k + 1 < steps.length && t >= starts[k + 1]) k++;
  const into = k === 0 ? 1 : seg(t, starts[k], starts[k] + MOVE);
  const rects = k === 0 ? layouts[0] : morph(layouts[k - 1], layouts[k], into, {stagger: 0.35, order: 'distance'});
  // how much each kind of arrangement is showing (for the parts that belong to one: bars' numbers, group heads)
  const weight = (layout: RearrangeStep['layout']) =>
    (steps[k].layout === layout ? into : 0) + (k > 0 && steps[k - 1].layout === layout ? 1 - into : 0);
  const heroW = steps[k].layout === 'hero' ? into : 0;
  const heroWas = k > 0 && steps[k - 1].layout === 'hero' ? 1 - into : 0;
  const heroIdx = steps[k].layout === 'hero' ? steps[k].hero ?? 0 : k > 0 && steps[k - 1].layout === 'hero' ? steps[k - 1].hero ?? 0 : -1;
  const heroLit = Math.max(heroW, heroWas);

  // ---- the title: centred and large, then demoted to the label band as the items arrive ----
  const demote = easeInOutCubic(clamp01(seg(t, 0.1, 0.22)));
  const bigPx = fitTextPx(title, W * 0.8, Math.round(U * 0.1), {usable: 0.95});
  const titleScale = lerp(bigPx / labelPx, 1, demote);
  const titleX = lerp(W / 2, padX, demote), titleY = lerp(H * 0.42, top, demote);

  const enterAt = title ? 0.18 : 0.06;
  const valueText = (it: RearrangeItem) => it.display ?? (typeof it.value === 'number' ? `${it.value}${unit}` : '');
  // a bar's length inside its row (rank only): its value's share of the largest
  const share = steps.some((s) => s.layout === 'rank') ? shares(items.map((it) => it.value as number)) : [];
  const rankW = weight('rank');
  const gOrder = steps.some((s) => s.layout === 'groups') ? groupOrder(items.map((it) => String(it.group ?? ''))) : [];
  const heads = gOrder.length ? groupHeads(items.map((it) => String(it.group)), box, {head: Math.round(U * 0.07)}) : [];

  return (
    <AbsoluteFill style={{background: dna ? `radial-gradient(110% 90% at 30% 15%, ${mix(BG, dna.accent, 0.08)}, ${BG} 70%)` : BG}}>
      {heads.map((r, g) => (
        <div key={'h' + g} style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, opacity: weight('groups'),
          display: 'flex', alignItems: 'flex-end', borderBottom: `2px solid ${mix(EDGE, TONES[g % TONES.length], 0.6)}`,
          color: TONES[g % TONES.length], font: `700 ${Math.max(floor, fitTextPx(gOrder[g], r.w, Math.round(U * 0.034)))}px/1.1 ${DISPLAY}`}}>
          {gOrder[g]}
        </div>
      ))}
      {items.map((it, i) => {
        const r = rects[i];
        const st = enterAt + (i / items.length) * 0.12;
        const e = easeOutBack(clamp01(seg(t, st, st + 0.12)));
        const tone = TONES[(gOrder.length ? Math.max(0, gOrder.indexOf(String(it.group))) : i) % TONES.length];
        const lit = i === heroIdx ? heroLit : 0;
        const dim = heroIdx >= 0 && i !== heroIdx ? heroLit : 0;
        const pad = Math.round(Math.max(12, Math.min(r.h * 0.14, r.w * 0.06, U * 0.03)));
        // a ROW (a wide box: rank, groups) and a CARD (grid, hero) are two arrangements of one item's words,
        // cross-faded by the box's shape; the bar FILL inside a row belongs to `rank` alone
        // decided by the two ARRANGEMENTS the item is between, not by its box mid-flight: a settled frame is always
        // exactly one drawing (a box near the threshold drew both, and printed the value twice)
        const isRow = (q: Rect) => (q.w / q.h > 2.6 ? 1 : 0);
        const barness = k === 0 ? isRow(layouts[0][i]) : lerp(isRow(layouts[k - 1][i]), isRow(layouts[k][i]), into);
        const inner = {w: r.w - 2 * pad, h: r.h - 2 * pad};
        const valTxt = valueText(it);
        const big = i === heroIdx && heroLit > 0.5;
        const lab = Math.max(floor, Math.min(fitTextPx(it.label, inner.w * (barness > 0.5 ? 0.3 : 1), Math.round(Math.min(
          inner.h * (big ? 0.16 : barness > 0.5 ? 0.5 : 0.3), U * (big ? 0.07 : 0.045)))), Math.round(inner.h * 0.6)));
        const iconPx = it.icon ? Math.round(Math.min(inner.h * (barness > 0.5 ? 0.7 : 0.42), inner.w * 0.4, U * (big ? 0.2 : 0.1))) : 0;
        const valPx = Math.max(floor, Math.round(Math.min(inner.h * (barness > 0.5 ? 0.6 : 0.24), U * 0.05)));
        return (
          <div key={i} style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, boxSizing: 'border-box',
            opacity: clamp01(e * 1.4) * (1 - 0.45 * dim), transform: glide(`scale(${lerp(0.9, 1, e)})`, true),
            transformOrigin: 'center', borderRadius: Math.round(U * 0.016), padding: pad, overflow: 'hidden',
            background: `linear-gradient(160deg, ${mix(SURF, tone, 0.08 + 0.18 * lit)}, ${mix(SURF, BG, 0.4)})`,
            border: `${Math.max(1, Math.round(U * (0.0015 + 0.002 * lit)))}px solid ${mix(EDGE, tone, 0.35 + 0.65 * lit)}`,
            boxShadow: `0 ${Math.round(U * 0.02)}px ${Math.round(U * 0.05)}px #0005`}}>
            {/* the card: icon, then label (and value) at the foot */}
            <div style={{position: 'absolute', inset: pad, opacity: 1 - barness, display: 'flex', flexDirection: 'column',
              justifyContent: it.icon ? 'space-between' : 'flex-end'}}>
              {it.icon ? <Icon name={it.icon} size={iconPx} ink={tone} weight={1.9} /> : null}
              <div>
                <div style={{color: FG, font: `700 ${lab}px/${leading(it.label, 1.15)} ${DISPLAY}`, textWrap: 'balance'}}>{it.label}</div>
                {valTxt ? <div style={{color: tone, marginTop: Math.round(U * 0.006),
                  font: `600 ${Math.max(floor, Math.round(lab * 0.75))}px/1 ${MONO}`, fontVariantNumeric: 'lining-nums tabular-nums'}}>{valTxt}</div> : null}
              </div>
            </div>
            {/* the row: icon and label in a column of their own, then (rank) the bar, then the value */}
            <div style={{position: 'absolute', inset: pad, opacity: barness, display: 'flex', alignItems: 'center',
              gap: Math.round(U * 0.014)}}>
              {it.icon ? <Icon name={it.icon} size={Math.min(iconPx, Math.round(inner.h * 0.8))} ink={FG} weight={1.9} /> : null}
              <div style={{flex: 'none', width: Math.round(inner.w * 0.3), color: FG, whiteSpace: 'nowrap', overflow: 'hidden',
                font: `700 ${lab}px/1.1 ${DISPLAY}`}}>{it.label}</div>
              <div style={{flex: 1, alignSelf: 'stretch', position: 'relative'}}>
                {share.length ? <div style={{position: 'absolute', left: 0, top: '18%', bottom: '18%',
                  width: `${100 * share[i] * rankW}%`, borderRadius: Math.round(U * 0.006),
                  background: `linear-gradient(90deg, ${tone}, ${mix(tone, SURF, 0.35)})`}} /> : null}
              </div>
              {valTxt ? <div style={{flex: 'none', color: FG, font: `700 ${valPx}px/1 ${MONO}`,
                fontVariantNumeric: 'lining-nums tabular-nums'}}>{valTxt}</div> : null}
            </div>
          </div>
        );
      })}
      {title ? (
        // placed at its anchor, scaled about it, and shifted by half its own size while it is still centred
        <div style={{position: 'absolute', left: 0, top: 0, transformOrigin: '0 0',
          transform: glide(`translate(${titleX}px, ${titleY}px) scale(${titleScale}) ` +
            `translate(${-50 * (1 - demote)}%, ${-50 * (1 - demote)}%)`, true),
          whiteSpace: 'nowrap', color: mix(FG, DIM, 0.35 * demote), letterSpacing: dna?.labelSpacing ?? '0.02em',
          font: `800 ${labelPx}px/1.1 ${DISPLAY}`, opacity: clamp01(seg(t, 0.02, 0.08))}}>{title}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default Rearrange;
