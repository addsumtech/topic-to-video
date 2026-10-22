// SHOT · ReplyWindow — the chat window, where a reader meets the reply: the question in its bubble, the reply in
// plain type behind the blue caret, the message box with its stop button live while the reply is still being written.
//   `stream`   the reply arrives a piece at a time for the whole beat.
//   `guesses`  two windows, two pictures people carry: the whole reply pulled out of a drawer of stored answers, and a
//              finished reply hidden under a cover that slides off as if typing it out — each struck through.
//   `search`   two windows: a drawer of stored answers pulled open and found empty, while the next piece is worked out
//              as chances; and a web search's results dropped into the conversation as more text to read, the reply
//              still written one piece at a time under them.
//   `versus`   two windows run the same reply: one shows it as it is written, the other shows nothing until it is all
//              written.
//   `uncover`  the page up close: the reply so far, and over everything after the caret a dark cover — the finished
//              rest of the answer people imagine. The cover slides away: blank page. Then the next slot's options open
//              under the caret, a roll lands, the piece is written, and the next slot opens. Nothing ahead of it.
//   `check`    a finished reply, and the one fact in it ringed by a reader who checks it.
//
// THE ARGUMENT SHAPE: what the reader sees, and what is (and is not) behind it. Every word, the reply, the options
// and their chances arrive as props; with none, the window is empty.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, hash01, life, ReducedMotionContext} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {rows} from '../runtime/rows';
import {useGlide, unlockSkewFor, BaselineUnlockContext} from '../runtime/glide';
import {textWidthPx} from '../runtime/layout';
import {Stage3D, Surface, projectLocal, matrixOf, faceShade, PERSP_FRAC, type Pose} from '../runtime/stage3d';
import {inkOf, frameOf, groundOf, flow, tileW, tileH, tintAt, Tile, TileRow, Caret, Title, Source, Spray, Cross, Tick,
  BODY, DISPLAY, MONO, TitleAt, Ink} from '../kits/Kit';
import {Fan, Cand} from '../kits/Fan';

export const DURATION = 180;

/** How many of the reply's words are out at progress p — pieces arrive at an uneven pace, never more than one at once. */
const wordsAt = (n: number, p: number, seed = 1) => {
  if (p <= 0) return 0;
  if (p >= 1) return n;
  // @decor: the uneven pace of arrival is the look of streaming; the order and the words are the reply's own
  const w = Array.from({length: n}, (_, i) => 0.6 + hash01(seed + i * 7));
  const tot = w.reduce((a, b) => a + b, 0);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += w[i] / tot;
    if (p < acc) return i;
  }
  return n;
};

/** How many lines `text` takes at `px` in a column `maxW` wide, wrapping at word boundaries — the same greedy break
 *  the browser makes, from the face's average advance (a hair wide, so a line is never promised room it lacks). */
const wrapLines = (text: string, px: number, maxW: number, adv = 0.53): number => {
  if (!text.trim()) return 0;
  let lines = 1, cur = 0;
  for (const word of text.split(/(?<=\s)/)) {
    const ww = textWidthPx(word, px, {adv});
    if (cur > 0 && cur + ww > maxW) { lines += 1; cur = textWidthPx(word.trimStart(), px, {adv}); } else cur += ww;
  }
  return lines;
};

/** How the window is made. `flat` is the page's own white rectangle. The others make it an OBJECT: `slab` faces the
 *  lens square — a thick white slab, its edge and its shadow drawn in 2D, so nothing about its type changes; `float`
 *  stands it on a stage (runtime/stage3d), leaning back a little, lit from above, casting its shadow on the page;
 *  `layers` turns it toward the frame's middle and lifts the question, the reply and the message box off the slab at
 *  their own heights. Type never rides the 3D layer: the stage draws the slab, and each block of words lies on its
 *  face through a 2D affine fitted to all four of its corners (`upright`), so it stays crisp, its lines stay level,
 *  and every type gate still reads it. */
export type Look = 'flat' | 'slab' | 'float' | 'layers';
// degrees of lean (rx) and turn (ry), thickness and shadow lift as fractions of the short side, and the scale
// that keeps the posed slab inside the box the flat window had
const LOOKS: Record<'float' | 'layers', {rx: number; ry: number; depth: number; lift: number; s: number}> = {
  float: {rx: 10, ry: 0, depth: 0.042, lift: 0.05, s: 0.93},
  layers: {rx: 12, ry: 13, depth: 0.022, lift: 0.06, s: 0.88},
};
// how far each part of the window stands off the slab in `layers`, fractions of the short side
const LAYER_Z = {question: 0.045, reply: 0.02, box: 0.06};

/** The face's height: a `slab` gives up its thickness's worth so face + edge fill the box a flat window had. */
const faceH = (look: Look, hBox: number, U: number) => (look === 'slab' ? hBox - U * 0.02 : hBox);

/** The window's layout in its own px — ONE definition, shared by the window and by every mode that draws inside it,
 *  so a drawer, a results box or a cover lands under the question bubble whatever height that bubble wraps to.
 *  `bare` is a window with no message box (a look inside the model rather than at the app). */
const paneLayout = (w: number, h: number, U: number, replyPx: number, question: string | undefined, qScale = 0.92,
  bare = false) => {
  const pad = U * 0.035;
  const qPx = Math.max(31, Math.round(replyPx * qScale));
  const boxH = U * 0.075;
  const qMaxW = w * 0.88, qPadX = qPx * 0.7, qPadY = qPx * 0.38;
  const qLines = question ? wrapLines(question, qPx, qMaxW - 2 * qPadX) : 0;
  const bubbleH = question ? qLines * qPx * 1.3 + 2 * qPadY : 0;
  const regTop = pad + (question ? bubbleH + qPx * 0.7 : 0);
  const regBot = bare ? h - pad : h - pad - boxH - pad * 0.5;
  const regH = Math.max(replyPx * 1.5, regBot - regTop);
  return {pad, qPx, boxH, qMaxW, qPadX, qPadY, bubbleH, regTop, regBot, regH};
};

/** The chat column: a window, the question's bubble, the reply's text with an inline caret, the message box. The
 *  reply has its own region under the bubble; when it outgrows it, it scrolls up under a soft fade, so no line is
 *  ever cut in half at an edge. `waiting` draws the typing dots and a note where the reply would be. */
