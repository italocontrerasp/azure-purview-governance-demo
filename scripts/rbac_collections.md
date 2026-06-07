# Hands-on — RBAC y Collections en Purview

Documento descriptivo de lo que efectivamente operé en el demo: la jerarquía de collections (creada por script Python) y los role assignments (entregados por Terraform; el script `pv_assign_self_roles.py` quedó como red de seguridad idempotente, no fue necesario correrlo).

> Asume que `register_sources.md` ya está aplicado.

> Nota de contexto: en Colmena el RBAC inicial y la jerarquía de collections la lideró el lider tecnico de Applaudo. Mi interaccion real fue conocer la estructura y operar dentro de mis collections asignadas, no disenar/asignar roles. Este doc modela lo que armaria yo como administrador de plataforma — complementando la experiencia real con el demo end-to-end.

---

## 1. Resumen mental (planos de permisos)

Purview tiene **dos planos** que es critico no confundir:

| Plano | Donde se asigna | Para que sirve | Ejemplo de rol |
|---|---|---|---|
| **Azure control plane** (Azure RBAC) | Azure Portal → IAM del recurso Purview | Crear/borrar/configurar el recurso, networking, escalado | `Owner`, `Contributor` |
| **Purview data plane** (Collection RBAC) | Studio → Data Map → Collections → Role assignments | Acceder y operar dentro del catalogo: ver assets, scanear, editar glossary | `Collection Admin`, `Data Source Admin`, `Data Curator`, `Data Reader`, `Insights Reader` |

**Regla:** todo lo que es trabajo diario en el catalogo se gobierna por **collection RBAC**. El Azure RBAC del recurso Purview se le da a 2-3 ingenieros de plataforma y no se toca mas.

---

## 2. Lo que efectivamente hice en el demo

### 2.1 Terraform asigno los roles de root antes que yo ejecutara nada

El modulo `infra/modules/purview` ya viene con los `azurerm_role_assignment` sobre el recurso Purview y un bootstrap del policystore que deja a mi user OID (`be58243b-e1a7-47d4-96ab-c5ef5bd47f73`) con los 4 roles built-in del data plane sobre la collection root `pv-italodemo-16de97`:

- `purviewmetadatarole_builtin_collection-administrator`
- `purviewmetadatarole_builtin_data-curator`
- `purviewmetadatarole_builtin_data-source-administrator`
- `purviewmetadatarole_builtin_purview-reader`

Eso es lo que me permitio correr `pv_create_collections.py`, `pv_register_sources.py`, etc., sin tener que hacer nada de RBAC manual.

### 2.2 `pv_assign_self_roles.py` quedo como red de seguridad

Script: **`demo/scripts_exec/pv_assign_self_roles.py`**

Idea: leer `GET /policystore/metadataPolicies`, recorrer los `attributeRules`, y para cada rule de los 4 roles built-in inyectar mi OID en `principal.microsoft.id.attributeValueIncludes` si no estaba ya. Despues PUT del policy completo.

```python
for rule in pol["properties"]["attributeRules"]:
    rid = rule["id"].split(":")[0]
    if rid not in ROLES: continue
    for cond_group in rule["dnfCondition"]:
        for cond in cond_group:
            if cond.get("attributeName") == "principal.microsoft.id":
                cur = cond.get("attributeValueIncludes") or []
                if USER_OID not in cur:
                    cur.append(USER_OID)
                cond["attributeValueIncludes"] = cur
```

Output observado en la corrida de verificacion:

```
rules updated: 0
PUT 200
```

`rules updated: 0` = Terraform ya me habia dejado adentro de las 4 reglas. El PUT 200 confirma que el shape del body era correcto. Si manana destruyo el RG y recreo, el script aplica solo lo que falta.

### 2.3 Collections — esto si lo cree con script

Script: **`demo/scripts_exec/pv_create_collections.py`**

```python
TREE = [
    ("colmena",      "Colmena",      ROOT),
    ("sales",        "Sales",        "colmena"),
    ("underwriting", "Underwriting", "colmena"),
    ("claims",       "Claims",       "colmena"),
]

for name, friendly, parent in TREE:
    body = {
        "parentCollection": {"referenceName": parent},
        "friendlyName": friendly,
        "description": f"Demo collection {friendly}",
    }
    requests.put(f"{EP}/account/collections/{name}?api-version=2019-11-01-preview", json=body, ...)
```

Output observado:

```
PUT colmena         -> 200 {"name":"colmena","friendlyName":"Colmena","parentCollection":{...}}
PUT sales           -> 200 ...
PUT underwriting    -> 200 ...
PUT claims          -> 200 ...

--- final tree ---
pv-italodemo-16de97       parent=-                        state=Succeeded
colmena                   parent=pv-italodemo-16de97      state=Succeeded
sales                     parent=colmena                  state=Succeeded
underwriting              parent=colmena                  state=Succeeded
claims                    parent=colmena                  state=Succeeded
```

### 2.4 Estado real al cierre

```
Root (pv-italodemo-16de97)         ← yo: 4 roles built-in (via Terraform)
└── colmena                        ← hereda
    ├── sales                      ← hereda
    ├── underwriting               ← hereda
    └── claims                     ← hereda
        + adls-italodemo-colmena (source, colgada de "colmena")
```

Las sub-collections estan vacias de sources en el demo — la source ADLS colgo de `colmena` directamente y los 3 scans (bronze/silver/gold) funcionan bajo ese scope. En un cliente real cada sub-collection tendria su set de sources (`sales` → Snowflake `SALES.*`, `claims` → tablas de siniestros, etc.) y role assignments distintos.

---

## 3. Los 5 roles del data plane (referencia)

| Rol | Puede | NO puede |
|---|---|---|
| **Collection Admin** | Crear sub-collections, asignar roles, mover sources | Nada — es admin de la collection |
| **Data Source Admin** | Registrar sources, configurar scans, crear credentials | Ver el contenido del catalogo, editar glossary |
| **Data Curator** | Editar assets, classifications, glossary, lineage manual | Crear sub-collections, gestionar scans |
| **Data Reader** | Buscar y ver assets (read-only) | Editar nada |
| **Insights Reader** | Acceder a Data Estate Insights | Ver el catalogo en si |

**Sutileza importante:** **Data Curator NO puede registrar sources ni correr scans.** Para eso necesita Data Source Admin. En proyectos chicos la misma persona tiene ambos; en grandes se separan.

Roles legacy (`Purview Data Reader/Curator/Source Admin` en Azure IAM) estan deprecados desde 2022. No recomendar.

---

## 4. Herencia entre collections

Las collections forman un arbol. Los roles **se heredan hacia abajo**:

```
Root
  └── Colmena (asignas: Maria como Collection Admin)
         ├── Sales            ← Maria hereda Collection Admin
         ├── Underwriting     ← idem
         └── Claims           ← idem
```

Puedes **romper la herencia** asignando explicitamente en una sub-collection, pero **no quitar** un rol heredado. Si necesitas que Maria NO sea admin en `Claims`, hay que mover `Claims` fuera del subarbol. La herencia es solo aditiva.

**Implicacion:** disena el arbol de collections **antes** que el RBAC. Si despues hay que separar permisos en una rama, toca reestructurar.

---

## 5. Patron de arbol — caso Colmena (como lo armaria en cliente)

En el demo solo tengo `colmena/{sales,underwriting,claims}`. En un cliente real el arbol seria:

```
Root (pv-cliente-prod)
└── Colmena
    ├── Sales
    │   ├── (sources: snowflake SALES.*, gold Delta dim_policy/fact_sales en ADLS)
    │   └── (curador: equipo comercial)
    ├── Underwriting
    │   ├── (sources: ADLS bronze/silver/gold de polizas)
    │   └── (curador: equipo de suscripcion)
    ├── Claims
    │   ├── (sources: snowflake CLAIMS.*, ADLS claims/*)
    │   └── (curador: equipo de siniestros — datos mas sensibles)
    └── Platform
        ├── (sources: ADF, Databricks)
        └── (curador: data platform team)
```

Por que este split:

1. **Por dominio de negocio**, no por tecnologia. Una collection "ADLS" seria un anti-patron porque mezcla datos de sales, claims y underwriting.
2. **Platform** aparte porque ADF/Databricks son **transversales** — sirven a todas las areas. No tiene sentido bajo Sales o Claims.
3. **Claims** separada del resto porque los datos de siniestros tienen restricciones legales adicionales (Ley 19.628 chilena, equivalente a habeas data).

---

## 6. Matriz de asignaciones — modelo cliente (como lo armaria)

| Persona / grupo | Rol | Collection | Justificacion |
|---|---|---|---|
| Lider tecnico de Applaudo | Collection Admin | Root | Unico con permiso de tocar la estructura inicial |
| Data Engineers Applaudo (3 ing) | Data Curator + Data Source Admin | Platform + sus dominios | Configuran scans, registran sources, curan assets |
| Analistas funcionales del cliente | Data Reader | Su dominio (Sales/Underwriting/Claims) | Buscan datos, no editan |
| Equipo BI del cliente | Data Reader | Colmena | Buscan datos para sus dashboards Tableau |
| Compliance Officer (cliente) | Insights Reader + Data Reader | Root | KPIs de gobernanza globales |
| Auditor externo (temporal, 90d) | Data Reader | Colmena/Claims solo | Acceso scoped y revocable |

