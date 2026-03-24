"""User management module for ProfitPulse - Supabase backend."""
import hashlib
import os

# Supabase client will be passed in
_supabase = None

def _get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        try:
            import streamlit as st
            url = os.environ.get("SUPABASE_URL") or (st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None)
            key = os.environ.get("SUPABASE_KEY") or (st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None)
            if url and key:
                _supabase = create_client(url, key)
        except Exception as e:
            print(f"Supabase init error: {e}")
    return _supabase

def _hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Verify user credentials against Supabase."""
    sb = _get_supabase()
    if not sb:
        # Fallback for local dev without Supabase
        return _verify_local(username, password)
    
    try:
        result = sb.table("users").select("*").eq("username", username).execute()
        if result.data:
            user = result.data[0]
            if user.get("password_hash") == _hash_pw(password):
                return True, {"username": username, "email": user.get("email", ""), "tier": user.get("tier", "free")}
    except Exception as e:
        print(f"Verify error: {e}")
    
    return False, None

def _verify_local(username, password):
    """Local fallback for development."""
    return False, None

def create_user(username, email, password):
    """Create new user in Supabase."""
    sb = _get_supabase()
    if not sb:
        return False, "Database not configured"
    
    try:
        # Check if user exists
        result = sb.table("users").select("username").eq("username", username).execute()
        if result.data:
            return False, "User already exists"
        
        # Create user
        sb.table("users").insert({
            "username": username,
            "email": email,
            "password_hash": _hash_pw(password),
            "tier": "free"
        }).execute()
        return True, "Account created! Please sign in."
    except Exception as e:
        print(f"Create user error: {e}")
        return False, f"Error: {str(e)}"

def load_user_data(username, data_type):
    """Load user's business data from Supabase."""
    sb = _get_supabase()
    if not sb:
        return None
    
    try:
        table_name = f"user_{data_type}"
        result = sb.table(table_name).select("*").eq("username", username).execute()
        if result.data:
            return result.data
    except Exception as e:
        print(f"Load {data_type} error: {e}")
    
    return []

def save_user_data(username, data_type, data):
    """Save user's business data to Supabase."""
    sb = _get_supabase()
    if not sb:
        return False
    
    try:
        table_name = f"user_{data_type}"
        # Delete old data first
        sb.table(table_name).delete().eq("username", username).execute()
        # Insert new data
        for row in data:
            row["username"] = username
        sb.table(table_name).insert(data).execute()
        return True
    except Exception as e:
        print(f"Save {data_type} error: {e}")
        return False

def load_user_setting(username, key):
    """Load user setting from Supabase."""
    sb = _get_supabase()
    if not sb:
        return ""
    
    try:
        result = sb.table("users").select(key).eq("username", username).execute()
        if result.data:
            return result.data[0].get(key, "")
    except:
        pass
    return ""

def save_user_setting(username, key, value):
    """Save user setting to Supabase."""
    sb = _get_supabase()
    if not sb:
        return False
    
    try:
        sb.table("users").update({key: value}).eq("username", username).execute()
        return True
    except:
        return False

def get_user_tier(username):
    """Get user's subscription tier."""
    sb = _get_supabase()
    if not sb:
        return "free"
    
    try:
        result = sb.table("users").select("tier").eq("username", username).execute()
        if result.data:
            return result.data[0].get("tier", "free")
    except:
        pass
    return "free"

def update_user_tier(username, tier):
    """Update user's subscription tier."""
    sb = _get_supabase()
    if not sb:
        return False
    
    try:
        sb.table("users").update({"tier": tier}).eq("username", username).execute()
        return True
    except:
        return False