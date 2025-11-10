terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                        = var.key_vault_name
  location                    = var.location
  resource_group_name         = var.resource_group_name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = var.sku_name
  
  soft_delete_retention_days  = var.soft_delete_retention_days
  purge_protection_enabled    = var.purge_protection_enabled
  
  # Network settings
  public_network_access_enabled = var.enable_public_access
  
  # RBAC for access control (recommended over access policies)
  enable_rbac_authorization = true
  
  tags = var.tags
}

# Grant Key Vault Secrets Officer to current service principal (for Terraform operations)
resource "azurerm_role_assignment" "terraform_sp_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Grant Key Vault Secrets User to AKS workload identity (if provided)
resource "azurerm_role_assignment" "aks_workload_secrets_user" {
  count                = var.aks_workload_identity_principal_id != null ? 1 : 0
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.aks_workload_identity_principal_id
}

# Private endpoint for Phase 2 (disabled by default)
resource "azurerm_private_endpoint" "key_vault" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "${var.key_vault_name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.key_vault_name}-psc"
    private_connection_resource_id = azurerm_key_vault.main.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  tags = var.tags
}

# Secrets (to be populated after Key Vault is created)
# These are placeholders - actual secrets should be set via Azure CLI or portal

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "openai-api-key"
  value        = var.openai_api_key != null ? var.openai_api_key : "placeholder-set-via-cli"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]  # Don't overwrite if manually updated
  }
}

resource "azurerm_key_vault_secret" "openrouter_api_key" {
  name         = "openrouter-api-key"
  value        = var.openrouter_api_key != null ? var.openrouter_api_key : "placeholder-set-via-cli"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "weaviate_api_key" {
  name         = "weaviate-api-key"
  value        = "not-required-for-local"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "langfuse_public_key" {
  name         = "langfuse-public-key"
  value        = var.langfuse_public_key != null ? var.langfuse_public_key : "placeholder-set-via-cli"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "langfuse_secret_key" {
  name         = "langfuse-secret-key"
  value        = var.langfuse_secret_key != null ? var.langfuse_secret_key : "placeholder-set-via-cli"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "databricks_workspace_url" {
  name         = "databricks-workspace-url"
  value        = var.databricks_workspace_url != null ? var.databricks_workspace_url : "not-configured-yet"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "databricks_job_id" {
  name         = "databricks-job-id"
  value        = var.databricks_job_id != null ? var.databricks_job_id : "0"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.terraform_sp_secrets_officer]
  
  lifecycle {
    ignore_changes = [value]
  }
}

