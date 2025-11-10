variable "key_vault_name" {
  description = "Name of the Key Vault (must be globally unique, 3-24 chars)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "sku_name" {
  description = "SKU name for Key Vault (standard or premium)"
  type        = string
  default     = "standard"
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain soft-deleted vaults and secrets"
  type        = number
  default     = 90
}

variable "purge_protection_enabled" {
  description = "Enable purge protection (recommended for production)"
  type        = bool
  default     = false
}

variable "enable_public_access" {
  description = "Enable public network access (Phase 1: true, Phase 2: false)"
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint (Phase 2)"
  type        = bool
  default     = false
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for private endpoint"
  type        = string
  default     = null
}

variable "aks_workload_identity_principal_id" {
  description = "Principal ID of AKS workload identity for secret access"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Secret values (optional - can be set via CLI after creation)
variable "openai_api_key" {
  description = "OpenAI API key (optional - can be set manually)"
  type        = string
  default     = null
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API key (optional - can be set manually)"
  type        = string
  default     = null
  sensitive   = true
}

variable "langfuse_public_key" {
  description = "Langfuse public key (optional - can be set manually)"
  type        = string
  default     = null
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key (optional - can be set manually)"
  type        = string
  default     = null
  sensitive   = true
}

variable "databricks_workspace_url" {
  description = "Databricks workspace URL (optional - can be set manually)"
  type        = string
  default     = null
}

variable "databricks_job_id" {
  description = "Databricks job ID (optional - can be set manually)"
  type        = string
  default     = null
}

