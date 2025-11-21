# AWS Infrastructure Setup Guide

This guide will help you set up the AWS infrastructure for your GIS database service.

## Architecture Overview

- **RDS PostgreSQL with PostGIS**: Database for storing spatial data
- **S3 Bucket**: Storage for GeoJSON, Shapefiles, and other GIS files
- **EC2 Instance**: Host for the API service (your existing instance)
- **Security Groups**: Network access control
- **IAM Roles**: Permissions for S3 and RDS access

## Prerequisites

- AWS CLI installed and configured
- AWS account with appropriate permissions
- Your EC2 instance running (43.204.148.243)

## Step 1: Create S3 Bucket

```bash
# Create S3 bucket for GIS files
aws s3 mb s3://gis-data-bucket-$(date +%s) --region us-east-1

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
    --bucket YOUR_BUCKET_NAME \
    --versioning-configuration Status=Enabled
```

## Step 2: Create RDS PostgreSQL Instance with PostGIS

### Option A: Using AWS Console

1. Go to RDS Console → Create Database
2. Choose PostgreSQL (version 15 or later)
3. Select "PostgreSQL" template
4. Configure:
   - DB instance identifier: `gis-db-prod`
   - Master username: `postgres`
   - Master password: (create a strong password)
   - DB instance class: `db.t3.medium` (or larger for production)
   - Storage: 20 GB (adjust as needed)
   - VPC: Same as your EC2 instance
   - Public access: No (use same VPC as EC2)
   - Security group: Create new or use existing
5. After creation, enable PostGIS extension:
   ```sql
   CREATE EXTENSION postgis;
   ```

### Option B: Using AWS CLI

```bash
# Create DB subnet group (if not exists)
aws rds create-db-subnet-group \
    --db-subnet-group-name gis-db-subnet-group \
    --db-subnet-group-description "Subnet group for GIS database" \
    --subnet-ids subnet-xxx subnet-yyy

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier gis-db-prod \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --master-username postgres \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name gis-db-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted
```

## Step 3: Configure Security Groups

### RDS Security Group

Allow inbound PostgreSQL (port 5432) from your EC2 security group:

```bash
# Get your EC2 security group ID
EC2_SG=$(aws ec2 describe-instances \
    --instance-ids $(aws ec2 describe-instances \
        --filters "Name=ip-address,Values=43.204.148.243" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text) \
    --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
    --output text)

# Get RDS security group ID
RDS_SG=$(aws rds describe-db-instances \
    --db-instance-identifier gis-db-prod \
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
    --output text)

# Add rule to allow EC2 to access RDS
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG
```

### EC2 Security Group

Allow inbound HTTP/HTTPS (ports 80/443) for API access:

```bash
# Allow HTTP
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0
```

## Step 4: Create IAM Role for EC2

```bash
# Create IAM policy for S3 access
cat > s3-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_BUCKET_NAME",
                "arn:aws:s3:::YOUR_BUCKET_NAME/*"
            ]
        }
    ]
}
EOF

# Create policy
aws iam create-policy \
    --policy-name GISDataS3Access \
    --policy-document file://s3-policy.json

# Create IAM role for EC2
aws iam create-role \
    --role-name GISDataEC2Role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach policy to role
aws iam attach-role-policy \
    --role-name GISDataEC2Role \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GISDataS3Access

# Create instance profile
aws iam create-instance-profile \
    --instance-profile-name GISDataEC2Profile

# Add role to instance profile
aws iam add-role-to-instance-profile \
    --instance-profile-name GISDataEC2Profile \
    --role-name GISDataEC2Role

# Attach to EC2 instance (if not already attached)
aws ec2 associate-iam-instance-profile \
    --instance-id YOUR_INSTANCE_ID \
    --iam-instance-profile Name=GISDataEC2Profile
```

## Step 5: Get RDS Endpoint

After RDS is created, get the endpoint:

```bash
aws rds describe-db-instances \
    --db-instance-identifier gis-db-prod \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

## Step 6: Enable PostGIS Extension

Connect to your RDS instance and enable PostGIS:

```bash
# Using psql (install on EC2 if needed)
psql -h YOUR_RDS_ENDPOINT -U postgres -d gis_db

# Then run:
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
\q
```

## Step 7: Update Environment Variables

On your EC2 instance, create/update `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/gis_db
RDS_ENDPOINT=YOUR_RDS_ENDPOINT.region.rds.amazonaws.com
RDS_DB_NAME=gis_db
RDS_USERNAME=postgres
RDS_PASSWORD=YOUR_SECURE_PASSWORD

# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=YOUR_BUCKET_NAME

# Application Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
```

## Step 8: Deploy Application

See `../deploy.sh` for deployment instructions.

## Cost Optimization Tips

1. **RDS**: Use `db.t3.medium` for development, scale up for production
2. **S3**: Use S3 Intelligent-Tiering for automatic cost optimization
3. **Backup**: Configure automated backups with appropriate retention
4. **Monitoring**: Set up CloudWatch alarms for cost and performance

## Security Best Practices

1. Use IAM roles instead of access keys when possible
2. Enable encryption at rest for RDS
3. Use VPC endpoints for S3 access (reduces data transfer costs)
4. Regularly rotate database passwords
5. Enable RDS automated backups
6. Use SSL/TLS for database connections

