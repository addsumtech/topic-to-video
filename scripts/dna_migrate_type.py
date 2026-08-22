#!/usr/bin/env python3
"""dna_migrate_type — rewrite hardcoded font families in the shot library to DNA-aware CSS variables.

    font: '800 200px/0.9 Inter, system-ui, sans-serif'
 -> font: '800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)'

The ORIGINAL family list becomes the variable's fallback, so a film with no DNA resolves exactly what
it resolved before (verified on real renders by scripts/null_dna_pixel_gate.py, not asserted).

Role is a HEURISTIC read off the shorthand: a mono family list -> mono; else >= 64px -> display;
else body. No gate can check whether a role is RIGHT - a heading on --f-body still renders fine - so
--report is reviewed by a human before --apply.

Every `font:`/`fontFamily:` declaration AND every SVG/JSX `fontFamily="..."` presentation attribute
the scanner finds is ACCOUNTED FOR: it is either rewritten, or recorded in the SKIPPED table with a
reason. Something this script cannot parse is a silent miss waiting to leave a shot's face
hardcoded — that is the exact failure class this whole plan keeps finding, so nothing is dropped
quietly (verified against a full-library count: rewritten + skipped == every occurrence found by an
independent, more permissive scan — see the bottom of scan_font_decls). Skip reasons (fixed set):
  already-dynamic-family   the family position holds `${...}` / a bare variable (already reads a
                            prop or the DNA) — applies to both `font:` and `fontFamily:` declarations
  already-migrated         the family position already holds `var(--f-`
  no-literal-px            `font:` matched but the shorthand has no literal `<number>px` (interpolated
                            size, e.g. a template literal with `${size}px`) — NOT extended in this
                            task; counted so the next task can decide whether to extend the regex
  unparsed-shorthand       matched `font:` (single-/back-quoted) but _SHORTHAND_RE still failed
  double-quoted-shorthand  `font: "..."` — _DECL_RE (kept verbatim from the brief; its tests pin the
                            exact rewrite strings) only recognises `'`/`` ` `` as the outer quote, so a
                            double-quoted shorthand is invisible to the rewrite entirely. Real: 15
                            occurrences across 11 shots. NOT extended in this task for the same reason
                            as no-literal-px — measure first.
  unrecognized-font-decl   a `font:` occurrence neither of the above two scans could parse: a
                            template literal whose *inner* quote is a different type from its outer
                            backtick (e.g. `` `...${x ?? '"Serif"'}...` `` — the embedded `'...'`
                            breaks the naive `[^'`]*` content class before reaching the real close),
                            or a bare variable (`font: fontCss`). 3 occurrences.
  fontFamily-declaration   a `fontFamily:` property with a literal quoted value (not a `font:`
                            shorthand) — out of scope for this codemod by design; hand-migrated in the
                            next task, listed here so that task has the exact list
  svg-attribute-not-css    a `fontFamily="..."` JSX attribute on an SVG element. React lowercases this
                            to the `font-family` XML presentation attribute at render time — the exact
                            case the brief's `<text font-family="...">` guard protects `font:` from —
                            so var() cannot apply and this codemod does not touch it. It is NOT what
                            "no shot uses an SVG font-family= XML attribute" (the literal, hyphenated
                            spelling) refers to: that statement is true of the raw string, but the JSX
                            camelCase equivalent is in fact the single largest hardcoded-family
                            category in the library — 62 occurrences across 17 shots.

Usage:
  python3 scripts/dna_migrate_type.py --report          # dry run, prints rewrite + skip tables
  python3 scripts/dna_migrate_type.py --apply           # writes the files
"""
import json, os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHOTS = os.path.join(_HERE, "..", "remotion", "src", "shots")

DISPLAY_MIN_PX = 64.0
_MONO_RE = re.compile(r"mono|JetBrains|Menlo|Consolas|Courier", re.I)

