#!/usr/bin/env python3
"""dna_migrate — CONSERVATIVE shadow-trick codemod that makes a library shot Design-DNA-aware, for the shots that
fit the clean pattern (named MODULE-scope colour consts + a single top-level component). It NEVER runs blind: you
pass an explicit allowlist of shot ids, and it SKIPS (with a reason) anything it can't transform safely, so a shot
it can't handle is left byte-identical for hand migration rather than broken. After running it you MUST render each
migrated shot under a themed DNA and LOOK — a green codemod is not a correct look (the two documented traps —
module-scope sibling subcomponents closing over a renamed const, and TDZ — are why this stays conservative).

The transform (the "shadow trick" from §C2):
  const ACC = '#37E0A0';                      // module scope, BEFORE the component
    →  const ACC_D0 = '#37E0A0';              // renamed = the fallback
       ... inside the component, right after `=> {`:
       const dna = useDNA();
       const ACC = dna?.accent ?? ACC_D0;     // component-scoped shadow → every JSX `ACC` inherits, zero further edits

Null DNA ⇒ `ACC === ACC_D0` ⇒ byte-identical original look (backward-compatible by construction).

Usage:  python scripts/dna_migrate.py AnswerStream ChartLive BrutalistType ...     # migrate these ids
        python scripts/dna_migrate.py --dry AnswerStream                          # show the plan, write nothing
"""
import os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHOTS = os.path.join(os.path.dirname(_HERE), "remotion", "src", "shots")
_SHOTLUMA = os.path.join(os.path.dirname(_HERE), "remotion", "src", "runtime", "shotLuma.ts")


def _ground_lum(shot):
    """The shot's ground luminance ('dark'/'mid'/'light') from shotLuma.ts, else None. The mechanical shadow trick
    is only SAFE on a DARK-ground shot: on a light/mid-ground shot, remapping ink/accent onto a dark DNA while the
    (usually inline) light ground stays put INVERTS text-on-ground contrast — the shot renders with invisible text.
    Those are level-C hand rebuilds, not codemod targets."""
    try:
        txt = open(_SHOTLUMA, encoding="utf-8").read()
        m = re.search(rf"(?<![A-Za-z0-9_]){re.escape(shot)}:\s*'(dark|mid|light)'", txt)
        return m.group(1) if m else None
    except OSError:
        return None

# name → DNA token. Exact, conservative: only names we're confident about. Anything else on the const line is left
# hardcoded (a partial migration still unifies bg/accent, which is what the coherence + the lint care about).
_EXACT = {
    "BG": "bg", "BACKGROUND": "bg", "GROUND": "bg", "PAPER": "bg", "CANVAS": "bg", "DARK": "bg",
    "INK": "fg", "FG": "fg", "TEXT": "fg", "WHITE": "fg",
    "PANEL": "surface", "CARD": "surface", "SURFACE": "surface", "TILE": "surface", "BOX": "surface",
    "DIM": "dim", "MUTE": "dim", "MUTED": "dim", "SUB": "dim",
    "LINE": "line", "BORDER": "line", "RULE": "line", "STROKE": "line", "GRID": "line",
    "ACC2": "accent2", "ACCENT2": "accent2", "SECOND": "accent2", "SECONDARY": "accent2",
}
# accent-class names — assigned accent to the FIRST seen, accent2 to the next, rest left hardcoded.
_ACCENTISH = {"ACC", "ACCENT", "ACC1", "HL", "HILITE", "PRIMARY", "TEAL", "MAG", "MAGENTA", "CYAN", "GREEN",
              "LIME", "GOLD", "NEON", "PINK", "BLUE", "AMBER", "ORANGE", "RED", "PURPLE", "VIOLET", "YELLOW"}

_COLOR_CONST = re.compile(r"^const\s+([A-Z][A-Z0-9_]*)\s*=\s*(['\"]#[0-9a-fA-F]{3,8}['\"])")


