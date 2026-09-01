// ICONS — one coherent line family, so a category beat can name what it is instead of pointing at a block.
//
// WHY THIS EXISTS. This tier had no icons at all. A register with a list drew an abstract mark per row —
// QuadSplit's `bars` / `ring` / `dots` / `wave` — chosen by INDEX, so the same four shapes appeared on every
// film in the same order whatever the labels said. A viewer reads "开表格" beside a ring and learns nothing
// from the ring; it is furniture that happens to be on the frame. The html tier settled this long ago
// (`references/icons.md`): an icon must answer **what is this / what does it do / why pay attention** before
// the viewer reads the text, and if it answers none it is decoration and gets cut.
//
// ONE FAMILY ACROSS BOTH TIERS. Same 24-unit grid, same 2-unit stroke, same round caps and joins as the
// html tier's Lucide set, so a film that mixes tiers reads as one identity system rather than two. These
// are drawn here rather than imported: the render bundle stays dependency-free and deterministic, and every
// glyph can be checked against the frame it actually ships on.
//
// THE RULES THAT KEEP THEM FROM BECOMING SLOP, carried over verbatim in intent from references/icons.md:
//   * Pick by the ROLE the point plays, not by the picture the word suggests.
//   * An icon on EVERY row of every beat is wallpaper. A few, consistent, purposeful.
//   * Never beside a headline figure — the number is the focal point and an icon competes with it.
//   * Never larger than the title it sits with.
//   * An unknown name THROWS. A silently-missing icon is a hole in a layout nobody notices until delivery.
import React from 'react';

export type IconName =
  // category — what kind of thing this is
  | 'file' | 'table' | 'slides' | 'image' | 'folder' | 'layout'
  // action — a thing being done
  | 'edit' | 'search' | 'refresh' | 'download' | 'send' | 'wand'
  // decision / structure
  | 'checks' | 'branch' | 'boxes' | 'target'
  // state
  | 'clock' | 'alert' | 'lock' | 'check'
  // data / people / talk
  | 'chart' | 'database' | 'users' | 'message' | 'code' | 'trend';

// Each entry draws inside a 24x24 box. Stroke is applied by the component, so a glyph never hardcodes ink.
const P: Record<IconName, React.ReactNode> = {
  file: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" />
    <path d="M9 13h6" /><path d="M9 17h4" /></>,
  table: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18" /><path d="M3 15h18" />
    <path d="M9 4v16" /></>,
  slides: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M12 16v4" /><path d="M8 20h8" /></>,
  image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8.5" cy="9.5" r="1.5" />
    <path d="M21 15l-5-5-9 9" /></>,
  folder: <><path d="M3 7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></>,
  layout: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18" /><path d="M10 9v11" /></>,

  edit: <><path d="M4 20h4l10-10a2.8 2.8 0 0 0-4-4L4 16z" /><path d="M13.5 6.5l4 4" /></>,
  search: <><circle cx="11" cy="11" r="6" /><path d="M20 20l-4.5-4.5" /></>,
  refresh: <><path d="M20 12a8 8 0 1 1-2.3-5.6" /><path d="M20 4v5h-5" /></>,
  download: <><path d="M12 4v11" /><path d="M8 11l4 4 4-4" /><path d="M4 20h16" /></>,
  send: <><path d="M21 4L3 11l7 3 3 7z" /><path d="M10 14l4-4" /></>,
  wand: <><path d="M5 19L16 8" /><path d="M14 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" /><path d="M19 12l.7 1.4 1.4.6-1.4.7-.7 1.3-.7-1.3-1.3-.7 1.3-.6z" /></>,

  checks: <><path d="M4 7l2 2 3-3" /><path d="M4 15l2 2 3-3" /><path d="M13 8h7" /><path d="M13 16h7" /></>,
  branch: <><circle cx="6" cy="5" r="2" /><circle cx="6" cy="19" r="2" /><circle cx="18" cy="12" r="2" />
    <path d="M6 7v10" /><path d="M8 12h8" /></>,
  boxes: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.5" /><path d="M12 2v3" />
    <path d="M12 19v3" /><path d="M2 12h3" /><path d="M19 12h3" /></>,

  clock: <><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></>,
  alert: <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17.2v.1" /></>,
  lock: <><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
  check: <><circle cx="12" cy="12" r="8.5" /><path d="M8 12.5l2.7 2.7L16 9" /></>,

  chart: <><path d="M4 20V10" /><path d="M10 20V4" /><path d="M16 20v-7" /><path d="M3 20h18" /></>,
  database: <><ellipse cx="12" cy="6" rx="8" ry="3" /><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6" />
    <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
  users: <><circle cx="9" cy="8" r="3.2" /><path d="M3 20a6 6 0 0 1 12 0" /><path d="M16.5 5.6a3.2 3.2 0 0 1 0 5.8" />
    <path d="M17 14.4A6 6 0 0 1 21 20" /></>,
  message: <><path d="M4 5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-5 4V6a1 1 0 0 1 1-1z" /></>,
  code: <><path d="M9 8l-5 4 5 4" /><path d="M15 8l5 4-5 4" /></>,
  trend: <><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></>,
};

export const ICON_NAMES = Object.keys(P) as IconName[];

/**
 * One icon, drawn at `size` px on the 24-grid, inked with `ink`.
 *
 * PURE, like the content atoms: no remotion hooks and no internal animation, so a shot keeps ownership of
 * timing. Fade or scale it from the outside.
 */
export const Icon: React.FC<{
  name: IconName;
  size: number;
  ink?: string;
  /** stroke weight in GRID units (the 24-box), so it scales with the icon rather than going spidery */
  weight?: number;
  style?: React.CSSProperties;
  title?: string;
}> = ({name, size, ink = 'currentColor', weight = 2, style, title}) => {
  const d = P[name];
  if (!d) {
    // LOUD. A missing icon leaves a hole the layout still reserves space for, which reads as a bug nobody
    // notices until the film is delivered — the same failure mode as an unknown QuadSplit glyph.
    throw new Error(`Icon: unknown name "${name}". Use one of: ${ICON_NAMES.join(', ')}`);
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={ink}
      strokeWidth={weight} strokeLinecap="round" strokeLinejoin="round"
      aria-hidden={title ? undefined : true} role={title ? 'img' : undefined} style={style}>
      {title ? <title>{title}</title> : null}
      {d}
    </svg>
  );
};

export default Icon;
