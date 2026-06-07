# Facts canónicos — Colmena + demo

Fuente única de verdad para los números, fechas, nombres y detalles del relato. **Si un doc contradice este archivo, gana este archivo.**

> Léelo el sábado y el domingo. Memorízalo. Si bajo presión te preguntan algo numérico que no está acá, recurre a las plantillas defensivas.

---

## 1. Cliente y proyecto

| Campo | Valor |
|---|---|
| Cliente | **Colmena Seguros** (aseguradora chilena, segmento salud) |
| Empresa empleadora | **Applaudo Studios** |
| Tu rol | **Data Engineer (uno de 3 en el equipo)** |
| Líder técnico | **Líder técnico de Applaudo** (no del cliente) |
| Duración del proyecto | **8 meses (Diciembre 2023 – Julio 2024)** |
| Modalidad | Híbrida, equipo distribuido LATAM |

> ⚠️ **No digas "yo lideré la migración"**. Di "**fui parte del equipo técnico que lideró la migración**" o "**el líder técnico de Applaudo lideró la iniciativa y yo me hice cargo de [tu pieza concreta]**". Esto es defendible. La primera versión no.

---

## 2. Equipo (composición)

- **1 líder técnico de Applaudo** (definió arquitectura, decidió stack incluyendo Purview, lideró integración con cliente)
- **3 data engineers de Applaudo** (tú eras uno de los tres) — migración de SPs, PySpark, pipelines ADF
- **Stakeholders del cliente Colmena** — equipo de BI y analistas funcionales con conocimiento del negocio asegurador. **No había rol formal de "data steward"** en el cliente. El conocimiento de negocio se levantaba en workshops puntuales.

> ⚠️ **No menciones "data stewards de negocio formales"**. Si te preguntan por stewardship, di: "**No había rol formal de steward en el cliente. El conocimiento de negocio venía de workshops periódicos con el equipo de Colmena. En un siguiente paso, le habríamos propuesto formalizar stewards por dominio, pero quedó fuera del scope inicial**".

---

## 3. Stack tecnológico real

| Componente | Versión / detalle |
|---|---|
| Origen OLTP (legacy, no cambió) | **Sybase on-prem** (sistema transaccional del cliente; vivía en su data center, requiere SHIR) |
| DW legacy (en migración) | **Snowflake** (DW analítico con 20+ stored procedures que producían tablas para Tableau) |
| Orquestador | **Azure Data Factory** (Copy con SHIR para Sybase, trigger de notebooks Databricks) |
| Compute (nuevo) | **Azure Databricks** (Hive metastore, sin Unity Catalog en ese momento) — los 20+ SPs de Snowflake fueron reimplementados como **notebooks PySpark** |
| Lake | **ADLS Gen2** medallion (bronze raw parquet / silver y gold como tablas Delta) |
| Serving para BI | **Databricks SQL Warehouse** sobre gold Delta (JDBC/ODBC para Tableau) |
| BI | **Tableau** (cliente, ya existía; cada dashboard se repointó de Snowflake → Databricks SQL Warehouse al validar paridad tabla por tabla) |
| Secrets | **Azure Key Vault** |
| Gobernanza | **Microsoft Purview** *(en el stack definido por el líder técnico)* |

> ⚠️ **Es "Microsoft Purview", no "Azure Purview"**. Rebrand 2022.

---

## 4. Tu interacción REAL con Purview en Colmena — framing híbrido (opción C)

**La línea exacta a defender:**

> "En Colmena, **la infraestructura inicial** del recurso Purview — despliegue, jerarquía de collections, RBAC base, conexión a ADF — la lideró el **líder técnico** del proyecto. Yo me hice cargo del **trabajo de configuración continua y uso día-a-día**: registrar las sources de mis pipelines, configurar los scans incrementales sobre los containers que mi equipo poblaba, crear las custom classifications para identificadores LATAM, y validar el lineage de mis pipelines. Es decir: **configuración y uso día-a-día sí; administración de plataforma a nivel infraestructura no era mi responsabilidad principal**."

Esto cubre los 3 verbos de la JD (**configuración + administración + uso**) sin sobreprometer.

### 4.1 Lo que SÍ puedes defender que hiciste tú directamente

**Configuración (continua):**
- "Registré las sources de mis pipelines (ADLS containers de bronze y silver donde mi equipo escribía)."
- "Configuré los scans incrementales sobre esos containers — scope acotado, ventana de domingo madrugada."
- "Definí los scan rule sets para que solo escanearan formatos Parquet y Delta, no CSV/JSON."
- "Creé las custom classifications para identificadores chilenos: RUT, número de póliza, número de siniestro. Probé los regex contra muestras antes de aplicarlos al rule set."

