"""Create custom classifications for Chilean PII / business IDs via Atlas API.

  CL.RUT             : ^[0-9]{7,8}-[0-9Kk]$           (RUT chileno)
  CL.POLICY_NUMBER   : ^POL-[0-9]{10}$                 (numero de poliza Colmena)
  CL.CLAIM_NUMBER    : ^CLM-[0-9]{4}-[0-9]{6}$         (numero de siniestro)

Two-step process per classification:
  1) typedefs    -> classificationDefs           (the tag itself)
  2) scan/classificationrules -> regex rule      (engine that applies it)
"""
import requests, json, sys
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP  = "https://pv-italodemo-16de97.purview.azure.com"
TOK = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

CLASS_DEFS = [
  {
    "name":         "CL.RUT",
    "description":  "Chilean national ID (Rol Unico Tributario)",
    "displayName":  "CL RUT",
    "category":     "CLASSIFICATION",
    "superTypes":   [],
    "subTypes":     [],
    "entityTypes":  [],
  },
  {
    "name":         "CL.POLICY_NUMBER",
    "description":  "Colmena policy number",
    "displayName":  "CL Policy Number",
    "category":     "CLASSIFICATION",
    "superTypes":   [],
    "subTypes":     [],
    "entityTypes":  [],
  },
  {
    "name":         "CL.CLAIM_NUMBER",
    "description":  "Colmena claim number",
    "displayName":  "CL Claim Number",
    "category":     "CLASSIFICATION",
    "superTypes":   [],
    "subTypes":     [],
    "entityTypes":  [],
  },
]

# ---- step 1: typedefs ----
body = {"classificationDefs": CLASS_DEFS}
r = requests.post(f"{EP}/catalog/api/atlas/v2/types/typedefs", json=body, headers=H)
print("typedefs:", r.status_code, r.text[:400])

# ---- step 2: classification rules with regex pattern ----
RULES = [
  {
    "kind": "Custom",
    "name": "cl_rut_rule",
    "description": "Detect Chilean RUTs",
    "properties": {
        "description": "Detect Chilean RUTs in column values",
        "classificationName": "CL.RUT",
        "ruleStatus": "Enabled",
        "minimumPercentageMatch": 60.0,
        "columnPatterns":  [{"kind":"Regex","pattern":".*"}],
        "dataPatterns":    [{"kind":"Regex","pattern":"^[0-9]{7,8}-[0-9Kk]$"}],
    }
  },
  {
    "kind": "Custom",
    "name": "cl_policy_rule",
    "description": "Detect Colmena policy IDs",
    "properties": {
        "description": "Detect POL-NNNNNNNNNN policy IDs",
        "classificationName": "CL.POLICY_NUMBER",
        "ruleStatus": "Enabled",
        "minimumPercentageMatch": 60.0,
        "columnPatterns":  [{"kind":"Regex","pattern":".*"}],
        "dataPatterns":    [{"kind":"Regex","pattern":"^POL-[0-9]{10}$"}],
    }
  },
  {
    "kind": "Custom",
    "name": "cl_claim_rule",
    "description": "Detect Colmena claim IDs",
    "properties": {
        "description": "Detect CLM-YYYY-NNNNNN claim IDs",
        "classificationName": "CL.CLAIM_NUMBER",
        "ruleStatus": "Enabled",
        "minimumPercentageMatch": 60.0,
        "columnPatterns":  [{"kind":"Regex","pattern":".*"}],
        "dataPatterns":    [{"kind":"Regex","pattern":"^CLM-[0-9]{4}-[0-9]{6}$"}],
    }
  },
]

for rule in RULES:
    r = requests.put(f"{EP}/scan/classificationrules/{rule['name']}?api-version=2022-02-01-preview",
                     json=rule, headers=H)
    print(f"rule {rule['name']:18s} -> {r.status_code} {r.text[:200]}")
