// SHOT · StateSheet — one thing IS its states, laid out as the contact sheet the directory already is.
//
// A grid of real pictures, printed in a raster sweep the way a contact sheet comes off a sheet-fed printer,
// each cell carrying the picture and the name of the state it is. One cell is the state the thing is in
// right now: it lifts, takes the accent border, and the rest settle under it.
//
// WHY IT WAS BUILT RATHER THAN CAST. A film about a desktop companion had a beat whose whole sentence was
// "twenty character sets, seventeen states each — on disk that is seventeen files", and it drew a TERMINAL
// TREE of the filenames: `idle-wave.svg`, `thinking.svg`, `typing.svg`. An independent reviewer put the
// cost plainly — the beat is ABOUT what the character looks like in seventeen states, and it drew the names
// of the pictures while the pictures themselves sat in the repository the same beat's `source_ref` already
// cited. A list of names can say HOW MANY. It cannot say that each one is a different drawing, which is the
// only reason seventeen is worth saying out loud.
//
// AND IT IS A FORM, NOT A PRODUCT. Nothing here is specific to a companion, a sprite or anyone's app: the
// cells are whatever pictures the film hands it. A beat about a typeface's weights, a component's variants,
// a species' plumages or a machine's error states uses the same register — what it carries is "this ONE
// thing is actually N pictures, and here they all are, countable".
//
// THE PICTURES MUST BE STATIC. An SVG referenced by <img> runs its own CSS/SMIL clock off WALL time, not off
// Remotion's frame counter, so the same frame renders differently twice and the film is no longer
// deterministic. Whatever prepares the assets has to strip the animation declarations first; this register
// cannot check that from inside, so it is said here and in the authoring notes.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 200; // ~6.7s

type Cell = {src: string; label?: string};

