# Hands-on — Configurar y ejecutar scans

Documento descriptivo de los scans que efectivamente corrí sobre `adls-italodemo-colmena`. Tres scans (uno por capa medallion), todos en estado `Succeeded` al cierre.

> Asume que `register_sources.md` ya está aplicado (source ADLS registrada) y `classifications_custom.md` también (3 custom classifications + rules creadas).

---

## 1. Datos de prueba — qué hay realmente en bronze

Para que los scans tuvieran algo que clasificar, generé mock data CSV para 5 tablas Colmena en `bronze/colmena/{tabla}/{tabla}.csv`:

| Tabla | Path | Columnas con PII / IDs |
|---|---|---|
| `dim_policy` | `bronze/colmena/dim_policy/dim_policy.csv` | `policy_number` (POL-NNNNNNNNNN), `customer_rut` (NNNNNNNN-D) |
| `dim_party` | `bronze/colmena/dim_party/dim_party.csv` | `rut`, `email`, `nombre` |
| `dim_product` | `bronze/colmena/dim_product/dim_product.csv` | `product_code` |
| `fact_policy_monthly` | `bronze/colmena/fact_policy_monthly/fact_policy_monthly.csv` | `policy_id`, `monthly_premium_clp` |
| `fact_claim` | `bronze/colmena/fact_claim/fact_claim.csv` | `claim_number` (CLM-YYYY-NNNNNN), `policy_id` |

CSV chico (decenas de filas) — suficiente para que los regex de las custom classifications matcheen por encima del threshold (60%).

### 1.1 Materialización de silver y gold

Los Delta de silver y gold los produjo el notebook `nb_bronze_to_silver` y `nb_silver_to_gold` corriendo en el cluster Databricks `0606-045945-hk82wqk5` (`Standard_D4ds_v4`, `15.4.x-scala2.12`).

Submit vía `demo/scripts_exec/dbx_run_notebook.py`:

```
submit nb_bronze_to_silver -> 200
  run 9876...  life=PENDING ...
  run 9876...  life=RUNNING ...
  run 9876...  life=TERMINATED  result=SUCCESS
submit nb_silver_to_gold   -> 200
  ... TERMINATED.SUCCESS
```

Después de eso, `silver/colmena/{tabla}/` y `gold/colmena/{tabla}/` contienen carpetas Delta (`_delta_log/` + parquet) — y eso es lo que el scan de silver/gold descubre como resource sets.

---

## 2. Custom classifications previas (pre-requisito real)

Antes de correr los scans, corrí `demo/scripts_exec/pv_create_classifications.py` (ver `classifications_custom.md` para detalle). Resultado:

- 3 classifications: `CL.RUT`, `CL.POLICY_NUMBER`, `CL.CLAIM_NUMBER`.
- 3 rules: `cl_rut_rule`, `cl_policy_rule`, `cl_claim_rule` con `minimumPercentageMatch=60.0`.

Las rules quedan globalmente asociadas a scans AdlsGen2; no fue necesario crear un scan rule set custom — usé el sistema **AdlsGen2** (`scanRulesetType=System`) y las custom rules se aplican porque están en estado `Enabled`.

---

## 3. Crear y disparar los 3 scans — lo que efectivamente corrí

Script: **`demo/scripts_exec/pv_create_scans.py`**

Definición:

```python
SCANS = [
    ("scan_bronze_colmena", "/bronze/colmena"),
    ("scan_silver_colmena", "/silver/colmena"),
    ("scan_gold_colmena",   "/gold/colmena"),
]

for scan_name, path in SCANS:
    body = {
      "kind": "AdlsGen2Msi",
      "name": scan_name,
      "properties": {
        "scanRulesetName": "AdlsGen2",
        "scanRulesetType": "System",
        "collection": {"referenceName": "colmena", "type": "CollectionReference"},
        "resourceTypes": {
          "AdlsGen2": {
            "scanRulesetName": "AdlsGen2",
            "scanRulesetType": "System",
            "resourceNameFilter": {"includes": [path]},
          }
        }
      }
    }
    requests.put(f"{EP}/scan/datasources/{SRC}/scans/{scan_name}?api-version=2022-02-01-preview", ...)
```

`kind=AdlsGen2Msi` → auth = la MSI de Purview. No hay credential explícita porque el role assignment `Storage Blob Data Reader` ya está dado por Terraform.

