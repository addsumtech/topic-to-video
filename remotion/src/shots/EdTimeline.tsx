// SHOT · EdTimeline — an EDITORIAL ruled timeline (the editorial analogue of TermGitLog): dated entries with a
// serif title + note, separated by hairline rules, like a magazine chronology. The 'lineage/sequence' idea in the
// editorial DNA. Deterministic (entry reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, EdFrame} from '../runtime/dna';

export const DURATION = 165;
type Entry = {date?: string; title?: string; note?: string};

export const EdTimeline: React.FC<{kicker?: string; entries?: Entry[]; framed?: boolean}> = ({
  kicker = 'A HISTORY', framed = false,
  entries = [{date: '01', title: 'first', note: 'note'}, {date: '02', title: 'second', note: 'note'}]} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const disp = dna?.fontDisplay ?? '"Playfair Display", Georgia, serif';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const fg = dna?.fg ?? '#efe9df', dim = dna?.dim ?? '#9a9084', acc = dna?.accent ?? '#e2603f', line = dna?.line ?? '#2a2018';

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
            const start = 0.24 + i * 0.16;
            const show = clamp01(seg(t, start, start + 0.14));
            return (
              <div key={i} style={{display: 'flex', gap: 40, alignItems: 'baseline', padding: '26px 0',
                borderTop: i ? `1px solid ${line}` : 'none', opacity: show, transform: `translateY(${(1 - show) * 14}px)`}}>
                <span style={{color: acc, font: `700 40px/${leading(e.date, 1)} ${disp}`, textWrap: 'balance', minWidth: '3ch'}}>{e.date}</span>
                <div>
                  <div style={{color: fg, font: `700 52px/1.1 ${disp}`, letterSpacing: '-0.01em'}}>{e.title}</div>
                  {e.note ? <div style={{color: dim, font: `400 30px/1.4 ${body}`, textWrap: 'balance', marginTop: 8}}>{e.note}</div> : null}
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
