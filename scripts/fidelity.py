#!/usr/bin/env python3
"""OBJECT FIDELITY — is a built thing TRUE to the thing it depicts, and finely made?
(references/object-authoring.md rule 7; the critic's S16.)

    python3 scripts/workshop.py <out_dir> fidelity <Name> [--props p.json] [--host ObjectStage]

WHY. The object rules asked that a built thing ENCODE its beat, size to its box and invent no words. Nothing asked
that it be the THING: a film shipped a hand-drawn watch with no crown and a band floating off its case, and every
gate was green. A real thing has references, proportions, defining parts and materials, and all four can be
declared before anything is drawn and looked at after.

THE RECORD. An object declares `META.fidelity`; a workshop SHOT that draws a real thing inline declares the same
record on its `meta.build_list` entry (`fidelity`); a LIBRARY register that does declares it as
`export const FIDELITY = {…}` (register_fidelity()):

    {subject, depicts: 'real' | 'abstract',
     references: [{kind: photo|spec|drawing|asset, source: url-or-path, note}],
     proportions: {name: {value, source}}, parts: [names], materials: [names], exploded?: bool,
     mounted_on?: {part: part | [parts] | None}} # what each part is FIXED to — checked to touch it; None: held
                                                 # by something not drawn (a pivot, the frame)

`depicts: 'abstract'` (a chart, a metaphor shape) needs no references. A device's sourced spec table
(runtime/deviceSpec.json) is the device-shaped instance of the same record.

THE CHECKS (problems(), run by workshop.py check and validate.py) — ERROR unless said:
  * a `real` thing with no reference; with no reference IMAGE the sheet can show (a local photo, drawing or asset)
  * a reference of an unknown kind, with no source, or a local file that does not exist
  * a local PHOTO without its imagefetch sidecar (`<path>.json`, licence + source) — a product's own picture is
    kind `asset`
  * a proportion with no value or no source, or citing a source that is not among the references
  * empty `parts` on a real thing; a part name that cannot be a `data-part` token
  * WARN: no spec/drawing reference; no materials; a declared part the source never marks `data-part="…"`;
    a real thing of two or more parts that leaves a part out of `mounted_on` (neither mounted, held by something
    not drawn, nor a mount) — that part's attachment is checked against nothing

THE SHEET (sheet()). The object is rendered twice — alone at hero size (Root's `FidelityHero`) and on the host
the film shows it on, at the film's size — with `fidelityParts` armed: runtime/fidelity.tsx logs the box of every
`data-part` node after layout. The sheet puts the reference images beside the hero render (each part outlined and
named), the film-size frame, and a 100% crop of every declared part, at `<out_dir>/_fidelity/<Name>.png` with its
findings in `<Name>.json`. Two findings are measured from the DOM, both ERROR:
  * MISSING — a declared part no node draws (absent, zero-sized or invisible): the object claims a part it lacks
  * DETACHED — a part that touches no other part (SVG shapes by their drawn outlines, other nodes by their boxes),
    within the smaller of 2% of the drawing's diagonal and 10% of the part's own short side, unless `exploded`
  * NOT ON ITS MOUNT — a part `mounted_on` names that does not touch the part it is fixed to (a mechanism's parts
    touch each other everywhere, so touching SOMETHING is no evidence a part is attached; only the record says what)
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(_HERE)
FIDELITY_TAG = "FIDELITY-PARTS "          # runtime/fidelity.tsx FIDELITY_TAG — tests hold them equal
KINDS = ("photo", "spec", "drawing", "asset")
IMAGE_KINDS = ("photo", "drawing", "asset")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
PART_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
SHEET_DIR = "_fidelity"
DETACH_TOL = 0.02           # a part must come within 2% of the drawing's diagonal of another part...
DETACH_OWN = 0.10           # ...and within 10% of the smaller part's own short side (dom_problems)
DETACH_MIN_PX = 1.5         # ...but never less than this: an anti-aliased seam between two shapes drawn edge to edge


class FidelityParseError(ValueError):
    pass


# ── READING THE RECORD OUT OF A .tsx ─────────────────────────────────────────────────────────────────────────
# The record lives in TypeScript, so it is read with a scanner that knows strings and comments: the comment
# stripper the other declaration readers share deletes `//` to end of line, which cuts every URL in a source.

def _skip_string(src, i):
    """Index just past the string literal starting at src[i] (', " or `)."""
    q, n = src[i], len(src)
    i += 1
    while i < n:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if c == q:
            return i + 1
        i += 1
    raise FidelityParseError("an unterminated string")


def _skip_comment(src, i):
    """Index past the comment at src[i], or i when there is none."""
    if src.startswith("//", i):
        j = src.find("\n", i)
        return len(src) if j < 0 else j
    if src.startswith("/*", i):
        j = src.find("*/", i + 2)
        if j < 0:
            raise FidelityParseError("an unterminated /* comment")
        return j + 2
    return i


def strip_comments(src):
    """`src` with its comments removed and its strings intact."""
    out, i, n = [], 0, len(src)
    while i < n:
        j = _skip_comment(src, i)
        if j != i:
            out.append(" ")
            i = j
            continue
        if src[i] in "'\"`":
            j = _skip_string(src, i)
            out.append(src[i:j])
            i = j
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


_META_DECL = re.compile(r"export\s+const\s+META\b")
_FIDELITY_DECL = re.compile(r"export\s+const\s+FIDELITY\b")


def meta_span(src, decl=_META_DECL):
    """(start, end) of META's object literal `{…}` in `src` (comment- and string-aware), or None. `decl` names
    another exported literal instead (a library register's FIDELITY)."""
    src = src or ""
    i, n = 0, len(src)
    while i < n:
        j = _skip_comment(src, i)
        if j != i:
            i = j
            continue
        if src[i] in "'\"`":
            i = _skip_string(src, i)
            continue
        m = decl.match(src, i)
        if m and (i == 0 or not (src[i - 1].isalnum() or src[i - 1] in "_$")):
            k = src.find("=", m.end())
            if k < 0:
                return None
            k += 1
            while k < n and src[k].isspace():
                k += 1
            if k >= n or src[k] != "{":
                return None
            return k, _match(src, k)
        i += 1
    return None


def _match(src, i):
    """Index just past the bracket that closes the one at src[i]."""
    pairs = {"{": "}", "[": "]", "(": ")"}
    stack, n = [], len(src)
    while i < n:
        j = _skip_comment(src, i)
        if j != i:
            i = j
            continue
        c = src[i]
        if c in "'\"`":
            i = _skip_string(src, i)
            continue
        if c in pairs:
            stack.append(pairs[c])
        elif c in ")]}":
            if not stack or stack.pop() != c:
                raise FidelityParseError("unbalanced %r" % c)
            if not stack:
                return i + 1
        i += 1
    raise FidelityParseError("an unclosed bracket")


def _top_level_value(body, key):
    """(start, end) of the value of `key` at the top level of an object literal's text `{…}`, or None."""
    i, n, depth = 1, len(body) - 1, 0
    expect_key = True
    while i < n:
        j = _skip_comment(body, i)
        if j != i:
            i = j
            continue
        c = body[i]
        if c in "'\"`":
            if depth == 0 and expect_key:
                e = _skip_string(body, i)
                if body[i + 1:e - 1] == key:
                    k = e
                    while k < n and body[k].isspace():
                        k += 1
                    if k < n and body[k] == ":":
                        return _value_span(body, k + 1, n)
                i = e
                expect_key = False
                continue
            i = _skip_string(body, i)
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == "," and depth == 0:
            expect_key = True
        elif depth == 0 and expect_key and (c.isalpha() or c in "_$"):
            m = re.match(r"[A-Za-z_$][\w$]*", body[i:])
            word = m.group(0)
            k = i + len(word)
            while k < n and body[k].isspace():
                k += 1
            if word == key and k < n and body[k] == ":":
                return _value_span(body, k + 1, n)
            expect_key = False
            i += len(word)
            continue
        i += 1
    return None


def _value_span(body, i, n):
    while i < n and body[i].isspace():
        i += 1
    start, depth = i, 0
    while i < n:
        j = _skip_comment(body, i)
        if j != i:
            i = j
            continue
        c = body[i]
        if c in "'\"`":
            i = _skip_string(body, i)
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    end = i
    while end > start and body[end - 1].isspace():
        end -= 1
    return start, end


class _Lit:
    """A strict reader for a JS object/array literal of plain values — strings, numbers, booleans, null — with
    unquoted keys and trailing commas. Anything computed (an identifier, a call, a template with `${}`) is refused:
    the record is data a Python gate reads, so it must be written as data."""

    def __init__(self, text):
        self.s, self.i = strip_comments(text), 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def fail(self, what):
        near = self.s[max(0, self.i - 20):self.i + 20].replace("\n", " ")
        raise FidelityParseError("%s near %r" % (what, near))

    def value(self):
        self.ws()
        if self.i >= len(self.s):
            self.fail("a value is missing")
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "'\"`":
            return self.string()
        m = re.match(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            v = float(m.group(0))
            return int(v) if v.is_integer() and re.fullmatch(r"-?\d+", m.group(0)) else v
        for word, v in (("true", True), ("false", False), ("null", None)):
            if self.s.startswith(word, self.i) and not re.match(r"[\w$]", self.s[self.i + len(word):self.i + len(word) + 1]):
                self.i += len(word)
                return v
        self.fail("not a plain value (write the record as literal data, not an expression)")

    def string(self):
        q = self.s[self.i]
        j = _skip_string(self.s, self.i)
        raw = self.s[self.i + 1:j - 1]
        if q == "`" and "${" in raw:
            self.fail("a template with ${…} is computed, not data")
        self.i = j
        return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), raw)

    def key(self):
        self.ws()
        c = self.s[self.i:self.i + 1]
        if c in ("'", '"'):
            return self.string()
        m = re.match(r"[A-Za-z_$][\w$]*", self.s[self.i:])
        if not m:
            self.fail("a key is missing")
        self.i += len(m.group(0))
        return m.group(0)

    def obj(self):
        self.i += 1
        out = {}
        while True:
            self.ws()
            if self.s[self.i:self.i + 1] == "}":
                self.i += 1
                return out
            k = self.key()
            self.ws()
            if self.s[self.i:self.i + 1] != ":":
                self.fail("':' expected after %r" % k)
            self.i += 1
            out[k] = self.value()
            self.ws()
            c = self.s[self.i:self.i + 1]
            if c == ",":
                self.i += 1
            elif c != "}":
                self.fail("',' or '}' expected")

    def arr(self):
        self.i += 1
        out = []
        while True:
            self.ws()
            if self.s[self.i:self.i + 1] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.ws()
            c = self.s[self.i:self.i + 1]
            if c == ",":
                self.i += 1
            elif c != "]":
                self.fail("',' or ']' expected")


