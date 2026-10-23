# Craft research — what premium promo films do that ours did not (2026-10-23)

Four web-research passes (launch-film craft, short-form vertical design, Remotion texture engineering, promo sound
design), each told to read this skill's own references first and report only what is new. Numbers are SOURCED unless
marked (U) — an unsourced suggestion or the researcher's own derivation — or (measured) — computed on this machine.
Read this before changing how the stage moves, where a 9:16 film puts its captions, or how the sound is mixed.

## 1. Motion: front-loaded curves and retargetable springs

- **Premium UI motion is front-loaded.** Time to reach 50% of a move, as a fraction of its duration (measured from the
  live CSS curves): Stripe `cubic-bezier(.25,1,.5,1)` 0.16 · Raycast / Emil Kowalski `(.23,1,.32,1)` 0.13 · Linear
  drawer `(.32,.72,0,1)` 0.16 · Cap's camera spring ≈0.34 · `easeInOutCubic` 0.49. Stripe uses `0.3s (.25,1,.5,1)` 84
  times in its CSS; Raycast 0.2–0.4 s; Linear panels 0.5 s. Sources: stripe.com, raycast.com, linear.app CSS.
- **The camera is a near-critical spring that is RETARGETED, not a fresh ease per key.** Cap (open Screen Studio
  clone): stiffness 200, damping 40, mass 2.25 (ζ≈0.94); retargets carry velocity, no fixed durations. Remotion's
  `spring()` with that config: 90% at 0.38 s, 2% settle at 0.53 s, no overshoot (measured). Source:
  github.com/CapSoftware/Cap `crates/rendering/src/zoom_spring.rs`.
- **A fresh ease at each key stalls.** Simulated: a move at 53 px/frame retargeted mid-way dropped to 1 px/frame (max
  |dv| 52 px/f²); summing one spring response per key — x(t) = x₀ + Σ (x_k − x_{k−1})·s(t − t_k) — kept speed 42→59
  (max |dv| 23). Linear, a pure function of the frame, O(keys). (U, derivation)
- **Spring parametrisation.** Apple `Spring(duration d, bounce b)`: mass 1, stiffness (2π/d)², damping 4π(1−b)/d
  (developer.apple.com/documentation/swiftui/spring). Overshoot = exp(−πζ/√(1−ζ²)). Premium spatial moves ζ 0.7–0.85
  (overshoot 4.6–0.6%), d 0.4–0.5 s, e.g. `{mass:1, stiffness:158, damping:21}`; opacity/colour/blur get ζ=1 (no
  overshoot). `spring({durationInFrames})` lands a spring exactly on a cue (remotion.dev/docs/spring).
- **The cursor is spring-chased with lead.** Cap presets (tension/mass/friction): default 470/3/70 (90% in 0.30 s),
  click approach 530/1/40; the target snaps to the click point once a click is ≤500 ms away and the spring stiffens
  175 ms before it. Cap click shrink 0.8 over 130 ms; ripple 0.6 s (Fovea 620 ms). Velocity tilt up to 20° (Cap; Tella
  "movement tilt"). Idle fade 400 ms after ≥0.5 s idle. Cursor size 2× system (Tella). Sources: Cap
  `crates/project/src/configuration.rs`, `layers/cursor.rs`; tella.com help.
- **Zoom timing for UI demos** (three open clones agree): zoom 1.5× (Cap) – 2.0× (Reframed, Fovea); Reframed ramps 0.4 s
  starting 0.4 s BEFORE the click and dwells ≥0.5 s; Fovea ramps 0.55 s and holds 2.2 s after the last click, merging
  zooms for clicks <2.2 s apart (pan instead). Screen Studio users complain its default zoom starts too late.
- **Entrances are small**: Linear scaleIn .96/.98→1; Raycast .96 with a 10 px offset; never from scale(0).
- **Motion blur**: Remotion `CameraMotionBlur` (shutter 180°, 5–10 samples) combs, posterises dark grounds and runs
  ~0.75 frame early (measured) — not for narrated films. Analytic per-element blur instead: SVG `feGaussianBlur`
  stdDeviation `s 0` along the motion, s = |v|·(shutter/360)/√12, v in px/frame (U, derivation; +22 ms/frame measured).
