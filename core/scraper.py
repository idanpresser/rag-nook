import os
import re
import asyncio
import urllib.parse
import requests
import concurrent.futures
from pathlib import Path
from typing import Tuple, Dict, Any, List
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from config import config

class ResilientCrawl4AIScraper:
    """A resilient asynchronous web scraper built on Crawl4AI.

    Extracts high-fidelity Markdown, page title, and image assets cleanly.
    """

    def __init__(self):
        # Configure Crawl4AI runner settings
        self.run_config = CrawlerRunConfig(
            wait_for_images=True,
            scan_full_page=True,
            exclude_external_images=False
        )

    def scrape_url(self, url: str) -> Tuple[str, str, List[Dict[str, Any]]]:
        """Runs the asynchronous Crawl4AI crawler synchronously using an event loop.

        Automatically detects running event loops and delegates to a separate thread if needed to avoid event loop collisions.

        Args:
            url: The HTTP/HTTPS target link.

        Returns:
            A tuple of (title, clean_markdown, list_of_image_dicts).
        """
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # If there's already a running event loop (e.g. inside FastAPI/Uvicorn),
                # delegate execution to a separate thread to run asyncio.run safely.
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(self._async_scrape(url)))
                    return future.result()
            else:
                return asyncio.run(self._async_scrape(url))
        except Exception as e:
            # Fallback gracefully if event loop or scraping fails
            return f"Crawl Failed: {url}", f"Unable to crawl webpage content. Error: {str(e)}", []

    async def _async_scrape(self, url: str) -> Tuple[str, str, List[Dict[str, Any]]]:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url, config=self.run_config)
            
            if not result.success:
                return f"Crawl Failed: {url}", f"Failed to retrieve content. Status: {result.status_code}", []

            title = result.extracted_content or "Untitled Page"
            # Get clean fit_markdown if available, otherwise full markdown
            markdown_content = result.markdown or ""
            images = result.media.get("images", [])

            # Fallback: extract title from markdown if empty
            if title == "Untitled Page" and markdown_content.startswith("# "):
                title_line = markdown_content.split("\n")[0]
                title = title_line.replace("# ", "").strip()

            return title, markdown_content, images

class DocumentCompiler:
    """Compiles extracted Markdown pages, downloads images locally, and rewrites image embeds."""

    def __init__(self, scraped_dir: Path = config.scraped_dir):
        self.scraped_dir = scraped_dir
        os.makedirs(self.scraped_dir, exist_ok=True)

    def _sanitize_filename(self, slug: str) -> str:
        """Cleans slugs to avoid OS-level conflicts."""
        clean = re.sub(r"[^\w\-]", "_", slug)
        return clean.strip("_")

    def save_markdown_with_images(
        self,
        title: str,
        markdown: str,
        images: List[Dict[str, Any]],
        slug: str
    ) -> str:
        """Downloads webpage images locally and compiles them into a Markdown file with clickable links.

        Args:
            title: The title of the scraped webpage.
            markdown: The raw markdown content from the crawler.
            images: List of image dictionaries containing 'src' and 'alt'.
            slug: Saniztized identifier slug for directories.

        Returns:
            The absolute path of the generated markdown file.
        """
        clean_slug = self._sanitize_filename(slug)
        filename = f"{clean_slug}.md"
        filepath = self.scraped_dir / filename

        # Define local directory for downloaded images
        # e.g., output/scraped_pages/images/<slug>/
        local_img_dir = self.scraped_dir / "images" / clean_slug
        os.makedirs(local_img_dir, exist_ok=True)

        compiled_markdown = markdown

        for i, img in enumerate(images):
            src = img.get("src", "")
            alt = img.get("alt", "") or f"image_{i+1}"
            
            # Skip invalid, empty, or base64 embedded images
            if not src or not src.startswith("http"):
                continue

            # Safe encode the URL for requests and regex matching (e.g. handle Hebrew characters)
            try:
                parts = urllib.parse.urlsplit(src)
                path = urllib.parse.quote(urllib.parse.unquote(parts.path))
                query = urllib.parse.quote(urllib.parse.unquote(parts.query), safe="=&")
                fragment = urllib.parse.quote(urllib.parse.unquote(parts.fragment))
                src_encoded = urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, fragment))
            except Exception:
                src_encoded = src

            # Generate standard filename from URL (use unquoted version to get a cleaner readable name)
            try:
                unquoted_src = urllib.parse.unquote(src)
                url_filename = unquoted_src.split("/")[-1].split("?")[0]
            except Exception:
                url_filename = src.split("/")[-1].split("?")[0]
                
            # Ensure filename is clean and has a fallback extension
            url_filename = re.sub(r"[^\w\-\.]", "_", url_filename)
            if not url_filename or "." not in url_filename:
                url_filename = f"image_{i+1}.png"
                
            local_filename = f"{i+1}_{url_filename}" if len(url_filename) > 0 else f"image_{i+1}.png"

            # Download and save the image locally
            try:
                img_response = requests.get(src_encoded, timeout=config.request_timeout_seconds, headers={"User-Agent": config.user_agent})
                if img_response.status_code == 200:
                    img_filepath = local_img_dir / local_filename
                    with open(img_filepath, "wb") as f:
                        f.write(img_response.content)

                    local_rel_path = f"images/{clean_slug}/{local_filename}"

                    # Try to replace all possible variants of src in markdown:
                    # 1. src_encoded (standard percent-encoded)
                    # 2. unquoted version (unicode Hebrew)
                    # 3. raw src
                    # 4. Relative path versions
                    variants = {src, src_encoded, urllib.parse.unquote(src)}
                    for v in list(variants):
                        try:
                            parsed_v = urllib.parse.urlsplit(v)
                            variants.add(parsed_v.path)
                            variants.add(parsed_v.path.lstrip("/"))
                        except Exception:
                            pass

                    for var in variants:
                        if not var:
                            continue
                        # Regex match standard markdown image embeds for this specific src URL
                        # Matches: ![alt_text](src) or ![alt_text](src "title")
                        pattern = re.compile(rf"!\[([^\]]*?)\]\({re.escape(var)}(?:\s+[\"\'].*?[\"\'])?\)")
                        
                        # Rewrite as clickable locally cached image:
                        # [![alt_text](images/slug/local_filename)](original_remote_url)
                        compiled_markdown = pattern.sub(rf"[![\1]({local_rel_path})]({src_encoded})", compiled_markdown)
            except Exception:
                # Gracefully skip if image download fails, leaving original link intact
                continue

        # Write clean final Markdown document
        md_text = f"# {title}\n\n{compiled_markdown}\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_text)

        return str(filepath.resolve())
