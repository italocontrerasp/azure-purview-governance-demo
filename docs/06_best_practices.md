# Best Practices de Gobernanza de Datos con Purview

Recopilación de buenas prácticas que debes saber defender si te preguntan "¿cómo lo harías?".

---

## 1. Diseño organizacional

### Estructurar collections por dominio de negocio, no por tecnología
- ✅ `Sales`, `Marketing`, `Finance`
- ❌ `Azure SQL`, `ADLS`, `Snowflake`

**Razón:** los stewards y owners son humanos del dominio, no de la tecnología. El RBAC heredado funciona naturalmente.

### Máximo 3 niveles de jerarquía
- Más profundidad complica auditoría de permisos y rompe la UX de búsqueda.

### Asignar 4 roles mínimos por collection antes de poblarla
| Rol | Quién |
|---|---|
| Collection Admin | Team lead del dominio |
| Data Curator | Ingeniero de datos del equipo |
| Data Steward | Analista funcional senior |
| Data Reader | Todo el equipo |

---

## 2. Scans

### Usar Managed Identity sobre Service Principal
- ✅ Cero secretos rotando
- ✅ Audit nativo en Azure AD
- ✅ Menos superficie de ataque

Si la source no soporta MSI (ej: Snowflake sin Azure AD integration), usar SP con secret en Key Vault y rotación automática.

### Scope explícito, no scans del lake entero
```yaml
# ✅ bueno
scan_scope:
  - /bronze/sales/*
  - /silver/sales/*

# ❌ malo
scan_scope:
  - /*
```

### Scans incrementales sobre full
- Full scan solo el primer día y luego semanal (sanity check)
- Incremental diario para detectar cambios

### Ventanas de baja carga
- ADLS: madrugada UTC del país de operación
- SQL: idem + verificar índices/maintenance windows
- Snowflake: usar warehouse dedicado para scans

### Scan rule sets ajustados al formato
- Si solo guardas parquet/delta, no scanear csv/json
- Reduce tiempo de scan y falsos positivos en classifications

---

## 3. Classifications

### Empezar con built-in, sumar custom según necesidad
- 200+ built-in cubren PII US/EU bien
- Custom para identificadores locales: DNI (PE), RUT (CL), CC (CO), CPF (BR)

### Threshold de match conservador (80% por defecto)
- 100% = pierdes positivos reales por ruido
- 50% = demasiado falsos positivos

### Validar con muestra real antes de aplicar global
- Crear un scan rule set de prueba sobre una tabla conocida
- Revisar match results manualmente
- Iterar el regex / threshold

### Documentar la lógica de cada custom classification
- En el repo del proyecto, no solo en la UI
- Owner, regex, criterio de match, ejemplo positivo y negativo

---

## 4. Sensitivity Labels

### Mínimo 4 niveles, máximo 6
- Public, Internal, Confidential, Highly Confidential
- Más niveles = nadie los aplica consistentemente

### Mapear classifications → sensitivity labels automáticamente cuando sea posible
- Cualquier columna con `Credit Card` → `Highly Confidential`
- Cualquier columna con `Email` → `Confidential`

### Integrar con MIP para que las labels alimenten DLP
- DLP de Microsoft 365 puede actuar sobre archivos exportados según label

---

## 5. Glossary

### Estructura jerárquica de términos
```
Customer
├── Customer Active
├── Customer Lifetime Value
└── Customer Segment
    ├── Premium
    └── Standard
```

### Workflow de aprobación obligatorio
- Draft → Review → Approved
- Aprobador: Data Steward del dominio

### Asociar términos a assets críticos primero
- Empezar por las tablas gold/fact/dim
- Luego silver
- Bronze raramente necesita glossary (es raw)

### Sinónimos y acrónimos siempre
- "CLV" = "Customer Lifetime Value"
- "Premium" = "VIP" = "Top Tier"

---

## 6. Lineage

