// MAGIC MOVE — glyphs that travel from one setting of type into the next.
//
// WHAT IT DRAWS. A list of SETTINGS (each a runtime/kinetic handle: its own copy, box, size and place on the frame).
// Before the first move the first setting rests; at each move the glyphs two consecutive settings share travel from
// where the first set them to where the second does (kineticMoveCore.matchGlyphs — the longest common subsequence
// first, so a word both share travels as a body), the glyphs only the first has leave, the glyphs only the second
// has arrive. Optionally the first setting assembles out of a SCATTER: every glyph starts at its own seeded place in
// a box, turned and sized, and flies into the measured line.
//
// IT IS STILL THE TEXT IT SHOWS. Every glyph is drawn where runtime/kinetic's reference node laid it out (kerning,
// CJK punctuation compression, kinsoku — the primitive's measurement, not a re-implementation), and it carries the
// primitive's DOM marks (runtime/kineticDom), so every type gate reads a setting as its LINES: each setting is an
// alternative (KIN_ALT) and a glyph belongs to the setting it is resting in or travelling TO. The hold gate
// (scripts/shot_proof.py) asks this component, through the same KineticHoldContext the primitive answers, how long
// each setting is readable: every one of its glyphs at rest in place, walked frame by frame through the same state
// function the picture uses.
//
// IT GLIDES. The baseline unlock (runtime/glide) is on for the whole shot whenever anything travels — the span rule:
// switched on with each move, a glyph would jump from whole-pixel to quarter-pixel on the frame it starts to move.
import React from 'react';
import {useVideoConfig} from 'remotion';
import {useT, useAnimSpan, ReducedMotionContext, SceneDurationContext, REDUCED_MOTION_T} from './motion';
import {useGlide} from './glide';
import {KIN_ALIGN, KIN_ALT, KIN_GLYPH, KIN_LINE, KIN_READ, KIN_ROOT} from './kineticDom';
import {clamp01, EASES, graphemes, tAtFrame, tToSec, wordCount, longestRun} from './kineticCore';
import {KineticHandle, KineticHoldContext, HoldRecord, KGlyph, KLayout} from './kinetic';
import {kineticExtent} from './kineticWord';
import {arcAt, arriveWindow, leaveWindow, matchGlyphs, moveTiming, MoveTiming, scatterOf, travelWindow} from
  './kineticMoveCore';

export type MoveSetting = {k: KineticHandle; x: number; y: number};
/** How far (em) a travelling glyph leaves its line — the room a register keeps clear above and below the type. */
export const MOVE_ROOM_EM = 0.55;
export type KineticMoveProps = {
  settings: MoveSetting[];
  /** seconds (from the shot's first moving frame) at which move j → j+1 STARTS — one per move */
  starts: number[];
  /** seconds each move takes */
  dur?: number;
  color: string;
  emphColor?: string;
  /** the first setting assembles out of a scatter in this box (frame px), starting `at` s, taking `dur` s */
  scatter?: {box: {x: number; y: number; w: number; h: number}; at?: number; dur?: number; seed?: number};
  /** without a scatter, the first setting rises in glyph by glyph from `at` s over `dur` s (false: already there) */
  enter?: {at?: number; dur?: number} | false;
  /** how far a travelling glyph's path bows, as a share of the distance (0 = straight) */
  bow?: number;
  read?: boolean;
  id?: string;
};

type Sprite = {key: string; g: string; lay: KLayout; gl: KGlyph; x: number; y: number; scale: number; rot: number;
  opacity: number; blur: number; alt: number; line: number; idx: number; emix: number};

type Plan = {
  moves: {match: ReturnType<typeof matchGlyphs>; mt: MoveTiming; start: number; rankT: Map<number, number>;
    rankL: Map<number, number>; rankA: Map<number, number>; nT: number; nL: number; nA: number}[];
};

