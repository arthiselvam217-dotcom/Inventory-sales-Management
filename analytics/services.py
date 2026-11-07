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

    # 1. Graceful empty data handling
    if not sales:
        return {
            "has_data": False,
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
            "daily_summary": [],
            "monthly_summary": [],
            "chart_daily": {"labels": [], "revenues": [], "quantities": []},
            "chart_products": {"labels": [], "revenues": [], "quantities": []},
            "chart_categories": {"labels": [], "revenues": []}
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
    # Use quantity sold distribution:
    sold_quantities = df_all_products["total_quantity"].to_numpy()
    median_sold = float(np.median(sold_quantities)) if len(sold_quantities) > 0 else 0.0
    mean_sold = float(np.mean(sold_quantities)) if len(sold_quantities) > 0 else 0.0
    threshold = max(1.0, median_sold)

    df_all_products["movement"] = df_all_products["total_quantity"].apply(
        lambda q: "Fast-Moving" if q >= threshold and q > 0 else "Slow-Moving"
    )

    fast_moving = df_all_products[df_all_products["movement"] == "Fast-Moving"].to_dict(orient="records")
    slow_moving = df_all_products[df_all_products["movement"] == "Slow-Moving"].to_dict(orient="records")

    # Product analysis list sorted by total revenue
    product_analysis = df_all_products.sort_values(by="total_revenue", ascending=False).to_dict(orient="records")
    top_products = product_analysis[:5]

    # 6. Daily and Monthly Sales Summaries using Pandas
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

    # 7. Category Distribution using Pandas Groupby
    category_df = df.groupby("category").agg(
        revenue=("total_amount", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    # 8. Data structures formatted specifically for Chart.js
    chart_daily = {
        "labels": daily_df["day_str"].tolist(),
        "revenues": [round(val, 2) for val in daily_df["revenue"].tolist()],
        "quantities": [int(val) for val in daily_df["units"].tolist()]
    }

    # Top products for Bar Chart (up to 8 products)
    bar_df = df_all_products[df_all_products["total_quantity"] > 0].head(8)
    if bar_df.empty:
        bar_df = df_all_products.head(8)

    chart_products = {
        "labels": bar_df["product_name"].tolist(),
        "revenues": [round(val, 2) for val in bar_df["total_revenue"].tolist()],
        "quantities": [int(val) for val in bar_df["total_quantity"].tolist()]
    }

    chart_categories = {
        "labels": category_df["category"].tolist(),
        "revenues": [round(val, 2) for val in category_df["revenue"].tolist()]
    }

    return {
        "has_data": True,
        "total_revenue": total_revenue,
        "total_units_sold": total_units_sold,
        "total_transactions": total_transactions,
        "avg_transaction_value": avg_transaction_value,
        "stats": stats,
        "product_analysis": product_analysis,
        "top_products": top_products,
        "fast_moving": fast_moving,
        "slow_moving": slow_moving,
        "daily_summary": daily_summary,
        "monthly_summary": monthly_summary,
        "chart_daily": chart_daily,
        "chart_products": chart_products,
        "chart_categories": chart_categories
    }
