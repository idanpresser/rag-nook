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
    mocker.patch("backend.services.recovery_service.RecoveryService.run_async_ingest")
    
    response = client.post("/api/recovery/ingest", json={"url": "https://example.com/new-source", "category": "security"})
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "queued"
    assert "task_id" in json_data

def test_api_get_lms_models_disabled(client, mocker):
    config_mock = mocker.patch("backend.routers.metadata.config")
    config_mock.lms_sdk_enabled = False
    
    response = client.get("/api/lms/models")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["sdk_enabled"] is False
    assert json_data["status"] == "disabled"

def test_api_get_lms_models_enabled(client, mocker):
    config_mock = mocker.patch("backend.routers.metadata.config")
    config_mock.lms_sdk_enabled = True
    config_mock.llm_model_name = "google/gemma-4-e2b"
    
    mock_loaded = [mocker.Mock(identifier="google/gemma-4-e2b")]
    mocker.patch("lmstudio.list_loaded_models", return_value=mock_loaded)
    
    mock_downloaded = [
        mocker.Mock(model_key="google/gemma-4-e2b", type="llm", display_name="Gemma 4 E2B"),
        mocker.Mock(model_key="text-embedding-nomic-embed-text-v1.5", type="embedding", display_name="Nomic Embed")
    ]
    mocker.patch("lmstudio.list_downloaded_models", return_value=mock_downloaded)
    
    response = client.get("/api/lms/models")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["sdk_enabled"] is True
    assert json_data["status"] == "online"
    assert len(json_data["loaded"]) == 1
    assert json_data["loaded"][0]["identifier"] == "google/gemma-4-e2b"
    assert len(json_data["downloaded"]) == 2
    assert json_data["downloaded"][0]["model_key"] == "google/gemma-4-e2b"

