# GIS Data API

A FastAPI backend for storing and managing geographic data files with full CRUD operations. Supports multiple file formats including GeoJSON, Shapefiles, KML/KMZ, GPX, and CSV.

## Features

- **Multi-format Support**: GeoJSON, JSON, KML, KMZ, Shapefile (ZIP), GPX, CSV
- **PostGIS Integration**: Stores geometries in PostGIS-enabled PostgreSQL database
- **Full CRUD Operations**: Create, Read, Update, Delete features
- **Auto-detection**: Automatically detects and parses file types
- **Flexible Storage**: Stores all attributes in JSONB column alongside geometry

## Supported File Formats

- `.geojson` / `.json` - GeoJSON format
- `.kml` - Keyhole Markup Language
- `.kmz` - Compressed KML (ZIP containing KML)
- `.shp` - Shapefile (must be uploaded as ZIP with .shp, .shx, .dbf files)
- `.gpx` - GPS Exchange Format
- `.csv` - CSV with lat/lon columns or WKT geometry column

## Project Structure

```
app/
 ├── main.py                 # FastAPI application entry point
 ├── db.py                   # Database connection and configuration
 ├── models.py               # SQLAlchemy models
 ├── schemas.py              # Pydantic schemas for request/response
 ├── routers/
 │     └── features.py       # Feature CRUD endpoints
 ├── services/
 │     └── file_parser.py    # File parsing logic for all formats
 └── utils/
       └── geometry.py       # Geometry conversion utilities
```

## Local Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 12+ with PostGIS extension

### Installation

1. **Clone and navigate to project directory**

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database**

Install PostgreSQL and PostGIS:
```bash
# macOS (using Homebrew)
brew install postgresql postgis

# Ubuntu/Debian
sudo apt-get install postgresql postgis

# Start PostgreSQL service
# macOS
brew services start postgresql
# Ubuntu
sudo systemctl start postgresql
```

Create database and enable PostGIS:
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE gis_db;

# Connect to the database
\c gis_db

# Enable PostGIS extension
CREATE EXTENSION postgis;

# Exit
\q
```

5. **Configure environment variables**

Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

Edit `.env` with your database credentials:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/gis_db
```

6. **Initialize database**
```bash
python -c "from app.db import init_db; init_db()"
```

7. **Run the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Endpoints

### Upload File
```http
POST /features/upload
Content-Type: multipart/form-data

file: <your-geographic-file>
```

### List Features
```http
GET /features?skip=0&limit=100
```

### Get Feature
```http
GET /features/{feature_id}
```

### Update Feature
```http
PUT /features/{feature_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "properties": {"key": "value"},
  "geometry": {
    "type": "Point",
    "coordinates": [lon, lat]
  }
}
```

### Delete Feature
```http
DELETE /features/{feature_id}
```

## Testing with Sample Data

1. **Create a sample GeoJSON file** (`test.geojson`):
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Sample Point",
        "description": "A test location"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      }
    }
  ]
}
```

2. **Upload it**:
```bash
curl -X POST "http://localhost:8000/features/upload" \
  -F "file=@test.geojson"
```

## Troubleshooting

### Database Connection Issues

- Check PostgreSQL service is running: `sudo systemctl status postgresql`
- Verify credentials in `.env`
- Test connection: `psql -U postgres -d gis_db`
- Ensure database exists and PostGIS extension is enabled

### File Parsing Errors

- Ensure file format is supported
- For shapefiles, upload as ZIP containing all required files (.shp, .shx, .dbf)
- Check file encoding (UTF-8 recommended)

### PostGIS Extension

If PostGIS extension fails:
- Verify PostgreSQL version supports PostGIS
- Check user has CREATE EXTENSION permission
- RDS should have PostGIS available in supported PostgreSQL versions

## Security Considerations

For production:
- Use environment variables for sensitive data
- Enable SSL/TLS for database connections
- Implement authentication/authorization
- Use HTTPS with valid certificates
- Restrict security group access
- Regularly update dependencies

## License

MIT

