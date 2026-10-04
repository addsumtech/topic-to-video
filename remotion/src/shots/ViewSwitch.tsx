// SHOT · ViewSwitch — one body of records, several VIEWS of it: what changes between tabs is the SHAPE, and
// the rows keep their identity, their order and their words.
//
// WHAT IT ARGUES, AND WHY THE LIBRARY HAD NO WAY TO SAY IT. "Several things that are really one thing" was
// already sayable — a cube turns to show four faces, a rail seats modules onto one standard, a stack shows
// the layers something is made of. None of them says THIS: that the same records are being re-presented, so
// the difference between two screens is a presentation and not a copy. The distinction matters wherever a
// system claims one source of truth — a database and its materialised views, a spreadsheet that is also an
// application, a design system themed twice, one dataset drawn three ways, a document and its outline. A
// cube asserts four DIFFERENT contents on one object; this asserts one content in four arrangements, which
// is the opposite claim and the harder one to draw, because the proof is that nothing changed.
//
// SO THE PROOF IS THE MOTION. Each row is ONE element for the whole shot and travels from its place in the
// old arrangement to its place in the new one. It is never re-created per view, its ordinal never changes,
// and its words never change — a viewer watching a row move is watching the argument. The substrate under
// them is named once and never re-drawn, because it is the thing that did not move.
//
// EVERY CLAIM COMES FROM A PROP. A view's `shape` is declared by the film, never picked by the tab's index —
// a shape chosen by position is precisely the "widget by cell number" defect this library keeps finding, and
// here it would also make the register lie about which view looks like what. A view with no shape throws.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeInOutCubic, easeOutCubic, lerp} from '../runtime/motion';
import {captionBand, CONTENT_TOP, fitTextPx, fitBlockPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn} from '../runtime/dna';
import {onAccentInk} from '../runtime/onAccent';
import {useGlide} from '../runtime/glide';

export const DURATION = 180; // 6s

/** Four tabs is a strip; a fifth stops being readable as a set of alternatives at any frame width and
 *  becomes navigation, which is a different claim. */
export const MAX_VIEWS = 4;
/** Six rows is what every one of the shapes below can hold at a legible size — a board gives each of six a
 *  sixth of the width, and a seventh column sets its label under the floor. */
export const MAX_VIEW_ROWS = 6;

export type ViewShape = 'list' | 'cards' | 'board' | 'panel';
const SHAPES: ViewShape[] = ['list', 'cards', 'board', 'panel'];

const BG_D0 = '#f3efe6', FG_D0 = '#171a22', DIM_D0 = '#6e7488',
  ACC_D0 = '#2b4fb8', SURF_D0 = '#fbf8f1', LINE_D0 = '#cfc5b0';

type View = {
  /** the tab's own name */
  label?: string;
  /** what this view arranges the same rows INTO — declared, never inferred from the tab's position */
  shape?: ViewShape;
};

type Row = {
  /** the record's name — it is the same in every view, because that is the claim */
  label?: string;
  /** one short line with it */
  note?: string;
};

const DEMO_VIEWS: View[] = [
  {label: 'table', shape: 'list'},
  {label: 'cards', shape: 'cards'},
  {label: 'board', shape: 'board'},
];
const DEMO_ROWS: Row[] = [
  {label: 'first record', note: 'a line about it'},
  {label: 'second record', note: 'a line about it'},
  {label: 'third record', note: 'a line about it'},
  {label: 'fourth record', note: 'a line about it'},
];

type Rect = {x: number; y: number; w: number; h: number};

/** Where each row sits in a given arrangement. Pure geometry — the same n rows, laid out n different ways. */
const rectsFor = (shape: ViewShape, n: number, box: Rect, gap: number): Rect[] => {
  const out: Rect[] = [];
  if (shape === 'list') {
    const h = box.h / n;
    for (let i = 0; i < n; i++) out.push({x: box.x, y: box.y + i * h, w: box.w, h: h - gap * 0.5});
  } else if (shape === 'board') {
    const w = box.w / n;
    for (let i = 0; i < n; i++) out.push({x: box.x + i * w, y: box.y, w: w - gap * 0.6, h: box.h});
  } else if (shape === 'panel') {
    const headH = box.h * 0.44;
    out.push({x: box.x, y: box.y, w: box.w, h: headH - gap * 0.5});
    const rest = Math.max(1, n - 1);
    const h = (box.h - headH) / rest;
    for (let i = 1; i < n; i++) out.push({x: box.x, y: box.y + headH + (i - 1) * h, w: box.w, h: h - gap * 0.5});
  } else {
    const cols = n <= 2 ? n : n <= 4 ? 2 : 3;
    const rowsN = Math.ceil(n / cols);
    const w = box.w / cols, h = box.h / rowsN;
    for (let i = 0; i < n; i++) {
      out.push({x: box.x + (i % cols) * w, y: box.y + Math.floor(i / cols) * h,
        w: w - gap * 0.6, h: h - gap * 0.5});
    }
  }
  return out;
};

