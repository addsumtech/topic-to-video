// LABEL PLACE — put every label beside its point with NO two labels, and no label and another point, overlapping.
//
// A map's labels are where its legibility goes first: two cities a few hundred kilometres apart are a few pixels apart
// on a whole globe, and a label pinned to the right of every point lands on its neighbour. Choosing a side by "which
// half of the frame is the point in" fails the same way at the frame's edge (layout.placeLabel's note). So each label
// tries the eight positions round its point, nearest first, then the same eight one and two steps further out with a
// leader back to the point (out to eight steps), and takes the first that is inside the box and clear of everything already placed and of
// every point. NONE CLEAR THROWS — a label laid over another is not a label, and silently dropping one is a place the
// film named that the frame no longer shows.
//
// Pure and deterministic: the registers call it once, on the SETTLED view, so a label never jumps while it is read.
export type Rect = {x0: number; y0: number; x1: number; y1: number};
export type LabelReq = {x: number; y: number; w: number; h: number; text: string; r?: number};
export type Placed = Rect & {ax: number; ay: number; leader: boolean; side: string};

export const overlaps = (a: Rect, b: Rect, pad = 0) =>
  a.x0 < b.x1 + pad && b.x0 < a.x1 + pad && a.y0 < b.y1 + pad && b.y0 < a.y1 + pad;

const SIDES: [string, number, number][] = [
  ['right', 1, 0], ['left', -1, 0], ['above', 0, -1], ['below', 0, 1],
  ['above-right', 1, -1], ['below-right', 1, 1], ['above-left', -1, -1], ['below-left', -1, 1],
];

export const placeLabels = (reqs: LabelReq[], box: Rect, gap: number, obstacles: Rect[] = [],
  shot = 'placeLabels'): Placed[] => {
  const dots: Rect[] = reqs.map((q) => {
    const r = q.r ?? gap * 0.5;
    return {x0: q.x - r, y0: q.y - r, x1: q.x + r, y1: q.y + r};
  });
  const placed: Placed[] = [];
  reqs.forEach((q, i) => {
    let got: Placed | null = null;
    for (const step of [1, 2.2, 3.6, 5.5, 8]) {
      const d = gap * step + (q.r ?? 0);
      for (const [side, sx, sy] of SIDES) {
        const cx = q.x + sx * (d + q.w / 2), cy = q.y + sy * (d + q.h / 2);
        const rect = {x0: cx - q.w / 2, y0: cy - q.h / 2, x1: cx + q.w / 2, y1: cy + q.h / 2};
        if (rect.x0 < box.x0 || rect.x1 > box.x1 || rect.y0 < box.y0 || rect.y1 > box.y1) continue;
        if (obstacles.some((o) => overlaps(rect, o, gap * 0.25))) continue;
        if (placed.some((p) => overlaps(rect, p, gap * 0.35))) continue;
        if (dots.some((o, j) => j !== i && overlaps(rect, o, gap * 0.2))) continue;
        got = {...rect, ax: q.x, ay: q.y, leader: step > 1, side};
        break;
      }
      if (got) break;
    }
    if (!got) {
      throw new Error(`${shot}: no room to label ${JSON.stringify(q.text)} without it lying on another label or ` +
        'point. The places are too close together at this view for every one of them to be named — name fewer, ' +
        'or give the beat a closer view.');
    }
    placed.push(got);
  });
  return placed;
};
