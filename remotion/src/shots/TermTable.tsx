// SHOT · TermTable — a TERMINAL-NATIVE table (a `cat *.tsv` / config readout). A command executes and a mono
// table PRINTS row by row, one row optionally HERO-lit. Default OPEN (prompt + output on the canvas, no window
// box); `framed` = an explicit terminal window. Deterministic (every reveal is a function of useT()).
//
// The table SIZES ITSELF TO ITS CONTENT and then owns the frame's content zone. Before, the rows were laid out
// by the browser inside a fixed `min(84vw, 1320px)` LEFT-aligned column, so a short Chinese table parked in
// x≈300..980 of a 1920 frame — under half the width, the right half of every such beat empty, and three beats
// using this register all read as one recycled slot. Now:
//   • every cell is MEASURED (measureText) with a CJK-AWARE analytic floor — a CJK glyph is ~2x a Latin advance
//     in a mono face, so a Latin-width assumption under-measures Chinese copy by half;
//   • column widths follow that measured content;
//   • the type scales UP until the table fills the content zone (capped by the action-safe border, the caption
//     band and a max size), and a table that is still narrow widens its columns proportionally to fill.
// Everything is a fraction of W/H, so it reflows at 9:16 / 1:1 / 4:5 as well as 16:9.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
// A terminal row does NOT wrap — every cell is one line by register — so the width-fitting primitives
// here are measureText (per cell, to derive the column widths + the type size) and fitText (the one
// prompt line), not fitTextOnNLines, which fits a multi-line box.
import {fitText, measureText} from '@remotion/layout-utils';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 160;

// null-DNA fallbacks (the shot's original palette). Never put a literal INTO an expression that also uses a DNA
// token — take the token, fall back to the D0 constant, so a themed film never gets an off-system colour.
const BORDER_D0 = '#26324c', FG_D0 = '#cdd7e4', DIM_D0 = '#5f6b80', ACC_D0 = '#3dd6a4', ACC2_D0 = '#c9a227';
const BG_D0 = 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)';
const GROUND_D0 = '#06080d', SURFACE_D0 = '#0f1723';
// (the mono FALLBACK is read inline as `dna?.fontMono ?? '...'` below — a shot must never bind a font
//  stack to a const, that is how a film's typeface stops reaching the shot)

// ── metrics ───────────────────────────────────────────────────────────────────────────────────────────────
const MEASURE_AT = 100;        // measure at 100px, divide → em units (widths scale linearly with font-size)
const CELL_PAD_EM = 0.62;      // horizontal padding per side, inside a cell
const HEAD_ROW_EM = 1.85;      // header row height, in body-em
const ROW_EM = 2.0;            // body row height, in body-em
const HEAD_SCALE = 0.62;       // header font = HEAD_SCALE * body font
const STRETCH_MAX = 1.75;      // a narrow table widens its columns at most this much before it stops growing
const ROW_BREATHE_MAX = 1.35;  // ...and grows its row height at most this much to use the vertical zone
const HEAD_BREATHE = 0.35;     // the header row breathes LESS than the body rows (its type is smaller)
const VALUE_COL_EM = 4.2;      // a non-first column this narrow is a VALUE column → set flush to its right edge

// FULL-WIDTH / CJK ranges — kana, hangul, han, CJK punctuation (、。「」), full-width forms. A char in these
// ranges occupies ~1em in a mono face against ~0.6em for Latin: roughly TWICE the advance. Sizing Chinese copy
// with Latin widths is exactly how a table ends up half the width it needs.
const WIDE = /[\u1100-\u115F\u2E80-\u303E\u3041-\u33FF\u3400-\u4DBF\u4E00-\u9FFF\uA000-\uA4CF\uA960-\uA97F\uAC00-\uD7A3\uF900-\uFAFF\uFE10-\uFE19\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/;
const advEm = (s: string) => [...s].reduce((a, ch) => a + (WIDE.test(ch) ? 1.02 : 0.6), 0);

/** Width of `text` in em of its own font-size. measureText is exact when the real face is available; the
 *  CJK-aware analytic estimate is the FLOOR, so a measurement taken against a fallback face (or a measurement
 *  that throws in a non-DOM context) can only ever make a column wider — never let text overflow its cell. */
const emOf = (text: string, fontFamily: string, fontWeight: number, lsEm: number): number => {
  const s = String(text ?? '');
  if (!s) return 0;
  const analytic = advEm(s) + lsEm * [...s].length;
  let measured = 0;
  try {
    measured = measureText({
      text: s, fontFamily, fontSize: MEASURE_AT, fontWeight,
      letterSpacing: lsEm ? `${lsEm}em` : null,
    }).width / MEASURE_AT;
  } catch {
    measured = 0;                        // fall back to the conservative analytic width
  }
  return Math.max(analytic, measured);
};

/** '0.1em' → 0.1 (only em spacing can be folded into an em-unit measurement; anything else counts as 0). */
const parseEmSpacing = (v: string): number => {
  const m = /^\s*(-?[\d.]+)em\s*$/.exec(String(v ?? ''));
  return m ? parseFloat(m[1]) || 0 : 0;
};

const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));

