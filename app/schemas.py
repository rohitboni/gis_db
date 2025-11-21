from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from geojson import Feature, FeatureCollection


class GISDataBase(BaseModel):
    name: str
    description: Optional[str] = None
    file_type: str
    file_name: str
    properties: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    srid: int = 4326
    feature_count: int = 0
    file_size: Optional[float] = None


class GISDataCreate(GISDataBase):
    geometry: Optional[str] = None  # WKT or GeoJSON string
    file_path: str


class GISDataUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class GISDataResponse(GISDataBase):
    id: int
    file_path: str
    geometry: Optional[Dict[str, Any]] = None  # GeoJSON geometry
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    message: str
    file_id: int
    file_name: str
    file_path: str


class SpatialQueryRequest(BaseModel):
    geometry: Dict[str, Any]  # GeoJSON geometry
    operation: str = Field(..., description="intersects, contains, within, distance")
    distance: Optional[float] = None  # For distance queries (in meters)


class SpatialQueryResponse(BaseModel):
    results: List[GISDataResponse]
    count: int

