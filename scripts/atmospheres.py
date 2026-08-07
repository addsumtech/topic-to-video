"""ATMOSPHERE library + topic routing for the cinematic tier.

An ATMOSPHERE is a whole-film WORLD — not a colour re-skin. Each one bundles a RENDER SUBSTRATE that reaches
the actual pixels: a base `style` (drives the material/mood/grade recipes the render already binds), a
`materialClass` (`standard` lit PBR vs `toon` cel-shaded), a `post` profile (`film` grade+grain / `crt`
scanlines+phosphor / `clean` crisp product), a `camera` grammar and a `motion` cadence. So picking the
"terminal" atmosphere makes the render terminal — CRT scanlines over emissive phosphor forms — while "cartoon"
makes it cel-shaded, which "just a different palette" never could.

This module is the CONTEST CANDIDATE GENERATOR the director was told to pull from: `route(topic)` scores the
library against the topic and returns the best ~3 atmosphere keys to offer the user (a real topic→best-3
contest, like the HTML tier). `profile(key)` returns the render bundle build_props threads into the props.

Extending the tier = adding ONE entry here; routing + the contest pick it up automatically. Only `materialClass`
and `post` need matching render code (ThreeScene/Finish); everything else reuses the style/mood/grade axes.
"""

# key -> {name, pitch, topics(routing keywords), render bundle}. `style` is a theme.py style key (one of the
# 18); `materialClass` in {standard, toon}; `post` in {film, crt, clean}; camera/motion are stored for the
# motion-grammar pass (not all wired yet — see the render bridge). 3 SEED atmospheres (terminal/cartoon/app)
# are fully render-distinct today; the rest route now and deepen as the render axes grow.
ATMOSPHERES = {
    "terminal": {
        "name": "Mainframe", "pitch": "A CRT terminal you step inside — scanlines, phosphor, streaming glyphs.",
        "topics": ["cli", "command", "terminal", "shell", "dev", "developer", "api", "sdk", "infra",
                   "infrastructure", "agent", "framework", "code", "coding", "backend", "devops", "kubernetes",
                   "compiler", "database", "server", "protocol"],
        "render": {"style": "terminal", "materialClass": "standard", "post": "crt", "camera": "punch", "motion": "boot"},
    },
    "app": {
        "name": "Device", "pitch": "A clean product world — a device volume with UI cards floating at real depth.",
        "topics": ["app", "saas", "product", "mobile", "ios", "android", "ui", "ux", "dashboard", "platform",
                   "web", "startup", "tool", "software", "subscription", "onboarding", "feature", "interface"],
        "render": {"style": "glassmorphism", "materialClass": "standard", "post": "clean", "camera": "turntable", "motion": "snap"},
    },
    "cartoon": {
        "name": "Storybook", "pitch": "Cel-shaded, ink-outlined, bouncy — a friendly hand-illustrated world.",
        "topics": ["kids", "children", "education", "learn", "learning", "explainer", "fun", "playful", "story",
                   "storytelling", "game", "onboarding", "tutorial", "simple", "friendly", "beginner", "guide"],
        "render": {"style": "manga", "materialClass": "toon", "post": "film", "camera": "whip", "motion": "bouncy"},
    },
    "blueprint": {
        "name": "Schematic", "pitch": "Drafting-table world — wireframe to metal, engineered and exact.",
        "topics": ["hardware", "engineering", "mechanical", "robotics", "chip", "gpu", "semiconductor", "device",
                   "architecture", "system", "spec", "industrial", "manufacturing", "aerospace", "sensor", "circuit"],
        "render": {"style": "blueprint", "materialClass": "standard", "post": "clean", "camera": "dolly", "motion": "smooth"},
    },
    "hologram": {
        "name": "Holo-HUD", "pitch": "A futuristic HUD locks onto the subject — reticles, scan lines, volumetric glow.",
        "topics": ["ai", "ml", "machine learning", "model", "neural", "deep learning", "data", "science",
                   "futuristic", "sci-fi", "quantum", "embeddings", "llm", "reasoning", "vision", "autonomous"],
        "render": {"style": "cyberpunk", "materialClass": "standard", "post": "crt", "camera": "punch", "motion": "boot"},
    },
    "clay": {
        "name": "Soft Clay", "pitch": "Matte, squishy, tactile 3D — warm and approachable.",
        "topics": ["wellness", "health", "consumer", "friendly", "fintech", "banking", "savings", "community",
                   "social", "lifestyle", "habit", "care", "family", "personal"],
        "render": {"style": "claymorphism", "materialClass": "toon", "post": "clean", "camera": "dolly", "motion": "bouncy"},
    },
    "noir": {
        "name": "Rakelight", "pitch": "Void, then a blade of light reveals it — obsidian, gravity, prestige.",
        "topics": ["luxury", "premium", "security", "privacy", "enterprise", "brand", "exclusive", "high-end",
                   "confidential", "defense", "compliance", "trust"],
        "render": {"style": "noir", "materialClass": "standard", "post": "film", "camera": "dolly", "motion": "smooth"},
    },
    "diorama": {
        "name": "Diorama", "pitch": "A tiny tabletop world seen from above — process and place in miniature.",
        "topics": ["logistics", "supply", "supply chain", "process", "pipeline", "workflow", "city", "map",
                   "operations", "network", "flow", "journey", "route", "delivery", "warehouse"],
        "render": {"style": "swiss", "materialClass": "standard", "post": "clean", "camera": "turntable", "motion": "snap"},
    },
    "papercut": {
        "name": "Paper-cut", "pitch": "Layered paper at real depth — craft, story, warmth.",
        "topics": ["culture", "craft", "heritage", "art", "design", "editorial", "magazine", "publishing",
                   "nonprofit", "museum", "book", "narrative", "history"],
        "render": {"style": "risograph", "materialClass": "toon", "post": "film", "camera": "dolly", "motion": "smooth"},
    },
    "vaporwave": {
        "name": "Neon Arcade", "pitch": "Glowing grid, chrome, retro-future haze — high-energy and loud.",
        "topics": ["crypto", "web3", "blockchain", "nft", "gaming", "retro", "music", "entertainment",
                   "metaverse", "defi", "token", "streaming", "creator"],
        "render": {"style": "vaporwave", "materialClass": "standard", "post": "crt", "camera": "whip", "motion": "bouncy"},
    },
    "chalkboard": {
        "name": "Field Notebook", "pitch": "Hand-drawn on dark slate — teaching, theory, working it out.",
        "topics": ["math", "mathematics", "teaching", "academic", "university", "course", "lecture", "physics",
                   "theory", "algorithm", "proof", "research", "study", "concept", "formula"],
        "render": {"style": "editorial", "materialClass": "standard", "post": "film", "camera": "dolly", "motion": "smooth"},
    },
    "molten": {
        "name": "Molten Ledger", "pitch": "Numbers cast in metal — magnitude as a physical, weighty thing.",
        "topics": ["finance", "money", "revenue", "markets", "trading", "wealth", "gold", "economy", "valuation",
                   "profit", "growth", "capital", "investment", "returns", "fund"],
        # artdeco base = warm GOLD-metal (distinct from noir's cool steel) so molten never clones noir.
        "render": {"style": "artdeco", "materialClass": "standard", "post": "film", "camera": "dolly", "motion": "smooth"},
    },
}

