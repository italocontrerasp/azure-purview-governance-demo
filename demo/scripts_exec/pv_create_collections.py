"""Create child collections: Colmena → Sales / Underwriting / Claims."""
import requests, sys
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP   = "https://pv-italodemo-16de97.purview.azure.com"
ROOT = "pv-italodemo-16de97"
TOK  = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

# Tree definition: (name, friendlyName, parent)
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
    r = requests.put(f"{EP}/account/collections/{name}?api-version=2019-11-01-preview",
                     json=body, headers=H)
    print(f"PUT {name:14s} -> {r.status_code}  {r.text[:120]}")

print("\n--- final tree ---")
r = requests.get(f"{EP}/account/collections?api-version=2019-11-01-preview", headers=H)
for c in r.json().get("value", []):
    print(f"{c.get('name','?'):24s} parent={c.get('parentCollection',{}).get('referenceName','-')}  state={c.get('collectionProvisioningState','?')}")
