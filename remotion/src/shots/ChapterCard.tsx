// SHOT · ChapterCard — a chapter of the argument opens: one short statement rises unit by unit through its mask
// (a Latin word, or one CJK character), its accent span (`*…*`) inked in the accent once it lands, numbered 01 / 04
// with a hairline showing how far through the film we are. The breath between product or diagram beats.
// (references/promo-film.md §cards — the same card the promo film uses, here inside a narrated film.)
//
// Every word is a prop: `text` (the statement — the film's own line, ≤ ~8 words / ~16 CJK characters), `kicker`
// (the chapter's name), `index`/`total` (its place in the argument). The statement sits in the zone above the
// caption band; the numbering and the progress hairline sit at the top.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useDNA} from '../runtime/dna';
import {SceneDurationContext} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {LookContext, lookFromDna, typeScale, alpha, span, MONO} from '../promo/kit';
import {CardGround, RiseLine} from '../promo/Cards';

export const DURATION = 90; // 3s
// the shot frames and moves its own camera: coverage leaves it alone
export const CAMERA = 'directed';

type Props = {text?: string; kicker?: string; index?: number; total?: number; size?: number};

const Card: React.FC<Required<Pick<Props, 'size'>> & Props & {dur: number}> = ({text = '', kicker, index, total, size, dur}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const s = typeScale(W, H);
  const look = React.useContext(LookContext);
  const zoneBottom = H - captionBand(W, H);
  const pad = 72 * s;
  const meta = span(frame, 0, 10, 'out') * (1 - span(frame, dur - 8, dur, 'exit'));
  const p0 = index && total ? (index - 1) / total : 0, p1 = index && total ? index / total : 0;
  const bar = span(frame, 4, 22, 'snappy');
  const push = 1 + 0.02 * span(frame, 0, dur, 'linear');
  return (
    <CardGround>
      <div style={{position: 'absolute', left: pad, right: pad, top: CONTENT_TOP, height: zoneBottom - CONTENT_TOP, display: 'flex',
        alignItems: 'center', justifyContent: 'center', transform: `scale(${push})`}}>
        {text ? <RiseLine text={text} px={(H > W ? size * 0.9 : size) * s} start={3} leaveAt={dur - 9} maxWidth={W - 2 * pad} /> : null}
      </div>
      {index ? (
        <div style={{position: 'absolute', left: pad, right: pad, top: pad * 0.8, opacity: meta}}>
          <div style={{display: 'flex', alignItems: 'baseline', gap: 18 * s, fontFamily: MONO, fontSize: 22 * s, letterSpacing: '0.16em',
            textTransform: 'uppercase', color: look.muted}}>
            <span style={{color: look.accentInk, fontWeight: 700, fontSize: 30 * s, letterSpacing: '0.04em'}}>{String(index).padStart(2, '0')}</span>
            {total ? <span>/ {String(total).padStart(2, '0')}</span> : null}
            {kicker ? <span style={{marginLeft: 10 * s, color: look.ink}}>{kicker}</span> : null}
          </div>
          {total ? (
            <div style={{position: 'relative', marginTop: 16 * s, height: 2 * s, background: alpha(look.ink, 0.12)}}>
              <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${p0 * 100}%`, background: alpha(look.ink, 0.35)}} />
              <div style={{position: 'absolute', left: `${p0 * 100}%`, top: -1 * s, height: 4 * s, width: `${(p1 - p0) * 100 * bar}%`,
                background: look.accent, boxShadow: `0 0 ${10 * s}px ${alpha(look.accent, 0.6)}`}} />
            </div>
          ) : null}
        </div>
      ) : null}
    </CardGround>
  );
};

// the form's own demo copy (what a preview shows); a film always sends its own
export const ChapterCard: React.FC<Props> = ({text = 'One *statement* opens each chapter.', kicker = 'Chapter', index = 1, total = 3, size = 104}) => {
  const dna = useDNA();
  const {durationInFrames} = useVideoConfig();
  const dur = React.useContext(SceneDurationContext) ?? durationInFrames;
  return (
    <LookContext.Provider value={lookFromDna(dna)}>
      <AbsoluteFill>
        <Card text={text} kicker={kicker} index={index} total={total} size={size} dur={dur} />
      </AbsoluteFill>
    </LookContext.Provider>
  );
};
export default ChapterCard;