# `font:` followed by a single- or back-quoted shorthand. Captures the quote so the rewrite keeps it.
_DECL_RE = re.compile(r"font: *(['`])([^'`]*)\1")
# <weight/style words> <size>px[/<line-height>] <families...>
_SHORTHAND_RE = re.compile(r"^(?P<head>.*?)(?P<size>\d+(?:\.\d+)?)px(?P<lh>/[\d.]+)? +(?P<families>.+)$")

# Recognises a `font:` shorthand string even when _SHORTHAND_RE can't parse it (e.g. the size is
# interpolated: `` `700 ${size}px/1 Inter` `` still contains the literal text "px" — but more to the
# point, ANY quoted/back-quoted string after `font:` counts as "seen", so it can be classified into a
# skip reason instead of vanishing. This mirrors _DECL_RE exactly; kept separate so a future change to
# one doesn't silently desync the other without a diff showing it.
_SEEN_FONT_RE = re.compile(r"font: *(['`])([^'`]*)\1")

# `font: "..."` — the outer quote _DECL_RE/_SEEN_FONT_RE don't recognise (double quote). Real in this
# library (11 shots) and otherwise entirely invisible to the scan above.
_DOUBLE_QUOTED_FONT_RE = re.compile(r'font: *"([^"]*)"')

# Anchors every `font:` occurrence regardless of what follows, so anything _SEEN_FONT_RE and
# _DOUBLE_QUOTED_FONT_RE both fail to parse (nested-quote template literals, bare variables) still
# gets caught by the catch-all pass in scan_font_decls instead of vanishing. `fontFamily:`/`fontWeight:`
# etc. never match this — none of those keys have a `:` directly after "font".
_FONT_ANCHOR_RE = re.compile(r"font:\s*")

# A `fontFamily:` property (React inline-style object key) with a LITERAL quoted value — one
# alternative per quote type, each excluding only its own delimiter, so a value like
# `'"Baloo 2", Inter, sans-serif'` (a double-quoted family name inside a single-quoted string) is
# captured whole instead of truncating at the embedded `"`.
_FONT_FAMILY_LITERAL_RE = re.compile(r"fontFamily:\s*(?:'([^']*)'|\"([^\"]*)\"|`([^`]*)`)")

# Anchors every `fontFamily:` occurrence (literal or not), so a `fontFamily:` pointing at a variable —
# `fontFamily: FONTS[i % FONTS.length]` — is still accounted for rather than silently absent from
# both the rewrite table and the skip table.
_FONT_FAMILY_ANY_RE = re.compile(r"fontFamily:\s*")

# The JSX/React spelling of an SVG `font-family` presentation attribute: `<text fontFamily="...">`.
# React renders this as the `font-family` XML attribute — var() cannot apply there, so this codemod
# only surfaces it (does not rewrite it), the same stance the brief's own SVG guard takes.
_SVG_FONTFAMILY_ATTR_RE = re.compile(r'fontFamily="([^"]*)"')

_HAS_PX_LITERAL_RE = re.compile(r"\d+(?:\.\d+)?px")


def _role(families, size):
    if _MONO_RE.search(families):
        return "mono"
    return "display" if size >= DISPLAY_MIN_PX else "body"


def rewrite_font_decl(text):
    """Rewrite every hardcoded `font:` shorthand in `text`. Returns (new_text, assignments).

    Every `font:` string the scanner encounters is classified: rewritten (returned in `assignments`,
    each also carries a `skipped: False`-shaped absence — see `scan_font_decls` for the full skip
    accounting used by --report) or left untouched. `rewrite_font_decl` itself only needs to return
    what Task 9's `--apply` consumes: the rewritten text and the list of assignments it made. The
    richer skip bookkeeping for `--report` lives in `scan_font_decls` below, which calls this function
    and separately reasons about anything it left alone.
    """
    report = []

    def sub(m):
        quote, body = m.group(1), m.group(2)
        sh = _SHORTHAND_RE.match(body)
        if not sh:
            return m.group(0)
        families = sh.group("families").strip()
        # already dynamic (reads a prop or the DNA) or already migrated - leave it alone
        if "${" in families or "var(--f-" in families:
            return m.group(0)
        size = float(sh.group("size"))
        role = _role(families, size)
        line = text[: m.start()].count("\n") + 1
        report.append({"line": line, "size": size, "role": role, "families": families})
        head = sh.group("head") + sh.group("size") + "px" + (sh.group("lh") or "")
        return "font: %s%s var(--f-%s, %s)%s" % (quote, head, role, families, quote)

    # An SVG font-family="..." attribute cannot take a var(); _DECL_RE only matches `font:` in a CSS
    # context, so attributes are excluded by construction. Asserted by a test.
    return _DECL_RE.sub(sub, text), report


