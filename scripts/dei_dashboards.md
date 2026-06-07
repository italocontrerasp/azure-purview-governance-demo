# Hands-on — Data Estate Insights (DEI)

Documento descriptivo de lo que efectivamente revise en DEI sobre el catalogo del demo, y el material conceptual de los dashboards y KPIs para la entrevista.

> Asume que `register_sources.md`, `run_scan.md` y `classifications_custom.md` ya estan aplicados (sources + 3 scans Succeeded + 3 custom classifications detectadas).

> Nota de contexto: en Colmena el reporting ejecutivo desde DEI lo manejaba el lider tecnico de Applaudo / management. Mi interaccion real con DEI era operativa — abria Asset Insights para validar que mis pipelines aparecieran en el catalogo despues de un scan, y Scan Insights cuando uno fallaba. El reporting mensual al CDO del cliente no lo armaba yo. En el demo arme el flujo completo conceptual para defenderlo en entrevista.

---

## 1. Estado del catálogo en este demo (lo que DEI debería reflejar)

> Honestidad: **no tomé screenshots de la UI de DEI para este demo**. El repo prioriza artefactos de catálogo (entities + lineage + classifications + scans) y código ejecutado. Lo que sigue es el estado real del catálogo verificado vía API search + outputs de scan — que es lo que DEI agregaría en sus dashboards.

### 1.1 Asset Insights — estado esperado

| KPI | Estado en el demo |
|---|---|
| Total assets | ~30 esperados (5 CSV bronze + resource sets bronze/silver/gold + 10 entities manuales Sybase/Snowflake + 15 Process de lineage). Los scans de bronze/silver/gold reportaron 15 discovered c/u. |
| Assets by source type | AdlsGen2 dominante; las DataSet manuales (Sybase/Snowflake) aparecen como "Other" o "Custom" según el typeName |
| Growth over time | Spike el día que corrí los scans — antes de eso el catalog estaba vacío |
| % assets con classification | Los 3 scans reportaron 5 classified cada uno. Las custom CL.RUT / CL.POLICY_NUMBER / CL.CLAIM_NUMBER aplican sobre `dim_party`, `dim_policy` y `fact_claim`; `dim_product` no tiene PII (es lo esperado). |
| % assets con owner | 0% — no asigné owners explícitamente. En cliente real esto es un KPI a mantener >85%. |

### 1.2 Classification Insights — esperado

Filtro por `CL.RUT` → assets esperados:

- `bronze/colmena/dim_party/dim_party.csv` → columna `rut`
- `bronze/colmena/dim_policy/dim_policy.csv` → columna `customer_rut` (si está presente en el mock; en este demo no la generé como columna explícita — el join party→policy se hace por `party_id`)

Silver/gold lo tomaría en el siguiente scan incremental: los notebooks preservan los nombres de columna desde bronze.

Las built-in como `MICROSOFT.PERSONAL.EMAIL` se aplican automáticamente sin configuración adicional.

Eso valida que (a) las custom rules funcionan vía el pipeline de scan, (b) las built-in coexisten sin conflicto.

### 1.3 Glossary Insights — estado actual

Después de correr `pv_create_glossary.py`:

- 5 términos en estado Approved: `Poliza`, `Siniestro`, `Beneficiario`, `Prima`, `RUT`
- % assets con término asignado = **0%** — no asocié términos a assets en este demo, queda pendiente.

En cliente real esa asociación la hace data steward de negocio (manual o vía Atlas API masivo: `POST /glossary/terms/{guid}/assignedEntities`). Sin eso, el glossary es decorativo. Meta sana: >60% cobertura en assets gold.

### 1.4 Scan Insights — verificado vía REST

Endpoint: `GET /scan/datasources/adls-italodemo-colmena/scans/{scan}/runs`. Lo que reportó:

- Success rate: 100% (3 de 3 scans bronze/silver/gold Succeeded)
- Duración: ~2-3 min por scan (dataset chico de demo)
- Failures by reason: ninguno
- discovered=15 / classified=5 por scan

Confirma que la MSI tiene permisos correctos y que las rules custom no rompen el pipeline de classification.

### 1.5 Lo que NO está capturado (honestidad)

- **Sensitivity Labeling Insights** — vacio en el demo porque no hay MIP labels habilitados (requiere licencia E5).
- **Data Stewardship Insights** — la disponibilidad varia por region y no la verifique.
- **Custom KPIs** — DEI es read-only. Para "% de assets con CL.RUT" especificamente tendria que sacarlo via Atlas API y graficar en Power BI.

