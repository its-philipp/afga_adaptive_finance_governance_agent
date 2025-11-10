# Databricks notebook source
# MAGIC %md
# MAGIC # 02: Validate & Enrich Finance Transactions
# MAGIC
# MAGIC This notebook reads raw invoices from the bronze layer, validates business rules, computes finance governance signals, and publishes enriched records to the silver layer for downstream analytics and retrieval.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

dbutils.widgets.text("catalog_name", "afga_dev", "Unity Catalog")
dbutils.widgets.text("bronze_schema", "bronze", "Bronze Schema")
dbutils.widgets.text("silver_schema", "silver", "Silver Schema")

catalog_name = dbutils.widgets.get("catalog_name")
bronze_schema = dbutils.widgets.get("bronze_schema")
silver_schema = dbutils.widgets.get("silver_schema")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports & Setup

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType
from delta.tables import DeltaTable

spark = SparkSession.builder.appName("AFGA_ValidateTransform").getOrCreate()

bronze_table = f"{catalog_name}.{bronze_schema}.finance_transactions_raw"
silver_table = f"{catalog_name}.{silver_schema}.finance_transactions_enriched"

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"📦 Bronze source table : {bronze_table}")
print(f"🏛️ Silver target table : {silver_table}")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Bronze Data

# COMMAND ----------

bronze_df = spark.table(bronze_table)

if bronze_df.isEmpty():
    raise ValueError("❌ Bronze table is empty. Run notebook 01 to ingest raw invoices first.")

print(f"✅ Loaded {bronze_df.count()} bronze records")
bronze_df.select("invoice_id", "vendor", "amount", "currency").show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation Rules

# COMMAND ----------

issues = [
    F.when(F.col("invoice_id").isNull(), F.lit("missing_invoice_id")),
    F.when(F.col("vendor").isNull() | (F.length(F.col("vendor")) < 3), F.lit("invalid_vendor")),
    F.when(F.col("total").isNull() | (F.col("total") <= 0), F.lit("non_positive_total")),
    F.when(F.col("currency").isNull(), F.lit("missing_currency")),
    F.when(F.col("date").isNull(), F.lit("missing_posted_date")),
]

validated_df = (
    bronze_df
    .withColumn("_validation_array", F.array(*issues))
    .withColumn(
        "validation_messages",
        F.expr("filter(_validation_array, x -> x is not null)")
    )
    .withColumn(
        "validation_status",
        F.when(F.size(F.col("validation_messages")) > 0, F.lit("failed")).otherwise(F.lit("passed"))
    )
    .withColumn("validation_checked_at", F.current_timestamp())
    .drop("_validation_array")
)

failed_count = validated_df.filter(F.col("validation_status") == "failed").count()
print(f"⚠️ Validation failures: {failed_count}")

# Only promote valid invoices downstream
valid_invoices_df = validated_df.filter(F.col("validation_status") == "passed")
print(f"✅ Valid invoices ready for enrichment: {valid_invoices_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Currency Normalisation

# COMMAND ----------

currency_rates = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.73,
    "JPY": 0.0066,
}

rate_map = F.create_map([F.lit(x) for kv in currency_rates.items() for x in kv])

enriched_df = (
    valid_invoices_df
    .withColumn("exchange_rate_to_usd", F.coalesce(F.element_at(rate_map, F.col("currency")), F.lit(1.0)))
    .withColumn("amount_usd", F.round(F.col("total") * F.col("exchange_rate_to_usd"), 2))
    .withColumn("amount_pre_tax_usd", F.round(F.col("amount") * F.col("exchange_rate_to_usd"), 2))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Finance Governance Signals

# COMMAND ----------

risk_score = (
    F.lit(20)
    + F.when(F.col("amount_usd") > 15000, F.lit(25)).otherwise(F.lit(0))
    + F.when(F.col("vendor_reputation") < 60, F.lit(20)).otherwise(F.lit(0))
    + F.when(F.lower(F.col("compliance_status")) != F.lit("compliant"), F.lit(25)).otherwise(F.lit(0))
    + F.when(F.col("notes").rlike("(?i)(urgent|override|expedite)"), F.lit(10)).otherwise(F.lit(0))
    + F.when(F.col("payment_terms").rlike("(?i)net\\s*(60|90|120)"), F.lit(5)).otherwise(F.lit(0))
)

policy_flags_expr = F.array(
    F.when(F.col("amount_usd") > 20000, F.lit("high_value_approval")).otherwise(F.lit(None)),
    F.when(F.col("vendor_reputation") < 50, F.lit("vendor_watchlist")).otherwise(F.lit(None)),
    F.when(F.lower(F.col("compliance_status")) == F.lit("exception"), F.lit("requires_policy_exception")).otherwise(F.lit(None))
)

enriched_df = (
    enriched_df
    .withColumn("risk_score", F.round(risk_score, 2))
    .withColumn(
        "risk_level",
        F.when(F.col("risk_score") >= 70, F.lit("high"))
         .when(F.col("risk_score") >= 40, F.lit("medium"))
         .otherwise(F.lit("low"))
    )
    .withColumn("_policy_flags", policy_flags_expr)
    .withColumn("policy_flags", F.expr("filter(_policy_flags, x -> x is not null)"))
    .withColumn(
        "recommended_route",
        F.when(F.col("risk_level") == "high", F.lit("escalate_controller"))
         .when(F.col("risk_level") == "medium", F.lit("finance_review"))
         .otherwise(F.lit("auto_route"))
    )
    .drop("_policy_flags")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Narrative Summary for Retrieval

# COMMAND ----------

enriched_df = (
    enriched_df
    .withColumn(
        "structured_summary",
        F.concat_ws(
            " ",
            F.concat(F.lit("Invoice "), F.col("invoice_id"), F.lit(" from "), F.col("vendor")),
            F.concat(F.lit("worth $"), F.col("amount_usd").cast("string"), F.lit(" USD ("), F.col("currency"), F.lit(").")),
            F.concat(F.lit("Risk level:"), F.upper(F.col("risk_level"))),
            F.concat(F.lit("Policy flags:"), F.coalesce(F.array_join(F.col("policy_flags"), ", "), F.lit("none"))),
            F.concat(F.lit("Notes:"), F.coalesce(F.col("notes"), F.lit("n/a")))
        )
    )
    .withColumn("processed_at", F.current_timestamp())
)

enriched_df.select("invoice_id", "risk_level", "policy_flags", "structured_summary").show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Upsert into Silver

# COMMAND ----------

if spark.catalog.tableExists(silver_table):
    silver_delta = DeltaTable.forName(spark, silver_table)
    (
        silver_delta.alias("target")
        .merge(
            enriched_df.alias("source"),
            "target.invoice_id = source.invoice_id"
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    (
        enriched_df.write
        .format("delta")
        .mode("overwrite")
        .option("mergeSchema", "true")
        .saveAsTable(silver_table)
    )

print("✅ Silver table updated!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"📊 Valid invoices processed : {enriched_df.count()}")
print(f"⚠️ Failed validations       : {failed_count}")
print(f"🏛️ Silver table             : {silver_table}")
print(f"🎯 High-risk invoices       : {enriched_df.filter(F.col('risk_level') == 'high').count()}")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

