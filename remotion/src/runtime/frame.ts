// A FILM IS NOT A SLIDE DECK: most shots carry no header title (validate's SLIDE TITLES warning,
// references/remotion-shot-authoring.md rule 5). A shot without one keeps only an action-safe top margin, so its
// picture gets the band a title would have taken; a shot that keeps a title starts its content at CONTENT_TOP.
import {CONTENT_TOP} from './layout';

export const contentTop = (W: number, H: number, titled = false): number =>
  titled ? CONTENT_TOP : Math.round(Math.min(W, H) * 0.065);
