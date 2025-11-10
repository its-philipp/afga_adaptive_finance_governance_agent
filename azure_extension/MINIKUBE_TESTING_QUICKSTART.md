# Minikube Testing Quickstart

## Overview

This guide provides step-by-step instructions to test your Helm charts locally using minikube before deploying to Azure AKS. Testing locally is **free** and allows rapid iteration.

## Benefits of Local Testing

- ✅ **Zero cost**: No Azure charges
- ✅ **Fast iteration**: Deploy in seconds, not minutes
- ✅ **Learn Kubernetes**: Hands-on experience without risk
- ✅ **Validate charts**: Catch configuration errors early
- ✅ **Debug easily**: Direct access to logs and pods

## Prerequisites

Install required tools:

```bash
# Install minikube
brew install minikube

# Install kubectl (if not already installed)
brew install kubectl

# Install helm
brew install helm

# Verify installations
minikube version
kubectl version --client
helm version
```

## Quick Start: Test Your Helm Chart in 5 Minutes

### Step 1: Start Minikube

```bash
# Start with adequate resources
minikube start --driver=docker --cpus=4 --memory=8192

# Verify it's running
kubectl get nodes
# Should show: minikube   Ready   control-plane   ...
```

**Expected output:**
```
😄  minikube v1.32.0 on Darwin
✨  Using the docker driver
👍  Starting control plane node minikube
🔥  Creating docker container ...
🐳  Preparing Kubernetes v1.28.3 ...
🔗  Configuring bridge CNI ...
🔎  Verifying Kubernetes components...
🏄  Done! kubectl is now configured to use "minikube"
```

### Step 2: Build and Load Docker Image Locally

```bash
# Navigate to project root
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

# Build the Docker image
docker build -t adaptive-finance-governance-agent:local .

# Load image into minikube
minikube image load adaptive-finance-governance-agent:local

# Verify image is loaded
minikube image ls | grep trusted-ai
```

### Step 3: Create Namespace

```bash
# Create test namespace
kubectl create namespace afga-agent-test

# Set as default context for convenience
kubectl config set-context --current --namespace=afga-agent-test

# Verify
kubectl config view --minify | grep namespace:
```

### Step 4: Validate Helm Chart

```bash
# Navigate to Helm chart directory
cd azure_extension/aks

# Lint the chart (checks for errors)
helm lint helm/afga-agent -f overlays/dev/values.yaml

# Expected: No errors or warnings
```

### Step 5: Dry-Run to See Generated Manifests

```bash
# Generate and review Kubernetes manifests without installing
helm template afga-agent helm/afga-agent \
  -f overlays/dev/values.yaml \
  --namespace afga-agent-test \
  --set image.repository=adaptive-finance-governance-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set keyVaultSecrets.enabled=false \
  --set istio.enabled=false \
  --set autoscaling.enabled=false \
  --set replicaCount=1 \
  --debug > /tmp/helm-dry-run.yaml

# Review the output
less /tmp/helm-dry-run.yaml

# Or view specific resources
echo "\n=== DEPLOYMENT ===" && cat /tmp/helm-dry-run.yaml | grep -A 50 "kind: Deployment"
echo "\n=== SERVICE ===" && cat /tmp/helm-dry-run.yaml | grep -A 20 "kind: Service"
```

### Step 6: Install Helm Chart

```bash
# Install with simplified config for local testing
helm install afga-agent helm/afga-agent \
  --namespace afga-agent-test \
  -f overlays/dev/values.yaml \
  --set image.repository=adaptive-finance-governance-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set keyVaultSecrets.enabled=false \
  --set istio.enabled=false \
  --set autoscaling.enabled=false \
  --set replicaCount=1 \
  --wait

# Expected output:
# NAME: afga-agent
# NAMESPACE: afga-agent-test
# STATUS: deployed
```

**Configuration Overrides Explained:**
- `image.repository=adaptive-finance-governance-agent`: Use local image
- `image.tag=local`: Use the local tag we built
- `image.pullPolicy=Never`: Don't try to pull from registry
- `keyVaultSecrets.enabled=false`: Skip Azure Key Vault (not available locally)
- `istio.enabled=false`: Skip Istio service mesh (not installed locally)
- `autoscaling.enabled=false`: Disable HPA for simplicity
- `replicaCount=1`: Single pod for testing

### Step 7: Verify Deployment

```bash
# Check all resources
kubectl get all -n afga-agent-test

# Check pod status (wait until Running)
kubectl get pods -n afga-agent-test -w
# Press Ctrl+C when pod shows 1/1 Running

# Check service
kubectl get svc -n afga-agent-test

# View pod logs
kubectl logs -f deployment/afga-agent -n afga-agent-test

# Check for errors
kubectl describe pod -n afga-agent-test -l app.kubernetes.io/name=afga-agent
```

### Step 8: Test the Application

