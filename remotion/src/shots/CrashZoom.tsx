// SHOT · Crash Zoom — a wide overview grid holds, then the camera PUNCHES in on one target tile (radial speed
// lines, a touch of overshoot) until it fills the CONTENT ZONE as a detail card. The "…and here's the one that
// matters" register (family B — camera). Deterministic (zoom scale = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutBack, easeOutCubic} from '../runtime/motion';
import {captionBand} from '../runtime/layout';
import {useDNA, mix, shade} from '../runtime/dna';

export const DURATION = 140; // ~4.7s
const BG_D0 = '#0a0c13', ACC_D0 = '#5b8cff';
const OVERSHOOT = 1.06;      // the easeOutBack punch past the resting scale — the fit budget pre-divides by it

export const CrashZoom: React.FC<{items?: string[]; label?: string; target?: number; title?: string}> = ({
  items: ITEMS = ['Inbox', 'Docs', 'Tasks', 'Chat', 'Focus', 'Data', 'Code', 'Team', 'Calls'],
  label: LABEL = 'One place for all of it', target: TARGET = 4, title: TITLE = 'Your workspace'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, ACC = dna?.accent ?? ACC_D0;
  // The hero card's second gradient stop used to be a hardcoded '#2c3ac0'. On a themed film that stop
  // OVERRODE the DNA: the card is ~25% of the frame, so a green/amber film got a royal-blue hero. Derive
  // it from the film's own two hues; with no DNA the original blue is still exactly what renders.
  const ACC_DEEP = dna ? shade(mix(ACC, dna.accent2 ?? ACC, 0.45), 0.3) : '#2c3ac0';
  const bodyFace = 'var(--f-body, Inter, system-ui, sans-serif)';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // GRID GEOMETRY. ch is capped so a 1- or 2-row grid doesn't produce absurdly tall tiles (a 3-item grid
  // used to make each tile 704px tall, which left the punch nowhere to go — the "zoom" was 1.1x).
  const cols = Math.max(1, Math.min(3, ITEMS.length));
  const rows = Math.ceil(ITEMS.length / cols);
  // gw is frame-relative: a hardcoded 1180 overflowed the overview state at 9:16 (W=1080) before the punch
  // even started.
  const cw = Math.min(1180, W * 0.90) / cols, ch = Math.min(720 / rows, 300);
  const gw = cw * cols, gh = ch * rows;
  const gx = (W - gw) / 2, gy = (H - gh) / 2;
  const tw = cw - 16, th = ch - 16;                            // one tile's box
  const ti = Math.min(Math.max(0, TARGET), ITEMS.length - 1);
  const tcol = ti % cols, trow = Math.floor(ti / cols);
  // target-tile centre in overview coords
  const tcx = gx + tcol * cw + cw / 2, tcy = gy + trow * ch + ch / 2;

  // WHERE THE PUNCH LANDS. The hero must come to rest INSIDE the content zone: clear of the action-safe
  // border (frame_safe_qa errors on bright pixels there) and clear of the burned caption band. Letting it
  // run to (W/cw)*0.98 sent the neighbours off-frame at near-full opacity and parked the card's own edge
  // under the subtitle. Both are measured off the frame, so this holds at 9:16 and 1:1 too.
  const CB = captionBand(W, H);
  const zoneTop = H * 0.10, zoneBot = H - CB;
  const cy = (zoneTop + zoneBot) / 2;
  const fit = Math.min(W * 0.80 / tw, (zoneBot - zoneTop) * 0.88 / th) / OVERSHOOT;

  const z = easeInOutCubic(seg(t, 0.34, 0.74));               // the punch
  const over = 1 + (OVERSHOOT - 1) * easeOutBack(clamp01(seg(t, 0.68, 0.82))) * (1 - clamp01(seg(t, 0.82, 0.95)));
  const scale = lerp(1, fit, z) * over;
  // Scale about the target centre, then dolly that centre to the content-zone centre.
  const dx = lerp(0, W / 2 - tcx, z), dy = lerp(0, cy - tcy, z);
  // The neighbours leave frame during the punch — they must be GONE before their edges reach the border,
  // not still legible and sliced in half by it.
  const away = clamp01(z * 2.6);
  const speed = Math.sin(clamp01(seg(t, 0.34, 0.74)) * Math.PI);  // speed-lines intensity, rise+fall
  const detail = easeOutCubic(seg(t, 0.72, 0.9));
  const titleIn = easeOutCubic(seg(t, 0.04, 0.18));

  // WIDTH-AWARE TYPE. Both strings are fitted against the UNSCALED tile, so the text/card ratio is fixed and
  // whatever fits in the overview still fits at full punch. Hardcoded 40/54px overflowed the card for any
  // label longer than the demo default.
  const itemSize = React.useMemo(() => {
    const sizes = ITEMS.map((s) => fitTextOnNLines({
      text: String(s ?? ''), maxLines: 2, maxBoxWidth: tw - 48, fontFamily: bodyFace,
      fontWeight: 800, maxFontSize: 44,
    }).fontSize);
    return sizes.length ? Math.min(...sizes) : 40;
  }, [ITEMS, tw, bodyFace]);
  const labelSize = React.useMemo(() => fitTextOnNLines({
    text: String(LABEL ?? ''), maxLines: 2, maxBoxWidth: tw - 48, fontFamily: bodyFace,
    fontWeight: 800, maxFontSize: 56,
  }).fontSize, [LABEL, tw, bodyFace]);

  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #12162a, ${BG} 72%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 60, left: 0, right: 0, textAlign: 'center',
        opacity: titleIn * (1 - z), color: '#aeb6ca', font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)',
        letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <AbsoluteFill style={{transformOrigin: `${tcx}px ${tcy}px`,
        transform: `translate(${dx}px, ${dy}px) scale(${scale})`}}>
        {ITEMS.map((it, i) => {
          const c = i % cols, r = Math.floor(i / cols);
          const isT = i === ti;
          const enter = easeOutBack(clamp01(seg(t, 0.06 + i * 0.03, 0.28 + i * 0.03)));
          return (
            <div key={i} style={{position: 'absolute', left: gx + c * cw + 8, top: gy + r * ch + 8,
              width: tw, height: th, opacity: clamp01(enter * 1.4) * (isT ? 1 : 1 - away),
              transform: `scale(${lerp(0.9, 1, enter)})`, borderRadius: 18,
              background: isT ? `linear-gradient(150deg, ${ACC}, ${ACC_DEEP})` : 'linear-gradient(160deg, #14172480, #0d0f18)',
              border: `1px solid ${isT ? 'transparent' : '#20243a'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 24px',
              boxShadow: isT ? `0 20px 60px ${ACC}44` : '0 12px 30px #0006'}}>
              <div style={{color: isT ? '#fff' : '#c7cee0',
                font: `800 ${isT && detail > 0.1 ? labelSize : itemSize}px/1.16 ${bodyFace}`,
                letterSpacing: '-0.02em', textAlign: 'center'}}>
                {isT && detail > 0.1 ? LABEL : it}
              </div>
            </div>
          );
        })}
      </AbsoluteFill>

      {/* radial speed lines during the punch — centred on where the hero lands, not the raw frame centre */}
      {speed > 0.02 ? (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'screen'}}>
          {[...Array(28)].map((_, i) => {
            const a = (i / 28) * Math.PI * 2, r0 = 180 + (i % 3) * 40, r1 = r0 + 260;
            const cx = W / 2, cyy = cy;
            return <line key={i} x1={cx + Math.cos(a) * r0} y1={cyy + Math.sin(a) * r0}
              x2={cx + Math.cos(a) * r1} y2={cyy + Math.sin(a) * r1} stroke="#ffffff" strokeWidth={3}
              opacity={speed * 0.5} strokeLinecap="round" />;
          })}
        </svg>
      ) : null}
    </AbsoluteFill>
  );
};
export default CrashZoom;
