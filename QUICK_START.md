# Quick Start Guide

## For Your EC2 Instance (43.204.148.243)

### Step 1: Upload Project to EC2

From your local machine:

```bash
# Navigate to project directory
cd /Users/rohitboni/Downloads/All_files/project/1acre/geomapping_full/gis_db

# Upload to EC2
scp -i "oneacre-prod.pem" -r . ubuntu@43.204.148.243:/home/ubuntu/gis_db
```

### Step 2: SSH into EC2

```bash
ssh -i "oneacre-prod.pem" ubuntu@43.204.148.243
```

### Step 3: Set Up AWS Infrastructure

```bash
cd /home/ubuntu/gis_db/aws-setup

# Set your database password
export DB_PASSWORD="YourSecurePassword123!"

# Make scripts executable
chmod +x setup-s3.sh setup-rds.sh

# Create S3 bucket
./setup-s3.sh

# Create RDS instance (takes 10-15 minutes)
./setup-rds.sh
```

**Note the output:**
- S3 Bucket Name
- RDS Endpoint

### Step 4: Configure Environment

```bash
cd /home/ubuntu/gis_db
cp .env.example .env
nano .env
```

Update these values:
```env
DATABASE_URL=postgresql://postgres:YourSecurePassword123!@YOUR_RDS_ENDPOINT:5432/gis_db
RDS_ENDPOINT=your-rds-endpoint.region.rds.amazonaws.com
RDS_PASSWORD=YourSecurePassword123!
S3_BUCKET_NAME=your-bucket-name-from-step-3
AWS_REGION=us-east-1
```

If using IAM user (not IAM role):
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### Step 5: Enable PostGIS on RDS

```bash
# Install PostgreSQL client (if not installed)
sudo apt-get update
sudo apt-get install -y postgresql-client

# Connect to RDS (replace with your endpoint)
psql -h YOUR_RDS_ENDPOINT -U postgres -d postgres

# In psql, run:
CREATE DATABASE gis_db;
\c gis_db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
\q
```

### Step 6: Deploy Service

```bash
cd /home/ubuntu/gis_db
chmod +x deploy.sh
./deploy.sh
```

### Step 7: Verify

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f api

# Test API
curl http://localhost:8000/health

# Access API docs
# Open browser: http://43.204.148.243:8000/docs
```

## API Usage Examples

### Upload GeoJSON

```bash
curl -X POST "http://43.204.148.243:8000/api/v1/files/upload/geojson" \
  -F "file=@data.geojson" \
  -F "name=My GeoJSON" \
  -F "description=Test data"
```

### Get All Data

```bash
curl "http://43.204.148.243:8000/api/v1/gis-data/"
```

### Spatial Query (Intersects)

```bash
curl -X POST "http://43.204.148.243:8000/api/v1/spatial/intersects" \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-122.4, 37.8], [-122.3, 37.8], [-122.3, 37.9], [-122.4, 37.9], [-122.4, 37.8]]]
    },
    "operation": "intersects"
  }'
```

## Troubleshooting

### Can't connect to RDS
- Check security group allows EC2 security group on port 5432
- Verify RDS endpoint is correct
- Check password is correct

### S3 upload fails
- Verify IAM permissions
- Check AWS credentials in .env
- Verify bucket name is correct

### PostGIS errors
- Make sure PostGIS extension is enabled: `CREATE EXTENSION postgis;`
- Check RDS instance has PostGIS support (PostgreSQL 12+)

### Service won't start
- Check logs: `docker-compose logs api`
- Verify .env file is configured correctly
- Check port 8000 is not in use: `sudo lsof -i :8000`

## Next Steps

1. Set up nginx reverse proxy for HTTPS
2. Configure domain name
3. Set up monitoring
4. Implement authentication
5. Set up automated backups