def parse_literal(text):
    p = _Lit(text)
    v = p.value()
    p.ws()
    if p.i != len(p.s):
        p.fail("unexpected text after the value")
    return v


def meta_body(src):
    """META's literal as written (comments and all), or None."""
    span = meta_span(src)
    return None if span is None else (src or "")[span[0]:span[1]]


def meta_body_without_fidelity(src):
    """META's literal, comments removed and the `fidelity` value blanked — what the older one-line readers
    (aspect, turns, demo, provenance) search, so a proportion named `aspect` can never be read as META.aspect."""
    body = meta_body(src)
    if body is None:
        return None
    v = _top_level_value(body, "fidelity")
    if v:
        body = body[:v[0]] + "null" + body[v[1]:]
    return strip_comments(body)


def object_fidelity(src):
    """(record, None) — the object's META.fidelity — or (None, None) when it declares none, or (None, why) when it
    declares one this cannot read."""
    try:
        body = meta_body(src)
        if body is None:
            return None, None
        v = _top_level_value(body, "fidelity")
        if not v:
            return None, None
        return parse_literal(body[v[0]:v[1]]), None
    except FidelityParseError as e:
        return None, "META.fidelity cannot be read as data: %s" % e


def register_fidelity(src):
    """(record, None) — a LIBRARY register's `export const FIDELITY = {…}` — or (None, None) when it declares none,
    or (None, why) when it declares one this cannot read.

    A library register that draws a real thing inline (a gear train, a double helix, a satellite over the Earth) has
    no `meta.build_list` entry to carry the record a workshop shot would, and no META (that is an object's), so it
    exports the same record as FIDELITY beside its DURATION. The rules (problems()) and the sheet are the same;
    reference paths are relative to the skill root, like a library object's."""
    try:
        span = meta_span(src, _FIDELITY_DECL)
        if span is None:
            return None, None
        return parse_literal((src or "")[span[0]:span[1]]), None
    except FidelityParseError as e:
        return None, "FIDELITY cannot be read as data: %s" % e


