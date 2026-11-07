import os
import sys

# Ensure UTF-8 output encoding for Indian Rupee symbol on Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd
from app import app
from extensions import db
from models import Product, Sale
from analytics.services import get_sales_analytics

def run_phase4_tests():
    print("=" * 70)
    print("PHASE 4: SALES ANALYTICS (NUMPY & PANDAS) INTEGRATION TEST SUITE")
    print("=" * 70)

    client = app.test_client()

    with app.app_context():
        # Ensure we have active sample data in DB
        prod_count = Product.query.count()
        sale_count = Sale.query.count()
        print(f"\n[INFO] Current Database State: {prod_count} product(s), {sale_count} sale(s).")

        # If database has no sales yet, add 2 sample products and 3 sample sales
        if sale_count == 0:
            print(" -> Seeding baseline sales transactions for verification...")
            p1 = Product(name="Analytics Sample Laptop", category="Computers", price=55000.0, stock=20, description="Test Laptop")
            p2 = Product(name="Analytics Sample Mouse", category="Accessories", price=1200.0, stock=50, description="Test Mouse")
            db.session.add_all([p1, p2])
            db.session.commit()

            s1 = Sale(product_id=p1.id, quantity=2, total_amount=110000.0)
            s2 = Sale(product_id=p2.id, quantity=5, total_amount=6000.0)
            s3 = Sale(product_id=p2.id, quantity=3, total_amount=3600.0)
            db.session.add_all([s1, s2, s3])
            db.session.commit()

        # -------------------------------------------------------------
        # TEST 1: Reusable Analytics Service & DB Fetch
        # -------------------------------------------------------------
        print("\n[TEST 1] Fetching actual database records via get_sales_analytics()...")
        analytics = get_sales_analytics()
        assert analytics["has_data"] is True, "Service reported no data despite database containing sales!"
        print(f" -> PASS: Analytics computed successfully for {analytics['total_transactions']} transaction(s).")

        # -------------------------------------------------------------
        # TEST 2: NumPy Statistical Calculation Integrity
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying NumPy calculations against raw DB records...")
        raw_sales = Sale.query.all()
        db_amounts = [float(s.total_amount) for s in raw_sales]
        db_quantities = [int(s.quantity) for s in raw_sales]

        expected_revenue = float(np.sum(db_amounts))
        expected_units = int(np.sum(db_quantities))
        expected_mean = float(np.mean(db_amounts))
        expected_min = float(np.min(db_amounts))
        expected_max = float(np.max(db_amounts))
        expected_median = float(np.median(db_amounts))
        expected_std = float(np.std(db_amounts))

        assert round(analytics["total_revenue"], 2) == round(expected_revenue, 2), "Revenue mismatch!"
        assert analytics["total_units_sold"] == expected_units, "Units sold mismatch!"
        assert round(analytics["avg_transaction_value"], 2) == round(expected_mean, 2), "Mean sale mismatch!"
        assert round(analytics["stats"]["min_sale"], 2) == round(expected_min, 2), "Min sale mismatch!"
        assert round(analytics["stats"]["max_sale"], 2) == round(expected_max, 2), "Max sale mismatch!"
        assert round(analytics["stats"]["median_sale"], 2) == round(expected_median, 2), "Median sale mismatch!"
        assert round(analytics["stats"]["std_sale"], 2) == round(expected_std, 2), "Std deviation mismatch!"

        print(f" -> PASS: NumPy calculations verified:")
        print(f"    - Total Revenue     : ₹{analytics['total_revenue']:,.2f}")
        print(f"    - Total Units Sold  : {analytics['total_units_sold']}")
        print(f"    - Average Sale      : ₹{analytics['avg_transaction_value']:,.2f}")
        print(f"    - Min / Max Sale    : ₹{analytics['stats']['min_sale']:,.2f} / ₹{analytics['stats']['max_sale']:,.2f}")
        print(f"    - Median Sale       : ₹{analytics['stats']['median_sale']:,.2f}")
        print(f"    - Std Deviation (σ) : ₹{analytics['stats']['std_sale']:,.2f}")

        # -------------------------------------------------------------
        # TEST 3: Pandas GroupBy Product-Wise Analysis
        # -------------------------------------------------------------
        print("\n[TEST 3] Verifying Pandas GroupBy product-wise aggregation...")
        prod_analysis = analytics["product_analysis"]
        assert len(prod_analysis) > 0, "Product analysis list is empty!"

        total_analyzed_revenue = sum(p["total_revenue"] for p in prod_analysis)
        total_analyzed_units = sum(p["total_quantity"] for p in prod_analysis)

        assert round(total_analyzed_revenue, 2) == round(expected_revenue, 2), "Grouped revenue sum mismatch!"
        assert total_analyzed_units == expected_units, "Grouped units sold sum mismatch!"
        print(f" -> PASS: Pandas GroupBy aggregated {len(prod_analysis)} products matching database total revenue (₹{total_analyzed_revenue:,.2f}).")

        # -------------------------------------------------------------
        # TEST 4: Fast-Moving & Slow-Moving Categorization
        # -------------------------------------------------------------
        print("\n[TEST 4] Verifying fast-moving vs slow-moving classification...")
        fast_moving = analytics["fast_moving"]
        slow_moving = analytics["slow_moving"]

        print(f"    Fast-Moving count: {len(fast_moving)}")
        print(f"    Slow-Moving count: {len(slow_moving)}")

        for p in fast_moving:
            assert p["total_quantity"] > 0, "Fast-moving product has 0 units sold!"
            assert p["movement"] == "Fast-Moving"

        for p in slow_moving:
            assert p["movement"] == "Slow-Moving"

        print(" -> PASS: Product movement categorization verified.")

        # -------------------------------------------------------------
        # TEST 5: Daily & Monthly Sales Summaries (Pandas)
        # -------------------------------------------------------------
        print("\n[TEST 5] Verifying daily & monthly summaries...")
        daily = analytics["daily_summary"]
        monthly = analytics["monthly_summary"]

        assert len(daily) > 0, "Daily summary is empty!"
        assert len(monthly) > 0, "Monthly summary is empty!"

        daily_revenue_sum = sum(d["revenue"] for d in daily)
        monthly_revenue_sum = sum(m["revenue"] for m in monthly)

        assert round(daily_revenue_sum, 2) == round(expected_revenue, 2), "Daily revenue sum mismatch!"
        assert round(monthly_revenue_sum, 2) == round(expected_revenue, 2), "Monthly revenue sum mismatch!"
        print(f" -> PASS: Daily summary ({len(daily)} days) and monthly summary ({len(monthly)} months) match total revenue.")

        # -------------------------------------------------------------
        # TEST 6: Chart.js Payload Structures
        # -------------------------------------------------------------
        print("\n[TEST 6] Verifying Chart.js payload structures...")
        chart_daily = analytics["chart_daily"]
        chart_prods = analytics["chart_products"]

        assert len(chart_daily["labels"]) == len(chart_daily["revenues"]) == len(chart_daily["quantities"])
        assert len(chart_prods["labels"]) == len(chart_prods["revenues"]) == len(chart_prods["quantities"])
        print(f" -> PASS: Chart.js datasets verified with {len(chart_daily['labels'])} timeline points and {len(chart_prods['labels'])} products.")

        # -------------------------------------------------------------
        # TEST 7: Graceful Empty Data Handling
        # -------------------------------------------------------------
        print("\n[TEST 7] Testing empty data handling...")
        # Temporarily test behavior with empty query logic
        from unittest.mock import patch
        with patch("analytics.services.Sale.query") as mock_sale_query:
            mock_sale_query.order_by.return_value.all.return_value = []
            empty_analytics = get_sales_analytics()
            assert empty_analytics["has_data"] is False
            assert empty_analytics["total_revenue"] == 0.0
            assert empty_analytics["total_units_sold"] == 0
            assert empty_analytics["stats"]["min_sale"] == 0.0
        print(" -> PASS: Empty sales state handled gracefully without errors.")

        # -------------------------------------------------------------
        # TEST 8: Web Route Verification (GET /analytics/)
        # -------------------------------------------------------------
        print("\n[TEST 8] Verifying web endpoint GET /analytics/...")
        res = client.get('/analytics/')
        assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
        html = res.get_data(as_text=True)

        assert 'Sales & Inventory Analytics' in html
        assert '₹' in html
        assert 'salesTrendChart' in html
        assert 'productBarChart' in html
        assert 'Fast-Moving Products' in html
        assert 'Slow-Moving' in html
        print(" -> PASS: /analytics/ endpoint rendered HTTP 200 with Chart.js canvases and INR (₹) formatting.")

        # -------------------------------------------------------------
        # TEST 9: Regression Check across all routes
        # -------------------------------------------------------------
        print("\n[TEST 9] Regression check across all application blueprints...")
        for endpoint, title_check in [
            ('/', 'Inventory and Sales Analytics System'),
            ('/dashboard', 'Inventory and Sales Analytics System'),
            ('/products/', 'Product Inventory'),
            ('/sales/', 'Sales Management'),
            ('/analytics/', 'Sales & Inventory Analytics')
        ]:
            r = client.get(endpoint)
            assert r.status_code == 200, f"Failed at {endpoint} with {r.status_code}"
            assert title_check in r.get_data(as_text=True)
            print(f"    - {endpoint:15} -> 200 OK (Verified: '{title_check}')")

        print(" -> PASS: All existing Phase 1, 2, and 3 routes functional.")

    print("\n" + "=" * 70)
    print("ALL PHASE 4 SALES ANALYTICS TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_phase4_tests()
