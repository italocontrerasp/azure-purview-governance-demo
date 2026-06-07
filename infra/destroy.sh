#!/usr/bin/env bash
# ============================================================================
# destroy.sh — Elimina el sandbox de Purview (Terraform)
# ----------------------------------------------------------------------------
# Uso:
#   bash infra/destroy.sh
#
# Purview cuesta ~$0.40/hora por capacity unit, así que es CRÍTICO correr
# este script al terminar cada sesión de práctica.
# ============================================================================

set -euo pipefail

PREFIX="${PREFIX:-italodemo}"
LOCATION="${LOCATION:-eastus}"
RG_NAME="${RG_NAME:-rg-purview-demo}"

INFRA_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------
if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: terraform no encontrado."
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: az CLI no encontrada."
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "ERROR: no estás logueado. Ejecuta: az login"
  exit 1
fi

SUB_NAME=$(az account show --query name -o tsv)
SUB_ID=$(az account show --query id -o tsv)

# ---------------------------------------------------------------------------
# Confirmación
# ---------------------------------------------------------------------------
echo
echo "===================================================================="
echo " ⚠️  Vas a ELIMINAR todos los recursos del sandbox."
echo " Suscripción: $SUB_NAME"
echo " Resource grp: $RG_NAME"
echo "===================================================================="
echo
if az group show -n "$RG_NAME" >/dev/null 2>&1; then
  echo "Recursos actuales en $RG_NAME:"
  az resource list -g "$RG_NAME" --query "[].{name:name, type:type}" --output table || true
  echo
fi
read -rp "¿Confirmar eliminación? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Cancelado."
  exit 0
fi

# ---------------------------------------------------------------------------
# Variables para Terraform
# ---------------------------------------------------------------------------
export ARM_SUBSCRIPTION_ID="$SUB_ID"
export TF_VAR_prefix="$PREFIX"
export TF_VAR_location="$LOCATION"
export TF_VAR_resource_group_name="$RG_NAME"

cd "$INFRA_DIR"

# ---------------------------------------------------------------------------
# Capturar nombres para purge antes de destruir
# ---------------------------------------------------------------------------
PURVIEW_NAME=""
KV_NAME=""
if az group show -n "$RG_NAME" >/dev/null 2>&1; then
  PURVIEW_NAME=$(az resource list -g "$RG_NAME" --resource-type Microsoft.Purview/accounts --query "[0].name" -o tsv 2>/dev/null || true)
  KV_NAME=$(az resource list -g "$RG_NAME" --resource-type Microsoft.KeyVault/vaults --query "[0].name" -o tsv 2>/dev/null || true)
fi

# ---------------------------------------------------------------------------
# Terraform destroy (preferred — usa el state si existe)
# ---------------------------------------------------------------------------
TF_DESTROY_OK=0
if [[ -f "$INFRA_DIR/terraform.tfstate" || -d "$INFRA_DIR/.terraform" ]]; then
  echo ">>> terraform destroy..."
  if terraform destroy -auto-approve; then
    TF_DESTROY_OK=1
  else
    echo "⚠️  terraform destroy falló — caigo a 'az group delete'."
  fi
else
  echo ">>> No hay state de Terraform — usando 'az group delete' directo."
fi

# ---------------------------------------------------------------------------
# Fallback: eliminar RG completo
# ---------------------------------------------------------------------------
if [[ $TF_DESTROY_OK -eq 0 ]] && az group show -n "$RG_NAME" >/dev/null 2>&1; then
  echo ">>> Eliminando resource group $RG_NAME ..."
  az group delete --name "$RG_NAME" --yes --no-wait
fi

# ---------------------------------------------------------------------------
# Purge de soft-deleted resources (best effort)
# ---------------------------------------------------------------------------
if [[ -n "$KV_NAME" ]]; then
  echo ">>> Intentando purgar Key Vault $KV_NAME (soft-delete)..."
  for _ in {1..30}; do
    if az keyvault list-deleted --query "[?name=='$KV_NAME']" -o tsv 2>/dev/null | grep -q "$KV_NAME"; then
      az keyvault purge --name "$KV_NAME" --location "$LOCATION" 2>/dev/null || true
      echo "    ✓ Key Vault purgado"
      break
    fi
    sleep 10
  done
fi

if [[ -n "$PURVIEW_NAME" ]]; then
  echo ">>> Purview ($PURVIEW_NAME) puede tardar más en soft-delete."
  echo "    Si necesitas purgarlo manual luego:"
  echo "    az purview account delete --name $PURVIEW_NAME --resource-group $RG_NAME"
fi

echo
echo "===================================================================="
echo " ✅ Eliminación completada."
echo " Verifica: az group list --query \"[?name=='$RG_NAME']\""
echo "===================================================================="
