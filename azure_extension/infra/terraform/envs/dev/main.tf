terraform {
  required_version = ">= 1.0"
  
  backend "azurerm" {
    # Configure backend state storage
    # Update these values with your actual backend details:
    resource_group_name  = "tfstate-rg"
    storage_account_name = "philippsstorageaccount"  # e.g., tfstateyourname123
    container_name       = "tfstate"
    key                  = "adaptive-finance-governance-rag/dev/terraform.tfstate"
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "adaptive-finance-governance-rag"
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Storage Account (ADLS Gen2)
module "storage" {
  source = "../../modules/storage_adls"

  # Storage account name: max 24 chars, lowercase + numbers only
  # Use existing storage account name (created in first apply)
  storage_account_name    = "trustedaidevsa251031"
  resource_group_name     = azurerm_resource_group.main.name
  location                = var.location
  enable_public_access    = true  # Phase 1: Public access
  enable_private_endpoint  = false # Phase 2: Enable this
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Key Vault (for secrets management)
module "key_vault" {
  source = "../../modules/key_vault"

  key_vault_name      = "kv-${var.environment}-afga"  # Max 24 chars
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  enable_public_access = true  # Phase 1: Public access
  enable_private_endpoint = false
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
  
  depends_on = [azurerm_resource_group.main]
}

# Azure Container Registry
module "acr" {
  source = "../../modules/acr"

  acr_name            = "acr${var.environment}${var.project_name}"  # Must be alphanumeric, 5-50 chars, globally unique
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Basic"  # Use Standard or Premium for production
  admin_enabled       = true     # Temporary for dev - disable in prod
  enable_public_access = true
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
  
  depends_on = [azurerm_resource_group.main]
}

# Log Analytics Workspace (for AKS monitoring)
module "monitoring" {
  source = "../../modules/monitoring"

  workspace_name      = "log-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  retention_in_days   = 30
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
  
  depends_on = [azurerm_resource_group.main]
}

# Azure Kubernetes Service
module "aks" {
  source = "../../modules/aks"

  cluster_name        = "${var.project_name}-${var.environment}-aks"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  dns_prefix          = "${var.project_name}-${var.environment}"
  
  # Node pool configuration
  node_count          = 2
  vm_size             = "Standard_D2s_v3"
  enable_auto_scaling = true
  min_node_count      = 1
  max_node_count      = 5
  
  # Monitoring
  log_analytics_workspace_id = module.monitoring.workspace_id
  
  # Application configuration for workload identity
  app_namespace       = "afga-agent-${var.environment}"
  app_service_account = "afga-agent"
  
  # Integrate with other modules
  acr_id              = module.acr.acr_id
  key_vault_id        = module.key_vault.key_vault_id
  storage_account_id  = module.storage.storage_account_id
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
  
  depends_on = [
    azurerm_resource_group.main,
    module.monitoring,
    module.acr,
    module.key_vault,
    module.storage
  ]
}

# Note: Databricks and Networking modules can be added later

