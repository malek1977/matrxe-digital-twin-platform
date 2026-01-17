#!/bin/bash
# MATRXe Deployment Script for Hostinger VPS
# Usage: bash setup_hostinger.sh

set -e

echo "🚀 Starting MATRXe Deployment on Hostinger VPS..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="matrxe"
DOMAIN="matrxe.com"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"
DATABASE_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 64)

# Log function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root"
fi

# Step 1: System Update
log "Step 1: Updating system packages..."
apt-get update
apt-get upgrade -y

# Step 2: Install Docker and Docker Compose
log "Step 2: Installing Docker and Docker Compose..."
apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Step 3: Configure Docker
log "Step 3: Configuring Docker..."
systemctl enable docker
systemctl start docker
usermod -aG docker $SUDO_USER

# Step 4: Install Nginx
log "Step 4: Installing and configuring Nginx..."
apt-get install -y nginx certbot python3-certbot-nginx

# Step 5: Create application directory
log "Step 5: Creating application directory..."
APP_DIR="/opt/$APP_NAME"
mkdir -p $APP_DIR
cd $APP_DIR

# Step 6: Clone or create project structure
log "Step 6: Setting up project structure..."
mkdir -p {backend,frontend,ai_models,deployment,database,documentation}

# Step 7: Create environment file
log "Step 7: Creating environment configuration..."
cat > .env << EOF
# MATRXe Environment Configuration
# ===============================

# Application
APP_NAME=$APP_NAME
DOMAIN=$DOMAIN
ENVIRONMENT=production
DEBUG=false

# Security
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
REFRESH_TOKEN_EXPIRE_MINUTES=43200

# Database
DB_PASSWORD=$DATABASE_PASSWORD
DATABASE_URL=postgresql://matrxe_user:$DATABASE_PASSWORD@postgres/matrxe

# Redis
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0

# AI Services
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=llama3:8b

# File Uploads
UPLOAD_DIR=/uploads
MAX_UPLOAD_SIZE=104857600

# Billing
DEFAULT_CURRENCY=USD
CREDIT_PRICE=0.01
TRIAL_CREDITS=1000
TRIAL_DAYS=30

# Internationalization
DEFAULT_LANGUAGE=ar
SUPPORTED_LANGUAGES=ar,en,fr,es,de,ru,tr,ur

# Email (configure if needed)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@$DOMAIN

# Monitoring
GRAFANA_PASSWORD=$(openssl rand -base64 16)
EOF

# Step 8: Create docker-compose.yml
log "Step 8: Creating docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: matrxe
      POSTGRES_USER: matrxe_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U matrxe_user"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=${ENVIRONMENT}
      - DEBUG=${DEBUG}
    volumes:
      - uploads_data:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    depends_on:
      - backend
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    volumes:
      - ./deployment/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./deployment/ssl:/etc/nginx/ssl
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  ollama_data:
  uploads_data:
EOF

# Step 9: Configure Nginx
log "Step 9: Configuring Nginx..."
mkdir -p deployment/nginx deployment/ssl

cat > deployment/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/atom+xml image/svg+xml;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

    # Backend upstream
    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    # Frontend upstream
    upstream frontend {
        server frontend:80;
        keepalive 32;
    }

    # Include server configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF

