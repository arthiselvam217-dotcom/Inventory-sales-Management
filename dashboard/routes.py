from flask import render_template
from . import dashboard_bp

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def index():
    """
    Home and dashboard route rendering the Phase 1 welcome screen.
    Displays: 'Welcome to Inventory and Sales Analytics System'
    """
    welcome_message = "Welcome to Inventory and Sales Analytics System"
    return render_template(
        'dashboard.html',
        title="Dashboard - Inventory and Sales Analytics System",
        welcome_message=welcome_message
    )
