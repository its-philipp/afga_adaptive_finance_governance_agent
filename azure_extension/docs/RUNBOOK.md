# Runbook: Azure Extension Deployment and Operations

## Prerequisites

- Azure subscription with appropriate permissions
- Terraform >= 1.0
- Helm >= 3.0
- kubectl configured for AKS cluster
- ArgoCD CLI (optional, for GitOps management)

## Initial Setup

### 1. Configure Terraform Backend

Edit `azure_extension/infra/terraform/envs/dev/main.tf` (and staging/prod) to configure remote state:

```hcl
backend "azurerm" {
  resource_group_name  = "tfstate-rg"
  storage_account_name = "tfstatestorage"
  container_name       = "tfstate"
  key                  = "adaptive-finance-governance-rag/dev/terraform.tfstate"
}
```

### 2. Set Environment Variables

```bash
export ARM_SUBSCRIPTION_ID="<subscription-id>"
export ARM_TENANT_ID="<tenant-id>"
export ARM_CLIENT_ID="<service-principal-id>"
export ARM_CLIENT_SECRET="<service-principal-secret>"
```

### 3. Provision Infrastructure

```bash
cd azure_extension/infra/terraform/envs/dev
terraform init
terraform plan
terraform apply
```

Save outputs:
```bash
terraform output -json > ../../outputs/dev.json
```

### 4. Configure Key Vault Secrets

```bash
# Set secrets in Key Vault
az keyvault secret set --vault-name kv-dev-adaptive-finance-governance --name openai-api-key --value "<openai-key>"
az keyvault secret set --vault-name kv-dev-adaptive-finance-governance --name weaviate-api-key --value "<weaviate-key>"
az keyvault secret set --vault-name kv-dev-adaptive-finance-governance --name langfuse-public-key --value "<langfuse-key>"
az keyvault secret set --vault-name kv-dev-adaptive-finance-governance --name langfuse-secret-key --value "<langfuse-secret>"
```

### 5. Build and Push Docker Image

```bash
# Build image
docker build -t adaptive-finance-governance-agent:latest .

# Tag for ACR
docker tag adaptive-finance-governance-agent:latest <ACR_NAME>.azurecr.io/adaptive-finance-governance-agent:latest

# Push to ACR
az acr login --name <ACR_NAME>
docker push <ACR_NAME>.azurecr.io/adaptive-finance-governance-agent:latest
```

### 6. Deploy via Helm

```bash
# Update values.yaml with ACR name and Key Vault details
# Then deploy:
helm install afga-agent ./azure_extension/aks/helm/afga-agent \
  --namespace afga-agent-dev \
  --create-namespace \
  -f ./azure_extension/aks/overlays/dev/values.yaml \
  --set image.repository=<ACR_NAME>.azurecr.io/adaptive-finance-governance-agent \
  --set keyVaultSecrets.vaultName=kv-dev-adaptive-finance-governance \
  --set serviceAccount.annotations."azure\.workload\.identity/client-id"=<workload-identity-client-id>
```

### 7. Configure ArgoCD (Optional)

```bash
# Apply ArgoCD Application
kubectl apply -f azure_extension/ops/argocd/app-of-apps.yaml

# Sync manually
argocd app sync adaptive-finance-governance-rag-apps
```

## Databricks Setup

### 1. Create Unity Catalog

```bash
# Connect to Databricks workspace
databricks configure --token

# Run Unity Catalog setup
databricks workspace import azure_extension/databricks/unity_catalog/catalogs.sql /catalogs.sql
databricks workspace import azure_extension/databricks/unity_catalog/schemas.sql /schemas.sql
databricks workspace import azure_extension/databricks/unity_catalog/grants.sql /grants.sql
```

### 2. Upload Notebooks

```bash
databricks workspace import azure_extension/databricks/notebooks/01_ingest_raw.py /notebooks/01_ingest_raw --language PYTHON
databricks workspace import azure_extension/databricks/notebooks/02_validate_transform.py /notebooks/02_validate_transform --language PYTHON
databricks workspace import azure_extension/databricks/notebooks/03_chunk_embed_register.py /notebooks/03_chunk_embed_register --language PYTHON
```

### 3. Create Databricks Job

```bash
databricks jobs create --json-file azure_extension/databricks/jobs/pipeline_job.json
```

Note: Update job JSON with actual variable values before creating.

## Operations

### Monitoring

#### Check Pod Status
```bash
kubectl get pods -n afga-agent-dev
kubectl logs -f deployment/afga-agent -n afga-agent-dev
```

#### Check HPA
```bash
kubectl get hpa -n afga-agent-dev
```

#### Check Istio Gateway
```bash
kubectl get gateway -n afga-agent-dev
kubectl get virtualservice -n afga-agent-dev
```

### Scaling

#### Manual Scaling
```bash
kubectl scale deployment afga-agent --replicas=5 -n afga-agent-dev
```

#### Update HPA
```bash
kubectl edit hpa afga-agent -n afga-agent-dev
```

### Troubleshooting

#### Pod Failing to Start
1. Check logs: `kubectl logs <pod-name> -n afga-agent-dev`
2. Check events: `kubectl describe pod <pod-name> -n afga-agent-dev`
3. Verify secrets: `kubectl get secret -n afga-agent-dev`
4. Check Key Vault access: Verify workload identity is configured correctly

#### Databricks Job Failing
1. Check job runs: `databricks runs list --job-id <job-id>`
2. Check logs: `databricks runs get-output --run-id <run-id>`
3. Verify ADLS access: Check service principal permissions

#### Retrieval Issues
1. Check Weaviate connectivity (if using local mode)
2. Verify Databricks Vector Search index exists (if using cloud mode)
3. Check retrieval adapter configuration in code

### Updates

#### Update Application
```bash
# Build new image
docker build -t adaptive-finance-governance-agent:v0.2.0 .
docker tag adaptive-finance-governance-agent:v0.2.0 <ACR_NAME>.azurecr.io/adaptive-finance-governance-agent:v0.2.0
docker push <ACR_NAME>.azurecr.io/adaptive-finance-governance-agent:v0.2.0

# Update Helm
helm upgrade afga-agent ./azure_extension/aks/helm/afga-agent \
  --namespace afga-agent-dev \
  --set image.tag=v0.2.0
```

#### Update Infrastructure
```bash
cd azure_extension/infra/terraform/envs/dev
terraform plan
terraform apply
```

## Backup and Recovery

### Key Vault Secrets
```bash
# Backup secrets
az keyvault secret backup --vault-name kv-dev-adaptive-finance-governance --id "<secret-id>" --file backup.json
```

### Databricks Data
- Delta tables are versioned automatically
- Use Databricks backup for Unity Catalog metadata

## Security Best Practices

1. **Rotate Secrets Regularly**: Use `ops/scripts/rotate_keys.sh`
2. **Enable Private Endpoints**: Phase 2 deployment
3. **Enforce mTLS**: Set `istio.destinationRule.mTLS.mode: STRICT` in production
4. **Audit Logs**: Enable Azure Monitor and Log Analytics
5. **RBAC**: Use least-privilege access for service principals

## Cost Optimization

1. **HPA**: Configure appropriate min/max replicas
2. **Databricks**: Use job clusters (terminate when not in use)
3. **Storage**: Enable lifecycle policies for ADLS Gen2
4. **Monitoring**: Set up alerts for unexpected scaling

