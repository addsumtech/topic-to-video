// SHOT · Source Deal — the document stays on screen, pushed aside and still being read, while the conclusions
// drawn from it are dealt out one at a time.
//
// WHAT IT ARGUES, and what the obvious version loses. The obvious version fades the source out and shows the
// conclusions: three confident statements floating on a ground, which the viewer has no reason to believe and
// no way to place. Keeping the source IN FRAME — reduced to a sliver, still scrolling, visibly being read —
// makes every conclusion look like it came from somewhere. That is the whole shot: not "here are three
// findings" but "here are three findings FROM THIS".
//
// THE PACE IS THE NARRATION'S, NOT THE UI'S. Cards in a product normally stagger 80ms apart; these are more
// than a second apart, because each one has to be said. Dealt at UI speed the shot is over before the voice
// has finished the first conclusion, and the viewer reads three things while hearing one.
//
// THE SCROLL IS THE TELL. A parked document that sits still reads as a screenshot of a document; one that
// creeps reads as a document being read. It runs whole periods so the last frame lands where it started —
// a beat that ends mid-scroll cannot be cut away from cleanly.
//
// EVERY CONCLUSION IS DEALT, OR THE REGISTER SAYS IT CANNOT DEAL THEM. It used to take
// `items.filter(nonEmpty).slice(0, MAX_DEALT)`: a fifth finding was simply never dealt, on a shot whose whole
// claim is "here are the findings FROM THIS", and an empty entry vanished the same way. Three more pieces of
// film copy fell away in silence: a note past the last pill (notes are matched by position) had no pill to sit
// under; `doc` rows past the drawn table's seven were never printed; and a `src` without the rest of its
// capture (`pageW`, `pageH`, `blocks` — what scripts/capture_page.py writes together) was ignored in favour of
// the drawn table, so a film that captured its real source showed a generic one. Each now THROWS saying what
// to pass.

import React from 'react';
import {AbsoluteFill, useVideoConfig, staticFile} from 'remotion';
import {useT, useAnimSpan, springAt, SPRING_SEAT, seg, lerp, clamp01, easeInOutCubic,
        easeOutCubic} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {useDNA, contrastOf, readableOn} from '../runtime/dna';
import {UiSurface, type UiContent} from '../runtime/uiSurface';
import {CONTENT_TOP, captionBand, fitBlockPx, fitTextPx, textWidthPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useGlide} from '../runtime/glide';

export const DURATION = 174; // 5.8s

const BG_D0 = '#0b0d13', FG_D0 = '#eef2f8', DIM_D0 = '#8f97a8', ACC_D0 = '#6c8cff';

// A conclusion has to be SAID before the next one arrives, and a short spoken sentence is about 1.2s. Four is
// the most that fits: the deal runs 0.26-0.92 in equal slots (0.66/n), so at four each conclusion gets 0.165
// of the clip — ~0.96s at this register's 5.8s — and at five 0.132, ~0.77s, which reads as the caption
// flashing rather than as a sentence being read. (An earlier version of this note said the fifth note "starts
// past 0.9"; that was the old spacing — the slots have since been divided from the window that exists.)
export const MAX_DEALT = 4;
/** The drawn source table's row count — runtime/uiSurface's `Rows` draws exactly seven; a `doc` row past it is
 *  never printed, so it is refused here rather than lost. Keep in step with uiSurface. */
const DOC_ROWS = 7;

/** How much of `text` has been read at progress `u`, snapped forward to a word boundary where there is one. */
const wordCut = (text: string, u: number) => {
  const raw = Math.round(text.length * clamp01(u));
  if (raw <= 0 || raw >= text.length) return raw;
  if (!/\s/.test(text)) return raw;              // CJK: every character is its own boundary
  const nxt = text.indexOf(' ', raw);
  return nxt < 0 ? text.length : nxt;
};

