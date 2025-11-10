# Local Kubernetes Testing Guide

## Overview

Test your Helm charts and Kubernetes manifests locally before deploying to Azure AKS. This saves money and allows rapid iteration.

## Prerequisites

Install one of these local Kubernetes options:

### Option 1: Minikube (Recommended for Mac)
```bash
brew install minikube
minikube start --driver=docker --cpus=4 --memory=8192
```

### Option 2: Kind (Kubernetes in Docker)
```bash
brew install kind
kind create cluster --name afga-agent-dev
```

### Option 3: Docker Desktop Kubernetes
Enable Kubernetes in Docker Desktop settings.

## Testing the Helm Chart

### Step 1: Validate Helm Chart

```bash
cd azure_extension/aks

# Lint the chart
helm lint helm/afga-agent -f overlays/dev/values.yaml

# Template and review (dry-run)
helm template afga-agent helm/afga-agent \
  -f overlays/dev/values.yaml \
  --set image.repository=acrdevafga.azurecr.io/adaptive-finance-governance-agent \
  --set image.tag=v0.1.0 \
  --set keyVaultSecrets.enabled=false \
  --debug
```

### Step 2: Install to Local Cluster

```bash
# Create namespace
kubectl create namespace afga-agent-dev

# Install with simplified config (no Key Vault, no Istio for local)
helm install afga-agent helm/afga-agent \
  --namespace afga-agent-dev \
  -f overlays/dev/values.yaml \
  --set image.repository=acrdevafga.azurecr.io/adaptive-finance-governance-agent \
  --set image.tag=v0.1.0 \
  --set keyVaultSecrets.enabled=false \
  --set istio.enabled=false \
  --set autoscaling.enabled=false \
  --set replicaCount=1
```

### Step 3: Verify Deployment

```bash
# Check pods
kubectl get pods -n afga-agent-dev

# Check service
kubectl get svc -n afga-agent-dev

# Check logs
kubectl logs -f deployment/afga-agent -n afga-agent-dev
```

### Step 4: Port Forward and Test

```bash
# Forward port
kubectl port-forward svc/afga-agent 8000:8000 -n afga-agent-dev

# Test in another terminal
curl http://localhost:8000/api/v1/health
```

## Testing with Local Docker Image

If you don't want to pull from ACR:

```bash
# Build image locally
docker build -t adaptive-finance-governance-agent:local .

# For minikube: Load image into minikube
minikube image load adaptive-finance-governance-agent:local

# For kind: Load image into kind
kind load docker-image adaptive-finance-governance-agent:local --name afga-agent-dev

# Install with local image
helm install afga-agent helm/afga-agent \
  --namespace afga-agent-dev \
  -f overlays/dev/values.yaml \
  --set image.repository=adaptive-finance-governance-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set keyVaultSecrets.enabled=false \
  --set istio.enabled=false
```

## Testing Istio Locally

### Install Istio in Local Cluster

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install Istio
istioctl install --set profile=demo -y

# Enable injection
kubectl label namespace afga-agent-dev istio-injection=enabled

# Reinstall app with Istio enabled
helm upgrade afga-agent helm/afga-agent \
  --namespace afga-agent-dev \
  -f overlays/dev/values.yaml \
  --set istio.enabled=true
```

### Access via Istio Gateway

```bash
# Get ingress gateway port
kubectl get svc istio-ingressgateway -n istio-system

# Port forward
kubectl port-forward svc/istio-ingressgateway 8080:80 -n istio-system

# Access application
curl http://localhost:8080/api/v1/health
```

## Testing ArgoCD Locally

### Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ready
kubectl wait --for=condition=available \
  --timeout=600s \
  deployment/argocd-server -n argocd

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### Access ArgoCD UI

```bash
# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open browser: https://localhost:8080
# Username: admin
# Password: (from above)
```

### Create Application

```bash
# Login via CLI
argocd login localhost:8080 --username admin --password <password> --insecure

# Create app
argocd app create afga-agent-dev \
  --repo https://github.com/its-philipp/kpmg_adaptive_finance_governance_agent.git \
  --path azure_extension/aks/helm/afga-agent \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace afga-agent-dev \
  --helm-set-file values=azure_extension/aks/overlays/dev/values.yaml \
  --sync-policy automated

# Watch sync
argocd app get afga-agent-dev --refresh
```

## Cleanup Local Resources

### Uninstall Application

```bash
helm uninstall afga-agent -n afga-agent-dev
kubectl delete namespace afga-agent-dev
```

### Remove Istio

```bash
istioctl uninstall --purge -y
kubectl delete namespace istio-system
```

### Remove ArgoCD

```bash
kubectl delete -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl delete namespace argocd
```

### Stop Local Cluster

```bash
# Minikube
minikube stop
minikube delete

# Kind
kind delete cluster --name afga-agent-dev
```

## Benefits of Local Testing

1. **Zero cost**: No Azure charges
2. **Fast iteration**: Deploy in seconds
3. **Learn K8s**: Understand how everything works
4. **Validate charts**: Catch errors before Azure deployment
5. **Test GitOps**: Practice ArgoCD workflows

## Limitations of Local Testing

- ❌ No Azure Workload Identity (use env vars instead)
- ❌ No Key Vault CSI (use Kubernetes secrets)
- ❌ No Azure Load Balancer (use port-forward)
- ❌ Limited resources (your laptop vs cloud)

## When to Move to AKS

Move to Azure AKS when you need:
- ✅ Production-grade infrastructure
- ✅ Azure integration (Key Vault, Managed Identity)
- ✅ CTO demo with full architecture
- ✅ Load testing at scale
- ✅ Public ingress with real domain

Until then, local testing is perfect for development!

