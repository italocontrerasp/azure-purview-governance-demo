# Interview Script — Sesión técnica conversacional (español)

Guion para la entrevista **Bluetab — Azure Purview Specialist**. Modalidad: **sesión técnica única, en español, sin compartir pantalla, vía videollamada**.

> Este doc reemplaza al antiguo `demo_script.md`. Como no hay pantalla, todo es **narrativa verbal**.

> Antes de leer este script, lee **`docs/07_facts_canon.md`** — define el framing, los facts canónicos, y qué SÍ / qué NO digas que hiciste tú.

---

## 0. El framing (recuérdalo siempre)

> "En Colmena la infraestructura de Purview la lideró el líder técnico. Yo me hice cargo del trabajo de configuración continua (registro de sources de mis pipelines, scans, custom classifications LATAM) y uso día-a-día (catálogo, lineage, etiquetado). La administración de plataforma profunda — el resto — la armé en un demo end-to-end para tener experiencia hands-on de esa parte."

Esta línea es **tu ancla**. Si pierdes el rumbo en cualquier respuesta, vuelve a ella.

---

## 1. Pre-entrevista checklist (mismo día, 30 min antes)

- [ ] Vaso de agua a mano
- [ ] Micro y cámara probados (joinear 5 min antes para asegurar)
- [ ] `docs/07_facts_canon.md` abierto en otra pestaña (NO en la misma pantalla que la videollamada — ventana aparte o segundo monitor / celular)
- [ ] Bloc físico + lápiz al lado (para escribir números/palabras clave que te diga el entrevistador)
- [ ] CV abierto en otra pestaña por si te citan un bullet
- [ ] **Repaso mental del framing del bloque 0 — léelo en voz alta una vez antes de entrar**
- [ ] Notificaciones del sistema OFF (no quieres que suene un mensaje a la mitad)
- [ ] Cierre todas las apps que consuman ancho de banda (Spotify, Dropbox sync, etc.)

---

## 2. Pitch de apertura (90 segundos memorizado)

Cuando te digan "**cuéntame de tu experiencia con Purview**", esta es tu respuesta de apertura. **Memorízala literal.**

> "En Applaudo Studios, durante 8 meses entre diciembre 2023 y julio 2024, fui parte del equipo de 3 ingenieros que migró la plataforma analítica de **Colmena**, una aseguradora chilena de salud. El sistema transaccional, **Sybase on-prem**, no cambió. Lo que migramos fue el **DW analítico**: antes era Snowflake con 20+ stored procedures que producían las tablas para los dashboards de Tableau del área comercial, y lo movimos a una arquitectura medallion sobre **Databricks + Delta gold en ADLS**, reimplementando cada SP como un notebook PySpark. Durante esos 8 meses ambas rutas convivieron en **dual-load** desde Sybase, y los dashboards de Tableau se fueron repointando de Snowflake a Databricks SQL Warehouse tabla por tabla, al validar paridad.
>
> En el stack que definió el líder técnico estaba Microsoft Purview como capa de gobernanza. La infraestructura inicial — despliegue del recurso, jerarquía de collections, RBAC base, el **Self-Hosted Integration Runtime para que Purview pudiera escanear Sybase on-prem** — la lideró él. Yo me hice cargo del trabajo continuo: **registrar las sources de mis pipelines, configurar los scans incrementales, crear las custom classifications para identificadores chilenos como RUT y números de póliza, y validar el lineage de mis pipelines en el catálogo**. Además era usuario diario del catálogo: buscar tablas antes de construir nuevas, seguir lineage para impacto downstream, etiquetar columnas sensibles, asociar términos de glosario.
>
> Para esta vacante quise asegurarme de dominar también la parte de administración de plataforma — que en Colmena no era mi área principal — así que armé un proyecto demo end-to-end con IaC en Terraform aplicada efectivamente sobre Azure: cuenta Purview `pv-italodemo-16de97`, ADLS con bronze/silver/gold materializados, Databricks corrió los notebooks, registré la source ADLS y disparé 3 scans con estado Succeeded, creé las 3 custom classifications LATAM (RUT, póliza, siniestro), modelé el RBAC del data plane vía policystore, emití el lineage end-to-end vía Atlas API conectando Sybase manual → bronze → silver → gold más el path legacy Sybase → Snowflake, y corrí el patrón de **validación de paridad Snowflake↔Delta** con publicación de tags `migration_status=ready` en Purview. Todo está en el repo con los outputs de cada script. Eso me permite hablar con confianza del rol full — config, admin y uso."

