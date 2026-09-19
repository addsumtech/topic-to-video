// FIGURE — the film's number, printed as the film wrote it.
//
// WHY THIS EXISTS. Eight registers printed a figure by stripping the film's string down to digits and
// re-formatting what was left: `parseFloat(String(value).replace(/[^\d.]/g, ''))`. That one line turns
// "−12" into 12, "3–5" into 35, "2019-2024" into 20,192,024, "N/A" into 0 and "1.2M" into 1.2 — and
// `Math.round` then turns 4.2 into 4 and 99.6 into 100. Every one of those is a figure on a delivered frame
// that nobody supplied, which is the one thing this library must never draw. The fix is not a better regex
// in each register; it is that the SETTLED frame prints the film's string, byte for byte, and only a string
// that is unambiguously ONE number is allowed to count up to it.
//
// THE RULES:
//   * `figureText` is what a settled frame shows: the input, trimmed. Never re-formatted, never rounded.
//   * `parseFigure` recognises exactly one number with an optional sign, grouping commas, decimals, a prefix
//     (`$`, `~`, `≈`) and a suffix (`%`, `ms`, `k`, `×`, ` 个`). Anything else — a range, a date span, two
//     numbers, no number — has `num: null` and is shown verbatim at every frame: there is nothing honest to
//     count up to.
//   * `figureAt(fig, p)` is the count-up frame: the same prefix, sign, decimals, grouping and suffix as the
//     input, with the magnitude scaled by p. At p >= 1 it returns `figureText` exactly.
//   * `figureValue` is the number for DRAWING (a bar length, an arc) — null when the string is not one number,
//     so a register that needs a quantity can refuse instead of drawing 0.

export type Figure = {
  /** the film's string, trimmed — what the settled frame prints */
  text: string;
  /** the single number it states, signed; null when it is not exactly one number */
  num: number | null;
  prefix: string;
  suffix: string;
  decimals: number;
  grouped: boolean;
};

// prefix · sign · integer (grouped or not) · decimals · suffix. The prefix may not contain a digit or a sign,
// and the suffix may not contain a digit, so "3–5" and "2019-2024" cannot match.
const ONE_NUMBER = /^([^\dA-Za-z+\-−]*?)([+\-−]?)((?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.(\d+))?([^\d]*)$/;

export const figureText = (raw: unknown): string => String(raw ?? '').trim();

export const parseFigure = (raw: unknown): Figure => {
  const text = figureText(raw);
  const m = ONE_NUMBER.exec(text);
  if (!m) return {text, num: null, prefix: '', suffix: '', decimals: 0, grouped: false};
  const [, prefix, sign, int, dec = '', suffix] = m;
  // a suffix that starts with a separator a range would use means this was never one number ("3 – 5" is
  // excluded by the digit rule already; "3-" alone is not a figure anyone writes)
  const magnitude = parseFloat(int.replace(/,/g, '') + (dec ? '.' + dec : ''));
  const neg = sign === '-' || sign === '−';
  return {
    text, num: neg ? -magnitude : magnitude, prefix, suffix,
    decimals: dec.length, grouped: int.includes(','),
  };
};

const _format = (fig: Figure, v: number): string => {
  const signStr = v < 0 ? (fig.text.includes('−') ? '−' : '-') : (/^[^\d]*\+/.test(fig.text) ? '+' : '');
  const abs = Math.abs(v);
  let body = abs.toFixed(fig.decimals);
  if (fig.grouped) {
    const [i, d] = body.split('.');
    body = i.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (d != null ? '.' + d : '');
  }
  return `${fig.prefix}${signStr}${body}${fig.suffix}`;
};

/** The frame at count-up progress p (0..1). At p >= 1, or when the string is not one number, the film's text. */
export const figureAt = (fig: Figure, p: number): string => {
  if (fig.num == null || !(p < 1)) return fig.text;
  return _format(fig, fig.num * Math.max(0, p));
};

/** The number to DRAW with (a bar, an arc), or null when the film's string is not exactly one number. */
export const figureValue = (raw: unknown): number | null => parseFigure(raw).num;
