# Preguntas frecuentes de entrevista — Purview Specialist

Banco de preguntas técnicas y conductuales con respuestas modelo. Practica las de "alta probabilidad" en voz alta.

> ⚠️ **Importante:** las respuestas conceptuales (A, B, C, E, F) son genéricas y aplicables sin pivote. Las **conductuales (D)** y cualquier respuesta que diga "yo configuré" deben leerse con el framing C (ver [`07_facts_canon.md`](07_facts_canon.md)): en Colmena el líder técnico llevó la admin de plataforma; tú hiciste config diaria + uso. Si una respuesta de este banco te suena más fuerte que lo que puedes defender, **modérala** con las plantillas del [`scripts/interview_script.md`](../scripts/interview_script.md) bloque 4.

---

## A. Conceptuales (alta probabilidad)

### A1. ¿Qué es Microsoft Purview y para qué sirve?
> "Es la plataforma unificada de gobernanza de datos de Microsoft. Permite construir un mapa de metadatos de todos los datos de la organización en cloud, on-premise y SaaS, descubrirlos automáticamente vía scans, clasificarlos por tipo y sensibilidad, ver su linaje punta a punta, y medir la salud del estate vía dashboards. Resuelve el problema de 'no sabemos qué datos tenemos ni dónde están' que es típico en empresas grandes."

### A2. ¿Cuál es la diferencia entre Data Map, Data Catalog y Data Estate Insights?
> "Data Map es la columna vertebral — el grafo de metadatos basado en Apache Atlas que guarda los assets y sus relaciones. Data Catalog es la interfaz de descubrimiento donde los usuarios buscan, exploran y entienden los datos. Y Data Estate Insights son los dashboards ejecutivos sobre el catálogo: coverage de clasificación, stewardship, glossary. Data Map es el backend, Catalog es el frontend para data users, e Insights es el frontend para C-level."

### A3. ¿Cuál es la diferencia entre classification y sensitivity label?
> "Una classification responde a 'qué tipo de dato es esto' — por ejemplo Credit Card Number o Email. Una sensitivity label responde a 'qué tan sensible es' — por ejemplo Confidential o Highly Confidential. Las classifications son objetivas (un patrón regex matchea o no), las sensitivity labels son una decisión de negocio sobre el nivel de protección. Las sensitivity labels vienen de Microsoft Information Protection y se aplican a partir de classifications + reglas de negocio."

### A4. ¿Cómo funciona el lineage en Purview?
> "Hay dos formas. La automática: cuando integras Purview con ADF, Synapse Pipelines, Databricks con Unity Catalog o Power BI, esos servicios publican eventos de lineage al Data Map cada vez que se ejecuta un pipeline o se actualiza un dataset. La manual: vía Atlas REST API puedes publicar lineage para sources no soportadas, como pipelines custom de Airflow. Granularidad: dataset-level siempre, column-level solo en sources supported."

### A5. ¿Qué son las collections y por qué importan?
> "Son la jerarquía organizacional de Purview, tipo carpetas anidadas. Agrupan sources y assets, y heredan permisos del padre. Su importancia es que el RBAC se asigna por collection, no globalmente. Una buena estructura de collections refleja la organización de gobernanza (por dominio o por business unit), no la organización técnica."

### A6. ¿Cómo se cobra Purview?
> "Por Capacity Units del Data Map (vCU), unas $0.40 por hora por vCU con mínimo 1 vCU, y por vCore-hora de cómputo de scans, alrededor de $0.63. El minimum baseline always-on es cerca de $290 al mes. Para proyectos de prueba conviene desplegar con IaC, usar, y destruir."

### A7. ¿Cómo se integra Purview con Azure Data Factory?
> "Desde el portal de ADF, vas a Manage → Purview y conectas la cuenta. ADF necesita Managed Identity con rol de Data Curator en la collection raíz de Purview. Una vez conectado, cada Copy Activity y Data Flow publican lineage automáticamente al Data Map. ADF y Purview deben estar en el mismo tenant Azure AD."

