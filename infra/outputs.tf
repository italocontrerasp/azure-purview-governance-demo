output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "purview_account_name" {
  value = azurerm_purview_account.pv.name
}

output "purview_endpoint" {
  value = "https://${azurerm_purview_account.pv.name}.purview.azure.com"
}

output "purview_catalog_endpoint" {
  value = "https://${azurerm_purview_account.pv.name}.purview.azure.com/catalog"
}

output "storage_account_name" {
  value = azurerm_storage_account.adls.name
}

output "storage_dfs_endpoint" {
  value = azurerm_storage_account.adls.primary_dfs_endpoint
}

output "adf_name" {
  value = azurerm_data_factory.adf.name
}

output "databricks_workspace_url" {
  value = "https://${azurerm_databricks_workspace.dbx.workspace_url}"
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}

output "next_steps" {
  value = "Ejecuta los pasos manuales en infra/README.md sección 'Post-deploy'."
}
