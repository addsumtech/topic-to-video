// A BEAT'S TIME AS GRAMMAR — the film frame mapped to the frame the register draws. Pure (tests/test_time_grammar.py).
//
// Three moves, each named by what it says:
//   hits    — HIT-STOP. Each impact freezes the drawing for `hold` frames (2 by default), the way a blow lands in a
//             fighting game or a stamp hits paper: the freeze is what gives the moment its weight.
//   freeze  — A LOOK. The drawing eases to a stop, holds for `hold` seconds, and eases off again: a moment held while
//             the voice points at it.
//   sakuga  — HELD DRAWINGS THAT BREAK INTO ONES. Up to `until` the drawing moves on 2s or 3s; from it, on every
//             frame — the climax arriving with a change of texture as well as of content.
// The peer library (video-shotcraft) cuts time this way in five shots; this tier could only WARP a beat's clock
// (Film.tsx BeatClock, a monotone map derived for sync) or step a whole styled film.
//
// EVERY PAUSE IS REPAID. A hold leaves the register behind the film; the frames after it run the register a little
// fast until it has caught up, so past a short window the map is the identity again. That is what keeps the beat in
// sync: an item the voice names a second after a hit still reads on its word. The repay never runs faster than
// MAX_REPAY_SLOPE, so a catch-up never reads as a fast-forward.
//
// Times are SECONDS inside the beat (render_remotion resolves `{cue: "..."}` to them); frames are the beat's own.

export type TimeSpec = {
  hits?: number[];
  /** frames each hit's impact frame is held past its own (2 by default) */
  hold?: number;
  freeze?: {at: number; hold: number};
  sakuga?: {until: number; every: number};
};

export const HIT_HOLD = 2;
export const MAX_HIT_HOLD = 4;
export const MAX_HITS = 4;
export const MAX_FREEZE_S = 1.5;
/** frames to ease into, and out of, a freeze */
export const FREEZE_EASE = 6;
export const MAX_REPAY_SLOPE = 2;

/** A pause that ends at film frame `end` with the register at `held`, repaid over `R` frames: the register frame. */
const repay = (f: number, end: number, held: number) => {
  const lag = end - held;
  const R = Math.max(1, Math.ceil(lag / (MAX_REPAY_SLOPE - 1)));
  if (f >= end + R) return f;
  return held + (f - end) * ((R + lag) / R);
};

// the impact frame `h` is shown on frames h .. h + hold — held for `hold` frames past its own
const hitFrame = (f: number, h: number, hold: number) => {
  if (f <= h) return f;
  if (f <= h + hold) return h;
  return repay(f, h + hold, h);
};

const freezeFrame = (f: number, a: number, hold: number) => {
  const E = FREEZE_EASE;
  if (f < a - E) return f;
  if (f < a) {                       // slowing: slope 1 -> 0
    const u = (f - (a - E)) / E;
    return a - E + E * (u - u * u / 2);
  }
  const c = a - E / 2;               // where the drawing stops
  if (f < a + hold) return c;
  if (f < a + hold + E) {            // speeding up again: slope 0 -> 1
    const v = (f - (a + hold)) / E;
    return c + E * (v * v / 2);
  }
  return repay(f, a + hold + E, c + E / 2);
};

export const grammarFrame = (f: number, spec: TimeSpec | null | undefined, fps: number): number => {
  if (!spec) return f;
  let g = f;
  if (spec.freeze) g = freezeFrame(g, Math.round(spec.freeze.at * fps), Math.round(spec.freeze.hold * fps));
  const hold = spec.hold ?? HIT_HOLD;
  // later hits first, so an earlier hit's repay sees a clock the later one has not yet bent
  for (const h of [...(spec.hits ?? [])].sort((a, b) => b - a)) g = hitFrame(g, Math.round(h * fps), hold);
  if (spec.sakuga && f < Math.round(spec.sakuga.until * fps)) {
    const e = spec.sakuga.every;
    g = Math.floor(g / e) * e;
  }
  return g;
};

/** Refuses a spec that cannot be what was meant: a hold long enough to read as a stall, a stepping that is not
 *  drawn animation's, a time outside the beat or inside the seams' held edges. */
export const checkTime = (spec: TimeSpec, where: string, durS: number, fps: number, padF = 12) => {
  const inBeat = (s: number, what: string) => {
    if (!(typeof s === 'number' && isFinite(s))) throw new Error(`${where}: time ${what} is not a number (${s})`);
    const fr = s * fps;
    if (fr < padF || fr > durS * fps - padF) {
      throw new Error(`${where}: time ${what} at ${s.toFixed(2)} s falls in the beat's held edges (the first and last ` +
        `${padF} frames, where a seam runs) or outside the beat — move it inside`);
    }
  };
  const hold = spec.hold ?? HIT_HOLD;
  if (spec.hits) {
    if (spec.hits.length > MAX_HITS) throw new Error(`${where}: ${spec.hits.length} hits — at most ${MAX_HITS}; more is a stutter, not emphasis`);
    if (!(Number.isInteger(hold) && hold >= 1 && hold <= MAX_HIT_HOLD)) {
      throw new Error(`${where}: a hit holds ${hold} frames — 1..${MAX_HIT_HOLD} (2 is the default); longer is a freeze, not a hit`);
    }
    spec.hits.forEach((h, k) => inBeat(h, `hits[${k}]`));
  }
  if (spec.freeze) {
    if (!(spec.freeze.hold > 0 && spec.freeze.hold <= MAX_FREEZE_S)) {
      throw new Error(`${where}: a freeze holds ${spec.freeze.hold} s — up to ${MAX_FREEZE_S} s; past that the beat looks stuck`);
    }
    inBeat(spec.freeze.at, 'freeze.at');
    inBeat(spec.freeze.at + spec.freeze.hold, 'freeze.at + hold');
  }
  if (spec.sakuga) {
    if (spec.sakuga.every !== 2 && spec.sakuga.every !== 3) {
      throw new Error(`${where}: sakuga steps every ${spec.sakuga.every} frames — drawn animation is on 2s or 3s`);
    }
    inBeat(spec.sakuga.until, 'sakuga.until');
  }
};
