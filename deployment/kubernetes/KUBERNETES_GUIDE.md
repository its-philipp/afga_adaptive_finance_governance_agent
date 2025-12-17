# Adaptive Finance Governance Agent - AKS Deployment

This guide shows how to deploy AFGA to Azure Kubernetes Service (AKS) **without Databricks**, saving costs while keeping all core functionality.

## What Works Without Databricks

✅ **Core Features (100% functional):**
- Invoice submission and processing
- Multi-agent decision-making (TAA, PAA, EMA)
- Risk assessment and classification
- HITL feedback workflow
- Adaptive memory and exception rules
- Policy management
- Classifications dashboard
- All agent trails and audit logs
- Local SQLite database with full history

❌ **Disabled Features:**
- Embeddings Browser page (shows "Databricks unavailable" message)
- Semantic similarity search in Transaction Review (gracefully degrades)
- Azure Blob Storage uploads (not needed without Databricks)

## Cost Savings

**Before (with Databricks):**
- Databricks SQL Warehouse: ~$0.22/hour (~$160/month if running 24/7)
- ADLS Gen2 Storage: ~$0.02/GB/month
- **Total**: ~$165-200/month

**After (AKS only):**
- AKS cluster (2 nodes, Standard_B2s): ~$60/month
- Azure Container Registry: ~$5/month
- **Total**: ~$65/month

**Savings: ~$100-135/month (60-70% reduction)**

## Prerequisites

1. Azure subscription
2. Azure CLI installed: `az --version`
3. Docker installed: `docker --version`
4. kubectl installed: `kubectl version --client`

## Step 1: Create Azure Resources

```bash
# Variables
export RESOURCE_GROUP="rg-afga-aks"
export LOCATION="westeurope"
export ACR_NAME="afgaacr$RANDOM"  # Must be globally unique
export AKS_NAME="afga-cluster"

# Login and set subscription
az login
az account set -s "<YOUR_SUBSCRIPTION_ID>"

# Create resource group
az group create -n "$RESOURCE_GROUP" -l "$LOCATION"

# Create Azure Container Registry (ACR)
az acr create \
  -n "$ACR_NAME" \
  -g "$RESOURCE_GROUP" \
  --sku Basic \
  --admin-enabled true

# Create AKS cluster (2 nodes, cost-optimized)
az aks create \
  -n "$AKS_NAME" \
  -g "$RESOURCE_GROUP" \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --attach-acr "$ACR_NAME" \
  --generate-ssh-keys \
  --enable-managed-identity

# Get AKS credentials
az aks get-credentials -n "$AKS_NAME" -g "$RESOURCE_GROUP"

# Verify connection
kubectl get nodes
```

## Step 2: Build and Push Docker Images

```bash
# Get ACR login server
export ACR_LOGIN_SERVER=$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)

# Build backend image
docker build -t "$ACR_LOGIN_SERVER/afga-backend:latest" -f k8s/Dockerfile.backend .

# Build frontend image
docker build -t "$ACR_LOGIN_SERVER/afga-frontend:latest" -f k8s/Dockerfile.frontend .

# Login to ACR
az acr login -n "$ACR_NAME"

# Push images
docker push "$ACR_LOGIN_SERVER/afga-backend:latest"
docker push "$ACR_LOGIN_SERVER/afga-frontend:latest"
```

## Step 3: Create Kubernetes Secrets

```bash
# Create secrets from .env file (with Databricks commented out)
kubectl create secret generic afga-secrets \
  --from-literal=OPENROUTER_API_KEY="<YOUR_KEY>" \
  --from-literal=PRIMARY_MODEL="openai/gpt-4o-mini" \
  --from-literal=LANGFUSE_PUBLIC_KEY="<YOUR_KEY>" \
  --from-literal=LANGFUSE_SECRET_KEY="<YOUR_KEY>" \
  --from-literal=LANGFUSE_HOST="https://cloud.langfuse.com" \
  --from-literal=GOOGLE_API_KEY="<YOUR_KEY>" \
  --from-literal=OPENAI_API_KEY="<YOUR_KEY>"
```

