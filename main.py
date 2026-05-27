import sys
import argparse
import re
from pathlib import Path
import json
import concurrent.futures
import datetime
import threading
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from config import config
from core.parser import WhatsAppParser
from core.preprocessor import Preprocessor, ScrapedURLMetadata
from core.scraper import ResilientCrawl4AIScraper, DocumentCompiler
from core.llm_engine import LMStudioHermesClient
from core.vector_store import ChromaDBIndexer

console = Console()

def run_pipeline(chat_path: Path, reset: bool = False) -> None:
    """Executes the entire WhatsApp chat ETL, concurrent URL scraping, serial LLM enrichment, and ChromaDB indexing pipeline."""
    # Ensure all directories are initialized
    config.initialize_directories()

    console.print("[bold cyan]🚀 Starting WhatsApp Chat Processing Pipeline[/bold cyan]")

    # Centralized Task State Tracking Initialization
    tasks_path = config.output_dir / "pipeline_tasks.json"
    if reset and tasks_path.exists():
        try:
            tasks_path.unlink()
            console.print("[bold yellow]🔄 Reset requested. Deleted existing pipeline_tasks.json state.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]⚠️ Reset Failed to delete existing state file:[/bold red] {str(e)}")

    state = {
        "meta": {
            "status": "in_progress",
            "total_urls": 0,
            "completed_urls": 0,
            "total_segments": 0,
            "completed_segments": 0,
            "updated_at": ""
        },
        "steps": {
            "parsing": { "status": "pending", "error": None },
            "segmentation": { "status": "pending", "error": None },
            "scraping": { "status": "pending", "error": None },
            "llm_enrichment": { "status": "pending", "error": None }
        },
        "urls": {},
        "segments": {}
    }

    if tasks_path.exists():
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            console.print("[bold green]🔄 Loaded existing pipeline tasks state. Resuming where we left off...[/bold green]")
        except Exception as e:
            console.print(f"[bold yellow]⚠️ Failed to load existing tasks JSON ({str(e)}). Starting fresh...[/bold yellow]")

    state_lock = threading.Lock()

    def save_state():
        with state_lock:
            state["meta"]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # Recalculate meta counts
            total_urls = len(state["urls"])
            completed_urls = sum(1 for u in state["urls"].values() if u.get("crawl_status") == "done" and u.get("llm_status") == "done")
            total_segments = len(state["segments"])
            completed_segments = sum(1 for s in state["segments"].values() if s.get("status") == "done")
            
            state["meta"]["total_urls"] = total_urls
            state["meta"]["completed_urls"] = completed_urls
            state["meta"]["total_segments"] = total_segments
            state["meta"]["completed_segments"] = completed_segments
            
            # Check overall pipeline status
            is_completed = (
                state["steps"]["parsing"]["status"] == "done" and
                state["steps"]["segmentation"]["status"] == "done" and
                (not state["urls"] or all(u.get("crawl_status") == "done" and u.get("llm_status") == "done" for u in state["urls"].values())) and
                (not state["segments"] or all(s.get("status") == "done" for s in state["segments"].values()))
            )
            state["meta"]["status"] = "completed" if is_completed else "in_progress"
            
            try:
                # Ensure output directory exists
                tasks_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tasks_path, "w", encoding="utf-8") as sf:
                    json.dump(state, sf, indent=2, ensure_ascii=False)
            except Exception as e:
                console.print(f"[bold red]State Save Error:[/bold red] {str(e)}")

    # 1. Phase 1: Parsing raw chat file
    parser = WhatsAppParser()
    console.print(f"📦 [bold yellow]Phase 1:[/bold yellow] Ingesting and parsing raw chat: {chat_path}...")
    
    if state["steps"]["parsing"]["status"] == "done":
        console.print("✔️ Skip: Chat already parsed successfully in a previous run.")
    else:
        state["steps"]["parsing"]["status"] = "in_progress"
        save_state()
        try:
            raw_messages = parser.parse_file(str(chat_path))
            state["steps"]["parsing"]["status"] = "done"
            state["steps"]["parsing"]["error"] = None
            save_state()
            console.print(f"✔️ Successfully parsed [bold green]{len(raw_messages)}[/bold green] raw message lines.")
        except Exception as e:
            state["steps"]["parsing"]["status"] = "error"
            state["steps"]["parsing"]["error"] = str(e)
            save_state()
            console.print(f"❌ [bold red]Parsing Failed:[/bold red] {str(e)}")
            sys.exit(1)

    # Load messages for downstream pipeline
    try:
        raw_messages = parser.parse_file(str(chat_path))
    except Exception as e:
        console.print(f"❌ [bold red]Fatal parsing exception during resume phase:[/bold red] {str(e)}")
        sys.exit(1)

    # 2. Phase 2: Chronological turn segmentation
    preprocessor = Preprocessor()
    console.print("🧹 [bold yellow]Phase 2:[/bold yellow] Running chronological turn segmentation...")
    
    if state["steps"]["segmentation"]["status"] == "done":
        console.print("✔️ Skip: Conversation already segmented successfully in a previous run.")
        segments = preprocessor.segment_conversation(raw_messages)
    else:
        state["steps"]["segmentation"]["status"] = "in_progress"
        save_state()
        try:
            segments = preprocessor.segment_conversation(raw_messages)
            state["steps"]["segmentation"]["status"] = "done"
            state["steps"]["segmentation"]["error"] = None
            save_state()
            console.print(f"✔️ Grouped conversation into [bold green]{len(segments)}[/bold green] conversational segments.")
        except Exception as e:
            state["steps"]["segmentation"]["status"] = "error"
            state["steps"]["segmentation"]["error"] = str(e)
            save_state()
            console.print(f"❌ [bold red]Segmentation Failed:[/bold red] {str(e)}")
            sys.exit(1)

    # Synchronize segments list into task tracking dictionary
    for seg in segments:
        if seg.segment_id not in state["segments"]:
            state["segments"][seg.segment_id] = {
                "segment_id": seg.segment_id,
                "status": "pending",
                "error": None,
                "summary": "",
                "tags": [],
                "data": None
            }
    save_state()

    # 3. Phase 3: Concurrent Link Crawling Queue (4 concurrent workers)
    console.print("\n🕸️ [bold yellow]Phase 3:[/bold yellow] Scanning for links and initiating concurrent Web crawling...")
    
    unique_urls = {}
    for seg in segments:
        for msg in seg.messages:
            if msg.media_type == "link" and msg.links:
                for url in msg.links:
                    if url not in unique_urls:
                        unique_urls[url] = []
                    unique_urls[url].append(msg)
                    
                    if url not in state["urls"]:
                        state["urls"][url] = {
                            "url": url,
                            "crawl_status": "pending",
                            "crawl_error": None,
                            "title": "",
                            "slug": "",
                            "markdown_path": "",
                            "llm_status": "pending",
                            "llm_error": None,
                            "executive_summary": "",
                            "tags": [],
                            "categories": []
                        }
    save_state()

    console.print(f"✔️ Identified [bold green]{len(unique_urls)}[/bold green] unique URLs to crawl.")
    
    scraper = ResilientCrawl4AIScraper()
    compiler = DocumentCompiler()
    
    scraped_pages_cache = {}
    
    # 3a. Prepopulate cache with already completed crawling URLs, loading from disk
    for url, u_state in state["urls"].items():
        if u_state["crawl_status"] == "done":
            md_path = u_state["markdown_path"]
            md_content = ""
            if md_path and Path(md_path).exists():
                try:
                    with open(md_path, "r", encoding="utf-8") as f:
                        md_content = f.read()
                except Exception:
                    pass
            scraped_pages_cache[url] = {
                "title": u_state["title"],
                "slug": u_state["slug"],
                "markdown_path": md_path,
                "markdown": md_content
            }

    # 3b. Crawl pending and error URLs
    urls_to_crawl = [url for url, u_state in state["urls"].items() if u_state["crawl_status"] != "done"]
    
    def crawl_url(url):
        # 1. Scrape webpage asynchronously (network operation)
        web_title, web_markdown, web_images = scraper.scrape_url(url)
        
        # 2. Compile clean file slug
        slug = re.sub(r"https?://", "", url)
        slug = re.sub(r"[^\w\-]", "_", slug)[:50]
        
        # 3. Generate locally cached images and clickable markdown
        md_path = compiler.save_markdown_with_images(web_title, web_markdown, web_images, slug)
        
        # Update thread-safe state for crawled URL
        with state_lock:
            state["urls"][url]["title"] = web_title
            state["urls"][url]["slug"] = slug
            state["urls"][url]["markdown_path"] = md_path
            state["urls"][url]["crawl_status"] = "done"
            state["urls"][url]["crawl_error"] = None
        save_state()
        
        return url, {
            "title": web_title,
            "slug": slug,
            "markdown_path": md_path,
            "markdown": web_markdown
        }

    if urls_to_crawl:
        state["steps"]["scraping"]["status"] = "in_progress"
        save_state()
        
        console.print(f"🕸️ Queuing [bold cyan]{len(urls_to_crawl)}[/bold cyan] URLs to crawl.")
        
        # Set all targets status to in_progress initially
        for url in urls_to_crawl:
            state["urls"][url]["crawl_status"] = "in_progress"
        save_state()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Crawling websites (4 threads)...[/cyan]", total=len(urls_to_crawl))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.max_scraper_workers) as executor:
                futures = {executor.submit(crawl_url, url): url for url in urls_to_crawl}
                for future in concurrent.futures.as_completed(futures):
                    url = futures[future]
                    try:
                        url, result = future.result()
                        scraped_pages_cache[url] = result
                    except Exception as e:
                        console.print(f"[bold red]Crawl Error for {url}:[/bold red] {str(e)}")
                        error_slug = re.sub(r"[^\w\-]", "_", url)[:50]
                        scraped_pages_cache[url] = {
                            "title": "Untitled Page (Crawl Error)",
                            "slug": error_slug,
                            "markdown_path": "",
                            "markdown": f"Crawl failed: {str(e)}"
                        }
                        with state_lock:
                            state["urls"][url]["crawl_status"] = "error"
                            state["urls"][url]["crawl_error"] = str(e)
                            state["urls"][url]["title"] = "Untitled Page (Crawl Error)"
                            state["urls"][url]["slug"] = error_slug
                        save_state()
                    progress.advance(task)
                    
        state["steps"]["scraping"]["status"] = "done"
        state["steps"]["scraping"]["error"] = None
        save_state()
        console.print("[bold green]✔️ Phase 3 Complete! Scraping and local compilation finished.[/bold green]")
    else:
        state["steps"]["scraping"]["status"] = "done"
        state["steps"]["scraping"]["error"] = None
        save_state()
        console.print("[bold green]✔️ Phase 3 Skip: All URLs already crawled in previous run.[/bold green]")
        
    # 4. Phase 4 & 5: Serial LLM Processing & Vector Database Indexing Queue (concurrency of 1)
    console.print("\n🧠 [bold yellow]Phases 4-5:[/bold yellow] Running serial LLM summaries and ChromaDB vector indexing...")
    
    llm_client = LMStudioHermesClient()
    vector_indexer = ChromaDBIndexer()
    
    # Try to recreate collection only if starting a reset fresh pipeline run
    if reset:
        try:
            vector_indexer.client.delete_collection("whatsapp_chat")
            console.print("[bold yellow]🧹 Reset database collection 'whatsapp_chat' successfully.[/bold yellow]")
        except Exception:
            pass
    vector_indexer.collection = vector_indexer.client.get_or_create_collection(name="whatsapp_chat")
    
    enriched_segments = []
    
    state["steps"]["llm_enrichment"]["status"] = "in_progress"
    save_state()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Processing and indexing turns (Serial LLM)...[/cyan]", total=len(segments))
        
        for seg in segments:
            seg_state = state["segments"][seg.segment_id]
            
            # If segment is already completed, load enriched data from task cache directly
            if seg_state["status"] == "done" and seg_state.get("data") is not None:
                enriched_segments.append(seg_state["data"])
                progress.advance(task)
                continue
                
            seg_state["status"] = "in_progress"
            save_state()
            
            try:
                # 1. Process messages containing links serially
                for msg in seg.messages:
                    if msg.media_type == "link" and msg.links:
                        for url in msg.links:
                            cache = scraped_pages_cache.get(url)
                            if not cache:
                                continue
                                
                            web_title = cache["title"]
                            web_markdown = cache["markdown"]
                            web_slug = cache["slug"]
                            web_md_path = cache["markdown_path"]
                            
                            u_state = state["urls"][url]
                            
                            # Webpage LLM summary enrichment caching
                            if u_state["llm_status"] == "done":
                                web_summary = u_state["executive_summary"]
                                web_tags = u_state["tags"]
                                web_categories = u_state["categories"]
                            else:
                                u_state["llm_status"] = "in_progress"
                                save_state()
                                
                                try:
                                    # Fetch webpage enrichment serially with 3x retry protection
                                    web_enrichment = llm_client.enrich_webpage_content(web_markdown)
                                    web_summary = web_enrichment.get("executive_summary", "")
                                    web_tags = web_enrichment.get("tags", [])
                                    web_categories = web_enrichment.get("categories", ["web"])
                                    
                                    u_state["executive_summary"] = web_summary
                                    u_state["tags"] = web_tags
                                    u_state["categories"] = web_categories
                                    u_state["llm_status"] = "done"
                                    u_state["llm_error"] = None
                                    save_state()
                                except Exception as e:
                                    u_state["llm_status"] = "error"
                                    u_state["llm_error"] = str(e)
                                    save_state()
                                    raise e
                            
                            metadata_obj = ScrapedURLMetadata(
                                url=url,
                                title=web_title,
                                slug=web_slug,
                                markdown_path=web_md_path,
                                executive_summary=web_summary,
                                tags=web_tags,
                                categories=web_categories
                            )
                            msg.scraped_urls.append(metadata_obj)
                            
                            # Sync to message attributes
                            msg.summary = web_summary
                            msg.tags.extend(["scraped-web", web_slug])
                            msg.tags.extend(web_tags)
                            msg.tags.extend(web_categories)
                
                # 2. Segment-level conversation text compiled for LLM segment analysis
                conversation_text = "\n".join([f"{msg.sender}: {msg.content}" for msg in seg.messages])
                
                # Call local Hermes LLM to generate summary and tags serially with 3x retry protection
                enrichment = llm_client.enrich_message_segment(conversation_text)
                seg.summary = enrichment.get("executive_summary", "")
                seg.tags = enrichment.get("tags", [])
                
                # Compile crawled URL contexts for ChromaDB
                crawled_url_contexts = []
                all_web_tags = []
                all_web_categories = []
                for msg in seg.messages:
                    for scraped in msg.scraped_urls:
                        crawled_url_contexts.append(
                            f"- Webpage: {scraped.title} ({scraped.url})\n"
                            f"  Summary: {scraped.executive_summary}\n"
                            f"  Categories: {', '.join(scraped.categories)}\n"
                            f"  Tags: {', '.join(scraped.tags)}"
                        )
                        all_web_tags.extend(scraped.tags)
                        all_web_categories.extend(scraped.categories)
                        
                crawled_section = ""
                if crawled_url_contexts:
                    crawled_section = "\nCrawled Webpages Context:\n" + "\n".join(crawled_url_contexts) + "\n"
                    
                # Prepare unified text context document block for Vector DB search
                vector_document = (
                    f"[Context Segment: {seg.segment_id} | Range: {seg.start_time} to {seg.end_time}]\n"
                    f"[Summary: {seg.summary}]\n"
                    f"[Tags: {', '.join(seg.tags)}]\n"
                    f"{crawled_section}"
                    f"Conversation log:\n{conversation_text}"
                )
                
                # Define indexing metadata
                vector_metadata = {
                    "segment_id": seg.segment_id,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "has_links": int(any(msg.media_type == "link" for msg in seg.messages)),
                    "tags": ", ".join(list(set(seg.tags + all_web_tags))),
                    "categories": ", ".join(list(set(all_web_categories)))
                }
                
                # Idempotent Indexing document chunk into database using upsert!
                vector_indexer.collection.upsert(
                    documents=[vector_document],
                    ids=[seg.segment_id],
                    metadatas=[vector_metadata]
                )
                
                # Update task state to done
                seg_state["status"] = "done"
                seg_state["summary"] = seg.summary
                seg_state["tags"] = seg.tags
                seg_state["error"] = None
                seg_state["data"] = seg.model_dump(mode="json")
                save_state()
                
            except Exception as e:
                seg_state["status"] = "error"
                seg_state["error"] = str(e)
                save_state()
                
                seg.summary = f"Processing Failed. Error: {str(e)}"
                seg.tags = ["error", "segment-failed"]
                
            enriched_segments.append(seg.model_dump(mode="json"))
            progress.advance(task)
            
    state["steps"]["llm_enrichment"]["status"] = "done"
    state["steps"]["llm_enrichment"]["error"] = None
    save_state()

    # Sort enriched segments by segment_id sequence to maintain strict chronological order
    enriched_segments.sort(key=lambda x: int(x["segment_id"].split("-")[1]))

    # Save final structured JSON database
    output_path = config.output_dir / "parsed_chat.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched_segments, f, indent=2, ensure_ascii=False)

    console.print(f"\n[bold green]🎉 WhatsApp Chat Processing Completed Successfully![/bold green]")
    console.print(f"📁 Enriched Chat JSON: [bold white]{output_path}[/bold white]")
    console.print(f"📁 Scraped Markdown/PDF Pages: [bold white]{config.scraped_dir}[/bold white]")
    console.print(f"📁 Local Chroma Vector Store: [bold white]{config.vector_db_dir}[/bold white]\n")

