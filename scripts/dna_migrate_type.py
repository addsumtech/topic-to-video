#!/usr/bin/env python3
"""dna_migrate_type — rewrite hardcoded font families in the shot library to DNA-aware CSS variables.

    font: '800 200px/0.9 Inter, system-ui, sans-serif'
 -> font: '800 200px/0.9 var(--f-display, Inter, system-ui, sans-serif)'

The ORIGINAL family list becomes the variable's fallback, so a film with no DNA resolves exactly what
it resolved before (verified on real renders by scripts/null_dna_pixel_gate.py, not asserted).

Role is a HEURISTIC read off the shorthand: a mono family list -> mono; else >= 64px -> display;
else body. No gate can check whether a role is RIGHT - a heading on --f-body still renders fine - so
--report is reviewed by a human before --apply. A closed table of hand-reviewed overrides
(_ROLE_OVERRIDES) corrects the handful of declarations two reviewers confirmed the heuristic gets
wrong (decorative numerals the size threshold puts in display that read as body register).

Every `font:`/`fontFamily:` declaration AND every SVG/JSX `fontFamily="..."` presentation attribute
the scanner finds is ACCOUNTED FOR: it is either rewritten, or recorded in the SKIPPED table with a
reason. Something this script cannot parse is a silent miss waiting to leave a shot's face
hardcoded — that is the exact failure class this whole plan keeps finding, so nothing is dropped
quietly (verified against a full-library count: rewritten + skipped == every occurrence found by an
independent, more permissive scan — see the bottom of scan_font_decls). Skip reasons (fixed set):
  already-dynamic-family   the family position holds `${...}` / a bare variable (already reads a
                            prop or the DNA) — applies to both `font:` and `fontFamily:` declarations
  already-migrated         the family position already holds `var(--f-` — applies to `font:`
                            shorthands AND to SVG `fontFamily="..."` attributes (idempotent re-run)
  no-literal-px            `font:` matched but the shorthand has no literal `<number>px` NOR a
                            `${...}px` interpolated size _SHORTHAND_RE can parse (e.g. the `${...}`
                            contains nested braces) — genuinely unparseable, not just interpolated;
                            an interpolated-but-parseable size (`` `700 ${size}px/1 Inter` ``) IS
                            rewritten, see below.
  unparsed-shorthand       matched `font:` (single-/back-/double-quoted) but _SHORTHAND_RE still
                            failed even though a literal `<number>px` is present
  unrecognized-font-decl   a `font:` occurrence neither of the above two scans could parse: a
                            template literal whose *inner* quote is a different type from its outer
                            backtick (e.g. `` `...${x ?? '"Serif"'}...` `` — the embedded `'...'`
                            breaks the naive `[^'`]*` content class before reaching the real close),
                            or a bare variable (`font: fontCss`). 3 occurrences.
  fontFamily-declaration   a `fontFamily:` property with a literal quoted value (not a `font:`
                            shorthand) — out of scope for this codemod by design; hand-migrated in the
                            next task, listed here so that task has the exact list

Two categories Task 8 believed were permanent limits turned out not to be, and Task 9 widened this
codemod to cover them instead of leaving them skipped:
  - Double-quoted shorthands (`font: "..."`) — ordinary CSS. `_DECL_RE`/`_SEEN_FONT_RE` previously
    only recognised `'`/`` ` `` as the outer quote; a third alternative now recognises `"` too, with
    its own content class (`[^"]*`) so it doesn't interfere with the existing single-/back-quote
    matching (which, unchanged, still tolerates an embedded `"` inside a single-quoted family list —
    see the `'500 30px/1 "JetBrains Mono"...'` case in the tests).
  - Interpolated sizes (`` `700 ${size}px/1 Inter` ``) — `_SHORTHAND_RE`'s size token now accepts
    either a literal number or a single-level `${...}` expression, tolerated up to the literal `px`
    that follows it. Role assignment can't use the >=64px threshold on a value that isn't a literal
    number, so `_resolve_size` extracts every numeric literal >= 8 (a plausible minimum font size —
    excludes small multiplier coefficients like the 0.42 in `` `${r * 0.42}px` ``, which are never
    themselves a font size) from the expression and uses the largest; a bare identifier or an
    expression with no literal >= 8 at all (`` `${FS}px` ``) has no textual size signal, and
    empirically in this library that shape is used for large, hero-scale text (a headline reveal, a
    gauge's big readout) — so it defaults to DISPLAY_MIN_PX (i.e. `display`) rather than guessing
    `body` from nothing.

A third category, the SVG/JSX `fontFamily="..."` presentation attribute, was believed to be a hard
CSS limitation (var() cannot apply to an XML attribute) and was skipped under
`svg-attribute-not-css`. A later reviewer built a probe demonstrating that a REAL browser (this
Remotion/Chromium render pipeline) resolves `var()` inside this attribute correctly, including its
fallback when unset — re-confirmed on an actual `npx remotion render` (not just `still`) for Task 9.
So this codemod now REWRITES it in place: `fontFamily="var(--f-ROLE, <original list>)"`. Role is
read off a `fontSize=` attribute the scanner finds on the SAME source line (every real occurrence in
this library has one); no literal/extractable size on that line falls back to the same
DISPLAY_MIN_PX default `_resolve_size` uses for an interpolated `font:` size, for the same reason.

Usage:
  python3 scripts/dna_migrate_type.py --report          # dry run, prints rewrite + skip tables
  python3 scripts/dna_migrate_type.py --apply           # writes the files
"""
import json, os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHOTS = os.path.join(_HERE, "..", "remotion", "src", "shots")