### A8. ¿Cómo se integra Purview con Databricks?
> "Hay dos caminos. El moderno, con Unity Catalog: configurar el sync nativo bidireccional, donde Unity expone su metastore a Purview y los cambios fluyen automáticamente. El alternativo, sin Unity: usar OpenLineage o un Spark listener que publica eventos al Atlas API de Purview cada vez que corre un job. También puedes registrar el Hive Metastore como source y escanearlo."

### A9. ¿Qué es un self-hosted integration runtime y cuándo lo necesito?
> "Es un agente que instalas en una VM o servidor del cliente para que Purview pueda escanear sources que están en redes privadas, on-premise o detrás de firewalls. Lo necesitas para SQL Server on-prem, Oracle on-prem, o cualquier source que no sea accesible desde la red de Azure. Para sources cloud-native (Azure SQL, ADLS, Snowflake público) usas el Azure Integration Runtime nativo."

### A10. ¿Qué buenas prácticas aplicarías para diseñar collections?
> "Cuatro: primero, espejar la estructura de gobernanza de negocio (dominios, business units), no la técnica. Segundo, no anidar más de 3 niveles porque el RBAC se vuelve difícil de auditar. Tercero, asignar Collection Admin, Data Curator y Data Steward por cada collection antes de poblarla con sources. Cuarto, documentar la jerarquía en el README del repo de IaC, no solo en la UI."

---

## B. Operacionales (probabilidad media-alta)

### B1. ¿Cómo programarías scans en producción?
> "En ventanas de baja carga del source (típicamente madrugada). Scans incrementales en vez de full cuando la source los soporta. Scope limitado a las carpetas o schemas relevantes — no escanear el storage entero. Capacity unit del Data Map ajustado a la ventana — si tienes 50 scans paralelos, sube vCU temporalmente. Y monitoreo de scan failures con alertas vía Azure Monitor."

### B2. ¿Cómo configurarías RBAC para un equipo nuevo?
> "Crearía una collection dedicada para el equipo bajo el dominio que corresponda. Asignaría Collection Admin al team lead, Data Curator a los ingenieros senior del equipo, Data Steward a un analista funcional con conocimiento del dominio, y Data Reader a todo el equipo. Si el equipo necesita scopes especiales (por ejemplo, ver datos de otro dominio en read-only), agregaría Data Reader cross-collection puntualmente."

### B3. ¿Cómo crearías una custom classification?
> "Defino el patrón regex o el data dictionary que identifica el tipo de dato. Por ejemplo para RUT chileno: `^[0-9]{7,8}-[0-9Kk]$`. Configuro el minimum match percentage según el balance falso-positivo/falso-negativo que tolere el negocio, típicamente 80%. Lo asocio a un scan rule set y lo aplico a las sources relevantes. Después del primer scan, valido los matches contra una muestra real."

### B4. ¿Cómo migrarías un catálogo existente (por ejemplo Collibra) a Purview?
> "Tres pasos. Primero, exportar metadatos de Collibra vía su REST API: assets, glossary terms, owners. Segundo, mapear el modelo de Collibra al modelo de Atlas/Purview (sus 'communities' a collections, 'domains' a glossary). Tercero, importar vía el Atlas API de Purview, idealmente en lotes con un script Python que maneje retry y errores. Glossary primero, luego assets, luego relaciones. Validar coverage post-migración."

### B5. ¿Cómo verificarías que Purview está catalogando todo lo que debería?
> "Comparo el inventario de Purview contra la fuente de verdad de cada source. Para ADLS, listo containers/paths y comparo. Para SQL, query a INFORMATION_SCHEMA. La diferencia me da el gap. Después me apoyo en Data Estate Insights que tiene un widget de coverage. Para producción, automatizo este check con un job que corre semanal y alerta si el gap supera 5%."

### B6. ¿Qué métricas usarías para medir el éxito de la implementación?
> "Cuatro KPIs principales: coverage de inventario (% de assets reales catalogados), coverage de clasificación (% de columnas escaneadas con tag), coverage de glossary (% de tablas críticas con término de negocio), y stewardship coverage (% de collections con owner). Una de adopción: número de búsquedas únicas por mes en el catalog. Y una financiera: costo de Purview / número de assets gobernados."

