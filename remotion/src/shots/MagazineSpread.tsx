// SHOT · Magazine Spread — a designer editorial COVER sets itself: a serif masthead, a hairline rule that
// draws, a bold hero colour block that slides in, a giant feature headline that sets word-by-word, a deck,
// column body-rules, and a folio. Precise print-grid typography on an off-white ground (family L · editorial).
// A rare LIGHT register. Deterministic (every reveal = fn of t).
//
// EVERY ENTRY AND EVERY WORD ARRIVES. Two silent drops lived here. The contents index took
// `contents.slice(0, 6)`, so a film's seventh chapter was not on the cover and nothing said so; it now draws
// every entry up to MAX_MAGAZINE_CONTENTS and THROWS past it (and on an empty entry). And the headline set
// word by word on a FIXED 0.06 stagger from 0.44 with 0.18 per word, so the tenth word started at 0.98 and
// anything past it never started at all: an eleven-word headline shipped with its last words missing and a
// settled frame that read as a complete, shorter sentence. The stagger is now laid out for the word count so
// the last word has landed by 0.90 — the 0.06 rhythm is kept wherever it already fitted.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {captionBand, contentBottom, fitBlockPx, fitTextPx, monoFit, textWidthPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
const PAPER_D0 = '#f3f0e8', INK_D0 = '#161512';

/** The most contents entries the index is drawn with. It wraps to as many rows as it needs and the deck and
 *  headline yield to it, so this is a cover's index, not a table of contents: past six, give it its own beat. */
