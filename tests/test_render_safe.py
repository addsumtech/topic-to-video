"""The html tier's platform-safe portrait profile (render.py `_platform_safe`): a 9:16 film's caption, page and brand
bug kept clear of the platform's own UI, read from remotion/src/runtime/safeZone.ts like the remotion tier."""
import json
import os

import pytest
from PIL import Image, ImageDraw

import _common
import render
import storyboard as sb
import text_safe_qa as tq
from _caption_band import aspect_table, caption_band_px, caption_margin_px

PROF = tq.safe_profile()
W9, H9 = aspect_table()["9:16"]
CJK = "抖音和小红书会在竖屏视频的底部叠加说明文字与作者信息，右侧还有一列点赞评论和分享按钮，所以字幕要放在它们碰不到的地方"
LATIN = "The caption has to end above the description and author line and short of the button column on the right side"


def _geom(W=W9, H=H9):
    return render._platform_safe({}, W, H)


# ── the profile and where it applies ────────────────────────────────────────────────────────────────────────────

def test_profile_reads_the_caption_scale_and_action_safe_border_from_the_runtime():
    src = open(os.path.join(tq._REMOTION, "src", "runtime", "safeZone.ts"), encoding="utf-8").read()
    assert "SAFE_CAPTION_SCALE = %s" % ("%g" % PROF["caption_scale"]) in src
    assert 0 < tq.action_safe_frac() < 0.2


def test_applies_to_a_full_screen_vertical_film_only():
    for name, (w, h) in aspect_table().items():
        g = render._platform_safe({}, w, h)
        assert (g is not None) == tq.safe_applies(w, h), name
    assert _geom() is not None                                  # 9:16 — the default is "social"
    assert render._platform_safe({"safe_zone": "social"}, W9, H9) is not None


@pytest.mark.parametrize("meta", [{"safe_zone": "none"}, {"safe_zone": ""}, {"safe_zone": None}, {"safe_zone": False},
                                  {"caption_mode": "band"}])
def test_opt_outs_and_band_mode_render_as_before(meta):
    assert render._platform_safe(meta, W9, H9) is None


def test_an_unknown_profile_is_refused_not_ignored():
    with pytest.raises(sb.StoryboardError, match="safe_zone"):
        render._platform_safe({"safe_zone": "tiktok"}, 1920, 1080)


# ── the geometry (pure) ─────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wh", [(1080, 1920), (720, 1280), (1440, 2560), (1081, 1921), (607, 1080)])
def test_geometry_matches_film_tsx_and_stays_out_of_the_platform_ui(wh):
    W, H = wh
    g = render._safe_geometry(W, H, PROF, tq.action_safe_frac(), caption_band_px(W, H), caption_margin_px(W, H))
    # the scaled frame: k of the film, centred across, from y0 — every offset even (ffmpeg pads yuv420p on even px)
    assert abs(g["fw"] - PROF["k"] * W) <= 1 and abs(g["fh"] - PROF["k"] * H) <= 1
    assert all(g[k] % 2 == 0 for k in ("fw", "fh", "x0", "y0"))
    assert abs(g["x0"] - (W - g["fw"]) / 2) <= 1 and abs(g["y0"] - PROF["y0"] * H) <= 1
    assert g["x0"] + g["fw"] <= W and g["y0"] + g["fh"] <= H
    # the caption: bottom on captionBottomY (within Math.round), above the platform's bottom share
    want = PROF["y0"] * H + PROF["k"] * H - caption_margin_px(W, H)
    assert abs(g["cap_bottom"] - want) <= 0.5 and g["cap_bottom"] <= H * (1 - PROF["bottom"])
    # …its lines may not climb above the scaled page's own caption band
    assert g["cap_bottom"] - g["cap_room"] >= PROF["y0"] * H + PROF["k"] * (H - caption_band_px(W, H)) - 1
    # a centred line of the full measure ends left of the button column
    assert (W + g["measure"]) / 2 <= W * (1 - PROF["right"]) and g["measure"] <= int(W * 0.9)
    assert g["bug_top"] >= PROF["top"] * H
    assert g["fade_x"] == pytest.approx(tq.action_safe_frac() * g["fw"])


