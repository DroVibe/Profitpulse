"""Simple user management module for ProfitPulse."""
import json
import hashlib
from pathlib import Path

USER_DATA_FILE = Path(__file__).parent / "user_data.json"
SETTINGS_FILE = Path(__file__).parent / "user_settings.json"

def _load_users():
    if USER_DATA_FILE.exists():
        with open(USER_DATA_FILE) as f:
            return json.load(f)
    return {"admin": {"password_hash": _hash_pw("pilot2026"), "email": "admin@demo.com"}}

def _save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

def _hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def _load_settings():
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {}

def _save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def verify_user(username, password):
    users = _load_users()
    if username in users:
        if users[username]["password_hash"] == _hash_pw(password):
            return True, {"username": username, "email": users[username].get("email")}
    return False, None

def create_user(username, email, password):
    users = _load_users()
    if username in users:
        return False, "User already exists"
    users[username] = {"password_hash": _hash_pw(password), "email": email}
    _save_users(users)
    return True, "User created"

def load_user_data(username, data_type):
    return None

def load_user_setting(username, key):
    settings = _load_settings()
    return settings.get(username, {}).get(key, "")

def save_user_setting(username, key, value):
    settings = _load_settings()
    if username not in settings:
        settings[username] = {}
    settings[username][key] = value
    _save_settings(settings)