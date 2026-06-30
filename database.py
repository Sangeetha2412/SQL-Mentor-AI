"""
database.py - Database initialization
Creates the SQLAlchemy instance used across the application.
"""

from flask_sqlalchemy import SQLAlchemy

# Create the database instance
# This is imported by app.py and models.py
db = SQLAlchemy()