def test_caption_margin_is_film_tsx_cap_margin():
    import math
    import _caption_band as cb
    frac = cb._fracs()["CAPTION_MARGIN_FRAC"]
    for w, h in [(1080, 1920), (1920, 1080), (720, 1280), (1081, 1921)]:
        assert caption_margin_px(w, h) == math.floor(min(w, h) * frac + 0.5)   # Math.round, not round-half-even


# ── the wrap: push-out kinsoku on a hard measure ──────────────────────────────────────────────────────────────

def _d():
    return ImageDraw.Draw(Image.new("RGB", (4, 4)))


def test_strict_wrap_never_passes_the_measure_and_never_starts_a_line_with_a_closer():
    font = render._load_font(49, render._font_path({"language": "zh"}, CJK))
    d = _d()
    hits = 0
    for n in range(8, 40):                    # sweep the measure so a closer lands on a line end many times
        mw = int(font.size * n + font.size * 0.4)
        hung = render._wrap(d, CJK, font, mw)
        strict = render._wrap(d, CJK, font, mw, hang=False)
        assert "".join(strict) == "".join(hung) == CJK.replace(" ", "")
        assert all(d.textlength(ln, font=font) <= mw for ln in strict), (n, strict)
        assert not any(ln[0] in "，。、：；！？…）』」》%" for ln in strict[1:]), strict
        hits += any(d.textlength(ln, font=font) > mw for ln in hung)
    assert hits, "no measure put a closer on a line end — the test lost its point"


def test_default_wrap_is_unchanged():
    font = render._load_font(43, render.BUNDLED_FONT)
    d = _d()
    assert render._wrap(d, LATIN, font, 900) == render._wrap(d, LATIN, font, 900, hang=True)


# ── the caption: size, fit and where its ink lands ─────────────────────────────────────────────────────────────

def test_short_caption_takes_the_safe_size_step():
    g = _geom()
    font, lines = render._safe_caption_fit(_d(), "短句", W9, H9, {"language": "zh"}, g)
    assert font.size == render._caption_font_px(W9, H9, safe_scale=PROF["caption_scale"]) > render._caption_font_px(W9, H9)
    assert lines == ["短句"]


@pytest.mark.parametrize("text", [CJK[:33], LATIN, LATIN + " " + LATIN])
def test_a_long_caption_yields_size_to_fit_its_band(text):
    g = _geom()
    font, lines = render._safe_caption_fit(_d(), text, W9, H9, {"language": "zh"}, g)
    a, de = font.getmetrics()
    assert (a + de) * len(lines) <= g["cap_room"] or font.size == 12


def _ink_box(png):
    a = Image.open(png).getchannel("A")
    return a.point(lambda v: 255 if v > 40 else 0).getbbox()


@pytest.mark.parametrize("text,kw", [(CJK[:30], {}), (LATIN, {}), (LATIN, {"hl_word": 3}),
                                     (CJK[:30], {"hl_span": [4, 9]})])
def test_safe_caption_ink_stays_out_of_the_platform_ui(tmp_path, text, kw):
    g = _geom()
    p = str(tmp_path / "c.png")
    render._caption_layer(text, W9, H9, p, {"language": "zh", "_out": str(tmp_path)}, safe=g, **kw)
    x0, y0, x1, y1 = _ink_box(p)
    assert x1 <= W9 * (1 - PROF["right"]), "caption ink runs to x %d, under the button column" % x1
    # (bbox bounds are exclusive) the ink — its outline included — ends ON captionBottomY, above the platform's bottom
    assert y1 <= g["cap_bottom"] <= H9 * (1 - PROF["bottom"]), "caption ink reaches y %d" % y1
    assert y0 >= g["cap_bottom"] - g["cap_room"] - 2, "caption climbs onto the scaled page (top %d)" % y0
    assert x0 >= W9 * PROF["right"] - 2                         # centred: as far from the left edge


