"""Streamlit app for Florida tax estimate planning."""

from __future__ import annotations

import streamlit as st

from calculator import (
    BUSINESS_TYPE_LABELS,
    COUNTY_TAX_RATES,
    DEFAULT_PROFIT_MARGIN,
    FILING_FREQUENCY_LABELS,
    STRUCTURE_LABELS,
    calculate_collection_allowance,
    calculate_corporate_tax,
    calculate_sales_tax,
    get_business_types,
)


st.set_page_config(page_title="FL Tax Shield", page_icon="Shield", layout="wide")

st.markdown(
    """
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .hero {
        background: linear-gradient(135deg, #f3f7ff 0%, #dbeafe 55%, #e0f2fe 100%);
        border: 1px solid #bfdbfe;
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
    }
    .hero h1 {
        color: #0f172a;
        margin-bottom: 0.3rem;
    }
    .hero p {
        color: #334155;
        font-size: 1rem;
        margin-bottom: 0;
    }
    .note-card {
        background: #fff7ed;
        border-left: 4px solid #f97316;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        color: #7c2d12;
        margin-top: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    return f"${value:,.2f}"


def build_county_rows() -> list[dict[str, str | float]]:
    return [
        {"County": county, "Rate": f"{rate * 100:.2f}%", "Numeric Rate": rate}
        for county, rate in sorted(COUNTY_TAX_RATES.items(), key=lambda item: (-item[1], item[0]))
    ]


st.markdown(
    """
<div class="hero">
    <h1>FL Tax Shield</h1>
    <p>Estimate Florida sales tax, filing cadence, and C-corp exposure with cleaner assumptions and clearer quarterly planning.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Business Inputs")

    counties = sorted(COUNTY_TAX_RATES)
    selected_county = st.selectbox(
        "Florida county",
        counties,
        index=counties.index("Miami-Dade") if "Miami-Dade" in counties else 0,
    )

    business_type = st.selectbox(
        "Business type",
        get_business_types(),
        format_func=lambda value: BUSINESS_TYPE_LABELS[value],
    )

    monthly_revenue = st.number_input(
        "Monthly gross revenue",
        min_value=0.0,
        value=10000.0,
        step=500.0,
        format="%.2f",
    )

    entity_type = st.selectbox(
        "Business structure",
        list(STRUCTURE_LABELS.keys()),
        index=list(STRUCTURE_LABELS.keys()).index("llc"),
        format_func=lambda value: STRUCTURE_LABELS[value],
    )

    filing_frequency = st.selectbox(
        "Sales tax filing frequency",
        list(FILING_FREQUENCY_LABELS.keys()),
        index=list(FILING_FREQUENCY_LABELS.keys()).index("quarterly"),
        format_func=lambda value: FILING_FREQUENCY_LABELS[value],
        help="Florida assigns filing frequency based on expected collections. This selector changes the schedule and allowance estimate.",
    )

    profit_margin = st.slider(
        "Estimated profit margin for C-corp tax",
        min_value=0.0,
        max_value=0.5,
        value=DEFAULT_PROFIT_MARGIN,
        step=0.01,
        format="%.0f%%",
        help="Only used when the business structure is C-corporation.",
    )

annual_revenue = monthly_revenue * 12
sales_tax = calculate_sales_tax(annual_revenue, selected_county, business_type, filing_frequency)
corporate_tax = calculate_corporate_tax(annual_revenue, entity_type, profit_margin)
allowance = calculate_collection_allowance(sales_tax["annual_sales_tax"], filing_frequency)
net_annual_tax = (
    sales_tax["annual_sales_tax"]
    + corporate_tax["annual_corporate_tax"]
    - allowance["annual_allowance"]
)

top_left, top_right = st.columns([2, 1], gap="large")

with top_left:
    st.subheader("📊 Estimate Snapshot")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.metric("Annual Revenue", money(annual_revenue))
        st.metric("Sales Tax (Annual)", money(sales_tax["annual_sales_tax"]))
    with col2:
        st.metric(f"{sales_tax['filing_frequency_label']} Filing", money(sales_tax["filing_period_sales_tax"]))
        st.metric("Net Annual Estimate", money(net_annual_tax), delta_color="inverse")

    st.subheader("📋 Tax Details")
    d1, d2, d3 = st.columns(3, gap="large")
    with d1:
        st.metric("Taxable Revenue", money(sales_tax["taxable_revenue"]))
    with d2:
        st.metric("Collection Allowance", money(allowance["annual_allowance"]), help=allowance["note"])
    with d3:
        st.metric("Corporate Tax", money(corporate_tax["annual_corporate_tax"]), help=corporate_tax["note"])

    st.subheader("Tax Basis")
    st.write(f"County rate: **{sales_tax['tax_rate'] * 100:.2f}%**")
    st.write(f"Business type assumption: **{sales_tax['business_type_label']}**")
    st.write(f"Taxable ratio assumption: **{sales_tax['taxable_ratio'] * 100:.0f}%** of gross revenue")
    st.write(f"Sales tax filing cadence: **{sales_tax['filing_frequency_label']}**")
    st.write(f"Business structure: **{corporate_tax['structure_label']}**")

    if corporate_tax["applies"]:
        st.info(
            "C-corp tax estimate uses your selected profit margin rather than assuming all revenue is taxable income."
        )
    else:
        st.success("Florida corporate income tax is not estimated for pass-through entities in this tool.")

with top_right:
    st.subheader("Filing Schedule")
    st.dataframe(sales_tax["schedule"], hide_index=True, width='stretch')
    st.markdown(
        f"""
<div class="note-card">
    Timely filing allowance estimate: <strong>{money(allowance['per_filing_allowance'])}</strong> per return,<br>
    capped at $30 each filing period.
</div>
""",
        unsafe_allow_html=True,
    )

st.subheader("Annual View")
annual_chart_rows = [
    {"Category": "Sales tax", "Amount": sales_tax["annual_sales_tax"]},
    {"Category": "Corporate tax", "Amount": corporate_tax["annual_corporate_tax"]},
    {"Category": "Collection allowance", "Amount": -allowance["annual_allowance"]},
]
st.bar_chart(annual_chart_rows, x="Category", y="Amount", horizontal=False)

county_col, assumptions_col = st.columns([1.2, 1])

with county_col:
    st.subheader("County Rates")
    st.dataframe(build_county_rows(), hide_index=True, width='stretch')

with assumptions_col:
    st.subheader("Assumptions and Limits")
    st.markdown(
        """
- Sales tax is estimated from county rate times the modeled taxable share of revenue.
- Collection allowance is based on filing frequency and Florida's $30 per return cap.
- Corporate income tax is only modeled for C-corporations.
- This app does not replace product-level taxability rules, exemptions, or nexus analysis.
"""
    )

st.markdown("---")
st.caption(
    "Estimate only. Confirm taxability, filing frequency, and official rates with the Florida Department of Revenue or a CPA before filing."
)
