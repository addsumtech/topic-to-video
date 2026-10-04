// SHOT · Chat Thread — conversation language: a messaging thread where you ask and WorkBuddy replies, with
// typing indicators and bubbles sliding in. Light, human, casual (a communication/support look). Deterministic.
//
// EVERY MESSAGE THE FILM GIVES IS ON SCREEN WHEN THE SHOT SETTLES — or the register refuses. Past its type
// floor this thread used to clip, and the comment said that was "what a chat does with its oldest messages".
// It was not what this one did: the column was laid out from the TOP with `overflow: hidden`, so the clip
// took the NEWEST messages off the bottom. A nine-turn Chinese booking exchange rendered with its last reply —
// the line the exchange is for — cut off at the column's bottom edge, a few pixels of it showing. So two changes:
//   * past the floor it THROWS, naming the room it needed and what to do (split the exchange over two beats,
//     or shorten it). Scrolling the oldest away instead would be chat-like, but a film whose early turns land
//     close together would have a message on screen for a few frames and then gone — dropped, quietly — and a
//     settled frame that shows only half the thread it was given;
//   * the column is still anchored so that IF it overflows (the fit is an estimate) the overflow leaves by
//     the TOP, the way a chat scrolls, and the newest message stays in view. While the thread fits, it sits at
//     the top exactly as before.
// A message with no text, no `at`, an `at` too late to finish landing, or a side other than 'you' / 'wb' also
// throws: each of those used to draw nothing (an `at` of undefined never passes `t > at - 0.02`) or, for an
// unrecognised side ('user', 'bot', a typo), draw it on the LEFT as a reply with no typing indicator — the
// human's message on the assistant's side if the film meant 'user' — with no error anywhere.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, textWidthPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
// LEVEL-C DNA migration: the whole chat UI flips together — ground, bubble surfaces, ink, and on-accent text — so
// on a dark DNA it reads as a dark chat instead of light-ink-on-light-bubble (the level-A inversion). Both the main
// component AND the Bubble subcomponent read useDNA (a subcomponent renders inside the provider). Null DNA = original.
const YOU = '#2E7BFF', WB = '#f0f1f4', INK = '#1b2333', A2 = '#7C5CFF', DOT = '#9aa3b2';
type Msg = {side: 'you' | 'wb'; text: string; at: number};
// A bubble rises over RISE of the clip, but its easeOutBack passes 1 at 0.37 of the way (and the clamp holds
// it there), so it is opaque and in place ~0.08 after its `at`. LAST_AT is the latest `at` that is still whole
// on the settled frame; at 0.95 it ends 77% opaque, at 1.0 it is never drawn at all.
const RISE = 0.22, LAST_AT = 0.9;
const FLOOR = 0.34;   // the smallest type scale, below which a bubble is not readable at 1080p (46px -> ~16px)
const DEFAULT_MSGS: Msg[] = [
  {side: 'you', text: 'Build the Q3 board deck from the finance folder', at: 0.1},
  {side: 'wb', text: 'On it — planning now.', at: 0.32},
  {side: 'wb', text: '5 experts working in parallel…', at: 0.5},
  {side: 'wb', text: 'Done ✓ — 24 slides, in your Deliverables folder.', at: 0.74},
];

// THE THREAD SCALES WITH ITS COLUMN. Every number here was drawn for a 1500px column, and the column is
// `min(1500, W * 0.94)` — 1015 on a 1080-wide frame. So the same four messages wrapped to more lines in a
// narrower box at the SAME 46px, and the last one ('Done ✓ — 24 slides, in your Deliverables folder.', the
// line the whole exchange is for) ran 28px into the caption band at 1:1. A chat column that gets narrower
// sets its type smaller; `f` is exactly 1 on any frame wide enough for the full column, so 16:9 and 9:16
// are byte-identical.
const Bubble: React.FC<{m: Msg; t: number; f: number}> = ({m, t, f}) => {
  const dna = useDNA();
  const glide = useGlide();
  const A1 = dna?.accent ?? YOU, SURF = dna?.surface ?? WB, INKc = dna?.fg ?? INK, ON = dna?.onAccent ?? '#fff', A2c = dna?.accent2 ?? A2;
  const r = easeOutBack(seg(t, m.at, m.at + RISE));
  const you = m.side === 'you';
  const av = Math.round(74 * f);
  return (
    <div style={{display: 'flex', justifyContent: you ? 'flex-end' : 'flex-start', marginBottom: Math.round(34 * f),
      opacity: clamp01(r), transform: glide(`translateY(${lerp(30, 0, clamp01(r))}px)`, r !== 1)}}>
      {!you && <div style={{width: av, height: av, borderRadius: av / 2, marginRight: Math.round(22 * f), background: `linear-gradient(150deg,${A1},${A2c})`, flexShrink: 0}} />}
      {/* overflowWrap: a run with no break opportunity (a URL, a row of ✅) used to run straight out of the
          bubble's right edge and across the frame; it now breaks inside the bubble. Text that has break points
          lays out exactly as before. */}
      <div style={{maxWidth: 880 * f, padding: `${Math.round(30 * f)}px ${Math.round(40 * f)}px`, borderRadius: Math.round(28 * f), background: you ? A1 : SURF,
        overflowWrap: 'anywhere', color: you ? ON : INKc, font: `500 ${Math.round(46 * f)}px/1.35 var(--f-body, Inter,system-ui,sans-serif)`, borderBottomRightRadius: you ? 8 : Math.round(28 * f), borderBottomLeftRadius: you ? Math.round(28 * f) : 8}}>{m.text}</div>
    </div>
  );
};

