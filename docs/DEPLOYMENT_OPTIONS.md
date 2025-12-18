# 🚀 Deployment Options Guide

## Overview

This guide compares different deployment options for AFGA, from simple local development to enterprise-grade cloud deployments.

---

## 🏢 Deployment Decision Matrix

| Scenario | Users | Best Solution | Monthly Cost | Access Method |
|----------|-------|---------------|--------------|---------------|
| **Development/Testing** | 1-2 | Local (`./start.sh`) | $0 | `localhost:8501` |
| **Small Team (Internal)** | 5-20 | Azure App Service | $50-100 | `https://afga.azurewebsites.net` |
| **Department (Internal)** | 20-100 | Azure App Service + VNet | $100-200 | `https://afga-internal.company.com` |
| **On-Premises Only** | Any | Docker Compose on VM | Server cost | `http://afga-server.internal:8501` |
| **Enterprise/Multi-Tenant** | 100+ | AKS (Current setup) | $150-300 | `https://afga.company.com` |

---

## 1️⃣ Azure App Service (Recommended for Internal Apps)

**Best for:** 5-100 users, managed platform, easy maintenance

### Access Method
- **Public URL**: `https://afga-backend.azurewebsites.net` (with SSL)
- **Internal Only**: Configure VNet integration + Private Endpoint
- **Custom Domain**: `https://finance-governance.company.com`

### Deployment Steps

#### Step 1: Create Azure Resources
```bash
# Login to Azure
az login

# Create Resource Group
az group create --name rg-afga-appservice --location westeurope

# Create App Service Plan (B2: 2 cores, 3.5GB RAM)
az appservice plan create \
  --name afga-plan \
  --resource-group rg-afga-appservice \
  --sku B2 \
  --is-linux

# Create Container Registry (if not exists)
az acr create \
  --resource-group rg-afga-appservice \
  --name afgaacr \
  --sku Basic \
  --admin-enabled true
```

#### Step 2: Build and Push Images
```bash
# Login to ACR
az acr login --name afgaacr

# Build images
docker build -t afgaacr.azurecr.io/afga-backend:latest \
  -f deployment/docker/Dockerfile.backend .
docker build -t afgaacr.azurecr.io/afga-frontend:latest \
  -f deployment/docker/Dockerfile.frontend .

# Push to registry
docker push afgaacr.azurecr.io/afga-backend:latest
docker push afgaacr.azurecr.io/afga-frontend:latest
```

#### Step 3: Create Web Apps
```bash
# Backend App
az webapp create \
  --resource-group rg-afga-appservice \
  --plan afga-plan \
  --name afga-backend \
  --deployment-container-image-name afgaacr.azurecr.io/afga-backend:latest

# Frontend App
az webapp create \
  --resource-group rg-afga-appservice \
  --plan afga-plan \
  --name afga-frontend \
  --deployment-container-image-name afgaacr.azurecr.io/afga-frontend:latest

# Configure ACR credentials
ACR_USERNAME=$(az acr credential show --name afgaacr --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name afgaacr --query passwords[0].value -o tsv)

az webapp config container set \
  --name afga-backend \
  --resource-group rg-afga-appservice \
  --docker-registry-server-url https://afgaacr.azurecr.io \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD

az webapp config container set \
  --name afga-frontend \
  --resource-group rg-afga-appservice \
  --docker-registry-server-url https://afgaacr.azurecr.io \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD
```

#### Step 4: Configure Environment Variables
```bash
# Set backend environment variables
az webapp config appsettings set \
  --name afga-backend \
  --resource-group rg-afga-appservice \
  --settings \
    OPENROUTER_API_KEY="your-key" \
    OPENAI_API_KEY="your-key" \
    DATABASE_URL="sqlite:///data/afga.db" \
    ENVIRONMENT="production"

# Set frontend environment variable
az webapp config appsettings set \
  --name afga-frontend \
  --resource-group rg-afga-appservice \
  --settings \
    BACKEND_URL="https://afga-backend.azurewebsites.net"
```

