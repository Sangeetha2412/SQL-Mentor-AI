"""
encryption_utils.py - Secure API Key Encryption
Uses Fernet symmetric encryption to store API keys safely in the database.
Never stores or logs API key values in plaintext.
"""

import os
import logging
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_fernet():
    """Get the Fernet cipher using the encryption key from environment."""
    key = os.environ.get('SETTINGS_ENCRYPTION_KEY', '')
    if not key:
        # Generate a warning - in production this must be set
        logger.warning("SETTINGS_ENCRYPTION_KEY not set. Using fallback key. SET THIS IN PRODUCTION!")
        # Use a deterministic fallback for development only
        key = Fernet.generate_key().decode()
    
    # Ensure key is bytes
    if isinstance(key, str):
        key = key.encode()
    
    try:
        return Fernet(key)
    except Exception as e:
        logger.error(f"Invalid encryption key format: {e}")
        raise ValueError("Invalid SETTINGS_ENCRYPTION_KEY. Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using Fernet encryption.
    Returns base64-encoded encrypted string safe for database storage.
    """
    if not value:
        return ''
    try:
        f = _get_fernet()
        encrypted = f.encrypt(value.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt a Fernet-encrypted string.
    Returns the original plaintext string.
    """
    if not encrypted_value:
        return ''
    try:
        f = _get_fernet()
        decrypted = f.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Decryption failed: Invalid token or wrong key")
        return ''
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ''


def get_groq_api_key() -> str:
    """
    Get the Groq API key with priority:
    1. Encrypted key from database (set by admin)
    2. GROQ_API_KEY from .env file
    """
    try:
        # Import here to avoid circular imports
        from models import AppSettings
        setting = AppSettings.query.filter_by(setting_key='groq_api_key').first()
        if setting and setting.setting_value_encrypted:
            decrypted = decrypt_value(setting.setting_value_encrypted)
            if decrypted:
                return decrypted
    except Exception as e:
        logger.warning(f"Could not load API key from database: {e}")
    
    # Fall back to environment variable
    return os.environ.get('GROQ_API_KEY', '')


def update_groq_api_key(new_key: str, updated_by_user_id: int = None) -> bool:
    """
    Encrypt and save a new Groq API key to the database.
    Returns True on success, False on failure.
    """
    try:
        from models import AppSettings
        from database import db
        from datetime import datetime
        
        encrypted = encrypt_value(new_key)
        
        setting = AppSettings.query.filter_by(setting_key='groq_api_key').first()
        if setting:
            setting.setting_value_encrypted = encrypted
            setting.updated_at = datetime.utcnow()
            setting.updated_by = updated_by_user_id
        else:
            setting = AppSettings(
                setting_key='groq_api_key',
                setting_value_encrypted=encrypted,
                updated_by=updated_by_user_id
            )
            db.session.add(setting)
        
        db.session.commit()
        logger.info("Groq API key updated successfully (key value not logged)")
        return True
    except Exception as e:
        logger.error(f"Failed to update API key: {e}")
        return False


def test_groq_api_key(key: str) -> dict:
    """
    Test a Groq API key by making a minimal API call.
    Returns dict with status and message.
    """
    import requests
    
    if not key:
        return {'status': 'missing', 'message': 'No API key provided'}
    
    try:
        headers = {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': 'Say OK'}],
            'max_tokens': 5
        }
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return {'status': 'active', 'message': 'API key is valid and working'}
        elif response.status_code == 401:
            return {'status': 'invalid', 'message': 'API key is invalid or expired'}
        elif response.status_code == 429:
            return {'status': 'rate_limited', 'message': 'API key valid but rate limit reached'}
        else:
            return {'status': 'error', 'message': f'Unexpected response: {response.status_code}'}
    except requests.exceptions.Timeout:
        return {'status': 'error', 'message': 'Connection timed out'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def mask_api_key(key: str) -> str:
    """
    Return a masked version of an API key for display.
    Example: gsk_**************abcd
    """
    if not key or len(key) < 8:
        return '***'
    prefix = key[:4]
    suffix = key[-4:]
    return f"{prefix}{'*' * 14}{suffix}"
