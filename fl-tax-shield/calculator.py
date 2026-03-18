"""
FL Tax Shield - Florida tax calculator helpers.

These estimates are intentionally conservative and are not a substitute for
state guidance or advice from a CPA.
"""

from __future__ import annotations

from dataclasses import dataclass

STATE_SALES_TAX_RATE = 0.06
DEFAULT_TAXABLE_RATIO = 0.50
DEFAULT_PROFIT_MARGIN = 0.10
CORPORATE_TAX_RATE = 0.055
COLLECTION_ALLOWANCE_RATE = 0.025
COLLECTION_ALLOWANCE_MAX = 30.00

COUNTY_TAX_RATES = {
    "Miami-Dade": 0.07,
    "Broward": 0.07,
    "Palm Beach": 0.07,
    "Hillsborough": 0.075,
    "Pinellas": 0.075,
    "Orange": 0.075,
    "Lee": 0.065,
    "Alachua": 0.085,
    "Baker": 0.07,
    "Bay": 0.075,
    "Bradford": 0.075,
    "Brevard": 0.07,
    "Calhoun": 0.075,
    "Charlotte": 0.07,
    "Citrus": 0.065,
    "Clay": 0.075,
    "Collier": 0.075,
    "Columbia": 0.075,
    "Desoto": 0.075,
    "Dixie": 0.07,
    "Duval": 0.075,
    "Escambia": 0.075,
    "Flagler": 0.07,
    "Franklin": 0.075,
    "Gadsden": 0.075,
    "Gilchrist": 0.075,
    "Glades": 0.075,
    "Gulf": 0.075,
    "Hamilton": 0.08,
    "Hardee": 0.075,
    "Hendry": 0.075,
    "Hernando": 0.07,
    "Highlands": 0.075,
    "Holmes": 0.075,
    "Indian River": 0.07,
    "Jackson": 0.075,
    "Jefferson": 0.075,
    "Lafayette": 0.075,
    "Lake": 0.075,
    "Leon": 0.075,
    "Levy": 0.075,
    "Liberty": 0.07,
    "Madison": 0.08,
    "Manatee": 0.07,
    "Marion": 0.075,
    "Martin": 0.07,
    "Monroe": 0.075,
    "Nassau": 0.075,
    "Okaloosa": 0.07,
    "Okeechobee": 0.075,
    "Osceola": 0.075,
    "Pasco": 0.075,
    "Polk": 0.075,
    "Putnam": 0.075,
    "Santa Rosa": 0.075,
    "Sarasota": 0.07,
    "Seminole": 0.07,
    "St. Johns": 0.075,
    "St. Lucie": 0.07,
    "Sumter": 0.075,
    "Suwannee": 0.075,
    "Taylor": 0.07,
    "Union": 0.07,
    "Volusia": 0.07,
    "Wakulla": 0.075,
    "Walton": 0.075,
    "Washington": 0.075,
}

BUSINESS_TYPE_LABELS = {
    "restaurant": "Restaurant",
    "retail": "Retail",
    "salon": "Salon",
    "spa": "Spa",
    "cleaning": "Cleaning",
    "lawncare": "Lawn Care",
    "landscaping": "Landscaping",
    "contractor": "Contractor",
    "consulting": "Consulting",
    "real_estate": "Real Estate",
    "medical": "Medical",
    "legal": "Legal",
    "accounting": "Accounting",
    "e-commerce": "E-Commerce",
    "dropshipping": "Dropshipping",
    "hotel": "Hotel",
    "short_term_rental": "Short-Term Rental",
    "gym": "Gym",
    "subscriptions": "Subscriptions",
    "other": "Other / Mixed",
}

TAXABLE_SERVICES = {
    "restaurant": 1.0,
    "retail": 1.0,
    "salon": 1.0,
    "spa": 1.0,
    "cleaning": 0.6,
    "lawncare": 0.0,
    "landscaping": 0.0,
    "contractor": 0.0,
    "consulting": 0.0,
    "real_estate": 0.0,
    "medical": 0.0,
    "legal": 0.0,
    "accounting": 0.0,
    "e-commerce": 1.0,
    "dropshipping": 1.0,
    "hotel": 1.0,
    "short_term_rental": 1.0,
    "gym": 1.0,
    "subscriptions": 1.0,
    "other": DEFAULT_TAXABLE_RATIO,
}

STRUCTURE_LABELS = {
    "sole_prop": "Sole Proprietorship",
    "llc": "LLC",
    "s_corp": "S-Corporation",
    "c_corp": "C-Corporation",
}

FILING_FREQUENCY_LABELS = {
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "semiannual": "Semiannual",
    "annual": "Annual",
}

