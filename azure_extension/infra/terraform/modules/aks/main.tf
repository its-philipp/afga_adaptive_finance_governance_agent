terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.dns_prefix
  
  # Kubernetes version
  kubernetes_version = var.kubernetes_version
  
  # SKU
  sku_tier = var.sku_tier
  
  # Default node pool
  default_node_pool {
    name                = "default"
    node_count          = var.node_count
    vm_size             = var.vm_size
    os_disk_size_gb     = var.os_disk_size_gb
    type                = "VirtualMachineScaleSets"
    enable_auto_scaling = var.enable_auto_scaling
    min_count           = var.enable_auto_scaling ? var.min_node_count : null
    max_count           = var.enable_auto_scaling ? var.max_node_count : null
    
    # vnet_subnet_id     = var.subnet_id  # For Phase 2 with custom VNet
  }
  
  # Identity
  identity {
    type = "SystemAssigned"
  }
  
  # Workload Identity for pod authentication
  oidc_issuer_enabled       = true
  workload_identity_enabled = true
  
  # Network profile
  network_profile {
    network_plugin    = "azure"  # Use kubenet for simpler Phase 1, azure for Phase 2
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }
  
  # Azure Monitor integration
  oms_agent {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }
  
  # Key Vault secrets provider
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }
  
  # Azure Policy Add-on (optional, for governance)
  # azure_policy_enabled = true
  
  tags = var.tags
}

# Create user-assigned managed identity for workload identity
resource "azurerm_user_assigned_identity" "aks_workload" {
  name                = "${var.cluster_name}-workload-identity"
  location            = var.location
  resource_group_name = var.resource_group_name
  
  tags = var.tags
}

# Federated identity credential for workload identity
resource "azurerm_federated_identity_credential" "aks_workload" {
  name                = "${var.cluster_name}-federated-credential"
  resource_group_name = var.resource_group_name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.aks_workload.id
  subject             = "system:serviceaccount:${var.app_namespace}:${var.app_service_account}"
}

# Role assignment for ACR pull
resource "azurerm_role_assignment" "aks_acr_pull" {
  count                = var.acr_id != null ? 1 : 0
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

# Role assignment for workload identity to access Key Vault
resource "azurerm_role_assignment" "workload_keyvault_secrets_user" {
  count                = var.key_vault_id != null ? 1 : 0
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.aks_workload.principal_id
}

# Role assignment for workload identity to access Storage
resource "azurerm_role_assignment" "workload_storage_contributor" {
  count                = var.storage_account_id != null ? 1 : 0
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.aks_workload.principal_id
}

