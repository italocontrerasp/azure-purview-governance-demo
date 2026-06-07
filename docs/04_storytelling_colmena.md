# Storytelling — Cómo contar tu experiencia Purview en Colmena

Consejos narrativos sobre cómo posicionar tu experiencia. **Para el guion verbal completo y las plantillas de respuesta, ve a [`scripts/interview_script.md`](../scripts/interview_script.md)**.

> ⚠️ **Lee primero** [`07_facts_canon.md`](07_facts_canon.md) — define el framing (opción C: líder técnico llevó admin de plataforma; tú hiciste config diaria + uso), los facts canónicos, y qué SÍ / qué NO digas que hiciste tú.

---

## 1. El framing en una línea

> "En Colmena la **infraestructura de Purview** (incluyendo el Self-Hosted IR para escanear Sybase on-prem) la lideró el líder técnico. Yo me hice cargo del **trabajo de configuración continua** (registro de sources de mis pipelines, scans, custom classifications LATAM) y **uso día-a-día** (5 verbos: search-before-build, validar lineage, completar classifications, impact analysis, asociar glossary terms). La **administración de plataforma** profunda — el resto — la armé en un demo end-to-end para tener experiencia hands-on de esa parte."

Esta línea es **tu ancla**. Si pierdes el rumbo en cualquier respuesta, vuelve a ella.

El pitch completo de 90 segundos memorizado está en `scripts/interview_script.md` sección 2.

---

## 2. Anatomía del pitch (por qué funciona)

| Bloque | Función |
|---|---|
| "En Applaudo, equipo de 3 ingenieros..." | Establece **seniority como parte de equipo**, no como solo-developer |
| "Migré +20 stored procedures... dashboards de Tableau" | Detalle **verificable del CV** |
| "Aseguradora chilena... migración Snowflake→Databricks" | **Business driver real** |
| "El líder técnico definió Purview en el stack" | **Honestidad de scope** — quién hizo qué |
| "Yo me hice cargo de scans, classifications LATAM, validación de lineage" | **Configuración + uso** real y defendible |
| "Armé un demo end-to-end con IaC, RBAC, lineage 3 mecanismos" | **Iniciativa proactiva** y autodidacta — palabras de la JD |

---

## 3. Trampas a evitar

❌ **No digas "yo lideré la migración".** Di "fui parte del equipo técnico de 3 ingenieros que migró...". Liderar la implica seniority que no tenías formalmente; ser parte de un equipo de 3 sí lo demuestra.

❌ **No digas "yo desplegué / configuré / administré Purview".** Eso lo hizo el líder técnico. Tú **configuraste tus scans, tus sources, tus custom classifications**. La diferencia es operativa pero crítica si profundizan.

❌ **No exageres números.** El estate era ~200 assets, no 10 mil. Equipo de 3, no de 15. Tableros impactados ~10-15, no 80.

❌ **No menciones features que no existían en tu ventana de tiempo (Dic 2023 – Jul 2024).** Domains GA, algunos features de Data Sharing, partes de Data Policies son posteriores. Si te preguntan por algo nuevo: "no lo tuvimos disponible en ese momento, conceptualmente entiendo que…".

❌ **No digas "Azure Purview".** Desde 2022 es **Microsoft Purview**. Decirlo "Azure" te delata como out-of-date.

❌ **No confundas classification con sensitivity label.** Si te preguntan la diferencia, ten clara la respuesta del cheatsheet (sección 3.3 del `interview_script.md`).

❌ **No inventes nombres internos.** Nombre de la cuenta de Purview, nombres de tablas, nombres de personas. Si te preguntan: "convención estándar tipo `pv-<cliente>-<env>`" o "tablas de pólizas / siniestros / primas, no me siento cómodo dando nombres exactos sin checar con el cliente".

---

## 4. Las dos preguntas trampa más peligrosas — repaso

### 4.1 "Si tu CV dice Purview, ¿por qué armaste un demo?"

Respuesta completa en `interview_script.md` sección 6.4. Resumen: "Mi trabajo continuo con Purview en Colmena fue config diaria + uso. La **administración de plataforma** profunda la lideraba el líder técnico. Para esta vacante donde piden config + admin + uso, armé el demo para asegurar la parte de admin con hands-on real. El demo no contradice el CV — lo complementa."

### 4.2 "Muéstrame el comando exacto / la versión exacta / el error exacto"

Respuesta completa en `interview_script.md` bloque 4 (plantillas defensivas). Resumen: la operación de plataforma la llevaba el líder técnico; tú conocías el resultado, no el comando. **Para el comando puedes hablar desde el demo** que sí construiste con detalle.

---

## 5. Plantillas de respuesta para "no sé"

Cuando no sepas algo, una de estas tres:

> "Esa parte la llevaba el líder técnico. Yo lo conocía conceptualmente. En el demo profundicé en eso — ¿te lo explico desde ahí?"

> "No lo implementé en Colmena directamente, pero conozco el patrón: [explica desde el cheatsheet]. En la práctica habría que validar con la documentación oficial porque el detalle de [X] cambia entre versiones."

> "Es algo que tengo en backlog de profundización. Mi entendimiento actual es [X]. ¿Es algo que el equipo usa intensivamente?"

**Devolver la pregunta es válido y senior** — muestra interés y te da contexto.

---

## 6. Cierre fuerte

Si te dan espacio al final ("¿algo más que quieras agregar?"):

> "Sí. Me motiva especialmente este rol porque mi experiencia con Purview en Colmena fue muy concreta — config y uso día-a-día — pero me dejó con ganas reales de profundizar en administración de plataforma, Data Policies, y la integración con Microsoft Fabric. El demo que armé para esta entrevista es la prueba de que ya empecé a moverme en esa dirección. Me interesa Bluetab justamente porque puedo llevarlo al siguiente nivel."

---

## 7. Próximo paso

Para el guion verbal completo con pitch memorizado, respuestas niveladas (30s / 2min / 5min), preguntas operativas peligrosas, frases puente y plan B → **[`scripts/interview_script.md`](../scripts/interview_script.md)**.
