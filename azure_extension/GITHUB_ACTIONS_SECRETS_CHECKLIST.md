# GitHub Actions Secrets Setup Checklist

## Overview

This checklist walks you through configuring all required secrets for GitHub Actions workflows. Follow each step in order and check them off as you complete them.

## Prerequisites

- GitHub repository: `its-philipp/adaptive_finance_governance_agent`
- Azure CLI installed and logged in: `az login`
- GitHub CLI installed (optional but recommended): `brew install gh`
- Azure subscription ID: `fd6c7319-01d0-4610-9681-b82980e227fb`

## Secrets Required

Your workflows need these secrets:

| Secret Name | Purpose | Used By |
|-------------|---------|---------|
| `AZURE_CREDENTIALS` | Azure login (JSON format) | All workflows |
| `ARM_CLIENT_ID` | Terraform authentication | Terraform workflows |
| `ARM_CLIENT_SECRET` | Terraform authentication | Terraform workflows |
| `ARM_SUBSCRIPTION_ID` | Terraform authentication | Terraform workflows |
| `ARM_TENANT_ID` | Terraform authentication | Terraform workflows |

## Step-by-Step Setup

### ✅ Step 1: Create Azure Service Principal

This Service Principal will be used by GitHub Actions to access Azure resources.

```bash
# Create Service Principal with SDK auth format
az ad sp create-for-rbac \
  --name "github-actions-trusted-ai-rag" \
  --role Contributor \
  --scopes /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb \
  --sdk-auth
```

**Expected Output:**
```json
{
  "clientId": "231db8e9-407b-465e-9bbb-...",
  "clientSecret": "abc123def456...",
  "subscriptionId": "fd6c7319-01d0-4610-9681-b82980e227fb",
  "tenantId": "2beb7b8f-96ca-46a2-...",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

**⚠️ IMPORTANT: Save this entire JSON output!** You'll need it in the next steps.

**Save to a secure temporary file:**
```bash
# Save to a file (will delete later)
az ad sp create-for-rbac \
  --name "github-actions-trusted-ai-rag" \
  --role Contributor \
  --scopes /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb \
  --sdk-auth > /tmp/sp-credentials.json

# View to confirm
cat /tmp/sp-credentials.json
```

**Extract individual values:**
```bash
# Set variables for later use
export ARM_CLIENT_ID=$(cat /tmp/sp-credentials.json | jq -r '.clientId')
export ARM_CLIENT_SECRET=$(cat /tmp/sp-credentials.json | jq -r '.clientSecret')
export ARM_SUBSCRIPTION_ID=$(cat /tmp/sp-credentials.json | jq -r '.subscriptionId')
export ARM_TENANT_ID=$(cat /tmp/sp-credentials.json | jq -r '.tenantId')

# Verify
echo "Client ID: $ARM_CLIENT_ID"
echo "Subscription ID: $ARM_SUBSCRIPTION_ID"
echo "Tenant ID: $ARM_TENANT_ID"
echo "Client Secret: (hidden)"
```

---

### ✅ Step 2: Grant ACR Push Permission

The Service Principal needs permission to push Docker images to Azure Container Registry.

```bash
# Replace <CLIENT_ID> with the clientId from Step 1
az role assignment create \
  --assignee $ARM_CLIENT_ID \
  --role "AcrPush" \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/adaptive-finance-governance-rag-dev-rg/providers/Microsoft.ContainerRegistry/registries/acrdevafga
```

**Expected Output:**
```json
{
  "id": "/subscriptions/.../roleAssignments/...",
  "name": "...",
  "principalId": "...",
  "roleDefinitionId": ".../AcrPush",
  "scope": ".../registries/acrdevafga",
  "type": "Microsoft.Authorization/roleAssignments"
}
```

**Verification:**
```bash
# List role assignments for the ACR
az role assignment list \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/adaptive-finance-governance-rag-dev-rg/providers/Microsoft.ContainerRegistry/registries/acrdevafga \
  --output table
