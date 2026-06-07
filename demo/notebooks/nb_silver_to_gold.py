# Databricks notebook source
# MAGIC %md
# MAGIC # nb_silver_to_gold
# MAGIC
# MAGIC Builds analytical gold marts from silver Delta tables.
# MAGIC Replaces the Snowflake stored procedures `sp_build_gold_*` family.
# MAGIC
# MAGIC **Inputs**: `silver/colmena/*` Delta
# MAGIC **Outputs**:
# MAGIC - `gold/colmena/dim_policy` (conformed dim with party + product joined)
# MAGIC - `gold/colmena/fact_policy_monthly` (with party + product enrichment)
# MAGIC - `gold/colmena/fact_claim` (with party + policy enrichment)

# COMMAND ----------

from pyspark.sql import functions as F

SILVER = "abfss://silver@stitalodemo16de97.dfs.core.windows.net/colmena"
GOLD   = "abfss://gold@stitalodemo16de97.dfs.core.windows.net/colmena"

dim_party   = spark.read.format("delta").load(f"{SILVER}/dim_party")
dim_product = spark.read.format("delta").load(f"{SILVER}/dim_product")
dim_policy  = spark.read.format("delta").load(f"{SILVER}/dim_policy")
f_fpm       = spark.read.format("delta").load(f"{SILVER}/fact_policy_monthly")
f_clm       = spark.read.format("delta").load(f"{SILVER}/fact_claim")

# COMMAND ----------

# MAGIC %md ## gold/dim_policy — conformed dim

# COMMAND ----------

gold_dim_policy = (dim_policy.alias("p")
    .join(dim_party.alias("pty"),   "party_id",   "left")
    .join(dim_product.alias("prd"), "product_id", "left")
    .select(
        F.col("p.policy_id"),
        F.col("p.party_id"),
        F.col("pty.rut").alias("party_rut"),
        F.col("pty.full_name").alias("party_name"),
        F.col("pty.email").alias("party_email"),
        F.col("p.product_id"),
        F.col("prd.product_code"),
        F.col("prd.product_name"),
        F.col("prd.category").alias("product_category"),
        F.col("p.start_date"),
        F.col("p.end_date"),
        F.col("p.monthly_premium_clp"),
        F.col("p.status").alias("policy_status"),
        F.current_timestamp().alias("gold_processed_ts"),
    ))

(gold_dim_policy.write.format("delta").mode("overwrite")
                .save(f"{GOLD}/dim_policy"))
print("gold/dim_policy rows:", gold_dim_policy.count())

# COMMAND ----------

# MAGIC %md ## gold/fact_policy_monthly

# COMMAND ----------

gold_fpm = (f_fpm.alias("f")
    .join(gold_dim_policy.alias("p"), "policy_id", "inner")
    .select(
        F.col("f.policy_id"),
        F.col("p.party_id"),
        F.col("p.party_rut"),
        F.col("p.product_code"),
        F.col("p.product_category"),
        F.col("f.month_date"),
        F.col("f.premium_paid_clp"),
        F.col("f.is_paid"),
        F.year("f.month_date").alias("year"),
        F.month("f.month_date").alias("month"),
        F.current_timestamp().alias("gold_processed_ts"),
    ))

(gold_fpm.write.format("delta").mode("overwrite")
         .partitionBy("year")
         .save(f"{GOLD}/fact_policy_monthly"))
print("gold/fact_policy_monthly rows:", gold_fpm.count())

# COMMAND ----------

# MAGIC %md ## gold/fact_claim

# COMMAND ----------

gold_fclm = (f_clm.alias("c")
    .join(dim_party.alias("pty"),  "party_id",  "left")
    .join(dim_policy.alias("p"),   "policy_id", "left")
    .select(
        F.col("c.claim_id"),
        F.col("c.policy_id"),
        F.col("c.party_id"),
        F.col("pty.rut").alias("party_rut"),
        F.col("pty.full_name").alias("party_name"),
        F.col("p.product_id"),
        F.col("c.claim_date"),
        F.col("c.claim_type"),
        F.col("c.claim_amount_clp"),
        F.col("c.status").alias("claim_status"),
        F.year("c.claim_date").alias("year"),
        F.current_timestamp().alias("gold_processed_ts"),
    ))

(gold_fclm.write.format("delta").mode("overwrite")
          .partitionBy("year")
          .save(f"{GOLD}/fact_claim"))
print("gold/fact_claim rows:", gold_fclm.count())

# COMMAND ----------

print("=== GOLD COUNTS ===")
for t in ["dim_policy","fact_policy_monthly","fact_claim"]:
    print(t, spark.read.format("delta").load(f"{GOLD}/{t}").count())
