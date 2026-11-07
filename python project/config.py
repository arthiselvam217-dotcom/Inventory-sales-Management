import os

class Config:
    """Application configuration settings."""
    # Secret key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY', 'inventory-sales-analytics-secret-key-phase2')

    # SQLite database configuration: inventory.db stored inside the instance/ folder
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
