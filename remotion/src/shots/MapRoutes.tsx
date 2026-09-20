// SHOT · Map Routes — logistics/network language: glowing routes DRAW between pins on a dark night map, with
// packets travelling the arcs and pins pulsing. A cool, premium "it reaches everywhere / connects your stack"
// look. Deterministic (dash offset + packet position are pure fns of frame).
//
// EVERY PIN HAS LANDED BEFORE THE FRAME IS READ. Pin i pops in over `0.14 + i * 0.05 … + 0.24` and nothing
// capped the list, so past about a dozen spokes the last pins were still popping when the clip ended (and
// from the twentieth on they started after it). The pop step is now laid out for the count — 0.05 stays the
// upper bound, which every list up to MAX_SPOKES already satisfies, so their timing is unchanged — and a list
// past MAX_SPOKES refuses: rendered with twelve, neighbouring labels overlapped on a 1:1 frame (北京 on 上海,
// 重庆 on 武汉), and a hub with that many spokes is a directory, not a picture of reach.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, easeInOutCubic, easeOutBack, clamp01, REDUCED_MOTION_T} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {pointAt} from '../runtime/alongPath';
import {leading, fitIfCJK} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';

export const DURATION = 165; // 5.5s
export const MAX_SPOKES = 10;
// Pin i pops over [PIN_START + i * step, … + PIN_DUR]; PIN_STEP is the original gap and only an upper bound —
// the real step is derived from the count so the last pin has landed by LAND_BY.
const PIN_START = 0.14, PIN_STEP = 0.05, PIN_DUR = 0.24;
const LAND_BY = REDUCED_MOTION_T - 0.02;
export const MapRoutes: React.FC<{items?: string[]; hub?: string; accent?: string}> = ({
  items: SPOKES = ['GitHub', 'Slack', 'Notion', 'Drive', 'Jira', 'Gmail'], hub: HUB = 'WorkBuddy', accent: TEAL = '#3FE0D0'} = {}) => {
  if (!Array.isArray(SPOKES) || SPOKES.length < 1 || SPOKES.length > MAX_SPOKES) {
    throw new Error(
      `MapRoutes needs 1-${MAX_SPOKES} \`items\` (got ${Array.isArray(SPOKES) ? SPOKES.length : typeof SPOKES}). ` +
      'Each is a pin on the ellipse that pops in one after another and must have landed before the settled ' +
      `frame; past ${MAX_SPOKES} the labels collide round the hub. Keep the connections that make the point, ` +
      'or use a list/grid register for a long directory.');
  }
  SPOKES.forEach((s, i) => {
    if (typeof s !== 'string' || !s.trim()) {
      throw new Error(`MapRoutes: item ${i + 1} is empty (got ${JSON.stringify(s)}). Every pin carries the name ` +
        'of what the hub reaches; pass one for each, or leave it out.');
    }
  });
  const n = SPOKES.length;
  const step = n > 1 ? Math.min(PIN_STEP, (LAND_BY - PIN_START - PIN_DUR) / (n - 1)) : PIN_STEP;
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  // Centred on the CONTENT ZONE, not the frame, and scaled to it. Centred on H/2 with a fixed radius the
  // lowest node landed inside the strip the renderer burns the caption over, so a node label and a subtitle
  // drew on top of each other. Deriving both from the zone also makes the layout right at aspects the fixed
  // radius was never checked against.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const SPOKE_ROOM = 44;                                     // the label that rides each spoke's end
  const hx = W / 2, hy = (zTop + zBot) / 2;
  const R = Math.min(460, (zBot - zTop) / 2 - SPOKE_ROOM);
  // the spokes fan out on an ellipse 1.5R wide — cap that axis by the frame, or the east/west labels ride
  // 176-190px off a portrait frame's edges
  const Rx = Math.min(R * 1.5, W / 2 - 150);
  const pts = SPOKES.map((_, i) => {
    const a = (i / SPOKES.length) * Math.PI * 2 - Math.PI / 2;
    return [hx + Math.cos(a) * Rx, hy + Math.sin(a) * R] as [number, number];
  });
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(130% 130% at 50% 45%, #0d2033, #060d16 72%)')}}>
      {/* faint map grid / graticule */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.35}}>
        {[...Array(30)].map((_, i) => <line key={`v${i}`} x1={i * 70} y1={0} x2={i * 70} y2={H} stroke="#123049" strokeWidth={1} />)}
        {[...Array(16)].map((_, i) => <ellipse key={`h${i}`} cx={hx} cy={hy} rx={120 + i * 130} ry={70 + i * 78} fill="none" stroke="#0f2a42" strokeWidth={1} />)}
      </svg>
      {/* glowing routes hub→spoke, drawing on, with a travelling packet */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {pts.map(([px, py], i) => {
          const midx = (hx + px) / 2, midy = (hy + py) / 2 - 140;
          const d = `M${hx},${hy} Q${midx},${midy} ${px},${py}`;
          const draw = clamp01((easeInOutCubic(seg(t, 0.12, 0.7)) - i * 0.03) / 0.4);
          const pk = clamp01((t - 0.3 - i * 0.05) / 0.5); // packet position 0→1
          // ON the route, not beside it. `lerp(hub, pin) - sin` is a second, different model of a curve the
          // `d` string above already describes exactly; measured against the route's own arc length the
          // packet rode up to 140px off the line it is supposed to be travelling down.
          const {x: bx, y: by} = pointAt(d, pk);
          return <g key={i}>
            <path d={d} fill="none" stroke={TEAL} strokeWidth={3} strokeOpacity={0.9} {...drawOn(draw)}
              style={{filter: `drop-shadow(0 0 8px ${TEAL})`}} />
            {t > 0.3 + i * 0.05 && pk < 1 && <circle cx={bx} cy={by} r={7} fill="#eafffb" style={{filter: `drop-shadow(0 0 10px ${TEAL})`}} />}
          </g>;
        })}
      </svg>
      {/* spoke pins + labels */}
      {pts.map(([px, py], i) => {
        const pop = easeOutBack(seg(t, PIN_START + i * step, PIN_START + i * step + PIN_DUR));
        const pulse = 1 + 0.4 * Math.max(0, Math.sin((t - 0.3 - i * 0.05) * 9));
        // THE LABEL TAKES THE SIDE THAT HAS ROOM, AND IS FITTED TO IT. It was pinned 34px to the RIGHT of
        // every spoke and set `nowrap` at a fixed 26px — fine for the east spokes of a 1920 frame and for
        // short English names, and 187px off the edge for a Chinese one on a 1080-wide frame. A pin near
        // the right edge has no room on its right; it has plenty on its left. Anchoring by `right` inside
        // this zero-size container puts the label's RIGHT edge 34px left of the pin, mirroring the offset.
        const LBL_OFF = 34, LBL_PADX = 16, LBL_MARGIN = 24;
        const roomR = W - (px + LBL_OFF) - LBL_MARGIN, roomL = (px - LBL_OFF) - LBL_MARGIN;
        const flip = roomR < roomL;
        const lblPx = fitTextPx(SPOKES[i], Math.max(80, (flip ? roomL : roomR) - LBL_PADX * 2), 26, {usable: 1});
        return <div key={i} style={{position: 'absolute', left: px, top: py, transform: `translate(-50%,-50%) scale(${clamp01(pop)})`}}>
          <div style={{position: 'absolute', left: -18, top: -18, width: 36, height: 36, borderRadius: 18, background: TEAL, boxShadow: `0 0 20px ${TEAL}`}} />
          <div style={{position: 'absolute', left: -18 * pulse, top: -18 * pulse, width: 36 * pulse, height: 36 * pulse, borderRadius: '50%', border: `2px solid ${TEAL}`, opacity: 2 - pulse}} />
          <div style={{position: 'absolute', ...(flip ? {right: LBL_OFF} : {left: LBL_OFF}), top: -20, padding: `8px ${LBL_PADX}px`, borderRadius: 8, background: 'rgba(10,25,35,.85)', border: `1px solid ${TEAL}55`, font: `700 ${lblPx}px/1 var(--f-body, Inter)`, color: '#dffffa', whiteSpace: 'nowrap'}}>{SPOKES[i]}</div>
        </div>;
      })}
      {/* the hub */}
      <div style={{position: 'absolute', left: hx, top: hy, transform: 'translate(-50%,-50%)'}}>
        {/* THE HUB LABEL IS FITTED AND BALANCED. A 130px disc holds a short English word at 30px and drops a
          single Chinese character onto a second line the moment the label is one unit wider: a delivered
          film's hub read 「MCP 协」 over a line holding just 「议」, at a leading with no air in it either.
          `fitIfCJK` shrinks only CJK copy (English keeps the size the disc was designed at), `leading`
          only ever raises, and `balance` splits what still has to wrap into even lines. */}
      <div style={{width: 130, height: 130, borderRadius: 65, background: 'radial-gradient(circle,#fff,#8ff5e8 60%,#2fb5a5)', boxShadow: `0 0 60px ${TEAL}`, display: 'flex', alignItems: 'center', justifyContent: 'center', font: `800 ${fitIfCJK(HUB, 30, (t, base) => fitTextPx(t, 114, base, {usable: 1.0}))}px/${leading(HUB, 1)} var(--f-body, Inter)`, color: '#06322b', textAlign: 'center', textWrap: 'balance', padding: 8}}>{HUB}</div>
      </div>
    </AbsoluteFill>
  );
};
export default MapRoutes;
