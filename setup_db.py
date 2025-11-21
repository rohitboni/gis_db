#!/usr/bin/env python3
"""
Database setup script - Run this to initialize the database with PostGIS
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/gis_db"
)

def setup_database():
    """Set up database and enable PostGIS extension"""
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT version()"))
            print(f"✓ Connected to PostgreSQL: {result.fetchone()[0][:50]}...")
            
            # Check if PostGIS extension exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'postgis'
                )
            """))
            postgis_exists = result.fetchone()[0]
            
            if postgis_exists:
                print("✓ PostGIS extension is already enabled")
            else:
                print("Creating PostGIS extension...")
                try:
                    # Note: This might require superuser privileges
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                    conn.commit()
                    print("✓ PostGIS extension enabled successfully")
                except Exception as e:
                    print(f"✗ Error enabling PostGIS extension: {e}")
                    print("\nYou may need to enable PostGIS manually:")
                    print("  psql -U postgres -d gis_db")
                    print("  CREATE EXTENSION postgis;")
                    return False
            
            # Verify PostGIS is working
            result = conn.execute(text("SELECT PostGIS_version()"))
            postgis_version = result.fetchone()[0]
            print(f"✓ PostGIS version: {postgis_version}")
            
            return True
            
    except OperationalError as e:
        print(f"✗ Connection error: {e}")
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'gis_db' exists")
        print("  3. DATABASE_URL in .env file is correct")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("PostgreSQL/PostGIS Database Setup")
    print("=" * 60)
    print()
    
    if setup_database():
        print()
        print("=" * 60)
        print("Database setup complete! You can now run the application.")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("Database setup failed. Please fix the issues above.")
        print("=" * 60)
        exit(1)

