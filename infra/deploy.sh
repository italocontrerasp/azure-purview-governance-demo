#!/usr/bin/env bash
# ============================================================================
# deploy.sh — Despliega el sandbox Purview con Terraform
# ----------------------------------------------------------------------------
# Uso:
#   bash infra/deploy.sh
#
# Variables ajustables (env vars):
#   PREFIX, LOCATION, RG_NAME
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
  echo "ERROR: terraform no encontrado. Instala desde https://developer.hashicorp.com/terraform/install"
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: az CLI no encontrada. Instala desde https://aka.ms/installazurecli"
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "ERROR: no estás logueado en Azure. Ejecuta: az login"
  exit 1
fi

# ---------------------------------------------------------------------------
# Info actual
# ---------------------------------------------------------------------------
SUB_NAME=$(az account show --query name -o tsv)
SUB_ID=$(az account show --query id -o tsv)

echo
echo "===================================================================="
echo " Suscripción : $SUB_NAME ($SUB_ID)"
echo " Resource grp: $RG_NAME"
echo " Región      : $LOCATION"
echo " Prefijo     : $PREFIX"
echo "===================================================================="
echo
read -rp "¿Continuar con el despliegue? [y/N] " confirm
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
# Despliegue
# ---------------------------------------------------------------------------
echo ">>> terraform init..."
terraform init -upgrade

echo ">>> terraform validate..."
terraform validate

echo ">>> terraform plan..."
terraform plan -out=tfplan

echo ">>> terraform apply (10-15 min)..."
terraform apply -auto-approve tfplan
rm -f tfplan

echo
echo ">>> Outputs:"
terraform output

echo
echo "===================================================================="
echo " ✅ Despliegue completado."
echo
echo " Próximos pasos (ver infra/README.md sección 'Post-deploy'):"
echo "   1. Conectar ADF con Purview (Manage → Purview en ADF Studio)"
echo "   2. Asignarte roles en root collection de Purview"
echo "   3. Registrar sources en Purview"
echo "   4. Configurar scans"
echo
echo " ⚠️  RECUERDA: al terminar la sesión, ejecuta:"
echo "     bash infra/destroy.sh"
echo "===================================================================="
