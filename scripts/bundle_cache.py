"""ONE Remotion bundle per film state, shared by the render and every census gate.

`npx remotion bundle` took 25 s (measured 2026-11-05), and a delivery bundled the same project again for the render,
the sync census, and each census gate (text_safe_qa x3, media_res_qa, plate_qa, craft_qa, fidelity): the same
bytes, built over and over. A bundle is a pure function of its inputs, so it is kept under the key of everything
it is built from and handed back while that key holds:

  · every file of remotion/ outside node_modules (by content; files over 1 MB by size and mtime);
  · the skill's assets/ the library imports (fonts; by size and mtime);
  · the film's workshop (SLIDES_WORKSHOP, by content) — its shots and plates.ts;
  · the public folder it is given (by name, size and mtime: minimal_public LINKS files, so a film's media keep theirs);
  · the installed packages (node_modules/.package-lock.json), the SLIDES_*/REMOTION_* environment and the arguments.

`TTV_BUNDLE_CACHE=off` builds every bundle afresh (as before); `TTV_BUNDLE_CACHE=<dir>` moves the cache."""
import hashlib
import os
import shutil
import subprocess
import tempfile

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPTS)
REMOTION = os.path.join(SKILL_ROOT, "remotion")
KEEP = 8                    # bundles kept; the oldest go first
BIG = 1 << 20


def cache_root():
    v = os.environ.get("TTV_BUNDLE_CACHE", "")
    if v.lower() == "off":
        return None
    return v or os.path.join(os.path.expanduser("~"), ".cache", "topic-to-video", "bundles")


def _tree(h, root, by_content=True, skip=("node_modules",)):
    if not root or not os.path.isdir(root):
        h.update(b"<none>\0")
        return
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in skip and not x.startswith("."))
        for f in sorted(files):
            if f.startswith(".") and f != ".package-lock.json":
                continue
            p = os.path.join(d, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            h.update(os.path.relpath(p, root).encode("utf-8") + b"\0")
            if by_content and st.st_size <= BIG:
                with open(p, "rb") as fh:
                    h.update(hashlib.sha256(fh.read()).digest())
            else:
                h.update(("%d:%d" % (st.st_size, st.st_mtime_ns)).encode())


def key(public_dir, env, args):
    env = env if env is not None else os.environ
    h = hashlib.sha256()
    for part, root, content in (("remotion", REMOTION, True), ("assets", os.path.join(SKILL_ROOT, "assets"), False),
                                ("workshop", env.get("SLIDES_WORKSHOP"), True),
                                ("public", public_dir or os.path.join(REMOTION, "public"), False)):
        h.update(part.encode() + b"\0")
        _tree(h, root, content)
    lock = os.path.join(REMOTION, "node_modules", ".package-lock.json")
    h.update(open(lock, "rb").read() if os.path.isfile(lock) else b"<no lock>")
    for k in sorted(k for k in env if k.startswith(("SLIDES_", "REMOTION_"))):
        h.update(("%s=%s\0" % (k, env[k])).encode())
    # the public folder's PATH is a temp dir of each caller: its contents are keyed above, its name must not be
    h.update("\0".join(a for a in args if not a.startswith("--public-dir=")).encode())
    h.update(b"public-dir" if public_dir else b"default-public")
    return h.hexdigest()


def bundle(public_dir=None, env=None, extra=(), run=subprocess.run):
    """The path of a Remotion bundle of the project (with the film's workshop when `env` carries SLIDES_WORKSHOP and
    `public_dir` as its public folder). Built once per key; a failed build raises and leaves nothing behind."""
    args = ["src/index.ts", "--log=error"] + (["--public-dir=" + os.path.abspath(public_dir)] if public_dir else []) \
        + list(extra)
    root = cache_root()
    k = key(public_dir, env, args) if root else None
    final = os.path.join(root, k[:24]) if root else None
    if final and os.path.isfile(os.path.join(final, "index.html")):
        os.utime(final)
        return final
    base = root or tempfile.gettempdir()
    os.makedirs(base, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=".building-", dir=base)
    kw = {"env": env} if env is not None else {}
    r = run(["npx", "remotion", "bundle", *args[:1], "--out-dir=" + tmp, *args[1:]], cwd=REMOTION,
            capture_output=True, text=True, **kw)
    if getattr(r, "returncode", 0) != 0 or not os.path.isfile(os.path.join(tmp, "index.html")):
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError("remotion bundle failed: %s" % (((r.stdout or "") + (r.stderr or ""))[-600:]))
    if not final:
        return tmp
    try:
        os.rename(tmp, final)
    except OSError:                       # another process built the same key first: theirs is the same bundle
        shutil.rmtree(tmp, ignore_errors=True)
    _evict(root)
    return final


def _evict(root):
    try:
        ds = [os.path.join(root, d) for d in os.listdir(root) if not d.startswith(".")]
    except OSError:
        return
    ds.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for d in ds[KEEP:]:
        shutil.rmtree(d, ignore_errors=True)
