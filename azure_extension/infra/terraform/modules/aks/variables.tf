variable "cluster_name" {
  description = "Name of the AKS cluster"
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

variable "dns_prefix" {
  description = "DNS prefix for the AKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "sku_tier" {
  description = "SKU tier (Free, Standard, Premium)"
  type        = string
  default     = "Free"
}

variable "node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
  default     = 2
}

variable "vm_size" {
  description = "VM size for nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "os_disk_size_gb" {
  description = "OS disk size in GB"
  type        = number
  default     = 30
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for the node pool"
  type        = bool
  default     = true
}

variable "min_node_count" {
  description = "Minimum number of nodes (if auto-scaling enabled)"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes (if auto-scaling enabled)"
  type        = number
  default     = 5
}

variable "subnet_id" {
  description = "Subnet ID for AKS nodes (Phase 2)"
  type        = string
  default     = null
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for monitoring"
  type        = string
}

variable "acr_id" {
  description = "ID of Azure Container Registry for image pull"
  type        = string
  default     = null
}

variable "key_vault_id" {
  description = "ID of Key Vault for workload identity access"
  type        = string
  default     = null
}

variable "storage_account_id" {
  description = "ID of Storage Account for workload identity access"
  type        = string
  default     = null
}

variable "app_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "afga-agent-dev"
}

variable "app_service_account" {
  description = "Kubernetes service account name for the application"
  type        = string
  default     = "afga-agent"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