cat > deployment/nginx/conf.d/matrxe.conf << EOF
# MATRXe Platform Configuration
# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Redirect to HTTPS
    return 301 https://\$server_name\$request_uri;
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL certificates (will be added by certbot)
    ssl_certificate /etc/nginx/ssl/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/live/$DOMAIN/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https: wss:;" always;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_buffering off;
    }

    # Backend API
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_buffering off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Authentication endpoints (stricter rate limiting)
    location /api/v1/auth/ {
        limit_req zone=auth burst=5 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    # Static files
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Uploads
    location /uploads/ {
        internal;
        alias /uploads/;
        expires 1h;
        add_header Cache-Control "public";
    }

    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOF

# Step 10: Set up SSL certificates
log "Step 10: Setting up SSL certificates..."
if [ ! -f "deployment/ssl/live/$DOMAIN/fullchain.pem" ]; then
    warning "SSL certificates not found. Please run:"
    warning "certbot --nginx -d $DOMAIN -d www.$DOMAIN"
    warning "Then copy certificates to deployment/ssl/live/$DOMAIN/"
else
    log "SSL certificates found."
fi

# Step 11: Create project directories structure
log "Step 11: Creating project files structure..."

# Backend Dockerfile
cat > backend/Dockerfile << 'EOF'
# Backend Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Frontend Dockerfile
cat > frontend/Dockerfile << 'EOF'
# Frontend Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
EOF

cat > frontend/nginx.conf << 'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/atom+xml image/svg+xml;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Main application
    location / {
        try_files $uri $uri/ /index.html;
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # API proxy (if needed)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Step 12: Create initial database schema
log "Step 12: Creating initial database schema..."
cat > database/init.sql << 'EOF'
-- MATRXe Initial Database Schema
-- Created on deployment

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create admin user (password will be set via application)
INSERT INTO users (id, email, username, password_hash, is_verified, is_active)
VALUES (
    uuid_generate_v4(),
    'admin@matrxe.com',
    'admin',
    -- Default password: Admin123 (should be changed after first login)
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- Insert default AI providers
INSERT INTO ai_providers (id, name, provider_type, is_active)
VALUES 
    (uuid_generate_v4(), 'Ollama (Local)', 'chat', true),
    (uuid_generate_v4(), 'ElevenLabs', 'voice', true),
    (uuid_generate_v4(), 'MediaPipe', 'face', true)
ON CONFLICT DO NOTHING;
EOF

# Step 13: Set permissions
log "Step 13: Setting permissions..."
chown -R $SUDO_USER:$SUDO_USER $APP_DIR
chmod -R 755 $APP_DIR
chmod +x $APP_DIR/deployment/setup_hostinger.sh

# Step 14: Create systemd service
log "Step 14: Creating systemd service..."
cat > /etc/systemd/system/matrxe.service << EOF
[Unit]
Description=MATRXe Digital Twin Platform
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable matrxe.service

# Step 15: Create backup script
log "Step 15: Creating backup script..."
cat > $APP_DIR/deployment/backup.sh << 'EOF'
#!/bin/bash
# Backup script for MATRXe
BACKUP_DIR="/opt/matrxe/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/matrxe_backup_$TIMESTAMP.tar.gz"

mkdir -p $BACKUP_DIR

# Backup database
docker exec matrxe-postgres pg_dump -U matrxe_user matrxe > /tmp/matrxe_db_backup.sql

# Backup uploads
tar -czf $BACKUP_FILE \
    /tmp/matrxe_db_backup.sql \
    /opt/matrxe/uploads

# Cleanup
rm /tmp/matrxe_db_backup.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "matrxe_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

chmod +x $APP_DIR/deployment/backup.sh

# Step 16: Create restore script
cat > $APP_DIR/deployment/restore.sh << 'EOF'
#!/bin/bash
# Restore script for MATRXe
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring from backup: $BACKUP_FILE"
echo "WARNING: This will overwrite existing data!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Extract backup
tar -xzf $BACKUP_FILE -C /tmp

# Restore database
docker exec -i matrxe-postgres psql -U matrxe_user matrxe < /tmp/matrxe_db_backup.sql

# Restore uploads
rm -rf /opt/matrxe/uploads/*
cp -r /tmp/uploads/* /opt/matrxe/uploads/

# Cleanup
rm -rf /tmp/matrxe_db_backup.sql /tmp/uploads

echo "Restore completed successfully!"
EOF

chmod +x $APP_DIR/deployment/restore.sh

# Step 17: Create update script
cat > $APP_DIR/deployment/update.sh << 'EOF'
#!/bin/bash
# Update script for MATRXe
APP_DIR="/opt/matrxe"

cd $APP_DIR

echo "Starting MATRXe update..."
echo "=========================="

# Pull latest code (if using git)
# git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d

echo "Update completed!"
echo "Check status with: docker compose ps"
EOF

chmod +x $APP_DIR/deployment/update.sh

# Step 18: Create maintenance script
cat > $APP_DIR/deployment/maintenance.sh << 'EOF'
#!/bin/bash
# Maintenance script for MATRXe
ACTION=$1

case $ACTION in
    start)
        echo "Starting maintenance mode..."
        docker compose exec nginx mv /etc/nginx/conf.d/matrxe.conf /etc/nginx/conf.d/matrxe.conf.disabled
        docker compose exec nginx mv /etc/nginx/conf.d/maintenance.conf /etc/nginx/conf.d/maintenance.conf.enabled
        docker compose exec nginx nginx -s reload
        ;;
    stop)
        echo "Stopping maintenance mode..."
        docker compose exec nginx mv /etc/nginx/conf.d/maintenance.conf.enabled /etc/nginx/conf.d/maintenance.conf
        docker compose exec nginx mv /etc/nginx/conf.d/matrxe.conf.disabled /etc/nginx/conf.d/matrxe.conf
        docker compose exec nginx nginx -s reload
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac
EOF

chmod +x $APP_DIR/deployment/maintenance.sh

# Step 19: Create maintenance page
cat > deployment/nginx/conf.d/maintenance.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name matrxe.com www.matrxe.com;

    location / {
        return 503;
    }

    error_page 503 @maintenance;
    
    location @maintenance {
        root /usr/share/nginx/html;
        rewrite ^(.*)$ /maintenance.html break;
    }
}
EOF

cat > frontend/public/maintenance.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MATRXe - Maintenance</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            color: white;
        }
        
        .container {
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            max-width: 600px;
        }
        
        h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }
        
        .loader {
            border: 5px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 5px solid white;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 2rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .languages {
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .language {
            display: inline-block;
            margin: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .language:hover {
            background: rgba(255, 255, 255, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="loader"></div>
        <h1>🛠️ MATRXe</h1>
        <p>We're currently performing scheduled maintenance to improve your experience.</p>
        <p>The platform will be back online shortly. Thank you for your patience!</p>
        
        <div class="languages">
            <div class="language" onclick="changeLanguage('en')">English</div>
            <div class="language" onclick="changeLanguage('ar')">العربية</div>
            <div class="language" onclick="changeLanguage('fr')">Français</div>
            <div class="language" onclick="changeLanguage('es')">Español</div>
        </div>
    </div>

    <script>
        const messages = {
            en: {
                title: "🛠️ MATRXe",
                message: "We're currently performing scheduled maintenance to improve your experience.",
                submessage: "The platform will be back online shortly. Thank you for your patience!"
            },
            ar: {
                title: "🛠️ ماتركس إي",
                message: "نحن نقوم حاليًا بإجراء صيانة مجدولة لتحسين تجربتك.",
                submessage: "ستعود المنصة للعمل قريبًا. شكرًا لصبرك!"
            },
            fr: {
                title: "🛠️ MATRXe",
                message: "Nous effectuons actuellement une maintenance programmée pour améliorer votre expérience.",
                submessage: "La plateforme sera de nouveau en ligne sous peu. Merci de votre patience!"
            },
            es: {
                title: "🛠️ MATRXe",
                message: "Actualmente estamos realizando mantenimiento programado para mejorar tu experiencia.",
                submessage: "La plataforma volverá a estar en línea en breve. ¡Gracias por tu paciencia!"
            }
        };

        function changeLanguage(lang) {
            const msg = messages[lang] || messages.en;
            document.querySelector('h1').textContent = msg.title;
            document.querySelectorAll('p')[0].textContent = msg.message;
            document.querySelectorAll('p')[1].textContent = msg.submessage;
        }
    </script>
</body>
</html>
EOF

# Step 20: Create monitoring dashboard
log "Step 20: Setting up monitoring..."
mkdir -p deployment/monitoring

cat > deployment/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'matrxe-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    
  - job_name: 'matrxe-postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'matrxe-redis'
    static_configs:
      - targets: ['redis-exporter:9121']
EOF

# Step 21: Create startup script
cat > $APP_DIR/start.sh << 'EOF'
#!/bin/bash
# MATRXe Startup Script
echo "Starting MATRXe Platform..."
echo "============================"

# Load environment
set -a
source .env
set +a

# Start services
docker compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check services status
echo "Checking services status..."
docker compose ps

# Show logs
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
echo ""
echo "MATRXe is now running!"
echo "Frontend: https://matrxe.com"
echo "Backend API: https://matrxe.com/api/v1"
echo "Health check: https://matrxe.com/health"
EOF

chmod +x $APP_DIR/start.sh

# Step 22: Create stop script
cat > $APP_DIR/stop.sh << 'EOF'
#!/bin/bash
# MATRXe Stop Script
echo "Stopping MATRXe Platform..."
docker compose down
echo "Platform stopped."
EOF

chmod +x $APP_DIR/stop.sh

# Step 23: Create status script
cat > $APP_DIR/status.sh << 'EOF'
#!/bin/bash
# MATRXe Status Script
echo "MATRXe Platform Status"
echo "======================"
docker compose ps
echo ""
echo "Disk Usage:"
df -h /opt/matrxe
echo ""
echo "Recent Logs:"
docker compose logs --tail=20
EOF

chmod +x $APP_DIR/status.sh

# Step 24: Finalize setup
log "Step 24: Finalizing setup..."

# Create README
cat > $APP_DIR/README_DEPLOYMENT.md << 'EOF'
# MATRXe Deployment Guide

## Quick Start
1. Configure SSL certificates:
   ```bash
   certbot --nginx -d matrxe.com -d www.matrxe.com
   cp -r /etc/letsencrypt/live/matrxe.com deployment/ssl/live/