// SHOT · TermBars — a TERMINAL-NATIVE metric readout. Default OPEN (no window box): a `$ cmd` executes and the
// figures grow out as a measured run on the open canvas (command→result motion). `framed` renders it inside an
// explicit terminal window (an anchor beat). Deterministic (fill = fn of t). The bar's FORM is the DNA's call
// (block run / ruled scale / pixel cells / solid track); this shot owns the CLOCK, the COLUMNS and the SCALE.
//
// TWO DEFECTS THIS SHOT SHIPPED IN A DELIVERED FILM — the rules below are the fix, do not "tidy" either away:
//
//  1. THE CLOCK. The bars used to grow over [0.24 … 0.84] with a 0.20 stagger per row, so for the whole first
//     half of the beat they showed the WRONG quantities — and because a later row started later, a LONGER bar
//     could still be drawn SHORTER than a shorter one mid-flight: rows 0.20 / 0.40 read "19%" / "17%" at the
//     exact frame the narration claimed 20% vs 40%, i.e. the RANKING INVERTED while the claim was being made.
//     Now every bar is `target × g` with ONE shared g, so the ratio between any two bars is exact at every
//     frame (a ranking can never invert, for any row count or any values), and g is SETTLED at FILL_B ≈ 0.21 of
//     the beat — the shot then holds the true figures for ~80% of its length, including any gate/keyframe grab.
//
//  2. THE TRACK. The bar ran at the Bar atom's default 420px inside a 1920 frame, so 20% vs 40% differed by
//     ~85px — barely visible, and the comparison is the whole reason the beat exists. The track is now SIZED
//     FROM THE FRAME (the TermFrame column minus the label / value / tag columns), so a 2× difference is a 2×
//     length, and a whisper-quiet 25/50/75 guide + a % axis give the eye a common scale to measure against.
//
// AND A THIRD, FROM THE CONTENT CONTRACT — every bar and every figure is one the film supplied:
//
//  3. THE QUANTITY. A row with no `fill` and no `pct` fell through to 0 and drew an EMPTY bar labelled "0%" — a
//     measurement nobody made; a row carrying only a `value` ("1.2M") got the same empty bar beside its figure.
//     `pct` also GUESSED its unit: ≤ 1 was read as a fraction, so `pct: 0.8` (0.8%) drew an 80% bar. And the
//     printed figure was `Math.round(100 × fill)`, so a sourced 99.6% settled as "100%". Now `fill` is a 0-1
//     fraction and `pct` a 0-100 percentage, always, each range-checked; the printed figure is the film's own
//     (`value` as written, else `pct` as written + "%", else `fill` converted exactly, never rounded), counted
//     up through runtime/figure.ts; a row with only a `value` prints it with NO bar and no track; a row with
//     nothing to draw or print THROWS, as do an unlabelled row and more than MAX_TERMBARS_ROWS rows.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {fitTextOnNLines, measureText} from '@remotion/layout-utils';
import {useT, seg, clamp01, easeOutExpo} from '../runtime/motion';
import {useDNA, TermFrame, type DesignDNA} from '../runtime/dna';
import {Bar} from '../runtime/atoms';
import {CONTENT_TOP, contentBottom, titleStyle, textWidthPx, monoFit} from '../runtime/layout';
import {parseFigure, figureAt, figureText, figureValue} from '../runtime/figure';

export const DURATION = 165;

// no-DNA fallbacks (the un-themed render) — every colour below is `dna?.token ?? *_D0`, never a literal
// mixed into a themed expression.
const BG_D0 = 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)';
const FG_D0 = '#cdd7e4', DIM_D0 = '#5f6b80', ACC_D0 = '#3dd6a4', ACC2_D0 = '#f2b544';
const RUN_AT = 0.11;                    // the command finishes typing and EXECUTES here
const FILL_A = 0.12, FILL_B = 0.205;    // …and every bar grows in this window, settled for the rest of the beat

