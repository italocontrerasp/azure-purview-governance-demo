# Hands-on — Lineage ADF ↔ Databricks ↔ Purview

Documento descriptivo del grafo de lineage que efectivamente armé en Purview: Sybase on-prem → ADLS bronze → silver → gold (path nuevo) y, en paralelo, Sybase → Snowflake legacy (caja negra del DW que se está deprecando).

En este demo **no usé conectores nativos automáticos** (no levanté ADF como recurso de runtime, no configuré OpenLineage en el cluster). Todo el grafo está construido con **manual Atlas API** vía 3 scripts:

- `demo/scripts_exec/pv_manual_entities.py` — DataSet entities para Sybase y Snowflake (sources sin sistema físico).
- `demo/scripts_exec/pv_push_lineage_legacy.py` — 5 Process entities Sybase→Snowflake (path legacy).
- `demo/scripts_exec/pv_push_lineage_new.py` — 8 DataSet (silver/gold) + 15 Process entities (path nuevo Sybase→bronze→silver→gold).

> ⚠️ **Scope de este doc:** material **del demo end-to-end**. En Colmena la configuración de OpenLineage en los clusters Databricks y la integración ADF↔Purview las lideró el **líder técnico**; mi interacción real fue como **usuario** del lineage en el catálogo. La sección 2 (OpenLineage conceptual) y la 1 (ADF nativo conceptual) están acá para framing de entrevista, no porque las haya operado en el demo.

---

## 0. Resumen mental (para la entrevista)

Purview tiene **tres mecanismos** para capturar lineage:

| Mecanismo | Source típica | Coste | Cobertura | En este demo |
|---|---|---|---|---|
| **Automático nativo** | ADF, Synapse, Power BI | 0 (built-in) | Solo conectores soportados | No |
| **OpenLineage** | Databricks, dbt, Airflow | Bajo (init script) | Solo lo que el motor emite | No |
| **Manual vía Atlas API** | Snowflake legacy, scripts ad-hoc, BI no soportada | Alto (mantenimiento) | Lo que tú codifiques | **Sí — todo el grafo se hizo así** |

La realidad: en cualquier estate grande usas los tres. Para este demo, hacer todo manual fue la decisión correcta porque no había sistemas físicos a la izquierda (Sybase, Snowflake) ni a la derecha runtime ADF/OL — todo es Atlas API pura.

---

## 1. Lineage automático ADF → Purview (conceptual, no operado en este demo)

### 1.1 Conectar ADF a Purview (en un proyecto real)

```bash
ADF_ID=$(az datafactory show -g rg-purview-demo -n adf-italodemo-xxxx --query id -o tsv)
PURVIEW_ID=$(az purview account show -g rg-purview-demo -n pv-italodemo-16de97 --query id -o tsv)

az datafactory update --ids $ADF_ID \
  --set properties.purviewConfiguration.purviewResourceId=$PURVIEW_ID
```

Pre-requisito: la MSI del ADF tiene que tener rol `Data Curator` en la collection raíz (se asigna vía Terraform o policystore REST, ver `rbac_collections.md`).

### 1.2 Qué actividades emiten lineage automático

| Activity | Lineage emitido |
|---|---|
| **Copy** | source → sink, con column mapping si está configurado |
| **Data Flow (mapping)** | source(s) → transformaciones → sink(s) |
| **Execute SSIS Package** | parcial (solo source/sink, no internals) |
| **Notebook (Databricks)** | NO — el notebook es caja negra para ADF |
| **Stored Procedure** | NO |
| **Web / Lookup / If / ForEach** | NO — son control de flujo |

> **Truco de entrevista:** si te preguntan "¿por qué mi pipeline ADF no muestra lineage?", la respuesta 9 de 10 veces es "porque está usando Notebook activity y eso no emite lineage; tienes que complementarlo con OpenLineage en Databricks".

---

## 2. Lineage Databricks vía OpenLineage (conceptual, no operado en este demo)

Aquí está el verdadero diferenciador en proyectos reales. El conector Spark de OpenLineage emite eventos cada vez que un job lee/escribe, y Purview los ingiere si configuras el endpoint.

### 2.1 Init script + Spark config (referencia)

```bash
#!/bin/bash
OL_VERSION="1.18.0"
cd /databricks/jars
wget -q "https://repo1.maven.org/maven2/io/openlineage/openlineage-spark_2.12/${OL_VERSION}/openlineage-spark_2.12-${OL_VERSION}.jar"
```

Spark conf:

```properties
spark.jars.packages io.openlineage:openlineage-spark_2.12:1.18.0
spark.extraListeners io.openlineage.spark.agent.OpenLineageSparkListener
spark.openlineage.transport.type http
spark.openlineage.transport.url https://pv-italodemo-16de97.purview.azure.com
spark.openlineage.transport.endpoint /openlineage/api/v1/lineage
spark.openlineage.transport.auth.type api_key
spark.openlineage.transport.auth.apiKey {{secrets/colmena/purview-ol-token}}
spark.openlineage.namespace colmena-databricks
spark.openlineage.facets.disabled spark_unknown;spark.logicalPlan
```

