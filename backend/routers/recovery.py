from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from backend.services.recovery_service import RecoveryService

router = APIRouter()
recovery_service = RecoveryService()

class IngestRequest(BaseModel):
    url: str
    category: str

@router.post("/api/recovery/ingest")
def recover_url(request: IngestRequest, background_tasks: BackgroundTasks):
    """Enqueues an async background web crawling, local compilation, image caching, and vector indexing task."""
    task_id = recovery_service.trigger_recovery_ingest(request.url, request.category)
    
    # Enqueue background task to keep execution fully non-blocking
    background_tasks.add_task(
        recovery_service.run_async_ingest,
        url=request.url,
        category=request.category,
        task_id=task_id
    )
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": f"Ingestion task {task_id} successfully queued for URL {request.url}"
    }
