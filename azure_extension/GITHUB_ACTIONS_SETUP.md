# GitHub Actions Setup Guide

## Overview

This guide shows how to configure GitHub Actions secrets for automated CI/CD workflows.

## Required Secrets

Go to your repository: https://github.com/its-philipp/kpmg_adaptive_finance_governance_agent

Navigate to: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### 1. Azure Credentials (for Azure Login)

Create a Service Principal with SDK-auth format:

```bash
az ad sp create-for-rbac \
  --name "github-actions-trusted-ai-rag" \
  --role Contributor \
  --scopes /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb \
  --sdk-auth
```

This will output JSON like:
```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "fd6c7319-01d0-4610-9681-b82980e227fb",
  "tenantId": "...",
  ...
}
```

**Copy the entire JSON output** and create secret:
- **Name**: `AZURE_CREDENTIALS`
- **Value**: The entire JSON output

### 2. Individual ARM Credentials

From the same Service Principal output above:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `ARM_CLIENT_ID` | `clientId` from JSON | 231db8e9-407b-465e-9bbb-... |
| `ARM_CLIENT_SECRET` | `clientSecret` from JSON | abc123... |
| `ARM_SUBSCRIPTION_ID` | `subscriptionId` from JSON | fd6c7319-01d0-4610-9681-... |
| `ARM_TENANT_ID` | `tenantId` from JSON | 2beb7b8f-96ca-46a2-... |

### 3. Grant Service Principal ACR Push Permission

```bash
az role assignment create \
  --assignee <CLIENT_ID_from_above> \
  --role "AcrPush" \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/adaptive-finance-governance-rag-dev-rg/providers/Microsoft.ContainerRegistry/registries/acrdevafga
```

## Workflows Available

### 1. Build and Push (`build-and-push.yml`)

**Purpose**: Automatically build and push Docker images to ACR

**Triggers**:
- Push to `main` → Tags as `latest`
- Push to `develop` → Tags as `develop`
- Push tag `v*` → Tags as the version number
- Pull request → Builds but doesn't push

**Usage**:
```bash
# Trigger by pushing code
git push origin main

# Or create a version tag
git tag v0.1.1
git push origin v0.1.1
```

**What it does**:
1. Checks out code
2. Sets up Docker Buildx
3. Logs into Azure and ACR
4. Determines appropriate tag
5. Builds image with caching
6. Pushes to ACR

### 2. Terraform Plan (`terraform-plan.yml`)

**Purpose**: Automatically validate and plan Terraform changes on PRs

**Triggers**:
- Pull requests to `main` that modify Terraform files

**What it does**:
1. Runs `terraform fmt -check`
2. Runs `terraform init`
3. Runs `terraform validate`
4. Runs `terraform plan`
5. Comments the plan on the PR

### 3. Terraform Apply (`terraform-apply.yml`)

**Purpose**: Manually deploy infrastructure via GitHub Actions

**Triggers**:
- Manual workflow dispatch (click "Run workflow" in GitHub)

**Usage**:
1. Go to Actions tab in GitHub
2. Select "Terraform Apply"
3. Click "Run workflow"
4. Choose environment (dev/staging/prod)
5. Optionally enable auto-approve

**Safety**:
- Requires manual trigger
- Can review plan before applying
- Environment protection can be configured

## Testing the Workflows

### Test Build Workflow (No Cost)

```bash
# Make a small change
echo "# Test CI" >> README.md

# Commit and push
git add README.md
git commit -m "test: Trigger CI/CD workflow"
git push origin main
```

Then watch in GitHub: Actions tab → "Build and Push Docker Image"

### Test Terraform Plan Workflow

```bash
# Create a branch
git checkout -b test-terraform-pr

# Make a Terraform change (non-destructive)
# Edit azure_extension/infra/terraform/envs/dev/main.tf
# Add a comment or change a tag

# Commit and push
git add azure_extension/infra/terraform/envs/dev/main.tf
git commit -m "test: Terraform PR workflow"
git push origin test-terraform-pr

# Create PR in GitHub UI
# Watch the workflow run and comment on PR
```

## Verifying Setup

### Check if secrets are configured

```bash
# List secrets (won't show values, just names)
gh secret list
```

Should show:
- AZURE_CREDENTIALS
- ARM_CLIENT_ID
- ARM_CLIENT_SECRET
- ARM_SUBSCRIPTION_ID
- ARM_TENANT_ID

### Manually trigger a workflow

```bash
# Using GitHub CLI
gh workflow run terraform-apply.yml \
  -f environment=dev \
  -f auto_approve=false
```

## Security Best Practices

1. **Least Privilege**: Service Principal only has Contributor on specific resource group
2. **Secret Rotation**: Rotate Service Principal secrets every 90 days
3. **Environment Protection**: Configure required reviewers for production
4. **Branch Protection**: Require PR reviews before merging to main
5. **CODEOWNERS**: Add CODEOWNERS file for Terraform changes

## Troubleshooting

### Workflow fails with authentication error

**Solution**: Verify secrets are set correctly
```bash
gh secret list
```

### Terraform backend access denied

**Solution**: Service Principal needs Storage Blob Data Contributor on tfstate storage:
```bash
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee <SERVICE_PRINCIPAL_CLIENT_ID> \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/tfstate-rg/providers/Microsoft.Storage/storageAccounts/philippsstorageaccount
```

### ACR push permission denied

**Solution**: Grant AcrPush role (see step 3 above)

## Cost Implications

**GitHub Actions usage (Free tier)**:
- 2,000 minutes/month free for private repos
- Each workflow run: ~5-10 minutes
- Typical usage: ~20-50 minutes/month
- **Cost**: $0 (well within free tier)

**No additional Azure costs** from CI/CD - workflows just automate what you'd do manually.

## Next Steps

1. Configure secrets in GitHub
2. Test build workflow
3. Set up branch protection
4. Configure environment protection for prod
5. When ready, use workflows to deploy to AKS

