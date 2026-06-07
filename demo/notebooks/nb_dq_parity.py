# Databricks notebook source
# MAGIC %md
# MAGIC # nb_dq_parity
# MAGIC
# MAGIC **The historia técnica fuerte de la entrevista.**
# MAGIC
# MAGIC Validates parity between Snowflake legacy tables and new Delta gold tables during dual-load.
# MAGIC When a table passes thresholds N days in a row, publishes `migration_status=ready`
# MAGIC on the Delta asset in Purview via Atlas API.
# MAGIC
# MAGIC **In this demo**: since there is no real Snowflake, we simulate the legacy baseline
# MAGIC by reading the same source CSVs (bronze) — this represents the perfect-parity case.
# MAGIC In production the snowflake reader uses the snowflake-spark connector.

# COMMAND ----------

from pyspark.sql import functions as F
from datetime import date
import json, requests

GOLD = "abfss://gold@stitalodemo16de97.dfs.core.windows.net/colmena"
PARITY_PATH = f"{GOLD}/dq/parity_report"

# COMMAND ----------

# MAGIC %md ## Metric functions

# COMMAND ----------

def row_count(df):
    return df.count()

def checksum_by_pk(df, pk_cols):
    other = [c for c in df.columns if c not in pk_cols]
    return (df.withColumn("row_hash",
                F.sha2(F.concat_ws("||",
                    *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in other]), 256))
              .select(*pk_cols, "row_hash"))

def parity_for_pair(name, sf_df, dl_df, pk, tol_rc=0, tol_match=0.999):
    sf_count = row_count(sf_df)
    dl_count = row_count(dl_df)
    rc_diff  = abs(sf_count - dl_count)

    sf_hash = checksum_by_pk(sf_df, pk)
    dl_hash = checksum_by_pk(dl_df, pk)

    joined = sf_hash.alias("s").join(dl_hash.alias("d"), pk, "full_outer")
    total   = joined.count()
    matched = joined.filter(F.col("s.row_hash") == F.col("d.row_hash")).count()
    pct = (matched / total) if total else 0.0

    return {
        "run_date":         date.today().isoformat(),
        "table_name":       name,
        "sf_row_count":     int(sf_count),
        "dl_row_count":     int(dl_count),
        "row_count_diff":   int(rc_diff),
        "value_match_pct":  round(pct * 100, 4),
        "thresholds_met":   bool(rc_diff <= tol_rc and pct >= tol_match),
    }

# COMMAND ----------

# MAGIC %md ## Run parity for the 3 gold tables
# MAGIC Baseline = bronze CSV reread (= perfect parity, since both sides come from the same source).

# COMMAND ----------

BRONZE = "abfss://bronze@stitalodemo16de97.dfs.core.windows.net/colmena"

# dim_policy: en gold tiene columnas enriquecidas; comparamos por PK solamente para demo
dl_dim_policy = (spark.read.format("delta").load(f"{GOLD}/dim_policy")
                 .select("policy_id","party_id","product_id","start_date","end_date",
                         "monthly_premium_clp","policy_status"))

sf_dim_policy = (spark.read.option("header", True).csv(f"{BRONZE}/dim_policy/*.csv")
                 .select("policy_id","party_id","product_id","start_date","end_date",
                         "monthly_premium_clp",
                         F.col("status").alias("policy_status")))

res_policy = parity_for_pair("dim_policy", sf_dim_policy, dl_dim_policy, ["policy_id"])

# fact_policy_monthly
dl_fpm = (spark.read.format("delta").load(f"{GOLD}/fact_policy_monthly")
          .select("policy_id","month_date","premium_paid_clp","is_paid"))
sf_fpm = (spark.read.option("header", True).csv(f"{BRONZE}/fact_policy_monthly/*.csv")
          .select("policy_id","month_date","premium_paid_clp","is_paid"))

res_fpm = parity_for_pair("fact_policy_monthly", sf_fpm, dl_fpm, ["policy_id","month_date"])

# fact_claim
dl_clm = (spark.read.format("delta").load(f"{GOLD}/fact_claim")
          .select("claim_id","policy_id","party_id","claim_date","claim_type",
                  "claim_amount_clp","claim_status"))
sf_clm = (spark.read.option("header", True).csv(f"{BRONZE}/fact_claim/*.csv")
          .select("claim_id","policy_id","party_id","claim_date","claim_type",
                  "claim_amount_clp",
                  F.col("status").alias("claim_status")))

res_clm = parity_for_pair("fact_claim", sf_clm, dl_clm, ["claim_id"])

results = [res_policy, res_fpm, res_clm]
for r in results:
    print(json.dumps(r, indent=2))

# COMMAND ----------

# MAGIC %md ## Persist parity_report (append-only)

# COMMAND ----------

(spark.createDataFrame(results)
      .write.format("delta").mode("append").save(PARITY_PATH))

print("parity_report rows:",
      spark.read.format("delta").load(PARITY_PATH).count())

# COMMAND ----------

# MAGIC %md ## Publish migration_status=ready to Purview via Atlas API
# MAGIC
# MAGIC In production: only after N consecutive days of `thresholds_met=True`.
# MAGIC In this demo: we publish on first pass to demonstrate the API call.

# COMMAND ----------

PURVIEW_ENDPOINT = "https://pv-italodemo-16de97.purview.azure.com"

def get_purview_token():
    """In real Databricks the AAD token is from dbutils.secrets.get; for the demo we
    pre-provisioned a token in the cluster's spark conf."""
    tok = spark.conf.get("spark.italodemo.purview_token", None)
    if not tok:
        raise RuntimeError("set spark.italodemo.purview_token in the cluster conf")
    return tok

def mark_ready_in_purview(table_name, last_pass):
    qname = f"https://stitalodemo16de97.dfs.core.windows.net/gold/colmena/{table_name}"
    payload = {
        "entity": {
            "typeName": "azure_datalake_gen2_resource_set",
            "attributes": {
                "qualifiedName": qname,
                "name":          table_name,
            },
            "customAttributes": {
                "migration_status":      "ready",
                "parity_last_pass_date": last_pass,
                "parity_match_pct":      str(next(r["value_match_pct"]
                                                  for r in results
                                                  if r["table_name"] == table_name)),
            }
        }
    }
    r = requests.post(
        f"{PURVIEW_ENDPOINT}/catalog/api/atlas/v2/entity",
        json=payload,
        headers={"Authorization": f"Bearer {get_purview_token()}",
                 "Content-Type": "application/json"},
        timeout=30,
    )
    return r.status_code, r.text[:400]

for r in results:
    if r["thresholds_met"]:
        try:
            sc, body = mark_ready_in_purview(r["table_name"], r["run_date"])
            print(f"{r['table_name']:25s} -> HTTP {sc}  {body[:120]}")
        except Exception as e:
            print(f"{r['table_name']:25s} -> ERROR {e}")
    else:
        print(f"{r['table_name']:25s} -> SKIP (thresholds not met)")
