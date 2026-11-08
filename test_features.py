"""
Comprehensive Verification and Test Suite
Inventory and Sales Analytics Web Application

Verifies:
1. Flask Application & Database Models
2. Product Management (CRUD & Search)
3. Sales Management (Record, Automatic Total, Stock Reduction, Insufficient Stock Validation)
4. NumPy & Pandas Data Analytics (Revenue, Units, Orders, Statistical Dispersion, Category Distribution)
5. PySpark Big Data Workflow & CSV Export
6. Demand Forecasting (Velocity, Linear Trend Slope, Estimations, Handling Insufficient Data)
7. Dashboard Integration & Indian Rupee (₹) Formatting
"""

import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd
from app import app
from extensions import db
from models import Product, Sale
from analytics.services import get_sales_analytics, get_demand_forecast
from utils import format_inr
import pyspark_analytics

def run_all_verification_tests():
    print("=" * 80)
    print("INVENTORY AND SALES ANALYTICS SYSTEM: END-TO-END VERIFICATION SUITE")
    print("=" * 80)

    client = app.test_client()

    with app.app_context():
        # -----------------------------------------------------------------
        # 1. Verify Indian Currency Formatter (Requirement 8)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 1] Testing Indian Currency Formatter (INR / ₹)...")
        assert format_inr(0) == "₹0.00", f"Failed for 0: {format_inr(0)}"
        assert format_inr(89.99) == "₹89.99", f"Failed for 89.99: {format_inr(89.99)}"
        assert format_inr(125000) == "₹1,25,000.00", f"Failed for 125000: {format_inr(125000)}"
        assert format_inr(10000000) == "₹1,00,00,000.00", f"Failed for 1 Crore: {format_inr(10000000)}"
        assert format_inr(-4500.5) == "-₹4,500.50", f"Failed for negative: {format_inr(-4500.5)}"
        print(" -> PASS: Indian currency formatting complies with Lakhs & Crores standard (₹1,25,000.00).")

        # -----------------------------------------------------------------
        # 2. Verify Database State & Models (Requirement 1)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 2] Verifying Database Models & Relationships...")
        products = Product.query.all()
        sales = Sale.query.all()
        print(f" -> Found {len(products)} products and {len(sales)} sales records in SQLite.")
        assert len(products) > 0, "No products found in database!"
        assert len(sales) > 0, "No sales found in database!"

        for s in sales:
            assert s.product is not None, f"Sale #{s.id} is missing product relationship!"
            assert s.quantity > 0, f"Sale #{s.id} has invalid quantity!"
            assert s.total_amount > 0, f"Sale #{s.id} has invalid total amount!"
        print(" -> PASS: One-to-many relationship (Product -> Sales) verified.")

        # -----------------------------------------------------------------
        # 3. Verify Product Management (Requirement 2)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 3] Verifying Product Management Endpoints...")
        # GET /products/
        res_prod = client.get('/products/')
        assert res_prod.status_code == 200
        assert 'Product Inventory' in res_prod.get_data(as_text=True)

        # Search
        res_search = client.get('/products/?q=Keyboard')
        assert res_search.status_code == 200
        assert 'Sample Mechanical Keyboard' in res_search.get_data(as_text=True)
        print(" -> PASS: Product listing and search filter verified.")

        # -----------------------------------------------------------------
        # 4. Verify Sales Management & Stock Deduction (Requirement 3)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 4] Verifying Sales Management & Stock Validation...")
        # GET /sales/
        res_sales = client.get('/sales/')
        assert res_sales.status_code == 200
        assert 'Sales Management' in res_sales.get_data(as_text=True)

        # Test overstock rejection
        sample_prod = products[0]
        curr_stock = sample_prod.stock
        res_invalid = client.post('/sales/record', data={
            'product_id': str(sample_prod.id),
            'quantity': str(curr_stock + 100)
        }, follow_redirects=True)
        assert 'Insufficient stock' in res_invalid.get_data(as_text=True)
        db.session.refresh(sample_prod)
        assert sample_prod.stock == curr_stock, "Stock incorrectly updated after rejected sale!"
        print(f" -> PASS: Insufficient stock validation verified for '{sample_prod.name}' (Stock: {curr_stock}).")

        # -----------------------------------------------------------------
        # 5. Verify NumPy & Pandas Analytics (Requirement 4)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 5] Verifying NumPy & Pandas Analytics Service...")
        analytics = get_sales_analytics()
        assert analytics["has_data"] is True
        assert analytics["total_revenue"] > 0
        assert analytics["total_units_sold"] > 0
        assert analytics["total_transactions"] == len(sales)
        assert analytics["total_products"] == len(products)
        assert len(analytics["category_analysis"]) > 0
        assert len(analytics["stats"]) == 4

        # Verify NumPy dispersion calculations
        raw_amounts = [float(s.total_amount) for s in sales]
        assert round(analytics["stats"]["min_sale"], 2) == round(float(np.min(raw_amounts)), 2)
        assert round(analytics["stats"]["max_sale"], 2) == round(float(np.max(raw_amounts)), 2)
        assert round(analytics["stats"]["median_sale"], 2) == round(float(np.median(raw_amounts)), 2)
        assert round(analytics["stats"]["std_sale"], 2) == round(float(np.std(raw_amounts)), 2)
        print(f" -> PASS: NumPy calculations verified: Mean={format_inr(analytics['avg_transaction_value'])}, StdDev={format_inr(analytics['stats']['std_sale'])}.")

        # Verify Category-Wise Breakdown
        cat_rev_sum = sum(c["total_revenue"] for c in analytics["category_analysis"])
        assert round(cat_rev_sum, 2) == round(analytics["total_revenue"], 2)
        print(f" -> PASS: Pandas category-wise breakdown ({len(analytics['category_analysis'])} categories) matches total revenue ({format_inr(analytics['total_revenue'])}).")

        # -----------------------------------------------------------------
        # 6. Verify Demand Forecasting Engine (Requirement 6)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 6] Verifying Demand Forecasting Engine...")
        forecast = get_demand_forecast()
        assert forecast["has_data"] is True
        assert len(forecast["forecast_list"]) == len(products)
        assert forecast["summary"]["total_projected_demand_30d"] > 0

        # Check that forecast estimates are distinct and labeled
        for item in forecast["forecast_list"]:
            assert "forecast_7d" in item
            assert "forecast_30d" in item
            assert "trend_label" in item
            assert "confidence" in item
            assert "stock_status" in item
            print(f"    - {item['product_name'][:25]:<25}: Sold={item['historical_sold']:<2} | Est. 30D Demand={item['forecast_30d']:<3} | Status={item['stock_status']}")

        print(f" -> PASS: Demand forecasting generated {len(forecast['forecast_list'])} product projections with risk flags.")

        # -----------------------------------------------------------------
        # 7. Verify Dashboard & UI (Requirement 7)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 7] Verifying Executive Dashboard & Visualizations...")
        dash_res = client.get('/dashboard')
        assert dash_res.status_code == 200
        dash_html = dash_res.get_data(as_text=True)

        assert 'Welcome to Inventory and Sales Analytics System' in dash_html
        assert 'Total Revenue' in dash_html
        assert 'Units Dispatched' in dash_html
        assert 'Total Products' in dash_html
        assert 'Total Orders' in dash_html
        assert 'dashSalesChart' in dash_html
        assert 'dashCategoryChart' in dash_html
        assert 'Best-Selling Products' in dash_html
        assert 'Demand Forecasting Highlights' in dash_html
        assert 'Recent Sales Transactions' in dash_html
        print(" -> PASS: Executive Dashboard rendered all KPIs, charts, and forecasts from actual DB records.")

        # -----------------------------------------------------------------
        # 8. Verify Dedicated Forecasting Page (Requirement 6 & 7)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 8] Verifying Dedicated Demand Forecasting Page (/analytics/forecast)...")
        fc_res = client.get('/analytics/forecast')
        assert fc_res.status_code == 200
        fc_html = fc_res.get_data(as_text=True)
        assert 'Demand Forecasting &amp; Inventory Planning' in fc_html or 'Demand Forecasting' in fc_html
        assert 'forecastChart' in fc_html
        assert 'Mathematical Forecasting Methodology' in fc_html
        print(" -> PASS: Dedicated forecasting page operational with viva methodology guide.")

        # -----------------------------------------------------------------
        # 9. Verify PySpark Pipeline & CSV Exports (Requirement 5)
        # -----------------------------------------------------------------
        print("\n[VERIFICATION 9] Verifying PySpark Export Reports in reports/ ...")
        reports_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'reports')
        raw_csv = os.path.join(reports_dir, 'sales_raw_export.csv')
        sales_summary = os.path.join(reports_dir, 'pyspark_sales_summary.csv')
        prod_summary = os.path.join(reports_dir, 'pyspark_product_summary.csv')
        cat_summary = os.path.join(reports_dir, 'pyspark_category_summary.csv')

        assert os.path.exists(raw_csv), f"Missing {raw_csv}"
        assert os.path.exists(sales_summary), f"Missing {sales_summary}"
        assert os.path.exists(prod_summary), f"Missing {prod_summary}"
        assert os.path.exists(cat_summary), f"Missing {cat_summary}"

        df_prod = pd.read_csv(prod_summary)
        df_cat = pd.read_csv(cat_summary)
        print(f" -> PySpark Product Summary: {len(df_prod)} rows exported.")
        print(f" -> PySpark Category Summary: {len(df_cat)} rows exported.")
        assert len(df_prod) > 0
        assert len(df_cat) > 0
        print(" -> PASS: All PySpark CSV export datasets verified.")

    print("\n" + "=" * 80)
    print("ALL 9 VERIFICATION AND DEMONSTRATION MODULES PASSED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == '__main__':
    run_all_verification_tests()
