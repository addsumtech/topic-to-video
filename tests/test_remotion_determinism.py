"""ONE repo-wide determinism guard for the whole Remotion TS. Everything must render as a pure function of
useCurrentFrame() — a wall-clock or per-call source (RNG, timers, real-time animation) renders frozen or
non-deterministically under Remotion's off-thread frame-by-frame capture. This replaces the scattered
per-file two-token greps with a single sweep over the full forbidden set + all of remotion/src."""
import glob
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# match CALLS (a trailing paren) so a comment MENTIONING the token as "don't use this" is fine.
_FORBIDDEN = [
    r"Math\.random\s*\(", r"Date\.now\s*\(", r"new Date\s*\(", r"performance\.now\s*\(",
    r"requestAnimationFrame\s*\(", r"\bsetTimeout\s*\(", r"\bsetInterval\s*\(", r"crypto\.getRandomValues\s*\(",
]


def _strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)   # block comments
    src = re.sub(r"//.*", "", src)                     # line comments (so a "don't use Math.random()" note is fine)
    return src


def test_no_nondeterministic_sources_anywhere_in_remotion_src():
    bad = []
    for f in glob.glob(os.path.join(_SKILL, "remotion", "src", "**", "*.ts*"), recursive=True):
        src = _strip_comments(open(f, encoding="utf-8").read())
        for pat in _FORBIDDEN:
            if re.search(pat, src):
                bad.append("%s :: %s" % (os.path.relpath(f, _SKILL), pat))
    assert not bad, "non-deterministic source in Remotion TS (must be a pure fn of useCurrentFrame): %s" % bad
