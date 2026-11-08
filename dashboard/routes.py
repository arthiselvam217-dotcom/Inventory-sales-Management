from flask import render_template
from . import dashboard_bp
from models import Product, Sale
from analytics.services import get_sales_analytics, get_demand_forecast

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def index():
    """
    Executive Inventory & Sales Analytics Dashboard.
    Presents key operational KPIs, NumPy/Pandas aggregations,
    low-stock alerts, sales trend visualizations, and demand forecasting insights.
    """
    analytics_data = get_sales_analytics()
    forecast_data = get_demand_forecast()
    recent_sales = Sale.query.order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        title="Dashboard | Inventory and Sales Analytics System",
        analytics=analytics_data,
        forecast=forecast_data,
        recent_sales=recent_sales
    )
