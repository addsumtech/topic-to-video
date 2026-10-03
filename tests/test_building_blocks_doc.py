"""references/building-blocks.md covers EVERY runtime module a film's code can import — by the module's own name,
naming exports that really exist — because half of them used to be discoverable only from their source headers."""
import glob
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(_ROOT, "remotion", "src", "runtime")
DOC = os.path.join(_ROOT, "references", "building-blocks.md")


def _modules():
    """{module: its exports} — code modules by name, data files (deviceSpec.json) by file name and top-level keys."""
    import json
    out = {}
    for p in sorted(glob.glob(os.path.join(RUNTIME, "*.ts")) + glob.glob(os.path.join(RUNTIME, "*.tsx"))):
        name = os.path.basename(p).rsplit(".", 1)[0]
        if name.startswith("__probe"):
            continue
        out[name] = set(re.findall(r"^export (?:const|function|type) ([A-Za-z_]\w*)", open(p, encoding="utf-8").read(), re.M))
    for p in sorted(glob.glob(os.path.join(RUNTIME, "*.json"))):
        out[os.path.basename(p)] = set(json.load(open(p, encoding="utf-8")))
    return out


def _sections():
    doc = open(DOC, encoding="utf-8").read().split("## Recipes", 1)[0]     # the recipes name many modules on purpose
    parts = re.split(r"^### `([\w.]+)`\s*$", doc, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_every_runtime_module_has_a_section():
    missing = sorted(set(_modules()) - set(_sections()))
    assert not missing, "runtime modules the builder cannot read about: %s" % missing


def test_every_section_names_exports_that_exist():
    mods, secs = _modules(), _sections()
    bad = {}
    for name, body in secs.items():
        if name not in mods:
            bad[name] = "no such runtime module"
            continue
        named = set(re.findall(r"`(\w+)`", body))
        if not (named & mods[name]):
            bad[name] = "names none of its exports (%s)" % ", ".join(sorted(mods[name])[:8])
        ghosts = sorted(n for n in named - mods[name] if re.match(r"^[a-z][A-Za-z0-9]+$|^[A-Z][A-Z0-9_]+$", n)
                        and n in {e for m in mods.values() for e in m} and n not in mods[name])
        if ghosts:
            bad[name] = "names exports of OTHER modules as its own: %s" % ghosts
    assert not bad, bad


def test_the_recipes_the_films_keep_needing_are_written():
    doc = open(DOC, encoding="utf-8").read()
    recipes = doc.split("## Recipes", 1)[1]
    for r in ("A mechanism in cutaway", "Liquid or particles along a path", "A turntable", "Layered strata",
              "A route on a map", "An interface being operated"):
        assert "### " + r in recipes, r