export const ViewSwitch: React.FC<{
  kicker?: string;
  /** what the rows ARE — the one thing under every view, named once */
  body?: string;
  views?: View[];
  rows?: Row[];
  /** which view the frame rests on (0-based). Omitted, the shot WALKS them, which is the whole argument. */
  at?: number;
  note?: string;
}> = ({
  kicker = 'THE SAME RECORDS',
  body = 'one store',
  views = DEMO_VIEWS,
  rows = DEMO_ROWS,
  at,
  note = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();

  const vs = (Array.isArray(views) ? views : []).filter((v) => v && String(v.label ?? '').trim());
  const rs = (Array.isArray(rows) ? rows : []).filter((r) => r && String(r.label ?? '').trim());
  if (vs.length < 2) {
    throw new Error(
      'ViewSwitch needs at least TWO `views`. The register\'s claim is that the same rows are re-arranged; ' +
      'with one arrangement there is nothing to be the same across.');
  }
  if (vs.length > MAX_VIEWS) {
    throw new Error(`ViewSwitch holds at most ${MAX_VIEWS} views, got ${vs.length}.`);
  }
  if (rs.length < 2) {
    throw new Error(
      'ViewSwitch needs at least TWO `rows`. One record cannot show that an arrangement changed while the ' +
      'records did not.');
  }
  if (rs.length > MAX_VIEW_ROWS) {
    throw new Error(
      `ViewSwitch holds at most ${MAX_VIEW_ROWS} rows, got ${rs.length}. A board view gives each row a ` +
      'column, and past six the column sets its label under the size anyone reads.');
  }
  const bad = vs.find((v) => !SHAPES.includes(v.shape as ViewShape));
  if (bad) {
    throw new Error(
      `ViewSwitch view ${JSON.stringify(bad.label)} has no valid \`shape\` — one of ${SHAPES.join(' | ')}. ` +
      'The shape is what that view LOOKS like, so it is the film\'s claim, not the tab\'s position: picking ' +
      'it by index is how a register comes to assert an arrangement nobody chose.');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const LINE = dna?.line ?? LINE_D0;
  const RAD = dna?.radius ?? 6;
  const BW = Math.max(1, dna?.borderWidth ?? 1);
  const disp = dna?.fontDisplay ?? 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyFace = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';

  const INK = readableOn(SURF, FG, GROUND, '#0a0d14', '#ffffff');
  const DIM = dimOn(SURF, INK, 4.5);
  const GROUND_DIM = dimOn(GROUND, readableOn(GROUND, FG, '#0a0d14', '#ffffff'), 4.5);
  // THE ACTIVE TAB IS THE ONE REVERSED OBJECT IN THE FRAME. Its ink is measured against the block it sits on
  // (`onAccentInk`), which on a light-stock system is also the only place the second accent can be type at
  // all — so "which view you are looking at" is the one thing that colour ever means in a film.
  const TAB_BLOCK = readableOn(GROUND, ACC, INK);
  const TAB_INK = onAccentInk(TAB_BLOCK, dna?.accent2, dna?.onAccent, GROUND);

  const U = Math.min(W, H);
  const n = rs.length, m = vs.length;
  const top = CONTENT_TOP;
  const bottom = H - captionBand(W, H);

  const kickPx = Math.round(U * 0.024);
  const tabPx = Math.round(U * 0.028);
  const bodyPx = Math.round(U * 0.026);
  const notePx = Math.round(U * 0.026);
  const noteH = note ? inkBlockH(notePx, 2) + Math.round(U * 0.016) : 0;

  const kickH = inkBlockH(kickPx) + Math.round(U * 0.018);
  const tabH = Math.round(inkBlockH(tabPx) + U * 0.024);
  const bodyH = body ? inkBlockH(bodyPx) + Math.round(U * 0.026) : 0;

  const pad = Math.round(W * 0.06);
  const gap = Math.round(U * 0.018);
  const boxY = top + kickH + tabH + Math.round(U * 0.030);
  const boxH = Math.max(U * 0.22, bottom - noteH - bodyH - boxY);
  const box: Rect = {x: pad, y: boxY, w: W - pad * 2, h: boxH};

  // WHICH VIEW, AND HOW FAR BETWEEN TWO. Pinned by `at`, else the shot walks every view with a HOLD on each
  // one — the travel has to be watchable or the register proves nothing.
  const pinned = Number.isFinite(at as number) ? Math.max(0, Math.min(m - 1, Math.round(at as number))) : null;
  const enter = clamp01(seg(t, 0.03, 0.18));
  let idx = 0, frac = 0;
  if (pinned === null) {
    const span = clamp01(seg(t, 0.16, 0.94)) * (m - 1);
    idx = Math.min(m - 2, Math.floor(span));
    frac = easeInOutCubic(clamp01((span - idx) * 1.45 - 0.22));   // hold, travel, hold
  } else {
    idx = Math.min(pinned, m - 1);
    frac = 0;
  }
  const a = rectsFor(vs[idx].shape as ViewShape, n, box, gap);
  const b = rectsFor(vs[Math.min(m - 1, idx + 1)].shape as ViewShape, n, box, gap);
  const activeF = pinned === null ? idx + frac : pinned;
  // every row shares this: `frac` holds at 0, travels, holds at 1 — true exactly while a row's LAYOUT
  // position (left/top, lerped between the old and new arrangement's rects) is still changing.
  const walking = frac !== 0 && frac !== 1;

  // the tab strip
  const tabW = Math.floor((W - pad * 2) / m);
  const tabX = (i: number) => pad + i * tabW;

  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', top, left: pad, right: pad, color: GROUND_DIM,
        opacity: clamp01(seg(t, 0.01, 0.12)), letterSpacing: dna?.labelSpacing ?? '0.16em',
        font: `600 ${kickPx}px/${leading(kicker, 1.2)} ${mono}`}}>{kicker}</div>

      {/* the strip: a rule across the frame, and ONE block riding it */}
      <div style={{position: 'absolute', left: pad, right: pad, top: top + kickH + tabH - Math.max(1, BW),
        height: Math.max(1, BW), background: LINE, opacity: clamp01(enter)}} />
      <div style={{position: 'absolute', left: tabX(0) + (tabW * activeF), top: top + kickH,
        width: tabW, height: tabH, background: TAB_BLOCK, borderRadius: `${RAD}px ${RAD}px 0 0`,
        opacity: clamp01(enter)}} />
      {vs.map((v, i) => {
        const label = String(v.label ?? '');
        const on = clamp01(1 - Math.abs(activeF - i));
        const px = fitTextPx(label, tabW - Math.round(U * 0.03), tabPx, {usable: 0.96});
        return (
          <div key={i} style={{position: 'absolute', left: tabX(i), top: top + kickH, width: tabW, height: tabH,
            display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: clamp01(enter),
            color: on > 0.55 ? TAB_INK : GROUND_DIM, whiteSpace: 'nowrap',
            letterSpacing: dna?.labelSpacing ?? '0.06em',
            font: `${on > 0.55 ? 700 : 500} ${px}px/${leading(label, 1.2)} ${mono}`}}>{label}</div>
        );
      })}

      {/* the rows — ONE element each, travelling between arrangements */}
      {rs.map((r, i) => {
        const ra = a[i], rb = b[i];
        // THE ROW TRAVELS BY TRANSLATE. By its layout left/top it was rounded to whole pixels before anything was
        // drawn, and stepped whatever unlocked it.
        const x = lerp(ra.x, rb.x, frac), y = lerp(ra.y, rb.y, frac);
        const w = lerp(ra.w, rb.w, frac), h = lerp(ra.h, rb.h, frac);
        const label = String(r.label ?? '');
        const rnote = String(r.note ?? '');
        const rise = easeOutCubic(clamp01(seg(t, 0.06 + i * 0.045, 0.24 + i * 0.045)));
        const moving = rise !== 1 || walking;
        // THE ROW'S INSIDE IS PLACED BY TRANSLATE TOO: centred by flex on a height that is being lerped, its
        // ordinal and label were laid out at a fractional offset — rounded, and crawling in whole-pixel stairs as
        // the row resized. In a row the content's line runs through the row's middle and each piece is centred
        // on it by its own -50% (the label's height changes as it is refitted, so flex centring the ordinal
        // against it stepped the ordinal too); in a column it stands at the inset. The inset is unrounded while
        // the row walks, pinned to the rounded inset at both arrangements.
        const insetAt = (ww: number, hh: number) => Math.max(U * 0.012, Math.min(ww * 0.07, hh * 0.16, U * 0.028));
        const innerPad = walking
          ? insetAt(w, h) + (1 - frac) * (Math.round(insetAt(ra.w, ra.h)) - insetAt(ra.w, ra.h))
            + frac * (Math.round(insetAt(rb.w, rb.h)) - insetAt(rb.w, rb.h))
          : Math.round(insetAt(w, h));
        const markPx = Math.max(11, Math.round(Math.min(U * 0.019, h * 0.20)));
        const wide = w > h * 1.6;                       // a row reads across; a column reads down
        const labelBox = w - innerPad * 2 - (wide ? Math.round(U * 0.05) : 0);
        const labelH = Math.max(markPx, h - innerPad * 2 - markPx - Math.round(U * 0.008));
        const lPx = fitBlockPx(label, labelBox, wide ? Math.min(labelH, U * 0.05) : labelH * 0.55,
          Math.round(U * 0.032), {usable: 0.96, leading: 1.25, min: 13});
        const nPx = Math.max(11, Math.round(lPx * 0.62));
        return (
          // at rest the row stands at its layout place again, so its edges are snapped as they always were
          <div key={i} style={{position: 'absolute', left: moving ? 0 : x, top: moving ? 0 : y, width: w, height: h,
            boxSizing: 'border-box',
            background: SURF, border: `${BW}px solid ${LINE}`, borderRadius: RAD, overflow: 'hidden',
            opacity: clamp01(rise * 1.2),
            transform: moving ? glide(`translate(${x}px, ${y + lerp(U * 0.02, 0, rise)}px)`, true) : 'translateY(0px)'}}>
            <div style={{position: 'absolute', left: 0, top: 0, width: w - 2 * innerPad - 2 * BW, display: 'flex',
              flexDirection: wide ? 'row' : 'column', alignItems: 'flex-start',
              gap: Math.round(innerPad * 0.7),
              transform: `translate(${innerPad}px, ${wide ? h / 2 - BW : innerPad}px)`}}>
            {/* the ordinal is the row's IDENTITY — it is the same mark in every arrangement, which is the
                only reason a viewer can tell that the rows did not change when the shape did */}
            <div style={{flex: 'none', color: DIM, letterSpacing: '0.08em', transform: wide ? 'translateY(-50%)' : undefined,
              font: `600 ${markPx}px/1.2 ${mono}`}}>{String(i + 1).padStart(2, '0')}</div>
            <div style={{flex: 1, minWidth: 0, transform: wide ? 'translateY(-50%)' : undefined}}>
              <div style={{color: INK, textWrap: 'balance',
                font: `700 ${lPx}px/${leading(label, 1.22)} ${disp}`}}>{label}</div>
              {rnote && h > markPx + lPx * 2.2 ? (
                <div style={{color: DIM, marginTop: Math.round(U * 0.006), textWrap: 'balance',
                  font: `500 ${nPx}px/${leading(rnote, 1.35)} ${bodyFace}`}}>{rnote}</div>
              ) : null}
            </div>
            </div>
          </div>
        );
      })}

      {/* the substrate: named ONCE, under every arrangement, and never redrawn */}
      {body ? (
        <div style={{position: 'absolute', left: pad, right: pad, top: boxY + boxH + Math.round(U * 0.010),
          opacity: clamp01(seg(t, 0.28, 0.44)), display: 'flex', alignItems: 'center',
          gap: Math.round(U * 0.016)}}>
          <div style={{flex: 'none', width: Math.round(U * 0.06), height: Math.max(2, BW * 2),
            background: TAB_BLOCK}} />
          <div style={{color: readableOn(GROUND, ACC, FG, '#0a0d14', '#ffffff'), whiteSpace: 'nowrap',
            letterSpacing: dna?.labelSpacing ?? '0.08em',
            font: `700 ${fitTextPx(body, (W - pad * 2) * 0.7, bodyPx, {usable: 0.98})}px/${leading(body, 1.25)} ${mono}`}}>{body}</div>
          <div style={{flex: 1, height: Math.max(1, BW), background: LINE}} />
        </div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left: pad, right: pad, top: bottom - noteH + Math.round(U * 0.004),
          color: GROUND_DIM, opacity: clamp01(seg(t, 0.72, 0.86)),
          font: `500 ${notePx}px/${leading(note, 1.4)} ${bodyFace}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ViewSwitch;