export const StateSheet: React.FC<{
  /** what the sheet is OF — the one thing all these pictures are */
  title?: string;
  /** the directory / collection line, set in the mono face like the path it is */
  dir?: string;
  /** the pictures and the state each one is. The count IS the argument, so nothing is capped away. */
  cells?: Cell[];
  /** which cell is the state the thing is in right now (0-based); -1 or absent marks none */
  mark?: number;
  /** one line under the sheet */
  note?: string;
}> = ({
  title: TITLE = '', dir: DIR = '', cells: CELLS = [], mark: MARK = -1, note: NOTE = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  const cells = (Array.isArray(CELLS) ? CELLS : []).filter((c) => c && String(c.src ?? '').trim());
  if (!cells.length) {
    throw new Error(
      'StateSheet needs at least one `cells` entry — {src, label}. The form exists to show that one thing ' +
      'IS several pictures; with no pictures it is a caption over an empty sheet, which is the "measuring ' +
      'an empty plate" result every gate in this repo would then report as clean.');
  }

  const title = String(TITLE ?? '').trim();
  const dir = String(DIR ?? '').trim();
  const note = String(NOTE ?? '').trim();
  const mark = Number.isFinite(MARK) ? Math.trunc(MARK as number) : -1;

  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 50% 34%, #141a26, #080a0f 74%)';
  const FG = dna?.fg ?? '#eef2f8';
  const DIM = dna?.dim ?? '#7c8699';
  const ACC = dna?.accent ?? '#3dd6a4';
  const SURF = dna?.surface ?? '#131a26';
  const LINE = dna?.surfaceBorder ?? dna?.line ?? '#243149';
  const MONO = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';

  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);

  const headPx = title ? fitTextPx(title, W * 0.86, Math.round(U * 0.040), {usable: 1}) : 0;
  const dirPx = Math.round(U * 0.018);
  const notePx = Math.round(U * 0.019);
  const headH = (title ? Math.round(headPx * 1.25) : 0) + (dir ? Math.round(dirPx * 1.9) : 0);
  const noteH = note ? Math.round(notePx * 2.2) : 0;

  const gridTop = zTop + headH + Math.round(U * 0.016);
  const gridH = Math.max(U * 0.2, zBot - gridTop - noteH);
  const gridW = W * 0.88;
  const gridLeft = (W - gridW) / 2;

  // THE GRID IS SOLVED, NOT PICKED. A fixed column count is a constant tuned on one cell count: six columns
  // is right for seventeen pictures at 16:9 and wrong for five, and wrong again at 9:16 where the same six
  // would each be a sixth of a 1080 frame. Search the column counts and keep the one whose cells come out
  // largest inside the zone — which is what a contact sheet does when the paper changes.
  const gap = Math.round(U * 0.012);
  const labelH = Math.round(U * 0.022);
  let cols = 1, best = -1;
  for (let c = 1; c <= cells.length; c++) {
    const rws = Math.ceil(cells.length / c);
    const w = (gridW - gap * (c - 1)) / c;
    const h = (gridH - gap * (rws - 1)) / rws - labelH;
    if (h <= 0 || w <= 0) continue;
    const s = Math.min(w, h);                            // a sprite is square; the cell follows it
    if (s > best) {
      best = s; cols = c;
    }
  }
  // EVERYTHING IS SPACED BY THE CELL, not by its share of the zone. Laying rows out on `cellH` — the
  // height a row was ALLOTTED — while drawing a square `side` inside it put a band of empty ground between
  // every row and made the sheet read as two stranded strips rather than one sheet.
  const rows = Math.ceil(cells.length / cols);
  const side = Math.max(1, Math.min((gridW - gap * (cols - 1)) / cols,
                                    (gridH - gap * (rows - 1)) / rows - labelH));
  const pitchX = side + gap, pitchY = side + labelH + gap;
  const usedW = cols * side + gap * (cols - 1);
  const usedH = rows * (side + labelH) + gap * (rows - 1);
  const x0 = gridLeft + (gridW - usedW) / 2;
  const y0 = gridTop + Math.max(0, (gridH - usedH) / 2);

  // THE SWEEP IS THE SHEET PRINTING, so it runs in reading order and every cell lands before the close —
  // a cell that arrives after the clip ends is a picture the film was given and never drew, which is the
  // defect this library has now met twice (WordTunnel's last phrase, SplitFlap's unbounded cascade).
  const SWEEP_FROM = 0.10, SWEEP_TO = 0.62;
  const per = (SWEEP_TO - SWEEP_FROM) / Math.max(1, cells.length);
  const headIn = easeOutCubic(clamp01(seg(t, 0.02, 0.18)));
  const lift = easeOutCubic(clamp01(seg(t, 0.66, 0.82)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.74, 0.90)));

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {title ? (
        <div style={{position: 'absolute', top: zTop, left: W * 0.07, width: W * 0.86, opacity: headIn,
          transform: `translateY(${(1 - headIn) * U * 0.014}px)`,
          color: FG, textWrap: 'balance',
          font: `700 ${headPx}px/${leading(title, 1.2)} var(--f-display, Inter, system-ui, sans-serif)`}}>
          {title}
        </div>
      ) : null}
      {dir ? (
        <div style={{position: 'absolute', top: zTop + (title ? Math.round(headPx * 1.25) : 0),
          left: W * 0.07, width: W * 0.86, opacity: headIn * 0.9, color: DIM,
          font: `500 ${dirPx}px/1.4 ${MONO}`, letterSpacing: '0.03em',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{dir}</div>
      ) : null}

      {cells.map((c, i) => {
        const r = Math.floor(i / cols), k = i % cols;
        const on = easeOutCubic(clamp01(seg(t, SWEEP_FROM + i * per, SWEEP_FROM + i * per + per * 2.2)));
        const isMark = i === mark;
        const up = isMark ? lift : 0;
        // the LAST row is centred on its own count, so 17 cells in a 9-wide sheet do not leave the
        // short row hanging off the left edge like a truncated one.
        const inRow = Math.min(cols, cells.length - r * cols);
        const rowW = inRow * side + gap * (inRow - 1);
        const cx = gridLeft + (gridW - rowW) / 2 + k * pitchX;
        const cy = y0 + r * pitchY;
        return (
          <div key={c.src + i} style={{position: 'absolute', left: cx, top: cy,
            width: side, height: side + labelH, opacity: on,
            transform: `translateY(${(1 - on) * U * 0.02 - up * U * 0.012}px)`}}>
            <div style={{position: 'absolute', left: 0, top: 0, width: side, height: side,
              borderRadius: Math.round(U * 0.010), background: SURF,
              border: `${isMark ? 2 : 1}px solid ${isMark ? ACC : LINE}`,
              boxShadow: isMark
                ? `0 0 ${Math.round(U * 0.03 * up)}px ${ACC}${up > 0.5 ? '55' : '22'}`
                : `0 ${Math.round(U * 0.004)}px ${Math.round(U * 0.012)}px #0006`,
              overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <Img src={staticFile(c.src)}
                style={{width: '84%', height: '84%', objectFit: 'contain'}} />
            </div>
            {c.label ? (
              <div style={{position: 'absolute', left: 0, top: side + Math.round(U * 0.004), width: side,
                textAlign: 'center', color: isMark ? ACC : DIM,
                font: `500 ${Math.round(labelH * 0.62)}px/1.2 ${MONO}`,
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{c.label}</div>
            ) : null}
          </div>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.07, top: zBot - noteH + Math.round(U * 0.004),
          width: W * 0.86, opacity: noteIn, color: DIM, textWrap: 'balance',
          font: `500 ${notePx}px/${leading(note, 1.35)} var(--f-body, system-ui, sans-serif)`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default StateSheet;