> **Importante:** el token va a Databricks secret scope, NUNCA hardcoded.

### 2.2 Limitaciones reales (lo que aprendí leyendo)

- `spark.sql.execution.arrow.pyspark.enabled=true` rompe algunos facets.
- Delta `MERGE INTO` emitía lineage incompleto en versiones <1.16.
- Notebook con múltiples celdas → cada acción Spark emite un evento; el lineage en Purview se ve como N nodos. Mejor encapsular en una función/job.
- Unity Catalog tables emiten con namespace distinto al Hive metastore → puede aparecer duplicado.

---

## 3. Lineage manual vía Atlas API — lo que efectivamente corrí

### 3.1 Modelo Atlas (mental model)

Purview es Atlas por dentro. Todo es:

- **Entity** = un asset (tabla, archivo, dashboard, columna).
- **Process** = un nodo intermedio que representa la transformación (un SP, un script, un notebook).
- Lineage = `inputs[]` → `Process` → `outputs[]`.

### 3.2 War story: el bulk API no resuelve refs en la misma batch

Mi primera implementación intentaba un solo bulk POST con datasets + processes mezclados. Falló porque **el bulk Atlas API no resuelve `uniqueAttributes` refs dentro del mismo batch** — los datasets tienen que existir antes de que un Process pueda referenciarlos.

Solución (lo que está en `pv_push_lineage_new.py`):

```
Phase 1: POST /entity/bulk con SOLO los 10 DataSets (silver + gold para 5 tablas)
Phase 2: POST /entity/bulk con SOLO los 15 Process entities (referenciando esos DataSets)
```

Output observado:

```
phase 1 datasets: 200
  CREATE: 8           # 8 nuevos; los otros 2 ya existian de una corrida previa
phase 2 processes: 200
  CREATE: 15
  UPDATE: 0
  total processes sent: 15
```

(Los DataSets de bronze los descubrió el scan; no hubo que crearlos manuales — solo los de silver y gold porque los Delta no estaban escaneados aún al momento de correr este script.)

### 3.3 Sources sin sistema físico — `pv_manual_entities.py`

Para Sybase on-prem y Snowflake legacy (que no existen en este demo), creé 10 DataSet entities a mano:

```python
TABLES = ["dim_policy", "dim_party", "dim_product", "fact_policy_monthly", "fact_claim"]

# Sybase
for t in TABLES:
    entities.append({
        "typeName": "DataSet",
        "attributes": {
            "qualifiedName": f"sybase://colmena-onprem.local/POLICIES/{t}",
            "name":          f"sybase.POLICIES.{t}",
            ...
        }
    })

# Snowflake
for t in TABLES:
    entities.append({
        "typeName": "DataSet",
        "attributes": {
            "qualifiedName": f"snowflake://colmena.snowflakecomputing.com/COLMENA_LEGACY/PUBLIC/{t.upper()}",
            ...
        }
    })

requests.post(f"{EP}/catalog/api/atlas/v2/entity/bulk", json={"entities": entities}, ...)
# move them to collection 'colmena'
requests.post(f"{EP}/account/collections/colmena/entity:moveHere?api-version=2022-08-01-preview", ...)
```

Output:

```
bulk create: 200
  created: 10
move: 204
```

### 3.4 Path legacy Sybase→Snowflake — `pv_push_lineage_legacy.py`

5 Process entities, una por tabla, que dibujan el legacy ETL como caja negra:

```python
for t in TABLES:
    procs.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://legacy_etl/sybase_to_snowflake/{t}",
            "name":          f"legacy_etl_sybase_to_snowflake_{t}",
            "description":   "Carga legacy (caja negra) Sybase -> Snowflake DW",
            "inputs":  [ref(SY)],     # sybase://...
            "outputs": [ref(SF)],     # snowflake://...
        }
    })
```

Output:

```
legacy lineage: 200
  created: 5
   - process://legacy_etl/sybase_to_snowflake/dim_policy
   - process://legacy_etl/sybase_to_snowflake/dim_party
   - process://legacy_etl/sybase_to_snowflake/dim_product
   - process://legacy_etl/sybase_to_snowflake/fact_policy_monthly
   - process://legacy_etl/sybase_to_snowflake/fact_claim
```

> **Por qué un solo Process por tabla y no por cada SP de Snowflake (los 20+ del caso real):** simplificación de demo. En Colmena se modelarían los 20+ Process entities, uno por SP, para que la auditoría pueda trazar columna a columna. Acá basta con el "caja negra" agregada por tabla.

### 3.5 Path nuevo Sybase→bronze→silver→gold — `pv_push_lineage_new.py`

15 Process entities (3 por cada una de las 5 tablas):

```
sybase://.../POLICIES/{t}   --[adf_pl_sybase_to_bronze_{t}]-->   https://.../bronze/colmena/{t}/{t}.csv
https://.../bronze/colmena/{t}/{t}.csv --[dbx_nb_bronze_to_silver_{t}]--> https://.../silver/colmena/{t}
https://.../silver/colmena/{t}         --[dbx_nb_silver_to_gold_{t}]--> https://.../gold/colmena/{t}
```

