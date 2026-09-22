// SHOT · EdTimeline — an EDITORIAL ruled timeline (the editorial analogue of TermGitLog): dated entries with a
// serif title + note, separated by hairline rules, like a magazine chronology. The 'lineage/sequence' idea in the
// editorial DNA. Deterministic (entry reveal = fn of t).
//
// EVERY ENTRY THE FILM GIVES LANDS BEFORE THE FRAME IS READ. Entry i used to rise in at `0.24 + i * 0.16` — a
// fixed step, so the list's length decided whether it ever finished: a fourth entry landed exactly at the
// settled frame (t = 0.86, the frame every gate and the shot-critic read, and the one reduced motion freezes
// on), a fifth was still fading in on the LAST frame, and a sixth began after the clip had ended. A film that
// wrote six dated moments got a chronology of four and nothing said so. The step is now laid out for the count
// — the original 0.16 is kept as the upper bound, so a short chronology keeps its rhythm and its render, and a
// long one closes the gaps until its last entry has landed by LAND_BY. Past MAX_ED_ENTRIES the rows would be
// arriving faster than a viewer can read a date, a title and a note, so the register refuses instead.
//
// AND THE ENTRIES THAT NOW ARRIVE HAVE TO FIT. Type was a fixed 40 / 52 / 30px with nothing fitted, so the
// longer lists this register can now finish would have run out of the content zone into the caption band.
// The whole chronology scales by one factor, estimated from the copy's own wraps, so it fits the zone; a
// chronology that would need type below half size throws rather than printing under the subtitle.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, REDUCED_MOTION_T} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, textWidthPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, EdFrame} from '../runtime/dna';

export const DURATION = 165;
type Entry = {date?: string; title?: string; note?: string};

export const MAX_ED_ENTRIES = 6;
// The reveal: the first entry rises at START and each takes DUR. STEP is the ORIGINAL gap and only an upper
// bound — the real one is derived from the count so the last entry lands by LAND_BY, a hair before the frame
// `useT` calls settled (derived from it, so the two cannot drift).
const START = 0.24, STEP = 0.16, DUR = 0.14;
const LAND_BY = REDUCED_MOTION_T - 0.02;
// The smallest the chronology may be scaled to fit its zone; below this a note is no longer body copy.
const K_MIN = 0.5;

