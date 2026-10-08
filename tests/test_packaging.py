"""The skill ships as a plain clone, through `npx skills add`, and as a Claude Code plugin. The two plugin
manifests must agree with each other and with SKILL.md, or a plugin install registers a skill under the wrong
name or at a version the marketplace never offered."""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _json(name):
    with open(os.path.join(_ROOT, ".claude-plugin", name), encoding="utf-8") as f:
        return json.load(f)


def _skill_name():
    with open(os.path.join(_ROOT, "SKILL.md"), encoding="utf-8") as f:
        head = f.read().split("---")[1]
    return next(l.split(":", 1)[1].strip() for l in head.splitlines() if l.startswith("name:"))


def test_plugin_and_marketplace_agree_with_the_skill():
    plugin, market = _json("plugin.json"), _json("marketplace.json")
    entry = market["plugins"][0]
    assert plugin["name"] == entry["name"] == market["name"] == _skill_name() == "topic-to-video"
    assert plugin["version"] == entry["version"] == market["metadata"]["version"]
    assert entry["source"] == "./"                      # the repo root IS the skill
    assert os.path.exists(os.path.join(_ROOT, "SKILL.md"))
    assert plugin["repository"] == entry["repository"] == "https://github.com/addsumtech/topic-to-video"


def test_version_is_semver():
    parts = _json("plugin.json")["version"].split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)
