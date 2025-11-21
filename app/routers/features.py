from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_, cast, String
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional
from uuid import UUID

from app.db import get_db
from app.models import Feature
from app.schemas import FeatureResponse, FeatureUpdate, geometry_to_geojson
from app.services.file_parser import FileParser
from app.utils.geometry import geojson_to_wkb_element

router = APIRouter(prefix="/features", tags=["features"])


@router.post("/upload", response_model=List[FeatureResponse], status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a geographic file and parse it into features.
    
    NOTE: This endpoint is deprecated. Features now require a file_id.
    Please use /files/upload instead to upload files with features.
    """
    raise HTTPException(
        status_code=400, 
        detail="This endpoint is deprecated. Please use /files/upload to upload files with features. Features require a file_id."
    )


@router.get("", response_model=List[FeatureResponse])
def list_features(
    skip: int = 0,
    limit: int = 100,
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    village: Optional[str] = None,
    state: Optional[str] = None,
    include_geometry: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all features with pagination and optional filtering by hierarchical fields.
    
    Filters can use any of the common property field names:
    - District: District_Name, district, DISTRICT, District
    - Taluk: Taluk_Name, taluk, TALUK, Taluk, Block_Name, block
    - Village: Village_Name, village, VILLAGE, Village
    - State: State_Name, state, STATE, State
    """
    query = db.query(Feature)
    
    # Build filters for JSONB properties
    # Support multiple possible field names in properties
    # Use cast to convert JSON values to text for PostgreSQL
    if district:
        district_filters = []
        for field in ['District_Name', 'district', 'DISTRICT', 'District', 'district_name']:
            district_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{district}%")
            )
        query = query.filter(or_(*district_filters))
    
    if taluk:
        taluk_filters = []
        for field in ['Taluk_Name', 'taluk', 'TALUK', 'Taluk', 'Block_Name', 'block', 'taluk_name']:
            taluk_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{taluk}%")
            )
        query = query.filter(or_(*taluk_filters))
    
    if village:
        village_filters = []
        for field in ['Village_Name', 'village', 'VILLAGE', 'Village', 'village_name']:
            village_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{village}%")
            )
        query = query.filter(or_(*village_filters))
    
    if state:
        state_filters = []
        for field in ['State_Name', 'state', 'STATE', 'State', 'state_name']:
            state_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{state}%")
            )
        query = query.filter(or_(*state_filters))
    
    features = query.offset(skip).limit(limit).all()
    
    from geoalchemy2.shape import to_shape
    
    return [
        FeatureResponse(
            id=feature.id,
            file_id=feature.file_id,
            name=feature.name,
            properties=feature.properties,
            geometry=geometry_to_geojson(feature.geometry) if include_geometry else {
                "type": to_shape(feature.geometry).geom_type,
                "coordinates": []
            },
            created_at=feature.created_at,
            updated_at=feature.updated_at
        )
        for feature in features
    ]


@router.get("/districts", response_model=List[str])
def list_districts(
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of all unique districts from properties.
    Optionally filter by state.
    """
    # Build coalesce expression for district field names
    # Cast JSON values to String for PostgreSQL
    district_fields = [
        cast(Feature.properties['District_Name'], String),
        cast(Feature.properties['district'], String),
        cast(Feature.properties['DISTRICT'], String),
        cast(Feature.properties['District'], String),
        cast(Feature.properties['district_name'], String)
    ]
    
    query = db.query(
        func.distinct(func.coalesce(*district_fields))
    ).filter(func.coalesce(*district_fields).isnot(None))
    
    if state:
        state_filters = []
        for field in ['State_Name', 'state', 'STATE', 'State', 'state_name']:
            state_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{state}%")
            )
        query = query.filter(or_(*state_filters))
    
    # Filter out None values and sort
    districts = [d for d, in query.all() if d]
    return sorted(list(set(districts)))


@router.get("/taluks", response_model=List[str])
def list_taluks(
    district: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of all unique taluks from properties.
    Optionally filter by district.
    """
    # Build coalesce expression for taluk field names
    # Cast JSON values to String for PostgreSQL
    taluk_fields = [
        cast(Feature.properties['Taluk_Name'], String),
        cast(Feature.properties['taluk'], String),
        cast(Feature.properties['TALUK'], String),
        cast(Feature.properties['Taluk'], String),
        cast(Feature.properties['Block_Name'], String),
        cast(Feature.properties['block'], String),
        cast(Feature.properties['taluk_name'], String)
    ]
    
    query = db.query(
        func.distinct(func.coalesce(*taluk_fields))
    ).filter(func.coalesce(*taluk_fields).isnot(None))
    
    if district:
        district_filters = []
        for field in ['District_Name', 'district', 'DISTRICT', 'District', 'district_name']:
            district_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{district}%")
            )
        query = query.filter(or_(*district_filters))
    
    # Filter out None values and sort
    taluks = [t for t, in query.all() if t]
    return sorted(list(set(taluks)))


