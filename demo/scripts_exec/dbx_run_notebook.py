"""Submit a one-time run for a notebook on the medallion cluster, poll until done."""
import requests, sys, time
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
DBX_URL = "https://adb-7405614935582152.12.azuredatabricks.net"
TOK     = (SECRETS / "dbx_token.txt").read_text().strip()
CLUSTER = "0606-045945-hk82wqk5"
USER    = "italocontrerasperez@outlook.com"

H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

def run(nb_name, timeout_sec=900):
    body = {
        "run_name":          f"run_{nb_name}",
        "existing_cluster_id": CLUSTER,
        "notebook_task": {"notebook_path": f"/Users/{USER}/{nb_name}"},
        "timeout_seconds":   timeout_sec,
    }
    r = requests.post(f"{DBX_URL}/api/2.1/jobs/runs/submit", json=body, headers=H)
    print(f"submit {nb_name} -> {r.status_code}", r.text[:200])
    run_id = r.json()["run_id"]

    while True:
        r = requests.get(f"{DBX_URL}/api/2.1/jobs/runs/get?run_id={run_id}", headers=H)
        st = r.json()["state"]
        life = st.get("life_cycle_state")
        result = st.get("result_state","-")
        msg = st.get("state_message","")[:80]
        print(f"  run {run_id}  life={life}  result={result}  msg={msg}")
        if life in ("TERMINATED", "INTERNAL_ERROR", "SKIPPED"):
            return run_id, st
        time.sleep(15)

if __name__ == "__main__":
    nb = sys.argv[1] if len(sys.argv) > 1 else "nb_bronze_to_silver"
    rid, final = run(nb)
    print("FINAL:", final)
