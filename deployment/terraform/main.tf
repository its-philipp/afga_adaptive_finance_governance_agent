terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

variable "resource_group_name" {
  default = "rg-afga-prod"
}

variable "location" {
  default = "westeurope"
}

variable "cluster_name" {
  default = "afga-cluster"
}

# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# 2. Azure Container Registry (ACR)
resource "random_id" "acr_suffix" {
  byte_length = 4
}

resource "azurerm_container_registry" "acr" {
  name                = "afgaacr${random_id.acr_suffix.hex}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

# 3. Azure Key Vault
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                        = "afga-kv-${random_id.acr_suffix.hex}"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"

  # Grant current user full access to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions     = ["Get", "List", "Update", "Create", "Import", "Delete", "Recover", "Backup", "Restore"]
    secret_permissions  = ["Get", "List", "Set", "Delete", "Recover", "Backup", "Restore", "Purge"]
    storage_permissions = ["Get", "List"]
  }
}

# 4. AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "afga"

  default_node_pool {
    name       = "default"
    node_count = 2
    vm_size    = "Standard_B2s" # Change to Standard_D2s_v3 for production
  }

  identity {
    type = "SystemAssigned"
  }

  # Enables the Key Vault CSI Driver automatically
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  tags = {
    Environment = "Production"
  }
}

# 5. Grant AKS access to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}
