# ============================================================
# ProfitPulse — AI-Powered Business Analytics Dashboard
# Polished & Production-Ready | February 2026
# Updated: March 2026 - ScaleStack color palette sync (dark-only theme)
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
    page_icon="logo.webp",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────
# GLOBAL CSS
# FIX: corrected unclosed .pnl-row.total brace that bled into
#      .premium-card/.tier-card, breaking dark-mode premium page.
# ADDED: dark-mode alert colours, button radius, input focus ring,
#        scrollbar, mobile padding tweak, card hover polish.
# March 2026: ScaleStack color palette sync (dark-only theme)
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
    background: linear-gradient(180deg, #0a0a0a 0%, #14202B 100%);
  }
  section[data-testid="stSidebar"] .stMarkdown p,
  section[data-testid="stSidebar"] .stMarkdown h3,
  section[data-testid="stSidebar"] .stMarkdown span,
  section[data-testid="stSidebar"] label { color: #a0a0a0 !important; }

  /* Theme Toggle Button */
  .theme-toggle {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 9999;
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 20px;
    padding: 6px 14px;
    color: #a5b4fc;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .theme-toggle:hover {
    background: rgba(59, 130, 246, 0.35);
    color: #fff;
  }

  .pp-card {
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.1);
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
    border: 1px solid rgba(255,255,255,0.1);
    background: linear-gradient(135deg, rgba(15,23,42,0.92) 0%, rgba(30,41,59,0.92) 100%);
    color: #e2e8f0;
  }
  .status-strip strong { display:block; font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.72; margin-bottom: 0.25rem; }
  .status-strip span { font-size: 0.95rem; font-weight: 600; display: block; margin-top: 0.25rem; }

  .card-default { background: linear-gradient(135deg, #14202B 0%, #334155 100%); }
  .card-good    { background: linear-gradient(135deg, #065f46 0%, #059669 100%); }
  .card-warn    { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); }
  .card-bad     { background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); }
  .card-accent  { background: linear-gradient(135deg, #312e81 0%, #3b82f6 100%); }

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
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    background: linear-gradient(135deg, #0a0a0a 0%, #14202B 100%);
    color: #e2e8f0;
  }
  .tier-card {
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.5rem;
    background: linear-gradient(135deg, #14202B 0%, #0a0a0a 100%);
    color: #e2e8f0;
    height: 100%;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }
  .tier-card:hover { transform: translateY(-3px); box-shadow: 0 10px 28px rgba(0,0,0,0.5); }
  .tier-card h2 { color: #ffffff; margin: 0.25rem 0; }
  .tier-card p  { color: #cbd5e1; }
  .tier-card hr { border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 1rem 0; }
  .tier-card.featured {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.4), 0 8px 24px rgba(99,102,241,0.15);
    background: linear-gradient(135deg, #2d3748 0%, #14202B 100%);
  }

  .page-header {
    font-size: 1.6rem; font-weight: 700; color: #f1f5f9;
    margin-bottom: 0.25rem; letter-spacing: -0.03em;
  }
  .page-sub { font-size: 0.9rem; color: #a0a0a0; margin-bottom: 1.5rem; }

  .stButton > button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: opacity 0.15s ease !important;
  }
  .stButton > button:hover { opacity: 0.88; }

  input:focus, textarea:focus, select:focus {
    outline: 2px solid #3b82f6 !important;
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
      background: #3b82f6;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      margin-top: -8px;
    }
    input[type="range"]::-webkit-slider-runnable-track {
      height: 8px;
      border-radius: 4px;
      background: linear-gradient(90deg, #3b82f6, #60a5fa);
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
    color: #14202B !important;
  }
  .light-mode .block-container {
    background: #ffffff;
  }
  .light-mode .pp-card {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
    color: #14202B !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
  }
  .light-mode .pp-card .label {
    color: #475569 !important;
    opacity: 1 !important;
  }
  .light-mode .pp-card .value {
    color: #0a0a0a !important;
  }
  .light-mode .pp-card .sub {
    color: #64748b !important;
  }
  .light-mode h1, .light-mode h2, .light-mode h3 {
    color: #0a0a0a !important;
  }
  .light-mode .page-header {
    color: #0a0a0a !important;
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
    """No theme toggle - dark mode only"""
    pass  # Dark theme is permanent
def apply_theme():
    """Apply dark theme CSS (ScaleStack palette)"""
    # ScaleStack color palette: dark-only theme
    # Colors set in global CSS at top of file
    pass
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
    # Save pending nav BEFORE rerun so sidebar can read it
    st.session_state["_pending_nav"] = page
    st.session_state.nav_page = page
    # Clear the nav_select widget key so sidebar selectbox uses our index
    if "nav_select" in st.session_state:
        del st.session_state["nav_select"]
    st.rerun()


CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#a0a0a0"),
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
            <p style="color:#64748b; font-size:0.75rem; margin:0; text-transform:uppercase; letter-spacing:2px;">From ScaleStack</p>
            <h1 style="font-size:1.8rem; font-weight:700; margin:0.5rem 0 0.2rem;">ProfitPulse</h1>
            <p style="color:#a0a0a0; font-size:0.9rem; margin:0;">
                AI-powered profitability analytics for any small business
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Toggle between Login and Signup
        if "show_signup" not in st.session_state:
            st.session_state.show_signup = False

        # Deep-link: ?page=signup opens Create Account tab by default
        if st.query_params.get("page") == "signup":
            st.session_state.show_signup = True

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
                "<p style='text-align:center;font-size:0.75rem;color:#a0a0a0;margin-top:1rem;'>"
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
                                 name="Revenue", marker_color="#3b82f6", marker_cornerradius=6))
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
                line=dict(color="#3b82f6", width=2.5),
                marker=dict(size=7, color="#3b82f6"),
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
                    color_discrete_sequence=["#3b82f6"],
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




# ────────────────────────────────────────────────
# MAIN ENTRY POINT
# ────────────────────────────────────────────────
def main():
    # Page routing
    page = st.sidebar.radio(
        "Navigate",
        ["Data Input", "Dashboard"],
        index=0 if "page" not in st.session_state else (1 if st.session_state.page == "Dashboard" else 0),
        key="page"
    )
    
    if page == "Data Input":
        page_data_input()
    elif page == "Dashboard":
        page_dashboard()


if __name__ == "__main__":
    main()
