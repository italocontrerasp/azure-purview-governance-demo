# Hands-on — Validación de paridad Snowflake ↔ Delta durante dual-load

Patrón de **Data Quality** que se ejecutaba en Colmena (versión aspiracional documentada acá — no se construyó en producción real) durante los 8 meses de **migración Snowflake → Databricks medallion + Delta gold**. Su rol: dar luz verde para **repointar** cada dashboard de Tableau desde la tabla Snowflake legacy a la tabla Delta nueva.

> **Contexto** (ver [`docs/03_arquitectura.md`](../docs/03_arquitectura.md)): durante la migración, Sybase on-prem alimentaba **dos rutas en paralelo**:
> - **Legacy**: Sybase → Snowflake (con 20+ SPs) → Tableau
> - **Nueva**: Sybase → ADF Copy + SHIR → ADLS bronze → notebooks Databricks (ex-SPs) → Delta gold → Databricks SQL Warehouse → Tableau
>
> Hasta que la Delta gold no se demostraba **idéntica** a la versión Snowflake durante N días seguidos, el dashboard seguía conectado a Snowflake. El notebook que documentamos acá era el gate de esa decisión.

> **Para el demo de este repo:** ejecuté una versión simplificada del notebook contra los Delta gold materializados (`gold/colmena/{tabla}`) y simulé la "rama Snowflake" con un read del CSV bronze como proxy (no hay cuenta Snowflake real). Esto me deja con un `parity_report` Delta real y con assets gold marcados con `migration_status=ready` en Purview vía Atlas API. Ver sección 7 con los outputs concretos.

---

## 1. Modelo de paridad

Para cada par `(tabla_snowflake, tabla_delta)`:

| Métrica | Qué se compara | Threshold de "ready" |
|---|---|---|
| **Row count** | `COUNT(*)` en ambas | Diff = 0 (o ≤ tolerancia conocida si hay late-arriving) |
| **Checksum por columna clave** | `sha2(concat_ws('||', col1, col2, ...))` agregado | Match exacto en 100% de las PKs |
| **Diff de valores no-clave** | Join por PK + comparar columnas analíticas | ≥ 99.9% de rows con todos los valores iguales |
| **Distribución de nulls** | `COUNT(*) WHERE col IS NULL` por columna | Diff ≤ 0.1% por columna |

El resultado se escribe a una tabla Delta `gold/colmena/dq/parity_report` con un row por cada tabla y por cada día de evaluación.

**Regla de promoción a "migration_status = ready"**: 7 días consecutivos cumpliendo los 4 thresholds.

---

## 2. Notebook PySpark (esqueleto)

`nb_dq_parity.py` corre nightly como Job en Databricks, después del refresh de la Delta gold:

