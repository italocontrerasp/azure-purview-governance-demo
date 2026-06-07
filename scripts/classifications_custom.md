# Hands-on — Custom Classifications

Documento descriptivo de las 3 custom classifications que creé en este demo para identificadores chilenos (RUT, número de póliza, número de siniestro). Mismo patrón que en Colmena.

> Asume que la source ADLS ya está registrada (`register_sources.md`). El orden recomendado: classifications primero, después correr scan.

---

## 1. Conceptos clave

Una **custom classification** identifica un tipo de dato propio (no cubierto por las 200+ built-in). Se compone de:

1. **Classification** = la etiqueta semántica (ej: `CL.RUT`). Va a `typedefs` (Atlas).
2. **Classification rule** = el patrón que detecta esa etiqueta (regex `dataPatterns` + opcional `columnPatterns`). Va a `/scan/classificationrules`.

Las rules globalmente habilitadas se aplican automáticamente durante cualquier scan AdlsGen2 que use el ruleset `System`. No fue necesario crear un scan rule set custom para esta demo.

---

## 2. Lo que efectivamente creé

Script: **`demo/scripts_exec/pv_create_classifications.py`**

### 2.1 Step 1 — classification defs (POST typedefs)

```python
CLASS_DEFS = [
  {"name": "CL.RUT",            "displayName": "CL RUT",            ...},
  {"name": "CL.POLICY_NUMBER",  "displayName": "CL Policy Number",  ...},
  {"name": "CL.CLAIM_NUMBER",   "displayName": "CL Claim Number",   ...},
]
requests.post(f"{EP}/catalog/api/atlas/v2/types/typedefs", json={"classificationDefs": CLASS_DEFS}, ...)
```

Output:

```
typedefs: 200 {"classificationDefs":[{"name":"CL.RUT","guid":"...","category":"CLASSIFICATION", ...}, ...]}
```

> **Convención de nombres aplicada:** prefijo de país (`CL.`) para evitar colisiones cuando entre otro cliente LATAM. Si mañana entra Perú, sería `PE.DNI`, `PE.RUC`, etc.

### 2.2 Step 2 — classification rules (PUT /scan/classificationrules)

| Rule name | Classification | dataPattern | minimumPercentageMatch |
|---|---|---|---|
| `cl_rut_rule` | `CL.RUT` | `^[0-9]{7,8}-[0-9Kk]$` | 60.0 |
| `cl_policy_rule` | `CL.POLICY_NUMBER` | `^POL-[0-9]{10}$` | 60.0 |
| `cl_claim_rule` | `CL.CLAIM_NUMBER` | `^CLM-[0-9]{4}-[0-9]{6}$` | 60.0 |

`columnPatterns` quedó como `.*` (matchea cualquier nombre de columna). En producción aceleraría con un `columnPatterns` más específico (ej: `(?i)(rut|run|id_persona|customer_id)`) — pero para el dataset chico del demo no aporta y prefería que el regex de contenido fuera el que mandara.

Output observado por cada PUT:

```
rule cl_rut_rule       -> 200 {"kind":"Custom","name":"cl_rut_rule","properties":{...}}
rule cl_policy_rule    -> 200 {...}
rule cl_claim_rule     -> 200 {...}
```

### 2.3 Por qué `minimumPercentageMatch=60.0` y no 80%

Fui directo a 60% en el script (no fue iterativo). El razonamiento: el mock RUT generator produce RUTs válidos en 100% de las filas, pero el regex `^[0-9]{7,8}-[0-9Kk]$` no tolera variantes comunes (RUT con puntos `12.345.678-9`, espacios, RUT del estado tipo `60805000-0`). En un dataset productivo esas variantes existen — con 80% me arriesgo a perder la classification si los datos vienen sucios. 60% me da margen para ese caso y sigue siendo restrictivo (un campo numérico arbitrario no lo dispara).

En cliente con datos limpios y validados (CRM con regla de input) subiría a 80-90% para reducir falsos positivos; aquí el demo prioriza que la classification aparezca de forma consistente.

---

## 3. Validación de regex (lo hice antes de subir)

Antes de PUT-tearlos, probé los 3 regex en Python:

