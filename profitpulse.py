# ============================================================
# ProfitPulse — AI-Powered Business Analytics Dashboard
# Polished & Production-Ready | February 2026
# Updated: March 2026 - Mobile improvements, Dark/Light mode, Venice key fix
# ============================================================
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import importlib.util
load_dotenv()

import io
import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from openai import OpenAI
from fpdf import FPDF

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
APP_NAME  = "ProfitPulse"
# Placeholder - will be set after st is imported
API_KEY  = None
BASE_URL = "https://api.venice.ai/api/v1"
MODEL    = "llama-3.3-70b"
DEMO_USER = "admin"
DEMO_PASS = "pilot2026"

TAX_CALCULATOR_PATH = Path(__file__).resolve().parent / "fl-tax-shield" / "calculator.py"
TAX_CALCULATOR = None

if TAX_CALCULATOR_PATH.exists():
    tax_spec = importlib.util.spec_from_file_location("fl_tax_calculator", TAX_CALCULATOR_PATH)
    if tax_spec and tax_spec.loader:
        TAX_CALCULATOR = importlib.util.module_from_spec(tax_spec)
        sys.modules["fl_tax_calculator"] = TAX_CALCULATOR  # Register before exec
        tax_spec.loader.exec_module(TAX_CALCULATOR)


