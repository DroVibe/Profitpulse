"""
ProfitPulse — User Management
Cloud → Supabase Auth (email + password, session-based).
      Username stored in auth.users user_metadata (no profiles table required).
Local → SQLite.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3

import pandas as pd

# ── Supabase Auth ──────────────────────────────────────────────────────────────
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

_supabase_client = None

def _get_supabase():
    global _supabase_client
    if not SUPABASE_AVAILABLE:
        return None
    if _supabase_client is not None:
        return _supabase_client
    try:
        import streamlit as st
        url = os.environ.get("SUPABASE_URL") or (st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None)
        key = os.environ.get("SUPABASE_KEY") or (st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None)
        if url and key:
            _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception:
        return None

# ── SQLite (local dev) ─────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "profitpulse.db")

def _salt_hash(pw: str) -> str:
    return hashlib.sha256((pw + "profitpulse2026").encode()).hexdigest()

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


# ── Public API ─────────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password: str):
    """
    Create account in two steps:
      A. Insert into Supabase Auth (email + password)
      B. Insert matching row into public.users (username, email, tier)

    Both steps must succeed. If Step A succeeds but Step B fails,
    the error is surfaced to the user rather than silently swallowed.
    """
    sb = _get_supabase()

    if sb is not None:
        # Step A — create auth account
        # email_confirm: False skips the confirmation email so users can log in
        # immediately. Disable this in the Supabase dashboard only if you want
        # email verification on signup.
        try:
            resp = sb.auth.sign_up({
                "email":    email,
                "password": password,
                "options":  {"email_confirm": False},
            })
        except Exception as e:
            err = str(e).lower()
            if "already" in err:
                return False, "Email already registered."
            return False, f"Signup failed: {e}"

        # resp.user can be None even when autoconfirm is off (confirmed-email flow).
        # Only fail if BOTH user and session are None — session proves auth succeeded.
        if resp.user is None and resp.session is None:
            msg = getattr(resp, "msg", "") or str(resp)
            return False, f"Signup failed: {msg}"

        # Step B — insert into public.users (username + tier for downstream use)
        # New signups default to "free" tier. Stripe webhook upgrades to "starter"/"complete".
        try:
            sb.table("users").insert({
                "username": username,
                "email":     email,
                "tier":      "free",
            }).execute()
        except Exception as e:
            err = str(e).lower()
            if "already" in err and "username" in err:
                return False, "Username already taken."
            if "already" in err:
                return False, "Email already registered."
            # Auth succeeded but profile save failed — tell the user clearly
            return False, "Account created but profile save failed. Please contact support."

        return True, "Account created! Check your email to confirm, then sign in."

    # ── Local SQLite fallback ─────────────────────────────────────────────────
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
        msg = str(e)
        if "username" in msg:
            return False, "Username already taken."
        if "email" in msg:
            return False, "Email already registered."
        return False, "Registration failed."
    finally:
        conn.close()


def verify_user(email: str, password: str):
    """
    Verify credentials via Supabase Auth, then look up username + tier
    from public.users (filtered by email).
    Returns (True, dict) on success, (False, error_message) on failure.
    Dict shape: {"username": str, "email": str, "tier": str}
    """
    sb = _get_supabase()

    if sb is not None:
        auth_error = None
        # Step A — authenticate via Supabase Auth
        try:
            sess = sb.auth.sign_in_with_password({"email": email, "password": password})
            if sess.user is None:
                auth_error = "Login failed. Please try again."
        except Exception as e:
            auth_error = str(e)

        if auth_error:
            # Check whether this email exists in public.users.
            # If yes: auth failed but the user account exists — something is wrong.
            # If no: the email is simply not registered.
            try:
                r = sb.table("users").select("username").eq("email", email).execute()
                if r.data:
                    return False, "Login failed. Please contact support."
            except Exception:
                pass
            return False, "Invalid credentials."

        # Step B — look up username and tier from public.users
        try:
            r = sb.table("users").select("username", "email", "tier").eq("email", email).execute()
            if r.data:
                row = r.data[0]
                return True, {
                    "username": row["username"],
                    "email":    row["email"],
                    "tier":     row.get("tier") or "free",
                }
        except Exception:
            pass

        # Auth succeeded but public.users row missing — edge case, derive from email
        username = email.split("@")[0]
        return True, {
            "username": username,
            "email":    email,
            "tier":     "free",
        }

    # ── Local SQLite fallback ───────────────────────────────────────────────
    _init_sqlite()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, email, tier, subscription_status FROM users WHERE email=? AND password_hash=?",
        (email, _salt_hash(password))
    )
    row = c.fetchone()
    conn.close()
    if row:
        return True, {
            "id": row[0], "username": row[1], "email": row[2],
            "tier": row[3], "subscription_status": row[4]
        }
    return False, None


def _get_email_from_auth(sb, username: str) -> str | None:
    """
    DEPRECATED — kept for migration compatibility only.
    Look up a user's email from public.users by username (no service-role key needed).
    """
    try:
        r = sb.table("users").select("email").eq("username", username).execute()
        if r.data:
            return r.data[0]["email"]
    except Exception:
        pass
    return None


def get_user_by_username(username: str) -> dict | None:
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, username, email, tier, subscription_status FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2],
                    "tier": row[3], "subscription_status": row[4]}
        return None

    # Cloud: query public.users directly by username (no service-role key needed)
    try:
        r = sb.table("users").select("username", "email", "tier").eq("username", username).execute()
        if r.data:
            row = r.data[0]
            return {
                "username": row["username"],
                "email":    row["email"],
                "tier":     row.get("tier") or "starter",
            }
    except Exception:
        pass
    return None


def update_tier(username: str, tier: str, stripe_customer_id: str | None = None):
    """No-op on cloud (tier stored in auth metadata / Stripe)."""
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


def save_user_setting(username: str, key: str, value: str) -> bool:
    """Store user settings in a public settings table (no extra columns)."""
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        uid_row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not uid_row:
            conn.close()
            return False
        c.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, business_type) VALUES (?, ?)",
            (uid_row[0], value)
        )
        conn.commit()
        conn.close()
        return True

    # Cloud: settings table with only username + business_type
    try:
        sb.table("settings").upsert(
            {"username": username, "business_type": value},
            on_conflict="username"
        ).execute()
    except Exception:
        pass
    return True


def load_user_setting(username: str, key: str) -> str | None:
    sb = _get_supabase()
    if sb is None:
        _init_sqlite()
        conn = sqlite3.connect(DB_PATH)
        uid_row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not uid_row:
            conn.close()
            return None
        row = conn.execute(f"SELECT {key} FROM user_settings WHERE user_id=?", (uid_row[0],)).fetchone()
        conn.close()
        return row[0] if row else None

    try:
        r = sb.table("settings").select(key).eq("username", username).execute()
        if r.data and key in r.data[0]:
            return r.data[0][key]
    except Exception:
        pass
    return None


# ── Data storage (per-user tables) ────────────────────────────────────────────

def _data_table_name(data_type: str, username: str) -> str:
    safe = username.replace("-", "_").replace(" ", "_")
    return f"{data_type}_{safe}"


def save_user_data(username: str, data_type: str, df: pd.DataFrame) -> bool:
    """Save user's data to the shared Supabase table (user_sales, etc.).
    Uses DELETE + INSERT with username column to isolate per-user rows.
    Returns True on success."""
    # TEMP DEBUG
    print(f"[DEBUG save_user_data] username={username!r}, data_type={data_type!r}, rows={len(df) if df is not None else 'None'}")
    sb = _get_supabase()
    table_map = {
        "sales": "user_sales", "purchases": "user_purchases",
        "expenses": "user_expenses", "labor": "user_labor",
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
        # FIX: use the shared table name from table_map, NOT _data_table_name()
        tname = table_map[data_type]
        print(f"[DEBUG save_user_data] Supabase path — table={tname}, username={username!r}, records={len(records)}")
        try:
            # Delete then insert — all-or-nothing semantics
            sb.table(tname).delete().eq("username", username).execute()
            print(f"[DEBUG save_user_data] DELETE succeeded")
        except Exception as e:
            print(f"[DEBUG save_user_data] DELETE FAILED: {e}")
            return False  # Delete failed — abort rather than lose data
        if records:
            try:
                sb.table(tname).insert(records).execute()
                print(f"[DEBUG save_user_data] INSERT succeeded")
            except Exception as e:
                print(f"[DEBUG save_user_data] INSERT FAILED: {e}")
                return False  # Insert failed — data not saved
        return True

    # SQLite fallback
    _init_sqlite()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    uid = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not uid:
        conn.close()
        return False
    tname = table_map[data_type]
    c.execute(f"DELETE FROM {tname} WHERE user_id=?", (uid[0],))
    for r in records:
        c.execute(
            f"INSERT INTO {tname} (user_id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
            (uid[0], str(r.get("date", "")), r.get("category", ""),
             r.get("amount", 0), r.get("description", ""))
        )
    conn.commit()
    conn.close()
    return True


def load_user_data(username: str, data_type: str) -> pd.DataFrame:
    """Load user's data from the shared Supabase table.
    Filters by username column. Always returns pd.DataFrame (never None)."""
    sb = _get_supabase()
    table_map = {
        "sales": "user_sales", "purchases": "user_purchases",
        "expenses": "user_expenses", "labor": "user_labor",
    }
    if data_type not in table_map:
        return pd.DataFrame()

    if sb is not None:
        # FIX: use shared table name AND filter by username (prevents data leak)
        tname = table_map[data_type]
        try:
            r = sb.table(tname).select("*").eq("username", username).execute()
            if r.data:
                df = pd.DataFrame(r.data)
                return df.drop(columns=["id", "user_id"], errors="ignore")
        except Exception:
            pass
        return pd.DataFrame()

    # SQLite fallback
    _init_sqlite()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    uid = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not uid:
        conn.close()
        return pd.DataFrame()
    tname = table_map[data_type]
    df = pd.read_sql_query(f"SELECT * FROM {tname} WHERE user_id=?", conn, params=(uid[0],))
    conn.close()
    return df.drop(columns=["id", "user_id"], errors="ignore")