def test_api_load_lms_model_success(client, mocker):
    config_mock = mocker.patch("backend.routers.metadata.config")
    config_mock.lms_sdk_enabled = True
    
    mock_llm = mocker.patch("lmstudio.llm", return_value=mocker.Mock())
    
    response = client.post("/api/lms/model/load", json={"model_key": "google/gemma-4-e2b"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    mock_llm.assert_called_once_with("google/gemma-4-e2b")

def test_api_unload_lms_model_success(client, mocker):
    config_mock = mocker.patch("backend.routers.metadata.config")
    config_mock.lms_sdk_enabled = True
    
    mock_client_inst = mocker.Mock()
    mocker.patch("lmstudio.Client", return_value=mock_client_inst)
    
    response = client.post("/api/lms/model/unload", json={"model_key": "google/gemma-4-e2b"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    mock_client_inst.llm.unload.assert_called_once_with("google/gemma-4-e2b")

def test_api_get_settings_success(client, mocker):
    from backend.services.lms_settings_service import LMStudioSettings
    mock_settings = LMStudioSettings(
        temperature_segment=0.1,
        temperature_webpage=0.1,
        temperature_search=0.2,
        max_tokens=2048,
        prompt_etl="test etl prompt",
        prompt_search="test search prompt",
        routing_etl_model="gemma",
        routing_search_model="hermes"
    )
    mocker.patch("backend.services.lms_settings_service.settings_service.load_settings", return_value=mock_settings)
    
    response = client.get("/api/lms/settings")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["temperature_segment"] == 0.1
    assert json_data["max_tokens"] == 2048
    assert json_data["prompt_etl"] == "test etl prompt"

def test_api_post_settings_success(client, mocker):
    mock_save = mocker.patch("backend.services.lms_settings_service.settings_service.save_settings")
    
    payload = {
        "temperature_segment": 0.5,
        "temperature_webpage": 0.5,
        "temperature_search": 0.5,
        "max_tokens": 128000,
        "prompt_etl": "new etl",
        "prompt_search": "new search",
        "routing_etl_model": "model-1",
        "routing_search_model": "model-2"
    }
    
    response = client.post("/api/lms/settings", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["settings"]["max_tokens"] == 128000
    mock_save.assert_called_once()

def test_api_pipeline_status_idle(client, mocker):
    mocker.patch("backend.routers.metadata.pipeline_running", False)
    mocker.patch("pathlib.Path.exists", return_value=False)
    
    response = client.get("/api/pipeline/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "idle"
    assert json_data["running"] is False
    assert json_data["steps"]["parsing"]["status"] == "pending"

def test_api_pipeline_resume_success(client, mocker):
    mocker.patch("backend.routers.metadata.pipeline_running", False)
    
    response = client.post("/api/pipeline/resume")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "resumption triggered" in json_data["message"].lower()

def test_api_pipeline_resume_busy(client, mocker):
    mocker.patch("backend.routers.metadata.pipeline_running", True)
    
    response = client.post("/api/pipeline/resume")
    assert response.status_code == 400
    json_data = response.json()
    assert "already running" in json_data["detail"]


def test_api_backup_list(client, mocker):
    mock_backups = [
        {
            "name": "20260527_120000_snapshot",
            "label": "snapshot",
            "created_at": "2026-05-27 12:00:00",
            "size_bytes": 1024,
            "size_str": "1.0 KB"
        }
    ]
    mocker.patch("backend.routers.metadata.backup_service.list_backups", return_value=mock_backups)
    
    response = client.get("/api/backup/list")
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) == 1
    assert json_data[0]["name"] == "20260527_120000_snapshot"
    assert json_data[0]["label"] == "snapshot"

def test_api_backup_create(client, mocker):
    mocker.patch("backend.routers.metadata.backup_service.create_backup", return_value="20260527_120000_snapshot")
    
    response = client.post("/api/backup/create", json={"label": "snapshot"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["name"] == "20260527_120000_snapshot"

def test_api_backup_restore(client, mocker):
    mock_restore = mocker.patch("backend.routers.metadata.backup_service.restore_backup")
    
    response = client.post("/api/backup/restore", json={"name": "20260527_120000_snapshot"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    mock_restore.assert_called_once_with("20260527_120000_snapshot")

def test_api_backup_delete(client, mocker):
    mock_delete = mocker.patch("backend.routers.metadata.backup_service.delete_backup")
    
    response = client.delete("/api/backup/20260527_120000_snapshot")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    mock_delete.assert_called_once_with("20260527_120000_snapshot")


def test_api_ingest_message(client, mocker):
    # Mock file writing and directory initialization
    mocker.patch("config.AppConfig.initialize_directories")
    mocker.patch("builtins.open", mocker.mock_open())
    
    # Mock background task runner
    mocker.patch("backend.routers.metadata.run_pipeline_task")
    mocker.patch("backend.routers.metadata.pipeline_running", False)
    
    response = client.post("/api/ingest/message", json={"text": "Hello world from test", "sender": "TestUser"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "TestUser: Hello world from test" in json_data["formatted_message"]
    
def test_api_ingest_file(client, mocker):
    mocker.patch("config.AppConfig.initialize_directories")
    mocker.patch("builtins.open", mocker.mock_open())
    
    mocker.patch("backend.routers.metadata.run_pipeline_task")
    mocker.patch("backend.routers.metadata.pipeline_running", False)
    
    # Send a multipart file upload request
    from io import BytesIO
    file_content = b"3/1/24, 06:56 - Idan P: some file chat logTurn"
    file = ("supplementary.txt", BytesIO(file_content), "text/plain")
    
    response = client.post("/api/ingest/file", files={"file": file})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "merged supplementary.txt" in json_data["message"]


def test_api_archive_export(client, mocker):
    mocker.patch("backend.routers.metadata.pipeline_running", False)
    
    # Mock archive service export
    mock_export = mocker.patch("backend.services.archive_service.archive_service.export_archive")
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.unlink")
    
    from fastapi.responses import Response
    mocker.patch("backend.routers.metadata.FileResponse", return_value=Response(content=b"dummy zip data", media_type="application/zip"))
    
    response = client.get("/api/archive/export")
    assert response.status_code == 200
    assert response.content == b"dummy zip data"
    mock_export.assert_called_once()

def test_api_archive_import(client, mocker):
    mocker.patch("backend.routers.metadata.pipeline_running", False)
    
    # Mock archive service import
    mock_import = mocker.patch("backend.services.archive_service.archive_service.import_archive")
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.unlink")
    
    # Send a multipart file upload request
    from io import BytesIO
    file_content = b"dummy zip contents"
    file = ("memory_base.zip", BytesIO(file_content), "application/zip")
    
    response = client.post("/api/archive/import", files={"file": file})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "imported successfully" in json_data["message"]
    mock_import.assert_called_once()


def test_api_ingest_folder(client, mocker):
    from pathlib import Path
    mocker.patch("config.AppConfig.initialize_directories")
    mocker.patch("builtins.open", mocker.mock_open())
    
    mock_scan_result = mocker.Mock()
    mock_scan_result.chat_log_path = Path("WhatsApp Chat with ענתי.txt")
    mock_scan_result.media_files = [Path("photo.jpg")]
    mock_scan_result.vcard_files = [Path("contact.vcf")]
    mocker.patch("core.scanner.LocalFolderScanner.scan", return_value=mock_scan_result)

    mocker.patch("core.parser.WhatsAppParser.parse_file", return_value=[])
    mocker.patch("core.preprocessor.Preprocessor.enrich_conversation", return_value=[])

    from io import BytesIO
    files = [
        ("files", ("WhatsApp Chat with ענתי.txt", BytesIO(b"chat data"), "text/plain")),
        ("files", ("photo.jpg", BytesIO(b"image data"), "image/jpeg")),
        ("files", ("contact.vcf", BytesIO(b"vcard data"), "text/vcard")),
    ]

    response = client.post("/api/ingest/folder", files=files)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "processed 3 files" in json_data["message"]


def test_api_serve_media_file(client, mocker):
    mocker.patch("config.AppConfig.initialize_directories")
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.is_file", return_value=True)
    
    from fastapi.responses import Response
    mocker.patch("backend.routers.metadata.FileResponse", return_value=Response(content=b"image bytes", media_type="image/avif"))
    
    response = client.get("/api/media/photo.avif")
    assert response.status_code == 200
    assert response.content == b"image bytes"
    assert response.headers["content-type"] == "image/avif"







