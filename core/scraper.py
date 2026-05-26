import os
import re
import requests
from bs4 import BeautifulSoup
import trafilatura
from markdownify import markdownify as md
from fpdf import FPDF
from pathlib import Path
from typing import Tuple
from config import config

class ResilientScraper:
    """A resilient web scraper designed to extract article titles and clean text.

    Uses desktop User-Agents, session retries, and dual-layer parsing (Trafilatura + BeautifulSoup).
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })

    def scrape(self, url: str) -> Tuple[str, str]:
        """Scrapes a URL and returns a tuple of (title, clean_text_content).

        Args:
            url: The HTTP/HTTPS target link.

        Returns:
            A tuple of (title_string, content_string).
        """
        try:
            response = self.session.get(
                url,
                timeout=config.request_timeout_seconds,
                allow_redirects=True
            )
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            # Return graceful error info instead of crashing the pipeline
            return f"Scrape Failed: {url}", f"Unable to retrieve webpage content. Error: {str(e)}"

        # 1. Parse Title using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        title = "Untitled Page"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # 2. Extract Main Content using Trafilatura (advanced main-article text extractor)
        content = trafilatura.extract(html_content, include_links=True)
        
        # 3. Fallback to basic HTML parser if Trafilatura fails to detect article structure
        if not content:
            paragraphs = []
            # Gather all headers, paragraphs, and list items
            for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
                text = element.get_text().strip()
                if text:
                    paragraphs.append(text)
            content = "\n\n".join(paragraphs)

        return title, content

class CleanPDF(FPDF):
    """Custom FPDF layout manager providing headers, footers, and margins."""
    
    def __init__(self, title_str: str):
        super().__init__()
        self.title_str = title_str

    def header(self):
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        # Resiliently handle title text
        safe_title = self.title_str.encode("latin-1", "replace").decode("latin-1")
        self.cell(0, 10, f"Scraped Report: {safe_title}", border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        # Simple aesthetic divider line
        self.set_draw_color(200, 200, 200)
        self.line(10, 18, 200, 18)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

class DocumentCompiler:
    """Compiles extracted text pages into beautiful clean Markdown and PDF files."""

    def __init__(self, scraped_dir: Path = config.scraped_dir):
        self.scraped_dir = scraped_dir
        os.makedirs(self.scraped_dir, exist_ok=True)

    def _sanitize_filename(self, slug: str) -> str:
        """Cleans filenames to avoid OS-level conflicts."""
        # Replace non-alphanumeric or non-hyphen with underscores
        clean = re.sub(r"[^\w\-]", "_", slug)
        return clean.strip("_")

    def save_markdown(self, title: str, content: str, slug: str) -> str:
        """Saves scraped content as a clean Markdown file.

        Returns:
            The absolute path of the generated markdown file.
        """
        filename = f"{self._sanitize_filename(slug)}.md"
        filepath = self.scraped_dir / filename
        
        md_text = f"# {title}\n\n{content}\n"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_text)
            
        return str(filepath.resolve())

    def save_pdf(self, title: str, content: str, slug: str) -> str:
        """Saves scraped content as a clean PDF file with auto-wrap and headers.

        Returns:
            The absolute path of the generated PDF file.
        """
        filename = f"{self._sanitize_filename(slug)}.pdf"
        filepath = self.scraped_dir / filename

        # Create custom PDF with header details
        pdf = CleanPDF(title)
        pdf.add_page()
        pdf.set_font("helvetica", size=10)
        pdf.set_text_color(33, 33, 33)

        # Title Block
        pdf.set_font("helvetica", "B", 16)
        safe_title = title.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 10, text=safe_title)
        pdf.ln(6)

        # Content Block
        pdf.set_font("helvetica", size=10)
        
        # Replace characters not supported by standard FPDF helvetica core font (Latin-1)
        safe_content = content.encode("latin-1", "replace").decode("latin-1")
        
        # Write lines with standard margins
        pdf.multi_cell(0, 6, text=safe_content)

        pdf.output(str(filepath))
        return str(filepath.resolve())
