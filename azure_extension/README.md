# Azure Extension - Complete Guide Index

## 🚀 Quick Start

**New to this project?** Start here:
1. Run verification script: `./verify-readiness.sh`
2. Read: [NEXT_STEPS_SUMMARY.md](NEXT_STEPS_SUMMARY.md)
3. Follow the recommended path based on your goals

---

## 📚 Complete Guide Library

### 🎯 Getting Started (Start Here!)

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| **[NEXT_STEPS_SUMMARY.md](NEXT_STEPS_SUMMARY.md)** | **Master roadmap - read this first!** | 10 min | $0 |
| [verify-readiness.sh](verify-readiness.sh) | Check your readiness for each step | 2 min | $0 |
| [QUICKSTART.md](QUICKSTART.md) | Fast setup for local development | 15 min | $0 |

---

### 🧪 Local Development & Testing

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| **[MINIKUBE_TESTING_QUICKSTART.md](MINIKUBE_TESTING_QUICKSTART.md)** | **Test Helm charts locally (NEW!)** | 30 min | $0 |
| [LOCAL_KUBERNETES_TESTING.md](LOCAL_KUBERNETES_TESTING.md) | Detailed K8s local testing guide | 1 hour | $0 |

**Use when:** Before deploying to cloud, validating Helm charts, learning Kubernetes

---

### 🤖 CI/CD & Automation

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| **[GITHUB_ACTIONS_SECRETS_CHECKLIST.md](GITHUB_ACTIONS_SECRETS_CHECKLIST.md)** | **Setup GitHub Actions (NEW!)** | 45 min | $0 |
| [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) | Original GitHub Actions guide | 30 min | $0 |

**Use when:** Automating builds, setting up CI/CD pipelines

---

### 🎤 Demo & Presentation

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| **[DEMO_NARRATIVE_SCRIPT.md](DEMO_NARRATIVE_SCRIPT.md)** | **Complete CTO demo script (NEW!)** | 2-3 hours | $0 |
| [DEMO_SCENARIOS.md](DEMO_SCENARIOS.md) | Demo scenario comparison | 30 min | $0 |
| [docs/CTO_OVERVIEW.md](docs/CTO_OVERVIEW.md) | Executive summary for CTOs | 15 min | $0 |

**Use when:** Preparing for technical presentations, CTO meetings, sales demos

---

### 🏗️ Data Governance & Databricks

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| **[DATABRICKS_READINESS_CHECKLIST.md](DATABRICKS_READINESS_CHECKLIST.md)** | **Databricks decision & setup (NEW!)** | 5-8 hours | ~$50/mo |
| [databricks/SETUP.md](databricks/SETUP.md) | Detailed Databricks setup | 3-4 hours | ~$50/mo |
| [databricks/README.md](databricks/README.md) | Databricks architecture overview | 15 min | $0 |

**Use when:** Need Unity Catalog, data governance, PII detection, enterprise demos

---

### ☁️ Cloud Deployment

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Complete Azure AKS deployment | 3-4 hours | ~$150/mo |
| [RESOURCE_MANAGEMENT.md](RESOURCE_MANAGEMENT.md) | Azure resource management | 30 min | Varies |
| [CLOUD_MODE_SUCCESS.md](CLOUD_MODE_SUCCESS.md) | Cloud mode validation | 15 min | $0 |

**Use when:** Deploying to production, need Kubernetes orchestration

---

### 📖 Architecture & Design

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Complete architecture documentation | 30 min | $0 |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Operational runbook | 20 min | $0 |
| [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) | Implementation summary | 15 min | $0 |

**Use when:** Understanding the system, onboarding new developers, technical reviews

---

### 🔒 Security & Enterprise

| Guide | Purpose | Time | Cost |
|-------|---------|------|------|
| [ENTERPRISE_INTEGRATION.md](../ENTERPRISE_INTEGRATION.md) | SharePoint & enterprise features | 1 hour | Varies |
| [SHAREPOINT_SETUP.md](../SHAREPOINT_SETUP.md) | SharePoint integration setup | 45 min | $0 |

**Use when:** Integrating with corporate systems, enterprise deployment

---

## 🎯 Common Workflows

### Workflow 1: First-Time Setup (Local Development)

```bash
# 1. Check readiness
./verify-readiness.sh

# 2. Follow these guides in order:
# - MINIKUBE_TESTING_QUICKSTART.md (test locally)
# - GITHUB_ACTIONS_SECRETS_CHECKLIST.md (automate builds)
# - DEMO_NARRATIVE_SCRIPT.md (prepare presentation)

# Time: 1 week
# Cost: $0
```

### Workflow 2: Preparing for CTO Demo

```bash
# 1. Read demo guides
# - DEMO_NARRATIVE_SCRIPT.md
# - DEMO_SCENARIOS.md
# - docs/CTO_OVERVIEW.md

# 2. Practice demo flow (2-3 times)

# 3. Prepare environment
# - Test local Streamlit
# - Verify Azure Portal access
# - Prepare backup slides

# Time: 1 day
# Cost: $0
```