**Uso (diario) — los 5 verbos que defiendes:**
1. **Search-before-build**: "Antes de empezar un pipeline buscaba en el Data Catalog si la tabla ya existía, quién la mantenía y qué classifications tenía. Evité duplicar trabajo más de una vez gracias a esto."
2. **Validar lineage**: "Después de cada deploy abría el asset en el catálogo y validaba que el grafo upstream/downstream estuviera completo. Si no aparecía, troubleshooting típicamente apuntaba a activity de Notebook en ADF (caja negra para el lineage automático)."
3. **Completar classifications**: "Tras cada scan revisaba columnas que el detector automático no había clasificado y aplicaba tag manual si correspondía. Ej: un campo `cliente_codigo` que era RUT enmascarado y el regex no pillaba."
4. **Impact analysis**: "Antes de renombrar una columna o cambiar un tipo, miraba el lineage downstream del asset para ver qué pipelines/dashboards la consumían. Eso ahorraba reuniones de coordinación."
5. **Glossary**: "Al publicar una tabla gold, le asociaba el término de negocio correspondiente (`Prima Mensual`, `Siniestro Pagado`, `Cliente Activo`) para que los analistas funcionales la encontraran por concepto, no por nombre técnico."

**Además, ocasional/mensual:**
- "Revisaba el dashboard de Data Estate Insights una vez al mes para monitorear coverage de classifications y glossary association."
- "Onboarding de nuevos compañeros: les pedía que buscaran las tablas de su primer ticket en Purview antes de tocar código."
- "Participé en el workshop donde decidimos qué identificadores chilenos necesitaban custom classifications."

**Administración (parcial):**
- "Conocía la estructura de collections y los racionales de por qué eran por dominio."
- "Sabía qué roles tenía cada parte del equipo y por qué."
- "Reportaba al líder técnico cuando algo no funcionaba (scans fallidos, lineage no apareciendo)."

### 4.2 Lo que NO digas que hiciste

- ❌ "Yo desplegué Purview / hice el IaC del recurso" → fue el líder técnico
- ❌ "Yo diseñé la estructura inicial de collections" → fue el líder técnico
- ❌ "Yo asigné los roles RBAC" → fue el líder técnico
- ❌ "Yo configuré OpenLineage en los clusters Databricks" → fue el líder técnico (era infra del workspace)
- ❌ "Yo conecté ADF a Purview" → fue el líder técnico (es config de plataforma)
- ❌ "Yo configuré el Self-Hosted IR para Sybase on-prem" → fue el líder técnico (era infra de plataforma + acceso a red del cliente)
- ❌ "Yo gestionaba el capacity unit del Data Map" → fue el líder técnico
- ❌ "Yo armé las dashboards ejecutivas de DEI" → DEI lo veía el líder técnico / management

### 4.3 Cómo pivotar cuando te preguntan algo del "NO" list

> "Esa parte específica la llevaba el líder técnico — era admin de plataforma, no parte del trabajo continuo del equipo de ingeniería. Yo lo conocía conceptualmente y veía el resultado en el catálogo. Para tener experiencia hands-on de esa parte armé el demo del repo. ¿Te lo explico desde lo que aprendí en el demo o seguimos a otro tema?"

Esa frase es tu salvavidas. Memorízala.

### 4.4 El demo del repo es tu prueba de "administración"

Cuando hables del demo, **no digas "lo hice de aprendizaje porque no lo había hecho"**. Di:

> "Para asegurarme de que dominaba también la parte de administración de plataforma — que en Colmena no era mi área principal — armé este proyecto demo end-to-end. Tiene la IaC en Terraform, los scripts hands-on de registro de sources, scans, custom classifications LATAM, modelo de RBAC versionado, y la integración de lineage con los 3 mecanismos. Lo construí justamente para poder hablar con confianza del rol full — config + admin + uso — y no solo de la parte que viví en Colmena."

Eso suena **proactivo y autodidacta**, exactamente lo que la JD pide.

---

## 5. El demo (lo que SÍ hiciste de verdad — defiéndelo a fondo)

Este sí es 100% tuyo:

- **IaC en Terraform:** recursos azurerm para Purview, ADF, Databricks, ADLS Gen2 (bronze/silver/gold), Key Vault + role assignment de la MSI de Purview sobre el storage. **Sybase on-prem y Snowflake legacy quedan documentados como sources aspiracionales** (vía SHIR para Sybase, basic auth + KV para Snowflake) sin desplegarse — son la respuesta a "¿cómo gobiernas sources on-prem y SaaS?".
- **Documentación hands-on:** registro de sources, scans, custom classifications LATAM (RUT/DNI/CUIT/CPF/etc.), lineage end-to-end con los 3 mecanismos, RBAC con matriz por roles, DEI con KPIs
- **Scripts de despliegue/destrucción** para control de costos
- **Storytelling, Q&A y guion de entrevista** preparados

