from fastapi import APIRouter, Query
from backend.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.get("/api/search")
def search(
    q: str = Query(..., description="Semantic search query text"),
    mode: str = Query("prose", description="Toggle between prose or data mode layout views")
):
    """Semantic RAG search and generative answer synthesis endpoint."""
    return search_service.execute_rag_search(q)
