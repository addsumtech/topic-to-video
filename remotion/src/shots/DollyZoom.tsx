// SHOT · DollyZoom — the subject did not change. The room around it did.
//
// Dolly in, zoom out: the camera walks toward the subject while the lens widens by exactly as much. The
// subject's projected size never moves; everything behind it swells. It is the one camera move whose
// meaning is neither "look closer" nor "here is the whole of it" — it says THIS DID NOT CHANGE, WHAT
// SURROUNDS IT DID, and nothing in this library could say it. The peer study named it as the unbuilt half
// of its depth gap, with the figure it uses: subject pinned, background 1 -> 2.25.
//
// USE IT when the beat re-reads something that has not moved: the same task inside a bigger system, the
// same claim once its context arrives, one register inside a library of a hundred and sixty. If the SUBJECT
// is what changes, this is the wrong register — a dolly-zoom on a moving subject is just a zoom.
//
// WHY THE TYPE DOES NOT SCALE WITH THE ROOM. `runtime/depth.tsx` argues, with the measurement behind it,
// that a layer under a 3D or scaling transform is rasterized once and upscaled — glyph edge strength fell
// from 91 to 56 — so depth here is built from the cues that survive: SIZE, FOCUS, SHADOW and PARALLAX, and
// text goes on the plane that stays sharp. The ROOM (hairlines, no type) takes the SIZE cue and swells; the
// context labels take PARALLAX and FOCUS, travelling outward and softening at a constant type size. The move
// a viewer reads is the same one, and every word on the frame is rendered at its final resolution.
//
// AND THE SUBJECT IS PINNED IN THE STRICT SENSE: no scale, no translate, no filter — not "barely moves".
// The whole argument is that its size is the one quantity in the frame that does not change, so a shot that
// let it drift 2% would be quietly making the opposite point. `test_dolly_zoom` measures it.
//
// THE LABELS NEVER LEAVE THE FRAME, which is a deliberate departure from the real move. A room swelling past
// the lens would sweep its contents out of shot, and an earlier draft did that — until the register's own
// family produced the lesson: `WordTunnel`'s final phrase was culled for width and the shot ended on an empty
// frame while `text_safe_qa` reported 0 findings at all five aspects, because type that is never drawn is
// never cut off. Copy a film hands this register has to be READABLE at the frame it settles on, so the travel
// is budgeted from the safe box and the labels arrive at its edge rather than through it.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {focusFilter} from '../runtime/focus';
import {dollyAt} from '../runtime/depth';

export const DURATION = 175; // ~5.8s

