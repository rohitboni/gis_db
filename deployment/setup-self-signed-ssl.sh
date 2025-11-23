#!/bin/bash

# Script to create a self-signed SSL certificate for temporary HTTPS access
# This is for testing only - browsers will show a security warning

set -e

DOMAIN="gis-portal.1acre.in"
CERT_DIR="/opt/gis_db/deployment/ssl"
NGINX_CONF="/opt/gis_db/deployment/nginx/conf.d/default.conf"

echo "🔐 Setting up self-signed SSL certificate for $DOMAIN..."

# Create SSL directory
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -subj "/C=IN/ST=State/L=City/O=Organization/CN=$DOMAIN" \
  -addext "subjectAltName=DNS:$DOMAIN,DNS:*.$DOMAIN"

echo "✅ Self-signed certificate created"

# Update nginx configuration to use self-signed certificate
cat > "$NGINX_CONF" << 'NGINX_EOF'
# Temporary self-signed SSL configuration
# Browsers will show a security warning - this is expected for self-signed certificates

server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;

    # Self-signed SSL certificate
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Client max body size for large GIS file uploads
    client_max_body_size 100M;

    # Main proxy settings for FastAPI
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for FastAPI docs)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts - INCREASED for large GIS operations
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffer settings for large responses
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # FastAPI interactive API documentation (Swagger UI)
    location /docs {
        proxy_pass http://web:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for interactive docs
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # FastAPI ReDoc documentation
    location /redoc {
        proxy_pass http://web:8000/redoc;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # OpenAPI JSON schema
    location /openapi.json {
        proxy_pass http://web:8000/openapi.json;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Allow caching of OpenAPI schema
        expires 1h;
        add_header Cache-Control "public";
    }

    # Health check endpoint
    location /health {
        proxy_pass http://web:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        access_log off;
        
        # Fast health check response
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }

    # API endpoints
    location /files {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Longer timeouts for API calls (GIS processing can be slow)
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Buffer settings for large file uploads/downloads
        proxy_buffering off;
        proxy_request_buffering off;
        
        # No caching for API responses
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    location /features {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Longer timeouts for API calls (GIS processing can be slow)
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Buffer settings for large file uploads/downloads
        proxy_buffering off;
        proxy_request_buffering off;
        
        # No caching for API responses
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
}
NGINX_EOF

echo "✅ Nginx configuration updated"

# Update docker-compose to mount SSL directory
echo ""
echo "⚠️  IMPORTANT: You need to update docker-compose.yml to mount the SSL directory"
echo "   Add this volume mount to the nginx service:"
echo "   - ./ssl:/etc/nginx/ssl:ro"
echo ""
echo "📋 Next steps:"
echo "   1. Update docker-compose.yml to mount ./ssl:/etc/nginx/ssl:ro"
echo "   2. Run: docker-compose restart nginx"
echo "   3. Access: https://gis-portal.1acre.in/docs"
echo "   4. Accept the security warning in your browser (it's a self-signed cert)"

