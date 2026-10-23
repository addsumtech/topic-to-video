// THE PLATFORM'S OWN UI — where a 9:16 film posted to Xiaohongshu / Douyin / TikTok / Reels / Shorts is covered.
//
// No platform publishes organic-post safe zones; ad specs and third-party tables agree on ranges for 1080×1920: the
// top 5–11% under the tabs, the BOTTOM 17–35% under the description, author and music line, and a column of buttons
// down the right from about 40% of the height (references/craft-research.md §2). A caption burned into the bottom
// 13% — where this renderer put it — sits under the description on every one of them.
//
// THE `social` PROFILE (meta.safe_zone, the default for 9:16) keeps everything a viewer must read out of those zones:
//   · the caption's bottom edge at ~81% of the height (the bottom 19% left to the platform);
//   · a REGISTER is drawn in a frame scaled by `k` from `y0` — its own reserved caption band then lands exactly where
//     the caption now is, so no register in the library is re-laid-out (a re-layout re-keys every register's measured
//     manifest: layout.ts is imported by 120 of them);
//   · a STAGE (remotion/src/stage/) lays itself out in the safe area directly: its title from `top`, its zone above
//     the caption, its labels clear of the button column.
// Imported only by Film.tsx and the stage components, never by a register.
import React from 'react';

export type SafeProfile = {
  name: 'social';
  top: number;        // the top share a title starts below (platform tabs)
  bottom: number;     // the bottom share left to the platform (description, author, music)
  right: number;      // the right share the button column covers…
  rightFrom: number;  // …from this share of the height down
  k: number;          // a register's frame scale
  y0: number;         // the register frame's top, as a share of the height
};

/** The caption's size on a platform-safe film, against the film's own: a size larger (vertical-video guidance starts
 *  captions around 55-65px at 1080 wide). Film.tsx sets it and CardStage reserves room for it — one number. */
export const SAFE_CAPTION_SCALE = 1.15;

export const SOCIAL: SafeProfile = {name: 'social', top: 0.08, bottom: 0.19, right: 0.14, rightFrom: 0.40, k: 0.80, y0: 0.03};

/** The profile a film asks for (`safe: 'social'`), on a portrait frame only — a landscape film has no such UI. */
export const safeProfile = (safe: unknown, W: number, H: number): SafeProfile | null =>
  safe === 'social' && H > W ? SOCIAL : null;

export const SafeZoneContext = React.createContext<SafeProfile | null>(null);

/** Where a register's 1:1 canvas goes in the frame: scaled by k, centred across, from y0 down. */
export const registerFrame = (W: number, H: number, p: SafeProfile) => ({k: p.k, x0: ((1 - p.k) * W) / 2, y0: p.y0 * H});

/** The caption block's bottom edge, in frame px: the register frame's bottom less the caption's own margin. */
export const captionBottomY = (H: number, p: SafeProfile, capMargin: number) => p.y0 * H + p.k * H - capMargin;
