from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance without an active application.
# This prevents circular dependencies when importing models and blueprints.
db = SQLAlchemy()
