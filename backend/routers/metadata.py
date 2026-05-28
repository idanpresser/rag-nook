import json
import threading
import datetime
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.services.gap_service import GapService
from core.vector_store import ChromaDBIndexer
from config import config
from backend.services.lms_settings_service import settings_service, LMStudioSettings
from backend.services.backup_service import backup_service

pipeline_running = False
pipeline_lock = threading.Lock()

def run_pipeline_task():
    global pipeline_running
    with pipeline_lock:
        if pipeline_running:
            return
        pipeline_running = True
    try:
        from main import run_pipeline
        run_pipeline(config.chat_file_path, reset=False)
    except Exception as e:
        print(f"[Pipeline Background Task] Pipeline failed with error: {str(e)}")
    finally:
        with pipeline_lock:
            pipeline_running = False

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

@router.get("/api/scraped/{slug}")
def get_scraped_page(slug: str):
    """Retrieves full scraped markdown webpage content and its AI summary/tags metadata."""
    filepath = config.scraped_dir / f"{slug}.md"
    if not filepath.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scraped markdown file not found")
        
    with open(filepath, "r", encoding="utf-8") as f:
        markdown_content = f.read()
        
    # Attempt to locate metadata in parsed_chat.json first
    parsed_chat_path = config.output_dir / "parsed_chat.json"
    metadata = None
    if parsed_chat_path.exists():
        try:
            with open(parsed_chat_path, "r", encoding="utf-8") as f:
                parsed_chat_data = json.load(f)
            for seg in parsed_chat_data:
                for msg in seg.get("messages", []):
                    for scraped in msg.get("scraped_urls", []):
                        if scraped.get("slug") == slug:
                            metadata = scraped
                            break
                    if metadata:
                        break
                if metadata:
                    break
        except Exception:
            pass
            
    if metadata:
        return {
            "slug": slug,
            "title": metadata.get("title"),
            "url": metadata.get("url"),
            "markdown": markdown_content,
            "executive_summary": metadata.get("executive_summary"),
            "tags": metadata.get("tags", []),
            "categories": metadata.get("categories", ["web"])
        }
        
    # Fallback: Query ChromaDB collection
    import re
    title = "Untitled Page"
    lines = markdown_content.split("\n")
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        
    url = ""
    executive_summary = ""
    tags = []
    categories = ["web"]
    
    try:
        vector_indexer = ChromaDBIndexer()
        chroma_res = vector_indexer.collection.get(ids=[slug])
        if chroma_res and chroma_res.get("documents") and len(chroma_res["documents"]) > 0:
            doc_text = chroma_res["documents"][0]
            meta = chroma_res["metadatas"][0] if chroma_res.get("metadatas") else {}
            
            url_match = re.search(r"URL:\s*(.*?)[\]\n]", doc_text)
            if url_match:
                url = url_match.group(1).strip()
                
            summary_match = re.search(r"\[Summary:\s*(.*?)[\]\n]", doc_text)
            if summary_match:
                executive_summary = summary_match.group(1).strip()
                
            if meta.get("tags"):
                tags = [t.strip() for t in meta["tags"].split(",") if t.strip()]
            if meta.get("categories"):
                categories = [c.strip() for c in meta["categories"].split(",") if c.strip()]
    except Exception:
        pass
        
    if not executive_summary:
        executive_summary = f"Cached markdown page for {title}."
        
    return {
        "slug": slug,
        "title": title,
        "url": url,
        "markdown": markdown_content,
        "executive_summary": executive_summary,
        "tags": tags,
        "categories": categories
    }

from pydantic import BaseModel

class ModelActionRequest(BaseModel):
    model_key: str

@router.get("/api/lms/models")
def get_lms_models():
    """Fetches currently loaded models and available downloaded models via lmstudio SDK."""
    settings = settings_service.load_settings()
    if not config.lms_sdk_enabled:
        return {
            "sdk_enabled": False,
            "status": "disabled",
            "loaded": [],
            "downloaded": [],
            "active_settings": settings.model_dump()
        }
    try:
        import lmstudio as lms
        loaded_raw = lms.list_loaded_models()
        loaded = []
        for m in loaded_raw:
            loaded.append({
                "identifier": m.identifier,
                "type": "llm"
            })
            
        downloaded_raw = lms.list_downloaded_models()
        downloaded = []
        for d in downloaded_raw:
            downloaded.append({
                "model_key": d.model_key,
                "type": d.type,
                "display_name": getattr(d, "display_name", d.model_key)
            })
            
        return {
            "sdk_enabled": True,
            "status": "online",
            "loaded": loaded,
            "downloaded": downloaded,
            "default_model": config.llm_model_name,
            "active_settings": settings.model_dump()
        }
    except Exception as e:
        return {
            "sdk_enabled": True,
            "status": "offline",
            "error": str(e),
            "loaded": [],
            "downloaded": [],
            "active_settings": settings.model_dump()
        }

