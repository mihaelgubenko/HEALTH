#!/bin/bash

# Deploy script for Smart Secretary on Yandex Cloud

echo "🚀 Starting deployment of Smart Secretary..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
echo "🐍 Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install PostgreSQL
echo "🐘 Installing PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib

# Install Nginx
echo "🌐 Installing Nginx..."
sudo apt install -y nginx

# Install Git
echo "📥 Installing Git..."
sudo apt install -y git

# Create project directory
echo "📁 Creating project directory..."
sudo mkdir -p /var/www/smart_secretary
sudo chown $USER:$USER /var/www/smart_secretary

# Clone or copy project
echo "📋 Setting up project..."
cd /var/www/smart_secretary

# If using Git repository:
# git clone https://github.com/your-username/smart-secretary.git .

# Or copy files from local machine:
# scp -r /path/to/local/project/* user@server:/var/www/smart_secretary/

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Configure PostgreSQL
echo "🗄️ Configuring PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE smart_secretary;"
sudo -u postgres psql -c "CREATE USER smart_secretary_user WITH PASSWORD 'your-db-password-here';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE smart_secretary TO smart_secretary_user;"
sudo -u postgres psql -c "ALTER USER smart_secretary_user CREATEDB;"

# Create production environment file
echo "⚙️ Creating production environment file..."
cat > .env.production << EOF
DEBUG=False
SECRET_KEY=your-production-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=smart_secretary
DB_USER=smart_secretary_user
DB_PASSWORD=your-db-password-here
DB_HOST=localhost
DB_PORT=5432

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Center Configuration
CENTER_NAME=Центр здоровья "Новая Жизнь"
CENTER_ADDRESS=Израиль. Рамот Алеф. ул. Сулам Яков 1/3
PHONE_MAIN=+972545270015
PHONE_ALT=+972545270015
BASE_URL=https://your-domain.com

# AI Features
AI_PRO_PLAYBOOKS_ENABLED=false
AI_PRO_PLAYBOOK_STAGE=0
EOF

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Create superuser
echo "👤 Creating superuser..."
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None"

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Configure Gunicorn
echo "🔧 Configuring Gunicorn..."
cat > gunicorn.conf.py << EOF
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
user = "www-data"
group = "www-data"
EOF

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/smart-secretary.service > /dev/null << EOF
[Unit]
Description=Smart Secretary Django App
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/smart_secretary
Environment=PATH=/var/www/smart_secretary/venv/bin
ExecStart=/var/www/smart_secretary/venv/bin/gunicorn --config gunicorn.conf.py smart_secretary.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/smart-secretary > /dev/null << EOF
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/smart_secretary;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root /var/www/smart_secretary;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/smart-secretary /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable smart-secretary
sudo systemctl start smart-secretary
sudo systemctl restart nginx

echo "✅ Deployment completed!"
echo "🌐 Your site should be available at: http://your-server-ip"
echo "👤 Admin login: admin / admin123"
echo "🔧 Don't forget to:"
echo "   - Update your domain in Nginx config"
echo "   - Set up SSL certificate"
echo "   - Change admin password"
echo "   - Update environment variables"