def query_database(query_str: str, has_links: int = None, limit: int = 5) -> None:
    """Executes a semantic search query against the ChromaDB vector database."""
    console.print(f"[bold cyan]🔍 Querying Vector Database for:[/bold cyan] '{query_str}'...")

    vector_indexer = ChromaDBIndexer()

    # Build optional filter conditions
    where_filter = None
    if has_links is not None:
        where_filter = {"has_links": has_links}

    results = vector_indexer.query(query_str, limit=limit, where_filter=where_filter)

    if not results or not results["ids"] or len(results["ids"][0]) == 0:
        console.print("[bold yellow]⚠️ No matching conversational turns found.[/bold yellow]")
        return

    # Draw result grid
    table = Table(title=f"Semantic Search Results (Query: '{query_str}')", show_lines=True)
    table.add_column("Segment ID", justify="center", style="cyan", no_wrap=True)
    table.add_column("Relevance Distance", justify="center", style="yellow")
    table.add_column("Enriched Tags", style="magenta")
    table.add_column("Matched Content Snippet", style="green")

    for i in range(len(results["ids"][0])):
        seg_id = results["ids"][0][i]
        # Distances represent relevance (smaller = more relevant)
        distance = str(round(results["distances"][0][i], 4)) if "distances" in results else "N/A"
        meta = results["metadatas"][0][i]
        doc = results["documents"][0][i]

        snippet = doc[:250] + "..." if len(doc) > 250 else doc

        table.add_row(
            seg_id,
            distance,
            meta.get("tags", "None"),
            snippet
        )

    console.print(table)

def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Chat ETL Ingestion, Web Scraper, and Local LLM (Hermes) Vector indexing pipeline."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. run command
    run_parser = subparsers.add_parser("run", help="Execute the chat ETL parser and scraper pipeline.")
    run_parser.add_argument(
        "--file",
        type=str,
        default=str(config.chat_file_path),
        help="Custom path to raw WhatsApp chat export .txt file."
    )
    run_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset pipeline tasks state and rebuild database from scratch instead of resuming."
    )

    # 2. search command
    search_parser = subparsers.add_parser("search", help="Query the local vector store database.")
    search_parser.add_argument("query", type=str, help="Search terms or semantic query text.")
    search_parser.add_argument(
        "--has-links",
        type=int,
        choices=[0, 1],
        default=None,
        help="Filter by segments containing web links (1) or no links (0)."
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Max number of search results to return."
    )

    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(Path(args.file), reset=args.reset)
    elif args.command == "search":
        query_database(args.query, has_links=args.has_links, limit=args.limit)

if __name__ == "__main__":
    main()
