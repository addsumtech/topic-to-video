// REACTS — the environment answers the object (spec 2026-11-06 C2).
//
// WHY. The user's example of a frame worth a second look: a 3D character hops across a Mac, and the Dock icon under
// it rises to meet it. The object does not move over a backdrop — it moves THROUGH a world that answers it. Our films
// drew the object and the world as two layers that never touched. An element here declares HOW it answers (`rise`
// like a magnified dock icon, `press` like a key, `light`, `ripple` after a touch) and gets its answer from the
// object's distance to it, per frame: a pure function of the frame, like every other motion in the film.
//
// `d` is the distance from the object to the element in ELEMENT WIDTHS (0 = on it). Every curve is a raised cosine,
// so an answer grows and fades without a step (a step in scale or offset reads as a pop and trips jitter_qa).
export type ReactKind = 'rise' | 'light' | 'press' | 'ripple';
export type Reaction = {dy: number; scale: number; glow: number};
export type ReactOpts = {radius?: number; amount?: number; since?: number};

const NONE: Reaction = {dy: 0, scale: 1, glow: 0};
const bump = (d: number, r: number) => (Math.abs(d) < r ? 0.5 * (1 + Math.cos((Math.PI * Math.abs(d)) / r)) : 0);
const RIPPLE_S = 0.8;          // a touched element settles within this many seconds
const zero = (v: number) => (v === 0 ? 0 : v);   // never hand a -0 to a style

export const react = (kind: ReactKind, d: number, opts: ReactOpts = {}): Reaction => {
  switch (kind) {
    case 'press': {            // a key: down under the object, up as it leaves (element heights)
      const f = bump(d, opts.radius ?? 1);
      return f ? {dy: (opts.amount ?? 0.08) * f, scale: 1, glow: f} : NONE;
    }
    case 'rise': {             // a dock icon: the one under the object lifts and grows most, its neighbours less
      const f = bump(d, opts.radius ?? 2);
      return f ? {dy: zero(-0.35 * f), scale: 1 + (opts.amount ?? 0.5) * f, glow: 0} : NONE;
    }
    case 'light': {
      const f = bump(d, opts.radius ?? 1);
      return f ? {dy: 0, scale: 1, glow: f} : NONE;
    }
    case 'ripple': {           // after a touch: a small decaying wobble, `since` = seconds since the contact
      const s = opts.since ?? -1;
      const f = bump(d, opts.radius ?? 1);
      if (s < 0 || s >= RIPPLE_S || !f) return NONE;
      const a = (opts.amount ?? 0.12) * f * Math.exp(-5 * s) * Math.cos(2 * Math.PI * 4 * s) * (1 - s / RIPPLE_S);
      return {dy: 0, scale: 1 + a, glow: 0};
    }
    default:
      throw new Error(`react: unknown reaction ${JSON.stringify(kind)} — rise | light | press | ripple`);
  }
};

// When the object first reaches each item, from its sampled path (x in the items' units): a beat times its
// sounds and its reactions to these instead of guessing frames. null = it never gets there.
export const contactTimes = (samples: {t: number; x: number}[], items: {x: number; w: number}[]): (number | null)[] =>
  items.map((it) => {
    const hit = samples.find((s) => s.x >= it.x && s.x <= it.x + it.w);
    return hit ? hit.t : null;
  });