> **Por qué funciona:** abres con experiencia real (Colmena), nombras Purview en la lista del stack (consistente con tu CV), declaras explícitamente qué hiciste tú y qué no, y cierras posicionando el demo como **iniciativa proactiva** que cubre el gap. Es honesto-defensivo y la JD pide "proactivo y autodidacta".

---

## 3. Respuestas niveladas (30s / 2min / 5min)

Para cada pregunta probable, tres niveles según cuánto espacio te den.

### 3.1 "¿Qué es Microsoft Purview?"

**30s:** "Es la plataforma unificada de gobernanza de datos de Microsoft. Permite construir un mapa de metadatos de todos los datos de la organización — cloud, on-premise, SaaS — descubrirlos vía scans, clasificarlos, ver su lineage, y medir la salud del estate vía dashboards ejecutivos."

**2min:** *(30s + lo siguiente)* "Por dentro está construido sobre **Apache Atlas**, un estándar abierto de metadatos, lo que le da el modelo grafo. Tiene cuatro componentes principales: **Data Map** que es la columna vertebral con el grafo de assets y relaciones; **Data Catalog** que es la interfaz de descubrimiento para usuarios de negocio y técnicos; **Data Estate Insights** que son dashboards ejecutivos sobre la salud del catálogo; y **Data Policies** que es la parte más nueva, asignar permisos de acceso a datos desde Purview mismo. La gobernanza no es solo un catálogo — es trazabilidad, clasificación, y stewardship."

**5min:** *(2min + lo siguiente)* "Vale la pena destacar el rebrand: hasta 2022 se llamaba **Azure Purview** y solo cubría gobernanza. Microsoft fusionó esa marca con su suite de compliance — DLP, Information Protection, eDiscovery — bajo el paraguas **Microsoft Purview**. En esta entrevista entiendo que el foco es la parte de gobernanza original, pero conceptualmente las dos partes comparten labels e identidad — por ejemplo las sensitivity labels que se aplican vía MIP las consume Purview para auto-clasificación. Y el modelo Atlas le permite a Purview integrar lineage de sistemas heterogéneos: ADF y Databricks en MS stack publican nativo, pero también puedes meter Snowflake, dbt, Airflow vía OpenLineage o vía el Atlas API directamente."

### 3.2 "¿Diferencia entre Data Map, Data Catalog y Data Estate Insights?"

**30s:** "Data Map es el backend, el grafo de metadatos basado en Atlas. Data Catalog es el frontend para que data users busquen y entiendan los datos. Data Estate Insights son los dashboards ejecutivos para el CDO o el oficial de compliance. Backend, frontend de usuario, frontend ejecutivo."

**2min:** *(30s +)* "El **Data Map** es donde viven los assets y sus relaciones — tablas, columnas, archivos, pipelines, dashboards y las relaciones entre ellos. Crece automáticamente con cada scan. El **Catalog** sirve para buscar por nombre, classification, glossary term, owner — y entrar a la página del asset para ver schema, lineage, classifications, owners. El **DEI** te da el cuánto: porcentaje de assets con classification, con owner, con término de glosario; trends; assets sensibles más accedidos. En el día a día como ingeniero vives en Data Map y Catalog. DEI lo abres una vez al mes para reportar."

### 3.3 "¿Diferencia entre classification y sensitivity label?"

**30s:** "Classification responde a 'qué tipo de dato es esto' — Credit Card Number, Email, RUT chileno. Sensitivity label responde a 'qué tan sensible es' — Public, Confidential, Highly Confidential. La label se calcula a partir de las classifications vía regla de negocio."

**2min:** *(30s +)* "Las classifications las configura el equipo técnico de gobernanza — son objetivas, un regex matchea o no. Las sensitivity labels son una decisión de negocio sobre el nivel de protección, y son las que viajan con el dato — si copias un archivo etiquetado a tu OneDrive, la label persiste. En Colmena teníamos custom classifications para identificadores chilenos. Para sensitivity labels — la parte MIP — eso lo gestionaba el equipo de seguridad del cliente, no nosotros como ingeniería."

### 3.4 "¿Cómo funciona el lineage en Purview?" — **pregunta clave**

