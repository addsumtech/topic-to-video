// SANKEY — a flow layout from the film's own nodes and links, where every ribbon's width IS its quantity.
//
// The claim a flow diagram makes is CONSERVATION: what enters a stage leaves it, split. So the layout refuses a node
// whose inflow and outflow differ — drawn anyway, the difference would have to appear from nowhere or vanish into the
// node, and the picture would assert a balance the figures do not have. A film that loses something on the way says
// so with a link to a node named for the loss. Equality is judged relative to the node's flow (1e-9), so 0.1 + 0.2
// balances 0.3 and nothing larger than float noise is forgiven.
//
// LAYOUT (after d3-sankey, rebuilt here so the refusals and the label check live in one place): a node's column is its
// longest path from a source, sinks are justified to the last column; one vertical scale for the whole diagram (the
// tightest column sets it, so a width means the same quantity everywhere); six relaxation passes pull each node
// toward the value-weighted centre of its neighbours, then de-overlap within the column; links stack at each node in
// the order of the node at their other end, so ribbons do not cross where they leave or arrive.
export type SNodeIn = {id?: string; label?: string; display?: string};
export type SLinkIn = {from?: string; to?: string; value?: number};
export type SNode = {id: string; label: string; display: string; i: number; col: number; value: number;
  inV: number; outV: number; x0: number; x1: number; y0: number; y1: number};
export type SLink = {i: number; source: SNode; target: SNode; value: number; width: number; y0: number; y1: number};
export type SLayout = {nodes: SNode[]; links: SLink[]; cols: number; k: number};

export const SANKEY_TOL = 1e-9;

export const validateSankey = (nodesIn: SNodeIn[], linksIn: SLinkIn[], shot: string) => {
  const ids = new Map<string, number>();
  const nodes = nodesIn.map((n, i) => {
    const id = String(n?.id ?? n?.label ?? '').trim();
    const label = String(n?.label ?? n?.id ?? '').trim();
    if (!id || !label) throw new Error(`${shot}: node ${i + 1} needs a \`label\` (and an \`id\` if links name it differently).`);
    if (ids.has(id)) throw new Error(`${shot}: two nodes share the id ${JSON.stringify(id)}.`);
    ids.set(id, i);
    return {id, label, display: String(n?.display ?? '').trim(), i};
  });
  const links = linksIn.map((l, i) => {
    const s = ids.get(String(l?.from ?? '').trim()), tg = ids.get(String(l?.to ?? '').trim());
    if (s == null || tg == null) {
      throw new Error(`${shot}: link ${i + 1} runs ${JSON.stringify(l?.from)} → ${JSON.stringify(l?.to)}, and both ends must ` +
        `be node ids (${nodes.map((n) => n.id).join(', ')}).`);
    }
    if (s === tg) throw new Error(`${shot}: link ${i + 1} flows from ${nodes[s].label} into itself.`);
    const v = l?.value;
    if (typeof v !== 'number' || !Number.isFinite(v) || v <= 0) {
      throw new Error(`${shot}: link ${i + 1} (${nodes[s].label} → ${nodes[tg].label}) needs a \`value\` that is a number > 0, ` +
        `got ${JSON.stringify(v)}. A ribbon's width is drawn from it; pass the sourced figure.`);
    }
    return {i, s, t: tg, value: v};
  });
  // a cycle has no left-to-right order to draw it in
  const indeg = nodes.map(() => 0);
  links.forEach((l) => { indeg[l.t] += 1; });
  const order: number[] = [];
  const queue = nodes.map((_, i) => i).filter((i) => indeg[i] === 0);
  const deg = [...indeg];
  while (queue.length) {
    const u = queue.shift()!;
    order.push(u);
    links.filter((l) => l.s === u).forEach((l) => { deg[l.t] -= 1; if (deg[l.t] === 0) queue.push(l.t); });
  }
  if (order.length !== nodes.length) {
    throw new Error(`${shot}: the links form a loop, so there is no left-to-right order to draw the flow in.`);
  }
  const linked = new Set(links.flatMap((l) => [l.s, l.t]));
  const loose = nodes.filter((n) => !linked.has(n.i));
  if (loose.length) throw new Error(`${shot}: ${loose.map((n) => n.label).join(', ')} has no link — a node with no flow has no height.`);
  // CONSERVATION
  for (const n of nodes) {
    const inV = links.filter((l) => l.t === n.i).reduce((a, l) => a + l.value, 0);
    const outV = links.filter((l) => l.s === n.i).reduce((a, l) => a + l.value, 0);
    if (inV > 0 && outV > 0 && Math.abs(inV - outV) > SANKEY_TOL * Math.max(inV, outV)) {
      throw new Error(`${shot}: ${JSON.stringify(n.label)} receives ${inV} and sends on ${outV}. Every ribbon's width is its ` +
        'quantity, so the difference would have to appear from nowhere or vanish inside the node. If something is lost ' +
        'or added there, give it its own node and link; otherwise fix the figures.');
    }
  }
  return {nodes, links, order};
};

