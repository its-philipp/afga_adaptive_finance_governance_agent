#!/bin/bash
# Readiness Verification Script
# Checks if you're ready for each next step

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Adaptive Finance Governance - Readiness Check    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 - NOT INSTALLED${NC}"
        return 1
    fi
}

# Function to check GitHub secret
check_gh_secret() {
    local secret_name="$1"
    local repo="${2:-its-philipp/kpmg_adaptive_finance_governance_agent}"
    
    if gh secret list -R "$repo" 2>/dev/null | grep -q "$secret_name"; then
        echo -e "${GREEN}✅ $secret_name${NC}"
        return 0
    else
        echo -e "${RED}❌ $secret_name - NOT CONFIGURED${NC}"
        return 1
    fi
}

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 - NOT FOUND${NC}"
        return 1
    fi
}

# =============================================================================
# CHECK 1: Local Testing Prerequisites
# =============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📦 Check 1: Local Testing with Minikube${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

LOCAL_READY=true

echo "Required tools:"
check_command "docker" || LOCAL_READY=false

# Check for minikube OR kind (at least one)
KUBE_TOOL_FOUND=false
if check_command "kind"; then
    echo -e "   ${GREEN}(Recommended for M2 Mac / limited resources)${NC}"
    KUBE_TOOL_FOUND=true
fi
if check_command "minikube"; then
    echo -e "   ${GREEN}(More features, higher resource usage)${NC}"
    KUBE_TOOL_FOUND=true
fi
if [ "$KUBE_TOOL_FOUND" = false ]; then
    echo -e "${RED}❌ kind or minikube - NEITHER INSTALLED${NC}"
    LOCAL_READY=false
fi

check_command "kubectl" || LOCAL_READY=false
check_command "helm" || LOCAL_READY=false

echo ""
echo "Helm chart files:"
# Check from current directory or parent
if [ -f "aks/helm/afga-agent/Chart.yaml" ]; then
    check_file "aks/helm/afga-agent/Chart.yaml" || LOCAL_READY=false
    check_file "aks/helm/afga-agent/values.yaml" || LOCAL_READY=false
    check_file "aks/overlays/dev/values.yaml" || LOCAL_READY=false
elif [ -f "../azure_extension/aks/helm/afga-agent/Chart.yaml" ]; then
    check_file "../azure_extension/aks/helm/afga-agent/Chart.yaml" || LOCAL_READY=false
    check_file "../azure_extension/aks/helm/afga-agent/values.yaml" || LOCAL_READY=false
    check_file "../azure_extension/aks/overlays/dev/values.yaml" || LOCAL_READY=false
else
    echo -e "${RED}❌ Helm charts not found (run from project root or azure_extension/)${NC}"
    LOCAL_READY=false
fi

echo ""
if [ "$LOCAL_READY" = true ]; then
    echo -e "${GREEN}✅ Ready for local testing!${NC}"
    echo -e "   📖 Next: Follow ${YELLOW}MINIKUBE_TESTING_QUICKSTART.md${NC}"
else
    echo -e "${RED}❌ Not ready for local testing${NC}"
    echo -e "   📖 Install missing tools first${NC}"
    echo ""
    echo "   Install commands:"
    if [ "$KUBE_TOOL_FOUND" = false ]; then
        echo -e "     ${YELLOW}# Choose ONE (kind recommended for M2 Mac):${NC}"
        echo "     brew install kind        # Lighter, faster"
        echo "     brew install minikube    # More features"
    fi
    if ! command -v kubectl &> /dev/null; then
        echo "     brew install kubectl"
    fi
    if ! command -v helm &> /dev/null; then
        echo "     brew install helm"
    fi
fi
echo ""

# =============================================================================
# CHECK 2: GitHub Actions Prerequisites
# =============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔐 Check 2: GitHub Actions Secrets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

GITHUB_READY=true

echo "GitHub CLI:"
if check_command "gh"; then
    if gh auth status &>/dev/null; then
        echo -e "${GREEN}✅ GitHub CLI authenticated${NC}"
    else
        echo -e "${RED}❌ GitHub CLI not authenticated${NC}"
        echo "   Run: gh auth login"
        GITHUB_READY=false
    fi
else
    GITHUB_READY=false
fi

