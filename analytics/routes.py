from flask import render_template, jsonify, redirect, url_for, flash
from . import analytics_bp
from .services import get_sales_analytics, get_demand_forecast
import pyspark_analytics

@analytics_bp.route('/', methods=['GET'])
def index():
    """
    Renders the Sales Analytics Dashboard with statistical insights,
    product performance breakdowns, demand forecasting, and Chart.js visualizations.
    """
    analytics_data = get_sales_analytics()
    forecast_data = get_demand_forecast()
    return render_template('analytics.html', analytics=analytics_data, forecast=forecast_data)

@analytics_bp.route('/forecast', methods=['GET'])
def forecast():
    """
    Dedicated view for Demand Forecasting and Inventory Replenishment Planning.
    """
    forecast_data = get_demand_forecast()
    return render_template('forecast.html', forecast=forecast_data)

@analytics_bp.route('/api/summary', methods=['GET'])
def api_summary():
    """
    JSON API endpoint providing sales and inventory analytical summaries.
    """
    analytics_data = get_sales_analytics()
    return jsonify(analytics_data)

@analytics_bp.route('/api/forecast', methods=['GET'])
def api_forecast():
    """
    JSON API endpoint providing product-wise demand forecast estimates.
    """
    forecast_data = get_demand_forecast()
    return jsonify(forecast_data)

@analytics_bp.route('/run-pyspark', methods=['GET', 'POST'])
def run_pyspark():
    """
    Web endpoint to trigger the PySpark Big Data Analytics workflow.
    Executes local[*] PySpark DataFrame aggregations and exports CSV reports.
    """
    try:
        pyspark_analytics.extract_sales_from_sqlite()
        pyspark_analytics.run_spark_analytics()
        flash(
            "⚡ PySpark Analytics executed successfully! Reports exported to reports/pyspark_sales_summary.csv and reports/pyspark_category_summary.csv",
            "success"
        )
    except Exception as e:
        flash(f"Error executing PySpark pipeline: {str(e)}", "danger")
    return redirect(url_for('analytics.index'))
