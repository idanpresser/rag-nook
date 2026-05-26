import json
from fastapi import APIRouter
from backend.services.gap_service import GapService
from core.vector_store import ChromaDBIndexer
from config import config

router = APIRouter()
gap_service = GapService(vector_indexer=ChromaDBIndexer())

@router.get("/api/atlas")
def get_atlas():
    """Generates the categories heatmap density, trending tags, 2D coordinates map, and knowledge gaps silence report."""
    parsed_chat_path = config.output_dir / "parsed_chat.json"
    parsed_chat_data = []
    
    # Safely load the current parsed chat log database to scan gaps
    if parsed_chat_path.exists():
        try:
            with open(parsed_chat_path, "r", encoding="utf-8") as f:
                parsed_chat_data = json.load(f)
        except Exception:
            pass

    return {
        "heatmap": gap_service.calculate_category_heatmap(),
        "trending_tags": gap_service.get_trending_tags(limit=10),
        "tsne_coordinates": gap_service.calculate_tsne_coordinates(),
        "gap_report": gap_service.detect_knowledge_gaps(parsed_chat_data)
    }
