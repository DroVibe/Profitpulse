"""
User management module for ProfitPulse.
Cloud  → Supabase Auth (email+password, session-based).
Local  → SQLite (simple file-based fallback).
Returns DataFrames for data, dicts for user info.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime

import pandas as pd

# ── Supabase Auth ──────────────────────────────────────────────────────────────
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    create_client = None

_supabase_client = None

def _get_supabase():
    """Get or create Supabase client. Returns Client or None."""
    global _supabase_client
    if not SUPABASE_AVAILABLE:
        return None
    if _supabase_client is not None:
        return _supabase_client
    try:
        import streamlit as st
        url = os.environ.get("SUPABASE_URL") or (
            st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None
        )
        key = os.environ.get("SUPABASE_KEY") or (
            st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None
        )
        if url and key:
            _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception:
        return None

# ── SQLite (local dev fallback) ───────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "profitpulse.db")

def _salt_hash(password: str) -> str:
    return hashlib.sha256((password + "profitpulse2026").encode()).hexdigest()

def _init_sqlite():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
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
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            business_type TEXT
        )
    """)
    conn.commit()
    conn.close()

# ── Public Auth API ────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password: str):
    """
    Create a new account.
    Cloud → Supabase Auth + public users table (username as unique key).
    Local → SQLite.
    Returns (success: bool, message: str).
    """
    sb = _get_supabase()

    if sb is not None:
        # ── Cloud: Supabase Auth ──────────────────────────────────────────
        try:
            # Check if username already taken
            existing = sb.table("users").select("username").eq("username", username).execute()
            if existing.data:
                return False, "Username already taken."

            # Sign up via Supabase Auth
            auth_resp = sb.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"username": username}}
            })
            if auth_resp.user is None:
                return False, "Signup failed. Please try again."

            # Store in public users table (username as unique key, no 'id' column)
            sb.table("users").upsert({
                "username":  username,
                "email":     email,
                "tier":      "free",
                "subscription_status": "inactive",
            }, on_conflict="username").execute()

            return True, "Account created! Check your email to confirm, then sign in."
        except Exception as e:
            err = str(e).lower()
            if "already" in err or "unique" in err:
                return False, "Username or email already taken."
            return False, f"Signup failed: {e}"

    else:
        # ── Local: SQLite fallback ────────────────────────────────────────
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, _salt_hash(password))
            )
            conn.commit()
            return True, "Account created! Please sign in."
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Username already taken."
            elif "email" in str(e):
                return False, "Email already registered."
            return False, "Registration failed."
        finally:
            conn.close()


def verify_user(username: str, password: str):
    """
    Verify login credentials.
    Cloud → Supabase Auth (username lookups only, no 'id' column).
    Local → SQLite.
    Returns (success: bool, user_data: dict|None).
    """
    sb = _get_supabase()

    if sb is not None:
        # ── Cloud: Supabase Auth ──────────────────────────────────────────
        try:
            # Look up user by username (no 'id' column assumption)
            row = sb.table("users").select("*").eq("username", username).execute()
            if not row.data:
                return False, None
            user_row = row.data[0]
            email = user_row.get("email", "")

            # Authenticate with Supabase
            sess = sb.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            if sess.user is None:
                return False, None

            return True, {
                "username":           username,
                "email":              sess.user.email,
                "tier":               user_row.get("tier", "free"),
                "subscription_status": user_row.get("subscription_status", "inactive"),
            }
        except Exception:
            return False, None

    else:
        # ── Local: SQLite fallback ────────────────────────────────────────
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, username, email, tier, subscription_status FROM users WHERE username=? AND password_hash=?",
            (username, _salt_hash(password))
        )
        row = c.fetchone()
        conn.close()
        if row:
            return True, {
                "id": row[0], "username": row[1], "email": row[2],
                "tier": row[3], "subscription_status": row[4]
            }
        return False, None


