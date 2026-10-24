// SHOT · Globe Focus — WHERE: the planet turns the short way round to the place the film names, the camera pushes in
// until that place fills the frame, the region lights in the accent, and the film's own points land on it named.
//
// WHAT IT ARGUES. Location, at the scale that makes it legible: a viewer is first shown the whole Earth (so they know
// which side of it they are on), then carried to the place without a cut, so its position relative to everything else
// is something they WATCHED rather than were told. Not for a list of places with no geography between them (a list
// register), nor for routes between places (FlightArcs), nor an imagined/engraved plate (MapPlate).
//
// WHAT COMES FROM WHERE. The coastlines and country outlines are Natural Earth's (runtime/geo.ts); the regions are
// named by the film as Natural Earth names them; every mark's position is the film's sourced lon/lat. Nothing here
// looks a city up by name, and a region the atlas does not carry throws with the names it does.
//
// THE CAMERA. One continuous move, two channels: the turn (longitude the short way round, runtime/geo wrapDelta)
// eases over the first half; the push-in starts after the turn is under way and moves the radius EXPONENTIALLY so the
// zoom reads at one rate. The view is decided from the settled frame — the regions' main bodies (an overseas
// territory is lit but not chased) and every mark — and the coastline resolution is chosen once from the final
// radius, so detail never pops mid-move.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, easeOutBack, life} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, TITLE_Y} from '../runtime/layout';
import {useDNA, readableOn, dimOn, mix} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {hasCJK} from '../runtime/cjkType';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {Earth} from '../runtime/earth';
import {findRegion, regionFrame, lonLatOf, LonLat, GlobeView, lerpView, radiusFor, resFor, orthoXY, arcDeg,
  orthoProjection, geoPath, geoContains, pointsFrame} from '../runtime/geo';
import {placeLabels, Rect} from '../runtime/labelPlace';
import {useGlide} from '../runtime/glide';
import {useLabelWidths} from '../runtime/labelWidths';

export const DURATION = 180; // 6s
export const MAX_REGIONS = 6, MAX_MARKS = 6;

type RegionIn = {name?: string; label?: string};
type MarkIn = {label?: string; lon?: number; lat?: number};

const BG_D0 = '#060a12', FG_D0 = '#eef2f8', DIM_D0 = '#8d97aa', ACC_D0 = '#4fd1c5', ACC2_D0 = '#f2b84b';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy in the library's placeholder voice — it describes the register, states nothing about a place.
// The demo's one region is only a shape to aim at; its label says so.
const DEMO_REGIONS: RegionIn[] = [{name: 'Brazil', label: 'the region the film names'}];

