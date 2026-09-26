"""Every prop LIBRARY.md tells an author to pass is a prop the register declares.

THE FAILURE. The manifest is what the shot-director casts from, and it had drifted from the code in the one
direction that fails silently: `TermThink` was advertised as `prompt, thoughts[], answer` and declares
`question, think`; `TermGitLog` as `entries[{hash,msg,tag}]` and declares `commits[{hash,ref,msg}]`;
`TermTable` as `cols[]` and declares `headers`; `SpinningProton` listed a `sublabel` that did not exist. A film
authored from the manifest passes names the register never reads, the render succeeds, and every omitted prop
prints its DEMO default — "hermes --mode hybrid", two invented commits — on a frame about something else.
Nothing errors, because an unknown prop is not an error in React.

WHAT IS CHECKED. Each signature in backticks attached to a register name (`**Name** \\`a, b[]\\`` in the
catalogue, `Name \\`a, b\\`` in the tables): every top-level name must be a declared prop, and every field
named inside `{...}` must appear in that prop's declared type (following a named alias).
"""
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import demo_copy_qa as dq  # noqa: E402

LIBRARY = os.path.join(_ROOT, "remotion", "LIBRARY.md")
SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")

_ITEM = re.compile(r"^([a-zA-Z]\w*)((?:\[\d*\])*)(?:\{([^{}]*)\})?((?:\[\d*\])*)$")
_BRACED = re.compile(r"\[\{([^{}]*)\}\]")


def _split_sig(sig):
    """Top-level comma split, respecting [] and {}."""
    out, depth, cur = [], 0, ""
    for ch in sig:
        depth += ch in "[{"
        depth -= ch in "]}"
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _parse(sig):
    """[(prop, [nested field names])] when `sig` reads as a prop signature, else None."""
    parts = _split_sig(sig)
    if not parts:
        return None
    out = []
    for p in parts:
        p = p.replace(" ", "")
        nested = []
        m = _BRACED.search(p)
        if m:
            nested = [f for f in re.split(r"[,\s]+", re.sub(r"\[[^\]]*\]", "", m.group(1))) if f]
            p = _BRACED.sub("[]", p)
        mm = _ITEM.match(p)
        if not mm:
            return None
        if mm.group(3) is not None:
            nested += [f for f in re.split(r"[,\s]+", re.sub(r"\[[^\]]*\]", "", mm.group(3))) if f]
        out.append((mm.group(1), nested))
    return out


def signatures():
    """[(line_no, register, prop, nested)] from LIBRARY.md."""
    shots = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(SHOTS, "*.tsx"))}
    found = []
    for n, line in enumerate(open(LIBRARY, encoding="utf-8"), 1):
        pairs = re.findall(r"\*\*(\w+)\*\*\s*`([^`]+)`", line)
        pairs += re.findall(r"\*\*(\w+)\*\*\s+—[^`]*?\*Use:[^*]*\*\s*`([^`]+)`", line)
        if line.lstrip().startswith("|"):
            pairs += re.findall(r"(?:^|[|·]\s*)([A-Z]\w+)\s+`([^`]+)`", line)
        for reg, sig in pairs:
            if reg not in shots:
                continue
            parsed = _parse(sig)
            if parsed is None:
                continue
            for prop, nested in parsed:
                found.append((n, reg, prop, nested))
    return found


def _type_text(src, ty):
    """The declared type, with one level of named alias resolved (`Commit[]` -> the body of `type Commit`)."""
    text = ty
    for alias in re.findall(r"\b([A-Z]\w*)\b", ty):
        am = re.search(r"\b(?:type|interface)\s+%s\b[^={]*=?\s*" % re.escape(alias), src)
        if am:
            body = dq._brace_body(src, am.end()) if src[am.end():am.end() + 1] == "{" else None
            if body:
                text += " " + body
    return text


