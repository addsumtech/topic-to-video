# Visual-style catalog — the deck's named aesthetic register

A **style is a rendering TREATMENT of the atmosphere, never the data.** The design-director picks ONE named
style per deck (smart contest below), sets `meta.visual_style` + `theme.style` (a key here) and, on AI tiers,
`meta.style_preamble`. It threads everywhere automatically: `imagegen._apply_style` prepends the preamble to
EVERY generated prompt (sandwiched **subject → style → hard faithfulness tail**, so it can never leak into the
facts); `theme.py --style <key>` seeds the palette + emits style-hint vars for the flat/HTML tiers; the WCAG
floors still run after, so a style can never make an unreadable palette. **No style ⇒ exactly today's flat
look** (backward-compatible). Data-forms (charts/timelines/stats) stay in the semantic color ledger and are
never distorted. Litmus: hide the text — a viewer must still tell what the video is ABOUT (style OF the subject,
not generic style decoration).

> **Hex below is ILLUSTRATIVE.** When you AUTHOR a page, use the semantic theme vars — `var(--accent)`,
> `var(--fg)`, `var(--border-ink)`, `var(--radius)`, `var(--border-weight)` — never a raw `#hex` in a
> `style=`/SVG-`fill`/`<style>` (validate lints it, the critic REVISEs it). Most of the style's DNA (palette,
> corner radius, border weight, headline face, grid density) is already baked into `theme.css` by
> `theme.py --style <key>` and auto-applied by base.css/motifs.css — you rarely need inline color at all.

## Smart selection (a ranked contest, not a reflex)

STYLE-REGISTER SELECTION — a ranked contest, not a reflex. Drop-in replacement for the design-director's style_thesis authoring. The director already knows topic + brief + tone, so the SMART pick happens here. It widens the existing style_thesis vocabulary (blueprint/field-notebook/editorial/terminal/cartographic/specimen) to the full named-style catalog in references/visual-styles.md and crowns ONE the deck's register.

OUTPUT: an enriched style_thesis = { named_style (a catalog key, or "custom"+DNA), why (fit to THIS subject), rejected_style (nearest rival + the ONE separating clause), dna{palette_bias, type_treatment, texture/linework, composition_bias, motion_feel}, style_clause (the reusable prompt fragment), theme_bias{mode, accent_family}, tier_realization }. Mirror named_style into the top-level theme.style and meta.visual_style; on AI tiers also author meta.style_preamble (the catalog prompt_fragment adapted to this subject + palette accents).

STEP 0 — HONOR EXPLICIT INPUT FIRST. If the interview Batch-3 "Art style" set meta.visual_style (or a free-text brief → "custom"), or slide frames/ carry a brand palette (theme.from_frames), that is a HARD constraint: the named style wins outright (skip the contest) and the brand palette pins theme.py's mode/accent family. EXCEPTION: if an explicit/branded style collides with a somber-stakes topic (Step 3 veto), do NOT silently render — surface it via AskUserQuestion (selectable options, per user memory) offering the restrained alternative.

STEP 1 — READ FIVE SIGNALS off artifacts already in the pipeline into a profile (domain, content-shape, audience-formality, purpose-temperature, brand-cue): (a) DOMAIN from brief.thesis / motif; (b) CONTENT-SHAPE = data-dense (charts/benchmarks/KPIs, from the beat mix + per-beat visual_intent + rhythm_map density) vs narrative/emotional; (c) AUDIENCE-FORMALITY from director_note.audience; (d) PURPOSE-TEMPERATURE from meta.arc_kind + director_note.tone (explainer/tutorial · pitch · launch/hype · survey/reference · somber report); (e) BRAND-CUE (frames palette / stated brand / free-text).

STEP 2 — SHORTLIST 2–3 candidates from the domain map (below), then apply the guardrail VETOES to drop any candidate whose emotional temperature or legibility profile fights the profile. What survives is the contest field.

STEP 3 — SCORE each survivor on four axes, CROWN A WINNER, and NAME THE NEAREST REJECTED RIVAL with the one clause that separates them (mirrors the skill's existing rejected_default discipline — a contest, never a strawman): (1) DOMAIN FIT — cultural association matches the subject (blueprint↔engineering, art-deco↔luxury, riso↔indie/craft, noir↔investigation, terminal↔code/data); (2) CONTENT-SHAPE FIT — a data-dense deck needs a high-legibility SPINE (Swiss, editorial, bauhaus, blueprint, terminal), NEVER a low-contrast/high-texture spine (watercolor, vaporwave, heavy riso) that fights charts; an emotional/narrative deck can carry an expressive register (noir, watercolor, cinematic, manga); (3) AUDIENCE-FORMALITY FIT — exec/clinical/legal → restrained; youth/consumer/creative → expressive; (4) TEMPERATURE FIT — aspirational vs diagnostic vs somber vs playful. Winner = highest total. Emit e.g. "editorial beats Swiss because the content is long-form narrative with pull-quotes, not a systematic data-grid — Swiss would starve the story of warmth."

STEP 4 — DELIVERABILITY + FAITHFULNESS GATE the winner. If its DNA can't land in the tiers in play (glassmorphism/claymorphism need real blur/3D — thin in the FLAT CSS tier; theme.py's ≥7:1 fg and ≥3:1 accent contrast floors will veto a low-contrast palette), either down-rank to a deliverable rival OR confine the style to the AI tier and pick a contrast-safe palette/type bias for the flat parts. Record this as tier_realization.

STEP 5 — EMIT the enriched style_thesis, set theme.style = meta.visual_style, and (AI tiers) author meta.style_preamble. ONE named_style per deck (coherence), realized AT MINIMUM on the theme + the signature beat + the hero/opener.

