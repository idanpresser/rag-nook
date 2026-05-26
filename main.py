import sys
import argparse
import re
from pathlib import Path
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from config import config
from core.parser import WhatsAppParser
from core.preprocessor import Preprocessor
from core.scraper import ResilientScraper, DocumentCompiler
from core.llm_engine import LMStudioHermesClient
from core.vector_store import ChromaDBIndexer

console = Console()

def run_pipeline(chat_path: Path) -> None:
    """Executes the entire WhatsApp chat ETL, Scraping, Hermes enrichment, and ChromaDB indexing pipeline."""
    # Ensure all directories are initialized
    config.initialize_directories()

    console.print("[bold cyan]🚀 Starting WhatsApp Chat Processing Pipeline[/bold cyan]")

    # 1. Phase 1: Parsing raw chat file
    parser = WhatsAppParser()
    console.print(f"📦 [bold yellow]Phase 1:[/bold yellow] Ingesting and parsing raw chat: {chat_path}...")
    try:
        raw_messages = parser.parse_file(str(chat_path))
        console.print(f"✔️ Successfully parsed [bold green]{len(raw_messages)}[/bold green] raw message lines.")
    except Exception as e:
        console.print(f"❌ [bold red]Parsing Failed:[/bold red] {str(e)}")
        sys.exit(1)

    # 2. Phase 2: Chronological turn segmentation
    preprocessor = Preprocessor()
    console.print("🧹 [bold yellow]Phase 2:[/bold yellow] Running chronological turn segmentation...")
    segments = preprocessor.segment_conversation(raw_messages)
    console.print(f"✔️ Grouped conversation into [bold green]{len(segments)}[/bold green] conversational segments.")

    # Initialize Phase 3, 4, and 5 clients
    scraper = ResilientScraper()
    compiler = DocumentCompiler()
    llm_client = LMStudioHermesClient()
    vector_indexer = ChromaDBIndexer()

    console.print("🧠 [bold yellow]Phases 3-5:[/bold yellow] Scraping links, running Hermes local LLM enrichment, and vector indexing...")

    enriched_segments = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Processing turns and fetching web pages...[/cyan]", total=len(segments))

        for seg in segments:
            # Compile conversation text for LLM segment analysis
            conversation_text = "\n".join([f"{msg.sender}: {msg.content}" for msg in seg.messages])

            # Call local Hermes LLM to generate summary and tag list
            enrichment = llm_client.enrich_message_segment(conversation_text)
            seg.summary = enrichment.get("executive_summary", "")
            seg.tags = enrichment.get("tags", [])

            # Check and process messages containing external links
            for msg in seg.messages:
                if msg.media_type == "link" and msg.links:
                    for url in msg.links:
                        # Resilient scrape
                        web_title, web_body = scraper.scrape(url)

                        # Create clean file slug
                        slug = re.sub(r"https?://", "", url)
                        slug = re.sub(r"[^\w\-]", "_", slug)[:50]

                        # Generate Markdown and PDF exports
                        md_path = compiler.save_markdown(web_title, web_body, slug)
                        pdf_path = compiler.save_pdf(web_title, web_body, slug)

                        # Fetch concise page summary from local model
                        web_summary = llm_client.summarize_text(web_body)

                        # Save scraper outcomes to the message schema
                        msg.summary = web_summary
                        msg.tags.extend(["scraped-web", slug])

            # Prepare unified text context document block for Vector DB search
            vector_document = (
                f"[Context Segment: {seg.segment_id} | Range: {seg.start_time} to {seg.end_time}]\n"
                f"[Summary: {seg.summary}]\n"
                f"[Tags: {', '.join(seg.tags)}]\n"
                f"Conversation log:\n{conversation_text}"
            )

            # Define indexing metadata
            vector_metadata = {
                "segment_id": seg.segment_id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "has_links": int(any(msg.media_type == "link" for msg in seg.messages)),
                "tags": ", ".join(seg.tags)
            }

            # Index document chunk into local database
            vector_indexer.add_documents(
                documents=[vector_document],
                ids=[seg.segment_id],
                metadatas=[vector_metadata]
            )

            enriched_segments.append(seg.model_dump(mode="json"))
            progress.advance(task)

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
        run_pipeline(Path(args.file))
    elif args.command == "search":
        query_database(args.query, has_links=args.has_links, limit=args.limit)

if __name__ == "__main__":
    main()