export const DollyZoom: React.FC<{
  /** the thing that does not change — the one element drawn sharp, at a constant size */
  subject?: string;
  /** one line under it: what the subject IS, when the name alone is not enough */
  note?: string;
  /** SHORT labels for the surroundings — the first six are used. They are the room, not the argument: a
   *  sentence here reads as the subject's own caption rather than as context, and gets a size to match. */
  context?: string[];
  /** what the new scale MEANS, landing once the room has settled */
  reading?: string;
  /** `in` = the room closes in around the subject; `out` = an overwhelming room recedes off it */
  direction?: 'in' | 'out';
}> = ({
  subject: SUBJ = 'The thing itself', note: NOTE = '', context: CTX = ['around it', 'and this', 'and this too',
    'this as well', 'also this', 'and all of this'], reading: READ = '', direction: DIR = 'in',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  const subject = String(SUBJ ?? '').trim();
  if (!subject) {
    throw new Error(
      'DollyZoom needs a `subject`. The form is a room changing size around something that does not; with ' +
      'nothing pinned in the middle there is no reference, and the move reads as a plain zoom.');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 50% 45%, #141926, #080a0f 74%)';
  const FG = dna?.fg ?? '#eef2f8';
  const ACC = dna?.accent ?? '#5b8cff';
  const DIM = dna?.dim ?? '#7c8699';
  // THE ROOM'S LINES ARE BUILT FROM `dim`, NOT FROM `line`. Looked at rather than assumed: `line` is the
  // token for a hairline rule sitting ON a surface, and every preset sets it a few levels off its own
  // ground (product #20242f on #060709, editorial #2a2018 on #12100e). At that contrast a full-frame field
  // seen through the room's own defocus is invisible, and the first render of this register was a subject
  // floating in nothing — the move it exists to make had no room to make it in. `dim` is a mid-tone in
  // every preset because it has to stay readable, so an alpha over it lands in the same visible band on
  // any ground. A MAJOR line every fourth cell gives the swell something to count by: a uniform grid
  // scaling up looks much the same at 1x and 2.25x until a heavier line crosses the frame.
  const LINE = `${DIM}38`;
  const LINE_MAJOR = `${DIM}66`;

  // A DIRECTION THAT IS NEITHER IS REFUSED, not quietly read as `in`. The `= {}` default on the props
  // object widens a literal union to `string` for TypeScript, so the compiler cannot hold this prop to its
  // own declared type — and a film that writes `"inward"` would otherwise get the opposite beat from the
  // one it asked for, on a frame that looks perfectly finished.
  if (DIR !== 'in' && DIR !== 'out') {
    throw new Error(
      `DollyZoom direction must be 'in' or 'out', got ${JSON.stringify(DIR)}. 'in' closes the room around ` +
      `the subject; 'out' recedes an overwhelming room off it. They are opposite arguments, so there is no ` +
      `sensible default to fall back to.`);
  }
  // A LIGHTER BLUR THAN THE HOUSE DEFAULT FOR A RACK, and the reason is that this plane carries COPY a film
  // supplied. `RackFocus` can push to 0.0065 because its far reading is meant to be unreadable until the
  // lens turns; here the room's labels have to be legible at the frame the shot settles on. The anchor's
  // other two halves — brightness and saturation — do most of the receding, which is what keeps the pinned
  // subject the thing you read without making its surroundings a fog.
  const dolly = dollyAt(t, U, {direction: DIR, blurFrac: 0.0018});
  const roomFilter = focusFilter(dolly.focus);

  // ── the zone ────────────────────────────────────────────────────────────────────────────────────────
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const zoneH = Math.max(160, zBot - zTop);
  const cy = (zTop + zBot) / 2;
  const portrait = H > W * 1.1;
  const MARGIN = Math.round(U * 0.045);

  // ── the subject, measured first: everything else is laid out around what it actually takes ──────────
  const SW = Math.round(W * (portrait ? 0.80 : 0.44));
  const subjLead = leading(subject, 1.05);
  const subjPx = fitBlockPx(subject, SW, Math.round(zoneH * 0.24), Math.round(U * 0.088),
    {usable: 1, leading: subjLead});
  const note = String(NOTE ?? '').trim();
  const reading = String(READ ?? '').trim();
  // The note and the reading are FITTED to budgets of their own rather than set at a flat size. A flat one
  // is fine until a film writes three clauses into `note`, and then the plate grows downward into the strip
  // the burned caption owns — the defect `contentBottom` exists to prevent, arriving from above it.
  const noteLead = leading(note, 1.35), readLead = leading(reading, 1.3);
  const notePx = note
    ? fitBlockPx(note, SW, Math.round(zoneH * 0.12), Math.round(U * 0.026), {usable: 1, leading: noteLead})
    : 0;
  const readPx = reading
    ? fitBlockPx(reading, SW, Math.round(zoneH * 0.12), Math.round(U * 0.028), {usable: 1, leading: readLead})
    : 0;
  const subjH = Math.ceil(wrapLines(subject, subjPx, SW) * subjPx * subjLead)
    + (note ? Math.round(U * 0.022) + Math.ceil(wrapLines(note, notePx, SW) * notePx * noteLead) : 0);
  const readH = reading
    ? Math.round(U * 0.05) + Math.ceil(wrapLines(reading, readPx, SW) * readPx * readLead) : 0;
  const plateH = subjH + readH;

  // ── the context labels ──────────────────────────────────────────────────────────────────────────────
  // Two groups on opposite sides of the subject, along whichever axis the frame has room on: sideways in
  // landscape, above and below in portrait. Each group travels OUTWARD as the room swells and its members
  // spread apart — the parallax that carries the size cue the type is not allowed to take.
  const items = CTX.map((s) => String(s ?? '').trim()).filter(Boolean).slice(0, 6);
  const half = Math.ceil(items.length / 2);
  const groups = items.length ? [items.slice(0, half), items.slice(half)].filter((g) => g.length) : [];

  // THE LABELS FIT THE FRAME'S LEFTOVERS, and on a narrow one the leftovers are small: at 9:16 the side
  // bands are under a hundred pixels, which is why the groups go above and below there instead. Even then a
  // frame can be too tight for the type size chosen at 16:9, so the size STEPS DOWN until the travel is
  // real, and says so loudly if no step works — a register that quietly draws its context on top of its
  // subject is worse than one that refuses.
  const MIN_TRAVEL = U * 0.02;
  const fit = (() => {
    for (const s of [1, 0.92, 0.84, 0.76, 0.68, 0.6]) {
      const px = Math.max(11, Math.round(U * (portrait ? 0.026 : 0.028) * s));
      // The labels share ONE leading, and it is the CJK floor when any of them carries Han: a mixed group
      // set at two leadings reads as two different kinds of thing standing in the same room.
      const lead = leading(items, 1.3);
      const w = portrait
        ? Math.round((W - 2 * MARGIN) / Math.max(1, half) - U * 0.02)
        : Math.round((W / 2 - MARGIN - SW / 2 - U * 0.03) * 0.62 * s);
      if (w < px * 2) continue;                                   // a box under two glyphs wide is not a label
      const h = (str: string) => Math.ceil(wrapLines(str, px, w) * px * lead);
      // ALONG the travel axis a landscape group is one box wide; a portrait group is its tallest label.
      const along = groups.map((g) => (portrait ? Math.max(...g.map(h)) : w));
      const maxAlong = Math.max(...along, 0);
      const axisRoom = (portrait ? zoneH / 2 : W / 2) - MARGIN - maxAlong / 2;
      const clear = (portrait ? plateH / 2 : SW / 2) + U * 0.05 + maxAlong / 2;
      if (!groups.length) return {px, lead, w, h, offMin: 0, offMax: 0};
      if (axisRoom - clear >= MIN_TRAVEL) {
        return {px, lead, w, h, offMin: clear + (axisRoom - clear) * 0.28, offMax: axisRoom};
      }
    }
    throw new Error(
      `DollyZoom cannot place its context labels on a ${W}x${H} frame: the subject plate and the margins ` +
      `leave no room outside it for them to travel in, at any label size down to 60%. Shorten \`subject\`, ` +
      `pass fewer \`context\` labels, or use a register whose context does not surround its subject.`);
  })();
  const off = lerp(fit.offMin, fit.offMax, dolly.k);

  // Spacing WITHIN a group, which opens with the room. Bounded by the cross axis — the content zone's own
  // height in landscape, the safe width in portrait — so a group can spread to the edge of the safe box and
  // no further.
  const crossRoom = portrait ? W - 2 * MARGIN : zoneH - 2 * Math.round(U * 0.02);
  const crossBase = (g: string[]) => (portrait ? fit.w * g.length : g.reduce((n, s) => n + fit.h(s), 0));
  const gapAt = (g: string[]) => {
    const n = Math.max(1, g.length - 1);
    const slack = Math.max(0, crossRoom - crossBase(g)) / n;
    return lerp(Math.min(U * 0.018, slack), slack, dolly.k);
  };

  // On the way IN the labels arrive with the room; on the way OUT they are there from frame one, because the
  // room they make was always around the subject and it is the RECEDING that is the argument.
  const ctxOn = DIR === 'out' ? 1 : easeOutCubic(clamp01(seg(t, 0.10, 0.52)));
  const readOn = reading ? easeOutCubic(clamp01(seg(t, 0.74, 0.94))) : 0;

  const labels: React.ReactNode[] = [];
  groups.forEach((g, gi) => {
    const sign = gi === 0 ? -1 : 1;
    const gap = gapAt(g);
    const cross = crossBase(g) + gap * Math.max(0, g.length - 1);
    let run = (portrait ? W / 2 : cy) - cross / 2;
    g.forEach((s, i) => {
      const h = fit.h(s);
      const left = portrait ? run : W / 2 + sign * off - fit.w / 2;
      const top = portrait ? cy + sign * off - h / 2 : run;
      labels.push(
        <div key={`${gi}-${i}`} style={{position: 'absolute', left: Math.round(left), top: Math.round(top),
          width: fit.w, textAlign: 'center', opacity: ctxOn, color: FG, filter: roomFilter,
          font: `600 ${fit.px}px/${fit.lead} var(--f-body, system-ui, sans-serif)`, letterSpacing: '0.01em'}}>
          {s}
        </div>);
      run += (portrait ? fit.w : h) + gap;
    });
  });

  const plateTop = Math.max(zTop, Math.round(cy - plateH / 2));
  const OVER = Math.round(U * 0.6);                 // the room is drawn larger than the frame so it can swell
  const CELL = Math.round(U * 0.075);               // one cell of the room, at rest

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* THE ROOM. Hairlines only — no type rides this layer, so it is free to swell past every edge, which
          is what a room does when you walk into it.

          THE FADE IS ON THE WRAPPER, NOT ON THE GRID. A mask is painted in the masked element's own box and
          is then carried by that element's transform, so a mask on the swelling layer swells with it: at
          2.25x its soft edge sits far outside the frame and the grid meets all four edges on a hard cut
          line — the opposite of what it was written for, and invisible in the frame where it was authored
          (scale 1). Held on a wrapper that never moves, the fade stays put in FRAME coordinates and the
          grid travels underneath it, which is what atmosphere does. It is centred on the swell's own origin
          rather than on the frame's, so the room opens from the point the subject occupies. */}
      <div style={{position: 'absolute', inset: 0, overflow: 'hidden',
        WebkitMaskImage: `radial-gradient(62% 58% at 50% ${((cy / H) * 100).toFixed(1)}%, #000 34%, transparent 96%)`,
        maskImage: `radial-gradient(62% 58% at 50% ${((cy / H) * 100).toFixed(1)}%, #000 34%, transparent 96%)`}}>
        <div style={{position: 'absolute', inset: -OVER,
          transform: `scale(${dolly.ground.toFixed(4)})`,
          transformOrigin: `50% ${(cy + OVER).toFixed(1)}px`,
          filter: roomFilter,
          backgroundImage:
            `repeating-linear-gradient(0deg, ${LINE_MAJOR} 0 2px, transparent 2px ${CELL * 4}px),`
            + ` repeating-linear-gradient(90deg, ${LINE_MAJOR} 0 2px, transparent 2px ${CELL * 4}px),`
            + ` repeating-linear-gradient(0deg, ${LINE} 0 1px, transparent 1px ${CELL}px),`
            + ` repeating-linear-gradient(90deg, ${LINE} 0 1px, transparent 1px ${CELL}px)`,
        }} />
      </div>

      {/* THE FOCAL PLANE the subject sits on, and the one layer that is NOT filtered: it is the depth the
          room is measured against, so softening it with the room would say the subject is receding too. */}
      <div style={{position: 'absolute', left: 0, right: 0, top: Math.round(cy),
        height: Math.round(U * 0.44), transform: 'translateY(-50%)',
        background: `radial-gradient(52% 50% at 50% 50%, ${ACC}1a, transparent 74%)`}} />

      {labels}

      {/* THE SUBJECT — no transform, no filter, one size for the whole shot. */}
      <div style={{position: 'absolute', left: Math.round((W - SW) / 2), top: plateTop, width: SW,
        textAlign: 'center'}}>
        <div style={{color: FG,
          font: `800 ${subjPx}px/${subjLead} var(--f-display, Inter, system-ui, sans-serif)`,
          letterSpacing: '-0.02em'}}>{subject}</div>
        {note ? (
          // `balance` because Chinese breaks between ANY two glyphs: a note a unit too wide for the subject's
          // column drops a single character onto a line of its own under the display word, which reads as a
          // typo rather than a wrap. Measured on the first Chinese render this register ever got — it was
          // invisible to the CJK gate until 2026-09-15, because its props are documented with JSDoc.
          <div style={{marginTop: Math.round(U * 0.022), color: DIM, textWrap: 'balance',
            font: `500 ${notePx}px/${noteLead} var(--f-body, system-ui, sans-serif)`}}>{note}</div>
        ) : null}
        {reading && readOn > 0 ? (
          // `balance` for the same reason as the note above it — and it matters more here, because the
          // reading is the line the whole move lands on. A single glyph left alone under it is the last
          // thing the shot shows.
          <div style={{marginTop: Math.round(U * 0.05), opacity: readOn, textWrap: 'balance',
            color: readableOn(dna?.bg ?? '#0b0f17', ACC, FG),
            font: `700 ${readPx}px/${readLead} var(--f-mono, "JetBrains Mono", monospace)`,
            letterSpacing: '0.07em', textTransform: 'uppercase'}}>{reading}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default DollyZoom;