### Workflow 3: Production Deployment

```bash
# 1. Validate locally
# - MINIKUBE_TESTING_QUICKSTART.md

# 2. Deploy infrastructure
# - DEPLOYMENT_GUIDE.md (AKS)
# - DATABRICKS_READINESS_CHECKLIST.md (optional)

# 3. Configure monitoring
# - RESOURCE_MANAGEMENT.md

# Time: 1-2 weeks
# Cost: $150-200/month
```

---

### Workflow 4: Databricks Lakehouse Sync (AFGA Phase 2)

```bash
# 1. Provision Databricks + ADLS (follow databricks/SETUP.md)
# 2. Install backend extras:
#    uv add azure-identity azure-storage-file-datalake databricks-sdk
# 3. Start backend with overrides:
#    ./azure_extension/scripts/run_backend_databricks.sh
# 4. Process invoices via API/Streamlit
# 5. Monitor Databricks job + Delta tables (bronze/silver/gold)
# 6. (Optional) Add to .env:
#    MEMORY_BACKEND=databricks

# Time: 1 day for setup, then continuous sync
# Cost: ~$50/month (Databricks dev workspace + storage)
```

When the backend runs in Databricks mode it keeps SQLite for the interactive demo while replicating transactions, HITL feedback, and invoices to Azure Data Lake, triggering the notebook pipeline automatically.

---

## 📊 Cost Overview

| Scenario | Monthly Cost | What's Included |
|----------|--------------|-----------------|
| **Local Only** | $0 | Docker Compose, minikube, testing |
| **Cloud Storage** | ~$10 | ADLS Gen2, Key Vault, ACR |
| **+ Databricks** | ~$50 | + Unity Catalog, data governance |
| **+ AKS (Dev)** | ~$160 | + Kubernetes, Istio, ArgoCD |
| **Production** | ~$300-500 | Full stack with HA, scaling |

---

## 🛠️ Tools Reference

### Required Tools

```bash
# For local testing
brew install docker minikube kubectl helm

# For Azure
brew install azure-cli

# For GitHub
brew install gh

# For Databricks (optional)
pip install databricks-cli

# For Python development
brew install uv
```

### Verification

```bash
# Check tool versions
docker --version
minikube version
kubectl version --client
helm version
az --version
gh --version

# Or run comprehensive check
./verify-readiness.sh
```

---

## 🆘 Getting Help

### Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Minikube won't start | `minikube delete && minikube start` |
| GitHub Actions auth fails | Check secrets with `gh secret list` |
| Helm chart errors | Run `helm lint` first |
| Databricks costs high | Enable auto-terminate, use job clusters |

### Where to Find Answers

1. **Check the relevant guide's troubleshooting section**
2. **Run:** `./verify-readiness.sh` for diagnostic info
3. **Review:** `NEXT_STEPS_SUMMARY.md` for decision trees

---

## 📈 Progress Tracking

### Week 1: Foundation
- [ ] Local testing with minikube working
- [ ] GitHub Actions secrets configured
- [ ] CI/CD pipeline executing successfully
- [ ] Helm charts validated

### Week 2: Demo Ready
- [ ] Demo narrative practiced
- [ ] Architecture talking points memorized
- [ ] Demo environment tested
- [ ] Backup materials prepared

### Week 3: Cloud Deployment (Optional)
- [ ] AKS cluster deployed
- [ ] Application accessible
- [ ] GitOps configured
- [ ] Monitoring active

### Week 4: Data Governance (Optional)
- [ ] Databricks workspace created
- [ ] Unity Catalog configured
- [ ] Pipelines running
- [ ] Integration tested

---

## 🎓 Learning Path

### Beginner
1. Start with local development (Docker Compose)
2. Read `QUICKSTART.md`
3. Test with `MINIKUBE_TESTING_QUICKSTART.md`

### Intermediate
1. Set up GitHub Actions automation
2. Deploy to Azure with basic config
3. Practice demo presentations

### Advanced
1. Full AKS deployment with Istio
2. Databricks integration
3. Multi-environment GitOps

---

## 📝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## 📅 Document Updates

**Last Updated:** October 31, 2025  
**Version:** 2.0 (with new quickstart guides)

### Recent Additions
- ✨ **MINIKUBE_TESTING_QUICKSTART.md** - Fast local K8s testing
- ✨ **GITHUB_ACTIONS_SECRETS_CHECKLIST.md** - CI/CD setup
- ✨ **DEMO_NARRATIVE_SCRIPT.md** - Complete demo script
- ✨ **DATABRICKS_READINESS_CHECKLIST.md** - Databricks decision guide
- ✨ **NEXT_STEPS_SUMMARY.md** - Master roadmap
- ✨ **verify-readiness.sh** - Automated readiness check

---

## 🚀 Ready to Start?

1. **Run:** `./verify-readiness.sh`
2. **Read:** `NEXT_STEPS_SUMMARY.md`
3. **Follow:** The recommended path for your goals

Good luck! 🎉
