# Setup Guide for GIS Database Service

This guide will walk you through setting up the GIS Database Service on your AWS EC2 instance.

## Prerequisites

- AWS Account with EC2, RDS, and S3 access
- EC2 instance running (43.204.148.243)
- SSH access to EC2 instance
- AWS CLI configured (optional, for automated setup)

## Quick Start

### Option 1: Automated Setup (Recommended)

1. **Clone/Upload the project to your EC2 instance:**

```bash
# On your local machine, upload the project
scp -i "oneacre-prod.pem" -r gis_db ubuntu@43.204.148.243:/home/ubuntu/
```

2. **SSH into your EC2 instance:**

```bash
ssh -i "oneacre-prod.pem" ubuntu@43.204.148.243
```

3. **Set up AWS infrastructure:**

```bash
cd gis_db/aws-setup

# Set your database password
export DB_PASSWORD="your_secure_password_here"

# Set up S3 bucket
chmod +x setup-s3.sh
./setup-s3.sh

# Set up RDS (this takes 10-15 minutes)
chmod +x setup-rds.sh
./setup-rds.sh
```

4. **Configure environment variables:**

```bash
cd /home/ubuntu/gis_db
cp .env.example .env
nano .env  # Edit with your RDS endpoint and S3 bucket name
```

5. **Deploy the service:**

```bash
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual Setup

#### Step 1: Set Up AWS RDS

1. Go to AWS Console → RDS → Create Database
2. Choose PostgreSQL 15+
3. Configure:
   - Instance: `db.t3.medium` or larger
   - Storage: 20 GB minimum
   - VPC: Same as your EC2 instance
   - Security Group: Allow port 5432 from EC2 security group
4. After creation, connect and enable PostGIS:

```sql
CREATE DATABASE gis_db;
\c gis_db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

#### Step 2: Set Up S3 Bucket

1. Go to AWS Console → S3 → Create Bucket
2. Name: `gis-data-bucket-<unique-id>`
3. Enable versioning
4. Enable encryption
5. Note the bucket name for `.env` file

#### Step 3: Configure IAM

1. Create IAM policy for S3 access (see `aws-setup/README.md`)
2. Attach policy to EC2 instance role or create IAM user with access keys

#### Step 4: Deploy Application

1. **Upload project to EC2:**

```bash
# From your local machine
scp -i "oneacre-prod.pem" -r gis_db ubuntu@43.204.148.243:/home/ubuntu/
```

2. **SSH into EC2:**

```bash
ssh -i "oneacre-prod.pem" ubuntu@43.204.148.243
```

3. **Install Docker (if not installed):**

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
```

4. **Install Docker Compose:**

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

5. **Configure environment:**

```bash
cd /home/ubuntu/gis_db
cp .env.example .env
nano .env
```

Update these values in `.env`:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/gis_db
RDS_ENDPOINT=your-rds-endpoint.region.rds.amazonaws.com
RDS_PASSWORD=your_secure_password
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your_access_key  # If using IAM user
AWS_SECRET_ACCESS_KEY=your_secret_key  # If using IAM user
AWS_REGION=us-east-1
```

6. **Deploy:**

```bash
docker-compose up -d
```

7. **Run migrations:**

```bash
docker-compose exec api alembic upgrade head
```

## Verify Installation

1. **Check service status:**

```bash
docker-compose ps
```

2. **View logs:**

```bash
docker-compose logs -f api
```

3. **Test API:**

```bash
curl http://localhost:8000/health
```

4. **Access API documentation:**

Open in browser: `http://43.204.148.243:8000/docs`

## Using the API

### Upload a GeoJSON file:

```bash
curl -X POST "http://43.204.148.243:8000/api/v1/files/upload/geojson" \
  -F "file=@your-file.geojson" \
  -F "name=My GeoJSON Data" \
  -F "description=Description of the data"
```

### Get all GIS data:

```bash
curl "http://43.204.148.243:8000/api/v1/gis-data/"
```

### Perform spatial query:

```bash
curl -X POST "http://43.204.148.243:8000/api/v1/spatial/intersects" \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
    },
    "operation": "intersects"
  }'
```

## Troubleshooting

### Database Connection Issues

1. Check RDS security group allows EC2 security group
2. Verify DATABASE_URL in `.env` is correct
3. Test connection: `psql -h YOUR_RDS_ENDPOINT -U postgres -d gis_db`

### S3 Access Issues

1. Verify IAM permissions
2. Check AWS credentials in `.env`
3. Test S3 access: `aws s3 ls s3://your-bucket-name`

### PostGIS Extension Not Found

1. Connect to RDS and verify PostGIS is installed:
```sql
SELECT PostGIS_version();
```

2. If not installed, run:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Port Already in Use

If port 8000 is already in use, change it in `docker-compose.yml` and `.env`:

```yaml
ports:
  - "8001:8000"  # Change 8001 to any available port
```

## Maintenance

### Update the service:

```bash
cd /home/ubuntu/gis_db
git pull  # If using git
docker-compose build
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Backup database:

```bash
# Using pg_dump
pg_dump -h YOUR_RDS_ENDPOINT -U postgres gis_db > backup.sql
```

### View logs:

```bash
docker-compose logs -f api
docker-compose logs -f db
```

### Restart service:

```bash
docker-compose restart
```

## Security Considerations

1. **Change default passwords** in production
2. **Use IAM roles** instead of access keys when possible
3. **Enable SSL/TLS** for database connections
4. **Restrict API access** using security groups or a reverse proxy (nginx)
5. **Enable HTTPS** using a load balancer or nginx with Let's Encrypt
6. **Regular backups** of RDS database
7. **Monitor costs** using AWS Cost Explorer

## Next Steps

- Set up nginx reverse proxy for HTTPS
- Configure domain name and SSL certificate
- Set up monitoring and alerting (CloudWatch)
- Implement authentication/authorization
- Add rate limiting
- Set up automated backups

