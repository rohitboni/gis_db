from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2 import functions as gf
from typing import List, Optional
from app.database import get_db
from app.models import GISData
from app.schemas import GISDataCreate, GISDataResponse, GISDataUpdate
from app.utils import geometry_to_geojson
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
import json

router = APIRouter()


@router.post("/", response_model=GISDataResponse, status_code=201)
async def create_gis_data(
    data: GISDataCreate,
    db: Session = Depends(get_db)
):
    """Create a new GIS data record"""
    try:
        # Convert geometry string to PostGIS geometry
        geometry = None
        if data.geometry:
            geom_dict = json.loads(data.geometry) if isinstance(data.geometry, str) else data.geometry
            shapely_geom = shape(geom_dict)
            geometry = from_shape(shapely_geom, srid=data.srid)
        
        db_data = GISData(
            name=data.name,
            description=data.description,
            file_type=data.file_type,
            file_name=data.file_name,
            file_path=data.file_path,
            geometry=geometry,
            properties=data.properties,
            bbox=data.bbox,
            srid=data.srid,
            feature_count=data.feature_count,
            file_size=data.file_size
        )
        
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        
        # Convert geometry back to GeoJSON for response
        response_data = GISDataResponse.model_validate(db_data)
        response_data.geometry = geometry_to_geojson(db_data.geometry)
        
        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[GISDataResponse])
async def get_all_gis_data(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    file_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all GIS data records with pagination"""
    query = db.query(GISData)
    
    if file_type:
        query = query.filter(GISData.file_type == file_type)
    
    results = query.offset(skip).limit(limit).all()
    
    response_list = []
    for result in results:
        response_data = GISDataResponse.model_validate(result)
        response_data.geometry = geometry_to_geojson(result.geometry)
        response_list.append(response_data)
    
    return response_list


@router.get("/{data_id}", response_model=GISDataResponse)
async def get_gis_data(
    data_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific GIS data record by ID"""
    data = db.query(GISData).filter(GISData.id == data_id).first()
    
    if not data:
        raise HTTPException(status_code=404, detail="GIS data not found")
    
    response_data = GISDataResponse.model_validate(data)
    response_data.geometry = geometry_to_geojson(data.geometry)
    
    return response_data


@router.put("/{data_id}", response_model=GISDataResponse)
async def update_gis_data(
    data_id: int,
    data_update: GISDataUpdate,
    db: Session = Depends(get_db)
):
    """Update a GIS data record"""
    db_data = db.query(GISData).filter(GISData.id == data_id).first()
    
    if not db_data:
        raise HTTPException(status_code=404, detail="GIS data not found")
    
    update_data = data_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_data, field, value)
    
    db.commit()
    db.refresh(db_data)
    
    response_data = GISDataResponse.model_validate(db_data)
    response_data.geometry = geometry_to_geojson(db_data.geometry)
    
    return response_data


@router.delete("/{data_id}", status_code=204)
async def delete_gis_data(
    data_id: int,
    db: Session = Depends(get_db)
):
    """Delete a GIS data record"""
    db_data = db.query(GISData).filter(GISData.id == data_id).first()
    
    if not db_data:
        raise HTTPException(status_code=404, detail="GIS data not found")
    
    db.delete(db_data)
    db.commit()
    
    return None