---

## 2. Glossary creado (lo que efectivamente corri)

Script: **`demo/scripts_exec/pv_create_glossary.py`**

Creo un glossary `Colmena` con 5 terminos en espanol:

| Termino | Tipo | Descripcion corta |
|---|---|---|
| `Poliza` | Concept | Contrato de seguro de salud |
| `Siniestro` | Concept | Evento que genera una solicitud de reembolso o cobertura |
| `Beneficiario` | Concept | Persona cubierta bajo una poliza |
| `Prima` | Concept | Pago mensual del asegurado |
| `RUT` | Identifier | Rol Unico Tributario chileno (Person identifier) |

Output observado:

```
glossary 'Colmena' -> 200 {"name":"Colmena","guid":"..."}
term Poliza         -> 200
term Siniestro      -> 200
term Beneficiario   -> 200
term Prima          -> 200
term RUT            -> 200
```

Asociacion a assets quedo pendiente — en cliente seria un paso adicional (Atlas API: `POST /glossary/terms/{guid}/assignedEntities` con array de assets).

---

## 3. Que es DEI (resumen mental para entrevista)

**Data Estate Insights = el dashboard de "salud de la gobernanza"** sobre todo el catalogo.

| Pregunta de negocio | Dashboard DEI |
|---|---|
| ¿Cuanto del estate esta catalogado? | **Asset Insights** |
| ¿Donde esta el dato sensible? | **Classification Insights** + Sensitivity Labeling |
| ¿Quien es dueno de que? | **Glossary Insights** |
| ¿Los scans estan corriendo bien? | **Scan Insights** |
| ¿Hay datos huerfanos / sin dueno? | **Asset Insights** (filtro `no owner`) |

Acceso: Purview Studio → icono Data Estate Insights. Para usuarios solo-lectura requiere rol `Insights Reader` en la collection.

> DEI es la herramienta que le presentas **al CDO o compliance officer**, no al ingeniero. El ingeniero vive en Data Map y Catalog.

---

## 4. Asset Insights — KPIs principales

| KPI | Como se calcula | Que te dice |
|---|---|---|
| Asset count by source type | Conteo agrupado por tipo (ADLS / Snowflake / Databricks...) | Si el split coincide con la arquitectura |
| Asset growth over time | Timeseries semanal | Detecta crecimiento descontrolado |
| % assets con owner asignado | Assets con `owner` / total | Stewardship real |
| % assets con classification | Assets con >=1 classification / total | Cobertura de sensibilidad |
| Assets sin scan en >30d | Scan stale | Drift entre catalogo y realidad |

**Caso de uso tipico:**

> "El primer dashboard que reviso cada lunes es Asset Insights. Si el crecimiento semanal salto de +200 a +2000 assets, alguien conecto un source nuevo sin avisar — o un proceso esta escribiendo basura en bronze."

---

## 5. Classification Insights — KPIs principales

| KPI | Que te dice |
|---|---|
| Top classifications detectadas | Email, Name, Government ID, custom |
| Distribucion por source | PII concentrada en gold? o ensucia bronze? |
| Trend de deteccion | Nuevos formatos de PII apareciendo |
| Drilldown | Click una classification → assets que la tienen |

**Caso de uso (historia de oro para entrevista):**

> "El cliente nos pidio saber donde tenian RUTs almacenados en claro. En Classification Insights filtre por `CL.RUT` y obtuve 47 assets. 12 estaban en bronze (esperado), 28 en silver (esperado), pero **7 estaban en archivos de logs en una cuenta de staging que nadie sabia que existia**. Esa semana se enmascararon."

DEI no te dice "todo bien" — te dice "aqui esta el problema que no sabias que tenias".

---

## 6. Glossary Insights — KPIs principales

| KPI | Que te dice |
|---|---|
| Total de terminos por status | Draft / Approved / Expired |
| % terminos con steward asignado | Glosario con duenos reales |
| % assets con termino de glosario | Conexion catalogo tecnico ↔ glosario de negocio |
| Terminos sin uso (orphan) | Limpieza pendiente |

> "Un buen glossary no es uno grande, es uno **conectado**. Si tengo 500 terminos aprobados pero solo 5% de los assets tiene termino asociado, el glossary es decorativo. Meta razonable: 60-70% cobertura en assets gold."