FILING_PERIODS_PER_YEAR = {
    "monthly": 12,
    "quarterly": 4,
    "semiannual": 2,
    "annual": 1,
}


@dataclass(frozen=True)
class FilingPeriod:
    label: str
    due_window: str


def validate_non_negative(value: float, label: str) -> float:
    if value < 0:
        raise ValueError(f"{label} cannot be negative.")
    return value


def normalize_structure(structure: str) -> str:
    key = structure.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in STRUCTURE_LABELS:
        raise ValueError(f"Unsupported business structure: {structure}")
    return key


def normalize_business_type(business_type: str) -> str:
    key = business_type.strip().lower().replace(" ", "_")
    if key not in TAXABLE_SERVICES:
        return "other"
    return key


def normalize_filing_frequency(filing_frequency: str) -> str:
    key = filing_frequency.strip().lower()
    if key not in FILING_PERIODS_PER_YEAR:
        raise ValueError(f"Unsupported filing frequency: {filing_frequency}")
    return key


def get_business_types() -> list[str]:
    return list(BUSINESS_TYPE_LABELS.keys())


def get_county_rate(county: str) -> float:
    return COUNTY_TAX_RATES.get(county, STATE_SALES_TAX_RATE)


def get_filing_periods_per_year(filing_frequency: str) -> int:
    return FILING_PERIODS_PER_YEAR[normalize_filing_frequency(filing_frequency)]


def build_sales_tax_schedule(filing_frequency: str, amount_per_period: float) -> list[dict[str, str | float]]:
    frequency = normalize_filing_frequency(filing_frequency)

    schedules = {
        "monthly": [
            FilingPeriod("January", "Feb 1-Feb 20"),
            FilingPeriod("February", "Mar 1-Mar 20"),
            FilingPeriod("March", "Apr 1-Apr 20"),
            FilingPeriod("April", "May 1-May 20"),
            FilingPeriod("May", "Jun 1-Jun 20"),
            FilingPeriod("June", "Jul 1-Jul 20"),
            FilingPeriod("July", "Aug 1-Aug 20"),
            FilingPeriod("August", "Sep 1-Sep 20"),
            FilingPeriod("September", "Oct 1-Oct 20"),
            FilingPeriod("October", "Nov 1-Nov 20"),
            FilingPeriod("November", "Dec 1-Dec 20"),
            FilingPeriod("December", "Jan 1-Jan 20"),
        ],
        "quarterly": [
            FilingPeriod("Q1 (Jan-Mar)", "Apr 1-Apr 20"),
            FilingPeriod("Q2 (Apr-Jun)", "Jul 1-Jul 20"),
            FilingPeriod("Q3 (Jul-Sep)", "Oct 1-Oct 20"),
            FilingPeriod("Q4 (Oct-Dec)", "Jan 1-Jan 20"),
        ],
        "semiannual": [
            FilingPeriod("H1 (Jan-Jun)", "Jul 1-Jul 20"),
            FilingPeriod("H2 (Jul-Dec)", "Jan 1-Jan 20"),
        ],
        "annual": [
            FilingPeriod("Calendar Year", "Jan 1-Jan 20"),
        ],
    }

    return [
        {
            "period": period.label,
            "due_window": period.due_window,
            "amount": round(amount_per_period, 2),
        }
        for period in schedules[frequency]
    ]


def calculate_sales_tax(
    annual_revenue: float,
    county: str,
    business_type: str,
    filing_frequency: str = "quarterly",
) -> dict:
    annual_revenue = validate_non_negative(annual_revenue, "Annual revenue")
    normalized_business_type = normalize_business_type(business_type)
    normalized_frequency = normalize_filing_frequency(filing_frequency)

    rate = get_county_rate(county)
    taxable_ratio = TAXABLE_SERVICES[normalized_business_type]
    taxable_revenue = annual_revenue * taxable_ratio
    annual_tax = taxable_revenue * rate
    periods_per_year = get_filing_periods_per_year(normalized_frequency)
    filing_amount = annual_tax / periods_per_year if periods_per_year else 0.0

    return {
        "county": county,
        "tax_rate": rate,
        "business_type": normalized_business_type,
        "business_type_label": BUSINESS_TYPE_LABELS[normalized_business_type],
        "filing_frequency": normalized_frequency,
        "filing_frequency_label": FILING_FREQUENCY_LABELS[normalized_frequency],
        "periods_per_year": periods_per_year,
        "taxable_ratio": taxable_ratio,
        "annual_revenue": round(annual_revenue, 2),
        "monthly_revenue": round(annual_revenue / 12, 2),
        "taxable_revenue": round(taxable_revenue, 2),
        "annual_sales_tax": round(annual_tax, 2),
        "monthly_sales_tax": round(annual_tax / 12, 2),
        "filing_period_sales_tax": round(filing_amount, 2),
        "schedule": build_sales_tax_schedule(normalized_frequency, filing_amount),
    }


