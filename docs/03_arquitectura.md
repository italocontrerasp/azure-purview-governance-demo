# Arquitectura del proyecto

Mini-réplica del proyecto **Colmena** (Applaudo Studios, Dic 2023 – Jul 2024, 8 meses): migración de Snowflake a Databricks. En el proyecto real Microsoft Purview estaba en el stack definido por el líder técnico; este demo end-to-end fue construido aparte para profundizar en la **administración de plataforma** que en Colmena lideró el TL, complementando la experiencia de configuración y uso día-a-día.

---

## 1. Visión

Una aseguradora chilena (caso Colmena) tenía sus datos transaccionales en **Sybase on-prem** (OLTP de pólizas y siniestros), cargados a **Snowflake** como DW analítico donde **20+ stored procedures** producían las tablas que alimentaban los dashboards de Tableau del área comercial. El cliente quería:

1. **Reemplazar Snowflake** como motor analítico por **Azure Databricks** (preparación para workloads ML/IA + reducción de costo operativo).
2. **Re-implementar los 20+ SPs como notebooks PySpark** sobre una arquitectura medallion en ADLS Gen2 con gold en tablas Delta.
3. **Mantener** la trazabilidad y lineage para auditoría regulatoria (SVS chilena ≈ SBS peruana / Superfinanciera colombiana).
4. **Catalogar** los datos sensibles (RUT, beneficiarios, primas) para cumplir Ley 19.628 (protección de datos Chile).

**Origen no cambió**: Sybase on-prem se mantuvo como sistema transaccional. Lo que cambió fue el **DW analítico** (Snowflake → Databricks + Delta) y la **forma del procesamiento** (Snowflake SPs → notebooks PySpark).

Arquitectura objetivo: **Sybase on-prem → ADF Copy (vía SHIR) → ADLS Gen2 bronze/silver/gold (Delta) → Tableau**, donde el procesamiento bronze→silver→gold lo ejecutan **notebooks PySpark en Databricks** y el serving a Tableau lo hace **Databricks SQL Warehouse** (motor SQL que ejecuta queries directamente sobre las tablas Delta en ADLS — no es una capa de almacenamiento separada). Todo gobernado por **Microsoft Purview**. Durante los 8 meses de migración convivió con la ruta legacy **Sybase → Snowflake → Tableau** en **dual-load**, con repointing progresivo de cada dashboard al validar paridad por tabla.

---

## 2. Diagrama completo

```
                        ┌───────────────────────────────────────┐
                        │        Microsoft Purview (root)       │
                        │  ┌─────────────────────────────────┐  │
                        │  │   Collection: Colmena           │  │
                        │  │  ├─ Sales                       │  │
                        │  │  ├─ Underwriting                │  │
                        │  │  └─ Claims                      │  │
                        │  └─────────────────────────────────┘  │
                        └────────────────┬──────────────────────┘
                                         │ (scans + lineage de TODOS:
                                         │  Sybase, Snowflake, ADLS, ADF, DBX)
                                         │
       ┌──────────── LEGACY (durante migración) ──────────────┐
       │                                                      │
       │  ┌──────────────┐  ┌───────────────────┐  ┌────────┐ │
       │  │  Sybase      │  │  Snowflake (DW)   │  │ Tableau│ │
       │  │  on-prem     │─►│  20+ SPs procesan │─►│ legacy │ │ ← apunta a Snowflake
       │  │  (OLTP)      │  │  dim/fact/agg     │  │ view   │ │   antes del repoint
       │  │  POLICIES.*  │  └───────────────────┘  └────────┘ │
       │  │  CLAIMS.*    │                                    │
       │  └──────┬───────┘                                    │
       │         │  (carga legacy = caja negra para Purview,  │
       │         │   Snowflake aparece como source huérfana)  │
       └─────────┼────────────────────────────────────────────┘
                 │
                 │  ◄── DUAL-LOAD: misma Sybase alimenta los dos caminos
                 │
       ┌─────────┼────────────── NUEVO ───────────────────────────────┐
       │         ▼                                                    │
       │  ┌──────────────────┐                                        │
       │  │  ADF Copy + SHIR │  (SHIR en VM dentro de la red del      │
       │  │  pl_sybase_to_   │   cliente para alcanzar Sybase on-prem)│
       │  │  adls_bronze     │                                        │
       │  └─────────┬────────┘                                        │
       │            ▼                                                 │
       │  ┌──────────────────────────────────────────────┐            │
       │  │  ADLS Gen2 (medallion — STORAGE real)        │            │
       │  │  bronze (raw parquet)                        │            │
       │  │    └─ silver (Delta, cleansed/conformed)     │            │
       │  │         └─ gold (Delta, dim_* / fact_*)      │◄────┐      │
       │  └──────────────────┬───────────────────────────┘     │      │
       │           ▲ escribe │ lee                             │ lee  │
       │           │         │                                 │ Delta│
       │  ┌────────┴─────────┴───────────────────────────────┐ │(sin  │
       │  │  Databricks workspace (COMPUTE, sin storage)     │ │ copia│
       │  │                                                  │ │ de   │
       │  │  ┌────────────────────────┐   ┌────────────────┐ │ │datos)│
       │  │  │ notebooks PySpark      │   │ SQL Warehouse  │─┼─┘      │
       │  │  │ (ex-SPs Snowflake)     │   │ (motor SQL     │ │        │
       │  │  │ ejecutan medallion +   │   │  serverless)   │ │        │
       │  │  │ nb_dq_parity           │   └───────┬────────┘ │        │
       │  │  └────────────────────────┘           │ JDBC/ODBC│        │
       │  └──────────────────────────────────────┼──────────┘        │
       └─────────────────────────────────────────┼───────────────────┘
                                                 ▼
                                         ┌───────────────┐
                                         │ Tableau       │ ← apunta a
                                         │ (post-repoint)│   SQL Warehouse,
                                         └───────────────┘   que lee Delta
                                                             gold tras validar
                                                             paridad
       ┌─────────────────────────┐
       │   Azure Key Vault       │
       │   (secrets ADF/DBX)     │
       └─────────────────────────┘
```