---

## C. Diseño y arquitectura (probabilidad media)

### C1. Diseña la gobernanza para una empresa con 5 BUs y 3 clouds.
> "Empezaría con una sola cuenta Purview (no fragmentar) y una jerarquía de collections con un nivel por BU y subniveles por dominio dentro de cada BU. Para multi-cloud: Azure se integra nativo, AWS S3/Redshift/RDS tienen connectors nativos, GCP BigQuery también. Para sources sin connector usaría el Atlas API. Self-hosted IR para on-premise si aplica. Un Collection Admin por BU descentralizando el gobierno pero con un equipo central definiendo classifications y glossary core."

### C2. Cómo integrarías Purview con un data mesh?
> "Las collections de Purview se mapean bien a domains de data mesh. Cada dominio tiene su collection, su Data Steward (data product owner) y su Data Curator (data product engineer). Los data products se publican como assets con glossary terms compartidos. El equipo central define el modelo de classifications cross-domain (PII, financial), pero el dueño de cada data product es responsable de aplicarlas. Purview tiene Domains en preview que formaliza este patrón."

### C3. ¿Cómo controlarías costos de Purview en producción?
> "Tres ejes. Capacity: usar el mínimo de vCU posible y escalar elásticamente solo en ventanas de scan masivos. Scan scope: limitar a paths/schemas relevantes, evitar wildcard scans sobre lakes enormes. Scan frequency: incremental sobre full siempre que la source lo soporte. Y monitoring vía cost analysis en Azure separando por etiqueta de proyecto."

---

## D. Conductuales (alta probabilidad)

### D1. Cuéntame de un proyecto donde implementaste gobernanza de datos.
> [Ver `04_storytelling_colmena.md` — usar el pitch de 90 segundos]

### D2. Cuéntame de una vez que un stakeholder no entendió la importancia de la gobernanza.
> "En Colmena el equipo comercial al inicio veía la documentación de los pipelines como burocracia que retrasaba entregas. Mi approach fue mostrarles, en una sesión corta, el ROI concreto: el tiempo que perdíamos cada semana respondiendo 'de qué tabla viene este número' cuando alguien pedía un cambio. Pasaron de tratar la documentación como deuda opcional a pedirla explícitamente en cada nuevo pipeline. No fue Purview el que los convenció — fue ver el ahorro de su propio tiempo. Lo que me quedó como aprendizaje es que la gobernanza se vende con métricas operativas concretas, no con 'es buena práctica'."

### D3. ¿Cómo manejas un desacuerdo técnico con un colega senior?
> "Trato de separar datos de opinión. Le pido los argumentos del 'por qué' detrás de su recomendación, no solo el 'qué'. Comparto los míos con la misma estructura. Si seguimos en desacuerdo, propongo un POC chico que decida con evidencia, o subimos a quien tenga ownership de la decisión. Lo que evito es ceder solo por jerarquía si tengo argumentos sólidos, pero también evito atrincherarme sin abrir la posibilidad de estar equivocado."

### D4. ¿Por qué Bluetab?
> "Tres razones. Primero, ser parte del grupo IBM significa proyectos de envergadura enterprise y exposición a stacks completos de gobernanza, no solo piezas sueltas. Segundo, su cultura de 'no consultoría tradicional' coincide con cómo me gusta trabajar — más equipo y crecimiento, menos billing puro. Tercero, técnicamente este rol me permite consolidar mi experiencia en Azure y pasar de implementar pipelines a diseñar y gobernar el data estate, que es la dirección a la que quiero llevar mi carrera."

### D5. ¿Dónde te ves en 3-5 años?
> "Liderando técnicamente una iniciativa de gobernanza completa para un cliente enterprise: diseño de plataforma de datos, modelo de gobierno, RBAC y data mesh. Idealmente con certificación DP-700 o el equivalente vigente, y con experiencia profunda en Microsoft Fabric ya que es claramente hacia dónde Microsoft está consolidando la stack. Y en paralelo, mentoreando ingenieros más junior, algo que ya hice en Miami Heat y disfruté."

