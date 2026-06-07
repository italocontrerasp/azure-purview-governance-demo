variable "prefix" {
  description = "Prefijo único (5-10 chars, lowercase + números) para naming de recursos."
  type        = string
  default     = "italodemo"

  validation {
    condition     = length(var.prefix) >= 5 && length(var.prefix) <= 10 && can(regex("^[a-z0-9]+$", var.prefix))
    error_message = "prefix debe tener 5-10 caracteres, solo lowercase y números."
  }
}

variable "location" {
  description = "Región Azure (debe soportar Purview)."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Nombre del resource group del sandbox."
  type        = string
  default     = "rg-purview-demo"
}

variable "databricks_tier" {
  description = "Tier del workspace Databricks: standard o premium."
  type        = string
  default     = "premium"

  validation {
    condition     = contains(["standard", "premium"], var.databricks_tier)
    error_message = "databricks_tier debe ser 'standard' o 'premium'."
  }
}

variable "tags" {
  description = "Tags aplicados a todos los recursos."
  type        = map(string)
  default = {
    project     = "purview-specialist-demo"
    owner       = "italo"
    environment = "sandbox"
    cost_center = "training"
  }
}
