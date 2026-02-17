# ⚡ Self-Hosting Quick Reference

Deploy on YOUR server in minutes!

---

## 🚀 Three Deployment Methods

### 1. Docker (Fastest - 5 minutes)

```bash
# One command deployment
./deploy_docker.sh

# Access at http://your-server-ip:8501
```

**Requirements:** Linux server with internet  
**Time:** 5 minutes  
**Difficulty:** Easy

---

### 2. Automated Script (10 minutes)

```bash
# Upload files to server, then:
sudo ./deploy_server.sh

# Configure nginx and SSL
sudo nano /etc/nginx/sites-available/forecasting
sudo certbot --nginx -d your-domain.com

# Access at https://your-domain.com
```

**Requirements:** Ubuntu/Debian server  
**Time:** 10 minutes  
**Difficulty:** Easy

---

### 3. Manual Setup (20 minutes)

**See SELF_HOSTING_GUIDE.md for step-by-step**

**Best for:** Custom configurations, Windows Server, etc.

---

## 📋 Quick Commands by Platform

### Docker
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Restart
docker-compose restart

# Update
docker-compose down && docker-compose build --no-cache && docker-compose up -d
```

### Systemd (Linux)
```bash
# Start
sudo systemctl start forecasting

# Stop
sudo systemctl stop forecasting

# Restart
sudo systemctl restart forecasting

# Logs
sudo journalctl -u forecasting -f

# Status
sudo systemctl status forecasting
```

### Windows Service (NSSM)
```powershell
# Start
.\nssm start ForecastingApp

# Stop
.\nssm stop ForecastingApp

# Restart
.\nssm restart ForecastingApp

# Status
.\nssm status ForecastingApp
```

---

## 🔒 Quick Security Setup

### Add Password Protection

1. Edit `app.py`, add at top of `main()`:
```python
from auth import check_password

def main():
    if not check_password():
        st.stop()
```

2. Create `auth.py` (see SELF_HOSTING_GUIDE.md for code)

3. Restart service

### Firewall Setup

```bash
# Linux (UFW)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Check status
sudo ufw status
```

### SSL Certificate (Free)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is automatic!
```

---

## 🌐 Access URLs

After deployment:

**Local access:**
```
http://localhost:8501
```

**Network access:**
```
http://YOUR_SERVER_IP:8501
```

**Domain (with nginx):**
```
https://your-domain.com
```

**Internal only:**
```
http://192.168.1.100:8501
```

---

## 📊 Resource Requirements

### Minimum
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB
- OS: Ubuntu 20.04+

### Recommended
- CPU: 4 cores
- RAM: 8GB
- Storage: 20GB SSD
- OS: Ubuntu 22.04 LTS

### Docker
- Same as above
- Docker installed
- docker-compose installed

---

## 🆘 Quick Troubleshooting

### Can't access from other machines?
```bash
# Check if running
docker-compose ps
# OR
sudo systemctl status forecasting

# Check firewall
sudo ufw status

# Check if port is listening
sudo netstat -tlnp | grep 8501
```

### Container won't start?
```bash
# Check logs
docker-compose logs

# Common fix: rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Service won't start?
```bash
# Check logs
sudo journalctl -u forecasting -n 50

# Check file permissions
ls -la /home/streamlit/forecasting_app

# Try manual start
sudo -u streamlit /home/streamlit/forecasting_app/venv/bin/streamlit run /home/streamlit/forecasting_app/app.py
```

### High memory usage?
```bash
# Check Docker stats
docker stats

# Add memory limit in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 4G
```

---

## 💡 Pro Tips

✅ **Use Docker** for easiest deployment  
✅ **Set up SSL** immediately for security  
✅ **Add authentication** for private data  
✅ **Monitor logs** regularly  
✅ **Backup data** weekly  
✅ **Update monthly** for security patches  

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Docker orchestration |
| `deploy_docker.sh` | Automated Docker setup |
| `deploy_server.sh` | Automated server setup |
| `nginx.conf.template` | Reverse proxy config |
| `SELF_HOSTING_GUIDE.md` | Complete manual |

---

## 🎯 Deployment Checklist

Before going live:
- [ ] Server meets requirements
- [ ] Application deployed and accessible
- [ ] Firewall configured
- [ ] SSL certificate installed
- [ ] Authentication enabled
- [ ] Backups configured
- [ ] Monitoring setup
- [ ] Team tested access
- [ ] Documentation shared

---

## 📞 Get Help

**Full Guide:**
- SELF_HOSTING_GUIDE.md - Complete step-by-step

**Platform Docs:**
- Docker: https://docs.docker.com
- Nginx: https://nginx.org/en/docs
- Certbot: https://certbot.eff.org

**Common Issues:**
- Check logs first
- Verify firewall settings
- Test with curl from server
- Check file permissions

---

## 🎉 Ready to Deploy!

**Fastest path:**
1. Upload files to your server
2. Run: `./deploy_docker.sh`
3. Access at http://your-server-ip:8501
4. Setup SSL and domain (optional)

**Total time:** 5-10 minutes  
**Total cost:** Your server only  
**Result:** Full control, complete privacy

---

**Deploy on YOUR infrastructure today!** 🚀

For detailed instructions, see **SELF_HOSTING_GUIDE.md**