def source_part_names(src):
    """({data-part names written as literals}, dynamic) — the names a source marks, and whether any mark is computed
    beyond them. `data-part="x"`, `data-part={'x'}` and `data-part={a ? 'x' : 'y'}` name their literals; a mark
    with no literal, or a template with ${…}, is dynamic: only the rendered DOM can say what it names."""
    code = strip_comments(src or "")
    names, dynamic = set(), False
    for m in re.finditer(r"data-part\s*=\s*", code):
        i = m.end()
        if i < len(code) and code[i] in "'\"":
            j = _skip_string(code, i)
            names.add(code[i + 1:j - 1].strip())
        elif i < len(code) and code[i] == "{":
            expr = code[i:_match(code, i)]
            lits = re.findall(r"""(['"`])((?:(?!\1).)*)\1""", expr)
            if not lits or any(q == "`" and "${" in v for q, v in lits):
                dynamic = True
            names |= {v.strip() for q, v in lits if not (q == "`" and "${" in v)}
        else:
            dynamic = True
    # the same mark as a createElement prop — a .ts helper has no JSX: {'data-part': 'x'} / {"data-part": a ? 'x' : 'y'}
    for m in re.finditer(r"""(['"])data-part\1\s*:\s*""", code):
        i = m.end()
        if i < len(code) and code[i] in "'\"":
            j = _skip_string(code, i)
            names.add(code[i + 1:j - 1].strip())
            continue
        k, depth = i, 0
        while k < len(code) and not (depth == 0 and code[k] in ",}"):
            depth += code[k] in "([{"
            depth -= code[k] in ")]}" and depth > 0
            k += 1
        lits = re.findall(r"""(['"`])((?:(?!\1).)*)\1""", code[i:k])
        if not lits or any(q == "`" and "${" in v for q, v in lits):
            dynamic = True
        names |= {v.strip() for q, v in lits if not (q == "`" and "${" in v)}
    return names, dynamic


# ── THE RECORD'S RULES ───────────────────────────────────────────────────────────────────────────────────────

def _is_url(s):
    return bool(re.match(r"^https?://", str(s or "").strip()))


def resolve(source, base):
    s = str(source or "").strip()
    return s if os.path.isabs(s) else os.path.normpath(os.path.join(base, s))


def problems(rec, base, where, part_names=None):
    """[(level, sentence)] for one record. `base` resolves relative reference paths (a film's out_dir, or the skill
    root for a library object); `part_names` = source_part_names(src) of the object, when there is a source."""
    out = []

    def err(m):
        out.append(("ERROR", "%s: %s" % (where, m)))

    def warn(m):
        out.append(("WARN", "%s: %s" % (where, m)))

    if not isinstance(rec, dict):
        err("fidelity is {subject, depicts: 'real' | 'abstract', references, proportions, parts, materials} "
            "(got %r)" % (rec,))
        return out
    known = {"subject", "depicts", "references", "proportions", "parts", "materials", "exploded", "mounted_on"}
    for k in sorted(set(rec) - known):
        err("fidelity has an unknown key %r (known: %s)" % (k, ", ".join(sorted(known))))
    if not str(rec.get("subject") or "").strip():
        err("fidelity.subject is empty — name the thing it depicts, as specifically as the references allow "
            "(\"GPS Block IIF satellite\", not \"satellite\")")
    dep = rec.get("depicts")
    if dep not in ("real", "abstract"):
        err("fidelity.depicts is 'real' (it depicts a real thing — a satellite, a watch, a puck) or 'abstract' "
            "(a chart, a metaphor shape) — got %r" % (dep,))
        return out
    refs = rec.get("references")
    if refs is None:
        refs = []
    if not isinstance(refs, list):
        err("fidelity.references is a list of {kind, source, note}")
        refs = []
    sources, images, specs = set(), 0, 0
    for i, r in enumerate(refs):
        tag = "fidelity.references[%d]" % i
        if not isinstance(r, dict):
            err("%s is {kind: photo|spec|drawing|asset, source, note} (got %r)" % (tag, r))
            continue
        kind, src = r.get("kind"), str(r.get("source") or "").strip()
        if kind not in KINDS:
            err("%s.kind is one of %s (got %r)" % (tag, ", ".join(KINDS), kind))
        if not src:
            err("%s has no source — a URL you read, or the path of the file" % tag)
            continue
        sources.add(src)
        if kind in ("spec", "drawing"):
            specs += 1
        if _is_url(src):
            if kind == "photo":
                err("%s is a photo by URL — fetch it (python3 scripts/imagefetch.py \"<query>\" <path>) so it "
                    "carries its licence sidecar and the sheet can show it; a product's own picture is kind "
                    "`asset`" % tag)
            continue
        path = resolve(src, base)
        if not os.path.isfile(path):
            err("%s: %s does not exist" % (tag, src))
            continue
        if kind in IMAGE_KINDS and path.lower().endswith(IMAGE_EXT):
            images += 1
        if kind == "photo":
            side = path + ".json"
            meta = None
            try:
                meta = json.load(open(side, encoding="utf-8"))
            except (OSError, ValueError):
                pass
            if not (isinstance(meta, dict) and meta.get("license") and meta.get("source")):
                err("%s: a photo carries its imagefetch sidecar %s with its licence and source — fetch it with "
                    "scripts/imagefetch.py, or, if it is the product's own picture, mark it kind `asset`"
                    % (tag, os.path.basename(side)))
    props = rec.get("proportions")
    if props is None:
        props = {}
    if not isinstance(props, dict):
        err("fidelity.proportions is {name: {value, source}}")
        props = {}
    for name, p in props.items():
        tag = "fidelity.proportions.%s" % name
        if not isinstance(p, dict):
            err("%s is {value, source} (got %r)" % (tag, p))
            continue
        if p.get("value") in (None, ""):
            err("%s has no value" % tag)
        cited = p.get("source")
        cited = cited if isinstance(cited, list) else [cited]
        cited = [str(c or "").strip() for c in cited]
        if not any(cited):
            err("%s has no source — which reference did the ratio come from?" % tag)
        else:
            stray = [c for c in cited if c and c not in sources]
            if stray:
                err("%s cites %s, which is not among fidelity.references — cite a reference's `source` exactly"
                    % (tag, ", ".join(repr(c) for c in stray)))
    parts = rec.get("parts")
    if parts is None:
        parts = []
    if not isinstance(parts, list):
        err("fidelity.parts is a list of part names")
        parts = []
    seen = set()
    for p in parts:
        if not isinstance(p, str) or not PART_NAME.match(p):
            err("fidelity.parts: %r is not a part name — lower-case letters, digits and '-', as written in "
                "data-part=\"…\"" % (p,))
        elif p in seen:
            err("fidelity.parts names %r twice" % p)
        seen.add(p)
    mats = rec.get("materials")
    if mats is not None and not (isinstance(mats, list) and all(isinstance(m, str) and m.strip() for m in mats)):
        err("fidelity.materials is a list of names")
    if "exploded" in rec and not isinstance(rec.get("exploded"), bool):
        err("fidelity.exploded is true or false")
    mounts = rec.get("mounted_on")
    if mounts is not None:
        if not isinstance(mounts, dict):
            err("fidelity.mounted_on is {part: the part (or list of parts) it is fixed to}")
        else:
            for k, v in mounts.items():
                on = [] if v is None else (v if isinstance(v, list) else [v])
                for name in [k] + on:
                    if not isinstance(name, str) or name not in seen:
                        err("fidelity.mounted_on names %r, which is not one of fidelity.parts" % (name,))
                if k in on:
                    err("fidelity.mounted_on: %r is mounted on itself" % k)
    # EVERY PART OF A REAL ASSEMBLY SAYS WHAT HOLDS IT. Detachment is judged against a declared mount, and a part no
    # mount names is judged against nothing: a jewel drawn off its fork touches the wheel beside it and passes. So a
    # real thing of two or more parts accounts for each one — mounted on a part (`'exit-pallet': 'pallet-fork'`),
    # held by something the drawing does not show (`'escape-wheel': null` — a pivot in the plate, the hand), or
    # named as another part's mount. An exploded view is exempt: its parts are apart on purpose.
    if (dep == "real" and isinstance(parts, list) and len(parts) >= 2 and not rec.get("exploded")
            and (mounts is None or isinstance(mounts, dict))):
        held = set(mounts or {})
        for v in (mounts or {}).values():
            held.update(v if isinstance(v, list) else ([v] if isinstance(v, str) else []))
        loose = [q for q in parts if isinstance(q, str) and q not in held]
        if loose:
            warn("names %d part(s) but says what holds only %d — %s: declare each in fidelity.mounted_on, on the part "
                 "it is fixed to, or null when what holds it is not drawn (a pivot, the frame). A part no mount names "
                 "is checked against nothing, and a part drawn floating beside another passes"
                 % (len(parts), len(parts) - len(loose), ", ".join(loose)))
    if dep == "real":
        if not refs:
            err("depicts a real thing and names no reference — collect them BEFORE drawing: a real photo "
                "(scripts/imagefetch.py) or the product's own asset, and a spec or drawing from a source you read")
        elif not images:
            err("depicts a real thing and has no reference IMAGE the sheet can show beside it — a local photo "
                "(scripts/imagefetch.py, with its sidecar), drawing or the product's own asset")
        if refs and not specs:
            warn("no spec or drawing among the references — proportions read off one photo carry its lens")
        if not props:
            err("depicts a real thing and records no proportion — take the key ratios from the references and "
                "cite each one's source")
        if not parts:
            err("depicts a real thing and names no defining parts — the parts without which it is not that thing "
                "(a watch's crown and band), each marked data-part=\"<name>\" where it is drawn")
        if not mats:
            warn("names no materials — say what the real thing is made of, so the critic can hold the render to it")
    if part_names is not None and parts:
        names, dynamic = part_names
        missing = [p for p in parts if isinstance(p, str) and p not in names]
        if missing and not names and not dynamic:
            err("declares parts %s and marks none of them — mark each on the node that draws it: "
                "data-part=\"<name>\"" % ", ".join(missing))
        elif missing:
            warn("declares %s but its source marks no data-part=\"…\" with %s literally%s — the fidelity sheet "
                 "checks the drawn DOM" % (", ".join(missing), "that name" if len(missing) == 1 else "those names",
                                           " (some marks are computed)" if dynamic else ""))
    return out


