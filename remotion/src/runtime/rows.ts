/**
 * A register's LIST prop, normalised — or a refusal that names what was actually sent.
 *
 * WHY THIS EXISTS. A register declares `parts?: Part[]` and then calls `parts.map(...)`. Handed a string,
 * that dies with `parts.map is not a function` — an error that names a line of the REGISTER and says nothing
 * about the board that caused it. It is not a hypothetical: a fixture generator that mis-read one nested
 * type handed `cells` a sentence, and the library-wide sweep recorded the result as
 * "SameStuffChanged refused to render — TypeError", a finding filed under the register's name for a defect
 * that was entirely in its caller. Two sessions were spent on the wrong file before the message was read
 * closely enough to notice it described the shape, not the content.
 *
 * `Array.isArray(v) ? v : []` is the other tempting answer and it is worse: it swallows the wrong shape and
 * lets the register refuse a few lines later with a message about the COUNT ("needs at least two stages"),
 * which sends the reader looking for missing data that is in fact right there in the wrong wrapper.
 *
 * So: absent is absent and returns nothing; a list is itself; anything else is a mistake that is named.
 */
const describe = (v: unknown): string => {
  if (typeof v === 'string') {
    const s = v.length > 40 ? v.slice(0, 40) + '…' : v;
    return `a string (${JSON.stringify(s)})`;
  }
  if (typeof v === 'object') return 'a single object — wrap it in a list';
  return `a ${typeof v} (${String(v)})`;
};

export const rows = <T>(v: unknown, prop: string, shot: string): T[] => {
  if (v === null || v === undefined) return [];
  if (Array.isArray(v)) return v as T[];
  throw new Error(
    `${shot}'s \`${prop}\` must be a LIST and it was given ${describe(v)}. Nothing here can be drawn from ` +
    `that shape; send a list, or leave the prop out and let the register use its own default.`);
};
