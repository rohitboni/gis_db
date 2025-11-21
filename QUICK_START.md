# Quick Start Guide

## Local Development Setup (5 minutes)

### 1. Install PostgreSQL with PostGIS

**macOS (Homebrew):**
```bash
brew install postgresql postgis
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgis
sudo systemctl start postgresql
```

### 2. Create Database

```bash
psql -U postgres
```

In PostgreSQL shell:
```sql
CREATE DATABASE gis_db;
\c gis_db
CREATE EXTENSION postgis;
\q
```

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example env file
cp env.example .env

# Edit .env file with your database credentials
# DATABASE_URL=postgresql://postgres:your_password@localhost:5432/gis_db
```

### 5. Initialize Database

```bash
python -c "from app.db import init_db; init_db()"
```

### 6. Run Application

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs in your browser to see the interactive API documentation!

## Test the API

### Upload a GeoJSON file

Create `test.geojson`:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"name": "Test Point"},
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      }
    }
  ]
}
```

Upload it:
```bash
curl -X POST "http://localhost:8000/features/upload" \
  -F "file=@test.geojson"
```

### List all features

```bash
curl http://localhost:8000/features
```

## Troubleshooting

**Can't connect to database:**
- Check PostgreSQL service is running: `sudo systemctl status postgresql`
- Verify DATABASE_URL in .env file
- Check database exists and PostGIS extension is enabled

**File upload fails:**
- Check file format is supported
- Ensure file is not corrupted
- For shapefiles, upload as ZIP containing .shp, .shx, .dbf files

**Import errors:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.9+ required)

