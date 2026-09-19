"""No register draws a claim the film did not make — `scripts/content_contract_qa.py` over the whole library.

THE INCIDENT. A delivered frame labelled six cells with anime characters, and each cell carried a sparkline,
a gauge or a bar chart: `BentoReveal` picked the widget by the cell's INDEX, made the heights up from the index
and the clock, and cycled the labels to fill six slots. A picture beside a film's label is a claim about that
label. A read of all 168 registers afterwards found the same class in about sixty, in six syntactic shapes,
and every gate in the repo had been green on all of them.

The fixtures below are the ORIGINAL lines those registers shipped, copied from the source before the repair,
so a checker that stops recognising one of them fails here rather than on the next delivered film.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import content_contract_qa as cc  # noqa: E402


def _rules(src):
    return sorted({rule for _, rule, _ in cc.violations(src)})


# (register, the line it shipped, the rule that must catch it)
SHIPPED = [
    ("BentoReveal", "<Widget t={t} kind={(i - 1) % 6} c={tone} g={g} />", "cycle"),
    ("BentoReveal", "const ITEMS = props.items;\n<div>{ITEMS[(i - 1) % ITEMS.length]}</div>", "cycle"),
    ("DataOrrery", "const labels = items;\nconst RINGS = RING_GEOM.map((r, i) => ({...r, label: labels[i % labels.length]}));",
     "cycle"),
    ("QuadSplit", "const INDEX_GLYPHS = ['bars', 'ring', 'dots', 'wave'];\n"
                  "if (!name) return INDEX_GLYPHS[i % INDEX_GLYPHS.length];", "cycle"),
    ("PhysicsStack", "const DEFAULT_BARS = [{h: 220, c: '#4c8dff', label: 'Mon'}];\n"
                     "const BARS = DEFAULT_BARS.map((b, i) => ({...b, label: items[i]}));", "relabel"),
    ("LiquidGlass", "const done = settled > 0.5 && i === 3;", "position"),
    ("BlockAssembly", "<div style={{background: k < 2 ? GOOD : SURF}} />", "position"),
    ("uiSurface", "background: i % 3 === 0 ? accent : dim,", "position"),
    ("KineticManifesto", "const HERO = 2; // which phrase pops in the accent colour", "position"),
    ("FocalIsolation", "const focal = 4; // centre item", "position"),
    ("EdStat", "const num = sign * (parseFloat(raw.replace(/[^\\d.]/g, '')) || 0);", "retype"),
    ("GaugeCluster", "const num = Math.round(parseFloat(String(VALUE)) * heroFill);", "retype"),
    ("GaugeCluster", "fill={easeOutExpo(seg(t, 0.12, 0.5)) * (SATS[0]?.fill ?? 0.6)}", "fallback"),
    ("PhotoPlate", "const mx = px0 + clamp01(m.x ?? 0.5) * PW;", "fallback"),
    ("DataMonolith", "const hFrac = 0.4 + hash01(i * 4.7) * 0.6;", "invent"),
    ("ChartLive", "const DATA = [0.28, 0.34, 0.30, 0.44, 0.52, 0.48, 0.62, 0.7];", "invent"),
    ("KnowledgeGraph", "{[[0, 1], [1, 5], [2, 3], [4, 6], [5, 6]].map(([a, b], k) => {", "invent"),
    ("CollaborativeCursors", "const kinds: Kind[] = ['chart', 'chart', 'slide', 'doc', 'doc', 'table'];", "invent"),
]


def test_every_shape_the_library_shipped_is_caught():
    missed = [(reg, line, rule) for reg, line, rule in SHIPPED if rule not in _rules(line)]
    assert not missed, "the checker no longer recognises a shape a register actually shipped: %r" % missed


def test_style_is_not_a_claim():
    """A palette or a font stack cycled by index, alternation, a 2x2 position grid and `i === 0` are honest."""
    clean = [
        "const TONES = dnaPalette(dna, 5) ?? TONES0;\nconst tone = TONES[i % TONES.length];",
        "const POP = ['#ff5a5f', '#ffd23f', '#3ec1d3'];\nconst col = POP[(i + 2) % POP.length];",
        "const FONTS = ['Impact, sans-serif', 'Georgia, serif'];\nconst f = FONTS[i % FONTS.length];",
        "const up = i % 2 === 0;",
        "{[[0, 0], [1, 0], [0, 1], [1, 1]].map(([hx, hy], k) => null)}",
        "const hero = i === 0;",
        "const p1 = pts[(i + 1) % N];",
    ]
    for src in clean:
        assert not cc.violations(src), (src, cc.violations(src))


def test_a_declaration_needs_its_reason():
    """`// @positional:` with nothing after it is a lint-dodge, not a decision; it must not silence the rule."""
    line = "const done = settled > 0.5 && i === 3;"
    assert _rules("// @positional:\n" + line) == ["position"]
    assert _rules("// @positional:   \n" + line) == ["position"]
    assert _rules("// @positional: the fourth step is the register's fixed payoff\n" + line) == []
    # and the declaration must name the RIGHT rule
    assert _rules("// @decor: texture\n" + line) == ["position"]


def test_the_library_honours_the_content_contract():
    """Every register and `runtime/uiSurface`: no flagged shape without a reasoned declaration."""
    found = cc.library()
    report = "\n".join("%s:%d [%s] %s" % (n, ln, rule, text[:120])
                       for n, vs in sorted(found.items()) for ln, rule, text in vs)
    assert not found, ("registers draw something the film did not supply — fix it from props, or declare why it "
                       "is not a claim (`// @positional:` / `@cycles:` / `@fallback:` / `@decor:` + reason):\n"
                       + report)