const Pane: React.FC<{x: number; y: number; w: number; h: number; ink: Ink; U: number; on: number; question?: string;
  reply?: string; shown?: number; caret?: boolean; busy?: boolean; replyPx: number; children?: React.ReactNode;
  ring?: string; ringP?: number; dim?: number; autoScroll?: boolean; waiting?: {note?: string};
  look?: Look; side?: -1 | 0 | 1; qScale?: number; bare?: boolean}> = (
  {x, y, w, h: hBox, ink, U, on, question, reply = '', shown, caret = false, busy = false, replyPx, children,
    ring, ringP = 0, dim = 0, autoScroll = false, waiting, look = 'flat', side = 0, qScale = 0.92, bare = false}) => {
  const glide = useGlide();
  const t = useT();
  const reduced = React.useContext(ReducedMotionContext);
  const unlockAllowed = React.useContext(BaselineUnlockContext);
  const slabDepth = U * 0.02;
  const h = faceH(look, hBox, U);
  const {width: W, height: H, fps, durationInFrames: durF} = useVideoConfig();
  const words = reply.split(/(?<=\s)/);
  const k = shown ?? words.length;
  const r = U * 0.022;
  // ── the layout, in the window's own px ──
  const {pad, qPx, boxH, qMaxW, qPadX, qPadY, bubbleH, regTop, regH} = paneLayout(w, h, U, replyPx, question, qScale, bare);
  // @truncates: the reply is still being written; every word is drawn once it has arrived
  const text = words.slice(0, k);
  // does the reply overflow its region? Only to decide whether the top edge fades — WHERE it sits is left to the
  // browser, which knows the real height of the wrapped lines (an estimate overshot by a line and left a blank gap)
  const overflows = autoScroll && wrapLines(text.join(''), replyPx, w - 2 * pad, 0.48) * replyPx * 1.42 > regH * 0.9;
  const fadeH = replyPx * 1.2;
  const ringed = ring && reply.includes(ring) ? ring : null;
  const dots = Array.from({length: 3}, (_, j) => 0.3 + 0.7 * life(t, durF, fps, 3, j * 0.22));
  const solid = look === 'flat';

  // ── the parts, each in the window's own coordinates ──
  const bubble = question ? (
    <div style={{position: 'absolute', right: pad, top: pad, maxWidth: qMaxW, boxSizing: 'border-box',
      background: `linear-gradient(180deg, ${mix(ink.fg, ink.surface, 0.955)}, ${mix(ink.fg, ink.surface, 0.92)})`,
      borderRadius: qPx * 0.9, padding: `${qPadY}px ${qPadX}px`, color: ink.fg, font: `400 ${qPx}px/1.3 ${BODY}`,
      boxShadow: solid ? undefined : `0 ${U * 0.003}px ${U * 0.008}px ${mix(ink.fg, ink.bg, 0.9)}, inset 0 1px 0 #ffffff`}}>
      {question}</div>
  ) : null;
  const replyBlock = (
    <div style={{position: 'absolute', left: pad, right: pad, top: regTop, height: regH, overflow: 'hidden',
      ...(overflows ? {WebkitMaskImage: `linear-gradient(180deg, transparent 0, #000 ${fadeH}px)`,
        maskImage: `linear-gradient(180deg, transparent 0, #000 ${fadeH}px)`} : {})}}>
      {/* top-aligned while it fits; once taller than the region, its LAST line sits on the region's floor: the
          shift is min(0, region - own height), resolved by the browser from the block's real height */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, color: ink.fg, font: `400 ${replyPx}px/1.42 ${BODY}`,
        paddingBottom: replyPx * 0.25,
        transform: autoScroll ? glide(`translateY(min(0px, calc(${regH}px - 100%)))`, caret) : undefined}}>
        {ringed ? (() => {
          const s = text.join('');
          const at = s.indexOf(ringed);
          if (at < 0) return s;
          return <>{s.slice(0, at)}<span style={{position: 'relative', whiteSpace: 'nowrap'}}>{ringed}
            <svg viewBox="0 0 100 40" preserveAspectRatio="none" style={{position: 'absolute', left: '-18%', top: '-30%',
              width: '136%', height: '160%', overflow: 'visible'}}>
              <ellipse cx={50} cy={20} rx={48} ry={17} fill="none" stroke={ink.acc2} strokeWidth={3}
                vectorEffect="non-scaling-stroke" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - ringP}
                style={{strokeWidth: Math.max(3, U * 0.004)}} />
            </svg></span>{s.slice(at + ringed.length)}</>;
        })() : text.join('')}
        {caret ? <span style={{display: 'inline-block', width: Math.max(4, U * 0.0045), height: replyPx * 1.05,
          marginLeft: 3, verticalAlign: '-0.18em', background: ink.acc2}} /> : null}
      </div>
      {waiting ? (
        <>
          <svg width={w - 2 * pad} height={replyPx * 1.4} style={{position: 'absolute', left: 0, top: 0}}>
            {dots.map((d, j) => <circle key={j} cx={replyPx * 0.45 + j * replyPx * 0.9} cy={replyPx * 0.7}
              r={replyPx * 0.2} fill={ink.dim} opacity={d} />)}
          </svg>
          {waiting.note ? <div style={{position: 'absolute', left: 0, right: 0, top: replyPx * 1.6, color: ink.dim,
            font: `500 ${Math.max(31, Math.round(U * 0.0285))}px/1.3 ${BODY}`}}>{waiting.note}</div> : null}
        </>
      ) : null}
    </div>
  );
  // the message box, its button a stop square while the reply is being written, a send arrow after
  const msgBox = bare ? null : (
    <div style={{position: 'absolute', left: pad, right: pad, top: h - pad - boxH, height: boxH}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: boxH / 2, border: `1px solid ${ink.border}`,
        background: ink.bg, boxShadow: solid ? undefined : `inset 0 ${U * 0.002}px ${U * 0.005}px ${mix(ink.fg, ink.bg, 0.92)}`}} />
      <svg width={w - 2 * pad} height={boxH} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <defs>
          <radialGradient id="rwBtn" cx="35%" cy="30%" r="80%">
            <stop offset="0%" stopColor={mix(ink.fg, ink.surface, 0.3)} />
            <stop offset="100%" stopColor={ink.fg} />
          </radialGradient>
        </defs>
        <circle cx={w - 2 * pad - boxH / 2} cy={boxH / 2} r={boxH * 0.36} fill={solid ? ink.fg : 'url(#rwBtn)'} />
        {busy ? <rect x={w - 2 * pad - boxH / 2 - boxH * 0.12} y={boxH / 2 - boxH * 0.12} width={boxH * 0.24}
          height={boxH * 0.24} rx={2} fill={ink.surface} />
          : <path d={`M${w - 2 * pad - boxH / 2},${boxH / 2 + boxH * 0.17} l0,${-boxH * 0.32} m${-boxH * 0.13},${boxH * 0.13} l${boxH * 0.13},${-boxH * 0.13} l${boxH * 0.13},${boxH * 0.13}`}
            fill="none" stroke={ink.surface} strokeWidth={Math.max(2.5, U * 0.003)} strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
    </div>
  );

  if (solid) {
    return (
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, opacity: on, background: ink.surface,
        border: `1px solid ${ink.border}`, borderRadius: U * 0.018, overflow: 'hidden',
        filter: dim > 0 ? `saturate(${1 - dim})` : undefined}}>
        {bubble}{replyBlock}{children}{msgBox}
      </div>
    );
  }

  // the slab keeps living after it settles: a slow sway, as if the room's air moved it (none under reduced motion)
  const sway = reduced ? 0 : life(t, durF, fps, 7.5, 0.1) - 0.5;
  const sway2 = reduced ? 0 : life(t, durF, fps, 9.5, 0.6) - 0.5;
  const arrive = 1 - on;
  const faceBg = `linear-gradient(162deg, #ffffff 0%, ${ink.surface} 38%, ${mix(ink.surface, ink.fg, 0.035)} 100%)`;
  // a soft band of light that crosses the face as it sways — the moving highlight that says "hard, smooth surface"
  const sheenAt = 30 + 40 * (sway + 0.5);
  const sheen = <div style={{position: 'absolute', inset: 0, borderRadius: r,
    background: `linear-gradient(115deg, transparent ${sheenAt - 18}%, rgba(255,255,255,0.55) ${sheenAt}%, transparent ${sheenAt + 18}%)`}} />;
  const content = <>{bubble}{replyBlock}{children}{msgBox}</>;

  if (look === 'slab') {
    // square to the lens: the slab's edge shows below its face, its shadow falls on the page under it
    const depth = slabDepth, steps = 12;
    const rise = U * 0.012 * arrive;
    return (
      <div style={{position: 'absolute', left: x, top: y + rise, width: w, height: h, opacity: on}}>
        <div style={{position: 'absolute', left: w * 0.03, right: w * 0.03, top: U * 0.05, bottom: -U * 0.05 - depth,
          borderRadius: r * 1.5, background: mix(ink.fg, ink.bg, 0.45), opacity: 0.34 + 0.06 * sway2,
          filter: `blur(${U * 0.045}px)`}} />
        {Array.from({length: steps}, (_, i) => (
          <div key={i} style={{position: 'absolute', left: 0, top: depth * (steps - i) / steps, width: w, height: h,
            borderRadius: r, background: mix(ink.surface, ink.fg, 0.07 + 0.13 * ((steps - i) / steps))}} />
        ))}
        <div style={{position: 'absolute', inset: 0, borderRadius: r, background: faceBg, overflow: 'hidden',
          boxShadow: `inset 0 1.5px 0 #ffffff, inset 0 0 0 1px ${mix(ink.border, ink.surface, 0.3)}, inset 0 -${U * 0.004}px ${U * 0.01}px ${mix(ink.fg, ink.bg, 0.94)}`,
          filter: dim > 0 ? `saturate(${1 - dim})` : undefined}}>
          {sheen}
          {content}
        </div>
      </div>
    );
  }

  // ── on a stage: the slab is posed in 3D, its words laid on its face in 2D ──
  const L = LOOKS[look];
  const turn = side === 0 ? -1 : side;
  // each window has its own vanishing point, at its own centre, so a window off to one side is not skewed by
  // the frame's perspective: the container that holds its stage and its words is centred on it
  const dx = x + w / 2 - W / 2, dy = y + h / 2 - H / 2;
  const persp = Math.round(Math.min(W, H) * PERSP_FRAC);
  const pose: Pose = {z: -U * 0.08 * arrive, rx: L.rx + 2.2 * sway + 10 * arrive,
    ry: -turn * L.ry + (L.ry ? 3 * sway2 : 0), s: L.s};
  const Rm = matrixOf({rx: pose.rx, ry: pose.ry});
  const n = [Rm[8], Rm[9], Rm[10]];                     // the slab's normal, out of its face
  // @fallback: an unset pose coordinate IS zero (the stage's origin) — geometry, not a claim the film makes
  const along = (pz: Pose, d: number): Pose => ({...pz, x: (pz.x ?? 0) + n[0] * d, y: (pz.y ?? 0) + n[1] * d,
    z: (pz.z ?? 0) + n[2] * d});
  const depth = U * L.depth;
  const steps = 14;
  const shade = faceShade(pose, {}, 0.55);
  const unlockOn = unlockAllowed && !reduced;
  // A BLOCK OF WORDS ON THE FACE, as a 2D affine fitted to ALL FOUR projected corners (least squares) rather than
  // three: on a slab leaning back, the face is a trapezoid; a three-corner fit takes the slant of its left edge
  // for the whole block, and the lines read as italic. Over four corners the slants of the two sides cancel, the
  // lines stay level, and the leftover is a sliver of width at the corners.
  const upright = (pz: Pose, left: number, top: number, width: number, height: number, node: React.ReactNode,
    key: string) => {
    const hw = width / 2, hh = height / 2;
    const cxl = left - w / 2 + hw, cyl = top - h / 2 + hh;
    const pts = [[-hw, -hh], [hw, -hh], [-hw, hh], [hw, hh]].map(([u, v]) => ({u, v,
      p: projectLocal(pz, {}, persp, W, H, cxl + u, cyl + v)}));
    if (pts.some((q) => q.p.behind)) return null;
    const e = pts.reduce((a, q) => a + q.p.x, 0) / 4, fy = pts.reduce((a, q) => a + q.p.y, 0) / 4;
    const a = pts.reduce((acc, q) => acc + q.p.x * q.u, 0) / (4 * hw * hw);
    const c = pts.reduce((acc, q) => acc + q.p.x * q.v, 0) / (4 * hh * hh);
    const b = pts.reduce((acc, q) => acc + q.p.y * q.u, 0) / (4 * hw * hw);
    const d = pts.reduce((acc, q) => acc + q.p.y * q.v, 0) / (4 * hh * hh);
    const tx = e - a * hw - c * hh, ty = fy - b * hw - d * hh;
    const k = unlockOn ? unlockSkewFor(Math.max(0.1, Math.sqrt(Math.abs(a * d - b * c)))) : 0;
    return (
      <div key={key} style={{position: 'absolute', left: 0, top: 0, width, height, overflow: 'visible', transformOrigin: '0 0',
        transform: `matrix(${a},${b},${c},${d},${tx},${ty})${k ? ` matrix(1, ${k}, 0, 1, 0, 0)` : ''}`, opacity: on}}>
        {/* clipped to the face: nothing the window holds may hang off its edge */}
        <div style={{position: 'absolute', left: -left, top: -top, width: w, height: h, overflow: 'hidden',
          borderRadius: r}}>{node}</div>
      </div>
    );
  };
  const lz = (part: keyof typeof LAYER_Z) => (look === 'layers' ? U * LAYER_Z[part] : 0);
  return (
    <div style={{position: 'absolute', left: dx, top: dy, width: W, height: H, pointerEvents: 'none'}}>
      <Stage3D persp={persp}>
        {/* the shadow it casts on the page behind it, below the key light */}
        <Surface pose={{...along(pose, -depth - U * L.lift), y: U * 0.045}} w={w} h={h}
          style={{borderRadius: r, background: mix(ink.fg, ink.bg, 0.45), opacity: 0.42 * on,
            filter: `blur(${U * 0.04}px)`}} />
        {/* its thickness: the face's outline stacked back into the page, darkening toward the back */}
        {Array.from({length: steps}, (_, i) => {
          const dd = depth * (i + 1) / steps;
          return <Surface key={i} pose={along(pose, -dd)} w={w} h={h}
            style={{borderRadius: r, opacity: on, background: mix(mix(ink.surface, ink.fg, 0.14 + 0.22 * (i / steps)), ink.bg, 1 - shade)}} />;
        })}
        <Surface pose={pose} w={w} h={h} style={{borderRadius: r, background: faceBg, opacity: on, overflow: 'hidden',
          boxShadow: `inset 0 1.5px 0 #ffffff, inset 0 0 0 1px ${mix(ink.border, ink.surface, 0.3)}`,
          filter: dim > 0 ? `saturate(${1 - dim})` : undefined}}>
          {sheen}
          {look === 'layers' ? (
            // where each lifted part stands, its shadow on the slab
            <>
              {question ? <div style={{position: 'absolute', right: pad - U * 0.004, top: pad + U * 0.012,
                width: Math.min(qMaxW, textWidthPx(question, qPx, {adv: 0.5}) + 2 * qPadX), height: bubbleH,
                borderRadius: qPx * 0.9, background: mix(ink.fg, ink.bg, 0.82), filter: `blur(${U * 0.008}px)`, opacity: 0.45}} /> : null}
              <div style={{position: 'absolute', left: pad + U * 0.008, right: pad - U * 0.008, top: h - pad - boxH + U * 0.018, height: boxH,
                borderRadius: boxH / 2, background: mix(ink.fg, ink.bg, 0.8), filter: `blur(${U * 0.012}px)`, opacity: 0.6}} />
            </>
          ) : null}
        </Surface>
      </Stage3D>
      {look === 'layers' ? (
        <>
          {upright(along(pose, lz('reply')), 0, regTop, w, regH, <>{replyBlock}{children}</>, 'reply')}
          {question ? upright(along(pose, lz('question')), 0, pad, w, bubbleH, bubble, 'q') : null}
          {upright(along(pose, lz('box')), 0, h - pad - boxH, w, boxH, msgBox, 'box')}
        </>
      ) : (
        <>
          {upright(pose, 0, 0, w, regTop, bubble, 'q')}
          {upright(pose, 0, regTop, w, regH, <>{replyBlock}{children}</>, 'reply')}
          {upright(pose, 0, h - pad - boxH, w, boxH, msgBox, 'box')}
        </>
      )}
    </div>
  );
};