DISPLAY_MIN_PX = 64.0
_MONO_RE = re.compile(r"mono|JetBrains|Menlo|Consolas|Courier", re.I)

# `font:` followed by a quoted shorthand. Three independent alternatives, one per quote type, each
# excluding only ITS OWN delimiter from its content class (the pattern `_FONT_FAMILY_LITERAL_RE`
# below already uses) — NOT a shared "exclude both" class, because a single-quoted shorthand can
# legitimately contain an embedded double-quoted family name (`'500 30px/1 "JetBrains Mono", ...'`,
# pinned by a test) and that must still match all the way to its real closing `'`.
_DECL_RE = re.compile(r"font: *(?:(['`])([^'`]*)\1|\"([^\"]*)\")")

# <weight/style words> <size>px[/<line-height>] <families...>
# The size token is a literal number OR a single-level `${...}` template interpolation, tolerated up
# to the literal "px" that must still follow it. `[^{}]*` deliberately doesn't nest — every real size
# interpolation in this library is a flat expression (`${size}`, `${lerp(56, 132, grow)}`, `${r *
# 0.42}`); a genuinely nested one fails to match here and falls through to no-literal-px/
# unparsed-shorthand rather than being silently mis-parsed.
_SIZE_TOKEN = r"(?:\d+(?:\.\d+)?|\$\{[^{}]*\})"
_SHORTHAND_RE = re.compile(r"^(?P<head>.*?)(?P<size>%s)px(?P<lh>/[\d.]+)? +(?P<families>.+)$" % _SIZE_TOKEN)

# Recognises a `font:` shorthand string even when _SHORTHAND_RE can't parse it — mirrors _DECL_RE
# exactly; kept separate so a future change to one doesn't silently desync the other without a diff
# showing it. ANY quoted string after `font:` counts as "seen", so it can be classified into a skip
# reason instead of vanishing.
_SEEN_FONT_RE = re.compile(r"font: *(?:(['`])([^'`]*)\1|\"([^\"]*)\")")

# Anchors every `font:` occurrence regardless of what follows, so anything _SEEN_FONT_RE fails to
# parse (nested-quote template literals, bare variables) still gets caught by the catch-all pass in
# scan_font_decls instead of vanishing. `fontFamily:`/`fontWeight:` etc. never match this — none of
# those keys have a `:` directly after "font".
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
# JSX attribute syntax has no way to interpolate INSIDE a plain quoted string (a dynamic value would
# be written `fontFamily={expr}`, a wholly different, never-seen-in-this-library shape — see the
# module docstring), so every match here is a literal family list, rewritten in place.
_SVG_FONTFAMILY_ATTR_RE = re.compile(r'fontFamily="([^"]*)"')

# A `fontSize=` attribute (literal `"24"` or JSX-expression `{r * 0.42}`), used to find the sibling
# size hint for an SVG fontFamily="..." attribute on the SAME source line — every real occurrence in
# this library has one on the same line as its fontFamily=.
_FONTSIZE_ATTR_RE = re.compile(r'fontSize=(?:"([^"]*)"|\{([^}]*)\})')

_HAS_PX_LITERAL_RE = re.compile(r"\d+(?:\.\d+)?px")

# Numeric literals inside an interpolated size expression, used by _resolve_size. >= 8 filters out
# small multiplier coefficients (`r * 0.42`, `gap * 0.8`) that are never themselves a plausible font
# size in this codebase (the smallest real literal font size anywhere in the library is well above
# this).
_NUMERIC_LITERAL_RE = re.compile(r"\d+(?:\.\d+)?")
_MIN_PLAUSIBLE_PX = 8.0

