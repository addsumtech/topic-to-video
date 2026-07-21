#!/usr/bin/env python3
"""Capture the SOURCE TEXT behind every claim, so a brief can be checked against what was
actually read rather than trusted.

The hole this closes: when the comprehension brief is built from web research or from a
document that is never persisted, `brief.json` becomes the only record of what the material
said. Nothing downstream can verify it. A content critic reviewing a real deck put it exactly:

    "no raw source documents exist in the workdir, so I audited brief.json as an ARTIFACT …
     but could not independently re-verify its web-sourced figures."

That is the one place in the pipeline where a wrong INPUT yields a fully-green output: the
gates check the brief's internal consistency, the plans inherit it, and 40 beats carry the
error with every check passing. Persisting the extracts turns `source_ref` from a free-text
string nobody reads into a pointer a critic (or a human, months later) can follow.

Layout — `<out_dir>/sources/`:
    sources/index.json          {sid → {origin, kind, fetched, title, chars}}
    sources/<sid>.txt           the extract, verbatim, as it was read

`sid` is a short stable slug. An evidence item then carries `source_ref: "<sid>#<anchor>"`,
where `<anchor>` is a literal substring of that extract — so `brief_qa` can confirm the
claim's support EXISTS in the captured text, not merely that a citation was typed.

Usage
  python scripts/sources.py add <out_dir> --sid tencent-overview \\
        --origin https://… --kind web --title "WorkBuddy 简介" --text-file extract.txt
  python scripts/sources.py add <out_dir> --sid paper --origin ./paper.pdf --kind pdf \\
        --title "…" --pages 3-9 --text-file extract.txt
  python scripts/sources.py list <out_dir>
  python scripts/sources.py verify <out_dir> --ref "tencent-overview#交付可验收的结果"

API: `add(out_dir, sid, text, origin, kind, title, extra)` · `load(out_dir)` ·
     `resolve(out_dir, ref)` -> (ok, detail)
"""
import argparse, json, os, re, sys

SOURCES_DIR = "sources"
INDEX = "index.json"


def _dir(out_dir):
    return os.path.join(out_dir, SOURCES_DIR)


def _index_path(out_dir):
    return os.path.join(_dir(out_dir), INDEX)


def load(out_dir):
    """→ {sid: meta}; {} when nothing has been captured."""
    try:
        with open(_index_path(out_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def text_of(out_dir, sid):
    try:
        with open(os.path.join(_dir(out_dir), sid + ".txt"), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def add(out_dir, sid, text, origin, kind="web", title="", extra=None, fetched=None):
    """Persist one extract verbatim. `fetched` must be supplied by the caller (the pipeline
    knows today's date); it is recorded, never invented here."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", sid or ""):
        raise ValueError("sid must be a short lowercase slug (a-z 0-9 . _ -)")
    if not (text or "").strip():
        raise ValueError("refusing to record an empty extract — capture what you actually read")
    os.makedirs(_dir(out_dir), exist_ok=True)
    with open(os.path.join(_dir(out_dir), sid + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    idx = load(out_dir)
    meta = {"origin": origin, "kind": kind, "title": title, "chars": len(text)}
    if fetched:
        meta["fetched"] = fetched
    if extra:
        meta.update(extra)
    idx[sid] = meta
    with open(_index_path(out_dir), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return meta


def _norm(s):
    # match on visible characters: whitespace and the CJK/ASCII punctuation that varies between
    # a page's rendering and a hand-typed citation must not decide whether support exists.
    return re.sub(r"[\s，,。.、；;：:！!？?（）()「」『』\"'’“”\-–—]+", "", s or "")


def resolve(out_dir, ref):
    """(ok, detail) for one `source_ref`.

    A ref is `<sid>` or `<sid>#<anchor>`. With an anchor, the anchor must appear in the captured
    extract — that is what makes the citation checkable rather than decorative.
    """
    if not (ref or "").strip():
        return False, "empty source_ref"
    idx = load(out_dir)
    if not idx:
        return True, "no sources/ captured — nothing to check against (advisory)"
    sid, _, anchor = str(ref).partition("#")
    sid = sid.strip()
    if sid not in idx:
        return False, f"unknown source id '{sid}' (sources/index.json has: {', '.join(sorted(idx)[:6])}…)"
    if not anchor.strip():
        return True, f"'{sid}' exists (no anchor given — the claim is not pinned to a passage)"
    body = text_of(out_dir, sid)
    if body is None:
        return False, f"sources/{sid}.txt is missing though the index lists it"
    if _norm(anchor) in _norm(body):
        return True, f"anchor found in '{sid}'"
    return False, (f"anchor not found in '{sid}' — the captured text does not contain "
                   f"\"{anchor[:40]}\"; quote the source, or fix the claim")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="capture one extract")
    a.add_argument("out_dir"); a.add_argument("--sid", required=True)
    a.add_argument("--origin", required=True, help="URL or file path the text came from")
    a.add_argument("--kind", default="web", choices=["web", "pdf", "doc", "code", "notes", "transcript", "image"])
    a.add_argument("--title", default=""); a.add_argument("--fetched", default="")
    a.add_argument("--pages", default="", help="page range, for a pdf/doc extract")
    src = a.add_mutually_exclusive_group(required=True)
    src.add_argument("--text-file"); src.add_argument("--text")
    l = sub.add_parser("list", help="what has been captured"); l.add_argument("out_dir")
    v = sub.add_parser("verify", help="resolve one source_ref"); v.add_argument("out_dir"); v.add_argument("--ref", required=True)
    args = ap.parse_args()

    if args.cmd == "add":
        text = args.text if args.text else open(args.text_file, encoding="utf-8").read()
        extra = {"pages": args.pages} if args.pages else None
        m = add(args.out_dir, args.sid, text, args.origin, args.kind, args.title, extra, args.fetched or None)
        print(f"[sources] captured '{args.sid}' ({m['chars']} chars) from {args.origin}")
    elif args.cmd == "list":
        idx = load(args.out_dir)
        if not idx:
            print("[sources] nothing captured"); return 0
        for sid, m in sorted(idx.items()):
            print(f"  {sid:<28} {m.get('kind',''):<10} {m.get('chars',0):>7} chars  {m.get('origin','')[:60]}")
    else:
        ok, detail = resolve(args.out_dir, args.ref)
        print(("  OK   " if ok else "  FAIL ") + detail)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
