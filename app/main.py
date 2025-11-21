from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import gis_data, files, spatial_queries

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GIS Database Service",
    description="A service for managing GIS data with support for GeoJSON, Shapefiles, and spatial queries",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gis_data.router, prefix="/api/v1/gis-data", tags=["GIS Data"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(spatial_queries.router, prefix="/api/v1/spatial", tags=["Spatial Queries"])


@app.get("/")
async def root():
    return {
        "message": "GIS Database Service API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

