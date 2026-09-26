"""Run a TypeScript snippet against the REAL runtime modules in node (esbuild bundle); return its JSON.

The snippet assigns into `out`; this returns it. Pure functions only — nothing here renders a frame."""
import json
import os
import shutil
import subprocess
import tempfile

_REM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
RUNTIME = os.path.join(_REM, "src", "runtime")


def available():
    return bool(shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules")))


def mod(name):
    return json.dumps(os.path.join(RUNTIME, name))


def run_ts(imports, body):
    tmp = tempfile.mkdtemp(prefix="tsprobe_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.tsx")
        with open(entry, "w", encoding="utf-8") as fh:
            fh.write(imports + "\nconst out: any = {};\n" + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)