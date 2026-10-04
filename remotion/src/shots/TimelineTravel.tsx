// SHOT · Timeline Travel — roadmap/journey language: a horizontal timeline the camera TRAVELS along, each
// dated milestone lighting up as it passes. Clean light rail (a calm, temporal look). Deterministic camera
// pan over a world wider than the frame — a travelling reveal the flat tier can't do.
//
// THE CAMERA ENDS ON THE LAST STOP. The pan used to run from W/2 to `worldW - W/2` — the lens stopping half a
// frame short of the world's right edge, while the last stop stood 520px before that edge. So the end of the
// travel depended on the frame's WIDTH: at 1080 wide it happened to land on the last stop, and at 1920 the
// lens stopped 440px short of it, so on a 16:9 film the final milestone's label never appeared and its node
// never lit — the destination of the journey was the one stop the viewer never reached. With one or two
// stops the world was narrower than the frame, the end was LEFT of the start, and the camera panned
// backwards; with none it drew an empty rail. The travel now ends with the lens on the last stop at every
// aspect (the lit/pop thresholds are 30px and 260px, and the settled frame leaves the lens under 6px short),
// a list too short to pan simply holds on its stop, an empty list throws, and past MAX_STOPS the pan would
// sweep each milestone past faster than its label can be read, so the register refuses.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
export const MAX_STOPS = 6;
// LEVEL-C: the timeline UI flips with the DNA (rail, nodes, ink, accent) → a dark-mode timeline on a dark DNA, the
// original light rail on null DNA.
const ACCENT0 = '#2E7BFF', INK0 = '#1b2333';
const DEFAULT_NODES = [
  {time: '9:00', label: 'You brief it'},
  {time: '9:02', label: 'It plans'},
  {time: '9:18', label: 'Experts work'},
  {time: '9:41', label: 'You review'},
  {time: '9:45', label: 'Shipped'},
];

export const TimelineTravel: React.FC<{nodes?: {time: string; label: string}[]}> = ({nodes: NODES = DEFAULT_NODES} = {}) => {
  if (!Array.isArray(NODES) || NODES.length < 1 || NODES.length > MAX_STOPS) {
    const got = Array.isArray(NODES) ? NODES.length : typeof NODES;
    throw new Error(
      `TimelineTravel needs 1-${MAX_STOPS} \`nodes\` (got ${got}). ` +
      (Array.isArray(NODES) && NODES.length > MAX_STOPS
        ? `The camera travels the whole rail in one clip; past ${MAX_STOPS} stops it sweeps each milestone past ` +
          'faster than its time and label can be read. Keep the stops the journey turns on, or use a list ' +
          'register for a long schedule.'
        : 'With no stop there is no journey — the rail would be drawn empty. Pass `nodes: [{time, label}]`.'));
  }
  NODES.forEach((n, i) => {
    if (!n || typeof n.label !== 'string' || !n.label.trim()) {
      throw new Error(`TimelineTravel: stop ${i + 1} has no \`label\` (got ${JSON.stringify(n)}). Every stop ` +
        'names the milestone it marks; pass `{time, label}` for each.');
    }
  });
  const dna = useDNA();
  const ACCENT = dna?.accent ?? ACCENT0, INK = dna?.fg ?? INK0, BG = dna?.bg ?? '#f4f6fa';
  const RAIL = dna?.line ?? '#d8dee8', SURF = dna?.surface ?? '#fff', BORD = dna?.line ?? '#c7cedb', DIM = dna?.dim ?? '#9aa3b2';
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const gap = 720, x0 = 520, railY = H / 2;
  const worldW = x0 * 2 + (NODES.length - 1) * gap;
  // camera travels along the rail left→right, from where it always began (the frame's left edge on world 0)
  // to the LAST STOP — and never backwards: a rail too short to travel holds on its end.
  const lastX = x0 + (NODES.length - 1) * gap;
  const camStart = Math.min(W / 2, lastX);
  const camX = lerp(camStart, lastX, easeInOutCubic(seg(t, 0.1, 0.92)));
  const wx = W / 2 - camX;
  const passedX = camX; // nodes to the left of the lens centre are "done"
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* data-bleed: the WORLD travels past the frame — that is the shot. Stops already visited leave to the
          left and stops still ahead wait to the right; both are off-frame on purpose. */}
      <div data-bleed style={{position: 'absolute', left: wx, top: 0, width: worldW, height: H}}>
        {/* the rail: a dim base + a bright progress fill up to the camera */}
        <div style={{position: 'absolute', left: x0, top: railY - 3, width: worldW - x0 * 2, height: 6, background: RAIL, borderRadius: 3}} />
        <div style={{position: 'absolute', left: x0, top: railY - 3, width: Math.max(0, Math.min(worldW - x0 * 2, passedX - x0)), height: 6, background: ACCENT, borderRadius: 3}} />
        {NODES.map((n, i) => {
          const nx = x0 + i * gap;
          const done = passedX > nx - 30;
          const pop = easeOutBack(clamp01((passedX - (nx - 260)) / 240));
          const up = i % 2 === 0;
          return (
            <div key={i}>
              <div style={{position: 'absolute', left: nx - 16, top: railY - 16, width: 32, height: 32, borderRadius: 16,
                background: done ? ACCENT : SURF, border: `3px solid ${done ? ACCENT : BORD}`,
                boxShadow: done ? `0 0 0 8px ${ACCENT}22` : 'none', transform: `scale(${done ? 1.1 : 1})`}} />
              <div style={{position: 'absolute', left: nx - 190, top: up ? railY - 200 : railY + 70, width: 380,
                textAlign: 'center', opacity: clamp01(pop),
                transform: glide(`translateY(${lerp(up ? 20 : -20, 0, clamp01(pop))}px)`, clamp01(pop) !== 1)}}>
                <div style={{font: '800 40px/1 var(--f-body, Inter,system-ui,sans-serif)', color: done ? ACCENT : DIM}}>{n.time}</div>
                <div style={{font: '600 46px/1.15 var(--f-body, Inter,system-ui,sans-serif)', color: INK, marginTop: 12}}>{n.label}</div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export default TimelineTravel;
