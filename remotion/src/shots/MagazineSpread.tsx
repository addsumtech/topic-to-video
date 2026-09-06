// SHOT · Magazine Spread — a designer editorial COVER sets itself: a serif masthead, a hairline rule that
// draws, a bold hero colour block that slides in, a giant feature headline that sets word-by-word, a deck,
// column body-rules, and a folio. Precise print-grid typography on an off-white ground (family L · editorial).
// A rare LIGHT register. Deterministic (every reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {captionBand, fitBlockPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 165; // 5.5s
const PAPER_D0 = '#f3f0e8', INK_D0 = '#161512';

export const MagazineSpread: React.FC<{sectionLabel?: string; title?: string; headline?: string; deck?: string; issue?: string; contents?: string[]; accent?: string}> = ({
  sectionLabel: SECTION = 'FEATURE',
  title: TITLE = 'OBLIQUE', headline: HEADLINE = 'The quiet revolution in how we work',
  deck: DECK = 'A field guide to the tools reshaping the day', issue: ISSUE = 'ISSUE 07 — 2026',
  contents: CONTENTS, accent: accentProp} = {}) => {
  const dna = useDNA();
  // accent is a PROP (an explicit override always wins); fall back to the DNA accent so a themed film unifies,
  // then the register's own editorial red as the un-themed default — not a fixed red block on a terminal/blue film.
  const PAPER = dna?.bg ?? PAPER_D0, INK = dna?.fg ?? INK_D0, ACC = accentProp ?? dna?.accent ?? '#e8452e';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const M = 150; // margin
  const BAND0 = captionBand(W, H);
  // The headline column. `fitIfCJK` used to guard this: Latin kept 116px because a giant headline wrapping in
  // a narrow column is the composition, and only the Chinese path was fitted. Rendering the register's own
  // ENGLISH demo copy showed the same defect there — a third line sitting on the standfirst — so the fit is
  // now two-dimensional and language-blind. It only ever shrinks a block that would otherwise overflow.
  const HEAD_W = W - 2 * M - 640;
  // THE HEADLINE IS FITTED TO ITS BOX, IN BOTH LANGUAGES. The first repair fitted only the CJK path, on the
  // reasoning that a giant headline wrapping in a narrow column is the composition — true, and it is still
  // true when it wraps ONE LINE TOO MANY and lands on the standfirst, which is what this register's own
  // English demo copy did at 116px. The box is the column, from the headline's top to the deck's own top.
  const HEAD_TOP = 470;
  const HEAD_H = (H - (BAND0 + 62)) - HEAD_TOP - 18;
  const headLead = leading(HEADLINE, 0.98);
  const headPx = fitBlockPx(HEADLINE, HEAD_W, HEAD_H, 116, {leading: headLead});
  const mast = easeOutExpo(seg(t, 0.05, 0.34));
  const rule = easeOutCubic(seg(t, 0.2, 0.5));
  const block = easeOutExpo(seg(t, 0.34, 0.6));
  const words = HEADLINE.split(' ');
  const BAND = BAND0;

  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden', color: INK}}>
      {/* masthead */}
      <div style={{position: 'absolute', left: M, top: 92, opacity: clamp01(mast * 1.3),
        transform: `translateY(${(1 - mast) * -20}px)`,
        font: '800 132px/0.9 var(--f-display, "Playfair Display", Georgia, serif)', letterSpacing: '-0.02em'}}>{TITLE}</div>
      <div style={{position: 'absolute', right: M, top: 128, opacity: clamp01(seg(t, 0.28, 0.44)),
        font: '600 26px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.16em'}}>{ISSUE}</div>
      {/* hairline rule */}
      <div style={{position: 'absolute', left: M, top: 250, height: 3, background: INK,
        width: (W - 2 * M) * rule}} />

      {/* hero colour block */}
      <div style={{position: 'absolute', right: M, top: 320, width: 560, height: 560,
        transform: `translateX(${(1 - block) * 120}px)`, opacity: block,
        background: `linear-gradient(160deg, ${ACC}, ${dna?.accent2 ?? '#b0311f'})`, boxShadow: '0 40px 80px #0002'}}>
        {/* THE PLATE'S CAPTION IS THE SECTION PROP, not the word FEATURE written into the JSX.
            It was both — declared as a prop default AND printed as a literal — so the prop looked like it
            worked and did nothing, and a Chinese film carried an English word no prop could reach. The
            second line said `No. 01`, which only repeated the issue already set in the top corner. */}
        <div style={{position: 'absolute', left: 34, bottom: 30, color: '#fff',
          font: '700 26px/1.3 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.08em', opacity: clamp01(seg(t, 0.5, 0.66))}}>
          {SECTION}<br />{ISSUE}</div>
        {/* a couple of framing corner ticks */}
        <div style={{position: 'absolute', left: 20, top: 20, width: 40, height: 40, borderLeft: '3px solid #fff', borderTop: '3px solid #fff', opacity: 0.7}} />
      </div>

      {/* giant feature headline, word by word */}
      {/* FITTED TO THE BOX, not set at a fixed 116px — see `fitBlockPx`. The box runs from the headline's
          top to the deck's own top, so the headline can wrap as much as the composition wants and can
          never reach the standfirst. */}
      <div style={{position: 'absolute', left: M, top: HEAD_TOP, width: HEAD_W,
        // 0.98 reads as a tight editorial headline in Latin and collides in Chinese (see runtime/cjkType).
        // The SIZE is fitted too: a Chinese headline of the same word count is far wider, and at a fixed
        // 116px it wrapped to three lines that ran down through the standfirst below.
        font: `800 ${headPx}px/${headLead} var(--f-display, "Playfair Display", Georgia, serif)`, letterSpacing: '-0.015em'}}>
        {words.map((w, i) => {
          const on = easeOutCubic(clamp01(seg(t, 0.44 + i * 0.06, 0.62 + i * 0.06)));
          return <span key={i} style={{display: 'inline-block', marginRight: '0.28em', opacity: on,
            transform: `translateY(${(1 - on) * 24}px)`}}>{w}</span>;
        })}
      </div>

      {/* deck + body column rules.
          The deck, the body rules and the folio were pinned at bottom:190 / 96 / 84 — literal pixels that
          cleared the burned caption only while the reserved band happened to be 150px. The folio at 84 sat
          inside the band the moment it grew. All three are measured from the BAND now. */}
      <div style={{position: 'absolute', left: M, bottom: BAND + 62, width: 720, opacity: clamp01(seg(t, 0.72, 0.9)),
        font: 'italic 600 34px/1.35 var(--f-body, "Playfair Display", Georgia, serif)', color: '#3a352c'}}>{DECK}</div>
      {/* THE CONTENTS LIST — where three columns of grey RULES used to stand in for body text.
          Twelve 5px bars at 13% opacity are a drawing of paragraphs that do not exist: on a rendered frame
          they read as a page that has not finished loading, and a viewer cannot decode a single one of
          them. A cover does not carry body columns anyway — it carries an index. So the space now holds
          real entries when the film supplies them, and nothing at all when it does not. Losing a little
          ink is the right trade against furniture nobody can read. */}
      {CONTENTS?.length ? (
        <div style={{position: 'absolute', left: M, bottom: BAND + 14, display: 'flex', flexWrap: 'wrap',
          maxWidth: 720, columnGap: 34, rowGap: 10, opacity: clamp01(seg(t, 0.8, 0.95))}}>
          {CONTENTS.slice(0, 6).map((e, i) => (
            <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 10}}>
              <span style={{font: '700 15px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.12em',
                color: ACC}}>{String(i + 1).padStart(2, '0')}</span>
              <span style={{font: `600 24px/${leading(e, 1.2)} var(--f-body, "Playfair Display", Georgia, serif)`,
                color: '#3a352c'}}>{e}</span>
            </div>
          ))}
        </div>
      ) : null}
      {/* THE FOLIO IS GONE, and that is the honest end of it. It used to read `{TITLE}.CO — 01`: a DOMAIN
          manufactured out of the film's own title, for a site that does not exist, on every film that ever
          reached for this register — a Chinese film's corner read 「答得更好，交付没变.CO — 01」. Rebuilt from
          real props it said `{TITLE} — {ISSUE}`, which the masthead and the top corner already say, and it
          sat ON the image plate where it ran into the plate's own caption. A folio carries the publication
          and the issue; both are already on the page. The plate caption carries the issue now. */}
    </AbsoluteFill>
  );
};
export default MagazineSpread;