const rankBy = (ids: number[], key: (i: number) => number): Map<number, number> => {
  const sorted = [...ids].sort((a, b) => key(a) - key(b) || a - b);
  return new Map(sorted.map((i, r) => [i, r]));
};
/** A rank per WORD: every glyph of one word shares its word's place in the sweep, so a word that travels travels as
 *  one body. (Staggered glyph by glyph, a word moving left spread into "m o v e s" mid-flight — its first letter left
 *  first and pulled ahead of the rest; measured on the first render of the register.) Returns [rank map, count]. */
const rankWords = (ids: number[], G: KGlyph[], ox: number): [Map<number, number>, number] => {
  const words = Array.from(new Set(ids.map((i) => G[i].word)));
  const firstOf = (w: number) => Math.min(...ids.filter((i) => G[i].word === w).map((i) => G[i].line * 1e5 + ox + G[i].left));
  words.sort((a, b) => firstOf(a) - firstOf(b) || a - b);
  const wr = new Map(words.map((w, r) => [w, r]));
  return [new Map(ids.map((i) => [i, wr.get(G[i].word) ?? 0])), words.length];
};

/** Everything the frame shows at `sec` seconds into the shot's span — ONE function for the picture and the report. */
const spritesAt = (S: MoveSetting[], plan: Plan, sec: number, P: KineticMoveProps, reduced: boolean): Sprite[] => {
  const lays = S.map((s) => s.k.layout as KLayout);
  const glyphsOf = (j: number) => lays[j].alts[0].glyphs;
  const rest = (j: number, i: number, extra?: Partial<Sprite>): Sprite => {
    const gl = glyphsOf(j)[i];
    return {key: `s${j}g${i}`, g: gl.g, lay: lays[j], gl, x: S[j].x + gl.x, y: S[j].y + gl.y, scale: 1, rot: 0,
      opacity: 1, blur: 0, alt: j, line: gl.line, idx: i, emix: gl.emph ? 1 : 0, ...extra};
  };
  const n = S.length;
  if (reduced) return glyphsOf(n - 1).map((g, i) => rest(n - 1, i)).filter((s) => !s.gl.sp);
  // which move is running, or which setting rests
  let j = 0;
  while (j < plan.moves.length && sec >= plan.moves[j].start + plan.moves[j].mt.dur) j += 1;
  const mv = plan.moves[j];
  if (!mv || sec < mv.start) {
    // setting j at rest — or, for the first setting, still assembling out of its scatter
    const out = glyphsOf(j).map((g, i) => rest(j, i)).filter((s) => !s.gl.sp);
    if (j === 0 && P.scatter) {
      const sc = P.scatter, a0 = sc.at ?? 0, d = Math.max(0.3, sc.dur ?? 1.2);
      const vis = out.map((s) => s.idx);
      const rk = rankBy(vis, (i) => glyphsOf(0)[i].left + glyphsOf(0)[i].line * 1e5);
      const st = vis.length > 1 ? Math.min(0.05, (d * 0.35) / (vis.length - 1)) : 0;
      const trav = d - st * Math.max(0, vis.length - 1);
      return out.map((s) => {
        const r = rk.get(s.idx) ?? 0;
        const p = clamp01((sec - a0 - r * st) / Math.max(1e-6, trav));
        if (p >= 1) return s;
        const e = EASES.power4(p);
        const from = scatterOf(s.idx, sc.seed ?? 3, sc.box);
        // the scatter is a place for the glyph's CENTRE; the holder is placed by its top-left
        const cx = s.gl.adv / 2, cy = s.gl.dy + s.gl.h / 2;
        const pt = arcAt(e, from.x - cx, from.y - cy, s.x, s.y, 0.1);
        return {...s, x: pt.x, y: pt.y, rot: from.rot * (1 - e), scale: from.scale + (1 - from.scale) * e,
          opacity: clamp01(p * 3.5), blur: 0.05 * Math.sin(Math.PI * p)};
      });
    }
    if (j === 0 && P.enter !== false) {
      const en = P.enter ?? {}, a0 = en.at ?? 0.05, d = Math.max(0.2, en.dur ?? 0.9);
      const vis = out.map((s) => s.idx);
      const rk = rankBy(vis, (i) => glyphsOf(0)[i].left + glyphsOf(0)[i].line * 1e5);
      const st = vis.length > 1 ? Math.min(0.04, (d * 0.45) / (vis.length - 1)) : 0;
      const one = d - st * Math.max(0, vis.length - 1);
      return out.map((s) => {
        const p = clamp01((sec - a0 - (rk.get(s.idx) ?? 0) * st) / Math.max(1e-6, one));
        if (p >= 1) return s;
        const e = EASES.power4(p);
        return {...s, y: s.y + s.lay.size * 0.36 * (1 - e), opacity: clamp01(p * 2.2), blur: 0.05 * (1 - e)};
      }).filter((s) => s.opacity > 0);
    }
    return out;
  }
  // move j: from setting j to setting j+1
  const u = sec - mv.start, mt = mv.mt;
  const out: Sprite[] = [];
  const {nT, nL, nA} = mv;
  for (const [ia, ib] of mv.match.pairs) {
    const [a, b] = travelWindow(mv.rankT.get(ib) ?? 0, nT, mt);
    const p = clamp01((u - a) / Math.max(1e-6, b - a));
    if (p <= 0) { out.push(rest(j, ia)); continue; }
    const B = rest(j + 1, ib);
    if (p >= 1) { out.push(B); continue; }
    const A = rest(j, ia);
    const e = EASES.inOut(p);
    // the glyph is drawn at the DESTINATION's size, scaled from the source's about its baseline centre (the holder's
    // transform origin), so at p = 0 its baseline centre sits on the source glyph's and at p = 1 on its own
    const r0 = A.lay.size / B.lay.size;
    const ax = A.x + A.gl.adv / 2 - B.gl.adv / 2, ay = A.y + A.gl.base - B.gl.base;
    // at most 0.55 em off the line: a glyph moving right passes just over it and one moving left just under, ~1.1 em
    // apart, so they never cross each other — and the room a register leaves above and below is MOVE_ROOM_EM
    const pt = arcAt(e, ax, ay, B.x, B.y, P.bow ?? 0.16, MOVE_ROOM_EM * B.lay.size);
    const dir = Math.sign(B.x - A.x) || 1;
    out.push({...B, key: `t${j}-${ib}`, x: pt.x, y: pt.y, scale: r0 + (1 - r0) * e,
      rot: dir * 5 * Math.sin(Math.PI * e), blur: 0.025 * Math.sin(Math.PI * p),
      emix: A.emix + (B.emix - A.emix) * e});
  }
  for (const ia of mv.match.leave) {
    const [a, b] = leaveWindow(mv.rankL.get(ia) ?? 0, nL, mt);
    const p = clamp01((u - a) / Math.max(1e-6, b - a));
    if (p >= 1) continue;
    const A = rest(j, ia);
    const e = EASES.power3(p);
    out.push({...A, y: A.y - A.lay.size * 0.32 * e, opacity: 1 - e, blur: 0.06 * e, scale: 1 - 0.08 * e});
  }
  for (const ib of mv.match.arrive) {
    const [a, b] = arriveWindow(mv.rankA.get(ib) ?? 0, nA, mt);
    const p = clamp01((u - a) / Math.max(1e-6, b - a));
    if (p <= 0) continue;
    const B = rest(j + 1, ib);
    const e = EASES.power3(p);
    out.push({...B, y: B.y + B.lay.size * 0.32 * (1 - e), opacity: e, blur: 0.06 * (1 - e), scale: 0.92 + 0.08 * e});
  }
  return out.filter((s) => !s.gl.sp);
};

