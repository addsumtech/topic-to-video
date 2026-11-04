"""A register's demo copy names no real product.

A register's defaults are what a film shows on any prop it leaves empty, and what the library's stills, sweeps and
contest samples show. The library review (2026-11-03) found real products standing in as sample words — MapRoutes'
spokes were GitHub, Slack, Notion, Drive, Jira and Gmail, KnowledgeGraph had Slack among its nodes, and 29 registers
carried another film's product name (0c9a7eb). On a film that leaves the prop empty that is a claim about someone
else's product ("integrates with Jira"), which is exactly the invented fact the skill refuses. So the source of every
register is read for product names in its string literals. Comments are skipped: a register may explain where a
measure came from.
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")

PRODUCTS = ["GitHub", "GitLab", "Slack", "Notion", "Jira", "Gmail", "Google Drive", "Figma", "Discord", "Dropbox",
            "Trello", "Asana", "Salesforce", "Shopify", "Stripe", "OpenAI", "ChatGPT", "Claude", "Anthropic", "Gemini",
            "Copilot", "WorkBuddy", "Codex", "Sora", "Raycast", "Netflix", "Spotify", "Zoom", "Airtable", "HubSpot",
            "Zapier", "Linear", "Vercel", "Outlook", "Excel", "Hermes"]
# names no ordinary word shares are matched in any case (a command types them lower-case: `hermes --mode`); the rest
# ("Linear", "Zoom", "Excel", "Notion", "Sora", "Stripe") only as the product spells itself, or `linear` easing and a
# camera `zoom` would read as products
_ANY_CASE = {"GitHub", "GitLab", "Slack", "Jira", "Gmail", "Figma", "Discord", "Dropbox", "Trello", "Asana", "Salesforce",
             "Shopify", "OpenAI", "ChatGPT", "Anthropic", "Copilot", "WorkBuddy", "Raycast", "Netflix", "Spotify",
             "Airtable", "HubSpot", "Zapier", "Vercel", "Hermes", "Codex"}
_PRODUCT = re.compile(r"\b(%s|(?i:%s))\b" % ("|".join(re.escape(p) for p in PRODUCTS if p not in _ANY_CASE),
                                             "|".join(re.escape(p) for p in sorted(_ANY_CASE))))
# a font stack names a typeface family, not a product claim ("Microsoft YaHei")
_STRING = re.compile(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"|`([^`]*)`")


def _code(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(ln.split("//")[0] if "//" in ln and "://" not in ln else ln for ln in src.splitlines())


def test_no_register_default_names_a_real_product():
    bad = []
    for f in sorted(os.listdir(SHOTS)):
        if not f.endswith(".tsx"):
            continue
        code = _code(open(os.path.join(SHOTS, f), encoding="utf-8").read())
        for m in _STRING.finditer(code):
            s = next(g for g in m.groups() if g is not None)
            hit = _PRODUCT.search(s)
            if hit:
                bad.append("%s: %r" % (f[:-4], s[:60]))
    assert not bad, "register copy that names a real product:\n  " + "\n  ".join(bad)


def test_the_scan_sees_a_product_in_a_list_and_not_in_a_comment():
    assert _PRODUCT.search("hermes --mode hybrid") and not _PRODUCT.search("ease: 'linear', zoom: 1.2")
    code = _code("const A = ['Docs', 'Slack'];\n// measured against Slack's own layout\n")
    hits = [m for m in _STRING.finditer(code) if _PRODUCT.search(next(g for g in m.groups() if g is not None))]
    assert len(hits) == 1


def test_a_card_describes_the_defaults_its_register_has():
    """The cards' Known traps told the director what an omitted prop prints — `WorkBuddy` on thirteen of them — and
    went on saying it after the defaults were made neutral, so a director reading a card was warned off a product name
    no longer there and not told what prints instead. A product name in a card must be in its register's code."""
    cards = os.path.join(_ROOT, "remotion", "cards")
    bad = []
    for f in sorted(os.listdir(cards)):
        reg = os.path.join(SHOTS, f[:-3] + ".tsx")
        if not f.endswith(".md") or not os.path.exists(reg):
            continue
        code = _code(open(reg, encoding="utf-8").read())
        for name in sorted(set(_PRODUCT.findall(open(os.path.join(cards, f), encoding="utf-8").read()))):
            if not re.search(r"(?i)\b%s\b" % re.escape(name), code):
                bad.append("%s names %s" % (f, name))
    assert not bad, "cards describing defaults their register no longer has: %r" % bad