**30s:** "Tres mecanismos. **Automático nativo** desde ADF y Synapse para Copy activities y Data Flows. **OpenLineage** o sync nativo desde Databricks. Y **manual vía Atlas REST API** para todo lo que no es soportado nativamente. La realidad es que en un estate grande usas los tres."

**2min:** *(30s +)* "Cada uno tiene su trade-off. El **automático ADF** es gratis pero solo cubre Copy y Data Flow — no Notebook activity, no Stored Procedure, no Lookup. Si tu pipeline ejecuta un Notebook, ese tramo es **caja negra** para ADF. **OpenLineage en Databricks** es un Spark listener que se carga vía init script del cluster; cada read/write emite un evento al endpoint Atlas de Purview. El **Atlas API manual** es para los casos donde nada de lo anterior llega — típicamente legacy: stored procedures de Snowflake, scripts ad-hoc, BI tools sin connector. Es código que mantienes tú."

**5min:** *(2min +)* "Sobre la granularidad: **dataset-level** siempre, **column-level** solo en algunas combinaciones — depende de que el connector lo emita. Por ejemplo, Copy ADF emite column-level solo si configuraste el column mapping en el activity. OpenLineage emite column-level desde versiones recientes si no deshabilitaste el facet. Atlas API permite emitir column-level pero es caro de mantener a mano. En Colmena, a nivel table teníamos buena cobertura desde el principio. Column-level lo veíamos en silver→gold en Databricks, no en los tramos legacy. La regla práctica es: column-level solo donde compensa el coste — assets sensibles, tablas financieras. No es gratis ni en almacenamiento ni en performance de la UI."

### 3.5 "¿Cómo se modelan las collections?" — **pregunta clave**

**30s:** "Como árbol jerárquico que refleja la estructura de gobernanza de negocio — por dominio o business unit, **no por tecnología**. El RBAC se hereda hacia abajo. Es la decisión de diseño más importante porque después es muy difícil reestructurar."

**2min:** *(30s +)* "En Colmena el árbol fue: raíz, debajo una collection 'Colmena' que agrupaba todo el cliente, y debajo sub-collections por dominio de negocio — Sales, Underwriting, Claims — y una transversal Platform donde iban ADF y Databricks porque servían a todos los dominios. El error típico que veo es modelar por tecnología — collection 'ADLS', collection 'SQL'. Eso no escala porque el negocio no piensa por tecnología y el RBAC se vuelve imposible de mantener. Una buena estructura de collections demuestra que entiendes que la gobernanza es una disciplina de negocio, no de TI."

### 3.6 "¿Cuáles son los roles de RBAC?"

**30s:** "Cinco roles principales en el data plane: **Collection Admin** que gestiona la collection y asigna roles; **Data Source Admin** que registra sources y configura scans; **Data Curator** que edita assets, classifications y glossary; **Data Reader** que solo lee; e **Insights Reader** para acceso a DEI."

**2min:** *(30s +)* "Una sutileza importante: **Data Curator NO puede registrar sources ni correr scans**, eso es Data Source Admin. Estos dos se complementan — en proyectos pequeños los tiene la misma persona, en grandes se separan. Y la otra sutileza: hay **dos planos** de permisos. **Azure RBAC** sobre el recurso Purview se le da a 2-3 personas de plataforma para mantener el recurso. **Collection RBAC** es el data plane, lo que rige quién puede ver y editar el catálogo. El 70% de los candidatos confunde estos dos planos. La regla es: trabajo diario en el catálogo se gobierna con collection RBAC, no con Azure RBAC del recurso."

### 3.7 "¿Cómo creaste custom classifications para identificadores chilenos?" — **pregunta probable**

**30s:** "Una classification custom se compone de la **etiqueta semántica** — por ejemplo `CL.RUT` con prefijo por país — y la **rule** que la detecta. La rule combina un data pattern, regex sobre el contenido, y un column pattern, regex sobre el nombre de la columna. Threshold típico 80%."

**2min:** *(30s +)* "Para el RUT chileno el data pattern fue `^[0-9]{7,8}-[0-9Kk]$` y el column pattern algo como `(?i)(rut|run|id_persona)`. El column pattern es crítico — sin él, Purview analiza cada columna numérica del estate buscando RUTs, que es lento y ruidoso. Para validar antes de subir, probé el regex contra una lista de ejemplos: válidos con K mayúscula y minúscula, demasiado cortos, demasiado largos, con dígito inválido. Solo después de pasar todos lo apliqué al scan rule set. Y la convención de naming: prefijo por país — `CL.`, `PE.`, `MX.` — para evitar colisiones cuando entre otro cliente."

