// SHOT · StrataColumn — a stratigraphic column read top-down: what lies under this ground, layer by
// layer, with depths and finds. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "it is still there, underneath" is a claim about DEPTH, and depth is the one thing
// a flat diagram of boxes cannot say. An excavator's column says it natively — surface at the top, each
// layer drawn to its own thickness with the depth ruled off at the left, and the thing you are arguing
// about sitting at the level it actually sits at. Any film with a buried, layered or historically-stacked
// subject can reach for it: sediment, infrastructure under a street, versions under a codebase.
//
// The layers draw DOWNWARD in order, so the viewer descends with the shot instead of being shown a
// finished cross-section.
//
// A NOTE ON THE ONE THING THIS FORM CANNOT FAKE. A column with numerals ruled off its left edge is read
// as a ruler: the eye takes the distance between two marks as the interval between them. So the band
// heights have to come from the depths, or the marks must not be presented as a ruler. Both paths are
// implemented below (`metric`); which one runs is decided by what the film supplied, never by taste.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';

export const DURATION = 155;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', ACC2_D0 = '#2e5e4e', LINE_D0 = '#cdbfa7';

type Layer = {label?: string; depth?: string; note?: string; find?: boolean};

// The depth a film writes is copy, not a number: '0', '3.8 m', '−2,5 m', '深さ 4 m', or 'street'. This
// reads the figure it states, or null when it states none. Thousands separators go first so a comma is
// only ever read as a decimal point afterwards ('1,200 m' → 1200, '2,5 m' → 2.5), and the three dashes a
// typographer might use for a minus are normalised — 'street' and 'water' correctly yield null, which is
// what puts a beat like those on the non-metric path instead of inventing a position for it.
const readDepth = (s?: string): number | null => {
  if (typeof s !== 'string') return null;
  const t = s.replace(/(\d),(\d{3})(?!\d)/g, '$1$2').replace(/[−–—]/g, '-');
  const m = t.match(/-?\d+(?:[.,]\d+)?/);
  if (!m) return null;
  const v = Number(m[0].replace(',', '.'));
  return Number.isFinite(v) ? v : null;
};

