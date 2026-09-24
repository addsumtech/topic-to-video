// SHOT · LastLeg — a run that covers almost the whole distance and STOPS, with the uncovered remainder left
// lit differently and labelled. The argument shape is "it gets you most of the way, and the rest is yours".
//
// WHY THIS EXISTS AS A REGISTER. The claim "it does 90% and leaves the last part to you" is one every product
// film has to make at some point — an automation that handles nine steps of ten, a funnel that drops at the
// end, a coverage map with a hole. Said in words it is a shrug; drawn, it has an exact shape: one continuous
// track, a stretch of it carried, and a visibly UNCARRIED tail that nobody hands off. A viewer reads the gap
// before they read a single label, which is the test this register is built to pass.
//
// FRAME-CRAFT, deliberately at launch grade. The track runs FULL BLEED and is cropped by both edges: the
// distance is longer than the frame, which is the point, and a route that politely inset itself would be
// arguing the opposite. The display word is cropped too, and INVERTS across the boundary. Both were illegal
// here until the action-safe gate was found to be inverted — it blocked full-bleed technique and missed
// every real cut — and text_safe_qa replaced it by asking the DOM whether any TYPE is actually destroyed.
//
// THE LIGHT IS THE ARGUMENT, not a finish on top of it. Ground that has been CARRIED is lit; ground still to
// be walked is dark; the boundary between them is the head of the run, and it sweeps the frame and then
// stops. So the shot's luminance arc and its meaning are the same fact, and hiding the caption still leaves
// "it took me this far and stopped" legible.
//
// EACH LEG IS LIT BY ITS OWN FLAG. The carry used to stop at `nCarried / legs.length` of the track and a leg's
// chip lit when its POSITION fell behind that head (`lx < headX`) — `carried` was only ever counted, never read
// per leg. So `carried: [false, true, true, true]` drew leg 1 lit (it sits first) and the last carried leg dark
// in the "yours to walk" tail: the frame asserted the opposite of the film for two of four legs. And the demo
// only looked right because its carried legs happened to come first and the count fraction happened to land
// between the right ticks. Now the carry stops between the last carried leg and the first uncarried one, each
// chip lights only if its own `carried` is true, and a pattern this shape cannot draw — a carried leg after an
// uncarried one — throws instead of being drawn as something else. The legs were also cut at six with
// `.slice(0, 6)`; more than six now throws, a leg needs a `label`, and a film that marks no leg's `carried`
// at all (not even `false`) is refused, because the split is the whole claim and none was given.
//
// The first version of this register put a lit rail and a pulsing field on a static dark ground. It measured
// 15.3% ink (over the 12% floor) but frame-diff p75 0.0033 and luminance span 0.075 — under BOTH the motion
// and light floors film_energy_qa derives from real launch films. Local animation on a still ground is what
// "it could have been HTML" looks like from the inside; the ground itself has to move.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
// SHOT_LUMA 'dark' / DNA_GROUND_TOKEN 'bg', both MEASURED (0.003): the lit plane fades out across the
// caption band, so what the burned caption sits on is the film's own dark ground for the whole shot,
// whatever the carry is doing above it. Keep that fade if this register is ever re-laid-out.

const BG_D0 = '#07090f', FG_D0 = '#eef2f8', ACC_D0 = '#4f8cff', DIM_D0 = '#6c7788', LINE_D0 = '#1b2330';

type Leg = {label?: string; carried?: boolean};

export const MAX_LEGS = 6;

const DEFAULT_LEGS: Leg[] = [
  {label: 'brief', carried: true}, {label: 'draft', carried: true},
  {label: 'check', carried: true}, {label: 'send', carried: false},
];