- **Type in launch films** (live CSS): Apple display 80 px / 600 / line-height 1.05 / −0.015 em; Linear ≥32 px
  1.0–1.125 / −0.022 em; Vercel 56–72 px semibold 1.0 / −0.06 em. Per-glyph inline-block spans lose kerning (+4.7% on
  "AVATAR Wave", measured): place glyph i at measureText(text[0..i]).width − measureText(char_i).width.

## 2. 9:16 platform safe zones and covers

- No platform publishes organic-post safe zones; ad specs and third-party tables agree on ranges, 1080×1920: top
  90–220 px (5–11%), **bottom 17–35% covered** (TikTok up to 45% with a 4-line caption; Douyin "bottom 25%" third-party),
  right 100–164 px (up to 22%), left 48–60 px. Caption block guidance y≈1200–1550 (62–81%). Sources:
  strikesocial.com safe-zone guide, blitzcutai.com caption placement, reap.video short-form safe zones,
  secaiyun.com (Douyin). Xiaohongshu: none found — check on a phone.
- Vertical captions: 8–12 Chinese characters a line (aiyotaipei.com, airuru.cc), Medium weight or heavier, one of
  stroke/shadow/box; highlight 2–4 key characters, ≤110% scale, constant vertical position (cutup.shop, zellahq.com).
  Size guidance conflicts (36–100 px); 55–65 px is the common start (blitzcutai.com).
- Hook: TikTok (official) — state the proposition in the first 3 s (ads.tiktok.com creative best practices). Title
  visible and something moving from frame 0.
- Xiaohongshu cover 3:4 at 1080×1440 (woshipm.com, huasheng.ai); a centre crop of 9:16 loses 240 px top and bottom, so
  a top title is cut — export a dedicated cover. Cover title 3–7 characters, ≤15 total.
- Pacing (third-party): a visible change every 2–4 s; a new information point every 5–10 s (opus.pro; Sina, Zhihu).

## 3. Sound

- No official LUFS for TikTok/Reels/Shorts/Douyin/Xiaohongshu; −14 LUFS is convention (forasoft.com 2026 table).
  EBU R128 s1 (ads): max short-term ≤ programme + 5 LU, TP ≤ −1 dBTP; LRA is meaningless under ~1 min
  (tech.ebu.ch/docs/r/r128s1.pdf). Lossy delivery: TP −2 (U).
- Measured on this pipeline: single-pass loudnorm landed 1.5–1.7 LU low (pre-limiter peaks +1.1 dBTP); the output was
  96 kHz (loudnorm upsamples) — AAC wants ≤48 kHz (`aresample=48000`).
- Voice over music: ≥10 LU for commentary over music, ≥15 over ambience (Torcoli et al., JAES 2019); WCAG 1.4.7 asks
  20 dB. Ducking 6–12 dB, attack 30–80 ms, release 250–700 ms (vendor). ffmpeg `sidechaincompress` with `apad` on the
  sidechain (or the music drops to silence when the voice ends).
- Sync: EBU R37 — audio early ≤40 ms, late ≤60 ms (tech.ebu.ch/publications/r037): a cue leads by ≤1 frame at 30 fps,
  aligned by its PEAK, not its start (morphic.com, pixflow.net).
- A whoosh is band-limited noise whose band SWEEPS (e.g. 300 Hz→6 kHz over the move, U); flat noise × envelope reads as
  hiss. Identical cues on every call machine-gun: jitter pitch/gain per occurrence (U).
- Redistributable samples: only CC0 is safe to vendor (Kenney.nl all CC0; Freesound CC0 filter). Pixabay forbids
  standalone redistribution.

## 4. Texture (not yet adopted)

- Shadows: 4–5 layers, offsets/blur doubling 1,2,4,8,16 px, alpha 0.075–0.2, one light, hue-tinted
  (joshwcomeau.com/css/designing-shadows). Raycast window: `0 4px 40px 8px #0006, 0 0 0 .5px #000c, inset 0 .5px
  #ffffff4d`. A top inset highlight; a rim light masked by a radial gradient that follows a point (linear.app `.shine`).
- Grain: a STATIC tile at 0.10–0.12 opacity removes banding on dark smooth grounds (CAMBI 4.66→~1.0, +29% bytes);
  per-frame grain is WORSE after x264 (measured). Gate banding with libvmaf `cambi` (>~5 annoying).
- Remotion ≥4.0.500 transitions (pushCut, blurSlide, lightLeak overlay) — the pinned 4.0.486 lacks them. HtmlInCanvas
  effects over CSS-3D content were not byte-identical between renders (measured).
