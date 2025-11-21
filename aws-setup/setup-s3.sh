#!/bin/bash

# Script to set up S3 bucket for GIS data storage
# Make sure AWS CLI is configured with appropriate permissions

set -e

# Configuration
BUCKET_NAME="${S3_BUCKET_NAME:-gis-data-bucket-$(date +%s)}"
REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up S3 bucket for GIS data...${NC}"

# Check if bucket already exists
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo -e "${YELLOW}Creating S3 bucket: $BUCKET_NAME${NC}"
    
    if [ "$REGION" == "us-east-1" ]; then
        # us-east-1 doesn't require LocationConstraint
        aws s3 mb "s3://$BUCKET_NAME" --region $REGION
    else
        aws s3 mb "s3://$BUCKET_NAME" --region $REGION --region $REGION
    fi
    
    echo -e "${GREEN}Bucket created successfully${NC}"
else
    echo -e "${YELLOW}Bucket already exists: $BUCKET_NAME${NC}"
fi

# Enable versioning
echo -e "${YELLOW}Enabling versioning...${NC}"
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled \
    --region $REGION

# Enable server-side encryption
echo -e "${YELLOW}Enabling server-side encryption...${NC}"
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }' \
    --region $REGION

# Set up lifecycle policy (optional - move old files to cheaper storage)
echo -e "${YELLOW}Setting up lifecycle policy...${NC}"
cat > /tmp/lifecycle.json <<EOF
{
    "Rules": [{
        "Id": "TransitionToIA",
        "Status": "Enabled",
        "Transitions": [{
            "Days": 30,
            "StorageClass": "STANDARD_IA"
        }],
        "Transitions": [{
            "Days": 90,
            "StorageClass": "GLACIER"
        }]
    }]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET_NAME \
    --lifecycle-configuration file:///tmp/lifecycle.json \
    --region $REGION 2>/dev/null || echo "Lifecycle policy setup skipped (optional)"

# Create folder structure
echo -e "${YELLOW}Creating folder structure...${NC}"
aws s3api put-object --bucket $BUCKET_NAME --key "geojson/" --region $REGION
aws s3api put-object --bucket $BUCKET_NAME --key "shapefile/" --region $REGION
aws s3api put-object --bucket $BUCKET_NAME --key "kml/" --region $REGION

echo -e "${GREEN}S3 setup complete!${NC}"
echo ""
echo "Bucket Name: $BUCKET_NAME"
echo "Region: $REGION"
echo ""
echo "Update your .env file with:"
echo "S3_BUCKET_NAME=$BUCKET_NAME"
echo "AWS_REGION=$REGION"

