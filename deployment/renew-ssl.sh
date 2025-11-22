#!/bin/bash

# Script to renew expired SSL certificate for gis-portal.1acre.in
# Run this script on the server via SSH

set -e

DOMAIN="gis-portal.1acre.in"
PROJECT_DIR="/opt/gis_db"
DEPLOYMENT_DIR="$PROJECT_DIR/deployment"

echo "🔄 Renewing SSL certificate for $DOMAIN..."
echo ""

# Check if we're on the server
if [ ! -d "$DEPLOYMENT_DIR" ]; then
    echo "❌ Error: This script must be run on the server where the application is deployed"
    echo "   Expected directory: $DEPLOYMENT_DIR"
    exit 1
fi

cd "$DEPLOYMENT_DIR"

# Step 1: Stop nginx container to free ports 80 and 443
echo "📦 Step 1: Stopping nginx container..."
docker-compose stop nginx || echo "⚠️  nginx container might not be running"
sleep 3

# Step 2: Check if certbot is available
echo "🔍 Step 2: Checking certbot installation..."
if ! command -v certbot &> /dev/null; then
    echo "❌ Error: certbot is not installed"
    echo "   Install it with: sudo apt-get update && sudo apt-get install -y certbot"
    exit 1
fi

# Step 3: Renew the certificate using standalone mode
echo "🔐 Step 3: Renewing SSL certificate using standalone mode..."
echo "   This will use ports 80 and 443, so nginx must be stopped"
echo ""

sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@1acre.in \
    --preferred-challenges http \
    -d "$DOMAIN" \
    --force-renewal \
    --expand

# Check if renewal was successful
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo ""
    echo "✅ Certificate renewal successful!"
    echo ""
    
    # Display certificate info
    echo "📋 Certificate information:"
    sudo openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -noout -subject -dates
    echo ""
    
    # Step 4: Restart nginx container
    echo "🔄 Step 4: Restarting nginx container..."
    docker-compose start nginx || docker-compose up -d nginx
    
    echo ""
    echo "✅ SSL certificate renewal complete!"
    echo "   Domain: $DOMAIN"
    echo "   Certificate path: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo ""
    echo "🌐 Test your site at: https://$DOMAIN"
else
    echo ""
    echo "❌ Error: Certificate renewal failed"
    echo "   Please check the error messages above"
    exit 1
fi