### 3.8 "¿Cómo monitoreabas scans?"

**30s:** "Los scans se ven en Data Map → Sources → el source → pestaña de scans. Status, duración, assets descubiertos, errores. En producción además mandábamos los logs a Log Analytics y teníamos alerta vía Azure Monitor sobre la métrica de `ScanFailedCount`."

**2min:** *(30s +)* "El error típico era credencial expirada o permiso faltante en una source nueva. Las dos causas son distintas: credencial expirada se ve como auth failure y se arregla rotando en Key Vault y refrescando la credential en Purview; permiso faltante es típicamente que la MSI no tiene acceso a un container o schema nuevo. Para sources grandes el otro error común es timeout — la solución es subir temporalmente el capacity unit del Data Map o reducir el scope del scan. Los scans recurrentes siempre deben ser incrementales, no full."

### 3.9 "Y tú, ¿qué hacías con Purview en el día a día?" — **pregunta de uso, no de admin**

Esta pregunta busca distinguir entre "lo desplegaste" (plataforma) vs "lo usaste" (data engineer). Tu respuesta cubre el segundo lado con detalle concreto.

**30s:** "Cinco cosas, todos los días. **Search-before-build** en el catálogo antes de empezar cualquier pipeline. **Validar lineage** de mis pipelines después de cada deploy. **Revisar y completar classifications** de las tablas que producía. **Impact analysis** vía lineage downstream antes de cambiar un schema. Y **asociar términos de glosario** a tablas gold para que los analistas las encontraran por concepto de negocio."

**2min:** *(30s + lo siguiente)* "El primero — **search-before-build** — era el más útil. Antes de levantar un pipeline nuevo, buscaba en el Data Catalog si la tabla ya existía en algún lado, quién la había construido, qué classifications tenía. Más de una vez evité duplicar trabajo porque encontré que un compañero ya había materializado lo que yo iba a construir. El segundo — **validar lineage** — era operacional: corría mi pipeline, esperaba 5-10 minutos, abría el asset en el catálogo, confirmaba que el grafo upstream/downstream estuviera completo. Si faltaba, troubleshooting: típicamente activity de Notebook en ADF en lugar de Copy, que es caja negra para el lineage automático. El tercero — **completar classifications** — era manual: después de un scan, revisar las columnas que el detector automático no había clasificado y aplicar tag manual si correspondía. Por ejemplo, un campo `cliente_codigo` que era RUT enmascarado y el regex no pillaba. El cuarto — **impact analysis** — era preventivo: antes de renombrar una columna o cambiar tipo, abrir el asset en Purview y mirar lineage downstream para ver qué dashboards o pipelines la consumían. Eso ahorraba reuniones de coordinación. El quinto — **glossary** — era de stewardship ligero: cuando publicaba una tabla gold, le asociaba el término de negocio correspondiente (`Prima Mensual`, `Siniestro Pagado`) para que los analistas funcionales la encontraran por concepto, no por nombre técnico."

**5min:** *(2min + lo siguiente)* "Hay otros tres que hacía con menor frecuencia. **Revisar el dashboard de Data Estate Insights una vez al mes**, principalmente la métrica de coverage de classifications y de glossary association — si esa métrica bajaba semana a semana, era señal de que estábamos publicando assets sin curar. **Onboarding de nuevos integrantes del equipo**: les daba un tour del catálogo como primera tarea — 'buscá las tablas de tu primer ticket en Purview antes de tocar el código'. Eso reducía dramáticamente el tiempo de ramp-up. Y **auditoría informal de PII**: cada vez que tocaba un nuevo dataset, verificaba que las classifications de RUT, email, número de póliza estuvieran aplicadas; si no, escalaba al líder técnico para que ajustara el scan rule set. En el demo del repo tengo un script `dei_dashboards.md` que documenta los KPIs que reportaría a un CDO mensual — eso es lo que en Colmena lo veía el líder técnico, no yo, pero conceptualmente lo entiendo y lo modelé para defenderlo."

