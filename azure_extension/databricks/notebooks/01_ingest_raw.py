# Databricks notebook source
# MAGIC %md
# MAGIC # 01: Ingest Raw Finance Transactions from ADLS Gen2
# MAGIC
# MAGIC This notebook loads raw invoice and transaction JSON files from ADLS Gen2 into the bronze layer (Delta Lake + Unity Catalog) for downstream processing.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

dbutils.widgets.text("storage_account", "", "Storage Account Name")
dbutils.widgets.text("raw_container", "raw-transactions", "Raw Container")
dbutils.widgets.text("catalog_name", "afga_dev", "Unity Catalog")
dbutils.widgets.text("bronze_schema", "bronze", "Bronze Schema")
dbutils.widgets.text("limit_to_invoice", "", "Invoice ID (optional)")

storage_account = dbutils.widgets.get("storage_account")
raw_container = dbutils.widgets.get("raw_container")
catalog_name = dbutils.widgets.get("catalog_name")
bronze_schema = dbutils.widgets.get("bronze_schema")
invoice_filter = dbutils.widgets.get("limit_to_invoice")

if not storage_account:
    raise ValueError("❌ storage_account widget is required. Provide the ADLS account used for Phase 2 uploads.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, input_file_name, lit
spark = SparkSession.builder.appName("AFGA_IngestRawTransactions").getOrCreate()

# Build ADLS path (requires cluster credentials configured via spark conf or managed identity)
adls_base_path = f"abfss://{raw_container}@{storage_account}.dfs.core.windows.net/"

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"📂 Storage account      : {storage_account}")
print(f"📦 Raw container        : {raw_container}")
print(f"🗂️  Unity Catalog catalog: {catalog_name}")
print(f"🛢️ Bronze schema        : {bronze_schema}")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validate Storage Connectivity

# COMMAND ----------

print("🔍 Checking ADLS connectivity...")
try:
    sample_entries = dbutils.fs.ls(adls_base_path)
    print(f"✅ Connected! Found {len(sample_entries)} items at container root.")
    for entry in sample_entries[:5]:
        print(f"   - {entry.path} ({entry.size} bytes)")
except Exception as e:
    print(f"❌ Unable to list ADLS path {adls_base_path}. Verify credentials and container.")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Raw Invoice JSON

# COMMAND ----------

# Finance invoices are stored as JSON; schemas are well-defined in Phase 1 assets.
raw_path_pattern = adls_base_path + "**/*.json"

print(f"📥 Reading JSON files from {raw_path_pattern}")

raw_df = (
    spark.read
    .option("recursiveFileLookup", "true")
    .option("multiLine", "true")
    .json(raw_path_pattern)
)

if raw_df.isEmpty():
    raise ValueError(f"❌ No JSON invoices discovered under {raw_path_pattern}. Upload Phase 1 samples to ADLS first.")

# Persist invoice id to avoid recomputing file name extraction downstream
raw_df = (
    raw_df
    .withColumn("source_path", input_file_name())
    .withColumn("ingested_at", current_timestamp())
)

if invoice_filter:
    raw_df = raw_df.filter(col("invoice_id") == lit(invoice_filter))
    print(f"📎 Filtering to invoice_id={invoice_filter}")

print(f"✅ Loaded {raw_df.count()} invoices from ADLS.")
raw_df.select("invoice_id", "vendor", "amount", "currency", "date").show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Bronze (Delta + Unity Catalog)

# COMMAND ----------

bronze_table = f"{catalog_name}.{bronze_schema}.finance_transactions_raw"

(
    raw_df.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")
    .saveAsTable(bronze_table)
)

print("✅ Bronze load complete!")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"📊 Records ingested : {raw_df.count()}")
print(f"📌 Target table     : {bronze_table}")
print(f"📁 Source container : {raw_container}")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps

# MAGIC - Run notebook `02_validate_transform` to validate invoices and compute fraud signals.
# MAGIC - Configure Unity Catalog grants via `unity_catalog/*.sql` to expose data to AFGA services.
# MAGIC - Register this load with Databricks Workflows using `jobs/pipeline_job.json`.

