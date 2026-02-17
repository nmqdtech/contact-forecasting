# 🖥️ Self-Hosting Guide - Deploy on Your Own Server

Deploy the Contact Volume Forecasting System on **YOUR** infrastructure!

---

## 🎯 Why Self-Host?

**Benefits:**
✅ Complete control over your infrastructure
✅ Data stays on YOUR servers
✅ No third-party dependencies
✅ Custom security policies
✅ Unlimited resources (based on your hardware)
✅ Internal network deployment (no internet exposure if desired)
✅ Integration with existing systems

**Perfect for:**
- Organizations with strict data policies
- Companies with existing infrastructure
- Teams requiring internal-only access
- High-security environments
- Custom compliance requirements

---

## 📋 Server Requirements

### Minimum Specifications
- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 10GB
- **OS:** Ubuntu 20.04+, CentOS 7+, Windows Server 2016+, or Docker

### Recommended Specifications
- **CPU:** 4 cores
- **RAM:** 8GB
- **Storage:** 20GB SSD
- **OS:** Ubuntu 22.04 LTS

### Software Requirements
- Python 3.9+
- pip
- systemd (Linux) or equivalent service manager
- nginx or Apache (for reverse proxy)
- SSL certificate (for HTTPS)

---

## 🚀 Deployment Options

Choose your server type:

1. **Linux VPS/Server** (Ubuntu, CentOS, Debian) - Most common
2. **Windows Server** - For Windows environments
3. **Docker** - Platform-independent, easiest
4. **On-Premise Server** - Your physical hardware
5. **Internal Network** - No internet access required

---

## 🐧 Option 1: Linux Server Deployment (Ubuntu/Debian)

### Step 1: Prepare Your Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.9+ and dependencies
sudo apt install python3 python3-pip python3-venv nginx -y

# Install build tools (required for Prophet)
sudo apt install build-essential python3-dev -y
```

### Step 2: Create Application User

```bash
# Create dedicated user for security
sudo useradd -m -s /bin/bash streamlit
sudo su - streamlit
```

### Step 3: Upload and Setup Application

```bash
# Create application directory
mkdir ~/forecasting_app
cd ~/forecasting_app

# Upload your files here (use SCP, SFTP, or Git)
# For example, using SCP from your local machine:
# scp -r contact_forecasting_webapp/* user@your-server:~/forecasting_app/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Test the Application

```bash
# Test run (still as streamlit user)
streamlit run app.py --server.port 8501

# Open browser to http://YOUR_SERVER_IP:8501
# If it works, press Ctrl+C to stop
```

### Step 5: Create Systemd Service

Exit back to your admin user:
```bash
exit  # Exit streamlit user
```

Create service file:
```bash
sudo nano /etc/systemd/system/forecasting.service
```

Add this content:
```ini
[Unit]
Description=Contact Volume Forecasting System
After=network.target

[Service]
Type=simple
User=streamlit
WorkingDirectory=/home/streamlit/forecasting_app
Environment="PATH=/home/streamlit/forecasting_app/venv/bin"
ExecStart=/home/streamlit/forecasting_app/venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit (Ctrl+X, Y, Enter)

### Step 6: Start and Enable Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start forecasting

# Enable on boot
sudo systemctl enable forecasting

# Check status
sudo systemctl status forecasting
```

### Step 7: Setup Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/forecasting
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain or IP

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/forecasting /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### Step 8: Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow ssh  # Don't lock yourself out!
sudo ufw enable
```

### Step 9: Setup SSL/HTTPS (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (make sure DNS points to your server first)
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

### Step 10: Access Your Application

Visit: `https://your-domain.com` (or `http://your-server-ip`)

---

## 🪟 Option 2: Windows Server Deployment

### Step 1: Install Python

1. Download Python 3.9+ from https://python.org
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Complete installation

### Step 2: Setup Application

```powershell
# Open PowerShell as Administrator

# Create application directory
mkdir C:\forecasting_app
cd C:\forecasting_app

# Copy your files here

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Test Application

```powershell
streamlit run app.py --server.port 8501

