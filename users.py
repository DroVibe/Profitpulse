# ProfitPulse - User Management Module
import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def init_db():
    """Initialize users database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tier TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            stripe_customer_id TEXT,
            subscription_status TEXT DEFAULT 'inactive'
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password with salt."""
    salt = "profitpulse2026"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def create_user(username, email, password):
    """Create new user. Returns (success, message)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hash_password(password))
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already exists."
        elif "email" in str(e):
            return False, "Email already registered."
        return False, "Registration failed."
    finally:
        conn.close()

def verify_user(username, password):
    """Verify login. Returns (success, user_data or None)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, email, tier, subscription_status FROM users WHERE username = ? AND password_hash = ?",
        (username, hash_password(password))
    )
    row = c.fetchone()
    conn.close()
    if row:
        return True, {"id": row[0], "username": row[1], "email": row[2], "tier": row[3], "subscription": row[4]}
    return False, None

def get_user_by_username(username):
    """Get user by username."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, email, tier, subscription_status FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "email": row[2], "tier": row[3], "subscription": row[4]}
    return None

def update_tier(username, tier, stripe_customer_id=None):
    """Update user subscription tier."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if stripe_customer_id:
        c.execute(
            "UPDATE users SET tier = ?, stripe_customer_id = ?, subscription_status = 'active' WHERE username = ?",
            (tier, stripe_customer_id, username)
        )
    else:
        c.execute("UPDATE users SET tier = ? WHERE username = ?", (tier, username))
    conn.commit()
    conn.close()

# Initialize on import
if not os.path.exists(DB_PATH):
    init_db()