const normalise = (msgs: unknown): Msg[] => {
  if (!Array.isArray(msgs) || msgs.length < 1) {
    throw new Error(`ChatThread needs at least one message in \`messages\` (got ${Array.isArray(msgs) ? 0 : typeof msgs}). ` +
      "Pass [{side: 'you' | 'wb', text, at}].");
  }
  return msgs.map((m: any, i: number) => {
    const text = String(m?.text ?? '').trim();
    if (!text) throw new Error(`ChatThread: message ${i + 1} has no \`text\`.`);
    if (m?.side !== 'you' && m?.side !== 'wb') {
      throw new Error(`ChatThread: message ${i + 1} ("${text.slice(0, 24)}") needs \`side\` 'you' (right, in the accent) or ` +
        `'wb' (left, with the avatar and a typing indicator), got ${JSON.stringify(m?.side)}.`);
    }
    const at = Number(m?.at);
    if (m?.at == null || !Number.isFinite(at) || at < 0 || at > LAST_AT) {
      throw new Error(`ChatThread: message ${i + 1} ("${text.slice(0, 24)}") needs \`at\` between 0 and ${LAST_AT} — the ` +
        `fraction of the clip where it appears (a later one is still fading in on the last frame, and 1 or more is ` +
        `never drawn), got ${JSON.stringify(m?.at)}.`);
    }
    return {side: m.side, text, at};
  });
};

export const ChatThread: React.FC<{messages?: Msg[]}> = ({messages: RAW = DEFAULT_MSGS} = {}) => {
  const MSGS = normalise(RAW);
  const dna = useDNA();
  const BG = dna?.bg ?? '#fbfcfe', SURF = dna?.surface ?? WB, A1 = dna?.accent ?? YOU, A2c = dna?.accent2 ?? A2, DIM = dna?.dim ?? DOT;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // typing indicator shows just before the next wb message
  const nextWb = MSGS.find((m) => m.side === 'wb' && t > m.at - 0.12 && t < m.at);
  const CW = Math.min(1500, W * 0.94);
  // AND A THREAD IS AS TALL AS ITS CONTENT, not as wide as its column. Scaling by width alone is right for
  // the demo's four short messages and wrong for five long ones: at 16:9 the last two ran off the bottom
  // AND through the caption band, and the width was never the thing that overflowed. So estimate the stack
  // the way `fitBlockPx` estimates a headline — the advance is deliberately generous and a Han glyph counts
  // a full em — and close the type up until it fits the content zone. `f` stays exactly 1 on any frame wide
  // enough for the full column, so 16:9 and 9:16 with the demo thread are untouched.
  const TOP = 170;
  const BUDGET = contentBottom(W, H) - TOP;
  const heightAt = (k: number) => {
    const measure = Math.max(1, Math.min(880 * k, CW - 96 * k) - 80 * k);   // the bubble's text column
    return MSGS.reduce((h, m) => {
      const lines = Math.max(1, Math.ceil(textWidthPx(m.text, 46 * k) / measure));
      return h + lines * 46 * k * 1.35 + 60 * k + 34 * k;                   // padding + the row's margin
    }, 0);
  };
  let scale = Math.min(1, CW / 1500);
  // A FIXED NUMBER OF STEPS, because the estimate is not continuous — a line count changes in jumps — so a
  // while-loop on it can sit between two states forever. Four halvings of the error is plenty and always
  // terminates.
  for (let i = 0; i < 4 && heightAt(scale) > BUDGET; i++) {
    scale *= Math.sqrt(BUDGET / heightAt(scale));
  }
  // and a floor, because type nobody can read is not a fix. Past it the thread does not fit this beat, and
  // the register says so rather than cutting messages off (see the header).
  if (heightAt(FLOOR) > BUDGET) {
    throw new Error(`ChatThread: these ${MSGS.length} messages need about ${Math.round(heightAt(FLOOR))}px even at the ` +
      `smallest readable type, and the content zone of this ${W}x${H} frame holds ${Math.round(BUDGET)}px. Split the ` +
      'exchange across two ChatThread beats, or shorten the messages.');
  }
  const f = Math.max(FLOOR, scale);
  // BOTTOM-ANCHORED OVERFLOW. The column is a flex column justified to the END with a growing spacer after the
  // thread: while the thread fits, the spacer takes the slack and the thread sits at the top (the look is
  // unchanged); if the estimate above was short and it overflows, the spacer is 0 and the overflow leaves by
  // the top — the oldest message — the way a chat scrolls, never the newest.
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: (W - CW) / 2, top: TOP, width: CW,
        height: BUDGET, overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end'}}>
        <div style={{flexShrink: 0}}>
        {MSGS.map((m, i) => (t > m.at - 0.02 ? <Bubble key={i} m={m} t={t} f={f} /> : null))}
        {nextWb && (
          <div style={{display: 'flex', alignItems: 'center', gap: Math.round(22 * f), marginBottom: Math.round(34 * f)}}>
            <div style={{width: Math.round(74 * f), height: Math.round(74 * f), borderRadius: Math.round(37 * f), background: `linear-gradient(150deg,${A1},${A2c})`}} />
            <div style={{padding: `${Math.round(30 * f)}px ${Math.round(36 * f)}px`, borderRadius: Math.round(28 * f), background: SURF, display: 'flex', gap: Math.round(12 * f)}}>
              {[0, 1, 2].map((k) => <div key={k} style={{width: Math.round(18 * f), height: Math.round(18 * f), borderRadius: Math.round(9 * f), background: DIM,
                opacity: 0.4 + 0.6 * Math.max(0, Math.sin((t * 30 - k * 2)))}} />)}
            </div>
          </div>
        )}
        </div>
        <div style={{flexGrow: 1}} />
      </div>
    </AbsoluteFill>
  );
};
export default ChatThread;
