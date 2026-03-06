# ProfitPulse - User Management Module
import sqlite3
import hashlib
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "profitpulse.db")

def init_db():
    """Initialize users and data database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
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
    
    # User business data tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_labor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            employee TEXT,
            hours REAL,
            rate REAL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # User settings
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            business_type TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
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


# === DATA STORAGE FUNCTIONS ===

def get_user_id(username):
    """Get user ID from username."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def save_user_data(username, data_type, df):
    """Save user's data (sales/purchases/expenses/labor) to database."""
    user_id = get_user_id(username)
    if not user_id:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Map data type to table and columns
    table_map = {
        "sales": ("user_sales", "date, category, amount, description"),
        "purchases": ("user_purchases", "date, category, amount, description"),
        "expenses": ("user_expenses", "date, category, amount, description"),
        "labor": ("user_labor", "date, employee, hours, rate, description"),
    }
    
    if data_type not in table_map:
        conn.close()
        return False
    
    table, cols = table_map[data_type]
    
    # Clear existing data for this user
    c.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    
    # Insert new data
    if data_type == "labor":
        for _, row in df.iterrows():
            c.execute(
                f"INSERT INTO {table} (user_id, {cols}) VALUES (?, ?, ?, ?, ?)",
                (user_id, str(row.get("date", "")), row.get("employee", ""), 
                 row.get("hours", 0), row.get("rate", 0), row.get("description", ""))
            )
    else:
        for _, row in df.iterrows():
            c.execute(
                f"INSERT INTO {table} (user_id, {cols}) VALUES (?, ?, ?, ?, ?)",
                (user_id, str(row.get("date", "")), row.get("category", ""), 
                 row.get("amount", 0), row.get("description", ""))
            )
    
    conn.commit()
    conn.close()
    return True


def load_user_data(username, data_type):
    """Load user's data from database. Returns DataFrame."""
    user_id = get_user_id(username)
    if not user_id:
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    
    table_map = {
        "sales": "user_sales",
        "purchases": "user_purchases", 
        "expenses": "user_expenses",
        "labor": "user_labor",
    }
    
    if data_type not in table_map:
        conn.close()
        return pd.DataFrame()
    
    df = pd.read_sql_query(
        f"SELECT * FROM {table_map[data_type]} WHERE user_id = ?",
        conn, params=(user_id,)
    )
    
    conn.close()
    
    # Clean up columns
    if "user_id" in df.columns:
        df = df.drop(columns=["user_id"])
    if "id" in df.columns:
        df = df.drop(columns=["id"])
    
    return df


def save_user_setting(username, key, value):
    """Save user setting (like business_type)."""
    user_id = get_user_id(username)
    if not user_id:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_settings (user_id, business_type) VALUES (?, ?)",
        (user_id, value)
    )
    conn.commit()
    conn.close()
    return True


def load_user_setting(username, key):
    """Load user setting."""
    user_id = get_user_id(username)
    if not user_id:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT {key} FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


# Initialize on import
init_db()