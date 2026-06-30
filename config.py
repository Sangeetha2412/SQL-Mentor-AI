"""
config.py - Application Configuration
All environment variables and settings are loaded here.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask secret key for session security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    
    # Database configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
    BASE_DIR,
    "instance",
    "sql_mentor.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 52428800))  # 50MB default
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'csv', 'txt', 'md', 'pdf', 'json', 
        'xlsx', 'xls', 'sql', 'db', 'sqlite', 'sqlite3'
    }
    
    # Groq API
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GROQ_MODEL = 'llama-3.3-70b-versatile'
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    # Admin credentials
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin123!')
    
    # Encryption key for storing API keys securely
    SETTINGS_ENCRYPTION_KEY = os.environ.get('SETTINGS_ENCRYPTION_KEY', '')
    
    # ChromaDB path
    CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db')
    
    # SQL docs path for global knowledge base
    SQL_DOCS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sql_docs')
    
    # Query execution settings
    MAX_QUERY_ROWS = 500
    QUERY_TIMEOUT = 10  # seconds
    
    # Session config
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