```bash
# Port forward to access locally
kubectl port-forward svc/afga-agent 8000:8000 -n afga-agent-test &

# Wait 2 seconds for port forward to establish
sleep 2

# Test health endpoint
curl http://localhost:8000/api/v1/health

# Expected: {"status": "healthy", ...}

# Test API documentation
open http://localhost:8000/docs
```

**Success Indicators:**
- ✅ Pod is in `Running` state
- ✅ Health check returns 200 OK
- ✅ No error logs in pod logs
- ✅ API docs accessible

### Step 9: Make Changes and Update

```bash
# After making changes to your code, rebuild and update:

# 1. Rebuild Docker image
docker build -t adaptive-finance-governance-agent:local .

# 2. Reload into minikube
minikube image load adaptive-finance-governance-agent:local

# 3. Upgrade Helm release
helm upgrade afga-agent helm/afga-agent \
  --namespace afga-agent-test \
  -f overlays/dev/values.yaml \
  --set image.repository=adaptive-finance-governance-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set keyVaultSecrets.enabled=false \
  --set istio.enabled=false \
  --reuse-values

# 4. Watch rollout
kubectl rollout status deployment/afga-agent -n afga-agent-test
```

### Step 10: Cleanup When Done

```bash
# Uninstall Helm release
helm uninstall afga-agent -n afga-agent-test

# Delete namespace
kubectl delete namespace afga-agent-test

# Stop minikube (optional)
minikube stop

# Delete minikube cluster (to start fresh next time)
# minikube delete
```

## Common Issues and Solutions

### Issue 1: Pod in ImagePullBackOff

**Symptom:**
```bash
kubectl get pods -n afga-agent-test
# NAME                          READY   STATUS             RESTARTS   AGE
# afga-agent-xxx                 0/1     ImagePullBackOff   0          30s
```

**Solution:**
```bash
# Ensure image.pullPolicy is set to Never
helm upgrade afga-agent helm/afga-agent \
  --namespace afga-agent-test \
  --set image.pullPolicy=Never \
  --reuse-values

# Verify image is loaded in minikube
minikube image ls | grep trusted-ai
```

### Issue 2: Pod in CrashLoopBackOff

**Symptom:**
```bash
kubectl get pods -n afga-agent-test
# NAME                          READY   STATUS              RESTARTS   AGE
# afga-agent-xxx                 0/1     CrashLoopBackOff    3          2m
```

**Solution:**
```bash
# Check logs for errors
kubectl logs -n afga-agent-test -l app.kubernetes.io/name=afga-agent --tail=50

# Common causes:
# 1. Missing environment variables
# 2. Application startup errors
# 3. Health check failures

# Temporarily disable health checks to debug
helm upgrade afga-agent helm/afga-agent \
  --namespace afga-agent-test \
  --set livenessProbe.enabled=false \
  --set readinessProbe.enabled=false \
  --reuse-values
```

### Issue 3: Port Forward Connection Refused

**Symptom:**
```bash
curl http://localhost:8000/api/v1/health
# curl: (7) Failed to connect to localhost port 8000
```

**Solution:**
```bash
# Kill existing port-forward
pkill -f "kubectl port-forward"

# Restart port-forward in foreground to see errors
kubectl port-forward svc/afga-agent 8000:8000 -n afga-agent-test

# Or use pod directly if service has issues
POD_NAME=$(kubectl get pod -n afga-agent-test -l app.kubernetes.io/name=afga-agent -o jsonpath="{.items[0].metadata.name}")
kubectl port-forward $POD_NAME 8000:8000 -n afga-agent-test
```

### Issue 4: Helm Lint Warnings

**Symptom:**
```bash
helm lint helm/afga-agent -f overlays/dev/values.yaml
# [WARNING] templates/deployment.yaml: ...
```

**Solution:**
```bash
# Review the specific warning
# Common warnings:
# - Indentation issues
# - Missing labels
# - Resource limits not set

# Fix in the template files and re-lint
helm lint helm/afga-agent -f overlays/dev/values.yaml
```

## Advanced Local Testing

### Test with Environment Variables from .env File

```bash
# Create a values file with your environment variables
cat > /tmp/local-test-values.yaml <<EOF
env:
  CLOUD_MODE: "local"
  LOG_LEVEL: "DEBUG"
  OPENAI_MODEL: "gpt-4o-mini"
  WEAVIATE_URL: "http://weaviate:8080"
  
  # Add your secrets (for local testing only!)
  OPENAI_API_KEY: "sk-your-key-here"
  LANGFUSE_PUBLIC_KEY: "pk-lf-your-key"
  LANGFUSE_SECRET_KEY: "sk-lf-your-key"
EOF

# Install with custom values
helm install afga-agent helm/afga-agent \
  --namespace afga-agent-test \
  -f overlays/dev/values.yaml \
  -f /tmp/local-test-values.yaml \
  --set image.repository=adaptive-finance-governance-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set keyVaultSecrets.enabled=false \
  --set istio.enabled=false

# Cleanup: Remove the file with secrets
rm /tmp/local-test-values.yaml
```