type Row = {label?: string; fill?: number; pct?: number; value?: string; tag?: string; tone?: string};

const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));

export const MAX_TERMBARS_ROWS = 10;   // at the 16px bar floor, ten rows (+ a note) still fit a 1:1 content zone

/** `fill` 0.845 → "84.5%": the exact percentage the fraction states, with only the digits it carries. */
const pctOfFraction = (f: number): string => {
  const s = String(f);
  if (/e/i.test(s)) return `${parseFloat((f * 100).toFixed(10))}%`;
  const d = Math.max(0, (s.split('.')[1] ?? '').length - 2);
  return `${(f * 100).toFixed(d)}%`;
};

/** One row, checked: its drawable fraction (null = no bar) and the figure it prints (the film's own).
 *  `fill` is a 0-1 fraction and `pct` a 0-100 percentage — always; LIBRARY.md advertises `pct`, so an author
 *  following the manifest writes `pct: 40`, and the old "≤ 1 means a fraction" guess drew `pct: 0.8` as 80%. */
const readRow = (r: Row, i: number): {label: string; frac: number | null; figure: string} => {
  if (!r || typeof r !== 'object') throw new Error(`TermBars: row ${i + 1} is ${JSON.stringify(r)}, not a row object.`);
  const label = String(r.label ?? '').trim();
  if (!label) throw new Error(`TermBars: row ${i + 1} has no \`label\`.`);
  const num = (v: unknown) => (typeof v === 'number' ? v : figureValue(v));
  let frac: number | null = null;
  let pctText = '';
  if (r.fill != null) {
    const f = num(r.fill);
    if (f == null || !Number.isFinite(f) || f < 0 || f > 1) {
      throw new Error(`TermBars: row ${i + 1} ("${label}") has \`fill\` ${JSON.stringify(r.fill)}; fill is a fraction 0-1 ` +
        '(use `pct` for a 0-100 percentage).');
    }
    frac = f;
    pctText = pctOfFraction(f);
  } else if (r.pct != null) {
    const p = num(r.pct);
    if (p == null || !Number.isFinite(p) || p < 0 || p > 100) {
      throw new Error(`TermBars: row ${i + 1} ("${label}") has \`pct\` ${JSON.stringify(r.pct)}; pct is a percentage 0-100 ` +
        '(use `fill` for a 0-1 fraction).');
    }
    frac = p / 100;
    const t = figureText(r.pct);
    pctText = /%$/.test(t) ? t : `${t}%`;
  }
  const value = r.value == null ? '' : figureText(r.value);
  if (frac == null && !value) {
    throw new Error(`TermBars: row ${i + 1} ("${label}") has nothing to draw — pass \`fill\` (0-1) or \`pct\` (0-100) ` +
      'for a bar, and/or `value` for the figure beside it. An empty bar reading "0%" would be a measurement nobody made.');
  }
  return {label, frac, figure: value || pctText};
};

/** A row's semantic colour, resolved to a DNA token — never a literal. `warn`/`accent2` marks a row the film's
 *  grammar treats as a warning (unverified / still wrong); `dim` de-emphasises; anything else is the primary
 *  accent, which stays the default so every existing film renders exactly as before. */
const toneOf = (dna: DesignDNA | null, name?: string): string => {
  const key = String(name ?? '').toLowerCase();
  if (key === 'accent2' || key === 'warn' || key === 'alert') return dna?.accent2 ?? ACC2_D0;
  if (key === 'dim' || key === 'muted') return dna?.dim ?? DIM_D0;
  return dna?.accent ?? ACC_D0;
};

