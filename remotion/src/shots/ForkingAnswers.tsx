// SHOT · ForkingAnswers — the decoding tree: one question asked several times, drawn as the paths its rolls actually
// wrote. The tree is never shown whole and waiting: it GROWS from the reply's first slot, left to right, column by
// column; wherever the growth front reaches a piece, a spray of hairlines flashes there — every option scored at that
// place — and dies back to a trace, leaving only the branches a roll took. Where rolls split, each branch is as thick
// as its measured chance, its chance printed on it. An unfinished answer ends in the blue caret with its next slot
// still stirring, and nothing past it; a finished one ends in its end mark. A count says how many rolls took a path,
// and a verdict can be struck on an answer. An `answer` node is a whole reply whose pieces the film does not have,
// drawn as a card rather than as tokens.
//
// THE ARGUMENT SHAPE: branching under chance, grown in time. Hide the caption and the frame still says "the same
// question went different ways, by different odds, one piece at a time". Every token, chance, count and verdict
// arrives as a prop; with none, the page is empty.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, springAt, useAnimSpan, SPRING_SEAT, lerp} from '../runtime/motion';
import {useGlide} from '../runtime/glide';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {rows} from '../runtime/rows';
import {figureValue} from '../runtime/figure';
import {inkOf, frameOf, groundOf, tileW, tileH, tintAt, Tile, Caret, Title, Source, Spray, Cross, branchD, branchW,
  BODY, MONO, MONO_ADV, TILE_PAD, TitleAt} from '../kits/Kit';

export const DURATION = 180;

const MAX_LEAVES = 7, MAX_DEPTH = 10;

type TNode = {token?: string; answer?: string; start?: boolean; chance?: string; p?: number; rolls?: string;
  verdict?: string; end?: boolean; children?: TNode[]};
type Tree = {prompt?: string; tree?: TNode};
type Flat = {node: TNode; text: string; depth: number; parent: number; kids: number[]; leaf0: number; leaf1: number;
  y: number; tree: number; branch: number};