### Integraciones nativas primero
- ADF, Synapse, Power BI, Databricks Unity Catalog: configurar conexión nativa
- Cero código, lineage automático

### Para sources no soportadas, Atlas REST API
- Ej: pipelines en Airflow, dbt, scripts custom
- Publicar lineage al final de cada job exitoso

### Validar lineage post-deployment
- Correr el pipeline una vez
- Buscar el asset target en Purview
- Confirmar que aparece el grafo completo upstream

---

## 7. RBAC y seguridad

### Principio de menor privilegio
- Data Reader es el default para usuarios de negocio
- Data Curator solo para ingenieros con responsabilidad de edición
- Collection Admin solo para team leads

### Auditoría regular de roles
- Trimestral mínimo
- Remover usuarios que ya no están en el dominio
- Revisar Collection Admins (sweetest spot para abuso)

### Integración con grupos Azure AD
- Asignar roles a grupos, no a usuarios individuales
- Facilita on-boarding/off-boarding

---

## 8. IaC para Purview

### Terraform (o Bicep) para infraestructura, scripts Python para metadatos
- IaC despliega la cuenta, los IRs, las MSIs
- Scripts crean collections, registran sources, configuran scans vía REST API

### Idempotencia
- Los scripts deben poder correrse 10 veces y dejar el mismo estado
- Usar tags/descripciones para identificar objetos creados por IaC

### Repo separado para gobernanza vs infra general
- `infra-platform` para todo el resto de Azure
- `infra-purview` específico para gobernanza, con su propio ciclo de releases

---

## 9. Monitoreo y alertas

### Métricas a monitorear vía Azure Monitor
- Scan success rate por source
- Scan duration (alerta si crece >50% vs baseline)
- Capacity unit usage (alerta si >80% sostenido)
- Number of assets (alerta si baja inesperadamente — algo se despubblicó)

### Dashboards a mantener
- Coverage por dominio (% assets clasificados, % con glossary)
- Top 10 scans más lentos
- Sources sin scan en N días

### Alertas críticas
- Scan fallido 3 veces seguidas en la misma source → page
- Capacity unit >90% por 24h → page
- Eliminación masiva de assets (>10%) → page

---

## 10. Adopción y change management

### Workshop de onboarding por dominio
- 1 hora teoría + 1 hora hands-on en el catalog
- Hacer que cada participante busque sus propias tablas

### Documentar quick wins
- "Antes buscábamos tabla X en 30 min, ahora en 30 segundos"
- Compartir en canales de Slack/Teams

### Asignar campeones por dominio
- 1 persona en cada equipo que sea el go-to para Purview
- No es trabajo full-time, ~10% de su rol

### Hacer la auditoría dependiente del catalog
- Cuando los reportes de cumplimiento se generen desde Purview, deja de ser opcional
- Es la única forma de garantizar coverage en empresas grandes

---

## 11. Anti-patrones a evitar

❌ **Usar Purview como source of truth de schemas.** No es eso. Es metadata sobre las sources reales.

❌ **Importar TODO sin filtro.** El catálogo se vuelve ruido y nadie lo usa. Mejor: empezar por gold y silver, ignorar bronze hasta que haya demanda.

❌ **Glossary sin owner.** Términos huérfanos se desactualizan y pierden confianza.

❌ **Classifications sin re-scan después de cambios.** Las classifications se aplican durante el scan, no en tiempo real.

❌ **Confiar 100% en lineage automático.** Validar siempre con un caso de prueba post-deployment.

❌ **Permitir que Power BI sea el único catalog.** Power BI tiene su propio lineage pero solo dentro de sí mismo. Purview da la vista cross-platform.

❌ **Dejar Purview always-on en sandbox/dev.** Cuesta dinero. Deploy + destroy con IaC.

❌ **Crear collections por proyecto.** Los proyectos terminan, los dominios persisten. Collections por dominio.