// CJK-EXEMPT (tight leading, no floor): the display line is whiteSpace:'nowrap' — it cannot wrap, so its lines cannot collide.
export const LastLeg: React.FC<{
  kicker?: string;      // what this frame is about
  display?: string;     // the one big word; cropped by the frame on purpose
  legs?: Leg[];         // the run — `carried` marks the stretch that is covered for you
  gapLabel?: string;    // the label on the uncovered tail
  carriedLabel?: string;// the label on the covered stretch
  note?: string;        // one line under the track
}> = ({kicker = '', display = '', legs: LEGS = DEFAULT_LEGS,
       gapLabel = '', carriedLabel = '', note = ''} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const ACC2 = dna?.accent2 ?? ACC;
  const DIM = dna?.dim ?? DIM_D0;
  const LINE = dna?.line ?? LINE_D0;
  const ON = dna?.onAccent ?? '#fff';
  const disp = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';
  const mono = dna?.fontMono ?? 'ui-monospace, monospace';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';

  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const base = Math.min(W, H);
  const zoneTop = CONTENT_TOP;
  const zoneBottom = H - captionBand(W, H);
  const portrait = H > W;

  // The run as the film gave it — every leg, each with its own flag (see the header for what this replaces).
  if (!Array.isArray(LEGS) || LEGS.length < 1 || LEGS.length > MAX_LEGS) {
    throw new Error(
      `LastLeg needs 1-${MAX_LEGS} \`legs\` (got ${Array.isArray(LEGS) ? LEGS.length : typeof LEGS}). Every leg is a chip ` +
      'in the tick lane and a dropped one would shorten the run the film is measuring; group legs into at most six.');
  }
  const legs = LEGS.map((l, i) => {
    const label = String(l?.label ?? '').trim();
    if (!label) throw new Error(`LastLeg: leg ${i + 1} has no \`label\`.`);
    if (l?.carried != null && typeof l.carried !== 'boolean') {
      throw new Error(`LastLeg: leg ${i + 1} ("${label}") has carried=${JSON.stringify(l.carried)}; it must be true or false.`);
    }
    return {label, carried: l?.carried === true};
  });
  if (LEGS.every((l) => l?.carried == null)) {
    throw new Error('LastLeg: no leg says whether it is `carried`. The register draws exactly that split — the ' +
      'stretch covered for you and the tail that is not — so mark each leg `carried: true` or `carried: false`.');
  }
  const nCarried = legs.findIndex((l) => !l.carried) < 0 ? legs.length : legs.findIndex((l) => !l.carried);
  const late = legs.findIndex((l, i) => i > nCarried && l.carried);
  if (late >= 0) {
    throw new Error(
      `LastLeg: leg ${late + 1} ("${legs[late].label}") is carried but leg ${nCarried + 1} ("${legs[nCarried].label}") ` +
      'before it is not. This register draws ONE carried stretch from the start and then the uncovered tail, so ' +
      'that pattern would be drawn as something the film did not say. If the order is not the claim, list the ' +
      'carried legs first; if it is, use a register that marks each item on its own.');
  }

  // The track OVERRUNS the frame on both sides: the distance does not begin or end on screen.
  const overrun = W * 0.14;
  const x0 = -overrun, x1 = W + overrun;
  // The tick lane's positions, shared by the chips and by where the carry stops.
  const tickPad = W * 0.07;
  const tickX = (i: number) => tickPad + ((W - tickPad * 2) / Math.max(1, legs.length - 1)) * i;
  const trackY = Math.round(zoneTop + (zoneBottom - zoneTop) * (portrait ? 0.58 : 0.62));
  const railH = Math.max(4, Math.round(base * 0.012));

  const draw = easeOutCubic(clamp01(seg(t, 0.10, 0.62)));    // the carry advances
  const stop = easeOutCubic(clamp01(seg(t, 0.60, 0.74)));    // it halts, hard
  const gapIn = easeOutCubic(clamp01(seg(t, 0.70, 0.88)));   // the uncovered tail is named
  const dispIn = easeOutCubic(clamp01(seg(t, 0.04, 0.34)));

  // The carry stops BETWEEN the last carried leg and the first uncarried one — read off the legs themselves.
  // Nothing carried: it never leaves the origin. Everything carried: it runs off the far edge.
  const carriedX = nCarried === 0 ? x0 : nCarried === legs.length ? x1
    : (tickX(nCarried - 1) + tickX(nCarried)) / 2;
  const headX = x0 + (carriedX - x0) * draw;

  // The CARRIED GROUND — a lit plane that sweeps to the head of the run and stops. This is the frame's
  // luminance arc and its argument at once: everything behind the head has been walked for you.
  // FULL BLEED to every edge, and FADED OUT across the caption band rather than stopped at it.
  //
  // Stopping at the band drew a hard horizontal edge above the subtitle, which is precisely the thing this
  // project forbids: a separate strip for the caption instead of the caption sitting on the frame's own
  // ground. shot_still_qa measured that edge at 100% band coverage. Fading the plane out leaves the film's
  // own dark ground showing through under the subtitle — one stable ground to contrast against for the whole
  // shot, whatever the carry is doing above it — with no bar and no step.
  const fadeFrom = ((zoneBottom - base * 0.10) / H) * 100;
  const litFade = `linear-gradient(to bottom, #000 ${fadeFrom.toFixed(1)}%, transparent ${((zoneBottom + base * 0.02) / H * 100).toFixed(1)}%)`;
  const lit = {
    position: 'absolute' as const, left: 0, top: 0, width: Math.max(0, headX), height: H,
    background: `linear-gradient(100deg, ${ACC2}, ${ACC})`,
    WebkitMaskImage: litFade, maskImage: litFade,
  };

  // WHAT FILLS THE CARRIED GROUND. The first version tiled it with rounded dashes, which measured as 49.8%
  // ink and read as lint: a viewer cannot say what one of them is, so the density was decoration wearing
  // content's clothes — and film_energy_qa went green on it, which is worth knowing about that gate.
  //
  // These are set as PARAGRAPH LINES: ragged-width rules grouped into blocks with a gap between them, the
  // universal shorthand for "text, a great deal of it". On this beat that is the argument itself — the
  // assistant fills every metre it covers with words, and the metre it does not cover has none. The idiom
  // generalises: whatever a register's carry produces, the carried ground should be full of THAT.
  const units: React.ReactNode[] = [];
  const lineH = Math.max(3, Math.round(base * 0.011));
  const lineGap = Math.round(base * 0.026);
  const blockGap = Math.round(base * 0.030);
  const colW = Math.round(W * 0.30);
  const fieldTop = Math.round(zoneTop + base * 0.13);
  const travel = t * base * 0.5;
  let y = fieldTop, block = 0;
  while (y < zoneBottom - base * 0.14) {
    const inBlock = 4;
    for (let k = 0; k < inBlock && y < zoneBottom - base * 0.14; k++, y += lineGap) {
      for (let cx = -colW; cx < W + colW; cx += colW) {
        const i = Math.round((cx + block * 7 + k) / 10);
        const ph = ((i * 41 + k * 17 + block * 23) % 100) / 100;
        // the last line of a block is short, the way a paragraph ends
        const wRatio = k === inBlock - 1 ? 0.28 + 0.34 * ph : 0.72 + 0.26 * ph;
        const drift = ((block % 2) ? -1 : 1) * travel;
        const px = cx + (((drift % colW) + colW) % colW);
        if (px > headX) continue;                        // only carried ground holds the words
        // ...all of each word-line, not just its start: a line beginning a little behind the head used to run on
        // across it, printing "carried work" into the dark tail the frame says is still yours to walk.
        const lineW = Math.min(Math.round((colW - blockGap) * wRatio), Math.max(0, headX - px));
        if (lineW < lineH * 2) continue;
        units.push(
          <div key={`${block}-${k}-${cx}`} style={{position: 'absolute', left: px,
            top: y, width: lineW, height: lineH,
            borderRadius: lineH, background: ON, opacity: 0.30 + 0.28 * ph}} />
        );
      }
    }
    y += blockGap;
    block += 1;
  }

  // The tick lane sits ABOVE the display word, not across it: as a chip over a 300px glyph it read as
  // something dropped on the type rather than a scale the type stands on.
  const tickLane = zoneTop;
  const dispTop = Math.round(zoneTop + base * 0.085);
  const dispSize = Math.round(base * (portrait ? 0.20 : 0.28));

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {/* the ground that has been CARRIED — lit, and it sweeps */}
      <div style={lit} />

      {/* the work it carried, riding the lit ground */}
      {units}

      {/* the display word, cropped by the frame AND inverted across the boundary: the part of the sentence
          that has been carried reads on the lit ground, the rest is left in the dark. One word, two grounds,
          which is the whole claim in a single object. The bright half is clipped by a sub-frame container —
          a deliberate crop, which is exactly what text_safe_qa reads as intent rather than as an accident. */}
      {display ? (
        <>
          <div style={{position: 'absolute', left: -Math.round(base * 0.045), top: dispTop,
            opacity: dispIn, transform: `translateX(${(1 - dispIn) * -base * 0.06}px)`,
            font: `900 ${dispSize}px/0.86 ${disp}`, letterSpacing: '-0.03em',
            color: FG, whiteSpace: 'nowrap'}}>{display}</div>
          <div style={{position: 'absolute', left: 0, top: 0, width: Math.max(0, headX), height: H,
            overflow: 'hidden'}}>
            <div style={{position: 'absolute', left: -Math.round(base * 0.045), top: dispTop,
              opacity: dispIn, transform: `translateX(${(1 - dispIn) * -base * 0.06}px)`,
              font: `900 ${dispSize}px/0.86 ${disp}`, letterSpacing: '-0.03em',
              color: ON, whiteSpace: 'nowrap'}}>{display}</div>
          </div>
        </>
      ) : null}

      {/* The kicker sits BOTTOM-right, mirroring the note at bottom-left. At the top right it shared the corner
          with the run's last tick and the two labels overprinted into an unreadable smear — and on this beat
          they were the same words, so the frame said one thing twice and neither legibly. */}
      {/* THE RAIL PRINTS THROUGH A RIGHT-ANCHORED KICKER, and only its COLOUR was ever handling that.
          `headX` is data — it moves with how many legs are carried — while this box was pinned to the
          right margin with no width, so for any film whose carry lands the rail inside the kicker's span
          the stop bar is painted straight over the first glyph. Measured on the film that found it: the
          rail sat at x≈1510 and the kicker ran 1492–1824, so `排练的是取出,不是内容` read as
          `练的是取出,不是内容` with the first character sliced. No gate sees this — nothing is cut off
          by the CANVAS, so `text_safe_qa` is correctly silent; it took a person looking at a 2x crop.
          The kicker now ends left of the rail whenever the rail is in its way, and is bounded so it can
          never grow back into it. */}
      {kicker ? (
        <div style={{position: 'absolute', right: Math.round(W * 0.05),
          top: zoneBottom - Math.round(base * 0.062), opacity: dispIn,
          // BOUNDED to the room RIGHT of the rail, not pushed left of it. The rail spans the full zone
          // height, so there is no vertical escape; pushing the kicker left instead lands it in `note`,
          // which is what a first repair did — one collision traded for another. Right of the rail is
          // the uncovered tail, and it is empty by construction. Too narrow to set means the kicker is
          // simply not drawn: `note` already says what the frame is about, and a missing kicker is a
          // visible absence rather than two strings printed through each other.
          maxWidth: Math.max(0, Math.round(W * 0.95 - headX - railH - base * 0.02)),
          textAlign: 'right',
          letterSpacing: '0.16em', color: headX > W * 0.95 ? ON : DIM,
          font: `700 ${Math.round(base * 0.024)}px/1.2 ${mono}`}}>{kicker}</div>
      ) : null}

      {/* the road AHEAD — only the unwalked part is drawn, dashed, running off the right edge. Drawing a rail
          across the carried ground too would put a black bar through the lit plane and read as a divider;
          what the frame needs to show is that the distance CONTINUES past where the carry stopped. */}
      <div style={{position: 'absolute', left: headX, top: trackY, width: Math.max(0, x1 - headX),
        height: railH, opacity: 0.55 * draw,
        backgroundImage: `repeating-linear-gradient(90deg, ${DIM} 0 ${railH * 3}px, transparent ${railH * 3}px ${railH * 6}px)`}} />

      {/* where it STOPS — a hard edge, not a fade */}
      <div style={{position: 'absolute', left: headX - railH, top: zoneTop,
        width: railH * 2, height: zoneBottom - zoneTop, background: ON, opacity: 0.9 * draw,
        boxShadow: `0 0 ${Math.round(base * 0.07)}px ${ACC}`}} />

      {/* the UNCOVERED tail, named, standing in the dark */}
      {/* CLAMPED into the frame. The head starts at the track's overrunning origin, so with nothing carried
          yet the label was positioned off-frame left and vanished — an author passing `gapLabel` saw no label
          and no complaint. Degrade visibly: if the carry covers everything, the label sits at the right
          margin and reads as the contradiction it is, rather than being dropped. */}
      {gapLabel ? (
        <div style={{position: 'absolute',
          left: Math.min(Math.max(headX + base * 0.03, W * 0.05), W * 0.74),
          // ...and BOUNDED on the right. The clamp above stopped the label starting off-frame; nothing
          // stopped it ENDING there. With no maxWidth a 14-character CJK label set to x≈1911 of 1920 — a
          // 9px margin — and wrapped mid-word, splitting 代写 across two lines. Give it the room that is
          // actually left on the frame, so it wraps where a typesetter would.
          maxWidth: Math.round(W * 0.94 - Math.min(Math.max(headX + base * 0.03, W * 0.05), W * 0.74)),
          top: trackY + railH * 3, opacity: gapIn, color: FG,
          font: `800 ${Math.round(base * 0.042)}px/1.2 ${body}`,
          borderLeft: `${Math.max(2, Math.round(base * 0.004))}px solid ${FG}`,
          paddingLeft: Math.round(base * 0.018)}}>{gapLabel}</div>
      ) : null}
      {carriedLabel ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.05), top: zoneBottom - Math.round(base * 0.115),
          opacity: draw, background: ON, color: ACC, borderRadius: Math.round(base * 0.008),
          padding: `${Math.round(base * 0.008)}px ${Math.round(base * 0.016)}px`,
          font: `700 ${Math.round(base * 0.026)}px/1.2 ${mono}`}}>{carriedLabel}</div>
      ) : null}

      {/* leg ticks — countable distance. On a CHIP, in its own lane above the text field: set as bare type
          they were dark-on-dark against the lines behind them and unreadable at 26px, which is the one
          failure mode this project treats as non-negotiable (a viewer must decode every element in ~1s). */}
      {legs.map((l, i) => {
        const lx = tickX(i);
        const on = l.carried && lx < headX;   // its OWN flag, lit as the carry reaches it
        return (
          <div key={i} style={{position: 'absolute', left: lx, top: tickLane,
            transform: 'translateX(-50%)', opacity: on ? draw : 0.85 * gapIn,
            background: on ? ON : 'transparent',
            border: on ? 'none' : `1px solid ${DIM}`,
            color: on ? ACC : DIM, whiteSpace: 'nowrap',
            borderRadius: Math.round(base * 0.006),
            padding: `${Math.round(base * 0.007)}px ${Math.round(base * 0.014)}px`,
            font: `700 ${Math.round(base * 0.024)}px/1.2 ${mono}`}}>{l.label}</div>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.05),
          top: zoneBottom - Math.round(base * 0.062),
          width: W * 0.62, opacity: gapIn, color: headX > W * 0.62 ? ON : DIM,
          font: `400 ${Math.round(base * 0.026)}px/1.45 ${body}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default LastLeg;