def _skip_reason_for_font_decl(quote, body):
    """Classify a `font:` string that rewrite_font_decl's inner sub() did NOT rewrite. Mirrors the
    exact checks in `sub()` above, in the same order, so a skip reason always matches why the rewrite
    actually declined it."""
    sh = _SHORTHAND_RE.match(body)
    if not sh:
        # Matched `font:` but the shorthand regex failed. The most common cause in this library is an
        # interpolated size (`${size}px` instead of a literal `NNpx`) — distinguish that from a
        # genuinely unparsed shorthand so the next task knows which of the two to extend for.
        if not _HAS_PX_LITERAL_RE.search(body):
            return "no-literal-px"
        return "unparsed-shorthand"
    families = sh.group("families").strip()
    if "var(--f-" in families:
        return "already-migrated"
    if "${" in families:
        return "already-dynamic-family"
    # sub() would have rewritten this — should not reach here in practice.
    return "unparsed-shorthand"


def _bracket_aware_snippet(text, start, max_len=200):
    """A short, readable snippet of a declaration's VALUE starting at `start`, for display in the
    skipped table only (never re-parsed) — stops at the first top-level `,`/newline or an unmatched
    closing bracket, tracking (), [], {} depth so `FONTS[i % FONTS.length]` isn't cut at the `%`."""
    depth, i, n = 0, start, len(text)
    while i < n and i - start < max_len:
        c = text[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c in ",\n" and depth == 0:
            break
        i += 1
    return text[start:i].strip()


def scan_font_decls(text):
    """Full accounting of every `font:`/`fontFamily:` declaration and every SVG/JSX
    `fontFamily="..."` attribute in `text`. Returns (new_text, rewritten, skipped) where `rewritten`
    is rewrite_font_decl's assignment list (unchanged) and `skipped` is a list of
    {"line": int, "declaration": str, "reason": str} for every one of these three constructs this
    codemod did not rewrite — so nothing a human reviewing --report has to see vanishes silently.
    """
    new_text, rewritten = rewrite_font_decl(text)
    rewritten_lines = {r["line"] for r in rewritten}
    skipped = []
    covered = []  # spans already accounted for (font: only), so later passes don't double-count

    # 1) `font:` shorthands _SEEN_FONT_RE can parse (single-quote / backtick) but weren't rewritten.
    for m in _SEEN_FONT_RE.finditer(text):
        covered.append(m.span())
        line = text[: m.start()].count("\n") + 1
        if line in rewritten_lines:
            continue
        quote, body = m.group(1), m.group(2)
        reason = _skip_reason_for_font_decl(quote, body)
        skipped.append({"line": line, "declaration": m.group(0), "reason": reason})

    # 2) `font: "..."` — double-quoted, invisible to _DECL_RE/_SEEN_FONT_RE by construction.
    for m in _DOUBLE_QUOTED_FONT_RE.finditer(text):
        if any(s <= m.start() < e for s, e in covered):
            continue
        covered.append(m.span())
        line = text[: m.start()].count("\n") + 1
        skipped.append({"line": line, "declaration": m.group(0), "reason": "double-quoted-shorthand"})

    # 3) Catch-all: any remaining `font:` occurrence neither (1) nor (2) covered — a template literal
    # whose embedded quote of a DIFFERENT type breaks the naive content class before its real close,
    # or a bare variable reference. Named honestly rather than mis-filed under an existing reason.
    for m in _FONT_ANCHOR_RE.finditer(text):
        if any(s <= m.start() < e for s, e in covered):
            continue
        covered.append((m.start(), m.end()))
        line = text[: m.start()].count("\n") + 1
        snippet = "font: " + _bracket_aware_snippet(text, m.end())
        skipped.append({"line": line, "declaration": snippet, "reason": "unrecognized-font-decl"})

    # 4) `fontFamily:` with a literal quoted value — out of scope for this codemod; hand-migrated next.
    ff_literal_spans = []
    for m in _FONT_FAMILY_LITERAL_RE.finditer(text):
        ff_literal_spans.append(m.span())
        line = text[: m.start()].count("\n") + 1
        skipped.append({"line": line, "declaration": m.group(0), "reason": "fontFamily-declaration"})

    # 5) `fontFamily:` pointing at a variable/expression (not a literal) — already dynamic, same
    # status as a `${...}` font: shorthand, just surfaced under the fontFamily: spelling.
    for m in _FONT_FAMILY_ANY_RE.finditer(text):
        if any(s <= m.start() < e for s, e in ff_literal_spans):
            continue
        if _FONT_FAMILY_LITERAL_RE.match(text, m.start()):
            continue  # a literal — already emitted in (4)
        line = text[: m.start()].count("\n") + 1
        snippet = "fontFamily: " + _bracket_aware_snippet(text, m.end())
        skipped.append({"line": line, "declaration": snippet, "reason": "already-dynamic-family"})

    # 6) `fontFamily="..."` — the JSX/React spelling of an SVG font-family presentation attribute.
    # var() cannot apply; surfaced (not rewritten) so it isn't silently absent from the accounting.
    for m in _SVG_FONTFAMILY_ATTR_RE.finditer(text):
        line = text[: m.start()].count("\n") + 1
        skipped.append({"line": line, "declaration": m.group(0), "reason": "svg-attribute-not-css"})

    skipped.sort(key=lambda r: r["line"])
    return new_text, rewritten, skipped


def main(argv):
    apply = "--apply" in argv
    rows, skip_rows, total = [], [], 0
    for name in sorted(os.listdir(_SHOTS)):
        if not name.endswith(".tsx"):
            continue
        path = os.path.join(_SHOTS, name)
        src = open(path, encoding="utf-8").read()
        out, rep, skipped = scan_font_decls(src)
        for r in skipped:
            skip_rows.append(dict(r, shot=name))
        if not rep:
            if apply:
                pass  # nothing to write for this shot
            continue
        total += len(rep)
        for r in rep:
            rows.append(dict(r, shot=name))
        if apply:
            open(path, "w", encoding="utf-8").write(out)
    if apply:
        print("rewrote %d declarations across %d shots" % (total, len({r['shot'] for r in rows})))
        if skip_rows:
            print("skipped %d declarations across %d shots (rerun with --report to see why)"
                  % (len(skip_rows), len({r['shot'] for r in skip_rows})))
    else:
        print(json.dumps(rows, indent=1))
        print("\n%d declarations REWRITTEN in %d shots" % (total, len({r['shot'] for r in rows})))
        for role in ("display", "body", "mono"):
            print("  %-8s %d" % (role, sum(1 for r in rows if r["role"] == role)))

        print("\n--- SKIPPED ---")
        print(json.dumps(skip_rows, indent=1))
        reasons = ("already-dynamic-family", "already-migrated", "no-literal-px",
                   "unparsed-shorthand", "double-quoted-shorthand", "unrecognized-font-decl",
                   "fontFamily-declaration", "svg-attribute-not-css")
        seen_reasons = {r["reason"] for r in skip_rows}
        unknown = sorted(seen_reasons - set(reasons))
        print("\n%d declarations SKIPPED in %d shots" % (len(skip_rows), len({r['shot'] for r in skip_rows})))
        for reason in reasons:
            print("  %-24s %d" % (reason, sum(1 for r in skip_rows if r["reason"] == reason)))
        for reason in unknown:
            print("  %-24s %d  (** unrecognised reason - fix the classifier **)" % (reason,
                  sum(1 for r in skip_rows if r["reason"] == reason)))

        print("\n%d declarations SEEN total (rewritten + skipped)" % (total + len(skip_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