_MATERIAL_CLASSES = ("standard", "toon")
_POST_PROFILES = ("film", "crt", "clean")
# fallback priority when a topic matches < 3 atmospheres — a broad, safe spread so the contest always offers 3.
_FALLBACK_ORDER = ["app", "terminal", "hologram", "noir", "cartoon", "diorama", "blueprint", "molten",
                   "clay", "chalkboard", "papercut", "vaporwave"]


def keys():
    return list(ATMOSPHERES.keys())


def profile(key):
    """The render bundle for an atmosphere key, or None if unknown."""
    a = ATMOSPHERES.get(str(key or "").lower())
    return dict(a["render"]) if a else None


def route(topic, n=3):
    """Score the library against a free-text TOPIC and return the best `n` atmosphere keys (the contest
    candidates). Deterministic: score = count of the atmosphere's keywords found as substrings in the topic;
    ties break by the fixed _FALLBACK_ORDER. Always returns `n` distinct keys (pads from the fallback order),
    so the director always has a full contest to offer — no topic can leave it short."""
    t = " " + str(topic or "").lower() + " "
    prio = {k: i for i, k in enumerate(_FALLBACK_ORDER)}
    scored = []
    for key, a in ATMOSPHERES.items():
        score = sum(1 for kw in a["topics"] if kw in t)
        scored.append((key, score))
    # highest score first; among equal scores, the fallback-priority order (stable, deterministic)
    scored.sort(key=lambda kv: (-kv[1], prio.get(kv[0], 999)))
    picked = [k for k, s in scored if s > 0][:n]
    for k in _FALLBACK_ORDER:                      # pad to n with distinct fallbacks if the topic was thin
        if len(picked) >= n:
            break
        if k not in picked:
            picked.append(k)
    return picked[:n]
