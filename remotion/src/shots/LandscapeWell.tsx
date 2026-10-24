// SHOT · Landscape Well — the product's own 16:9 picture (a frame it made, a screenshot, its recording) shown in a
// frame of another shape without shrinking it to a strip: a CROP that travels from one named point of interest to the
// next (pan-and-scan, with a map of the whole frame in the corner saying where the crop is), or the whole frame as a
// band with a LOUPE that magnifies each point in turn on a leader from where it sits.
//
// WHAT IT ARGUES. "Look at THIS in the thing itself." A vertical film about a product that makes landscape pictures
// could only show them as small thumbnails on black (bench-launch: five of eight beats a 16:9 frame in a band across a
// 9:16 one; SourceTrace, CaptionCover and RenderCheck each hand-rolled a crop). The crop is the film's: it goes only to
// the points the film names, in its order, each named by its own label — the media, the points and the labels are
// props, and with none the register draws its own skeleton frame, which no film ever sees.
//
// HOW IT MOVES. The well rises in on the first point's framing; then the crop travels — centre eased, zoom
// geometric, so a push in reads at a constant rate — and holds each point for its label's reading time
// (runtime/readingSpec.json: the read-once time first, the rest by must-read time). A ring draws round the point as
// the crop lands; the label rolls to the point's name (runtime/kinetic swap — the hold gate measures each name). In the
// loupe the lens stays put and its content pans, and the leader follows the point along the band.
//
// THE PACE IS IN SECONDS: travels and holds are durations, shrunk on a short beat to floors. The well is the `screen`
// carry anchor, so a container can carry a device's screen into it, and a through-window can push into it.
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, contrastOf, mix} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {readingSeconds, secToT, tToSec, EASES} from '../runtime/kineticCore';

export const DURATION = 240; // 8s — three points, each named and held to its reading time
export const PACE = 'seconds';
export const MAX_POINTS = 6;

const BG_D0 = '#0b0d12', FG_D0 = '#f1f3f7', ACC_D0 = '#ffb547', SURF_D0 = '#151923';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';

export type WellMedia = {
  /** a still in the film's public dir */
  image?: string;
  /** or a recording in the film's public dir, played from `from` s at 1x */
  video?: string;
  from?: number;
  /** its pixel size (the aspect the crop is computed in) */
  w: number; h: number;
  /** shares of the media the CROP must never show — a film's own frame carries its burned caption along the bottom,
   *  and a crop that shows it puts a second subtitle on screen (bench-launch b2). The map still shows the whole. */
  keepOut?: {top?: number; bottom?: number; left?: number; right?: number};
};
export type WellPoint = {
  /** where the point is, as shares of the media's width and height */
  x: number; y: number;
  /** its name — the label the well shows while it holds the point */
  label: string;
  /** how much of the media's WIDTH the crop shows at this point (0.15–1); absent, as close as the well allows
   *  while still covering it */
  zoom?: number;
};

// Placeholder points in the library's placeholder voice, on the register's own skeleton frame.
const DEMO_POINTS: WellPoint[] = [
  {x: 0.2, y: 0.28, label: 'the start'},
  {x: 0.64, y: 0.56, label: 'a detail', zoom: 0.34},
  {x: 0.84, y: 0.8, label: 'the next point', zoom: 0.3},
];
const SKELETON = {w: 1600, h: 900};

