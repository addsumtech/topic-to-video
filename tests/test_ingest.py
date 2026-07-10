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