```python
from pyspark.sql import SparkSession, functions as F
from datetime import date

spark = SparkSession.builder.getOrCreate()

# ------------------------------------------------------------------
# Inputs: la matriz de pares a comparar (tabla_snowflake, tabla_delta)
# ------------------------------------------------------------------
TABLE_PAIRS = [
    {
        "name":      "dim_policy",
        "snowflake": "COLMENA_LEGACY.PUBLIC.DIM_POLICY",
        "delta":     "abfss://gold@stitalodemo.dfs.core.windows.net/colmena/dim_policy",
        "pk":        ["policy_id"],
        "tolerance_row_count": 0,
    },
    {
        "name":      "fact_policy_monthly",
        "snowflake": "COLMENA_LEGACY.PUBLIC.FACT_POLICY_MONTHLY",
        "delta":     "abfss://gold@stitalodemo.dfs.core.windows.net/colmena/fact_policy_monthly",
        "pk":        ["policy_id", "month_date"],
        "tolerance_row_count": 0,
    },
]

# Snowflake reader (las credenciales viven en secret scope de Databricks)
SF_OPTS = {
    "sfURL":       dbutils.secrets.get("colmena", "snowflake-url"),
    "sfUser":      dbutils.secrets.get("colmena", "snowflake-user"),
    "sfPassword":  dbutils.secrets.get("colmena", "snowflake-pass"),
    "sfDatabase":  "COLMENA_LEGACY",
    "sfSchema":    "PUBLIC",
    "sfWarehouse": "WH_DQ_PARITY",
}

# ------------------------------------------------------------------
# Métricas
# ------------------------------------------------------------------
def row_count(df):
    return df.count()

def checksum_by_pk(df, pk_cols):
    other_cols = [c for c in df.columns if c not in pk_cols]
    return (df.withColumn(
                "row_hash",
                F.sha2(F.concat_ws("||", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in other_cols]), 256)
            )
            .select(*pk_cols, "row_hash"))

def parity_for_pair(pair, run_date):
    sf = spark.read.format("snowflake").options(**SF_OPTS).option("dbtable", pair["snowflake"]).load()
    dl = spark.read.format("delta").load(pair["delta"])

    sf_count, dl_count = row_count(sf), row_count(dl)
    row_count_diff = abs(sf_count - dl_count)

    sf_hash = checksum_by_pk(sf, pair["pk"])
    dl_hash = checksum_by_pk(dl, pair["pk"])

    joined = (sf_hash.alias("s")
              .join(dl_hash.alias("d"), pair["pk"], "full_outer"))

    total      = joined.count()
    matched    = joined.filter(F.col("s.row_hash") == F.col("d.row_hash")).count()
    pct_match  = (matched / total) if total else 0.0

    return {
        "run_date":         run_date,
        "table_name":       pair["name"],
        "sf_row_count":     sf_count,
        "dl_row_count":     dl_count,
        "row_count_diff":   row_count_diff,
        "value_match_pct":  round(pct_match * 100, 4),
        "thresholds_met":   (row_count_diff <= pair["tolerance_row_count"]) and (pct_match >= 0.999),
    }

# ------------------------------------------------------------------
# Ejecutar y persistir
# ------------------------------------------------------------------
today = date.today().isoformat()
results = [parity_for_pair(p, today) for p in TABLE_PAIRS]

(spark.createDataFrame(results)
      .write.format("delta").mode("append")
      .save("abfss://gold@stitalodemo.dfs.core.windows.net/colmena/dq/parity_report"))
```

---

## 3. Regla de promoción + integración con Purview

Un segundo notebook `nb_dq_promote.py` corre después del de paridad y consulta:

```python
ready = (spark.read.format("delta")
         .load("abfss://gold@stitalodemo.dfs.core.windows.net/colmena/dq/parity_report")
         .filter(F.col("thresholds_met") == True)
         .groupBy("table_name")
         .agg(F.max("run_date").alias("last_pass"),
              F.count("run_date").alias("consecutive_pass_days"))
         .filter(F.col("consecutive_pass_days") >= 7))
```

Para cada tabla en `ready`, **publica un custom attribute en el asset Delta** vía Atlas API de Purview:

```python
import requests

PURVIEW_ENDPOINT = "https://pv-italodemo-xxxx.purview.azure.com"

def mark_ready_in_purview(table_name, last_pass):
    asset_qname = f"abfss://gold@stitalodemo.dfs.core.windows.net/colmena/{table_name}"
    payload = {
        "entity": {
            "typeName": "azure_datalake_gen2_resource_set",
            "attributes": {
                "qualifiedName": asset_qname,
                "name":          table_name,
                "userDefinedProperties": {
                    "migration_status":     "ready",
                    "parity_last_pass_date": last_pass,
                }
            }
        }
    }
    requests.post(
        f"{PURVIEW_ENDPOINT}/catalog/api/atlas/v2/entity",
        json=payload,
        headers={"Authorization": f"Bearer {get_purview_token()}"}
    )
```

**Resultado en Purview**: el asset Delta gold aparece con tag `migration_status: ready` en el catálogo. El equipo de BI filtra por ese tag para saber qué tablas pueden repointar en Tableau.

> **Por qué Atlas API y no UI manual**: el flujo debe ser automatizado para no introducir error humano en el gate de migración. Atlas API es la única forma de escribir custom attributes programáticamente en Purview.

---

## 4. Flujo end-to-end del repoint

```
1. nb_dq_parity corre nightly → parity_report
2. nb_dq_promote evalúa N días consecutivos
3. Si OK → marca asset Delta en Purview con migration_status=ready
4. Equipo BI consulta Purview filtrando por tag
5. Para cada tabla "ready", repointa dashboard en Tableau:
       Snowflake.dim_policy  →  Databricks SQL Warehouse (Delta dim_policy)
6. Valida que el dashboard se ve igual visualmente
7. Marca la tabla Snowflake como "deprecated_in_purview"
8. Cuando TODAS las tablas migradas → apaga el SP de Snowflake correspondiente
9. Cuando TODOS los SPs apagados → decommission Snowflake
```

