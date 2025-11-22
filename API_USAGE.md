# API Usage Guide

## Hierarchical Data Structure

Your GIS data follows a hierarchical structure: **State → District → Taluk → Village**

Files are organized by district (e.g., `Bengaluru_Rural.geojson`), and each feature contains properties with hierarchical information:
- `District_Name`, `Taluk_Name`, `Village_Name`, `Survey_Number`
- The system supports various field name formats (e.g., `District_Name`, `district`, `DISTRICT`)

## API Endpoints

### 1. Upload Geographic File

**POST** `/features/upload`

Upload a file and automatically parse all features. Supports multiple formats:
- GeoJSON (`.geojson`, `.json`)
- KML/KMZ (`.kml`, `.kmz`)
- Shapefile (`.shp` in ZIP with `.shx`, `.dbf`)
- GPX (`.gpx`)
- CSV (with lat/lon or WKT)

**Example:**
```bash
curl -X POST "http://localhost:8000/features/upload" \
  -F "file=@Bengaluru_Rural.geojson"
```

### 2. List Features with Filtering

**GET** `/features`

List all features with optional hierarchical filtering and pagination.

**Query Parameters:**
- `skip` (int, default: 0) - Number of records to skip
- `limit` (int, default: 100) - Maximum number of records to return
- `state` (string, optional) - Filter by state name (partial match)
- `district` (string, optional) - Filter by district name (partial match)
- `taluk` (string, optional) - Filter by taluk name (partial match)
- `village` (string, optional) - Filter by village name (partial match)

**Examples:**
```bash
# Get all features
curl "http://localhost:8000/features"

# Filter by district
curl "http://localhost:8000/features?district=Bengaluru%20Rural"

# Filter by district and taluk
curl "http://localhost:8000/features?district=Bengaluru%20Rural&taluk=Nelamangala"

# Filter by village with pagination
curl "http://localhost:8000/features?village=Devarahosahalli&skip=0&limit=50"
```

**Response:**
```json
[
  {
    "id": "uuid-here",
    "name": "78",
    "properties": {
      "Survey_Number": "78",
      "Village_Name": "Devarahosahalli",
      "Taluk_Name": "Nelamangala",
      "District_Name": "Bengaluru (Rural)"
    },
    "geometry": {
      "type": "MultiPolygon",
      "coordinates": [...]
    },
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

### 3. Get Unique States

**GET** `/features/states`

Get list of all unique states from all features.

**Example:**
```bash
curl "http://localhost:8000/features/states"
```

**Response:**
```json
["Karnataka", "Tamil Nadu", ...]
```

### 4. Get Unique Districts

**GET** `/features/districts`

Get list of all unique districts, optionally filtered by state.

**Query Parameters:**
- `state` (string, optional) - Filter districts by state

**Examples:**
```bash
# Get all districts
curl "http://localhost:8000/features/districts"

# Get districts for a specific state
curl "http://localhost:8000/features/districts?state=Karnataka"
```

**Response:**
```json
["Bengaluru (Rural)", "Bengaluru Urban", "Mysuru", ...]
```

### 5. Get Unique Taluks

**GET** `/features/taluks`

Get list of all unique taluks, optionally filtered by district.

**Query Parameters:**
- `district` (string, optional) - Filter taluks by district

**Examples:**
```bash
# Get all taluks
curl "http://localhost:8000/features/taluks"

# Get taluks for a specific district
curl "http://localhost:8000/features/taluks?district=Bengaluru%20Rural"
```

**Response:**
```json
["Nelamangala", "Devanahalli", "Doddaballapura", ...]
```

### 6. Get Unique Villages

**GET** `/features/villages`

Get list of all unique villages, optionally filtered by district and/or taluk.

**Query Parameters:**
- `district` (string, optional) - Filter villages by district
- `taluk` (string, optional) - Filter villages by taluk

**Examples:**
```bash
# Get all villages
curl "http://localhost:8000/features/villages"

# Get villages for a district
curl "http://localhost:8000/features/villages?district=Bengaluru%20Rural"

# Get villages for a specific taluk
curl "http://localhost:8000/features/villages?taluk=Nelamangala"

# Get villages for district and taluk
curl "http://localhost:8000/features/villages?district=Bengaluru%20Rural&taluk=Nelamangala"
```

**Response:**
```json
["Devarahosahalli", "Village2", "Village3", ...]
```

### 7. Get Single Feature

**GET** `/features/{feature_id}`

Get a single feature by its UUID.

**Example:**
```bash
curl "http://localhost:8000/features/123e4567-e89b-12d3-a456-426614174000"
```

### 8. Update Feature

**PUT** `/features/{feature_id}`

Update a feature's name, properties, or geometry.

**Example:**
```bash
curl -X PUT "http://localhost:8000/features/123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "properties": {"key": "value"},
    "geometry": {
      "type": "Point",
      "coordinates": [77.5946, 12.9716]
    }
  }'