GUARDRAIL VETOES (a style must never fight the content):
• SOMBER/SENSITIVE — death, disease, disaster, layoffs, war, safety-critical medicine forbid playful/ironic/retro-pop (manga, memphis, vaporwave, claymorphism, pop-cyberpunk); default editorial/Swiss/blueprint/noir.
• ENTERPRISE/TRUST — finance, enterprise, legal, gov, healthcare-B2B forbid vaporwave, cyberpunk-neon, memphis, brutalism-for-clients.
• DATA-DENSITY — a chart/benchmark deck forbids a busy/low-contrast SPINE (watercolor washes, vaporwave grids, riso grain under a chart); such treatments live only as behind-glass backgrounds.
• KIDS/PLAYFUL — welcomes risograph, claymorphism, friendly memphis/manga; forbids brutalism/noir/terminal.
• CLICHÉ GUARD — never reflex cyberpunk-neon or terminal for "AI/tech" (the electric-blue-on-#0d1117 slop the skill already bans); reason from the SPECIFIC subject, not the umbrella domain.
• 3-SECOND-READ SUPREMACY — if a style hurts legibility, the style YIELDS to atmosphere/background and the content spine stays legible (ties into the whitespace/squint/keyframe_qa gates and theme.py's contrast floors).

BASELINE: absent any strong signal, fall back to the enhanced-flat native look (Minimal/Flat 2.0 — the contrast-safe, every-tier-deliverable default that is backward-compatible with today). A style is chosen on EVERY run and is user-visible at the 🔴 plan checkpoint before authoring.

## Topic-domain → style map (the Step-2 shortlist source)

Step-2 shortlist source: DOMAIN → APT STYLE(S) → ANTI-PICK (the register whose emotional temperature or legibility profile collides with the subject). The map narrows; the Step-3 four-axis contest decides.

| Topic domain | Apt style(s) | Anti-pick (why it fights the domain) |
|---|---|---|
| Finance / enterprise / consulting | Swiss · editorial | vaporwave / cyberpunk-neon — unserious, breaks trust |
| Engineering / hardware / architecture | blueprint · bauhaus | watercolor — imprecise, fights schematic clarity |
| Software / dev-tooling / infra | terminal · Swiss | art-deco (ornament fights code density); DON'T reflex cyberpunk-neon (#0d1117 cliché) |
| AI / ML / technical research | editorial · blueprint · Swiss | cyberpunk-neon — glossy sci-fi cliché faking "futuristic" over real method |
| Medicine / biotech / clinical | editorial · blueprint (anatomical) | manga / memphis / vaporwave — trivializes (somber veto) |
| History / museums / culture / heritage | editorial · art-deco (era) · risograph | cyberpunk-neon / glassmorphism — anachronistic, screen-glossy |
| Luxury / fashion / hospitality / spirits | art-deco · high-fashion editorial | brutalism / terminal — cold, cheap-looking, off-brand |
| Gaming / esports / entertainment / youth | cyberpunk-neon · manga-comic · vaporwave | Swiss — too austere, kills the energy |
| Consumer app / lifestyle / wellness / D2C | glassmorphism · claymorphism (AI tier) · editorial | brutalism / noir — harsh, off-brand |
| Startup pitch / product launch / hype | glassmorphism · bold editorial · memphis (playful brand) | blueprint — reads like a lab report, not a launch |
| Climate / nature / sustainability / travel | watercolor · risograph · cartographic · editorial | terminal / cyberpunk-neon — cold, screen-bound, off-topic |
| Music / arts / indie / creative | risograph · memphis · vaporwave (retro-music) | blueprint — clinical, kills expressiveness |
| Crime / security / investigative / defense | noir · brutalism | memphis / claymorphism — playful, undercuts gravity |
| Kids education / general-public explainer | risograph · claymorphism · friendly memphis · bauhaus | brutalism / noir / terminal — cold / scary |
| Geography / geopolitics / logistics / supply-chain | cartographic · Swiss (data) · blueprint | watercolor — imprecise for spatial data |
| Space / physics / deep-tech futures | blueprint (star-chart) · editorial · restrained cyberpunk (only if genuinely futuristic) | watercolor — imprecise for hard science |
| Data / analytics / observability | terminal · Swiss | vaporwave / watercolor — low-contrast under charts (data-density veto) |
| Legal / policy / government | editorial · Swiss | vaporwave / manga — undermines authority |

ANTI-PICK PRINCIPLE: the anti-pick always collides on ONE of two axes — emotional temperature (a playful/ironic register over a somber or authority-demanding subject) or legibility profile (a low-contrast/high-texture spine under a data-dense deck). Both are hard vetoes in the selection contest, above the four scoring axes.

## Coherence + faithfulness (the two laws)

TWO LAWS, one enforced by the pipeline, one by the prompt structure.

LAW 1 — ONE STYLE, THREADED AS ATMOSPHERE UNDER THE CONTENT SYSTEM. The style tints HOW things look, never WHAT is shown: a chart is still the right chart, a flow still a flow — form-selection is unchanged; the style layers under it.

Single source of truth = style_thesis.style_clause / meta.style_preamble — one compact fragment distilling the style's DNA (e.g. riso → "2–3 spot-ink print: coarse halftone, paper grain, ~2mm layer misregistration, matte"; noir → "low-key chiaroscuro, deep shadow, single cold key light, high grain"; blueprint → "thin cyan/white line-work on a dark drafting grid").

THREAD IT EVERYWHERE THE STYLE APPEARS — this is the fix for imagegen.py having NO global preamble today. Two complementary paths: (a) the director appends the same style_clause to every media.image_prompt (hero cover + illustrated .split panels) AND every meta.soft_texture_prompts[] (the rotated content-page textures); (b) the LOAD-BEARING backstop — imagegen._apply_style reads meta.style_preamble and prepends it to EVERY per-scene and soft-texture prompt at the single choke point, so coherence becomes a property of the pipeline, not of the director remembering 12 prompts. Because the styled prompt is what gets hashed into the sha1 cache, a constant style ⇒ cache hits (re-renders stay free/offline); changing the style ⇒ new hash ⇒ correct re-render.

BIAS THE FLAT + HTML TIERS TO MATCH (style is not just the AI images): THEME — the style sets theme.py's mode + accent FAMILY (Swiss → near-mono + one saturated accent; noir → dark + one cold accent; art-deco → jewel + gold; riso → warm spot-ink duotone); the style PROPOSES, theme.py's ≥7:1 fg / ≥3:1 accent math DISPOSES. TYPE — the style picks a BUNDLED display + body FACE (theme.py `--font-display`/`--font-body`/`--font-kind`; four SIL-OFL faces in `assets/fonts/`, `@font-face`'d in base.css): **comic** styles (manga) → Bangers; **grotesque/geometric** (swiss, bauhaus, memphis, vaporwave, riso, glass, clay) → Space Grotesk; **serif/display** (editorial, art-deco, noir, cinematic, watercolor, cartographic) → Playfair Display display + a text serif body; **mono/technical** (terminal, blueprint, cyberpunk, brutalism) → JetBrains Mono. So the deck's TYPE genuinely reads the style for LATIN text (a comic deck reads comic, not a plain sans); on a zh/ja/ko deck the comic/mono display faces have no CJK glyphs — headlines fall back to the system CJK sans, so prefer a sans/serif style for CJK decks (validate warns) — applied to EVERY headline + hero-number/value role (`.stat`/`.num`/`.hs-hub`/`.segbar`…); descriptive sub-labels use the body face; data labels (`.kicker`/axis/table/`.chrome`) stay mono. Each stack keeps a CJK + generic fallback so 中文 decks and non-mac machines still render, and scenes.py mirrors the same face on the programmatic (chart/title) tier via `--font-kind`. COMPOSITION — the style sets the default envelope (Swiss → strict asymmetric grid; bauhaus → primary-shape blocks + diagonal; art-deco → symmetric framed), on top of which the existing per-beat composition-signature variety rules still apply. FREE-TIER MOTIF — the topical .bg-motif SVG is drawn in the style's linework. MOTION — the style flavours the ONE allowed seek-frozen primitive (noir → slow drift; cyberpunk → sharper wipe; watercolor → gentle bloom) without ever adding motion.

COHERENCE CHECK: every image prompt shares the identical style_clause; theme + type + composition defaults all read as the same named register; the design-critic's freshness/name-swap gates confirm the style is on-topic, not generic wallpaper. Result: "THIS subject, art-directed in style X," never "style X pasted over generic slides."

LAW 2 — A STYLE IS A RENDERING TREATMENT OF ATMOSPHERE, NEVER THE DATA. It changes broll/backgrounds/palette/type/composition; it never changes what is claimed. Five hard rules:
1. STYLE NEVER FABRICATES SPECIFICS. The broll doctrine holds: no logos, faces, named things, invented UI, fake numbers/labels, in-image text. Several styles TEMPT their own fabrication — cyberpunk wants glowing HUD figures; terminal wants readable fake code; blueprint wants dimension callouts; art-deco wants gilt signage; manga wants speech bubbles. So each style_clause EXPLICITLY negates its own temptation, and imagegen._apply_style ALWAYS appends a hard faithfulness tail after the style clause: "…no text, no letters, no numbers, no logos, no readable signage, no real-world named specifics; the style treats the atmosphere, never the data." Structurally the style is the MIDDLE clause between the subject and the negatives, so it can never override faithfulness.
2. STYLE STAYS TOPICAL. Prompt shape is always render [THIS topic's motif] in the style of [X] — the topic motif is the NOUN, the style the ADVERB, both present. A Swiss-style reef image is a Swiss-grid composition OF reef structures, not generic Swiss colour-blocks. LITMUS (the skill's topical test): hide the text — can a viewer still tell what the video is ABOUT? A gorgeous on-style but off-topic texture is a MISS.
3. LEGIBILITY SUPREMACY. When the treatment would harm the 3-second read (busy texture under a chart, low-contrast type), the style YIELDS to backgrounds-behind-glass (.bg-soft ~.12, cap .14, on .bg-soft-tint) and the content spine stays high-contrast; theme.py's ≥7:1/≥3:1 floors are the automatic backstop.
4. DATA-FORMS ARE STYLE-AGNOSTIC. Charts, timelines, quadrants, stats render in the deck's semantic color_ledger and stay accurate — the style may tint their frame/background but must never distort axes, proportions or values (no fake-perspective art-deco bars, no melted claymorphism charts).
5. TONAL FAITHFULNESS. Faithfulness includes fidelity to the subject's GRAVITY: if a somber topic meets a trivializing style (auto-picked or user-requested), the guard ESCALATES (down-rank per the vetoes, or AskUserQuestion) rather than silently rendering a flippant treatment over serious material.

## The catalog — 18 named styles

### typographic-modernist

#### `swiss` — Swiss / International Typographic
- **When:** The default SPINE for systematic, authoritative, data-dense material that must read rigorous in 3 seconds.
- **Best fit:** finance, enterprise/consulting, science & reference, dashboards/benchmarks, government/policy
- **Visual DNA:** Mathematical modular grid; flush-left neutral grotesque (Helvetica/Akzidenz/Univers) at a bold scale; huge ACTIVE whitespace; 2–3 flat colours (often International red + black on white); objective, ornament-free rigor; asymmetric balance.
- **Palette:** light; near-mono fg + ONE saturated accent (International red #e2231a or a single brand hue); temperature-neutral off-white bg  ·  **Type:** tight neutral grotesque, flush-left, oversized heads, rag-right body, tabular figures  ·  **Composition:** strict asymmetric modular grid, flush-left kickers, generous margins; never centered filler
- **gpt-image style clause:** rendered with Swiss/International-Typographic restraint: strict grid, flat objective imagery, vast negative space, 2–3 flat colours, zero ornament — no decorative flourish, no faux chart or axis marks
- **Flat/HTML tier (no AI):** lands FULLY with no AI: tighter grid, flush-left mono kickers, bigger whitespace, 2-colour ledger, .bg-grid at a whisper
- **Faithfulness trap:** tempts fake axis/chart marks as 'Swiss decoration' — keep imagery a flat objective shape/photo OF the subject; data stays in real charts
- **Avoid the cliché:** not a Helvetica poster of random rectangles — the grid must ORGANIZE real content; red is emphasis, not confetti
- **Beats its rival:** beats Editorial when the deck is a systematic data-grid, not a quote-driven narrative

#### `editorial` — Editorial / Magazine
- **When:** NARRATIVE + PREMIUM: thought-leadership, brand/culture stories, journalism, essays, considered long-form with a human voice.
- **Best fit:** thought-leadership, brand/culture stories, journalism/essays, medicine/biotech explainers, history/museums/heritage, legal/policy
- **Visual DNA:** High-contrast serif display (Didot/Bodoni) over a quiet body serif; multi-column grid; kicker/deck/byline structure; drop caps, pull-quotes; ink-on-cream + ONE restrained accent (oxblood/forest/navy); documentary photography.
- **Palette:** light; ink-on-cream (#f6f3ea), single muted accent (oxblood #7a1f1f)  ·  **Type:** serif display head + quiet serif body + mono/small-caps kicker; generous leading  ·  **Composition:** multi-column grid, folios, real pull-quote pulled from the script, one ::first-letter drop cap
- **gpt-image style clause:** as a refined editorial magazine feature: documentary photography in muted natural light, shallow depth, generous negative space, ink-on-cream with one restrained accent — calm, journalistic, never stock-smiling or advertorial
- **Flat/HTML tier (no AI):** the typographic voice IS carried by base.css's serif stack + theme; needs no AI
- **Faithfulness trap:** tempts fake magazine headlines/kickers in-image — keep photography wordless; the department label is real HTML type
- **Avoid the cliché:** no chunky Playfair over a beige gradient with a fake 'MAGAZINE' kicker and a smiling stock photo
- **Beats its rival:** beats Swiss when the content is warm long-form narrative, not a systematic data-grid

#### `bauhaus` — Bauhaus
- **When:** FIRST-PRINCIPLES, constructive energy: education, design/architecture, workshops, foundational explainers, product/engineering culture.
- **Best fit:** education & workshops, design/art/architecture, foundational explainers, product/engineering culture
- **Visual DNA:** Three primaries (red / cobalt / chrome-yellow) + black on warm cream; geometric sans, often lowercase; circle/triangle/square as structural vocabulary; diagonal tension, overlapping hard-edged planes; matte poster flatness, no gradients.
- **Palette:** light; bg #f3ead6, accent red #e5231b, accent2 cobalt #1552c4, chrome-yellow on one beat  ·  **Type:** geometric sans (Futura/Century-Gothic lineage), lowercase heads, border-radius:0  ·  **Composition:** .split/.grid-asym with overlapping planes on a real diagonal; one hero title at rotate(-4deg)
- **gpt-image style clause:** as a Bauhaus constructivist composition: bold flat geometric planes in primary red, cobalt and chrome-yellow with black on cream, diagonal balance, the subject abstracted INTO geometry, matte flatness, no gradients or shadow
- **Flat/HTML tier (no AI):** lands fully: geometric-sans + 3-primary ledger + a .bg-motif built from circle+triangle+rectangle
- **Faithfulness trap:** the shapes must ENCODE meaning (triangle=increase, circle=whole), never fabricate quantities
- **Avoid the cliché:** no random primary circles/triangles as confetti behind text — that's a Canva template; each shape must carry meaning
- **Beats its rival:** beats Swiss when the mood is optimistic-constructive 'made of parts', not austere data-rigor

#### `brutalism` — Brutalism (web/graphic)
- **When:** Deliberate ANTI-CORPORATE POV where bluntness IS the message.
- **Best fit:** developer tools, crypto/web3 & indie tech, design portfolios/hackathons, provocative theses, 'not-like-the-enterprise' positioning
- **Visual DNA:** Stark black on off-white + ONE acid hit (lime/orange/electric-blue); monospace or system-default, oversized, clashing sizes; exposed grid, thick rules, hard offset shadows (no blur), zero radius; xerox/halftone grit.
- **Palette:** light; bg #ffffff, accent #111, accent2 acid lime #c6ff00; --hairline 3px solid #000  ·  **Type:** var(--font-mono), oversized, clashing weights  ·  **Composition:** everything left-flush, exposed .bg-grid, hard offset box-shadow:8px 8px 0 #000
- **gpt-image style clause:** in raw graphic brutalism: stark black on off-white with a single acid accent, heavy hard-edged blocks, thick rules, harsh flat frontal light, gritty photocopied/halftone texture, deliberately blunt
- **Flat/HTML tier (no AI):** native: mono type + 3px borders + hard offset shadows + radius:0
- **Faithfulness trap:** tempts fake UI text/console strings — keep blocks wordless
- **Avoid the cliché:** not Times-New-Roman + random neon that wrecks legibility; keep a real first-read hierarchy and AA contrast — rawness is intentional, not an accessibility failure
- **Beats its rival:** beats Terminal when the register wants confrontation/attitude, not code-console texture

### material-surface

#### `glassmorphism` — Glassmorphism
- **When:** Sleek modern-tech wanting layered translucent depth — SELECT it deliberately, NOT as a fallback (it is the skill's default AI look, so reflexive use reads as generic AI filler).
- **Best fit:** SaaS/dashboards, fintech, AI/data platforms & dev tools, premium consumer apps, startup pitch/launch
- **Visual DNA:** Frosted translucent panels with z-depth over an out-of-focus field of vibrant colour; thin bright edge-light, gaussian blur, inner glow, faint grain; clean geometric sans near-white on glass.
- **Palette:** dark; one vivid accent + its complement; two .bg-glow blobs as the light field  ·  **Type:** clean geometric sans, medium weight, .grad-text headline  ·  **Composition:** one or two glass panels MAX, generous space, content on .card.glass
- **gpt-image style clause:** rendered as glassmorphism: frosted translucent panels floating in layered depth over a soft out-of-focus field of colour DERIVED FROM THE SUBJECT, thin edge-light, heavy background blur, inner glow, faint grain — clean and premium
- **Flat/HTML tier (no AI):** native idiom: .card.glass + two .bg-glow + .bg-soft-tint behind text (backdrop-blur is a GPU bonus)
- **Faithfulness trap:** the blurred field must be the subject's colour (a reef = coral-teal), not a random purple haze; no fake UI in the glass
- **Avoid the cliché:** do not stack many glass cards into unreadable frosted soup — one/two panels, a solid tint behind text
- **Beats its rival:** beats Aero-gloss when the surface should be see-through/frosted, not wet-reflective

#### `claymorphism` — Claymorphism
- **When:** Friendly, playful, human, low-stakes-delightful topics.
- **Best fit:** kids/edtech, app onboarding, wellness/health-lite, community/social/lifestyle, fun mobile products
- **Visual DNA:** Soft pastel candy (2–3 hues); big rounded chunky forms; MATTE inflated clay with paired soft inner shadows + a top-left highlight; rounded bold sans, dark-on-pastel; playful air.
- **Palette:** light; high-lightness pastel bg + candy accent + analogous accent2; oversized radius  ·  **Type:** rounded heavy sans  ·  **Composition:** puffiness as an ACCENT on the hero only; flat calm space around it
- **gpt-image style clause:** rendered as claymorphism: soft inflated 3D clay forms with rounded puffy edges, matte pastel candy surfaces, paired soft shadows + a top-left highlight for a pillowy tactile look, gentle studio light — the subject shaped as cute puffy objects
- **Flat/HTML tier (no AI):** approximates with pastel palette + pillowy rounded matte surfaces + friendly type (true dual inner-shadow only lands in the AI tier)
- **Faithfulness trap:** puffiness must not distort magnitude (no melted clay 'charts'); data stays flat and accurate
- **Avoid the cliché:** no 3D-Memoji/Fisher-Price glossy-rainbow toybox — restrain to 2–3 MATTE pastels
- **Beats its rival:** beats Glassmorphism when the mood is warm/tactile/friendly, not cool tech-depth

### illustrative-pop

#### `manga` — Manga / Comic Ink
- **When:** High-energy, story-driven arcs with DRAMA + MOMENTUM or a face-off/level-up.
- **Best fit:** youth/gaming/anime culture, hero's-journey explainers, hype launches, competitor showdowns, retro-Americana, marketing/pop-culture (pop-art variant)
- **Visual DNA:** Confident black ink linework + halftone/screentone shading; dramatic radial speed-lines, foreshortened hero angle; wordless bursts/motion streaks. MODE A (manga): monochrome + grey screentone + ONE accent wash, kinetic. MODE B (comic): saturated CMYK primaries + heavy black on cream newsprint, heroic. VARIANT (pop-art): flat silkscreen blocks, a Warhol repetition grid, ironic.
- **Palette:** manga: light/dark, off-white #f6f3ec + one hot accent; comic: bg cream #f7f1df, accent red #e63329, accent2 cyan #12a5c8  ·  **Type:** heavy grotesque/condensed display, italic-slant motion kickers  ·  **Composition:** dynamic diagonals, foreshortened angle, thick ink keyline cards + hard offset shadow, screentone via repeating-radial-gradient
- **gpt-image style clause:** rendered as inked comic/manga art: confident black linework, halftone/screentone dot shading, radial speed-lines converging on the subject, a dramatic foreshortened hero angle, wordless — no speech balloons, no lettering
- **Flat/HTML tier (no AI):** ink keyline + screentone repeating-radial-gradient + skewed diagonal rules
- **Faithfulness trap:** NO in-panel speech bubbles / 'POW!' word-art (fabricates text); carry drama in composition
- **Avoid the cliché:** no big-eyed moe mascot or literal POW!/BAM! costume-shop kitsch — drama lives in speed-lines + angle over the REAL subject
- **Beats its rival:** beats Memphis when the content has a narrative arc/drama, not just playful energy

#### `risograph` — Risograph
- **When:** Warm, tactile, human, deliberately non-corporate registers — analog honesty over slick precision.
- **Best fit:** indie/craft/zine, community & nonprofit, arts & culture / education, sustainability/eco, books & literature, design-studio branding
- **Visual DNA:** 2–3 spot inks only (fluoro pink / riso blue / sunflower yellow) overprinting into extra hues; bold flat reduced shapes; heavy visible grain + halftone dither; 1–3px layer misregistration; warm manila paper.
- **Palette:** light; accent riso-pink #ff4d8d, accent2 riso-blue #2340d6, bg manila #f4efe2  ·  **Type:** friendly grotesque or warm serif, generous  ·  **Composition:** FLAT reduced shapes, genuine multiply overlap; fake overprint = same .bg-motif twice, one translated 2–3px with mix-blend-mode:multiply
- **gpt-image style clause:** rendered as a 2–3 colour risograph print: a limited spot-ink palette overprinting where layers overlap, bold flat reduced shapes, heavy grain and halftone dither, ~2mm layer misregistration, ink bleed on warm recycled paper — tactile and analog
- **Flat/HTML tier (no AI):** real: duotone .bg-motif with multiply offset + feTurbulence grain + halftone gradient
- **Faithfulness trap:** grain must not sit UNDER a chart (kills the read); riso is a background/broll treatment when data is present
- **Avoid the cliché:** not a pink-blue gradient + noise over a stock photo — commit to FLAT reduced shapes + honest 2–3 ink count (reduction, not just grain, reads as riso)
- **Beats its rival:** beats Memphis when the mood is warm/handmade/reduced, not clashing 80s energy

#### `memphis` — Memphis / 80s Postmodern
- **When:** Playful, irreverent, retro-flavoured FUN with legible content.
- **Best fit:** 80s nostalgia, creative agencies, events/parties, kids & family, fashion/lifestyle/music, joyful consumer brands
- **Visual DNA:** Clashing non-harmonious brights (hot pink, turquoise, lemon, black) on white; asymmetric off-grid confetti (circles, triangles, half-circles); black squiggles/zig-zags; terrazzo speckle; bold geometric sans.
- **Palette:** light; accent hot-pink #ff3d81, accent2 turquoise #22c1c3, lemon utility hue, white bg  ·  **Type:** bold geometric sans  ·  **Composition:** confetti + squiggles CONFINED to margins/corners as a FRAME around a clean high-contrast content zone
- **gpt-image style clause:** rendered in 1980s Memphis-Milano postmodern design: flat clashing brights, scattered playful geometric shapes, black squiggles/zig-zags, confetti dots and terrazzo speckle in a bold asymmetric off-grid — graphic, flat, joyful
- **Flat/HTML tier (no AI):** native: confetti/squiggle .bg-motif in corners + terrazzo radial specks + chevron .accent-fill
- **Faithfulness trap:** pattern must not carpet the frame (illegible chaos) — confine to a border, never wallpaper
- **Avoid the cliché:** pattern as FRAME, never wallpaper drowning the text
- **Beats its rival:** beats Pop-Art/Sticker when the energy is geometric-postmodern, not iconic-repetition or cute-mascot

### atmospheric-cinematic

#### `noir` — Film Noir (1940s chiaroscuro)
- **When:** MYSTERY-shaped topics where tension/suspense is the emotional spine.
- **Best fit:** investigation/forensics, fraud/anomaly detection, security breach / incident post-mortem, true-crime & investigative journalism, 'hidden truth revealed' arcs
- **Visual DNA:** Near-monochrome — warm charcoal-black ground, cream foreground, ONE restrained cold-steel or amber highlight; single hard key light, strong diagonal shadow falloff; venetian-blind slats, smoke, rain-slick, heavy grain; subject emerges from darkness.
- **Palette:** dark; bg warm charcoal #12100e, fg cream #efe9dd, accent one cold steel #6f8ba0 OR amber #c69a52, accent2 muted  ·  **Type:** condensed serif/slab titles, wide-tracked all-caps kickers  ·  **Composition:** one .bg-glow key light, venetian-slat .bg-motif at ~.06, .scrim shadow falloff, off-center silhouette
- **gpt-image style clause:** in 1940s film-noir: high-contrast black-and-white chiaroscuro from a single hard key light, venetian-blind shadow slats, drifting smoke and rain-slick reflections, heavy grain, a silhouette emerging from darkness — low-key suspense
- **Flat/HTML tier (no AI):** cream-on-charcoal + one accent + slat motif + heavy .scrim (no bright cards)
- **Faithfulness trap:** atmosphere is what's HIDDEN, not fake props/text; keep it geometry of light, no crime clip-art
- **Avoid the cliché:** no detective-fedora clip-art, no neon-noir purple mashup — pure high-contrast mono, ONE accent
- **Beats its rival:** beats Cinematic-Photoreal when the topic needs suspense/monochrome gravity, not naturalistic warmth

#### `cyberpunk` — Cyberpunk Neon
- **When:** TECH-EDGE topics that are LITERALLY cyber/futuretech and want a near-future high-stakes charge.
- **Best fit:** cybersecurity/red-team, gaming/esports, crypto/web3 (edgy), autonomous systems, sci-fi-adjacent launches for a young technical audience
- **Visual DNA:** Two committed neons (magenta + cyan/electric-blue) over deep blue-black; dense rain-soaked night-city depth, wet reflections doubling the light, volumetric haze, lens bloom, subtle chromatic aberration; techno mono/wide uppercase.
- **Palette:** dark; bg deep blue-black #0a0d18 (NOT #0d1117), accent magenta #ff2e88, accent2 cyan #22d3ee  ·  **Type:** mono/sans wide-tracked uppercase, .grad-text magenta→cyan  ·  **Composition:** TWO .bg-glow blobs for dual-neon bloom, fine .bg-grid, glass cards with a glowing 1px edge; glow on the HERO only
- **gpt-image style clause:** in cyberpunk neon: a rain-soaked near-future night lit by glowing magenta and cyan, deep blue-black shadows, volumetric haze and lens bloom, wet reflective surfaces doubling the light, holographic sheen — no READABLE signage, no HUD figures
- **Flat/HTML tier (no AI):** dual glows + grid + glass edge-glow
- **Faithfulness trap:** WANTS glowing HUD readouts & fake numbers — the clause must ban readable signage/figures; data stays on clean glass
- **Avoid the cliché:** NOT the reflex 'AI/tech' pick — never electric-blue-on-#0d1117 slop, Matrix rain, or rainbow-neon; reserve for genuinely cyber subjects
- **Beats its rival:** beats Vaporwave when the mood is gritty/dark/urban, not pastel-nostalgic

#### `vaporwave` — Vaporwave / Synthwave
- **When:** NOSTALGIA-and-hype with a fun edge — 'the future as imagined in the past' for a young meme-literate audience.
- **Best fit:** retro 80s/90s culture, music & audio, creative/design tools, gaming/entertainment, aesthetics/lifestyle launches
- **Visual DNA:** Banded sunset (hot pink→magenta→purple→orange) over deep indigo, cyan + chrome accents; glowing perspective grid to a low horizon, slatted gradient sun, centered symmetry; VHS haze, scanlines, chrome sheen.
- **Palette:** dark; bg deep indigo #1a0f33, accent hot-pink #ff4fa3, accent2 cyan #35e0e0  ·  **Type:** chrome-gloss/italic retro display, .grad-text pink→cyan  ·  **Composition:** perspective-grid .bg-motif with a real vanishing point, low horizontal sun-glow band, starfield above, glossy glass
- **gpt-image style clause:** in 1980s synthwave/vaporwave: a glowing neon perspective grid receding to a low horizon, a banded gradient sun, chrome-gloss highlights, soft VHS haze and scanlines, deep indigo sky — dreamy retro-futuristic, no meme props
- **Flat/HTML tier (no AI):** SVG perspective grid (vanishing point .bg-grid can't draw) + sun-glow band + starfield
- **Faithfulness trap:** keep it clean atmosphere; no Windows-95 chrome, dolphins, Roman busts, wingdings
- **Avoid the cliché:** no ironic-meme props — SUNSET + PERSPECTIVE-GRID + glow only, restrained pink/cyan/indigo
- **Beats its rival:** beats Cyberpunk when the mood is pastel-optimistic-retro, not gritty rain-city

#### `watercolor` — Watercolor / Ink Wash (sumi-e & aquarelle)
- **When:** SOFT, HUMAN, ORGANIC, calm, artisanal topics — the only LIGHT low-energy register.
- **Best fit:** nature & sustainability, wellness & mental health, arts/culture/humanities, heritage & craft, food & travel, poetry/philosophy, East-Asian subjects (lean sumi-e)
- **Visual DNA:** Warm paper cream ground, deep ink, 2–3 muted botanical washes (indigo/sage/rust/ochre); wet-on-wet bleeds, blooms, granulation, cold-press grain; negative space AS subject (~50% empty); serif/brush titles.
- **Palette:** light; bg warm paper #f7f4ee, fg ink #1c1712, accent a muted wash (indigo #5a6b8c / sage #7a8b6f / rust #a8623f)  ·  **Type:** elegant serif for title AND kicker, ~50% utilization  ·  **Composition:** one loose focal wash off-center, .bg-paper grain, no hard rules/grid
- **gpt-image style clause:** as a loose watercolor and ink-wash painting: translucent washes with wet-on-wet bleeds and blooms, cold-press paper grain and granulation, calligraphic strokes, generous negative space, muted natural tones, soft organic edges, no hard outlines
- **Flat/HTML tier (no AI):** .bg-paper + a single loose brushstroke .bg-motif + a wash-bloom .bg-soft-tint; drop .bg-grid/.bg-stars
- **Faithfulness trap:** DATA-DENSITY VETO applies — washes never sit under charts (imprecise); background/broll only when data is present
- **Avoid the cliché:** no spilled-paint-splatter PNG on a white card, no rainbow watercolor — 2–3 muted washes + ink discipline
- **Beats its rival:** beats Editorial when the subject is organic/meditative and wants hand-made softness over publication polish

#### `artdeco` — Art Deco / Gatsby
- **When:** LUXURY and PRESTIGE — timeless elegance, glamour, geometric confidence. The one register where centered symmetry is correct.
- **Best fit:** premium/heritage brands, private banking/wealth, hospitality/hotels/spirits, fashion & jewelry, awards & milestones, architecture / 1920s-40s history
- **Visual DNA:** Metallic gold/brass on a deep jewel ground (emerald/midnight-navy/black); high-contrast deco display caps, WIDE tracking, fine gold linework; strong vertical/central SYMMETRY, radiating sunburst/fan, stepped ziggurat/chevron; brushed-metal sheen.
- **Palette:** dark; bg emerald #0c2a24 or navy #0d1836, fg ivory, accent gold #c8a24a, accent2 jewel complement  ·  **Type:** deco/geometric display caps, wide-tracked all-caps kickers  ·  **Composition:** true bilateral symmetry with breathing room, sunburst/fan/chevron .bg-motif in gold at ~.10
- **gpt-image style clause:** in 1920s Art Deco: symmetrical geometric elegance, radiating sunburst and fan motifs, stepped ziggurat and chevron forms, gilded gold linework on a deep jewel ground, brushed-metal sheen — Jazz-Age glamour
- **Flat/HTML tier (no AI):** symmetric gold-linework .bg-motif + .grad-text gold sheen + jewel .accent-fill dividers
- **Faithfulness trap:** WANTS fake gilt signage/monograms — ban in-image lettering; ornament is geometry, not words
- **Avoid the cliché:** no casino/Vegas glitter or literal 'Gatsby'-font stamp — restrained fine gold LINEWORK, one metallic accent
- **Beats its rival:** beats Noir when the topic is celebratory-luxurious, not suspenseful

#### `cinematic` — Cinematic Photoreal (teal-orange grade)
- **When:** REAL-WORLD topics wanting premium grounded emotional gravitas as actual cinematography.
- **Best fit:** brand films/documentaries, product launches with physical products, corporate/enterprise storytelling, travel/adventure/sports, human-interest & mission-driven
- **Visual DNA:** Complementary teal-and-orange blockbuster grade (warm amber highlights vs cool teal shadows); shallow depth of field isolating one subject; creamy bokeh, subtle anamorphic flare, filmic grain, golden-hour light; photoreal frames OF the subject.
- **Palette:** dark; bg teal-charcoal #0f1e22, fg warm off-white #f2ece2, accent amber #e8944e, accent2 teal #3aa6a0  ·  **Type:** clean sans, letter-spaced caps, lower-third title feel  ·  **Composition:** AI .bg-photo heroes + .scrim; flat approx = warm glow opposite a cool glow + glass cards
- **gpt-image style clause:** as a cinematic photoreal frame with a Hollywood teal-and-orange grade: warm amber highlights against cool teal shadows, shallow depth with creamy bokeh, subtle anamorphic flare, filmic grain, golden-hour atmosphere, high production value
- **Flat/HTML tier (no AI):** warm .bg-glow opposite a cool .bg-glow + .scrim falloff + .card.glass (real grade needs AI tier)
- **Faithfulness trap:** photoreal broll must stay generic (no real logos/faces/products/text); it's atmosphere, the facts are text/charts
- **Avoid the cliché:** no over-cranked orange-teal oversaturation or HDR halos — keep the grade subtle, one warm subject on a cool field
- **Beats its rival:** beats Noir when the subject wants naturalistic colour warmth, not monochrome mystery

### technical-documentary

#### `blueprint` — Blueprint / Schematic (cyanotype drafting)
- **When:** Engineering, architecture, hardware, mechanical/structural systems, teardowns — any topic whose logic is an OBJECT/ASSEMBLY with parts and mechanism.
- **Best fit:** engineering/hardware, architecture/structures, product teardowns, 'how it is built' explainers, AI/ML method (schematic)
- **Visual DNA:** Deep Prussian/cyan ground with white + pale-cyan linework, one warm drafting-red/amber highlight; orthographic discipline — dimension lines, section callouts, corner title-block; flat matte 'ink on blueprint paper', faint drafting grid, consistent thin line weights, dashed hidden lines.
- **Palette:** dark; bg Prussian #0e2a4a, accent pale cyan #7ec8ff, accent2 drafting amber/red  ·  **Type:** var(--font-mono) drafting labels, small-caps title-block, tabular figures  ·  **Composition:** orthographic; .hairline drafting rules, .rtable mono spec table, .bg-motif of the structure drawn with .draw at whisper opacity
- **gpt-image style clause:** rendered as a cyanotype architectural blueprint: deep Prussian-blue ground with thin white and pale-cyan technical line-work, a faint drafting grid, dimension lines, section callouts and an exploded/orthographic feel — GENERIC ambient linework only, no readable dimensions or labels
- **Flat/HTML tier (no AI):** NATIVE — .bg-grid IS a blueprint mesh; mono labels, hairline rules, structural .draw motif (no AI needed)
- **Faithfulness trap:** WANTS fake dimension numbers/callouts — dimensions are DATA; keep drawn linework generic, real specs in faithful tables
- **Avoid the cliché:** no glowing neon-blue Tron/HUD/circuit-board with lens flare — flat matte drafting DOCUMENT, one line weight, one accent, no glow
- **Beats its rival:** beats Cartographic when the subject is one built OBJECT, not a whole territory; beats Isometric-cutaway (its 3D-volume sub-variant) when flat orthographic lines read the mechanism better

#### `terminal` — Terminal / Data-Console (CRT phosphor)
- **When:** Software, data/ML, security, networking, DevOps, analytics, APIs, CLI how-tos — topics whose native texture is CODE, DATA STREAMS, or MONITORING. NOT the reflexive default for every tech deck.
- **Best fit:** dev-tooling/infra, data/ML pipelines, observability/telemetry, APIs & CLI tutorials, networking/DevOps
- **Visual DNA:** Near-black ground + ONE phosphor accent (amber or green), muted grey mid-tones; monospace everywhere, tabular figures, uppercase status-line labels; strict readout grid, hairline dividers, bottom status line; faint scanlines + monospace-cell grid, soft phosphor bloom on the accent only.
- **Palette:** dark; bg near-black #0e0f11, accent phosphor green #35d07f OR amber #ffb454 (deliberately NOT cliché cyan)  ·  **Type:** var(--font-mono) on nearly everything, tabular-nums, .chrome status-line rail  ·  **Composition:** aligned readout panels, .hairline dividers, low-opacity .bg-grid console mesh; one accent held strictly
- **gpt-image style clause:** rendered as a retro data-console / CRT terminal: near-black ground with a single phosphor accent, faint scanlines and a monospace-cell grid, softly glowing readout panels and abstract data-stream shapes — GENERIC glow only, no legible code, text or numbers
- **Flat/HTML tier (no AI):** native: mono type + phosphor accent + .bg-grid mesh; REAL data in .rtable/charts
- **Faithfulness trap:** WANTS readable fake code/log lines — illegible gibberish still skirts fabrication; keep it abstract glow, real data in faithful tables
- **Avoid the cliché:** no Matrix glyph-rain or walls of 'hacker' code, no electric-cyan-on-navy AI slop — calm mono grid, one phosphor accent
- **Beats its rival:** beats Blueprint when the subject is code/data/monitoring (glowing readouts), not a drafted physical object

#### `cartographic` — Cartographic / Atlas (topographic plate)
- **When:** Geography, geopolitics, logistics/supply-chain, distribution/coverage, travel, exploration, history-across-territory — topics whose logic is SPATIAL.
- **Best fit:** geography/geopolitics, logistics & supply-chain, distribution/coverage, travel/exploration, space/star-chart (blueprint hybrid)
- **Visual DNA:** Aged warm paper with muted hypsometric tints (ochre, sage, slate) + one ink accent; fine mono/engraved coordinate lettering, scale-bar + compass-rose chrome; framed plate — graticule border, legend corner, one focal landform; engraved contour/isoline hatching.
- **Palette:** light; bg aged-paper #f8f7f4 (warm ochre-tinted), accent ochre/terracotta #c67b3f, accent2 slate-teal  ·  **Type:** var(--font-mono) coordinate/legend labels, tabular-nums  ·  **Composition:** .bg-grid as a faint graticule, contour-ring .bg-motif via .draw, .hairline isolines, compass-rose/scale-bar SVG
- **gpt-image style clause:** rendered as a vintage cartographic atlas plate: aged warm-paper ground, fine contour and graticule lines, muted hypsometric tints, engraved compass-rose and scale-bar motifs, topographic hatching — GENERIC abstract landforms only, no real place names, borders or coordinates
- **Flat/HTML tier (no AI):** native: graticule .bg-grid + contour .draw motif + mono legend labels + compass-rose SVG (no AI needed)
- **Faithfulness trap:** never draw a real identifiable coastline/border implying a geographic CLAIM; landforms stay generic, real places in faithful labels
- **Avoid the cliché:** no pushpins-on-cork-world-map, no red-dashed flight arcs, no burnt-edge 'treasure map' — restrained topographic linework, one ink accent, generous paper
- **Beats its rival:** beats Blueprint when the subject is a whole territory / how-things-move-across-space, not one built object
