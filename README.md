# topic-to-video: any topic, made into a short video

<p align="center">
  <a href="README_CN.md"><strong>简体中文</strong></a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude_Code-supported-5b5bd6">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-111827">
  <img alt="Output: MP4 + SRT" src="https://img.shields.io/badge/output-MP4_%2B_SRT-0f766e">
  <img alt="Free by default" src="https://img.shields.io/badge/voice-free_by_default-2f6feb">
</p>

> **Give it a subject — "how does an espresso machine make a shot", "why a city grew past its own border" — and get back a one-to-two-minute narrated video with captions, where every fact on screen comes from a source it can show you.**

Chat with it in Claude Code or Codex. It isn't a text-to-video model painting frames. It works the way a small explainer studio does: it researches the topic (or reads your slides), writes a script, voices it, designs each shot around what that line is saying, builds the drawings the topic needs when its library doesn't have them, renders the film, and checks the result before handing it over.

What you get, and what to expect:

- 🔎 **Sourced, not invented.** Every date and figure in the narration is pinned to a quote from a page it fetched. Where sources disagree, it picks the defensible reading and says so in the brief. If it can't source a number, the film says it qualitatively instead.
- 🎬 **Designed shot by shot.** It picks from a library of 194 hand-built shot designs: cutaway plates, compare panels, routes, timelines, phone demos, data stages. When a film needs something the library doesn't have (a coffee puck in section, a scale's load cell, a city's growth drawn to scale), it builds that object or shot for the film, then checks it reads with the caption covered.
- 🗣️ **Narrated and captioned in any language.** A free neural voice by default (edge-tts), word-synced captions burned onto the frame's own background, Chinese included. It can voice an English deck in Chinese, or the other way round.
- 🧪 **Checked before you see it.** Text inside the frame, captions not colliding with content, audio in sync, no text jittering as the camera moves, no placeholder copy left on screen. The checks run on the rendered frames, not on the plan.
- 📐 **Any canvas.** 16:9, vertical 9:16, square 1:1 and more. Each shot recomposes for the frame instead of being cropped.

Honest limits: it runs locally and makes a **file** (MP4 plus SRT, copied to your Desktop). No cloud, no share links. A polished five-shot film takes real agent time: our test films took one to two hours each, most of it planning, building and checking; a full render itself takes a couple of minutes.

<p align="center">
  <a href="#example-films"><strong>Example films</strong></a> ·
  <a href="#what-makes-it-different"><strong>What's different</strong></a> ·
  <a href="#two-tiers-which-one-to-pick"><strong>Two tiers</strong></a> ·
  <a href="#how-it-works"><strong>How it works</strong></a> ·
  <a href="#quick-start"><strong>Quick start</strong></a> ·
  <a href="#troubleshooting"><strong>Troubleshooting</strong></a>
</p>

## Example films

Stills from four films made from a one-line topic, in Chinese. Each drawing below was built by the film itself, not picked from stock.

<table>
  <tr>
    <td align="center" width="33%">
      <img src="docs/assets/mri-precession.jpg" alt="MRI film: a proton tipped flat by a radio pulse, still turning, inducing a signal in a coil"><br/>
      <sub><strong>How MRI turns the body into an image</strong><br/>a proton tipped by a radio pulse keeps turning and sends a signal to the coil</sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/assets/espresso-puck.jpg" alt="Espresso film: loose grounds leak water down channels; a tamped puck lets it down evenly"><br/>
      <sub><strong>How an espresso machine pulls a shot</strong><br/>loose grounds leak through channels; a tamped puck lets water down evenly</sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/assets/espresso-extraction.jpg" alt="Espresso film: three grinds side by side — too fast and sour, about 25 seconds and balanced, too slow and bitter"><br/>
      <sub><strong>Same film, the payoff</strong><br/>resistance sets the time, and the time sets the taste</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <img src="docs/assets/scale-cutaway.jpg" alt="Product launch film: cutaway of a smart coffee scale with numbered parts"><br/>
      <sub><strong>Launching a concept smart scale</strong><br/>a cutaway plate: weight bends the load cell, the board reads it, Bluetooth sends it</sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/assets/scale-app-sync.jpg" alt="Product launch film: the scale and the phone app show the same 240 g pour at once"><br/>
      <sub><strong>Same film, the climax</strong><br/>one pour, read live on the scale and on the phone</sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/assets/shenzhen-growth.jpg" alt="City film: Shenzhen's built-up area drawn to scale, from 3 to 962 square kilometres"><br/>
      <sub><strong>Shenzhen: from border town to megacity</strong><br/>built-up area drawn to scale, 3 → 962 km², past the old zone's line</sub>
    </td>
  </tr>
</table>

## What makes it different

Most "AI video" tools fall into one of two camps. Some are generative models: impressive motion, but they can't keep a fact straight or put a label in the right place. Others are template slideshows: your text over stock footage. topic-to-video sits elsewhere. **Every frame is drawn as code**: real type, real diagrams, real data. So it can be exact, and it can be checked.