def test_library_signatures_name_real_props():
    drift = []
    for n, reg, prop, nested in signatures():
        src = open(os.path.join(SHOTS, reg + ".tsx"), encoding="utf-8").read()
        types = dq._declared_types(src, reg)
        if not types:
            continue                        # a register whose props this reader cannot see is not judged here
        if prop not in types:
            drift.append("LIBRARY.md:%d %s: `%s` is not a prop (declares: %s)" % (n, reg, prop, ", ".join(types)))
            continue
        tt = _type_text(src, types[prop])
        for f in nested:
            if not re.search(r"\b%s\s*\??\s*:" % re.escape(f), tt):
                drift.append("LIBRARY.md:%d %s: `%s{%s}` — `%s` is not a field of %s" % (n, reg, prop, f, f, types[prop]))
    assert not drift, "LIBRARY.md advertises props the code does not read:\n" + "\n".join(drift)


def test_the_parser_reads_the_forms_the_manifest_uses():
    assert _parse("lines[{t,text,level}]") == [("lines", ["t", "text", "level"])]
    assert _parse("cols[], rows[][]") == [("cols", []), ("rows", [])]
    assert _parse("left{label,points[]}, right{label,points[]}, winner, title") == [
        ("left", ["label", "points"]), ("right", ["label", "points"]), ("winner", []), ("title", [])]
    assert _parse("task, states[2], returnsTo, note") == [("task", []), ("states", []), ("returnsTo", []), ("note", [])]
    assert _parse("runtime/uiSurface") is None and _parse("i % 3") is None
    assert len(signatures()) > 100, "the reader stopped finding the manifest's signatures"


def test_validate_errors_on_a_prop_the_register_never_reads():
    """The board-side half: a key the register does not declare is an ERROR naming the props it does read,
    and an author's own `_note` key is left alone."""
    import validate as v
    errors, warnings = [], []
    slides = [{"index": 3, "shot": "TermThink",
               "shot_props": {"prompt": "why?", "thoughts": ["a"], "answer": "b", "_note": "mine"},
               "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"}}]
    v._check_remotion({"renderer": "remotion"}, slides, errors, warnings)
    hits = [e for e in errors if "has no prop" in e]
    assert any("`prompt`" in e for e in hits) and any("`thoughts`" in e for e in hits), errors
    assert not any("`_note`" in e for e in hits) and not any("`answer`" in e for e in hits), hits
    assert "question" in hits[0] and "think" in hits[0], "the error must name the props the register reads"


def test_the_librarys_own_headline_count_is_the_number_of_registers_it_documents():
    """The heading said 134 while the directory held 175 and every one of them was documented below it.

    Nobody writes the wrong number on purpose: a register is added, its section is written, and the count
    in the title — the one line a reader takes on trust without scrolling — is the one thing no step
    touches. It drifted by 41, which is a quarter of the library missing from the only number most readers
    will ever read. This repo has shipped this exact shape before as a stale folio ("第 N / 37 页" on a
    30-beat film): a rule that lived in prose and never as a gate. So it is a gate.
    """
    import glob
    head = open(LIBRARY, encoding="utf-8").readline()
    m = re.search(r"\((\d+)\s+design languages\)", head)
    assert m, "LIBRARY.md's first line no longer states a count: %r" % head
    on_disk = len(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx")))
    assert int(m.group(1)) == on_disk, (
        "LIBRARY.md's headline claims %s design languages and the library holds %d — the one number a "
        "reader takes on trust is the one nothing updates" % (m.group(1), on_disk))


def test_registering_a_shot_keeps_the_headline_count_current(tmp_path, monkeypatch):
    """register_shot refreshed the census on every registration but never the headline: adding DeviceDemo left
    "(185 design languages)" over 186 registers. The refresh now rewrites both, from the files on disk."""
    import register_shot as rs
    rem = tmp_path / "remotion"
    shots = rem / "src" / "shots"
    shots.mkdir(parents=True)
    for n in ("A", "B", "C"):
        (shots / (n + ".tsx")).write_text("// stub\n", encoding="utf-8")
    src = open(LIBRARY, encoding="utf-8").read()
    (rem / "LIBRARY.md").write_text(re.sub(r"\(\d+\s+design languages\)", "(999 design languages)", src, count=1),
                                    encoding="utf-8")
    monkeypatch.setattr(rs, "_REM", str(rem))
    monkeypatch.setattr(rs, "_SHOTS", str(shots))
    assert rs.refresh_family_census()
    head = (rem / "LIBRARY.md").read_text(encoding="utf-8").splitlines()[0]
    assert "(3 design languages)" in head, head
