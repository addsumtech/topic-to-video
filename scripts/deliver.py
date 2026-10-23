"""Hand the finished video to the user where they look for it — the Desktop, else Downloads.

A pipeline's out_dir can live anywhere: a scratch folder, this skill's own tree, a git-ignored work folder. None of
those is somewhere a person browses, and handing the user a path inside one has cost real time more than once. This
copies the deliverables (`out.mp4`, and `out.srt` beside it under the same name) to `~/Desktop`, or to `~/Downloads`
when the Desktop cannot be written — macOS can withdraw a process's access to either folder mid-session, so the test
is a real probe write, not `os.access`. It never writes under this skill's folder or `~/.claude`, and it never
overwrites a file already there: a second delivery of the same film lands as "<name> (2).mp4".

The sign-off renders go the same way (`--what sample` for step 8's sample.mp4, `--what preview` for the html tier's
preview.mp4), named "<film> - sample.mp4" so they are never mistaken for the film.

CLI:  deliver.py <out_dir> [--to <folder>] [--what out|sample|preview]   prints each delivered path and the `open` line
API:  deliver(out_dir, to=None, home=None, what="out") -> [paths], destination(to=None, home=None) -> folder
"""
import argparse
import json
import os
import re
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.dirname(_HERE)
CANDIDATES = ("Desktop", "Downloads")


def _writable(folder):
    """True when a file can really be created in `folder` — a probe write, because macOS privacy controls can refuse
    a write that `os.access` reports as allowed."""
    if not os.path.isdir(folder):
        return False
    probe = os.path.join(folder, ".topic-to-video-probe-%d" % os.getpid())
    try:
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def _not_for_the_user(folder, home):
    """A folder the user does not browse: this skill's own tree, or anything under ~/.claude."""
    real = os.path.realpath(folder)
    for root in (os.path.realpath(_SKILL), os.path.realpath(os.path.join(home, ".claude"))):
        if real == root or real.startswith(root + os.sep):
            return True
    return False


def destination(to=None, home=None):
    """The folder the video goes to: `to` when given, else ~/Desktop, else ~/Downloads."""
    home = home or os.path.expanduser("~")
    if to:
        folder = os.path.abspath(os.path.expanduser(to))
        if _not_for_the_user(folder, home):
            raise SystemExit("deliver: %s is inside this skill or ~/.claude, where the user does not look — "
                             "choose a folder they browse (Desktop, Downloads)" % folder)
        if not _writable(folder):
            raise SystemExit("deliver: %s cannot be written" % folder)
        return folder
    tried = []
    for name in CANDIDATES:
        folder = os.path.join(home, name)
        if _writable(folder):
            return folder
        tried.append(folder)
    raise SystemExit("deliver: neither %s can be written (macOS may have withdrawn this process's access) — "
                     "ask the user for a folder and pass --to <folder>" % " nor ".join(tried))


def film_name(out_dir):
    """`meta.title` when the board has one, else the out_dir's own name — made safe for a file name."""
    title = None
    try:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            title = (json.load(fh).get("meta") or {}).get("title")
    except (OSError, ValueError, AttributeError):
        title = None
    name = title if isinstance(title, str) and title.strip() else os.path.basename(os.path.abspath(out_dir))
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", name).strip() or "video"
    return name[:80]


def _free(path):
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path = "%s (%d)%s" % (base, n, ext)
        n += 1
    return path


WHAT = ("out", "sample", "preview")


def deliver(out_dir, to=None, home=None, what="out"):
    """Copy <what>.mp4 (and its .srt) to the user's folder; return the delivered paths, the video first."""
    if what not in WHAT:
        raise SystemExit("deliver: --what must be one of %s, got %r" % (", ".join(WHAT), what))
    src = os.path.join(out_dir, what + ".mp4")
    if not os.path.isfile(src):
        hint = "render the film first" if what == "out" else "render the %s first" % what
        raise SystemExit("deliver: %s has no %s.mp4 — %s" % (out_dir, what, hint))
    folder = destination(to, home)
    name = film_name(out_dir) + ("" if what == "out" else " - " + what)
    video = _free(os.path.join(folder, name + ".mp4"))
    shutil.copy2(src, video)
    delivered = [video]
    srt = os.path.join(out_dir, what + ".srt")
    if os.path.isfile(srt):
        captions = os.path.splitext(video)[0] + ".srt"
        shutil.copy2(srt, captions)
        delivered.append(captions)
    # a portrait film's 3:4 feed card (scripts/cover.py), beside the film under the same name
    cover = os.path.join(out_dir, "out.cover.png")
    if what == "out" and os.path.isfile(cover):
        card = os.path.splitext(video)[0] + " - cover.png"
        shutil.copy2(cover, card)
        delivered.append(card)
    return delivered


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--to", help="a folder the user browses (default: ~/Desktop, else ~/Downloads)")
    ap.add_argument("--what", default="out", choices=WHAT,
                    help="which render: the film (out, default), the step-8 sample, or the html preview")
    a = ap.parse_args(argv)
    paths = deliver(a.out_dir, a.to, what=a.what)
    for p in paths:
        print("[deliver] %s" % p)
    print("[deliver] hand the user this path; to open it: open %s" % _quote(paths[0]))
    return 0


def _quote(path):
    return "'%s'" % path.replace("'", "'\\''")


if __name__ == "__main__":
    sys.exit(main())
