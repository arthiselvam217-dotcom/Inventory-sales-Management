import numpy as np
import pandas as pd
from models import Product, Sale

def get_sales_analytics():
    """
    Core analytics service fetching actual sales records from SQLite via SQLAlchemy
    and performing statistical analysis using NumPy and Pandas.
    """
    sales = Sale.query.order_by(Sale.sale_date.asc()).all()
    products = Product.query.order_by(Product.name.asc()).all()

    total_products_count = len(products)

    # 1. Graceful empty data handling
    if not sales:
        low_stock_products = [
            {
                "product_id": p.id,
                "product_name": p.name,
                "category": p.category or "General",
                "price": float(p.price),
                "stock": p.stock,
                "is_out_of_stock": (p.stock <= 0)
            }
            for p in products if p.stock <= 10
        ]
        low_stock_products.sort(key=lambda x: x["stock"])

        return {
            "has_data": False,
            "total_products": total_products_count,
            "total_revenue": 0.0,
            "total_units_sold": 0,
            "total_transactions": 0,
            "avg_transaction_value": 0.0,
            "stats": {
                "min_sale": 0.0,
                "max_sale": 0.0,
                "median_sale": 0.0,
                "std_sale": 0.0
            },
            "product_analysis": [],
            "top_products": [],
            "fast_moving": [],
            "slow_moving": [],
            "low_stock_products": low_stock_products,
            "category_analysis": [],
            "daily_summary": [],
            "monthly_summary": [],
            "chart_daily": {"labels": [], "revenues": [], "quantities": []},
            "chart_products": {"labels": [], "revenues": [], "quantities": []},
            "chart_categories": {"labels": [], "revenues": [], "quantities": []}
        }

    # 2. Build Pandas DataFrame from database records
    sales_data = []
    for s in sales:
        p_name = s.product.name if s.product else f"Product #{s.product_id}"
        category = (s.product.category or "General") if s.product else "General"
        stock = s.product.stock if s.product else 0
        sales_data.append({
            "sale_id": s.id,
            "product_id": s.product_id,
            "product_name": p_name,
            "category": category,
            "quantity": s.quantity,
            "total_amount": float(s.total_amount),
            "stock": stock,
            "sale_date": s.sale_date
        })

    df = pd.DataFrame(sales_data)
    df["sale_date"] = pd.to_datetime(df["sale_date"])

    # 3. NumPy Statistical Calculations
    amounts = df["total_amount"].to_numpy()
    quantities = df["quantity"].to_numpy()

    total_revenue = float(np.sum(amounts))
    total_units_sold = int(np.sum(quantities))
    total_transactions = int(len(amounts))
    avg_transaction_value = float(np.mean(amounts)) if total_transactions > 0 else 0.0

    stats = {
        "min_sale": float(np.min(amounts)),
        "max_sale": float(np.max(amounts)),
        "median_sale": float(np.median(amounts)),
        "std_sale": float(np.std(amounts))
    }

    # 4. Pandas Groupby Operations: Product-Wise Sales Analysis
    prod_grouped = df.groupby(["product_id", "product_name", "category", "stock"]).agg(
        total_quantity=("quantity", "sum"),
        total_revenue=("total_amount", "sum"),
        transaction_count=("sale_id", "count")
    ).reset_index()

    # Calculate revenue share %
    prod_grouped["revenue_share"] = (
        (prod_grouped["total_revenue"] / total_revenue) * 100
    ).round(2) if total_revenue > 0 else 0.0

    # Include products with 0 sales from catalog for comprehensive inventory analytics
    all_products_dict = {
        p.id: {
            "product_id": p.id,
            "product_name": p.name,
            "category": p.category or "General",
            "stock": p.stock,
            "total_quantity": 0,
            "total_revenue": 0.0,
            "transaction_count": 0,
            "revenue_share": 0.0
        } for p in products
    }

    # Update with actual sales data
    for row in prod_grouped.to_dict(orient="records"):
        all_products_dict[row["product_id"]] = row

    all_products_list = list(all_products_dict.values())
    df_all_products = pd.DataFrame(all_products_list)
    df_all_products = df_all_products.sort_values(by=["total_quantity", "total_revenue"], ascending=False)

    # 5. Identify Fast-Moving and Slow-Moving Products
    sold_quantities = df_all_products["total_quantity"].to_numpy()
    median_sold = float(np.median(sold_quantities)) if len(sold_quantities) > 0 else 0.0
    threshold = max(1.0, median_sold)

    df_all_products["movement"] = df_all_products["total_quantity"].apply(
        lambda q: "Fast-Moving" if q >= threshold and q > 0 else "Slow-Moving"
    )

    fast_moving = df_all_products[df_all_products["movement"] == "Fast-Moving"].to_dict(orient="records")
    slow_moving = df_all_products[df_all_products["movement"] == "Slow-Moving"].to_dict(orient="records")

    # Product analysis list sorted by total revenue
    product_analysis = df_all_products.sort_values(by="total_revenue", ascending=False).to_dict(orient="records")
    top_products = product_analysis[:5]

    # 6. Low-Stock Products (< 10 units or 0 units)
    low_stock_products = [
        {
            "product_id": p.id,
            "product_name": p.name,
            "category": p.category or "General",
            "price": float(p.price),
            "stock": p.stock,
            "is_out_of_stock": (p.stock <= 0)
        }
        for p in products if p.stock <= 10
    ]
    low_stock_products.sort(key=lambda x: x["stock"])

    # 7. Category-Wise Analysis using Pandas GroupBy
    cat_product_counts = {}
    for p in products:
        cat_name = p.category or "General"
        cat_product_counts[cat_name] = cat_product_counts.get(cat_name, 0) + 1

    category_grouped = df.groupby("category").agg(
        total_revenue=("total_amount", "sum"),
        total_units=("quantity", "sum"),
        transaction_count=("sale_id", "count")
    ).reset_index().sort_values("total_revenue", ascending=False)

    category_analysis = []
    for row in category_grouped.to_dict(orient="records"):
        cat_name = row["category"]
        cat_rev = float(row["total_revenue"])
        cat_share = round((cat_rev / total_revenue) * 100, 2) if total_revenue > 0 else 0.0
        category_analysis.append({
            "category": cat_name,
            "product_count": cat_product_counts.get(cat_name, 0),
            "total_revenue": cat_rev,
            "total_units": int(row["total_units"]),
            "transaction_count": int(row["transaction_count"]),
            "revenue_share": cat_share
        })

    # 8. Daily and Monthly Sales Summaries using Pandas
    df["day_str"] = df["sale_date"].dt.strftime("%Y-%m-%d")
    df["month_str"] = df["sale_date"].dt.strftime("%Y-%m")

    # Daily Summary
    daily_df = df.groupby("day_str").agg(
        revenue=("total_amount", "sum"),
        units=("quantity", "sum"),
        transactions=("sale_id", "count")
    ).reset_index().sort_values("day_str")
    daily_summary = daily_df.to_dict(orient="records")

    # Monthly Summary
    monthly_df = df.groupby("month_str").agg(
        revenue=("total_amount", "sum"),
        units=("quantity", "sum"),
        transactions=("sale_id", "count")
    ).reset_index().sort_values("month_str")
    monthly_summary = monthly_df.to_dict(orient="records")

    # 9. Data structures formatted specifically for Chart.js
    chart_daily = {
        "labels": daily_df["day_str"].tolist(),
        "revenues": [round(float(val), 2) for val in daily_df["revenue"].tolist()],
        "quantities": [int(val) for val in daily_df["units"].tolist()]
    }

    # Top products for Bar Chart (up to 8 products)
    bar_df = df_all_products[df_all_products["total_quantity"] > 0].head(8)
    if bar_df.empty:
        bar_df = df_all_products.head(8)

    chart_products = {
        "labels": bar_df["product_name"].tolist(),
        "revenues": [round(float(val), 2) for val in bar_df["total_revenue"].tolist()],
        "quantities": [int(val) for val in bar_df["total_quantity"].tolist()]
    }

    chart_categories = {
        "labels": [c["category"] for c in category_analysis],
        "revenues": [round(float(c["total_revenue"]), 2) for c in category_analysis],
        "quantities": [int(c["total_units"]) for c in category_analysis]
    }

    return {
        "has_data": True,
        "total_products": total_products_count,
        "total_revenue": total_revenue,
        "total_units_sold": total_units_sold,
        "total_transactions": total_transactions,
        "avg_transaction_value": avg_transaction_value,
        "stats": stats,
        "product_analysis": product_analysis,
        "top_products": top_products,
        "fast_moving": fast_moving,
        "slow_moving": slow_moving,
        "low_stock_products": low_stock_products,
        "category_analysis": category_analysis,
        "daily_summary": daily_summary,
        "monthly_summary": monthly_summary,
        "chart_daily": chart_daily,
        "chart_products": chart_products,
        "chart_categories": chart_categories
    }

