from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from geoalchemy2.shape import to_shape


class GeoFileBase(BaseModel):
    filename: str
    original_filename: str
    file_type: str


class GeoFileCreate(GeoFileBase):
    state: Optional[str] = None
    district: Optional[str] = None
    file_size: Optional[int] = None


class GeoFileUpdate(BaseModel):
    filename: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None


class GeoFileResponse(GeoFileBase):
    id: UUID
    state: Optional[str] = None
    district: Optional[str] = None
    total_features: int
    file_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GeoFileSummary(GeoFileResponse):
    """File summary with feature count"""
    pass


class FeatureBase(BaseModel):
    name: str
    properties: Optional[Dict[str, Any]] = None


class FeatureCreate(FeatureBase):
    geometry: Dict[str, Any] = Field(..., description="Geometry in GeoJSON format")


class FeatureUpdate(BaseModel):
    name: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    geometry: Optional[Dict[str, Any]] = Field(None, description="Geometry in GeoJSON format")


class FeatureResponse(FeatureBase):
    id: UUID
    file_id: UUID
    geometry: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


def geometry_to_geojson(geometry):
    """Convert GeoAlchemy2 geometry to GeoJSON dict
    
    If the geometry coordinates are out of WGS84 bounds (lat: -90 to 90, lon: -180 to 180),
    it might be in a projected coordinate system. For display purposes, we'll still return
    the coordinates, but the frontend should handle invalid coordinate ranges.
    """
    if geometry is None:
        return None
    try:
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping
        shape_obj = to_shape(geometry)
        geojson = mapping(shape_obj)
        
        # Log a warning if coordinates seem invalid for WGS84
        bounds = shape_obj.bounds
        if bounds:
            minx, miny, maxx, maxy = bounds
            if not (-180 <= minx <= 180 and -180 <= maxx <= 180 and
                    -90 <= miny <= 90 and -90 <= maxy <= 90):
                import warnings
                warnings.warn(
                    f"Geometry coordinates are out of WGS84 range. "
                    f"Bounds: ({minx:.6f}, {miny:.6f}, {maxx:.6f}, {maxy:.6f}). "
                    f"This geometry may have been stored with incorrect coordinate system. "
                    f"Expected: longitude -180 to 180, latitude -90 to 90."
                )
        
        return geojson
    except Exception as e:
        # Fallback if conversion fails
        import traceback
        print(f"Error converting geometry to GeoJSON: {e}")
        print(traceback.format_exc())
        return None

