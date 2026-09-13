// SHOT · RackFocus — the beat TURNS, and the lens is what turns it.
//
// Two readings of the same subject stand at different depths. The obvious one is near and sharp; the one
// that actually matters is further back and soft, present from the first frame but unreadable. Halfway
// through, the focus RACKS: the near reading recedes — softer, dimmer, smaller, less saturated, all at once
// — and the far one comes forward. "Not this. That." said in optics, with no arrow, no split screen and no
// second panel.
//
// WHY THIS IS A REGISTER AND NOT A GARNISH. The peer-library study named focus as a capability gap in as
// many words: "no register uses focus as an argument". `runtime/focus.ts` was built afterwards and three
// registers use it — to make neighbours recede, which is scenery. FocalIsolation blurs everything but one
// phrase, which is emphasis. Neither MOVES the focus, and a focus that never moves cannot carry a turn: it
// says "look here", not "you were looking at the wrong thing". The rack is the whole argument.
//
// THE RECEDING READING NEVER LEAVES. A turn only lands if you can still see what you turned away from —
// blurred out of existence it is a cut, not a rack, and the beat reads as two unrelated frames. `focusAt`'s
// floors (0.34 opacity, 0.62 scale) are what keeps it in the room.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {focusAt, focusFilter, type Focus} from '../runtime/focus';
import {panAt} from '../runtime/depth';

export const DURATION = 170; // ~5.7s