export const TermBars: React.FC<{cmd?: string; title?: string; rows?: Row[]; note?: string; cells?: number;
  framed?: boolean}> = ({
  cmd = 'eval --suite bench', cells, note = '', framed = false, title = '',
  rows = [{label: 'metric_a', fill: 0.9, tag: 'PASS'}, {label: 'metric_b', fill: 0.84, tag: 'PASS'}]} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const disp = dna?.fontDisplay ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? FG_D0, dim = dna?.dim ?? DIM_D0;
  if (!Array.isArray(rows) || rows.length < 1 || rows.length > MAX_TERMBARS_ROWS) {
    throw new Error(`TermBars needs 1-${MAX_TERMBARS_ROWS} \`rows\` (got ${Array.isArray(rows) ? rows.length : typeof rows}). ` +
      'Past ten the bars fall below a legible height; split the readout across beats or use TermTable. Rows are ' +
      'never dropped to fit.');
  }
  const list = rows;
  const checked = list.map(readRow);
  const n = Math.max(1, list.length);

  // ── ONE shared growth clock. `target × g` for every row ⇒ the bars are always in exact proportion. ──
  const gRaw = easeOutExpo(seg(t, FILL_A, FILL_B));
  const g = gRaw > 0.99 ? 1 : gRaw;      // snap, so a 0.40 bar never prints "39%" on its settled frames
  const done = g >= 1;
  // the rows still PRINT with a terminal stagger — but capped so the last row is up well before g settles,
  // and the stagger is opacity only, never the quantity (that is what used to invert the ranking).
  const stag = Math.min(0.012, Math.max(0, (FILL_B - FILL_A - 0.04) / Math.max(1, n - 1)));

  // ── COLUMNS, sized from the FRAME (not a hardcoded track width) ──────────────────────────────────────
  const zoneTop = CONTENT_TOP, zoneH = Math.max(180, contentBottom(W, H) - zoneTop);
  // TermFrame's own content column: open = min(84vw, 1320px); framed = min(80vw, 1180px) minus its 34px padding.
  const RW = framed ? Math.max(240, Math.min(0.8 * W, 1180) - 68) : Math.min(0.84 * W, 1320);
  const head = framed ? 0 : 110;                       // the `$ cmd` line + its margin (framed puts it in the bar)
  // a % axis is only honest when the bars ARE percentages — a row carrying its own `value` ("1.2M") is a
  // proportion of something else, so the scale keeps its guides but drops the misleading 0-100 labels.
  const isPct = list.length > 0 && list.every((r) => r.value == null);   // (every such row has a fill or pct: readRow)
  const avail = Math.max(140, zoneH - head - (note ? 84 : 0) - (isPct ? 46 : 0));
  const barSize = clamp(avail / (2.15 * n), 16, 52);   // shrinks for a long list, so N rows always fit the zone
  const trackH = Math.round(barSize * 1.3);            // the row's track box — tall enough for the `block` glyphs
  const massH = Math.round(barSize * 0.56);            // …and the weight the quantity is drawn at
  // the rhythm breathes into whatever the zone has left over (a 2-row readout would otherwise sit as a small
  // strip in a tall frame) but stays TIGHT enough that two bars can still be compared at a glance, and a long
  // list keeps the compact rhythm that makes it fit at all.
  const rowGap = clamp(((avail - n * trackH) / n) * 0.35, barSize * 0.5, barSize * 0.9);
  const gap = clamp(RW * 0.018, 12, 26);
  const labelW = clamp(RW * 0.15, 96, 300);
  // the figure column is sized for the widest figure the film gave (a value like "3–5 千" is wider than "90%"),
  // so a long figure widens its column instead of shrinking every row's figure to fit
  const figUnits = Math.max(2.4, ...checked.map((c) => textWidthPx(c.figure, 1, monoFit())));
  const pctW = clamp(Math.max(RW * 0.085, figUnits * barSize * 0.78), 60, Math.max(140, RW * 0.25));
  const hasTag = list.some((r) => Boolean(r.tag));
  const tagW = hasTag ? clamp(RW * 0.13, 84, 210) : 0;
  const TW = Math.max(120, RW - labelW - pctW - tagW - gap * (hasTag ? 3 : 2));

  // ── TYPE fitted to the real copy (Chinese labels are far wider than the demo's `metric_a`) ───────────
  const labels = list.map((r) => String(r.label ?? '')).filter(Boolean);
  const tags = list.map((r) => String(r.tag ?? '')).filter(Boolean);
  const labelSize = React.useMemo(() => {
    const s = labels.map((txt) => fitTextOnNLines({text: txt, maxLines: 1, maxBoxWidth: labelW,
      fontFamily: mono, fontWeight: 600, maxFontSize: barSize}).fontSize);
    return s.length ? Math.min(...s) : barSize;
  }, [labels.join('\u0000'), labelW, mono, barSize]);
  const tagSize = React.useMemo(() => {
    const cap = Math.max(11, barSize * 0.52);
    const s = tags.map((txt) => fitTextOnNLines({text: txt, maxLines: 1, maxBoxWidth: Math.max(24, tagW - 26),
      fontFamily: mono, fontWeight: 700, maxFontSize: cap}).fontSize);
    return s.length ? Math.min(...s) : cap;
  }, [tags.join('\u0000'), tagW, mono, barSize]);
  // 4 mono glyphs ("100%") always fit the value column — and so does the film's widest figure ("84.5%", "1.2M")
  const pctSize = Math.min(barSize * 0.78, pctW / figUnits);
  const titleSize = React.useMemo(() => (title ? fitTextOnNLines({text: String(title), maxLines: 1,
    maxBoxWidth: W * 0.84, fontFamily: disp, fontWeight: 700,
    // a narrow frame must not scale the title off the same ratio as a 1920 one, or it arrives tiny
    maxFontSize: clamp(W * (W < H ? 0.042 : 0.028), 26, 46)}).fontSize : 0), [title, W, H, disp]);
  // the `block` form is TEXT, so its width is a glyph count — measure the real advance and fit it to the track
  // (an explicit `cells` from a caller still wins). Never let it overrun: the wrapper clips.
  const autoCells = React.useMemo(() => {
    const probe = measureText({text: '█'.repeat(20), fontFamily: mono, fontSize: barSize,
      fontWeight: 500, letterSpacing: '-2px'}).width;
    const adv = probe > 0 ? probe / 20 : barSize * 0.6;
    return clamp(Math.floor(TW / Math.max(1, adv)), 8, 80);
  }, [mono, barSize, TW]);
  const cellCount = Number.isFinite(cells) && (cells as number) > 0 ? Math.round(cells as number) : autoCells;

  const trackLeft = labelW + gap;
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0}}>
      {title ? (
        <div style={{...titleStyle, color: fg, font: `700 ${titleSize}px/1.15 ${disp}`,
          letterSpacing: '-0.01em', padding: '0 8%', opacity: clamp01(t * 7)}}>{title}</div>
      ) : null}

      <div style={{position: 'absolute', left: 0, right: 0, top: zoneTop, height: zoneH,
        display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left" runAt={RUN_AT}>
          <div style={{width: RW}}>
            <div style={{position: 'relative', width: RW}}>
              {/* the common scale the bars are measured against — a whisper, never louder than the data */}
              {ticks.slice(1).map((f) => (
                <div key={f} style={{position: 'absolute', top: -Math.round(barSize * 0.2), bottom: 0,
                  left: trackLeft + f * TW, width: 1, background: dim,
                  opacity: (f === 1 ? 0.32 : 0.17) * clamp01(seg(t, FILL_A, FILL_A + 0.06))}} />
              ))}

              {list.map((r, i) => {
                const {label: rowLabel, frac, figure} = checked[i];
                const target = frac ?? 0;
                const tone = toneOf(dna, r.tone);
                const a = FILL_A - 0.015 + i * stag;
                const rowIn = clamp01(seg(t, a, a + 0.04));
                return (
                  <div key={i} style={{display: 'flex', alignItems: 'center', gap, width: RW,
                    margin: i ? `${rowGap}px 0 0` : 0, opacity: rowIn}}>
                    <span style={{flex: '0 0 auto', width: labelW, color: fg, whiteSpace: 'nowrap',
                      overflow: 'hidden', textOverflow: 'ellipsis', font: `600 ${labelSize}px/1.2 ${mono}`}}>{rowLabel}</span>
                    {/* the TRACK: the shot draws the quantity's MASS + the empty channel at the row's weight,
                        the Bar atom draws the DNA's own mark (block run / ruled scale / cells) crisply on top —
                        a 3px hairline is unreadable at hero scale, and the mark alone left the bar floating
                        with no visible full-scale to read the fraction against. */}
                    <span style={{flex: '0 0 auto', position: 'relative', width: TW, height: trackH, overflow: 'hidden'}}>
                      {/* a row with only a `value` has no fraction: no bar AND no empty track, which would read as 0 */}
                      {frac == null ? null : (<>
                      <span style={{position: 'absolute', left: 0, top: (trackH - massH) / 2, width: TW, height: massH,
                        border: `1px solid ${dim}`, opacity: 0.2, borderRadius: 2}} />
                      <span style={{position: 'absolute', left: 0, top: (trackH - massH) / 2, height: massH,
                        width: target * g * TW, background: tone, opacity: 0.42, borderRadius: 2}} />
                      <span style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center'}}>
                        {/* the blank `tag` is the atom's documented "this caller annotates the value itself"
                            signal: without it the `dimension` form prints its own bare number ON the bar and
                            the frame states the same quantity twice, colliding with the row's value column. */}
                        <Bar value={target * g} width={TW} cells={cellCount} size={barSize} tag=" "
                          tone={tone} ink={fg} dimInk={dim} fallbackForm="block" />
                      </span>
                      </>)}
                    </span>
                    <span style={{flex: '0 0 auto', width: pctW, textAlign: 'right', color: tone, whiteSpace: 'nowrap',
                      fontVariantNumeric: 'tabular-nums', font: `700 ${pctSize}px/1 ${mono}`}}>
                      {figureAt(parseFigure(figure), g)}</span>
                    {hasTag ? (
                      <span style={{flex: '0 0 auto', width: tagW, textAlign: 'center', whiteSpace: 'nowrap',
                        overflow: 'hidden', color: done ? tone : dim, border: `1px solid ${done ? tone : dim}`,
                        borderRadius: dna?.radius ?? 4, padding: `${Math.round(barSize * 0.13)}px 0`,
                        font: `700 ${tagSize}px/1.15 ${mono}`, opacity: done ? 1 : 0.45}}>{r.tag}</span>
                    ) : null}
                  </div>
                );
              })}
            </div>

            {isPct ? (
              <div style={{position: 'relative', height: Math.round(barSize * 0.8),
                opacity: 0.8 * clamp01(seg(t, FILL_A + 0.02, FILL_A + 0.09))}}>
                <div style={{position: 'absolute', left: trackLeft, top: 0, width: TW, height: 1, background: dim, opacity: 0.35}} />
                {ticks.map((f) => (
                  <span key={f} style={{position: 'absolute', top: Math.round(barSize * 0.22),
                    left: trackLeft + f * TW, transform: f === 0 ? 'none' : f === 1 ? 'translateX(-100%)' : 'translateX(-50%)',
                    color: dim, fontVariantNumeric: 'tabular-nums',
                    font: `500 ${Math.round(barSize * 0.36)}px/1 ${mono}`}}>{f === 1 ? '100%' : String(f * 100)}</span>
                ))}
              </div>
            ) : null}
          </div>

          {note ? <div style={{marginTop: Math.round(barSize * 0.85), color: dim,
            textWrap: 'balance',
            font: `500 ${Math.round(barSize * 0.68)}px/1.3 ${mono}`}}># {note}</div> : null}
        </TermFrame>
      </div>
    </AbsoluteFill>
  );
};
export default TermBars;
