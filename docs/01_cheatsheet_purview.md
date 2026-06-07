# Cheatsheet — Microsoft Purview

> Esta es tu guía de fundamentos. Léela 2 veces antes de la entrevista. Lo que está en **negrita** debes saber decir de memoria.

---

## 1. Qué es Microsoft Purview

**Microsoft Purview** (rebranded desde *Azure Purview* en 2022) es la **plataforma unificada de gobernanza, riesgo y cumplimiento de datos de Microsoft**. Combina:

- **Azure Purview** (gobernanza de datos: catálogo, lineage, clasificación)
- **Microsoft Purview Compliance** (DLP, eDiscovery, Information Protection — antes Microsoft 365 Compliance)

En esta entrevista te van a preguntar mayormente sobre la parte de **gobernanza** (data map, catalog, lineage, insights).

**Pitch corto (memoriza):**
> "Microsoft Purview es la plataforma unificada de gobernanza de datos de Microsoft. Te permite crear un mapa de todos tus datos en cloud, on-premise y SaaS, descubrirlos automáticamente vía scans, clasificarlos, etiquetarlos, ver su linaje punta a punta y medir la salud de tu estate de datos."

---

## 2. Componentes principales

### 2.1 Data Map
**Es la columna vertebral de Purview.** Almacena los metadatos de todos los assets registrados: bases de datos, tablas, archivos, dashboards, pipelines.

- Modelado tipo **grafo** (assets + relaciones)
- Construido sobre **Apache Atlas** (open metadata standard)
- Crece automáticamente con cada **scan**
- **Capacity Units (vCore)**: unidad de cómputo y throughput. Mínimo 1 vCU (~$0.411/hora). Escala elástica.

### 2.2 Data Catalog
**La interfaz para que usuarios de negocio busquen y entiendan los datos.**

- Búsqueda por nombre, tipo, clasificación, glosario
- Vista de **schema, lineage, clasificación, owners, descripción**
- **Glossary terms** (términos de negocio)
- **Contact roles**: data owner, data steward, expert

### 2.3 Data Estate Insights (DEI)
**Dashboards ejecutivos sobre la salud del estate de datos.**

- % de assets escaneados, clasificados, con glossary
- Distribución de clasificaciones (PII, financial, etc.)
- Assets sensibles más accedidos
- Coverage de stewardship

> **Pregunta probable:** "¿Para qué sirve Data Estate Insights?"
> **Respuesta:** "Te da una visión ejecutiva del cumplimiento de gobernanza: cuántos assets están catalogados, clasificados y tienen owner asignado. Lo uso para reportar al CDO el avance de iniciativas de gobierno."

### 2.4 Data Policy / Data Sharing (avanzado)
- **Data Policy:** asignar permisos de acceso a datos *desde* Purview (access policies sobre SQL, Storage).
- **Data Sharing:** compartir datasets entre tenants sin moverlos.

---

## 3. Conceptos operativos

### 3.1 Collections
**Jerarquía organizacional de Purview.** Carpetas anidadas que agrupan assets, sources y permisos.

- Heredan **RBAC** del padre
- Top-level = nombre de la cuenta Purview (root)
- Buena práctica: estructurar por **dominio de negocio** o **business unit**

```
Root (mycompany-purview)
├── Finance
│   ├── Sales
│   └── Accounting
├── Marketing
└── Operations
```

### 3.2 Sources
**Sistemas de datos registrados.** Soporta nativamente:

- **Azure:** Storage (ADLS, Blob), SQL DB, SQL DW/Synapse, Cosmos DB, Data Factory, Databricks, Power BI
- **AWS:** S3, Redshift, RDS
- **GCP:** BigQuery
- **SaaS:** Snowflake, Salesforce, SAP, Teradata, Oracle, MySQL, PostgreSQL
- **On-premise:** via **Self-hosted Integration Runtime (SHIR)**

### 3.3 Scans
**Proceso que extrae metadatos desde una source.**

- **Scan rule set:** qué tipos de archivo escanear y qué clasificaciones aplicar
- **Schedule:** una vez, diario, semanal
- **Incremental scans:** detectan cambios desde el último scan
- **Trigger manual o automático**

Buenas prácticas:
- Usar **MSI (Managed Identity)** sobre Service Principal cuando sea posible
- **Scope** los scans (no escanear todo el lake si solo necesitas una carpeta)
- **Programar** scans en ventanas de baja carga

### 3.4 Classifications
**Etiquetas que identifican el tipo de dato.**

Dos tipos:
- **System (200+ built-in):** Credit Card Number, SSN, Email, Phone, IBAN, etc.
- **Custom:** patterns regex o data dictionary

```yaml
# Ejemplo de custom classification rule
name: PE_DNI
description: Número DNI peruano
pattern: ^[0-9]{8}$
minimum_match_percentage: 80
```

> **Importante:** las clasificaciones se aplican durante el scan, no en tiempo real. Si cambias una regla, debes re-escanear.

### 3.5 Sensitivity Labels
**Etiquetas de sensibilidad** (Confidential, Highly Confidential, Public). Vienen del **Microsoft Information Protection (MIP)** y se aplican vía Purview.

