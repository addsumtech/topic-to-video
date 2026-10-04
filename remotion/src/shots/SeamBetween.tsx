// SHOT · SeamBetween — two masses of the same material, and the SPACE BETWEEN THEM is the subject.
//
// WHAT IT ARGUES. Two masses stand apart. What the frame is about is neither of them: it is the strip of
// nothing they leave between their facing edges — and the register says so by MEASURING it, with a
// dimension line drawn under the gap and the gap's own name set beneath. Then, in the second state, the
// two travel together until the space is gone and survives only as the line of the joint. The same form
// at two states is an argument with a beginning and an end: the gap was the cost; the gap was closed.
//
// WHY NOTHING ELSE IN THE LIBRARY SAYS IT. The library could already draw a comparison between two
// parties (`VersusSplit`, `EdCompare`, `RealVersus` — the two sides are the subject and the divider is
// furniture), a transfer that loses fields across a handoff (`CarryOver` — the loss is the subject, the
// boundary is assumed), a run that stops short of its distance (`LastLeg`), and several things seating
// onto one standard (`PortRail` — a fit, where the parts are the subject and there are three to six of
// them). In every one of those the space between is drawn and means nothing. Here it is the only thing
// that is MEASURED — the masses are named and then left alone, and the dimension line points at the air.
//
// WHY IT IS REUSABLE. The argument shape is "the expensive thing is the interface, not either side":
// two teams and the handover between them, two datastores and the sync, two codebases and their bridge,
// two jurisdictions and the border, a merger that removes a reconciliation step, a migration that
// deletes an integration. The topic arrives entirely through props — the masses, the gap's name, the
// name of the single mass once it is shut — so the form speaks any language and any pairing.
//
// NOTHING IS EVER SET ON THE ACCENT FILL. The gap is painted in the DNA's second accent, which on a
// light stock is frequently a colour that CANNOT carry type (measured on this file's first consumer:
// 1.59:1 on the paper). So the gap is a FILL and only a fill, and every word on the frame — the masses'
// names, the gap's name, the whole's name — sits on the sheet or on the paper. That is a property of
// the design, not of one film's palette: a strip narrow enough to be the subject of a dimension line is
// never wide enough to set a word in anyway.
//
// THE SECOND STATE COMES FROM A PROP, and from exactly one. The gap shuts when — and only when — the
// film NAMES what the two became (`whole`); nothing is inferred from the beat's index, the clock or a
// hash. It was two props, `state` beside `whole`, until it was noticed that two props for one fact make
// two of the four combinations invalid and make the register unrenderable to the audit that feeds every
// string prop a sentence. See `whole` below.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, lerp, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, fitBlockPx, inkBlockH, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix, shade, readableOn, dimOn, contrastOf} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 180; // 6s

// THE FLOORS ARE THE POINT AT WHICH TYPE STOPS BEING A WORD, not the size anything is aimed at. Copy
// WRAPS and SHRINKS to the room it has first; these say when there is no room left worth drawing into,
// and the register throws with the measured size rather than setting a smudge nobody can read.
/** a mass's name, as a share of the frame's short side */
export const MIN_NAME_FRAC = 0.016;
/** the gap's name — the frame's pointed remark, set smaller than a mass name by design */
export const MIN_SEAM_NAME_FRAC = 0.014;
/** a masthead under this is not a masthead — split the beat, or shorten the word */
export const MIN_TITLE_FRAC = 0.024;

const BG_D0 = '#f3f0e8', FG_D0 = '#161512', DIM_D0 = '#6b6660',
  ACC_D0 = '#b2452c', ACC2_D0 = '#0f9c8c', SURF_D0 = '#fbf9f3', LINE_D0 = '#d9d2c4';

