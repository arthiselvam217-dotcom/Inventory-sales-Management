from flask import render_template, jsonify, redirect, url_for, flash
from . import analytics_bp
from .services import get_sales_analytics
import pyspark_analytics

@analytics_bp.route('/', methods=['GET'])
def index():
    """
    Renders the Sales Analytics Dashboard with statistical insights,
    product performance breakdowns, and Chart.js visualizations.
    """
    analytics_data = get_sales_analytics()
    return render_template('analytics.html', analytics=analytics_data)

@analytics_bp.route('/api/summary', methods=['GET'])
def api_summary():
    """
    Optional JSON API endpoint providing analytical summaries.
    """
    analytics_data = get_sales_analytics()
    return jsonify(analytics_data)

@analytics_bp.route('/run-pyspark', methods=['GET', 'POST'])
def run_pyspark():
    """
    Web endpoint to trigger the Phase 5 PySpark Analytics workflow.
    """
    try:
        pyspark_analytics.extract_sales_from_sqlite()
        pyspark_analytics.run_spark_analytics()
        flash("⚡ PySpark Analytics pipeline executed successfully! Results exported to reports/pyspark_sales_summary.csv", "success")
    except Exception as e:
        flash(f"Error executing PySpark pipeline: {str(e)}", "danger")
    return redirect(url_for('analytics.index'))
