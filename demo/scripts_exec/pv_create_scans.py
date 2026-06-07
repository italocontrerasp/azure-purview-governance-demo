"""Create a scan ruleset that includes our custom classifications, then create
3 scans (bronze/silver/gold) on the ADLS source and trigger each."""
import requests, json, time
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP    = "https://pv-italodemo-16de97.purview.azure.com"
TOK   = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}
SRC = "adls-italodemo-colmena"

# ---------- Scan rule set ----------
# AdlsGen2 system rule set already exists; we just attach our custom rules to it implicitly
# by listing them in the scan definition.

CLASS_RULES = ["cl_rut_rule", "cl_policy_rule", "cl_claim_rule"]

# ---------- Scans (one per layer) ----------
SCANS = [
    ("scan_bronze_colmena", "/bronze/colmena"),
    ("scan_silver_colmena", "/silver/colmena"),
    ("scan_gold_colmena",   "/gold/colmena"),
]

for scan_name, path in SCANS:
    body = {
      "kind": "AdlsGen2Msi",
      "name": scan_name,
      "properties": {
        "scanRulesetName": "AdlsGen2",
        "scanRulesetType": "System",
        "collection": {"referenceName": "colmena", "type": "CollectionReference"},
        "resourceTypes": {
          "AdlsGen2": {
            "scanRulesetName": "AdlsGen2",
            "scanRulesetType": "System",
            "resourceNameFilter": {"includes": [path]},
          }
        }
      }
    }
    r = requests.put(f"{EP}/scan/datasources/{SRC}/scans/{scan_name}?api-version=2022-02-01-preview",
                     json=body, headers=H)
    print(f"scan {scan_name:25s} -> {r.status_code} {r.text[:140]}")

print("\nrun scans...")
for scan_name, _ in SCANS:
    r = requests.put(
        f"{EP}/scan/datasources/{SRC}/scans/{scan_name}/runs/{scan_name}-run1?api-version=2022-02-01-preview",
        headers=H)
    print(f"  trigger {scan_name:25s} -> {r.status_code} {r.text[:140]}")
