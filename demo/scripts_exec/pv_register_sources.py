"""Register ADLS Gen2 source in Purview pointing to our demo storage account."""
import requests, json
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP    = "https://pv-italodemo-16de97.purview.azure.com"
TOK   = (SECRETS / "pv_token.txt").read_text().strip()
SUBID = "f856a8ba-46fc-4efc-b8b7-0780a54d1fa4"

H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

# ---------- ADLS Gen2 ----------
adls_body = {
  "kind": "AdlsGen2",
  "name": "adls-italodemo-colmena",
  "properties": {
    "endpoint":     "https://stitalodemo16de97.dfs.core.windows.net/",
    "subscriptionId": SUBID,
    "resourceGroup": "rg-purview-demo",
    "location":      "brazilsouth",
    "resourceName":  "stitalodemo16de97",
    "resourceId":   f"/subscriptions/{SUBID}/resourceGroups/rg-purview-demo/providers/Microsoft.Storage/storageAccounts/stitalodemo16de97",
    "collection":   {"referenceName": "colmena", "type": "CollectionReference"},
    "dataUseGovernance": "Disabled",
  }
}

r = requests.put(f"{EP}/scan/datasources/adls-italodemo-colmena?api-version=2022-02-01-preview",
                 json=adls_body, headers=H)
print("ADLS source:", r.status_code, r.text[:300])
