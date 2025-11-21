from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from geoalchemy2 import functions as gf
from app.database import get_db
from app.models import GISData
from app.schemas import SpatialQueryRequest, SpatialQueryResponse, GISDataResponse
from app.utils import geometry_to_geojson
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
import json

router = APIRouter()


@router.post("/intersects", response_model=SpatialQueryResponse)
async def spatial_intersects(
    query: SpatialQueryRequest,
    db: Session = Depends(get_db)
):
    """Find all geometries that intersect with the given geometry"""
    try:
        # Convert GeoJSON to PostGIS geometry
        shapely_geom = shape(query.geometry)
        query_geom = from_shape(shapely_geom, srid=4326)
        
        # Query for intersecting geometries
        results = db.query(GISData).filter(
            gf.ST_Intersects(GISData.geometry, query_geom)
        ).all()
        
        response_list = []
        for result in results:
            response_data = GISDataResponse.model_validate(result)
            response_data.geometry = geometry_to_geojson(result.geometry)
            response_list.append(response_data)
        
        return SpatialQueryResponse(
            results=response_list,
            count=len(response_list)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in spatial query: {str(e)}")


@router.post("/within", response_model=SpatialQueryResponse)
async def spatial_within(
    query: SpatialQueryRequest,
    db: Session = Depends(get_db)
):
    """Find all geometries that are within the given geometry"""
    try:
        shapely_geom = shape(query.geometry)
        query_geom = from_shape(shapely_geom, srid=4326)
        
        results = db.query(GISData).filter(
            gf.ST_Within(GISData.geometry, query_geom)
        ).all()
        
        response_list = []
        for result in results:
            response_data = GISDataResponse.model_validate(result)
            response_data.geometry = geometry_to_geojson(result.geometry)
            response_list.append(response_data)
        
        return SpatialQueryResponse(
            results=response_list,
            count=len(response_list)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in spatial query: {str(e)}")


@router.post("/contains", response_model=SpatialQueryResponse)
async def spatial_contains(
    query: SpatialQueryRequest,
    db: Session = Depends(get_db)
):
    """Find all geometries that contain the given geometry"""
    try:
        shapely_geom = shape(query.geometry)
        query_geom = from_shape(shapely_geom, srid=4326)
        
        results = db.query(GISData).filter(
            gf.ST_Contains(GISData.geometry, query_geom)
        ).all()
        
        response_list = []
        for result in results:
            response_data = GISDataResponse.model_validate(result)
            response_data.geometry = geometry_to_geojson(result.geometry)
            response_list.append(response_data)
        
        return SpatialQueryResponse(
            results=response_list,
            count=len(response_list)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in spatial query: {str(e)}")


@router.post("/distance", response_model=SpatialQueryResponse)
async def spatial_distance(
    query: SpatialQueryRequest,
    db: Session = Depends(get_db)
):
    """Find all geometries within a certain distance from the given geometry"""
    if not query.distance:
        raise HTTPException(status_code=400, detail="Distance parameter is required")
    
    try:
        shapely_geom = shape(query.geometry)
        query_geom = from_shape(shapely_geom, srid=4326)
        
        # ST_DWithin uses the geometry's SRID units, so for 4326 we need to convert distance
        # For meters, we'll use ST_Distance_Sphere or transform to a metric projection
        results = db.query(GISData).filter(
            gf.ST_DWithin(
                GISData.geometry,
                query_geom,
                query.distance  # Distance in degrees for 4326, or use ST_Transform for meters
            )
        ).all()
        
        response_list = []
        for result in results:
            response_data = GISDataResponse.model_validate(result)
            response_data.geometry = geometry_to_geojson(result.geometry)
            response_list.append(response_data)
        
        return SpatialQueryResponse(
            results=response_list,
            count=len(response_list)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in spatial query: {str(e)}")

