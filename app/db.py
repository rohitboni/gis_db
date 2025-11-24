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

# Create engine with PostGIS support and SSL for RDS
# Parse connection string to add SSL parameters if not present
database_url = settings.database_url
if 'sslmode' not in database_url and 'rds.amazonaws.com' in database_url:
    # Add SSL mode for AWS RDS if not already present
    separator = '&' if '?' in database_url else '?'
    database_url = f"{database_url}{separator}sslmode=require"

engine = create_engine(
    database_url,
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
    import time
    
    # Retry connection with exponential backoff for RDS
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Test connection first
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"✓ Database connection successful (attempt {attempt + 1})")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠ Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"  Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"✗ Database connection failed after {max_retries} attempts: {e}")
                raise
    
    # Enable PostGIS extension FIRST (before creating tables)
    # Use begin() for proper transaction handling
    try:
        with engine.begin() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                print("✓ PostGIS extension enabled successfully")
            except Exception as e:
                # If extension already exists, that's fine - continue
                print(f"ℹ PostGIS extension check: {e}")
                # Extension might already exist, so we continue
    except Exception as e:
        print(f"⚠ Error during PostGIS extension setup: {e}")
        # Continue anyway - extension might already exist
    
    # Import models to register them
    from app.models import Feature, GeoFile
    
    # Create tables AFTER PostGIS extension is enabled
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables initialized successfully")
    except Exception as e:
        print(f"⚠ Error creating tables: {e}")
        # Tables might already exist, continue