def get_api_key():
    """Get API key from environment, .env, or Streamlit Cloud secrets"""
    # Priority: os.environ -> .env -> st.secrets
    key = os.environ.get("VENICE_API_KEY") or os.getenv("VENICE_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                key = st.secrets.get("VENICE_API_KEY", "")
        except Exception:
            pass
    return key

BENCHMARKS = {
    "gross_margin_pct":         45.0,
    "labor_pct_of_revenue":     25.0,
    "net_margin_pct":           10.0,
    "overtime_threshold_hours":  8.0,
}

EXPENSE_CATEGORIES = [
    "Rent/Lease", "Utilities", "Insurance", "Marketing",
    "Office Supplies", "Equipment", "Vehicle/Fuel",
    "Software/Subscriptions", "Maintenance", "Misc",
]

BUSINESS_TYPES = [
    "Auto Repair", "Coffee Shop", "Retail Clothing",
    "Restaurant", "Freelance/Service", "Other",
]

# ────────────────────────────────────────────────
# PAGE CONFIG — must be first st.* call
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="ProfitPulse",
    page_icon="single_green_pulse_32.png",   # 32px version
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────
# GLOBAL CSS
# FIX: corrected unclosed .pnl-row.total brace that bled into
#      .premium-card/.tier-card, breaking dark-mode premium page.
# ADDED: dark-mode alert colours, button radius, input focus ring,
#        scrollbar, mobile padding tweak, card hover polish.
# March 2026: Mobile touch optimizations, Light mode support, Theme toggle
# ────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }
  .block-container { padding-top: 2rem; max-width: 1200px; }
  h1, h2, h3 { font-weight: 600; letter-spacing: -0.02em; }

  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
  }
  section[data-testid="stSidebar"] .stMarkdown p,
  section[data-testid="stSidebar"] .stMarkdown h3,
  section[data-testid="stSidebar"] .stMarkdown span,
  section[data-testid="stSidebar"] label { color: #e0e0e0 !important; }

  /* Theme Toggle Button */
  .theme-toggle {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 9999;
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 20px;
    padding: 6px 14px;
    color: #a5b4fc;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .theme-toggle:hover {
    background: rgba(99, 102, 241, 0.35);
    color: #fff;
  }

  .pp-card {
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    color: #fff;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }
  .pp-card:hover { transform: translateY(-3px); box-shadow: 0 10px 28px rgba(0,0,0,0.18); }
  .pp-card .label {
    font-size: 0.78rem; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.06em;
    opacity: 0.8; margin-bottom: 0.25rem;
  }
  .pp-card .value { font-size: 1.75rem; font-weight: 700; line-height: 1.1; margin: 0; }
  .pp-card .sub   { font-size: 0.72rem; opacity: 0.65; margin-top: 0.3rem; }

  .status-strip {
    border-radius: 14px;
    padding: 0.95rem 1.1rem;
    margin: 0.25rem 0 1rem;
    border: 1px solid rgba(255,255,255,0.08);
    background: linear-gradient(135deg, rgba(15,23,42,0.92) 0%, rgba(30,41,59,0.92) 100%);
    color: #e2e8f0;
  }
  .status-strip strong { display:block; font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.72; margin-bottom: 0.25rem; }
  .status-strip span { font-size: 0.95rem; font-weight: 600; display: block; margin-top: 0.25rem; }

  .card-default { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); }
  .card-good    { background: linear-gradient(135deg, #065f46 0%, #059669 100%); }
  .card-warn    { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); }
  .card-bad     { background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); }
  .card-accent  { background: linear-gradient(135deg, #312e81 0%, #6366f1 100%); }

  /* Dark-mode safe alert colours */
  .pp-alert {
    border-radius: 12px; padding: 0.8rem 1.2rem;
    font-size: 0.88rem; margin-bottom: 0.5rem;
    border-left: 4px solid;
  }
  .pp-alert-warn { background: rgba(245,158,11,0.15); border-color: #f59e0b; color: #fde68a; }
  .pp-alert-bad  { background: rgba(239,68,68,0.15);  border-color: #ef4444; color: #fca5a5; }

  .pnl-row {
    display: flex; justify-content: space-between;
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(241,245,249,0.12);
    font-size: 0.92rem;
  }
  /* FIX: properly closed this rule so it no longer bleeds into premium cards */
  .pnl-row.total {
    font-weight: 700;
    border-bottom: 2px solid rgba(30,41,59,0.8);
    padding-top: 0.8rem;
    margin-top: 0.3rem;
  }

  .premium-card {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #e2e8f0;
  }
  .tier-card {
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.5rem;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: #e2e8f0;
    height: 100%;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }
  .tier-card:hover { transform: translateY(-3px); box-shadow: 0 10px 28px rgba(0,0,0,0.5); }
  .tier-card h2 { color: #ffffff; margin: 0.25rem 0; }
  .tier-card p  { color: #cbd5e1; }
  .tier-card hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1rem 0; }
  .tier-card.featured {
    border-color: #6366f1;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.4), 0 8px 24px rgba(99,102,241,0.15);
    background: linear-gradient(135deg, #2d3748 0%, #1e293b 100%);
  }

  .page-header {
    font-size: 1.6rem; font-weight: 700; color: #f1f5f9;
    margin-bottom: 0.25rem; letter-spacing: -0.03em;
  }
  .page-sub { font-size: 0.9rem; color: #94a3b8; margin-bottom: 1.5rem; }

  .stButton > button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: opacity 0.15s ease !important;
  }
  .stButton > button:hover { opacity: 0.88; }

  input:focus, textarea:focus, select:focus {
    outline: 2px solid #6366f1 !important;
    outline-offset: 1px !important;
  }

  /* Mobile Touch Optimizations */
  @media (max-width: 768px) {
    .block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; }
    .pp-card .value  { font-size: 1.35rem; }
    
    /* Smooth slider interaction on mobile */
    input[type="range"] {
      -webkit-tap-highlight-color: transparent;
      touch-action: pan-x;
    }
    input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #6366f1;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      margin-top: -8px;
    }
    input[type="range"]::-webkit-slider-runnable-track {
      height: 8px;
      border-radius: 4px;
      background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    input[type="range"]:focus::-webkit-slider-thumb {
      box-shadow: 0 0 0 4px rgba(99,102,241,0.3);
    }
    
    /* Better touch targets */
    .stButton > button {
      min-height: 48px;
      padding: 12px 20px;
    }
    
    /* Fluid sidebar */
    section[data-testid="stSidebar"] {
      width: 85vw !important;
    }
  }

  /* Light Mode Styles */
  .light-mode {
    background: #ffffff !important;
    color: #1e293b !important;
  }
  .light-mode .block-container {
    background: #ffffff;
  }
  .light-mode .pp-card {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
    color: #1e293b !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
  }
  .light-mode .pp-card .label {
    color: #475569 !important;
    opacity: 1 !important;
  }
  .light-mode .pp-card .value {
    color: #0f172a !important;
  }
  .light-mode .pp-card .sub {
    color: #64748b !important;
  }
  .light-mode h1, .light-mode h2, .light-mode h3 {
    color: #0f172a !important;
  }
  .light-mode .page-header {
    color: #0f172a !important;
  }
  .light-mode .page-sub {
    color: #64748b !important;
  }
  .light-mode .pnl-row {
    border-bottom: 1px solid rgba(0,0,0,0.08) !important;
    color: #334155 !important;
  }
  .light-mode .stMarkdown p {
    color: #334155 !important;
  }
  .light-mode section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%) !important;
  }
  .light-mode section[data-testid="stSidebar"] .stMarkdown p,
  .light-mode section[data-testid="stSidebar"] .stMarkdown h3,
  .light-mode section[data-testid="stSidebar"] .stMarkdown span,
  .light-mode section[data-testid="stSidebar"] label {
    color: #334155 !important;
  }

  #MainMenu { visibility: hidden; }
  footer     { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# THEME TOGGLE FUNCTIONALITY
# ────────────────────────────────────────────────
def render_theme_toggle():
    """Render theme toggle button and apply theme"""
    # Get current theme - default to dark
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    theme = st.session_state.theme
    
    # Toggle button with icons
    col_t1, col_t2 = st.columns([1, 4])
    with col_t1:
        if theme == "dark":
            if st.button("🌙", key="theme_toggle_btn", help="Switch to light mode"):
                st.session_state.theme = "light"
                st.rerun()
        else:
            if st.button("☀️", key="theme_toggle_btn", help="Switch to dark mode"):
                st.session_state.theme = "dark"
                st.rerun()
    with col_t2:
        st.caption(f"Current: {'Dark' if theme == 'dark' else 'Light'} mode")

# Apply theme class to body
def apply_theme():
    """Apply theme CSS class based on user preference"""
    theme = st.session_state.get("theme", "dark")
    
    # Use Streamlit's native theme support where possible
    # and CSS variables for the rest
    if theme == "light":
        st.markdown("""
        <style>
            /* Light mode CSS overrides */
            .block-container { background: #ffffff !important; }
            section[data-testid="stMain"] { background: #ffffff !important; }
            section[data-testid="stMain"] > div { background: #ffffff !important; }
            [data-testid="stAppViewContainer"] { background: #ffffff !important; }
            [data-testid="stApp"] { background: #ffffff !important; }
            .pp-card {
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
                color: #1e293b !important;
            }
            .pp-card .value { color: #0f172a !important; }
            .page-header, h1, h2, h3 { color: #0f172a !important; }
            .page-sub, .stMarkdown p, .stMarkdown span { color: #475569 !important; }
            .pnl-row { border-bottom: 1px solid rgba(0,0,0,0.08) !important; color: #334155 !important; }
            section[data-testid="stSidebar"] { 
                background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%) !important;
            }
            section[data-testid="stSidebar"] .stMarkdown p,
            section[data-testid="stSidebar"] .stMarkdown span,
            section[data-testid="stSidebar"] label {
                color: #334155 !important;
            }
            /* Input fields */
            .stTextInput > div > div > input,
            .stNumberInput > div > div > input,
            .stSelectbox > div > div > div {
                background: #ffffff !important;
                color: #1e293b !important;
                border-color: #cbd5e1 !important;
            }
            /* DataFrames */
            [data-testid="stDataFrame"] {
                background: #ffffff !important;
            }
            /* Metrics */
            [data-testid="stMetricValue"] {
                color: #0f172a !important;
            }
            [data-testid="stMetricLabel"] {
                color: #64748b !important;
            }
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
                background: #e2e8f0 !important;
                color: #0f172a !important;
            }
            /* Buttons */
            .stButton > button {
                background: #6366f1 !important;
                color: #ffffff !important;
            }
            /* Alert boxes */
            .stAlert {
                background: #f8fafc !important;
                color: #1e293b !important;
            }
            /* Info boxes */
            .stInfo {
                background: #e0f2fe !important;
                color: #0369a1 !important;
            }
            /* Warning boxes */
            .stWarning {
                background: #fef3c7 !important;
                color: #92400e !important;
            }
            /* Success boxes */
            .stSuccess {
                background: #dcfce7 !important;
                color: #166534 !important;
            }
            /* Error boxes */
            .stError {
                background: #fee2e2 !important;
                color: #991b1b !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Dark mode CSS (default)
        st.markdown("""
        <style>
            /* Ensure dark mode stays dark */
            .block-container { background: transparent !important; }
            [data-testid="stAppViewContainer"] { background: #0f172a !important; }
            [data-testid="stApp"] { background: #0f172a !important; }
        </style>
        """, unsafe_allow_html=True)


# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
def init_state() -> None:
    defaults: dict = {
        "authenticated":   False,
        "username":        "",
        "user_tier":       "free",  # free, pro, demo
        "nav_page":        "Overview",
        "df_sales":        pd.DataFrame(),
        "df_purchases":    pd.DataFrame(),
        "df_expenses":     pd.DataFrame(),
        "df_labor":        pd.DataFrame(),
        "chat_history":    [],
        "pnl_cache":       {},
        "business_type":   None,
        "tax_county":      "Miami-Dade",
        "tax_structure":   "llc",
        "tax_filing":      "quarterly",
        "tax_profit_margin": 0.10,
        "onboarded":       False,
        "onboarding_step": 0,
        "last_calculated": None,   # timestamp shown on dashboard
        "theme":           "dark",  # default to dark
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ────────────────────────────────────────────────
# UI COMPONENT HELPERS
# ────────────────────────────────────────────────
def pp_card(label: str, value: str, sub: str = "", theme: str = "default") -> None:
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"""<div class="pp-card card-{theme}">
              <div class="label">{label}</div>
              <div class="value">{value}</div>
              {sub_html}
            </div>""",
        unsafe_allow_html=True,
    )


def pp_alert(text: str, level: str = "warn") -> None:
    st.markdown(
        f'<div class="pp-alert pp-alert-{level}">{text}</div>',
        unsafe_allow_html=True,
    )


def pnl_row(label: str, amount: float, pct: str = "", total: bool = False) -> None:
    cls       = "pnl-row total" if total else "pnl-row"
    sign      = "" if amount >= 0 else "-"
    formatted = f"{sign}${abs(amount):,.2f}"
    st.markdown(
        f"""<div class="{cls}">
              <span>{label}</span>
              <span style="flex:1"></span>
              <span style="margin-right:1.5rem;opacity:0.65">{pct}</span>
              <span style="min-width:120px;text-align:right">{formatted}</span>
            </div>""",
        unsafe_allow_html=True,
    )


PLAN_LABELS = {
    "free": "ProfitPulse Starter",
    "starter": "ProfitPulse Starter",
    "pro": "ProfitPulse Complete",
    "complete": "ProfitPulse Complete",
    "demo": "ProfitPulse Complete (Demo)",
}


BUSINESS_TYPE_TO_TAX = {
    "Auto Repair": "contractor",
    "Coffee Shop": "restaurant",
    "Retail Clothing": "retail",
    "Restaurant": "restaurant",
    "Freelance/Service": "consulting",
    "Other": "other",
}


def has_complete_access() -> bool:
    return st.session_state.user_tier in {"pro", "complete", "demo"}


def current_plan_label() -> str:
    return PLAN_LABELS.get(st.session_state.user_tier, "ProfitPulse Starter")


def map_business_type_to_tax_key() -> str:
    biz = st.session_state.business_type or "Other"
    return BUSINESS_TYPE_TO_TAX.get(biz, "other")


def estimate_annualized_revenue(pnl: dict) -> float:
    days = max(float(pnl.get("date_range_days", 0) or 0), 1.0)
    return round((pnl.get("total_revenue", 0.0) / days) * 365, 2)


def build_tax_snapshot(pnl: dict) -> dict | None:
    if TAX_CALCULATOR is None or not pnl or pnl.get("total_revenue", 0) <= 0:
        return None

    annual_revenue = estimate_annualized_revenue(pnl)
    sales_tax = TAX_CALCULATOR.calculate_sales_tax(
        annual_revenue,
        st.session_state.tax_county,
        map_business_type_to_tax_key(),
        st.session_state.tax_filing,
    )
    corporate_tax = TAX_CALCULATOR.calculate_corporate_tax(
        annual_revenue,
        st.session_state.tax_structure,
        st.session_state.tax_profit_margin,
    )
    allowance = TAX_CALCULATOR.calculate_collection_allowance(
        sales_tax["annual_sales_tax"],
        sales_tax["filing_frequency"],
    )
    return {
        "annualized_revenue": annual_revenue,
        "sales_tax": sales_tax,
        "corporate_tax": corporate_tax,
        "allowance": allowance,
        "net_annual_tax": round(
            sales_tax["annual_sales_tax"]
            + corporate_tax["annual_corporate_tax"]
            - allowance["annual_allowance"],
            2,
        ),
    }


def jump_to(page: str) -> None:
    st.session_state.nav_page = page
    st.rerun()


CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#94a3b8"),
    margin=dict(t=30, b=30, l=40, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(gridcolor="rgba(241,245,249,0.08)", zerolinecolor="rgba(226,232,240,0.1)"),
    yaxis=dict(gridcolor="rgba(241,245,249,0.08)", zerolinecolor="rgba(226,232,240,0.1)"),
)


# ────────────────────────────────────────────────
# AUTH
# ────────────────────────────────────────────────
def login_page() -> None:
    import users  # User management module
    
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style="text-align:center; margin-top:6vh; margin-bottom:2rem;">
            <span style="font-size:2.5rem;">◈</span>
            <h1 style="font-size:1.8rem; font-weight:700; margin:0.5rem 0 0.2rem;">ProfitPulse</h1>
            <p style="color:#94a3b8; font-size:0.9rem; margin:0;">
                AI-powered profitability analytics for any small business
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Toggle between Login and Signup
        if "show_signup" not in st.session_state:
            st.session_state.show_signup = False
        
        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])
        
        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Username", placeholder="admin")
                pw   = st.text_input("Password", type="password", placeholder="••••••••")
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
                if submitted:
                    # First check demo credentials
                    valid_user = os.getenv("APP_USER", DEMO_USER)
                    valid_pass = os.getenv("APP_PASS", DEMO_PASS)
                    if user == valid_user and pw == valid_pass:
                        st.session_state.authenticated = True
                        st.session_state.username = user
                        st.session_state.user_tier = "demo"
                        initialize_demo_workspace()
                        st.rerun()
                    # Then check database users
                    success, user_data = users.verify_user(user, pw)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = user
                        st.session_state.user_tier = user_data["tier"]
                        # Load user's saved data from database
                        st.session_state.df_sales = users.load_user_data(user, "sales")
                        st.session_state.df_purchases = users.load_user_data(user, "purchases")
                        st.session_state.df_expenses = users.load_user_data(user, "expenses")
                        st.session_state.df_labor = users.load_user_data(user, "labor")
                        # Load user's business type
                        biz_type = users.load_user_setting(user, "business_type")
                        if biz_type:
                            st.session_state.business_type = biz_type
                            st.session_state.onboarded = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
            st.markdown(
                "<p style='text-align:center;font-size:0.78rem;color:#cbd5e1;margin-top:1rem;'>"
                "Demo: admin / pilot2026</p>",
                unsafe_allow_html=True,
            )
        
        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email", placeholder="your@email.com")
                new_pw = st.text_input("Password", type="password", placeholder="Create password")
                confirm_pw = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                signup_submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                if signup_submit:
                    if not new_user or not new_email or not new_pw:
                        st.error("Please fill in all fields.")
                    elif new_pw != confirm_pw:
                        st.error("Passwords do not match.")
                    elif len(new_pw) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        success, msg = users.create_user(new_user, new_email, new_pw)
                        if success:
                            st.success(msg + " Please sign in.")
                            st.session_state.show_signup = False
                            st.rerun()
                        else:
                            st.error(msg)
            st.markdown(
                "<p style='text-align:center;font-size:0.75rem;color:#94a3b8;margin-top:1rem;'>"
                "Starter includes analytics. Complete adds TaxShield planning tools.</p>",
                unsafe_allow_html=True,
            )


def logout() -> None:
    # Wipe entire session on sign-out for security
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ────────────────────────────────────────────────
# DEMO DATA  (@st.cache_data — deterministic, safe to cache by args)
# ADDED: Restaurant profile; cleaner profile dict structure
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def generate_demo_data(months: int = 6, business_type: str = "Auto Repair") -> dict:
    """Return realistic demo DataFrames for the chosen business type."""
    np.random.seed(42)
    end   = datetime.date.today()
    start = end - datetime.timedelta(days=30 * months)
    dates = pd.date_range(start, end, freq="D")

    profiles = {
        "Auto Repair": {
            "prices":    {"Oil Change": 75, "Brake Service": 350, "Tires": 600,
                          "Diagnostics": 120, "Parts Sale": 85, "Alignment": 100,
                          "Transmission": 900, "AC Service": 250},
            "purchases": ["Parts Wholesale", "Oil/Fluids", "Tires Wholesale",
                          "Brake Components", "Filters", "Misc Parts"],
            "employees": {"Mike T.": 28, "Sarah L.": 24, "Jose R.": 22, "Kim P.": 20},
            "txn_range": (3, 12),
        },
        "Coffee Shop": {
            "prices":    {"Latte": 5.5, "Cappuccino": 5.0, "Espresso": 3.5,
                          "Pastry": 4.0, "Cold Brew": 6.0, "Bagel": 3.8},
            "purchases": ["Coffee Beans", "Milk", "Pastries Wholesale",
                          "Cups/Lids", "Syrups", "Misc"],
            "employees": {"Emma": 16, "Liam": 15.5, "Olivia": 15, "Noah": 14.5},
            "txn_range": (8, 25),
        },
        "Retail Clothing": {
            "prices":    {"T-Shirt": 28, "Jeans": 65, "Jacket": 120,
                          "Shoes": 89, "Accessory": 18, "Dress": 95},
            "purchases": ["Wholesale Clothing", "Accessories", "Shoes Wholesale",
                          "Packaging", "Misc"],
            "employees": {"Ava": 18, "Sophia": 17, "Isabella": 16.5, "Mia": 16},
            "txn_range": (4, 15),
        },
        "Restaurant": {
            "prices":    {"Appetizer": 12, "Entree": 24, "Dessert": 9,
                          "Beverage": 6, "Cocktail": 14, "Lunch Special": 16},
            "purchases": ["Food Wholesale", "Beverages", "Produce",
                          "Dairy", "Packaging", "Misc"],
            "employees": {"Chef": 28, "Server 1": 16, "Server 2": 15, "Host": 14},
            "txn_range": (10, 40),
        },
    }

    profile    = profiles.get(business_type, {
        "prices":    {"Product A": 100, "Service B": 250, "Item C": 50},
        "purchases": ["Inventory", "Supplies", "Misc"],
        "employees": {"Employee 1": 22, "Employee 2": 20},
        "txn_range": (3, 10),
    })
    base_prices = profile["prices"]
    purch_cats  = profile["purchases"]
    employees   = profile["employees"]          # name → hourly rate
    emp_names   = list(employees.keys())
    txn_lo, txn_hi = profile["txn_range"]

    sales_rows = []
    for d in dates:
        for _ in range(np.random.randint(txn_lo, txn_hi)):
            cat = np.random.choice(list(base_prices.keys()))
            amt = round(base_prices[cat] * np.random.uniform(0.8, 1.4), 2)
            sales_rows.append({"date": d.strftime("%Y-%m-%d"), "category": cat,
                               "amount": amt, "description": f"{cat} sale"})

    purch_rows = []
    for d in dates[::3]:
        for _ in range(np.random.randint(1, 5)):
            cat = np.random.choice(purch_cats)
            amt = round(np.random.uniform(40, 1200), 2)
            purch_rows.append({"date": d.strftime("%Y-%m-%d"), "category": cat,
                               "amount": amt, "description": f"{cat} order"})

    exp_ranges = {
        "Rent/Lease":             (1800, 3200),
        "Utilities":              (300,   900),
        "Insurance":              (600,  1200),
        "Marketing":              (150,   800),
        "Software/Subscriptions": (80,    300),
        "Maintenance":            (50,    600),
        "Misc":                   (40,    400),
    }
    exp_rows = []
    for m in pd.date_range(start, end, freq="MS"):
        for cat, (lo, hi) in exp_ranges.items():
            amt = round(np.random.uniform(lo, hi), 2)
            exp_rows.append({"date": m.strftime("%Y-%m-%d"), "category": cat,
                             "amount": amt, "description": f"Monthly {cat}"})

    labor_rows = []
    for d in dates:
        if d.weekday() < 6:
            size = np.random.randint(2, min(len(emp_names) + 1, 5))
            chosen = np.random.choice(emp_names, size=size, replace=False)
            for emp in chosen:
                hrs = round(np.random.uniform(4, 10.5), 1)
                labor_rows.append({
                    "date":        d.strftime("%Y-%m-%d"),
                    "employee":    emp,
                    "hours":       hrs,
                    "rate":        employees[emp],
                    "description": "Regular shift" if hrs <= 8 else "Overtime shift",
                })

    return {
        "sales":     pd.DataFrame(sales_rows),
        "purchases": pd.DataFrame(purch_rows),
        "expenses":  pd.DataFrame(exp_rows),
        "labor":     pd.DataFrame(labor_rows),
    }


def initialize_demo_workspace() -> None:
    if not st.session_state.business_type:
        st.session_state.business_type = "Auto Repair"

    if st.session_state.df_sales.empty:
        demo = generate_demo_data(6, st.session_state.business_type)
        st.session_state.df_sales = demo["sales"]
        st.session_state.df_purchases = demo["purchases"]
        st.session_state.df_expenses = demo["expenses"]
        st.session_state.df_labor = demo["labor"]

    st.session_state.onboarded = True
    st.session_state.onboarding_step = None
    st.session_state.nav_page = "Overview"


# ────────────────────────────────────────────────
# CSV PARSING
# ────────────────────────────────────────────────
def parse_csv(file, expected_cols: list, name: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
            st.warning(f"**{name}:** Missing columns {missing}. Found: {list(df.columns)}")
            return pd.DataFrame()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            bad = df["date"].isna().sum()
            df  = df.dropna(subset=["date"])
            if bad:
                st.warning(f"**{name}:** Dropped {bad} rows with unparseable dates.")
        for num_col in ["amount", "hours", "rate"]:
            if num_col in df.columns:
                df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(0)
        return df
    except Exception as exc:
        st.error(f"**{name} parse error:** {exc}")
        return pd.DataFrame()


# ────────────────────────────────────────────────
# P&L ENGINE
# Refactored: pure @st.cache_data function hashed by DataFrame content.
# Session-state wrapper keeps call-sites identical to before.
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _compute_pnl(
    sales_df:     pd.DataFrame,
    purchases_df: pd.DataFrame,
    expenses_df:  pd.DataFrame,
    labor_df:     pd.DataFrame,
) -> dict:
    total_revenue = sales_df["amount"].sum()     if not sales_df.empty     else 0.0
    total_cogs    = purchases_df["amount"].sum() if not purchases_df.empty else 0.0
    total_opex    = expenses_df["amount"].sum()  if not expenses_df.empty  else 0.0

    if not labor_df.empty and {"rate", "hours"}.issubset(labor_df.columns):
        ldf           = labor_df.copy()
        ldf["cost"]   = ldf["hours"] * ldf["rate"]
        total_labor   = ldf["cost"].sum()
        total_hours   = ldf["hours"].sum()
        overtime_rows = ldf[ldf["hours"] > BENCHMARKS["overtime_threshold_hours"]]
    else:
        ldf           = pd.DataFrame()
        total_labor   = 0.0
        total_hours   = 0.0
        overtime_rows = pd.DataFrame()

    gross_profit      = total_revenue - total_cogs
    gross_margin_pct  = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    total_operating   = total_opex + total_labor
    net_profit        = gross_profit - total_operating
    net_margin_pct    = (net_profit  / total_revenue * 100)  if total_revenue > 0 else 0.0
    labor_pct         = (total_labor / total_revenue * 100)  if total_revenue > 0 else 0.0
    breakeven_revenue = (total_operating / (gross_margin_pct / 100)) if gross_margin_pct > 0 else 0.0

    rev_by_cat   = (sales_df.groupby("category")["amount"].sum()
                   .sort_values(ascending=False).to_dict() if not sales_df.empty else {})
    cogs_by_cat  = (purchases_df.groupby("category")["amount"].sum()
                   .sort_values(ascending=False).to_dict() if not purchases_df.empty else {})
    opex_by_cat  = (expenses_df.groupby("category")["amount"].sum()
                   .sort_values(ascending=False).to_dict() if not expenses_df.empty else {})
    labor_by_emp = (ldf.groupby("employee")["cost"].sum()
                   .sort_values(ascending=False).to_dict()
                   if not ldf.empty and "cost" in ldf.columns else {})

    monthly = pd.DataFrame()
    if not sales_df.empty:
        ms = sales_df.copy()
        ms["month"] = pd.to_datetime(ms["date"]).dt.to_period("M").astype(str)
        monthly = ms.groupby("month")["amount"].sum().reset_index().rename(
            columns={"amount": "revenue"})

    for src, col in [(purchases_df, "cogs"), (expenses_df, "opex")]:
        if not src.empty and not monthly.empty:
            tmp = src.copy()
            tmp["month"] = pd.to_datetime(tmp["date"]).dt.to_period("M").astype(str)
            agg = tmp.groupby("month")["amount"].sum().reset_index().rename(
                columns={"amount": col})
            monthly = monthly.merge(agg, on="month", how="left").fillna(0)

    if not ldf.empty and "cost" in ldf.columns and not monthly.empty:
        ml = ldf.copy()
        ml["month"] = pd.to_datetime(ml["date"]).dt.to_period("M").astype(str)
        mlg = ml.groupby("month")["cost"].sum().reset_index().rename(columns={"cost": "labor"})
        monthly = monthly.merge(mlg, on="month", how="left").fillna(0)

    if not monthly.empty and "cogs" in monthly.columns:
        monthly["gross_profit"]     = monthly["revenue"] - monthly["cogs"]
        labor_col                   = monthly.get("labor", pd.Series(0, index=monthly.index))
        opex_col                    = monthly.get("opex",  pd.Series(0, index=monthly.index))
        monthly["net_profit"]       = monthly["gross_profit"] - opex_col - labor_col
        monthly["gross_margin_pct"] = (monthly["gross_profit"] / monthly["revenue"] * 100).round(1)

    date_range_days = 1
    if not sales_df.empty:
        date_range_days = max(
            (pd.to_datetime(sales_df["date"]).max()
             - pd.to_datetime(sales_df["date"]).min()).days, 1,
        )

    return {
        "total_revenue":     round(total_revenue, 2),
        "total_cogs":        round(total_cogs, 2),
        "gross_profit":      round(gross_profit, 2),
        "gross_margin_pct":  round(gross_margin_pct, 1),
        "total_opex":        round(total_opex, 2),
        "total_labor":       round(total_labor, 2),
        "total_operating":   round(total_operating, 2),
        "net_profit":        round(net_profit, 2),
        "net_margin_pct":    round(net_margin_pct, 1),
        "labor_pct":         round(labor_pct, 1),
        "total_hours":       round(total_hours, 1),
        "breakeven_revenue": round(breakeven_revenue, 2),
        "overtime_count":    len(overtime_rows),
        "overtime_pct":      round(len(overtime_rows) / len(ldf) * 100, 1) if not ldf.empty else 0.0,
        "rev_by_cat":        rev_by_cat,
        "cogs_by_cat":       cogs_by_cat,
        "opex_by_cat":       opex_by_cat,
        "labor_by_emp":      labor_by_emp,
        "monthly":           monthly,
        "daily_avg_revenue": round(total_revenue / date_range_days, 2),
        "date_range_days":   date_range_days,
    }


def calculate_pnl() -> dict:
    """Session-state wrapper: runs _compute_pnl and stores result + timestamp."""
    pnl = _compute_pnl(
        st.session_state.df_sales,
        st.session_state.df_purchases,
        st.session_state.df_expenses,
        st.session_state.df_labor,
    )
    st.session_state.pnl_cache      = pnl
    st.session_state.last_calculated = datetime.datetime.now().strftime("%b %d, %H:%M")
    return pnl


# ────────────────────────────────────────────────
# AI HELPERS
# ────────────────────────────────────────────────
def build_data_context() -> str:
    """Serialise P&L cache into a compact text block for the AI system prompt."""
    pnl = st.session_state.pnl_cache
    if not pnl:
        return "No financial data loaded yet."

    biz = st.session_state.business_type or "Small Business"
    ctx = (
        f"=== {biz.upper()} — P&L SNAPSHOT ===\n"
        f"Period: {pnl.get('date_range_days',0)} days  |  "
        f"Daily Avg Revenue: ${pnl.get('daily_avg_revenue',0):,.2f}\n\n"
        f"REVENUE:            ${pnl['total_revenue']:,.2f}\n"
        f"COGS:               ${pnl['total_cogs']:,.2f}\n"
        f"GROSS PROFIT:       ${pnl['gross_profit']:,.2f}  ({pnl['gross_margin_pct']:.1f}%)\n"
        f"OPERATING EXPENSES: ${pnl['total_opex']:,.2f}\n"
        f"LABOR COSTS:        ${pnl['total_labor']:,.2f}  ({pnl['labor_pct']:.1f}% of revenue)\n"
        f"NET PROFIT:         ${pnl['net_profit']:,.2f}  ({pnl['net_margin_pct']:.1f}%)\n"
        f"BREAKEVEN REVENUE:  ${pnl['breakeven_revenue']:,.2f}\n"
        f"OVERTIME SHIFTS:    {pnl['overtime_count']} ({pnl['overtime_pct']:.1f}%)\n\n"
        f"BENCHMARKS → GM ≥ {BENCHMARKS['gross_margin_pct']}%  |  "
        f"Labor ≤ {BENCHMARKS['labor_pct_of_revenue']}%  |  "
        f"Net ≥ {BENCHMARKS['net_margin_pct']}%\n"
    )

    def _section(title: str, items: dict) -> str:
        if not items:
            return ""
        out = f"\n{title}:\n"
        for k, v in items.items():
            out += f"  {k}: ${v:,.2f}\n"
        return out

    ctx += _section("REVENUE BY CATEGORY",   pnl.get("rev_by_cat",   {}))
    ctx += _section("COGS BY CATEGORY",       pnl.get("cogs_by_cat",  {}))
    ctx += _section("EXPENSES BY CATEGORY",   pnl.get("opex_by_cat",  {}))
    ctx += _section("LABOR COST BY EMPLOYEE", pnl.get("labor_by_emp", {}))

    monthly = pnl.get("monthly", pd.DataFrame())
    if not monthly.empty:
        ctx += "\nMONTHLY TREND:\n"
        for _, row in monthly.iterrows():
            line = f"  {row['month']}: Rev=${row.get('revenue',0):,.0f}"
            if "gross_margin_pct" in row:
                line += f" | GM={row['gross_margin_pct']:.1f}%"
            if "net_profit" in row:
                line += f" | Net=${row['net_profit']:,.0f}"
            ctx += line + "\n"

    return ctx


SYSTEM_PROMPT = """You are ProfitPulse AI — a plain-speaking virtual CFO for small businesses.

RULES:
1. Use ACTUAL numbers from the user's data. Never invent figures.
2. Compare metrics to the provided benchmarks; flag deviations clearly.
3. Give specific, actionable recommendations with estimated dollar impact.
4. Use short bullets or numbered steps — no walls of text.
5. Gross margin below 40% = critical: suggest pricing or sourcing fixes.
6. Labor above 25% of revenue = flag: suggest scheduling or staffing tweaks.
7. Overtime: quantify extra cost vs. hiring part-time help.
8. Identify highest- and lowest-margin product/service categories.
9. Spot seasonal trends and recommend preparation actions.
10. Keep replies under 400 words unless user explicitly asks for deep analysis.
11. Close EVERY response with exactly ONE bolded line: ⚡ Quick Win This Week: <action>"""


def save_all_user_data():
    """Save all user data to database."""
    import users as user_db
    username = st.session_state.get("username", "")
    if not username or username == "admin":
        return  # Don't save demo data
    
    user_db.save_user_data(username, "sales", st.session_state.df_sales)
    user_db.save_user_data(username, "purchases", st.session_state.df_purchases)
    user_db.save_user_data(username, "expenses", st.session_state.df_expenses)
    user_db.save_user_data(username, "labor", st.session_state.df_labor)
    
    # Save business type
    if st.session_state.get("business_type"):
        user_db.save_user_setting(username, "business_type", st.session_state.business_type)


def call_ai(user_query: str) -> str:
    """Call Venice AI with full P&L context. Returns response string."""
    api_key = get_api_key()
    if not api_key:
        pnl = st.session_state.pnl_cache
        return (
            "**⚠ Venice API key not configured.**\n\n"
            "Add `VENICE_API_KEY=your_key` to your `.env` file or Streamlit Cloud secrets to enable AI advice.\n\n"
            "**Snapshot from your data:**\n"
            f"- Gross margin: **{pnl.get('gross_margin_pct','N/A')}%** "
            f"(target ≥ {BENCHMARKS['gross_margin_pct']}%)\n"
            f"- Labor % of revenue: **{pnl.get('labor_pct','N/A')}%** "
            f"(target ≤ {BENCHMARKS['labor_pct_of_revenue']}%)\n"
            f"- Net margin: **{pnl.get('net_margin_pct','N/A')}%** "
            f"(target ≥ {BENCHMARKS['net_margin_pct']}%)\n\n"
            "**⚡ Quick Win This Week:** Review your largest expense category and find one cut."
        )

    messages = [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": f"Here is my current business data:\n\n{build_data_context()}"},
        {"role": "assistant", "content": "Reviewed. What would you like to analyse?"},
    ]
    for msg in st.session_state.chat_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_query})

    try:
        client   = OpenAI(api_key=api_key, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=800, temperature=0.4,
        )
        return response.choices[0].message.content
    except Exception as exc:
        err = str(exc)
        if "401" in err or "auth" in err.lower():
            return "**Auth failed.** Your Venice API key may be invalid or expired."
        if "429" in err:
            return "**Rate limited.** Please wait a moment and try again."
        if "model" in err.lower():
            return f"**Model error.** `{MODEL}` may be unavailable on Venice."
        return f"**AI Error:** {err}\n\nCheck your internet connection and API key."


def _ai_pulse_prompt() -> str:
    """Build a dynamic, data-driven sidebar AI Pulse prompt."""
    pnl = st.session_state.pnl_cache
    if not pnl:
        return (
            "No data loaded yet. Give me a quick motivational tip "
            "for small business profitability while I get set up."
        )
    flags = []
    if pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"]:
        flags.append(
            f"gross margin is {pnl['gross_margin_pct']:.1f}% "
            f"(target ≥ {BENCHMARKS['gross_margin_pct']}%)"
        )
    if pnl["labor_pct"] > BENCHMARKS["labor_pct_of_revenue"]:
        flags.append(
            f"labor is {pnl['labor_pct']:.1f}% of revenue "
            f"(target ≤ {BENCHMARKS['labor_pct_of_revenue']}%)"
        )
    if pnl["overtime_count"] > 0:
        flags.append(f"{pnl['overtime_count']} overtime shifts detected")
    if pnl["net_margin_pct"] < 5:
        flags.append(f"net margin critically low at {pnl['net_margin_pct']:.1f}%")

    flag_str = "; ".join(flags) if flags else "metrics look reasonable overall"
    return (
        f"Quick health check: {flag_str}. "
        "Give me a 3-bullet summary of the biggest profit risk RIGHT NOW "
        "and ONE specific action I can take THIS WEEK to improve it, "
        "including a rough dollar-impact estimate."
    )


# ────────────────────────────────────────────────
# ONBOARDING WIZARD
# ────────────────────────────────────────────────
def onboarding_wizard() -> None:
    st.markdown("""
    <div style="text-align:center; padding:4rem 1rem 2rem;">
        <span style="font-size:4rem;">◈</span>
        <h1 style="font-size:2.4rem; margin:1rem 0 0.5rem;">Welcome to ProfitPulse</h1>
        <p style="font-size:1.1rem; color:#64748b; max-width:560px; margin:0 auto 2.5rem;">
            Let's get your dashboard ready in under 60 seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.get("onboarding_step", 0)
    st.progress((step + 1) / 2, text=f"Step {step + 1} of 2")

    if step == 0:
        st.markdown("### Step 1 — What kind of business do you run?")
        biz_type = st.selectbox(
            "Business Type", BUSINESS_TYPES, index=0,
            help="Tailors demo data and AI advice to your industry.",
        )
        if st.button("Continue →", type="primary", use_container_width=True):
            st.session_state.business_type   = biz_type
            st.session_state.onboarding_step = 1
            st.rerun()

    elif step == 1:
        biz = st.session_state.business_type
        st.markdown(f"### Step 2 — Load data for your **{biz}**")
        col1, col2 = st.columns([3, 2])
        with col1:
            st.info(
                f"Load **6 months of realistic {biz} demo data** "
                "so you can explore the full dashboard right away?"
            )
            if st.button("✅ Yes — Load Demo Data", type="primary", use_container_width=True):
                with st.spinner("Generating demo data…"):
                    demo = generate_demo_data(6, biz)
                    st.session_state.df_sales     = demo["sales"]
                    st.session_state.df_purchases = demo["purchases"]
                    st.session_state.df_expenses  = demo["expenses"]
                    st.session_state.df_labor     = demo["labor"]
                    save_all_user_data()
                st.session_state.onboarded        = True
                st.session_state.onboarding_step  = None
                st.toast("Demo data loaded — welcome to ProfitPulse! 🎉", icon="✅")
                st.rerun()
            if st.button("📁 No thanks — I'll upload my own data", use_container_width=True):
                st.session_state.onboarded       = True
                st.session_state.onboarding_step = None
                st.rerun()
        with col2:
            st.markdown("""
            **What you get with demo data:**
            - 6 months of sales, purchases, expenses & labor
            - Pre-populated P&L dashboard
            - Instant AI insights you can explore immediately
            - Overwrite anytime with your real data
            """)


# ────────────────────────────────────────────────
# PAGE: DATA INPUT
# ────────────────────────────────────────────────
def page_data_input() -> None:
    st.markdown('<div class="page-header">Data Input</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Upload CSVs, add transactions manually, or load demo data</div>',
        unsafe_allow_html=True,
    )

    biz = st.session_state.business_type or "Auto Repair"
    if st.session_state.business_type:
        st.caption(f"Configured for: **{biz}**")

    col_demo, _ = st.columns([1, 2])
    with col_demo:
        if st.button(
            f"⚡ Reload {biz} Demo (6 months)", use_container_width=True, type="primary",
            help="Replace all current data with fresh demo data for your business type.",
        ):
            with st.spinner("Generating demo data…"):
                demo = generate_demo_data(6, biz)
                st.session_state.df_sales     = demo["sales"]
                st.session_state.df_purchases = demo["purchases"]
                st.session_state.df_expenses  = demo["expenses"]
                st.session_state.df_labor     = demo["labor"]
                save_all_user_data()
            st.toast("Demo data loaded!", icon="✅")
            st.rerun()

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── CSV Uploaders ───────────────────────────
    st.markdown("##### Upload CSVs")
    st.caption(
        "Sales / Purchases / Expenses: `date, category, amount, description`  ·  "
        "Labor: `date, employee, hours, rate, description`"
    )
    upload_specs = [
        ("up_sales",  "df_sales",    ["date","category","amount"], "Sales"),
        ("up_purch",  "df_purchases",["date","category","amount"], "Purchases"),
        ("up_exp",    "df_expenses", ["date","category","amount"], "Expenses"),
        ("up_labor",  "df_labor",    ["date","employee","hours","rate"], "Labor"),
    ]
    cols = st.columns(4)
    for col, (key, state_key, required_cols, label) in zip(cols, upload_specs):
        with col:
            f = st.file_uploader(label, type="csv", key=key)
            if f:
                parsed = parse_csv(f, required_cols, label)
                if not parsed.empty:
                    st.session_state[state_key] = parsed
                    save_all_user_data()
                    st.toast(f"{label}: {len(parsed):,} rows loaded", icon="📂")

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    # ── Receipt Scanner ─────────────────────────
    st.markdown("##### 📷 Add from Receipt")
    st.caption("Upload a receipt photo from your phone or computer, then add to expenses")
    
    with st.expander("Open Receipt Scanner", expanded=False):
        uploaded_file = st.file_uploader(
            "Upload receipt (photo or PDF)",
            type=["png", "jpg", "jpeg", "pdf"],
            help="Take a photo of your receipt and upload it here"
        )
        
        if uploaded_file is not None:
            # Show preview if image
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, caption="Receipt preview", use_container_width=True)
            else:
                st.info(f"PDF uploaded: {uploaded_file.name}")
            
            st.markdown("---")
            st.markdown("**Enter details from the receipt:**")
            
            with st.form("receipt_expense_form", clear_on_submit=True):
                r1, r2 = st.columns(2)
                with r1:
                    rec_vendor = st.text_input("Vendor / Store", placeholder="e.g., Home Depot, Starbucks")
                with r2:
                    rec_date = st.date_input("Date", value=datetime.date.today())
                
                r3, r4 = st.columns(2)
                with r3:
                    rec_amount = st.number_input("Total Amount ($)", min_value=0.0, step=0.01)
                with r4:
                    rec_category = st.selectbox("Category", EXPENSE_CATEGORIES)
                
                rec_desc = st.text_input("Description (optional)", placeholder="What was this for?")
                
                if st.form_submit_button("💾 Save to Expenses", type="primary", use_container_width=True):
                    if rec_amount <= 0:
                        st.warning("Please enter a valid amount")
                    else:
                        # Build expense row
                        desc_text = f"Receipt: {rec_vendor}"
                        if rec_desc:
                            desc_text += f" - {rec_desc}"
                        
                        row = pd.DataFrame([{
                            "date": str(rec_date),
                            "category": rec_category,
                            "amount": rec_amount,
                            "description": desc_text
                        }])
                        
                        # Append to expenses
                        if st.session_state.df_expenses.empty:
                            st.session_state.df_expenses = row
                        else:
                            st.session_state.df_expenses = pd.concat(
                                [st.session_state.df_expenses, row], ignore_index=True)
                        
                        save_all_user_data()
                        st.toast(f"Receipt saved: {rec_vendor} - ${rec_amount:,.2f}", icon="✅")
                        st.rerun()

    # ── Manual Entry ────────────────────────────
    st.markdown("##### Or Enter Transactions Manually")
    tab_s, tab_p, tab_e, tab_l = st.tabs(
        ["➕ Sale", "➕ Purchase", "➕ Expense", "➕ Labor Shift"]
    )

    with tab_s:
        with st.form("add_sale", clear_on_submit=True):
            r1, r2, r3 = st.columns(3)
            s_date = r1.date_input("Date", value=datetime.date.today())
            s_cat  = r2.text_input("Category", placeholder="Oil Change",
                                   help="Service or product sold")
            s_amt  = r3.number_input("Amount ($)", min_value=0.0, step=1.0)
            s_desc = st.text_input("Description (optional)")
            if st.form_submit_button("Add Sale", use_container_width=True, type="primary"):
                if not s_cat.strip():
                    st.warning("Please enter a category.")
                else:
                    row = pd.DataFrame([{"date": str(s_date), "category": s_cat.strip(),
                                         "amount": s_amt, "description": s_desc}])
                    st.session_state.df_sales = pd.concat(
                        [st.session_state.df_sales, row], ignore_index=True)
                    save_all_user_data()
                    st.toast("Sale added ✓", icon="✅")

    with tab_p:
        with st.form("add_purchase", clear_on_submit=True):
            r1, r2, r3 = st.columns(3)
            p_date = r1.date_input("Date", value=datetime.date.today())
            p_cat  = r2.text_input("Category", placeholder="Parts Wholesale",
                                   help="What you bought for resale or production")
            p_amt  = r3.number_input("Amount ($)", min_value=0.0, step=1.0)
            p_desc = st.text_input("Description (optional)")
            if st.form_submit_button("Add Purchase", use_container_width=True, type="primary"):
                if not p_cat.strip():
                    st.warning("Please enter a category.")
                else:
                    row = pd.DataFrame([{"date": str(p_date), "category": p_cat.strip(),
                                         "amount": p_amt, "description": p_desc}])
                    st.session_state.df_purchases = pd.concat(
                        [st.session_state.df_purchases, row], ignore_index=True)
                    save_all_user_data()
                    st.toast("Purchase added ✓", icon="✅")

    with tab_e:
        with st.form("add_expense", clear_on_submit=True):
            r1, r2, r3 = st.columns(3)
            e_date = r1.date_input("Date", value=datetime.date.today())
            e_cat  = r2.selectbox("Category", EXPENSE_CATEGORIES,
                                  help="Choose the closest operating expense type")
            e_amt  = r3.number_input("Amount ($)", min_value=0.0, step=1.0)
            e_desc = st.text_input("Description (optional)")
            if st.form_submit_button("Add Expense", use_container_width=True, type="primary"):
                row = pd.DataFrame([{"date": str(e_date), "category": e_cat,
                                     "amount": e_amt, "description": e_desc}])
                st.session_state.df_expenses = pd.concat(
                    [st.session_state.df_expenses, row], ignore_index=True)
                save_all_user_data()
                st.toast("Expense added ✓", icon="✅")

    with tab_l:
        with st.form("add_labor", clear_on_submit=True):
            r1, r2, r3, r4 = st.columns(4)
            l_date = r1.date_input("Date", value=datetime.date.today())
            l_emp  = r2.text_input("Employee", placeholder="Name")
            l_hrs  = r3.number_input(
                "Hours", min_value=0.0, step=0.5, value=8.0,
                help=f"Shifts over {BENCHMARKS['overtime_threshold_hours']}h flagged as overtime",
            )
            l_rate = r4.number_input("Rate $/hr", min_value=0.0, step=0.5, value=20.0)
            l_desc = st.text_input("Description", placeholder="Regular shift")
            if st.form_submit_button("Add Shift", use_container_width=True, type="primary"):
                if not l_emp.strip():
                    st.warning("Please enter an employee name.")
                else:
                    row = pd.DataFrame([{"date": str(l_date), "employee": l_emp.strip(),
                                         "hours": l_hrs, "rate": l_rate, "description": l_desc}])
                    st.session_state.df_labor = pd.concat(
                        [st.session_state.df_labor, row], ignore_index=True)
                    save_all_user_data()
                    st.toast("Shift added ✓", icon="✅")

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sales rows",    f"{len(st.session_state.df_sales):,}")
    m2.metric("Purchase rows", f"{len(st.session_state.df_purchases):,}")
    m3.metric("Expense rows",  f"{len(st.session_state.df_expenses):,}")
    m4.metric("Labor rows",    f"{len(st.session_state.df_labor):,}")


# ────────────────────────────────────────────────
# PAGE: DASHBOARD
# NEW: Recalculate button, last-updated timestamp, What-If simulator
# ────────────────────────────────────────────────
def page_dashboard() -> None:
    if st.session_state.df_sales.empty:
        st.info("No data loaded yet. Head to **Data Input** or load the demo.")
        return

    # Header row with refresh control
    hdr_col, ts_col, btn_col = st.columns([3, 2, 1])
    with hdr_col:
        biz_label = st.session_state.business_type or "Business"
        st.markdown('<div class="page-header">Analytics</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="page-sub">Welcome back, <strong>{biz_label}</strong>'
            f' — your deeper business performance workspace</div>',
            unsafe_allow_html=True,
        )
    with ts_col:
        if st.session_state.last_calculated:
            st.caption(f"Last calculated: **{st.session_state.last_calculated}**")
    with btn_col:
        if st.button("🔄 Recalculate", use_container_width=True,
                     help="Re-run P&L with latest data"):
            _compute_pnl.clear()   # bust the cache so next call recomputes
            st.rerun()

    pnl = calculate_pnl()

    # ── Natural Language Summary ─────────────────
    if pnl["total_revenue"] > 0:
        st.markdown("### 💡 Business Snapshot")
        cols = st.columns(len([k for k in [
            pnl["net_profit"] > 0 or pnl["net_profit"] < 0,
            bool(pnl["rev_by_cat"]),
            pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"],
            pnl["labor_pct"] > BENCHMARKS["labor_pct_of_revenue"]
        ] if k]))
        
        col_idx = 0
        if pnl["net_profit"] > 0:
            with cols[col_idx]: st.metric("Status", "✅ Profitable")
            col_idx += 1
        elif pnl["net_profit"] < 0:
            with cols[col_idx]: st.metric("Status", "⚠️ At a loss")
            col_idx += 1
        
        if pnl["rev_by_cat"]:
            top_cat = max(pnl["rev_by_cat"].items(), key=lambda x: x[1])
            with cols[col_idx]: st.metric("Top Category", top_cat[0])
            col_idx += 1
        
        if pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"]:
            with cols[col_idx]: st.metric("Margin", f"⚠️ {pnl['gross_margin_pct']:.1f}%")
            col_idx += 1
        
        if pnl["labor_pct"] > BENCHMARKS["labor_pct_of_revenue"]:
            with cols[col_idx]: st.metric("Labor", f"⚠️ {pnl['labor_pct']:.1f}%")
        
        st.markdown("---")

    # ── KPI Cards ───────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        pp_card("Revenue", f"${pnl['total_revenue']:,.0f}",
                f"${pnl['daily_avg_revenue']:,.0f}/day avg", "accent")
    with k2:
        theme = "good" if pnl["gross_margin_pct"] >= BENCHMARKS["gross_margin_pct"] else "bad"
        pp_card("Gross Margin", f"{pnl['gross_margin_pct']:.1f}%",
                f"Target ≥ {BENCHMARKS['gross_margin_pct']}%", theme)
    with k3:
        theme = "good" if pnl["net_profit"] > 0 else "bad"
        pp_card("Net Profit", f"${pnl['net_profit']:,.0f}",
                f"{pnl['net_margin_pct']:.1f}% margin", theme)
    with k4:
        theme = "good" if pnl["labor_pct"] <= BENCHMARKS["labor_pct_of_revenue"] else "warn"
        pp_card("Labor", f"{pnl['labor_pct']:.1f}%",
                f"of revenue · target ≤ {BENCHMARKS['labor_pct_of_revenue']}%", theme)
    with k5:
        pp_card("Breakeven", f"${pnl['breakeven_revenue']:,.0f}",
                f"over {pnl['date_range_days']}-day period", "default")

    # ── Alerts ──────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"]:
        pp_alert(
            f"⚠ Gross margin {pnl['gross_margin_pct']:.1f}% is below the "
            f"{BENCHMARKS['gross_margin_pct']}% benchmark — review pricing or COGS.", "warn"
        )
    if pnl["labor_pct"] > BENCHMARKS["labor_pct_of_revenue"]:
        pp_alert(
            f"⚠ Labor at {pnl['labor_pct']:.1f}% of revenue exceeds the "
            f"{BENCHMARKS['labor_pct_of_revenue']}% target — review scheduling.", "warn"
        )
    if pnl["overtime_count"] > 0:
        # Rough overtime premium estimate: flag the extra cost
        ot_est = pnl["total_labor"] * (pnl["overtime_pct"] / 100) * 0.5
        pp_alert(
            f"🔴 {pnl['overtime_count']} overtime shifts ({pnl['overtime_pct']:.1f}%) — "
            f"estimated extra cost ~${ot_est:,.0f}. Consider adjusting shift schedules.", "bad"
        )
    if pnl["net_margin_pct"] < 5:
        pp_alert(
            f"🔴 Net margin critically low at {pnl['net_margin_pct']:.1f}% — "
            "immediate action required on costs or pricing.", "bad"
        )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    # ── What-If Simulator ───────────────────────
    with st.expander("🔮 What-If Simulator — Test Scenarios", expanded=False):
        st.caption("Adjust sliders to model the profit impact of business changes.")
        colA, colB, colC = st.columns(3)
        with colA:
            rev_change   = st.slider("Revenue change (%)",          -30, 50,  0, step=5, key="sim_rev",
                                     help="e.g. +10% from raising prices or winning more customers")
        with colB:
            cost_change  = st.slider("COGS & Expenses change (%)",  -20, 30,  0, step=5, key="sim_cost",
                                     help="e.g. -10% from renegotiating supplier contracts")
        with colC:
            labor_change = st.slider("Labor cost change (%)",       -25, 25,  0, step=5, key="sim_labor",
                                     help="e.g. -15% from reducing overtime shifts")

        sim_rev   = pnl["total_revenue"] * (1 + rev_change   / 100)
        sim_cogs  = pnl["total_cogs"]    * (1 + cost_change  / 100)
        sim_opex  = pnl["total_opex"]    * (1 + cost_change  / 100)
        sim_labor = pnl["total_labor"]   * (1 + labor_change / 100)
        sim_gp    = sim_rev - sim_cogs
        sim_np    = sim_gp  - (sim_opex + sim_labor)
        sim_margin = (sim_np / sim_rev * 100) if sim_rev > 0 else 0.0

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Simulated Revenue",    f"${sim_rev:,.0f}",
                   delta=f"{rev_change:+.0f}%")
        sc2.metric("Simulated Net Profit", f"${sim_np:,.0f}",
                   delta=f"${sim_np - pnl['net_profit']:+,.0f} vs now")
        sc3.metric("Simulated Net Margin", f"{sim_margin:.1f}%",
                   delta=f"{sim_margin - pnl['net_margin_pct']:+.1f}pp")

    # ── P&L Statement ───────────────────────────
    with st.expander("📋 Profit & Loss Statement", expanded=True):
        rev = pnl["total_revenue"]
        def pct_of_rev(v: float) -> str:
            return f"{(v / rev * 100):.1f}%" if rev > 0 else "—"

        pnl_row("Revenue",             rev,                   "100.0%")
        pnl_row("Cost of Goods Sold",  -pnl["total_cogs"],    pct_of_rev(pnl["total_cogs"]))
        pnl_row("Gross Profit",        pnl["gross_profit"],   f"{pnl['gross_margin_pct']:.1f}%", total=True)
        pnl_row("Operating Expenses",  -pnl["total_opex"],    pct_of_rev(pnl["total_opex"]))
        pnl_row("Labor Costs",         -pnl["total_labor"],   f"{pnl['labor_pct']:.1f}%")
        pnl_row("Net Profit",          pnl["net_profit"],     f"{pnl['net_margin_pct']:.1f}%", total=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Charts row 1 ────────────────────────────
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("##### Monthly Revenue vs COGS")
        if not pnl["monthly"].empty and "cogs" in pnl["monthly"].columns:
            m = pnl["monthly"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=m["month"], y=m["revenue"],
                                 name="Revenue", marker_color="#6366f1", marker_cornerradius=6))
            fig.add_trace(go.Bar(x=m["month"], y=m["cogs"],
                                 name="COGS",    marker_color="#475569", marker_cornerradius=6))
            if "net_profit" in m.columns:
                fig.add_trace(go.Scatter(x=m["month"], y=m["net_profit"],
                                         name="Net Profit",
                                         line=dict(color="#10b981", width=2.5)))
            fig.update_layout(**CHART_LAYOUT, barmode="group", height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Upload sales + purchases to see this chart.")

    with ch2:
        st.markdown("##### Gross Margin Trend")
        if not pnl["monthly"].empty and "gross_margin_pct" in pnl["monthly"].columns:
            m   = pnl["monthly"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m["month"], y=m["gross_margin_pct"],
                mode="lines+markers",
                line=dict(color="#6366f1", width=2.5),
                marker=dict(size=7, color="#6366f1"),
                fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
            ))
            fig.add_hline(
                y=BENCHMARKS["gross_margin_pct"],
                line_dash="dot", line_color="#ef4444", line_width=1.5,
                annotation_text=f"Target {BENCHMARKS['gross_margin_pct']}%",
                annotation_font_size=11,
            )
            fig.update_layout(**CHART_LAYOUT, height=340, yaxis_title="Gross Margin %")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("More data needed for this chart.")

    # ── Charts row 2 — Hidden behind expander ──
    with st.expander("📊 See detailed breakdowns", expanded=False):
        ch3, ch4 = st.columns(2)
        with ch3:
            st.markdown("##### Revenue by Category")
            if pnl["rev_by_cat"]:
                df_rc = pd.DataFrame(
                    list(pnl["rev_by_cat"].items()), columns=["Category", "Revenue"]
                )
                fig = px.pie(
                    df_rc, names="Category", values="Revenue", hole=0.55,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig.update_layout(**CHART_LAYOUT, height=340, showlegend=True)
                fig.update_traces(textposition="inside", textinfo="percent")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No sales data available.")

        with ch4:
            st.markdown("##### Labor Cost by Employee")
            if pnl["labor_by_emp"]:
                df_le = pd.DataFrame(
                    list(pnl["labor_by_emp"].items()), columns=["Employee", "Cost"]
                )
                fig = px.bar(
                    df_le.sort_values("Cost", ascending=True),
                    x="Cost", y="Employee", orientation="h",
                    color_discrete_sequence=["#6366f1"],
                )
                fig.update_layout(**CHART_LAYOUT, height=340)
                fig.update_traces(marker_cornerradius=6)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No labor data available.")

        # ── Operating Expenses breakdown ────────────
        if pnl["opex_by_cat"]:
            st.markdown("##### Operating Expenses Breakdown")
            df_oc = pd.DataFrame(
                list(pnl["opex_by_cat"].items()), columns=["Category", "Amount"]
            )
            fig = px.bar(
                df_oc.sort_values("Amount", ascending=True),
                x="Amount", y="Category", orientation="h",
                color_discrete_sequence=["#f59e0b"],
            )
            fig.update_layout(**CHART_LAYOUT, height=300)
            fig.update_traces(marker_cornerradius=6)
            st.plotly_chart(fig, use_container_width=True)


def page_overview() -> None:
    if st.session_state.df_sales.empty:
        st.info("No data loaded yet. Head to **Data Input** or load the demo.")
        return

    pnl = calculate_pnl()
    tax = build_tax_snapshot(pnl)
    complete = has_complete_access()
    biz_label = st.session_state.business_type or "Business"

    hdr_col, ts_col, plan_col = st.columns([3, 2, 1.4])
    with hdr_col:
        st.markdown('<div class="page-header">Overview</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="page-sub">Welcome back, <strong>{biz_label}</strong>'
            ' — your business health and tax picture in one place</div>',
            unsafe_allow_html=True,
        )
    with ts_col:
        if st.session_state.last_calculated:
            st.caption(f"Last calculated: **{st.session_state.last_calculated}**")
    with plan_col:
        st.caption(f"Plan: **{current_plan_label()}**")

    # ── Business Status Strip ───────────────────────
    status_messages = []
    if pnl["net_profit"] > 0:
        status_messages.append(("✅", "You're profitable this month", "good"))
    elif pnl["net_profit"] < 0:
        status_messages.append(("⚠️", "You're currently running at a loss", "warn"))
    
    if pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"]:
        status_messages.append(("⚠️", "Margins are tight — review expenses", "warn"))
    
    if tax and complete:
        schedule = tax.get("sales_tax", {}).get("schedule", [])
        if schedule:
            next_due = schedule[0].get("due_window", "")
            if next_due:
                status_messages.append(("📅", f"Tax deadline: {next_due}", "info"))
    
    if status_messages:
        status_html = '<div class="status-strip"><strong>Business Status</strong>'
        for emoji, msg, _ in status_messages:
            status_html += f'<span>{emoji} {msg}</span><br>'
        status_html = status_html.rstrip('<br>') + '</div>'
        st.markdown(status_html, unsafe_allow_html=True)
    # ── End Status Strip ───────────────────────────

    # ── Simplified KPI Cards (3 primary + expander) ─
    k1, k2, k3 = st.columns(3)
    with k1:
        pp_card("💰 Money In", f"${pnl['total_revenue']:,.0f}", f"${pnl['daily_avg_revenue']:,.0f}/day avg", "accent")
    with k2:
        theme = "good" if pnl["net_profit"] > 0 else "bad"
        pp_card("💎 Money Kept", f"${pnl['net_profit']:,.0f}", f"{pnl['net_margin_pct']:.1f}% margin", theme)
    with k3:
        if tax and complete:
            pp_card(
                "🏛️ Tax Set-Aside",
                f"${tax['sales_tax']['filing_period_sales_tax']:,.0f}",
                tax["sales_tax"]["filing_frequency_label"],
                "warn",
            )
        elif tax:
            pp_card(
                "🏛️ Tax Set-Aside",
                f"${tax['sales_tax']['filing_period_sales_tax']:,.0f}*",
                "Preview in Starter",
                "default",
            )
        else:
            pp_card("🏛️ Tax Set-Aside", "—", "Add data to calculate", "default")
    
    with st.expander("📊 Show more metrics"):
        m1, m2, m3 = st.columns(3)
        with m1:
            pp_card("Expenses", f"${pnl['total_operating']:,.0f}", "Operating + labor", "default")
        with m2:
            theme = "good" if pnl["gross_margin_pct"] >= BENCHMARKS["gross_margin_pct"] else "warn"
            pp_card("Gross Margin", f"{pnl['gross_margin_pct']:.1f}%", f"Target ≥ {BENCHMARKS['gross_margin_pct']}%", theme)
        with m3:
            if tax and complete:
                next_deadline = tax.get("sales_tax", {}).get("schedule", [{}])[0].get("due_window", "N/A")
                pp_card("Tax Deadlines", next_deadline, "Next filing window", "info")
            else:
                pp_card("Tax Deadlines", "—", "Complete plan to view", "default")
    # ── End KPI Cards ─────────────────────────────

    # ── Quick Actions ───────────────────────────────
    st.markdown("### ⚡ Quick Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("📁 Add Data", use_container_width=True, key="qa_overview_data"):
            jump_to("Data Input")
    with qa2:
        if st.button("🤖 Ask AI", use_container_width=True, key="qa_overview_ai"):
            jump_to("AI Advisor")
    with qa3:
        if st.button("📤 Export Report", use_container_width=True, key="qa_overview_export"):
            jump_to("Export")
    # ── End Quick Actions ───────────────────────────

    # ── Smart Insights (auto-calculated, free) ──────
    insights = []
    
    # Revenue trend insight
    if not pnl["monthly"].empty and len(pnl["monthly"]) >= 2:
        recent = pnl["monthly"].iloc[-1]["revenue"]
        prev = pnl["monthly"].iloc[-2]["revenue"]
        if prev > 0:
            change = ((recent - prev) / prev) * 100
            if change > 10:
                insights.append(("📈", f"Revenue up {change:.0f}% vs last month", "good"))
            elif change < -10:
                insights.append(("📉", f"Revenue down {abs(change):.0f}% vs last month", "warn"))
    
    # Margin insight
    if pnl["gross_margin_pct"] < 30:
        insights.append(("⚠️", f"Gross margin at {pnl['gross_margin_pct']:.1f}% — target is 30%+", "warn"))
    elif pnl["gross_margin_pct"] >= 40:
        insights.append(("✅", f"Strong margin at {pnl['gross_margin_pct']:.1f}%", "good"))
    
    # Expense insight
    if not st.session_state.df_expenses.empty:
        top_expense = st.session_state.df_expenses.groupby("category")["amount"].sum().idxmax()
        top_amount = st.session_state.df_expenses.groupby("category")["amount"].sum().max()
        insights.append(("💳", f"Largest expense: {top_expense} (${top_amount:,.0f})", "info"))
    
    # Profitability insight
    if pnl["net_profit"] > 0:
        insights.append(("💰", f"Net profit: ${pnl['net_profit']:,.0f} this month", "good"))
    elif pnl["net_profit"] < 0:
        insights.append(("🔴", f"Operating at loss: -${abs(pnl['net_profit']):,.0f}", "warn"))
    
    # Tax insight
    if tax and complete:
        if tax["sales_tax"]["filing_period_sales_tax"] > 0:
            insights.append(("🏛️", f"Sales tax due: ${tax['sales_tax']['filing_period_sales_tax']:,.0f}", "info"))
    
    if insights:
        st.markdown("### 🤖 Smart Insights")
        for emoji, text, _ in insights:
            st.markdown(f"{emoji} {text}")
        st.caption("💡 Want deeper analysis?")
        if st.button("Generate AI Insight →", key="generate_ai_insight"):
            if not st.session_state.pnl_cache:
                calculate_pnl()
            with st.spinner("Analyzing..."):
                insight = call_ai(_ai_pulse_prompt())
            st.markdown(insight)
    # ── End Smart Insights ─────────────────────────

    left, right = st.columns([1.8, 1], gap="large")
    with left:
        st.markdown("##### Performance trend")
        if not pnl["monthly"].empty:
            monthly = pnl["monthly"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly["month"],
                y=monthly["revenue"],
                name="Revenue",
                marker_color="#6366f1",
                marker_cornerradius=6,
            ))
            if "net_profit" in monthly.columns:
                fig.add_trace(go.Scatter(
                    x=monthly["month"],
                    y=monthly["net_profit"],
                    name="Net Profit",
                    line=dict(color="#10b981", width=2.5),
                ))
            fig.update_layout(**CHART_LAYOUT, barmode="group", height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Load more data to unlock the overview trend chart.")

        panel_a, panel_b, panel_c = st.columns(3)
        with panel_a:
            st.markdown("##### 📊 Continue to Analytics")
            if st.button("Open Analytics →", use_container_width=True, key="overview_to_analytics"):
                jump_to("Analytics")
            st.caption(f"{len(st.session_state.df_sales):,} transactions · {pnl['net_margin_pct']:.1f}% margin")
        with panel_b:
            st.markdown("##### 🏛️ Continue to TaxShield")
            if tax and complete:
                if st.button("Open TaxShield →", use_container_width=True, key="overview_to_tax"):
                    jump_to("TaxShield")
                st.caption(f"{tax['sales_tax']['county']} county · ${tax['net_annual_tax']:,.0f}/year")
            elif tax:
                if st.button("Preview Complete →", use_container_width=True, key="overview_preview_tax"):
                    jump_to("Billing")
                st.caption(f"{tax['sales_tax']['filing_frequency_label']} filing")
            else:
                if st.button("Unlock TaxShield →", use_container_width=True, key="overview_unlock_tax"):
                    jump_to("Billing")
                st.caption("Add data to calculate")
        with panel_c:
            st.markdown("##### 💎 Plan benefits")
            if not complete:
                if st.button("Compare plans →", use_container_width=True, key="overview_compare"):
                    jump_to("Billing")
                st.caption("Unlock tax estimates & full analytics")
            else:
                st.caption("You have Complete access")

    with right:
        st.markdown("##### What to do next")
        
        # Dynamic action cards based on data
        if pnl["net_profit"] < 0:
            if st.button("📉 Review expenses", use_container_width=True, key="action_expenses"):
                jump_to("Analytics")
            st.caption("You're running at a loss — identify cost-cutting opportunities")
        elif pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"]:
            if st.button("📊 Check margins", use_container_width=True, key="action_margins"):
                jump_to("Analytics")
            st.caption("Your margins are below target — review pricing or costs")
        elif pnl["labor_pct"] > BENCHMARKS["labor_pct_of_revenue"]:
            if st.button("👷 Review labor", use_container_width=True, key="action_labor"):
                jump_to("Analytics")
            st.caption("Labor costs are high — check scheduling or staffing")
        
        if tax and complete:
            if st.button("🏛️ Set aside tax", use_container_width=True, key="action_tax"):
                jump_to("TaxShield")
            next_due = tax["sales_tax"]["schedule"][0].get("due_window", "soon")
            st.caption(f"Tax deadline: {next_due}")
        elif not complete:
            if st.button("🔓 Unlock TaxShield", use_container_width=True, key="action_unlock"):
                jump_to("Billing")
            st.caption("Upgrade to see tax estimates and deadlines")
        
        if st.button("➕ Add transactions", use_container_width=True, key="action_add"):
            jump_to("Data Input")
        st.caption("Keep your data fresh for accurate insights")


def page_taxshield() -> None:
    st.markdown('<div class="page-header">TaxShield</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Estimate Florida sales tax and review filing cadence without leaving ProfitPulse</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.df_sales.empty:
        st.info("Load business data first so TaxShield can estimate from your actual performance.")
        return

    if TAX_CALCULATOR is None:
        st.warning("TaxShield calculator module is not available in this environment.")
        return

    pnl = calculate_pnl()
    tax = build_tax_snapshot(pnl)
    complete = has_complete_access()

    if not tax:
        st.info("We need more revenue data before we can build a tax estimate.")
        return

    # ── TaxShield Summary ─────────────────────────
    if tax:
        st.markdown("### 💡 Tax Snapshot")
        ts1, ts2, ts3 = st.columns(3)
        with ts1: st.metric("Annual Tax", f"${tax['net_annual_tax']:,.0f}")
        with ts2: st.metric("Next Filing", tax['sales_tax']['schedule'][0]['due_window'])
        with ts3: st.metric("County Rate", f"{tax['sales_tax']['tax_rate']*100:.2f}%")
        st.markdown("---")

    if not complete:
        st.markdown("##### Included with ProfitPulse Complete")
        st.write("Starter users can preview TaxShield, but full estimates and schedules live in Complete.")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric("County-aware estimate", "Included")
        with p2:
            st.metric("Filing cadence", tax["sales_tax"]["filing_frequency_label"])
        with p3:
            st.metric("Annualized revenue basis", f"${tax['annualized_revenue']:,.0f}")
        if st.button("Upgrade to Complete", type="primary"):
            jump_to("Billing")
        st.caption("TaxShield provides planning support only. Always confirm with a CPA or the Florida Department of Revenue before filing.")
        return

    with st.sidebar:
        st.markdown("---")
        st.subheader("Tax inputs")
        tax_mod = TAX_CALCULATOR
        if tax_mod is None:
            st.warning("Tax calculator unavailable.")
            return
        counties = sorted(tax_mod.COUNTY_TAX_RATES)
        selected_county = st.selectbox(
            "Florida county",
            counties,
            index=counties.index(st.session_state.tax_county) if st.session_state.tax_county in counties else 0,
            key="tax_county_select",
        )
        structures = list(tax_mod.STRUCTURE_LABELS.keys())
        selected_structure = st.selectbox(
            "Business structure",
            structures,
            index=structures.index(st.session_state.tax_structure) if st.session_state.tax_structure in structures else 0,
            format_func=lambda value: tax_mod.STRUCTURE_LABELS[value],
            key="tax_structure_select",
        )
        filing_options = list(tax_mod.FILING_FREQUENCY_LABELS.keys())
        selected_filing = st.selectbox(
            "Sales tax filing frequency",
            filing_options,
            index=filing_options.index(st.session_state.tax_filing) if st.session_state.tax_filing in filing_options else 1,
            format_func=lambda value: tax_mod.FILING_FREQUENCY_LABELS[value],
            key="tax_filing_select",
        )
        selected_profit_margin = st.slider(
            "Estimated profit margin",
            min_value=0.0,
            max_value=0.5,
            value=float(st.session_state.tax_profit_margin),
            step=0.01,
            format="%.0f%%",
            key="tax_profit_margin_select",
        )

    st.session_state.tax_county = selected_county
    st.session_state.tax_structure = selected_structure
    st.session_state.tax_filing = selected_filing
    st.session_state.tax_profit_margin = selected_profit_margin
    tax = build_tax_snapshot(pnl)
    if not tax:
        st.info("We need more data before rendering the full TaxShield estimate.")
        return

    top_left, top_right = st.columns([2, 1], gap="large")
    with top_left:
        c1, c2, c3 = st.columns(3)
        c1.metric("Annualized revenue", f"${tax['annualized_revenue']:,.0f}")
        c2.metric("Annual sales tax", f"${tax['sales_tax']['annual_sales_tax']:,.0f}")
        c3.metric("Net annual estimate", f"${tax['net_annual_tax']:,.0f}")

        # Tax details in expander
        with st.expander("📋 See tax details"):
            d1, d2, d3 = st.columns(3)
            d1.metric("Taxable revenue", f"${tax['sales_tax']['taxable_revenue']:,.0f}")
            d2.metric("Collection allowance", f"${tax['allowance']['annual_allowance']:,.0f}")
            d3.metric("Corporate tax", f"${tax['corporate_tax']['annual_corporate_tax']:,.0f}")

        # Basis in expander
        with st.expander("📐 See assumptions"):
            st.write(f"- County rate: **{tax['sales_tax']['tax_rate'] * 100:.2f}%**")
            st.write(f"- Business type: **{tax['sales_tax']['business_type_label']}**")
            st.write(f"- Taxable share: **{tax['sales_tax']['taxable_ratio'] * 100:.0f}%**")
            st.write(f"- Filing cadence: **{tax['sales_tax']['filing_frequency_label']}**")
            st.write(f"- Structure: **{tax['corporate_tax']['structure_label']}**")

    with top_right:
        st.markdown("##### Filing schedule")
        st.dataframe(tax['sales_tax']['schedule'], hide_index=True, use_container_width=True)
        st.caption("Estimate only. Confirm with Florida DOR or CPA before filing.")


def page_billing() -> None:
    st.markdown('<div class="page-header">Billing</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">ProfitPulse has two in-app plans: Starter for analytics, Complete for analytics + TaxShield</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### ProfitPulse Starter")
        st.caption("Core operating view")
        st.write("- Core analytics dashboard")
        st.write("- Revenue, expenses, profit, and margin visibility")
        st.write("- Business health insights")
        st.write("- Tax previews across Overview")
        st.write("- Best for owners focused on numbers first")
    with c2:
        st.markdown("##### ProfitPulse Complete")
        st.caption("Full operating picture")
        st.write("- Everything in Starter")
        st.write("- TaxShield estimates and filing cadence")
        st.write("- County-aware Florida tax context")
        st.write("- Stronger operational planning visibility")

    st.markdown("##### Upgrade framing")
    u1, u2, u3 = st.columns(3)
    with u1:
        st.metric("Starter", "Analytics", "Core visibility")
    with u2:
        st.metric("Complete", "Analytics + TaxShield", "Planning clarity")
    with u3:
        st.metric("White-glove", "Separate service", "On-premises setup")

    st.markdown("##### Current plan")
    st.info(f"You are currently on **{current_plan_label()}**.")

    if has_complete_access():
        st.success("Complete access is enabled. You can use TaxShield from the main navigation.")
    else:
        st.warning("Upgrade to Complete to unlock TaxShield and tax planning surfaces across Overview.")
        if st.button("Upgrade to Complete", type="primary"):
            st.info("Stripe/billing connection can be attached here next.")

    st.caption("ScaleStack On-Premises is a separate white-glove service line. This page only covers ProfitPulse Starter and ProfitPulse Complete.")


def page_settings() -> None:
    st.markdown('<div class="page-header">Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Update the business profile and defaults that power your dashboard</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        new_business_type = st.selectbox(
            "Business type",
            BUSINESS_TYPES,
            index=BUSINESS_TYPES.index(st.session_state.business_type) if st.session_state.business_type in BUSINESS_TYPES else BUSINESS_TYPES.index("Other"),
            key="settings_biz_type",
        )
        if new_business_type != st.session_state.business_type:
            st.session_state.business_type = new_business_type
        
        st.selectbox(
            "Plan",
            ["ProfitPulse Starter", "ProfitPulse Complete"],
            index=1 if has_complete_access() else 0,
            disabled=True,
            help="Plan state currently comes from the authenticated account tier.",
        )
        
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            # Save to user DB if logged in
            username = st.session_state.get("username")
            if username:
                users.save_user_setting(username, "business_type", st.session_state.business_type)
                st.success("Settings saved!")
            else:
                st.success("Settings updated (session-only)")
            st.rerun()
    
    with col2:
        st.text_input("Florida county", value=st.session_state.tax_county, disabled=True)
        st.text_input("Tax filing frequency", value=st.session_state.tax_filing.title(), disabled=True)

    st.caption("Settings should later become the home for business profile, county/location, and notification preferences.")


# ────────────────────────────────────────────────
# PAGE: AI ADVISOR
# ────────────────────────────────────────────────
def page_ai_chat() -> None:
    st.markdown('<div class="page-header">AI Advisor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Ask anything about your profitability — get actionable answers</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.df_sales.empty:
        st.info("Load data first so the AI can analyse your actual numbers.")
        return

    if not st.session_state.pnl_cache:
        calculate_pnl()

    if get_api_key():
        st.caption("✓ Venice AI connected")
    else:
        st.caption("⚠ No API key — add VENICE_API_KEY to your .env file or Streamlit Cloud secrets")

    # ── Quick-query buttons ──────────────────────
    quick_queries = [
        "Full P&L health check",
        "Where can I cut costs?",
        "Labor efficiency analysis",
        "Margin optimisation ideas",
        "Seasonal trends & prep",
        "How do I hit 15% net margin?",
    ]
    cols = st.columns(len(quick_queries))
    selected_quick = None
    for i, q in enumerate(quick_queries):
        if cols[i].button(q, use_container_width=True, key=f"qq_{i}"):
            selected_quick = q

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Chat history display ─────────────────────
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Input — quick button takes priority over typed input ──
    user_input = st.chat_input("Ask about margins, labor costs, breakeven, trends…")
    query = selected_quick or user_input

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        with st.chat_message("assistant"):
            with st.spinner("Analysing your numbers…"):
                response = call_ai(query)
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑 Clear chat history", use_container_width=False):
            st.session_state.chat_history = []
            st.rerun()

    st.caption("AI suggestions are advisory — always verify against your dashboard data.")


# ────────────────────────────────────────────────
# PAGE: EXPORT
# ────────────────────────────────────────────────
def page_export() -> None:
    st.markdown('<div class="page-header">Export</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Download raw data and professional reports</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.df_sales.empty:
        st.info("No data to export yet. Load some data first.")
        return

    pnl = calculate_pnl()

    # ── Raw data downloads ───────────────────────
    st.markdown("##### Raw Data")
    datasets = [
        ("df_sales",     "Sales",     "sales_data.csv"),
        ("df_purchases", "Purchases", "purchases_data.csv"),
        ("df_expenses",  "Expenses",  "expenses_data.csv"),
        ("df_labor",     "Labor",     "labor_data.csv"),
    ]
    cols = st.columns(4)
    for col, (key, label, filename) in zip(cols, datasets):
        with col:
            df = st.session_state[key]
            if not df.empty:
                st.download_button(
                    f"↓ {label}", df.to_csv(index=False),
                    filename, "text/csv", use_container_width=True,
                )
            else:
                st.button(f"{label} — no data", disabled=True, use_container_width=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── P&L summary table ───────────────────────
    st.markdown("##### P&L Summary")
    pnl_summary = pd.DataFrame([
        {"Metric": "Total Revenue",        "Value": f"${pnl['total_revenue']:,.2f}"},
        {"Metric": "COGS",                 "Value": f"${pnl['total_cogs']:,.2f}"},
        {"Metric": "Gross Profit",         "Value": f"${pnl['gross_profit']:,.2f}"},
        {"Metric": "Gross Margin %",       "Value": f"{pnl['gross_margin_pct']:.1f}%"},
        {"Metric": "Operating Expenses",   "Value": f"${pnl['total_opex']:,.2f}"},
        {"Metric": "Labor Costs",          "Value": f"${pnl['total_labor']:,.2f}"},
        {"Metric": "Labor % of Revenue",   "Value": f"{pnl['labor_pct']:.1f}%"},
        {"Metric": "Net Profit",           "Value": f"${pnl['net_profit']:,.2f}"},
        {"Metric": "Net Margin %",         "Value": f"{pnl['net_margin_pct']:.1f}%"},
        {"Metric": "Breakeven Revenue",    "Value": f"${pnl['breakeven_revenue']:,.2f}"},
        {"Metric": "Total Labor Hours",    "Value": f"{pnl['total_hours']:,.1f}"},
        {"Metric": "Overtime Shifts",      "Value": f"{pnl['overtime_count']} ({pnl['overtime_pct']:.1f}%)"},
        {"Metric": "Daily Avg Revenue",    "Value": f"${pnl['daily_avg_revenue']:,.2f}"},
        {"Metric": "Data Period (days)",   "Value": str(pnl['date_range_days'])},
    ])
    st.dataframe(pnl_summary, use_container_width=True, hide_index=True)
    st.download_button(
        "↓ Download P&L CSV", pnl_summary.to_csv(index=False),
        "pnl_summary.csv", "text/csv",
    )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── PDF Report ───────────────────────────────
    st.markdown("##### PDF Report")
    if st.button("Generate PDF Report", type="primary"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Header
            pdf.set_font("Helvetica", "B", 22)
            pdf.cell(0, 14, "ProfitPulse", ln=True, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(120, 120, 120)
            biz_label = st.session_state.business_type or "Business"
            pdf.cell(
                0, 6,
                f"{biz_label}  |  P&L Report  |  {datetime.date.today().strftime('%B %d, %Y')}",
                ln=True, align="C",
            )
            pdf.set_text_color(0, 0, 0)
            pdf.ln(12)

            # P&L table
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Profit & Loss Summary", ln=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(245, 245, 250)
            pdf.cell(95, 7, "  Line Item",  border=0, fill=True)
            pdf.cell(50, 7, "Amount",       border=0, align="R", fill=True)
            pdf.cell(35, 7, "% of Revenue", border=0, align="R", fill=True, ln=True)

            rev = pnl["total_revenue"]
            def pdf_pct(v: float) -> str:
                return f"{(v / rev * 100):.1f}%" if rev > 0 else "—"

            pnl_rows_pdf = [
                ("Revenue",              pnl["total_revenue"],   "100.0%",                          False),
                ("Cost of Goods Sold",   pnl["total_cogs"],      pdf_pct(pnl["total_cogs"]),        False),
                ("Gross Profit",         pnl["gross_profit"],    f"{pnl['gross_margin_pct']:.1f}%", True),
                ("Operating Expenses",   pnl["total_opex"],      pdf_pct(pnl["total_opex"]),        False),
                ("Labor Costs",          pnl["total_labor"],     f"{pnl['labor_pct']:.1f}%",        False),
                ("Total Operating",      pnl["total_operating"], pdf_pct(pnl["total_operating"]),   False),
                ("Net Profit",           pnl["net_profit"],      f"{pnl['net_margin_pct']:.1f}%",   True),
            ]
            for label, amount, pct, is_bold in pnl_rows_pdf:
                pdf.set_font("Helvetica", "B" if is_bold else "", 9)
                sign      = "-" if amount < 0 else ""
                formatted = f"{sign}${abs(amount):,.2f}"
                prefix    = ">> " if is_bold else "   "
                pdf.cell(95, 7, f"{prefix}{label}", border=0)
                pdf.cell(50, 7, formatted,          border=0, align="R")
                pdf.cell(35, 7, pct,                border=0, align="R", ln=True)

            pdf.ln(10)

            # Revenue by category
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Revenue by Category", ln=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(245, 245, 250)
            pdf.cell(95, 7, "  Category",  border=0, fill=True)
            pdf.cell(50, 7, "Revenue",     border=0, align="R", fill=True)
            pdf.cell(35, 7, "% of Total",  border=0, align="R", fill=True, ln=True)
            pdf.set_font("Helvetica", "", 9)
            for cat, amt in pnl.get("rev_by_cat", {}).items():
                cat_pct = f"{(amt / rev * 100):.1f}%" if rev > 0 else "—"
                pdf.cell(95, 7, f"  {cat}",    border=0)
                pdf.cell(50, 7, f"${amt:,.2f}", border=0, align="R")
                pdf.cell(35, 7, cat_pct,        border=0, align="R", ln=True)

            pdf.ln(10)

            # Expense breakdown
            if pnl.get("opex_by_cat"):
                pdf.set_font("Helvetica", "B", 13)
                pdf.cell(0, 8, "Operating Expenses by Category", ln=True)
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_fill_color(245, 245, 250)
                pdf.cell(95, 7, "  Category", border=0, fill=True)
                pdf.cell(85, 7, "Amount",     border=0, align="R", fill=True, ln=True)
                pdf.set_font("Helvetica", "", 9)
                for cat, amt in pnl["opex_by_cat"].items():
                    pdf.cell(95, 7, f"  {cat}",    border=0)
                    pdf.cell(85, 7, f"${amt:,.2f}", border=0, align="R", ln=True)
                pdf.ln(10)

            # Key metrics
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Key Metrics", ln=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 9)
            key_metrics = [
                ("Daily Avg Revenue",  f"${pnl['daily_avg_revenue']:,.2f}"),
                ("Breakeven Revenue",  f"${pnl['breakeven_revenue']:,.2f}"),
                ("Total Labor Hours",  f"{pnl['total_hours']:,.1f} hrs"),
                ("Overtime Shifts",    f"{pnl['overtime_count']} ({pnl['overtime_pct']:.1f}%)"),
                ("Data Period",        f"{pnl['date_range_days']} days"),
            ]
            for label, val in key_metrics:
                pdf.cell(95, 7, f"  {label}", border=0)
                pdf.cell(85, 7, val,           border=0, align="R", ln=True)

            # Footer
            pdf.ln(15)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 5, f"Generated by ProfitPulse AI  |  {datetime.date.today()}", ln=True, align="C")

            buf = io.BytesIO()
            pdf.output(buf)
            st.download_button(
                "↓ Download PDF", buf.getvalue(),
                "profitpulse_report.pdf", "application/pdf",
            )
            st.toast("PDF ready to download!", icon="📄")

        except Exception as exc:
            st.error(f"PDF generation error: {exc}")


# ────────────────────────────────────────────────
# SIDEBAR (extracted from main for clarity)
# ────────────────────────────────────────────────
def render_sidebar() -> str:
    """Render sidebar nav + AI Pulse. Returns selected page name."""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:1rem 0 0.5rem;">
            <span style="font-size:1.6rem; color:#e0e0e0;">◈</span>
            <p style="font-size:1.1rem;font-weight:600;color:#e0e0e0;margin:0.3rem 0 0;">
                ProfitPulse
            </p>
        </div>
        <div style="text-align:center; margin:0 0 0.75rem;">
            <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:999px; background:linear-gradient(135deg, #f97316 0%, #ef4444 100%); color:#fff; font-size:0.78rem; font-weight:700; box-shadow:0 6px 16px rgba(239,68,68,0.25);">
                🔥 v0.1.2 - GPT-5.4 Test
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"Signed in as **{st.session_state.username}**")
        if st.session_state.business_type:
            st.caption(f"Business: **{st.session_state.business_type}**")
        st.caption(f"Plan: **{current_plan_label()}**")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        nav_options = ["Overview", "Analytics", "TaxShield", "Data Input", "AI Advisor", "Billing", "Settings", "Export"]

        default_page = st.session_state.get("nav_page", "Overview")
        if default_page not in nav_options:
            default_page = "Overview"

        # Build format func dict once
        nav_labels = {
            "Overview":   "🏠  Overview",
            "Analytics":  "📊  Analytics",
            "TaxShield":  "🧾  TaxShield",
            "Data Input": "📁  Data Input",
            "AI Advisor": "🤖  AI Advisor",
            "Billing":    "◈  Billing",
            "Settings":   "⚙️  Settings",
            "Export":     "📤  Export",
        }
        
        # Use a selectbox instead of radio for more reliable state handling
        page = st.selectbox(
            "Navigation",
            nav_options,
            index=nav_options.index(default_page),
            format_func=lambda x: nav_labels.get(x, x),
            key="nav_select",
            label_visibility="collapsed"
        )
        
        # Only rerun if page changed
        if page != st.session_state.get("nav_page"):
            st.session_state.nav_page = page

        # ── AI Pulse ────────────────────────────
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        with st.expander("🤖 AI Pulse", expanded=True):
            st.caption("Dynamic insight based on your current numbers")
            if st.button("Generate Insight", use_container_width=True):
                if st.session_state.df_sales.empty:
                    st.warning("Load data first so the AI can give meaningful advice.")
                else:
                    if not st.session_state.pnl_cache:
                        calculate_pnl()
                    with st.spinner("Analysing…"):
                        insight = call_ai(_ai_pulse_prompt())
                    st.markdown(insight)
            # Static fallback tip when no AI call made yet
            if not st.session_state.pnl_cache:
                st.info("💡 **Tip:** Track every expense category separately — "
                        "vague 'Misc' entries hide your biggest cost leaks.")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        # ── Data status ──────────────────────────
        has_data = not st.session_state.df_sales.empty
        if has_data:
            total_rows = sum(
                len(st.session_state[k])
                for k in ["df_sales", "df_purchases", "df_expenses", "df_labor"]
            )
            st.caption(f"✓ {total_rows:,} records loaded")
            if st.session_state.last_calculated:
                st.caption(f"P&L last run: {st.session_state.last_calculated}")
        else:
            st.caption("No data loaded")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        if st.button("🗑 Clear all data", use_container_width=True):
            for key in ["df_sales", "df_purchases", "df_expenses", "df_labor"]:
                st.session_state[key] = pd.DataFrame()
            # Clear from database for non-demo users
            username = st.session_state.get("username", "")
            if username and username != "admin":
                import users as user_db
                user_db.save_user_data(username, "sales", pd.DataFrame())
                user_db.save_user_data(username, "purchases", pd.DataFrame())
                user_db.save_user_data(username, "expenses", pd.DataFrame())
                user_db.save_user_data(username, "labor", pd.DataFrame())
            st.session_state.chat_history    = []
            st.session_state.pnl_cache       = {}
            st.session_state.last_calculated = None
            st.session_state.onboarded       = False
            st.session_state.business_type   = None
            st.session_state.nav_page        = "Overview"
            st.session_state.onboarding_step = 0
            _compute_pnl.clear()
            st.rerun()

        if st.button("🚪 Sign out", use_container_width=True):
            logout()

        st.markdown("---")
        st.caption("v0.1.1 - Test Edit")
    return page


# ────────────────────────────────────────────────
# MAIN ROUTER
# ────────────────────────────────────────────────
def main() -> None:
    # Global error handler
    try:
        _main_impl()
    except Exception as e:
        st.error(f"⚠️ An error occurred: {str(e)}")
        st.info("Try refreshing the page. If the problem persists, your session may have expired.")
        st.button("↻ Reload", on_click=lambda: st.rerun())

def _main_impl() -> None:
    # Apply theme early
    apply_theme()
    
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Render theme toggle in sidebar
    render_theme_toggle()

    # Show onboarding for brand-new users with no data
    if not st.session_state.onboarded and st.session_state.df_sales.empty:
        onboarding_wizard()
        return

    page = render_sidebar()

    if page == "Overview":
        page_overview()
    elif page == "Analytics":
        page_dashboard()
    elif page == "TaxShield":
        page_taxshield()
    elif page == "Data Input":
        page_data_input()
    elif page == "AI Advisor":
        page_ai_chat()
    elif page == "Export":
        page_export()
    elif page == "Billing":
        page_billing()
    elif page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
