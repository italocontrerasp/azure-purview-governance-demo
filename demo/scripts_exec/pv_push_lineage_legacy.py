"""Push the LEGACY lineage edges only (Sybase -> Snowflake).
Both endpoints exist as manual entities so this batch is safe.
"""
import requests, json
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP   = "https://pv-italodemo-16de97.purview.azure.com"
TOK  = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

TABLES = ["dim_policy", "dim_party", "dim_product", "fact_policy_monthly", "fact_claim"]

def ref(qn): return {"typeName": "DataSet", "uniqueAttributes": {"qualifiedName": qn}}

procs = []
for t in TABLES:
    SY = f"sybase://colmena-onprem.local/POLICIES/{t}"
    SF = f"snowflake://colmena.snowflakecomputing.com/COLMENA_LEGACY/PUBLIC/{t.upper()}"
    procs.append({
        "typeName": "Process",
        "attributes": {
            "qualifiedName": f"process://legacy_etl/sybase_to_snowflake/{t}",
            "name":          f"legacy_etl_sybase_to_snowflake_{t}",
            "description":   "Carga legacy (caja negra) Sybase -> Snowflake DW",
            "inputs":  [ref(SY)],
            "outputs": [ref(SF)],
        }
    })

r = requests.post(f"{EP}/catalog/api/atlas/v2/entity/bulk",
                  json={"entities": procs}, headers=H)
print("legacy lineage:", r.status_code)
res = r.json()
created = res.get("mutatedEntities", {}).get("CREATE", [])
print(f"  created: {len(created)}")
for e in created:
    print(f"   - {e['attributes']['qualifiedName']}")
