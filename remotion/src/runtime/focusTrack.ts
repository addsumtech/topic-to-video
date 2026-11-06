// FOCUS TRACK — a FilmScreen close-up that follows the action (spec 2026-11-06 E3).
//
// WHY. Launch videos built from screen recordings read well because the close-up follows the clicks and the cursor
// path is smoothed; a FilmScreen close-up was one fixed `region`. A track is the action's centre over the beat —
// [{t: seconds into the beat, x, y: shares of the clip's frame}] — and the region's top-left follows it at the
// region's OWN size, so the magnification never changes and the picture is never drawn past its pixels.
//
// SMOOTH, OR REFUSED. Between two keys the centre moves on a smoothstep (it leaves and arrives at rest). Its fastest
// frame is 1.5 x the distance over the gap; past MAX_STEP of the picture a frame the close-up whips, and a viewer
// loses the very thing it follows — such a track is refused with the gap it would need, never silently slowed.
export type FocusKey = {t: number; x: number; y: number};
export const MAX_STEP = 0.02;           // share of the picture a close-up may travel in one frame

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export const checkFocusTrack = (track: FocusKey[], region: {w: number}, fps: number): void => {
  if (!Array.isArray(track) || track.length < 1) throw new Error('focusTrack: needs at least one {t, x, y} key');
  track.forEach((k, i) => {
    if (!k || ![k.t, k.x, k.y].every(Number.isFinite) || k.x < 0 || k.x > 1 || k.y < 0 || k.y > 1 || k.t < 0) {
      throw new Error(`focusTrack: key ${i} must be {t >= 0, x, y in 0..1}, got ${JSON.stringify(k)}`);
    }
    if (i && !(k.t > track[i - 1].t)) throw new Error(`focusTrack: key ${i}'s t must come after key ${i - 1}'s`);
  });
  if (!(region?.w > 0)) throw new Error('focusTrack: the close-up region needs a width');
  for (let i = 1; i < track.length; i++) {
    const d = Math.hypot(track[i].x - track[i - 1].x, track[i].y - track[i - 1].y);
    const dt = track[i].t - track[i - 1].t;
    const step = (1.5 * d) / (dt * fps);
    if (step > MAX_STEP) {
      throw new Error(`focusTrack: too fast between keys ${i - 1} and ${i} — ${(step * 100).toFixed(1)}% of the picture a ` +
        `frame (limit ${MAX_STEP * 100}%); give them at least ${((1.5 * d) / (MAX_STEP * fps)).toFixed(2)} s`);
    }
  }
};

// The region's top-left at `tSec`, kept inside the picture (its height share `hs`; `yMax` the lowest top allowed).
export const focusAt = (track: FocusKey[], tSec: number, region: {w: number}, hs: number,
  yMax = 1 - hs): {x: number; y: number} => {
  let c: {x: number; y: number};
  if (tSec <= track[0].t) c = track[0];
  else if (tSec >= track[track.length - 1].t) c = track[track.length - 1];
  else {
    const i = track.findIndex((k) => k.t > tSec);
    const a = track[i - 1], b = track[i];
    const u = (tSec - a.t) / (b.t - a.t), e = u * u * (3 - 2 * u);
    c = {x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e};
  }
  return {x: clamp(c.x - region.w / 2, 0, 1 - region.w), y: clamp(c.y - hs / 2, 0, Math.max(0, yMax))};
};