- **The visual says the thing.** Each shot is chosen and built for what its line of narration claims. Hide the caption and the picture should still carry the idea. Built objects are tested against exactly that before rendering.
- **Facts carry receipts.** The brief keeps each figure next to the quote it came from, so you can audit a film line by line.
- **Real places, real credits.** When a topic needs a real photo or map, it fetches a license-clean image from Wikimedia Commons and credits it on screen.
- **It notices its own mistakes.** Its checks measure the rendered video. One example: a check reads every frame for text that steps a pixel at a time during a slow camera move, a flaw no screenshot shows.
- **You stay in charge of taste.** It shows you a render early, you say what to change, and it re-renders only the shots that changed (and the cut into the next one).

## How it works

1. **Brief.** It asks a few questions (what the video is for, language, length, vertical or wide, which visual tier), then researches the topic or reads your deck. Facts go into a sourced brief.
2. **Plan.** A script, one beat per idea, and a design direction for the whole film: type, colour, how shots cut.
3. **Build.** For each beat it picks a shot from the library, or builds the object or shot the beat needs in the film's own workshop.
4. **Voice.** It narrates each beat and times captions and on-screen reveals to the spoken words.
5. **Render and check.** It renders the film and runs the frame, caption, audio and motion checks, then copies the MP4 and SRT to your Desktop.

## Two tiers: which one to pick

Every film is made by one of two renderers. They're built for different jobs. The skill suggests one from what the video is for, and you choose.

| | **Cinematic tier** (Remotion) | **Page tier** (HTML) |
| --- | --- | --- |
| What a shot is | A hand-built animated shot from a library of 194 designs (cutaways, compare panels, routes, phone demos, data stages), plus objects the film builds for itself | A designed page per beat (flows, timelines, comparisons, tables, charts, code, equations), laid out for that content |
| Motion | Camera pushes and pans, depth and 3D-style staging, cuts planned across the whole film | Each point appears on the word that names it, timed to the voice |
| One look for the film | A design direction (type, colour, motif) carried through every shot | A theme and page styles; editorial and print looks suit it well |
| Editing | Re-renders the shot you changed and the cut into the next one | Re-renders just the page you changed; a quick preview mode too |
| Needs | Node.js (`npm install` once) and a bit more memory | Chrome only |
| **Best for** | **Product launches, promos, stories, how-a-mechanism-works films**, anything where motion carries the explanation | **Teaching, how-tos, research briefings, narrating a deck**, anything with dense tables, figures or step-by-step text |

Pitches and overviews can go either way: evidence-heavy ones suit pages, story-led ones suit the cinematic tier. If you just want your own slides narrated as they are, there's a third option that shows each slide full-frame with gentle motion and needs only ffmpeg.

## Quick start

### Step 1: Install

You need **Python 3.9+**, **ffmpeg**, and **Google Chrome** (used headless to draw frames). Add **Node.js** for the cinematic tier, and **LibreOffice** if you'll feed it .pptx files.

| OS | ffmpeg | LibreOffice (for .pptx input) |
| --- | --- | --- |
| macOS | `brew install ffmpeg` | `brew install --cask libreoffice` |
| Linux | `sudo apt install ffmpeg` | `sudo apt install libreoffice` |

Then install the skill and its Python packages:

```bash
# Claude Code
git clone --depth 1 https://github.com/addsumtech/topic-to-video.git ~/.claude/skills/topic-to-video
# Codex
git clone --depth 1 https://github.com/addsumtech/topic-to-video.git ~/.agents/skills/topic-to-video

python3 -m pip install pillow pymupdf python-pptx edge-tts
```

For the cinematic tier, run this once:

```bash
cd ~/.claude/skills/topic-to-video/remotion && npm install
```

Or install the skill alone with [`npx skills`](https://github.com/vercel-labs/skills): `npx skills add addsumtech/topic-to-video`. You still need the tools above.

### Step 2: Ask for a video

Start a chat and describe the video:

```text
Make a 90-second video explaining how an espresso machine pulls a shot.
```

```text
做一个讲解视频：深圳是怎么从边境小镇变成超大城市的，竖屏，中文配音。
```

```text
Turn slides/q3-review.pptx into a narrated video with a Chinese voice-over.
```

It interviews you briefly, shows you the plan, renders, and tells you where the file landed. You don't have to say "skill". Asking for a video about a topic or from slides is enough.

## Best-fit scenarios

- **Explainers and teaching:** how something works, why something happens, one idea per beat.
- **Product launches and demos:** a concept product, an app flow on a phone, a feature walkthrough.
- **Places and history:** a city, an era, a timeline, with real credited photos where they help.
- **Your existing deck, narrated:** a talk or report turned into a video, in its own language or another.
- **Pairs with [slide-maker](https://github.com/addsumtech/slides_maker):** make the deck there, narrate it here.

## Troubleshooting

- **Something missing?** Run `python3 scripts/doctor.py` from the skill folder. It lists each tool, what it's for, and the exact install command.
- **No voice / edge-tts fails:** edge-tts needs a network connection. Offline on macOS, it falls back to the system `say` voice.
- **Cinematic tier not offered:** run `npm install` in `remotion/` (see Step 1).
- **Can't find the video:** it's copied to your Desktop (or Downloads if the Desktop isn't writable), named after the film's title.

## License

[MIT](LICENSE)
