"""
admin.py - Admin Blueprint
All admin dashboard routes, protected by @admin_required decorator.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from database import db
from models import User, Chat, Message, UploadedFile, AppSettings, ApiUsageLog, SavedVisualization
from encryption_utils import update_groq_api_key, test_groq_api_key, get_groq_api_key, mask_api_key
from rag_pipeline import get_chroma_stats

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)


def admin_required(f):
    """Decorator: only allows admin users to access a route."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_chats = Chat.query.count()
    total_files = UploadedFile.query.count()

    # Storage used
    files = UploadedFile.query.all()
    total_storage = sum(f.file_size or 0 for f in files)

    # API stats
    total_api = ApiUsageLog.query.count()
    failed_api = ApiUsageLog.query.filter_by(status='error').count()

    # Groq key status
    key = get_groq_api_key()
    groq_status = 'configured' if key else 'missing'

    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_files = UploadedFile.query.order_by(UploadedFile.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
        total_users=total_users, active_users=active_users,
        total_chats=total_chats, total_files=total_files,
        total_storage=_format_size(total_storage),
        total_api=total_api, failed_api=failed_api,
        groq_status=groq_status, recent_users=recent_users,
        recent_files=recent_files)


@admin_bp.route('/users')
@admin_required
def users():
    search = request.args.get('q', '')
    query = User.query
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )
    all_users = query.order_by(User.created_at.desc()).all()

    user_stats = {}
    for u in all_users:
        user_stats[u.id] = {
            'chats': Chat.query.filter_by(user_id=u.id).count(),
            'files': UploadedFile.query.filter_by(user_id=u.id).count()
        }

    return render_template('admin/users.html', users=all_users, user_stats=user_stats, search=search)


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot change your own role'}), 400
    new_role = request.json.get('role')
    if new_role not in ('user', 'admin'):
        return jsonify({'error': 'Invalid role'}), 400
    user.role = new_role
    db.session.commit()
    return jsonify({'success': True, 'role': new_role})


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot disable your own account'}), 400
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': user.is_active})


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/files')
@admin_required
def files():
    user_filter = request.args.get('user_id', '')
    type_filter = request.args.get('file_type', '')
    query = UploadedFile.query
    if user_filter:
        query = query.filter_by(user_id=user_filter)
    if type_filter:
        query = query.filter_by(file_type=type_filter)
    all_files = query.order_by(UploadedFile.created_at.desc()).all()
    all_users = User.query.all()
    file_types = db.session.query(UploadedFile.file_type).distinct().all()
    file_types = [ft[0] for ft in file_types]
    return render_template('admin/files.html', files=all_files, users=all_users,
                           file_types=file_types, user_filter=user_filter, type_filter=type_filter,
                           format_size=_format_size)


@admin_bp.route('/files/<int:file_id>/delete', methods=['POST'])
@admin_required
def delete_file(file_id):
    from rag_pipeline import delete_user_file_vectors
    f = UploadedFile.query.get_or_404(file_id)
    try:
        if os.path.exists(f.file_path):
            os.remove(f.file_path)
        delete_user_file_vectors(f.id, f.user_id)
        db.session.delete(f)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/chats')
@admin_required
def chats():
    search = request.args.get('q', '')
    query = Chat.query
    if search:
        query = query.filter(Chat.title.ilike(f'%{search}%'))
    all_chats = query.order_by(Chat.updated_at.desc()).all()
    chat_stats = {c.id: Message.query.filter_by(chat_id=c.id).count() for c in all_chats}
    return render_template('admin/chats.html', chats=all_chats, chat_stats=chat_stats, search=search)


@admin_bp.route('/chats/<int:chat_id>/delete', methods=['POST'])
@admin_required
def delete_chat(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    db.session.delete(chat)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api-settings', methods=['GET'])
@admin_required
def api_settings():
    key = get_groq_api_key()
    masked = mask_api_key(key) if key else None
    setting = AppSettings.query.filter_by(setting_key='groq_api_key').first()
    last_updated = setting.updated_at if setting else None
    return render_template('admin/api_settings.html', masked_key=masked, last_updated=last_updated)


@admin_bp.route('/api-settings/update-groq-key', methods=['POST'])
@admin_required
def update_groq_key():
    new_key = request.json.get('api_key', '').strip()
    if not new_key:
        return jsonify({'error': 'API key cannot be empty'}), 400
    success = update_groq_api_key(new_key, current_user.id)
    if success:
        return jsonify({'success': True, 'masked': mask_api_key(new_key)})
    return jsonify({'error': 'Failed to save API key'}), 500


@admin_bp.route('/api-settings/test-groq-key', methods=['POST'])
@admin_required
def test_groq_key():
    key = request.json.get('api_key', '').strip() or get_groq_api_key()
    result = test_groq_api_key(key)
    return jsonify(result)


@admin_bp.route('/analytics')
@admin_required
def analytics():
    # Signups per day last 30 days
    thirty_ago = datetime.utcnow() - timedelta(days=30)
    signups = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_ago).group_by(func.date(User.created_at)).all()

    # File uploads by type
    file_types = db.session.query(
        UploadedFile.file_type, func.count(UploadedFile.id)
    ).group_by(UploadedFile.file_type).all()

    # API usage per day
    api_logs = db.session.query(
        func.date(ApiUsageLog.created_at).label('date'),
        func.count(ApiUsageLog.id).label('count')
    ).filter(ApiUsageLog.created_at >= thirty_ago).group_by(func.date(ApiUsageLog.created_at)).all()

    signups = [[str(r[0]), r[1]] for r in signups]

    file_types = [[r[0], r[1]] for r in file_types]

    api_logs = [[str(r[0]), r[1]] for r in api_logs]

    return render_template(
        'admin/analytics.html',
        signups=signups,
        file_types=file_types,
        api_logs=api_logs
    )

@admin_bp.route('/system-status')
@admin_required
def system_status():
    # Groq API status
    key = get_groq_api_key()
    groq_result = test_groq_api_key(key) if key else {'status': 'missing', 'message': 'No API key configured'}

    # ChromaDB status
    chroma = get_chroma_stats()

    # Database status
    try:
        User.query.count()
        db_status = 'connected'
    except Exception:
        db_status = 'error'

    # Disk usage
    upload_dir = 'uploads'
    total_size = 0
    total_files_count = 0
    if os.path.exists(upload_dir):
        for dirpath, dirnames, filenames in os.walk(upload_dir):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                total_size += os.path.getsize(fp)
                total_files_count += 1

    # Last ingestion
    last_file = UploadedFile.query.order_by(UploadedFile.created_at.desc()).first()

    return render_template('admin/system_status.html',
        groq_result=groq_result, chroma=chroma, db_status=db_status,
        disk_used=_format_size(total_size), total_files_on_disk=total_files_count,
        last_ingestion=last_file.created_at if last_file else None)


def _format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
