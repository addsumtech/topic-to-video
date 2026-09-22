// SHOT · StatedBy — figures whose SOURCE is the claim: the values stand on the plate, and a stamp is struck
// across its corner naming who asserted them and when.
//
// WHAT IT ARGUES, AND WHY NOTHING ELSE SAID IT. This library has several ways to show a number — a serif
// pull-stat, a mono counter, a bar readout — and every one of them presents the figure as a FACT, with any
// attribution demoted to a caption under it. That is the wrong hierarchy for a whole class of beat: a
// vendor-stated benchmark, a self-reported survey, a press release, a manufacturer's rating, a party's own
// count. There the figure's provenance is not a footnote to the claim, it IS the claim — "X says 98%" is a
// different sentence from "98%", and a frame that prints only the second has asserted something the film did
// not. So the stamp is a first-class object here: it lands LAST, it overlaps the plate's own rule, and it
// carries the source and the date at a size a viewer reads rather than a size a viewer forgives.
//
// WHY IT IS REUSABLE. The shape is "one to three figures, one speaker". Any film quoting figures it did not
// measure reaches for it, and its own defaults stay generic.
//
// NO NUMBER IS INVENTED. Every value is printed through `figureText`/`figureAt`, which keeps the film's own
// string exactly — its sign, its decimals, its grouping, its unit — and counts up only toward that string.
// `figureValue` is never used to redraw it. With no `figures` the register throws instead of composing an
// empty plate with a stamp on it, which would look authoritative and say nothing.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutBack, lerp} from '../runtime/motion';
import {captionBand, CONTENT_TOP, fitTextPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {parseFigure, figureAt} from '../runtime/figure';
import {useDNA, readableOn, dimOn} from '../runtime/dna';
import {onAccentInk} from '../runtime/onAccent';

export const DURATION = 165; // 5.5s

/** Three is the plate. A fourth takes each figure under the size at which a big number is the thing you see
 *  first, which is the only reason to set a number big. Four figures want a table. */
export const MAX_STATED_FIGURES = 3;

const BG_D0 = '#f3efe6', FG_D0 = '#171a22', DIM_D0 = '#6e7488',
  ACC_D0 = '#9c3b1e', SURF_D0 = '#fbf8f1', LINE_D0 = '#cfc5b0';

type Fig = {
  /** the figure, exactly as it should read — "1000 万", "98%", "0.5 秒", "−12" */
  value?: string;
  /** the unit, set small beside the figure */
  unit?: string;
  /** what the figure measures */
  label?: string;
};

type Stamp = {
  /** the word struck across the plate — the READING, not the source ("vendor-stated", "self-reported") */
  label?: string;
  /** who said it */
  source?: string;
  /** when it was read */
  date?: string;
};

const DEMO: Fig[] = [
  {value: '00', unit: 'unit', label: 'what it measures'},
  {value: '00', unit: 'unit', label: 'and the second thing'},
];

export const StatedBy: React.FC<{
  kicker?: string;
  figures?: Fig[];
  stamp?: Stamp;
  note?: string;
  /** false holds every figure at its final string from the first frame — for a beat whose point IS the
   *  number, where parading invented intermediate digits would be its own small lie. */
  roll?: boolean;
}> = ({
  kicker = 'THE FIGURES',
  figures = DEMO,
  stamp = {label: 'stated by', source: 'the source', date: ''},
  note = '',
  roll = true,
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  const figs = (Array.isArray(figures) ? figures : []).filter((f) => f && parseFigure(f.value).text);
  if (!figs.length) {
    throw new Error(
      'StatedBy needs at least one `figures` entry with a `value`. The register is a plate of figures under ' +
      'the stamp of whoever asserted them; with no figure the stamp attributes nothing.');
  }
  if (figs.length > MAX_STATED_FIGURES) {
    throw new Error(
      `StatedBy holds at most ${MAX_STATED_FIGURES} figures, got ${figs.length}. Past three each figure falls ` +
      'under the size that makes a number the first thing read — which is the only reason to set one big.');
  }
  const st: Stamp = stamp && typeof stamp === 'object' ? stamp : {};
  const stampLabel = String(st.label ?? '').trim();
  const stampSource = String(st.source ?? '').trim();
  const stampDate = String(st.date ?? '').trim();
  if (!stampLabel && !stampSource) {
    throw new Error(
      'StatedBy needs a `stamp` with a `label` or a `source`. Attribution is this register\'s whole argument — ' +
      'a plate of figures with no stamp is a different register (EdStat, TermCounter).');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const LINE = dna?.line ?? LINE_D0;
  const RAD = dna?.radius ?? 4;
  const BW = Math.max(1, dna?.borderWidth ?? 1);
  const disp = dna?.fontDisplay ?? 'var(--f-display, "Playfair Display", Georgia, serif)';
  const body = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';

  const INK = readableOn(SURF, FG, GROUND, '#0a0d14', '#ffffff');
  const DIM = dimOn(SURF, INK, 4.5);
  // THE STAMP IS A SOLID BLOCK, not an outline, and that is an argument about hierarchy rather than a
  // decoration: on this form the provenance is the claim, so it is the one object on the plate that is set
  // in reverse. Its ink is MEASURED against the block (see `onAccentInk`) — which is also how the system's
  // second accent gets to speak at all on a light film, where it cannot be read on the stock itself.
  const STAMP_BLOCK = readableOn(SURF, ACC, INK);
  const STAMP_INK = onAccentInk(STAMP_BLOCK, dna?.accent2, dna?.onAccent, GROUND);

  const U = Math.min(W, H);
  const top = CONTENT_TOP;
  const bottom = H - captionBand(W, H);
  const n = figs.length;
  const stacked = W < H * 1.1 || n > 2 && W < H * 1.45;

  const kickPx = Math.round(U * 0.026);
  const notePx = Math.round(U * 0.028);
  const noteH = note ? inkBlockH(notePx, 2) + Math.round(U * 0.02) : 0;
  const zoneTop = top + inkBlockH(kickPx) + Math.round(U * 0.028);
  const zoneBot = bottom - noteH;
  const zoneH = Math.max(U * 0.3, zoneBot - zoneTop);

  const plateW = Math.round(Math.min(W * 0.86, U * 1.60));
  const plateH = Math.round(Math.min(zoneH, U * 0.66));
  const plateX = Math.round((W - plateW) / 2);
  const plateY = Math.round(zoneTop + Math.max(0, (zoneH - plateH) / 2));
  const padX = Math.round(plateW * 0.065);
  const padY = Math.round(plateH * 0.12);
  // the stamp sits on its own band along the FOOT of the plate, so it overlaps the plate's rule and never
  // the figures' own type — a stamp across a number is a stamp that costs you the number.
  const footH = Math.round(plateH * 0.30);
  const cellH = plateH - padY - footH;

  const cellW = stacked ? plateW - padX * 2 : Math.floor((plateW - padX * 2) / n);
  const rowH = stacked ? Math.floor(cellH / n) : cellH;

  const figBase = Math.round(Math.min(rowH * (stacked ? 0.52 : 0.46), U * (stacked ? 0.11 : 0.15)));
  const unitPx = Math.round(figBase * 0.30);
  const labelPx = Math.min(Math.round(U * 0.026), Math.round(rowH * 0.18));

  const plateIn = easeOutCubic(clamp01(seg(t, 0.04, 0.24)));
  const kickIn = clamp01(seg(t, 0.02, 0.14));
  const land = easeOutBack(clamp01(seg(t, 0.62, 0.78)));
  const noteIn = clamp01(seg(t, 0.76, 0.88));

  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', top, left: 0, right: 0, textAlign: 'center', color: dna?.dim ?? DIM_D0,
        opacity: kickIn, letterSpacing: dna?.labelSpacing ?? '0.16em',
        font: `600 ${kickPx}px/${leading(kicker, 1.2)} ${mono}`}}>{kicker}</div>

      <div style={{position: 'absolute', left: plateX, top: plateY, width: plateW, height: plateH,
        boxSizing: 'border-box', background: SURF, border: `${BW}px solid ${LINE}`, borderRadius: RAD,
        opacity: clamp01(plateIn * 1.2), transform: `translateY(${lerp(U * 0.024, 0, plateIn)}px)`,
        boxShadow: `0 ${Math.round(U * 0.012)}px ${Math.round(U * 0.032)}px #00000018`}}>

        {figs.map((f, i) => {
          const fig = parseFigure(f.value);
          const enter = clamp01(seg(t, 0.14 + i * 0.10, 0.30 + i * 0.10));
          const p = roll ? clamp01(seg(t, 0.18 + i * 0.10, 0.52 + i * 0.10)) : 1;
          const shown = figureAt(fig, p);
          const unit = String(f.unit ?? '');
          const label = String(f.label ?? '');
          const px = fitTextPx(shown, cellW - Math.round(U * 0.05), figBase, {usable: 0.96, adv: 0.62});
          const x = stacked ? padX : padX + i * cellW;
          const y = stacked ? padY + i * rowH : padY;
          return (
            <div key={i} style={{position: 'absolute', left: x, top: y, width: cellW, height: rowH,
              boxSizing: 'border-box', paddingRight: stacked ? 0 : Math.round(U * 0.018),
              opacity: clamp01(enter * 1.3), display: 'flex', flexDirection: 'column',
              justifyContent: 'center', gap: Math.round(U * 0.008)}}>
              {/* a hairline above each cell is the plate's own ruling, not a divider between colours */}
              {i > 0 && !stacked ? (
                <div style={{position: 'absolute', left: 0, top: Math.round(rowH * 0.12),
                  bottom: Math.round(rowH * 0.12), width: Math.max(1, BW), background: LINE}} />
              ) : null}
              <div style={{display: 'flex', alignItems: 'baseline', gap: Math.round(U * 0.012),
                paddingLeft: i > 0 && !stacked ? Math.round(U * 0.022) : 0}}>
                <div style={{color: INK, whiteSpace: 'nowrap',
                  font: `700 ${px}px/${leading(shown, 1.0)} ${disp}`, letterSpacing: '-0.015em'}}>{shown}</div>
                {unit ? (
                  <div style={{color: DIM, whiteSpace: 'nowrap',
                    font: `500 ${unitPx}px/${leading(unit, 1.2)} ${body}`}}>{unit}</div>
                ) : null}
              </div>
              {label ? (
                <div style={{color: DIM, textWrap: 'balance',
                  paddingLeft: i > 0 && !stacked ? Math.round(U * 0.022) : 0,
                  font: `500 ${fitTextPx(label, cellW - Math.round(U * 0.04), labelPx, {usable: 0.98})}px/${leading(label, 1.3)} ${body}`}}>{label}</div>
              ) : null}
            </div>
          );
        })}

        {/* the plate's foot rule — the stamp is struck ACROSS it */}
        <div style={{position: 'absolute', left: padX, right: padX, top: plateH - footH,
          height: Math.max(1, BW), background: LINE}} />

        <div style={{position: 'absolute', left: padX, top: plateH - footH + Math.round(footH * 0.16),
          transform: `rotate(-2.4deg) scale(${lerp(1.45, 1, land)})`, transformOrigin: 'left center',
          opacity: clamp01(land * 1.25),
          border: `${Math.max(2, Math.round(U * 0.0035))}px solid ${STAMP_BLOCK}`,
          borderRadius: Math.max(2, RAD), padding: `${Math.round(U * 0.012)}px ${Math.round(U * 0.022)}px`,
          background: STAMP_BLOCK,
          display: 'flex', alignItems: 'baseline', gap: Math.round(U * 0.016), maxWidth: plateW - padX * 2}}>
          {stampLabel ? (
            <div style={{color: STAMP_INK, whiteSpace: 'nowrap', letterSpacing: dna?.labelSpacing ?? '0.08em',
              font: `800 ${fitTextPx(stampLabel, (plateW - padX * 2) * 0.5, Math.round(U * 0.034), {usable: 0.98})}px/${leading(stampLabel, 1.15)} ${disp}`}}>{stampLabel}</div>
          ) : null}
          {stampSource ? (
            <div style={{color: STAMP_INK, whiteSpace: 'nowrap', opacity: 0.92,
              font: `600 ${fitTextPx(stampSource, (plateW - padX * 2) * 0.42, Math.round(U * 0.024), {usable: 0.98})}px/${leading(stampSource, 1.2)} ${mono}`}}>{stampSource}</div>
          ) : null}
          {stampDate ? (
            <div style={{color: STAMP_INK, whiteSpace: 'nowrap', opacity: 0.8,
              font: `500 ${Math.round(U * 0.020)}px/1.2 ${mono}`}}>{stampDate}</div>
          ) : null}
        </div>
      </div>

      {note ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.1), right: Math.round(W * 0.1),
          top: zoneBot + Math.round(U * 0.012), textAlign: 'center', color: dna?.dim ?? DIM_D0, opacity: noteIn,
          font: `500 ${notePx}px/${leading(note, 1.4)} ${body}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default StatedBy;