### Test with Local Weaviate Instance

```bash
# Start Weaviate in minikube
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: weaviate
  namespace: afga-agent-test
spec:
  ports:
    - port: 8080
      targetPort: 8080
  selector:
    app: weaviate
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: weaviate
  namespace: afga-agent-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: weaviate
  template:
    metadata:
      labels:
        app: weaviate
    spec:
      containers:
      - name: weaviate
        image: semitechnologies/weaviate:1.23.0
        ports:
        - containerPort: 8080
        env:
        - name: AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED
          value: "true"
        - name: PERSISTENCE_DATA_PATH
          value: "/var/lib/weaviate"
        - name: DEFAULT_VECTORIZER_MODULE
          value: "none"
        - name: CLUSTER_HOSTNAME
          value: "node1"
EOF

# Wait for Weaviate to be ready
kubectl wait --for=condition=ready pod -l app=weaviate -n afga-agent-test --timeout=120s

# Now your RAG agent can connect to Weaviate at http://weaviate:8080
```

### Test Multiple Replicas

```bash
# Update to 2 replicas
helm upgrade afga-agent helm/afga-agent \
  --namespace afga-agent-test \
  --set replicaCount=2 \
  --reuse-values

# Watch pods scale up
kubectl get pods -n afga-agent-test -w

# Test load balancing
for i in {1..10}; do
  curl -s http://localhost:8000/api/v1/health | jq -r '.hostname'
done
# Should see different pod names
```

## Integration with CI/CD Testing

You can add minikube testing to your GitHub Actions:

```yaml
# .github/workflows/helm-test.yml
name: Helm Chart Test

on:
  pull_request:
    paths:
      - 'azure_extension/aks/helm/**'
      - '.github/workflows/helm-test.yml'

jobs:
  helm-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Minikube
        uses: medyagh/setup-minikube@latest
      
      - name: Helm lint
        run: |
          cd azure_extension/aks
          helm lint helm/afga-agent -f overlays/dev/values.yaml
      
      - name: Helm template
        run: |
          cd azure_extension/aks
          helm template afga-agent helm/afga-agent \
            -f overlays/dev/values.yaml \
            --set keyVaultSecrets.enabled=false \
            --set istio.enabled=false
```

## Next Steps After Local Testing

Once your Helm chart works well locally:

1. ✅ **Commit changes**: Push validated Helm charts to Git
2. ✅ **Set up GitHub Actions**: Configure automated Docker builds
3. ✅ **Deploy to Azure AKS**: Follow `DEPLOYMENT_GUIDE.md`
4. ✅ **Configure ArgoCD**: Enable GitOps deployment
5. ✅ **Add monitoring**: Azure Monitor and Langfuse

## Useful Commands Reference

```bash
# Minikube
minikube start                    # Start cluster
minikube stop                     # Stop cluster
minikube delete                   # Delete cluster
minikube dashboard                # Open K8s dashboard
minikube service list             # List all services
minikube ssh                      # SSH into minikube VM

# Helm
helm list -A                      # List all releases
helm history afga-agent -n afga-agent-test  # Show release history
helm get values afga-agent -n afga-agent-test  # Show current values
helm rollback afga-agent 1 -n afga-agent-test  # Rollback to revision 1
helm uninstall afga-agent -n afga-agent-test   # Uninstall release

# Kubectl
kubectl get all -n afga-agent-test           # Get all resources
kubectl describe pod <pod-name> -n afga-agent-test  # Detailed pod info
kubectl logs -f <pod-name> -n afga-agent-test       # Follow logs
kubectl exec -it <pod-name> -n afga-agent-test -- /bin/sh  # Shell into pod
kubectl delete pod <pod-name> -n afga-agent-test    # Delete pod (will recreate)
kubectl port-forward svc/afga-agent 8000:8000 -n afga-agent-test  # Port forward
```

## Cost Comparison: Local vs Azure

| Environment | Cost | Use Case |
|-------------|------|----------|
| **Minikube (Local)** | $0 | Development, testing, learning |
| **Azure AKS (Dev)** | ~$70-150/month | Demo, staging, light production |
| **Azure AKS (Prod)** | ~$300-500/month | Production workloads |

**Recommendation**: Use minikube extensively during development, then deploy to Azure AKS only when needed for demos or production.

## Summary

You now have a complete local Kubernetes testing environment! This allows you to:
- Validate Helm charts before Azure deployment
- Iterate quickly without costs
- Learn Kubernetes concepts hands-on
- Debug issues in a safe environment

When you're ready to deploy to Azure AKS, your Helm charts will already be tested and validated.

