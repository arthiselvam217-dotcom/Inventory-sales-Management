from flask import Blueprint

# Define the dashboard Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Import routes so they are registered with the blueprint
from . import routes