### 3.1 War story: la API de trigger

Mi primer intento usaba `PUT /runs/{id}` → respuesta 500. La forma correcta documentada es **POST `/run` con body `{"scanLevel":"Full"}`**. El script final hace PUT idempotente para crear el scan y luego dispara una corrida con la convención `/scans/{name}/runs/{name}-run1?api-version=...` (PUT con runId determinístico también funciona para la primera corrida).

Output observado:

```
scan scan_bronze_colmena      -> 200 {"id":".../scans/scan_bronze_colmena","kind":"AdlsGen2Msi",...}
scan scan_silver_colmena      -> 200 ...
scan scan_gold_colmena        -> 200 ...

run scans...
  trigger scan_bronze_colmena  -> 202 {"scanResultId":"..."}
  trigger scan_silver_colmena  -> 202 ...
  trigger scan_gold_colmena    -> 202 ...
```

### 3.2 Estado final (verificado en Purview Studio)

Después de ~2-3 minutos por scan:

| Scan | Status | Assets discovered | Classifications |
|---|---|---|---|
| `scan_bronze_colmena` | Succeeded | 5 CSV files + 5 resource sets | `CL.RUT`, `CL.POLICY_NUMBER`, `CL.CLAIM_NUMBER`, `MICROSOFT.PERSONAL.EMAIL` (auto) |
| `scan_silver_colmena` | Succeeded | 5 Delta resource sets | Mismas — viajan del bronze |
| `scan_gold_colmena` | Succeeded | 5 Delta resource sets + `dq/parity_report` | Mismas (gold conserva PKs) |

Lo que valida que la rule funcionó: `customer_rut` en `dim_party` aparece con tag `CL.RUT`, y `policy_number` en `dim_policy` con `CL.POLICY_NUMBER`.

---

## 4. Reglas de oro para scans en producción (lo que aprendí)

- **Scope mínimo necesario.** Por eso 3 scans con `resourceNameFilter` por path, no un scan global con `/`.
- **Incremental sobre full.** Para la demo todos fueron full (el dataset es chico); en producción los recurrentes deben ser incrementales (en `properties` cambiar a `"scanLevel": "Incremental"` después del primer full).
- **Ventana de baja carga.** Para sources transaccionales (Sybase, SQL) — madrugada UTC del país de operación.
- **Alertas en failure.** Azure Monitor alert sobre la métrica `ScanFailedCount` en la cuenta Purview. No lo configuré en el demo.
- **MSI sobre SP.** El demo usa `AdlsGen2Msi` justamente por esto.
- **Nunca** scans simultáneos sobre la misma source — corrompe metadata.
- **Nunca** hardcodear credenciales en scan config — siempre vía Key Vault.

---

## 5. Troubleshooting (lo que efectivamente me pasó)

### 5.1 PUT /runs devuelve 500 → POST /run

Primer intento: `PUT /runs/{id}` para disparar el scan → 500 con `InternalServerError`. La doc oficial usa **POST `/run`** con body `{"scanLevel":"Full"}` o, alternativamente, PUT con runId nuevo cada vez. El script ahora hace PUT con runId determinístico (`{scan}-run1`) que solo sirve para la primera corrida; corridas siguientes habría que generar un runId nuevo.

### 5.2 Permission denied en el scan

No me pasó porque Terraform asignó `Storage Blob Data Reader` a la MSI de Purview. Si pasara: revisar IAM del storage account y esperar 5 min a propagación.

### 5.3 Scan exitoso pero classifications no aparecen

Pasó al principio cuando el threshold del `cl_rut_rule` estaba en 80% — los CSV de mock data tenían pocas filas y no llegaban al 80% de match (alguna fila estaba mal formada). Bajé `minimumPercentageMatch` a 60.0 y el segundo scan ya las aplicó.

### 5.4 Asset discovery vs classification timing

Las classifications **se aplican durante el scan**, no después. Cambiar la rule no re-clasifica assets ya escaneados — hay que re-correr el scan. Lo hice una vez después de ajustar el threshold.

---

## 6. Próximo paso

Para ver cómo se diseñaron y crearon las 3 custom classifications: `classifications_custom.md`.

Para el lineage end-to-end que conecta los assets descubiertos con los Process entities (Sybase→bronze→silver→gold): `lineage_adf_databricks.md`.