> **Por qué esta pregunta importa**: es donde te diferencias de candidatos que "saben Purview teórico" pero nunca lo usaron. Concreto > abstracto. **Memoriza los 5 verbos**: search-before-build, validar lineage, completar classifications, impact analysis, glossary.

---

## 4. Preguntas operativas peligrosas + plantillas defensivas

Estas son preguntas donde la verdad técnica está en el "NO list" del `facts_canon.md`. Ten estas respuestas listas y **practícalas en voz alta el sábado**.

### 4.1 "¿Cómo desplegaste Purview, qué IaC usaste?"

> "El despliegue inicial del recurso lo lideró el líder técnico — es admin de plataforma, no parte del trabajo continuo del equipo de ingeniería. Yo conocía el resultado pero no toqué la IaC del recurso en sí. Para tener experiencia hands-on de esa parte armé el demo del repo en Terraform: el módulo `infra/modules/purview` despliega el recurso, role assignment de la MSI sobre el storage account, y bootstrap del policystore con mi OID en los 4 roles built-in. Lo apliqué efectivamente — la cuenta `pv-italodemo-16de97` corrió durante todo el demo. ¿Quieres que te explique el approach?"

### 4.2 "¿Qué versión de Purview usabas? ¿Capacity units?"

> "La que estuvo GA durante 2024. No me sé el sub-version exacto, no era información que tocara en el día a día. Sobre capacity units, el líder técnico mantenía 1 a 2 vCU como baseline y subía elásticamente durante scans masivos. Yo veía el efecto cuando un scan tardaba más de lo normal pero no gestionaba la palanca directamente."

### 4.3 "¿Cómo se llamaba tu cuenta de Purview?"

> "Convención estándar tipo `pv-<cliente>-<env>`. No me siento cómodo dando nombres exactos del cliente sin checar primero con ellos por temas de privacidad."

### 4.4 "¿Cómo conectaste ADF a Purview, paso a paso?"

> "La conexión inicial la hizo el líder técnico desde ADF Studio, Manage → Purview, vía MSI de ADF. Lo que yo verificaba en mis pipelines era que el lineage estuviera apareciendo: corría un pipeline, esperaba 5-10 minutos, validaba en Data Catalog. Cuando NO aparecía, la causa típica eran activities de Notebook en vez de Copy — esas no emiten lineage."

### 4.5 "¿Cómo configuraste OpenLineage en Databricks?"

> "OpenLineage estaba configurado en el init script del cluster por el líder técnico — el jar, las propiedades de Spark, el secret scope para el token. Yo era usuario del resultado, no del setup. En el demo del repo tomé un camino más simple para el lineage: emití los Process entities directamente via Atlas API desde `demo/scripts_exec/pv_push_lineage_new.py`, lo que me dio el grafo end-to-end sin depender de que el cluster tuviera OpenLineage operativo. El setup OL completo (jar + spark.conf + secret scope) lo tengo documentado conceptualmente y lo aplicaría en el cliente."

### 4.6 "¿Cómo se asignan roles RBAC vía API?"

> "Vía el endpoint `policystore/metadataPolicies`. El flujo es: GET el policy actual, recorrer `attributeRules`, inyectar el OID del principal en el array `attributeValueIncludes` de la rule correspondiente, y PUT el policy entero — no construyes uno desde cero porque el shape cambia entre versiones preview. En Colmena el RBAC inicial lo configuró el líder técnico. En el demo este patrón está en `demo/scripts_exec/pv_assign_self_roles.py` — quedó como red de seguridad idempotente porque Terraform ya me había dejado los 4 roles built-in via bootstrap del policystore. Para cliente lo evolucionaría a un YAML versionado con sync vía CI pipeline."

### 4.7 "Muéstrame el regex exacto que escribiste"

> "El del RUT chileno fue `^[0-9]{7,8}-[0-9Kk]$`. El número de póliza fue `^POL-[0-9]{10}$`. El número de siniestro `^CLM-[0-9]{4}-[0-9]{6}$`. En el demo el threshold quedó en 60% porque el dataset mock es chico — empecé con 80% y el RUT no llegaba al umbral; bajé a 60% y aparecieron las classifications en el rescan. En cliente con datos limpios y volumen alto el threshold sano es 80-90%. Los 3 regex y rules están en `demo/scripts_exec/pv_create_classifications.py`."

### 4.8 "¿Cuántos assets tenían catalogados?"