@router.get("/villages", response_model=List[str])
def list_villages(
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of all unique villages from properties.
    Optionally filter by district and/or taluk.
    """
    # Build coalesce expression for village field names
    # Cast JSON values to String for PostgreSQL
    village_fields = [
        cast(Feature.properties['Village_Name'], String),
        cast(Feature.properties['village'], String),
        cast(Feature.properties['VILLAGE'], String),
        cast(Feature.properties['Village'], String),
        cast(Feature.properties['village_name'], String)
    ]
    
    query = db.query(
        func.distinct(func.coalesce(*village_fields))
    ).filter(func.coalesce(*village_fields).isnot(None))
    
    if district:
        district_filters = []
        for field in ['District_Name', 'district', 'DISTRICT', 'District', 'district_name']:
            district_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{district}%")
            )
        query = query.filter(or_(*district_filters))
    
    if taluk:
        taluk_filters = []
        for field in ['Taluk_Name', 'taluk', 'TALUK', 'Taluk', 'Block_Name', 'block', 'taluk_name']:
            taluk_filters.append(
                cast(Feature.properties[field], String).ilike(f"%{taluk}%")
            )
        query = query.filter(or_(*taluk_filters))
    
    # Filter out None values and sort
    villages = [v for v, in query.all() if v]
    return sorted(list(set(villages)))


@router.get("/states", response_model=List[str])
def list_states(db: Session = Depends(get_db)):
    """
    Get list of all unique states from properties.
    """
    # Build coalesce expression for state field names
    # Cast JSON values to String for PostgreSQL
    state_fields = [
        cast(Feature.properties['State_Name'], String),
        cast(Feature.properties['state'], String),
        cast(Feature.properties['STATE'], String),
        cast(Feature.properties['State'], String),
        cast(Feature.properties['state_name'], String)
    ]
    
    query = db.query(
        func.distinct(func.coalesce(*state_fields))
    ).filter(func.coalesce(*state_fields).isnot(None))
    
    # Filter out None values and sort
    states = [s for s, in query.all() if s]
    return sorted(list(set(states)))


@router.get("/{feature_id}", response_model=FeatureResponse)
def get_feature(
    feature_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a single feature by ID"""
    try:
        feature = db.query(Feature).filter(Feature.id == feature_id).first()
        
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Convert geometry to GeoJSON
        try:
            geometry_geojson = geometry_to_geojson(feature.geometry)
            if geometry_geojson is None:
                raise ValueError("Failed to convert geometry to GeoJSON")
        except Exception as e:
            print(f"Error converting geometry: {str(e)}")
            # If geometry conversion fails, return a basic geometry structure
            from geoalchemy2.shape import to_shape
            try:
                shape = to_shape(feature.geometry)
                geometry_geojson = {
                    "type": shape.geom_type,
                    "coordinates": []
                }
            except Exception:
                geometry_geojson = {
                    "type": "Unknown",
                    "coordinates": []
                }
        
        return FeatureResponse(
            id=feature.id,
            file_id=feature.file_id,
            name=feature.name,
            properties=feature.properties,
            geometry=geometry_geojson,
            created_at=feature.created_at,
            updated_at=feature.updated_at
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        import traceback
        print(f"Error in get_feature: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error loading feature: {str(e)}")


@router.put("/{feature_id}", response_model=FeatureResponse)
def update_feature(
    feature_id: UUID,
    feature_update: FeatureUpdate,
    db: Session = Depends(get_db)
):
    """Update a feature's properties or geometry"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Update name
    if feature_update.name is not None:
        feature.name = feature_update.name
    
    # Update properties
    if feature_update.properties is not None:
        feature.properties = feature_update.properties
    
    # Update geometry
    if feature_update.geometry is not None:
        try:
            geometry_wkb = geojson_to_wkb_element(feature_update.geometry)
            feature.geometry = geometry_wkb
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid geometry: {str(e)}")
    
    db.commit()
    db.refresh(feature)
    
    return FeatureResponse(
        id=feature.id,
        file_id=feature.file_id,
        name=feature.name,
        properties=feature.properties,
        geometry=geometry_to_geojson(feature.geometry),
        created_at=feature.created_at,
        updated_at=feature.updated_at
    )


@router.delete("/{feature_id}", status_code=204)
def delete_feature(
    feature_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a feature by ID"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    db.delete(feature)
    db.commit()
    
    return None