# Two reviewers manually corrected these four `font:` role assignments after reading what the text
# actually is: the size->role heuristic is blind to REGISTER, and a decorative numeral rendered large
# (an odometer digit, an accelerating race counter, a before/after slider's headline metric) still
# reads as body-register type, not a headline. `SplitFlap.tsx:44` was reviewed too and left exactly
# as the codemod assigns it (`display`, 108px "Anton") — reviewers judged it genuinely ambiguous, so
# it carries no override.
_ROLE_OVERRIDES = {
    ("OdometerRoll.tsx", 33): "body",
    ("OdometerRoll.tsx", 56): "body",
    ("OdometerRoll.tsx", 65): "body",
    ("TemporalAccelerate.tsx", 57): "body",
    ("BeforeAfterSlider.tsx", 30): "body",
}


def _resolve_size(size_token):
    """Return a numeric px value to classify a shorthand's role by. A literal size (`"36"`) parses
    directly. An interpolated size (`${lerp(56, 132, grow)}`, `${r * 0.42}`, `${FS}`) has no single
    value — see the module docstring for the extract-largest-plausible-literal / default-to-display
    reasoning."""
    try:
        return float(size_token)
    except ValueError:
        candidates = [n for n in (float(s) for s in _NUMERIC_LITERAL_RE.findall(size_token))
                      if n >= _MIN_PLAUSIBLE_PX]
        return max(candidates) if candidates else DISPLAY_MIN_PX


def _size_from_line(line_text):
    """The size hint for an SVG fontFamily="..." attribute: the fontSize= attribute on the same
    line, resolved the same way as an interpolated `font:` size. No fontSize= on the line at all
    (never seen in this library today, but the regex doesn't assume it) gets the same
    no-textual-signal default as a bare `${FS}` — see _resolve_size."""
    m = _FONTSIZE_ATTR_RE.search(line_text)
    if not m:
        return DISPLAY_MIN_PX
    token = m.group(1) if m.group(1) is not None else m.group(2)
    return _resolve_size(token)


def _role(families, size):
    if _MONO_RE.search(families):
        return "mono"
    return "display" if size >= DISPLAY_MIN_PX else "body"


def _line_text(text, start, end):
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def rewrite_font_decl(text, filename=None):
    """Rewrite every hardcoded `font:` shorthand AND every SVG `fontFamily="..."` attribute in
    `text`. Returns (new_text, assignments).

    `filename` (the shot's basename, e.g. `"OdometerRoll.tsx"`) is optional and defaults to None so
    direct calls with a synthetic string (as the unit tests do) never accidentally match
    `_ROLE_OVERRIDES` — overrides only apply when a real file is being rewritten.

    Every `font:`/`fontFamily="..."` occurrence the scanner encounters is classified: rewritten
    (returned in `assignments`) or left untouched. `rewrite_font_decl` itself only needs to return
    what Task 9's `--apply` consumes: the rewritten text and the list of assignments it made. The
    richer skip bookkeeping for `--report` lives in `scan_font_decls` below, which calls this
    function and separately reasons about anything it left alone.
    """
    report = []

    def sub(m):
        if m.group(1) is not None:
            quote, body = m.group(1), m.group(2)
        else:
            quote, body = '"', m.group(3)
        sh = _SHORTHAND_RE.match(body)
        if not sh:
            return m.group(0)
        families = sh.group("families").strip()
        # already dynamic (reads a prop or the DNA) or already migrated - leave it alone
        if "${" in families or "var(--f-" in families:
            return m.group(0)
        size = _resolve_size(sh.group("size"))
        role = _role(families, size)
        line = text[: m.start()].count("\n") + 1
        if filename is not None and (filename, line) in _ROLE_OVERRIDES:
            role = _ROLE_OVERRIDES[(filename, line)]
        report.append({"line": line, "size": size, "role": role, "families": families, "kind": "font"})
        head = sh.group("head") + sh.group("size") + "px" + (sh.group("lh") or "")
        return "font: %s%s var(--f-%s, %s)%s" % (quote, head, role, families, quote)

    out1 = _DECL_RE.sub(sub, text)

    def sub_svg(m):
        family = m.group(1)
        if "var(--f-" in family:
            return m.group(0)  # already migrated (idempotent re-run) - leave it alone
        line_text = _line_text(out1, m.start(), m.end())
        size = _size_from_line(line_text)
        role = _role(family, size)
        line = out1[: m.start()].count("\n") + 1  # stable vs. `text`'s line numbers: font: rewrites
        # above never add/remove a newline, so a source line number computed against the once-
        # rewritten `out1` is identical to the number computed against the original `text`.
        if filename is not None and (filename, line) in _ROLE_OVERRIDES:
            role = _ROLE_OVERRIDES[(filename, line)]
        report.append({"line": line, "size": size, "role": role, "families": family, "kind": "svg-attr"})
        return 'fontFamily="var(--f-%s, %s)"' % (role, family)

    out2 = _SVG_FONTFAMILY_ATTR_RE.sub(sub_svg, out1)
    return out2, report


