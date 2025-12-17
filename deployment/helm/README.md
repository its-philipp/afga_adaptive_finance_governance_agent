# AFGA Helm Chart Deployment

## Overview

This Helm chart deploys the Adaptive Finance Governance Agent (AFGA) on Kubernetes. It supports:

- **Microservices Architecture**: Separate deployments for Backend (FastAPI) and Frontend (Streamlit).
- **Persistence**: Persistent Volume Claim (PVC) for the SQLite database.
- **Security**: Azure Key Vault integration via Secrets Store CSI Driver.
- **Scalability**: Horizontal Pod Autoscaling (HPA) configured.
- **Service Mesh**: Optional Istio integration.

## Prerequisites

1. **Infrastructure**
   If you don't have an AKS cluster, use the included Terraform scripts to provision one:
   ```bash
   cd ../terraform
   terraform init && terraform apply
   # Run the connect command output by terraform
   ```

2. **AKS Cluster** with:
   - Kubernetes 1.28+
   - Azure CNI networking
   - Azure Key Vault CSI driver installed
   - (Optional) Istio service mesh

3. **Azure Container Registry (ACR)**

4. **Helm 3.x** installed

## Quick Deploy

### 1. Build and Push Images

**Note:** For Apple Silicon (M1/M2/M3) users, ensure you build for `linux/amd64`.

```bash
# Set variables
export ACR_NAME="<your-acr-name>"
export ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

# Login to ACR
az acr login -n "$ACR_NAME"

# Build images from project root
docker build -t "$ACR_LOGIN_SERVER/afga-backend:latest" -f k8s/Dockerfile.backend .
docker build -t "$ACR_LOGIN_SERVER/afga-frontend:latest" -f k8s/Dockerfile.frontend .

# Push images
docker push "$ACR_LOGIN_SERVER/afga-backend:latest"
docker push "$ACR_LOGIN_SERVER/afga-frontend:latest"
```

### 2. Create Azure Key Vault Secrets

```bash
export RESOURCE_GROUP="rg-afga-prod"
export KEY_VAULT_NAME="afga-prod-kv"
export LOCATION="westeurope"

# Create Key Vault
az keyvault create \
  -n "$KEY_VAULT_NAME" \
  -g "$RESOURCE_GROUP" \
  -l "$LOCATION" \
  --enable-rbac-authorization false

# Add secrets from your .env file
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "openrouter-api-key" --value "<YOUR_KEY>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "openai-api-key" --value "<YOUR_KEY>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "google-api-key" --value "<YOUR_KEY>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "a2a-api-key" --value "<YOUR_KEY>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "langfuse-public-key" --value "<YOUR_KEY>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "langfuse-secret-key" --value "<YOUR_KEY>"
```

### 3. Install Azure Key Vault CSI Driver

```bash
# Add Helm repo
helm repo add csi-secrets-store-provider-azure https://azure.github.io/secrets-store-csi-driver-provider-azure/charts
helm repo update

# Install CSI driver
helm install csi-secrets-store-provider-azure/csi-secrets-store-provider-azure \
  --generate-name \
  --namespace kube-system
```

### 4. Update Helm Values

Edit `azure_extension/aks/overlays/prod/values.yaml`:

```yaml
backend:
  image:
    repository: <YOUR_ACR>.azurecr.io/afga-backend
    tag: "latest"

frontend:
  image:
    repository: <YOUR_ACR>.azurecr.io/afga-frontend
    tag: "latest"

keyVaultSecrets:
  enabled: true
  vaultName: "afga-prod-kv"
  tenantId: "<YOUR_TENANT_ID>"

ingress:
  enabled: true
  hosts:
    - host: afga.yourdomain.com
```

### 5. Deploy with Helm

```bash
cd azure_extension/aks

# Dev environment
helm install afga-dev helm/afga-agent \
  -f overlays/dev/values.yaml \
  --namespace afga-dev \
  --create-namespace

# Production environment
helm install afga-prod helm/afga-agent \
  -f overlays/prod/values.yaml \
  --namespace afga-prod \
  --create-namespace
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n afga-prod

# Check services
kubectl get svc -n afga-prod

# Get frontend external IP
kubectl get svc afga-agent-frontend -n afga-prod

# Check logs
kubectl logs -f deployment/afga-agent-backend -n afga-prod
kubectl logs -f deployment/afga-agent-frontend -n afga-prod
```

## Accessing the Application

```bash
# Get frontend LoadBalancer IP
FRONTEND_IP=$(kubectl get svc afga-agent-frontend -n afga-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Frontend: http://$FRONTEND_IP:8501"
echo "Backend: http://afga-agent-backend:8000 (internal only)"
```

## Scaling

```bash
# Manual scaling
kubectl scale deployment/afga-agent-backend -n afga-prod --replicas=5

# Check HPA status
kubectl get hpa -n afga-prod
```

## Upgrade Deployment

```bash
# Build new images with version tag
docker build -t "$ACR_LOGIN_SERVER/afga-backend:v1.1.0" -f k8s/Dockerfile.backend .
docker push "$ACR_LOGIN_SERVER/afga-backend:v1.1.0"

# Upgrade Helm release
helm upgrade afga-prod helm/afga-agent \
  -f overlays/prod/values.yaml \
  --namespace afga-prod \
  --set backend.image.tag=v1.1.0
```

## Rollback

```bash
# View history
helm history afga-prod -n afga-prod

# Rollback to previous version
helm rollback afga-prod -n afga-prod
```

## Uninstall

```bash
helm uninstall afga-prod -n afga-prod
kubectl delete namespace afga-prod
```

## Cost Estimate (Production)

With the updated Helm chart (Databricks disabled):

- **AKS cluster** (3 nodes, Standard_D2s_v3): ~$180/month
- **Azure Container Registry** (Standard): ~$20/month
- **Azure Key Vault**: ~$3/month
- **Load Balancer**: ~$20/month
- **Persistent Disk** (5GB): ~$0.50/month

**Total: ~$223/month** (vs ~$400/month with Databricks)

## Optional: Istio Service Mesh

If you want Istio for advanced traffic management:

```bash
# Install Istio
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update

helm install istio-base istio/base -n istio-system --create-namespace
helm install istiod istio/istiod -n istio-system --wait

# Enable Istio in Helm values
ingress:
  enabled: true
  className: "istio"

istio:
  enabled: true
```

## Troubleshooting

**Pods not starting:**
```bash
kubectl describe pod <POD_NAME> -n afga-prod
kubectl logs <POD_NAME> -n afga-prod
```

**CSI driver issues:**
```bash
kubectl get secretproviderclass -n afga-prod
kubectl get secretproviderclasspodstatus -n afga-prod
```

**Key Vault access denied:**
```bash
# Grant managed identity access to Key Vault
az keyvault set-policy \
  --name "$KEY_VAULT_NAME" \
  --object-id "<MANAGED_IDENTITY_OBJECT_ID>" \
  --secret-permissions get list
```

**Database persistence issues:**
```bash
# Check PVC
kubectl get pvc -n afga-prod
kubectl describe pvc afga-agent-data -n afga-prod

# Access pod to check data
kubectl exec -it <BACKEND_POD> -n afga-prod -- ls -la /app/data
```