```

### 9. Delete Feature

**DELETE** `/features/{feature_id}`

Delete a feature by its UUID.

**Example:**
```bash
curl -X DELETE "http://localhost:8000/features/123e4567-e89b-12d3-a456-426614174000"
```

## Field Name Variants Supported

The API automatically handles different field name formats in the properties JSONB column:

**District fields:**
- `District_Name`, `district`, `DISTRICT`, `District`, `district_name`

**Taluk fields:**
- `Taluk_Name`, `taluk`, `TALUK`, `Taluk`, `Block_Name`, `block`, `taluk_name`

**Village fields:**
- `Village_Name`, `village`, `VILLAGE`, `Village`, `village_name`

**State fields:**
- `State_Name`, `state`, `STATE`, `State`, `state_name`

## Workflow Example

1. **Upload district files:**
   ```bash
   curl -X POST "http://localhost:8000/features/upload" -F "file=@Bengaluru_Rural.geojson"
   curl -X POST "http://localhost:8000/features/upload" -F "file=@Mysuru.geojson"
   ```

2. **Browse hierarchical structure:**
   ```bash
   # Get all states
   curl "http://localhost:8000/features/states"
   
   # Get districts in Karnataka
   curl "http://localhost:8000/features/districts?state=Karnataka"
   
   # Get taluks in Bengaluru Rural
   curl "http://localhost:8000/features/taluks?district=Bengaluru%20Rural"
   
   # Get villages in Nelamangala taluk
   curl "http://localhost:8000/features/villages?taluk=Nelamangala"
   ```

3. **Query features:**
   ```bash
   # Get all features in Bengaluru Rural district
   curl "http://localhost:8000/features?district=Bengaluru%20Rural"
   
   # Get features in a specific village
   curl "http://localhost:8000/features?village=Devarahosahalli"
   ```

## File Download with Format Conversion

### Download Single File with Format Conversion

**GET** `/files/{file_id}/download`

Download a single file in any supported format, regardless of the original upload format. All data is preserved during conversion - no data loss.

**Query Parameters:**
- `format` (string, default: "geojson") - Output format: `geojson`, `shapefile`, `kml`, `kmz`, `gpx`, `csv`

**Supported Output Formats:**
- `geojson` - GeoJSON format (default)
- `shapefile` - ESRI Shapefile (returns ZIP with .shp, .shx, .dbf, .prj)
- `kml` - Keyhole Markup Language
- `kmz` - Compressed KML (ZIP)
- `gpx` - GPS Exchange Format
- `csv` - CSV with WKT geometry column

**Examples:**
```bash
# Download file as GeoJSON (default)
curl -O "http://localhost:8000/files/{file_id}/download"

# Download file as Shapefile (ZIP)
curl -O "http://localhost:8000/files/{file_id}/download?format=shapefile"

# Download file as KML
curl -O "http://localhost:8000/files/{file_id}/download?format=kml"

# Example: Upload .shp, download as .geojson
# 1. Upload shapefile
curl -X POST "http://localhost:8000/files/upload" -F "file=@maharashtra_districts.shp.zip"
# Response: {"id": "abc-123-def-456", ...}

# 2. Download as GeoJSON
curl -O "http://localhost:8000/files/abc-123-def-456/download?format=geojson"
```

### Batch Download Multiple Files

**GET** `/files/download/batch`

Download multiple files in batch with format conversion. Perfect for downloading all files from a state/district in one format.

**Query Parameters:**
- `state` (string, optional) - Filter files by state (e.g., "Maharashtra")
- `district` (string, optional) - Filter files by district
- `file_ids` (string, optional) - Comma-separated list of specific file IDs to download
- `format` (string, default: "geojson") - Output format for all files
- `merge` (boolean, default: true) - If true, merge all files into one. If false, return ZIP with separate files.

**Examples:**
```bash
# Download all files from Maharashtra as GeoJSON (merged into one file)
curl -O "http://localhost:8000/files/download/batch?state=Maharashtra&format=geojson&merge=true"

# Download all .shp files from Maharashtra as .geojson (merged)
curl -O "http://localhost:8000/files/download/batch?state=Maharashtra&format=geojson"

# Download all files from Maharashtra as separate files in a ZIP
curl -O "http://localhost:8000/files/download/batch?state=Maharashtra&format=geojson&merge=false"

# Download specific files by ID
curl -O "http://localhost:8000/files/download/batch?file_ids=id1,id2,id3&format=shapefile"

# Download all files from a district as KML
curl -O "http://localhost:8000/files/download/batch?state=Maharashtra&district=Pune&format=kml"
```

**Use Case Example:**
```bash
# Scenario: User uploaded 10 .shp files from Maharashtra
# They want to download all of them as .geojson files

# Option 1: Download as one merged GeoJSON file
curl -O "http://localhost:8000/files/download/batch?state=Maharashtra&format=geojson&merge=true"
# Returns: Maharashtra_merged.geojson (all 10 files combined)

# Option 2: Download as separate files in a ZIP
curl -O "http://localhost:8000/files/download/batch?state=Maharashtra&format=geojson&merge=false"
# Returns: Maharashtra_10_files.zip containing 10 separate .geojson files
```

**Important Notes:**
- ✅ **No Data Loss**: All geometry and properties are preserved during format conversion
- ✅ **Flexible Formats**: Upload in any format, download in any format
- ✅ **Batch Processing**: Download multiple files at once with filtering
- ✅ **Merged or Separate**: Choose to merge files or keep them separate

## Interactive Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI, where you can test all endpoints directly.