export const SeamBetween: React.FC<{
  /** a small standing label above the masthead */
  kicker?: string;
  /** the masthead — the ONE word this frame is about; it is what changes between a film's two states */
  title?: string;
  /** the mass on the left — required, because an unnamed block is furniture */
  left?: string;
  /** the mass on the right */
  right?: string;
  /** what the SPACE between them is — the thing the dimension line measures */
  seamLabel?: string;
  /**
   * The name of the single mass the two become — and, by being there, the register's SECOND STATE:
   * name what they became and the gap SHUTS until the accent survives as the line of the joint; leave
   * it out and the gap holds open and measured.
   *
   * WHY THE STATE IS NOT ITS OWN PROP. It was, as `state: 'open' | 'closed'` beside this one, and two
   * props encoding one fact means two of the four combinations are invalid — so the register threw on
   * both, which is the honest thing to do with a contradiction and still the wrong design. It also made
   * the register unrenderable to `scripts/cjk_type_qa.py`, which feeds every declared string prop and
   * therefore always produced a contradiction: the ONE audit that can see a string a register declined
   * to draw reported a coverage hole at all five aspects instead of a measurement. One prop carrying the
   * fact cannot contradict itself, loses no expressiveness (the closed state always needed this name),
   * and the sweep can render it.
   */
  whole?: string;
  /** the standfirst under the form */
  note?: string;
}> = ({
  // NO DEMO DEFAULT. Every other string here has one, because a register has to render standalone — but a
  // kicker is optional furniture, and a default prints on every film that simply does not pass one. This
  // shot's first consumer rendered `where the cost actually is` in English above a Chinese masthead, on a
  // film whose own chrome was already carrying a breadcrumb in that exact position.
  kicker = '',
  title = 'The Gap',
  left = 'one system',
  right = 'another system',
  seamLabel = 'everything that has to cross',
  whole = '',
  note = 'The expensive part is not either side. It is the distance between them.',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();

  const TITLE = String(title ?? '').trim();
  const KICK = String(kicker ?? '').trim();
  const NOTE = String(note ?? '').trim();
  const L = String(left ?? '').trim();
  const R = String(right ?? '').trim();
  const SEAM = String(seamLabel ?? '').trim();
  const WHOLE = String(whole ?? '').trim();

  /** THE SECOND STATE IS THE PRESENCE OF `whole`, and nothing else — not an index, not the clock. */
  const CLOSED = WHOLE.length > 0;

  if (!L || !R) {
    throw new Error(
      'SeamBetween needs both `left` and `right`. The gap is the space BETWEEN two named things; with one ' +
      'of them unnamed the frame is a block beside a block and the measurement points at nothing.');
  }
  if (!SEAM) {
    throw new Error(
      'SeamBetween needs a `seamLabel`. The dimension line under the gap is the whole reason this register ' +
      'exists — unnamed, the gap reads as the margin between two panels instead of as the subject.');
  }
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const GROUND = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const ACC2 = dna?.accent2 ?? ACC2_D0;
  const SHEET = dna?.surface ?? SURF_D0;
  const LINE = dna?.line ?? LINE_D0;
  const RAD = dna?.radius ?? 2;
  const BW = Math.max(1, dna?.borderWidth ?? 1);
  const disp = dna?.fontDisplay ?? 'var(--f-display, Inter, system-ui, sans-serif)';
  const body = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';

  // Ink is picked by MEASUREMENT against the surface it lands on, never assumed from the token names: this
  // register is used on light stock and on dark, and `fg` is only the right ink on one of them.
  const INK = readableOn(SHEET, FG, GROUND, '#ffffff', '#0a0d14');
  const INK_PAPER = readableOn(GROUND, FG, '#ffffff', '#0a0d14');
  // THE MEASUREMENT SPEAKS IN THE ACCENT, when the accent can be read on the page. `readableOn` returns
  // the MOST legible candidate, which is always the ink — so asking it here threw away the hierarchy the
  // frame needs (masses in ink on their stock, the measurement in the film's other voice on the paper) and
  // drew the dimension in the same black as everything else. Ask the question that is actually being
  // asked: is the accent readable here at all?
  const RULE_INK = contrastOf(ACC, GROUND) >= 4.5 ? ACC : INK_PAPER;   // the dimension line + the gap's name
  const DIM_PAPER = dimOn(GROUND, INK_PAPER, 4.5);
  // The facing edge of each mass is the CUT EDGE of the stock: a solid band of the sheet's own ink. It is
  // what gives the accent strip two hard sides, so the gap reads as a kerf between two masses rather than
  // as a coloured panel laid on the page — and when the two meet it is the pair of edges that touch.
  const EDGE = mix(INK, SHEET, 0.08);
  // The shadow the near sheet throws onto the page: the ground's OWN hue taken down, at low alpha, so a
  // light film does not gain a grey it never declared. Deliberately `shade`, NOT `plane` — `plane` asks the
  // tone which direction has room and would LIFT a dark film's shadow toward white, and a contact shadow
  // that is lighter than the page it falls on is not a shadow. Light only ever goes one way.
  const SHADOW = shade(GROUND, 0.62) + '33';

  const U = Math.min(W, H);
  const M = Math.round(W * 0.078);
  const colW = W - 2 * M;
  const top = CONTENT_TOP;
  const bottom = contentBottom(W, H);

  // ── TYPE. Long copy WRAPS and shrinks; it is refused only when it cannot be drawn at a size a viewer
  //    could read at all. The first cut fitted every string to ONE line and threw the moment that line
  //    went under a comfortable size — which refused ordinary sentences, and made the register
  //    unrenderable to the sweep that feeds every string prop a sentence on purpose. Refusing a silent
  //    DROP is the house rule; refusing to wrap is not the same thing. ─────────────────────────────────
  const fitted = (text: string, boxW: number, boxH: number, base: number, lh: number,
                  floorFrac: number, what: string) => {
    const px = fitBlockPx(text, boxW, boxH, base, {leading: lh});
    const floor = Math.round(U * floorFrac);
    if (px < floor) {
      throw new Error(
        `SeamBetween: ${what} (${[...text].length} characters) only fits the room this frame has at ${px}px, ` +
        `under the ${floor}px floor at which it is still a word on a screen. Shorten it, or give the beat a ` +
        'register that sets running text.');
    }
    return {px, lines: wrapLines(text, px, boxW)};
  };

  const kickPx = Math.round(U * 0.023);
  const kickH = KICK ? inkBlockH(kickPx) + Math.round(U * 0.014) : 0;
  const titleBoxW = colW * 0.78;
  const titleFit = TITLE
    ? fitted(TITLE, titleBoxW, U * 0.22, Math.round(U * 0.078), leading(TITLE, 1.06), MIN_TITLE_FRAC, '`title`')
    : {px: 0, lines: 0};
  const titlePx = titleFit.px;
  const titleH = TITLE ? inkBlockH(titlePx, titleFit.lines) + Math.round(U * 0.026) : 0;
  const ruleY = top + kickH + titleH;

  const notePx = NOTE
    ? fitBlockPx(NOTE, colW, U * 0.14, Math.round(U * 0.027), {leading: leading(NOTE, 1.45)})
    : 0;
  const noteH = NOTE
    ? Math.ceil(wrapLines(NOTE, notePx, colW) * notePx * leading(NOTE, 1.45)) + Math.round(U * 0.030)
    : 0;

  // ── THE FORM ────────────────────────────────────────────────────────────────────────────────────────
  const gapOpen = Math.round(W * 0.040);
  // SHUT is a LINE, not zero: the accent is squeezed until it is the joint, and a joint you cannot see is
  // an argument that the two were always one.
  const gapShut = Math.max(4, Math.round(U * 0.0055));
  // THE PAIR DOES NOT RUN THE FULL MEASURE. Set edge to edge across the column, two masses 235px tall and
  // 768 wide read as ONE strip with a coloured stripe in it — rendered and looked at, which is the only
  // way that is visible. A mass has to be shaped like a mass, so on a wide frame the form takes two thirds
  // of the column and the page keeps its margins; on a narrow one the column is already narrow enough.
  // ...and a SQUARE is not a wide frame: at 1:1 the `W >= H` test was true, so the form took two thirds of
  // an already-square column and left a third of the page empty either side. The threshold is the one
  // `CarryOver` uses for the same decision.
  const formW = Math.round(colW * (W >= H * 1.15 ? 0.66 : 1));
  const slabW = Math.round((formW - gapOpen) / 2);
  const edgeW = Math.max(2, Math.round(U * 0.0065));

  const formTop = ruleY + Math.round(U * 0.038);
  const formBot = bottom - noteH;
  const formH = Math.max(Math.round(U * 0.24), formBot - formTop);

  // Under the masses: the extension lines drop, the measure runs between them, the gap's name sits under
  // that — and, once there is no gap, the whole's name stands in the same place. All of it is on the
  // PAPER; nothing is ever set on the accent.
  const seamBoxW = colW * 0.62;
  const wholeBoxW = colW * 0.80;
  const seamFit = fitted(SEAM, seamBoxW, U * 0.11, Math.round(U * 0.029), leading(SEAM, 1.3),
    MIN_SEAM_NAME_FRAC, '`seamLabel`');
  const wholeFit = WHOLE
    ? fitted(WHOLE, wholeBoxW, U * 0.13, Math.round(U * 0.046), leading(WHOLE, 1.18), MIN_NAME_FRAC, '`whole`')
    : {px: 0, lines: 0};
  const dropH = Math.round(U * 0.030);
  const labelGap = Math.round(U * 0.022);
  const belowH = dropH + labelGap
    + Math.max(inkBlockH(seamFit.px, seamFit.lines), WHOLE ? inkBlockH(wholeFit.px, wholeFit.lines) : 0);
  // THE CAP IS THE MASS'S OWN PROPORTION, not a fraction of the frame. A flat `U * 0.34` is the right
  // height on a 16:9 page and a THIRD of the room a 9:16 one has: rendered at portrait, the form sat at
  // the top of the band with 550px of empty paper under it before the standfirst. A sheet may be up to
  // half again as tall as it is wide — past that it is a column, not a sheet — and on a wide frame the
  // band is what binds anyway, so this changes nothing at 16:9.
  const slabH = Math.min(Math.round((formH - belowH) * 0.94), Math.round(slabW * 1.6));

  // The masses' names are sized LAST, because the room they have is what the form left them.
  const nameBoxW = slabW * 0.84;
  const nameBoxH = Math.max(U * 0.05, slabH * 0.62);
  const nameBase = Math.round(U * 0.038);
  const namePx = Math.min(
    fitted(L, nameBoxW, nameBoxH, nameBase, leading(L, 1.2), MIN_NAME_FRAC, '`left`').px,
    fitted(R, nameBoxW, nameBoxH, nameBase, leading(R, 1.2), MIN_NAME_FRAC, '`right`').px);
  const blockH = slabH + belowH;
  // Centred in the band it has, but never floated: on a tall frame the band is most of the page and a
  // centred block leaves a third of it empty above the form.
  const formY = formTop + Math.min(Math.max(0, Math.round((formH - blockH) / 2)),
    Math.round(U * (W >= H * 1.15 ? 0.06 : 0.16)));

  // ── TIME. Each state has its own beat map; the CLOSED one replays the OPEN one first, because a
  //    bookend only lands if you watch the same picture you were shown at the start being finished. ────
  // THE HAND-OFF IS SEQUENTIAL, NOT A CROSS-FADE. Both labels stand in the same place under the form, so
  // one window driving "the gap's name out" and "the whole's name in" together printed the two strings on
  // top of each other for a third of a second — visible only in a rendered mid-clip frame, which is where
  // it was found. The old name is gone before the new one starts.
  const T = CLOSED
    ? {arrive: [0.02, 0.18], light: [0.16, 0.28], measure: [0.26, 0.40], name: [0.34, 0.46],
       shut: [0.46, 0.72], handOut: [0.50, 0.62], handIn: [0.72, 0.84]}
    : {arrive: [0.04, 0.26], light: [0.24, 0.40], measure: [0.38, 0.56], name: [0.56, 0.70],
       shut: [1, 1], handOut: [1, 1], handIn: [1, 1]};

  const arrive = easeOutCubic(clamp01(seg(t, T.arrive[0], T.arrive[1])));
  const light = clamp01(seg(t, T.light[0], T.light[1]));
  const measure = easeOutCubic(clamp01(seg(t, T.measure[0], T.measure[1])));
  const nameIn = clamp01(seg(t, T.name[0], T.name[1]));
  const shut = CLOSED ? easeInOutCubic(clamp01(seg(t, T.shut[0], T.shut[1]))) : 0;
  const handOut = CLOSED ? clamp01(seg(t, T.handOut[0], T.handOut[1])) : 0;
  const handIn = CLOSED ? clamp01(seg(t, T.handIn[0], T.handIn[1])) : 0;

  const gap = lerp(gapOpen, gapShut, shut);
  const cx = W / 2;
  const gapL = cx - gap / 2;
  const gapR = cx + gap / 2;
  const travelIn = lerp(W * 0.085, 0, arrive);
  const leftX = gapL - slabW + travelIn;
  const rightX = gapR - travelIn;

  const kickIn = clamp01(seg(t, 0.02, 0.12));
  const titleIn = easeOutCubic(clamp01(seg(t, 0.03, 0.20)));
  const ruleIn = easeOutCubic(clamp01(seg(t, 0.10, 0.34)));
  const noteIn = clamp01(seg(t, CLOSED ? 0.82 : 0.78, CLOSED ? 0.92 : 0.90));

  const slabTop = formY;
  const slabBot = formY + slabH;
  const measureY = slabBot + dropH;
  const labelY = measureY + labelGap;

  const EXT = Math.round(U * 0.052);                 // how far the measure runs past each side of the gap
  const ARROW = Math.round(U * 0.010);
  const measureW = (gapR + EXT) - (gapL - EXT);
  const clampX = (x: number, w: number) => Math.max(M, Math.min(x, W - M - w));

  const Slab: React.FC<{x: number; name: string; edgeSide: 'left' | 'right'}> = ({x, name, edgeSide}) => (
    <div style={{position: 'absolute', left: x, top: slabTop, width: slabW, height: slabH,
      background: SHEET, border: `${BW}px solid ${LINE}`, borderRadius: RAD, boxSizing: 'border-box',
      opacity: clamp01(arrive * 1.4),
      boxShadow: `0 ${Math.round(U * 0.012)}px ${Math.round(U * 0.030)}px ${SHADOW}`}}>
      {/* THE CUT EDGE — the face this mass presents to the other one. It is what the gap is measured
          between, and at the shut it is the pair of these that meet. */}
      <div style={{position: 'absolute', top: 0, bottom: 0, width: edgeW, background: EDGE,
        [edgeSide]: 0} as React.CSSProperties} />
      {/* THE MASSES KEEP THEIR NAMES THROUGH THE SHUT. The first cut faded them out as the two met, which
          left the settled frame a blank rectangle with a line in it — rendered and looked at. It also
          argued the wrong thing: closing the gap does not abolish the two things, it puts them in one
          body, and the name for that body arrives underneath. Two named halves, butted, with the accent
          as the joint between them is the picture of that; an unnamed slab is the picture of neither. */}
      <div style={{position: 'absolute', left: edgeW, right: edgeW, top: '50%',
        transform: 'translateY(-50%)', textAlign: 'center', color: INK, textWrap: 'balance',
        padding: `0 ${Math.round(slabW * 0.06)}px`, boxSizing: 'border-box',
        font: `700 ${namePx}px/${leading(name, 1.2)} ${disp}`}}>{name}</div>
    </div>
  );

  return (
    <AbsoluteFill style={{background: BG, color: INK_PAPER}}>
      {KICK ? (
        <div style={{position: 'absolute', left: M, top, width: colW, color: DIM_PAPER, opacity: kickIn,
          letterSpacing: dna?.labelSpacing ?? '0.16em',
          font: `600 ${kickPx}px/${leading(KICK, 1.2)} ${mono}`}}>{KICK}</div>
      ) : null}

      {TITLE ? (
        <div style={{position: 'absolute', left: M, top: top + kickH, width: colW * 0.78, color: INK_PAPER,
          opacity: titleIn, textWrap: 'balance',
          transform: glide(`translateY(${lerp(Math.round(U * 0.012), 0, titleIn)}px)`, titleIn !== 1),
          font: `700 ${titlePx}px/${leading(TITLE, 1.06)} ${disp}`}}>{TITLE}</div>
      ) : null}

      {/* the dossier's hairline, drawn across */}
      <div style={{position: 'absolute', left: M, top: ruleY - Math.round(U * 0.012),
        width: Math.round(colW * ruleIn), height: Math.max(1, BW * 2), background: mix(LINE, INK_PAPER, 0.45)}} />

      {/* ── the two masses, and the space between them ────────────────────────────────────────────── */}
      {/* the accent BLEEDS onto the stock either side of the kerf — a lit seam, and the one thing on the
          page that is warm. It dies as the gap shuts, so the last accent left is the joint itself. */}
      <div style={{position: 'absolute', left: gapL - U * 0.040, top: slabTop, width: gap + U * 0.080,
        height: slabH, opacity: 0.30 * light * (1 - shut),
        background: `linear-gradient(90deg, ${ACC2}00, ${ACC2} 42%, ${ACC2} 58%, ${ACC2}00)`,
        filter: `blur(${Math.round(U * 0.012)}px)`, pointerEvents: 'none'}} />

      <Slab x={leftX} name={L} edgeSide="right" />
      <Slab x={rightX} name={R} edgeSide="left" />

      {/* THE GAP. A fill and only a fill — nothing is ever set on it. */}
      <div style={{position: 'absolute', left: gapL, top: slabTop, width: Math.max(1, gap), height: slabH,
        background: ACC2, opacity: clamp01(light * 1.2 * arrive)}} />

      {/* ── the measurement: two extension lines, a measure between them, arrows pointing in ───────── */}
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, pointerEvents: 'none',
        opacity: clamp01(measure) * (1 - handOut)}}>
        {[gapL, gapR].map((x, i) => (
          <div key={i} style={{position: 'absolute', left: Math.round(x) - (i === 0 ? BW : 0),
            top: slabBot + Math.round(U * 0.008), width: Math.max(1, BW), background: RULE_INK,
            height: Math.round((measureY + U * 0.012 - slabBot - U * 0.008) * measure)}} />
        ))}
        <div style={{position: 'absolute', left: cx - (measureW / 2) * measure, top: measureY,
          width: measureW * measure, height: Math.max(1, BW), background: RULE_INK}} />
        {/* arrowheads OUTSIDE the extension lines pointing IN — the convention for a dimension too
            narrow to hold them, which is the only kind this register ever measures */}
        <div style={{position: 'absolute', left: gapL - ARROW, top: measureY - ARROW / 2 + BW / 2,
          width: 0, height: 0, borderTop: `${ARROW / 2}px solid transparent`,
          borderBottom: `${ARROW / 2}px solid transparent`, borderLeft: `${ARROW}px solid ${RULE_INK}`}} />
        <div style={{position: 'absolute', left: gapR, top: measureY - ARROW / 2 + BW / 2,
          width: 0, height: 0, borderTop: `${ARROW / 2}px solid transparent`,
          borderBottom: `${ARROW / 2}px solid transparent`, borderRight: `${ARROW}px solid ${RULE_INK}`}} />
      </div>

      {/* the gap's NAME, on the paper under the measurement */}
      <div style={{position: 'absolute', left: clampX(cx - seamBoxW / 2, seamBoxW), top: labelY,
        width: seamBoxW, textAlign: 'center', color: RULE_INK, textWrap: 'balance',
        opacity: clamp01(nameIn) * (1 - handOut),
        transform: glide(`translateY(${lerp(Math.round(U * 0.010), 0, nameIn)}px)`, nameIn !== 1),
        font: `600 ${seamFit.px}px/${leading(SEAM, 1.3)} ${body}`}}>{SEAM}</div>

      {/* and, once there is no gap, the ONE name the mass now has — in the place the measurement stood,
          because that is the position this frame has been using to say what the middle of it is */}
      {WHOLE ? (
        <div style={{position: 'absolute', left: clampX(cx - wholeBoxW / 2, wholeBoxW), top: labelY,
          width: wholeBoxW, textAlign: 'center', color: INK_PAPER, opacity: handIn, textWrap: 'balance',
          transform: glide(`translateY(${lerp(Math.round(U * 0.014), 0, handIn)}px)`, handIn !== 1),
          font: `700 ${wholeFit.px}px/${leading(WHOLE, 1.18)} ${disp}`}}>{WHOLE}</div>
      ) : null}

      {NOTE ? (
        <div style={{position: 'absolute', left: M, top: bottom - noteH + Math.round(U * 0.010),
          width: colW, color: DIM_PAPER, opacity: noteIn, textWrap: 'balance',
          font: `400 ${notePx}px/${leading(NOTE, 1.45)} ${body}`}}>{NOTE}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default SeamBetween;
