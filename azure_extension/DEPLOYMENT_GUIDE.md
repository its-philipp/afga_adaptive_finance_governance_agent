# Azure Extension - Deployment Guide

## Deployment Options

This guide provides multiple deployment paths based on your budget and requirements.

## 🆓 Option 1: Minimal Cost Setup (Recommended for Development)

**Monthly Cost**: ~$5-10  
**What's included**: ADLS Gen2, Key Vault, ACR  
**What's excluded**: AKS, Databricks

### Current Status (Already Deployed ✅)
- ✅ ADLS Gen2 Storage: `trustedaidevsa251031`
- ✅ Key Vault: `kv-dev-afga`
- ✅ Azure Container Registry: `acrdevafga`
- ✅ Docker image pushed to ACR
- ✅ Cloud mode ingestion working

### Running Locally with Cloud Storage

```bash
# Run backend with cloud storage
export CLOUD_MODE=databricks
export AZURE_STORAGE_ACCOUNT=trustedaidevsa251031
export AZURE_STORAGE_CONTAINER=raw
export AZURE_USE_MANAGED_IDENTITY=true

# Start services
docker-compose -f docker/docker-compose.yml up -d weaviate
uvicorn src.api.main:app --reload

# Uploads go to Azure, retrieval from local Weaviate
```

**Benefits**:
- ✅ Test cloud ingestion without AKS costs
- ✅ Verify ADLS Gen2 integration
- ✅ Develop and iterate quickly
- ✅ Pay-as-you-go for storage only (~pennies)

---

## 💰 Option 2: Add Databricks (Moderate Cost)

**Additional Monthly Cost**: ~$10-50  
**What's added**: Databricks workspace, Unity Catalog, ELT pipeline

### Setup Steps

See [databricks/SETUP.md](databricks/SETUP.md) for detailed instructions.

**Quick summary**:
1. Create Databricks workspace (Azure Portal)
2. Upload notebooks via Databricks CLI
3. Create Unity Catalog structure
4. Configure job for ELT pipeline
5. Grant storage access to Databricks

**Cost optimization**:
- Use job clusters (auto-terminate)
- Single-node cluster for dev
- 10-minute auto-termination
- Only run when testing

---

## 💎 Option 3: Full Azure-Native (Production-Ready)

**Additional Monthly Cost**: ~$70-150  
**What's added**: AKS cluster, Istio, full Kubernetes deployment

### Prerequisites
- All from Option 1 ✅
- Optionally Option 2 (Databricks)

### Step 1: Deploy AKS Infrastructure

```bash
cd azure_extension/infra/terraform/envs/dev

# Review what will be created
terraform plan

# Apply (creates AKS cluster - takes 10-15 minutes)
terraform apply
```

**What gets created**:
- AKS cluster (2 nodes, auto-scaling 1-5)
- Log Analytics workspace
- Workload Identity for pods
- RBAC permissions (ACR pull, Key Vault access, Storage access)

### Step 2: Configure kubectl

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group adaptive-finance-governance-rag-dev-rg \
  --name adaptive-finance-governance-rag-dev-aks

# Verify connection
kubectl get nodes
```

### Step 3: Install Istio (Service Mesh)

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install Istio
istioctl install --set profile=demo -y

# Enable Istio injection for namespace
kubectl create namespace afga-agent-dev
kubectl label namespace afga-agent-dev istio-injection=enabled
```

### Step 4: Install Key Vault CSI Driver

```bash
# Add Helm repo
helm repo add csi-secrets-store-provider-azure \
  https://azure.github.io/secrets-store-csi-driver-provider-azure/charts

# Install CSI driver
helm install csi csi-secrets-store-provider-azure/csi-secrets-store-provider-azure \
  --namespace kube-system
```

### Step 5: Deploy Application with Helm

```bash
cd azure_extension/aks

# Update values with your workload identity
WORKLOAD_IDENTITY_CLIENT_ID=$(cd ../../infra/terraform/envs/dev && terraform output -raw aks_workload_identity_client_id)

# Deploy
helm install afga-agent helm/afga-agent \
  --namespace afga-agent-dev \
  --create-namespace \
  -f overlays/dev/values.yaml \
  --set image.repository=acrdevafga.azurecr.io/adaptive-finance-governance-agent \
  --set image.tag=v0.1.0 \
  --set keyVaultSecrets.vaultName=kv-dev-afga \
  --set serviceAccount.annotations."azure\.workload\.identity/client-id"=$WORKLOAD_IDENTITY_CLIENT_ID
```

### Step 6: Install ArgoCD (Optional - GitOps)

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Port forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
# Username: admin
# Password: (from above command)
```

### Step 7: Configure ArgoCD Applications

```bash
# Apply app-of-apps
kubectl apply -f azure_extension/ops/argocd/app-of-apps.yaml