echo ""
echo "Required secrets:"
if command -v gh &> /dev/null && gh auth status &>/dev/null; then
    # Try to detect repository or use default
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "its-philipp/kpmg_adaptive_finance_governance_agent")
    
    # Check secrets with repository specified
    check_gh_secret "AZURE_CREDENTIALS" "$REPO" || GITHUB_READY=false
    check_gh_secret "ARM_CLIENT_ID" "$REPO" || GITHUB_READY=false
    check_gh_secret "ARM_CLIENT_SECRET" "$REPO" || GITHUB_READY=false
    check_gh_secret "ARM_SUBSCRIPTION_ID" "$REPO" || GITHUB_READY=false
    check_gh_secret "ARM_TENANT_ID" "$REPO" || GITHUB_READY=false
else
    echo -e "${YELLOW}⏭️  Skipping (GitHub CLI not authenticated)${NC}"
fi

echo ""
if [ "$GITHUB_READY" = true ]; then
    echo -e "${GREEN}✅ Ready for GitHub Actions!${NC}"
    echo -e "   📖 Workflows will execute automatically${NC}"
else
    echo -e "${RED}❌ Not ready for GitHub Actions${NC}"
    echo -e "   📖 Next: Follow ${YELLOW}GITHUB_ACTIONS_SECRETS_CHECKLIST.md${NC}"
fi
echo ""

# =============================================================================
# CHECK 3: Demo Preparation
# =============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🎤 Check 3: Demo Preparation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

DEMO_READY=true

echo "Documentation:"
# Check from current directory or parent
if [ -f "DEMO_NARRATIVE_SCRIPT.md" ]; then
    check_file "DEMO_NARRATIVE_SCRIPT.md" || DEMO_READY=false
    check_file "DEMO_SCENARIOS.md" || DEMO_READY=false
    check_file "docs/ARCHITECTURE.md" || DEMO_READY=false
elif [ -f "../azure_extension/DEMO_NARRATIVE_SCRIPT.md" ]; then
    check_file "../azure_extension/DEMO_NARRATIVE_SCRIPT.md" || DEMO_READY=false
    check_file "../azure_extension/DEMO_SCENARIOS.md" || DEMO_READY=false
    check_file "../azure_extension/docs/ARCHITECTURE.md" || DEMO_READY=false
else
    echo -e "${RED}❌ Documentation files not found${NC}"
    DEMO_READY=false
fi

