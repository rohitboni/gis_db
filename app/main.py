from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import features, files

app = FastAPI(
    title="GIS Data API",
    description="API for storing and managing geographic data files",
    version="1.0.0"
)

# CORS middleware - must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files.router)
app.include_router(features.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get("/")
async def root():
    return {
        "message": "GIS Data API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

