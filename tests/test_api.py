import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# We import the FastAPI app that we'll bootstrap
from backend.app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_search_endpoint(client, mocker):
    # Mock the SearchService methods
    mock_search_results = {
        "hero_answer": "This is a synthesized AI answer with citations [1].",
        "sources": [
            {
                "segment_id": "seg-2",
                "title": "PhotoLab Guide",
                "slug": "github_com_p-ranav_PhotoLab",
                "summary": "A clean C++ image library",
                "tags": ["image-processing", "cpp"],
                "categories": ["software-development"],
                "url": "https://github.com/p-ranav/PhotoLab"
            }
        ]
    }
    
    # Patch the SearchService singleton or router dependency resolver
    mocker.patch("backend.services.search_service.SearchService.execute_rag_search", return_value=mock_search_results)
    
    response = client.get("/api/search?q=PhotoLab&mode=prose")
    
    assert response.status_code == 200
    json_data = response.json()
    assert "hero_answer" in json_data
    assert len(json_data["sources"]) == 1
    assert json_data["sources"][0]["slug"] == "github_com_p-ranav_PhotoLab"

def test_api_atlas_endpoint(client, mocker):
    # Mock GapService methods
    mock_heatmap = {"coding": 12, "scrapers": 4}
    mock_trending = [{"tag": "coding", "count": 12}, {"tag": "scrapers", "count": 4}]
    mock_coords = [{"id": "seg-2", "x": 0.5, "y": 0.8, "category": "coding"}]
    mock_gaps = {
        "dangling_tags": ["security"],
        "broken_urls": ["https://example.com/dead"],
        "gap_suggestions": [{"tag": "security", "suggestion": "Add security info"}]
    }
    
    mocker.patch("backend.services.gap_service.GapService.calculate_category_heatmap", return_value=mock_heatmap)
    mocker.patch("backend.services.gap_service.GapService.get_trending_tags", return_value=mock_trending)
    mocker.patch("backend.services.gap_service.GapService.calculate_tsne_coordinates", return_value=mock_coords)
    mocker.patch("backend.services.gap_service.GapService.detect_knowledge_gaps", return_value=mock_gaps)
    
    response = client.get("/api/atlas")
    
    assert response.status_code == 200
    json_data = response.json()
    assert "heatmap" in json_data
    assert json_data["trending_tags"][0]["tag"] == "coding"
    assert json_data["gap_report"]["dangling_tags"] == ["security"]
    assert len(json_data["tsne_coordinates"]) == 1

def test_api_recovery_ingest_endpoint(client, mocker):
    # Mock recovery service async background worker trigger
    mocker.patch("backend.services.recovery_service.RecoveryService.trigger_recovery_ingest", return_value="task-abc-123")
    
    response = client.post("/api/recovery/ingest", json={"url": "https://example.com/new-source", "category": "security"})
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "queued"
    assert "task_id" in json_data