Diferencia con clasificaciones:
- **Classification** = qué *contiene* el dato (PII, financial)
- **Sensitivity label** = qué tan *sensible* es y qué políticas aplicar (acceso, retención, encryption)

### 3.6 Glossary
**Diccionario de términos de negocio.**

- "Cliente activo" = cliente con compra en últimos 90 días
- Se asocia a tablas/columnas técnicas
- Soporta **jerarquías, sinónimos, acrónimos**
- Aprobaciones tipo workflow (draft → approved)

### 3.7 Lineage
**Trazabilidad punta a punta del flujo de datos.**

- **Automático** cuando integras Purview con: ADF, Synapse Pipelines, Power BI, Databricks (Unity Catalog), Spark via hooks
- **Manual** vía API para sources no soportadas
- Granularidad: dataset y columna (column-level lineage para SQL en source supported)

---

## 4. Roles y RBAC en Purview

| Rol | Permisos |
|---|---|
| **Collection Admin** | Gestiona la colección, asigna roles |
| **Data Source Admin** | Registra y configura scans sobre sources |
| **Data Curator** | Edita metadatos, glossary, classifications |
| **Data Reader** | Solo lectura del catálogo |
| **Policy Author** *(preview)* | Crea data access policies |
| **Insights Reader** | Acceso a Data Estate Insights |

**Granularidad:** los roles se asignan **por collection**, no globalmente.

---

## 5. Integraciones críticas (las que vas a defender)

### 5.1 Azure Data Factory
- **Lineage automático**: conecta ADF con Purview desde el portal de ADF (Manage → Purview)
- Cada **Copy Activity** y **Data Flow** publica lineage al Data Map
- Requiere que ADF y Purview estén en el **mismo tenant**

### 5.2 Azure Databricks
- **Antes de Unity Catalog:** integración via OpenLineage / Spark listener
- **Con Unity Catalog (recomendado actual):** sync nativo bidireccional Unity ↔ Purview
- **Scans Hive Metastore:** soportados directamente

### 5.3 Azure SQL / Synapse
- **Scans** automáticos (schema, samples para clasificación)
- **Column-level lineage** en Synapse pipelines y SQL pools dedicados

### 5.4 Power BI
- Tenant-wide scan
- Lineage desde dataset → report → dashboard
- Endorsement (Promoted, Certified) visible en Purview

### 5.5 Snowflake
- Scan nativo
- Clasificación de columnas
- Lineage a nivel objeto (no column-level desde Snowflake)

---

## 6. Pricing (resumen)

| Componente | Costo aproximado |
|---|---|
| **Data Map capacity** | ~$0.411/hora por vCU (mínimo 1 vCU = ~$295/mes) |
| **Scans** | $0.63/vCore-hora de cómputo de scan |
| **Data Insights generation** | Incluido (procesado en background) |
| **Resource set / Advanced Resource Set** | Tier adicional |

**Optimización:** apaga Purview cuando no lo uses (delete + redeploy con IaC), usa scans incrementales, scope correcto.

---

## 7. Limitaciones que debes conocer

- **No es real-time:** los metadatos se actualizan vía scans (no streaming)
- **Lineage column-level** solo en sources supported (no todas)
- **Capacity Units no escalan a 0** (mínimo 1 vCU mientras la cuenta exista)
- **Multi-tenant compartido limitado** (Data Sharing tiene restricciones)
- **No reemplaza** a Microsoft Defender for Cloud (seguridad) ni a Azure Policy (compliance de recursos)

---

## 8. Cómo se diferencia de competidores (te lo pueden preguntar)

| | Purview | Collibra | Alation | Unity Catalog |
|---|---|---|---|---|
| **Cobertura cloud** | Azure-first, multi-cloud | Multi-cloud agnóstico | Multi-cloud | Databricks-only |
| **Lineage** | Auto en stack MS, manual fuera | Auto via connectors | Auto via SQL parsing | Auto en Databricks |
| **Pricing** | Capacity-based | Per-user license | Per-user license | Incluido en DBX |
| **Sweet spot** | Stack Azure/M365 | Enterprise complejo multi-vendor | Self-service analytics | Pure Databricks |

---

## 9. Frases de poder para la entrevista

Memoriza estas y úsalas naturalmente:

1. "El **Data Map** es el grafo de metadatos que sirve de fuente de verdad para todo el catálogo."
2. "Estructuramos las **collections** por dominio de negocio para que el RBAC sea heredable y fácil de mantener."
3. "Para clasificaciones de datos peruanos (DNI, RUC) creamos **custom classifications** porque las built-in solo cubren US/EU."
4. "Configuramos **scans incrementales** semanales para no impactar la performance del source y mantener metadata fresca."
5. "El **lineage automático** entre ADF y Purview nos permitió eliminar la documentación manual de pipelines."
6. "Usamos **Data Estate Insights** para reportar al CDO el progreso del programa de gobernanza."
7. "Aplicamos **Managed Identity** en los scans para evitar credenciales en Key Vault."
8. "Combinamos **classifications** (qué dato es) con **sensitivity labels** (qué tan sensible) para alimentar policies de DLP."
