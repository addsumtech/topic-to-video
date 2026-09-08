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

import React from 'react';
import {AbsoluteFill, useVideoConfig, staticFile} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {UiSurface, type UiContent} from '../runtime/uiSurface';
import {captionBand, CONTENT_TOP, fitTextPx, fitBlockPx, textWidthPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 174; // 5.8s

const BG_D0 = '#0b0d13', FG_D0 = '#eef2f8', DIM_D0 = '#8f97a8', ACC_D0 = '#6c8cff';

// A conclusion has to be SAID before the next one arrives, and a short spoken sentence is about 1.2s. Four is
// the most that fits: at five the last note starts past 0.9 and never finishes darkening, which reads as the
// caption flashing rather than as a sentence being read.
const MAX_DEALT = 4;

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
  notes: NOTES = [], doc: DOC = [], src: SRC, pageW: SRC_W, pageH: SRC_H, blocks: SRC_BLOCKS} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const SURF = dna?.surface ?? '#ffffff';
  const LINE = dna?.surfaceBorder ?? '#d7dce6';
  const U = Math.min(W, H);

  const list = (ITEMS ?? []).filter((x) => String(x ?? '').trim()).slice(0, MAX_DEALT);
  if (!list.length) {
    throw new Error(
      'SourceDeal needs at least one non-empty `items` entry. The whole form is conclusions dealt out of a ' +
      'source that stays on screen; with nothing to deal it parks a document and argues nothing.');
  }
  const n = list.length;
  const captured = !!(SRC && SRC_BLOCKS && SRC_BLOCKS.length && SRC_W && SRC_H);

  // A ROW NEEDS A WIDE FRAME. Parked LEFT in portrait the document takes a third of a 1080px width and the
  // conclusions have nothing to be dealt into, so the axis turns: the source parks UP and the pills come out
  // below it. The argument does not care which edge the source is pushed to.
  const vert = W / H < 1.1;
  const band = H - captionBand(W, H);
  const pad = Math.round(U * 0.035);

  // ── sizes first, because the copy is one of the frame's walls ────────────────────────────────────────────
  const pillPx = list.reduce((px, s) => Math.min(px, fitTextPx(s, W * 0.30, Math.round(U * 0.032),
    {usable: 0.92})), Math.round(U * 0.032));
  const pillH = Math.round(pillPx * 2.4);
  // ONE WIDTH FOR EVERY PILL. Sized to its own text each conclusion is a different-length lozenge, and three
  // ragged shapes read as three unrelated labels rather than as a set being dealt from one place — the same
  // rule that makes sibling labels share one type size, applied to the container. Widest label decides.
  const pillW = Math.min(Math.round(list.reduce((w, s2) => Math.max(w, textWidthPx(s2, pillPx)), 0)
    + pillH * 1.1 + pillPx * 0.76), Math.round(W * (vert ? 0.80 : 0.44)));
  const notePx = Math.round(U * 0.026);
  const noteH = Math.round(notePx * 2.6);
  const rowH = pillH + (NOTES.length ? noteH + Math.round(pad * 0.4) : 0) + Math.round(pad * 0.5);

  const zoneTop = CONTENT_TOP;
  const zoneH = Math.max(Math.round(U * 0.25), band - zoneTop - pad);
  const dealW = vert ? Math.round(W * 0.82) : Math.round(W * 0.46);
  const docW = vert ? Math.round(W * 0.86) : Math.round(W * 0.62);
  const docH = vert ? Math.round(Math.min(zoneH * 0.44, docW / 1.5)) : Math.round(Math.min(zoneH, docW / 0.86));
  const docX = vert ? Math.round((W - docW) / 2) : Math.round(W * 0.03);
  const docY = zoneTop;

  // PARK, DO NOT FADE. The source slides most of the way off its own edge and scales about that edge, so it
  // stays anchored there instead of drifting inward as it shrinks — and about a third of it stays readable,
  // which is the difference between a source and a decoration.
  const park = easeInOutCubic(clamp01(seg(t, 0.06, 0.24)));
  // Upright the source goes off its own LEFT edge, which hides a margin. Stood up it would go off the TOP,
  // which hides the title — the one part of a document that says what it is — so it is pushed less far.
  const parkShift = vert ? 0 : -0.55, parkLift = vert ? -0.28 : 0;
  const parkScale = lerp(1, 0.92, park);
  // WHERE THE PARKED SOURCE ACTUALLY ENDS. Measured from the un-parked box — the obvious way, and the way
  // this was first written — the conclusions were placed against a document that is no longer there: at 9:16
  // it left a 360px dead band between the source and the first pill and used half the frame for nothing.
  const parkedEnd = (px: number) => px * (parkScale + (vert ? parkLift : parkShift));

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
  const rowStep = Math.max(rowH, Math.floor((band - dealTop - pad) / Math.max(1, n)));

  const content: UiContent = {title: TITLE, items: DOC.length ? DOC : undefined};

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* THE SOURCE, still being read */}
      <div style={{position: 'absolute', left: docX, top: docY, width: docW, height: docH,
        transformOrigin: vert ? '50% 0%' : '0% 50%',
        transform: `translate(${parkShift * park * 100}%, ${parkLift * park * 100}%) scale(${parkScale})`,
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
        // two curves, deliberately unequal: the pill is SEEN before it is SETTLED, which is what makes it
        // read as landing rather than as fading in
        const o = easeOutCubic(clamp01(seg(t, f, f + 0.035)));
        const b = easeOutBack(clamp01(seg(t, f, f + 0.062)));
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
            <div style={{display: 'flex', alignItems: 'center', height: pillH, width: pillW, boxSizing: 'border-box',
              padding: `0 ${Math.round(pillH * 0.55)}px`, borderRadius: 999, whiteSpace: 'nowrap',
              transform: `translateY(${(1 - b) * pillH * 0.32}px) scale(${lerp(0.94, 1, b)})`,
              background: SURF, border: `${Math.max(1, Math.round(U * 0.0016))}px solid ${LINE}`,
              // A TERNARY WITH TWO IDENTICAL BRANCHES is a decision that was never made: this read
              // `dna?.fg && dna.surface ? '#1c2029' : '#1c2029'` and so painted near-black text whatever the
              // ground was — on a dark DNA's surface the conclusions were black on near-black. No typecheck
              // can see it and no text gate measures contrast; it took looking at the delivered film.
              color: readableOn(SURF),
              font: `700 ${pillPx}px/${leading(label, 1.15)} var(--f-body, system-ui, sans-serif)`}}>
              <span style={{width: Math.round(pillPx * 0.34), height: Math.round(pillPx * 0.34),
                borderRadius: '50%', background: ACC, marginRight: Math.round(pillPx * 0.42)}} />
              {label}
            </div>
            {/* THE NOTE DARKENS AS IT IS READ, and clears before the next pill lands — one sentence on the
                frame at a time, because two conclusions on screen at once is the thing dealing them was for */}
            {note ? (
              <div style={{marginTop: Math.round(pad * 0.4), color: DIM, opacity: outv, textWrap: 'balance',
                font: `500 ${fitBlockPx(note, dealW, noteH, notePx, {usable: 0.92, leading: 1.35})}px/`
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
