"""Push manual Atlas entities to represent the legacy systems that don't physically
exist in this demo:
  - Sybase on-prem  (OLTP source)
  - Snowflake DW    (legacy analytical layer with 20+ SPs)

These are CREATED as manual entries via Atlas API so the catalog and lineage graph
reflect the real Colmena topology even though the physical systems aren't deployed.

Pattern documented in Microsoft Purview docs (custom types / manual entities)
for sources without native connectors.
"""
import requests, json
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP    = "https://pv-italodemo-16de97.purview.azure.com"
TOK   = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

# ---------- Tables in each legacy system ----------
TABLES = ["dim_policy", "dim_party", "dim_product", "fact_policy_monthly", "fact_claim"]

entities = []

# Sybase
for t in TABLES:
    entities.append({
        "typeName": "DataSet",
        "attributes": {
            "qualifiedName": f"sybase://colmena-onprem.local/POLICIES/{t}",
            "name":          f"sybase.POLICIES.{t}",
            "description":   f"Legacy on-prem Sybase table (OLTP) — {t}",
        }
    })

# Snowflake legacy DW
for t in TABLES:
    entities.append({
        "typeName": "DataSet",
        "attributes": {
            "qualifiedName": f"snowflake://colmena.snowflakecomputing.com/COLMENA_LEGACY/PUBLIC/{t.upper()}",
            "name":          f"snowflake.COLMENA_LEGACY.{t.upper()}",
            "description":   f"Snowflake DW legacy table — produced by sp_build_{t}",
        }
    })

body = {"entities": entities}
r = requests.post(f"{EP}/catalog/api/atlas/v2/entity/bulk", json=body, headers=H)
print("bulk create:", r.status_code)
res = r.json()
gmap = res.get("guidAssignments", {})
created = res.get("mutatedEntities", {}).get("CREATE", [])
print(f"  created: {len(created)}")
for e in created[:5]:
    print(f"   - {e['attributes']['qualifiedName']}  guid={e['guid']}")

# move them under the right Purview collection
print("\nmove to collection 'colmena'...")
move_body = {"entityGuids": [e["guid"] for e in created]}
r = requests.post(f"{EP}/account/collections/colmena/entity:moveHere?api-version=2022-08-01-preview",
                  json=move_body, headers=H)
print("move:", r.status_code, r.text[:200])