```

---

### ✅ Step 3: Grant Storage Access (for Terraform State)

The Service Principal needs access to the storage account where Terraform state is stored.

```bash
# Grant Storage Blob Data Contributor
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $ARM_CLIENT_ID \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/tfstate-rg/providers/Microsoft.Storage/storageAccounts/philippsstorageaccount
```

**Expected Output:**
```json
{
  "id": "/subscriptions/.../roleAssignments/...",
  "principalId": "...",
  "roleDefinitionId": ".../Storage Blob Data Contributor",
  "scope": ".../storageAccounts/philippsstorageaccount"
}
```

---

### ✅ Step 4: Add Secrets to GitHub Repository

Now add the secrets to your GitHub repository.

#### Option A: Using GitHub Web UI

1. Go to your repository: https://github.com/its-philipp/adaptive_finance_governance_agent
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:

**Secret 1: AZURE_CREDENTIALS**
- Name: `AZURE_CREDENTIALS`
- Value: *The entire JSON output from Step 1*
- Click **Add secret**

**Secret 2: ARM_CLIENT_ID**
- Name: `ARM_CLIENT_ID`
- Value: *The `clientId` value from Step 1*
- Click **Add secret**

**Secret 3: ARM_CLIENT_SECRET**
- Name: `ARM_CLIENT_SECRET`
- Value: *The `clientSecret` value from Step 1*
- Click **Add secret**

**Secret 4: ARM_SUBSCRIPTION_ID**
- Name: `ARM_SUBSCRIPTION_ID`
- Value: *The `subscriptionId` value from Step 1*
- Click **Add secret**

**Secret 5: ARM_TENANT_ID**
- Name: `ARM_TENANT_ID`
- Value: *The `tenantId` value from Step 1*
- Click **Add secret**

#### Option B: Using GitHub CLI (Faster)

```bash
# Login to GitHub CLI (if not already)
gh auth login

# Navigate to your repository
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

# Add AZURE_CREDENTIALS (entire JSON)
gh secret set AZURE_CREDENTIALS < /tmp/sp-credentials.json

# Add individual ARM credentials
echo -n "$ARM_CLIENT_ID" | gh secret set ARM_CLIENT_ID
echo -n "$ARM_CLIENT_SECRET" | gh secret set ARM_CLIENT_SECRET
echo -n "$ARM_SUBSCRIPTION_ID" | gh secret set ARM_SUBSCRIPTION_ID
echo -n "$ARM_TENANT_ID" | gh secret set ARM_TENANT_ID

echo "✅ All secrets added successfully!"
```

---

### ✅ Step 5: Verify Secrets are Set

```bash
# List all secrets (won't show values, just names)
gh secret list

# Expected output:
# AZURE_CREDENTIALS       Updated 2025-10-31
# ARM_CLIENT_ID           Updated 2025-10-31
# ARM_CLIENT_SECRET       Updated 2025-10-31
# ARM_SUBSCRIPTION_ID     Updated 2025-10-31
# ARM_TENANT_ID           Updated 2025-10-31
```

**Verification Checklist:**
- [ ] `AZURE_CREDENTIALS` is listed
- [ ] `ARM_CLIENT_ID` is listed
- [ ] `ARM_CLIENT_SECRET` is listed
- [ ] `ARM_SUBSCRIPTION_ID` is listed
- [ ] `ARM_TENANT_ID` is listed

---

### ✅ Step 6: Clean Up Temporary Files

```bash
# Securely delete the credentials file
shred -u /tmp/sp-credentials.json 2>/dev/null || rm -f /tmp/sp-credentials.json

# Unset environment variables
unset ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_SUBSCRIPTION_ID ARM_TENANT_ID

echo "✅ Temporary credentials cleaned up"
```

---

### ✅ Step 7: Test GitHub Actions Workflows

Now test that your workflows can authenticate successfully.

#### Test 1: Build and Push Workflow (Dry Run)

```bash
# Create a small change to trigger CI
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

# Add a comment to trigger workflow
echo "# Test GitHub Actions - $(date)" >> README.md