def calculate_corporate_tax(
    annual_revenue: float,
    structure: str,
    profit_margin: float = DEFAULT_PROFIT_MARGIN,
) -> dict:
    annual_revenue = validate_non_negative(annual_revenue, "Annual revenue")
    profit_margin = validate_non_negative(profit_margin, "Profit margin")
    normalized_structure = normalize_structure(structure)

    if normalized_structure != "c_corp":
        return {
            "structure": normalized_structure,
            "structure_label": STRUCTURE_LABELS[normalized_structure],
            "estimated_profit": 0.0,
            "profit_margin": round(profit_margin, 4),
            "tax_rate": 0.0,
            "annual_corporate_tax": 0.0,
            "quarterly_corporate_tax": 0.0,
            "applies": False,
            "note": "Pass-through entity. Florida corporate income tax typically does not apply.",
        }

    estimated_profit = annual_revenue * profit_margin
    annual_corporate_tax = estimated_profit * CORPORATE_TAX_RATE

    return {
        "structure": normalized_structure,
        "structure_label": STRUCTURE_LABELS[normalized_structure],
        "estimated_profit": round(estimated_profit, 2),
        "profit_margin": round(profit_margin, 4),
        "tax_rate": CORPORATE_TAX_RATE,
        "annual_corporate_tax": round(annual_corporate_tax, 2),
        "quarterly_corporate_tax": round(annual_corporate_tax / 4, 2),
        "applies": True,
        "note": "Estimate only. Corporate tax uses the profit margin you selected.",
    }


def calculate_collection_allowance(annual_tax: float, filing_frequency: str = "quarterly") -> dict:
    annual_tax = validate_non_negative(annual_tax, "Annual sales tax")
    periods_per_year = get_filing_periods_per_year(filing_frequency)
    period_tax = annual_tax / periods_per_year if periods_per_year else 0.0
    allowance_per_filing = min(period_tax * COLLECTION_ALLOWANCE_RATE, COLLECTION_ALLOWANCE_MAX)

    return {
        "filing_frequency": normalize_filing_frequency(filing_frequency),
        "periods_per_year": periods_per_year,
        "per_filing_allowance": round(allowance_per_filing, 2),
        "annual_allowance": round(allowance_per_filing * periods_per_year, 2),
        "note": "Florida allows a timely-filing collection allowance of 2.5% of tax due, capped at $30 per return.",
    }


def generate_report(
    annual_revenue: float,
    county: str,
    structure: str,
    business_type: str,
    filing_frequency: str = "quarterly",
    profit_margin: float = DEFAULT_PROFIT_MARGIN,
) -> str:
    sales_tax = calculate_sales_tax(annual_revenue, county, business_type, filing_frequency)
    corporate_tax = calculate_corporate_tax(annual_revenue, structure, profit_margin)
    allowance = calculate_collection_allowance(
        sales_tax["annual_sales_tax"],
        sales_tax["filing_frequency"],
    )

    lines = [
        "FL TAX SHIELD - Tax Estimate Report",
        "=" * 40,
        f"County: {county}",
        f"Business type: {sales_tax['business_type_label']}",
        f"Structure: {corporate_tax['structure_label']}",
        f"Annual revenue: ${annual_revenue:,.2f}",
        f"Taxable revenue: ${sales_tax['taxable_revenue']:,.2f}",
        f"Sales tax rate: {sales_tax['tax_rate'] * 100:.2f}%",
        f"Annual sales tax: ${sales_tax['annual_sales_tax']:,.2f}",
        (
            f"{sales_tax['filing_frequency_label']} sales tax filing estimate: "
            f"${sales_tax['filing_period_sales_tax']:,.2f}"
        ),
        f"Annual collection allowance: ${allowance['annual_allowance']:,.2f}",
        f"Annual corporate tax: ${corporate_tax['annual_corporate_tax']:,.2f}",
        (
            "Net estimated annual tax: "
            f"${sales_tax['annual_sales_tax'] + corporate_tax['annual_corporate_tax'] - allowance['annual_allowance']:,.2f}"
        ),
        "",
        "Sales tax filing schedule:",
    ]

    for item in sales_tax["schedule"]:
        lines.append(
            f"- {item['period']}: ${item['amount']:,.2f} due {item['due_window']}"
        )

    lines.extend(
        [
            "",
            "Disclaimer: This tool provides estimates only. Consult a CPA and the Florida Department of Revenue for official guidance.",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_report(120000, "Miami-Dade", "llc", "restaurant"))
