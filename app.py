"""
app.py - Main Flask Application
Entry point for SQL Mentor AI. Sets up the app, registers blueprints,
and defines all main routes.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from config import Config
from database import db
from models import User, Chat, Message, UploadedFile, SavedVisualization, ApiUsageLog
from auth import auth_bp
from admin import admin_bp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    """Application factory - creates and configures the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    os.makedirs('chroma_db', exist_ok=True)
    os.makedirs('data/sql_docs', exist_ok=True)

    # Initialize database
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # Register main routes
    register_main_routes(app)

    # Create tables and seed admin
    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    """Create the admin user if it doesn't exist yet."""
    admin_email = Config.ADMIN_EMAIL.lower()
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name='Admin',
            email=admin_email,
            password_hash=generate_password_hash(Config.ADMIN_PASSWORD),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        logger.info(f"Admin user created: {admin_email}")


def _allowed_file(filename):
    """Check if a file extension is allowed."""
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS)


def _format_size(size_bytes):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def register_main_routes(app):
    """Register all main application routes."""

    # ─────────────────────────────────────────
    # LANDING PAGE
    # ─────────────────────────────────────────
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('admin.dashboard') if current_user.role == 'admin'
                            else url_for('main_dashboard'))
        return render_template('index.html')

    # ─────────────────────────────────────────
    # USER DASHBOARD
    # ─────────────────────────────────────────
    @app.route('/dashboard')
    @login_required
    def main_dashboard():
        total_chats = Chat.query.filter_by(user_id=current_user.id).count()
        total_files = UploadedFile.query.filter_by(user_id=current_user.id).count()
        total_charts = SavedVisualization.query.filter_by(user_id=current_user.id).count()
        recent_chats = (Chat.query.filter_by(user_id=current_user.id)
                        .order_by(Chat.updated_at.desc()).limit(5).all())
        recent_files = (UploadedFile.query.filter_by(user_id=current_user.id)
                        .order_by(UploadedFile.created_at.desc()).limit(5).all())
        recent_charts = (SavedVisualization.query.filter_by(user_id=current_user.id)
                         .order_by(SavedVisualization.created_at.desc()).limit(3).all())
        return render_template('dashboard.html',
            total_chats=total_chats, total_files=total_files,
            total_charts=total_charts, recent_chats=recent_chats,
            recent_files=recent_files, recent_charts=recent_charts,
            format_size=_format_size)

    # ─────────────────────────────────────────
    # CHAT PAGE
    # ─────────────────────────────────────────
    @app.route('/chat')
    @login_required
    def chat_page():
        chats = (Chat.query.filter_by(user_id=current_user.id)
                 .order_by(Chat.updated_at.desc()).all())
        user_files = (UploadedFile.query.filter_by(user_id=current_user.id, upload_status='processed')
                      .order_by(UploadedFile.created_at.desc()).all())
        return render_template('chat.html', chats=chats, user_files=user_files)

    # ─────────────────────────────────────────
    # CHAT API
    # ─────────────────────────────────────────
    @app.route('/api/chat', methods=['POST'])
    @login_required
    def api_chat():
        from rag_pipeline import generate_ai_response
        data = request.json or {}
        user_message = data.get('message', '').strip()
        chat_id = data.get('chat_id')
        selected_file_ids = data.get('file_ids', [])

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Get or create chat
        if chat_id:
            chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
        else:
            chat = None

        if not chat:
            title = user_message[:60] + ('...' if len(user_message) > 60 else '')
            chat = Chat(user_id=current_user.id, title=title)
            db.session.add(chat)
            db.session.flush()

        # Save user message
        user_msg = Message(chat_id=chat.id, role='user', content=user_message)
        db.session.add(user_msg)

        # Build history for context
        history_msgs = (Message.query.filter_by(chat_id=chat.id)
                        .order_by(Message.created_at.asc()).all())
        history = [{'role': m.role, 'content': m.content} for m in history_msgs]

        # Collect file metadata for selected files
        file_metadata = {}  
        if selected_file_ids:
            for fid in selected_file_ids:
                f = UploadedFile.query.filter_by(id=fid, user_id=current_user.id).first()
                if f and f.metadata_json:
                    try:
                        file_metadata[f.original_filename] = json.loads(f.metadata_json)
                    except Exception:
                        pass

        # Generate AI response
        result = generate_ai_response(
            user_message=user_message,
            chat_history=history,
            user_id=current_user.id,
            selected_file_ids=selected_file_ids if selected_file_ids else None,
            file_metadata=file_metadata if file_metadata else None
        )

        # Save assistant message
        ai_msg = Message(
            chat_id=chat.id,
            role='assistant',
            content=result['response'],
            sources_json=json.dumps(result.get('sources', []))
        )
        db.session.add(ai_msg)

        # Update chat timestamp and title
        chat.updated_at = datetime.utcnow()
        if not chat.title or chat.title == 'New Chat':
            chat.title = user_message[:60]

        # Log API usage
        log = ApiUsageLog(
            user_id=current_user.id,
            endpoint='/api/chat',
            status='error' if result.get('error') else 'success',
            model_name=Config.GROQ_MODEL
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'response': result['response'],
            'sources': result.get('sources', []),
            'chat_id': chat.id,
            'error': result.get('error', False)
        })

    @app.route('/api/new-chat', methods=['POST'])
    @login_required
    def new_chat():
        chat = Chat(user_id=current_user.id, title='New Chat')
        db.session.add(chat)
        db.session.commit()
        return jsonify({'chat_id': chat.id, 'title': chat.title})

    @app.route('/api/chat-history')
    @login_required
    def chat_history():
        chats = (Chat.query.filter_by(user_id=current_user.id)
                 .order_by(Chat.updated_at.desc()).limit(50).all())
        return jsonify([{
            'id': c.id, 'title': c.title,
            'updated_at': c.updated_at.strftime('%Y-%m-%d %H:%M')
        } for c in chats])

    @app.route('/api/chat-messages/<int:chat_id>')
    @login_required
    def chat_messages(chat_id):
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
        msgs = Message.query.filter_by(chat_id=chat.id).order_by(Message.created_at.asc()).all()
        return jsonify({
            'chat_id': chat.id,
            'title': chat.title,
            'messages': [{
                'role': m.role,
                'content': m.content,
                'sources': json.loads(m.sources_json) if m.sources_json else [],
                'created_at': m.created_at.strftime('%H:%M')
            } for m in msgs]
        })

    @app.route('/api/rename-chat', methods=['POST'])
    @login_required
    def rename_chat():
        data = request.json or {}
        chat = Chat.query.filter_by(id=data.get('chat_id'), user_id=current_user.id).first_or_404()
        chat.title = data.get('title', chat.title)[:100]
        db.session.commit()
        return jsonify({'success': True})

    @app.route('/api/delete-chat', methods=['POST'])
    @login_required
    def delete_chat():
        data = request.json or {}
        chat = Chat.query.filter_by(id=data.get('chat_id'), user_id=current_user.id).first_or_404()
        db.session.delete(chat)
        db.session.commit()
        return jsonify({'success': True})

    # ─────────────────────────────────────────
    # FILE UPLOAD
    # ─────────────────────────────────────────
    @app.route('/upload')
    @login_required
    def upload_page():
        files = (UploadedFile.query.filter_by(user_id=current_user.id)
                 .order_by(UploadedFile.created_at.desc()).all())
        return render_template('upload.html', files=files, format_size=_format_size)

    @app.route('/api/upload-file', methods=['POST'])
    @login_required
    def upload_file():
        from file_processor import process_file
        from rag_pipeline import ingest_user_file

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        if not _allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed: {", ".join(Config.ALLOWED_EXTENSIONS)}'}), 400

        # Secure and unique filename
        original_name = file.filename
        ext = original_name.rsplit('.', 1)[1].lower()
        stored_name = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(original_name)}"

        user_upload_dir = os.path.join(Config.UPLOAD_FOLDER, str(current_user.id))
        os.makedirs(user_upload_dir, exist_ok=True)
        file_path = os.path.join(user_upload_dir, stored_name)
        file.save(file_path)

        file_size = os.path.getsize(file_path)

        # Save to database
        uploaded = UploadedFile(
            user_id=current_user.id,
            original_filename=original_name,
            stored_filename=stored_name,
            file_path=file_path,
            file_type=ext,
            file_size=file_size,
            upload_status='processing'
        )
        db.session.add(uploaded)
        db.session.flush()

        # Process the file
        try:
            print("STEP 1")

            metadata = process_file(file_path, ext, current_user.id)

            print("STEP 2")
            print(metadata)

            uploaded.metadata_json = json.dumps(metadata)

            print("STEP 3")

            uploaded.upload_status = 'processed'

            text_content = metadata.get('extracted_text', '')

            if not text_content and ext in ('csv','xlsx','xls','json'):
                text_content = f"File: {original_name}\n"
                if 'columns' in metadata:
                    text_content += f"Columns: {', '.join(str(c) for c in metadata['columns'])}\n"
                text_content += f"Rows: {metadata.get('total_rows','N/A')}\n"

            print("STEP 4")

            if text_content:
                ingest_user_file(
                    uploaded.id,
                    current_user.id,
                    text_content,
                    original_name,
                    ext
                )

            print("STEP 5")

        except Exception as e:
            import traceback
            traceback.print_exc()

            uploaded.upload_status = "error"
            uploaded.metadata_json = json.dumps({
                "error": str(e)
            })

        except Exception as e:
            logger.error(f"File processing error: {e}")
            uploaded.upload_status = 'error'
            uploaded.metadata_json = json.dumps({'error': str(e)})
        db.session.commit()

        return jsonify({
            'success': True,
            'file_id': uploaded.id,
            'filename': original_name,
            'file_type': ext,
            'file_size': _format_size(file_size),
            'status': uploaded.upload_status
            })

    @app.route('/api/files')
    @login_required
    def get_files():
        files = (UploadedFile.query.filter_by(user_id=current_user.id)
                 .order_by(UploadedFile.created_at.desc()).all())
        return jsonify([{
            'id': f.id,
            'filename': f.original_filename,
            'file_type': f.file_type,
            'file_size': _format_size(f.file_size or 0),
            'status': f.upload_status,
            'created_at': f.created_at.strftime('%Y-%m-%d %H:%M')
        } for f in files])

    @app.route('/api/delete-file/<int:file_id>', methods=['POST'])
    @login_required
    def delete_file(file_id):
        from rag_pipeline import delete_user_file_vectors
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        try:
            if os.path.exists(f.file_path):
                os.remove(f.file_path)
            delete_user_file_vectors(f.id, f.user_id)
            db.session.delete(f)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/file-summary/<int:file_id>')
    @login_required
    def file_summary(file_id):
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        meta = json.loads(f.metadata_json) if f.metadata_json else {}
        return jsonify({'filename': f.original_filename, 'file_type': f.file_type,
                        'metadata': meta})

    # ─────────────────────────────────────────
    # DATA EXPLORER
    # ─────────────────────────────────────────
    @app.route('/data-explorer/<int:file_id>')
    @login_required
    def data_explorer(file_id):
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        meta = json.loads(f.metadata_json) if f.metadata_json else {}
        return render_template('data_explorer.html', file=f, metadata=meta, format_size=_format_size)

    @app.route('/api/file-preview/<int:file_id>')
    @login_required
    def file_preview(file_id):
        from data_analyzer import get_paginated_data
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        sort_col = request.args.get('sort', '')
        sort_dir = request.args.get('dir', 'asc')
        result = get_paginated_data(f.file_path, f.file_type, page, 50, search, sort_col, sort_dir)
        return jsonify(result)

    @app.route('/api/database-schema/<int:file_id>')
    @login_required
    def database_schema(file_id):
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        meta = json.loads(f.metadata_json) if f.metadata_json else {}
        return jsonify({'tables': meta.get('tables', {}), 'table_names': meta.get('table_names', [])})

    @app.route('/api/run-safe-query/<int:file_id>', methods=['POST'])
    @login_required
    def run_safe_query(file_id):
        from sql_executor import execute_safe_query
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        if f.file_type not in ('db', 'sqlite', 'sqlite3'):
            return jsonify({'error': 'File is not a SQLite database'}), 400
        query = (request.json or {}).get('query', '').strip()
        result = execute_safe_query(f.file_path, query)
        return jsonify(result)

    @app.route('/api/database-table-preview/<int:file_id>/<table_name>')
    @login_required
    def database_table_preview(file_id, table_name):
        from sql_executor import get_table_preview
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        if f.file_type not in ('db', 'sqlite', 'sqlite3'):
            return jsonify({'error': 'Not a SQLite file'}), 400
        result = get_table_preview(f.file_path, table_name)
        return jsonify(result)

    # ─────────────────────────────────────────
    # VISUALIZATIONS
    # ─────────────────────────────────────────
    @app.route('/visualizations/<int:file_id>')
    @login_required
    def visualizations(file_id):
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        meta = json.loads(f.metadata_json) if f.metadata_json else {}
        saved = (SavedVisualization.query.filter_by(user_id=current_user.id, file_id=file_id)
                 .order_by(SavedVisualization.created_at.desc()).all())
        return render_template('visualizations.html', file=f, metadata=meta, saved_charts=saved)

    @app.route('/api/generate-chart/<int:file_id>', methods=['POST'])
    @login_required
    def generate_chart(file_id):
        from chart_generator import generate_chart as gen_chart
        f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        data = request.json or {}
        result = gen_chart(
            file_path=f.file_path,
            file_type=f.file_type,
            chart_type=data.get('chart_type', 'bar'),
            x_column=data.get('x_column', ''),
            y_column=data.get('y_column', ''),
            aggregation=data.get('aggregation', 'count'),
            group_by=data.get('group_by')
        )
        return jsonify(result)

    @app.route('/api/save-chart', methods=['POST'])
    @login_required
    def save_chart():
        data = request.json or {}
        vis = SavedVisualization(
            user_id=current_user.id,
            file_id=data.get('file_id'),
            title=data.get('title', 'Untitled Chart'),
            chart_type=data.get('chart_type', 'bar'),
            chart_config_json=json.dumps(data.get('chart_config', {}))
        )
        db.session.add(vis)
        db.session.commit()
        return jsonify({'success': True, 'chart_id': vis.id})

    @app.route('/api/saved-charts')
    @login_required
    def saved_charts():
        charts = (SavedVisualization.query.filter_by(user_id=current_user.id)
                  .order_by(SavedVisualization.created_at.desc()).all())
        return jsonify([{
            'id': c.id, 'title': c.title, 'chart_type': c.chart_type,
            'file_id': c.file_id, 'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
        } for c in charts])

    @app.route('/api/delete-chart/<int:chart_id>', methods=['POST'])
    @login_required
    def delete_chart(chart_id):
        c = SavedVisualization.query.filter_by(id=chart_id, user_id=current_user.id).first_or_404()
        db.session.delete(c)
        db.session.commit()
        return jsonify({'success': True})

    # ─────────────────────────────────────────
    # PROFILE
    # ─────────────────────────────────────────
    @app.route('/profile')
    @login_required
    def profile():
        return render_template('profile.html')

    @app.route('/profile/update', methods=['POST'])
    @login_required
    def profile_update():
        name = request.form.get('name', '').strip()
        if len(name) < 2:
            flash('Name must be at least 2 characters.', 'error')
            return redirect(url_for('profile'))
        current_user.name = name
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    @app.route('/profile/change-password', methods=['POST'])
    @login_required
    def change_password():
        from werkzeug.security import check_password_hash, generate_password_hash
        if not current_user.password_hash:
            flash('Password change is not available for Google accounts.', 'error')
            return redirect(url_for('profile'))
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        if not check_password_hash(current_user.password_hash, current_pw):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('profile'))
        if len(new_pw) < 8:
            flash('New password must be at least 8 characters.', 'error')
            return redirect(url_for('profile'))
        if new_pw != confirm_pw:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('profile'))
        current_user.password_hash = generate_password_hash(new_pw)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('profile'))

    # ─────────────────────────────────────────
    # ERROR HANDLERS
    # ─────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html'), 404

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

    @app.context_processor
    def inject_globals():
        return {'now': datetime.utcnow(), 'format_size': _format_size}


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