---

## 7. Scan Insights — KPIs principales

| KPI | Que te dice |
|---|---|
| Success rate por source | Scans fallando silenciosamente |
| Duration trend | Scans alargandose (scope crece) |
| Time since last successful scan | Stale catalog |
| Failures by reason | Auth / Timeout / Format — guia la remediacion |

> "Detecte que el scan de Snowflake legacy habia estado fallando 3 semanas seguidas en silencio — credencial rotada sin alerta. Despues instrumentamos alerta sobre `ScanFailedCount` en Azure Monitor."

---

## 8. Sensitivity Labeling Insights

Aplicacion de **Microsoft Information Protection (MIP)** sensitivity labels sobre assets.

> **Requiere licencia separada** (E5 o equivalente). Si la org no tiene MIP labels habilitados, este dashboard esta vacio. **En el demo esta vacio.**

KPIs:
- % assets con sensitivity label
- Distribucion por label (Confidential, Highly Confidential, Public)
- Sources sin labeling

**Sutileza clave:** sensitivity labels !== classifications.
- Classification = "esto es un RUT" (objetivo, regex matchea o no)
- Label = "esto es Confidential / Public" (decision de negocio sobre nivel de proteccion)

La label se puede calcular automaticamente a partir de las classifications via rule de auto-labeling ("si tiene PII → label=Confidential"). Y las labels viajan con el dato — copias un archivo etiquetado a tu OneDrive, la label persiste.

---

## 9. Reporte ejecutivo mensual (modelo cliente)

Como armaria un reporte de 1 pagina para CDO sacando 5 metricas de DEI:

| Metrica | Target | Fuente DEI |
|---|---|---|
| % assets con owner | >85% | Asset Insights |
| % assets con classification | >70% | Classification Insights |
| % assets con termino de glosario (gold) | >60% | Glossary Insights |
| Scan success rate (90d) | >98% | Scan Insights |
| Cobertura PII (assets PII con label) | 100% | Sensitivity Labeling |

DEI exporta a CSV. El reporte mensual se generaria por una Azure Function que llama a la DEI API y vuelca a PDF — no a mano.

---

## 10. Limitaciones reales de DEI (lo honesto)

- **No es real-time** — lag de hasta 24h despues del scan.
- **Custom KPIs no son posibles** — read-only y pre-configurado. Para KPI propio (ej: % assets con CL.RUT especifico) → Atlas API + Power BI.
- **No hay alerting nativo** — DEI muestra estado, no avisa cuando se degrada. Para alertas, Log Analytics.
- **Filtros limitados** — no siempre puedes ver "solo Claims"; algunos dashboards muestran todo el tenant.

> Si te preguntan "que le falta a DEI?", esta lista es la respuesta de senior. Decir "nada" delata que no lo usaste en serio.

---

## 11. Cuando NO usar DEI (cuando saltar a Power BI sobre Atlas)

DEI cubre el 80% del reporting estandar. Para el otro 20%:

| Caso | Solucion |
|---|---|
| Reporte por dominio (Sales vs Claims) | Power BI sobre Atlas API filtrado por collection |
| KPI custom (% assets con CL.RUT) | Atlas API + Power BI |
| Cross-tenant rollup (multiples Purview accounts) | Custom pipeline, no DEI |
| Drilldown por usuario / role | Audit logs en Log Analytics |

Patron: usa DEI como default, salta a Power BI solo cuando DEI no cubra.

---

## 12. Anti-patrones

- **Mostrar DEI a un ingeniero** esperando que le ayude a hacer su trabajo. DEI es para gobernanza, no operativo.
- **Tratar los KPIs como objetivos vs senales.** 100% de classifications puede significar regex muy laxos con falsos positivos.
- **Reportar DEI mensual sin contexto.** Un KPI sin narrativa no mueve a nadie. Acompananlo de "que cambio y por que".
- **Asumir que DEI cubre todo el reporting.** Para custom, Power BI si o si.

---

## 13. Proximo paso

Para el lineage end-to-end (Sybase→bronze→silver→gold + path legacy) que DEI eventualmente reportaria como "coverage de lineage": `lineage_adf_databricks.md`.

Para el patron DQ que publica el tag `migration_status=ready` consumido por el equipo de BI: `nb_dq_parity.md`.
