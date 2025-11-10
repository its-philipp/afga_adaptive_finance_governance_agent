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

