#!/bin/bash

# Script to set up RDS PostgreSQL with PostGIS
# Make sure AWS CLI is configured with appropriate permissions

set -e

# Configuration
DB_INSTANCE_ID="gis-db-prod"
DB_NAME="gis_db"
DB_USERNAME="postgres"
DB_PASSWORD="${DB_PASSWORD:-}"  # Set via environment variable
DB_INSTANCE_CLASS="${DB_INSTANCE_CLASS:-db.t3.medium}"
STORAGE_SIZE="${STORAGE_SIZE:-20}"
REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up RDS PostgreSQL with PostGIS...${NC}"

# Check if password is set
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Error: DB_PASSWORD environment variable is not set${NC}"
    echo "Usage: DB_PASSWORD=yourpassword ./setup-rds.sh"
    exit 1
fi

# Get VPC and subnet information
echo -e "${YELLOW}Getting VPC information...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION | tr '\t' ',')

echo "VPC ID: $VPC_ID"
echo "Subnets: $SUBNET_IDS"

# Create DB subnet group
SUBNET_GROUP_NAME="gis-db-subnet-group"
echo -e "${YELLOW}Creating DB subnet group...${NC}"

if aws rds describe-db-subnet-groups --db-subnet-group-name $SUBNET_GROUP_NAME --region $REGION &>/dev/null; then
    echo "Subnet group already exists, skipping..."
else
    aws rds create-db-subnet-group \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --db-subnet-group-description "Subnet group for GIS database" \
        --subnet-ids $(echo $SUBNET_IDS | tr ',' ' ') \
        --region $REGION
    echo -e "${GREEN}Subnet group created${NC}"
fi

# Create security group for RDS
SG_NAME="gis-db-sg"
echo -e "${YELLOW}Creating security group...${NC}"

SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $REGION 2>/dev/null || echo "")

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SG_NAME \
        --description "Security group for GIS RDS database" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)
    echo -e "${GREEN}Security group created: $SG_ID${NC}"
else
    echo "Security group already exists: $SG_ID"
fi

# Get EC2 security group to allow access
echo -e "${YELLOW}Getting EC2 security group...${NC}"
EC2_SG=$(aws ec2 describe-instances \
    --filters "Name=ip-address,Values=43.204.148.243" \
    --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
    --output text \
    --region $REGION 2>/dev/null || echo "")

if [ -n "$EC2_SG" ] && [ "$EC2_SG" != "None" ]; then
    echo "EC2 Security Group: $EC2_SG"
    # Allow EC2 to access RDS
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 5432 \
        --source-group $EC2_SG \
        --region $REGION 2>/dev/null || echo "Rule may already exist"
fi

# Check if RDS instance already exists
if aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $REGION &>/dev/null; then
    echo -e "${YELLOW}RDS instance already exists${NC}"
    ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_ID \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text \
        --region $REGION)
    echo -e "${GREEN}RDS Endpoint: $ENDPOINT${NC}"
else
    # Create RDS instance
    echo -e "${YELLOW}Creating RDS PostgreSQL instance...${NC}"
    aws rds create-db-instance \
        --db-instance-identifier $DB_INSTANCE_ID \
        --db-instance-class $DB_INSTANCE_CLASS \
        --engine postgres \
        --engine-version 15.4 \
        --master-username $DB_USERNAME \
        --master-user-password $DB_PASSWORD \
        --allocated-storage $STORAGE_SIZE \
        --storage-type gp3 \
        --vpc-security-group-ids $SG_ID \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --backup-retention-period 7 \
        --storage-encrypted \
        --region $REGION \
        --publicly-accessible \
        --no-multi-az

    echo -e "${GREEN}RDS instance creation initiated${NC}"
    echo -e "${YELLOW}Waiting for RDS instance to be available (this may take 10-15 minutes)...${NC}"
    
    aws rds wait db-instance-available \
        --db-instance-identifier $DB_INSTANCE_ID \
        --region $REGION

    ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_ID \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text \
        --region $REGION)
    
    echo -e "${GREEN}RDS instance is available!${NC}"
    echo -e "${GREEN}RDS Endpoint: $ENDPOINT${NC}"
fi

# Create database if it doesn't exist
echo -e "${YELLOW}Creating database and enabling PostGIS...${NC}"
echo "You'll need to connect manually to enable PostGIS:"
echo ""
echo "psql -h $ENDPOINT -U $DB_USERNAME -d postgres"
echo ""
echo "Then run:"
echo "  CREATE DATABASE $DB_NAME;"
echo "  \\c $DB_NAME"
echo "  CREATE EXTENSION IF NOT EXISTS postgis;"
echo "  CREATE EXTENSION IF NOT EXISTS postgis_topology;"
echo ""

echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Connect to RDS and create database with PostGIS"
echo "2. Update .env file with RDS endpoint"
echo "3. Deploy the application"

