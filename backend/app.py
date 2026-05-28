from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

# Globally increase Starlette/FastAPI's multipart form field/file limits (default 1000)
# to safely support WhatsApp export folder ingestion with thousands of files.
original_form = Request.form
async def patched_form(self, *, max_files=100000, max_fields=100000, max_part_size=104857600):  # 100k files/fields, 100MB part size
    return await original_form(self, max_files=max_files, max_fields=max_fields, max_part_size=max_part_size)
Request.form = patched_form

from backend.routers import search, metadata, recovery

app = FastAPI(
    title="Insights Explorer API",
    description="FastAPI backend service layer for the WhatsApp RAG Insights Explorer.",
    version="1.0.0"
)

# Configure CORS to allow the local Vite React frontend to connect seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include SOLID routers
app.include_router(search.router)
app.include_router(metadata.router)
app.include_router(recovery.router)

@app.get("/")
def read_root():
    return {
        "title": "Insights Explorer API",
        "version": "1.0.0",
        "documentation": "/docs"
    }