# Commit and push
git add README.md
git commit -m "test: Verify GitHub Actions authentication"
git push origin main
```

**Monitor the workflow:**
1. Go to: https://github.com/its-philipp/adaptive_finance_governance_agent/actions
2. Click on the latest "Build and Push Docker Image to ACR" workflow
3. Watch for successful authentication and build

**Expected Steps:**
- ✅ Checkout code
- ✅ Set up Docker Buildx
- ✅ Log in to Azure (uses `AZURE_CREDENTIALS`)
- ✅ Log in to Azure Container Registry
- ✅ Build and push Docker image

#### Test 2: Terraform Plan Workflow (Create PR)

```bash
# Create a test branch
git checkout -b test-terraform-secrets

# Make a non-destructive Terraform change
cd azure_extension/infra/terraform/envs/dev

# Add a comment
echo "\n# GitHub Actions test - $(date)" >> main.tf

# Commit and push
git add main.tf
git commit -m "test: Verify Terraform workflow secrets"
git push origin test-terraform-secrets

# Create PR
gh pr create \
  --title "Test: Verify Terraform workflow secrets" \
  --body "Testing that GitHub Actions can authenticate with Terraform backend" \
  --base main
```

**Monitor the workflow:**
1. Go to the PR you just created
2. Wait for "Terraform Plan" workflow to run
3. Verify it completes successfully

**Expected Steps:**
- ✅ Terraform format check
- ✅ Terraform init (uses ARM credentials)
- ✅ Terraform validate
- ✅ Terraform plan
- ✅ Comment plan on PR

**Clean up test PR:**
```bash
# Close PR without merging
gh pr close test-terraform-secrets --delete-branch

# Switch back to main
git checkout main
```

---

## Troubleshooting

### Issue 1: "AZURE_CREDENTIALS not found"

**Symptom:**
```
Error: Input required and not supplied: creds
```

**Solution:**
```bash
# Verify secret exists
gh secret list | grep AZURE_CREDENTIALS

# If not found, re-add it
az ad sp create-for-rbac \
  --name "github-actions-trusted-ai-rag" \
  --role Contributor \
  --scopes /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb \
  --sdk-auth | gh secret set AZURE_CREDENTIALS
```

### Issue 2: "ACR login failed"

**Symptom:**
```
Error: unauthorized: authentication required
```

**Solution:**
```bash
# Verify AcrPush role is assigned
az role assignment list \
  --assignee $ARM_CLIENT_ID \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/adaptive-finance-governance-rag-dev-rg/providers/Microsoft.ContainerRegistry/registries/acrdevafga

# If not found, re-assign
az role assignment create \
  --assignee $ARM_CLIENT_ID \
  --role "AcrPush" \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/adaptive-finance-governance-rag-dev-rg/providers/Microsoft.ContainerRegistry/registries/acrdevafga
```

### Issue 3: "Terraform backend access denied"

**Symptom:**
```
Error: storage: service returned error: StatusCode=403
```

**Solution:**
```bash
# Grant Storage Blob Data Contributor
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $ARM_CLIENT_ID \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/tfstate-rg/providers/Microsoft.Storage/storageAccounts/philippsstorageaccount

# Wait 2-3 minutes for propagation
sleep 180

# Retry workflow
gh workflow run terraform-plan.yml
```

### Issue 4: "Service Principal not found"

**Symptom:**
```
Error: The service principal does not exist
```

**Solution:**
```bash
# List existing service principals
az ad sp list --display-name "github-actions-trusted-ai-rag" --query "[].{Name:displayName, AppId:appId}" -o table

# If exists but credentials are wrong, create new credentials
APP_ID=$(az ad sp list --display-name "github-actions-trusted-ai-rag" --query "[0].appId" -o tsv)

az ad sp credential reset \
  --id $APP_ID \
  --sdk-auth
```

---

## Security Best Practices

### ✅ DO:
- ✅ Use Service Principal with least privilege (Contributor on specific resource group)
- ✅ Rotate secrets every 90 days
- ✅ Use environment protection rules for production deployments
- ✅ Require PR reviews before merging to main
- ✅ Monitor Azure Activity Logs for Service Principal actions

### ❌ DON'T:
- ❌ Don't commit secrets to Git
- ❌ Don't share Service Principal credentials
- ❌ Don't use Owner role (Contributor is sufficient)
- ❌ Don't skip PR reviews for infrastructure changes
- ❌ Don't disable secret scanning in GitHub

---

## Secret Rotation Schedule

Set a reminder to rotate secrets every 90 days:

```bash
# In 90 days, rotate credentials:

