# GIS Database Service

A production-ready GIS data management service with support for GeoJSON, Shapefiles, and other geographical formats.

## Architecture

- **Database**: PostgreSQL with PostGIS extension
- **API**: FastAPI (Python)
- **File Storage**: AWS S3
- **Deployment**: Docker on EC2
- **Database Options**: 
  - AWS RDS PostgreSQL with PostGIS (Recommended for production)
  - PostgreSQL on EC2 instance

## Features

- ✅ Store and manage GeoJSON files
- ✅ Store and manage Shapefiles
- ✅ CRUD operations for spatial data
- ✅ Spatial queries (intersection, distance, etc.)
- ✅ File upload and management
- ✅ RESTful API
- ✅ AWS S3 integration for file storage
- ✅ Docker containerization

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- AWS Account with EC2, RDS, and S3 access
- PostgreSQL with PostGIS extension

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the service:
```bash
uvicorn app.main:app --reload
```

### Docker Deployment

1. Build and run:
```bash
docker-compose up -d
```

2. Run migrations:
```bash
docker-compose exec api alembic upgrade head
```

## AWS Setup

See `aws-setup/` directory for detailed AWS infrastructure setup instructions.

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

