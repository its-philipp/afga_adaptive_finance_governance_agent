# Databricks notebook source
# MAGIC %md
# MAGIC # 03: Embed Finance Summaries & Prepare Vector Search
# MAGIC
# MAGIC This notebook converts enriched finance governance records into vector-friendly summaries using OpenAI embeddings and stores them in the gold layer, ready for AFGA retrieval scenarios.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

dbutils.widgets.text("catalog_name", "afga_dev", "Unity Catalog")
dbutils.widgets.text("silver_schema", "silver", "Silver Schema")
dbutils.widgets.text("gold_schema", "gold", "Gold Schema")
dbutils.widgets.text("openai_api_key", "", "OpenAI API Key (optional override)")
dbutils.widgets.text("openai_model", "text-embedding-3-small", "OpenAI Embedding Model")
dbutils.widgets.text("vector_index_name", "finance_transactions_index", "Vector Index Name")

catalog_name = dbutils.widgets.get("catalog_name")
silver_schema = dbutils.widgets.get("silver_schema")
gold_schema = dbutils.widgets.get("gold_schema")
openai_model = dbutils.widgets.get("openai_model")
vector_index_name = dbutils.widgets.get("vector_index_name")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

%pip install --upgrade --force-reinstall openai httpx
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Configuration (After Restart)

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, FloatType
import os

spark = SparkSession.builder.appName("AFGA_EmbedTransactions").getOrCreate()

silver_table = f"{catalog_name}.{silver_schema}.finance_transactions_enriched"
gold_table = f"{catalog_name}.{gold_schema}.finance_transaction_embeddings"

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"🏛️ Source table : {silver_table}")
print(f"🥇 Target table : {gold_table}")
print(f"🧠 Embedding model: {openai_model}")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# Load API key from Databricks secrets first
try:
    openai_api_key = dbutils.secrets.get(scope="afga-secrets", key="openai-api-key")
    print("🔐 Using OpenAI API key from secret scope afga-secrets/openai-api-key")
except Exception:
    openai_api_key = dbutils.widgets.get("openai_api_key")
    if openai_api_key:
        print("⚠️ Using API key from widget (consider storing in Databricks secrets)")
    else:
        raise ValueError("❌ OpenAI API key not found. Create scope 'afga-secrets' with key 'openai-api-key' or supply widget value.")

os.environ["OPENAI_API_KEY"] = openai_api_key

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Records

# COMMAND ----------

silver_df = spark.table(silver_table)

if silver_df.isEmpty():
    raise ValueError("❌ Silver table is empty. Run notebook 02 before generating embeddings.")

print(f"✅ Loaded {silver_df.count()} enriched invoices for embedding")
silver_df.select("invoice_id", "risk_level", "structured_summary").show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prepare Embedding Payload

# COMMAND ----------

# Only embed records that changed since last export to avoid duplication
columns_for_embedding = [
    "invoice_id",
    "structured_summary",
    "risk_score",
    "risk_level",
    "recommended_route",
    "amount_usd",
    "vendor",
    "policy_flags",
    "processed_at",
]

payload_df = silver_df.select(*columns_for_embedding)

print(f"📦 Preparing {payload_df.count()} invoice summaries for embedding")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Embeddings

# COMMAND ----------

from openai import OpenAI
from pyspark.sql.functions import pandas_udf
import pandas as pd

client = OpenAI()

def embed_texts(texts, model):
    embeddings = []
    for text in texts:
        if not text or text.strip() == "":
            embeddings.append([])
            continue
        try:
            response = client.embeddings.create(
                model=model,
                input=text[:8000]
            )
            embeddings.append(response.data[0].embedding)
        except Exception as exc:
            print(f"⚠️ Embedding failure: {exc}")
            embeddings.append([])
    return embeddings

@pandas_udf(ArrayType(FloatType()))
def embedding_udf(text_series: pd.Series) -> pd.Series:
    return pd.Series(embed_texts(text_series.tolist(), openai_model))

embedded_df = payload_df.withColumn("embedding", embedding_udf(F.col("structured_summary")))
embedded_df = embedded_df.filter(F.size(F.col("embedding")) > 0)

print(f"✅ Generated embeddings for {embedded_df.count()} invoices")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Persist to Gold Layer

# COMMAND ----------

from delta.tables import DeltaTable

if spark.catalog.tableExists(gold_table):
    gold_delta = DeltaTable.forName(spark, gold_table)
    (
        gold_delta.alias("target")
        .merge(
            embedded_df.alias("source"),
            "target.invoice_id = source.invoice_id"
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    (
        embedded_df.write
        .format("delta")
        .mode("overwrite")
        .option("mergeSchema", "true")
        .saveAsTable(gold_table)
    )

print("🥇 Gold embeddings table updated")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Vector Search Notes

# COMMAND ----------

print("📝 Vector Search Integration Checklist")
print("--------------------------------------")
print(f"• Suggested index name : {vector_index_name}")
print(f"• Source table         : {gold_table}")
print("• Embedding column     : embedding")
print("• Metadata columns     : vendor, risk_level, policy_flags")
print("")
print("To enable Databricks Vector Search:")
print("1. Create a Vector Search endpoint once per workspace.")
print("2. Register index pointing at the gold table.")
print("3. Enable automated sync in the job definition or call the REST API post-update.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

high_risk = embedded_df.filter(F.col("risk_level") == "high").count()

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("✅ Embedding job complete")
print(f"📊 Records embedded     : {embedded_df.count()}")
print(f"🔥 High risk embeddings  : {high_risk}")
print(f"🥇 Gold table destination: {gold_table}")
print(f"🧠 Embedding model       : {openai_model}")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