> "Alrededor de 200 assets entre Sybase on-prem (cataloga vía SHIR), Snowflake legacy, y los containers de ADLS bronze/silver/gold (gold como tablas Delta servidas a Tableau vía Databricks SQL Warehouse). No era un estate gigante, pero tenía la complejidad de un origen on-prem, un DW legacy en migración, y PII regulada por ley chilena."

### 4.9 "¿Qué error te dio el primer scan de Sybase / Snowflake?"

> "Para Sybase, el típico de SHIR — al inicio el ODBC driver de Sybase no estaba instalado en la VM del IR; el scan fallaba con un connection error genérico hasta que el líder técnico lo instaló. Para Snowflake, el típico de permisos — la cuenta de servicio no tenía el rol con `USAGE` y `MONITOR` sobre todos los schemas. El DBA del cliente lo resolvió. La configuración inicial de scans la llevaba el líder técnico — yo veía el resultado cuando algo no aparecía en el catálogo y reportaba."

### 4.10 "¿Has usado Data Policies de Purview?"

> "Las evaluamos pero estaban en preview para varias sources en ese momento. Para producción mantuvimos el control de acceso directamente en Unity Catalog de Databricks y ADLS con RBAC nativo. Conceptualmente: te permiten asignar permisos de datos desde Purview en vez de tocar la source directamente. Hoy con Data Policies más maduras, en un proyecto nuevo las usaría como capa de abstracción."

---

## 5. Preguntas comportamentales — anclas

### 5.1 "Cuéntame de un desafío técnico"

> "El mayor desafío fue **gobernar la migración durante el dual-load**. Sybase on-prem alimentaba dos caminos en paralelo: el legacy hacia Snowflake con SPs, y el nuevo hacia Delta gold en Databricks. La pregunta crítica era cuándo cambiar cada dashboard de Tableau de Snowflake a Delta sin romper nada. Lo resolvimos **en equipo** con un patrón de validación de paridad: un notebook nightly comparaba row count, checksums por PK y diff de valores no-clave por par `(tabla_snowflake, tabla_delta)`. El líder técnico definió el modelo de thresholds y la regla de N días consecutivos; **yo me encargué de la implementación PySpark del notebook de paridad y la integración con Purview vía Atlas API** — escribir el custom attribute `migration_status=ready` en el asset Delta cuando una tabla pasaba el umbral 7 días seguidos. El equipo de BI filtraba por ese tag en el catálogo para saber qué podían repointar. Eso convirtió la decisión de migración en un proceso gobernado y auditable, no un Slack thread. En el demo de este repo está la corrida real: `nb_dq_parity` materializó `parity_report` como Delta, 4 de 5 tablas pasaron el umbral, y el script de marcado vía Atlas API publicó `migration_status=ready` con 200 OK en los 4 assets gold. La quinta la dejé fallando a propósito para mostrar el caso negativo. El patrón está documentado en `scripts/nb_dq_parity.md`."

### 5.2 "¿Cómo manejaste un desacuerdo técnico?"

> "Hubo discusión sobre si usar Hive metastore o esperar a Unity Catalog en Databricks. Yo prefería esperar a Unity por el sync nativo bidireccional con Purview que iba a salir. El líder técnico decidió Hive porque el timeline del cliente no daba para esperar a Unity Catalog en GA. Su criterio fue el correcto en retrospectiva — habernos atrasado por una feature en preview habría sido un riesgo. Lo que sí incluimos como deuda técnica documentada fue 'migrar a Unity en una fase 2'."

### 5.3 "¿Qué harías diferente?"

> "Tres cosas. Habilitaría Unity Catalog en Databricks desde el día uno para tener column-level lineage nativo. Formalizaría el rol de data steward del lado del cliente — en Colmena el conocimiento de negocio venía de workshops con analistas funcionales pero sin rol formal, y eso hacía que el glossary creciera lento. Y automatizaría la creación de custom classifications con Terraform o REST API desde el principio en vez de hacerlas por UI."

### 5.4 "¿Por qué Bluetab?"

> "Tres razones. Primero, ser parte del grupo IBM significa proyectos enterprise y exposición a stacks completos, no piezas sueltas. Segundo, la cultura de 'no consultoría tradicional' coincide con cómo me gusta trabajar — más equipo, más crecimiento, menos billing puro. Tercero, técnicamente este rol me permite **pasar de implementar pipelines a diseñar y gobernar el data estate** — es la dirección a la que quiero llevar mi carrera, y el demo que armé para esta entrevista es la prueba de que ya empecé a moverme en esa dirección."

