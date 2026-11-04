// SHOT-OWNED SOUND — a register declares the sounds its own picture makes (a needle's click as it lands on a station,
// a stamp's strike, a swell under a curtain brightening), and the mix plays them ON the frame the picture does it.
//
// WHY. Until this file the SFX bed was planned only from the EDIT — whooshes on marked seams, a focus tick on an
// arrival, and a closing riser -> impact -> sparkle — and only a stage run's cursor could click on its own. bench-rams:
// "No shot can trigger its own sounds (needle clicks, pencil strikes)". bench-aurora: "a film-local shot cannot say
// 'a low swell on my release flash at t = 0.62'".
//
// HOW IT IS READ — a STATIC declaration, not a census of rendered frames. A register exports
//
//     export const SOUNDS = [
//       {kind: 'strike', at: 0.72},                          // at a point of its own clock (useT's t, 0..1)
//       {kind: 'swell', at: 'surgeAt'},                      // at the t a PROP holds — no prop, no sound (and the
//                                                            //   prop has no default: no prop, no surge either)
//       {kind: 'tick', each: 'stations', at: 0.3, to: 0.7},  // one per item of a list prop, evenly from `at` to `to`
//     ] as const;
//
// and scripts/shot_sounds.py reads that literal, resolves it against the beat's own (cue-resolved) props, maps each t
// to the beat frame useT reaches it on (the same pad arithmetic as optics.useFrameAtT) and through the beat's sync
// warp to film time, and hands sfx.plan_cues the events. Chosen over a DOM census because: it needs no render (a
// census of a film is a full extra pass; the segment cache would also skip beats it reused); it is checked before
// anything renders (an unknown kind is a validate error, not a silent no-op); and it cannot drift from the picture,
// because the register times its picture FROM the same declaration (`soundTs` below) — one definition, as SEAM_PEAK
// is for the seams.
//
// THE GRAMMAR IS A LITERAL ON PURPOSE: numbers, strings and the keys below, nothing computed. Python reads it with a
// literal parser; an expression in it is refused there, loudly, rather than evaluated wrongly.

/** The sounds a picture can make. Each is synthesised by scripts/sfx.py `cue()` (no samples); a kind added here and
 *  not there is a test failure (tests/test_sfx.py). */
import {chunkTimes, typeChunks} from './gesture';
export const SOUND_KINDS = ['click', 'tick', 'strike', 'whoosh', 'chime', 'swell', 'key'] as const;
export type SoundKind = (typeof SOUND_KINDS)[number];

export type SoundDecl = {
  kind: SoundKind;
  /** a point on the register's clock (0..1), or the NAME of a prop holding one (not with `step`) */
  at?: number | string;
  /** a gesture script in `props.steps` (DeviceDemo, timed by scripts/device_script.prepare): 'type' sounds once per
   *  chunk of every `type` step, where gesture.typedCount lands it; 'tap' once per `tap` / `click` step, on its `ta` */
  step?: 'type' | 'tap';
  /** with `each`: the last item's point; items are spread evenly from `at` to `to` */
  to?: number;
  /** a list prop: one sound per item */
  each?: string;
  /** a STRING prop the register types: one sound per character, where that character appears on the typing curve
   *  from `at` to `to` (the register draws floor(n * ease(u)) characters — gesture's typing, CommandSummon's) */
  type?: string;
  /** with `type`: the typing curve — 'linear' (default) or 'out-cubic' */
  ease?: 'linear' | 'out-cubic';
  /** with `type`: how the register turns the curve into a count — 'floor' (default, floor(n * ease(u))) or 'round'
   *  (Math.round, as TermFrame and TermTable draw it: character i shows half a character earlier, at (i - 0.5) / n) */
  draw?: 'floor' | 'round';
  /** relative level, (0, 1] — the mix sets the absolute one under the voice */
  gain?: number;
};

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** Every t at which `decl` sounds, given the beat's props — the times the register must ALSO time its picture by.
 *  [] when a prop-named point is absent (no event). Throws on a malformed declaration (E9). */
export const soundTs = (decl: SoundDecl, props: Record<string, unknown> = {}, where = 'SOUNDS'): number[] => {
  if (!(SOUND_KINDS as readonly string[]).includes(decl.kind)) {
    throw new Error(`${where}: unknown sound ${JSON.stringify(decl.kind)} — one of ${SOUND_KINDS.join(', ')}`);
  }
  if (decl.step !== undefined) {
    if (decl.step !== 'type' && decl.step !== 'tap') throw new Error(`${where}: ${decl.kind} step is 'type' or 'tap'`);
    if (decl.type !== undefined || decl.each !== undefined) throw new Error(`${where}: step, type and each are exclusive`);
    const steps = Array.isArray(props.steps) ? (props.steps as Record<string, unknown>[]) : [];
    const out: number[] = [];
    for (const st of steps) {
      if (!st || !finite(st.ta) || !finite(st.t1)) continue;
      if (decl.step === 'tap' && (st.tap !== undefined || st.click !== undefined)) out.push(st.ta);
      if (decl.step === 'type' && st.type !== undefined) out.push(...chunkTimes(st.ta, st.t1, typeChunks(st.type as string | string[])));
    }
    return out;
  }
  const at = typeof decl.at === 'string' ? props[decl.at] : decl.at;
  if (at === undefined || at === null) return [];
  if (!finite(at) || at < 0 || at > 1) throw new Error(`${where}: ${decl.kind} at ${JSON.stringify(at)} — a point on the clock, 0..1`);
  if (decl.type !== undefined) {
    const text = props[decl.type];
    if (typeof text !== 'string' || !text.length) return [];
    const to = decl.to ?? at;
    if (!finite(to) || to < at || to > 1) throw new Error(`${where}: ${decl.kind} type ${decl.type}: to must be in [at, 1]`);
    const n = Array.from(text).length;
    // the i-th character appears when the curve first reaches i/n (floor) or (i - 0.5)/n (round): invert it
    if (decl.draw !== undefined && decl.draw !== 'floor' && decl.draw !== 'round') {
      throw new Error(`${where}: ${decl.kind} type ${decl.type}: draw is 'floor' or 'round'`);
    }
    const inv = (q: number) => (decl.ease === 'out-cubic' ? 1 - Math.cbrt(1 - q) : q);
    const half = decl.draw === 'round' ? 0.5 : 0;
    return Array.from({length: n}, (_, i) => at + (to - at) * inv((i + 1 - half) / n));
  }
  if (decl.each === undefined) return [at];
  const list = props[decl.each];
  if (!Array.isArray(list) || !list.length) return [];
  const to = decl.to ?? at;
  if (!finite(to) || to < at || to > 1) throw new Error(`${where}: ${decl.kind} each ${decl.each}: to must be in [at, 1]`);
  return list.map((_, i) => (list.length === 1 ? at : at + ((to - at) * i) / (list.length - 1)));
};

/** The first t of the first declaration of `kind` (or null) — for a register timing ONE picture event by its sound. */
export const soundT = (decls: readonly SoundDecl[], kind: SoundKind, props: Record<string, unknown> = {}): number | null => {
  for (const d of decls) if (d.kind === kind) { const ts = soundTs(d, props); if (ts.length) return ts[0]; }
  return null;
};
