# Hands-on — Registrar sources en Purview

Documento descriptivo de cómo registré las sources del demo Colmena: ADLS Gen2 (real, desplegado), y Sybase / Snowflake legacy (manuales vía Atlas API porque no hay sistema físico que escanear).

> Asume que el Terraform (`infra/`) ya está aplicado y las collections existen (ver `rbac_collections.md`).

---

## 1. Lo que registré (resumen ejecutivo)

| Source | Tipo | Cómo se registró | Estado |
|---|---|---|---|
| `adls-italodemo-colmena` | Azure Data Lake Storage Gen2 | `demo/scripts_exec/pv_register_sources.py` (PUT `/scan/datasources`) | Registrada y escaneada con 3 scans (bronze/silver/gold) |
| Sybase on-prem | Manual DataSet entities | `demo/scripts_exec/pv_manual_entities.py` (Atlas bulk) | 5 entities `sybase://colmena-onprem.local/POLICIES/{tabla}` |
| Snowflake DW legacy | Manual DataSet entities | `demo/scripts_exec/pv_manual_entities.py` (Atlas bulk) | 5 entities `snowflake://colmena.snowflakecomputing.com/...` |

Lo importante: **Sybase y Snowflake NO son conexiones reales** — son DataSets manuales para poder dibujar el grafo de lineage end-to-end sin tener que provisionar una VM con SHIR y una cuenta Snowflake real. La sección 6 y 7 explican qué se haría en un proyecto real.

---

## 2. Estructura de collections (pre-requisito)

Las collections las creé con `demo/scripts_exec/pv_create_collections.py` antes de registrar nada. Resultado:

```
Root (pv-italodemo-16de97)
└── colmena
    ├── sales
    ├── underwriting
    └── claims
```

Code: PUT `/account/collections/{name}?api-version=2019-11-01-preview` con `parentCollection.referenceName` apuntando al padre. Los 4 PUT volvieron 200/201.

(En un proyecto real cada sub-collection tendría role assignments distintos — en el demo todas heredan los roles que Terraform me dio sobre root; ver `rbac_collections.md`.)

---

## 3. Registrar ADLS Gen2 — lo que efectivamente corrí

Script: **`demo/scripts_exec/pv_register_sources.py`**

```python
# fragmento clave
adls_body = {
  "kind": "AdlsGen2",
  "name": "adls-italodemo-colmena",
  "properties": {
    "endpoint":     "https://stitalodemo16de97.dfs.core.windows.net/",
    "resourceId":   f"/subscriptions/{SUBID}/resourceGroups/rg-purview-demo/providers/Microsoft.Storage/storageAccounts/stitalodemo16de97",
    "collection":   {"referenceName": "colmena", "type": "CollectionReference"},
    "dataUseGovernance": "Disabled",
  }
}
requests.put(f"{EP}/scan/datasources/adls-italodemo-colmena?api-version=2022-02-01-preview", ...)
```

Output observado:

```
ADLS source: 200 {"id":".../datasources/adls-italodemo-colmena", "kind":"AdlsGen2", ...}
```

### 3.1 Qué quedó en Purview

- En Data Map → Sources, aparece `adls-italodemo-colmena` colgando de la collection `colmena`.
- Cubre los 3 containers (`bronze`, `silver`, `gold`) — no hay 3 sources separadas, sino una source con 3 scans con scope por path (ver `run_scan.md`).
- Auth: **Managed Identity de Purview** (rol `Storage Blob Data Reader` sobre el storage account, asignado por Terraform).

### 3.2 Por qué API y no UI

La UI funciona pero deja la operación sin huella reproducible. El script Python en `scripts_exec/` se puede correr otra vez si destruyo y rehago el RG. Mismo principio que IaC pero en data plane (ARM no expone `Microsoft.Purview/accounts/datasources`).

---

## 4. Gold layer = tablas Delta en ADLS (no hay DW separado)

En esta arquitectura **no hay Azure SQL DW ni Synapse Dedicated Pool**. Gold son tablas Delta dentro del mismo ADLS (`/gold/colmena/{tabla}`) y para Tableau se servirían vía Databricks SQL Warehouse (en el demo no levanté el warehouse — vive a nivel de notebook).

Por eso el registro de `adls-italodemo-colmena` ya cubre bronze, silver y gold. Purview detecta las carpetas Delta como resource sets durante el scan (ver `run_scan.md` para los resultados de discovered/classified counts).

> **Pregunta típica de entrevista:** *"¿Por qué gold en Delta y no en un DW dedicado?"*
> "Delta + Databricks SQL Warehouse nos dio ACID + time travel + un solo storage para todo el medallion sin pagar un DW aparte. Tableau lee por JDBC contra el warehouse igual que contra SQL Server. El ahorro operativo y de costo fue significativo y el caso de uso (reporting comercial) no requería sub-segundo."

---

## 5. War story: storage-account-key vs MSI en el cluster Databricks

El primer cluster Databricks (`Standard_D4ds_v4`, 15.4.x-scala2.12) lo monté como single-user y configuré las credenciales ADLS con `MsiTokenProvider`. Falló al primer notebook porque **el cluster no tenía managed identity attached** — el plan era usar la MSI del workspace pero en single-user esa MSI no se propaga al driver.

Solución para la demo: **storage-account-key directo en `spark.conf`** dentro del notebook (no a nivel cluster init). En producción esto sería un anti-patrón — irías por SP federation o cluster MI. Lo dejé documentado en los notebooks para ser honesto.