# ArgoCD will automatically sync and deploy your application
```

### Step 8: Access the Application

```bash
# Get Istio ingress gateway external IP
kubectl get svc istio-ingressgateway -n istio-system

# Application will be available at the external IP
# Or set up DNS/domain as needed
```

---

## 🔄 CI/CD Workflows

### GitHub Actions Workflows (Already Configured)

#### 1. Build and Push (`build-and-push.yml`)
**Triggers**: Push to main/develop, tags, pull requests  
**Actions**:
- Build Docker image
- Push to ACR with appropriate tags
- Cache layers for faster builds

**Required secrets**:
- `AZURE_CREDENTIALS` (Service Principal JSON)

#### 2. Terraform Plan (`terraform-plan.yml`)
**Triggers**: Pull requests affecting Terraform files  
**Actions**:
- Format check
- Validate configuration
- Generate plan
- Comment plan on PR

**Required secrets**:
- `ARM_CLIENT_ID`
- `ARM_CLIENT_SECRET`
- `ARM_SUBSCRIPTION_ID`
- `ARM_TENANT_ID`

#### 3. Terraform Apply (`terraform-apply.yml`)
**Triggers**: Manual workflow dispatch  
**Actions**:
- Deploy infrastructure to selected environment
- Optional auto-approve for automation

### Setting Up GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:

```bash
# Azure Credentials (for Azure login action)
AZURE_CREDENTIALS=$(az ad sp create-for-rbac \
  --name "github-actions-sp" \
  --role Contributor \
  --scopes /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb \
  --sdk-auth)
# Copy the entire JSON output

# Individual ARM credentials
ARM_CLIENT_ID=<your-service-principal-app-id>
ARM_CLIENT_SECRET=<your-service-principal-password>
ARM_SUBSCRIPTION_ID=fd6c7319-01d0-4610-9681-b82980e227fb
ARM_TENANT_ID=<your-tenant-id>
```

---

## 📊 Deployment Comparison

| Feature | Option 1 (Minimal) | Option 2 (+ Databricks) | Option 3 (Full) |
|---------|-------------------|------------------------|-----------------|
| **Cost/Month** | ~$5-10 | ~$15-60 | ~$85-160 |
| **Cloud Storage** | ✅ ADLS Gen2 | ✅ ADLS Gen2 | ✅ ADLS Gen2 |
| **Data Governance** | ❌ | ✅ Unity Catalog | ✅ Unity Catalog |
| **ELT Pipeline** | ❌ | ✅ Databricks | ✅ Databricks |
| **Container Hosting** | Local Docker | Local Docker | ✅ AKS |
| **Service Mesh** | ❌ | ❌ | ✅ Istio |
| **GitOps** | ❌ | ❌ | ✅ ArgoCD |
| **Production Ready** | ❌ | ⚠️ Partial | ✅ Yes |
| **Demo Quality** | Good | Very Good | Excellent |

## 🎯 Recommended Path

### Phase 1: Current State (✅ Complete)
- ADLS Gen2, Key Vault, ACR deployed
- Cloud mode ingestion working
- Docker image in ACR
- **Cost**: ~$5-10/month
- **Action**: Keep testing locally

### Phase 2: When Ready for Demo Prep
- Add Databricks workspace
- Upload notebooks and test pipeline
- Create Unity Catalog
- **Cost**: +$10-50/month
- **Action**: Follow databricks/SETUP.md

### Phase 3: When Ready for CTO Demo
- Deploy AKS cluster
- Install Istio and ArgoCD
- Deploy application to Kubernetes
- Full production-ready architecture
- **Cost**: +$70-100/month
- **Action**: Run terraform apply for AKS module

## 📝 Current Infrastructure Summary

```
Resource Group: adaptive-finance-governance-rag-dev-rg
├── ADLS Gen2: trustedaidevsa251031 ✅ 
│   ├── raw (uploads working)
│   ├── bronze
│   ├── silver
│   └── gold
├── Key Vault: kv-dev-afga ✅
│   ├── openai-api-key ✅
│   ├── openrouter-api-key ✅
│   └── 5 other secrets
├── ACR: acrdevafga ✅
│   ├── adaptive-finance-governance-agent:latest
│   └── adaptive-finance-governance-agent:v0.1.0
└── [AKS: Not yet created - saves ~$70-100/month]
```

**You have everything needed for cloud-enabled development without the AKS costs!**

## 💡 Working Without AKS

You can fully develop and test:
- ✅ Cloud mode uploads to Azure
- ✅ API endpoints
- ✅ Streamlit UI
- ✅ SharePoint sync
- ✅ CI/CD workflows (build/push images)
- ✅ Helm chart validation (can test locally with minikube/kind)
- ✅ Databricks pipeline development

When ready for the full demo, just run `terraform apply` to add AKS and you're production-ready!