/** The skeleton frame a register with no media draws — panels and rules in the DNA's surface, no text, no data. */
const Skeleton: React.FC<{surf: string; line: string; acc: string}> = ({surf, line, acc}) => (
  <svg width={SKELETON.w} height={SKELETON.h} viewBox={`0 0 ${SKELETON.w} ${SKELETON.h}`} style={{display: 'block'}}>
    <rect width={SKELETON.w} height={SKELETON.h} fill={surf} />
    <rect x={0} y={0} width={SKELETON.w} height={86} fill={mix(surf, line, 0.5)} />
    {/* @decor: the skeleton's own panels — no film ever sees them */}
    {[0, 1, 2].map((i) => <rect key={i} x={60 + i * 500} y={150} width={440} height={260} rx={18} fill={line} />)}
    <rect x={60} y={460} width={940} height={380} rx={18} fill={line} />
    <polyline points="110,780 260,690 420,720 580,600 740,640 900,520" fill="none" stroke={acc} strokeWidth={10}
      strokeLinecap="round" strokeLinejoin="round" opacity={0.85} />
    <rect x={1060} y={460} width={480} height={380} rx={18} fill={line} />
    {[0, 1, 2, 3].map((i) => <rect key={i} x={1100} y={510 + i * 80} width={400 - i * 60} height={28} rx={14}
      fill={mix(line, surf, 0.4)} />)}
  </svg>
);

type Region = {x0: number; y0: number; x1: number; y1: number};
/** The crop at a point: centre (media px) and width (media px), clamped so the crop never leaves the region it may
 *  show (the media less its keep-out margins). */
const cropAt = (p: WellPoint, mw: number, mh: number, R: Region, aspect: number) => {
  const rw = R.x1 - R.x0, rh = R.y1 - R.y0;
  const coverW = Math.min(rw, rh * aspect);           // the widest crop that still fills the well
  const cw = Math.min(coverW, Math.max(mw * 0.12, p.zoom !== undefined ? p.zoom * mw : coverW));
  const ch = cw / aspect;
  const cx = Math.min(R.x1 - cw / 2, Math.max(R.x0 + cw / 2, p.x * mw));
  const cy = Math.min(R.y1 - ch / 2, Math.max(R.y0 + ch / 2, p.y * mh));
  return {cx, cy, cw};
};