> Cuando te pregunten "qué hiciste para prepararte", esto es lo que respondes en detalle. Esta es la parte que **sí puedes mostrar y defender hasta el último regex**.

---

## 6. Métricas y números canónicos

> Si no figuran acá, **no los inventes en la entrevista**. Mejor decir "no llevábamos esa métrica directamente" que improvisar.

| Métrica | Valor canónico | Origen |
|---|---|---|
| Stored procedures migrados | **20+** | tu CV, real |
| Tablas/vistas migradas | "**alrededor de 50**" si insisten | aproximación segura |
| Duración del proyecto | **8 meses (Dic 2023 – Jul 2024)** | real |
| Tamaño del equipo Applaudo | **4 (3 DE + 1 TL)** | real |
| Tamaño del estate | "**unos 200 assets en el catálogo**" si insisten | conservador, defendible |
| Capacity unit del Data Map | "**2 vCU**" si insisten | razonable para ese tamaño |
| Tiempo de despliegue Purview | "**unas 2 semanas**" si insisten | tomado del 04_storytelling |
| % cobertura classification | **No des cifra específica.** Di: "no llevábamos el KPI exacto en el momento; en este demo lo modelé porque entendí que era importante" |
| Tableros Tableau impactados | "**unos 10-15**" si insisten | conservador |

> **Regla:** si dudas, **conservador y vago > preciso e improvisado**.

---

## 7. Nombres que NO inventes (cuando te pregunten)

- **Nombre exacto de la cuenta Purview** → "no recuerdo el nombre exacto del recurso, era convención estándar tipo `pv-<cliente>-<env>`"
- **Nombre de tu manager o líder técnico** → "no me siento cómodo dando nombres específicos del cliente sin checar primero con ellos por privacidad"
- **Nombres de tablas internas** → habla de tipos: "tablas de pólizas", "tablas de siniestros", "tablas de primas"
- **Versión específica de Purview** → "la que estaba GA durante 2024, no me sé el sub-version"

---

## 8. Glosario ES/EN (para no trabarte en la entrevista)

En LATAM, la mayoría de términos técnicos de Purview se dicen **en inglés**, incluso en una conversación en español. Sin embargo, hay equivalencias aceptables.

| Inglés | Español aceptable | Recomendación |
|---|---|---|
| Data Map | "el Data Map" | déjalo en inglés |
| Data Catalog | "el catálogo" / "Data Catalog" | cualquiera |
| Lineage | "el lineage" / "el linaje" | **lineage** suena más senior |
| Classification | "classification" / "clasificación" | **cualquiera, usa una y mantenla** |
| Scan | "scan" / "escaneo" | **scan** es más común |
| Collection | "collection" / "colección" | **collection** |
| Glossary | "glosario" / "glossary" | **glosario** es OK en español |
| Sensitivity label | "label de sensibilidad" | en inglés es OK |
| Source | "source" / "fuente" | **cualquiera** |
| Asset | "asset" / "activo" | **asset** (activo se confunde con financiero) |
| Scan rule set | "scan rule set" | **déjalo en inglés** |
| Data Estate Insights | "Data Estate Insights" / "los Insights" | déjalo en inglés |
| Managed Identity | "Managed Identity" / "MSI" | usa la sigla **MSI** |
| Workspace | "workspace" | inglés |
| Pipeline | "pipeline" | inglés |

> **Regla de oro:** sé consistente. Si dijiste "lineage" la primera vez, no digas "linaje" después. El cambio de léxico delata que estás traduciendo en tiempo real.

---

## 9. Tres frases puente para cuando te traben

1. **Cuando no sepas algo operativo:**
   > "Esa parte específica la llevaba el líder técnico. Yo lo conocía a nivel conceptual desde la documentación y desde lo que veía en el catálogo. En el demo del repo profundicé hasta ese detalle. ¿Lo quieres que te lo explique conceptual o entramos al demo?"

2. **Cuando quieres ganar tiempo para pensar:**
   > "Buena pregunta. Déjame estructurarte la respuesta en dos partes…" *(y ahí ya tienes 5 segundos para ordenar)*

3. **Cuando te llevan a terreno que no conoces:**
   > "No tengo experiencia directa con esa pieza. Lo que sí entiendo conceptualmente es [X]. ¿Es algo que el equipo de Bluetab usa intensivamente? Me ayuda a calibrar la importancia para profundizar después."
   *(Devolver la pregunta es senior, no evasivo)*
