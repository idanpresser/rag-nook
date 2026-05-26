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
        sources = []
        context_chunks = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            meta = results["metadatas"][0][i] if "metadatas" in results else {}
            doc_text = results["documents"][0][i] if "documents" in results else ""
            
            # Extract citation information
            title = "Conversation turn segment"
            slug = f"segment_{doc_id}"
            url = ""

            # Check if there are crawled URLs in the metadata tags
            tags_str = meta.get("tags", "")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            
            sources.append({
                "segment_id": doc_id,
                "title": title,
                "slug": slug,
                "summary": doc_text[:200] + "...",
                "tags": tags,
                "categories": [meta.get("categories", "general")] if "categories" in meta else ["general"],
                "url": url
            })
            
            # Format context chunk for LLM synthesis
            context_chunks.append(f"Source [{i+1}] (ID: {doc_id}):\n{doc_text}")

        # Construct LLM prompt for generative response
        context_text = "\n\n".join(context_chunks)
        system_prompt = (
            "You are a helpful research assistant utilizing a localized retrieval-augmented knowledge base. "
            "Your job is to answer user queries objectively and factually using only the provided sources. "
            "You must cite your sources explicitly in the text using bracketed numbers, e.g. [1], [2], corresponding to the source indexes."
        )
        user_prompt = (
            f"User Query: {query}\n\n"
            f"Retrieved Context Sources:\n{context_text}\n\n"
            "Synthesize a cohesive, high-density Hero Answer (maximum 200 words) using these sources. "
            "Make sure to place citations [1], [2] at the end of sentences that reference each specific source."
        )

        try:
            # Query local Nous Hermes client
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            hero_answer = response.choices[0].message.content.strip()
        except Exception as e:
            hero_answer = f"Synthesizer failed to generate answer from local model. Fallback: {doc_text[:250]}..."

        return {
            "hero_answer": hero_answer,
            "sources": sources
        }