export const SourceDeal: React.FC<{
  title?: string;
  items?: string[];
  notes?: string[];
  doc?: string[];
  src?: string;
  pageW?: number;
  pageH?: number;
  blocks?: {x: number; y: number; w: number; h: number}[];
}> = ({title: TITLE = 'Source', items: ITEMS = ['Quick start', 'Bundle plan', 'Starter kit'],
  notes: NOTES_IN = [], doc: DOC_IN = [], src: SRC, pageW: SRC_W, pageH: SRC_H, blocks: SRC_BLOCKS} = {}) => {
  const DOC = rows<string>(DOC_IN, 'doc', 'SourceDeal');
  const NOTES = rows<string>(NOTES_IN, 'notes', 'SourceDeal');
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H, fps} = useVideoConfig();
  const span = useAnimSpan();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const SURF = dna?.surface ?? '#ffffff';
  const LINE = dna?.surfaceBorder ?? '#d7dce6';
  // The conclusion's ink is the FILM's ink whenever that is readable on the pill, and only falls back when
  // it is not — `readableOn` alone picks the highest-contrast candidate, which would throw away a themed
  // DNA's colour in favour of pure white on every dark surface.
  const PILL_INK = contrastOf(FG, SURF) >= 4.5 ? FG : readableOn(SURF);
  const U = Math.min(W, H);

  // Every conclusion, note, row and capture the film gave is drawn, or it throws — see the header.
  if (Array.isArray(ITEMS) && ITEMS.length > MAX_DEALT) {
    throw new Error(
      `SourceDeal deals 1-${MAX_DEALT} conclusions (got ${ITEMS.length}). Each has to be said before the next ` +
      `lands, and at five each gets ~0.77s of a 5.8s beat. Keep the ${MAX_DEALT} that matter, ` +
      `or deal the rest from the same source in a second beat.`);
  }
  const list = (Array.isArray(ITEMS) ? ITEMS : []).map((x, i) => {
    const label = String(x ?? '').trim();
    if (!label) throw new Error(`SourceDeal: conclusion ${i + 1} is empty.`);
    return label;
  });
  if (!list.length) {
    throw new Error(
      'SourceDeal needs at least one `items` entry. The whole form is conclusions dealt out of a ' +
      'source that stays on screen; with nothing to deal it parks a document and argues nothing.');
  }
  const n = list.length;
  if (NOTES.length > n) {
    throw new Error(
      `SourceDeal got ${NOTES.length} \`notes\` for ${n} conclusions. Notes are matched to pills by position, ` +
      `so note ${n + 1} onward would have no pill to sit under. Pass one note per conclusion (or fewer).`);
  }
  if (DOC.length > DOC_ROWS) {
    throw new Error(
      `SourceDeal's drawn source shows ${DOC_ROWS} \`doc\` rows (got ${DOC.length}). Pass the ${DOC_ROWS} lines ` +
      `that carry the conclusions, or capture the real page and pass it as \`src\`.`);
  }
  const captured = !!(SRC && SRC_BLOCKS && SRC_BLOCKS.length && Number(SRC_W) > 0 && Number(SRC_H) > 0);
  if (SRC && !captured) {
    const missing = [!(Number(SRC_W) > 0) && '`pageW`', !(Number(SRC_H) > 0) && '`pageH`',
      !(SRC_BLOCKS && SRC_BLOCKS.length) && '`blocks`'].filter(Boolean).join(', ');
    throw new Error(
      `SourceDeal was given \`src\` without ${missing} — an incomplete capture, and the drawn table would ` +
      `stand in for the real source. Pass the whole capture scripts/capture_page.py writes (src, pageW, ` +
      `pageH, blocks), or drop \`src\` to use the drawn table.`);
  }

  // A ROW NEEDS A WIDE FRAME. Parked LEFT in portrait the document takes a third of a 1080px width and the
  // conclusions have nothing to be dealt into, so the axis turns: the source parks UP and the pills come out
  // below it. The argument does not care which edge the source is pushed to.
  const vert = W / H < 1.1;
  const band = H - captionBand(W, H);
  const pad = Math.round(U * 0.035);

  // ── sizes first, because the copy is one of the frame's walls ────────────────────────────────────────────
  // ONE MEASURE FOR THE LABEL AND THE PILL IT SITS IN. The label was fitted to `W * 0.30` while the pill
  // was capped at `W * 0.44` (0.80 stacked) — two different numbers for the same string. In Latin the fit
  // bound first and nothing showed; in Chinese the widest label plus its padding exceeded the CAP, the pill
  // stopped growing, and the text ran 343px off the left edge of the frame. So the label is fitted to the
  // text column the pill will actually have at that size. The two depend on each other, so it settles in
  // two passes — and it can only ever make the type smaller, so the Latin frames are untouched.
  const PILL_BASE = Math.round(U * 0.032);
  const capW = Math.round(W * (vert ? 0.80 : 0.44));
  const innerOf = (px: number) => Math.max(40, capW - Math.round(px * 2.4) * 1.1 - px * 0.76);
  let pillPx = PILL_BASE;
  for (let i = 0; i < 2; i++) {
    const measure = Math.min(W * 0.30, innerOf(pillPx));
    pillPx = list.reduce((px, s) => Math.min(px, fitTextPx(s, measure, PILL_BASE, {usable: 0.92})), pillPx);
  }
  const pillH = Math.round(pillPx * 2.4);
  // ONE WIDTH FOR EVERY PILL. Sized to its own text each conclusion is a different-length lozenge, and three
  // ragged shapes read as three unrelated labels rather than as a set being dealt from one place — the same
  // rule that makes sibling labels share one type size, applied to the container. Widest label decides.
  const pillW = Math.min(Math.round(list.reduce((w, s2) => Math.max(w, textWidthPx(s2, pillPx)), 0)
    + pillH * 1.1 + pillPx * 0.76), Math.round(W * (vert ? 0.80 : 0.44)));
  const notePx = Math.round(U * 0.026);
  // THE NOTE ROW RESERVES FOR THE LINES IT TAKES. 2.6 is two lines and a little air, measured on Latin
  // notes; a Chinese note in the same column runs to three and the last one lands in the caption band
  // (34px of it at 1:1). Counted by breaking each note in the column it actually wraps in.
  const noteLines = NOTES.length
    ? Math.max(1, ...NOTES.map((x) => wrapLines(String(x ?? ''), notePx, Math.max(40, capW - pillPx))))
    : 1;
  const noteH = Math.round(notePx * Math.max(2.6, noteLines * 1.3 + 0.3));
  const rowH = pillH + (NOTES.length ? noteH + Math.round(pad * 0.4) : 0) + Math.round(pad * 0.5);

  const zoneTop = CONTENT_TOP;
  const zoneH = Math.max(Math.round(U * 0.25), band - zoneTop - pad);
  const dealW = vert ? Math.round(W * 0.82) : Math.round(W * 0.46);
  const docW = vert ? Math.round(W * 0.86) : Math.round(W * 0.62);
  const docH = vert ? Math.round(Math.min(zoneH * 0.44, docW / 1.5)) : Math.round(Math.min(zoneH, docW / 0.86));
  const docX = vert ? Math.round((W - docW) / 2) : Math.round(W * 0.03);
  const docY = zoneTop;

  // PARK, DO NOT FADE — AND DO NOT SLIDE OFF. The source used to slide most of the way off its own edge
  // (55% upright, 28% stood up) and scale about that edge, on the reasoning that what went off-frame was
  // the document's margin. It was not. What a left slide hides is the START of every line and the title —
  // the one part of a document that says what it is — and what it leaves on frame is the ragged right end
  // of each row, which reads as nothing at all. Measured: four of the four rows a film supplies in `doc`
  // were cut by 343px at 16:9 and 257px at 4:3, in ANY language. The register's own demo default is an
  // EMPTY doc, which is the only reason this never showed on the English sweep.
  //
  // So it shrinks in place instead. The parked source occupies the same FOOTPRINT it did before — it ends
  // at exactly the same x, so every number the conclusions are laid out from is unchanged — but the whole
  // document is inside it: title, line starts and all, smaller.
  const park = easeInOutCubic(clamp01(seg(t, 0.06, 0.24)));
  // The fraction of its own box the parked source occupies. These are the two numbers the old slide left
  // visible (0.92 - 0.55 upright, 0.92 - 0.28 stood up), so the room handed to the conclusions is the same.
  const PARKED = vert ? 0.64 : 0.37;
  const parkScale = lerp(1, PARKED, park);
  // WHERE THE PARKED SOURCE ACTUALLY ENDS. Measured from the un-parked box — the obvious way, and the way
  // this was first written — the conclusions were placed against a document that is no longer there: at 9:16
  // it left a 360px dead band between the source and the first pill and used half the frame for nothing.
  const parkedEnd = (px: number) => px * parkScale;

  // whole periods, so the last frame is where the first one was and the next shot can cut in on a still doc
  const scroll = (t * 3) % 1;

  // ── the deal ─────────────────────────────────────────────────────────────────────────────────────────────
  // THE INTERVAL IS A SPOKEN SENTENCE, and it has to be derived from the room, not from a fraction someone
  // liked. Spread over 0.44 the gap came out at 0.147 for three conclusions, which left each note fully
  // legible for about three frames — the pills dealt correctly and the sentences under them flashed. The
  // window that actually exists is 0.26 to 0.92, and dividing THAT reproduces the reference's 0.22 at three
  // and still leaves a readable 0.165 at four.
  const T0 = list.map((_, i) => 0.26 + i * (0.66 / Math.max(1, n)));
  // Upright, the conclusions are CENTRED in the room the parked source leaves, not butted up against it.
  // Anchored to the source's edge they sat in a narrow column with two fifths of the frame empty to their
  // right — the source on one side, the conclusions beside it, and a third of the picture doing nothing.
  const dealLeft = Math.round(docX + parkedEnd(docW) + pad * 1.6);
  const dealX = vert ? Math.round((W - dealW) / 2)
    : Math.round(dealLeft + Math.max(0, (W - Math.round(W * 0.05) - dealLeft - dealW) / 2));
  const dealTop = vert ? Math.round(docY + parkedEnd(docH) + pad)
    : zoneTop + Math.round((zoneH - rowH * n) / 2);

  // The rows SPREAD into the room they are given rather than packing at the top of it. Packed, a portrait
  // cut put three conclusions in the upper third and left the rest of the frame doing nothing — the same
  // failure as a row that keeps its 16:9 size in a 9:16 frame, arrived at from the other direction.
  // THE SPREAD LEAVES ROOM FOR THE LAST ROW, not for an average one. Dividing the room by `n` spaces the
  // TOPS evenly and then the final row still needs its own `rowH` below its top — so the deeper a row is
  // (a Chinese note runs to three lines where a Latin one runs to two), the further the last note reaches
  // past the band. Divide the room MINUS one row by the gaps between them, which is what "these all fit"
  // actually means.
  // AND WHEN THE ROWS DO NOT FIT AT ALL, THE TYPE YIELDS. Spreading only decides where the tops go; it
  // cannot help when `n` rows each as deep as a Chinese note need more room than the zone has, and the last
  // note then lands in the caption band whatever the spacing. The sizes are scaled by the shortfall — one
  // pass, because the shortfall is computed from the sizes it corrects — so the shot degrades by getting
  // quieter rather than by drawing over the subtitle. `k` is 1 wherever the rows already fitted.
  const roomForRows = Math.max(1, band - dealTop - pad);
  const k = Math.min(1, roomForRows / Math.max(1, n * rowH));
  const pillPxF = Math.max(12, Math.round(pillPx * k));
  const pillHF = Math.round(pillPxF * 2.4);
  const notePxF = Math.max(10, Math.round(notePx * k));
  const noteHF = Math.round(noteH * k);
  const rowHF = pillHF + (NOTES.length ? noteHF + Math.round(pad * 0.4) : 0) + Math.round(pad * 0.5);
  const rowStep = Math.max(rowHF, Math.floor((band - dealTop - pad - rowHF) / Math.max(1, n - 1)));

  const content: UiContent = {title: TITLE, items: DOC.length ? DOC : undefined};

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* THE SOURCE, still being read */}
      <div style={{position: 'absolute', left: docX, top: docY, width: docW, height: docH,
        transformOrigin: vert ? '50% 0%' : '0% 50%',
        transform: `scale(${parkScale})`,
        overflow: 'hidden', borderRadius: dna?.radius ?? 10,
        border: `${dna?.borderWidth ?? 1}px solid ${LINE}`, background: SURF}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: docW, height: docH * 1.35,
          transform: `translateY(${-scroll * (docH * 0.35)}px)`}}>
          {captured ? (
            <img src={staticFile(SRC!)} width={docW} height={Math.round(docW * (SRC_H! / SRC_W!))} alt=""
              style={{display: 'block', width: docW, height: Math.round(docW * (SRC_H! / SRC_W!))}} />
          ) : (
            <UiSurface page="table" W={docW} H={Math.round(docH * 1.35)} dna={dna} content={content} seed={5} />
          )}
        </div>
      </div>

      {/* THE CONCLUSIONS, dealt */}
      {list.map((label, i) => {
        const f = T0[i];
        // TWO CURVES, DELIBERATELY UNEQUAL: the pill is SEEN before it is SETTLED, which is what makes it
        // read as landing rather than as fading in. The settle is a SPRING, not an eased curve — the
        // reference card's own note is that the overshoot is the手感 of a card dealt onto a table and that
        // an eased version "变成平淡的浮上来". A spring also gives the pill mass, so its landing is a
        // property of the object rather than of one curve every element in the library shares.
        const o = easeOutCubic(clamp01(seg(t, f, f + 0.035)));
        const b = springAt(t, span, fps, f, SPRING_SEAT);
        const note = NOTES[i];
        const cs = f + 0.05;
        const ce = (i + 1 < n ? T0[i + 1] - 0.03 : 0.98);
        const inn = clamp01(seg(t, cs, cs + (ce - cs) * 0.7));
        const outv = 1 - clamp01(seg(t, ce - 0.05, ce));
        const top = dealTop + i * rowStep;
        // DARKEN BY WORD, NOT BY CHARACTER. A character cut lands inside a Latin word — "the pro|cess" — which
        // reads as a rendering fault rather than as reading. CJK has no such boundary, so a character IS the
        // unit there and the same call is right for both.
        const chars = note ? wordCut(note, inn) : 0;
        return (
          <div key={i} style={{position: 'absolute', left: dealX, top, width: dealW, opacity: o}}>
            <div style={{display: 'flex', alignItems: 'center', height: pillHF, width: pillW, boxSizing: 'border-box',
              padding: `0 ${Math.round(pillHF * 0.55)}px`, borderRadius: 999, whiteSpace: 'nowrap',
              transform: glide(`translateY(${(1 - b) * pillHF * 0.32}px) scale(${lerp(0.94, 1, b)})`, b !== 1),
              background: SURF, border: `${Math.max(1, Math.round(U * 0.0016))}px solid ${LINE}`,
              // A TERNARY WITH TWO IDENTICAL BRANCHES is a decision that was never made: this read
              // `dna?.fg && dna.surface ? '#1c2029' : '#1c2029'` and so painted near-black text whatever the
              // ground was — on a dark DNA's surface the conclusions were black on near-black. No typecheck
              // can see it and no text gate measures contrast; it took looking at the delivered film.
              color: PILL_INK,
              font: `700 ${pillPxF}px/${leading(label, 1.15)} var(--f-body, system-ui, sans-serif)`}}>
              <span style={{width: Math.round(pillPxF * 0.34), height: Math.round(pillPxF * 0.34),
                borderRadius: '50%', background: ACC, marginRight: Math.round(pillPxF * 0.42)}} />
              {label}
            </div>
            {/* THE NOTE DARKENS AS IT IS READ, and clears before the next pill lands — one sentence on the
                frame at a time, because two conclusions on screen at once is the thing dealing them was for */}
            {note ? (
              <div style={{marginTop: Math.round(pad * 0.4), color: DIM, opacity: outv, textWrap: 'balance',
                font: `500 ${fitBlockPx(note, dealW, noteHF, notePxF, {usable: 0.92, leading: 1.35})}px/`
                  + `${leading(note, 1.35)} var(--f-body, system-ui, sans-serif)`}}>
                <span style={{color: FG}}>{note.slice(0, chars)}</span>
                <span style={{opacity: 0.45}}>{note.slice(chars)}</span>
              </div>
            ) : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default SourceDeal;
