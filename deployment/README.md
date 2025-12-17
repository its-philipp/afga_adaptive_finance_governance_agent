# 🚀 AFGA Deployment Guide

Three deployment options available: Docker Compose (local), Kubernetes (self-managed), or Helm/AKS (production).

## 📋 Prerequisites

- Python 3.11+
- Docker 24+ (for container deployments)
- kubectl (for Kubernetes)
- Helm 3+ (for AKS production deployment)
- Azure CLI (for AKS only)

## 🐳 Option 1: Docker Compose (Local Development)

Simplest way to run both services locally.

```bash
# Build and start
docker-compose up -d

# Access
# Frontend: http://localhost:8501
# Backend: http://localhost:8000

# Stop
docker-compose down
```

**Pros:** Quick setup, no K8s required  
**Cons:** Not production-ready, no scaling  
**Cost:** $0 (local only)

## ☸️ Option 2: Kubernetes (Self-Managed)

Deploy to any Kubernetes cluster (minikube, kind, on-prem, cloud).

```bash
# Deploy all resources
kubectl apply -f kubernetes/

# Check status
kubectl get pods -n afga
kubectl get svc -n afga

# Access frontend
kubectl port-forward -n afga svc/afga-frontend 8501:8501

# View logs
kubectl logs -n afga -l app=afga-backend --tail=50
```

## ☁️ Option 3: Azure Kubernetes Service (Production)

This is the recommended approach for production environments. It uses **Terraform** to provision the infrastructure and **Helm** to deploy the application.

### 1. Provision Infrastructure
Use Terraform to create the AKS cluster, Azure Container Registry, and Key Vault.
[Go to Terraform Guide](./terraform/README.md)

### 2. Deploy Application
Use Helm to deploy the application to the provisioned cluster.
[Go to Helm Guide](./helm/README.md)

**Pros:** Production-grade, portable across clouds  
**Cons:** Manual K8s cluster management  
**Cost:** ~$60/month (AKS Basic) or $0 (local minikube)

See [kubernetes/KUBERNETES_GUIDE.md](./kubernetes/KUBERNETES_GUIDE.md) for details.

## 🎯 Option 3: Helm + AKS (Production)

Enterprise-ready deployment with Azure Key Vault, Istio service mesh, and autoscaling.

```bash
# 1. Create AKS cluster
az aks create \
  --resource-group afga-rg \
  --name afga-cluster \
  --node-count 2 \
  --enable-addons azure-keyvault-secrets-provider \
  --generate-ssh-keys

# 2. Get credentials
az aks get-credentials --resource-group afga-rg --name afga-cluster

# 3. Install Helm chart
helm install afga ./helm/afga-agent \
  -f ./helm/overlays/prod/values.yaml \
  --namespace afga \
  --create-namespace

# 4. Check deployment
helm status afga -n afga
kubectl get pods -n afga
```

**Pros:** Full observability, autoscaling, secrets management, service mesh  
**Cons:** Most complex, requires Azure  
**Cost:** ~$200-400/month (2-node AKS + addons)

See [helm/README.md](./helm/README.md) for complete guide.

## 📊 Comparison Table

| Feature | Docker Compose | Kubernetes | Helm/AKS |
|---------|----------------|------------|----------|
| **Setup Time** | 5 min | 15 min | 30 min |
| **Scaling** | No | Yes | Auto |
| **HA** | No | Yes | Yes |
| **Secrets Mgmt** | .env file | K8s secrets | Azure Key Vault |
| **Monitoring** | Logs only | kubectl/logs | Istio + Grafana |
| **Cost** | $0 | $60-150/mo | $200-400/mo |
| **Production Ready** | ❌ | ✅ | ✅ |

## 🗂️ Deployment Structure

```
deployment/
├── README.md                    # This file
├── docker/
│   ├── Dockerfile.backend       # Backend container image
│   ├── Dockerfile.frontend      # Frontend container image
│   └── docker-compose.yml       # Local multi-container setup
├── kubernetes/
│   ├── KUBERNETES_GUIDE.md      # K8s deployment details
│   ├── namespace.yaml           # afga namespace
│   ├── persistent-volume.yaml   # 5GB PVC for SQLite
│   ├── backend-deployment.yaml  # FastAPI deployment (2 replicas)
│   ├── frontend-deployment.yaml # Streamlit deployment (2 replicas)
│   └── ingress.yaml             # Ingress controller config
└── helm/
    ├── README.md                # Helm/AKS complete guide
    └── afga-agent/
        ├── Chart.yaml           # Helm chart metadata
        ├── values.yaml          # Default configuration
        ├── templates/           # K8s resource templates
        └── overlays/
            ├── dev/             # Development values
            └── prod/            # Production values
```

## 🔐 Secrets Management

### Docker Compose
```bash
# Use .env file in project root
cp .env.example .env
# Edit .env with your API keys
```

### Kubernetes
```bash
# Create secret from .env file
kubectl create secret generic afga-secrets \
  --from-env-file=.env \
  --namespace=afga
```

### Helm/AKS
```bash
# Use Azure Key Vault (recommended)
# See helm/README.md for setup
```

## 📈 Cost Optimization Tips

1. **Databricks Disabled:** Already saving $100-135/month by using local SQLite
2. **AKS Node Size:** Use Standard_B2s ($30/mo) for dev, Standard_D2s_v3 ($70/mo) for prod
3. **Autoscaling:** Set minReplicas=1 to reduce idle costs
4. **Spot Instances:** Save 60-80% with AKS spot node pools
5. **Dev/Prod Split:** Use docker-compose for dev, AKS for prod only

## 🧪 Testing Deployments

### Docker Compose
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Kubernetes
```bash
kubectl exec -n afga deploy/afga-backend -- curl localhost:8000/health
```

### Helm/AKS
```bash
EXTERNAL_IP=$(kubectl get svc -n afga afga-frontend -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP:8501
```

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check logs
kubectl logs -n afga -l app=afga-backend --tail=100

# Common issue: Missing .env variables
kubectl describe secret afga-secrets -n afga
```

### Frontend can't reach backend
```bash
# Verify service exists
kubectl get svc -n afga afga-backend

# Check connectivity
kubectl exec -n afga deploy/afga-frontend -- curl afga-backend:8000/health
```

### PVC not mounting
```bash
# Check PVC status
kubectl get pvc -n afga

# Describe for events
kubectl describe pvc afga-data -n afga
```

## 📚 Next Steps

1. **Choose deployment option** based on your needs
2. **Follow specific guide** in kubernetes/ or helm/ folders
3. **Configure secrets** using appropriate method
4. **Deploy and verify** health endpoints
5. **Set up monitoring** (optional, see helm guide)

## 🔗 Related Documentation

- [Main README](../README.md) - Project overview
- [Quick Start](../QUICKSTART.md) - Local development setup
- [Architecture](../docs/ARCHITECTURE.md) - System design
- [API Docs](http://localhost:8000/docs) - Interactive API reference

---

**Need help?** Open an issue or check the troubleshooting sections in the specific deployment guides.
