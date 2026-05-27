import re
import urllib.parse
from typing import Dict, Any, List
import numpy as np
from sklearn.manifold import TSNE
import requests

class GapService:
    """A SOLID service designed to compute insights heatmap, 2D t-SNE projections, and detect knowledge gaps."""

    def __init__(self, vector_indexer):
        """Initializes the GapService injecting ChromaDB vector indexer.

        Args:
            vector_indexer: A ChromaDBIndexer concrete instance.
        """
        self.vector_indexer = vector_indexer

    def calculate_category_heatmap(self) -> Dict[str, int]:
        """Scans the ChromaDB collections metadata tags and aggregates density counts."""
        try:
            results = self.vector_indexer.collection.get(include=["metadatas"])
        except Exception:
            return {}

        heatmap = {}
        if results and "metadatas" in results and results["metadatas"]:
            for meta in results["metadatas"]:
                if not meta:
                    continue
                tags_str = meta.get("tags", "")
                categories_str = meta.get("categories", "")
                
                # Combine tags and categories for counting
                combined = []
                if tags_str:
                    combined.extend([t.strip().lower() for t in tags_str.split(",") if t.strip()])
                if categories_str:
                    combined.extend([c.strip().lower() for c in categories_str.split(",") if c.strip()])

                # Filter out standard system errors
                ignored = {
                    "error", 
                    "connection-failed", 
                    "scraped-web", 
                    "unparsed-json", 
                    "llm-failed", 
                    "crawl-failed", 
                    "segment-failed", 
                    "uncategorized"
                }
                for item in combined:
                    if item not in ignored and not item.startswith("seg-"):
                        heatmap[item] = heatmap.get(item, 0) + 1
        return heatmap

    def get_trending_tags(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Calculates and returns the top densest tags/categories in the database."""
        heatmap = self.calculate_category_heatmap()
        sorted_tags = sorted(heatmap.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": k, "count": v} for k, v in sorted_tags[:limit]]

    def calculate_tsne_coordinates(self) -> List[Dict[str, Any]]:
        """Runs scikit-learn t-SNE dimensionality reduction on document embeddings and normalizes coordinates.

        Supports highly resilient perplexity auto-scaling for low-sample local databases.
        """
        try:
            results = self.vector_indexer.collection.get(include=["embeddings", "metadatas"])
        except Exception:
            return []

        if not results or not results.get("ids"):
            return []

        ids = results["ids"]
        embeddings = results.get("embeddings", [])
        metadatas = results.get("metadatas", [])

        # Fallback: if we don't have enough embeddings to compute t-SNE (minimum 2), generate structured grid coords
        if embeddings is None or len(embeddings) < 2:
            coords = []
            for i, item_id in enumerate(ids):
                meta = metadatas[i] if i < len(metadatas) else {}
                tags_str = meta.get("tags", "")
                primary_tag = tags_str.split(",")[0].strip() if tags_str else "general"
                coords.append({
                    "id": item_id,
                    "x": 0.2 + (0.5 * (i % 2)),
                    "y": 0.2 + (0.5 * (i // 2)),
                    "category": primary_tag
                })
            return coords

        try:
            data = np.array(embeddings)
            n_samples = len(data)

            # Auto-scale perplexity mathematically to avoid scikit-learn crashes
            perplexity = max(1, min(5, n_samples - 1))

            tsne = TSNE(
                n_components=2,
                perplexity=perplexity,
                random_state=42,
                n_iter=250,
                init="random"
            )
            coords_2d = tsne.fit_transform(data)

            # Normalize to 0.0 - 1.0 range
            min_val = coords_2d.min(axis=0)
            max_val = coords_2d.max(axis=0)
            range_val = max_val - min_val
            # Prevent division by zero on uniform embeddings
            range_val = np.where(range_val == 0.0, 1.0, range_val)
            normalized = (coords_2d - min_val) / range_val

            coords = []
            for i in range(n_samples):
                meta = metadatas[i] if i < len(metadatas) else {}
                tags_str = meta.get("tags", "")
                primary_tag = tags_str.split(",")[0].strip() if tags_str else "general"
                coords.append({
                    "id": ids[i],
                    "x": float(normalized[i][0]),
                    "y": float(normalized[i][1]),
                    "category": primary_tag
                })
            return coords
        except Exception:
            # Final exception fallback to prevent endpoint crash
            coords = []
            for i, item_id in enumerate(ids):
                coords.append({
                    "id": item_id,
                    "x": 0.5,
                    "y": 0.5,
                    "category": "general"
                })
            return coords

    def detect_knowledge_gaps(self, parsed_chat_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Scans the WhatsApp log history to find empty voids, dangling tags, and low confidence summaries."""
        dangling_tags = set()
        broken_urls = []
        gap_suggestions = []

        for seg in parsed_chat_data:
            seg_tags = seg.get("tags", [])
            for msg in seg.get("messages", []):
                if msg.get("media_type") == "link":
                    for url in msg.get("links", []):
                        scraped = msg.get("scraped_urls", [])
                        
                        # A link is a gap if it has no scraped urls, or has connection-failed tags
                        is_scraped = False
                        if scraped:
                            for item in scraped:
                                if item.get("url") == url and "connection-failed" not in item.get("tags", []):
                                    is_scraped = True

                        if not is_scraped:
                            broken_urls.append(url)
                            # Segment tags that aren't system fallbacks are added to dangling tags
                            ignored = {
                                "error", 
                                "connection-failed", 
                                "scraped-web", 
                                "unparsed-json", 
                                "llm-failed", 
                                "crawl-failed", 
                                "segment-failed", 
                                "uncategorized"
                            }
                            for t in seg_tags:
                                if t not in ignored and not t.startswith("seg-"):
                                    dangling_tags.add(t)

        # Generate smart prompt suggestions
        for tag in list(dangling_tags)[:5]:
            gap_suggestions.append({
                "tag": tag,
                "suggestion": f"I noticed you have references to '{tag}' in your chat history, but no active crawled document exists. Would you like me to fetch related sources?"
            })

        return {
            "dangling_tags": list(dangling_tags),
            "broken_urls": broken_urls,
            "gap_suggestions": gap_suggestions
        }