**Repointing progresivo**: durante la migración Tableau apuntaba a Snowflake. Para cada tabla migrada, un notebook `nb_dq_parity` validaba que la Delta gold coincidiera con la versión Snowflake durante N días seguidos (row count + checksums + diff de valores). Al cumplir el SLA de paridad, se cambiaba la conexión del dashboard a Databricks SQL Warehouse. Tabla por tabla, hasta apagar Snowflake al final de la migración.

> **Aclaración técnica clave — Databricks SQL Warehouse**: NO es un destino de datos ni una capa de almacenamiento. Es un **motor de cómputo SQL serverless** dentro del workspace de Databricks que ejecuta queries directamente sobre las tablas Delta en ADLS gold. Para Tableau es un endpoint JDBC/ODBC; para el dato es un compute layer sin estado. Los notebooks PySpark **escriben** las Delta en ADLS gold; el SQL Warehouse **lee** esas mismas Delta cuando Tableau hace una query. No hay duplicación ni copia.

---

## 3. Componentes y rol de cada uno

| Recurso | Rol | Integración con Purview |
|---|---|---|
| **Sybase on-prem** | Origen OLTP (no cambió en la migración) | Registrado como source vía **Self-Hosted Integration Runtime** (SHIR) en VM dentro de la red del cliente; scan semanal con classifications de PII |
| **Snowflake (legacy)** | DW analítico legacy con 20+ SPs que producen tablas para Tableau (durante la migración) | Registrado, scan semanal; lineage upstream desde Sybase = caja negra (carga legacy fuera del scope del proyecto) |
| **ADLS Gen2 (bronze/silver/gold)** | Data lake medallion; **gold = tablas Delta** (`dim_*`, `fact_*`) que sirven a BI vía SQL Warehouse | Registrado, scans incrementales, resource sets agrupan particiones |
| **ADF** | Orquestador de ingesta Sybase → bronze (Copy con SHIR) y trigger de notebooks Databricks | Linked a Purview → lineage automático en Copy activities |
| **Databricks (workspace + Unity Catalog)** | Cómputo PySpark — **20+ notebooks que reimplementan los SPs de Snowflake** sobre Delta + **SQL Warehouse expone gold Delta a Tableau** | Unity Catalog sincronizado a Purview; lineage de notebooks vía OpenLineage en init script del cluster |
| **Key Vault** | Secretos (conn strings, tokens, credentials de SHIR) | No se registra (no contiene metadatos de negocio) |
| **Tableau** | Consumo BI; durante migración cada dashboard se repointa de Snowflake → Databricks SQL Warehouse al validar paridad | No registrado en Purview (no soportado nativo) |
| **Purview** | Gobierno: catalog, lineage, classifications | — |

---

## 4. Estructura de collections en Purview

Decisión de diseño: **organizar por dominio de negocio**, no por tipo de recurso. Esto facilita asignar stewards por dominio.

```
mycompany-purview-prod (root)
└── Colmena
    ├── Sales            ← lead generation, conversiones, partners
    ├── Underwriting     ← suscripción de pólizas, evaluación riesgo
    └── Claims           ← siniestros, pagos, peritajes
```

Cada collection tiene asignados:
- **Collection Admin:** team lead del dominio
- **Data Steward:** analista funcional senior
- **Data Curator:** ingeniero de datos del equipo
- **Data Reader:** todo el equipo del dominio

---

## 5. Scans configurados

| Source | Tipo de scan | Frecuencia | Scope |
|---|---|---|---|
| Sybase (on-prem vía SHIR) | Full + classification | Semanal (sábado 22:00 hora cliente) | Schemas `policies`, `claims`, `parties` |
| Snowflake (legacy) | Full + classification | Semanal (domingo 02:00) | DB `COLMENA_LEGACY` |
| ADLS bronze | Incremental + classification | Diario (02:00) | `/bronze/colmena/*` |
| ADLS silver | Incremental + classification | Diario (03:00) | `/silver/colmena/*` |
| ADLS gold (Delta) | Incremental + classification | Diario (04:00) | `/gold/colmena/*` (dim_*, fact_*) |
| Databricks UC | Sync continuo | Real-time | Catalog `colmena` (incluye SQL Warehouse) |