export const TermTable: React.FC<{cmd?: string; headers?: string[]; rows?: string[][]; hero?: number;
  framed?: boolean; heroNote?: string}> = ({
  cmd = 'cat table.tsv', headers = ['col', 'value'], rows = [['a', '1'], ['b', '2']], hero = -1, framed = false,
  heroNote = 'note'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const BORDER = dna?.surfaceBorder ?? BORDER_D0;
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  const SURFACE = dna?.surface ?? SURFACE_D0;
  const DEEP = dna?.bg ?? GROUND_D0;                 // the film's deepest ground
  const GROUND = framed ? SURFACE : DEEP;            // what the table sits ON (for the hero tint)
  const labelLs = dna?.labelSpacing ?? '0.06em';
  const upper: React.CSSProperties['textTransform'] =
    dna ? (dna.uppercaseLabels ? 'uppercase' : 'none') : 'uppercase';

  // ── the data, normalised. A ragged row (fewer cells than headers) used to produce a ragged grid; pad it. ──
  const head = React.useMemo(() => (headers ?? []).map((h) => String(h ?? '')), [headers]);
  const src = React.useMemo(() => (rows ?? []).map((r) => (r ?? []).map((c) => String(c ?? ''))), [rows]);
  const nCol = Math.max(1, head.length, ...src.map((r) => r.length));
  const body = React.useMemo(
    () => src.map((r) => Array.from({length: nCol}, (_, i) => r[i] ?? '')), [src, nCol]);
  const cols = React.useMemo(
    () => Array.from({length: nCol}, (_, i) => head[i] ?? ''), [head, nCol]);
  const nRow = body.length;
  const heroI = Number.isFinite(hero) ? Math.trunc(hero as number) : -1;
  const note = heroI >= 0 && heroI < nRow && heroNote ? `  ◂ ${heroNote}` : '';

  // ── the content zone (never the whole frame): below the title band, above the burned-caption band ─────────
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const zoneH = Math.max(80, zoneBot - zoneTop);
  const portrait = W < H;
  // The window spans at most maxWinW (clear of the action-safe border) and WANTS at least minWinW, so the table
  // is the frame's subject rather than a small panel adrift in it. Fractions of W → reflows at any aspect.
  const maxWinW = W * (portrait ? 0.9 : 0.86);
  const minWinW = Math.min(maxWinW, W * (portrait ? 0.9 : 0.66));
  const boxPadX = framed ? Math.round(W * 0.021) : 0;
  const boxPadY = framed ? Math.round(zoneH * 0.05) : 0;
  const innerMaxW = maxWinW - 2 * boxPadX;

  // header of the shot: the chrome bar (framed) or the prompt line + a gap (open)
  const cmdFsCap = Math.max(14, Math.round(W * 0.019));
  const chromeH = Math.round(cmdFsCap * 1.9);
  const cmdGap = Math.round(zoneH * 0.05);
  const headH = framed ? chromeH : Math.round(cmdFsCap * 1.3) + cmdGap;
  const availH = Math.max(60, zoneH - 2 * boxPadY - headH - 6);

  // ── COLUMN WIDTHS FROM THE ACTUAL CONTENT (em units, CJK-aware) ───────────────────────────────────────────
  const {colEm, bodyEm, emTotal} = React.useMemo(() => {
    const ls = parseEmSpacing(labelLs);
    const bodyPer = Array.from({length: nCol}, (_, i) => {
      const cells = body.map((r, ri) => r[i] + (ri === heroI && i === nCol - 1 ? note : ''));
      return cells.reduce((mx, c) => Math.max(mx, emOf(c, mono, i === 0 ? 700 : 500, 0)), 0);
    });
    const per = bodyPer.map((b, i) => Math.max(b, emOf(cols[i], mono, 600, ls) * HEAD_SCALE, 1.2));
    return {colEm: per, bodyEm: bodyPer,           // floor: an empty column is still a column
      emTotal: per.reduce((a, b) => a + b, 0) + CELL_PAD_EM * 2 * nCol};
  }, [body, cols, nCol, mono, labelLs, heroI, note]);

  // A non-first column of SHORT cells is a value/verdict column: set those flush RIGHT so a table that had to
  // be widened to fill the frame still carries ink at both edges instead of a left cluster and a field of air.
  // Prose (C's 「它是对的」的证据) stays flush left, where it reads as a sentence — and the decision is taken for
  // the table as a WHOLE, so one prose column (or a hero note) can never leave sibling values misaligned.
  const valueCols = nCol >= 2 && bodyEm.every((e, i) => i === 0 || (e > 0 && e <= VALUE_COL_EM));
  const alignEnd = bodyEm.map((_, i) => valueCols && i > 0);

  // ── SOLVE THE TYPE SIZE: as large as the width, the height and a sane cap allow ────────────────────────────
  const fsFromW = innerMaxW / emTotal;
  const fsFromH = availH / (HEAD_ROW_EM + nRow * ROW_EM);
  const fsCap = Math.min(zoneH * 0.108, W * 0.045);
  const fs = Math.max(8, Math.min(fsFromW, fsFromH, fsCap));

  // The natural (content) table width. When it is narrower than the frame deserves, widen the COLUMNS in
  // proportion to their content instead of leaving half the frame empty — capped so a tiny two-column table
  // does not become a field of air.
  const natW = Math.max(1, fs * emTotal);
  const innerW = Math.min(innerMaxW, Math.max(natW, Math.min(minWinW - 2 * boxPadX, natW * STRETCH_MAX)));
  const stretch = innerW / natW;
  const colW = colEm.map((e) => (e + CELL_PAD_EM * 2) * fs * stretch);
  colW[nCol - 1] += innerW - colW.reduce((a, b) => a + b, 0);   // absorb rounding: columns fill the box exactly

  // Rows breathe into the leftover vertical zone (a 2-row table in a tall zone should not sit as a thin strip).
  const natH = (HEAD_ROW_EM + nRow * ROW_EM) * fs;
  // a PORTRAIT frame's content zone is far taller than a table needs, so let the rows breathe further
  // there rather than leaving a thin slab floating in a tall column.
  const rowScale = clamp(availH / Math.max(1, natH), 1, portrait ? ROW_BREATHE_MAX + 0.35 : ROW_BREATHE_MAX);
  const headRowH = HEAD_ROW_EM * fs * (1 + (rowScale - 1) * HEAD_BREATHE), rowH = ROW_EM * fs * rowScale;
  const tableH = headRowH + nRow * rowH;

  const winW = innerW + 2 * boxPadX;
  const blockH = headH + 2 * boxPadY + tableH;
  const left = Math.round((W - winW) / 2);
  const top = Math.round(Math.max(zoneTop, zoneTop + (zoneH - blockH) / 2));

  // ── timing: the command types, the header prints, then the rows print one after another ───────────────────
  const chars = [...String(cmd)];
  const typed = Math.round(chars.length * clamp01(seg(t, 0.04, 0.17)));
  const shown = chars.slice(0, typed).join('');
  const ran = typed >= chars.length;
  const caretOn = Math.floor(t * 24) % 2 === 0;                  // blink driven by t → frozen under reduced motion
  const headIn = clamp01(seg(t, 0.2, 0.29));
  const R0 = 0.28, R1 = 0.8;                                     // ALL rows landed by 0.8 < REDUCED_MOTION_T
  const step = (R1 - R0) / Math.max(1, nRow);

  // The prompt line, fitted so a long command can never run past the window (and never past the frame).
  const cmdFs = Math.min(cmdFsCap, Math.round(fitText({
    text: `$ ${cmd}`, fontFamily: mono, fontWeight: 600,
    withinWidth: Math.max(40, innerW - fs * 0.9 - (framed ? cmdFsCap * 3.2 : 0)),
  }).fontSize));
  const caretW = Math.round(cmdFs * 0.5), caretH = Math.round(cmdFs * 0.92);
  const heroTint = /^#[0-9a-fA-F]{6}$/.test(ACC) ? `${ACC}1f` : mix(GROUND, ACC, 0.12);

  const prompt = (
    <div style={{color: DIM, font: `600 ${cmdFs}px/1.3 ${mono}`, letterSpacing: labelLs, whiteSpace: 'nowrap',
      opacity: clamp01(t / 0.05)}}>
      <span style={{color: ACC}}>$</span> {shown}
      <span style={{display: 'inline-block', width: caretW, height: caretH, marginLeft: 6,
        verticalAlign: 'text-bottom', background: ACC, opacity: ran ? (caretOn ? 0.5 : 0.12) : 0.9}} />
    </div>
  );

  const cellBase: React.CSSProperties = {
    display: 'flex', alignItems: 'center', padding: `0 ${CELL_PAD_EM * fs}px`, whiteSpace: 'nowrap',
    overflow: 'hidden', boxSizing: 'border-box',
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0}}>
      <div style={{position: 'absolute', left, top, width: winW,
        background: framed ? SURFACE : 'transparent',
        border: framed ? `1px solid ${BORDER}` : 'none', borderRadius: framed ? (dna?.radius ?? 8) : 0,
        boxShadow: framed ? '0 30px 90px #0009' : 'none', overflow: 'hidden'}}>

        {framed ? (
          // WINDOW chrome: three lights + the command in the title bar.
          <div style={{height: chromeH, display: 'flex', alignItems: 'center', gap: cmdFs * 0.42,
            padding: `0 ${boxPadX}px`, borderBottom: `1px solid ${BORDER}`, background: mix(SURFACE, DEEP, 0.55)}}>
            {[ACC2, DIM, ACC].map((c, i) => (
              <div key={i} style={{width: cmdFs * 0.36, height: cmdFs * 0.36, borderRadius: '50%',
                background: c, opacity: 0.8, flex: '0 0 auto'}} />
            ))}
            <div style={{marginLeft: cmdFs * 0.3, minWidth: 0}}>{prompt}</div>
          </div>
        ) : null}

        <div style={{padding: framed ? `${boxPadY}px ${boxPadX}px` : 0}}>
          {framed ? null : <div style={{marginBottom: cmdGap}}>{prompt}</div>}

          {/* the printed table — a real grid, sized to its content */}
          <div style={{width: innerW, border: `1px solid ${BORDER}`, boxSizing: 'border-box',
            opacity: clamp01(headIn * 1.2), fontFamily: mono}}>
            {/* header */}
            <div style={{display: 'flex', height: headRowH, boxSizing: 'border-box',
              borderBottom: `2px solid ${mix(BORDER, ACC, 0.28)}`, opacity: headIn}}>
              {cols.map((h, i) => (
                <div key={i} style={{...cellBase, width: colW[i], color: DIM,
                  justifyContent: alignEnd[i] ? 'flex-end' : 'flex-start',
                  borderLeft: i ? `1px solid ${BORDER}` : 'none',
                  font: `600 ${HEAD_SCALE * fs}px/1.2 ${mono}`, letterSpacing: labelLs, textTransform: upper}}>{h}</div>
              ))}
            </div>
            {/* rows PRINT: each wipes in left→right, the way a line lands in a terminal */}
            {body.map((r, ri) => {
              const p = clamp01(seg(t, R0 + ri * step, R0 + ri * step + step * 0.85));
              const isHero = ri === heroI;
              return (
                <div key={ri} style={{display: 'flex', height: rowH, boxSizing: 'border-box',
                  borderTop: ri ? `1px solid ${BORDER}` : 'none',
                  background: isHero ? heroTint : 'transparent',
                  boxShadow: isHero ? `inset ${Math.round(fs * 0.07)}px 0 0 ${ACC}` : 'none',
                  // the row PRINTS: a left→right wipe, not a fade — a terminal line lands, it does not dissolve
                  opacity: clamp01(p * 3), clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`}}>
                  {r.map((c, ci) => (
                    <div key={ci} style={{...cellBase, width: colW[ci],
                      justifyContent: alignEnd[ci] ? 'flex-end' : 'flex-start',
                      borderLeft: ci ? `1px solid ${BORDER}` : 'none',
                      color: ci === 0 && isHero ? ACC : FG,
                      font: `${ci === 0 ? 700 : 500} ${fs}px/1.25 ${mono}`}}>
                      {c}
                      {isHero && ci === nCol - 1 && note ? (
                        <span style={{color: ACC, marginLeft: fs * 0.4, fontSize: HEAD_SCALE * fs,
                          whiteSpace: 'nowrap'}}>◂ {heroNote}</span>
                      ) : null}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
export default TermTable;
