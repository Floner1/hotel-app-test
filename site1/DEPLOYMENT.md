# Deployment Guide

## Overview

This guide covers deploying the Thien Tai Hotel Booking System from development to production environments.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Development Environment](#development-environment)
3. [Production Deployment](#production-deployment)
4. [Database Setup](#database-setup)
5. [Static Files Configuration](#static-files-configuration)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Pre-Deployment Checklist

### ✅ Code Readiness

- [ ] All features tested locally
- [ ] No console errors in browser
- [ ] All database migrations applied
- [ ] Static files collected and verified
- [ ] Environment variables configured
- [ ] Debug mode set to False
- [ ] Allowed hosts configured
- [ ] Secret key generated for production
- [ ] HTTPS configured (if applicable)
- [ ] Database backup created

### ✅ Dependencies

```bash
# Check Python version
python --version  # Should be 3.8+

# Check Django installation
python -m django --version  # Should be 5.2.4

# Verify pip packages
pip list
```

### ✅ Required Packages

```text
Django==5.2.4
mssql-django>=1.5
pyodbc>=4.0.39
python-dotenv>=0.19.0
whitenoise>=6.0  # For static files serving
gunicorn>=20.1.0  # For production WSGI server
```

---

## Development Environment

### Local Setup

1. **Clone Repository**
```bash
git clone <repository-url>
cd hotel-app-test
```

2. **Navigate to Project**
```bash
cd site1
```

3. **Configure Environment Variables**

Create `.env` file in `site1/` directory:

```env
# Database Configuration
DB_NAME=hotelbooking
DB_HOST=DESKTOP-NS6H7CH\MSSQLSERVER01
DB_OPTIONS=driver=SQL Server Native Client 11.0;Trusted_Connection=yes

# Django Settings
DEBUG=True
SECRET_KEY=your-development-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Static Files
STATIC_URL=/static/
STATIC_ROOT=staticfiles/
```

4. **Apply Migrations**
```bash
python manage.py migrate
```

5. **Create Superuser**
```bash
python manage.py createsuperuser
```

6. **Collect Static Files**
```bash
python manage.py collectstatic --noinput
```

7. **Run Development Server**
```bash
python manage.py runserver
```

---

## Production Deployment

### Option 1: Windows Server with IIS

#### Prerequisites
- Windows Server 2016+ or Windows 10/11 Pro
- IIS installed with CGI module
- Python 3.8+ installed
- SQL Server installed and running

#### Step 1: Install wfastcgi

```bash
pip install wfastcgi
wfastcgi-enable
```

Note the path returned (e.g., `c:\python3\lib\site-packages\wfastcgi.py`)

#### Step 2: Configure web.config

Create `web.config` in `site1/` directory:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="Python FastCGI" 
           path="*" 
           verb="*" 
           modules="FastCgiModule" 
           scriptProcessor="C:\Python3\python.exe|C:\Python3\lib\site-packages\wfastcgi.py" 
           resourceType="Unspecified" 
           requireAccess="Script" />
    </handlers>
    <rewrite>
      <rules>
        <rule name="Static Files" stopProcessing="true">
          <match url="^static/.*" />
          <action type="Rewrite" url="{REQUEST_URI}" />
        </rule>
        <rule name="Configure Python" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="handler.fcgi/{R:1}" appendQueryString="true" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
  <appSettings>
    <add key="WSGI_HANDLER" value="site1.wsgi.application" />
    <add key="PYTHONPATH" value="D:\hotel-app-test\site1" />
    <add key="DJANGO_SETTINGS_MODULE" value="site1.settings" />
  </appSettings>
</configuration>
```

#### Step 3: Create IIS Site

1. Open IIS Manager
2. Right-click "Sites" → "Add Website"
3. Configure:
   - Site name: `ThienTaiHotel`
   - Physical path: `D:\hotel-app-test\site1`
   - Binding: HTTP, Port 80 (or 443 for HTTPS)
   - Host name: `yourdomain.com`

4. Set Application Pool:
   - .NET CLR version: No Managed Code
   - Identity: ApplicationPoolIdentity or custom account

5. Set Permissions:
   - Grant IIS_IUSRS read access to site folder
   - Grant modify access to `staticfiles/` directory

#### Step 4: Update Django Settings

In `site1/settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Security settings
SECURE_SSL_REDIRECT = True  # If using HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

#### Step 5: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

#### Step 6: Restart IIS

```bash
iisreset
```

### Option 2: Linux Server with Nginx + Gunicorn

#### Prerequisites
- Ubuntu 20.04+ or similar
- Python 3.8+
- Nginx installed
- SQL Server accessible from Linux

#### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx unixodbc unixodbc-dev
```

#### Step 2: Install Microsoft ODBC Driver

```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install msodbcsql17
```

#### Step 3: Setup Virtual Environment

```bash
cd /var/www/hotel-app-test/site1
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 4: Configure Gunicorn

Create `gunicorn_config.py`:

```python
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
timeout = 120
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

Create systemd service `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn daemon for Thien Tai Hotel
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/hotel-app-test/site1
ExecStart=/var/www/hotel-app-test/site1/venv/bin/gunicorn \
          --config /var/www/hotel-app-test/site1/gunicorn_config.py \
          site1.wsgi:application

[Install]
WantedBy=multi-user.target
```

#### Step 5: Configure Nginx

Create `/etc/nginx/sites-available/thientaihotel`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/hotel-app-test/site1/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/thientaihotel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 6: Start Gunicorn

```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

---

## Database Setup

### SQL Server Configuration

#### 1. Create Database

```sql
CREATE DATABASE hotelbooking;
GO

USE hotelbooking;
GO
```

#### 2. Create Database User (for non-Windows auth)

```sql
CREATE LOGIN hotel_app_user WITH PASSWORD = 'StrongPassword123!';
GO

USE hotelbooking;
CREATE USER hotel_app_user FOR LOGIN hotel_app_user;
GO

ALTER ROLE db_datareader ADD MEMBER hotel_app_user;
ALTER ROLE db_datawriter ADD MEMBER hotel_app_user;
ALTER ROLE db_ddladmin ADD MEMBER hotel_app_user;
GO
```

#### 3. Run Migrations

```bash
python manage.py migrate
```

#### 4. Create Initial Data

```bash
python manage.py createsuperuser

# Optional: Load fixtures
python manage.py loaddata initial_data.json
```

### Database Connection String

**Windows Authentication:**
```python
'OPTIONS': {
    'driver': 'SQL Server Native Client 11.0',
    'extra_params': 'Trusted_Connection=yes'
}
```

**SQL Authentication:**
```python
'OPTIONS': {
    'driver': 'ODBC Driver 17 for SQL Server',
},
'USER': 'hotel_app_user',
'PASSWORD': 'StrongPassword123!',
```

---

## Static Files Configuration

### Development

```python
# settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
```

### Production

```python
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Use WhiteNoise for serving static files
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
    # ... other middleware
]

# Optional: Enable compression and caching
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

## Security Hardening

### 1. Django Settings

```python
# settings.py (Production)

DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Security
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')  # Read from environment
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

### 2. Generate Secret Key

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 3. Database Security

- Use strong passwords
- Enable SSL/TLS for database connections
- Implement database-level RBAC (already configured)
- Regular backups
- Audit log monitoring

### 4. Firewall Configuration

**Windows:**
```powershell
# Allow HTTP
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# Allow HTTPS
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

**Linux (UFW):**
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 5. SSL/TLS Certificate

**Using Let's Encrypt (Linux):**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

**IIS (Windows):**
1. Generate CSR in IIS Manager
2. Purchase certificate from CA
3. Install certificate in IIS
4. Bind HTTPS to site

---

## Monitoring & Maintenance

### Logging

#### Configure Django Logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/error.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

### Database Backups

**Automated Backup Script (Windows):**

```powershell
# backup_database.ps1
$BackupPath = "D:\Backups\Hotel\"
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = "${BackupPath}hotelbooking_${Date}.bak"

Invoke-Sqlcmd -Query "BACKUP DATABASE hotelbooking TO DISK='$BackupFile'" `
              -ServerInstance "DESKTOP-NS6H7CH\MSSQLSERVER01"
```

Schedule with Task Scheduler to run daily.

**Linux:**

```bash
#!/bin/bash
# backup_database.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/hotel"
sqlcmd -S SERVER_IP -U sa -P 'Password' \
       -Q "BACKUP DATABASE hotelbooking TO DISK='/tmp/backup_$DATE.bak'"
```

### Health Checks

Create `health_check.py`:

```python
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({'status': 'healthy', 'database': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)
```

Add to `urls.py`:

```python
path('health/', health_check, name='health_check'),
```

### Performance Monitoring

1. **Enable Django Debug Toolbar** (development only)
2. **Use Application Insights** (Azure)
3. **Monitor with New Relic** (third-party)
4. **Custom metrics** in audit_log table

### Maintenance Tasks

```bash
# Weekly tasks
python manage.py clearsessions  # Clear expired sessions
python manage.py check --deploy  # Security checks

# Monthly tasks
# Review audit logs
# Update dependencies
# Database optimization
```

---

## Troubleshooting

### Common Issues

**1. Static files not loading**
```bash
python manage.py collectstatic --noinput
# Check STATIC_ROOT and STATIC_URL settings
```

**2. Database connection errors**
```bash
# Test connection
python manage.py dbshell
# Check SQL Server service status
# Verify firewall rules
```

**3. 500 Internal Server Error**
```bash
# Check logs
tail -f /var/log/gunicorn/error.log
# Enable DEBUG temporarily to see details
```

**4. Permission errors (IIS)**
```powershell
# Grant permissions
icacls "D:\hotel-app-test\site1" /grant "IIS_IUSRS:(OI)(CI)F"
```

---

## Rollback Procedure

### If Deployment Fails

1. **Revert code**
```bash
git checkout previous-stable-tag
```

2. **Rollback database** (if needed)
```sql
RESTORE DATABASE hotelbooking FROM DISK='backup_file.bak' WITH REPLACE;
```

3. **Restart services**
```bash
# Linux
sudo systemctl restart gunicorn nginx

# Windows
iisreset
```

---

## Checklist: Post-Deployment

- [ ] Site accessible via domain
- [ ] HTTPS working (if configured)
- [ ] All pages loading correctly
- [ ] Static files serving properly
- [ ] Database connections working
- [ ] Login/authentication functional
- [ ] Booking system operational
- [ ] Admin dashboard accessible
- [ ] Logs being written
- [ ] Backup system running
- [ ] Health check endpoint responding
- [ ] Email notifications working (if configured)

---

## Support & Maintenance

### Regular Tasks

**Daily:**
- Monitor error logs
- Check health endpoint
- Verify backups completed

**Weekly:**
- Review access logs
- Clear expired sessions
- Update security patches

**Monthly:**
- Database optimization
- Dependency updates
- Security audit
- Performance review

### Emergency Contacts

- **Database Admin:** [Contact Info]
- **Server Admin:** [Contact Info]
- **Development Team:** [Contact Info]

---

**Last Updated:** February 1, 2026  
**Version:** 1.0  
**Maintained By:** Development Team