# Access at http://localhost:8501
# If works, press Ctrl+C
```

### Step 4: Create Windows Service

Install NSSM (Non-Sucking Service Manager):
1. Download from https://nssm.cc/download
2. Extract to `C:\nssm`

Create service:
```powershell
# Open PowerShell as Administrator
cd C:\nssm\win64

.\nssm install ForecatingApp "C:\forecasting_app\venv\Scripts\streamlit.exe" "run app.py --server.port 8501"

.\nssm set ForecastingApp AppDirectory "C:\forecasting_app"
.\nssm set ForecastingApp DisplayName "Contact Forecasting System"
.\nssm set ForecastingApp Description "AI-powered contact volume forecasting"
.\nssm set ForecastingApp Start SERVICE_AUTO_START

# Start the service
.\nssm start ForecastingApp
```

### Step 5: Configure Windows Firewall

```powershell
# Allow port 8501
New-NetFirewallRule -DisplayName "Forecasting App" -Direction Inbound -LocalPort 8501 -Protocol TCP -Action Allow
```

### Step 6: Setup IIS Reverse Proxy (Optional)

1. Install IIS with Application Request Routing
2. Configure URL Rewrite to proxy to localhost:8501
3. Add SSL certificate

Access: `http://your-server-ip:8501`

---

## 🐳 Option 3: Docker Deployment (Easiest & Platform-Independent)

### Step 1: Create Dockerfile

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the application
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  forecasting:
    build: .
    container_name: contact-forecasting
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data  # Persistent data storage
    restart: unless-stopped
    environment:
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_SERVER_PORT=8501
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Step 3: Deploy with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Update application
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 4: Setup Nginx Reverse Proxy (on host)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Access: `http://your-domain.com`

---

## 🔒 Security Hardening

### 1. Add Authentication

Create `auth.py`:
```python
import streamlit as st
import hashlib

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password():
    """Returns True if user entered correct password."""
    
    # Store hashed passwords (change these!)
    passwords = {
        "admin": make_hash("your-secure-password-here"),
        "user": make_hash("another-password")
    }
    
    def password_entered():
        username = st.session_state["username"]
        password = st.session_state["password"]
        
        if username in passwords and make_hash(password) == passwords[username]:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = username
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Username or password incorrect")
        return False
    return True
```

Add to `app.py` (at the top of main()):
```python
from auth import check_password

def main():
    if not check_password():
        st.stop()
    
    # Rest of your app...
```

### 2. Configure Firewall

```bash
# Linux (UFW)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Windows (PowerShell)
Set-NetFirewallProfile -DefaultInboundAction Block
Set-NetFirewallProfile -DefaultOutboundAction Allow
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
```

### 3. Restrict by IP (Optional)

In nginx config:
```nginx
location / {
    allow 192.168.1.0/24;  # Your office network
    allow 10.0.0.0/8;      # VPN network
    deny all;
    
    proxy_pass http://127.0.0.1:8501;
    # ... rest of config
}
```

### 4. Enable HTTPS Only

In nginx:
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Strong SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        # ... rest of config
    }
}
```

---

## 📊 Resource Management

### Monitor Resource Usage

```bash
# Linux
htop  # Interactive process viewer
docker stats  # If using Docker

# Check application logs
sudo journalctl -u forecasting -f  # Systemd
docker logs -f contact-forecasting  # Docker

# Windows
Task Manager → Performance tab
```

### Optimize Performance

**Increase Workers:**
```bash
# In systemd service file
ExecStart=/path/to/streamlit run app.py --server.port 8501 --server.maxUploadSize 200
```

**Limit Resources (Docker):**
```yaml
services:
  forecasting:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## 🔄 Backup Strategy

### Automated Backups

Create backup script `/home/streamlit/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/backups/forecasting"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application files
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /home/streamlit/forecasting_app

# Backup data (if you have persistent storage)
tar -czf $BACKUP_DIR/data_$DATE.tar.gz /home/streamlit/forecasting_app/data

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

Schedule with cron:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/streamlit/backup.sh
```

