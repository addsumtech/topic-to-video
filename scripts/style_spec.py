#!/usr/bin/env python3
"""The film's STYLE SPEC (`meta.style`) — a drawing style decomposed into values on fixed, general axes.

WHY THIS EXISTS. A style the skill has never seen ("水墨", "a cartoon", "like Kurzgesagt") has to reach every
beat and every object as a change in HOW THINGS ARE DRAWN — line, fill, shade, shadow, form, surface, type,
motion — not as a palette. The axes are one table, runtime/styleAxes.json, read here and by the renderer
(runtime/styleSpec.ts); a new style is new values, never new code, so no axis or value names a style.

    python3 scripts/style_spec.py <out_dir>      # validate the board's meta.style; prints errors and warnings

THE RULES this module holds:
  * an unknown axis, parameter or value is an ERROR naming it (`style.fill.mode`) — an unknown value would
    silently draw as-drawn, which is the recolour-only film the user rejected;
  * `refs` (each with `src` and `from: user|found`) is required, or `refs_missing` saying why there are none;
  * a spec that leaves every axis as drawn changes only the palette — a WARNING, said in those words, because
    that can be the right answer (a style that matches the default drawing) and the user decides at the sample;
  * `spec_sha256` is what a sign-off is pinned to; shortfalls and credits are notes, not the spec.
"""
import hashlib
import json
import os
import re
import sys

AXES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "remotion", "src", "runtime", "styleAxes.json")
AXES = {k: v for k, v in json.load(open(AXES_PATH, encoding="utf-8")).items() if not k.startswith("_")}

PROVENANCE = ("name", "refs", "refs_missing", "notes", "shortfalls")
REF_FROM = ("user", "found")
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _value_problem(p, v):
    """None when `v` is a legal value for parameter spec `p`, else what is wrong with it."""
    kind = p["kind"]
    if kind == "enum":
        if v in p["values"] or (p.get("hex") and isinstance(v, str) and _HEX.match(v)):
            return None
        return "is %r; one of %s%s" % (v, p["values"], " or a #hex" if p.get("hex") else "")
    if kind == "bool":
        return None if isinstance(v, bool) else "is %r; true or false" % (v,)
    if kind == "string":
        return None if isinstance(v, str) and v.strip() else "is %r; a non-empty string" % (v,)
    if isinstance(v, str) and v in p.get("also", ()):
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (kind == "int" and int(v) != v):
        return "is %r; a%s %s–%s%s" % (v, "n integer" if kind == "int" else " number", p["min"], p["max"],
                                       (" or %s" % p["also"]) if p.get("also") else "")
    if not p["min"] <= v <= p["max"]:
        return "is %r; outside %s–%s" % (v, p["min"], p["max"])
    gap = p.get("gap")
    if gap and gap[0] < v < gap[1]:
        return "is %r; %s, or %s–%s" % (v, gap[0], gap[1], p["max"])
    return None


def validate_spec(spec):
    """(errors, warnings) for one `meta.style` value."""
    errors, warnings = [], []
    if not isinstance(spec, dict):
        return ["meta.style is %s; an object of drawing axes" % type(spec).__name__], []
    for key, val in spec.items():
        if key in PROVENANCE:
            continue
        if key not in AXES:
            errors.append("style.%s is not an axis; the axes are %s" % (key, sorted(AXES)))
            continue
        if not isinstance(val, dict):
            errors.append("style.%s is %s; an object of its parameters" % (key, type(val).__name__))
            continue
        for name, v in val.items():
            p = AXES[key].get(name)
            if p is None:
                errors.append("style.%s.%s is not a parameter of %s; it has %s" % (key, name, key, sorted(AXES[key])))
                continue
            why = _value_problem(p, v)
            if why:
                errors.append("style.%s.%s %s" % (key, name, why))
    if not (isinstance(spec.get("name"), str) and spec["name"].strip()):
        errors.append("style.name is missing — the style the user asked for, in their words")
    refs = spec.get("refs")
    if not isinstance(refs, list):
        errors.append("style.refs is missing — the reference frames the spec was read from")
    else:
        for i, r in enumerate(refs):
            if not (isinstance(r, dict) and isinstance(r.get("src"), str) and r["src"].strip()):
                errors.append("style.refs[%d] has no src" % i)
            elif r.get("from") not in REF_FROM:
                errors.append("style.refs[%d].from is %r; one of %s" % (i, r.get("from"), list(REF_FROM)))
        if not refs and not (isinstance(spec.get("refs_missing"), str) and spec["refs_missing"].strip()):
            errors.append("style.refs is empty — add the references the spec was read from, or say why there are "
                          "none in style.refs_missing (the sample sheet then says so in its title)")
    for i, s in enumerate(spec.get("shortfalls") or []):
        if not (isinstance(s, dict) and all(isinstance(s.get(k), str) for k in ("axis", "wanted", "got", "why"))):
            errors.append("style.shortfalls[%d] needs axis, wanted, got and why" % i)
    if not errors and is_recolour_only(spec):
        warnings.append("meta.style %r leaves every drawing axis as drawn: only the palette changes. If the style "
                        "really draws like the default, say so on the sample sheet; otherwise decompose it"
                        % spec.get("name"))
    return errors, warnings


def _value(spec, group, name):
    p = AXES[group][name]
    g = spec.get(group)
    return g.get(name, p["default"]) if isinstance(g, dict) else p["default"]


def structural_axes(spec):
    """Dotted names of the parameters set away from their default — the ones that change the drawing. A
    parameter whose `only_with` sibling is not set to a value it means anything under does not count."""
    out = []
    for group, params in AXES.items():
        g = spec.get(group) if isinstance(spec, dict) else None
        if not isinstance(g, dict):
            continue
        for name, p in params.items():
            if name not in g or g[name] == p["default"]:
                continue
            gate = p.get("only_with") or {}
            if any(_value(spec, group, sib) not in allowed for sib, allowed in gate.items()):
                continue
            out.append("%s.%s" % (group, name))
    return out


def is_recolour_only(spec):
    return not structural_axes(spec)


def spec_sha256(spec):
    """The hash a sign-off is pinned to: the spec with its notes taken out (shortfalls, credits)."""
    s = json.loads(json.dumps(spec))
    s.pop("shortfalls", None)
    for r in s.get("refs") or []:
        if isinstance(r, dict):
            r.pop("credit", None)
    return hashlib.sha256(json.dumps(s, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: style_spec.py <out_dir>", file=sys.stderr)
        return 1
    data = json.load(open(os.path.join(argv[0], "storyboard.json"), encoding="utf-8"))
    spec = (data.get("meta") or {}).get("style")
    if spec is None:
        print("no meta.style — the film draws as its registers do")
        return 0
    errors, warnings = validate_spec(spec)
    for e in errors:
        print("ERROR  " + e)
    for w in warnings:
        print("WARN   " + w)
    if not errors:
        print("style %r: %s" % (spec.get("name"), ", ".join(structural_axes(spec)) or "as drawn"))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
