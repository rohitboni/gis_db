from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
import uuid
from app.db import Base


class GeoFile(Base):
    __tablename__ = "geo_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # geojson, kml, shp, etc.
    state = Column(String, nullable=True, index=True)
    district = Column(String, nullable=True, index=True)
    total_features = Column(Integer, default=0)
    file_size = Column(Integer)  # Size in bytes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to features
    features = relationship("Feature", back_populates="file", cascade="all, delete-orphan")


class Feature(Base):
    __tablename__ = "features"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("geo_files.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    properties = Column(JSON, nullable=True)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to file
    file = relationship("GeoFile", back_populates="features")

