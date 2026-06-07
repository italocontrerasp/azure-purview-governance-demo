"""Push the NEW migration-path lineage in one bulk payload.

We co-send the silver/gold DataSet entities with the Process entities, so the
bulk transaction can resolve uniqueAttribute refs in the same call.

Edges:
    sybase://.../POLICIES/{t}   --[adf_pl_sybase_to_bronze]-->   adls bronze/{t}/{t}.csv
    adls bronze/{t}/{t}.csv     --[nb_bronze_to_silver]-->       adls silver/{t}
    adls silver/{t}             --[nb_silver_to_gold]-->         adls gold/{t}
"""
import requests, json
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP   = "https://pv-italodemo-16de97.purview.azure.com"
TOK  = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

ST_HOST = "stitalodemo16de97.dfs.core.windows.net"
TABLES  = ["dim_policy", "dim_party", "dim_product", "fact_policy_monthly", "fact_claim"]

def ref(qn): return {"typeName": "DataSet", "uniqueAttributes": {"qualifiedName": qn}}

entities = []

# Pre-create silver/gold DataSets so refs resolve
for t in TABLES:
    SI = f"https://{ST_HOST}/silver/colmena/{t}"
    GO = f"https://{ST_HOST}/gold/colmena/{t}"
    entities.append({
        "typeName": "DataSet",
        "attributes": {"qualifiedName": SI, "name": f"silver_{t}",
                       "description": "Delta silver (limpieza + tipos)"}
    })
    entities.append({
        "typeName": "DataSet",
        "attributes": {"qualifiedName": GO, "name": f"gold_{t}",
                       "description": "Delta gold (conformed)"}
    })

# Lineage Processes
for t in TABLES:
    SY = f"sybase://colmena-onprem.local/POLICIES/{t}"
    BR = f"https://{ST_HOST}/bronze/colmena/{t}/{t}.csv"
    SI = f"https://{ST_HOST}/silver/colmena/{t}"
    GO = f"https://{ST_HOST}/gold/colmena/{t}"

    entities.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://adf/pl_sybase_to_bronze/{t}",
            "name":          f"adf_pl_sybase_to_bronze_{t}",
            "description":   "ADF Copy via SHIR: Sybase OLTP -> ADLS bronze",
            "inputs":  [ref(SY)],
            "outputs": [ref(BR)],
        }
    })
    entities.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://databricks/nb_bronze_to_silver/{t}",
            "name":          f"dbx_nb_bronze_to_silver_{t}",
            "description":   "PySpark: bronze CSV -> silver Delta (limpieza)",
            "inputs":  [ref(BR)],
            "outputs": [ref(SI)],
        }
    })
    entities.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://databricks/nb_silver_to_gold/{t}",
            "name":          f"dbx_nb_silver_to_gold_{t}",
            "description":   "PySpark: silver Delta -> gold Delta (conformed)",
            "inputs":  [ref(SI)],
            "outputs": [ref(GO)],
        }
    })

datasets  = [e for e in entities if e["typeName"] == "DataSet"]
processes = [e for e in entities if e["typeName"] == "Process"]

# Phase 1: create the silver/gold DataSets (refs needed by processes)
r = requests.post(f"{EP}/catalog/api/atlas/v2/entity/bulk",
                  json={"entities": datasets}, headers=H)
print("phase 1 datasets:", r.status_code)
res = r.json()
print(f"  CREATE: {len(res.get('mutatedEntities',{}).get('CREATE',[]))}")
if r.status_code >= 400:
    print(json.dumps(res, indent=2)[:800]); raise SystemExit(1)

# Phase 2: now refs resolve, push the Process lineage edges
r = requests.post(f"{EP}/catalog/api/atlas/v2/entity/bulk",
                  json={"entities": processes}, headers=H)
print("phase 2 processes:", r.status_code)
res = r.json()
mut = res.get("mutatedEntities", {})
print(f"  CREATE: {len(mut.get('CREATE',[]))}")
print(f"  UPDATE: {len(mut.get('UPDATE',[]))}")
print(f"  total processes sent: {len(processes)}")
if r.status_code >= 400:
    print(json.dumps(res, indent=2)[:1500])