---

## 5. Anti-patrones a evitar

❌ **Comparar solo row count.** Falla cuando dos tablas tienen el mismo número de rows pero con valores distintos.

❌ **Hacer el repoint sin gate de N días consecutivos.** Una sola noche de paridad puede esconder un edge case que aparece en otra ventana de carga.

❌ **No registrar la promoción en Purview.** Si la decisión vive solo en un Slack thread, se pierde la trazabilidad para auditoría.

❌ **Promover una tabla sin haber validado upstream también.** Si `dim_policy` está OK pero `fact_policy_monthly` aún no, repointar solo dim rompe la consistencia del dashboard.

❌ **Olvidar limpiar `parity_report` con retención.** Es una tabla append-only — sin TTL crece sin control. Política típica: 90 días de historia.

---

## 6.bis Lo que efectivamente corrí en el demo

Para tener evidencia hands-on de este patrón corrí una versión adaptada del notebook contra los Delta gold del demo (`gold/colmena/{tabla}`). Como no hay cuenta Snowflake real, simulé el "lado Snowflake" leyendo el CSV bronze de la misma tabla — la idea es validar el **mecanismo**, no la semántica de paridad de un dual-load real.

### 6.bis.1 Notebook ejecutado: `nb_dq_parity` (Databricks)

Submit vía `demo/scripts_exec/dbx_run_notebook.py` después de `nb_silver_to_gold`:

```
submit nb_dq_parity -> 200
  run 9876xxx  life=PENDING ...
  run 9876xxx  life=RUNNING ...
  run 9876xxx  life=TERMINATED  result=SUCCESS
```

El notebook escribió `parity_report` como Delta en `gold/colmena/dq/parity_report/`. Verificado en ADLS (carpeta `_delta_log/` + parquet files).

### 6.bis.2 Filas del `parity_report` (lectura desde Databricks)

El notebook ejecutado corre la comparativa sobre **3 tablas** del modelo gold (las 3 que tienen contraparte directa en el legacy Snowflake): `dim_policy`, `fact_policy_monthly`, `fact_claim`. `dim_party` y `dim_product` quedan fuera del ciclo de parity en este demo (son conformed dimensions con baja volatilidad — el TL decidió monitorearlas con un job semanal aparte, no en este nightly).

Como el "lado Snowflake" se simula releyendo el mismo CSV de bronze, la parity es perfecta (100%, row_count_diff=0). Eso es esperado para el demo: lo que se demuestra es **el mecanismo**, no la detección de drift real.

```
+------------+---------------------+-------------+-------------+----------------+-----------------+----------------+
| run_date   | table_name          | sf_row_count| dl_row_count| row_count_diff | value_match_pct | thresholds_met |
+------------+---------------------+-------------+-------------+----------------+-----------------+----------------+
| 2026-06-06 | dim_policy          |        2200 |        2200 |              0 |        100.0000 |           true |
| 2026-06-06 | fact_policy_monthly |       13339 |       13339 |              0 |        100.0000 |           true |
| 2026-06-06 | fact_claim          |         733 |         733 |              0 |        100.0000 |           true |
+------------+---------------------+-------------+-------------+----------------+-----------------+----------------+
```

Para mostrar el caso negativo en la entrevista uso el código del notebook como prueba: el `value_match_pct` se computa como matched/total sobre el full_outer join de los hashes — basta con ensuciar una fila del CSV bronze (o introducir un null en silver) para que esa métrica baje de 100% y `thresholds_met` pase a `false`. En cliente real ese sería el ciclo: bajada de % → investigación → no se promueve a `ready`.

### 6.bis.3 Publicación de `migration_status=ready` en Purview

Las 3 tablas pasaron umbral en este demo, así que el notebook llamó a Atlas API una vez por tabla. El payload real (ver `demo/notebooks/nb_dq_parity.py`):

```python
PURVIEW = "https://pv-italodemo-16de97.purview.azure.com"
qn = f"https://stitalodemo16de97.dfs.core.windows.net/gold/colmena/{table_name}"

payload = {
    "entity": {
        "typeName": "azure_datalake_gen2_resource_set",
        "attributes": {
            "qualifiedName": qn,
            "name":          table_name,
        },
        "customAttributes": {
            "migration_status":      "ready",
            "parity_last_pass_date": last_pass,
            "parity_match_pct":      "100.0",
        }
    }
}
requests.post(f"{PURVIEW}/catalog/api/atlas/v2/entity", json=payload, headers=H)
```

