# ============================================================================
# main.tf — Sandbox Purview end-to-end (Terraform)
# ----------------------------------------------------------------------------
# Despliega: ADLS Gen2, Key Vault, Azure SQL, ADF, Databricks, Purview
#            + role assignment para que Purview MSI pueda escanear storage.
#
# Uso:
#   bash infra/deploy.sh
#
# Destrucción (IMPORTANTE para evitar costos):
#   bash infra/destroy.sh
# ============================================================================

data "azurerm_client_config" "current" {}

resource "random_id" "uniq" {
  byte_length = 3
}

locals {
  suffix = random_id.uniq.hex

  storage_name    = lower("st${var.prefix}${local.suffix}")
  keyvault_name   = lower("kv-${var.prefix}-${local.suffix}")
  adf_name        = lower("adf-${var.prefix}-${local.suffix}")
  databricks_name = lower("dbx-${var.prefix}-${local.suffix}")
  purview_name    = lower("pv-${var.prefix}-${local.suffix}")

  databricks_managed_rg = "${var.resource_group_name}-${local.databricks_name}-managed"
  purview_managed_rg    = "${var.resource_group_name}-${local.purview_name}-managed"
}

# ---------------------------------------------------------------------------
# Resource Group
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ---------------------------------------------------------------------------
# ADLS Gen2 (bronze / silver / gold)
# ---------------------------------------------------------------------------
resource "azurerm_storage_account" "adls" {
  name                            = local.storage_name
  resource_group_name             = azurerm_resource_group.rg.name
  location                        = azurerm_resource_group.rg.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  https_traffic_only_enabled      = true

  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_id    = azurerm_storage_account.adls.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_id    = azurerm_storage_account.adls.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_id    = azurerm_storage_account.adls.id
  container_access_type = "private"
}

# ---------------------------------------------------------------------------
# Key Vault (RBAC mode, sandbox abierto)
# ---------------------------------------------------------------------------
resource "azurerm_key_vault" "kv" {
  name                       = local.keyvault_name
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Azure Data Factory (idle = sin costo)
# ---------------------------------------------------------------------------
resource "azurerm_data_factory" "adf" {
  name                   = local.adf_name
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  public_network_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Azure Databricks workspace
# ---------------------------------------------------------------------------
resource "azurerm_databricks_workspace" "dbx" {
  name                        = local.databricks_name
  resource_group_name         = azurerm_resource_group.rg.name
  location                    = azurerm_resource_group.rg.location
  sku                         = var.databricks_tier
  managed_resource_group_name = local.databricks_managed_rg

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Microsoft Purview (la pieza más cara: ~$0.40/h por vCU)
# ---------------------------------------------------------------------------
resource "azurerm_purview_account" "pv" {
  name                        = local.purview_name
  resource_group_name         = azurerm_resource_group.rg.name
  location                    = azurerm_resource_group.rg.location
  managed_resource_group_name = local.purview_managed_rg
  public_network_enabled      = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Role assignment: Purview MSI → Storage Blob Data Reader sobre ADLS
# ---------------------------------------------------------------------------
resource "azurerm_role_assignment" "purview_to_storage" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_purview_account.pv.identity[0].principal_id
}