export const EdTimeline: React.FC<{kicker?: string; entries?: Entry[]; framed?: boolean}> = ({
  kicker = 'A HISTORY', framed = false,
  entries = [{date: '01', title: 'first', note: 'note'}, {date: '02', title: 'second', note: 'note'}]} = {}) => {
  if (!Array.isArray(entries) || entries.length < 1 || entries.length > MAX_ED_ENTRIES) {
    throw new Error(
      `EdTimeline needs 1-${MAX_ED_ENTRIES} \`entries\` (got ${Array.isArray(entries) ? entries.length : typeof entries}). ` +
      (Array.isArray(entries) && entries.length > MAX_ED_ENTRIES
        ? 'Every entry rises in one after another and must have landed before the settled frame; past ' +
          `${MAX_ED_ENTRIES} they would arrive faster than a date, a title and a note can be read. ` +
          'Keep the moments that carry the lineage, or cast a list register for a longer run.'
        : 'With no entry there is no chronology to draw — pass `entries: [{date, title, note?}]`.'));
  }
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const disp = dna?.fontDisplay ?? '"Playfair Display", Georgia, serif';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const fg = dna?.fg ?? '#efe9df', dim = dna?.dim ?? '#9a9084', acc = dna?.accent ?? '#e2603f', line = dna?.line ?? '#2a2018';

  const n = entries.length;
  const step = n > 1 ? Math.min(STEP, (LAND_BY - START - DUR) / (n - 1)) : STEP;

  // THE FIT. EdFrame's column is min(84vw, 1300) (less its 72px padding each side when framed) and this list
  // caps it at 1100; the header above the list is the kicker (26px + 22) and the rule's 2px + 40px. Each row
  // is its 26px padding top and bottom, the title's lines and the note's — wrapped in the width the text
  // column really gets, which is what is left beside the date. Estimated in the fitters' generous advance, so
  // the error runs toward fitting with room to spare, never toward spilling.
  const colW = Math.min(Math.min(W * 0.84, 1300) - (framed ? 144 : 0), 1100);
  const headH = (kicker ? 26 + 22 : 0) + 2 + 40 + (framed ? 122 : 0);
  const room = contentBottom(W, H) - CONTENT_TOP - headH;
  const listH = (k: number) => entries.reduce((h, e, i) => {
    const dateW = Math.max(textWidthPx('000', 40 * k), textWidthPx(String(e?.date ?? ''), 40 * k));
    const textW = colW - dateW - 40 * k;
    const tl = e?.title ? wrapLines(String(e.title), 52 * k, textW) : 0;
    const nl = e?.note ? wrapLines(String(e.note), 30 * k, textW) : 0;
    return h + (i ? 1 : 0) + 52 * k + Math.max(40 * k, tl * 52 * k * leading(e?.title, 1.1)
      + (nl ? 8 * k + nl * 30 * k * leading(e?.note, 1.4) : 0));
  }, 0);
  let k = 1;
  while (k > K_MIN && listH(k) > room) k = Math.round((k - 0.02) * 100) / 100;
  if (listH(k) > room) {
    throw new Error(
      `EdTimeline: these ${n} entries need ${Math.round(listH(K_MIN))}px at half size and the content zone ` +
      `leaves ${Math.round(room)}px at ${W}x${H}. Shorten the notes or pass fewer entries — set any smaller ` +
      'and the notes stop being readable.');
  }
  const px = (v: number) => Math.round(v * k);

  return (
    // CENTRED ON THE CONTENT ZONE, NOT THE FRAME. Every entry grows with its copy — a Han glyph is a full
    // em, so a Chinese note wraps where the English one did not — and a list centred on H/2 pushes half of
    // that growth downward into the caption band (36px of it at 1:1). The padding makes the flex centre the
    // zone's centre; on a frame whose band and title band are equal it changes nothing.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      paddingTop: CONTENT_TOP, paddingBottom: H - contentBottom(W, H)}}>
      <EdFrame dna={dna} kicker={kicker} t={t} framed={framed} align="left">
        <div style={{width: '100%', maxWidth: 1100}}>
          {entries.map((e, i) => {
            const start = START + i * step;
            const show = clamp01(seg(t, start, start + DUR));
            return (
              <div key={i} style={{display: 'flex', gap: px(40), alignItems: 'baseline', padding: `${px(26)}px 0`,
                borderTop: i ? `1px solid ${line}` : 'none', opacity: show, transform: `translateY(${(1 - show) * 14}px)`}}>
                <span style={{color: acc, font: `700 ${px(40)}px/${leading(e.date, 1)} ${disp}`, textWrap: 'balance', minWidth: '3ch'}}>{e.date}</span>
                <div>
                  {/* `text-wrap: balance` for the same reason `date` and `note` already carry it, and the
                      TITLE is the one that needed it most: it is the widest line in the row, so a Chinese
                      title one unit past its column drops a single glyph onto a line of its own — measured
                      here as 「…多种主流语言」 ending on a line holding 「言」. A break hint only; a title
                      that already fits cannot move, and Latin ragging is only improved. */}
                  <div style={{color: fg, font: `700 ${px(52)}px/${leading(e.title, 1.1)} ${disp}`, letterSpacing: '-0.01em', textWrap: 'balance'}}>{e.title}</div>
                  {e.note ? <div style={{color: dim, font: `400 ${px(30)}px/${leading(e.note, 1.4)} ${body}`, textWrap: 'balance', marginTop: px(8)}}>{e.note}</div> : null}
                </div>
              </div>
            );
          })}
        </div>
      </EdFrame>
    </AbsoluteFill>
  );
};
export default EdTimeline;
