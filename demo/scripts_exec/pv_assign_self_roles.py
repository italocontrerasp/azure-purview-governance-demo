"""Assign self (current user) all built-in roles on the Purview root collection.

This is the one operation that the Terraform `azurerm_purview_account` cannot do —
Purview's RBAC lives in the data plane (`policystore/metadataPolicies`), not in ARM.
"""
import json, requests, sys
from pathlib import Path

EP        = "https://pv-italodemo-16de97.purview.azure.com"
USER_OID  = "be58243b-e1a7-47d4-96ab-c5ef5bd47f73"
SECRETS   = Path(__file__).resolve().parent.parent / ".secrets"
TOK       = (SECRETS / "pv_token.txt").read_text().strip()

H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

# 1. fetch current root policy
r = requests.get(f"{EP}/policystore/metadataPolicies?api-version=2021-07-01", headers=H)
r.raise_for_status()
pol = r.json()["values"][0]

ROLES = {
    "purviewmetadatarole_builtin_collection-administrator",
    "purviewmetadatarole_builtin_data-curator",
    "purviewmetadatarole_builtin_data-source-administrator",
    "purviewmetadatarole_builtin_purview-reader",
}

# 2. inject user OID into principal.microsoft.id of each target role rule
changed = 0
for rule in pol["properties"]["attributeRules"]:
    rid = rule["id"].split(":")[0]
    if rid not in ROLES:
        continue
    for cond_group in rule["dnfCondition"]:
        for cond in cond_group:
            if cond.get("attributeName") == "principal.microsoft.id":
                cur = cond.get("attributeValueIncludes") or []
                if USER_OID not in cur:
                    cur.append(USER_OID)
                    changed += 1
                cond["attributeValueIncludes"] = cur

print(f"rules updated: {changed}")

body = {
    "id":      pol["id"],
    "name":    pol["name"],
    "version": pol["version"],
    "properties": pol["properties"],
}

# 3. PUT updated policy
r2 = requests.put(f"{EP}/policystore/metadataPolicies/{pol['id']}?api-version=2021-07-01",
                  json=body, headers=H)
print("PUT", r2.status_code)
print(r2.text[:500])
sys.exit(0 if r2.status_code in (200, 201) else 1)
