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

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';

export const DURATION = 155;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', ACC2_D0 = '#2e5e4e', LINE_D0 = '#cdbfa7';

type Layer = {label?: string; depth?: string; note?: string; find?: boolean};

export const StrataColumn: React.FC<{
  kicker?: string;
  layers?: Layer[];      // top (surface) → bottom; `find` marks the layer the beat is about
  note?: string;
}> = ({
  kicker = 'BELOW THE SURFACE',
  layers: LAYERS = [{label: 'surface', depth: '0'}, {label: 'fill', depth: '1 m'},
                    {label: 'what you came for', depth: '4 m', find: true}],
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? '#e5dac6';
  const disp = 'var(--f-display, Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0011));

  const top = CONTENT_TOP + H * 0.03;
  const bottom = H - captionBand(W, H) - H * 0.05;
  const n = Math.max(1, Math.min(6, LAYERS.length));
  const rows = LAYERS.slice(0, n);
  const bandH = (bottom - top) / n;

  // the column sits right of the depth scale and left of the labels
  const scaleX = W * 0.14;
  const colX = W * 0.22, colW = W * 0.26;
  const labX = colX + colW + W * 0.045;

  const kick = easeOutCubic(clamp01(seg(t, 0.03, 0.18)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left: W * 0.08, top: CONTENT_TOP - H * 0.055, opacity: kick,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
        letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>

      {rows.map((L, i) => {
        const st = 0.12 + i * (0.62 / n);
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.62 / n + 0.06)));
        const y = top + i * bandH;
        // each layer is a different density of the same ground, so the column reads as one material
        const tone = mix ? mix(SURF, i % 2 ? ACC2 : ACC, 0.10 + 0.06 * i) : SURF;
        const isFind = !!L.find;
        return (
          <React.Fragment key={i}>
            {/* the layer band, growing downward */}
            <div style={{position: 'absolute', left: colX, top: y, width: colW, height: bandH * on,
              background: isFind ? ACC : tone,
              borderLeft: `${hair}px solid ${LINE}`, borderRight: `${hair}px solid ${LINE}`,
              borderBottom: `${hair}px solid ${LINE}`}} />
            {/* the depth, ruled off at the left with a leader */}
            {L.depth ? (
              <>
                <div style={{position: 'absolute', left: scaleX, top: y - Math.round(W * 0.009),
                  width: colX - scaleX - Math.round(W * 0.008), textAlign: 'right', opacity: on,
                  font: `500 ${Math.round(W * 0.0135)}px/1.2 ${mono}`, color: DIM}}>{L.depth}</div>
                <div style={{position: 'absolute', left: colX - Math.round(W * 0.008), top: y,
                  width: Math.round(W * 0.008) * on, height: hair, background: LINE}} />
              </>
            ) : null}
            {/* the label, to the right of the column */}
            <div style={{position: 'absolute', left: labX, top: y + bandH * 0.5 - Math.round(W * 0.020),
              right: W * 0.07, opacity: on,
              font: `${isFind ? 700 : 500} ${Math.round(W * (isFind ? 0.026 : 0.0225))}px/1.25 ${disp}`,
              color: isFind ? ACC : FG}}>{L.label}
              {L.note ? (
                <div style={{font: `400 ${Math.round(W * 0.0145)}px/1.4 var(--f-body, system-ui, sans-serif)`,
                  color: DIM, marginTop: Math.round(W * 0.004)}}>{L.note}</div>
              ) : null}
            </div>
          </React.Fragment>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.08, right: W * 0.07, top: bottom + H * 0.015,
          opacity: easeOutExpo(clamp01(seg(t, 0.82, 0.96))),
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default StrataColumn;