#### Step 5: Access Your Application
```bash
# Get URLs
echo "Backend: https://afga-backend.azurewebsites.net"
echo "Frontend: https://afga-frontend.azurewebsites.net"
echo "API Docs: https://afga-backend.azurewebsites.net/docs"
```

### 🔒 Make It Internal-Only (VNet Integration)
```bash
# Create Virtual Network
az network vnet create \
  --resource-group rg-afga-appservice \
  --name afga-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name afga-subnet \
  --subnet-prefix 10.0.1.0/24

# Integrate Web App with VNet
az webapp vnet-integration add \
  --name afga-frontend \
  --resource-group rg-afga-appservice \
  --vnet afga-vnet \
  --subnet afga-subnet

# Disable public access
az webapp config access-restriction add \
  --name afga-frontend \
  --resource-group rg-afga-appservice \
  --rule-name "DenyAll" \
  --action Deny \
  --priority 100
```

**Access Method After VNet:**
- Only accessible from company network or via VPN
- URL remains `https://afga-frontend.azurewebsites.net` but only resolves internally

### 💰 Cost Optimization
```bash
# Enable auto-scaling (scale down at night)
az monitor autoscale create \
  --resource-group rg-afga-appservice \
  --resource afga-plan \
  --resource-type Microsoft.Web/serverfarms \
  --name afga-autoscale \
  --min-count 1 \
  --max-count 3 \
  --count 1

# Add schedule rule (scale up during business hours)
az monitor autoscale rule create \
  --resource-group rg-afga-appservice \
  --autoscale-name afga-autoscale \
  --condition "CpuPercentage > 70" \
  --scale out 1
```

### 🗑️ Cleanup
```bash
az group delete --name rg-afga-appservice --yes --no-wait
```

---

## 2️⃣ Azure Container Instances (ACI)

**Best for:** Simple deployments, dev/test environments, 5-50 users

### Access Method
- **Public IP**: `http://52.123.45.67:8501` (HTTP only, or add Azure Application Gateway for HTTPS)
- **DNS Label**: `http://afga.westeurope.azurecontainer.io:8501`

### Deployment Steps

```bash
# Create Resource Group
az group create --name rg-afga-aci --location westeurope

# Deploy Backend
az container create \
  --resource-group rg-afga-aci \
  --name afga-backend \
  --image afgaacr.azurecr.io/afga-backend:latest \
  --registry-login-server afgaacr.azurecr.io \
  --registry-username $(az acr credential show --name afgaacr --query username -o tsv) \
  --registry-password $(az acr credential show --name afgaacr --query passwords[0].value -o tsv) \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    OPENROUTER_API_KEY="your-key" \
    ENVIRONMENT="production" \
  --dns-name-label afga-backend

# Deploy Frontend
az container create \
  --resource-group rg-afga-aci \
  --name afga-frontend \
  --image afgaacr.azurecr.io/afga-frontend:latest \
  --registry-login-server afgaacr.azurecr.io \
  --registry-username $(az acr credential show --name afgaacr --query username -o tsv) \
  --registry-password $(az acr credential show --name afgaacr --query passwords[0].value -o tsv) \
  --cpu 2 \
  --memory 4 \
  --ports 8501 \
  --environment-variables \
    BACKEND_URL="http://afga-backend.westeurope.azurecontainer.io:8000" \
  --dns-name-label afga-frontend

# Get Access URL
echo "Frontend: http://afga-frontend.westeurope.azurecontainer.io:8501"
```

### 🔒 Make It Internal-Only
```bash
# Deploy with VNet (no public IP)
az network vnet create \
  --resource-group rg-afga-aci \
  --name afga-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name afga-subnet \
  --subnet-prefix 10.0.1.0/24

az container create \
  --resource-group rg-afga-aci \
  --name afga-frontend \
  --image afgaacr.azurecr.io/afga-frontend:latest \
  --vnet afga-vnet \
  --subnet afga-subnet \
  --ports 8501
  # No DNS label = no public access
```