Esto no afectó el registro de la source en Purview (Purview usa su propia MSI sobre el storage). Sí afectó la corrida de los notebooks (ver `nb_dq_parity.md`).

---

## 6. Sybase on-prem — DataSet manual + cómo sería en real

En el demo Sybase **no existe físicamente**. Lo represento como 5 DataSet entities creadas vía `demo/scripts_exec/pv_manual_entities.py`:

```python
entities.append({
    "typeName": "DataSet",
    "attributes": {
        "qualifiedName": f"sybase://colmena-onprem.local/POLICIES/{t}",
        "name":          f"sybase.POLICIES.{t}",
        "description":   f"Legacy on-prem Sybase table (OLTP) — {t}",
    }
})
```

Tablas: `dim_policy`, `dim_party`, `dim_product`, `fact_policy_monthly`, `fact_claim`.

Output observado en bulk POST `/catalog/api/atlas/v2/entity/bulk`:

```
bulk create: 200
  created: 10            # 5 Sybase + 5 Snowflake en la misma llamada
```

> Las entities quedaron en la raíz del catálogo — el `POST /entity:moveHere` para reubicarlas en `colmena` retornó 404 (el shape exacto del endpoint cambió entre versiones de la API y no es bloqueante para el demo). Para el demo siguen siendo descubribles vía search; en cliente real lo movería con el SDK oficial `azure-purview-account` que abstrae esa diferencia.

### 6.1 Por qué importa: la respuesta real (entrevista)

En un cliente real, Sybase on-prem se escanearía con **SHIR (Self-Hosted Integration Runtime)** — un agente Windows en una VM dentro de la red corporativa del cliente. SHIR abre conexión saliente persistente (HTTPS 443) hacia Azure, sin requerir puertos entrantes — eso lo hace viable en bancos y aseguradoras.

Pasos conceptuales (cinco):

1. Provisionar VM Windows Server 2019/2022 (4 vCPU / 8 GB RAM) en la red del cliente.
2. Instalar el SHIR agent (Purview Studio → Management → Integration runtimes → New → Self-Hosted → MSI + auth key).
3. Instalar el ODBC driver de Sybase ASE en la misma VM.
4. Credential en Purview con Basic Auth (user Sybase de lectura), password en Key Vault + Purview MSI con rol `Key Vault Secrets User`.
5. Data Map → Sources → New → tipo Sybase → IR = el SHIR registrado → credential del paso 4 → collection `colmena/underwriting`.

Scan típico: schemas `policies`, `claims`, `parties`; weekly sábado 22:00 hora del cliente; **siempre full** (Sybase no soporta incremental nativo).

> **Por qué no lo desplegué:** SHIR requiere una VM real y red privada simulada (VNet + VPN/ExpressRoute). En sandbox no aporta — la respuesta conceptual ya queda cubierta acá y el lineage Sybase→bronze sí está en el grafo gracias a las entities manuales + los Process edges de `pv_push_lineage_new.py`.

---

## 7. Snowflake legacy — DataSet manual + cómo sería en real

Mismo patrón: 5 entities Snowflake creadas en la misma bulk call de `pv_manual_entities.py`:

```python
"qualifiedName": f"snowflake://colmena.snowflakecomputing.com/COLMENA_LEGACY/PUBLIC/{t.upper()}"
```

En el grafo aparecen como source huérfana del path nuevo (Sybase→Snowflake es el legacy, ver `pv_push_lineage_legacy.py` — son los 5 Process entities que conectan los 5 pares).

### 7.1 Cómo sería en real

Connector nativo Snowflake en Purview:

1. Data Map → Sources → Register → tipo Snowflake.
2. Account: `<your-account>.snowflakecomputing.com`; warehouse: `WH_PURVIEW_SCAN`.
3. Auth Basic con user/password Snowflake (Key Vault + MSI, mismo patrón que SHIR).
4. Scan weekly full + classifications.

> **Por qué no lo desplegué:** requiere cuenta Snowflake real (free trial 30 días). Para representar la topología del caso Colmena durante la migración (dual-load), las entities manuales son suficientes.

---

## 8. Estado real en Purview al cierre

```
Data Map → Sources view (lo que efectivamente existe hoy):

pv-italodemo-16de97 (root)
└── colmena
    ├── sales            (sin sources, solo collection)
    ├── underwriting     (sin sources, solo collection)
    ├── claims           (sin sources, solo collection)
    └── adls-italodemo-colmena   ← registrado, 3 scans Succeeded

Catalog (Atlas entities):
    + 5 DataSet "sybase://colmena-onprem.local/POLICIES/{t}"          (manual)
    + 5 DataSet "snowflake://colmena.snowflakecomputing.com/...{T}"    (manual)
    + 5 DataSet "https://.../bronze/colmena/{t}/{t}.csv"               (descubiertas por scan)
    + 5 DataSet "https://.../silver/colmena/{t}"                       (manual via pv_push_lineage_new fase 1)
    + 5 DataSet "https://.../gold/colmena/{t}"                         (manual via pv_push_lineage_new fase 1)
    + Process entities (5 legacy + 15 nuevas) que dibujan el lineage
```

ADF y Databricks **no se registraron como sources** en este demo — el lineage de bronze→silver→gold lo emite el script `pv_push_lineage_new.py` directamente como Process entities (ver `lineage_adf_databricks.md`).

---

## 9. Próximo paso

Para ver cómo se configuraron y ejecutaron los scans sobre `adls-italodemo-colmena`: `run_scan.md`.

Para el grafo de lineage end-to-end (Sybase→bronze→silver→gold y el path legacy Sybase→Snowflake): `lineage_adf_databricks.md`.
