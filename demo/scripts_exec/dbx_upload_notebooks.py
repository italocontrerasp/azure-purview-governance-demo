"""Upload the 3 PySpark notebooks to Databricks workspace via REST API."""
import base64, requests
from pathlib import Path

DEMO    = Path(__file__).resolve().parent.parent
DBX_URL = "https://adb-7405614935582152.12.azuredatabricks.net"
TOK     = (DEMO / ".secrets" / "dbx_token.txt").read_text().strip()
NB_DIR  = DEMO / "notebooks"
USER    = "italocontrerasperez@outlook.com"

H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

for nb in ["nb_bronze_to_silver", "nb_silver_to_gold", "nb_dq_parity"]:
    src = NB_DIR / f"{nb}.py"
    b64 = base64.b64encode(src.read_bytes()).decode()
    body = {
        "path":      f"/Users/{USER}/{nb}",
        "format":    "SOURCE",
        "language":  "PYTHON",
        "content":   b64,
        "overwrite": True,
    }
    r = requests.post(f"{DBX_URL}/api/2.0/workspace/import", json=body, headers=H)
    print(f"{nb:25s} -> {r.status_code}  {r.text[:120]}")
