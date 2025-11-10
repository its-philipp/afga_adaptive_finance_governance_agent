terraform {
  required_version = ">= 1.0"
  
  backend "azurerm" {
    # Configure backend state storage
    # Update these values with your actual backend details:
    resource_group_name  = "tfstate-rg"
    storage_account_name = "philippsstorageaccount"  # Same backend as dev
    container_name       = "tfstate"
    key                  = "adaptive-finance-governance-rag/staging/terraform.tfstate"
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
  default     = "staging"
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
  # Format: trustedai<env><random> to ensure uniqueness
  storage_account_name    = "trustedai${var.environment}sa${formatdate("YYMMDD", timestamp())}"
  resource_group_name     = azurerm_resource_group.main.name
  location                = var.location
  enable_public_access    = true  # Phase 1: Public access
  enable_private_endpoint  = false # Phase 2: Enable this
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Note: Additional modules (Key Vault, ACR, AKS, Databricks) will be added
# as we progress through the implementation

