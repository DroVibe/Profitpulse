"""Supabase client for ProfitPulse user data."""
import os
from supabase import create_client, Client

def get_supabase() -> Client:
    """Create Supabase client from environment secrets."""
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    except:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return None
    
    return create_client(url, key)


def init_tables(supabase: Client):
    """Initialize tables if they don't exist."""
    # Users table
    supabase.table("users").execute()
    

def save_user(supabase: Client, username: str, email: str, tier: str = "free"):
    """Save or update user."""
    data = {
        "username": username,
        "email": email,
        "tier": tier,
    }
    supabase.table("users").upsert(data, on_conflict="username").execute()


def get_user(supabase: Client, username: str) -> dict:
    """Get user by username."""
    result = supabase.table("users").select("*").eq("username", username).execute()
    if result.data:
        return result.data[0]
    return None


def save_user_data(supabase: Client, username: str, table: str, data: dict):
    """Save user business data."""
    supabase.table(f"{table}_{username}").upsert(data).execute()


def load_user_data(supabase: Client, username: str, table: str) -> dict:
    """Load user business data."""
    result = supabase.table(f"{table}_{username}").select("*").execute()
    return result.data if result.data else []