def errors_of(probs):
    return [m for lv, m in probs if lv == "ERROR"]


# ── THE SHEET: WHAT THE DOM DREW ─────────────────────────────────────────────────────────────────────────────

def parts_from_log(text):
    """The last FIDELITY-PARTS record a render logged, or None."""
    rec = None
    for line in (text or "").splitlines():
        k = line.find(FIDELITY_TAG)
        if k < 0:
            continue
        raw = line[k + len(FIDELITY_TAG):].strip()
        try:
            rec = json.loads(raw)
        except ValueError:
            # the CLI may wrap a long browser line; take the longest JSON prefix that parses
            for end in range(len(raw), 0, -1):
                if raw[end - 1] == "}":
                    try:
                        rec = json.loads(raw[:end])
                        break
                    except ValueError:
                        continue
    return rec


def _gap(a, b):
    """The distance between two boxes {x, y, w, h} (0 when they touch or overlap)."""
    dx = max(0.0, max(a["x"], b["x"]) - min(a["x"] + a["w"], b["x"] + b["w"]))
    dy = max(0.0, max(a["y"], b["y"]) - min(a["y"] + a["h"], b["y"] + b["h"]))
    return (dx * dx + dy * dy) ** 0.5


def union(boxes):
    if not boxes:
        return None
    x0 = min(b["x"] for b in boxes)
    y0 = min(b["y"] for b in boxes)
    x1 = max(b["x"] + b["w"] for b in boxes)
    y1 = max(b["y"] + b["h"] for b in boxes)
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def dom_problems(rec, declared, where, exploded=False, mounted_on=None):
    """[(level, sentence)] from one render's part report: MISSING and DETACHED parts, and — for each part the record
    says is MOUNTED ON another (`mounted_on`) — whether the two touch.

    WHY A DECLARATION. Touching anything is not being attached to it. In a mechanism, parts meet that are not joined:
    the escapement's locked pallet jewel rests on an escape-wheel tooth, and its exit jewel is drawn across the
    balance rim. A jewel drawn floating off its fork (validation film A's first escapement) therefore touched the
    wheel and the rim, belonged to the drawing's one connected piece, and DETACHED had nothing to report however its
    tolerance was set. What the jewel must touch is the part it is FIXED to, and only the record knows which that is."""
    out = []
    if rec is None:
        return [("ERROR", "%s: the render logged no part report — the probe did not run, so nothing was measured"
                 % where)]
    got = rec.get("parts") or {}
    for p in declared:
        slot = got.get(p) or {}
        if not slot.get("boxes"):
            why = ("%d node(s) marked but none visible (zero-sized or transparent)" % slot.get("hidden")
                   if slot.get("hidden") else "no node is marked data-part=\"%s\"" % p)
            out.append(("ERROR", "%s: part %r is declared and not drawn — %s; the object claims a part it does "
                        "not draw" % (where, p, why)))
    present = [p for p in declared if (got.get(p) or {}).get("boxes")]
    if exploded or len(present) < 2:
        return out
    mount_pairs = []
    for part, on in sorted((mounted_on or {}).items()):
        for host in (on if isinstance(on, list) else [on]):
            if part in present and host in present:
                mount_pairs.append((part, host))
    # ATTACHMENT, judged on the LEAVES — the shapes that put ink down (runtime/fidelity.tsx leavesOf); a group's own
    # box spans whatever lies between its children. Every leaf of every declared part is a node; two nodes are joined
    # when their boxes come within `tol`. Whatever is not joined to the largest component floats.
    # every MARKED part is ink that can bridge two declared ones (a radiator face between the bus and a wing boom), so
    # the graph holds all of them; a piece is reported only when it holds a declared part.
    marked = present + sorted(p for p in got if p not in present and (got[p] or {}).get("boxes"))
    nodes = []                                           # (part, box, outline or None)
    for p in marked:
        leaves = got[p].get("leaves") or got[p]["boxes"]
        geo = got[p].get("geo") if got[p].get("leaves") else None
        geo = geo if isinstance(geo, list) and len(geo) == len(leaves) else [None] * len(leaves)
        nodes += [(p, b, g) for b, g in list(zip(leaves, geo))[:400]]
    u = union([b for _p, b, _g in nodes])
    diag_tol = DETACH_TOL * ((u["w"] ** 2 + u["h"] ** 2) ** 0.5)
    # A PART IS ATTACHED BY TOUCHING, AT ITS OWN SCALE. The tolerance between two pieces is the drawing's 2% only up to
    # DETACH_OWN of the SMALLER part's own short side (never under DETACH_MIN_PX): a 2%-of-the-diagonal gap is 27 px
    # on the escapement's hero render, wider than its 27 px jewel — a gap the jewel could float in whole.
    short = {p: min(union(got[p].get("leaves") or got[p]["boxes"])["w"],
                    union(got[p].get("leaves") or got[p]["boxes"])["h"]) for p in marked}

    def tol_of(i, j):
        return min(diag_tol, max(DETACH_MIN_PX, DETACH_OWN * min(short[nodes[i][0]], short[nodes[j][0]])))
    parent = list(range(len(nodes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def dist(i, j, cap):
        """The gap between two leaves: their OUTLINES' distance less both half strokes when both carry one (0 when
        one's outline enters the other's filled shape), else their boxes' — a lower bound, never an over-report."""
        bg = _gap(nodes[i][1], nodes[j][1])
        if bg > cap:
            return bg
        a, b = nodes[i][2], nodes[j][2]
        return bg if not (a and b) else _outline_gap(a, b)

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if find(i) != find(j) and dist(i, j, tol_of(i, j)) <= tol_of(i, j):
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(nodes)):
        groups.setdefault(find(i), []).append(i)
    if len(groups) > 1:
        area = lambda g: sum(nodes[i][1]["w"] * nodes[i][1]["h"] for i in g)  # noqa: E731
        main = max(groups.values(), key=area)
        floating = {}
        for g in (g for g in groups.values() if g is not main):
            names = tuple(sorted({nodes[i][0] for i in g}))
            if not set(names) & set(present):
                continue
            gap = min(dist(i, k, float("inf")) for i in g for k in main)
            lim = min(tol_of(i, k) for i in g for k in main)
            n, far, lo = floating.get(names, (0, 0.0, lim))
            floating[names] = (n + 1, max(far, gap), min(lo, lim))
        for names, (n, gap, lim) in sorted(floating.items()):
            out.append(("ERROR", "%s: %s detached — %s %.0f px from the rest of the drawing (more than %.1f px: the "
                        "smaller of %d%% of its diagonal and %d%% of the part's own short side); attach it where the "
                        "real one is, or set fidelity.exploded for an exploded view"
                        % (where, " + ".join(repr(p) for p in names) + (" is" if len(names) == 1 else " are"),
                           "a piece" if n == 1 else "%d pieces, up to" % n, gap, lim, round(DETACH_TOL * 100),
                           round(DETACH_OWN * 100))))
    # MOUNTED PARTS TOUCH THEIR MOUNT — whatever else they touch
    for part, host in mount_pairs:
        a = [i for i in range(len(nodes)) if nodes[i][0] == part]
        b = [i for i in range(len(nodes)) if nodes[i][0] == host]
        gap = min(dist(i, k, float("inf")) for i in a for k in b)
        lim = min(tol_of(i, k) for i in a for k in b)
        if gap > lim:
            out.append(("ERROR", "%s: %r is mounted on %r (fidelity.mounted_on) and does not touch it — %.1f px apart "
                        "(more than %.1f px); it floats where the real one is fixed" % (where, part, host, gap, lim)))
    return out


def _outline_pts(g):
    import numpy as np
    p = np.asarray(g.get("p") or [], dtype=float).reshape(-1, 2)
    return p


def _inside(pts, poly):
    """bool per point: inside the closed polygon `poly` (even-odd ray cast)."""
    import numpy as np
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    x0, y0 = poly[:, 0][None, :], poly[:, 1][None, :]
    x1, y1 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
    cond = (y0 > y) != (y1 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
    return (cond & (x < xc)).sum(axis=1) % 2 == 1


def _seg_dist(pts, poly, closed):
    """min distance from any of `pts` to the polyline `poly` (closed: back to its first point)."""
    import numpy as np
    a = poly if closed else poly[:-1]
    b = np.roll(poly, -1, axis=0) if closed else poly[1:]
    best = float("inf")
    for k in range(0, len(pts), 256):                       # chunked: a spiral carries ~2000 points
        P = pts[k:k + 256][:, None, :]
        d = b - a
        L2 = np.maximum((d ** 2).sum(axis=1), 1e-9)
        t = np.clip(((P - a[None]) * d[None]).sum(axis=2) / L2[None], 0, 1)
        q = a[None] + t[..., None] * d[None]
        best = min(best, float(np.sqrt(((P - q) ** 2).sum(axis=2)).min()))
    return best


def _closed(p):
    """An outline that ends where it began (a polygon, a circle, a closed path): its last sample sits one sampling
    step (runtime OUTLINE_STEP, 3 px) from its first. An open line's ends are apart."""
    import numpy as np
    return len(p) >= 3 and float(np.hypot(*(p[-1] - p[0]))) <= 6.0


def _outline_gap(ga, gb):
    """The ink gap between two leaf outlines (runtime/fidelity.tsx outlineOf): 0 when either filled single-subpath
    shape holds a point of the other; else the outlines' distance less both half strokes, floored at 0."""
    pa, pb = _outline_pts(ga), _outline_pts(gb)
    if len(pa) < 2 or len(pb) < 2:
        return 0.0
    for g, mine, other in ((ga, pa, pb), (gb, pb, pa)):
        if g.get("f") and g.get("s", 1) == 1 and len(mine) >= 3 and _inside(other, mine).any():
            return 0.0
    d = min(_seg_dist(pa, pb, _closed(pb)), _seg_dist(pb, pa, _closed(pa)))
    return max(0.0, d - float(ga.get("sw") or 0) - float(gb.get("sw") or 0))


# ── THE SHEET: COMPOSING IT ──────────────────────────────────────────────────────────────────────────────────

def _font(size, text=""):
    from PIL import ImageFont
    name = "NotoSansSC-Subset.ttf" if re.search(r"[　-鿿]", text or "") else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(os.path.join(SKILL, "assets", "fonts", name), size,
                                  layout_engine=ImageFont.Layout.BASIC)
    except Exception:                                    # noqa: BLE001 — a default face still labels the sheet
        return ImageFont.load_default()


def _on_white(img):
    """A reference image as RGB, its transparency laid on WHITE: a line drawing (an SVG render, black on transparent)
    converted straight to RGB comes out black on black, and the sheet showed an empty reference."""
    from PIL import Image
    if img.mode in ("RGBA", "LA", "P", "PA") or "transparency" in img.info:
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        return bg.convert("RGB")
    return img.convert("RGB")


def _fit(img, max_w, max_h):
    s = min(max_w / float(img.width), max_h / float(img.height))
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s)))), s


