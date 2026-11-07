import os
from flask import Flask
from config import Config
from extensions import db
from dashboard.routes import dashboard_bp
from products.routes import products_bp
from sales.routes import sales_bp
from analytics.routes import analytics_bp
# Import models so they are registered with SQLAlchemy metadata
from models import Product, Sale

def create_app(config_class=Config):
    """
    Application factory for the Inventory and Sales Analytics System.
    Configures extensions, ensures database initialization, and registers blueprints.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Ensure instance directory exists for SQLite database storage
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

    # Automatically create database tables if they do not exist
    with app.app_context():
        db.create_all()

    return app

# Expose app instance for standard WSGI servers or `flask run`
app = create_app()

if __name__ == '__main__':
    # Start the local development server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