def _skip_reason_for_font_decl(quote, body):
    """Classify a `font:` string that rewrite_font_decl's inner sub() did NOT rewrite. Mirrors the
    exact checks in `sub()` above, in the same order, so a skip reason always matches why the rewrite
    actually declined it."""
    sh = _SHORTHAND_RE.match(body)
    if not sh:
        # Matched `font:` but the shorthand regex failed even with the widened (literal-or-${...})
        # size token — a genuinely unparseable size (e.g. nested braces), not just an interpolated
        # one, so this is stricter than the old "any interpolation" check.
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


def scan_font_decls(text, filename=None):
    """Full accounting of every `font:`/`fontFamily:` declaration and every SVG/JSX
    `fontFamily="..."` attribute in `text`. Returns (new_text, rewritten, skipped) where `rewritten`
    is rewrite_font_decl's assignment list (unchanged) and `skipped` is a list of
    {"line": int, "declaration": str, "reason": str} for every one of these three constructs this
    codemod did not rewrite — so nothing a human reviewing --report has to see vanishes silently.
    """
    new_text, rewritten = rewrite_font_decl(text, filename)
    rewritten_font_lines = {r["line"] for r in rewritten if r["kind"] == "font"}
    rewritten_svg_lines = {r["line"] for r in rewritten if r["kind"] == "svg-attr"}
    skipped = []
    covered = []  # spans already accounted for (font: only), so later passes don't double-count

    # 1) `font:` shorthands _SEEN_FONT_RE can parse (single/double/back-quoted) but weren't
    # rewritten.
    for m in _SEEN_FONT_RE.finditer(text):
        covered.append(m.span())
        line = text[: m.start()].count("\n") + 1
        if line in rewritten_font_lines:
            continue
        if m.group(1) is not None:
            quote, body = m.group(1), m.group(2)
        else:
            quote, body = '"', m.group(3)
        reason = _skip_reason_for_font_decl(quote, body)
        skipped.append({"line": line, "declaration": m.group(0), "reason": reason})

    # 2) Catch-all: any remaining `font:` occurrence (1) didn't cover — a template literal whose
    # embedded quote of a DIFFERENT type breaks the naive content class before its real close, or a
    # bare variable reference. Named honestly rather than mis-filed under an existing reason.
    for m in _FONT_ANCHOR_RE.finditer(text):
        if any(s <= m.start() < e for s, e in covered):
            continue
        covered.append((m.start(), m.end()))
        line = text[: m.start()].count("\n") + 1
        snippet = "font: " + _bracket_aware_snippet(text, m.end())
        skipped.append({"line": line, "declaration": snippet, "reason": "unrecognized-font-decl"})

    # 3) `fontFamily:` with a literal quoted value — out of scope for this codemod; hand-migrated next.
    ff_literal_spans = []
    for m in _FONT_FAMILY_LITERAL_RE.finditer(text):
        ff_literal_spans.append(m.span())
        line = text[: m.start()].count("\n") + 1
        skipped.append({"line": line, "declaration": m.group(0), "reason": "fontFamily-declaration"})

    # 4) `fontFamily:` pointing at a variable/expression (not a literal) — already dynamic, same
    # status as a `${...}` font: shorthand, just surfaced under the fontFamily: spelling.
    for m in _FONT_FAMILY_ANY_RE.finditer(text):
        if any(s <= m.start() < e for s, e in ff_literal_spans):
            continue
        if _FONT_FAMILY_LITERAL_RE.match(text, m.start()):
            continue  # a literal — already emitted in (3)
        line = text[: m.start()].count("\n") + 1
        snippet = "fontFamily: " + _bracket_aware_snippet(text, m.end())
        skipped.append({"line": line, "declaration": snippet, "reason": "already-dynamic-family"})

    # 5) `fontFamily="..."` — the JSX/React spelling of an SVG font-family presentation attribute.
    # Rewritten via var() by rewrite_font_decl's sub_svg (Task 9 re-confirmed on a real `remotion
    # render` that var() resolves correctly there, reversing Task 8's assumption). Anything on this
    # line that rewrite_font_decl did NOT rewrite is a var(--f- already present (idempotent re-run) —
    # the same "already-migrated" status a font: shorthand gets in that situation.
    for m in _SVG_FONTFAMILY_ATTR_RE.finditer(text):
        line = text[: m.start()].count("\n") + 1
        if line in rewritten_svg_lines:
            continue
        skipped.append({"line": line, "declaration": m.group(0), "reason": "already-migrated"})

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
        out, rep, skipped = scan_font_decls(src, name)
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
                   "unparsed-shorthand", "unrecognized-font-decl", "fontFamily-declaration")
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