**Access Method After VNet:**
- Only accessible via internal IP: `http://10.0.1.4:8501`
- Requires VPN or Azure Bastion to access

---

## 3️⃣ Azure VM with Docker Compose

**Best for:** Full control, hybrid cloud/on-prem, 10-100 users

### Access Method
- **Public IP with Domain**: `https://afga.company.com` (via Azure DNS + Let's Encrypt)
- **Internal Only**: `http://10.0.1.4:8501` (VNet + VPN)
- **On-Prem Style**: `http://afga-vm.internal.company.com:8501`

### Deployment Steps

#### Step 1: Create VM
```bash
# Create VM with Docker pre-installed
az vm create \
  --resource-group rg-afga-vm \
  --name afga-vm \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-address-dns-name afga-vm

# Open ports
az vm open-port --port 8501 --resource-group rg-afga-vm --name afga-vm --priority 1001
az vm open-port --port 8000 --resource-group rg-afga-vm --name afga-vm --priority 1002
```

#### Step 2: SSH and Setup Docker
```bash
# SSH into VM
ssh azureuser@afga-vm.westeurope.cloudapp.azure.com

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Step 3: Deploy Application
```bash
# Create deployment directory
mkdir -p ~/afga && cd ~/afga

# Create docker-compose.yml
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  backend:
    image: afgaacr.azurecr.io/afga-backend:latest
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=\${OPENROUTER_API_KEY}
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  frontend:
    image: afgaacr.azurecr.io/afga-frontend:latest
    ports:
      - "8501:8501"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
EOF

# Create .env file
cat > .env <<EOF
OPENROUTER_API_KEY=your-key
OPENAI_API_KEY=your-key
EOF

# Login to ACR
docker login afgaacr.azurecr.io -u <username> -p <password>

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

#### Step 4: Access Application
```bash
# Get public IP
VM_IP=$(az vm show -d --resource-group rg-afga-vm --name afga-vm --query publicIps -o tsv)
echo "Frontend: http://$VM_IP:8501"
echo "Backend: http://$VM_IP:8000"

# Or use DNS name
echo "Frontend: http://afga-vm.westeurope.cloudapp.azure.com:8501"
```

### 🔒 Add SSL with Let's Encrypt (Optional)
```bash
# Install Nginx
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx

# Configure Nginx reverse proxy
sudo tee /etc/nginx/sites-available/afga <<EOF
server {
    listen 80;
    server_name afga.company.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/afga /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d afga.company.com
```

**Access After SSL:**
- `https://afga.company.com` (with valid SSL certificate)

### 💰 Auto-Shutdown for Cost Savings
```bash
# Stop VM at 6 PM weekdays
az vm auto-shutdown \
  --resource-group rg-afga-vm \
  --name afga-vm \
  --time 1800

# Or use Azure Automation to start/stop on schedule
# This can save ~70% costs (only running 9-6 weekdays)
```

---

## 4️⃣ On-Premises Deployment

**Best for:** Data sovereignty, no cloud costs, existing infrastructure

### Access Method
- **Internal Network**: `http://afga-server.company.local:8501`
- **VPN Access**: `http://10.20.30.40:8501`
- **Reverse Proxy**: `https://finance-governance.company.com`

### Deployment Steps

#### Prerequisites
- Physical or virtual server (4 cores, 8GB RAM recommended)
- Ubuntu 22.04 or similar Linux distribution
- Docker installed
- Internal DNS or static IP

#### Step 1: Prepare Server
```bash
# On your on-premises server
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Step 2: Transfer Application
```bash
# Option A: From your dev machine
scp -r adaptive_finance_governance_agent admin@afga-server:/opt/afga

# Option B: Clone from GitHub
ssh admin@afga-server
cd /opt
git clone <your-repo-url> afga
cd afga
```

#### Step 3: Build Images Locally (No Cloud Registry Needed)
```bash
cd /opt/afga

# Build images
docker build -t afga-backend:latest -f deployment/docker/Dockerfile.backend .
docker build -t afga-frontend:latest -f deployment/docker/Dockerfile.frontend .
```

#### Step 4: Create Production docker-compose.yml
```bash
cat > docker-compose.prod.yml <<EOF
version: '3.8'
services:
  backend:
    image: afga-backend:latest
    container_name: afga-backend
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=\${OPENROUTER_API_KEY}
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
      - DATABASE_URL=sqlite:///data/afga.db
    volumes:
      - /opt/afga/data:/app/data
      - /opt/afga/logs:/app/logs
    restart: unless-stopped
    networks:
      - afga-network

  frontend:
    image: afga-frontend:latest
    container_name: afga-frontend
    ports:
      - "8501:8501"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - afga-network

networks:
  afga-network:
    driver: bridge

volumes:
  afga-data:
    driver: local
EOF

# Create .env file
cat > .env <<EOF
OPENROUTER_API_KEY=your-key
OPENAI_API_KEY=your-key
EOF

# Set proper permissions
sudo chown -R 1000:1000 /opt/afga/data
```

#### Step 5: Start as System Service
```bash
# Create systemd service
sudo tee /etc/systemd/system/afga.service <<EOF
[Unit]
Description=AFGA Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/afga
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable afga
sudo systemctl start afga

# Check status
sudo systemctl status afga
```

#### Step 6: Configure Internal DNS (Optional)
```bash
# Add to your internal DNS server
# afga-server.company.local -> 10.20.30.40

# Or add to /etc/hosts on client machines
echo "10.20.30.40 afga.company.local" | sudo tee -a /etc/hosts
```

#### Step 7: Access Application
```bash
# From any machine on your internal network
echo "Frontend: http://afga-server.company.local:8501"
echo "Backend API: http://afga-server.company.local:8000"
echo "API Docs: http://afga-server.company.local:8000/docs"
```

### 🔒 Add Reverse Proxy with SSL (Recommended)

```bash
# Install Nginx
sudo apt update && sudo apt install -y nginx

# Configure reverse proxy
sudo tee /etc/nginx/sites-available/afga <<EOF
server {
    listen 80;
    server_name afga.company.local finance-governance.company.local;

    # Frontend
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/afga /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Now accessible at http://afga.company.local (no port number needed)
```

### 🔐 Add SSL with Internal CA (Enterprise)
```bash
# If your company has an internal Certificate Authority
# Request certificate from IT department, then:

sudo tee /etc/nginx/sites-available/afga <<EOF
server {
    listen 443 ssl http2;
    server_name afga.company.local;

    ssl_certificate /etc/ssl/certs/afga.company.local.crt;
    ssl_certificate_key /etc/ssl/private/afga.company.local.key;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}

server {
    listen 80;
    server_name afga.company.local;
    return 301 https://\$server_name\$request_uri;
}
EOF
```

**Final Access:**
- `https://afga.company.local` (with company SSL certificate)

### 📊 Monitoring and Maintenance
```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
sudo systemctl restart afga

# Update application
cd /opt/afga
git pull
docker build -t afga-backend:latest -f deployment/docker/Dockerfile.backend .
docker build -t afga-frontend:latest -f deployment/docker/Dockerfile.frontend .
sudo systemctl restart afga

# Backup database
sudo cp /opt/afga/data/afga.db /opt/afga/backups/afga-$(date +%Y%m%d).db
```

### 💾 Backup Strategy
```bash
# Create backup script
sudo tee /opt/afga/backup.sh <<EOF
#!/bin/bash
BACKUP_DIR=/opt/afga/backups
mkdir -p \$BACKUP_DIR
docker-compose -f /opt/afga/docker-compose.prod.yml exec -T backend \
  sqlite3 /app/data/afga.db ".backup /app/data/backup-\$(date +%Y%m%d-%H%M%S).db"
find \$BACKUP_DIR -name "backup-*.db" -mtime +30 -delete
EOF

sudo chmod +x /opt/afga/backup.sh

# Add cron job (daily at 2 AM)
echo "0 2 * * * /opt/afga/backup.sh" | sudo crontab -
```

---

## 📊 Access Method Comparison

| Deployment Type | URL Example | SSL | Public Access | Internal Only | Custom Domain |
|----------------|-------------|-----|---------------|---------------|---------------|
| **Local Development** | `http://localhost:8501` | ❌ | ❌ | ✅ | ❌ |
| **Azure App Service** | `https://afga.azurewebsites.net` | ✅ | ✅ | ⚙️ (VNet) | ✅ |
| **Azure ACI** | `http://afga.westeurope.azurecontainer.io:8501` | ❌ | ✅ | ⚙️ (VNet) | ⚙️ |
| **Azure VM** | `http://afga-vm.westeurope.cloudapp.azure.com:8501` | ⚙️ | ✅ | ⚙️ (VNet) | ✅ |
| **On-Premises** | `https://afga.company.local` | ⚙️ (Internal CA) | ❌ | ✅ | ✅ |
| **AKS (Current)** | `http://40.123.45.67:8501` | ⚙️ (Ingress) | ✅ | ⚙️ (Private) | ✅ |

**Legend:**
- ✅ = Built-in / Easy
- ⚙️ = Requires configuration
- ❌ = Not available

---

## 💡 Recommendations by Use Case

### 🏢 Small Finance Team (5-20 users)
**→ Azure App Service**
- **Why:** Managed SSL, easy deployment, $50-100/month
- **Access:** `https://afga-finance.azurewebsites.net`
- **Setup Time:** 30 minutes

### 🏭 Department Deployment (20-100 users)
**→ Azure App Service + VNet**
- **Why:** Secure internal access, scales automatically
- **Access:** `https://finance-governance.company.com` (internal only)
- **Setup Time:** 1-2 hours

### 🏛️ Enterprise with Existing Infrastructure
**→ On-Premises VM**
- **Why:** Use existing hardware, no cloud costs, full control
- **Access:** `https://afga.company.local`
- **Setup Time:** 2-3 hours

### 🚀 Multi-Tenant SaaS Product
**→ AKS (Current Setup)**
- **Why:** Microservices, auto-scaling, multi-region
- **Access:** `https://app.yourcompany.com`
- **Setup Time:** 4-6 hours

---

## 🔄 Migration Between Options

### From AKS → App Service
```bash
# Use same Docker images
az webapp create \
  --resource-group rg-afga \
  --plan afga-plan \
  --name afga-app \
  --deployment-container-image-name afgaacr.azurecr.io/afga-frontend:latest

# Export database from AKS pod
kubectl cp afga-prod/backend-pod:/app/data/afga.db ./afga.db

# Upload to App Service
az webapp deployment source config-zip \
  --resource-group rg-afga \
  --name afga-app \
  --src afga.zip
```

### From Cloud → On-Premises
```bash
# Export database from cloud
az webapp ssh --resource-group rg-afga --name afga-backend
# > sqlite3 /app/data/afga.db ".backup /tmp/afga.db"

# Download to local
az webapp download --resource-group rg-afga --name afga-backend

# Transfer to on-prem server
scp afga.db admin@afga-server:/opt/afga/data/
```

---

## 🆘 Troubleshooting

### App Service: Container Won't Start
```bash
# Check logs
az webapp log tail --name afga-backend --resource-group rg-afga

# Common fix: Increase memory
az appservice plan update \
  --name afga-plan \
  --resource-group rg-afga \
  --sku B3
```

### On-Premises: Can't Access from Other Machines
```bash
# Check firewall
sudo ufw status
sudo ufw allow 8501/tcp
sudo ufw allow 8000/tcp

# Check if service is listening
sudo netstat -tulpn | grep -E '8501|8000'

# Check Docker network
docker network inspect afga_afga-network
```

### SSL Certificate Issues
```bash
# For Let's Encrypt renewal
sudo certbot renew --dry-run

# For internal CA, check certificate expiry
openssl x509 -in /etc/ssl/certs/afga.crt -noout -dates
```

---

## 📞 Support

Need help choosing the right deployment option? Contact your IT department or open an issue in the repository.