@router.post("/api/lms/model/load")
def load_lms_model(req: ModelActionRequest):
    """Programmatically loads a model in LM Studio using the official Python SDK."""
    if not config.lms_sdk_enabled:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="LM Studio SDK integration is disabled in configuration.")
    try:
        import lmstudio as lms
        print(f"[API] Programmatically loading model: {req.model_key}...")
        lms.llm(req.model_key)
        return {"status": "success", "message": f"Successfully loaded model {req.model_key}"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to load model {req.model_key}. Error: {str(e)}")

@router.post("/api/lms/model/unload")
def unload_lms_model(req: ModelActionRequest):
    """Programmatically unloads a model in LM Studio to release VRAM."""
    if not config.lms_sdk_enabled:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="LM Studio SDK integration is disabled in configuration.")
    try:
        import lmstudio as lms
        print(f"[API] Programmatically unloading model: {req.model_key}...")
        client = lms.Client()
        client.llm.unload(req.model_key)
        return {"status": "success", "message": f"Successfully unloaded model {req.model_key}"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to unload model {req.model_key}. Error: {str(e)}")

@router.get("/api/lms/settings")
def get_lms_settings():
    """Retrieves current LM Studio custom settings."""
    settings = settings_service.load_settings()
    return settings.model_dump()

@router.post("/api/lms/settings")
def update_lms_settings(settings_data: LMStudioSettings):
    """Updates and persists LM Studio custom settings."""
    settings_service.save_settings(settings_data)
    return {
        "status": "success",
        "message": "Settings updated successfully",
        "settings": settings_data.model_dump()
    }

@router.get("/api/pipeline/status")
def get_pipeline_status():
    """Retrieves current background pipeline execution status and progress metrics."""
    global pipeline_running
    tasks_path = config.output_dir / "pipeline_tasks.json"
    status_data = {
        "status": "idle",
        "steps": {
            "parsing": {"status": "pending", "error": None},
            "segmentation": {"status": "pending", "error": None},
            "scraping": {"status": "pending", "error": None},
            "llm_enrichment": {"status": "pending", "error": None}
        },
        "meta": {
            "total_urls": 0,
            "completed_urls": 0,
            "total_segments": 0,
            "completed_segments": 0
        },
        "running": pipeline_running
    }
    
    if tasks_path.exists():
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            status_data["steps"] = data.get("steps", status_data["steps"])
            status_data["meta"] = data.get("meta", status_data["meta"])
            status_data["status"] = data.get("meta", {}).get("status", "idle")
        except Exception:
            pass
            
    # Override running status based on active thread flag
    if pipeline_running:
        status_data["status"] = "in_progress"
        status_data["running"] = True
        
    return status_data

@router.post("/api/pipeline/resume")
def resume_pipeline(background_tasks: BackgroundTasks):
    """Triggers the background ETL parser and RAG vector indexing pipeline in resume mode."""
    global pipeline_running
    if pipeline_running:
        raise HTTPException(status_code=400, detail="Pipeline is already running in the background.")
        
    background_tasks.add_task(run_pipeline_task)
    return {
        "status": "success",
        "message": "Pipeline resumption triggered in the background."
    }

class BackupCreateRequest(BaseModel):
    label: str = None

class BackupRestoreRequest(BaseModel):
    name: str

@router.get("/api/backup/list")
def list_backups_endpoint():
    """Retrieves all vector database snapshot backups."""
    return backup_service.list_backups()

@router.post("/api/backup/create")
def create_backup_endpoint(req: BackupCreateRequest = None):
    """Triggers a point-in-time snapshot backup of the ChromaDB collection."""
    label = req.label if req else None
    try:
        name = backup_service.create_backup(label)
        return {"status": "success", "message": f"Snapshot backup '{name}' created successfully.", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")

@router.post("/api/backup/restore")
def restore_backup_endpoint(req: BackupRestoreRequest):
    """Restores the ChromaDB collection to a targeted point-in-time snapshot."""
    try:
        backup_service.restore_backup(req.name)
        return {"status": "success", "message": f"ChromaDB restored to snapshot '{req.name}' successfully."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")

@router.delete("/api/backup/{name}")
def delete_backup_endpoint(name: str):
    """Permanently deletes a database snapshot backup."""
    try:
        backup_service.delete_backup(name)
        return {"status": "success", "message": f"Backup snapshot '{name}' deleted permanently."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")


class SingleIngestRequest(BaseModel):
    text: str
    sender: str = "User"

@router.post("/api/ingest/message")
def ingest_single_message(request: SingleIngestRequest, background_tasks: BackgroundTasks):
    """Appends a single chat message/link formatted in WhatsApp style to the chat database log
    and triggers a background ETL and indexing run.
    """
    global pipeline_running
    
    # Format the message in WhatsApp style
    now = datetime.datetime.now()
    timestamp = now.strftime("%-m/%-d/%y, %H:%M") # e.g. "5/27/26, 06:26"
    
    # Clean/normalize formatting
    formatted_msg = f"{timestamp} - {request.sender}: {request.text}\n"
    
    try:
        config.initialize_directories()
        
        # Ensure a newline exists at the end of the existing file if it has content
        prefix = ""
        if config.chat_file_path.exists():
            with open(config.chat_file_path, "r", encoding="utf-8") as f:
                existing = f.read()
                if existing and not existing.endswith("\n"):
                    prefix = "\n"
        
        with open(config.chat_file_path, "a", encoding="utf-8") as f:
            f.write(prefix + formatted_msg)
            
        # Trigger background pipeline if not already running
        if not pipeline_running:
            background_tasks.add_task(run_pipeline_task)
            
        return {
            "status": "success",
            "message": "Message successfully appended to chat log and ingestion triggered.",
            "formatted_message": formatted_msg.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to append message: {str(e)}")

@router.post("/api/ingest/file")
def ingest_text_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Appends an uploaded supplementary text file containing chat logs/notes to the active chat log
    and triggers a background pipeline resumption.
    """
    global pipeline_running
    
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only plain text (.txt) files are supported.")
        
    try:
        content_bytes = file.file.read()
        content = content_bytes.decode("utf-8")
        
        config.initialize_directories()
        
        # Format the content: ensure it starts with a newline if the active file is not empty
        prefix = "\n"
        if config.chat_file_path.exists():
            with open(config.chat_file_path, "r", encoding="utf-8") as f:
                existing = f.read()
                if not existing or existing.endswith("\n"):
                    prefix = ""
        else:
            prefix = ""
            
        with open(config.chat_file_path, "a", encoding="utf-8") as f:
            f.write(prefix + content + "\n")
            
        # Trigger background pipeline if not already running
        if not pipeline_running:
            background_tasks.add_task(run_pipeline_task)
            
        return {
            "status": "success",
            "message": f"Successfully merged {file.filename} into active database and triggered ingestion.",
            "bytes_appended": len(content_bytes)
        }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Failed to decode file as UTF-8 text.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file upload: {str(e)}")


@router.post("/api/ingest/folder")
def ingest_folder(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Accepts a multipart upload of files representing a selected WhatsApp export folder (chat log + attachments),
    saves them in a secure temporary folder, runs scanner/parser workflows, optimizes assets, indexes them in SQLite/ChromaDB.
    """
    import shutil
    from core.scanner import LocalFolderScanner
    from core.parser import WhatsAppParser
    from core.preprocessor import Preprocessor
    from core.media import MediaOptimizer
    from services.media_service import OCRProcessor
    from services.contact_service import VCardParser
    from core.database import ContactRepository
    from core.llm_engine import LMStudioHermesClient

    config.initialize_directories()
    
    # Setup temporary ingestion directory
    temp_dir = config.output_dir / "temp" / "folder_ingest"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    try:
        # Save all files to temp directory
        for file in files:
            clean_filename = Path(file.filename).name
            target_path = temp_dir / clean_filename
            with open(target_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_count += 1

        # Scan folder using LocalFolderScanner
        scanner = LocalFolderScanner()
        scan_result = scanner.scan(temp_dir)

        # Parse chat log
        parser = WhatsAppParser()
        raw_msgs = parser.parse_file(str(scan_result.chat_log_path))

        # Core enrichment tools
        media_optimizer = MediaOptimizer()
        ocr_processor = OCRProcessor()
        vcard_parser = VCardParser()
        contact_repo = ContactRepository()
        
        # Instantiate LLM client if SDK is enabled, otherwise mock/None
        llm_client = None
        if config.lms_sdk_enabled:
            llm_client = LMStudioHermesClient()

        # Align, process and segment the conversation chronologically
        preprocessor = Preprocessor()
        segments = preprocessor.enrich_conversation(
            raw_msgs=raw_msgs,
            directory_path=temp_dir,
            media_optimizer=media_optimizer,
            ocr_processor=ocr_processor,
            vcard_parser=vcard_parser,
            contact_repo=contact_repo,
            llm_client=llm_client
        )

        # Index segments in ChromaDB vector database
        vector_indexer = ChromaDBIndexer()
        for seg in segments:
            # Build text representation for vector indexing
            convo_lines = []
            for msg in seg.messages:
                convo_lines.append(f"[{msg.sender}]: {msg.content}")
            conversation_text = "\n".join(convo_lines)
            
            document_text = (
                f"[Context Segment: {seg.segment_id} | Range: {seg.start_time} to {seg.end_time}]\n"
                f"[Summary: {seg.summary or 'None'}]\n"
                f"[Tags: {', '.join(seg.tags)}]\n"
                f"Conversation log:\n{conversation_text}"
            )
            
            # Index segment in ChromaDB
            vector_indexer.index_segment(
                segment_id=seg.segment_id,
                document_text=document_text,
                start_time=seg.start_time,
                end_time=seg.end_time,
                messages=[msg.model_dump() for msg in seg.messages],
                tags=seg.tags
            )

        # Also save the parsed chat segment sequence database to parsed_chat.json
        parsed_chat_path = config.output_dir / "parsed_chat.json"
        chat_data = [seg.model_dump() for seg in segments]
        with open(parsed_chat_path, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=2, ensure_ascii=False)

        return {
            "status": "success",
            "message": f"Successfully processed {saved_count} files from the selected folder.",
            "scan_result": {
                "chat_log": Path(scan_result.chat_log_path).name,
                "media_count": len(scan_result.media_files),
                "vcards_count": len(scan_result.vcard_files)
            },
            "segments_indexed": len(segments)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal folder ingestion failed: {str(e)}")
    finally:
        # Clean up temporary upload files
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@router.get("/api/archive/export")
def export_archive_endpoint(background_tasks: BackgroundTasks):
    """Generates and streams a unified zip file backup containing the raw chat, markdown pages, images, and ChromaDB."""
    global pipeline_running
    if pipeline_running:
        raise HTTPException(status_code=400, detail="Cannot export archive while the ingestion pipeline is running.")

    # Create temp directory inside output directory
    temp_dir = config.output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"personal_memory_archive_{timestamp}.zip"
    zip_path = temp_dir / zip_filename
    
    try:
        from backend.services.archive_service import archive_service
        archive_service.export_archive(zip_path)
        
        # Schedule the temporary zip file deletion after it has been streamed
        def cleanup_temp_file(path: Path):
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass
                
        background_tasks.add_task(cleanup_temp_file, zip_path)
        
        return FileResponse(
            path=str(zip_path),
            filename=zip_filename,
            media_type="application/zip"
        )
    except Exception as e:
        if zip_path.exists():
            try:
                zip_path.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to generate backup archive: {str(e)}")

@router.post("/api/archive/import")
def import_archive_endpoint(file: UploadFile = File(...)):
    """Uploads, extracts, and restores a unified personal memory zip archive, hot-swapping all assets and ChromaDB."""
    global pipeline_running
    if pipeline_running:
        raise HTTPException(status_code=400, detail="Cannot import archive while the ingestion pipeline is running.")
        
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip archive files are supported.")
        
    # Write uploaded zip to temp file
    temp_dir = config.output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_zip_path = temp_dir / f"import_{uuid.uuid4().hex[:8]}.zip"
    
    try:
        with open(temp_zip_path, "wb") as f:
            f.write(file.file.read())
            
        from backend.services.archive_service import archive_service
        archive_service.import_archive(temp_zip_path)
        
        return {
            "status": "success",
            "message": "Memory base archive imported successfully. UI dashboard and databases hot-reloaded."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import memory archive: {str(e)}")
    finally:
        if temp_zip_path.exists():
            try:
                temp_zip_path.unlink()
            except Exception:
                pass


@router.get("/api/media/{filename}")
def serve_media_file(filename: str):
    """Serves optimized media files (such as AVIF images) from the local storage cache."""
    optimized_dir = config.output_dir / "optimized_media"
    file_path = optimized_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found.")
        
    suffix = file_path.suffix.lower()
    if suffix == ".avif":
        media_type = "image/avif"
    elif suffix == ".webp":
        media_type = "image/webp"
    elif suffix == ".png":
        media_type = "image/png"
    elif suffix == ".jpg" or suffix == ".jpeg":
        media_type = "image/jpeg"
    else:
        media_type = "application/octet-stream"
        
    return FileResponse(path=str(file_path), media_type=media_type)



