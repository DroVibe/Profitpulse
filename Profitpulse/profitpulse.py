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
from supabase import create_client, Client
from fpdf import FPDF

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
APP_NAME  = "ProfitPulse"
# Placeholder - will be set after st is imported
API_KEY  = None
BASE_URL = "https://api.venice.ai/api/v1"
MODEL      = "e2ee-qwen-2-5-7b-p"
VISION_MODEL = "qwen3-vl-235b-a22b"  # Venice's confirmed vision-capable model
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

/* Sidebar navigation buttons */
.nav-btn {
  display: block;
  width: 100%;
  padding: 10px 14px;
  margin-bottom: 4px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #94A3B8;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
  font-family: 'Inter', sans-serif;
}
.nav-btn:hover {
  background: rgba(99,102,241,0.12);
  color: #E2E8F0;
}
.nav-btn.active {
  background: rgba(59,130,246,0.18);
  color: #F1F5F9;
  font-weight: 600;
}
.nav-divider {
  border: none;
  border-top: 1px solid rgba(148,163,184,0.08);
  margin: 12px 0;
}
.sidebar-logo {
  text-align: center;
  padding: 1.2rem 0 0.75rem;
}
.sidebar-user {
  font-size: 12px;
  color: #64748B;
  text-align: center;
  padding-bottom: 0.75rem;
}

</style>

