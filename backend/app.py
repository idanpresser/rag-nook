from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