export const StrataColumn: React.FC<{
  kicker?: string;
  layers?: Layer[];      // top (surface) → bottom; `find` marks the layer the beat is about
  base?: string;         // depth at the FOOT of the column — the last layer's thickness lives here
  note?: string;
}> = ({
  kicker = 'BELOW THE SURFACE',
  layers: LAYERS = [{label: 'surface', depth: '0'}, {label: 'fill', depth: '1 m'},
                    {label: 'what you came for', depth: '4 m', find: true}],
  base = '',
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? '#e5dac6';
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0011));

  const top = CONTENT_TOP + H * 0.03;
  const bottom = H - captionBand(W, H) - H * 0.05;
  const n = Math.max(1, Math.min(6, LAYERS.length));
  const rows = LAYERS.slice(0, n);
  const truncated = LAYERS.length > n;   // the column does not bottom out where the frame does
  const bandH = (bottom - top) / n;

  // the column sits right of the depth scale and left of the labels
  const scaleX = W * 0.14;
  const colX = W * 0.22, colW = W * 0.26;
  const labX = colX + colW + W * 0.045;

  // THE MEASURED COLUMN — the fix for a scale nobody supplied.
  //
  // Every band used to be (bottom - top) / n, so its thickness came from the array index while a numeral
  // sat beside it claiming to be a depth. On beat 5 of the Utrecht film that put '0' at the column head
  // and '3.8 m' at the 2/3 line (measured on the render: tick at y=207, tick at y=600, foot at y=797) —
  // which reads off the frame as a medieval fill exactly 1.9 m thick and a fort floor at 5.7 m. Neither
  // figure was in the storyboard. On a survey form, a magnitude the film did not supply is the one thing
  // that must not be drawn.
  //
  // So: the bands are proportional to the depths ONLY when the film supplied enough to make them so —
  // every boundary numeric, a `base` for the foot, one consistent direction (a column of elevations
  // running the other way is as valid as one of depths, hence the sign check rather than a rising test),
  // and every band tall enough to still carry its own label. A run of intervals like 0.1 m / 30 m is
  // arithmetically fine and unreadable, and a band squeezed under its label is a worse lie than an
  // honest diagram. Any of those unmet and `metric` is null — see the fallback below.
  const marks = rows.map((L) => readDepth(L.depth));
  const baseD = readDepth(base);
  const metric: number[] | null = (() => {
    // `layers: []` with a base yielded an EMPTY interval list, which is truthy and made `hOf` return
    // undefined — a band of height NaN and a ruler running to nowhere. No layers, no scale.
    if (rows.length === 0) return null;
    if (baseD === null || marks.some((d) => d === null)) return null;
    const ds = [...(marks as number[]), baseD];
    const iv = ds.slice(1).map((d, i) => d - ds[i]);
    const dir = Math.sign(iv[0]);
    if (dir === 0 || iv.some((v) => Math.sign(v) !== dir)) return null;
    const span = Math.abs(baseD - (marks[0] as number));
    const hs = iv.map((v) => (Math.abs(v) / span) * (bottom - top));
    const needs = rows.map((L) => Math.round(W * 0.0225 * 1.25) +
      (L.note ? Math.round(W * 0.0145 * 1.4) : 0));
    return hs.some((h, i) => h < needs[i]) ? null : hs;
  })();

  // Without a scale the column must stop LOOKING like one. The bands are parted by a slot carrying a
  // dashed rule — the section-break every geological log uses for "material omitted, spacing not to
  // scale" — and the continuous ruler line down the left is not drawn. The depth numerals stay, because
  // each one is still a true statement about the boundary it touches; it is only the distance between
  // them that the film never measured, and a broken column is precisely the mark for that.
  const gap = metric ? 0 : Math.max(2, Math.round(H * 0.011));
  const yTop = (i: number) => metric ? top + metric.slice(0, i).reduce((a, b) => a + b, 0) : top + i * bandH;
  const hOf = (i: number) => metric ? metric[i] : bandH - gap;
  const foot = yTop(n - 1) + hOf(n - 1);

  const kick = easeOutCubic(clamp01(seg(t, 0.03, 0.18)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left: W * 0.08, top: CONTENT_TOP - H * 0.055, opacity: kick,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
        letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>

      {/* THE RULER, drawn only when there is one. A continuous line down the scale is the mark that says
          "these numerals share an axis" — so it appears exactly when the bands are proportional to the
          depths, and never otherwise. */}
      {metric ? (
        <div style={{position: 'absolute', left: colX - Math.round(W * 0.008), top,
          width: hair, height: (foot - top) * easeOutCubic(clamp01(seg(t, 0.10, 0.80))), background: LINE}} />
      ) : null}

      {rows.map((L, i) => {
        const st = 0.12 + i * (0.62 / n);
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.62 / n + 0.06)));
        const y = yTop(i);
        const h = hOf(i);
        // each layer is a different density of the same ground, so the column reads as one material
        const tone = mix ? mix(SURF, i % 2 ? ACC2 : ACC, 0.10 + 0.06 * i) : SURF;
        const isFind = !!L.find;
        return (
          <React.Fragment key={i}>
            {/* the section break — only in the fallback, where the gap is what it stands for. It overhangs
                both edges of the column because a dashed rule flush with the band edge reads as a seam
                between two courses, while one that runs past the edges reads as a cut through them — the
                difference between "next layer" and "not continuous", in the ~1s a viewer gives it. */}
            {!metric && i > 0 ? (
              <div style={{position: 'absolute', left: colX - W * 0.009, top: y - Math.round(gap / 2),
                width: (colW + W * 0.018) * on, height: 0, borderTop: `${hair}px dashed ${LINE}`}} />
            ) : null}
            {/* the layer band, growing downward */}
            <div style={{position: 'absolute', left: colX, top: y, width: colW, height: h * on,
              background: isFind ? ACC : tone,
              borderLeft: `${hair}px solid ${LINE}`, borderRight: `${hair}px solid ${LINE}`,
              borderBottom: `${hair}px solid ${LINE}`}} />
            {/* the depth, ruled off at the left with a leader */}
            {L.depth ? (
              <>
                <div style={{position: 'absolute', left: scaleX, top: y - Math.round(W * 0.009),
                  width: colX - scaleX - Math.round(W * 0.008), textAlign: 'right', opacity: on,
                  font: `500 ${Math.round(W * 0.0135)}px/1.2 ${mono}`, textWrap: 'balance', color: DIM}}>{L.depth}</div>
                <div style={{position: 'absolute', left: colX - Math.round(W * 0.008), top: y,
                  width: Math.round(W * 0.008) * on, height: hair, background: LINE}} />
              </>
            ) : null}
            {/* the label, to the right of the column */}
            <div style={{position: 'absolute', left: labX, top: y + h * 0.5 - Math.round(W * 0.020),
              right: W * 0.07, opacity: on,
              font: `${isFind ? 700 : 500} ${Math.round(W * (isFind ? 0.026 : 0.0225))}px/1.25 ${disp}`,
              color: isFind ? ACC : FG, textWrap: 'balance'}}>{L.label}
              {L.note ? (
                <div style={{font: `400 ${Math.round(W * 0.0145)}px/1.4 var(--f-body, system-ui, sans-serif)`,
                  color: DIM, textWrap: 'balance', marginTop: Math.round(W * 0.004)}}>{L.note}</div>
              ) : null}
            </div>
          </React.Fragment>
        );
      })}

      {/* The foot of a measured column is itself a reading, so it is written where the ruler ends — and
          it is written only when the film gave it, which is the same condition that made the column
          metric in the first place. */}
      {metric && base ? (
        <>
          <div style={{position: 'absolute', left: scaleX, top: foot - Math.round(W * 0.009),
            width: colX - scaleX - Math.round(W * 0.008), textAlign: 'right',
            opacity: easeOutCubic(clamp01(seg(t, 0.74, 0.90))),
            font: `500 ${Math.round(W * 0.0135)}px/1.2 ${mono}`, textWrap: 'balance', color: DIM}}>{base}</div>
          <div style={{position: 'absolute', left: colX - Math.round(W * 0.008), top: foot,
            width: Math.round(W * 0.008) * easeOutCubic(clamp01(seg(t, 0.74, 0.90))),
            height: hair, background: LINE}} />
        </>
      ) : null}

      {/* More layers than the frame can hold used to be dropped by `slice` in silence, which left a column
          that looks like it reaches bedrock. An open dashed foot is the log's own mark for "continues
          below" — the omission is shown rather than asserted away. */}
      {truncated ? (
        <div style={{position: 'absolute', left: colX, top: foot + Math.round(H * 0.012), width: colW,
          height: 0, opacity: easeOutCubic(clamp01(seg(t, 0.72, 0.92))),
          borderTop: `${hair}px dashed ${LINE}`}} />
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.08, right: W * 0.07, top: bottom + H * 0.015,
          opacity: easeOutExpo(clamp01(seg(t, 0.82, 0.96))),
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em', textWrap: 'balance'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default StrataColumn;
