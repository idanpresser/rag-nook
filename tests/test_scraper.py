import pytest
from pathlib import Path
import json
from core.scraper import ResilientCrawl4AIScraper, DocumentCompiler

class MockCrawlResult:
    """Mock result class matching Crawl4AI CrawlResult structure."""
    def __init__(self, success=True, markdown="", extracted_content="Test Page", media=None):
        self.success = success
        self.markdown = markdown
        self.extracted_content = extracted_content
        self.media = media or {"images": []}

def test_crawl4ai_scraper_extract_success(mocker):
    mock_result = MockCrawlResult(
        success=True,
        markdown="This is core article body content with an image ![logo](https://example.com/logo.png).",
        extracted_content="Awesome Programming Guide",
        media={
            "images": [
                {"src": "https://example.com/logo.png", "alt": "logo"}
            ]
        }
    )
    
    # Mock the AsyncWebCrawler's arun method
    mocker.patch("crawl4ai.AsyncWebCrawler.arun", return_value=mock_result)
    
    scraper = ResilientCrawl4AIScraper()
    title, markdown, images = scraper.scrape_url("https://example.com/guide")
    
    assert title == "Awesome Programming Guide"
    assert "This is core article body" in markdown
    assert len(images) == 1
    assert images[0]["src"] == "https://example.com/logo.png"
    assert images[0]["alt"] == "logo"

def test_document_compiler_saves_markdown_with_clickable_cached_images(temp_workspace, mocker):
    scraped_dir = temp_workspace["scraped"]
    compiler = DocumentCompiler(scraped_dir=scraped_dir)
    
    title = "Test Guide with Images"
    markdown = "Here is a logo: ![logo_alt](https://example.com/assets/logo.png) and some other text."
    images = [
        {"src": "https://example.com/assets/logo.png", "alt": "logo_alt"}
    ]
    slug = "test-guide-images"
    
    # Mock the requests.get call for downloading the image
    mock_img_response = mocker.Mock()
    mock_img_response.status_code = 200
    mock_img_response.content = b"fake-binary-image-content"
    mocker.patch("requests.get", return_value=mock_img_response)
    
    # Execute compiler saving
    md_path = compiler.save_markdown_with_images(title, markdown, images, slug)
    
    # 1. Assert markdown file exists
    assert Path(md_path).exists()
    assert md_path.endswith("test-guide-images.md")
    
    # 2. Assert local image directory and downloaded file exist
    local_img_dir = scraped_dir / "images" / slug
    assert local_img_dir.exists()
    
    downloaded_img_path = local_img_dir / "1_logo.png"
    assert downloaded_img_path.exists()
    assert downloaded_img_path.read_bytes() == b"fake-binary-image-content"
    
    # 3. Assert Markdown content has rewritten clickable links
    saved_md_text = Path(md_path).read_text(encoding="utf-8")
    
    # Clickable image format: [![logo_alt](images/slug/local_filename)](original_remote_url)
    expected_replacement = "[![logo_alt](images/test-guide-images/1_logo.png)](https://example.com/assets/logo.png)"
    assert expected_replacement in saved_md_text
    # Verify original unclickable Markdown image is removed
    assert "![logo_alt](https://example.com/assets/logo.png)" not in saved_md_text

def test_document_compiler_handles_hebrew_percent_encoded_images(temp_workspace, mocker):
    scraped_dir = temp_workspace["scraped"]
    compiler = DocumentCompiler(scraped_dir=scraped_dir)
    
    title = "Hebrew Image Guide"
    
    # Markdown contains percent-encoded Hebrew image URL
    markdown = "Here is a webinar image: ![וובינר](https://letsai.co.il/wp-content/uploads/2022/06/%D7%95%D7%95%D7%91%D7%99%D7%A0%D7%A8-AI.jpg)"
    
    # Crawl4AI returns Unicode Hebrew image URL in its images metadata list
    images = [
        {"src": "https://letsai.co.il/wp-content/uploads/2022/06/וובינר-AI.jpg", "alt": "וובינר"}
    ]
    slug = "hebrew-guide"
    
    mock_img_response = mocker.Mock()
    mock_img_response.status_code = 200
    mock_img_response.content = b"hebrew-image-binary-data"
    mocker.patch("requests.get", return_value=mock_img_response)
    
    # Execute compiler saving
    md_path = compiler.save_markdown_with_images(title, markdown, images, slug)
    
    assert Path(md_path).exists()
    
    # Verify the image was downloaded successfully
    local_img_dir = scraped_dir / "images" / slug
    assert local_img_dir.exists()
    
    # Verify the filename was cleaned and preserved
    downloaded_img_path = local_img_dir / "1_וובינר-AI.jpg"
    assert downloaded_img_path.exists()
    assert downloaded_img_path.read_bytes() == b"hebrew-image-binary-data"
    
    # Verify the Markdown content replaced the percent-encoded URL in the text with the local relative path
    saved_md_text = Path(md_path).read_text(encoding="utf-8")
    expected_replacement = "[![וובינר](images/hebrew-guide/1_וובינר-AI.jpg)](https://letsai.co.il/wp-content/uploads/2022/06/%D7%95%D7%95%D7%91%D7%99%D7%A0%D7%A8-AI.jpg)"
    assert expected_replacement in saved_md_text

