from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime
import os
import uuid
from app.database import get_db
from app.models import GISData
from app.schemas import FileUploadResponse, GISDataResponse
from app.services.file_handler import FileHandler
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
import json

router = APIRouter()

# Initialize file handler
s3_bucket = os.getenv("S3_BUCKET_NAME")
aws_region = os.getenv("AWS_REGION", "us-east-1")
file_handler = FileHandler(s3_bucket=s3_bucket, aws_region=aws_region)


@router.post("/upload/geojson", response_model=FileUploadResponse)
async def upload_geojson(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process a GeoJSON file"""
    if not file.filename.endswith(('.geojson', '.json')):
        raise HTTPException(status_code=400, detail="File must be a GeoJSON file")
    
    try:
        # Generate unique file path
        file_id = str(uuid.uuid4())
        file_key = f"geojson/{file_id}/{file.filename}"
        
        # Process the GeoJSON file
        processed_data = await file_handler.process_geojson(file)
        
        # Reset file pointer before upload
        await file.seek(0)
        
        # Upload to S3 if configured, otherwise store locally
        if s3_bucket:
            file_path = await file_handler.upload_to_s3(file, file_key)
        else:
            # Local storage (for development)
            os.makedirs("uploads/geojson", exist_ok=True)
            local_path = f"uploads/geojson/{file_id}_{file.filename}"
            with open(local_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_path = local_path
        
        # Convert geometry to PostGIS format
        geometry = None
        if processed_data["geometry"]:
            shapely_geom = shape(processed_data["geometry"])
            geometry = from_shape(shapely_geom, srid=4326)
        
        # Create database record
        db_data = GISData(
            name=name,
            description=description,
            file_type="geojson",
            file_name=file.filename,
            file_path=file_path,
            geometry=geometry,
            properties=processed_data["properties"],
            bbox=processed_data["bbox"],
            srid=4326,
            feature_count=processed_data["feature_count"],
            file_size=file.size if hasattr(file, 'size') else None
        )
        
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        
        return FileUploadResponse(
            message="GeoJSON file uploaded successfully",
            file_id=db_data.id,
            file_name=file.filename,
            file_path=file_path
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@router.post("/upload/shapefile", response_model=FileUploadResponse)
async def upload_shapefile(
    shp_file: UploadFile = File(...),
    shx_file: Optional[UploadFile] = File(None),
    dbf_file: Optional[UploadFile] = File(None),
    prj_file: Optional[UploadFile] = File(None),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process a Shapefile (requires .shp, .shx, .dbf files)"""
    if not shp_file.filename.endswith('.shp'):
        raise HTTPException(status_code=400, detail="Main file must be a .shp file")
    
    try:
        # Collect additional files
        additional_files = {}
        if shx_file:
            additional_files['.shx'] = shx_file
        if dbf_file:
            additional_files['.dbf'] = dbf_file
        if prj_file:
            additional_files['.prj'] = prj_file
        
        # Process the shapefile
        processed_data = await file_handler.process_shapefile(shp_file, additional_files)
        
        # Generate unique file path
        file_id = str(uuid.uuid4())
        file_key = f"shapefile/{file_id}/{shp_file.filename}"
        
        # Upload to S3 if configured
        if s3_bucket:
            file_path = await file_handler.upload_to_s3(shp_file, file_key)
        else:
            os.makedirs("uploads/shapefile", exist_ok=True)
            local_path = f"uploads/shapefile/{file_id}_{shp_file.filename}"
            with open(local_path, "wb") as f:
                content = await shp_file.read()
                f.write(content)
            file_path = local_path
        
        # Convert geometry to PostGIS format
        geometry = None
        if processed_data["geometry"]:
            shapely_geom = shape(processed_data["geometry"])
            geometry = from_shape(shapely_geom, srid=4326)
        
        # Create database record
        db_data = GISData(
            name=name,
            description=description,
            file_type="shapefile",
            file_name=shp_file.filename,
            file_path=file_path,
            geometry=geometry,
            properties=processed_data["properties"],
            bbox=processed_data["bbox"],
            srid=4326,
            feature_count=processed_data["feature_count"],
            file_size=shp_file.size if hasattr(shp_file, 'size') else None
        )
        
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        
        return FileUploadResponse(
            message="Shapefile uploaded successfully",
            file_id=db_data.id,
            file_name=shp_file.filename,
            file_path=file_path
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing shapefile: {str(e)}")


@router.post("/upload/kml", response_model=FileUploadResponse)
async def upload_kml(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process a KML file"""
    if not file.filename.endswith('.kml'):
        raise HTTPException(status_code=400, detail="File must be a KML file")
    
    try:
        # Process the KML file
        processed_data = await file_handler.process_kml(file)
        
        # Generate unique file path
        file_id = str(uuid.uuid4())
        file_key = f"kml/{file_id}/{file.filename}"
        
        # Upload to S3 if configured
        if s3_bucket:
            file_path = await file_handler.upload_to_s3(file, file_key)
        else:
            os.makedirs("uploads/kml", exist_ok=True)
            local_path = f"uploads/kml/{file_id}_{file.filename}"
            with open(local_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_path = local_path
        
        # Convert geometry to PostGIS format
        geometry = None
        if processed_data["geometry"]:
            shapely_geom = shape(processed_data["geometry"])
            geometry = from_shape(shapely_geom, srid=4326)
        
        # Create database record
        db_data = GISData(
            name=name,
            description=description,
            file_type="kml",
            file_name=file.filename,
            file_path=file_path,
            geometry=geometry,
            properties=processed_data["properties"],
            bbox=processed_data["bbox"],
            srid=4326,
            feature_count=processed_data["feature_count"],
            file_size=file.size if hasattr(file, 'size') else None
        )
        
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        
        return FileUploadResponse(
            message="KML file uploaded successfully",
            file_id=db_data.id,
            file_name=file.filename,
            file_path=file_path
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing KML file: {str(e)}")