---

## 🌐 Domain Setup

### 1. Configure DNS

Point your domain to your server:
```
A Record: your-domain.com → YOUR_SERVER_IP
```

### 2. Update Nginx Configuration

```nginx
server_name your-domain.com www.your-domain.com;
```

### 3. Get SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

## 📱 Internal Network Deployment

For companies wanting **internal-only** access:

### Setup (No Internet Required)

1. Deploy on internal server (192.168.x.x or 10.x.x.x)
2. Don't expose to internet (no port forwarding)
3. Access via internal IP: `http://192.168.1.100:8501`
4. Or setup internal DNS: `http://forecasting.company.local`

### Advantages
- ✅ Complete isolation from internet
- ✅ No external attack surface
- ✅ Data never leaves network
- ✅ No SSL required (if fully internal)
- ✅ Company firewall protection

---

## 🔧 Maintenance

### Update Application

```bash
# Linux (systemd)
sudo systemctl stop forecasting
cd /home/streamlit/forecasting_app
git pull  # If using Git
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl start forecasting

# Docker
docker-compose pull
docker-compose up -d
```

### Monitor Logs

```bash
# Systemd
sudo journalctl -u forecasting -f

# Docker
docker logs -f contact-forecasting

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Service

```bash
# Linux
sudo systemctl restart forecasting

# Docker
docker-compose restart

# Windows
.\nssm restart ForecastingApp
```

---

## ⚡ Quick Start Summary

### Fastest Self-Hosting (Docker)

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 2. Copy your files to server
scp -r contact_forecasting_webapp/* user@server:/opt/forecasting/

# 3. Deploy
cd /opt/forecasting
docker-compose up -d

# 4. Access
# http://your-server-ip:8501
```

**Total time:** 15 minutes  
**Platform:** Any Linux server  
**Complexity:** Low

---

## 🆘 Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u forecasting -n 50

# Common issues:
# - Port already in use: Change port in service file
# - Missing dependencies: Reinstall requirements.txt
# - Permission issues: Check file ownership
```

### Can't Access from Other Machines

```bash
# Check if service is running
sudo systemctl status forecasting

# Check if port is open
sudo netstat -tlnp | grep 8501

# Check firewall
sudo ufw status
```

### High Memory Usage

```bash
# Reduce forecast horizon in app
# Limit upload file size
# Add resource limits in Docker/systemd
```

---

## 💰 Cost Comparison

### Self-Hosting Costs

**Small VPS (DigitalOcean, Linode, Vultr):**
- 2 CPU, 4GB RAM: $12-20/month
- Better performance than free cloud tiers
- Full control

**On-Premise Server:**
- Initial hardware: $500-2000
- Electricity: ~$5-10/month
- Maintenance: Your time
- **Best for:** Long-term, existing infrastructure

**Cloud Platforms (for comparison):**
- Streamlit Cloud: Free or $20-200/month
- Railway: $5-50/month
- Heroku: $7-500/month

---

## ✅ Self-Hosting Checklist

Before going live:
- [ ] Server meets minimum requirements
- [ ] Application tested locally
- [ ] Systemd/service configured
- [ ] Reverse proxy setup (nginx/Apache)
- [ ] Firewall configured
- [ ] SSL certificate installed
- [ ] Backups automated
- [ ] Monitoring setup
- [ ] Authentication enabled
- [ ] DNS configured (if using domain)
- [ ] Team trained on access

---

## 🎉 You're Ready to Self-Host!

Choose your deployment method:
- **Quick & Easy:** Docker (recommended)
- **Traditional:** Systemd on Linux
- **Windows:** NSSM service
- **Enterprise:** Full nginx + SSL + monitoring

**Benefits of self-hosting:**
- Complete control
- Data sovereignty
- Custom integration
- No vendor lock-in

Deploy your forecasting system on YOUR infrastructure today! 🚀
