from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, String
from typing import List, Optional
from uuid import UUID

from app.db import get_db
from app.models import GeoFile, Feature
from app.schemas import GeoFileResponse, GeoFileSummary, FeatureResponse, geometry_to_geojson
from app.services.file_parser import FileParser
from app.utils.geometry import geojson_to_wkb_element
from app.utils.file_metadata import extract_state_district_from_filename, extract_state_district_from_properties
from pathlib import Path

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=GeoFileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    state: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a geographic file and create a file record with all its features.
    
    Supported formats: GeoJSON, JSON, KML, KMZ, Shapefile (ZIP), GPX, CSV
    
    State is required and can be provided as a form field or will be extracted from file.
    """
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Detect file type
        file_type = FileParser.detect_file_type(file.filename)
        if file_type == 'unknown':
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {Path(file.filename).suffix}")
        
        # Parse file to get features
        parsed_features = FileParser.parse_file(file_content, file.filename)
        
        if not parsed_features:
            raise HTTPException(status_code=400, detail="No features found in file")
        
        # Use provided state/district, or extract from filename/properties
        if not state:
            # Extract state/district from filename
            filename_metadata = extract_state_district_from_filename(file.filename)
            
            # Extract state/district from properties (if not found in filename)
            properties_metadata = extract_state_district_from_properties(parsed_features)
            
            # Combine metadata (properties take precedence if available)
            state = properties_metadata.get('state') or filename_metadata.get('state')
        
        # Use provided district or extract it
        if not district:
            filename_metadata = extract_state_district_from_filename(file.filename)
            properties_metadata = extract_state_district_from_properties(parsed_features)
            district = properties_metadata.get('district') or filename_metadata.get('district')
        
        # State is required
        if not state:
            raise HTTPException(status_code=400, detail="State is required. Please provide state name or ensure file contains state information.")
        
        # Create file record
        db_file = GeoFile(
            filename=Path(file.filename).stem,
            original_filename=file.filename,
            file_type=file_type,
            state=state,
            district=district,
            total_features=len(parsed_features),
            file_size=file_size
        )
        db.add(db_file)
        db.flush()  # Flush to get the file ID
        
        # Create feature records
        db_features = []
        for parsed_feature in parsed_features:
            try:
                # Convert geometry to WKBElement
                geometry_wkb = geojson_to_wkb_element(parsed_feature['geometry'])
                
                # Create Feature model linked to file
                db_feature = Feature(
                    file_id=db_file.id,
                    name=parsed_feature['name'],
                    properties=parsed_feature.get('properties', {}),
                    geometry=geometry_wkb
                )
                
                db.add(db_feature)
                db_features.append(db_feature)
                
            except Exception as e:
                # Log error but continue with other features
                print(f"Error processing feature {parsed_feature.get('name')}: {str(e)}")
                continue
        
        if not db_features:
            db.rollback()
            raise HTTPException(status_code=400, detail="Failed to process any features from file")
        
        # Update total_features count with actual saved features
        db_file.total_features = len(db_features)
        
        db.commit()
        db.refresh(db_file)
        
        return GeoFileResponse(
            id=db_file.id,
            filename=db_file.filename,
            original_filename=db_file.original_filename,
            file_type=db_file.file_type,
            state=db_file.state,
            district=db_file.district,
            total_features=db_file.total_features,
            file_size=db_file.file_size,
            created_at=db_file.created_at,
            updated_at=db_file.updated_at
        )
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = str(e)
        print(f"Upload error: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing file: {error_detail}")


@router.get("", response_model=List[GeoFileSummary])
def list_files(
    state: Optional[str] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all uploaded files, optionally filtered by state and/or district.
    """
    query = db.query(GeoFile)
    
    if state:
        query = query.filter(
            or_(
                cast(GeoFile.state, String).ilike(f"%{state}%"),
            )
        )
    
    if district:
        query = query.filter(
            or_(
                cast(GeoFile.district, String).ilike(f"%{district}%"),
            )
        )
    
    files = query.order_by(GeoFile.created_at.desc()).all()
    
    return [
        GeoFileSummary(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            file_type=file.file_type,
            state=file.state,
            district=file.district,
            total_features=file.total_features,
            file_size=file.file_size,
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        for file in files
    ]


@router.get("/states", response_model=List[str])
def list_states(db: Session = Depends(get_db)):
    """
    Get list of all unique states from uploaded files.
    """
    query = db.query(
        func.distinct(cast(GeoFile.state, String))
    ).filter(GeoFile.state.isnot(None))
    
    states = [s for s, in query.all() if s]
    return sorted(list(set(states)))


@router.get("/districts", response_model=List[str])
def list_districts(
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of all unique districts from uploaded files.
    Optionally filtered by state.
    """
    query = db.query(
        func.distinct(cast(GeoFile.district, String))
    ).filter(GeoFile.district.isnot(None))
    
    if state:
        query = query.filter(cast(GeoFile.state, String).ilike(f"%{state}%"))
    
    districts = [d for d, in query.all() if d]
    return sorted(list(set(districts)))


@router.get("/{file_id}", response_model=GeoFileResponse)
def get_file(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a single file by ID"""
    file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return GeoFileResponse(
        id=file.id,
        filename=file.filename,
        original_filename=file.original_filename,
        file_type=file.file_type,
        state=file.state,
        district=file.district,
        total_features=file.total_features,
        file_size=file.file_size,
        created_at=file.created_at,
        updated_at=file.updated_at
    )


@router.get("/{file_id}/features", response_model=List[FeatureResponse])
def get_file_features(
    file_id: UUID,
    skip: int = 0,
    limit: int = 100,
    include_geometry: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all features for a specific file.
    """
    # Verify file exists
    file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get features for this file
    query = db.query(Feature).filter(Feature.file_id == file_id)
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


@router.delete("/{file_id}", status_code=204)
def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a file and all its features"""
    file = db.query(GeoFile).filter(GeoFile.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete file (cascade will delete features)
    db.delete(file)
    db.commit()
    
    return None

