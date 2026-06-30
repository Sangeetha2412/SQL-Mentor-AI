"""
auth.py - Authentication Blueprint
Handles signup, login, logout, and Google OAuth.
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.requests_client import OAuth2Session
from database import db
from models import User
from config import Config

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        existing = User.query.filter_by(email=email).first()
        if existing:
            errors.append('An account with this email already exists.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('signup.html', name=name, email=email)

        role = 'admin' if email == Config.ADMIN_EMAIL.lower() else 'user'
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()

        flash(f'Welcome, {name}! Your account has been created.', 'success')
        return redirect(url_for('admin.dashboard') if role == 'admin' else url_for('main.dashboard'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('main_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html', email=email)

        if not user.is_active:
            flash('Your account has been disabled. Please contact support.', 'error')
            return render_template('login.html', email=email)

        login_user(user, remember=True)
        user.last_login = datetime.utcnow()
        db.session.commit()

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('admin.dashboard') if user.role == 'admin' else url_for('main_dashboard'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/auth/google')
def google_login():
    if not Config.GOOGLE_CLIENT_ID:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))

    oauth = OAuth2Session(Config.GOOGLE_CLIENT_ID, redirect_uri=Config.GOOGLE_REDIRECT_URI,
                          scope=['openid', 'email', 'profile'])
    uri, state = oauth.create_authorization_url(GOOGLE_AUTH_URL)
    session['oauth_state'] = state
    return redirect(uri)


@auth_bp.route('/auth/google/callback')
def google_callback():
    if not Config.GOOGLE_CLIENT_ID:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))

    try:
        oauth = OAuth2Session(Config.GOOGLE_CLIENT_ID,
                              redirect_uri=Config.GOOGLE_REDIRECT_URI,
                              state=session.get('oauth_state'))
        token = oauth.fetch_token(GOOGLE_TOKEN_URL,
                                   client_secret=Config.GOOGLE_CLIENT_SECRET,
                                   authorization_response=request.url)
        resp = oauth.get(GOOGLE_USERINFO_URL)
        user_info = resp.json()

        google_id = user_info.get('sub')
        email = user_info.get('email', '').lower()
        name = user_info.get('name', email.split('@')[0])

        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()

        if not user:
            role = 'admin' if email == Config.ADMIN_EMAIL.lower() else 'user'
            user = User(name=name, email=email, google_id=google_id, role=role)
            db.session.add(user)
        else:
            if not user.google_id:
                user.google_id = google_id

        if not user.is_active:
            flash('Your account has been disabled.', 'error')
            return redirect(url_for('auth.login'))

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=True)

        return redirect(url_for('admin.dashboard') if role == 'admin' else url_for('main_dashboard'))

    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))
