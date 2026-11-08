"""
Phase 5: PySpark Big Data Analytics Workflow
Inventory and Sales Analytics Web Application

This script executes a local PySpark ("local[*]") data pipeline that:
1. Extracts actual sales transactions and product details from SQLite.
2. Ingests data into an Apache Spark DataFrame.
3. Groups sales by product to compute total quantity sold, total revenue, and transaction statistics.
4. Groups sales by category to compute category-wise revenue and volume distribution.
5. Identifies top-selling products and top revenue-generating categories.
6. Displays processed results formatted with Indian Rupee (₹) currency.
7. Exports the processed analytics results into CSV files inside the reports/ folder.
"""

import os
import sys
import sqlite3
import pandas as pd
from utils import format_inr

# 1. Windows Console UTF-8 Encoding Setup
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 2. PySpark Environment Configuration
# Handle Windows path resolution (especially with spaces in directory names)
def get_windows_short_path(path):
    if sys.platform == 'win32' and os.path.exists(path):
        try:
            import ctypes
            from ctypes import wintypes
            _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            _GetShortPathNameW.restype = wintypes.DWORD
            buf = ctypes.create_unicode_buffer(1024)
            res = _GetShortPathNameW(path, buf, 1024)
            if res > 0:
                return buf.value
        except Exception:
            pass
    return path

# Configure JAVA_HOME
if 'JAVA_HOME' not in os.environ:
    default_java = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot'
    if os.path.exists(default_java):
        os.environ['JAVA_HOME'] = default_java

py_exec = get_windows_short_path(sys.executable)
os.environ['PYSPARK_PYTHON'] = py_exec
os.environ['PYSPARK_DRIVER_PYTHON'] = py_exec

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'inventory.db')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
EXPORT_CSV = os.path.join(REPORTS_DIR, 'sales_raw_export.csv')
SUMMARY_CSV = os.path.join(REPORTS_DIR, 'pyspark_sales_summary.csv')
PROD_SUMMARY_CSV = os.path.join(REPORTS_DIR, 'pyspark_product_summary.csv')
CAT_SUMMARY_CSV = os.path.join(REPORTS_DIR, 'pyspark_category_summary.csv')

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
    """
    Run genuine PySpark analytics pipeline with local[*] SparkSession:
    - Product-wise quantity and revenue aggregation
    - Category-wise quantity and revenue aggregation
    - Identification of top-selling products
    - Export processed analytics to CSV reports
    """
    print("[2/5] Initializing local SparkSession ('local[*]')...")
    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("InventoryAndSalesAnalytics_PySpark")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
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
            return None, None

        print(f"[4/5] Performing PySpark GroupBy & Aggregations...")
        
        # 1. Product-Wise Aggregation in PySpark
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
        print("PYSPARK ANALYSIS 1: TOP-SELLING PRODUCTS (SORTED BY REVENUE)")
        print("=" * 80)
        product_summary.show(truncate=False)

        # 2. Category-Wise Aggregation in PySpark
        category_summary = (
            df_spark.groupBy("category")
            .agg(
                F.sum("quantity").alias("total_units_sold"),
                F.round(F.sum("total_amount"), 2).alias("total_revenue"),
                F.count("sale_id").alias("transaction_count"),
                F.round(F.avg("total_amount"), 2).alias("avg_sale_amount")
            )
            .orderBy(F.desc("total_revenue"), F.desc("total_units_sold"))
        )

        print("\n" + "=" * 80)
        print("PYSPARK ANALYSIS 2: CATEGORY-WISE SALES DISTRIBUTION")
        print("=" * 80)
        category_summary.show(truncate=False)

        # Convert to Pandas for clean console formatting with Indian Rupee (₹) symbol
        pandas_prod = product_summary.toPandas()
        pandas_cat = category_summary.toPandas()

        print("\n" + "-" * 85)
        print(f"{'Rank':<5} | {'Product Name':<30} | {'Category':<15} | {'Units Sold':<10} | {'Total Revenue'}")
        print("-" * 85)
        for idx, row in pandas_prod.iterrows():
            rank = idx + 1
            rev_str = format_inr(row['total_revenue'])
            print(f"{rank:<5} | {row['product_name']:<30} | {row['category']:<15} | {row['total_quantity_sold']:<10} | {rev_str:>16}")
        print("-" * 85)

        print("\n" + "-" * 75)
        print(f"{'Category':<20} | {'Units Sold':<12} | {'Transactions':<14} | {'Total Revenue'}")
        print("-" * 75)
        for idx, row in pandas_cat.iterrows():
            rev_str = format_inr(row['total_revenue'])
            print(f"{row['category']:<20} | {row['total_units_sold']:<12} | {row['transaction_count']:<14} | {rev_str:>16}")
        print("-" * 75)

        # Overall totals using PySpark Aggregations
        overall_totals = df_spark.select(
            F.sum("quantity").alias("total_units"),
            F.round(F.sum("total_amount"), 2).alias("overall_revenue"),
            F.count("sale_id").alias("total_tx")
        ).collect()[0]

        print(f"\nOVERALL PYSPARK METRICS:")
        print(f" - Total Transactions : {overall_totals['total_tx']}")
        print(f" - Total Units Sold   : {overall_totals['total_units']}")
        print(f" - Total Sales Revenue: {format_inr(overall_totals['overall_revenue'])}")

        # 5. Export PySpark results to CSV files in reports/ folder
        os.makedirs(REPORTS_DIR, exist_ok=True)
        pandas_prod.to_csv(output_csv, index=False)
        pandas_prod.to_csv(PROD_SUMMARY_CSV, index=False)
        pandas_cat.to_csv(CAT_SUMMARY_CSV, index=False)

        print(f"\n[5/5] PySpark summarized results exported to:")
        print(f"  -> Product Summary : {output_csv}")
        print(f"  -> Product Summary : {PROD_SUMMARY_CSV}")
        print(f"  -> Category Summary: {CAT_SUMMARY_CSV}")

        return pandas_prod, pandas_cat

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