export const LandscapeWell: React.FC<{
  /** the film's own landscape picture; absent, the register's skeleton frame */
  media?: WellMedia;
  /** the points of interest, in the order the crop visits them (1–6) */
  points?: WellPoint[];
  /** `scan` — a crop that travels between the points; `loupe` — the whole frame and a lens on each point */
  mode?: 'scan' | 'loupe';
  kicker?: string;
  accent?: string;
}> = ({media, points: pointsIn = DEMO_POINTS, mode = 'scan', kicker = 'IN THE FRAME ITSELF', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, fps} = useVideoConfig();
  const spanF = useAnimSpan();
  const PTS = rows<WellPoint>(pointsIn, 'points', 'LandscapeWell');
  if (!PTS.length) throw new Error('LandscapeWell needs at least one point: a crop with nowhere to go is a still.');
  if (PTS.length > MAX_POINTS) {
    throw new Error(`LandscapeWell visits at most ${MAX_POINTS} points, got ${PTS.length}: past that each is gone ` +
      'before its name can be read. Split the beat.');
  }
  PTS.forEach((p, i) => {
    if (!(p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1)) {
      throw new Error(`LandscapeWell: point ${i} is at (${p.x}, ${p.y}) — x and y are shares of the media, 0..1.`);
    }
    if (!String(p.label ?? '').trim()) throw new Error(`LandscapeWell: point ${i} has no label; an unnamed point is a guess.`);
    if (p.zoom !== undefined && !(p.zoom > 0 && p.zoom <= 1)) {
      throw new Error(`LandscapeWell: point ${i}'s zoom ${p.zoom} is not a share of the width in (0, 1].`);
    }
  });
  if (media && !media.image && !media.video) {
    throw new Error('LandscapeWell: `media` needs an `image` or a `video` (in the film\'s public dir).');
  }
  if (media && !(media.w > 0 && media.h > 0)) {
    throw new Error(`LandscapeWell: the media needs its pixel size (w, h), got ${media.w}x${media.h}.`);
  }
  const mw = media ? media.w : SKELETON.w, mh = media ? media.h : SKELETON.h;

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const SURF = dna?.surface ?? SURF_D0;
  const LINE = dna?.surfaceBorder ?? mix(SURF, FG, 0.18);

  // ── geometry ────────────────────────────────────────────────────────────────────────────────────────────
  const U = Math.min(W, H);
  const portrait = W < H, square = Math.abs(W - H) < 2;
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H), zoneH = zoneBot - zoneTop;
  const KICK = Math.ceil(U * 0.026), LABEL = Math.round(U * (portrait ? 0.058 : 0.046));
  const gap = Math.round(U * 0.03);
  const kickH = kicker ? Math.round(KICK * 1.25) + gap : 0;
  const IDX = Math.max(Math.ceil(U * 0.022), Math.round(LABEL * 0.42)), idxH = Math.round(IDX * 1.6);
  const labelH = Math.round(LABEL * 1.3 * 2) + idxH;
  const room = zoneH - kickH - gap - labelH;
  const radius = Math.round(U * 0.016);
  const mAspect = mw / mh;
  // the well: tall in a tall frame (the point of the register), the media's own shape where the frame can hold it
  let wellW: number, wellH: number;
  if (mode === 'loupe') {
    wellW = portrait ? Math.round(W * 0.9) : Math.round(Math.min(W * 0.56, room * 0.95 * mAspect));
    wellH = Math.round(wellW / mAspect);
  } else if (portrait) {
    wellW = Math.round(W * 0.9);
    wellH = Math.round(Math.min(room, wellW * 1.3));
  } else if (square) {
    wellW = Math.round(W * 0.86);
    wellH = Math.round(Math.min(room, wellW * 0.82));
  } else {
    wellH = Math.round(room);
    wellW = Math.round(Math.min(W * 0.84, wellH * mAspect));
  }
  const aspect = wellW / wellH;
  // the loupe, beside the band (landscape) or under it (portrait)
  const lensD = mode === 'loupe' ? Math.round(portrait ? Math.min(W * 0.66, room - wellH - gap * 2)
    : Math.min(room * 0.98, W * 0.36)) : 0;
  const blockH = mode === 'loupe' && portrait ? wellH + gap * 2 + lensD : Math.max(wellH, lensD);
  const top = Math.round(zoneTop + kickH + Math.max(0, (room - blockH) / 2));
  const wellX = mode === 'loupe' && !portrait ? Math.round(W * 0.06) : Math.round((W - wellW) / 2);
  const wellY = mode === 'loupe' && !portrait ? Math.round(top + (blockH - wellH) / 2) : top;
  const lensCX = mode === 'loupe' ? (portrait ? W / 2 : W * 0.06 + wellW + (W * 0.94 - W * 0.06 - wellW) / 2) : 0;
  const lensCY = mode === 'loupe' ? (portrait ? wellY + wellH + gap * 2 + lensD / 2 : top + blockH / 2) : 0;
  const labelY = Math.round((mode === 'loupe' && portrait ? lensCY + lensD / 2 : Math.max(wellY + wellH,
    mode === 'loupe' ? lensCY + lensD / 2 : 0)) + gap);

  // ── the schedule, in seconds ──────────────────────────────────────────────────────────────────────────────
  const n = PTS.length;
  const spanS = Math.max(0.5, spanF / fps);
  const riseS = Math.max(0.35, Math.min(0.7, spanS * 0.1));
  const travelS = n > 1 ? Math.max(0.45, Math.min(0.8, (spanS * 0.24) / (n - 1))) : 0;
  const once = PTS.map((p) => readingSeconds(String(p.label)).once);
  const must = PTS.map((p) => readingSeconds(String(p.label)).must);
  const budget = spanS - riseS - travelS * (n - 1);
  const onceSum = once.reduce((a, b) => a + b, 0), mustSum = must.reduce((a, b) => a + b, 0);
  const hold = budget >= onceSum ? once.map((o, j) => o + ((budget - onceSum) * must[j]) / mustSum)
    : once.map((o) => (Math.max(0, budget) * o) / onceSum);   // too short: the hold gate names what cannot be read
  const arrive: number[] = [riseS];                            // seconds at which the crop lands on point j
  for (let j = 1; j < n; j++) arrive.push(arrive[j - 1] + hold[j - 1] + travelS);
  const sec = tToSec(t, spanF, fps);
  // which leg: before arrive[j] the crop travels from point j-1
  let leg = 0;
  for (let j = 1; j < n; j++) if (sec >= arrive[j] - travelS) leg = j;
  const pIn = leg === 0 ? 1 : EASES.inOut(clamp01((sec - (arrive[leg] - travelS)) / Math.max(1e-6, travelS)));
  const lerp = (a: number, b: number, k: number) => a + (b - a) * k;

  // the region a crop may show: the media less its keep-out margins (each a share, together under 80%)
  const ko = media?.keepOut ?? {};
  const kv = (v: number | undefined, k: string) => {
    const x = v ?? 0;
    if (!(x >= 0 && x < 0.8)) throw new Error(`LandscapeWell: keepOut.${k} ${v} is not a share in [0, 0.8).`);
    return x;
  };
  const R: Region = {x0: kv(ko.left, 'left') * mw, x1: (1 - kv(ko.right, 'right')) * mw, y0: kv(ko.top, 'top') * mh,
    y1: (1 - kv(ko.bottom, 'bottom')) * mh};
  if (R.x1 - R.x0 < mw * 0.2 || R.y1 - R.y0 < mh * 0.2) {
    throw new Error('LandscapeWell: keepOut leaves less than a fifth of the media to crop from.');
  }
  const crops = PTS.map((p) => cropAt(p, mw, mh, R, mode === 'loupe' ? 1 : aspect));
  const cA = crops[Math.max(0, leg - 1)], cB = crops[leg];
  const cur = leg === 0 ? cB : {cx: lerp(cA.cx, cB.cx, pIn), cy: lerp(cA.cy, cB.cy, pIn),
    cw: Math.exp(lerp(Math.log(cA.cw), Math.log(cB.cw), pIn))};
  // THE PICTURE IS THERE ON THE BEAT'S FIRST FRAME. Faded up from nothing, the well was an empty ground for the whole
  // seam in — a through-window into this beat looked through its letters at black. The media is drawn from the first
  // frame and only SETTLES (a 3.5% scale); the ring, the map, the lens, the leader and the label arrive with `rise`.
  const rise = easeOutCubic(clamp01(seg(t, 0.06, 0.06 + secToT(riseS, spanF, fps))));

  // ── the labels: one slot that rolls to each point's name as the crop lands on it ──────────────────────────
  const names = PTS.map((p) => String(p.label));
  const labW = Math.round(Math.min(W * 0.9, wellW));
  const lab = useKinetic({alts: names, w: labW, nowrap: false, fit: 'box', maxLines: 2,
    h: labelH - idxH, align: 'left', wrap: 'balance', font: {family: DISPLAY, weight: 600, size: LABEL,
      minSize: Math.ceil(U * 0.032), lineHeight: 1.18, tracking: -0.01}});
  const kick = useKinetic({text: kicker || ' ', w: wellW, nowrap: true, fit: 'box', align: 'left',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});
  const swapT = arrive.map((a, j) => (j === 0 ? 0 : 0.06 + secToT(a - travelS * 0.35, spanF, fps)));
  let named = 0;
  for (let j = 1; j < n; j++) if (t >= swapT[j]) named = j;

  // the media, drawn at its natural size and transformed (a still, a recording, or the skeleton)
  const mediaEl = (key: string) => media?.video ? (
    <Sequence key={key} from={0} layout="none">
      <OffthreadVideo src={staticFile(media.video)} muted trimBefore={Math.round((media.from ?? 0) * fps)}
        style={{position: 'absolute', left: 0, top: 0, width: mw, height: mh}} />
    </Sequence>
  ) : media?.image ? (
    <Img key={key} src={staticFile(media.image)} style={{position: 'absolute', left: 0, top: 0, width: mw, height: mh}} />
  ) : <div key={key} style={{position: 'absolute', left: 0, top: 0}}><Skeleton surf={SURF} line={LINE} acc={ACC} /></div>;

  const ringAt = (cx: number, cy: number, r: number, k: number) => (
    <circle cx={cx} cy={cy} r={r} fill="none" stroke={ACC} strokeWidth={Math.max(2, U * 0.004)}
      strokeDasharray={`${2 * Math.PI * r}`} strokeDashoffset={`${2 * Math.PI * r * (1 - k)}`}
      transform={`rotate(-90 ${cx} ${cy})`} />
  );
  // the ring draws as the crop lands, and stays while it holds
  const landK = leg === 0 ? easeOutCubic(clamp01((sec - riseS * 0.6) / 0.5)) : easeOutCubic(clamp01((pIn - 0.75) / 0.25));

  let body: React.ReactNode;
  if (mode === 'scan') {
    const s = wellW / cur.cw;
    const tx = wellW / 2 - cur.cx * s, ty = wellH / 2 - cur.cy * s;
    const P = PTS[leg];
    const px = tx + P.x * mw * s, py = ty + P.y * mh * s;
    // the map of the whole frame, top-left inside the well, with the crop's rectangle on it
    const mapW = Math.round(wellW * (portrait ? 0.36 : 0.24)), mapH = Math.round(mapW / mAspect);
    const ms = mapW / mw, inset = Math.round(U * 0.02);
    const ch = cur.cw / aspect;
    body = (
      <div data-carry="screen" data-carry-radius={String(radius)} style={{position: 'absolute', left: wellX, top: wellY,
        width: wellW, height: wellH, overflow: 'hidden', borderRadius: radius, background: SURF,
        boxShadow: `0 0 0 1px ${LINE}`, transform: `scale(${(1.035 - 0.035 * rise).toFixed(5)})`}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: mw, height: mh, transformOrigin: '0 0',
          transform: `translate(${tx.toFixed(3)}px, ${ty.toFixed(3)}px) scale(${s.toFixed(5)})`}}>{mediaEl('m')}</div>
        <svg width={wellW} height={wellH} style={{position: 'absolute', left: 0, top: 0}}>
          {ringAt(px, py, Math.round(U * 0.05), landK)}
        </svg>
        <div style={{position: 'absolute', left: inset, top: inset, width: mapW, height: mapH, overflow: 'hidden',
          borderRadius: Math.round(radius * 0.6), boxShadow: `0 0 0 1px ${mix(FG, BG, 0.5)}, 0 6px 18px rgba(0,0,0,0.35)`}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: mw, height: mh, transformOrigin: '0 0',
            transform: `scale(${ms.toFixed(5)})`}}>{mediaEl('map')}</div>
          <div style={{position: 'absolute', left: (cur.cx - cur.cw / 2) * ms, top: (cur.cy - ch / 2) * ms,
            width: cur.cw * ms, height: ch * ms, boxShadow: `0 0 0 2px ${ACC}`, borderRadius: 2}} />
        </div>
      </div>
    );
  } else {
    // the band: the whole frame; the lens: the media at `mag` times the band's scale, centred on the point
    const bs = wellW / mw;
    const mag = Math.max(2.2, Math.min(5, (lensD / (cur.cw * bs)) || 3));
    const ls = bs * mag;
    const P = PTS[leg];
    const bx = wellX + (leg === 0 ? P.x : lerp(PTS[leg - 1].x, P.x, pIn)) * wellW;
    const by = wellY + (leg === 0 ? P.y : lerp(PTS[leg - 1].y, P.y, pIn)) * wellH;
    const lx = (leg === 0 ? P.x : lerp(PTS[leg - 1].x, P.x, pIn)) * mw;
    const ly = (leg === 0 ? P.y : lerp(PTS[leg - 1].y, P.y, pIn)) * mh;
    const ringR = Math.max(U * 0.025, lensD / mag / 2);
    // the leader: from the ring on the band to the lens's rim, along the line between their centres
    const dx = lensCX - bx, dy = lensCY - by, dl = Math.hypot(dx, dy) || 1;
    const x1 = bx + (dx / dl) * ringR, y1 = by + (dy / dl) * ringR;
    const x2 = lensCX - (dx / dl) * (lensD / 2), y2 = lensCY - (dy / dl) * (lensD / 2);
    body = (
      <>
        <div data-carry="screen" data-carry-radius={String(radius)} style={{position: 'absolute', left: wellX, top: wellY,
          width: wellW, height: wellH, overflow: 'hidden', borderRadius: radius, boxShadow: `0 0 0 1px ${LINE}`}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: mw, height: mh, transformOrigin: '0 0',
            transform: `scale(${bs.toFixed(5)})`}}>{mediaEl('band')}</div>
        </div>
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, opacity: rise}}>
          {ringAt(bx, by, ringR, Math.max(landK, leg > 0 ? 1 : 0))}
          <line x1={x1} y1={y1} x2={lerp(x1, x2, rise)} y2={lerp(y1, y2, rise)} stroke={ACC}
            strokeWidth={Math.max(2, U * 0.003)} />
        </svg>
        <div style={{position: 'absolute', left: lensCX - lensD / 2, top: lensCY - lensD / 2, width: lensD, height: lensD,
          borderRadius: '50%', overflow: 'hidden', background: SURF, opacity: rise,
          transform: `scale(${(0.9 + 0.1 * rise).toFixed(4)})`,
          boxShadow: `0 0 0 ${Math.max(3, Math.round(U * 0.005))}px ${ACC}, 0 18px 50px rgba(0,0,0,0.45)`}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: mw, height: mh, transformOrigin: '0 0',
            transform: `translate(${(lensD / 2 - lx * ls).toFixed(3)}px, ${(lensD / 2 - ly * ls).toFixed(3)}px) ` +
              `scale(${ls.toFixed(5)})`}}>{mediaEl('lens')}</div>
        </div>
      </>
    );
  }
  const labelX = mode === 'loupe' && !portrait ? Math.round(lensCX - Math.min(W * 0.9, wellW) / 2) : wellX;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={wellX} y={zoneTop + Math.max(0, (room - blockH) / 2)} color={ACC} read={false}
          id="kicker" motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.06, stagger: 0.03,
            dur: 0.45, ease: 'power3', cueKeys: ['kicker'], until: 0.36}}} />
      ) : kick.anchor}
      {body}
      {/* the point's index over its name — both change on the label's own swap, as the crop lands */}
      <div style={{position: 'absolute', left: labelX, top: labelY, fontFamily: MONO, fontSize: IDX, lineHeight: 1.2,
        fontWeight: 600, color: ACC, letterSpacing: '0.12em', opacity: rise, whiteSpace: 'nowrap'}}>
        {String(named + 1).padStart(2, '0')} / {String(n).padStart(2, '0')}
      </div>
      <KineticText k={lab} x={labelX} y={labelY + idxH} color={FG} id="labels"
        motion={{from: {opacity: 0, y: 0.3}, enter: {by: 'word', at: 0.06 + secToT(riseS * 0.5, spanF, fps),
          stagger: 0.04, dur: 0.45, ease: 'power3', until: 0.5},
          swap: {mode: 'roll', first: swapT[1] ?? 0.5, last: swapT[n - 1] ?? 0.5, times: swapT, turn: 0.32,
            stagger: 0.02, cueKeys: PTS.map((_, i) => `points.${i}.label`), seed: 3}}} />
    </AbsoluteFill>
  );
};
export default LandscapeWell;