export const layoutSankey = (nodesIn: SNodeIn[], linksIn: SLinkIn[], box: {x0: number; x1: number; y0: number; y1: number},
  nodeW: number, pad: number, shot: string): SLayout => {
  const v = validateSankey(nodesIn, linksIn, shot);
  const N = v.nodes.length;
  // columns: longest path from a source, sinks justified right
  const col = new Array(N).fill(0);
  for (const u of v.order) v.links.filter((l) => l.s === u).forEach((l) => { col[l.t] = Math.max(col[l.t], col[u] + 1); });
  const maxCol = Math.max(...col);
  v.nodes.forEach((n) => { if (!v.links.some((l) => l.s === n.i)) col[n.i] = maxCol; });
  const cols = maxCol + 1;
  if (cols < 2) throw new Error(`${shot}: a flow needs at least two stages.`);
  const nodes: SNode[] = v.nodes.map((n) => {
    const inV = v.links.filter((l) => l.t === n.i).reduce((a, l) => a + l.value, 0);
    const outV = v.links.filter((l) => l.s === n.i).reduce((a, l) => a + l.value, 0);
    const x0 = box.x0 + (box.x1 - box.x0 - nodeW) * (col[n.i] / maxCol);
    return {...n, col: col[n.i], value: Math.max(inV, outV), inV, outV, x0, x1: x0 + nodeW, y0: 0, y1: 0};
  });
  const byCol = Array.from({length: cols}, (_, c) => nodes.filter((n) => n.col === c));
  const H = box.y1 - box.y0;
  const k = Math.min(...byCol.map((ns) => (H - pad * (ns.length - 1)) / ns.reduce((a, n) => a + n.value, 0)));
  if (!(k > 0)) throw new Error(`${shot}: a column holds too many nodes for the height at this spacing.`);
  // initial: stacked in the film's order, centred
  byCol.forEach((ns) => {
    const tot = ns.reduce((a, n) => a + n.value * k, 0) + pad * (ns.length - 1);
    let y = box.y0 + (H - tot) / 2;
    ns.forEach((n) => { n.y0 = y; n.y1 = y + n.value * k; y = n.y1 + pad; });
  });
  const links: SLink[] = v.links.map((l) => ({i: l.i, source: nodes[l.s], target: nodes[l.t], value: l.value,
    width: l.value * k, y0: 0, y1: 0}));
  const mid = (n: SNode) => (n.y0 + n.y1) / 2;
  const resolve = (ns: SNode[]) => {
    ns.sort((a, b) => mid(a) - mid(b));
    let y = box.y0;
    for (const n of ns) { const h = n.y1 - n.y0; if (n.y0 < y) { n.y0 = y; n.y1 = y + h; } y = n.y1 + pad; }
    let yb = box.y1;
    for (let j = ns.length - 1; j >= 0; j--) {
      const n = ns[j], h = n.y1 - n.y0;
      if (n.y1 > yb) { n.y1 = yb; n.y0 = yb - h; }
      yb = n.y0 - pad;
    }
  };
  for (let it = 0, alpha = 1; it < 6; it++, alpha *= 0.99) {
    const forward = it % 2 === 0;
    const seq = forward ? byCol.slice(1) : byCol.slice(0, -1).reverse();
    for (const ns of seq) {
      for (const n of ns) {
        const ls = forward ? links.filter((l) => l.target === n) : links.filter((l) => l.source === n);
        if (!ls.length) continue;
        const w = ls.reduce((a, l) => a + l.value, 0);
        const c = ls.reduce((a, l) => a + mid(forward ? l.source : l.target) * l.value, 0) / w;
        const dy = (c - mid(n)) * alpha;
        n.y0 += dy; n.y1 += dy;
      }
      resolve(ns);
    }
  }
  // link stacking at each end, ordered by the other end's position
  for (const n of nodes) {
    const outs = links.filter((l) => l.source === n).sort((a, b) => mid(a.target) - mid(b.target));
    let y = n.y0 + (n.y1 - n.y0 - outs.reduce((a, l) => a + l.width, 0)) / 2;
    outs.forEach((l) => { l.y0 = y + l.width / 2; y += l.width; });
    const ins = links.filter((l) => l.target === n).sort((a, b) => mid(a.source) - mid(b.source));
    y = n.y0 + (n.y1 - n.y0 - ins.reduce((a, l) => a + l.width, 0)) / 2;
    ins.forEach((l) => { l.y1 = y + l.width / 2; y += l.width; });
  }
  return {nodes, links, cols, k};
};

/** The ribbon's centreline: a horizontal cubic from the source's right edge to the target's left, stroked at the
 *  ribbon's width (d3-sankey's sankeyLinkHorizontal) — which is what lets a dash draw it on. */
export const ribbonPath = (l: SLink) => {
  const xa = l.source.x1, xb = l.target.x0, xm = (xa + xb) / 2;
  return `M${xa.toFixed(2)},${l.y0.toFixed(2)}C${xm.toFixed(2)},${l.y0.toFixed(2)} ${xm.toFixed(2)},${l.y1.toFixed(2)} ` +
    `${xb.toFixed(2)},${l.y1.toFixed(2)}`;
};

/** 1-D de-overlap of labels in one column: each wants to centre on its node; pushed apart by `gap`, kept inside
 *  [y0, y1]. Returns the tops, or null when they cannot all fit — the caller refuses rather than overlap them. */
export const stackLabels = (want: {cy: number; h: number}[], y0: number, y1: number, gap: number): number[] | null => {
  const idx = want.map((_, i) => i).sort((a, b) => want[a].cy - want[b].cy);
  const total = want.reduce((a, w) => a + w.h, 0) + gap * Math.max(0, want.length - 1);
  if (total > y1 - y0 + 1e-6) return null;
  const top = new Array(want.length).fill(0);
  let y = y0;
  for (const i of idx) { top[i] = Math.max(y, want[i].cy - want[i].h / 2); y = top[i] + want[i].h + gap; }
  let yb = y1;
  for (let j = idx.length - 1; j >= 0; j--) {
    const i = idx[j];
    if (top[i] + want[i].h > yb) top[i] = yb - want[i].h;
    yb = top[i] - gap;
  }
  return top;
};
