variable "acr_name" {
  description = "Name of the Azure Container Registry (must be globally unique, alphanumeric only)"
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

variable "sku" {
  description = "SKU for ACR (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"
}

variable "admin_enabled" {
  description = "Enable admin user (not recommended for production)"
  type        = bool
  default     = false
}

variable "enable_public_access" {
  description = "Enable public network access (Phase 1: true, Phase 2: false)"
  type        = bool
  default     = true
}

variable "aks_kubelet_identity_principal_id" {
  description = "Principal ID of AKS kubelet managed identity for image pull"
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

