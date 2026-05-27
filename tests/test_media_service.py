import pytest
from pathlib import Path
from PIL import Image
from core.media import MediaOptimizer
from services.media_service import OCRProcessor

def test_media_optimizer_success(tmp_path):
    # Create a dummy image for testing
    img_path = tmp_path / "test_image.png"
    img = Image.new("RGB", (200, 200), color="red")
    img.save(img_path)

    optimizer = MediaOptimizer()
    
    # Run optimization
    opt_path = optimizer.optimize_image(img_path)
    
    assert opt_path.exists()
    assert opt_path.suffix == ".avif"
    
    # Generate thumbnail
    thumb_base64 = optimizer.generate_thumbnail_base64(img_path)
    assert thumb_base64.startswith("data:image/")
    assert "base64," in thumb_base64


def test_media_optimizer_real_world():
    real_img = Path("/Users/idaneyal/DEV/personal_momory/Anat/IMG-20160509-WA0001.jpg")
    optimizer = MediaOptimizer()
    opt_path = optimizer.optimize_image(real_img)
    
    assert opt_path.exists()
    assert opt_path.suffix == ".avif"


def test_media_optimizer_non_existent():
    optimizer = MediaOptimizer()
    with pytest.raises(FileNotFoundError):
        optimizer.optimize_image(Path("non_existent_image.png"))


def test_ocr_processor(tmp_path):
    # Create dummy image for testing OCR fallback/mock
    img_path = tmp_path / "receipt.png"
    img = Image.new("RGB", (100, 50), color="white")
    img.save(img_path)
    
    processor = OCRProcessor()
    text = processor.extract_text(img_path)
    assert isinstance(text, str)