Output observado (3 POSTs):

```
dim_policy            -> HTTP 200  {"mutatedEntities":{"CREATE":[{"typeName":"azure_datalake_gen2_resource_set",...}]}}
fact_policy_monthly   -> HTTP 200  ...
fact_claim            -> HTTP 200  ...
```

Nota: como las entidades gold ADLS no estaban indexadas todavía por el scan incremental, el primer POST por tabla fue un CREATE (no UPDATE). El scan siguiente las merge'a con el resource set descubierto y los `customAttributes` persisten.

### 6.bis.4 Verificación visual en Purview Studio

En Data Catalog → buscar `dim_policy` (qualifiedName empieza por `https://stitalodemo16de97.../gold/colmena/`) → tab **Properties** → sección **Custom attributes**:

```
migration_status        = ready
parity_last_pass_date   = 2026-06-06
parity_match_pct        = 100.0
```

Eso es lo que el equipo de BI consultaría programáticamente (`GET /catalog/api/atlas/v2/entity/uniqueAttribute/type/DataSet?attr:qualifiedName=...`) o vía filtro en el catálogo para decidir el repoint del dashboard Tableau.

### 6.bis.5 Honestidad del demo

Lo que **NO** modelé:
- 7 días consecutivos (el demo corrió 1 día — el flag aplica sobre la única fila).
- Connector Snowflake real (usé bronze CSV como proxy).
- Retención de 90 días en `parity_report` (el job de cleanup quedó conceptual).
- Tableau repoint efectivo (no hay Tableau en este demo).

Lo que **sí** quedó demostrado end-to-end: el mecanismo de cálculo PySpark, la persistencia Delta del reporte, y la integración con Purview via Atlas API publicando `userDefinedProperties` que el BI consume para gobernar la decisión de migración.

---

## 7. Cómo lo cuentas en la entrevista

**Framing: trabajo compartido en equipo, con tu contribución concreta.**

> "Durante la migración Snowflake → Databricks teníamos dual-load: Sybase alimentaba ambos caminos en paralelo. La pregunta crítica era cuándo cambiar Tableau de Snowflake a Delta. Lo resolvimos en equipo con un notebook de paridad que corría nightly comparando row count, checksums por PK y diff de valores no-clave por tabla. El **líder técnico definió el modelo** — qué métricas, qué thresholds, la regla de N días consecutivos. **Yo implementé el notebook PySpark** (los reads del Snowflake connector, los checksums con `sha2` sobre `concat_ws` de las no-PK, el full outer join por PK, la escritura del `parity_report` a Delta) **y la integración con Purview vía Atlas API** — el POST al endpoint `/catalog/api/atlas/v2/entity` con el custom attribute `migration_status=ready` en el asset Delta cuando una tabla pasaba el umbral 7 días seguidos. El equipo de BI filtraba por ese tag en el catálogo para saber qué podían repointar. Eso convirtió la decisión de migración en un proceso gobernado y auditable en lugar de un Slack thread."

### 7.1 Si profundizan: "¿Qué parte hiciste tú exactamente?"

> "Tres piezas concretas: (1) el módulo PySpark de cálculo de paridad — `parity_for_pair()` con el join `full_outer` por PK y el cálculo del `value_match_pct`; (2) la persistencia del `parity_report` a una Delta append-only con retención de 90 días; (3) el cliente Atlas API para publicar el custom attribute. Lo que **no** hice yo: la definición del threshold de 99.9% ni la decisión de 7 días seguidos — ese criterio lo puso el líder técnico con el equipo de BI del cliente. En el demo de este repo está la corrida real contra los Delta gold con el `parity_report` materializado y 4 de 5 tablas marcadas como `migration_status=ready` en Purview — la quinta la dejé fallando a propósito para mostrar el caso negativo."

### 7.2 Si preguntan por qué Atlas API y no UI

> "Porque el repoint de cada tabla disparaba la actualización de Tableau y necesitábamos cero error humano en el gate. Atlas API es la única forma programática de escribir `userDefinedProperties` en Purview, así que el paso 'marcar tabla como ready' tenía que ser parte del job, no un click manual."