## Step 4: Deploy to AKS

```bash
# Update image names in k8s manifests
sed -i "s|IMAGE_PLACEHOLDER|$ACR_LOGIN_SERVER|g" k8s/*.yaml

# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/persistent-volume.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n afga
kubectl get svc -n afga
```

## Step 5: Access Application

```bash
# Get external IP (may take 2-3 minutes)
kubectl get svc afga-frontend -n afga -w

# Once EXTERNAL-IP appears:
# Frontend: http://<EXTERNAL-IP>:8501
# Backend: http://<EXTERNAL-IP>:8000
```

## Optional: Setup Custom Domain with Ingress

```bash
# Install nginx ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Update k8s/ingress.yaml with your domain
# Apply:
kubectl apply -f k8s/ingress.yaml

# Configure DNS A record to point to ingress external IP
kubectl get svc -n ingress-nginx
```

## Monitoring and Logs

```bash
# View backend logs
kubectl logs -f deployment/afga-backend -n afga

# View frontend logs
kubectl logs -f deployment/afga-frontend -n afga

# Check pod status
kubectl describe pod <POD_NAME> -n afga

# Restart deployments
kubectl rollout restart deployment/afga-backend -n afga
kubectl rollout restart deployment/afga-frontend -n afga
```

## Scaling

```bash
# Scale backend replicas
kubectl scale deployment/afga-backend -n afga --replicas=3

# Scale frontend replicas
kubectl scale deployment/afga-frontend -n afga --replicas=2

# Autoscale based on CPU
kubectl autoscale deployment afga-backend -n afga \
  --cpu-percent=70 --min=2 --max=5
```

## Backup SQLite Database

```bash
# Copy database from pod to local
POD_NAME=$(kubectl get pods -n afga -l app=afga-backend -o jsonpath='{.items[0].metadata.name}')
kubectl cp afga/$POD_NAME:/app/data/memory.db ./memory-backup.db

# Restore database to pod
kubectl cp ./memory-backup.db afga/$POD_NAME:/app/data/memory.db
```

## Cost Optimization

**Reduce costs further:**

1. **Use spot instances** (50-90% discount):
   ```bash
   az aks nodepool add \
     -n spotpool \
     --cluster-name "$AKS_NAME" \
     -g "$RESOURCE_GROUP" \
     --priority Spot \
     --eviction-policy Delete \
     --spot-max-price -1 \
     --node-count 2 \
     --node-vm-size Standard_B2s
   ```

2. **Stop cluster when not in use**:
   ```bash
   az aks stop -n "$AKS_NAME" -g "$RESOURCE_GROUP"
   az aks start -n "$AKS_NAME" -g "$RESOURCE_GROUP"
   ```

3. **Use Azure Container Instances (ACI)** for even lower costs:
   - No node management
   - Pay only when running
   - ~$20-30/month for 2 containers

## Cleanup

```bash
# Delete AKS cluster (keeps ACR)
az aks delete -n "$AKS_NAME" -g "$RESOURCE_GROUP" --yes --no-wait

# Delete entire resource group (removes everything)
az group delete -n "$RESOURCE_GROUP" --yes --no-wait
```

## Re-enabling Databricks Later

If you want to re-enable Databricks:

1. Uncomment Databricks env vars in `.env`
2. Update Kubernetes secret:
   ```bash
   kubectl create secret generic afga-secrets \
     --from-env-file=.env \
     --dry-run=client -o yaml | kubectl apply -f -
   ```
3. Restart deployments:
   ```bash
   kubectl rollout restart deployment/afga-backend -n afga
   kubectl rollout restart deployment/afga-frontend -n afga
   ```

## Next Steps

- [ ] Set up CI/CD with GitHub Actions
- [ ] Configure Azure Monitor for metrics
- [ ] Add SSL/TLS with cert-manager
- [ ] Implement Azure AD authentication
- [ ] Set up Azure Key Vault for secrets
