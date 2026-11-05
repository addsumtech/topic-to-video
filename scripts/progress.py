#!/usr/bin/env python3
"""Where a long step is, for the person waiting on it.

    python3 scripts/progress.py <out_dir>          one line: phase, i of n, the item, elapsed, ETA

WHY. On the ANC film (2026-11-05) the render sat 1 h 35 min on one beat and nobody could tell: its log was
block-buffered and empty, and the only question anyone could ask was "is it still going?". Every long step — the
Blender plates, the per-beat render, the delivery gates — now writes `<out_dir>/_progress.json` as it goes, and a
`_progress.html` beside it that reloads itself every few seconds: open it once and watch. The ETA is the measured
mean of the items done so far, times the items left; with none done there is none.
"""
import html
import json
import os
import sys
import time

FILE, PAGE = "_progress.json", "_progress.html"
REFRESH_S = 5


def write(out_dir, phase, done, total, item=None):
    """Record that `phase` has finished `done` of `total` items and is now on `item`. Never raises: progress is
    a courtesy, and a full disk or a read-only folder must not fail the render it describes."""
    try:
        path = os.path.join(out_dir, FILE)
        now = time.time()
        try:
            old = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            old = {}
        started = old.get("started") if old.get("phase") == phase and old.get("done", 0) <= done else now
        eta = None
        if done > 0 and total and done < total:
            eta = (now - started) / done * (total - done)
        rec = {"phase": phase, "done": int(done), "total": int(total), "item": item, "started": started,
               "updated": now, "eta_s": None if eta is None else round(eta, 1)}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        os.replace(tmp, path)
        with open(os.path.join(out_dir, PAGE + ".tmp"), "w", encoding="utf-8") as fh:
            fh.write(_page(rec))
        os.replace(os.path.join(out_dir, PAGE + ".tmp"), os.path.join(out_dir, PAGE))
    except Exception:                                    # noqa: BLE001 — see the docstring
        pass


def _clock(s):
    s = int(round(s))
    return "%d:%02d" % (s // 60, s % 60) if s < 3600 else "%d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60)


def line(rec, now=None):
    now = now or time.time()
    if not rec:
        return "no progress recorded"
    done = rec.get("phase_done") or rec["done"] >= rec["total"]
    parts = ["%s %d/%d" % (rec["phase"], rec["done"], rec["total"])]
    if rec.get("item") and not done:
        parts.append("on %s" % rec["item"])
    parts.append("elapsed %s" % _clock(now - rec["started"]))
    if rec.get("eta_s") is not None and not done:
        parts.append("about %s left" % _clock(rec["eta_s"]))
    parts.append("updated %s ago" % _clock(now - rec["updated"]))
    return " · ".join(parts)


def _page(rec):
    pct = 100.0 * rec["done"] / rec["total"] if rec["total"] else 0.0
    return ("<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=%d><title>%s %d/%d</title>"
            "<style>body{font:16px/1.4 system-ui,sans-serif;margin:32px;background:#f6f5f2;color:#1f2328}"
            ".bar{height:10px;background:#ddd;border-radius:5px}.bar i{display:block;height:10px;border-radius:5px;"
            "background:#b8713b;width:%.1f%%}</style><h2>%s</h2><div class=bar><i></i></div><p>%s</p>"
            % (REFRESH_S, html.escape(rec["phase"]), rec["done"], rec["total"], pct, html.escape(rec["phase"]),
               html.escape(line(rec, rec["updated"]))))


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    try:
        rec = json.load(open(os.path.join(argv[0], FILE), encoding="utf-8"))
    except (OSError, ValueError):
        rec = None
    print("[progress] " + line(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
