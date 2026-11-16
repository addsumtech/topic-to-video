import os, json, shutil, pytest
import ingest, storyboard as sb

def test_ingest_pdf(tmp_path, fixtures_dir):
    out = tmp_path / "proj"
    data = ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), str(out))
    sb.validate(data)
    assert len(data["slides"]) == 2
    assert os.path.exists(os.path.join(out, "frames", "01.png"))

def test_ingest_image_folder(tmp_path, fixtures_dir):
    out = tmp_path / "proj"
    data = ingest.ingest(os.path.join(fixtures_dir, "images"), str(out))
    assert len(data["slides"]) == 2
    assert data["slides"][1]["index"] == 2

def test_ingest_pptx_pulls_notes(tmp_path, fixtures_dir):
    if ingest._common.find_soffice() is None:
        pytest.skip("LibreOffice not installed")
    out = tmp_path / "proj"
    data = ingest.ingest(os.path.join(fixtures_dir, "deck.pptx"), str(out))
    assert len(data["slides"]) == 2
    assert "scanner" in data["slides"][0]["notes"].lower()


def test_natural_sort_orders_slide10_after_slide2():
    import ingest
    files = ["/x/Slide1.png", "/x/Slide10.png", "/x/Slide2.png", "/x/Slide11.png", "/x/Slide3.png"]
    names = [f.split("/")[-1] for f in sorted(files, key=ingest._natkey)]
    assert names == ["Slide1.png", "Slide2.png", "Slide3.png", "Slide10.png", "Slide11.png"]


def test_a_phone_photo_comes_in_upright_and_as_a_png(tmp_path):
    """EXIF orientation applied, and the frame IS a PNG (it was the JPEG's bytes under a .png name, on its side)."""
    from PIL import Image
    import ingest
    src = tmp_path / "in"
    src.mkdir()
    im = Image.new("RGB", (400, 200), (200, 30, 30))
    exif = Image.Exif()
    exif[0x0112] = 6                                   # "rotate 90 CW to view": a portrait phone shot
    im.save(src / "photo.jpg", exif=exif)
    out = tmp_path / "out"
    ingest.ingest(str(src), str(out))
    with Image.open(out / "frames" / "01.png") as f:
        assert f.format == "PNG" and f.size == (200, 400), (f.format, f.size)


def test_a_small_pdf_page_is_rendered_at_the_frame_s_width(tmp_path):
    import fitz
    import ingest
    pdf = tmp_path / "small.pdf"
    doc = fitz.open()
    doc.new_page(width=720, height=405)                # a 10 x 5.6 in page: 1500 px at 150 dpi
    doc.save(str(pdf))
    paths = ingest._render_pdf(str(pdf), str(tmp_path), dpi=150)
    from PIL import Image
    with Image.open(paths[0]) as f:
        assert f.size[0] >= ingest.MIN_PAGE_PX, f.size