**Buenas prácticas aplicadas:**
- Scans en ventana de baja carga (madrugada)
- **MSI** sobre service principals donde es posible
- **Scope** limitado a carpetas/schemas relevantes (no escanear todo el storage)
- Scan rule sets ajustados (solo formatos parquet/delta para lake)

---

## 6. Clasificaciones aplicadas

### System (built-in)
- `MICROSOFT.PERSONAL.EMAIL`
- `MICROSOFT.PERSONAL.PHONE_NUMBER`
- `MICROSOFT.FINANCIAL.CREDIT_CARD_NUMBER`
- `MICROSOFT.PERSONAL.NAME`

### Custom (Chile-specific para Colmena)
- `CL.RUT` — `^[0-9]{7,8}-[0-9Kk]$`
- `CL.POLICY_NUMBER` — `^POL-[0-9]{10}$`
- `CL.CLAIM_NUMBER` — `^CLM-[0-9]{4}-[0-9]{6}$`

Las custom classifications se aplican a columnas con `min_match_percentage = 80%` para reducir falsos positivos.

---

## 7. Sensitivity labels

Heredadas de **Microsoft Information Protection (MIP)**:

| Label | Aplicación |
|---|---|
| `Public` | Datos agregados, KPIs sin PII |
| `Internal` | Datos transaccionales sin PII |
| `Confidential` | Datos con PII (RUT, nombre, email) |
| `Highly Confidential` | Datos de siniestros + diagnósticos médicos |

Estas etiquetas alimentan **DLP** y políticas de acceso en Power BI / OneDrive.

---

## 8. Lineage end-to-end

Después de configurar la integración:

```
Sybase.policies.POLICY
        │
        ▼  (ADF Copy + SHIR: pl_sybase_to_adls_bronze)
ADLS bronze/colmena/policies/*.parquet
        │
        ▼  (Databricks notebook ex-SP: nb_bronze_to_silver_policies)
ADLS silver/colmena/dim_policy/_delta_log
        │
        ▼  (Databricks notebook ex-SP: nb_silver_to_gold_policy_monthly)
ADLS gold/colmena/fact_policy_monthly/_delta_log   ← tabla Delta gold
        │
        ▼  (Databricks SQL Warehouse — JDBC/ODBC)
Tableau dashboard "Pólizas mensuales"  ← post-repoint (antes apuntaba a Snowflake)
```

En paralelo, lineage legacy (durante migración, hasta que Snowflake se apague):

```
Snowflake.COLMENA_LEGACY.FACT_POLICY_MONTHLY (source huérfano)
        │
        ▼  (vista directa)
Tableau dashboard "Pólizas mensuales"  ← pre-repoint
```

Generado **automáticamente** porque ADF y Databricks están integrados con Purview vía Managed Identity.

---

## 9. Métricas visibles en Data Estate Insights — modelo demo

Set de KPIs que reportaría a un CDO mensualmente (modelados en el demo, no son cifras reales de Colmena):

- **Asset inventory coverage**: % del estate real catalogado (objetivo típico: 95%)
- **Classification coverage**: % de columnas escaneadas con tag (objetivo típico: 80%)
- **Glossary association**: % de tablas gold con término de negocio (objetivo: 100% en gold)
- **Stewardship coverage**: % de collections con owner asignado
- **Sensitivity label coverage**: % en assets confidential/highly confidential

> ⚠️ En la entrevista: si insisten en cifras específicas de Colmena, di "no llevábamos esos KPIs exactos en ese momento; los modelé en este demo porque entendí que era el siguiente paso natural en el programa de gobernanza".

---

## 10. Decisiones de diseño que vas a defender

1. **¿Por qué Terraform y no Bicep?** "Terraform es el estándar de facto en consultoras multi-cloud — state explícito, providers versionados, transferible si mañana hay AWS/GCP en el roadmap. Bicep sería marginalmente más simple en single-cloud Azure puro y se integra mejor con ARM, pero en una práctica como Bluetab/IBM el coste de mantener dos IaC distintos por cliente no compensa."

2. **¿Por qué scans incrementales y no streaming?** "Purview no soporta metadata streaming nativo. El batch incremental nocturno tiene buena relación costo/freshness para el caso de uso de catalogación; lo crítico (auditoría) tolera 24h de lag."

3. **¿Por qué collections por dominio y no por tipo de recurso?** "Porque el RBAC se hereda por collection, y los stewards y owners son por dominio, no por tecnología. Si organizara por 'todo ADF / todo Databricks' tendría que duplicar permisos."

4. **¿Por qué MSI sobre SP?** "Cero rotación de secretos, audit nativo en Azure AD, y elimina el riesgo de credenciales en Key Vault. SP solo cuando MSI no es soportado (algunas SaaS sources)."
