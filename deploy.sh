#!/bin/bash

# Deployment script for GIS Database Service on EC2
# This script should be run on your EC2 instance

set -e

# Configuration
PROJECT_DIR="/opt/gis_db"
SERVICE_NAME="gis-db-service"
USER="ubuntu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying GIS Database Service...${NC}"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Note: Some commands may require sudo${NC}"
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}Docker installed${NC}"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Installing Docker Compose...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed${NC}"
fi

# Create project directory
echo -e "${YELLOW}Setting up project directory...${NC}"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Copy project files (assuming you're running this from the project directory)
if [ -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}Copying project files...${NC}"
    cp -r . $PROJECT_DIR/
else
    echo -e "${RED}Error: docker-compose.yml not found. Make sure you're in the project directory.${NC}"
    exit 1
fi

cd $PROJECT_DIR

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${RED}Please edit .env file with your configuration before continuing${NC}"
        echo "Press Enter to continue after editing .env..."
        read
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Create uploads directory
mkdir -p uploads/geojson uploads/shapefile uploads/kml

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}Starting services...${NC}"
docker-compose up -d

# Wait for database to be ready
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
sleep 10

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose exec -T api alembic upgrade head || echo "Migrations may have already been run"

# Create systemd service (optional - for auto-start on boot)
echo -e "${YELLOW}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=GIS Database Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Service is running at: http://$(curl -s ifconfig.me):8000"
echo "API Documentation: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop service: docker-compose down"
echo "  Restart service: docker-compose restart"
echo "  System service: sudo systemctl start/stop/restart $SERVICE_NAME"