# 1. Reset Service Principal credentials
APP_ID=$(az ad sp list --display-name "github-actions-trusted-ai-rag" --query "[0].appId" -o tsv)

az ad sp credential reset \
  --id $APP_ID \
  --sdk-auth > /tmp/new-sp-credentials.json

# 2. Update GitHub secrets
gh secret set AZURE_CREDENTIALS < /tmp/new-sp-credentials.json

export NEW_ARM_CLIENT_SECRET=$(cat /tmp/new-sp-credentials.json | jq -r '.clientSecret')
echo -n "$NEW_ARM_CLIENT_SECRET" | gh secret set ARM_CLIENT_SECRET

# 3. Clean up
shred -u /tmp/new-sp-credentials.json 2>/dev/null || rm -f /tmp/new-sp-credentials.json

echo "✅ Secrets rotated successfully!"
```

---

## Verification Script

Save this script to verify all secrets are working:

```bash
#!/bin/bash
# verify-github-secrets.sh

echo "🔍 Verifying GitHub Actions Secrets Setup..."
echo

# Check GitHub CLI is authenticated
if ! gh auth status &>/dev/null; then
  echo "❌ GitHub CLI not authenticated. Run: gh auth login"
  exit 1
fi

# Check secrets exist
echo "📋 Checking GitHub secrets..."
SECRETS=(
  "AZURE_CREDENTIALS"
  "ARM_CLIENT_ID"
  "ARM_CLIENT_SECRET"
  "ARM_SUBSCRIPTION_ID"
  "ARM_TENANT_ID"
)

MISSING_SECRETS=()
for secret in "${SECRETS[@]}"; do
  if gh secret list | grep -q "$secret"; then
    echo "  ✅ $secret"
  else
    echo "  ❌ $secret - MISSING"
    MISSING_SECRETS+=("$secret")
  fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
  echo
  echo "❌ Missing secrets: ${MISSING_SECRETS[*]}"
  echo "   Follow GITHUB_ACTIONS_SECRETS_CHECKLIST.md to add them"
  exit 1
fi

echo
echo "✅ All required secrets are configured!"
echo
echo "🚀 Next steps:"
echo "   1. Test workflows by pushing a commit"
echo "   2. Monitor at: https://github.com/its-philipp/adaptive_finance_governance_agent/actions"
echo "   3. Set up secret rotation reminder (90 days)"
```

**Usage:**
```bash
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent
chmod +x verify-github-secrets.sh
./verify-github-secrets.sh
```

---

## Summary Checklist

**Azure Setup:**
- [ ] Created Service Principal with SDK auth
- [ ] Granted AcrPush role for container registry
- [ ] Granted Storage Blob Data Contributor for Terraform state
- [ ] Saved credentials securely

**GitHub Setup:**
- [ ] Added `AZURE_CREDENTIALS` secret
- [ ] Added `ARM_CLIENT_ID` secret
- [ ] Added `ARM_CLIENT_SECRET` secret
- [ ] Added `ARM_SUBSCRIPTION_ID` secret
- [ ] Added `ARM_TENANT_ID` secret

**Verification:**
- [ ] Verified all secrets with `gh secret list`
- [ ] Tested Build and Push workflow
- [ ] Tested Terraform Plan workflow
- [ ] Cleaned up temporary credential files

**Security:**
- [ ] Set calendar reminder for secret rotation (90 days)
- [ ] Enabled branch protection on main
- [ ] Configured environment protection for prod
- [ ] Reviewed Azure Activity Logs

---

## Next Steps

After completing this checklist:

1. **Test Locally**: Use minikube to test Helm charts (see `MINIKUBE_TESTING_QUICKSTART.md`)
2. **Prepare Demo**: Review demo scenarios (see `DEMO_SCENARIOS.md`)
3. **Deploy to AKS**: When ready, follow `DEPLOYMENT_GUIDE.md`
4. **Set up GitOps**: Configure ArgoCD for continuous deployment

Your CI/CD pipeline is now fully configured and ready to automate builds and deployments! 🎉

