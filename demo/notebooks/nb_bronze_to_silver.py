# Databricks notebook source
# MAGIC %md
# MAGIC # nb_bronze_to_silver
# MAGIC
# MAGIC Reads raw CSVs from ADLS bronze and writes cleansed Delta tables to silver.
# MAGIC Replaces the legacy Snowflake stored procedure `sp_load_silver_*` family.
# MAGIC
# MAGIC **Inputs**: `abfss://bronze@stitalodemo16de97.dfs.core.windows.net/colmena/{table}/*.csv`
# MAGIC **Outputs**: `abfss://silver@stitalodemo16de97.dfs.core.windows.net/colmena/{table}/`

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *

BRONZE = "abfss://bronze@stitalodemo16de97.dfs.core.windows.net/colmena"
SILVER = "abfss://silver@stitalodemo16de97.dfs.core.windows.net/colmena"

# COMMAND ----------

# MAGIC %md ## dim_party — normaliza tipos y agrega processed_ts

# COMMAND ----------

party_schema = StructType([
    StructField("party_id",   StringType(), False),
    StructField("rut",        StringType(), False),
    StructField("full_name",  StringType(), True),
    StructField("email",      StringType(), True),
    StructField("phone",      StringType(), True),
    StructField("comuna",     StringType(), True),
    StructField("birth_date", DateType(),   True),
])

(spark.read.option("header", True).schema(party_schema).csv(f"{BRONZE}/dim_party/*.csv")
       .withColumn("processed_ts", F.current_timestamp())
       .withColumn("rut_clean", F.upper(F.regexp_replace("rut", "[.]", "")))
       .write.format("delta").mode("overwrite")
       .save(f"{SILVER}/dim_party"))
print("silver/dim_party OK")

# COMMAND ----------

# MAGIC %md ## dim_product

# COMMAND ----------

product_schema = StructType([
    StructField("product_id",       StringType(), False),
    StructField("product_code",     StringType(), False),
    StructField("product_name",     StringType(), True),
    StructField("category",         StringType(), True),
    StructField("base_premium_clp", IntegerType(), True),
])

(spark.read.option("header", True).schema(product_schema).csv(f"{BRONZE}/dim_product/*.csv")
       .withColumn("processed_ts", F.current_timestamp())
       .write.format("delta").mode("overwrite")
       .save(f"{SILVER}/dim_product"))
print("silver/dim_product OK")

# COMMAND ----------

# MAGIC %md ## dim_policy

# COMMAND ----------

policy_schema = StructType([
    StructField("policy_id",            StringType(), False),
    StructField("party_id",             StringType(), False),
    StructField("product_id",           StringType(), False),
    StructField("start_date",           DateType(), True),
    StructField("end_date",             DateType(), True),
    StructField("monthly_premium_clp",  IntegerType(), True),
    StructField("status",               StringType(), True),
])

(spark.read.option("header", True).schema(policy_schema).csv(f"{BRONZE}/dim_policy/*.csv")
       .withColumn("processed_ts", F.current_timestamp())
       .write.format("delta").mode("overwrite")
       .save(f"{SILVER}/dim_policy"))
print("silver/dim_policy OK")

# COMMAND ----------

# MAGIC %md ## fact_policy_monthly

# COMMAND ----------

fpm_schema = StructType([
    StructField("policy_id",        StringType(), False),
    StructField("month_date",       DateType(),   False),
    StructField("premium_paid_clp", IntegerType(), True),
    StructField("is_paid",          BooleanType(), True),
])

(spark.read.option("header", True).schema(fpm_schema).csv(f"{BRONZE}/fact_policy_monthly/*.csv")
       .withColumn("processed_ts", F.current_timestamp())
       .write.format("delta").mode("overwrite")
       .save(f"{SILVER}/fact_policy_monthly"))
print("silver/fact_policy_monthly OK")

# COMMAND ----------

# MAGIC %md ## fact_claim

# COMMAND ----------

claim_schema = StructType([
    StructField("claim_id",         StringType(), False),
    StructField("policy_id",        StringType(), False),
    StructField("party_id",         StringType(), False),
    StructField("claim_date",       DateType(), True),
    StructField("claim_type",       StringType(), True),
    StructField("claim_amount_clp", IntegerType(), True),
    StructField("status",           StringType(), True),
])

(spark.read.option("header", True).schema(claim_schema).csv(f"{BRONZE}/fact_claim/*.csv")
       .withColumn("processed_ts", F.current_timestamp())
       .write.format("delta").mode("overwrite")
       .save(f"{SILVER}/fact_claim"))
print("silver/fact_claim OK")

# COMMAND ----------

# Sanity counts
for t in ["dim_party","dim_product","dim_policy","fact_policy_monthly","fact_claim"]:
    print(t, spark.read.format("delta").load(f"{SILVER}/{t}").count())
