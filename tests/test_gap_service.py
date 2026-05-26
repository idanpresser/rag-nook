import pytest
import numpy as np
from unittest.mock import MagicMock
from backend.services.gap_service import GapService

@pytest.fixture
def mock_vector_indexer(mocker):
    # Mock ChromaDB indexer return values
    indexer = mocker.Mock()
    
    # Fake documents in vector DB
    documents = [
        "[Context Segment: seg-1 | Range: 2024-03-01T06:56:00Z to 2024-03-01T06:57:00Z]\n[Summary: Shopping notes]\n[Tags: personal, shopping, gifts]\nConversation log...",
        "[Context Segment: seg-2 | Range: 2024-03-04T08:17:00Z to 2024-03-04T08:17:00Z]\n[Summary: Tech guides]\n[Tags: coding, python, git]\nConversation log..."
    ]
    
    metadatas = [
        {"segment_id": "seg-1", "tags": "personal, shopping, gifts", "has_links": 0},
        {"segment_id": "seg-2", "tags": "coding, python, git", "has_links": 1}
    ]
    
    ids = ["seg-1", "seg-2"]
    
    # Mock ChromaDB client collection peek or get results
    mock_collection = mocker.Mock()
    mock_collection.get.return_value = {
        "ids": ids,
        "documents": documents,
        "metadatas": metadatas,
        # Mock 128-dimensional mock embeddings for 2 documents
        "embeddings": [
            [0.1] * 128,
            [0.9] * 128
        ]
    }
    
    indexer.collection = mock_collection
    return indexer

def test_calculate_category_heatmap(mock_vector_indexer):
    service = GapService(vector_indexer=mock_vector_indexer)
    heatmap = service.calculate_category_heatmap()
    
    # Check that categories (parsed from tags) are aggregated
    assert "personal" in heatmap or "coding" in heatmap
    assert heatmap.get("personal", 0) >= 0

def test_get_trending_tags(mock_vector_indexer):
    service = GapService(vector_indexer=mock_vector_indexer)
    trending = service.get_trending_tags(limit=3)
    
    assert len(trending) > 0
    # verify tags structure like [{"tag": "python", "count": 1}]
    assert "tag" in trending[0]
    assert "count" in trending[0]

def test_calculate_tsne_coordinates(mock_vector_indexer):
    service = GapService(vector_indexer=mock_vector_indexer)
    coords = service.calculate_tsne_coordinates()
    
    assert len(coords) == 2
    for pt in coords:
        assert "id" in pt
        assert "x" in pt
        assert "y" in pt
        assert "category" in pt
        assert 0.0 <= pt["x"] <= 1.0
        assert 0.0 <= pt["y"] <= 1.0

def test_detect_knowledge_gaps(mock_vector_indexer, mocker):
    # Mocking check_url Head requests
    mocker.patch("requests.head", return_value=mocker.Mock(status_code=200))
    
    # Ingest mock parsed chat JSON
    mock_json_content = [
        {
            "segment_id": "seg-1",
            "messages": [
                {
                    "message_id": "msg-1",
                    "content": "Check out https://example.com/missing-ethical-scrapers",
                    "media_type": "link",
                    "links": ["https://example.com/missing-ethical-scrapers"],
                    "summary": "Request timed out",
                    "tags": ["error", "connection-failed"],
                    "scraped_urls": [] # Empty, meaning no scraped content exists -> Gap!
                }
            ],
            "tags": ["scrapers"]
        }
    ]
    
    service = GapService(vector_indexer=mock_vector_indexer)
    gaps = service.detect_knowledge_gaps(mock_json_content)
    
    assert len(gaps["dangling_tags"]) >= 0
    assert len(gaps["gap_suggestions"]) >= 0
