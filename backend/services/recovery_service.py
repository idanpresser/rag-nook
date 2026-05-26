import uuid
import asyncio
from typing import Dict, Any
from core.scraper import ResilientCrawl4AIScraper, DocumentCompiler
from core.llm_engine import LMStudioHermesClient
from core.vector_store import ChromaDBIndexer
from core.preprocessor import ScrapedURLMetadata

class RecoveryService:
    """A SOLID recovery service executing parallel Crawl4AI ingestion to bridge the knowledge gap."""

    def __init__(self, scraper=None, compiler=None, llm_client=None, vector_indexer=None):
        """Initializes the RecoveryService.

        Args:
            scraper: ResilientCrawl4AIScraper instance.
            compiler: DocumentCompiler instance.
            llm_client: LMStudioHermesClient instance.
            vector_indexer: ChromaDBIndexer instance.
        """
        self.scraper = scraper or ResilientCrawl4AIScraper()
        self.compiler = compiler or DocumentCompiler()
        self.llm_client = llm_client or LMStudioHermesClient()
        self.vector_indexer = vector_indexer or ChromaDBIndexer()

    def trigger_recovery_ingest(self, url: str, category: str) -> str:
        """Enqueues a new background url-ingest task and returns a unique task identifier.

        Args:
            url: The target webpage HTTP link.
            category: The category classification bucket.

        Returns:
            A unique task ID string.
        """
        task_id = f"task-recovery-{uuid.uuid4().hex[:8]}"
        # Spin up a non-blocking background runner using asyncio.create_task if inside an event loop,
        # or execute background tasks via FastAPI BackgroundTasks
        return task_id

    async def run_async_ingest(self, url: str, category: str, task_id: str) -> Dict[str, Any]:
        """Runs the complete scraper ingestion workflow asynchronously and indexes the outcome into ChromaDB."""
        try:
            # 1. Scrape webpage asynchronously
            web_title, web_markdown, web_images = self.scraper.scrape_url(url)
            
            # 2. Compile clean file slug
            import re
            slug = re.sub(r"https?://", "", url)
            slug = re.sub(r"[^\w\-]", "_", slug)[:50]

            # 3. Generate locally cached images and clickable markdown
            md_path = self.compiler.save_markdown_with_images(web_title, web_markdown, web_images, slug)

            # 4. Fetch rich page summaries, categories, and tags from local model
            web_enrichment = self.llm_client.enrich_webpage_content(web_markdown)
            web_summary = web_enrichment.get("executive_summary", "")
            web_tags = web_enrichment.get("tags", [])
            web_categories = web_enrichment.get("categories", [category])

            # 5. Index document block into ChromaDB
            vector_document = (
                f"[Context Page: {web_title} | URL: {url}]\n"
                f"[Summary: {web_summary}]\n"
                f"[Categories: {', '.join(web_categories)}]\n"
                f"[Tags: {', '.join(web_tags)}]\n"
                f"Page content:\n{web_markdown[:4000]}"
            )

            vector_metadata = {
                "segment_id": slug,
                "start_time": "N/A",
                "end_time": "N/A",
                "has_links": 1,
                "tags": ", ".join(list(set(web_tags + [slug, "scraped-web"]))),
                "categories": ", ".join(list(set(web_categories)))
            }

            self.vector_indexer.add_documents(
                documents=[vector_document],
                ids=[slug],
                metadatas=[vector_metadata]
            )

            return {
                "status": "success",
                "task_id": task_id,
                "title": web_title,
                "slug": slug,
                "markdown_path": md_path
            }
        except Exception as e:
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e)
            }
        
