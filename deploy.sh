#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Initial server setup + production deploy for a DigitalOcean Droplet
#
# Prerequisites on local machine:
#   export DOMAIN=your-domain.com
#   export CERTBOT_EMAIL=admin@your-domain.com
#   export DB_PASSWORD=your_strong_password
#   export SERVER_IP=<droplet-ip>
#   export REPO_URL=https://github.com/nmqdtech/contact-forecasting.git
#
# Run:  bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[info]${NC} $*"; }
ok()   { echo -e "${GREEN}[ ok ]${NC} $*"; }
die()  { echo -e "${RED}[fail]${NC} $*" >&2; exit 1; }

# ── Validate required env vars ────────────────────────────────────────────────
: "${DOMAIN:?Set DOMAIN=your-domain.com}"
: "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL=admin@your-domain.com}"
: "${DB_PASSWORD:?Set DB_PASSWORD=...}"
: "${SERVER_IP:?Set SERVER_IP=<droplet-ip>}"
: "${REPO_URL:=https://github.com/nmqdtech/contact-forecasting.git}"

APP_DIR=/opt/forecasting

# ─────────────────────────────────────────────────────────────────────────────
# All commands below run on the remote server via SSH
# ─────────────────────────────────────────────────────────────────────────────
ssh -o StrictHostKeyChecking=no "root@${SERVER_IP}" bash -s -- \
    "$DOMAIN" "$CERTBOT_EMAIL" "$DB_PASSWORD" "$REPO_URL" "$APP_DIR" << 'REMOTE'

set -euo pipefail
DOMAIN="$1"; CERTBOT_EMAIL="$2"; DB_PASSWORD="$3"; REPO_URL="$4"; APP_DIR="$5"

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[info]${NC} $*"; }
ok()   { echo -e "${GREEN}[ ok ]${NC} $*"; }

# ── 1. Install Docker ─────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    apt-get update -q
    apt-get install -y -q ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -q
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    ok "Docker installed"
else
    ok "Docker already present"
fi

# ── 2. Firewall ───────────────────────────────────────────────────────────────
info "Configuring UFW..."
ufw allow 22/tcp  > /dev/null
ufw allow 80/tcp  > /dev/null
ufw allow 443/tcp > /dev/null
ufw --force enable > /dev/null
ok "Firewall ready (22, 80, 443)"

# ── 3. Clone / update repo ────────────────────────────────────────────────────
if [[ -d "$APP_DIR/.git" ]]; then
    info "Updating repository..."
    git -C "$APP_DIR" pull --quiet
else
    info "Cloning repository → $APP_DIR ..."
    git clone --quiet "$REPO_URL" "$APP_DIR"
fi
ok "Repo at $APP_DIR"

# ── 4. Write .env ─────────────────────────────────────────────────────────────
info "Writing .env ..."
cat > "$APP_DIR/.env" <<EOF
DOMAIN=${DOMAIN}
DB_USER=forecasting
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=forecasting
DATABASE_URL=postgresql+asyncpg://forecasting:${DB_PASSWORD}@db:5432/forecasting
SYNC_DATABASE_URL=postgresql+psycopg2://forecasting:${DB_PASSWORD}@db:5432/forecasting
CERTBOT_EMAIL=${CERTBOT_EMAIL}
UPLOAD_MAX_MB=50
EOF
chmod 600 "$APP_DIR/.env"
ok ".env written"

# ── 5. Obtain initial SSL certificate ─────────────────────────────────────────
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
if [[ ! -f "$CERT_PATH" ]]; then
    info "Obtaining SSL certificate for ${DOMAIN} ..."
    # Temporarily bind port 80 with certbot standalone
    docker run --rm \
        -p 80:80 \
        -v "$(docker volume create certbot_certs):/etc/letsencrypt" \
        -v "$(docker volume create certbot_www):/var/www/certbot" \
        certbot/certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        -m "${CERTBOT_EMAIL}" \
        -d "${DOMAIN}" \
        --rsa-key-size 4096
    ok "SSL certificate obtained"
else
    ok "SSL certificate already exists"
fi

# ── 6. Build and start production stack ───────────────────────────────────────
info "Building production images..."
cd "$APP_DIR"
docker compose -f docker-compose.prod.yml build --no-cache

info "Starting production stack..."
docker compose -f docker-compose.prod.yml up -d

info "Waiting 20 s for services to initialise..."
sleep 20

info "Stack status:"
docker compose -f docker-compose.prod.yml ps

ok "Deployment complete!"
echo ""
echo "  App:    https://${DOMAIN}"
echo "  API:    https://${DOMAIN}/api/v1"
echo "  Docs:   https://${DOMAIN}/api/v1/docs"

REMOTE

ok "Remote deploy finished."