export const ReplyWindow: React.FC<{
  mode?: 'stream' | 'guesses' | 'search' | 'versus' | 'uncover' | 'check';
  question?: string;       // the user's question
  reply?: string;          // the reply, as written (streamed word by word)
  heads?: string[];        // two-window modes: each window's heading
  drawerLabel?: string;    // guesses/search: the drawer's label
  context?: string[];      // uncover/search: the reply so far, as its pieces
  cands?: Cand[];          // uncover/search: the next slot's options
  pick?: number;           // uncover/search: which option is written
  roll?: boolean;          // uncover: picked by a roll
  coverLabel?: string;     // uncover: the words on the imagined cover
  blankNote?: string;      // uncover: set in the blank page once the cover is gone
  note?: string;           // search: what the computed chances are; versus: what the waiting window shows
  results?: string;        // search: the label on the results dropped into the conversation
  replyNote?: string;      // search: the label under the reply still being written
  look?: Look;             // how the window is made: the page's flat rectangle, or a lit slab on a stage
  ring?: string;           // check: the fact a reader rings
  checkLabel?: string;     // check: the reader's note beside it
  title?: string; kicker?: string; titleAt?: TitleAt;
  source?: string; sourceAt?: 'bl' | 'br' | 'tl' | 'tr';
}> = ({mode = 'stream', question = '', reply = '', heads: hIn, drawerLabel = '', context: ctxIn, cands: cIn, pick = 0,
  roll = false, coverLabel = '', blankNote = '', note = '', results = '', replyNote = '', ring = '', checkLabel = '',
  look = 'flat',
  title = '', kicker = '', titleAt: titleAtIn, source = '', sourceAt: sourceAtIn}) => {
  // a title or kicker that was given is drawn: unplaced, it takes the top left (an unset spot used to draw nothing)
  const titleAt: TitleAt = titleAtIn ?? (title || kicker ? 'tl' : 'none');
  const sourceAt = sourceAtIn ?? 'br';
  const heads = rows<string>(hIn ?? [], 'heads', 'ReplyWindow');
  const context = rows<string>(ctxIn ?? [], 'context', 'ReplyWindow');
  const cands = rows<Cand>(cIn ?? [], 'cands', 'ReplyWindow');
  if (cands.length && !(pick >= 0 && pick < cands.length)) throw new Error(`ReplyWindow: pick ${pick} is not one of ${cands.length} options`);
  const dna = useDNA();
  const ink = inkOf(dna);
  const t = useT();
  const cue = useCues();
  const glide = useGlide();
  const reduced = React.useContext(ReducedMotionContext);
  const {width: W, height: H, fps, durationInFrames: durF} = useVideoConfig();
  const f = frameOf(W, H);
  const {U, sx, lw} = f;
  const row = titleAt[0], col = titleAt[1];
  const titled = titleAt !== 'none' && !!(title || kicker);
  const kOn = easeOutCubic(clamp01(seg(t, ...cue.win('kicker', 0.03, 0.14, REACH_CUBIC))));
  const tOn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.05, 0.17, REACH_CUBIC))));
  const sOn = easeOutCubic(clamp01(seg(t, 0.3, 0.42)));
  const pOn = easeOutCubic(clamp01(seg(t, 0.04, 0.14)));
  const secs = (t * durF) / fps;
  const words = reply.split(/(?<=\s)/);
  const nW = words.length;
  const two = mode === 'guesses' || mode === 'search' || mode === 'versus';
  const titleEl = <Title title={title} kicker={kicker} at={titleAt} W={W} H={H} on={tOn} kOn={kOn} ink={ink.fg}
    dim={ink.dim} maxW={row === 'm' || (row === 'b' && mode === 'stream') ? W * 0.27 : W * 0.6}
    lines={row === 'm' || mode === 'stream' ? 3 : 2} size={mode === 'stream' || row === 'm' ? Math.round(U * 0.066) : undefined} />;

  // ── two windows side by side ──
  if (two) {
    const gap = U * 0.05;
    const headPx = Math.round(U * 0.046);
    const top = f.zTop + headPx * 1.5;
    const bot = titled && row === 'b' ? f.zBot - U * 0.2 : f.zBot - (source && sourceAt[0] === 'b' ? U * 0.07 : U * 0.01);
    const pw = (W - 2 * sx - gap) / 2, ph = bot - top;
    const replyPx = Math.round(U * 0.034);
    // @positional: in `versus` the second window is the one that waits — the mode's definition; its heading says so
    const waitsAt = (i: number) => i === 1;
    const strike = (i: number) => easeOutCubic(clamp01(seg(t, ...cue.win(`heads.${i}`, 0.6 + i * 0.06, 0.7 + i * 0.06, REACH_CUBIC))));
    return (
      <AbsoluteFill style={{background: groundOf(dna, ink)}}>
        {titleEl}
        {heads.map((h, i) => {
          const s = mode === 'guesses' ? strike(i) : 0;
          return <div key={i} style={{position: 'absolute', left: sx + i * (pw + gap), top: f.zTop - headPx * 0.15,
            opacity: easeOutCubic(clamp01(seg(t, 0.05 + i * 0.08, 0.15 + i * 0.08))), color: ink.fg,
            font: `600 ${headPx}px/1.2 ${DISPLAY}`, whiteSpace: 'nowrap',
            textDecoration: s > 0.5 ? `line-through ${Math.max(3, U * 0.004)}px ${ink.acc}` : 'none'}}>{h}</div>;
        })}
        {[0, 1].map((i) => {
          const x = sx + i * (pw + gap);
          const pad = U * 0.035;
          if (mode === 'versus') {
            // the same reply, written over the same span: shown as it goes (left), or only when done (right)
            const p = clamp01(seg(t, 0.14, 0.94));
            const k = wordsAt(nW, p, 3);
            const done = p >= 1;
            const vPx = Math.round(U * 0.04);
            const waits = waitsAt(i);
            return (
              <Pane key={i} x={x} y={top} w={pw} h={ph} ink={ink} U={U} on={pOn} question={question} reply={reply}
                shown={!waits ? k : done ? nW : 0} caret={!waits && !done} busy={!done} replyPx={vPx}
                autoScroll={!waits} waiting={waits && !done ? {note} : undefined} look={look} side={i === 0 ? -1 : 1}
                qScale={0.8} />
            );
          }
          // everything below is drawn INSIDE its window, in the window's own px, so it rides the window's face
          // whatever the look (flat, or a slab posed on a stage)
          const L0 = paneLayout(pw, faceH(look, ph, U), U, replyPx, question);
          const ph0 = faceH(look, ph, U);
          if (mode === 'guesses') {
            const s = strike(i);
            if (i === 0) {
              // a drawer of stored answers; the whole reply comes out of it on one card
              const out = 0.5 - 0.5 * Math.cos(Math.PI * clamp01(seg(t, 0.12, 0.52)));
              const dW = pw * 0.5, dH = ph0 * 0.2, dx = L0.pad, dy = ph0 - dH - L0.pad * 3.2;
              const cy0 = dy + dH * 0.32, cy1 = L0.regTop;
              // the card ends above the drawer once it is out, and shows only the whole lines that fit in it
              const cardPad = L0.pad * 0.6, lineH = replyPx * 1.35;
              const cardLines = Math.max(1, Math.floor((dy - L0.pad * 0.3 - cy1 - 2 * cardPad) / lineH));
              const cardH = cardLines * lineH + 2 * cardPad;
              const cyN = cy0 + (cy1 - cy0) * out;
              return (
                <Pane key={i} x={x} y={top} w={pw} h={ph} ink={ink} U={U} on={pOn} question={question} reply=""
                  replyPx={replyPx} dim={s * 0.6} look={look} side={-1}>
                  {/* the card rises out of the drawer's slot: clipped at the slot, so it appears from inside */}
                  <div style={{position: 'absolute', left: 0, top: 0, width: pw, height: dy + dH * 0.3, overflow: 'hidden'}}>
                    <div style={{position: 'absolute', left: dx + L0.pad * 0.3, top: cyN, width: pw - L0.pad * 3, height: cardH,
                      background: '#FFFDF4', border: `1px solid ${mix(ink.border, ink.fg, 0.15)}`, borderRadius: 6,
                      boxShadow: `0 ${U * 0.006}px ${U * 0.02}px ${mix(ink.fg, ink.bg, 0.85)}`,
                      padding: cardPad, boxSizing: 'border-box', color: ink.fg, overflow: 'hidden',
                      font: `400 ${replyPx}px/1.35 ${BODY}`}}>
                      <div style={{display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: cardLines,
                        overflow: 'hidden'}}>{reply}</div>
                    </div>
                  </div>
                  <div style={{position: 'absolute', left: dx, top: dy, width: dW, height: dH, borderRadius: 6,
                    background: `linear-gradient(180deg, ${mix(ink.fg, ink.bg, 0.3)}, ${mix(ink.fg, ink.bg, 0.12)})`,
                    boxShadow: `inset 0 1px 0 ${mix(ink.fg, ink.bg, 0.45)}, 0 ${U * 0.004}px ${U * 0.01}px ${mix(ink.fg, ink.bg, 0.8)}`}} />
                  <div style={{position: 'absolute', left: dx + dW * 0.32, top: dy + dH * 0.16, width: dW * 0.36, height: dH * 0.12,
                    borderRadius: dH, background: mix(ink.fg, ink.bg, 0.5)}} />
                  {/* the drawer's own label plate, on its front */}
                  {drawerLabel ? <div style={{position: 'absolute', left: dx, width: dW, top: dy + dH * 0.36, textAlign: 'center',
                    color: mix(ink.bg, ink.fg, 0.12), font: `500 ${f.label}px/1.25 ${BODY}`, whiteSpace: 'nowrap'}}>{drawerLabel}</div> : null}
                  {/* struck where the stored answer is: on the card, clear of the drawer's label */}
                  <svg width={pw} height={ph0} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
                    <Cross x={dx + L0.pad * 0.3 + (pw - L0.pad * 3) / 2} y={cy1 + cardH / 2} s={Math.min(pw - L0.pad * 3, cardH) * 0.85}
                      color={ink.acc} p={s} lw={Math.max(8, U * 0.011)} />
                  </svg>
                </Pane>
              );
            }
            // a finished reply under a cover that slides off it, as if typing it out
            const off = clamp01(seg(t, 0.14, 0.58));
            return (
              <Pane key={i} x={x} y={top} w={pw} h={ph} ink={ink} U={U} on={pOn} question={question} reply={reply}
                replyPx={replyPx} dim={s * 0.6} look={look} side={1}>
                <div style={{position: 'absolute', left: L0.pad * 0.6 + (pw - L0.pad * 1.2) * off, right: L0.pad * 0.6,
                  top: L0.regTop - replyPx * 0.2, height: Math.min(L0.regH, replyPx * 1.42 * 5.4), background: ink.fg, borderRadius: 6}} />
                <svg width={pw} height={ph0} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
                  <Cross x={pw / 2} y={L0.regTop + Math.min(L0.regH, replyPx * 1.42 * 5) / 2} s={Math.min(pw, ph0) * 0.45}
                    color={ink.acc} p={s} lw={Math.max(8, U * 0.011)} />
                </svg>
              </Pane>
            );
          }
          // search
          if (i === 0) {
            // the drawer pulled open: nothing in it; beside it, the next piece worked out as chances
            const open = easeInOutCubic(clamp01(seg(t, 0.14, 0.32)));
            const s = easeOutCubic(clamp01(seg(t, 0.34, 0.42)));
            const B0 = paneLayout(pw, ph0, U, replyPx, '', 0.92, true);
            const dW = pw * 0.44, dH = ph0 * 0.13, dx = B0.pad, dy = B0.pad * 0.6;
            const depth = dH * 1.2 * open;
            const px = Math.round(U * 0.036);
            const th = tileH(px);
            const ly = dy + dH + depth + th * 1.0;
            const fl = flow(context, px, B0.pad, ly, pw * 0.5, th * 1.2);
            const caret = {x: fl.end.x + px * 0.1, y: fl.end.y};
            const grow = clamp01(seg(t, 0.46, 0.62));
            return (
              <Pane key={i} x={x} y={top} w={pw} h={ph} ink={ink} U={U} on={pOn} replyPx={replyPx} look={look} side={-1} bare>
                {/* the drawer's inside (empty), then its front */}
                <div style={{position: 'absolute', left: dx + dW * 0.04, top: dy + dH * 0.6, width: dW * 0.92, height: depth,
                  background: `linear-gradient(180deg, ${mix(ink.fg, ink.bg, 0.8)}, ${mix(ink.fg, ink.bg, 0.9)})`, borderRadius: 4}} />
                <div style={{position: 'absolute', left: dx, top: dy, width: dW, height: dH, borderRadius: 6,
                  transform: glide(`translateY(${depth}px)`, open > 0 && open < 1),
                  background: `linear-gradient(180deg, ${mix(ink.fg, ink.bg, 0.3)}, ${mix(ink.fg, ink.bg, 0.12)})`,
                  boxShadow: `inset 0 1px 0 ${mix(ink.fg, ink.bg, 0.45)}, 0 ${U * 0.004}px ${U * 0.01}px ${mix(ink.fg, ink.bg, 0.8)}`}}>
                  <div style={{position: 'absolute', left: dW * 0.32, top: dH * 0.4, width: dW * 0.36,
                    height: dH * 0.16, borderRadius: dH, background: mix(ink.fg, ink.bg, 0.5)}} />
                </div>
                {/* the label rides down with the drawer front: moved by a glided transform, never by `top` (text moved by
                    layout snaps to whole pixels and steps) */}
                {drawerLabel ? <div style={{position: 'absolute', left: dx + dW + B0.pad * 0.6, top: dy + dH / 2 - f.label * 0.65,
                  transform: glide(`translateY(${depth}px)`, open > 0 && open < 1), color: ink.dim, font: `500 ${f.label}px/1.25 ${BODY}`, whiteSpace: 'nowrap'}}>{drawerLabel}</div> : null}
                <svg width={pw} height={ph0} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
                  <Cross x={dx + dW / 2} y={dy + depth / 2 + dH * 0.5} s={dH * 0.9} color={ink.acc} p={s} lw={Math.max(6, U * 0.008)} />
                </svg>
                <TileRow tokens={context} pos={fl.pos} px={px} on={clamp01(seg(t, 0.4, 0.5))} ink={ink.fg} />
                <Fan cands={cands} ox={caret.x + px * 0.3} oy={caret.y + th * 0.58} x2={caret.x + px * 1.8}
                  top={caret.y + th * 1.7} pitch={th * 1.2} px={px} grow={grow} pick={null} pickOn={0} travel={0}
                  to={caret} wither={0} labelPx={f.label} ink={ink} U={U} lw={lw} tint0={context.length}
                  spray={{len: px * 5, n: 20, t, durF, fps, seed: 17}} />
                <Caret x={caret.x} y={caret.y} h={th * 0.9} color={ink.acc2} on={clamp01(seg(t, 0.4, 0.5))} U={U} />
                {note ? <div style={{position: 'absolute', left: B0.pad, width: Math.max(U * 0.25, caret.x - B0.pad - px * 0.4), top: caret.y + th * 1.3,
                  color: ink.dim, opacity: easeOutCubic(clamp01(seg(t, ...cue.win('note', 0.6, 0.7, REACH_CUBIC)))),
                  font: `500 ${f.label}px/1.3 ${BODY}`}}>{note}</div> : null}
              </Pane>
            );
          }
          // the web search's results dropped into the conversation as more text to read; the reply still written
          const drop = easeOutCubic(clamp01(seg(t, 0.3, 0.46)));
          const absorb = easeInOutCubic(clamp01(seg(t, 0.5, 0.62)));
          const px = Math.round(U * 0.03);
          const th = tileH(px);
          const rTop = L0.regTop;
          const rH = Math.min(ph0 * 0.24, L0.regH * 0.42);
          // three rows that always fit inside the results box, whatever its height
          const rowPitch = (rH - pad * 0.8) / 3, rowH = Math.min(th * 0.62, rowPitch * 0.7);
          // @decor: the results are drawn as rows of pieces whose widths are texture — the film does not show their words
          const resultRows = Array.from({length: 3}, (_, r) => Array.from({length: 7}, (_, c) => 2 + Math.floor(hash01(r * 17 + c * 5) * 5)));
          const replyY = rTop + rH + pad * 1.4;
          const p = clamp01(seg(t, 0.62, 0.95));
          // @decor: the reply's pieces are drawn without their words — the film shows how it is written, not what
          const reps0 = Array.from({length: 9}, (_, k) => 2 + Math.floor(hash01(300 + k * 3) * 5));
          // the row of pieces is scaled to end inside the window, with room left for the caret
          const rowFit = Math.min(1, (pw - pad * 2 - U * 0.02) / reps0.reduce((a, c) => a + c * px * 0.6 + px * 0.7, 0));
          const reps = reps0.map((c) => c * rowFit + (rowFit - 1) * (0.7 / 0.6));
          const nShown = Math.floor(p * reps.length + 0.0001);
          let rx = pad;
          return (
            <Pane key={i} x={x} y={top} w={pw} h={ph} ink={ink} U={U} on={pOn} question={question} reply="" replyPx={replyPx}
              busy={p < 1} look={look} side={1}>
              <div style={{position: 'absolute', left: pad, top: rTop, width: pw - pad * 2, height: rH,
                transform: glide(`translateY(${-(1 - drop) * U * 0.05}px)`, drop > 0 && drop < 1),
                background: mix(ink.acc2, ink.surface, 0.9), border: `1px solid ${mix(ink.acc2, ink.surface, 0.6)}`,
                borderRadius: 8, opacity: drop, boxShadow: `0 ${U * 0.004}px ${U * 0.012}px ${mix(ink.acc2, ink.bg, 0.85)}`}}>
                {resultRows.map((r, ri) => {
                  let cx = pad * 0.5;
                  return r.map((cells, ci) => {
                    const w = cells * px * 0.6 + px * 0.4;
                    const el = <div key={`${ri}-${ci}`} style={{position: 'absolute', left: cx, top: pad * 0.4 + ri * rowPitch,
                      width: w, height: rowH, borderRadius: 4, background: mix(tintAt(ri * 7 + ci), ink.surface, 1 - absorb)}} />;
                    cx += w + px * 0.18;
                    return cx < pw - pad * 2.5 ? el : null;
                  });
                })}
              </div>
              {results ? <div style={{position: 'absolute', left: pad, top: rTop + rH + pad * 0.15, color: ink.acc2,
                opacity: drop, font: `600 ${f.label}px/1.2 ${BODY}`, whiteSpace: 'nowrap'}}>{results}</div> : null}
              {reps.map((cells, k) => {
                const w = cells * px * 0.6 + px * 0.7;
                const at = rx;
                rx += w;
                return k < nShown ? <Tile key={k} text="" w={w} x={at} y={replyY + th * 0.6} px={px} fill={tintAt(k)} ink={ink.fg} /> : null;
              })}
              <Caret x={(() => { let cx = pad; for (let k = 0; k < nShown; k++) cx += reps[k] * px * 0.6 + px * 0.7; return cx + 3; })()}
                y={replyY + th * 0.6} h={th * 0.9} color={ink.acc2} on={clamp01(seg(t, 0.6, 0.66))} U={U} />
              {replyNote ? <div style={{position: 'absolute', left: pad, top: replyY + th * 1.25, color: ink.dim,
                opacity: clamp01(seg(t, 0.66, 0.74)), font: `500 ${f.label}px/1.3 ${BODY}`, width: pw - pad * 2}}>{replyNote}</div> : null}
            </Pane>
          );
        })}
        <Source text={source} at={sourceAt} W={W} H={H} on={sOn} ink={ink.dim} />
      </AbsoluteFill>
    );
  }

  if (mode === 'uncover') {
    // ── the page up close: the reply so far, the imagined rest under a cover; the cover goes, the page is blank ──
    const px = Math.round(U * 0.062);
    const th = tileH(px);
    const x0 = sx;
    const ly = f.zTop + th * 0.75;
    const fl = flow(context, px, x0, ly, W - 2 * sx, th * 1.25);
    const caret = {x: fl.end.x + px * 0.1, y: fl.end.y};
    const ctxOn = easeOutCubic(clamp01(seg(t, 0.03, 0.12)));
    const lift = 0.5 - 0.5 * Math.cos(Math.PI * clamp01(seg(t, ...cue.win('coverLabel', 0.12, 0.5, REACH_CUBIC))));
    const blank = easeOutCubic(clamp01(seg(t, 0.4, 0.5)));
    const grow = clamp01(seg(t, 0.5, 0.6));
    const r = roll ? clamp01(seg(t, 0.6, 0.76)) : null;
    const pickOn = easeOutCubic(clamp01(seg(t, roll ? 0.76 : 0.61, roll ? 0.8 : 0.65)));
    const travel = clamp01(seg(t, roll ? 0.8 : 0.65, roll ? 0.87 : 0.72));
    const wither = easeOutCubic(clamp01(seg(t, 0.83, 0.92)));
    const addW = cands[pick] ? tileW(cands[pick].token, px) : 0;
    const caretNow = caret.x + addW * easeOutCubic(travel);
    const nextOn = easeOutCubic(clamp01(seg(t, 0.88, 0.95)));
    const cover = {l: caret.x + px * 0.4, t: f.zTop - U * 0.02, b: f.zBot - U * 0.01};
    const coverX = cover.l + (W - cover.l + U * 0.05) * lift;      // the cover slides off to the right
    const lpx = Math.round(U * 0.05);
    const labelPx = f.label;
    return (
      <AbsoluteFill style={{background: groundOf(dna, ink)}}>
        {/* ruled lines of the blank page, ahead of the caret */}
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          {Array.from({length: 6}, (_, k) => {
            const y = ly + th * 0.55 + k * th * 1.25;
            return y < f.zBot - U * 0.03 ? <line key={k} x1={k === 0 ? caret.x + px * 0.5 : x0} x2={W - sx} y1={y} y2={y}
              stroke={ink.line} strokeWidth={Math.max(1.5, U * 0.0018)} opacity={blank} /> : null;
          })}
        </svg>
        <TileRow tokens={context} pos={fl.pos} px={px} on={ctxOn} ink={ink.fg} />
        <Fan cands={cands} ox={caret.x + px * 0.3} oy={caret.y + th * 0.58} x2={caret.x + px * 1.6} top={caret.y + th * 1.6}
          pitch={th * 1.0} px={Math.round(px * 0.72)} grow={grow} pick={pick} pickOn={pickOn} travel={travel}
          to={caret} wither={wither} roll={r} labelPx={labelPx} ink={ink} U={U} lw={lw} tint0={context.length} keep={0.45}
          spray={{len: px * 6, n: 30, t, durF, fps, seed: 23}} />
        {nextOn > 0 ? <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <Spray x={caretNow + px * 0.3} y={caret.y} len={px * 3.4} n={22} spread={1.0} ink={ink.dim} lw={lw}
            grow={nextOn} t={t} durF={durF} fps={fps} seed={77} />
        </svg> : null}
        <Caret x={caretNow} y={caret.y} h={th * 0.9} color={ink.acc2} on={ctxOn} U={U} />
        {blankNote ? <div style={{position: 'absolute', left: x0, top: f.zBot - U * 0.2, color: ink.dim,
          opacity: blank * (1 - 0.5 * nextOn), font: `500 ${lpx}px/1.2 ${DISPLAY}`, fontStyle: 'italic', whiteSpace: 'nowrap'}}>{blankNote}</div> : null}
        {/* the imagined rest of the answer: a dark cover over the page past the caret */}
        {lift < 1 ? (
          <div style={{position: 'absolute', left: coverX, top: cover.t, width: W - cover.l, height: cover.b - cover.t,
            background: ink.fg, borderRadius: `${U * 0.02}px 0 0 ${U * 0.02}px`}}>
            {coverLabel ? <div style={{position: 'absolute', left: U * 0.06, top: '42%', color: mix(ink.bg, ink.fg, 0.15),
              font: `500 ${lpx}px/1.2 ${DISPLAY}`, fontStyle: 'italic', whiteSpace: 'nowrap'}}>{coverLabel}</div> : null}
          </div>
        ) : null}
        {titleEl}
        <Source text={source} at={sourceAt} W={W} H={H} on={sOn} ink={ink.dim} />
      </AbsoluteFill>
    );
  }

  // ── one window: stream / check ──
  const replyPx = Math.round(U * (mode === 'check' ? 0.062 : 0.058));
  const leftCol = titled && (col === 'l');
  const px0 = leftCol ? W * 0.37 : sx;
  const pw = W - sx - px0;
  const top = f.zTop - U * 0.03;
  const bot = f.zBot - U * 0.01;
  const p = mode === 'stream' ? clamp01(seg(t, 0.12, 0.96)) : 1;
  const k = wordsAt(nW, p, 5);
  const ringP = mode === 'check' ? easeInOutCubic(clamp01(seg(t, ...cue.win('ring', 0.32, 0.48, REACH_CUBIC)))) : 0;
  const tick = mode === 'check' ? easeOutCubic(clamp01(seg(t, ...cue.win('checkLabel', 0.5, 0.6, REACH_CUBIC)))) : 0;
  // the closing frame keeps breathing: the reader's ring is re-inked slowly, as a pen going over it again
  const pen = mode === 'check' && !reduced ? 0.85 + 0.15 * life(t, durF, fps, 3.4, 0) : 1;
  // as the reply grows past its region, it scrolls up under a soft fade to keep the caret in view (as a chat app
  // does); the scroll follows the written length continuously, so it glides rather than jumping a line at a time
  const checkNode = mode === 'check' && checkLabel ? (
    <>
      <svg width={pw} height={bot - top} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <Tick x={U * 0.08} y={(bot - top) * 0.62} s={U * 0.06} color={ink.acc2} p={tick} lw={Math.max(5, U * 0.007)} />
      </svg>
      <div style={{position: 'absolute', left: U * 0.14, top: (bot - top) * 0.62 - f.label * 0.7, color: ink.fg,
        opacity: tick, font: `600 ${Math.round(U * 0.04)}px/1.2 ${BODY}`, whiteSpace: 'nowrap'}}>{checkLabel}</div>
    </>
  ) : null;
  return (
    <AbsoluteFill style={{background: groundOf(dna, ink)}}>
      {titleEl}
      <Pane x={px0} y={top} w={pw} h={bot - top} ink={ink} U={U} on={pOn} question={question} reply={reply} shown={k}
        caret={mode === 'stream' && p < 1} busy={mode === 'stream' && p < 1} replyPx={replyPx}
        ring={mode === 'check' ? ring : undefined} ringP={ringP * pen} autoScroll={mode === 'stream'}
        look={look} side={leftCol ? 1 : 0}>{checkNode}</Pane>
      <Source text={source} at={sourceAt} W={W} H={H} on={sOn} ink={ink.dim} />
    </AbsoluteFill>
  );
};
