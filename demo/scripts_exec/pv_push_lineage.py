"""Push manual lineage edges via Atlas API by creating Process entities
that connect upstream/downstream assets via inputs/outputs.

Edges we want to materialize:

  LEGACY path (already orphan in catalog, we connect it):
     sybase.POLICIES.{tbl}  --[adf_copy_legacy]-->  snowflake.COLMENA_LEGACY.{TBL}

  NEW path (the migration target):
     sybase.POLICIES.{tbl}  --[adf_copy_to_bronze]-->  adls.bronze/colmena/{tbl}.csv
     adls.bronze/{tbl}      --[nb_bronze_to_silver]--> adls.silver/{tbl}
     adls.silver/{tbl}      --[nb_silver_to_gold]-->   adls.gold/{tbl}

Each Process has typeName='Process' with qualifiedName/name, and inputs/outputs
referenced by uniqueAttributes (so no GUID juggling).
"""
import requests, json
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP   = "https://pv-italodemo-16de97.purview.azure.com"
TOK  = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

ST_HOST   = "stitalodemo16de97.dfs.core.windows.net"
TABLES    = ["dim_policy", "dim_party", "dim_product", "fact_policy_monthly", "fact_claim"]

def ref(typeName, qualifiedName):
    return {"typeName": typeName, "uniqueAttributes": {"qualifiedName": qualifiedName}}

processes = []

for t in TABLES:
    SY = f"sybase://colmena-onprem.local/POLICIES/{t}"
    SF = f"snowflake://colmena.snowflakecomputing.com/COLMENA_LEGACY/PUBLIC/{t.upper()}"
    BR = f"https://{ST_HOST}/bronze/colmena/{t}/{t}.csv"
    SI = f"https://{ST_HOST}/silver/colmena/{t}"
    GO = f"https://{ST_HOST}/gold/colmena/{t}"

    # Legacy: Sybase -> Snowflake (caja negra de la carga legacy)
    processes.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://legacy_etl/sybase_to_snowflake/{t}",
            "name":          f"legacy_etl_sybase_to_snowflake_{t}",
            "description":   "Carga legacy (caja negra) que poblaba Snowflake desde Sybase",
            "inputs":  [ref("DataSet", SY)],
            "outputs": [ref("DataSet", SF)],
        }
    })
    # NEW: Sybase -> ADLS bronze (ADF Copy + SHIR)
    processes.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://adf/pl_sybase_to_bronze/{t}",
            "name":          f"adf_pl_sybase_to_bronze_{t}",
            "description":   "ADF Copy via SHIR: Sybase OLTP -> ADLS bronze (replica fiel)",
            "inputs":  [ref("DataSet", SY)],
            "outputs": [ref("DataSet", BR)],
        }
    })
    # NEW: bronze -> silver (notebook)
    processes.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://databricks/nb_bronze_to_silver/{t}",
            "name":          f"dbx_nb_bronze_to_silver_{t}",
            "description":   "Notebook PySpark: limpieza + persistencia Delta en silver",
            "inputs":  [ref("DataSet", BR)],
            "outputs": [ref("DataSet", SI)],
        }
    })
    # NEW: silver -> gold (notebook)
    processes.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://databricks/nb_silver_to_gold/{t}",
            "name":          f"dbx_nb_silver_to_gold_{t}",
            "description":   "Notebook PySpark: conformed dim / fact en gold (Delta)",
            "inputs":  [ref("DataSet", SI)],
            "outputs": [ref("DataSet", GO)],
        }
    })

body = {"entities": processes}
r = requests.post(f"{EP}/catalog/api/atlas/v2/entity/bulk", json=body, headers=H)
print("lineage processes:", r.status_code)
res = r.json()
created = res.get("mutatedEntities", {}).get("CREATE", [])
print(f"  created: {len(created)}  total sent: {len(processes)}")
for e in created[:3]:
    print(f"   - {e['attributes']['qualifiedName']}")
print(f"  ...")
print(f"  full guidAssignments: {len(res.get('guidAssignments', {}))}")
