from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.database import Base
from datetime import datetime


class GISData(Base):
    __tablename__ = "gis_data"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=False)  # geojson, shapefile, kml, etc.
    file_path = Column(String(500), nullable=False)  # S3 path or local path
    file_name = Column(String(255), nullable=False)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
    properties = Column(JSONB, nullable=True)  # Store feature properties
    bbox = Column(JSONB, nullable=True)  # Bounding box [minx, miny, maxx, maxy]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    srid = Column(Integer, default=4326)  # Spatial Reference System Identifier
    feature_count = Column(Integer, default=0)
    file_size = Column(Float, nullable=True)  # File size in bytes

