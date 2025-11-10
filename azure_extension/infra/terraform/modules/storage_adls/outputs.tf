output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.adls.name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.adls.id
}

output "storage_account_primary_dfs_endpoint" {
  description = "Primary DFS endpoint for ADLS Gen2"
  value       = azurerm_storage_account.adls.primary_dfs_endpoint
}

output "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint"
  value       = azurerm_storage_account.adls.primary_blob_endpoint
}

output "managed_identity_id" {
  description = "Managed identity ID for the storage account"
  value       = azurerm_storage_account.adls.identity[0].principal_id
}

output "bronze_container_name" {
  description = "Name of the bronze container"
  value       = azurerm_storage_container.bronze.name
}

output "silver_container_name" {
  description = "Name of the silver container"
  value       = azurerm_storage_container.silver.name
}

output "gold_container_name" {
  description = "Name of the gold container"
  value       = azurerm_storage_container.gold.name
}

output "raw_container_name" {
  description = "Name of the raw container"
  value       = azurerm_storage_container.raw.name
}

