variable "storage_account_name" {
  description = "Name of the storage account (must be globally unique)"
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

variable "account_tier" {
  description = "Storage account tier (Standard or Premium)"
  type        = string
  default     = "Standard"
}

variable "account_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}

variable "enable_versioning" {
  description = "Enable blob versioning"
  type        = bool
  default     = true
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain soft-deleted blobs"
  type        = number
  default     = 30
}

variable "enable_public_access" {
  description = "Enable public network access (Phase 1: true, Phase 2: false)"
  type        = bool
  default     = true
}

variable "managed_identity_principal_id" {
  description = "Principal ID of managed identity for AKS workload access"
  type        = string
  default     = null
}

variable "databricks_service_principal_id" {
  description = "Service principal ID for Databricks access"
  type        = string
  default     = null
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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

