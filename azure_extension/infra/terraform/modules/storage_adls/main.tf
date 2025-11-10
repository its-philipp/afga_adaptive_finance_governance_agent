terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

resource "azurerm_storage_account" "adls" {
  name                           = var.storage_account_name
  resource_group_name            = var.resource_group_name
  location                       = var.location
  account_tier                   = var.account_tier
  account_replication_type       = var.account_replication_type
  account_kind                   = "StorageV2"
  is_hns_enabled                 = true  # Enable Hierarchical Namespace for ADLS Gen2
  allow_nested_items_to_be_public = false
  min_tls_version                = "TLS1_2"
  
  # Enable soft delete for data protection
  # Note: Blob versioning is not supported when hierarchical namespace (ADLS Gen2) is enabled
  blob_properties {
    delete_retention_policy {
      days = var.soft_delete_retention_days
    }
  }

  # Networking - Phase 1: Public with restrictions, Phase 2: Private endpoints
  public_network_access_enabled = var.enable_public_access
  
  # Security
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "raw" {
  name                  = "raw"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

# Role assignment for managed identity (AKS workload identity)
resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  count                = var.managed_identity_principal_id != null ? 1 : 0
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.managed_identity_principal_id
}

# Role assignment for Databricks service principal
resource "azurerm_role_assignment" "databricks_storage_access" {
  count                = var.databricks_service_principal_id != null ? 1 : 0
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.databricks_service_principal_id
}

# Private endpoint for Phase 2 (disabled by default)
resource "azurerm_private_endpoint" "storage" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "${var.storage_account_name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.storage_account_name}-psc"
    private_connection_resource_id = azurerm_storage_account.adls.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  tags = var.tags
}