export const ForkingAnswers: React.FC<{
  trees?: Tree[];         // one or two questions, each with the tree its rolls wrote
  tips?: boolean;         // an unfinished answer ends in a caret with its next slot stirring (default true)
  verdictLabel?: string;  // set beside a struck answer
  sequential?: boolean;   // the first slot's branches grow one after another (separate tries), not together
  rootLive?: boolean;     // the first slot's scoring keeps stirring (another try would roll again)
  title?: string; kicker?: string; titleAt?: TitleAt;
  source?: string; sourceAt?: 'bl' | 'br' | 'tl' | 'tr';
}> = ({trees: treesIn, tips = true, verdictLabel = '', sequential = false, rootLive = false, title = '', kicker = '', titleAt: titleAtIn, source = '',
  sourceAt: sourceAtIn}) => {
  // a title or kicker that was given is drawn: unplaced, it takes the top left (an unset spot used to draw nothing)
  const titleAt: TitleAt = titleAtIn ?? (title || kicker ? 'tl' : 'none');
  const sourceAt = sourceAtIn ?? 'br';
  const trees = rows<Tree>(treesIn ?? [], 'trees', 'ForkingAnswers');
  if (trees.length > 2) throw new Error(`ForkingAnswers: one or two trees fit the page — got ${trees.length}`);
  // ── flatten every tree, leaves in reading order ──
  const flat: Flat[] = [];
  const leafCount: number[] = [];
  trees.forEach((tr, ti) => {
    let leaves = 0;
    const walk = (n: TNode, depth: number, parent: number, path: string): number => {
      const text = n?.start ? '' : n?.answer ?? n?.token;
      if (!n || (!n.start && (typeof text !== 'string' || !text.length))) {
        throw new Error(`ForkingAnswers: ${path} needs a \`token\`, an \`answer\` or \`start\` — got ${JSON.stringify(n)}`);
      }
      if (n.chance !== undefined && figureValue(n.chance) === null) {
        throw new Error(`ForkingAnswers: ${path}.chance must be one figure like "86.8%" — got ${JSON.stringify(n.chance)}`);
      }
      if (depth > MAX_DEPTH) throw new Error(`ForkingAnswers: a tree deeper than ${MAX_DEPTH} pieces does not fit the page`);
      const idx = flat.length;
      const branch = depth <= 1 ? (parent < 0 ? 0 : flat[parent].kids.length) : flat[parent].branch;
      flat.push({node: n, text: text ?? '', depth, parent, kids: [], leaf0: 0, leaf1: 0, y: 0, tree: ti, branch});
      const kids = rows<TNode>(n.children ?? [], `${path}.children`, 'ForkingAnswers');
      if (!kids.length) {
        flat[idx].leaf0 = flat[idx].leaf1 = leaves++;
      } else {
        kids.forEach((k, i) => flat[idx].kids.push(walk(k, depth + 1, idx, `${path}.children.${i}`)));
        flat[idx].leaf0 = flat[flat[idx].kids[0]].leaf0;
        flat[idx].leaf1 = flat[flat[idx].kids[flat[idx].kids.length - 1]].leaf1;
      }
      return idx;
    };
    if (tr.tree) walk(tr.tree, 0, -1, `trees.${ti}.tree`);
    leafCount.push(leaves);
  });
  const allLeaves = leafCount.reduce((a, b) => a + b, 0);
  if (allLeaves > MAX_LEAVES) throw new Error(`ForkingAnswers: at most ${MAX_LEAVES} answers fit the page — got ${allLeaves}`);

  const dna = useDNA();
  const ink = inkOf(dna);
  const t = useT();
  const span = useAnimSpan();
  const glide = useGlide();
  const cue = useCues();
  const {width: W, height: H, fps, durationInFrames: durF} = useVideoConfig();
  const f = frameOf(W, H);
  const {U, sx, lw} = f;
  const row = titleAt[0];
  const titled = titleAt !== 'none' && !!(title || kicker);
  const kOn = easeOutCubic(clamp01(seg(t, ...cue.win('kicker', 0.03, 0.14, REACH_CUBIC))));
  const tOn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.05, 0.17, REACH_CUBIC))));
  const sOn = easeOutCubic(clamp01(seg(t, 0.3, 0.42)));
  const xL = sx, xR = W - sx;
  const zTop = f.zTop + U * 0.005;
  const zBot = (titled && row === 'b' ? f.zBot - U * 0.2 : f.zBot - U * 0.01) - (source && sourceAt[0] === 'b' ? U * 0.06 : 0);

  // ── columns per tree, each as wide as its widest piece; one token size for the whole page ──
  const promptPx = Math.round(U * 0.034);
  const D = (ti: number) => flat.filter((n) => n.tree === ti).reduce((m, n) => Math.max(m, n.depth), 0) + 1;
  const colEms = (ti: number) => Array.from({length: D(ti)}, (_, d) => {
    const ns = flat.filter((n) => n.tree === ti && n.depth === d);
    return ns.reduce((m, n) => Math.max(m, n.node.start ? 0.4 : [...n.text].length * MONO_ADV + TILE_PAD + (n.node.answer ? 0.8 : 0)), 0.4);
  });
  const GAP = 2.4, TAIL = 4.2;            // em between columns; em after the last column for caret, count, verdict
  const emsOf = (ti: number) => colEms(ti).reduce((s, c) => s + c, 0) + GAP * Math.max(0, D(ti) - 1) + TAIL;
  const widest = trees.reduce((m, _, ti) => Math.max(m, emsOf(ti)), 1);
  // rows first: a piece (or an answer card) must fit its row with air above and below it
  const avail0 = zBot - zTop - trees.reduce((s2, _, ti) => s2 + (trees[ti].prompt ? Math.round(U * 0.034) * 2.0 : 0), 0)
    - (trees.length - 1) * U * 0.03;
  const rowMax = avail0 / Math.max(1, allLeaves);
  const px = Math.max(f.label + 2, Math.min(Math.round(U * 0.075), Math.floor((xR - xL) / widest),
    Math.floor(rowMax / (1.5 * 1.1 * 1.25))));
  const th = tileH(px);
  // a shallow tree (few columns) spreads its columns across the page, so each branch is long enough to be seen growing
  const ce0 = trees.length ? colEms(0) : [0.4];
  const slack = (xR - xL) - (ce0.reduce((a, c) => a + c, 0) + TAIL) * px;
  const gap = trees.length === 1 && D(0) <= 3 ? Math.max(GAP * px, (slack * 0.55) / Math.max(1, D(0) - 1)) : GAP * px;
  // rows: each tree takes height in proportion to its answers, with its prompt above it
  const promptH = (ti: number) => (trees[ti].prompt ? promptPx * 2.0 : 0);
  const avail = zBot - zTop - trees.reduce((s, _, ti) => s + promptH(ti), 0) - (trees.length - 1) * U * 0.03;
  const pitch = Math.min(th * 2.1, avail / Math.max(1, allLeaves));
  const colX: number[][] = trees.map((_, ti) => {
    const ce = colEms(ti);
    const out: number[] = [];
    const used = ce.reduce((s2, c) => s2 + c, 0) * px + gap * Math.max(0, ce.length - 1) + TAIL * px;
    const x0 = xL + Math.max(0, (xR - xL - used) * 0.5);
    ce.forEach((c, d) => out.push(d === 0 ? x0 : out[d - 1] + ce[d - 1] * px + gap));
    return out;
  });
  const treeTop: number[] = [];
  let yy = zTop;
  trees.forEach((_, ti) => {
    treeTop.push(yy);
    yy += promptH(ti) + leafCount[ti] * pitch + U * 0.03;
  });
  flat.forEach((n) => {
    const base = treeTop[n.tree] + promptH(n.tree) + pitch / 2;
    n.y = base + ((n.leaf0 + n.leaf1) / 2) * pitch;
  });
  const wOf = (n: Flat) => (n.node.start ? px * 0.4 : n.node.answer ? tileW(n.text, px) + px * 0.8 : tileW(n.text, px));
  const xOf = (n: Flat) => colX[n.tree][n.depth];

  // ── time: each tree grows column by column; the second tree starts while the first is finishing ──
  const T0 = (ti: number) => 0.1 + ti * 0.26;
  const growSpan = (ti: number) => (trees.length > 1 ? 0.42 : 0.6);
  const K = (ti: number) => Math.max(1, flat.find((n) => n.tree === ti && n.depth === 0)?.kids.length ?? 1);
  // sequential: each branch of the first slot grows in its own window, one try after another
  const colAn = (n: Flat, d = n.depth) => sequential
    ? T0(n.tree) + (growSpan(n.tree) / K(n.tree)) * (Math.max(0, n.branch) + (0.8 * d) / Math.max(1, D(n.tree)))
    : T0(n.tree) + (growSpan(n.tree) * d) / Math.max(1, D(n.tree));
  const colBn = (n: Flat) => colAn(n) + (sequential ? 0.74 * growSpan(n.tree) / K(n.tree)
    : growSpan(n.tree) / Math.max(1, D(n.tree)) * 0.9);
  const strokeOf = (n: Flat) => {
    if (typeof n.node.p === 'number') return branchW(n.node.p, U, lw);
    const v = n.node.chance ? figureValue(n.node.chance) : null;
    return v === null ? lw * 1.6 : branchW(v, U, lw);
  };

  return (
    <AbsoluteFill style={{background: groundOf(dna, ink)}}>
      <Title title={title} kicker={kicker} at={titleAt} W={W} H={H} on={tOn} kOn={kOn} ink={ink.fg} dim={ink.dim}
        maxW={W * 0.62} lines={2} />
      {trees.map((tr, ti) => (tr.prompt ? (
        <div key={ti} style={{position: 'absolute', left: colX[ti][0], top: treeTop[ti], maxWidth: xR - colX[ti][0],
          color: ink.dim, opacity: easeOutCubic(clamp01(seg(t, ...cue.win(`trees.${ti}.prompt`, T0(ti) - 0.04, T0(ti) + 0.06, REACH_CUBIC)))),
          font: `500 ${promptPx}px/1.25 ${BODY}`}}>{tr.prompt}</div>) : null))}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* the scoring at each place: a spray where the growth front arrives, dying back to a trace */}
        {flat.map((n, i) => {
          const leaf = !n.kids.length;
          if (n.node.answer || (leaf && (n.node.end || !tips))) return null;
          const a = colBn(n);
          const flash = clamp01(seg(t, (n.node.start ? T0(n.tree) : a) - 0.02, (n.node.start ? T0(n.tree) : a) + 0.04));
          const keepLeaf = leaf || (n.node.start && rootLive) ? 1 : 0.22 + 0.78 * (1 - clamp01(seg(t, a + 0.06, a + 0.16)));
          const x = xOf(n) + wOf(n) + (leaf ? px * 0.55 : px * 0.15);
          return <Spray key={`s${i}`} x={x} y={n.y} len={gap * (leaf ? 1.0 : 0.85)} n={leaf ? 16 : 14} spread={1.3}
            ink={ink.dim} lw={lw} grow={flash} t={t} durF={durF} fps={fps} seed={i * 7 + 3} opacity={keepLeaf} />;
        })}
        {/* the branches the rolls took */}
        {flat.map((n, i) => {
          if (n.parent < 0) return null;
          const p = flat[n.parent];
          const x1 = xOf(p) + wOf(p) + px * 0.1, y1 = p.y, x2 = xOf(n), y2 = n.y;
          const grow = clamp01(seg(t, colAn(n) - 0.02, colAn(n) - 0.02 + (sequential ? (growSpan(n.tree) / K(n.tree)) * 0.72 : 0.09)));
          const fork = p.kids.length > 1;
          return <path key={`e${i}`} d={branchD(x1, y1, x2, y2)} fill="none"
            stroke={fork ? mix(ink.fg, ink.bg, 0.1) : mix(ink.fg, ink.bg, 0.45)} strokeWidth={strokeOf(n)}
            strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - grow} />;
        })}
      </svg>
      {/* each fork's printed chance, on its branch just before the piece */}
      {flat.map((n, i) => {
        if (n.parent < 0 || !n.node.chance) return null;
        const on = easeOutCubic(clamp01(seg(t, colAn(n) + 0.04, colAn(n) + 0.1)));
        const below = n.y > flat[n.parent].y + 1;
        const sw = strokeOf(n);
        return <div key={`c${i}`} style={{position: 'absolute', right: W - xOf(n) + px * 0.3,
          top: below ? n.y + sw / 2 + f.label * 0.15 : n.y - sw / 2 - f.label * 1.3, color: ink.acc, opacity: on,
          whiteSpace: 'nowrap', font: `600 ${f.label}px/1 ${MONO}`}}>{n.node.chance}</div>;
      })}
      {/* the pieces */}
      {flat.map((n, i) => {
        if (n.node.start) {
          const on = clamp01(seg(t, T0(n.tree) - 0.03, T0(n.tree) + 0.02));
          return <div key={`n${i}`} style={{position: 'absolute', left: xOf(n), top: n.y - th * 0.45,
            width: Math.max(4, U * 0.0045), height: th * 0.9, background: ink.acc2, opacity: on}} />;
        }
        const pop = springAt(t, span, fps, colAn(n) + 0.04, SPRING_SEAT);
        const on = clamp01(pop * 1.4);
        // a piece grows OUT of the one before it: it leaves its parent's edge and travels along its branch to its place
        const par = flat[n.parent];
        // separate tries each take their whole window to grow out; a tree's columns snap in one after another
        const gw = sequential ? (growSpan(n.tree) / K(n.tree)) * 0.72 : 0.11;
        const gq = clamp01(seg(t, colAn(n) - 0.02, colAn(n) - 0.02 + gw));
        const g = sequential ? 0.5 - 0.5 * Math.cos(Math.PI * gq) : easeOutCubic(gq);
        const fx = par ? xOf(par) + wOf(par) : xOf(n), fy = par ? par.y : n.y;
        const x = lerp(fx, xOf(n), g), y = lerp(fy, n.y, g);
        const moving = g > 0 && g < 1;
        if (n.node.answer) {
          return <div key={`n${i}`} style={{position: 'absolute', left: 0, top: 0,
            transform: glide(`translate(${x}px, ${y - th * 0.55}px)`, moving), height: th * 1.1,
            padding: `0 ${px * 0.4}px`, display: 'flex', alignItems: 'center', background: ink.surface,
            border: `${Math.max(2, U * 0.0022)}px solid ${ink.border}`, borderRadius: px * 0.25, color: ink.fg, opacity: on,
            font: `600 ${px}px/1 ${MONO}`, whiteSpace: 'pre', boxSizing: 'border-box'}}>{n.text}</div>;
        }
        return <Tile key={`n${i}`} text={n.text} x={x} y={y} px={px} fill={tintAt(n.depth - 1)} ink={ink.fg}
          opacity={on} scale={0.86 + 0.14 * Math.min(1, pop)} moving={moving} />;
      })}
      {/* each answer's tip: its caret (still being written), its end mark (finished), its count, its verdict */}
      {flat.filter((n) => !n.kids.length).map((n, i) => {
        const a = colBn(n);
        const on = easeOutCubic(clamp01(seg(t, a, a + 0.06)));
        let x = xOf(n) + wOf(n) + px * 0.3;
        const out: React.ReactNode[] = [];
        if (n.node.end) {
          out.push(<Tile key="end" text="" w={px * 0.75} x={x} y={n.y} px={px * 0.62} fill={ink.fg} ink={ink.bg} opacity={on} />);
          x += px * 1.05;
        } else if (tips && !n.node.answer) {
          out.push(<Caret key="caret" x={x} y={n.y} h={th * 0.9} color={ink.acc2} on={on} U={U} />);
          x += px * 0.6;
        }
        if (n.node.verdict) {
          const v0 = sequential ? a + 0.01 : a + 0.06 + i * 0.03;
          const s = easeOutCubic(clamp01(seg(t, ...cue.win('verdictLabel', v0, v0 + 0.06, REACH_CUBIC))));
          out.push(<svg key="v" width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <Cross x={x + px * 0.55} y={n.y} s={px * 0.8} color={ink.acc} p={s} lw={Math.max(5, U * 0.006)} /></svg>);
          if (verdictLabel) out.push(<div key="vl" style={{position: 'absolute', left: x + px * 1.3, top: n.y - f.label * 0.62,
            color: ink.acc, opacity: s, font: `600 ${f.label}px/1.2 ${BODY}`, whiteSpace: 'nowrap'}}>{verdictLabel}</div>);
          x += px * 1.3 + (verdictLabel ? [...verdictLabel].length * f.label * 0.55 + px * 0.4 : 0);
        }
        if (n.node.rolls) {
          out.push(<div key="r" style={{position: 'absolute', left: x + px * 0.3, top: n.y - f.label * 0.62, color: ink.dim,
            opacity: on, font: `500 ${f.label}px/1.2 ${MONO}`, whiteSpace: 'nowrap'}}>{n.node.rolls}</div>);
        }
        return <React.Fragment key={`t${i}`}>{out}</React.Fragment>;
      })}
      <Source text={source} at={sourceAt} W={W} H={H} on={sOn} ink={ink.dim} />
    </AbsoluteFill>
  );
};
