// A KINETIC LINE A SEAM CAN TAKE HOLD OF — the `word` carry anchor (runtime/carry.tsx) on runtime/kinetic type.
//
// A container carries the anchor's RECT from one beat into the next, `grow` opens the next beat out of it and
// `through-window` pushes into it (seams.tsx). None of the kinetic registers declared one, so a type film could not
// go "through the word" except by hand (bench-rams F5). This wraps a KineticText in an element marked
// `data-carry="word"` whose box is the type's own measured extent — the lines the copy was laid out on, not the
// fitting box around them — and, when the copy is ONE line, `data-carry-glyph`, so a through-window looks through the
// letterforms (seams.tsx glyphOf reads every drawn glyph holder). A swap's anchor hugs its LAST alternative: that is
// the one on the frame when the beat leaves.
//
// The wrapper paints nothing and moves nothing: the KineticText inside it is placed so every glyph lands exactly where
// it would without the wrapper. carry_anchors.py credits `word` to any register that DRAWS `<KineticWord`.
import React from 'react';
import {KineticText, KineticTextProps, KLayout} from './kinetic';

/** The extent of the type a KineticWord marks, in the KineticText's own box px: its alternative's line boxes. */
export const kineticExtent = (lay: KLayout | null): {left: number; top: number; width: number; height: number;
  lines: number} | null => {
  if (!lay) return null;
  const alt = lay.alts[lay.alts.length - 1];
  const ls = alt.lines.filter((l) => l.text.trim());
  if (!ls.length) return null;
  const left = Math.min(...ls.map((l) => l.left)), right = Math.max(...ls.map((l) => l.right));
  const top = Math.min(...ls.map((l) => l.top)), bottom = Math.max(...ls.map((l) => l.bottom));
  return {left, top, width: Math.max(1, right - left), height: Math.max(1, bottom - top), lines: ls.length};
};

export const KineticWord: React.FC<KineticTextProps & {
  /** false: a box anchor even on one line (a word too thin, or set on a path, to be looked through) */
  glyph?: boolean;
}> = ({glyph = true, ...props}) => {
  const ext = kineticExtent(props.k.layout);
  if (!ext) return <KineticText {...props} />;
  return (
    <div data-carry="word" data-carry-glyph={glyph && ext.lines === 1 ? '' : undefined}
      style={{position: 'absolute', left: props.x + ext.left, top: props.y + ext.top, width: ext.width,
        height: ext.height, pointerEvents: 'none'}}>
      <KineticText {...props} x={-ext.left} y={-ext.top} />
    </div>
  );
};
