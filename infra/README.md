# Infra — Despliegue del sandbox Purview

Guía paso a paso para levantar el entorno de práctica en Azure.

---

## 1. Pre-requisitos

### 1.1 Cuenta Azure
- Suscripción Azure activa (trial sirve, pero ten en cuenta los $200 USD de crédito)
- Permisos: **Owner** sobre la suscripción (o Contributor + User Access Administrator)
  - Necesario porque el despliegue crea **role assignments** (Storage Blob Data Reader → Purview MSI)

### 1.2 Herramientas locales
```bash
# Azure CLI (Windows)
winget install -e --id Microsoft.AzureCLI

# Terraform (Windows)
winget install -e --id Hashicorp.Terraform

# Verificar
az version
terraform version
```

### 1.3 Login
```bash
az login
az account set --subscription "<tu-subscription-id-o-nombre>"
az account show     # confirma la sub activa
```

### 1.4 Verifica disponibilidad de Purview en tu región
```bash
az provider show -n Microsoft.Purview --query "resourceTypes[?resourceType=='accounts'].locations[]" -o tsv
```

Si tu región preferida no aparece, usa `eastus`, `westeurope` o `southeastasia`.

---

## 2. Despliegue

### 2.1 Una sola línea
```bash
bash infra/deploy.sh
```

El script desplegará todo (no requiere inputs adicionales — gold = tablas Delta en ADLS, no se crea Azure SQL).

### 2.2 Manual (si prefieres)
```bash
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
export TF_VAR_prefix=italodemo
export TF_VAR_location=eastus
export TF_VAR_resource_group_name=rg-purview-demo

cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Tiempo de despliegue: **10-15 minutos**.

### 2.3 Variables ajustables
| Variable | Default | Descripción |
|---|---|---|
| `PREFIX` | `italodemo` | Prefijo único de recursos |
| `LOCATION` | `eastus` | Región |
| `RG_NAME` | `rg-purview-demo` | Nombre del resource group |

Ejemplo:
```bash
PREFIX=mypurview LOCATION=westeurope bash infra/deploy.sh
```

---

## 3. Post-deploy (pasos manuales en el portal)

Estos pasos **NO** se pueden automatizar 100% con Terraform porque dependen de APIs data-plane de Purview (policystore) o UIs propietarias.

### 3.1 Conectar ADF con Purview
1. Abre el ADF Studio: portal.azure.com → tu ADF → Open Azure Data Factory Studio
2. Manage (icono caja de herramientas) → Microsoft Purview
3. Click **Connect to a Purview account**
4. Selecciona la cuenta `pv-italodemo-xxxx`
5. Confirma → ADF Managed Identity recibirá rol Data Curator en root collection
6. Aparecerá el ícono morado de Purview en la barra superior de ADF

✅ Validación: en Purview Studio → Data Map → Sources, debe aparecer ADF automáticamente.

### 3.2 Asignar rol a tu usuario en Purview
Por default el usuario que despliega NO es Collection Admin de la root collection.

1. Abre Purview Studio: `https://<purview-name>.purview.azure.com`
2. Data Map → Collections → Root collection
3. Role assignments → Add
4. Add yourself como: **Collection Admin**, **Data Source Admin**, **Data Curator**, **Insights Reader**

✅ Validación: puedes ver el menú Management sin errores 403.

### 3.3 Registrar sources

Ver guías detalladas en:
- [`scripts/register_sources.md`](../scripts/register_sources.md)
- [`scripts/run_scan.md`](../scripts/run_scan.md)
- [`scripts/classifications_custom.md`](../scripts/classifications_custom.md)

---

## 4. Costos estimados

Con el sandbox prendido durante una sesión de 2 horas:

| Recurso | Costo aproximado por 2h |
|---|---|
| Purview (1 vCU Data Map) | $0.80 |
| Purview scans (~3 scans cortos) | $0.50 |
| ADLS Gen2 (mínimo) | $0.01 |
| Databricks workspace (sin clusters encendidos) | $0.00 |
| ADF (sin pipelines corriendo) | $0.00 |
| Key Vault | $0.00 (free tier) |
| **Total por sesión** | **~$1.50 - $5 USD** |

3 sesiones de práctica antes de la entrevista = **~$5-15 USD total**.

⚠️ Si OLVIDAS destruir → ~$10/día = $300/mes. **No olvides destroy.sh.**

---

## 5. Destrucción

### 5.1 Al terminar cada sesión
```bash
bash infra/destroy.sh
```

### 5.2 Manual
```bash
az group delete --name rg-purview-demo --yes --no-wait

# Purgar soft-deletes para liberar nombres
az keyvault purge --name <kv-name> --location eastus
```

### 5.3 Verificar que todo está destruido
```bash
az group list --query "[?name=='rg-purview-demo']" -o table
# Vacío = todo limpio
```

---

## 6. Troubleshooting

### Error: "Region X is not available for Purview"
→ Usa `eastus`, `westeurope`, `southeastasia` o `australiaeast`.

### Error: "Subscription not registered for Microsoft.Purview"
```bash
az provider register --namespace Microsoft.Purview
az provider register --namespace Microsoft.Databricks
az provider register --namespace Microsoft.DataFactory
```

### Error: "Quota exceeded for capacity units"
→ Tu sub trial puede tener cuota 0 de Purview. Pide elevación en Azure Portal → Help + Support → New support request → Service and subscription limits.

### Error: "Storage account name already taken"
→ Cambia el `PREFIX` y vuelve a correr.

### Purview Studio dice "403 Forbidden" al entrar
→ No te asignaste roles en la root collection. Hazlo desde el portal (alguien con rol previo necesita asignártelo). Si eres el deployer, eres dueño y puedes elevarte: settings de la cuenta Purview → Identity → asignarte Owner sobre el recurso.

### Quiero ver los logs de un scan que falló
→ Purview Studio → Data Map → Sources → click el source → Recent scans → click el scan → ver detalles del error.