def _plan(src, shot):
    """Return (new_src, note) or (None, skip_reason)."""
    if re.search(r"\buseDNA\s*\(", src):
        return None, "already DNA-aware"
    lum = _ground_lum(shot)
    if lum != "dark":
        return None, (f"ground is {lum or 'unknown'} (not dark) — a mechanical recolour would invert contrast on a "
                      f"dark DNA (light text on light ground); hand-migrate (level C: flip the ground too)")
    lines = src.split("\n")
    # locate the exported component line + its `=> {` opener
    exp_i = next((i for i, l in enumerate(lines) if re.match(rf"^export const {re.escape(shot)}\b", l)), None)
    if exp_i is None:
        return None, "no `export const %s` found" % shot
    open_i = next((i for i in range(exp_i, min(exp_i + 8, len(lines))) if lines[i].rstrip().endswith("=> {")), None)
    if open_i is None:
        return None, "couldn't find the component's `=> {` opener within 8 lines"
    # collect MODULE-scope colour consts (declared BEFORE the export line) with a mapped name
    mapping = []            # (name, token, decl_line)
    seen_accent = 0
    for i in range(0, exp_i):
        for name, _val in _re_pairs(lines[i]):
            tok = _EXACT.get(name)
            if tok is None and name in _ACCENTISH:
                tok = "accent" if seen_accent == 0 else ("accent2" if seen_accent == 1 else None)
                if tok:
                    seen_accent += 1
            if tok:
                mapping.append((name, tok, i))
    if not mapping:
        return None, "no mapped module-scope colour consts (inline-only or unrecognised names) — hand-migrate"
    # SAFETY: the shadow lives INSIDE the main component's BODY (after `=> {`), so a mapped const must be used ONLY
    # there. If any mapped name is referenced ANYWHERE up to and including the opener — a module-scope sibling
    # subcomponent, a module const, OR a PARAM DEFAULT like `accent: TONE = ACC` (evaluated in the param scope,
    # before the body) — the shadow would leave that reference pointing at the renamed NAME_D0 → ReferenceError
    # (the `INK/ACC is not defined` trap). Detect it robustly (catches un-annotated arrow subcomponents + param
    # defaults) and SKIP for hand migration.
    for name, _tok, li in mapping:
        for i in range(0, open_i + 1):
            if i != li and re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", lines[i]):
                where = "a param default" if i >= exp_i else "module scope"
                return None, (f"{name} is used in {where} (line {i+1}) — a shadow would break that reference; "
                              f"hand-migrate (sub-component reads useDNA itself, or the prop default falls back to dna)")
    # rename each mapped name's DECLARATION to NAME_D0 (only on its own line, only at the decl position)
    for name, _tok, li in mapping:
        lines[li] = re.sub(rf"(?<![A-Za-z0-9_])({re.escape(name)})(\s*=)", r"\1_D0\2", lines[li], count=1)
    # build the injection
    shadows = ", ".join(f"{name} = dna?.{tok} ?? {name}_D0" for name, tok, _li in mapping)
    inject = ["  const dna = useDNA();", f"  const {shadows};"]
    lines[open_i:open_i + 1] = [lines[open_i]] + inject
    out = "\n".join(lines)
    # ensure the import
    if "runtime/dna" in out:
        out = re.sub(r"import\s*\{([^}]*)\}\s*from\s*'(\.\./runtime/dna|\./runtime/dna)'",
                     lambda m: m.group(0) if "useDNA" in m.group(1) else f"import {{{m.group(1).strip()}, useDNA}} from '{m.group(2)}'",
                     out, count=1)
    else:
        # NOT every shot imports from runtime/motion (a three.js shot, for instance). Anchor on the LAST import line
        # instead; if even that is impossible, REFUSE the transform. Writing a file that calls useDNA() without
        # importing it is a hard ReferenceError at render time, and dna_audit's `useDNA(` grep would still score it
        # as migrated — a green tick on a broken shot. Fail loud instead. (MaterialHero was exactly this bug.)
        if re.search(r"import .*from '\.\./runtime/motion';", out):
            out = re.sub(r"(import .*from '\.\./runtime/motion';)",
                         r"\1\nimport {useDNA} from '../runtime/dna';", out, count=1)
        else:
            _lines = out.split("\n")
            _imports = [i for i, l in enumerate(_lines) if l.startswith("import ")]
            if not _imports:
                return None, "no import statement to anchor the useDNA import on — hand-migrate"
            _lines.insert(_imports[-1] + 1, "import {useDNA} from '../runtime/dna';")
            out = "\n".join(_lines)
    if not re.search(r"import\s*\{[^}]*\buseDNA\b[^}]*\}\s*from\s*'\.{1,2}/runtime/dna'", out):
        return None, "INTERNAL GUARD: transform would call useDNA() without importing it — refused"
    note = ", ".join(f"{n}->{t}" for n, t, _ in mapping)
    return out, note


def _re_pairs(line):
    """Every `NAME = '#hex'` on a single top-level const line (handles multi-name `const A=.., B=..;`)."""
    if not line.lstrip().startswith("const "):
        return []
    return [(m.group(1), m.group(2)) for m in re.finditer(r"([A-Z][A-Z0-9_]*)\s*=\s*(['\"]#[0-9a-fA-F]{3,8}['\"])", line)]


def main(argv):
    dry = "--dry" in argv
    ids = [a for a in argv if not a.startswith("-")]
    if not ids:
        print("usage: dna_migrate.py [--dry] <ShotId> [ShotId...]"); return 2
    ok = skip = 0
    for shot in ids:
        p = os.path.join(_SHOTS, shot + ".tsx")
        if not os.path.isfile(p):
            print(f"  SKIP {shot}: no such shot file"); skip += 1; continue
        src = open(p, encoding="utf-8").read()
        new, note = _plan(src, shot)
        if new is None:
            print(f"  SKIP {shot}: {note}"); skip += 1; continue
        if dry:
            print(f"  PLAN {shot}: {note}")
        else:
            open(p, "w", encoding="utf-8").write(new)
            print(f"  OK   {shot}: {note}")
        ok += 1
    print(f"\n{ok} migrated{' (dry-run)' if dry else ''}, {skip} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