<style>
/* Phase 2 — Overview redesign */
.pp-card-hero {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 0.75rem;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.pp-card-hero:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.pp-card-hero .hero-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94A3B8;
  margin-bottom: 8px;
}
.pp-card-hero .hero-value {
  font-size: 2rem;
  font-weight: 700;
  color: #F1F5F9;
  line-height: 1.1;
  margin-bottom: 4px;
}
.pp-card-hero .hero-value.green { color: #34D399; }
.pp-card-hero .hero-value.yellow { color: #FBBF24; }
.pp-card-hero .hero-value.red { color: #EF4444; }
.pp-card-hero .hero-sub {
  font-size: 12px;
  color: #64748B;
}
.pp-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 3px 10px;
  border-radius: 20px;
}
.pp-badge-healthy { background: #34D399; color: #0F172A; }
.pp-badge-warning { background: #FBBF24; color: #0F172A; }
.pp-badge-action { background: #EF4444; color: #ffffff; }
.pp-badge-insight { background: #6366F1; color: #ffffff; }
.pp-badge-review { background: #F59E0B; color: #0F172A; }
.insight-card {
  border-top: 1px solid rgba(148,163,184,0.08);
  padding: 14px 0;
}
.insight-card:first-child { border-top: none; }
.insight-title {
  font-size: 14px;
  font-weight: 600;
  color: #F1F5F9;
  margin-bottom: 4px;
}
.insight-desc {
  font-size: 12px;
  color: #94A3B8;
  line-height: 1.5;
}
.deadline-item {
  border-top: 1px solid rgba(148,163,184,0.08);
  padding: 12px 0;
}
.deadline-item:first-child { border-top: none; }
.deadline-title {
  font-size: 13px;
  font-weight: 600;
  color: #F1F5F9;
  margin-bottom: 2px;
}
.deadline-sub {
  font-size: 12px;
  color: #94A3B8;
}
.panel-container {
  background: rgba(30,41,59,0.5);
  border: 1px solid rgba(148,163,184,0.10);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 1rem;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #F1F5F9;
}
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


def _ensure_dfs() -> None:
    """Ensure all df_* session state vars are DataFrames (guards against type mismatch)."""
    for key in ["df_sales", "df_purchases", "df_expenses", "df_labor"]:
        val = st.session_state.get(key)
        if not isinstance(val, pd.DataFrame):
            st.session_state[key] = pd.DataFrame()


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
    "free": "ProfitPulse Free",
    "starter": "ProfitPulse Starter",
    "pro": "ProfitPulse Complete",
    "complete": "ProfitPulse Complete",
    "demo": "ProfitPulse Complete (Demo)",
    "beta": "ProfitPulse Beta 🚀",
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
    return st.session_state.user_tier in {"pro", "complete", "demo", "beta"}


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
    """Queue navigation to `page`. Navigation happens on the NEXT render cycle.
    Safe to call from anywhere — forms, buttons, etc.
    Does NOT call st.rerun() — form submissions auto-rerun; other callers
    will see the nav take effect on their next natural render."""
    st.session_state["_pending_nav"] = page
    st.session_state.nav_page = page
    # Clear nav_select so the sidebar selectbox default-index is recalculated
    # on the next render using the updated nav_page value.
    if "nav_select" in st.session_state:
        del st.session_state["nav_select"]


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

        # After signup success + rerun, show success message on login tab
        if st.session_state.get("just_signed_up"):
            st.session_state["just_signed_up"] = False
            st.session_state["_show_signup_success"] = True

        if st.session_state.get("_show_signup_success"):
            st.session_state["_show_signup_success"] = False
            st.success("Account created! Sign in with your credentials.")

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                user = st.text_input("Email", placeholder="your@email.com")
                pw   = st.text_input("Password", type="password", placeholder="••••••••")
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")

            # Handle AFTER form block — safe from Streamlit form rerun issues
            if submitted:
                user = user.lower().strip()
                # First check demo credentials
                valid_user = os.getenv("APP_USER", DEMO_USER)
                valid_pass = os.getenv("APP_PASS", DEMO_PASS)
                if user == valid_user and pw == valid_pass:
                    st.session_state.authenticated = True
                    st.session_state.username = user
                    st.session_state.user_tier = "demo"
                    _ensure_dfs()
                    initialize_demo_workspace()
                    st.rerun()
                else:
                    # Only check database users if demo creds did not match
                    success, user_data = users.verify_user(user, pw)
                    if success:
                        st.session_state.authenticated = True
                        # user_data contains the actual username (not the email)
                        db_username = user_data.get("username", user)
                        st.session_state.username = db_username
                        # New signups default to starter; paid users get their actual tier from billing
                        st.session_state.user_tier = user_data.get("tier") or "beta"
                        # Load user's saved data using their USERNAME (not email)
                        # so the per-user table names match what save_user_data uses
                        st.session_state.df_sales     = users.load_user_data(db_username, "sales")
                        st.session_state.df_purchases = users.load_user_data(db_username, "purchases")
                        st.session_state.df_expenses  = users.load_user_data(db_username, "expenses")
                        st.session_state.df_labor     = users.load_user_data(db_username, "labor")
                        # Load user's business type
                        biz_type = users.load_user_setting(db_username, "business_type")
                        if biz_type:
                            st.session_state.business_type = biz_type
                            st.session_state.onboarded = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

            if os.getenv("SHOW_DEMO_CREDS", "").lower() == "true":
                st.markdown(
                    "<p style='text-align:center;font-size:0.78rem;color:#cbd5e1;margin-top:1rem;'>"
                    "Demo: admin@pilot.com / pilot2026</p>",
                    unsafe_allow_html=True,
                )
        
        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                new_user = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email", placeholder="your@email.com")
                new_pw = st.text_input("Password", type="password", placeholder="Create password")
                confirm_pw = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                signup_submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            # Handle AFTER form block — safe from Streamlit form rerun issues
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
                        # Auto-log in the new user immediately
                        st.session_state.authenticated = True
                        st.session_state.username     = new_user
                        st.session_state.user_tier   = "free"
                        _ensure_dfs()
                        # Initialize default business type so onboarding doesn't
                        # re-trigger after signup (user already picked industry)
                        if not st.session_state.get("business_type"):
                            st.session_state.business_type = "Other"
                        st.session_state.onboarded = True
                        st.session_state.nav_page  = "Overview"
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown(
                "<p style='text-align:center;font-size:0.75rem;color:#94a3b8;margin-top:1rem;'>"
                "Starter includes analytics. Complete adds TaxShield planning tools.</p>",
                unsafe_allow_html=True,
            )


def logout() -> None:
    # Save all data before wiping session — skip for demo (no DB account)
    if st.session_state.get("authenticated") and st.session_state.get("user_tier") not in {"demo"}:
        username = st.session_state.get("username", "")
        if username:
            # save_all_user_data() persists all four dataframes in one call
            save_all_user_data()
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

    # Guard: ensure df_* are DataFrames before calling .empty
    _ensure_dfs()

    if st.session_state.df_sales.empty:
        demo = generate_demo_data(6, st.session_state.business_type)
        st.session_state.df_sales = demo["sales"]
        st.session_state.df_purchases = demo["purchases"]
        st.session_state.df_expenses = demo["expenses"]
        st.session_state.df_labor = demo["labor"]

    st.session_state.onboarded = True
    st.session_state.onboarding_step = None
    st.session_state.nav_page = st.session_state.get("nav_page", "Overview")


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
    """Save all user data to database. Returns True on success, False on any failure."""
    import users as user_db
    username = st.session_state.get("username", "")
    if not username:
        return False
    ok = True
    for dtype, df in [
        ("sales",     st.session_state.df_sales),
        ("purchases", st.session_state.df_purchases),
        ("expenses",  st.session_state.df_expenses),
        ("labor",     st.session_state.df_labor),
    ]:
        if not user_db.save_user_data(username, dtype, df):
            ok = False
    if st.session_state.get("business_type"):
        user_db.save_user_setting(username, "business_type", st.session_state.business_type)
    return ok


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


# ────────────────────────────────────────────────
# RECEIPT AI SCANNER
# Uses Venice AI to extract vendor, date, amount, category from a receipt photo.
# ────────────────────────────────────────────────
def _receipt_extraction_prompt() -> str:
    """System prompt for structured receipt extraction."""
    categories = ", ".join(EXPENSE_CATEGORIES)
    return (
        'You are a receipt parser. Extract structured data from this receipt image. '
        'The image may be rotated or at an angle — read it anyway. '
        'Respond ONLY with valid JSON in this exact format, no markdown, no explanation:\n\n'
        '{"vendor":"store or merchant name","date":"YYYY-MM-DD","amount":0.00,'
        '"category":"best match from this list","description":"brief description of items"}\n\n'
        f'Valid categories: {categories}\n\n'
        'Rules:\n'
        '- date: use YYYY-MM-DD format. If date is unclear, use today\'s date.\n'
        '- amount: the TOTAL shown on the receipt (subtotal or grand total, whichever is larger).\n'
        '- category: pick the closest match from the valid list above.\n'
        '- description: 1-2 words max, e.g. "Office supplies", "Restaurant meal", "Parts"\n'
        '- If you cannot read the receipt clearly, return {"error":"Could not read receipt"} instead.\n'
        'Respond with ONLY JSON.'
    )


def _preprocess_image(file_bytes: bytes) -> bytes:
    """Auto-rotate an image based on EXIF orientation tag, resize to max 1024px
    wide, then re-encode as JPEG. Keeps receipt scans fast for the vision model."""
    import io
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Auto-rotate based on EXIF orientation
        exif = img.getexif()
        if exif:
            orientation = exif.get(0x0112)  # EXIF orientation tag
            if orientation == 2:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 4:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(90, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 7:
                img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
        # Force RGB (handles RGBA, palette, etc.)
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        # Resize to max 1024px wide — dramatically faster for vision model
        max_w = 1024
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return buf.getvalue()
    except Exception:
        # If preprocessing fails, return original bytes
        return file_bytes


def scan_receipt_with_ai(uploaded_file) -> dict | None:
    """Send receipt image to Venice AI. Returns structured dict or None."""
    import base64
    import json

    api_key = get_api_key()
    if not api_key:
        return None

    try:
        file_bytes = uploaded_file.getvalue()
        processed_bytes = _preprocess_image(file_bytes)
        b64_data = base64.b64encode(processed_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_data}"

        client = OpenAI(
            api_key=api_key,
            base_url=BASE_URL,
            timeout=60,
        )
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _receipt_extraction_prompt()},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=400,
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1])
        result = json.loads(raw)
        if result.get("error"):
            return None
        return result

    except Exception as e:
        print(f"Receipt scan error: {e}")
        return None


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
    _ensure_dfs()
    st.markdown('<div class="page-header">Data Input</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Snap a receipt, upload a CSV, '
        'or enter transactions manually</div>',
        unsafe_allow_html=True,
    )

    # ── Upgrade nudge for free users (below header, above tabs) ──
    if st.session_state.user_tier == "free":
        st.info(
            "💡 Free plan. Starter ($19/mo) unlocks AI Advisor "
            "and full analytics. Complete ($29/mo) adds TaxShield."
        )

    # ── Row counts (always visible at top) ──────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sales", f"{len(st.session_state.df_sales):,}")
    m2.metric("Purchases", f"{len(st.session_state.df_purchases):,}")
    m3.metric("Expenses", f"{len(st.session_state.df_expenses):,}")
    m4.metric("Labor", f"{len(st.session_state.df_labor):,}")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── 3 primary tabs ───────────────────────────────────────────
    tab_scan, tab_csv, tab_manual = st.tabs([
        "📷 Snap & Save",
        "📁 Upload CSV",
        "✏️ Manual Entry",
    ])

    # ════════════════════════════════════════════════════════════
    # TAB 1 — SNAP & SAVE
    # ════════════════════════════════════════════════════════════
    with tab_scan:
        st.markdown("##### Scan a receipt and save it as an expense")
        st.caption("Works best with clear, well-lit photos. "
                   "Take a photo or upload from your camera roll.")

        input_method = st.radio(
            "How would you like to add your receipt?",
            ["📁 Upload a photo", "📷 Take a photo now"],
            horizontal=True,
            key="receipt_input_method"
        )

        uploaded_file = None
        if input_method == "📁 Upload a photo":
            uploaded_file = st.file_uploader(
                "Upload receipt image",
                type=["png", "jpg", "jpeg"],
                help="Clear, well-lit photos work best.",
                key="receipt_upload"
            )
        else:
            camera_photo = st.camera_input(
                "Point camera at receipt and tap capture",
                key="receipt_camera"
            )
            if camera_photo:
                uploaded_file = camera_photo

        if uploaded_file is not None:
            try:
                processed = _preprocess_image(uploaded_file.getvalue())
                st.image(io.BytesIO(processed),
                         caption="Receipt preview",
                         use_container_width=True)
            except Exception:
                st.image(uploaded_file, caption="Receipt preview",
                         use_container_width=True)

        _s = st.session_state
        d_vendor = _s.get("_r_vendor", "")
        d_amount = _s.get("_r_amount", 0.0)
        d_cat = _s.get("_r_category", EXPENSE_CATEGORIES[0])
        d_desc = _s.get("_r_desc", "")
        d_date = _s.get("_r_date", str(datetime.date.today()))
        d_conf = _s.get("_r_confidence", {})
        scan_ready = bool(d_vendor)

        try:
            d_date_val = datetime.date.fromisoformat(d_date[:10])
        except Exception:
            d_date_val = datetime.date.today()
        cat_idx = (EXPENSE_CATEGORIES.index(d_cat)
                   if d_cat in EXPENSE_CATEGORIES else 0)

        if scan_ready:
            st.markdown("**✅ Receipt scanned — review and confirm:**")
            conf_cols = st.columns(4)
            fields = [
                ("Vendor", d_vendor, d_conf.get("vendor", "high")),
                ("Amount", f"${float(d_amount):,.2f}",
                 d_conf.get("amount", "high")),
                ("Date", d_date, d_conf.get("date", "medium")),
                ("Category", d_cat, d_conf.get("category", "medium")),
            ]
            icons = {"high": "✅", "medium": "⚠️", "low": "❓"}
            for col, (label, value, conf) in zip(conf_cols, fields):
                with col:
                    st.caption(f"{icons.get(conf, '⚠️')} {label}")
                    st.markdown(f"**{value}**")
            st.markdown("---")
        else:
            st.info("👆 Tap Scan Receipt to auto-fill the "
                    "form below.")

        r1, r2 = st.columns(2)
        with r1:
            vendor_key = f"rec_vendor_f_{d_vendor}"
            rec_vendor = st.text_input(
                "Vendor / Store", value=d_vendor,
                placeholder="e.g., Home Depot, Sysco",
                key=vendor_key)
        with r2:
            date_key = f"rec_date_f_{d_date}"
            rec_date = st.date_input("Date", value=d_date_val,
                                    key=date_key)

        r3, r4 = st.columns(2)
        with r3:
            amount_key = f"rec_amount_f_{d_vendor}_{d_amount}"
            rec_amount = st.number_input(
                "Total Amount ($)", min_value=0.0, step=0.01,
                value=float(d_amount) if d_amount else 0.0,
                key=amount_key)
        with r4:
            category_key = f"rec_category_f_{d_cat}"
            rec_category = st.selectbox(
                "Category", EXPENSE_CATEGORIES,
                index=cat_idx, key=category_key)

        desc_key = f"rec_desc_f_{d_vendor}"
        rec_desc = st.text_input(
            "Description (optional)", value=d_desc,
            placeholder="What was this for?",
            key=desc_key)

        btn1, btn2, btn3 = st.columns([2, 1, 1])
        with btn1:
            save_clicked = st.button(
                "💾 Confirm & Save to Expenses",
                type="primary", use_container_width=True,
                key="receipt_save_btn")
        with btn2:
            scan_clicked = st.button(
                "🔍 Scan Receipt" + (" ✓" if scan_ready else ""),
                use_container_width=True,
                key="receipt_scan_btn")
        with btn3:
            if scan_ready:
                if st.button("🔄 Clear", use_container_width=True,
                             key="receipt_clear_btn"):
                    for k in ("_r_vendor","_r_amount","_r_category",
                              "_r_desc","_r_date","_r_confidence"):
                        _s.pop(k, None)
                    st.rerun()

        if scan_clicked:
            if uploaded_file is None:
                st.warning("Please upload or capture a receipt first.")
            else:
                with st.spinner("📷 Reading your receipt…"):
                    result = scan_receipt_with_ai(uploaded_file)
                    err = st.session_state.pop("_receipt_scan_error", None)
                    if result and result.get("vendor"):
                        _s["_r_vendor"] = result.get("vendor", "")
                        _s["_r_category"] = (
                            result["category"]
                            if result.get("category") in EXPENSE_CATEGORIES
                            else EXPENSE_CATEGORIES[0])
                        _s["_r_desc"] = result.get("description", "")
                        amt = result.get("amount", 0)
                        _s["_r_amount"] = float(amt) if amt else 0.0
                        if result.get("date"):
                            try:
                                _s["_r_date"] = result["date"][:10]
                            except Exception:
                                _s["_r_date"] = str(datetime.date.today())
                        else:
                            _s["_r_date"] = str(datetime.date.today())
                        _s["_r_confidence"] = {
                            "vendor": "high" if result.get("vendor") else "low",
                            "amount": "high" if result.get("amount") else "low",
                            "date": "high" if result.get("date") else "medium",
                            "category": "medium",
                        }
                        st.toast("✅ Receipt scanned! Review and confirm.",
                                 icon="🔍")
                        st.rerun()
                    else:
                        if err:
                            st.error(f"Scan error: {err}")
                        else:
                            st.warning(
                                "⚠️ Couldn't read this receipt clearly. "
                                "Fill in the fields manually.")

        if save_clicked:
            if rec_amount <= 0:
                st.warning("Please enter a valid amount.")
            else:
                desc_text = (f"Receipt: {rec_vendor}"
                              if rec_vendor else "Receipt")
                if rec_desc:
                    desc_text += f" — {rec_desc}"
                row = pd.DataFrame([{
                    "date": str(rec_date),
                    "category": rec_category,
                    "amount": rec_amount,
                    "description": desc_text,
                }])
                st.session_state.df_expenses = (
                    row if st.session_state.df_expenses.empty
                    else pd.concat([st.session_state.df_expenses, row],
                                   ignore_index=True))
                for k in ("_r_vendor","_r_amount","_r_category",
                          "_r_desc","_r_date","_r_confidence"):
                    _s.pop(k, None)
                if save_all_user_data():
                    _compute_pnl.clear()
                    calculate_pnl()
                    st.toast(
                        f"✅ Saved: {rec_vendor or 'Receipt'} "
                        f"— ${rec_amount:,.2f}", icon="💾")
                else:
                    st.warning("Saved to session but couldn't "
                               "persist to database.")
                st.rerun()

    # ════════════════════════════════════════════════════════════
    # TAB 2 — UPLOAD CSV
    # ════════════════════════════════════════════════════════════
    with tab_csv:
        st.markdown("##### Upload your data as CSV files")

        with st.expander("📖 CSV format guide", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Sales · Purchases · Expenses**")
                st.code(
                    "date,category,amount,description\n"
                    "2026-01-15,Oil Change,150.00,Maintenance\n"
                    "2026-01-20,Inspection,50.00,State inspection",
                    language="text")
            with c2:
                st.markdown("**Labor / Payroll**")
                st.code(
                    "date,employee,hours,rate,description\n"
                    "2026-01-15,Mike,8,25.00,Regular shift\n"
                    "2026-01-18,Mike,10,37.50,OT shift",
                    language="text")

        upload_specs = [
            ("up_sales", "df_sales",
             ["date","category","amount"], "Sales"),
            ("up_purch", "df_purchases",
             ["date","category","amount"], "Purchases"),
            ("up_exp", "df_expenses",
             ["date","category","amount"], "Expenses"),
            ("up_labor", "df_labor",
             ["date","employee","hours","rate"], "Labor"),
        ]
        cols = st.columns(4)
        for col, (key, state_key, required_cols, label) in zip(
                cols, upload_specs):
            with col:
                f = st.file_uploader(label, type="csv", key=key)
                if f:
                    parsed = parse_csv(f, required_cols, label)
                    if not parsed.empty:
                        st.session_state[state_key] = parsed
                        saved_ok = save_all_user_data()
                        _compute_pnl.clear()
                        calculate_pnl()
                        if saved_ok:
                            st.toast(
                                f"{label}: {len(parsed):,} rows loaded",
                                icon="📂")
                        else:
                            st.warning(
                                f"⚠️ {label} loaded but failed to "
                                f"persist. Will show in this session.")

        st.markdown("<div style='height:1rem'></div>",
                    unsafe_allow_html=True)

        biz = st.session_state.business_type or "Auto Repair"
        with st.expander("⚡ Load demo data", expanded=False):
            st.caption(
                f"Replace all current data with 6 months of "
                f"realistic {biz} demo data.")
            if st.button(f"Load {biz} Demo Data",
                          use_container_width=True):
                with st.spinner("Generating demo data…"):
                    demo = generate_demo_data(6, biz)
                    st.session_state.df_sales = demo["sales"]
                    st.session_state.df_purchases = demo["purchases"]
                    st.session_state.df_expenses = demo["expenses"]
                    st.session_state.df_labor = demo["labor"]
                    save_all_user_data()
                    _compute_pnl.clear()
                    calculate_pnl()
                    st.toast("Demo data loaded!", icon="✅")
                    st.rerun()

    # ════════════════════════════════════════════════════════════
    # TAB 3 — MANUAL ENTRY
    # ════════════════════════════════════════════════════════════
    with tab_manual:
        st.markdown("##### Enter transactions manually")

        tab_s, tab_p, tab_e, tab_l = st.tabs([
            "➕ Sale", "➕ Purchase",
            "➕ Expense", "➕ Labor Shift"
        ])

        with tab_s:
            with st.form("add_sale", clear_on_submit=True):
                r1, r2, r3 = st.columns(3)
                s_date = r1.date_input("Date",
                                       value=datetime.date.today())
                s_cat = r2.text_input("Category",
                                      placeholder="Oil Change")
                s_amt = r3.number_input("Amount ($)",
                                         min_value=0.0, step=1.0)
                s_desc = st.text_input("Description (optional)")
                if st.form_submit_button("Add Sale",
                                         use_container_width=True, type="primary"):
                    if not s_cat.strip():
                        st.warning("Please enter a category.")
                    else:
                        row = pd.DataFrame([{
                            "date": str(s_date),
                            "category": s_cat.strip(),
                            "amount": s_amt,
                            "description": s_desc
                        }])
                        st.session_state.df_sales = pd.concat(
                            [st.session_state.df_sales, row],
                            ignore_index=True)
                        if save_all_user_data():
                            _compute_pnl.clear()
                            calculate_pnl()
                            st.toast("Sale added ✓", icon="✅")
                        else:
                            st.warning(
                                "Sale added to session but failed "
                                "to save to the database.")
                        st.rerun()

        with tab_p:
            with st.form("add_purchase", clear_on_submit=True):
                r1, r2, r3 = st.columns(3)
                p_date = r1.date_input("Date",
                                        value=datetime.date.today())
                p_cat = r2.text_input("Category",
                                      placeholder="Parts Wholesale")
                p_amt = r3.number_input("Amount ($)",
                                         min_value=0.0, step=1.0)
                p_desc = st.text_input("Description (optional)")
                if st.form_submit_button("Add Purchase",
                                         use_container_width=True, type="primary"):
                    if not p_cat.strip():
                        st.warning("Please enter a category.")
                    else:
                        row = pd.DataFrame([{
                            "date": str(p_date),
                            "category": p_cat.strip(),
                            "amount": p_amt,
                            "description": p_desc
                        }])
                        st.session_state.df_purchases = pd.concat(
                            [st.session_state.df_purchases, row],
                            ignore_index=True)
                        if save_all_user_data():
                            _compute_pnl.clear()
                            calculate_pnl()
                            st.toast("Purchase added ✓", icon="✅")
                        else:
                            st.warning(
                                "Purchase added to session but "
                                "failed to save to the database.")
                        st.rerun()

        with tab_e:
            with st.form("add_expense", clear_on_submit=True):
                r1, r2, r3 = st.columns(3)
                e_date = r1.date_input("Date",
                                       value=datetime.date.today())
                e_cat = r2.selectbox("Category", EXPENSE_CATEGORIES)
                e_amt = r3.number_input("Amount ($)",
                                          min_value=0.0, step=1.0)
                e_desc = st.text_input("Description (optional)")
                if st.form_submit_button("Add Expense",
                                         use_container_width=True, type="primary"):
                    row = pd.DataFrame([{
                        "date": str(e_date),
                        "category": e_cat,
                        "amount": e_amt,
                        "description": e_desc
                    }])
                    st.session_state.df_expenses = pd.concat(
                        [st.session_state.df_expenses, row],
                        ignore_index=True)
                    if save_all_user_data():
                        _compute_pnl.clear()
                        calculate_pnl()
                        st.toast("Expense added ✓", icon="✅")
                    else:
                        st.warning(
                            "Expense added to session but failed "
                            "to save to the database.")
                    st.rerun()

        with tab_l:
            with st.form("add_labor", clear_on_submit=True):
                r1, r2, r3, r4 = st.columns(4)
                l_date = r1.date_input("Date",
                                        value=datetime.date.today())
                l_emp = r2.text_input("Employee",
                                      placeholder="Name")
                l_hrs = r3.number_input("Hours",
                                         min_value=0.0,
                                         step=0.5, value=8.0)
                l_rate = r4.number_input("Rate $/hr",
                                          min_value=0.0,
                                          step=0.5, value=20.0)
                l_desc = st.text_input("Description",
                                      placeholder="Regular shift")
                if st.form_submit_button("Add Shift",
                                         use_container_width=True, type="primary"):
                    if not l_emp.strip():
                        st.warning("Please enter an employee name.")
                    else:
                        row = pd.DataFrame([{
                            "date": str(l_date),
                            "employee": l_emp.strip(),
                            "hours": l_hrs,
                            "rate": l_rate,
                            "description": l_desc
                        }])
                        st.session_state.df_labor = pd.concat(
                            [st.session_state.df_labor, row],
                            ignore_index=True)
                        if save_all_user_data():
                            _compute_pnl.clear()
                            calculate_pnl()
                            st.toast("Shift added ✓", icon="✅")
                        else:
                            st.warning(
                                "Shift added to session but failed "
                                "to save to the database.")
                        st.rerun()

# ────────────────────────────────────────────────
# PAGE: DASHBOARD
# NEW: Recalculate button, last-updated timestamp, What-If simulator
# ────────────────────────────────────────────────
def page_dashboard() -> None:
    _ensure_dfs()
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

    # ── AI Period Summary Button ─────────────────
    if st.button("🤖 AI Period Summary", type="secondary", use_container_width=True):
        with st.spinner("Analyzing your period..."):
            benchmarks = calc_benchmarks(pnl)
            prompt = f"""You are a business analyst. Based on this P&L data: Revenue ${pnl['total_revenue']:.2f}, 
            OpEx ${pnl['total_opex']:.2f}, Gross Profit ${pnl['gross_profit']:.2f}, Net Margin {pnl['net_margin_pct']:.1f}%.
            Industry benchmarks: Gross Margin {benchmarks['gross_margin']:.0f}%, Net Margin {benchmarks['net_margin']:.0f}%.
            Labor % of Revenue: {pnl['labor_pct_of_revenue']:.1f}%.
            Write a 3-4 sentence plain-English summary: what's going well, what's concerning, and 1-2 specific suggestions."""
            response = call_ai(prompt)
            st.markdown("### 📋 AI Period Summary")
            st.markdown(response)
            st.caption("AI summaries are informational. Not financial advice.")


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

    # ── Alerts (max 2 highest priority) ─────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    alerts = []
    if pnl["net_margin_pct"] < 5:
        alerts.append(("bad", f"🔴 Net margin critically low at {pnl['net_margin_pct']:.1f}% — immediate action required."))
    if pnl["gross_margin_pct"] < BENCHMARKS["gross_margin_pct"]:
        alerts.append(("warn", f"⚠ Gross margin {pnl['gross_margin_pct']:.1f}% below {BENCHMARKS['gross_margin_pct']}% benchmark."))
    if pnl["overtime_count"] > 0:
        ot_est = pnl["total_labor"] * (pnl["overtime_pct"] / 100) * 0.5
        alerts.append(("bad", f"🔴 {pnl['overtime_count']} overtime shifts — est. extra cost ~${ot_est:,.0f}."))
    if pnl["labor_pct"] > BENCHMARKS["labor_pct_of_revenue"]:
        alerts.append(("warn", f"⚠ Labor at {pnl['labor_pct']:.1f}% of revenue — review scheduling."))

    for level, text in alerts[:2]:
        pp_alert(text, level)

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


def render_smart_insights(pnl: dict) -> None:
    """Render Smart Insights panel — data-driven, no API call."""
    import datetime as dt

    # Determine overall health score
    issues = 0
    if pnl.get("net_profit", 0) < 0: issues += 2
    if pnl.get("gross_margin_pct", 0) < BENCHMARKS["gross_margin_pct"]: issues += 1
    if pnl.get("labor_pct", 0) > BENCHMARKS["labor_pct_of_revenue"]: issues += 1
    if pnl.get("overtime_count", 0) > 0: issues += 1

    if issues == 0:
        health, badge_cls = "Healthy", "pp-badge-healthy"
    elif issues <= 1:
        health, badge_cls = "Good", "pp-badge-insight"
    elif issues <= 2:
        health, badge_cls = "Review", "pp-badge-review"
    else:
        health, badge_cls = "Action needed", "pp-badge-action"

    # Generate insights from data
    insights = []

    monthly = pnl.get("monthly", pd.DataFrame())
    if len(monthly) >= 2 and "gross_margin_pct" in monthly.columns:
        last_two = monthly.tail(2)["gross_margin_pct"].values
        diff = last_two[-1] - last_two[-2]
        if diff > 0:
            insights.append({
                "title": f"Margin up {diff:.1f}pp this month",
                "desc": f"Gross margin improved to {last_two[-1]:.1f}%",
                "badge": "Insight", "badge_cls": "pp-badge-insight"
            })
        elif diff < 0:
            insights.append({
                "title": f"Margin slipped {abs(diff):.1f}pp",
                "desc": "Review COGS or pricing",
                "badge": "Action", "badge_cls": "pp-badge-action"
            })

    if pnl.get("overtime_count", 0) > 0:
        ot_cost = round(pnl.get("total_labor", 0) * (pnl.get("overtime_pct", 0) / 100) * 0.5)
        insights.append({
            "title": f"{pnl['overtime_count']} overtime shifts detected",
            "desc": f"~${ot_cost:,.0f} in premium labor costs",
            "badge": "Review", "badge_cls": "pp-badge-review"
        })

    if pnl.get("net_profit", 0) > 0:
        insights.append({
            "title": "Business is profitable",
            "desc": f"Net margin: {pnl.get('net_margin_pct', 0):.1f}%",
            "badge": "Healthy", "badge_cls": "pp-badge-healthy"
        })
    elif pnl.get("net_profit", 0) < 0:
        insights.append({
            "title": "Running at a loss",
            "desc": "Review expenses immediately",
            "badge": "Action", "badge_cls": "pp-badge-action"
        })

    # Cap at 3 insights
    insights = insights[:3]
    if not insights:
        insights = [{"title": "Add more data for insights",
                     "desc": "Upload sales and expenses to unlock",
                     "badge": "Info", "badge_cls": "pp-badge-insight"}]

    cards_html = ""
    for ins in insights:
        cards_html += f"""
    <div class="insight-card">
        <div style="display:flex; justify-content:space-between;
        align-items:flex-start; margin-bottom:4px;">
            <div class="insight-title">{ins['title']}</div>
            <span class="pp-badge {ins['badge_cls']}">{ins['badge']}</span>
        </div>
        <div class="insight-desc">{ins['desc']}</div>
    </div>"""

    st.markdown(f"""
    <div class="panel-container">
        <div class="panel-header">
            <span class="panel-title">Smart insights</span>
            <span class="pp-badge {badge_cls}">{health}</span>
        </div>
        {cards_html}
    </div>
    """, unsafe_allow_html=True)


def render_tax_deadlines(tax: dict) -> None:
    """Render TaxShield Deadlines panel."""
    import datetime as dt
    today = dt.date.today()

    schedule = tax.get("sales_tax", {}).get("schedule", []) if tax else []
    county = tax.get("sales_tax", {}).get("county", "FL") if tax else "FL"
    corp_tax = tax.get("corporate_tax", {}) if tax else {}

    # Build all inner HTML first
    inner_html = ""

    if not schedule:
        inner_html = '<div class="insight-desc">Add revenue data to calculate filing deadlines.</div>'
    else:
        for deadline in schedule[:2]:
            due_str = deadline.get("due_window", "")
            try:
                due_date = dt.datetime.strptime(
                    due_str.split("-")[0].strip(), "%b %d, %Y").date()
                days_left = (due_date - today).days
                if days_left <= 7:
                    badge_cls = "pp-badge-action"
                elif days_left <= 14:
                    badge_cls = "pp-badge-review"
                else:
                    badge_cls = "pp-badge-insight"
                badge_txt = f"{days_left}d"
            except Exception:
                badge_cls = "pp-badge-insight"
                badge_txt = "Soon"

            inner_html += (
                f'<div class="deadline-item">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'<div>'
                f'<div class="deadline-title">Sales tax remittance</div>'
                f'<div class="deadline-sub">{county} &middot; Due {due_str}</div>'
                f'</div>'
                f'<span class="pp-badge {badge_cls}">{badge_txt}</span>'
                f'</div>'
                f'</div>'
            )

        if corp_tax.get("annual_corporate_tax", 0) > 0:
            inner_html += (
                '<div class="deadline-item">'
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                '<div>'
                '<div class="deadline-title">Quarterly estimate</div>'
                '<div class="deadline-sub">Corporate tax &middot; Due Apr 30</div>'
                '</div>'
                '<span class="pp-badge pp-badge-review">Q2</span>'
                '</div>'
                '</div>'
            )

    # Render everything in ONE st.markdown() call
    st.markdown(
        f'<div class="panel-container">'
        f'<div class="panel-header">'
        f'<span class="panel-title">TaxShield deadlines</span>'
        f'</div>'
        f'{inner_html}'
        f'</div>',
        unsafe_allow_html=True
    )


def page_overview() -> None:
    _ensure_dfs()
    if st.session_state.df_sales.empty:
        st.info("No data loaded yet. Head to Data Input to get started.")
        if st.button("➕ Add your first transaction", type="primary"):
            jump_to("Data Input")
        return

    pnl = calculate_pnl()
    tax = build_tax_snapshot(pnl)
    biz_label = st.session_state.business_type or "Business"

    # ── Page header ─────────────────────────────
    hdr_col, ts_col = st.columns([3, 1])
    with hdr_col:
        st.markdown('<div class="page-header">Overview</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<div class="page-sub">{biz_label} · '
            f'{pnl["date_range_days"]}-day snapshot</div>',
            unsafe_allow_html=True,
        )
    with ts_col:
        if st.session_state.last_calculated:
            st.caption(f"Updated: **{st.session_state.last_calculated}**")

    if st.session_state.user_tier == "beta":
        st.markdown("""
        <div style="background:linear-gradient(135deg,rgba(99,102,241,0.15) 0%,rgba(59,130,246,0.10) 100%);border:1px solid rgba(99,102,241,0.3);border-radius:12px;padding:14px 20px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.4rem;">🚀</span>
        <div>
        <div style="font-weight:700;color:#A5B4FC;font-size:13px;">Beta Access — Full Features Unlocked</div>
        <div style="color:#64748B;font-size:12px;margin-top:2px;">You have complete access to all ProfitPulse features. Thank you for testing!</div>
        </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Main layout: left (charts) + right (panels) ─
    left_col, right_col = st.columns([2, 1], gap="large")

    with left_col:
        # ── 3 Hero KPI Cards ────────────────────
        monthly = pnl.get("monthly", pd.DataFrame())
        mom_change = 0.0
        monthly_rev = pnl["total_revenue"]
        if len(monthly) >= 2 and "revenue" in monthly.columns:
            last_two = monthly.tail(2)["revenue"].values
            monthly_rev = last_two[-1]
            if last_two[-2] > 0:
                mom_change = (last_two[-1] - last_two[-2]) / last_two[-2] * 100

        days_until_due = 30
        next_filing_amount = 0
        if tax:
            schedule = tax.get("sales_tax", {}).get("schedule", [])
            if schedule:
                import datetime as dt
                try:
                    due_str = schedule[0].get("due_window", "")
                    due_date = dt.datetime.strptime(
                        due_str.split("-")[0].strip(), "%b %d, %Y").date()
                    days_until_due = (due_date - dt.date.today()).days
                except Exception:
                    pass
                next_filing_amount = tax.get("sales_tax", {}).get(
                    "filing_period_sales_tax", 0)

        margin_improving = None  # None = not enough data
        if len(monthly) >= 2 and "gross_margin_pct" in monthly.columns:
            last_two_m = monthly.tail(2)["gross_margin_pct"].values
            margin_improving = bool(last_two_m[-1] > last_two_m[-2])

        c1, c2, c3 = st.columns(3)
        with c1:
            mom_sign = "+" if mom_change >= 0 else ""
            mom_color = "#34D399" if mom_change >= 0 else "#EF4444"
            st.markdown(f"""
            <div class="pp-card-hero">
                <div class="hero-label">Monthly Revenue</div>
                <div class="hero-value">${monthly_rev:,.0f}</div>
                <div class="hero-sub" style="color:{mom_color}">
                    {mom_sign}{mom_change:.1f}% vs last month
                </div>
            </div>""", unsafe_allow_html=True)

        with c2:
            margin = pnl["net_margin_pct"]
            m_cls = "green" if margin >= 10 else ("yellow" if margin >= 0 else "red")
            if margin_improving is None:
                m_sub = f"Net margin {pnl['net_margin_pct']:.1f}%"
            elif margin_improving:
                m_sub = "Margins improving"
            else:
                m_sub = "Margins declining"
            st.markdown(f"""
            <div class="pp-card-hero">
                <div class="hero-label">Profit Margin</div>
                <div class="hero-value {m_cls}">{margin:.1f}%</div>
                <div class="hero-sub">{m_sub}</div>
            </div>""", unsafe_allow_html=True)

        with c3:
            if next_filing_amount > 0:
                st.markdown(f"""
            <div class="pp-card-hero">
                <div class="hero-label">Est. Tax Due</div>
                <div class="hero-value yellow">${next_filing_amount:,.0f}</div>
                <div class="hero-sub">Due in {days_until_due} days</div>
            </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
            <div class="pp-card-hero">
                <div class="hero-label">Est. Tax Due</div>
                <div class="hero-value">—</div>
                <div class="hero-sub">Add data to calculate</div>
            </div>""", unsafe_allow_html=True)


        # ── Quick Sale Button ─────────────────────
        if st.button("➕ Quick Sale", use_container_width=True):
            st.session_state.nav_page = "Data Input"
            st.session_state._data_input_tab = "sales"
            st.rerun()

        # ── Period Comparison (This Month vs Last Month) ─
        import datetime as dt
        sales = st.session_state.df_sales.copy()
        sales['date'] = pd.to_datetime(sales['date'])
        now = dt.datetime.now()
        this_month = sales[sales['date'].dt.month == now.month]
        last_month_df = sales[sales['date'].dt.month == ((now.month - 1) % 12 or 12)]
        rev_this = this_month['amount'].sum() if not this_month.empty else 0
        rev_last = last_month_df['amount'].sum() if not last_month_df.empty else 0
        mom = ((rev_this - rev_last) / rev_last * 100) if rev_last > 0 else 0
        pc1, pc2 = st.columns(2)
        with pc1:
            st.metric("This Month", f"${rev_this:,.0f}", 
                      f"{mom:+.1f}% vs last month" if rev_last > 0 else "No prior data")
        with pc2:
            st.metric("Last Month", f"${rev_last:,.0f}")

        # ── Revenue Trend Chart ──────────────────
        st.markdown("<div style='height:0.5rem'></div>",
                    unsafe_allow_html=True)
        st.markdown("##### Revenue trend")
        if not monthly.empty and "revenue" in monthly.columns:
            n_months = len(monthly)
            period_label = f"Last {n_months} months"

            # Ensure month column is clean string for display
            chart_monthly = monthly.copy()
            chart_monthly["month"] = chart_monthly["month"].astype(str)

            fig = go.Figure()
            colors = [f"rgba(59,130,246,{0.5 + 0.5 * (i/max(len(monthly)-1,1))})"
                      for i in range(len(monthly))]
            fig.add_trace(go.Bar(
                x=chart_monthly["month"],
                y=chart_monthly["revenue"],
                name="Revenue",
                marker_color=colors,
                marker_cornerradius=6,
            ))
            if "net_profit" in monthly.columns:
                fig.add_trace(go.Scatter(
                    x=chart_monthly["month"],
                    y=chart_monthly["net_profit"],
                    name="Net Profit",
                    line=dict(color="#34D399", width=2.5),
                    mode="lines+markers",
                    marker=dict(size=5),
                ))
            layout = dict(**CHART_LAYOUT)
            layout["height"] = 280
            layout["annotations"] = [dict(
                text=period_label,
                x=1, y=1.08, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=11, color="#64748B"),
                xanchor="right",
                bgcolor="rgba(30,41,59,0.8)",
                borderpad=6,
                bordercolor="rgba(148,163,184,0.2)",
                borderwidth=1,
            )]
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Add more data to unlock the revenue trend chart.")

        # ── Quick actions row ────────────────────
        st.markdown("<div style='height:0.5rem'></div>",
                    unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        with q1:
            if st.button("➕ Add Transaction",
                         use_container_width=True, type="primary"):
                jump_to("Data Input")
                st.rerun()
        with q2:
            if st.button("📊 View Full Analytics",
                         use_container_width=True):
                jump_to("Analytics")
                st.rerun()

    with right_col:
        # ── Smart Insights Panel ─────────────────
        render_smart_insights(pnl)

        # ── TaxShield Deadlines Panel ────────────
        render_tax_deadlines(tax)

        # ── Plan badge ───────────────────────────
        st.caption(f"Plan: **{current_plan_label()}**")


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

    if not complete and st.session_state.user_tier != "beta":
        user_tier = st.session_state.get("user_tier", "free")
        is_free = user_tier in {"free", "demo"}

        st.markdown("##### Included with ProfitPulse Complete")
        if is_free:
            st.markdown(
                "Free accounts can preview TaxShield estimates. "
                "Subscribe to Starter (\\$19/mo) or Complete (\\$29/mo) "
                "to unlock the full tool."
            )
        else:
            st.markdown(
                "Starter accounts can preview TaxShield. "
                "Upgrade to Complete (\\$29/mo) for the full tool."
            )
        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric("County-aware estimate", "Included")
        with p2:
            st.metric("Filing cadence", tax["sales_tax"]["filing_frequency_label"])
        with p3:
            st.metric("Annualized revenue basis", f"${tax['annualized_revenue']:,.0f}")

        if is_free:
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("Start with Starter — $19/mo", "https://buy.stripe.com/9B6fZgaaja9Dd0S95H87K01", type="primary")
            with c2:
                st.link_button("Get Complete — $29/mo", "https://buy.stripe.com/8x200ifuDbdH3qichT87K00", type="secondary")
        else:
            st.link_button("Upgrade to Complete — $29/mo", "https://buy.stripe.com/8x200ifuDbdH3qichT87K00", type="primary")
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
        selected_profit_margin_pct = st.slider(
            "Estimated profit margin",
            min_value=0,
            max_value=50,
            value=int(round(float(st.session_state.tax_profit_margin) * 100)),
            step=1,
            format="%d%%",
            key="tax_profit_margin_select",
        )

    st.session_state.tax_county = selected_county
    st.session_state.tax_structure = selected_structure
    st.session_state.tax_filing = selected_filing
    # Convert integer percent back to decimal for downstream calculations
    st.session_state.tax_profit_margin = selected_profit_margin_pct / 100.0
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

    st.markdown("##### Current plan")
    st.info(f"You are currently on **{current_plan_label()}**.")

    if has_complete_access():
        st.success("Complete access is enabled. You can use TaxShield from the main navigation.")
    else:
        user_tier = st.session_state.get("user_tier", "free")
        is_free = user_tier in {"free", "demo"}
        st.warning("Upgrade to Complete to unlock TaxShield and tax planning surfaces across Overview.")

        if is_free:
            st.markdown("##### Choose Your Plan")
            st.markdown("**Starter — $19/mo** — Analytics dashboard, revenue/expense tracking")
            st.link_button("Start Starter — $19/mo", "https://buy.stripe.com/9B6fZgaaja9Dd0S95H87K01", type="primary")
            st.divider()
            st.markdown("**Complete — $29/mo** — Starter + TaxShield, county estimates, filing schedules")
            st.link_button("Get Complete — $29/mo", "https://buy.stripe.com/8x200ifuDbdH3qichT87K00", type="primary")
        else:
            st.markdown("##### Upgrade to Complete")
            st.markdown("**$29/month** — Analytics + Florida TaxShield")
            st.link_button("Upgrade to Complete — $29/mo", "https://buy.stripe.com/8x200ifuDbdH3qichT87K00", type="primary")

    st.caption("ScaleStack On-Premises is a separate white-glove service line. This page only covers ProfitPulse Starter and ProfitPulse Complete.")


def page_settings() -> None:
    import users
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

    st.markdown("---")
    st.markdown("##### ⚠️ Data Management")
    st.caption("Danger zone — these actions cannot be undone.")
    if st.button("🗑 Clear all data", type="secondary", use_container_width=False):
        for key in ["df_sales", "df_purchases", "df_expenses", "df_labor"]:
            st.session_state[key] = pd.DataFrame()
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
        st.session_state.business_type    = None
        st.session_state["_data_loaded"] = False
        st.session_state.nav_page        = "Overview"
        st.session_state.onboarding_step = 0
        _compute_pnl.clear()
        st.toast("All data cleared.", icon="🗑")
        st.rerun()


# ────────────────────────────────────────────────
# PAGE: AI ADVISOR
# ────────────────────────────────────────────────
def page_ai_chat() -> None:
    if st.session_state.user_tier not in {"starter", "complete", "demo", "beta"}:
        st.error("AI Advisor is available on Starter and Complete plans.")
        if st.button("← Back to Overview"):
            jump_to("Overview")
        return

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
    """Render sidebar navigation. Returns selected page name."""
    with st.sidebar:
        # ── Logo + user info ─────────────────────
        st.markdown("""
        <div class="sidebar-logo">
        <span style="font-size:1.8rem; color:#e0e0e0;">◈</span>
        <p style="font-size:1.1rem; font-weight:700;
        color:#F1F5F9; margin:0.3rem 0 0;">
        ProfitPulse
        </p>
        </div>
        """, unsafe_allow_html=True)

        username = st.session_state.get("username", "")
        plan = current_plan_label()
        st.markdown(
            f'<div class="sidebar-user">'
            f'{username} &middot; {plan}'
            f'</div>',
            unsafe_allow_html=True
        )

        if st.session_state.business_type:
            st.markdown(
                f'<div style="text-align:center; font-size:11px; '
                f'color:#475569; padding-bottom:0.75rem;">'
                f'{st.session_state.business_type}'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown('<hr class="nav-divider">', unsafe_allow_html=True)

        # ── Navigation ───────────────────────────
        pending = st.session_state.pop("_pending_nav", None)
        if pending:
            st.session_state.nav_page = pending

        current_page = st.session_state.get("nav_page", "Overview")

        nav_items = [
            ("Overview",   "🏠", True),
            ("Analytics",  "📊", True),
            ("TaxShield",  "🧾", True),
            ("Data Input", "📁", True),
            ("AI Advisor", "🤖",
             st.session_state.user_tier in {"starter","complete","demo","beta"}),
        ]

        for page, icon, visible in nav_items:
            if not visible:
                continue
            is_active = current_page == page
            if st.button(
                    f"{icon} {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
            ):
                st.session_state.nav_page = page
                if "nav_select" in st.session_state:
                    del st.session_state["nav_select"]
                st.rerun()

        st.markdown('<hr class="nav-divider">', unsafe_allow_html=True)

        # ── Secondary nav ────────────────────────
        secondary_items = [
            ("Billing",  "💳"),
            ("Settings", "⚙️"),
            ("Export",   "📤"),
        ]
        for page, icon in secondary_items:
            if st.button(
                    f"{icon} {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
            ):
                st.session_state.nav_page = page
                st.rerun()

        st.markdown('<hr class="nav-divider">', unsafe_allow_html=True)

        # ── AI Pulse (collapsed by default) ─────
        with st.expander("🤖 AI Pulse", expanded=False):
            st.caption("Dynamic insight from your numbers")
            if st.button("Generate Insight",
                         use_container_width=True,
                         key="sidebar_ai_pulse"):
                if st.session_state.df_sales.empty:
                    st.warning("Load data first.")
                else:
                    if not st.session_state.pnl_cache:
                        calculate_pnl()
                    with st.spinner("Analysing…"):
                        insight = call_ai(_ai_pulse_prompt())
                    st.markdown(insight)
            if not st.session_state.pnl_cache:
                st.info("💡 Track every expense category "
                        "separately — vague 'Misc' entries "
                        "hide your biggest cost leaks.")

        # ── Data status ──────────────────────────
        st.markdown("<div style='height:0.5rem'></div>",
                    unsafe_allow_html=True)
        if not st.session_state.df_sales.empty:
            total_rows = sum(
                len(st.session_state[k])
                for k in ["df_sales","df_purchases",
                          "df_expenses","df_labor"]
            )
            st.caption(f"✓ {total_rows:,} records loaded")
            if st.session_state.last_calculated:
                st.caption(
                    f"P&L: {st.session_state.last_calculated}")
        else:
            st.caption("No data loaded")

        st.markdown("<div style='height:0.5rem'></div>",
                    unsafe_allow_html=True)

        # ── Sign out ─────────────────────────────
        if st.button("🚪 Sign out", use_container_width=True,
                     key="sidebar_signout"):
            logout()

        st.markdown("---")

        return st.session_state.get("nav_page", "Overview")


def _main_impl() -> None:
    # Apply theme early
    apply_theme()
    
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Render theme toggle in sidebar
    render_theme_toggle()

    # Load user data ONCE per session (on first authenticated render only).
    # After that, session state is the source of truth — don't overwrite it.
    # This prevents newly added entries from being wiped by a stale reload.
    import users as user_db
    username = st.session_state.get("username", "")
    if username and not st.session_state.get("_data_loaded", False):
        st.session_state.df_sales     = user_db.load_user_data(username, "sales")
        st.session_state.df_purchases = user_db.load_user_data(username, "purchases")
        st.session_state.df_expenses  = user_db.load_user_data(username, "expenses")
        st.session_state.df_labor     = user_db.load_user_data(username, "labor")
        biz_type = user_db.load_user_setting(username, "business_type")
        if biz_type:
            st.session_state.business_type = biz_type
            st.session_state.onboarded     = True
        # Refresh P&L cache so loaded data shows in charts immediately
        _compute_pnl.clear()
        calculate_pnl()
        st.session_state["_data_loaded"] = True

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


def main() -> None:
    try:
        _main_impl()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.button("↻ Reload", on_click=lambda: st.rerun())


if __name__ == "__main__":
    main()