export const MAX_MAGAZINE_CONTENTS = 6;

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
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  // THE SPREAD'S COLUMNS ARE FRACTIONS OF THE PAGE. Every width here was a literal measured once on a
  // 1920-wide frame: a 150px margin, a 560px plate and the 640 of sidebar the headline column subtracted.
  // At 1:1 that arithmetic left the headline 140px — a ribbon setting one word per line — while the plate
  // ate half the page and the deck, pinned at a flat 720, ran straight across it and through its caption.
  // Stated as fractions the same composition holds at every aspect: margin, text column, gutter, plate.
  const M = Math.round(W * 0.078);              // 150 at 1920
  const PLATE_W = Math.round(W * 0.292);        // 560
  const GUTTER = Math.round(W * 0.042);         // 80
  const BAND0 = captionBand(W, H);
  // The headline column. `fitIfCJK` used to guard this: Latin kept 116px because a giant headline wrapping in
  // a narrow column is the composition, and only the Chinese path was fitted. Rendering the register's own
  // ENGLISH demo copy showed the same defect there — a third line sitting on the standfirst — so the fit is
  // now two-dimensional and language-blind. It only ever shrinks a block that would otherwise overflow.
  const HEAD_W = W - 2 * M - PLATE_W - GUTTER;
  // THE HEADLINE IS FITTED TO ITS BOX, IN BOTH LANGUAGES. The first repair fitted only the CJK path, on the
  // reasoning that a giant headline wrapping in a narrow column is the composition — true, and it is still
  // true when it wraps ONE LINE TOO MANY and lands on the standfirst, which is what this register's own
  // English demo copy did at 116px. The box is the column, from the headline's top to the deck's own top.
  // THE PAGE'S VERTICAL RHYTHM IS A FRACTION OF THE ROOM IT HAS. 320 and 470 are where the plate and the
  // headline sit on a 1080-tall page; on a 1920-tall one they stayed put while the deck, anchored to the
  // caption band, went down with the frame — leaving 500px of nothing across the middle of a portrait
  // cover. The room is what lies between the rule and the deck, and the two sit at the same proportions of
  // it they always did: at 1080 tall this arithmetic returns 320 and 470 exactly, so the aspect this was
  // composed for does not move.
  const RULE_Y = 250;
  const DECK_PX = 34, DECK_LH = 1.35;
  const DECK_H = Math.ceil(wrapLines(DECK, DECK_PX, HEAD_W) * DECK_PX * DECK_LH);
  if (CONTENTS != null && (!Array.isArray(CONTENTS) || CONTENTS.length > MAX_MAGAZINE_CONTENTS)) {
    throw new Error(
      `MagazineSpread's contents index holds 0-${MAX_MAGAZINE_CONTENTS} entries (got ` +
      `${Array.isArray(CONTENTS) ? CONTENTS.length : typeof CONTENTS}). List the ${MAX_MAGAZINE_CONTENTS} ` +
      `that matter, or give the index its own beat with a list register.`);
  }
  const contents = (CONTENTS ?? []).map((e, i) => {
    const entry = String(e ?? '').trim();
    if (!entry) throw new Error(`MagazineSpread: contents entry ${i + 1} is empty.`);
    return entry;
  });
  // THE INDEX TAKES THE ROWS IT NEEDS, AND THE DECK SITS ON TOP OF THEM. The deck was pinned 62px above the
  // band and the index 14px above it, which leaves room for exactly ONE row of entries. Six entries at 9:16
  // wrap to two, and the second row climbed into the deck's last line — 「the tide tables」 printed over
  // 「Gravity · Inertia」. The rows are estimated here (conservatively: the advance model over-reads a
  // narrow serif, so it may reserve a row that is not needed, never the reverse) so the headline's box can
  // yield; the deck and the index are then laid out in ONE column so the deck always sits on the index as
  // drawn. With no index, or one row of it, the deck's bottom is at exactly 62 as before.
  const C_PX = 24, C_NUM_PX = 15, C_COL_GAP = 34, C_ROW_GAP = 10, C_ITEM_GAP = 10, C_DECK_GAP = 19;
  const C_ROW_H = Math.ceil(C_PX * leading(contents, 1.2));
  let contentRows = 0;
  // The ordinal's WIDTH is measured from a fixed '00' rather than from the row's own index: the face is mono,
  // so every two-digit ordinal is exactly this wide, and the row-fitting measure then carries no arithmetic on
  // the index at all (onscreen_text_qa reads a measurement computed from `i` as a number the film never gave).
  const C_NUM_W = textWidthPx('00', C_NUM_PX, {track: 0.12, ...monoFit()});
  contents.reduce((x, e, i) => {
    const w = C_NUM_W + C_ITEM_GAP + textWidthPx(e, C_PX);
    if (!contentRows || x + C_COL_GAP + w > HEAD_W) { contentRows += 1; return w; }
    return x + C_COL_GAP + w;
  }, 0);
  const CONTENTS_H = contentRows ? contentRows * C_ROW_H + (contentRows - 1) * C_ROW_GAP : 0;
  const DECK_BOTTOM = BAND0 + (contentRows ? 14 + CONTENTS_H + C_DECK_GAP : 62);
  const DECK_TOP = H - DECK_BOTTOM - DECK_H;
  const ROOM = Math.max(160, DECK_TOP - RULE_Y);
  const PLATE_TOP = RULE_Y + Math.round(ROOM * 0.134);
  const HEAD_TOP = RULE_Y + Math.round(ROOM * 0.421);
  // THE MASTHEAD IS FITTED TO THE ROOM BEFORE THE ISSUE LINE. 132px is a masthead on a 1920 frame; on a
  // 1080 one 'OBLIQUE' ran into 'ISSUE 07 — 2026' and the E sat on the I. The issue line is set in the
  // mono face with 0.16em of tracking, so its width is measured that way rather than guessed.
  const ISSUE_PX = 26;
  const issueW = textWidthPx(ISSUE, ISSUE_PX, {track: 0.16, ...monoFit()});
  const mastPx = fitTextPx(TITLE, Math.max(80, W - 2 * M - issueW - GUTTER), Math.round(Math.min(W, H) * 0.122),
    {usable: 1});
  // ...AND THE BOX ENDS WHERE THE DECK BEGINS. `BAND0 + 62` is the deck's BOTTOM, not its top, so this
  // reserve handed the headline every pixel the deck stands in. At 16:9 the deck is one line and the 18px
  // slack hid it; give the deck a narrower column, or a longer sentence, and it takes two — and the
  // headline's last line came down onto it. Measured in the column the deck actually wraps in.
  const HEAD_H = DECK_TOP - HEAD_TOP - 18;
  const headLead = leading(HEADLINE, 0.98);
  // 116px is a cover headline on a 1080-tall page. The CEILING scales with the page — a portrait cover
  // has twice the height and wants a bigger headline, and `fitBlockPx` brings it back down to what the
  // column can actually hold. At H = 1080 this is 116, so 16:9, 1:1 and 4:3 are untouched.
  const headPx = fitBlockPx(HEADLINE, HEAD_W, HEAD_H, Math.round(H * 0.1074), {leading: headLead});
  const mast = easeOutExpo(seg(t, 0.05, 0.34));
  const rule = easeOutCubic(seg(t, 0.2, 0.5));
  const block = easeOutExpo(seg(t, 0.34, 0.6));
  const words = HEADLINE.split(' ').filter(Boolean);
  // Laid out for the count: the last word's 0.18 reveal ends by 0.90 (see the header).
  const WORD_IN = 0.44, WORD_DUR = 0.18, WORDS_DONE = 0.90;
  const wordStep = Math.min(0.06, (WORDS_DONE - WORD_DUR - WORD_IN) / Math.max(1, words.length - 1));

  const BAND = BAND0;

  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden', color: INK}}>
      {/* masthead */}
      <div style={{position: 'absolute', left: M, top: 92, opacity: clamp01(mast * 1.3),
        transform: glide(`translateY(${(1 - mast) * -20}px)`, mast !== 1),
        font: `800 ${mastPx}px/0.9 var(--f-display, "Playfair Display", Georgia, serif)`, letterSpacing: '-0.02em'}}>{TITLE}</div>
      <div style={{position: 'absolute', right: M, top: 128, opacity: clamp01(seg(t, 0.28, 0.44)),
        font: `600 ${ISSUE_PX}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.16em'}}>{ISSUE}</div>
      {/* hairline rule */}
      <div style={{position: 'absolute', left: M, top: RULE_Y, height: 3, background: INK,
        width: (W - 2 * M) * rule}} />

      {/* hero colour block */}
      {/* the plate's own height yields to the band: 560 tall from y=320 reaches 880, which is inside the
          caption band on any frame narrower than 1400 (its FEATURE/ISSUE caption was 27px in at 1:1). */}
      <div style={{position: 'absolute', right: M, top: PLATE_TOP, width: PLATE_W, height: Math.min(PLATE_W, contentBottom(W, H) - PLATE_TOP),
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
          const on = easeOutCubic(clamp01(seg(t, WORD_IN + i * wordStep, WORD_IN + WORD_DUR + i * wordStep)));
          return <span key={i} style={{display: 'inline-block', marginRight: '0.28em', opacity: on,
            transform: glide(`translateY(${(1 - on) * 24}px)`, on !== 1)}}>{w}</span>;
        })}
      </div>

      {/* deck + body column rules.
          The deck, the body rules and the folio were pinned at bottom:190 / 96 / 84 — literal pixels that
          cleared the burned caption only while the reserved band happened to be 150px. The folio at 84 sat
          inside the band the moment it grew. All three are measured from the BAND now. */}
      {/* The deck lives in the headline's column. At a flat 720 it reached under the plate the moment the
          page narrowed, and ran through the plate's own FEATURE caption. */}
      {/* The deck and the contents index share ONE column (see DECK_BOTTOM): the deck sits on the index's
          real top however many rows it wraps to, and with no index it stands 62px above the band as before. */}
      <div style={{position: 'absolute', left: M, bottom: BAND + (contents.length ? 14 : 62), width: HEAD_W,
        display: 'flex', flexDirection: 'column'}}>
        <div style={{opacity: clamp01(seg(t, 0.72, 0.9)), marginBottom: contents.length ? C_DECK_GAP : 0,
          font: `italic 600 ${DECK_PX}px/${DECK_LH} var(--f-body, "Playfair Display", Georgia, serif)`, color: '#3a352c'}}>{DECK}</div>
        {/* THE CONTENTS LIST — where three columns of grey RULES used to stand in for body text.
            Twelve 5px bars at 13% opacity are a drawing of paragraphs that do not exist: on a rendered frame
            they read as a page that has not finished loading, and a viewer cannot decode a single one of
            them. A cover does not carry body columns anyway — it carries an index. So the space now holds
            real entries when the film supplies them, and nothing at all when it does not. Losing a little
            ink is the right trade against furniture nobody can read. */}
        {contents.length ? (
          <div style={{display: 'flex', flexWrap: 'wrap',
            maxWidth: HEAD_W, columnGap: C_COL_GAP, rowGap: C_ROW_GAP, opacity: clamp01(seg(t, 0.8, 0.95))}}>
            {contents.map((e, i) => (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: C_ITEM_GAP}}>
                <span style={{font: `700 ${C_NUM_PX}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.12em',
                  color: ACC}}>{String(i + 1).padStart(2, '0')}</span>
                <span style={{font: `600 ${C_PX}px/${leading(e, 1.2)} var(--f-body, "Playfair Display", Georgia, serif)`,
                  color: '#3a352c'}}>{e}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
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
