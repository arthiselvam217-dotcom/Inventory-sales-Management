"""
Phase 5: PySpark Big Data Analytics Workflow
Inventory and Sales Analytics Web Application

This script executes a local PySpark ("local[*]") data pipeline that:
1. Extracts actual sales transactions and product details from SQLite.
2. Ingests data into an Apache Spark DataFrame.
3. Groups sales by product to compute total quantity sold, total revenue, and transaction statistics.
4. Displays top-selling products formatted with Indian Rupee (₹) currency.
5. Exports the summarized analytics to a CSV file in the reports/ directory.
"""

import os
import sys
import sqlite3
import pandas as pd

# 1. Windows Console UTF-8 Encoding Setup
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 2. PySpark Environment Configuration
if 'JAVA_HOME' not in os.environ:
    default_java = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot'
    if os.path.exists(default_java):
        os.environ['JAVA_HOME'] = default_java

os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'inventory.db')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
EXPORT_CSV = os.path.join(REPORTS_DIR, 'sales_raw_export.csv')
SUMMARY_CSV = os.path.join(REPORTS_DIR, 'pyspark_sales_summary.csv')

def extract_sales_from_sqlite(db_path=DB_PATH, output_csv=EXPORT_CSV):
    """Extract actual sales and product data from SQLite database to CSV."""
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at: {db_path}")

    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        s.id AS sale_id,
        s.product_id,
        COALESCE(p.name, 'Unknown Product') AS product_name,
        COALESCE(p.category, 'General') AS category,
        s.quantity,
        COALESCE(p.price, 0.0) AS unit_price,
        s.total_amount,
        s.sale_date
    FROM sales s
    LEFT JOIN products p ON s.product_id = p.id
    ORDER BY s.id ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("[WARN] SQLite database contains 0 sales records.")
    
    df.to_csv(output_csv, index=False)
    print(f"[1/5] Extracted {len(df)} sales records from SQLite to: {output_csv}")
    return output_csv, len(df)

def run_spark_analytics(input_csv=EXPORT_CSV, output_csv=SUMMARY_CSV):
    """Run PySpark analytics pipeline with local[*] SparkSession."""
    print("[2/5] Initializing local SparkSession ('local[*]')...")
    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("InventoryAndSalesAnalytics_Phase5")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    # Reduce verbose logger noise
    spark.sparkContext.setLogLevel("ERROR")

    try:
        print(f"[3/5] Ingesting CSV dataset into PySpark DataFrame...")
        df_spark = spark.read.csv(input_csv, header=True, inferSchema=True)
        print(" -> PySpark Inferred Schema:")
        df_spark.printSchema()

        record_count = df_spark.count()
        if record_count == 0:
            print("[WARN] Empty dataset. Skipping aggregations.")
            return

        print(f"[4/5] Performing PySpark GroupBy & Aggregations...")
        # Group sales by product and calculate total quantity sold and total revenue
        product_summary = (
            df_spark.groupBy("product_id", "product_name", "category")
            .agg(
                F.sum("quantity").alias("total_quantity_sold"),
                F.round(F.sum("total_amount"), 2).alias("total_revenue"),
                F.count("sale_id").alias("transaction_count"),
                F.round(F.avg("total_amount"), 2).alias("avg_sale_amount")
            )
            .orderBy(F.desc("total_revenue"), F.desc("total_quantity_sold"))
        )

        print("\n" + "=" * 80)
        print("PYSPARK ANALYSIS: TOP-SELLING PRODUCTS (SORTED BY REVENUE)")
        print("=" * 80)
        product_summary.show(truncate=False)

        # Convert to Pandas for clean console formatting with Indian Rupee (₹) symbol
        pandas_summary = product_summary.toPandas()
        
        print("\n" + "-" * 80)
        print(f"{'Rank':<5} | {'Product Name':<30} | {'Category':<15} | {'Units Sold':<10} | {'Total Revenue (₹)':<15}")
        print("-" * 80)
        for idx, row in pandas_summary.iterrows():
            rank = idx + 1
            print(f"{rank:<5} | {row['product_name']:<30} | {row['category']:<15} | {row['total_quantity_sold']:<10} | ₹{row['total_revenue']:>13,.2f}")
        print("-" * 80)

        # Overall totals using PySpark Aggregations
        overall_totals = df_spark.select(
            F.sum("quantity").alias("total_units"),
            F.round(F.sum("total_amount"), 2).alias("overall_revenue"),
            F.count("sale_id").alias("total_tx")
        ).collect()[0]

        print(f"\nOVERALL PYSPARK METRICS:")
        print(f" - Total Transactions : {overall_totals['total_tx']}")
        print(f" - Total Units Sold   : {overall_totals['total_units']}")
        print(f" - Total Sales Revenue: ₹{overall_totals['overall_revenue']:,.2f}")

        # 5. Save PySpark results as a CSV file
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        pandas_summary.to_csv(output_csv, index=False)
        print(f"\n[5/5] PySpark summarized results successfully saved to: {output_csv}")

        return pandas_summary

    finally:
        spark.stop()
        print("[✓] SparkSession cleanly terminated.")

def main():
    print("=" * 80)
    print("PHASE 5: PYSPARK LOCAL SALES ANALYTICS WORKFLOW")
    print("=" * 80)
    extract_sales_from_sqlite()
    run_spark_analytics()
    print("=" * 80)
    print("PHASE 5 WORKFLOW EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    main()