Por cada tabla: 3 Process entities con qualifiedName tipo `process://adf/pl_sybase_to_bronze/{t}`, `process://databricks/nb_bronze_to_silver/{t}`, `process://databricks/nb_silver_to_gold/{t}`.

Output ya mostrado en 3.2: phase 1 = 8 datasets, phase 2 = 15 processes.

---

## 4. El grafo final en Purview (verificado en Studio)

```
sybase://.../POLICIES/dim_policy
    │
    ├─[legacy_etl_sybase_to_snowflake_dim_policy]──> snowflake://.../DIM_POLICY     (legacy, deprecando)
    │
    └─[adf_pl_sybase_to_bronze_dim_policy]──> bronze/colmena/dim_policy/dim_policy.csv
                                                           │
                                                           └─[dbx_nb_bronze_to_silver_dim_policy]──> silver/colmena/dim_policy
                                                                                                                │
                                                                                                                └─[dbx_nb_silver_to_gold_dim_policy]──> gold/colmena/dim_policy
```

Y el mismo patrón replicado para `dim_party`, `dim_product`, `fact_policy_monthly`, `fact_claim`. En total: 10 sources legacy (Sybase + Snowflake), 5 + 5 + 5 nuevas (bronze + silver + gold), 5 + 15 = 20 Process entities.

Click sobre cualquier asset gold → pestaña Lineage → expand upstream → ves toda la cadena hasta Sybase, con los 2 paths convergentes en Sybase como fuente común. Eso es lo que vendrías a mostrar en una entrevista como evidencia de que el cliente puede trazar cualquier campo gold hasta el OLTP de origen.

---

## 5. Estrategia recomendada para Colmena (storytelling)

> "En Colmena el lineage end-to-end lo armamos por capas:
> 1. **ADF→Purview nativo** cubrió todos los Copy de Sybase a ADLS — automático, sin código.
> 2. **OpenLineage en Databricks** capturó las transformaciones silver/gold; lo configuró el líder técnico en el cluster init para que aplicara a todos los jobs sin tocar notebooks.
> 3. Los **stored procedures legacy de Snowflake** (los 20+ que se migraron) los emitía el equipo manualmente vía Atlas API desde una Function que se gatillaba al final de cada ejecución ADF. Esto último era el dolor — lo eliminamos a medida que reemplazábamos SPs por jobs Spark.
>
> En el demo del repo no tengo ADF runtime ni cluster con OpenLineage real, así que **todo el grafo lo construí manual vía Atlas API** — fue una decisión consciente para tener experiencia hands-on con esa pieza, que es justamente la que menos se documenta y la que más cuesta debuggear."

Si te preguntan "¿qué tan completo quedó?": "End-to-end table-level llegamos a ~90%. Column-level solo en silver→gold (Databricks). Auditoría regulatoria estaba satisfecha porque podían trazar cualquier campo sensible (RUT, póliza) hasta su origen."

---

## 6. Troubleshooting (lo que efectivamente me pasó)

### 6.1 Bulk API no resuelve refs cross-entity → 2 fases

Ya cubierto en 3.2. Es la lección más importante del demo: **dataset endpoints primero, process endpoints después**.

### 6.2 Lineage manual aparece pero "huérfano" (sin conectar a sources)

Si el `qualifiedName` del input del Process no matchea exactamente con el de un DataSet existente → el Process aparece pero su upstream se ve cortado. Solución: copiar el qualifiedName desde Purview Studio (asset → Properties tab) y pegarlo literal en el ref.

### 6.3 Single-user cluster mismatched el PAT identity

War story relacionada a la corrida de notebooks (no al lineage en sí pero relevante para que aparezca lineage real desde Databricks): el cluster `0606-045945-hk82wqk5` lo creé como single-user con el UPN guest `..._outlook.com#EXT#@<tenant>.onmicrosoft.com`, pero el PAT estaba emitido como `italocontrerasperez@outlook.com`. Las llamadas a `jobs/runs/submit` fallaban con 403. Solución: `clusters/edit` para flipear `single_user_name` al UPN del PAT, lo que forzó restart del cluster.

---

## 7. Anti-patrones (lo que evité)

- **Lineage manual masivo.** Si emites >50 procesos a mano, lo vas a perder. Para el demo son 20 (manejable); en Colmena los SP-by-SP de Snowflake habrían pasado de 100 — por eso se automatizó vía Function.
- **Esperar lineage perfecto antes de mostrarlo.** Mejor 80% cubierto y en producción que 100% en backlog.
- **OpenLineage sin secret scope.** Hardcodear el token en cluster config = leak garantizado.
- **No versionar el init script.** Si rompe un upgrade del jar, no sabes qué versión funcionaba.
- **Column-level en TODO.** Caro (storage + UI lenta). Habilítalo solo en assets sensibles (PII, financieros).

---

## 8. Próximo paso

Para ver cómo se modelaron las collections sobre las que cuelgan estos assets: `rbac_collections.md`.

Para entender el patrón de promoción que usa estos lineage edges como soporte (custom attribute `migration_status=ready` sobre los DataSets gold): `nb_dq_parity.md`.
