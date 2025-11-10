terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = var.admin_enabled
  
  # Public network access
  public_network_access_enabled = var.enable_public_access
  
  # Security
  identity {
    type = "SystemAssigned"
  }
  
  tags = var.tags
}

# Role assignment for AKS to pull images
resource "azurerm_role_assignment" "aks_acr_pull" {
  count                = var.aks_kubelet_identity_principal_id != null ? 1 : 0
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = var.aks_kubelet_identity_principal_id
}

# Private endpoint for Phase 2 (disabled by default)
resource "azurerm_private_endpoint" "acr" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "${var.acr_name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.acr_name}-psc"
    private_connection_resource_id = azurerm_container_registry.acr.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }

  tags = var.tags
}

