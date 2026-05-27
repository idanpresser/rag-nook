import re
from typing import Dict, Any, List
from core.vector_store import ChromaDBIndexer
from core.llm_engine import LMStudioHermesClient

class SearchService:
    """A SOLID search service executing semantic RAG synthesis and citation compilation."""

    def __init__(self, vector_indexer=None, llm_client=None):
        """Initializes the SearchService, injecting vector indexer and LLM client via DIP.

        Args:
            vector_indexer: A ChromaDBIndexer instance.
            llm_client: An LMStudioHermesClient instance.
        """
        self.vector_indexer = vector_indexer or ChromaDBIndexer()
        self.llm_client = llm_client or LMStudioHermesClient()

    def execute_rag_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Runs a semantic query against ChromaDB and uses the local Hermes LLM to synthesize a Hero Answer with citations.

        Args:
            query: The semantic search query terms.
            limit: The maximum number of source references to retrieve.

        Returns:
            A dictionary containing 'hero_answer' (str) and 'sources' (list of dicts).
        """
        try:
            results = self.vector_indexer.query(query, limit=limit)
        except Exception as e:
            return {
                "hero_answer": f"RAG Search failed: {str(e)}",
                "sources": []
            }

        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            return {
                "hero_answer": "No relevant matching knowledge base turns found to generate a response.",
                "sources": []
            }

        # Build list of structured source items
        import json
        from config import config
        
        parsed_chat_path = config.output_dir / "parsed_chat.json"
        parsed_chat_data = []
        if parsed_chat_path.exists():
            try:
                with open(parsed_chat_path, "r", encoding="utf-8") as f:
                    parsed_chat_data = json.load(f)
            except Exception:
                pass
                
        segment_map = {seg["segment_id"]: seg for seg in parsed_chat_data}
        
        sources = []
        context_chunks = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            meta = results["metadatas"][0][i] if "metadatas" in results else {}
            doc_text = results["documents"][0][i] if "documents" in results else ""
            
            # 1. Attempt segment lookup first
            if doc_id in segment_map:
                seg = segment_map[doc_id]
                
                # Fetch crawled links inside this segment
                scraped_urls = []
                for msg in seg.get("messages", []):
                    for scraped in msg.get("scraped_urls", []):
                        scraped_urls.append({
                            "url": scraped.get("url"),
                            "title": scraped.get("title"),
                            "slug": scraped.get("slug"),
                            "executive_summary": scraped.get("executive_summary"),
                            "tags": scraped.get("tags", []),
                            "categories": scraped.get("categories", ["web"])
                        })
                        
                # Fetch formatted message logs
                messages = []
                for msg in seg.get("messages", []):
                    messages.append({
                        "sender": msg.get("sender"),
                        "content": msg.get("content"),
                        "datetime_utc": msg.get("datetime_utc"),
                        "media_type": msg.get("media_type")
                    })
                    
                sources.append({
                    "segment_id": doc_id,
                    "title": f"Conversation Segment: {doc_id}",
                    "slug": doc_id,
                    "summary": seg.get("summary", doc_text[:200] + "..."),
                    "tags": seg.get("tags", []),
                    "categories": [meta.get("categories", "general")] if "categories" in meta else ["general"],
                    "url": "",
                    "type": "segment",
                    "messages": messages,
                    "scraped_urls": scraped_urls
                })
            else:
                # 2. Check if the doc_id is a scraped website slug directly
                scraped_found = None
                for seg in parsed_chat_data:
                    for msg in seg.get("messages", []):
                        for scraped in msg.get("scraped_urls", []):
                            if scraped.get("slug") == doc_id:
                                scraped_found = scraped
                                break
                        if scraped_found:
                            break
                    if scraped_found:
                        break
                        
                if scraped_found:
                    sources.append({
                        "segment_id": doc_id,
                        "title": scraped_found.get("title", "Scraped Webpage"),
                        "slug": doc_id,
                        "summary": scraped_found.get("executive_summary", doc_text[:200] + "..."),
                        "tags": scraped_found.get("tags", []),
                        "categories": scraped_found.get("categories", ["web"]),
                        "url": scraped_found.get("url"),
                        "type": "webpage"
                    })
                else:
                    # 3. Fallback: Parse from ChromaDB document text using regex
                    url_match = re.search(r"URL:\s*(.*?)[\]\n]", doc_text)
                    url = url_match.group(1).strip() if url_match else ""
                    
                    summary_match = re.search(r"\[Summary:\s*(.*?)[\]\n]", doc_text)
                    summary = summary_match.group(1).strip() if summary_match else doc_text[:200]
                    
                    title_match = re.search(r"\[Context Page:\s*(.*?)\s*\|", doc_text)
                    title = title_match.group(1).strip() if title_match else "Scraped Webpage"
                    
                    tags_str = meta.get("tags", "")
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                    
                    sources.append({
                        "segment_id": doc_id,
                        "title": title,
                        "slug": doc_id,
                        "summary": summary,
                        "tags": tags,
                        "categories": [meta.get("categories", "general")] if "categories" in meta else ["general"],
                        "url": url,
                        "type": "webpage"
                    })
            
            # Format context chunk for LLM synthesis
            context_chunks.append(f"Source [{i+1}] (ID: {doc_id}):\n{doc_text}")

        # Construct LLM context and synthesize response using the unified engine helper
        context_text = "\n\n".join(context_chunks)
        try:
            hero_answer = self.llm_client.synthesize_answer(query, context_text)
        except Exception as e:
            hero_answer = f"Synthesizer failed to generate answer from local model. Fallback: {doc_text[:250]}..."

        return {
            "hero_answer": hero_answer,
            "sources": sources
        }
