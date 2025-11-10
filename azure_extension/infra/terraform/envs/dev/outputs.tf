output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = module.storage.storage_account_name
}

output "storage_account_primary_dfs_endpoint" {
  description = "Primary DFS endpoint for ADLS Gen2"
  value       = module.storage.storage_account_primary_dfs_endpoint
}

output "raw_container_name" {
  description = "Name of the raw container"
  value       = module.storage.raw_container_name
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = module.key_vault.key_vault_name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = module.key_vault.key_vault_uri
}

output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = module.acr.acr_name
}

output "acr_login_server" {
  description = "Login server for the ACR"
  value       = module.acr.acr_login_server
}

output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = module.aks.cluster_name
}

output "aks_cluster_fqdn" {
  description = "FQDN of the AKS cluster"
  value       = module.aks.cluster_fqdn
}

output "aks_workload_identity_client_id" {
  description = "Client ID of the AKS workload identity"
  value       = module.aks.workload_identity_client_id
}

output "log_analytics_workspace_name" {
  description = "Name of the Log Analytics workspace"
  value       = module.monitoring.workspace_name
}