> En Colmena **no habia rol formal de "data steward de negocio"** del lado del cliente. El conocimiento de negocio se levantaba en workshops puntuales. En una siguiente fase se habria propuesto formalizar stewards por dominio, pero quedo fuera del scope inicial.

---

## 7. Asignar roles via script — el patron del demo

Para producción, **no** se asignan por UI — se versionan en código. El demo demuestra dos caminos:

### 7.1 Policystore directo (lo que hace `pv_assign_self_roles.py`)

```python
# 1. GET policystore actual
r = requests.get(f"{EP}/policystore/metadataPolicies?api-version=2021-07-01", headers=H)
pol = r.json()["values"][0]

# 2. Mutar attributeRules → inyectar OID en attributeValueIncludes
# (codigo arriba en 2.2)

# 3. PUT policy entero
requests.put(f"{EP}/policystore/metadataPolicies/{pol['id']}?api-version=2021-07-01",
             json={"id": pol["id"], "name": pol["name"], "version": pol["version"],
                   "properties": pol["properties"]}, headers=H)
```

Trade-off: el shape exacto del body cambia con cierta frecuencia entre versiones preview de la API. Por eso el script lee, muta y reescribe el documento entero — no construye uno desde cero.

### 7.2 Pattern "RBAC como YAML versionado" (recomendado en cliente)

```yaml
collections:
  sales:
    data-curator:
      - group: aad-colmena-sales-stewards
    data-reader:
      - group: aad-colmena-bi-analysts
  claims:
    data-curator:
      - group: aad-colmena-claims-stewards
    data-reader:
      - group: aad-colmena-claims-readers
      - user: auditor-externo@bluetab.com  # vence 2026-09-01
```

Pipeline CI corre script Python que (a) lee el YAML, (b) lista asignaciones actuales via REST, (c) aplica el diff (POST nuevas, DELETE removidas), (d) loguea cambios y alerta si alguien asigno manualmente fuera de IaC.

> El **collection-level RBAC** (data plane) **no es asignable via ARM/Terraform/Bicep** todavia. Esto es una limitacion conocida y un dolor real en proyectos IaC-first. Por eso el demo usa Python directo contra el policystore.

---

## 8. Identidades a usar

| Identidad | Cuando |
|---|---|
| **AAD Security Group** | Default para humanos. IAM gestiona membresia sin tocar Purview. |
| **User (UPN)** | Solo accesos temporales y excepcionales (ej: auditor con expiracion) |
| **Service Principal** | Apps que se autentican a Purview (ADF MSI, Databricks SP, scripts CI) |
| **Managed Identity** | Idem SP, preferible cuando aplica (no hay secret que rotar) |

**Antipatron clasico:** asignar el rol al usuario directo. Cuando esa persona cambia de equipo o sale, hay que ir a Purview a limpiar. Con grupos, IAM lo saca del grupo y listo.

---

## 9. Auditoria

Purview emite logs a Azure Monitor si lo conectas:

1. Azure Portal → recurso Purview → Diagnostic settings → + Add
2. Categorias: `ScanStatusLogEvent`, `DataSensitivityLogEvent`, **`Audit`**
3. Destination: Log Analytics workspace

Queries KQL utiles:

```kusto
// Quien asigno / cambio roles en las ultimas 24h
PurviewAuditEvent
| where TimeGenerated > ago(24h)
| where Category == "RoleAssignment"
| project TimeGenerated, OperationName, CallerIpAddress, Identity, Properties
```

En el demo **no configure** Diagnostic settings — habria sido lo siguiente en producción.

---

## 10. Anti-patrones

- **Asignar todo al rol Collection Admin** "por si acaso". Termina siendo todo el equipo admin de todo. Aplica least privilege.
- **Confundir Azure RBAC con Collection RBAC.** Dar `Contributor` en el recurso Purview no da acceso al catalogo.
- **Disenar collections por tecnologia** (ADLS / Databricks / Snowflake). El negocio no piensa por tecnologia.
- **Asignar a usuarios individuales en lugar de grupos.** Imposible mantener cuando crece el equipo.
- **No versionar el RBAC.** Sin source of truth, no hay gobernanza.
- **Olvidar revocar accesos temporales.** Audita trimestralmente.

---

## 11. Proximo paso

Para los dashboards ejecutivos que consumen la metadata gobernada: `dei_dashboards.md`.

Para el lineage end-to-end que cruza las collections: `lineage_adf_databricks.md`.
