from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/gis_db"
    )
    
    class Config:
        env_file = ".env"


settings = Settings()

# Create engine with PostGIS support
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database and create PostGIS extension"""
    from sqlalchemy import text
    
    # Enable PostGIS extension FIRST (before creating tables)
    # Use begin() for proper transaction handling
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            print("PostGIS extension enabled successfully")
        except Exception as e:
            # If extension already exists, that's fine - continue
            print(f"Note: PostGIS extension check - {e}")
            # Extension might already exist, so we continue
    
    # Import models to register them
    from app.models import Feature, GeoFile
    
    # Create tables AFTER PostGIS extension is enabled
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully")