export const KineticMove: React.FC<KineticMoveProps> = (P) => {
  const t = useT();
  const {fps, durationInFrames} = useVideoConfig();
  const spanF = useAnimSpan();
  const sceneDur = React.useContext(SceneDurationContext);
  const reduced = React.useContext(ReducedMotionContext);
  const report = React.useContext(KineticHoldContext);
  const glide = useGlide();
  const S = P.settings;
  if (S.length < 1) throw new Error('KineticMove needs at least one setting.');
  if (P.starts.length !== S.length - 1) {
    throw new Error(`KineticMove: ${S.length} settings need ${S.length - 1} move start(s), got ${P.starts.length}.`);
  }
  const ready = S.every((s) => s.k.layout);
  const read = P.read ?? true;
  const plan = React.useMemo<Plan | null>(() => {
    if (!ready) return null;
    return {moves: P.starts.map((start, j) => {
      const A = S[j].k.layout!.alts[0].glyphs, B = S[j + 1].k.layout!.alts[0].glyphs;
      const posA = A.map((g) => S[j].x + g.left), posB = B.map((g) => S[j + 1].x + g.left);
      const match = matchGlyphs(A.map((g) => g.g), B.map((g) => g.g), posA, posB);
      if (j > 0 && start < P.starts[j - 1] + (P.dur ?? 1.15)) {
        throw new Error(`KineticMove: move ${j + 1} starts at ${start.toFixed(2)} s, before move ${j} has ended.`);
      }
      const [rankT, nT] = rankWords(match.pairs.map((p) => p[1]), B, S[j + 1].x);
      const [rankL, nL] = rankWords(match.leave, A, S[j].x);
      const [rankA, nA] = rankWords(match.arrive, B, S[j + 1].x);
      return {match, mt: moveTiming(P.dur ?? 1.15, nT), start, rankT, rankL, rankA, nT, nL, nA};
    })};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, ...S.map((s) => s.k.key), ...S.map((s) => `${s.x},${s.y}`), P.starts.join(','), P.dur]);

  // the hold report: each setting's longest run of frames with every one of its glyphs at rest in place
  React.useLayoutEffect(() => {
    if (!report || !plan || !read) return;
    const dur = sceneDur ?? durationInFrames;
    const pad = Math.min(12, Math.floor(Math.max(0, dur - 1) / 3));
    const okRuns: boolean[][] = S.map(() => []);
    for (let f = 0; f <= dur - 1 - pad; f++) {
      const tf = reduced ? REDUCED_MOTION_T : tAtFrame(f, dur);
      const sp = spritesAt(S, plan, tToSec(tf, spanF, fps), P, reduced);
      S.forEach((s, j) => {
        const G = s.k.layout!.alts[0].glyphs;
        const want = G.map((g, i) => (g.sp ? -1 : i)).filter((i) => i >= 0);
        const at = new Map(sp.filter((q) => q.alt === j).map((q) => [q.idx, q]));
        okRuns[j].push(want.every((i) => {
          const q = at.get(i);
          return Boolean(q && q.opacity >= 0.5 && Math.abs(q.x - (s.x + G[i].x)) < 0.5 &&
            Math.abs(q.y - (s.y + G[i].y)) < 0.5 && Math.abs(q.scale - 1) < 0.02);
        }));
      });
    }
    const texts: HoldRecord[] = S.map((s, j) => {
      const L = s.k.layout!;
      const text = L.alts[0].text.replace(/\n/g, ' ');
      return {text, kind: 'alt', hold: longestRun(okRuns[j]) / fps, chars: graphemes(text.replace(/\s+/g, '')).length,
        words: wordCount(text, L.lang), lang: L.lang};
    });
    report({id: P.id ?? 'move', frames: dur, fps, texts});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report, plan, read]);

  const anchors = S.map((s, j) => <React.Fragment key={`a${j}`}>{s.k.anchor}</React.Fragment>);
  const rootAttrs = {[KIN_ROOT]: P.id ?? 'move', [KIN_READ]: read ? '1' : '0',
    [KIN_ALIGN]: S[0].k.spec.align ?? 'left'};
  // THE ROOT IS THE `word` CARRY ANCHOR (runtime/carry): its box is the LAST setting's measured extent — what is on
  // the frame when the beat leaves — and, on one line, a glyph window (seams.tsx looks through every drawn holder).
  // The glyphs are placed relative to it, so the anchor moves nothing.
  const last = S[S.length - 1];
  const ext = kineticExtent(last.k.layout);
  const ax = ext ? last.x + ext.left : 0, ay = ext ? last.y + ext.top : 0;
  const box: React.CSSProperties = {position: 'absolute', left: ax, top: ay, width: ext?.width ?? 0,
    height: ext?.height ?? 0, pointerEvents: 'none'};
  if (!plan) return <div {...rootAttrs} style={box}>{anchors}</div>;

  const sec = tToSec(t, spanF, fps);
  const sprites = spritesAt(S, plan, sec, P, reduced);
  const moves = plan.moves.length > 0 || Boolean(P.scatter) || P.enter !== false;   // @glide-span: fixed by the plan for the whole beat
  const ec = P.emphColor ?? P.color;
  return (
    <div {...rootAttrs} data-carry="word" data-carry-glyph={ext && ext.lines === 1 ? '' : undefined} style={box}>
      {anchors}
      {sprites.map((s) => {
        const L = s.lay;
        const ox = s.gl.adv / 2, oy = s.gl.base;
        const parts: string[] = [];
        const at = `translate(${(s.x - ax).toFixed(3)}px, ${(s.y - ay).toFixed(3)}px)`;
        parts.push(at);
        if (s.rot) parts.push(`rotate(${s.rot.toFixed(3)}deg)`);
        if (Math.abs(s.scale - 1) > 1e-6) parts.push(`scale(${s.scale.toFixed(5)})`);
        const ink = s.emix >= 1 ? ec : s.emix <= 0 ? P.color
          : `color-mix(in oklab, ${ec} ${(s.emix * 100).toFixed(1)}%, ${P.color})`;
        const attrs: Record<string, string> = {[KIN_LINE]: String(s.line), [KIN_GLYPH]: String(s.idx),
          [KIN_ALT]: String(s.alt)};
        const blurPx = s.blur * L.size;
        return (
          <span key={s.key} style={{position: 'absolute', left: 0, top: 0, transformOrigin: `${ox}px ${oy}px`,
            transform: parts.join(' '), opacity: s.opacity >= 0.999 ? undefined : s.opacity,
            filter: blurPx > 0.05 ? `blur(${blurPx.toFixed(2)}px)` : undefined,
            fontFamily: L.family, fontSize: `${L.size}px`, lineHeight: `${L.lh}px`,
            fontWeight: s.gl.emph ? L.emphWeight : L.weight, fontStyle: L.italic ? 'italic' : 'normal',
            fontStretch: `${L.stretch}%`, fontVariantLigatures: 'none', letterSpacing: 0, whiteSpace: 'pre'}}>
            <span {...attrs} lang={L.lang} style={{display: 'block', color: ink,
              transform: glide(undefined, moves, Math.max(0.05, s.scale)),
              ...({textSpacingTrim: s.gl.trim ? 'trim-start' : 'space-all'} as React.CSSProperties)}}>
              {s.g}
            </span>
          </span>
        );
      })}
    </div>
  );
};

/** The seconds a schedule of settings needs: each setting held for its reading time `need[j]` (s), a move of
 *  `dur` s between each, after `lead` s. A register divides a longer beat in proportion to `need` and refuses
 *  nothing — the hold gate names a setting a short beat cannot let be read. */
export const moveSchedule = (need: number[], spanS: number, dur: number, lead: number): number[] => {
  const n = need.length;
  if (n < 2) return [];
  const moves = (n - 1) * dur;
  const room = Math.max(0, spanS - lead - moves);
  const total = need.reduce((a, b) => a + b, 0) || 1;
  // the LAST setting is held to the end of the shot, so the room is shared over the first n-1 and the last gets
  // its own reading time from what is left — never less than its share
  const share = need.map((x) => (room * x) / total);
  const starts: number[] = [];
  let at = lead;
  for (let j = 0; j < n - 1; j++) {
    at += share[j];
    starts.push(at);
    at += dur;
  }
  return starts;
};