def get_user_by_username(username: str) -> dict | None:
    """Look up user row by username. Cloud + local."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, username, email, tier, subscription_status FROM users WHERE username=?",
            (username,)
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2],
                    "tier": row[3], "subscription_status": row[4]}
        return None

    result = sb.table("users").select("*").eq("username", username).execute()
    if result.data:
        return result.data[0]
    return None


def update_tier(username: str, tier: str, stripe_customer_id: str | None = None):
    """Update user subscription tier."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if stripe_customer_id:
            c.execute(
                "UPDATE users SET tier=?, stripe_customer_id=?, subscription_status='active' WHERE username=?",
                (tier, stripe_customer_id, username)
            )
        else:
            c.execute("UPDATE users SET tier=? WHERE username=?", (tier, username))
        conn.commit()
        conn.close()
    else:
        data = {"tier": tier, "subscription_status": "active"}
        if stripe_customer_id:
            data["stripe_customer_id"] = stripe_customer_id
        sb.table("users").update(data).eq("username", username).execute()


def save_user_setting(username: str, key: str, value: str) -> bool:
    """Save a user setting (e.g. business_type). Uses username as key for Supabase."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, business_type) "
            "VALUES ((SELECT id FROM users WHERE username=?), ?)",
            (username, value)
        )
        conn.commit()
        conn.close()
        return True

    # Supabase path: use username as the unique identifier
    col = "business_type"
    existing = sb.table("user_settings").select("username").eq("username", username).execute()
    if existing.data:
        sb.table("user_settings").update({col: value}).eq("username", username).execute()
    else:
        sb.table("user_settings").insert({"username": username, col: value}).execute()
    return True


def load_user_setting(username: str, key: str) -> str | None:
    """Load a user setting. Uses username as key for Supabase."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            f"SELECT {key} FROM user_settings WHERE user_id=(SELECT id FROM users WHERE username=?)",
            (username,)
        )
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    # Supabase path: use username
    result = sb.table("user_settings").select(key).eq("username", username).execute()
    return result.data[0][key] if result.data else None


# ── Data storage helpers ───────────────────────────────────────────────────────

def _get_uid(username: str) -> int | None:
    """Get internal user id from username."""
    user = get_user_by_username(username)
    return user.get("id") if user else None


def save_user_data(username: str, data_type: str, df: pd.DataFrame) -> bool:
    """
    Persist a user's DataFrame (sales/purchases/expenses/labor) to storage.
    Cloud → one Supabase table per user per type (e.g. sales_john).
    Local → SQLite.
    """
    sb = _get_supabase()
    table_map = {
        "sales":     "user_sales",
        "purchases":  "user_purchases",
        "expenses":   "user_expenses",
        "labor":      "user_labor",
    }
    if data_type not in table_map:
        return False
    records = df.to_dict("records") if df is not None else []

    if sb is not None:
        table_name = f"{data_type}_{username}"
        try:
            sb.table(table_name).delete().eq("username", username).execute()
        except Exception:
            pass  # table may not exist yet
        if records:
            for r in records:
                r["username"] = username
            try:
                sb.table(table_name).insert(records).execute()
            except Exception:
                pass  # table may not exist yet
        return True

    # SQLite fallback
    _init_sqlite()
    uid = _get_uid(username)
    if not uid:
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    table = table_map[data_type]
    c.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
    for _, row in df.iterrows():
        c.execute(
            f"INSERT INTO {table} (user_id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
            (uid, str(row.get("date", "")), row.get("category", ""),
             row.get("amount", 0), row.get("description", ""))
        )
    conn.commit()
    conn.close()
    return True


def load_user_data(username: str, data_type: str) -> pd.DataFrame:
    """
    Load a user's DataFrame from storage.
    Always returns a pd.DataFrame (never None, never a list).
    """
    sb = _get_supabase()
    table_map = {
        "sales":     "user_sales",
        "purchases":  "user_purchases",
        "expenses":   "user_expenses",
        "labor":      "user_labor",
    }
    if data_type not in table_map:
        return pd.DataFrame()

    if sb is not None:
        table_name = f"{data_type}_{username}"
        try:
            result = sb.table(table_name).select("*").execute()
            if result.data:
                df = pd.DataFrame(result.data)
                for col in ("id", "user_id", "username"):
                    if col in df.columns:
                        df = df.drop(columns=[col])
                return df
        except Exception:
            pass
        return pd.DataFrame()

    # SQLite fallback
    _init_sqlite()
    uid = _get_uid(username)
    if not uid:
        return pd.DataFrame()
    table = table_map[data_type]
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM {table} WHERE user_id=?", conn, params=(uid,))
    conn.close()
    for col in ("id", "user_id"):
        if col in df.columns:
            df = df.drop(columns=[col])
    return df
