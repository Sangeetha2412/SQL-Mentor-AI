"""
models.py - Database Models
Defines all SQLAlchemy database tables and their relationships.
"""

from datetime import datetime
from flask_login import UserMixin
from database import db


class User(UserMixin, db.Model):
    """User accounts - stores all registered users"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Null for Google users
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')
    uploaded_files = db.relationship('UploadedFile', backref='user', lazy=True, cascade='all, delete-orphan')
    saved_visualizations = db.relationship('SavedVisualization', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Chat(db.Model):
    """Chat sessions - each conversation is a chat"""
    __tablename__ = 'chats'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='New Chat')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='chat', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Chat {self.title}>'


class Message(db.Model):
    """Messages within a chat session"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    sources_json = db.Column(db.Text, nullable=True)  # JSON list of source files
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.role} in chat {self.chat_id}>'


class UploadedFile(db.Model):
    """Uploaded files metadata"""
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, default=0)  # size in bytes
    upload_status = db.Column(db.String(50), default='pending')  # pending, processed, error
    metadata_json = db.Column(db.Text, nullable=True)  # JSON with file analysis results
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    saved_visualizations = db.relationship('SavedVisualization', backref='file', lazy=True)
    
    def __repr__(self):
        return f'<UploadedFile {self.original_filename}>'


class SavedVisualization(db.Model):
    """User saved charts and visualizations"""
    __tablename__ = 'saved_visualizations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    chart_type = db.Column(db.String(50), nullable=False)
    chart_config_json = db.Column(db.Text, nullable=False)  # Chart.js config as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SavedVisualization {self.title}>'


class AppSettings(db.Model):
    """Application settings - stores encrypted API keys and config"""
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value_encrypted = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f'<AppSettings {self.setting_key}>'


class ApiUsageLog(db.Model):
    """Logs every API call for admin analytics"""
    __tablename__ = 'api_usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    endpoint = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success, error
    model_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiUsageLog {self.endpoint} {self.status}>'
