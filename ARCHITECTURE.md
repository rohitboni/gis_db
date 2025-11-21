# Architecture Overview

## System Architecture

```
┌─────────────────┐
│   Client/API     │
│   Consumers      │
└────────┬─────────┘
         │
         │ HTTP/REST
         │
┌────────▼─────────────────────────────────────┐
│         EC2 Instance (43.204.148.243)        │
│  ┌─────────────────────────────────────────┐ │
│  │     FastAPI Application (Docker)        │ │
│  │  - File Upload Handler                  │ │
│  │  - GIS Data CRUD API                    │ │
│  │  - Spatial Query Engine                 │ │
│  └────────┬────────────────┬───────────────┘ │
│           │                │                 │
└───────────┼────────────────┼─────────────────┘
            │                │
    ┌───────▼──────┐  ┌──────▼──────┐
    │   AWS S3     │  │  AWS RDS    │
    │   Bucket     │  │  PostgreSQL │
    │              │  │  + PostGIS  │
    │ - GeoJSON    │  │             │
    │ - Shapefiles │  │ - Spatial   │
    │ - KML        │  │   Data      │
    │ - Other GIS  │  │ - Metadata  │
    │   Files      │  │ - Indexes   │
    └──────────────┘  └─────────────┘
```

## Components

### 1. FastAPI Application
- **Location**: EC2 Instance (Docker container)
- **Port**: 8000
- **Features**:
  - RESTful API for GIS data management
  - File upload endpoints (GeoJSON, Shapefile, KML)
  - CRUD operations for spatial data
  - Spatial query endpoints (intersects, within, contains, distance)
  - Automatic file processing and geometry extraction

### 2. PostgreSQL Database with PostGIS
- **Location**: AWS RDS
- **Purpose**: Store spatial geometries and metadata
- **Extensions**:
  - PostGIS: Spatial data types and functions
  - PostGIS Topology: Topological operations
- **Schema**:
  - `gis_data` table with geometry column
  - Spatial indexes for performance
  - JSONB for flexible property storage

### 3. AWS S3 Bucket
- **Purpose**: Store original GIS files
- **Structure**:
  - `geojson/` - GeoJSON files
  - `shapefile/` - Shapefile components
  - `kml/` - KML files
- **Features**:
  - Versioning enabled
  - Encryption at rest
  - Lifecycle policies for cost optimization

## Data Flow

### Upload Flow
1. Client uploads file via API endpoint
2. FastAPI receives file and processes it:
   - Extracts geometry using GeoPandas/Shapely
   - Calculates bounding box
   - Extracts properties/metadata
3. File is uploaded to S3 (or stored locally)
4. Geometry and metadata are stored in RDS with PostGIS
5. Response returned with file ID and metadata

### Query Flow
1. Client sends spatial query request
2. FastAPI converts GeoJSON to PostGIS geometry
3. PostGIS performs spatial operation (intersects, within, etc.)
4. Results are converted back to GeoJSON
5. Response returned with matching geometries

## Technology Stack

### Backend
- **Python 3.11**
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: ORM for database operations
- **GeoAlchemy2**: PostGIS integration
- **GeoPandas**: Geospatial data processing
- **Shapely**: Geometric operations
- **Boto3**: AWS SDK for S3 operations

### Database
- **PostgreSQL 15+**: Relational database
- **PostGIS 3.3+**: Spatial extension

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **AWS RDS**: Managed PostgreSQL
- **AWS S3**: Object storage
- **AWS EC2**: Compute instance

## API Endpoints

### File Upload
- `POST /api/v1/files/upload/geojson` - Upload GeoJSON
- `POST /api/v1/files/upload/shapefile` - Upload Shapefile
- `POST /api/v1/files/upload/kml` - Upload KML

### CRUD Operations
- `GET /api/v1/gis-data/` - List all GIS data (paginated)
- `GET /api/v1/gis-data/{id}` - Get specific record
- `POST /api/v1/gis-data/` - Create new record
- `PUT /api/v1/gis-data/{id}` - Update record
- `DELETE /api/v1/gis-data/{id}` - Delete record

### Spatial Queries
- `POST /api/v1/spatial/intersects` - Find intersecting geometries
- `POST /api/v1/spatial/within` - Find geometries within boundary
- `POST /api/v1/spatial/contains` - Find geometries containing point/area
- `POST /api/v1/spatial/distance` - Find geometries within distance

## Security Considerations

1. **Network Security**:
   - RDS in private subnet (or with restricted security groups)
   - EC2 security group allows only necessary ports
   - S3 bucket policies restrict access

2. **Authentication** (To be implemented):
   - API key authentication
   - JWT tokens
   - OAuth2

3. **Data Security**:
   - Encrypted database connections
   - S3 encryption at rest
   - Secure credential management (environment variables)

## Scalability

### Horizontal Scaling
- Multiple API instances behind load balancer
- Read replicas for RDS
- S3 automatically scales

### Performance Optimization
- Spatial indexes on geometry column
- Connection pooling
- Caching layer (Redis - optional)
- CDN for static files (optional)

## Monitoring & Logging

### Recommended Tools
- **CloudWatch**: AWS service monitoring
- **Application Logs**: Docker logs, file-based logging
- **Database Monitoring**: RDS performance insights
- **API Monitoring**: Request/response logging

## Backup & Recovery

### Database Backups
- RDS automated backups (7-day retention)
- Manual snapshots for long-term storage
- Point-in-time recovery

### File Backups
- S3 versioning
- Cross-region replication (optional)
- Lifecycle policies for archival

## Cost Optimization

### RDS
- Use appropriate instance size
- Reserved instances for predictable workloads
- Stop/start for development environments

### S3
- Intelligent-Tiering for automatic optimization
- Lifecycle policies to move old data to cheaper storage
- Compression for large files

### EC2
- Use appropriate instance type
- Reserved instances for production
- Spot instances for non-critical workloads

## Future Enhancements

1. **Authentication & Authorization**
2. **Rate Limiting**
3. **Caching Layer** (Redis)
4. **Background Job Processing** (Celery)
5. **WebSocket Support** for real-time updates
6. **GraphQL API** alternative
7. **Vector Tile Generation** (MVT)
8. **Spatial Analysis Tools** (buffers, unions, etc.)
9. **Export Functionality** (download as GeoJSON, Shapefile, etc.)
10. **Multi-tenant Support**