def _short(src, n=70):
    s = str(src)
    return s if len(s) <= n else s[:n - 1] + "…"


def _drawn(report, part):
    """The boxes of what a part actually DRAWS — its leaves when the probe reported them, else its nodes' boxes. A
    group's own box spans whatever lies between its children (two straps around a case): outlining or cropping it
    would show the case and call it the band."""
    slot = ((report or {}).get("parts") or {}).get(part) or {}
    return slot.get("leaves") or slot.get("boxes") or []


def _cover(boxes):
    """The leaves worth outlining: drop a leaf inside another, keep at most 24 by area."""
    keep = sorted(boxes, key=lambda b: -b["w"] * b["h"])
    out = []
    for b in keep:
        if any(o["x"] <= b["x"] and o["y"] <= b["y"] and o["x"] + o["w"] >= b["x"] + b["w"]
               and o["y"] + o["h"] >= b["y"] + b["h"] for o in out):
            continue
        out.append(b)
        if len(out) >= 24:
            break
    return out


PALETTE = [(255, 99, 71), (65, 190, 255), (120, 220, 120), (255, 200, 60), (200, 130, 255), (255, 140, 200),
           (90, 230, 210), (240, 240, 240)]


def compose(out_png, name, rec, base, hero_png, hero_parts, film_png, film_parts, findings, film_label):
    """Write the sheet: references | hero (parts outlined) / the film-size frame / 100% crops of every part."""
    from PIL import Image, ImageDraw
    W, pad = 2400, 28
    bg, ink, dim, red = (18, 20, 24), (236, 238, 242), (150, 156, 168), (255, 92, 92)
    parts = [p for p in (rec.get("parts") or []) if isinstance(p, str)]
    colour = {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(parts)}
    blocks = []                                   # (image, (x, y)) placed after the canvas height is known
    y = pad
    texts = []                                    # (xy, text, size, fill)
    texts.append(((pad, y), "%s — fidelity sheet" % name, 44, ink))
    y += 58
    texts.append(((pad, y), "subject: %s · depicts: %s · materials: %s" % (
        rec.get("subject"), rec.get("depicts"), ", ".join(rec.get("materials") or []) or "—"), 26, dim))
    y += 44
    # ROW 1: the references, then the hero render
    row_h = 620
    x = pad
    refs = [r for r in rec.get("references") or [] if isinstance(r, dict)]
    shown = 0
    for r in refs:
        src = str(r.get("source") or "")
        path = None if _is_url(src) else resolve(src, base)
        if path and os.path.isfile(path) and path.lower().endswith(IMAGE_EXT) and shown < 2:
            im, _s = _fit(_on_white(Image.open(path)), 640, row_h - 70)
            blocks.append((im, (x, y)))
            cap = "REFERENCE · %s" % r.get("kind")
            texts.append(((x, y + im.height + 8), cap, 22, ink))
            texts.append(((x, y + im.height + 36), _short(r.get("note") or os.path.basename(src), 52), 18, dim))
            x += im.width + pad
            shown += 1
    if not shown:
        texts.append(((x, y + 20), "NO REFERENCE IMAGE", 30, red))
        x += 420
    hero_box = None
    if hero_png and os.path.isfile(hero_png):
        hero = Image.open(hero_png).convert("RGB")
        obj = (hero_parts or {}).get("object") or union([b for p in (hero_parts or {}).get("parts", {}).values()
                                                           for b in p.get("boxes", [])])
        if obj:
            m = 0.04 * max(obj["w"], obj["h"])
            crop = (max(0, int(obj["x"] - m)), max(0, int(obj["y"] - m)),
                    min(hero.width, int(obj["x"] + obj["w"] + m)), min(hero.height, int(obj["y"] + obj["h"] + m)))
        else:
            crop = (0, 0, hero.width, hero.height)
        hc = hero.crop(crop)
        room = W - x - pad
        im, s = _fit(hc, room, row_h - 70)
        d = ImageDraw.Draw(im)
        for p in parts:
            for b in _cover(_drawn(hero_parts, p)):
                bx = ((b["x"] - crop[0]) * s, (b["y"] - crop[1]) * s, (b["x"] + b["w"] - crop[0]) * s,
                      (b["y"] + b["h"] - crop[1]) * s)
                d.rectangle(bx, outline=colour[p], width=2)
        blocks.append((im, (x, y)))
        hero_box = (x, y, im.width, im.height)
        texts.append(((x, y + im.height + 8), "THE RENDER · hero size, settled · parts outlined", 22, ink))
        lx = x
        for p in parts:
            t = "■ " + p
            texts.append(((lx, y + im.height + 36), t, 18, colour[p]))
            lx += 14 * len(t) + 18
    y += row_h + pad
    # ROW 2: as the film shows it
    if film_png and os.path.isfile(film_png):
        film = Image.open(film_png).convert("RGB")
        im, s = _fit(film, 1180, 664)
        d = ImageDraw.Draw(im)
        for p in parts:
            for b in _cover(_drawn(film_parts, p)):
                d.rectangle((b["x"] * s, b["y"] * s, (b["x"] + b["w"]) * s, (b["y"] + b["h"]) * s),
                            outline=colour[p], width=1)
        blocks.append((im, (pad, y)))
        texts.append(((pad, y + im.height + 8), "AS THE FILM SHOWS IT · %s · %dx%d shown at %d%%"
                      % (film_label, film.width, film.height, round(s * 100)), 22, ink))
        # ROW 2 right: the 100% crops, from the film-size frame
        cx, cy, col_w = pad + im.width + pad, y, W - (pad + im.width + 2 * pad)
        texts.append(((cx, cy), "100% CROPS at the film's size — does the detail hold where it is shown?", 22, ink))
        cy += 34
        tile = 260
        tx = cx
        for p in parts:
            boxes = ((film_parts or {}).get("parts", {}).get(p) or {}).get("boxes", [])
            drawn = _drawn(film_parts, p)
            if tx + tile > W - pad:
                tx, cy = cx, cy + tile + 56
            if not boxes:
                texts.append(((tx + 10, cy + tile // 2 - 30), "MISSING", 34, red))
                texts.append(((tx + 10, cy + tile // 2 + 12), "not drawn", 20, red))
            else:
                b = max(drawn, key=lambda q: q["w"] * q["h"])   # the largest thing the part DRAWS
                ccx, ccy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
                half = tile / 2
                box = (int(max(0, ccx - half)), int(max(0, ccy - half)))
                box = (box[0], box[1], min(film.width, box[0] + tile), min(film.height, box[1] + tile))
                c = film.crop(box)
                dd = ImageDraw.Draw(c)
                dd.rectangle((b["x"] - box[0], b["y"] - box[1], b["x"] + b["w"] - box[0], b["y"] + b["h"] - box[1]),
                             outline=colour[p], width=1)
                blocks.append((c, (tx, cy)))
            texts.append(((tx, cy + tile + 6), "%s · %d node(s)" % (p, len(boxes)), 18, colour[p]))
            tx += tile + 18
        y += max(im.height + 44, cy - y + tile + 40) + pad
    # ROW 3: the references' sources and the record's proportions, then the findings
    texts.append(((pad, y), "REFERENCES", 24, ink))
    y += 34
    for r in refs:
        texts.append(((pad, y), "· %s — %s" % (r.get("kind"), _short(r.get("source"), 150)), 18, dim))
        y += 26
    props = rec.get("proportions") or {}
    if props:
        y += 10
        texts.append(((pad, y), "PROPORTIONS (as recorded)", 24, ink))
        y += 34
        for k, v in props.items():
            v = v if isinstance(v, dict) else {}
            src = v.get("source")
            src = ", ".join(src) if isinstance(src, list) else src
            texts.append(((pad, y), "· %s = %s%s — %s" % (k, v.get("value"),
                          (" (drawn %s)" % v.get("drawn")) if v.get("drawn") is not None else "", _short(src, 120)),
                          18, dim))
            y += 26
    y += 10
    errs = [m for lv, m in findings if lv == "ERROR"]
    warns = [m for lv, m in findings if lv == "WARN"]
    texts.append(((pad, y), "FINDINGS — %d error(s), %d warning(s)" % (len(errs), len(warns)), 24,
                  red if errs else (120, 220, 120)))
    y += 34
    for lv, m in findings:
        texts.append(((pad, y), "%s  %s" % (lv, _short(m, 200)), 18, red if lv == "ERROR" else (255, 200, 60)))
        y += 26
    H = y + pad
    sheet = Image.new("RGB", (W, H), bg)
    for im, xy in blocks:
        sheet.paste(im, xy)
    d = ImageDraw.Draw(sheet)
    for xy, t, size, fill in texts:
        d.text(xy, t, fill=fill, font=_font(size, t))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sheet.save(out_png)
    return out_png


# ── ORCHESTRATION ────────────────────────────────────────────────────────────────────────────────────────────

def record_for(out_dir, name):
    """(record, base_dir, source_or_None, where, kind) for a workshop object/shot or a library object."""
    import workshop as ws
    if name in ws.shot_names(out_dir):
        board = ws._board(out_dir)
        e = next((x for x in (board.get("meta") or {}).get("build_list") or []
                  if isinstance(x, dict) and x.get("id") == name), None)
        rec = (e or {}).get("fidelity")
        return rec, out_dir, ws.shot_part_source(out_dir, name), "meta.build_list `%s`" % name, "shot"
    if name in ws.object_names(out_dir):
        src = ws.object_source(out_dir, name)
        rec, why = object_fidelity(src)
        if why:
            raise ws.WorkshopError(["workshop/objects/%s.tsx: %s" % (name, why)])
        return rec, out_dir, src, "workshop/objects/%s.tsx" % name, "object"
    if name in ws.library_object_names():
        src = ws._read(os.path.join(ws.LIB_OBJECTS, name + ".tsx"))
        rec, why = object_fidelity(src)
        if why:
            raise ws.WorkshopError(["remotion/src/objects/%s.tsx: %s" % (name, why)])
        return rec, SKILL, src, "remotion/src/objects/%s.tsx" % name, "object"
    if name in ws.library_shot_names():
        src = ws._read(os.path.join(ws.LIB_SHOTS, name + ".tsx"))
        rec, why = register_fidelity(src)
        if why:
            raise ws.WorkshopError(["remotion/src/shots/%s.tsx: %s" % (name, why)])
        return rec, SKILL, src, "remotion/src/shots/%s.tsx" % name, "shot"
    raise ws.WorkshopError(["%s is not in this film's workshop, the library's objects or the library's registers"
                            % name])


def _render_all(out_dir, jobs, parts=True):
    """Render each job {tag, id, props, frame, png} with the part probe armed — one bundle (the film's workshop in
    it), one browser (scripts/fidelity_stills.cjs) — under the machine-wide render lock. {tag: part report | None}.
    `parts=False` renders the stills alone (scripts/style_qa.py reuses the one-bundle, one-browser path)."""
    import shutil
    import subprocess
    import tempfile
    import _common as _c
    import workshop as ws
    import text_safe_qa as ts
    jobs = [dict(j, props=dict(j["props"], fidelityParts=True)) for j in jobs] if parts else list(jobs)
    work = tempfile.mkdtemp(prefix="fidelity_")
    try:
        with _c.render_lock():
            pub = out_dir if out_dir and os.path.isdir(out_dir) else None
            bundle = ts.glide_bundle(os.path.join(work, "bundle"), pub, ws.prepare(out_dir))
            jp, op = os.path.join(work, "jobs.json"), os.path.join(work, "out.jsonl")
            with open(jp, "w", encoding="utf-8") as fh:
                json.dump(jobs, fh, ensure_ascii=False)
            cmd = ["node", os.path.join(_HERE, "fidelity_stills.cjs"), ws.REMOTION, bundle, jp, op, "--gl=angle"]
            try:
                r = subprocess.run(cmd, cwd=ws.REMOTION, capture_output=True, text=True, timeout=300 + 120 * len(jobs))
            except subprocess.TimeoutExpired:
                raise ws.WorkshopError(["the fidelity renders did not finish in time"]) from None
        res = {}
        if os.path.exists(op):
            for line in open(op, encoding="utf-8"):
                rec = json.loads(line)
                if rec.get("error"):
                    raise ws.WorkshopError(["the fidelity render %s failed: %s" % (rec.get("tag"), rec["error"])])
                res[rec["tag"]] = rec.get("parts")
        missing = [j["tag"] for j in jobs if j["tag"] not in res or not os.path.exists(j["png"])]
        if r.returncode != 0 or missing:
            raise ws.WorkshopError(["the fidelity renders failed (%s): %s" % (", ".join(missing) or "exit %d" % r.returncode,
                                    ((r.stderr or "") + (r.stdout or "")).strip()[-400:] or "(no output)")])
        return res
    finally:
        shutil.rmtree(work, ignore_errors=True)


def sheet(out_dir, name, props=None, host="ObjectStage", slot=None, dna=None):
    """Render and compose `name`'s fidelity sheet; returns {png, json, problems: [(level, sentence)]}."""
    import workshop as ws
    import render_remotion as rr
    rec, base, src, where, kind = record_for(out_dir, name)
    if rec is None:
        raise ws.WorkshopError(["%s declares no fidelity record — %s" % (
            where, "add `fidelity` to its META" if kind == "object"
            else "export `FIDELITY` from it" if where.startswith("remotion/src/shots/")
            else "add `fidelity` to its build-list entry")])
    findings = problems(rec, base, where, source_part_names(src) if src else None)
    outd = os.path.join(out_dir, SHEET_DIR)
    os.makedirs(outd, exist_ok=True)
    declared = [p for p in rec.get("parts") or [] if isinstance(p, str)]
    board = ws._board(out_dir)
    meta = board.get("meta") or {}
    dna = dna or meta.get("design_dna") or meta.get("shot_template")
    # THE FILM'S DRAWING STYLE (runtime/style.tsx): a styled film shows its objects styled, so that is what is measured
    # — a style may round and simplify, and must not lose or detach a part
    style = meta.get("style") if isinstance(meta.get("style"), dict) else None
    jobs = []
    hero_png = os.path.join(outd, name + ".hero.png") if kind == "object" else None
    if kind == "object":
        placed = props and any(isinstance(r, dict) and r.get("id") == name
                               for _p, r in ws.object_refs(ws.shot_source(out_dir, host) or "", props))
        payload = {"object": dict({"id": name}, **({"props": props} if props and not placed else {}))}
        if dna:
            payload["dna"] = dna
        if style:
            payload["style"] = style
        jobs.append({"tag": "hero", "id": "FidelityHero", "props": payload, "frame": 0, "png": hero_png})
    comp, payload, dur = ws.still_plan(out_dir, name, props, host=host, slot=slot, dna=dna)
    if style:
        payload = dict(payload, style=style)
    frame = int(round(rr.frame_at_t(dur, rr.SETTLED_T)))
    film_png = os.path.join(outd, name + ".film.png")
    jobs.append({"tag": "film", "id": comp, "props": payload, "frame": frame, "png": film_png})
    got = _render_all(out_dir, jobs)
    hero_parts, film_parts = got.get("hero"), got.get("film")
    if declared:
        if hero_parts is not None or kind == "object":
            findings += dom_problems(hero_parts, declared, "%s at hero size" % name, bool(rec.get("exploded")),
                                     rec.get("mounted_on"))
        findings += [f for f in dom_problems(film_parts, declared, "%s as the film shows it (%s)" % (name, comp),
                                             bool(rec.get("exploded")), rec.get("mounted_on"))
                     if ("detached" not in f[1] and "does not touch" not in f[1])
                     or hero_parts is None]
    png = os.path.join(outd, name + ".png")
    compose(png, name, rec, base, hero_png, hero_parts, film_png, film_parts, findings,
            "on %s, frame %d" % (comp, frame))
    scope = scope_lines(declared, kind, comp, frame, payload.get("aspect") or "16:9", hero_parts, film_parts)
    report = {"name": name, "kind": kind, "record": rec, "hero": hero_parts, "film": film_parts,
              "film_host": comp, "frame": frame, "style": style.get("name") if style else None, "aspect": payload.get("aspect") or "16:9", "scope": scope,
              "problems": [{"level": lv, "message": m} for lv, m in findings]}
    jp = os.path.join(outd, name + ".json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    return {"png": png, "json": jp, "problems": findings, "scope": scope}


def scope_lines(declared, kind, host, frame, aspect, hero_parts, film_parts):
    """What the sheet MEASURED and what it leaves to the eye — printed with every sheet (E4)."""
    out = []
    renders = (["hero size"] if kind == "object" else []) + ["%s at %s, frame %d" % (host, aspect, frame)]
    got = [r for r, p in zip(renders, ([hero_parts] if kind == "object" else []) + [film_parts]) if p is not None]
    if declared and got:
        out.append("MEASURED — %d declared part(s) for presence (MISSING) and attachment (DETACHED: SVG shapes by "
                   "their drawn outlines, other nodes by their boxes, within %d%% of the drawing's diagonal or %d%% of "
                   "the smaller part's short side, whichever is less) in the rendered DOM: %s"
                   % (len(declared), round(DETACH_TOL * 100), round(DETACH_OWN * 100), "; ".join(got)))
        out.append("NOT MEASURED — depth: a part drawn OVER another (a jewel crossing the balance rim in the picture) "
                   "touches it on screen whether or not it is mounted on it; attachment in depth is left to the eye")
    elif declared:
        out.append("NOT MEASURED — no render logged a part report: presence and attachment are unchecked (an ERROR "
                   "above says so)")
    else:
        out.append("NOT MEASURED — the record declares no parts: presence and attachment were not checked")
    out.append("NOT MEASURED, left to the eye — likeness to the references, proportions (shown as recorded, not "
               "measured off the render), materials, detail at 100%: the sheet sets them side by side for a person")
    return out


def real_built_things(out_dir):
    """[(name, kind)] of a film's built things that declare `depicts: 'real'` — the sheet is owed for each."""
    import workshop as ws
    out = []
    board = ws._board(out_dir)
    for e in (board.get("meta") or {}).get("build_list") or []:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str):
            continue
        n = e["id"]
        try:
            rec = record_for(out_dir, n)[0]
        except Exception:                                # noqa: BLE001 — a malformed entry is validate.py's to report
            continue
        if isinstance(rec, dict) and rec.get("depicts") == "real":
            out.append((n, e.get("kind")))
    return out


def sheet_status(out_dir, name):
    """'ok' | 'errors' | 'missing' | 'stale' for a built thing's sheet — stale when its source or record moved
    after the sheet was made."""
    import workshop as ws
    jp = os.path.join(out_dir, SHEET_DIR, name + ".json")
    if not os.path.isfile(jp):
        return "missing"
    t = os.path.getmtime(jp)
    srcs = [p for p in (os.path.join(ws.workshop_dir(out_dir), k, name + ".tsx") for k in ws.KINDS) if os.path.isfile(p)]
    if any(os.path.getmtime(p) > t for p in srcs):
        return "stale"
    try:
        rep = json.load(open(jp, encoding="utf-8"))
    except (OSError, ValueError):
        return "missing"
    return "errors" if any(p.get("level") == "ERROR" for p in rep.get("problems") or []) else "ok"


if __name__ == "__main__":
    print(__doc__)
    sys.exit(0)