export const RackFocus: React.FC<{
  before?: string; after?: string; beforeNote?: string; afterNote?: string; pivot?: string;
}> = ({
  before: BEFORE = 'What it looks like', after: AFTER = 'What it is',
  beforeNote: BNOTE = '', afterNote: ANOTE = '', pivot: PIVOT = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  const near = String(BEFORE ?? '').trim();
  const far = String(AFTER ?? '').trim();
  if (!near || !far) {
    throw new Error(
      'RackFocus needs BOTH `before` and `after`. The form is a lens moving from one reading to another; ' +
      'with one of them missing there is nothing to rack between and the shot is a blurred title card.');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 50% 40%, #151a24, #080a0f 72%)';
  const FG = dna?.fg ?? '#eef2f8';
  const ACC = dna?.accent ?? '#5b8cff';
  const DIM = dna?.dim ?? '#7c8699';

  // THE RACK. Held on the near reading, then one move, then held on the far one — a rack that starts at
  // frame one has nothing to turn AWAY from, and one that never settles is a hunt for focus rather than a
  // decision. Eased in and out because a lens is turned by a hand.
  const rack = easeInOutCubic(clamp01(seg(t, 0.40, 0.62)));

  // d = 0 is the thing in focus, 1 the furthest the shot still shows — so the two readings simply swap.
  // A heavier blur than the house default and the saturation anchor with it: here the focus is not a
  // third cue behind a scale and a fade, it is the ARGUMENT, and it has to be unmistakable at a glance.
  const LENS = {blurFrac: 0.0065, desat: 0.45};
  const nearF = focusAt(rack, U, LENS);
  const farF = focusAt(1 - rack, U, LENS);

  // CONTINUING LIFE, AND IT IS THE DEPTH CUE ITSELF. Measured, this shot's motion_p75 was 0.0000 against a
  // 0.0037 floor: hold, rack, hold means three quarters of its frames are identical, and by the library's
  // own instrument that is a still. The answer is not to shorten the holds — the holds are what make the
  // turn readable — but to give the frame the slow lateral breath a handheld camera always has. Two planes
  // at different depths separate under it at DIFFERENT rates, which is parallax, so the same motion that
  // clears the floor is also the cue that says these two readings are not on one plane.
  //
  // The curve is `panAt`, not a raw ramp: a monotone three-piece ramp that accelerates, holds speed and
  // decelerates, pinned by `test_camera_pan` as the exact signature `shake_qa` calls a TRAVEL rather than a
  // jitter. Writing my own would have been a second copy of a curve this repo already argued its way to.
  // ...and BOUNDED BY THE ROOM THE WIDEST BOX HAS. A lateral move on a centred block spends the margin on
  // each side, and the boxes are a fraction of W, so at 9:16 the near reading has 75px of margin and a
  // 130px travel would have walked it off the frame. The camera may spend what is there and no more.
  const NEAR_BOX = Math.round(W * (H > W * 1.1 ? 0.86 : 0.56));
  const BREATH = Math.min(U * 0.12, Math.max(0, (W - NEAR_BOX) / 2 - Math.round(W * 0.015)) * 2);
  const nearDrift = panAt(t) * BREATH;
  const farDrift = nearDrift * 0.38;              // the far plane is exempt from most of the move

  // ── the zone, and the two boxes inside it ────────────────────────────────────────────────────────────
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const zoneH = Math.max(160, zBot - zTop);
  const portrait = H > W * 1.1;

  // The near reading sits lower and larger, the far one higher and smaller — which is where a lens would
  // put them, and it means neither box has to be pushed aside to make room for the other.
  const NEAR_W = NEAR_BOX;
  const FAR_W = Math.round(W * (portrait ? 0.74 : 0.46));
  const NEAR_H = Math.round(zoneH * 0.30);
  const FAR_H = Math.round(zoneH * 0.26);

  // Both are fitted to the box they are given, at the size they are drawn at — `focusAt` only ever SHRINKS
  // a reading (minScale 0.62), so a fit made at full size can never overflow once the focus moves off it.
  const nearLead = leading(near, 1.06), farLead = leading(far, 1.06);
  const nearPx = fitBlockPx(near, NEAR_W, NEAR_H, Math.round(U * 0.115), {usable: 1, leading: nearLead});
  const farPx = fitBlockPx(far, FAR_W, FAR_H, Math.round(U * 0.095), {usable: 1, leading: farLead});
  const notePx = Math.round(U * 0.026);

  const blockH = (text: string, px: number, lh: number, box: number, note: string) =>
    Math.ceil(wrapLines(text, px, box) * px * lh
      + (note ? Math.round(U * 0.02) + wrapLines(note, notePx, box) * notePx * 1.35 : 0));

  const nearBlock = blockH(near, nearPx, nearLead, NEAR_W, BNOTE);
  const farBlock = blockH(far, farPx, farLead, FAR_W, ANOTE);

  // Laid out from the zone's own edges: the far reading in the upper third, the near one below it, with the
  // gap between them whatever is left. Both are measured blocks, so neither can grow into the other.
  // THE PAIR IS CENTRED IN THE ZONE, not packed against its top. Anchoring the far reading at `zTop + gap`
  // and hanging the near one under it left 360px of dead frame below the pair at 9:16 — the two readings
  // are the whole composition, so the room left over belongs equally to both ends of it.
  const gap = Math.max(Math.round(U * 0.05), Math.round((zoneH - farBlock - nearBlock) * 0.30));
  const stackH = farBlock + gap + nearBlock;
  const farTop = Math.max(zTop, zTop + Math.round((zoneH - stackH) / 2));
  const nearTop = Math.min(farTop + farBlock + gap, zBot - nearBlock);

  // The pivot line rides the rack itself and sits between the two readings, which is the one place on the
  // frame that belongs to neither of them.
  const pivotPx = Math.round(U * 0.028);
  const pivotOn = PIVOT ? easeOutCubic(clamp01(seg(t, 0.44, 0.60))) : 0;

  const reading = (
    text: string, note: string, px: number, lh: number, box: number, top: number,
    f: Focus, sharp: boolean, drift: number,
  ) => (
    <div style={{position: 'absolute', left: Math.round((W - box) / 2 + drift), top, width: box,
      textAlign: 'center', opacity: f.opacity,
      // transform-origin at the block's own centre so a receding reading shrinks in place rather than
      // drifting toward a corner — drift reads as the thing moving, not as the lens leaving it.
      transform: `scale(${f.scale})`, transformOrigin: '50% 50%',
      // `focusFilter` returns NOTHING for the sharp reading on purpose: any filter promotes the element to
      // its own compositing layer and the in-focus type would be resampled through a pipeline it does not
      // need. The whole point is that the sharp one is genuinely sharp.
      filter: focusFilter(f),
    }}>
      <div style={{color: sharp ? FG : DIM,
        font: `800 ${px}px/${lh} var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em'}}>
        {text}
      </div>
      {note ? (
        <div style={{marginTop: Math.round(U * 0.02), color: DIM,
          font: `500 ${notePx}px/1.35 var(--f-body, system-ui, sans-serif)`}}>{note}</div>
      ) : null}
    </div>
  );

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* A LENS HAS A PLANE OF FOCUS, and it is worth seeing. The band sits at whichever reading is sharp
          and travels with the rack — the only element on the frame that says the move was optical rather
          than two things changing size on their own. */}
      <div style={{position: 'absolute', left: Math.round(lerp(nearDrift, farDrift, rack)), right: 0,
        top: Math.round(lerp(nearTop + nearBlock / 2, farTop + farBlock / 2, rack)),
        height: Math.round(U * 0.5), transform: 'translateY(-50%)',
        background: `radial-gradient(60% 50% at 50% 50%, ${ACC}1c, transparent 72%)`}} />

      {/* Painted far-to-near so the nearer reading is the one in front, whichever is sharp. */}
      {reading(far, ANOTE, farPx, farLead, FAR_W, farTop, farF, rack > 0.5, farDrift)}
      {reading(near, BNOTE, nearPx, nearLead, NEAR_W, nearTop, nearF, rack <= 0.5, nearDrift)}

      {PIVOT && pivotOn > 0 ? (
        <div style={{position: 'absolute', left: 0, right: 0,
          top: Math.round((farTop + farBlock + nearTop) / 2), transform: 'translateY(-50%)',
          textAlign: 'center', padding: `0 ${Math.round(W * 0.08)}px`, opacity: pivotOn,
          color: readableOn(dna?.bg ?? '#0b0f17', ACC, FG),
          font: `700 ${pivotPx}px/${leading(PIVOT, 1.3)} var(--f-mono, "JetBrains Mono", monospace)`,
          letterSpacing: '0.08em', textTransform: 'uppercase'}}>
          {PIVOT}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default RackFocus;