export const GlobeFocus: React.FC<{
  /** one line in the title band */
  title?: string;
  /** 1-6 regions to light, by Natural Earth name or ISO 3166-1 numeric code; `label` is what the frame prints */
  regions?: RegionIn[];
  /** 0-6 points on the region, each the film's sourced `lon`/`lat` */
  marks?: MarkIn[];
  /** where the turn starts from (staging, not a claim); default: a quarter-turn west of the aim */
  from?: {lon?: number; lat?: number};
  /** how much of the content zone the settled view gives the region, 0.3-0.9 */
  zoom?: number;
  /** a source or reading line under the globe */
  note?: string;
  accent?: string;
}> = ({title = '', regions: regionsIn = DEMO_REGIONS, marks: marksIn, from, zoom = 0.62, note = '', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H, durationInFrames: DUR, fps} = useVideoConfig();
  const S = 'GlobeFocus';

  // ── the film's places ────────────────────────────────────────────────────────────────────────────────
  // the demo region only when the film passed NOTHING: a film that names marks and no region lights no region
  const REG = rows<RegionIn>(regionsIn === DEMO_REGIONS && marksIn != null ? [] : regionsIn, 'regions', S);
  const MARKS = rows<MarkIn>(marksIn, 'marks', S);
  if (REG.length > MAX_REGIONS) throw new Error(`${S}: at most ${MAX_REGIONS} regions (got ${REG.length}); past that it is a choropleth, not a place.`);
  if (MARKS.length > MAX_MARKS) throw new Error(`${S}: at most ${MAX_MARKS} marks (got ${MARKS.length}); more cannot all be named at one view.`);
  if (!REG.length && !MARKS.length) throw new Error(`${S}: needs at least one region or one mark — a globe with nothing on it argues nothing.`);
  if (!(zoom >= 0.3 && zoom <= 0.9)) throw new Error(`${S}: \`zoom\` is the share of the content zone the region fills, 0.3-0.9 (got ${zoom}).`);
  const regions = REG.map((r) => ({...findRegion(r?.name, S), label: String(r?.label ?? r?.name ?? '').trim()}));
  const marks = MARKS.map((m, i) => {
    const label = String(m?.label ?? '').trim();
    if (!label) throw new Error(`${S}: mark ${i + 1} has no \`label\` — a point the film does not name is a point it has not explained.`);
    return {label, ll: lonLatOf(m, `mark ${i + 1} ("${label}")`, S)};
  });

  // ── palette ──────────────────────────────────────────────────────────────────────────────────────────
  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);
  const ACC = accIn ?? dna?.accent ?? ACC_D0;
  const MARK = dna?.accent2 ?? ACC2_D0;
  const CHIP = mix(BG, '#000000', 0.25);
  const CHIP_INK = readableOn(CHIP, FG, '#ffffff', '#0b0f17');

  // ── the settled view, decided once ───────────────────────────────────────────────────────────────────
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const noteH = note ? Math.round(U * 0.05) : 0;
  const cx = W / 2, cy = (zTop + zBot - noteH) / 2;
  const zoneMin = Math.min(W * 0.9, zBot - zTop - noteH);
  const rFull = 0.47 * zoneMin;
  let aim: LonLat, reach: number;
  if (regions.length) {
    const fr = regionFrame(regions.map((r) => r.f50));
    aim = fr.center;
    reach = Math.max(fr.reach, ...marks.map((m) => arcDeg(m.ll, aim)));
  } else {
    const pf = pointsFrame(marks.map((m) => m.ll));
    aim = pf.center; reach = pf.reach;
  }
  if (reach > 80) {
    throw new Error(`${S}: what the film names spans ${reach.toFixed(0)}° of arc from its centre — more than one side of a ` +
      'globe can show. Split the beat, or show it on FlightArcs\' flat view.');
  }
  const R1 = radiusFor(reach * 1.08, 0.5 * zoom * zoneMin, rFull, rFull * 60);
  const v1: GlobeView = {lon0: aim[0], lat0: aim[1], R: R1, cx, cy};
  const fromLL = from && Number.isFinite(from.lon) && Number.isFinite(from.lat) ? [from.lon!, from.lat!] : [aim[0] - 80, aim[1] * 0.35];
  const v0: GlobeView = {lon0: fromLL[0], lat0: fromLL[1], R: rFull * 0.94, cx, cy};
  const res = resFor(R1, W, H);

  // the camera: turn first, push in once the turn is under way (exponential radius, runtime/geo lerpView)
  const pTurn = easeInOutCubic(seg(t, 0.02, 0.5));
  const pPush = easeInOutCubic(seg(t, 0.2, 0.6));
  const turned = lerpView(v0, v1, pTurn);
  const view: GlobeView = {...turned, R: v0.R * Math.pow(v1.R / v0.R, pPush)};
  const show = easeOutCubic(seg(t, 0, 0.1));
  const lit = easeOutCubic(seg(t, 0.48, 0.64));

  // ── labels, placed once on the settled view ──────────────────────────────────────────────────────────
  const regPx = Math.round(U * 0.03), markPx = Math.round(U * 0.025);
  const padX = Math.round(U * 0.012), padY = Math.round(U * 0.007);
  const proj1 = orthoProjection(v1, W, H);
  const path1 = geoPath(proj1);
  const box: Rect = {x0: W * 0.04, y0: zTop, x1: W * 0.96, y1: zBot - noteH};
  // the chips are sized from the MEASURED label (runtime/labelWidths); until it lands nothing is placed
  const regW = useLabelWidths(regions.map((r) => r.label || ' '), BODY, 600, regPx);
  const markW = useLabelWidths(marks.map((m) => m.label), BODY, 600, markPx);
  const measured = Boolean(regW.widths && markW.widths);
  const chipOf = (w: number, px: number) => ({w: Math.ceil(w * 1.04) + padX * 2, h: Math.round(px * 1.2) + padY * 2});
  const dotR = Math.round(U * 0.008);
  const markPts = marks.map((m) => orthoXY(m.ll[0], m.ll[1], v1));
  const regionLabels = regions.map((r, ri) => {
    const [[bx0, by0], [bx1, by1]] = path1.bounds(r.f50);
    const c = orthoXY(...(regionFrame([r.f50]).center), v1);
    const sz = chipOf(regW.widths?.[ri] ?? 0, regPx);
    // a region big enough on screen carries its label INSIDE itself — when the whole chip lies on the region's own
    // land and covers none of the film's points. Its bounding box is not the test: Japan's box is mostly sea, and a
    // chip centred in it sat on the Pacific and over both cities. Otherwise it is labelled beside the region.
    const rect = {x0: c.x - sz.w / 2, y0: c.y - sz.h / 2, x1: c.x + sz.w / 2, y1: c.y + sz.h / 2};
    const probes: [number, number][] = [[rect.x0, rect.y0], [rect.x1, rect.y0], [rect.x0, rect.y1], [rect.x1, rect.y1], [c.x, c.y]];
    const onLand = probes.every(([x, y]) => { const ll = proj1.invert?.([x, y]); return !!ll && geoContains(r.f50, ll); });
    const clearOfMarks = markPts.every((m) => m.x < rect.x0 - dotR * 2 || m.x > rect.x1 + dotR * 2 || m.y < rect.y0 - dotR * 2 || m.y > rect.y1 + dotR * 2);
    const inside = (bx1 - bx0) > sz.w * 1.25 && (by1 - by0) > sz.h * 2.2 && onLand && clearOfMarks;
    return {r, c, sz, inside};
  });
  const insideRects: Rect[] = regionLabels.filter((q) => q.inside && q.r.label)
    .map((q) => ({x0: q.c.x - q.sz.w / 2, y0: q.c.y - q.sz.h / 2, x1: q.c.x + q.sz.w / 2, y1: q.c.y + q.sz.h / 2}));
  const reqs = [
    ...regionLabels.filter((q) => !q.inside && q.r.label).map((q) => ({x: q.c.x, y: q.c.y, ...q.sz, text: q.r.label, r: dotR})),
    ...marks.map((m, i) => ({x: markPts[i].x, y: markPts[i].y, ...chipOf(markW.widths?.[i] ?? 0, markPx), text: m.label, r: dotR * 1.6})),
  ];
  const placed = measured ? placeLabels(reqs, box, Math.round(U * 0.014), insideRects, S) : [];
  const outside = regionLabels.filter((q) => !q.inside && q.r.label);

  // the title arrives with the planet; the note under the globe after the region lights
  const titleK = useKinetic({text: title || ' ', w: Math.round(W * 0.84), nowrap: true, fit: 'box',
    font: {family: DISPLAY, weight: 640, size: Math.round(U * 0.046), minSize: Math.round(U * 0.03), lineHeight: 1.1,
      tracking: hasCJK(title) ? 0 : -0.015}});
  const noteK = useKinetic({text: note || ' ', w: Math.round(W * 0.84), fit: 'box', maxLines: 2, h: noteH,
    font: {family: MONO, weight: 500, size: Math.round(U * 0.021), minSize: Math.round(U * 0.017), lineHeight: 1.3}});

  const breathe = life(t, DUR, fps, 3.2);
  const chipStyle = (px: number, a: number, x: number, y: number, w: number, h: number): React.CSSProperties => ({
    position: 'absolute', left: 0, top: 0, width: w, height: h, transform: glide(`translate(${x}px, ${y}px)`, a < 1),
    opacity: clamp01(a), display: 'flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box',
    padding: `${padY}px ${padX}px`, borderRadius: Math.round(px * 0.35), background: `${CHIP}d9`,
    border: `1px solid ${mix(CHIP, FG, 0.22)}`, color: CHIP_INK, whiteSpace: 'nowrap',
    font: `600 ${px}px/1.2 ${BODY}`,
  });

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 110% at 50% 40%, ${mix(BG, ACC, 0.06)}, ${BG} 70%)`}}>
      <Earth uid="globefocus" W={W} H={H} res={res} view={view} show={show} lit={lit} regions={regions.map((r) => (res === '50m' ? r.f50 : r.f110))}
        ink={{bg: BG, fg: FG, accent: ACC}} />
      {/* leaders from a region to a label set beside it */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {placed.map((p, i) => {
          const a = easeOutCubic(seg(t, 0.6 + i * 0.04, 0.72 + i * 0.04));
          const lx = Math.max(p.x0, Math.min(p.ax, p.x1)), ly = Math.max(p.y0, Math.min(p.ay, p.y1));
          return p.leader || i < outside.length ? (
            <line key={i} x1={p.ax} y1={p.ay} x2={lerpN(p.ax, lx, a)} y2={lerpN(p.ay, ly, a)} stroke={FG} strokeOpacity={0.55} strokeWidth={1.4} />
          ) : null;
        })}
        {marks.map((m, i) => {
          const p = orthoXY(m.ll[0], m.ll[1], view);
          const a = easeOutBack(seg(t, 0.58 + i * 0.04, 0.7 + i * 0.04));
          if (!p.vis || p.z < 0) return null;
          return (
            <g key={i} opacity={clamp01(a)}>
              <circle cx={p.x} cy={p.y} r={dotR * (1.6 + 1.4 * breathe)} fill="none" stroke={MARK} strokeOpacity={0.35 * (1 - breathe) + 0.15} strokeWidth={1.5} />
              <circle cx={p.x} cy={p.y} r={dotR * Math.max(0, a)} fill={MARK} stroke={BG} strokeWidth={2} />
            </g>
          );
        })}
      </svg>
      {regW.anchor}{markW.anchor}
      {measured && regionLabels.filter((q) => q.inside && q.r.label).map((q, i) => {
        const a = easeOutCubic(seg(t, 0.6 + i * 0.04, 0.72 + i * 0.04));
        return <div key={`in${i}`} style={chipStyle(regPx, a, q.c.x - q.sz.w / 2, q.c.y - q.sz.h / 2, q.sz.w, q.sz.h)}>{q.r.label}</div>;
      })}
      {placed.map((p, i) => {
        const a = easeOutCubic(seg(t, 0.62 + i * 0.04, 0.74 + i * 0.04));
        const text = reqs[i].text, px = i < outside.length ? regPx : markPx;
        return <div key={`pl${i}`} style={chipStyle(px, a, p.x0, p.y0, p.x1 - p.x0, p.y1 - p.y0)}>{text}</div>;
      })}
      {title ? (
        <KineticText k={titleK} x={Math.round(W * 0.08)} y={TITLE_Y} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.04}, enter: {by: 'line', at: 0.03, stagger: 0.1, dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.4}}} />
      ) : titleK.anchor}
      {note ? (
        <KineticText k={noteK} x={Math.round(W * 0.08)} y={zBot - noteH} color={DIM} id="note"
          motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'word', at: 0.66, stagger: 0.03, dur: 0.5, ease: 'power3', cueKeys: ['note'], until: 0.84}}} />
      ) : noteK.anchor}
    </AbsoluteFill>
  );
};
const lerpN = (a: number, b: number, p: number) => a + (b - a) * p;
export default GlobeFocus;
