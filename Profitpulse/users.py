"""
User management module for ProfitPulse.
Cloud  → Supabase Auth (email+password).
Local  → SQLite (simple file-based fallback).

Design for Supabase:
- auth.users  → Supabase Auth handles session and email identity
- profiles   → minimal public table (username, email). Columns are created lazily.
- user_<type>_<username> → per-user data tables (created on demand)

RLS policies on the profiles table must allow authenticated inserts.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import sqlite3 as _sqlite3

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
    global _supabase_client
    if not SUPABASE_AVAILABLE:
        return None
    if _supabase_client is not None:
        return _supabase_client
    try:
        import streamlit as st
        url  = os.environ.get("SUPABASE_URL")  or (st.secrets.get("SUPABASE_URL")  if hasattr(st, "secrets") else None)
        key  = os.environ.get("SUPABASE_KEY")  or (st.secrets.get("SUPABASE_KEY")  if hasattr(st, "secrets") else None)
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
    conn = _sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tier TEXT DEFAULT 'free',
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _col_names(sb, table: str) -> set[str]:
    """Return set of column names for a table, or empty set on failure."""
    try:
        r = sb.table(table).select("*").limit(1).execute()
        if r.data:
            return set(r.data[0].keys())
    except Exception:
        pass
    return set()


# ── Public Auth API ────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password: str):
    """
    Create a new account.
    Returns (success: bool, message: str).
    """
    sb = _get_supabase()

    if sb is not None:
        # ── Cloud path ─────────────────────────────────────────────────────
        try:
            # Check username uniqueness
            cols = _col_names(sb, "profiles")
            if "username" in cols:
                existing = sb.table("profiles").select("username").eq("username", username).execute()
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

            # Upsert profile — build dict only with columns that exist
            profile = {"username": username, "email": email}
            if "tier" in cols:
                profile["tier"] = "free"
            if "subscription_status" in cols:
                profile["subscription_status"] = "inactive"

            try:
                if "username" in cols:
                    sb.table("profiles").upsert(profile, on_conflict="username").execute()
            except Exception as e:
                # Log but don't fail signup if profiles table has issues
                print(f"Profile upsert warning: {e}")

            return True, "Account created! Check your email to confirm, then sign in."
        except Exception as e:
            err = str(e).lower()
            if "already" in err:
                return False, "Username or email already taken."
            return False, f"Signup failed: {e}"

    else:
        # ── Local SQLite fallback ──────────────────────────────────────────
        _init_sqlite()
        conn = _sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, _salt_hash(password))
            )
            conn.commit()
            return True, "Account created! Please sign in."
        except _sqlite3.IntegrityError as e:
            msg = str(e)
            if "username" in msg:
                return False, "Username already taken."
            elif "email" in msg:
                return False, "Email already registered."
            return False, "Registration failed."
        finally:
            conn.close()


def verify_user(username: str, password: str):
    """
    Verify login credentials. Returns (success, user_data_dict|None).
    """
    sb = _get_supabase()

    if sb is not None:
        # ── Cloud path ─────────────────────────────────────────────────────
        # Find email for this username from profiles table
        email = None
        cols = _col_names(sb, "profiles")
        if "username" in cols:
            try:
                rows = sb.table("profiles").select("email" if "email" in cols else "username").eq("username", username).execute()
                if rows.data:
                    # Try to get email from profiles — fall back to username if no email col
                    row = rows.data[0]
                    email = row.get("email") or (username + "@placeholder.invalid")
            except Exception:
                pass

        if not email:
            return False, None

        try:
            sess = sb.auth.sign_in_with_password({"email": email, "password": password})
            if sess.user is None:
                return False, None
            # Get tier from profiles if available
            tier = "free"
            sub_status = "inactive"
            if "username" in cols:
                try:
                    rows = sb.table("profiles").select("tier","subscription_status").eq("username", username).execute()
                    if rows.data:
                        tier = rows.data[0].get("tier", "free")
                        sub_status = rows.data[0].get("subscription_status", "inactive")
                except Exception:
                    pass
            return True, {
                "username": username,
                "email":    sess.user.email,
                "tier":     tier,
                "subscription_status": sub_status,
            }
        except Exception:
            return False, None

    else:
        # ── Local SQLite fallback ──────────────────────────────────────────
        _init_sqlite()
        conn = _sqlite3.connect(DB_PATH)
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
    """Look up user by username."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = _sqlite3.connect(DB_PATH)
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

    cols = _col_names(sb, "profiles")
    if "username" not in cols:
        return None
    try:
        result = sb.table("profiles").select("*").eq("username", username).execute()
        if result.data:
            return result.data[0]
    except Exception:
        pass
    return None