### D6. ¿Qué te motiva del trabajo en equipo?
> "Que las mejores decisiones técnicas salen de buenos debates. En Colmena, las definiciones de collection structure y custom classifications no fueron mías solo — salieron de sesiones con el equipo de privacidad, el DBA y el arquitecto. Solo no habría llegado al mismo diseño. Y me energiza ver a un colega aprender algo nuevo que yo le pasé y luego mejorarlo."

---

## E. Curveballs (preguntas trampa)

### E1. ¿Cuál es la principal limitación de Purview?
> "El lineage no es real-time, depende de scans batch o de integraciones que publican eventos. Para casos de auditoría regulatoria estricta donde necesitas trazabilidad inmediata, Purview no la da out-of-the-box. Otra: las custom classifications con regex tienen limitaciones para patrones complejos, ahí a veces tienes que combinar con sampling externo."

### E2. ¿Cuándo NO usarías Purview?
> "Cuando el cliente está 100% en Databricks y Unity Catalog ya cubre sus necesidades de governance interna sin requerir vista cross-platform — el sobrecosto de Purview no se justifica. O cuando la organización es muy chica (menos de 50 tablas), el ROI no llega. O cuando ya tienen un Collibra/Alation maduro funcionando bien y la migración sería más costosa que mantener."

### E3. ¿Cómo defenderías el costo de Purview ante un CFO?
> "Cuantificaría tres ahorros: tiempo de búsqueda de datos (analistas pasan en promedio 30% del tiempo buscando vs analizando — Purview lo reduce a 10%), tiempo de auditoría (lineage automático elimina semanas de documentación manual por auditoría), y riesgo de compliance (multas evitadas por trazabilidad de PII). El costo de Purview se amortiza típicamente con 3-5 FTEs de analistas si el catálogo se usa de verdad."

### E4. Si tuvieras que enseñar Purview a un compañero en un día, ¿qué harías?
> "Una hora de teoría sobre los 4 componentes — Data Map, Catalog, DEI, Policies — y los conceptos de collection, source, scan, classification, glossary y lineage. Tres horas de hands-on en una cuenta de sandbox: registrar una source, configurar un scan, ver resultados en el catalog. Una hora de RBAC: crear roles en una collection y ver el impacto. Y al final, dos horas de proyecto guiado: implementar un pequeño caso end-to-end."

### E5. ¿Qué piensas de Microsoft Fabric vs Purview?
> "Fabric es la plataforma analítica integrada que reemplaza el ensamblaje manual de ADF, Synapse, Power BI y Databricks. Purview es la capa de gobernanza que se mantiene sobre Fabric. Microsoft los está integrando cada vez más fuerte — el catálogo de Fabric (OneLake catalog) ya tiene puentes con Purview. Mi expectativa es que en 1-2 años Purview será una capa nativa dentro de Fabric, no un servicio separado, similar a cómo Unity Catalog vive dentro de Databricks."

---

## F. Para el final de la entrevista

### Preguntas que TÚ debes hacer

1. "¿Cuál es el cliente actual donde se necesitaría este perfil, y en qué fase del programa de gobernanza están?"
2. "¿Bluetab tiene una práctica de gobernanza ya formada o este rol es parte de su construcción?"
3. "¿Qué porcentaje del rol es implementación técnica vs interacción con stakeholders de negocio del cliente?"
4. "¿Cómo es el modelo de trabajo híbrido — días específicos, horarios, oficina en Bogotá/Medellín?"
5. "¿Cómo miden el éxito en los primeros 90 días en este rol?"
6. "¿Qué oportunidades de certificación o formación financia Bluetab? Tengo interés en DP-700 y Fabric Analytics Engineer."
7. "¿Hay rotación entre clientes o el rol es dedicado a una cuenta?"

### Cierre

> "Gracias por el tiempo. Me quedo con muy buena impresión del rol y del equipo. ¿Cuáles son los siguientes pasos del proceso y en qué timeline esperan resolver?"