def get_demand_forecast():
    """
    Demand Forecasting Engine using Historical Database Records:
    1. Computes product-wise historical sales velocity.
    2. Calculates statistical trend slopes using NumPy (np.polyfit).
    3. Projects next-period (7-day and 30-day) demand estimates.
    4. Handles products with insufficient historical records gracefully.
    5. Evaluates stock safety buffers and flags urgent reorder recommendations.
    """
    sales = Sale.query.order_by(Sale.sale_date.asc()).all()
    products = Product.query.order_by(Product.name.asc()).all()

    if not sales or not products:
        return {
            "has_data": False,
            "forecast_list": [],
            "high_risk_products": [],
            "summary": {
                "total_projected_demand_30d": 0,
                "reorder_needed_count": 0,
                "high_confidence_count": 0,
                "insufficient_data_count": len(products)
            },
            "chart_forecast": {
                "labels": [],
                "historical_sold": [],
                "projected_demand": []
            }
        }

    # Find global active sales timeframe in days
    min_date = min(s.sale_date for s in sales)
    max_date = max(s.sale_date for s in sales)
    catalog_active_days = max(1, (max_date - min_date).days + 1)

    forecast_results = []
    total_projected_demand_30d = 0
    reorder_needed_count = 0
    high_confidence_count = 0
    insufficient_data_count = 0

    for prod in products:
        prod_sales = [s for s in sales if s.product_id == prod.id]
        sales_count = len(prod_sales)
        total_units_sold = sum(s.quantity for s in prod_sales)

        if sales_count == 0:
            # Case A: 0 sales records
            insufficient_data_count += 1
            daily_velocity = 0.0
            trend_label = "No Sales History ⏳"
            confidence = "Insufficient Data (0 Sales)"
            forecast_7d = 0
            forecast_30d = 0
            
            if prod.stock <= 0:
                stock_status = "Out of Stock - Immediate Restock 🚨"
                status_color = "danger"
                reorder_qty = 10
            elif prod.stock <= 5:
                stock_status = "Low Stock - Restock Baseline ⚠️"
                status_color = "warning"
                reorder_qty = 10 - prod.stock
            else:
                stock_status = "Sufficient Stock ✅"
                status_color = "success"
                reorder_qty = 0

        elif sales_count == 1:
            # Case B: Only 1 transaction (insufficient for mathematical trend slope)
            insufficient_data_count += 1
            # Baseline run-rate based on catalog active window
            daily_velocity = round(total_units_sold / catalog_active_days, 3)
            trend_label = "Baseline Run-Rate (1 Sale) 📌"
            confidence = "Low Confidence (1 Transaction)"
            
            forecast_7d = max(1, int(np.ceil(daily_velocity * 7)))
            forecast_30d = max(1, int(np.ceil(daily_velocity * 30)))
            
            if prod.stock <= 0:
                stock_status = "Out of Stock - Immediate Restock 🚨"
                status_color = "danger"
                reorder_qty = forecast_30d + 5
            elif prod.stock < forecast_7d:
                stock_status = "High Shortage Risk (Reorder Urgent) ⚠️"
                status_color = "danger"
                reorder_qty = max(0, (forecast_30d - prod.stock) + 5)
            elif prod.stock < forecast_30d:
                stock_status = "Reorder Soon (Moderate Risk) 🟡"
                status_color = "warning"
                reorder_qty = max(0, (forecast_30d - prod.stock) + 5)
            else:
                stock_status = "Sufficient Stock ✅"
                status_color = "success"
                reorder_qty = 0

        else:
            # Case C: 2 or more transactions -> Compute velocity and NumPy trend slope
            first_sale = prod_sales[0].sale_date
            last_sale = prod_sales[-1].sale_date
            prod_active_days = max(1, (last_sale - first_sale).days + 1)
            daily_velocity = round(total_units_sold / prod_active_days, 3)

            # NumPy linear regression fit for trend slope
            x_vals = np.arange(sales_count)
            y_vals = np.array([float(s.quantity) for s in prod_sales])
            slope, _ = np.polyfit(x_vals, y_vals, 1)

            if slope > 0.05:
                trend_label = "Rising Demand 📈 (+Trend)"
                trend_multiplier = 1.20
            elif slope < -0.05:
                trend_label = "Slowing Demand 📉 (-Trend)"
                trend_multiplier = 0.80
            else:
                trend_label = "Steady Demand ➡️ (Stable)"
                trend_multiplier = 1.00

            if sales_count >= 3:
                confidence = "High Confidence (Trend Verified)"
                high_confidence_count += 1
            else:
                confidence = "Medium Confidence (2 Transactions)"

            forecast_7d = max(1, int(np.ceil(daily_velocity * 7 * trend_multiplier)))
            forecast_30d = max(1, int(np.ceil(daily_velocity * 30 * trend_multiplier)))

            if prod.stock <= 0:
                stock_status = "Out of Stock - Immediate Restock 🚨"
                status_color = "danger"
                reorder_qty = forecast_30d + 5
            elif prod.stock < forecast_7d:
                stock_status = "High Shortage Risk (Reorder Urgent) ⚠️"
                status_color = "danger"
                reorder_qty = max(0, (forecast_30d - prod.stock) + 5)
            elif prod.stock < forecast_30d:
                stock_status = "Reorder Soon (Moderate Risk) 🟡"
                status_color = "warning"
                reorder_qty = max(0, (forecast_30d - prod.stock) + 5)
            else:
                stock_status = "Sufficient Stock ✅"
                status_color = "success"
                reorder_qty = 0

        if reorder_qty > 0:
            reorder_needed_count += 1

        total_projected_demand_30d += forecast_30d

        forecast_results.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "category": prod.category or "General",
            "price": float(prod.price),
            "current_stock": prod.stock,
            "historical_sold": total_units_sold,
            "transaction_count": sales_count,
            "daily_velocity": daily_velocity,
            "trend_label": trend_label,
            "confidence": confidence,
            "forecast_7d": forecast_7d,
            "forecast_30d": forecast_30d,
            "stock_status": stock_status,
            "status_color": status_color,
            "reorder_qty": reorder_qty
        })

    # Sort forecast results by estimated 30-day demand descending
    forecast_results.sort(key=lambda item: (item["forecast_30d"], item["historical_sold"]), reverse=True)

    high_risk_products = [item for item in forecast_results if item["status_color"] in ["danger", "warning"]]

    # Prepare Chart.js payload for comparison of Historical Sales vs Projected 30-Day Demand
    chart_products = forecast_results[:8]
    chart_forecast = {
        "labels": [item["product_name"] for item in chart_products],
        "historical_sold": [item["historical_sold"] for item in chart_products],
        "projected_demand": [item["forecast_30d"] for item in chart_products]
    }

    return {
        "has_data": True,
        "forecast_list": forecast_results,
        "high_risk_products": high_risk_products,
        "summary": {
            "total_projected_demand_30d": total_projected_demand_30d,
            "reorder_needed_count": reorder_needed_count,
            "high_confidence_count": high_confidence_count,
            "insufficient_data_count": insufficient_data_count
        },
        "chart_forecast": chart_forecast
    }
