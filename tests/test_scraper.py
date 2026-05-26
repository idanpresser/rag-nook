import pytest
from pathlib import Path
from core.scraper import ResilientScraper, DocumentCompiler

def test_scraper_extract_article(mocker):
    # Mock the HTTP response from requests
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = (
        "<html>"
        "<head><title>Test Tech Blog</title></head>"
        "<body>"
        "<article>"
        "<h1>Awesome Coding Tools</h1>"
        "<p>This is a test article describing the benefits of modern coding pipelines.</p>"
        "</article>"
        "</body>"
        "</html>"
    )
    
    # Patch the session GET request
    mocker.patch("requests.Session.get", return_value=mock_response)
    
    scraper = ResilientScraper()
    title, content = scraper.scrape("https://example.com/coding-tools")
    
    assert title == "Test Tech Blog"
    assert "Awesome Coding Tools" in content or "modern coding pipelines" in content

def test_document_compiler_markdown(temp_workspace):
    scraped_dir = temp_workspace["scraped"]
    compiler = DocumentCompiler(scraped_dir=scraped_dir)
    
    title = "UnigetUI Release Notes"
    content = "# Release 3.1.1\n\n- Package Manager support for Windows winget.\n- Sleek UI changes."
    slug = "unigetui-3-1-1"
    
    md_path = compiler.save_markdown(title, content, slug)
    
    assert Path(md_path).exists()
    assert md_path.endswith("unigetui-3-1-1.md")
    
    saved_content = Path(md_path).read_text(encoding="utf-8")
    assert "Release 3.1.1" in saved_content
    assert "Package Manager support" in saved_content

def test_document_compiler_pdf(temp_workspace):
    scraped_dir = temp_workspace["scraped"]
    compiler = DocumentCompiler(scraped_dir=scraped_dir)
    
    title = "Painkillers vs Vitamins"
    content = "This document describes the critical business comparison between painkillers and vitamins."
    slug = "painkillers-vs-vitamins"
    
    pdf_path = compiler.save_pdf(title, content, slug)
    
    assert Path(pdf_path).exists()
    assert pdf_path.endswith("painkillers-vs-vitamins.pdf")
    
    # Ensure it's a valid PDF by checking the header signature
    with open(pdf_path, "rb") as f:
        signature = f.read(4)
        assert signature == b"%PDF"
