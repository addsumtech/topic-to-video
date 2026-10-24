// LABEL WIDTHS — how wide each label really is, in the face the shot resolves, measured by the browser.
//
// A chip sized from the advance ESTIMATE (layout.textWidthPx, 0.72 em a Latin glyph — deliberately generous so a fit
// never under-counts) is half again as wide as the label inside it, and a map whose every chip is a slab with a short
// word floating in it reads as a placeholder. A collision check run on that estimate also refuses layouts that fit.
// So the labels are laid out once by runtime/kinetic's reference node — the face the shot resolves, at the size it
// draws — and each label's line extent is read back. `widths` is null until the measurement lands (the frame is held
// until it does), and a caller must not place anything on the estimate in the meantime.
import {useKinetic} from './kinetic';

export function useLabelWidths(texts: string[], family: string, weight: number, size: number) {
  const k = useKinetic({text: texts.length ? texts : [' '], w: 100000, fit: 'none', align: 'left',
    font: {family, weight, size, lineHeight: 1.2}});
  const lines = k.layout?.alts[0]?.lines ?? null;
  const widths = lines ? texts.map((_, i) => {
    const ls = lines.filter((l) => l.para === i);
    return ls.length ? Math.max(...ls.map((l) => l.right)) - Math.min(...ls.map((l) => l.left)) : 0;
  }) : null;
  return {widths, anchor: k.anchor};
}