### 5.5 "¿Dónde te ves en 3-5 años?"

> "Liderando técnicamente la gobernanza de un cliente enterprise: diseño de plataforma, modelo de gobierno, RBAC, custom classifications, lineage end-to-end. Con certificación DP-700 o el equivalente vigente. Y profundizando en Microsoft Fabric, que es claramente hacia donde Microsoft está consolidando la stack."

### 5.6 "¿Cuáles son tus áreas de mejora?"

> "**Administración a nivel de plataforma de Purview** — es justamente lo que el demo cubre, lo aprendí preparándome y necesito horas reales de despliegue. Y **MIP / sensitivity labels** desde el lado de seguridad — los conozco desde Purview pero la configuración en M365 Compliance no la he hecho. Si entro a Bluetab, esos serían los primeros dos focos de profundización."

---

## 6. Preguntas trampa

### 6.1 "¿Cuál es la principal limitación de Purview?"

> "El lineage no es real-time, depende de scans batch o de eventos batched. Para auditoría regulatoria estricta que requiera trazabilidad inmediata, no la da out-of-the-box. Otra: capacity units no escalan a cero — mientras la cuenta exista, pagas un baseline. Por eso para sandboxes y demos conviene desplegar con IaC, usar, y destruir."

### 6.2 "¿Cuándo NO usarías Purview?"

> "Cuando el cliente está 100% en Databricks y Unity Catalog cubre sus necesidades sin requerir vista cross-platform. El sobrecosto no se justifica. O cuando ya tienen un Collibra/Alation maduro funcionando — la migración sería más costosa que mantener. O cuando la organización es muy chica — menos de 50 tablas, el ROI no llega."

### 6.3 "¿Microsoft Fabric vs Purview?"

> "Fabric es la plataforma analítica integrada que reemplaza el ensamblaje manual de ADF, Synapse, Power BI y Databricks. Purview es la capa de gobernanza que se mantiene sobre Fabric. Microsoft los está integrando — el OneLake catalog tiene puentes con Purview. Mi expectativa es que en 1-2 años Purview será una capa nativa dentro de Fabric, no un servicio separado, similar a Unity Catalog dentro de Databricks."

### 6.4 "Si tu CV dice Purview, ¿por qué armaste un demo?" — **pregunta trampa potencial**

> "Buena pregunta. En Colmena Purview estaba en el stack y yo trabajé con él en el día a día — registrando sources, configurando scans, creando custom classifications, validando lineage. Pero la **administración de plataforma** — despliegue, jerarquía inicial de collections, capacity tuning, RBAC base — la lideró el líder técnico. Para esta vacante, donde explícitamente mencionan **configuración + administración + uso**, armé el demo para asegurar que también la parte de administración la pudiera defender con experiencia hands-on real. Es decir: el demo no contradice mi CV, lo complementa con la parte que en Colmena no fue mi área principal."

Esta respuesta es **honesta-defensiva**. Cubre el gap sin mentir.

---

## 7. Frases puente (para cuando te traben)

| Situación | Frase |
|---|---|
| Necesitas 5s para pensar | "Buena pregunta, déjame estructurarte la respuesta en dos partes…" |
| Te llevan a algo que no sabes | "No tengo experiencia directa con esa pieza específica. Lo que sí entiendo conceptualmente es [X]. ¿Es algo que el equipo de Bluetab usa intensivamente?" |
| Te piden detalle operativo del NO list | "Esa parte la llevaba el líder técnico. Yo lo conocía conceptualmente y veía el resultado en el catálogo. En el demo profundicé en eso. ¿Te lo explico desde el demo o seguimos a otro tema?" |
| Necesitas terminar una respuesta que se está alargando | "Para no irme largo: la idea central es [resumen en una frase]. ¿Quieres que profundice en algún aspecto?" |
| Te dicen "no es exactamente así" | "Tienes razón en el matiz, gracias por la corrección. Lo que sí me queda claro es [pivote a lo que sí sabes]." *(humildad senior, no defensivo)* |

---

## 8. Cierre fuerte — preguntas que TÚ haces

Al final el entrevistador va a decir "¿alguna pregunta tuya?". **Tener 3-4 preguntas listas demuestra interés y seniority.** Memoriza estas, elige según el ritmo de la conversación:

