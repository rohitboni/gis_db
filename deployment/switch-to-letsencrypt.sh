#!/bin/bash

# Script to switch from self-signed to Let's Encrypt certificate
# Run this after the rate limit resets (after 2025-11-23 15:13:01 UTC)

set -e

DOMAIN="gis-portal.1acre.in"
PROJECT_DIR="/opt/gis_db/deployment"

echo "🔐 Switching to Let's Encrypt certificate for $DOMAIN..."

cd "$PROJECT_DIR"

# Stop nginx to free ports 80 and 443
echo "📦 Stopping nginx container..."
docker-compose stop nginx
sleep 3

# Create Let's Encrypt certificate
echo "🔐 Creating Let's Encrypt certificate..."
sudo certbot certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --email admin@1acre.in \
  --preferred-challenges http \
  -d "$DOMAIN"

# Verify certificate was created
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✅ Let's Encrypt certificate created successfully"
    
    # Update nginx config to use Let's Encrypt certificate
    # The deployment script will handle this automatically, but we can verify
    echo "📝 Certificate location: /etc/letsencrypt/live/$DOMAIN/"
    echo "   - fullchain.pem"
    echo "   - privkey.pem"
    
    # Restart nginx (it should auto-detect the Let's Encrypt cert)
    echo "🔄 Restarting nginx..."
    docker-compose start nginx
    sleep 3
    
    # Test HTTPS
    echo "🧪 Testing HTTPS..."
    if curl -s https://localhost/health > /dev/null; then
        echo "✅ HTTPS is working with Let's Encrypt certificate!"
        echo "🌐 Access your site at: https://$DOMAIN"
        echo "   (No more browser warnings!)"
    else
        echo "⚠️  HTTPS test failed. Check nginx logs: docker logs deployment-nginx-1"
    fi
else
    echo "❌ Failed to create Let's Encrypt certificate"
    echo "   Check the error message above"
    echo "   Restarting nginx with self-signed certificate..."
    docker-compose start nginx
    exit 1
fi