```python
import re

rut = re.compile(r'^[0-9]{7,8}-[0-9Kk]$')
pol = re.compile(r'^POL-[0-9]{10}$')
clm = re.compile(r'^CLM-[0-9]{4}-[0-9]{6}$')

assert rut.match("12345678-9")        # ok
assert rut.match("9876543-K")          # ok mayuscula
assert rut.match("9876543-k")          # ok minuscula
assert not rut.match("123-5")          # muy corto
assert not rut.match("12345678-X")     # digito invalido

assert pol.match("POL-1234567890")
assert not pol.match("POL-123")
assert clm.match("CLM-2024-000001")
assert not clm.match("CLM-24-1")
```

Todo pasó. Recién después de eso disparé el script.

---

## 4. Resultado en Purview Studio (verificado)

Después de correr los 3 scans (ver `run_scan.md`):

- `bronze/colmena/dim_party.csv` → columna `rut` con tag `CL.RUT`.
- `bronze/colmena/dim_party.csv` → columna `email` con tag `MICROSOFT.PERSONAL.EMAIL` (built-in, automático).
- `bronze/colmena/dim_policy.csv` → columna `policy_number` con tag `CL.POLICY_NUMBER`.
- `bronze/colmena/fact_claim.csv` → columna `claim_number` con tag `CL.CLAIM_NUMBER`.

Las mismas tags viajan a silver y gold porque los notebooks preservan los nombres de columna.

---

## 5. Set completo de classifications LATAM (referencia para entrevista)

Útil tener este set listo si te preguntan en la entrevista qué clasificaciones se aplicarían a clientes en distintos países:

| País | Tipo | Regex |
|---|---|---|
| Chile | RUT | `^[0-9]{7,8}-[0-9Kk]$` |
| Perú | DNI | `^[0-9]{8}$` |
| Perú | RUC | `^(10\|20)[0-9]{9}$` |
| Colombia | Cédula | `^[0-9]{6,10}$` |
| Colombia | NIT | `^[0-9]{9,10}-[0-9]$` |
| México | CURP | `^[A-Z]{4}[0-9]{6}[A-Z]{6}[0-9A-Z][0-9]$` |
| México | RFC | `^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$` |
| Argentina | DNI | `^[0-9]{7,8}$` |
| Argentina | CUIT | `^[0-9]{2}-[0-9]{8}-[0-9]$` |
| Brasil | CPF | `^[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}$` |
| Brasil | CNPJ | `^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$` |

---

## 6. Por qué API y no UI

Tres razones:

1. **Reproducibilidad.** Si destruyo el RG y recreo, basta correr `pv_create_classifications.py` para tener exactamente las mismas defs y rules. La UI no deja huella.
2. **Versionado.** El script vive en el repo, las decisiones (regex, threshold, displayName) quedan en git history.
3. **Productivo en proyecto real.** En un cliente con 20-30 classifications custom, hacerlas a mano es inviable. Encapsularlas en script Python con el SDK `azure-purview-scanning` (o requests crudo como hice) es el patrón.

Trade-off: si en el futuro el SDK de Microsoft cambia el shape del body, el script habrá que actualizarlo (preview APIs cambian con cierta frecuencia). Ese mantenimiento es menor que el dolor de hacerlo a mano.

---

## 7. Anti-patrones (lo que evité a propósito)

- **Regex muy permisivo.** Ej: `^[0-9]+$` para "DNI peruano" matchea cualquier número, hasta IDs internos. Por eso el RUT chileno requiere el guion + dígito verificador.
- **Olvidar el `columnPatterns` en producción.** Lo dejé `.*` en demo, pero con dataset grande costaría caro. En el cliente real lo apretaba.
- **Threshold al 100%.** Datos sucios (espacios, formato variable, valores de prueba) hacen que el match nunca llegue al 100%. 60-90% es el rango sano.
- **No re-escanear después de cambiar la rule.** Las classifications se aplican durante el scan, no en tiempo real. Cambié threshold y re-corrí los 3 scans.
- **Classifications duplicadas con nombres distintos.** `CL.RUT`, `Chile_RUT`, `RUT_CL` → caos. La convención del demo es `<PAIS>.<TIPO>` punto.

---

## 8. Próximo paso

Para ver cómo se aplicaron estas classifications durante los scans efectivamente corridos: `run_scan.md`.

Para el grafo de lineage donde estas columnas etiquetadas se propagan por las capas medallion: `lineage_adf_databricks.md`.