echo ""
echo "Demo environment:"
if [ -f ".env" ] || [ -f "../.env" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found (needed for demo)${NC}"
    DEMO_READY=false
fi

if command -v uvicorn &> /dev/null; then
    echo -e "${GREEN}✅ uvicorn installed${NC}"
else
    echo -e "${YELLOW}⚠️  uvicorn not installed${NC}"
    DEMO_READY=false
fi

if command -v streamlit &> /dev/null; then
    echo -e "${GREEN}✅ streamlit installed${NC}"
else
    echo -e "${YELLOW}⚠️  streamlit not installed${NC}"
    DEMO_READY=false
fi

echo ""
if [ "$DEMO_READY" = true ]; then
    echo -e "${GREEN}✅ Ready for demo!${NC}"
    echo -e "   📖 Next: Practice using ${YELLOW}DEMO_NARRATIVE_SCRIPT.md${NC}"
else
    echo -e "${YELLOW}⚠️  Demo environment needs setup${NC}"
    echo -e "   📖 Review ${YELLOW}DEMO_NARRATIVE_SCRIPT.md${NC}"
fi
echo ""

# =============================================================================
# CHECK 4: Databricks Readiness
# =============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🏗️  Check 4: Databricks Integration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

DATABRICKS_READY=true

echo "Databricks files:"
# Check from current directory or parent
if [ -f "databricks/notebooks/01_ingest_raw.py" ]; then
    check_file "databricks/notebooks/01_ingest_raw.py" || DATABRICKS_READY=false
    check_file "databricks/notebooks/02_validate_transform.py" || DATABRICKS_READY=false
    check_file "databricks/notebooks/03_chunk_embed_register.py" || DATABRICKS_READY=false
    check_file "databricks/unity_catalog/catalogs.sql" || DATABRICKS_READY=false
elif [ -f "../azure_extension/databricks/notebooks/01_ingest_raw.py" ]; then
    check_file "../azure_extension/databricks/notebooks/01_ingest_raw.py" || DATABRICKS_READY=false
    check_file "../azure_extension/databricks/notebooks/02_validate_transform.py" || DATABRICKS_READY=false
    check_file "../azure_extension/databricks/notebooks/03_chunk_embed_register.py" || DATABRICKS_READY=false
    check_file "../azure_extension/databricks/unity_catalog/catalogs.sql" || DATABRICKS_READY=false
else
    echo -e "${YELLOW}⚠️  Databricks files not found (optional)${NC}"
    DATABRICKS_READY=false
fi

echo ""
echo "Azure CLI:"
if check_command "az"; then
    if az account show &>/dev/null; then
        SUBSCRIPTION=$(az account show --query name -o tsv 2>/dev/null)
        echo -e "${GREEN}✅ Azure CLI authenticated (${SUBSCRIPTION})${NC}"
    else
        echo -e "${RED}❌ Azure CLI not authenticated${NC}"
        echo "   Run: az login"
        DATABRICKS_READY=false
    fi
else
    DATABRICKS_READY=false
fi

echo ""
echo "Databricks CLI:"
if command -v databricks &> /dev/null; then
    echo -e "${GREEN}✅ databricks CLI installed${NC}"
else
    echo -e "${YELLOW}⚠️  databricks CLI not installed${NC}"
    echo "   Install: pip install databricks-cli"
    DATABRICKS_READY=false
fi

echo ""
if [ "$DATABRICKS_READY" = true ]; then
    echo -e "${GREEN}✅ Ready for Databricks integration!${NC}"
    echo -e "   📖 Next: Follow ${YELLOW}DATABRICKS_READINESS_CHECKLIST.md${NC}"
    echo -e "   💰 Estimated cost: \$10-50/month"
else
    echo -e "${YELLOW}⚠️  Not ready for Databricks yet${NC}"
    echo -e "   📖 Review ${YELLOW}DATABRICKS_READINESS_CHECKLIST.md${NC}"
fi
echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Summary & Recommended Next Steps${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Readiness Status:"
echo ""
[ "$LOCAL_READY" = true ] && echo -e "${GREEN}✅ Local Testing (minikube)${NC}" || echo -e "${RED}❌ Local Testing${NC} - Install missing tools"
[ "$GITHUB_READY" = true ] && echo -e "${GREEN}✅ GitHub Actions${NC}" || echo -e "${RED}❌ GitHub Actions${NC} - Configure secrets"
[ "$DEMO_READY" = true ] && echo -e "${GREEN}✅ Demo Preparation${NC}" || echo -e "${YELLOW}⚠️  Demo Preparation${NC} - Review documentation"
[ "$DATABRICKS_READY" = true ] && echo -e "${GREEN}✅ Databricks Integration${NC}" || echo -e "${YELLOW}⚠️  Databricks Integration${NC} - Optional, when ready"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Recommend next action
if [ "$LOCAL_READY" = false ]; then
    echo -e "${YELLOW}🎯 RECOMMENDED NEXT ACTION:${NC}"
    echo -e "   Install missing tools for local testing"
    echo -e "   Then follow: ${YELLOW}MINIKUBE_TESTING_QUICKSTART.md${NC}"
elif [ "$GITHUB_READY" = false ]; then
    echo -e "${YELLOW}🎯 RECOMMENDED NEXT ACTION:${NC}"
    echo -e "   Configure GitHub Actions secrets"
    echo -e "   Follow: ${YELLOW}GITHUB_ACTIONS_SECRETS_CHECKLIST.md${NC}"
elif [ "$DEMO_READY" = false ]; then
    echo -e "${YELLOW}🎯 RECOMMENDED NEXT ACTION:${NC}"
    echo -e "   Prepare demo environment"
    echo -e "   Follow: ${YELLOW}DEMO_NARRATIVE_SCRIPT.md${NC}"
else
    echo -e "${GREEN}🎯 EXCELLENT! All core items are ready!${NC}"
    echo ""
    echo -e "   You can now:"
    echo -e "   1. Test locally with minikube"
    echo -e "   2. Trigger GitHub Actions workflows"
    echo -e "   3. Deliver CTO demos"
    echo ""
    echo -e "   ${YELLOW}Optional next step:${NC}"
    echo -e "   - Add Databricks (Follow ${YELLOW}DATABRICKS_READINESS_CHECKLIST.md${NC})"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "📖 Full roadmap: ${YELLOW}azure_extension/NEXT_STEPS_SUMMARY.md${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

