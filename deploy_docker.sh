#!/bin/bash

# Contact Volume Forecasting System - Docker Deployment
# Quick deployment using Docker and Docker Compose

set -e

echo "=================================================="
echo "  Contact Forecasting - Docker Deployment"
echo "=================================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    
    # Add current user to docker group (if not root)
    if [ "$EUID" -ne 0 ]; then
        sudo usermod -aG docker $USER
        echo "⚠️  Please log out and log back in for Docker permissions to take effect"
        echo "Then run this script again."
        exit 0
    fi
    
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker is already installed"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    
    # Install Docker Compose
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose is already installed"
fi

echo ""
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting container..."
docker-compose up -d

echo ""
echo "Waiting for application to start..."
sleep 10

echo ""
echo "=================================================="
echo "  Deployment Complete!"
echo "=================================================="
echo ""
echo "✅ Application is now running!"
echo ""
echo "Access your forecasting system at:"
echo "  🌐 Local:    http://localhost:8501"
echo "  🌐 Network:  http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "Useful Commands:"
echo "  View logs:       docker-compose logs -f"
echo "  Stop:            docker-compose down"
echo "  Restart:         docker-compose restart"
echo "  View status:     docker-compose ps"
echo "  Update & rebuild: docker-compose down && docker-compose build --no-cache && docker-compose up -d"
echo ""
echo "For production deployment:"
echo "  1. Setup nginx reverse proxy"
echo "  2. Configure SSL certificate"
echo "  3. Add authentication"
echo ""
echo "See SELF_HOSTING_GUIDE.md for detailed instructions"
echo ""

# Show container status
docker-compose ps

# Optional: Show initial logs
echo ""
echo "Initial logs:"
docker-compose logs --tail=20