def update_tier(username: str, tier: str, stripe_customer_id: str | None = None):
    """Update user subscription tier."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = _sqlite3.connect(DB_PATH)
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
        return

    cols = _col_names(sb, "profiles")
    if "username" not in cols:
        return
    try:
        data = {"tier": tier}
        if stripe_customer_id and "stripe_customer_id" in cols:
            data["stripe_customer_id"] = stripe_customer_id
        if "subscription_status" in cols:
            data["subscription_status"] = "active"
        sb.table("profiles").update(data).eq("username", username).execute()
    except Exception:
        pass


def save_user_setting(username: str, key: str, value: str) -> bool:
    """Save a user setting (e.g. business_type)."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = _sqlite3.connect(DB_PATH)
        c = conn.cursor()
        uid_row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not uid_row:
            conn.close()
            return False
        uid = uid_row[0]
        c.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, business_type) VALUES (?, ?)",
            (uid, value)
        )
        conn.commit()
        conn.close()
        return True

    cols = _col_names(sb, "profiles")
    if "username" not in cols:
        return True  # Silently skip
    try:
        sb.table("profiles").update({"business_type": value}).eq("username", username).execute()
    except Exception:
        pass
    return True


def load_user_setting(username: str, key: str) -> str | None:
    """Load a user setting."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = _sqlite3.connect(DB_PATH)
        c = conn.cursor()
        uid_row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not uid_row:
            conn.close()
            return None
        uid = uid_row[0]
        c.execute(f"SELECT {key} FROM user_settings WHERE user_id=?", (uid,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    cols = _col_names(sb, "profiles")
    if "username" not in cols:
        return None
    try:
        result = sb.table("profiles").select(key).eq("username", username).execute()
        if result.data and key in result.data[0]:
            return result.data[0][key]
    except Exception:
        pass
    return None


# ── Data storage helpers ───────────────────────────────────────────────────────

def save_user_data(username: str, data_type: str, df: pd.DataFrame) -> bool:
    """
    Persist a user's DataFrame. Cloud: per-type per-user table (e.g. sales_johndoe).
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

    records = []
    if df is not None:
        for _, row in df.iterrows():
            r = {k: v for k, v in row.to_dict().items() if k not in ("id", "user_id")}
            r["username"] = username
            records.append(r)

    if sb is not None:
        table_name = f"{data_type}_{username}"
        try:
            sb.table(table_name).delete().eq("username", username).execute()
        except Exception:
            pass
        if records:
            try:
                sb.table(table_name).insert(records).execute()
            except Exception:
                pass
        return True

    # SQLite fallback
    _init_sqlite()
    conn = _sqlite3.connect(DB_PATH)
    c = conn.cursor()
    uid_row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not uid_row:
        conn.close()
        return False
    uid = uid_row[0]
    table = table_map[data_type]
    c.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
    for r in records:
        c.execute(
            f"INSERT INTO {table} (user_id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
            (uid, str(r.get("date", "")), r.get("category", ""),
             r.get("amount", 0), r.get("description", ""))
        )
    conn.commit()
    conn.close()
    return True


def load_user_data(username: str, data_type: str) -> pd.DataFrame:
    """
    Load a user's DataFrame. Always returns pd.DataFrame.
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
                return df.drop(columns=["id", "user_id"], errors="ignore")
        except Exception:
            pass
        return pd.DataFrame()

    # SQLite fallback
    _init_sqlite()
    conn = _sqlite3.connect(DB_PATH)
    c = conn.cursor()
    uid_row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not uid_row:
        conn.close()
        return pd.DataFrame()
    uid = uid_row[0]
    table = table_map[data_type]
    df = pd.read_sql_query(f"SELECT * FROM {table} WHERE user_id=?", conn, params=(uid,))
    conn.close()
    return df.drop(columns=["id", "user_id"], errors="ignore")