1. "¿Cuál es el cliente actual donde se necesitaría este perfil, y en qué fase del programa de gobernanza están? Pre-implementación, ampliación, o ya estable en operación."

2. "¿Bluetab tiene una práctica de gobernanza ya formada, o este rol es parte de su construcción? Pregunto por dónde se está acumulando el conocimiento internamente."

3. "¿Qué porcentaje del rol es implementación técnica vs interacción con stakeholders de negocio del cliente?"

4. "¿Cómo miden el éxito en los primeros 90 días en este rol?"

5. "¿Qué oportunidades de certificación financia Bluetab? Tengo interés en **DP-700** y en la nueva certificación de Microsoft Fabric Analytics Engineer."

6. "¿Cómo es el modelo de trabajo híbrido — días específicos, oficina en Bogotá/Medellín?"

7. *(Solo si la conversación fue muy buena)* "¿Cuáles son los siguientes pasos del proceso y en qué timeline esperan resolver?"

---

## 9. Cierre emocional (último minuto)

> "Antes de cerrar quería decir algo. Este rol es exactamente la dirección a la que quiero llevar mi carrera — pasar de implementación de pipelines a diseño y gobierno del data estate. El proyecto demo que armé para prepararme para esta entrevista es la prueba de que ya empecé a moverme. Quedo muy interesado. Gracias por el tiempo."

Eso te deja con la última palabra cargada de **convicción real** — porque sí es lo que quieres hacer.

---

## 10. Ensayo recomendado (sáb + dom)

**Sábado tarde — 45 min:**
- Lee `07_facts_canon.md` entero, voz alta.
- Memoriza literal el **pitch de apertura (sección 2 de este doc)**. Repítelo 5 veces seguidas, sin notas.
- Practica las **plantillas defensivas del bloque 4** una por una en voz alta. **Especialmente la 4.1, 4.4, 4.5, 4.6** — son las que más probabilidad tienen de salir.

**Domingo mañana — 45 min:**
- Repaso del pitch sin notas.
- Practica las **respuestas niveladas del bloque 3** — en cada una decide cuándo cortar (30s vs 2min vs 5min) leyendo la pregunta.
- Practica las **frases puente del bloque 7** — son las que en el momento más se te van a olvidar.

**Domingo tarde — 30 min:**
- Repaso final del pitch + plantillas defensivas.
- Lee la sección 6 (preguntas trampa) y especialmente **6.4** que es la que más temo te tiren.

**Domingo noche:**
- NO estudies material nuevo. Descansa.

---

## 11. Plan B — si algo sale mal

| Si pasa esto… | …haces esto |
|---|---|
| El entrevistador insiste en detalle operativo y se nota que se da cuenta | Honestidad parcial: "Para serte transparente, esa parte específica no la operé en Colmena directamente — la armé en el demo. Mi experiencia operativa fue la configuración día-a-día y el uso. ¿Te explico desde el demo?" |
| Te quedas en blanco a mitad de una respuesta | "Disculpa, déjame retomar. La idea era…" *(retomas desde el principio del bloque, no a la mitad)* |
| Te interrumpe con preguntas seguidas y no llegaste al pitch | OK, eso es normal. Si no llegaste a contar el demo, al final di: "Antes de cerrar quería mencionar el proyecto demo que armé para esta entrevista — [3 frases]." |
| Te preguntan algo que NO está en este script ni en el Q&A | Las plantillas del bloque 7. Y honestidad: "No lo conozco específicamente. Mi entendimiento conceptual es [X]." |
| El internet falla | Llamas por teléfono desde celular para retomar — los entrevistadores entienden. Avisa por mail al instante. |

---

## 12. Recordatorio final

La entrevista no es un examen. Es una **conversación de evaluación mutua**. El entrevistador quiere saber si te puede meter al equipo y dormir tranquilo. Tu trabajo no es saberlo todo — es **mostrar criterio, honestidad, capacidad de aprender y de comunicar**.

Habla desde el caso real (Colmena), sé claro con el framing (qué hiciste tú, qué hizo el líder técnico), apóyate en el demo cuando entres a admin profunda, y devuelve preguntas cuando puedas. Si no sabes algo, **dilo con tranquilidad** — un "no lo he tocado, pero conceptualmente es X" vale más que improvisar un detalle falso.

Suerte el lunes.
