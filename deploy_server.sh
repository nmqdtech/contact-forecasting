#!/bin/bash

# Contact Volume Forecasting System - Automated Server Deployment
# For Ubuntu/Debian servers

set -e  # Exit on error

echo "=================================================="
echo "  Contact Forecasting System - Server Deployment"
echo "=================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Configuration variables
APP_USER="streamlit"
APP_DIR="/home/$APP_USER/forecasting_app"
SERVICE_NAME="forecasting"
DOMAIN=""

echo "Step 1/8: Updating system..."
apt-get update && apt-get upgrade -y

echo ""
echo "Step 2/8: Installing dependencies..."
apt-get install -y python3 python3-pip python3-venv nginx build-essential python3-dev git curl

echo ""
echo "Step 3/8: Creating application user..."
if id "$APP_USER" &>/dev/null; then
    echo "User $APP_USER already exists, skipping..."
else
    useradd -m -s /bin/bash $APP_USER
    echo "User $APP_USER created"
fi

echo ""
echo "Step 4/8: Setting up application directory..."
sudo -u $APP_USER mkdir -p $APP_DIR
cd $APP_DIR

# Copy files if they exist in current directory
if [ -f "./app.py" ]; then
    echo "Copying application files..."
    cp -r ./* $APP_DIR/
    chown -R $APP_USER:$APP_USER $APP_DIR
else
    echo "Please upload your application files to $APP_DIR"
    echo "Then run: sudo chown -R $APP_USER:$APP_USER $APP_DIR"
fi

echo ""
echo "Step 5/8: Creating Python virtual environment..."
sudo -u $APP_USER python3 -m venv $APP_DIR/venv

echo ""
echo "Step 6/8: Installing Python packages..."
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
if [ -f "$APP_DIR/requirements.txt" ]; then
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt
    echo "Python packages installed"
else
    echo "⚠️  Warning: requirements.txt not found. Please install manually."
fi

echo ""
echo "Step 7/8: Creating systemd service..."
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Contact Volume Forecasting System
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

echo "Service created and started"

echo ""
echo "Step 8/8: Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo "Firewall configured"

echo ""
echo "=================================================="
echo "  Deployment Complete!"
echo "=================================================="
echo ""
echo "Service Status:"
systemctl status $SERVICE_NAME --no-pager
echo ""
echo "Next Steps:"
echo "1. Configure Nginx reverse proxy (see SELF_HOSTING_GUIDE.md)"
echo "2. Setup SSL certificate with: sudo certbot --nginx -d your-domain.com"
echo "3. Test access at: http://YOUR_SERVER_IP:8501"
echo ""
echo "Useful Commands:"
echo "  Check logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart:       sudo systemctl restart $SERVICE_NAME"
echo "  Stop:          sudo systemctl stop $SERVICE_NAME"
echo "  Status:        sudo systemctl status $SERVICE_NAME"
echo ""
echo "For detailed guide, see: SELF_HOSTING_GUIDE.md"
echo ""