def test_without_a_profile_the_caption_layer_is_byte_identical(tmp_path):
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    render._caption_layer(LATIN, W9, H9, a, {})
    render._caption_layer(LATIN, W9, H9, b, {}, safe=None)
    assert open(a, "rb").read() == open(b, "rb").read()


# ── the frame layer, the bug, the cache key ──────────────────────────────────────────────────────────────────

def test_frame_layer_is_ground_outside_clear_inside_and_ramps_over_the_action_safe_border(tmp_path):
    g = _geom()
    p = render._safe_frame_png(W9, H9, g, (10, 20, 30), str(tmp_path / "f.png"))
    im = Image.open(p)
    a = im.getchannel("A")
    assert im.getpixel((5, 5))[:3] == (10, 20, 30)
    assert a.getpixel((g["x0"] - 1, H9 // 2)) == 255 and a.getpixel((W9 // 2, g["y0"] + g["fh"])) == 255
    bx, by = int(g["fade_x"]) + 1, int(g["fade_y"]) + 1
    inner = a.crop((g["x0"] + bx, g["y0"] + by, g["x0"] + g["fw"] - bx, g["y0"] + g["fh"] - by))
    assert inner.getextrema() == (0, 0), "the page's own pixels must pass untouched inside the border"
    row = [a.getpixel((g["x0"] + i, H9 // 2)) for i in range(bx + 1)]
    assert row == sorted(row, reverse=True) and row[0] > 240 and row[-1] == 0


def test_brand_bug_sits_below_the_tabs_on_a_safe_film(tmp_path):
    os.makedirs(tmp_path / "brand")
    Image.new("RGBA", (120, 40), (200, 50, 20, 255)).save(tmp_path / "brand" / "l.png")
    meta = {"_out": str(tmp_path), "brand": {"logo": "brand/l.png", "placement": ["bug"]}}
    g = _geom()
    top = lambda p: Image.open(p).getchannel("A").getbbox()[1]
    assert top(render._brand_bug_png(meta, W9, H9, str(tmp_path / "a.png"), top=g["bug_top"])) >= PROF["top"] * H9
    assert top(render._brand_bug_png(meta, W9, H9, str(tmp_path / "b.png"))) < PROF["top"] * H9   # unchanged default


def test_fingerprint_keys_the_safe_geometry_only_where_it_applies():
    slide = {"index": 1, "type": "title", "props": {"title": "t"}, "narration": "x", "duration": 1.0}
    meta = {"_out": "/nonexistent"}
    fp = lambda m, W, H: render._fingerprint(slide, m, W, H, 2, True, W < H)
    assert fp(meta, W9, H9) != fp(dict(meta, safe_zone="none"), W9, H9)         # safe clips re-render
    assert fp(meta, 1920, 1080) == fp(dict(meta, safe_zone="none"), 1920, 1080)  # 16:9 keys unchanged
    assert fp(dict(meta, caption_mode="band"), W9, H9) != fp(meta, W9, H9)


def _gradient(path, W=W9, H=H9):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(30 + 60 * t), int(70 + 90 * (1 - t)), int(140 + 80 * t)))
    im.save(path)
    return path


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_margin_fill_is_decided_from_the_frames_own_edge(tmp_path):
    bg = (242, 239, 232)
    meta = {"_out": str(tmp_path)}
    open(tmp_path / "theme.css", "w").write(":root{--bg:#f2efe8}")
    png = str(tmp_path / "p.png")
    Image.new("RGB", (W9, H9), bg).save(png)
    assert render._safe_fill(meta, W9, H9, png) == {"uniform": True, "ground": bg, "std": 0.0}
    # a JPEG capture of the same ground is uniform, its pad the colour as DECODED (the graph composites that)
    jpg = str(tmp_path / "p.jpg")
    Image.new("RGB", (W9, H9), bg).save(jpg, quality=90)
    f = render._safe_fill(meta, W9, H9, jpg)
    assert f["uniform"] and max(abs(a - b) for a, b in zip(f["ground"], bg)) <= 3
    # type set inside the page's padding is not "a varied edge" — the ring measured is the action-safe border
    page = Image.new("RGB", (W9, H9), bg)
    ImageDraw.Draw(page).rectangle([80, 300, 1000, 420], fill=(20, 20, 20))
    page.save(png)
    assert render._safe_fill(meta, W9, H9, png)["uniform"]
    # a flat flood of another colour pads with ITS colour, not the deck's ground
    Image.new("RGB", (W9, H9), (200, 30, 30)).save(png)
    assert render._safe_fill(meta, W9, H9, png)["ground"] == (200, 30, 30)
    # a gradient to the edge is not a flat ground
    f = render._safe_fill(meta, W9, H9, _gradient(png))
    assert not f["uniform"] and f["std"] > render._SAFE_UNIFORM_STD
    # unreadable -> a solid pad of --bg
    assert render._safe_fill(meta, W9, H9, str(tmp_path / "missing.png"))["ground"] == bg


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_a_varied_frame_margin_continues_the_picture(tmp_path):
    out = str(tmp_path / "g")
    os.makedirs(os.path.join(out, "audio"))
    os.makedirs(os.path.join(out, "images"))
    _common.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=1", "-ar", "24000",
                 "-ac", "1", os.path.join(out, "audio", "01.wav")])
    open(os.path.join(out, "theme.css"), "w").write(":root{--bg:#f2efe8}")
    _gradient(os.path.join(out, "images", "g.png"))
    s = sb.new_slide(1, "images/g.png", narration="")
    s.update({"audio": "audio/01.wav", "duration": 1.0, "transition": "none",
              "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.0]}})
    data = sb.new_storyboard({"aspect": "9:16", "width": W9, "height": H9, "captions": False})
    data["slides"] = [s]
    json.dump(data, open(os.path.join(out, "storyboard.json"), "w"))
    mp4 = render.render(out)
    png = os.path.join(out, "f.png")
    _common.run(["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", mp4, "-frames:v", "1", png])
    im = Image.open(png).convert("RGB")
    g = _geom()
    for y in (g["y0"] + 200, H9 // 2, g["y0"] + g["fh"] - 200):
        margin, page = im.getpixel((10, y)), im.getpixel((g["x0"] + 60, y))
        assert max(abs(a - b) for a, b in zip(margin, page)) <= 12, (y, margin, page)   # continues the picture's row
        assert max(abs(a - b) for a, b in zip(margin, (242, 239, 232))) > 40              # not the deck's grey pad


# ── end to end: one programmatic scene through the real ffmpeg graph ─────────────────────────────────────────

def _board(out, captions=True, aspect="9:16"):
    os.makedirs(os.path.join(out, "audio"), exist_ok=True)
    _common.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=2", "-ar", "24000",
                 "-ac", "1", os.path.join(out, "audio", "01.wav")])
    open(os.path.join(out, "theme.css"), "w").write(":root{--bg:#f2efe8;--fg:#1d1d22;--accent:#c2410c;--on-accent:#fff}")
    s = sb.new_scene(1, "title", {"title": "Safe", "subtitle": "portrait"}, narration=LATIN + ".")
    s.update({"audio": "audio/01.wav", "duration": 2.0})
    w, h = aspect_table()[aspect]
    data = sb.new_storyboard({"aspect": aspect, "width": w, "height": h, "captions": captions, "transition": "none"})
    data["slides"] = [s]
    json.dump(data, open(os.path.join(out, "storyboard.json"), "w"))
    return render.render(out)


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_a_safe_portrait_render_scales_the_page_keeps_the_caption_clear_and_writes_a_cover(tmp_path):
    np = pytest.importorskip("numpy")
    on, off = str(tmp_path / "on"), str(tmp_path / "off")
    frames = []
    for out, cap in ((on, True), (off, False)):
        mp4 = _board(out, captions=cap)
        png = os.path.join(out, "f.png")
        _common.run(["ffmpeg", "-y", "-v", "error", "-ss", "1.0", "-i", mp4, "-frames:v", "1", png])
        frames.append(np.asarray(Image.open(png).convert("L"), dtype=float))
    ink = np.abs(frames[0] - frames[1]) > 40
    rows, cols = np.where(ink.any(axis=1))[0], np.where(ink.any(axis=0))[0]
    assert len(rows), "no caption was drawn"
    assert cols.max() <= W9 * (1 - PROF["right"]) and rows.max() <= H9 * (1 - PROF["bottom"])
    # the page is drawn in its scaled frame: its title (at 0.08 W on the page) now starts inside x0
    g = _geom()
    title_cols = np.where((frames[1][: H9 // 2] < 120).any(axis=0))[0]
    assert title_cols.min() >= g["x0"] + int(W9 * 0.08 * PROF["k"]) - 4
    cover = os.path.join(on, "out.cover.png")
    assert os.path.exists(cover) and Image.open(cover).size == (1080, 1440)


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_a_landscape_render_writes_no_cover(tmp_path):
    _board(str(tmp_path / "l"), aspect="16:9")
    assert not os.path.exists(str(tmp_path / "l" / "out.cover.png"))


# ── colour range: every clip limited, converted ────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_a_full_range_scene_first_no_longer_shifts_the_scenes_after_it(tmp_path):
    # an html scene's frames are Chrome JPEGs (full range); JPEG frames written here stand in for them, Chrome-free
    out = str(tmp_path)
    os.makedirs(os.path.join(out, "audio"))
    _common.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=1", "-ar", "24000",
                 "-ac", "1", os.path.join(out, "audio", "01.wav")])
    meta = {"_out": out, "fps": 10, "captions": False, "transition": "none"}
    clips = []
    for k, (ext, col) in enumerate((("jpg", (242, 239, 232)), ("png", (200, 60, 40)))):
        pat = os.path.join(out, f"f{k}_%04d.{ext}")
        for i in range(10):
            Image.new("RGB", (320, 180), col).save(pat % i, quality=95) if ext == "jpg" else \
                Image.new("RGB", (320, 180), col).save(pat % i)
        clip = os.path.join(out, f"c{k}.mp4")
        render._encode_frames_clip(pat, "audio/01.wav", 1.0, [], meta, 320, 180, clip, out, slide={"index": k})
        probe = _common.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=pix_fmt,color_range", "-of", "compact=p=0:nk=1", clip]).strip()
        assert probe.split("|")[:2] in (["yuv420p", "tv"], ["yuv420p", "unknown"]), probe
        clips.append(clip)
    lst = os.path.join(out, "list.txt")
    open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
    mp4 = os.path.join(out, "o.mp4")
    _common.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", mp4])
    for t, want in (("0.5", (242, 239, 232)), ("1.5", (200, 60, 40))):
        raw = subprocess_rgb(mp4, t, 320, 180)
        assert max(abs(a - b) for a, b in zip(raw, want)) <= 3, (t, raw, want)


def subprocess_rgb(mp4, t, W, H):
    import subprocess
    d = subprocess.run(["ffmpeg", "-v", "error", "-ss", t, "-i", mp4, "-frames:v", "1", "-vf",
                        "scale=flags=accurate_rnd+full_chroma_int+bitexact,format=rgb24", "-f", "rawvideo", "-"],
                       capture_output=True, check=True).stdout
    x, y = W // 2, H // 2
    return tuple(d[(y * W + x) * 3:(y * W + x) * 3 + 3])


# ── caption leading and band fit (every mode) ───────────────────────────────────────────────────────────────

_CJK3 = CJK + "所以字幕要放在它们碰不到的地方"
_LAT3 = LATIN + " of the frame, every single time it is posted"


def _ink_runs(png):
    a = Image.open(png).getchannel("A")
    rows = [a.crop((0, y, a.width, y + 1)).getextrema()[1] > 40 for y in range(a.height)]
    runs, start = [], None
    for y, r in enumerate(rows + [False]):
        if r and start is None:
            start = y
        if not r and start is not None:
            runs.append((start, y - 1)); start = None
    return runs


@pytest.mark.parametrize("aspect,extra", [("16:9", {}), ("9:16", {"safe_zone": "none"}), ("16:9", {"caption_mode": "band"}),
                                          ("9:16", {"caption_mode": "band"}), ("9:16", {})])
@pytest.mark.parametrize("text", [CJK[:33], LATIN[:81], _CJK3, _LAT3])
def test_caption_lines_never_touch_and_never_leave_their_band(tmp_path, aspect, extra, text):
    W, H = aspect_table()[aspect]
    meta = dict({"language": "zh", "_out": str(tmp_path)}, **extra)
    band = render._caption_band_px(meta, W, H)
    safe = render._platform_safe(meta, W, H)
    p = str(tmp_path / "c.png")
    render._caption_layer(text, W, H, p, meta, band=band, safe=safe)
    _, lines = render._caption_layout(_d(), text, W, H, meta, band=band, safe=safe)
    runs = _ink_runs(p)
    assert len(runs) == len(lines), "%d lines drew as %d ink runs — lines touch" % (len(lines), len(runs))
    if band:
        lo, hi = H, H + band
    elif safe:
        lo, hi = safe["cap_bottom"] - safe["cap_room"], safe["cap_bottom"]
    else:
        lo, hi = H - caption_band_px(W, H), H          # keyframe_qa keeps page content above this line
    assert runs[0][0] >= lo and runs[-1][1] < hi, (runs, lo, hi)


def test_band_strip_reserves_the_drawn_pitch():
    meta = {"caption_mode": "band"}
    for W, H in ((1920, 1080), (1080, 1920)):
        fp = render._caption_font_px(W, H, band=True, meta=meta)
        font = render._load_font(fp, render.BUNDLED_FONT)
        assert 2 * render._caption_line_h(font) + 2 * int(H * 0.012) <= render._caption_band_px(meta, W, H)


# ── validate's lint and the critic brief read the same geometry ─────────────────────────────────────────────

def test_validate_lints_the_caption_render_draws():
    import validate
    meta = {"aspect": "9:16", "language": "zh"}
    want = render._caption_layout(_d(), CJK[:33], W9, H9, meta, safe=_geom())[1]
    assert validate._caption_lines(CJK[:33], meta, W9, H9) == want
    plain = validate._caption_lines(CJK[:33], dict(meta, safe_zone="none"), W9, H9)
    assert plain != want and plain == render._caption_layout(_d(), CJK[:33], W9, H9, dict(meta, safe_zone="none"))[1]
    # a remotion board's caption is Film.tsx's; an unknown safe_zone is ERRORed elsewhere — neither crashes the lint
    assert validate._caption_lines(CJK[:33], dict(meta, renderer="remotion"), W9, H9) == plain
    assert validate._caption_lines(CJK[:33], dict(meta, safe_zone="tiktok"), W9, H9) == plain


def test_critic_brief_places_the_caption_where_the_delivered_film_has_it():
    import critic_brief
    g = _geom()
    safe_line = critic_brief._caption_band_line({"aspect": "9:16"})
    assert "%dx%d at (%d, %d)" % (g["fw"], g["fh"], g["x0"], g["y0"]) in safe_line
    assert "between y %d and %d" % (g["cap_bottom"] - g["cap_room"], g["cap_bottom"]) in safe_line
    assert "platform-safe" not in critic_brief._caption_band_line({"aspect": "9:16", "safe_zone": "none"})
    assert "platform-safe" not in critic_brief._caption_band_line({"aspect": "16:9"})
