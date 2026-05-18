"""Canadian tax calculator — estimates federal + provincial tax owing/refund.

Uses 2024 tax brackets. Provincial brackets included for all provinces/territories.
"""

# ─── 2024 Federal Brackets ──────────────────────────────────────
FEDERAL_BRACKETS_2024 = [
    (55867, 0.15),
    (111733, 0.205),
    (173205, 0.26),
    (246752, 0.29),
    (float("inf"), 0.33),
]

# Federal Basic Personal Amount 2024 (phased out at high income)
FEDERAL_BPA_2024 = 15705
FEDERAL_BPA_PHASEOUT_START = 173205
FEDERAL_BPA_PHASEOUT_END = 246752
FEDERAL_BPA_MIN = 14156  # Minimum BPA at high income

# ─── 2024 Provincial Brackets ───────────────────────────────────
PROVINCIAL_BRACKETS_2024 = {
    "ON": [  # Ontario
        (51446, 0.0505),
        (102894, 0.0915),
        (150000, 0.1116),
        (220000, 0.1216),
        (float("inf"), 0.1316),
    ],
    "BC": [  # British Columbia
        (47937, 0.0506),
        (95875, 0.077),
        (110076, 0.105),
        (133664, 0.1229),
        (181232, 0.147),
        (252752, 0.168),
        (float("inf"), 0.205),
    ],
    "AB": [  # Alberta
        (148269, 0.10),
        (177922, 0.12),
        (237230, 0.13),
        (355845, 0.14),
        (float("inf"), 0.15),
    ],
    "SK": [  # Saskatchewan
        (52057, 0.105),
        (148734, 0.125),
        (float("inf"), 0.145),
    ],
    "MB": [  # Manitoba
        (47000, 0.108),
        (100000, 0.1275),
        (float("inf"), 0.174),
    ],
    "QC": [  # Quebec
        (51780, 0.14),
        (103545, 0.19),
        (126000, 0.24),
        (float("inf"), 0.2575),
    ],
    "NB": [  # New Brunswick
        (49958, 0.094),
        (99916, 0.14),
        (185064, 0.16),
        (float("inf"), 0.195),
    ],
    "NS": [  # Nova Scotia
        (29590, 0.0879),
        (59180, 0.1495),
        (93000, 0.1667),
        (150000, 0.175),
        (float("inf"), 0.21),
    ],
    "PE": [  # Prince Edward Island
        (32656, 0.0965),
        (64313, 0.1363),
        (105000, 0.1665),
        (140000, 0.18),
        (float("inf"), 0.1875),
    ],
    "NL": [  # Newfoundland and Labrador
        (43198, 0.087),
        (86395, 0.145),
        (154244, 0.158),
        (215943, 0.178),
        (275870, 0.198),
        (551739, 0.208),
        (1103478, 0.213),
        (float("inf"), 0.218),
    ],
    "YT": [  # Yukon
        (55867, 0.064),
        (111733, 0.09),
        (173205, 0.109),
        (500000, 0.128),
        (float("inf"), 0.15),
    ],
    "NT": [  # Northwest Territories
        (50597, 0.059),
        (101198, 0.086),
        (164525, 0.122),
        (float("inf"), 0.1405),
    ],
    "NU": [  # Nunavut
        (53268, 0.04),
        (106537, 0.07),
        (173205, 0.09),
        (float("inf"), 0.115),
    ],
}

# Provincial Basic Personal Amounts 2024
PROVINCIAL_BPA_2024 = {
    "ON": 12399,
    "BC": 12580,
    "AB": 21885,
    "SK": 18491,
    "MB": 15780,
    "QC": 18056,
    "NB": 13044,
    "NS": 8744,  # Higher amount for income < $25K, lower for > $75K
    "PE": 13500,
    "NL": 10818,
    "YT": 15705,
    "NT": 17373,
    "NU": 18767,
}

# Lowest provincial tax rate (used for non-refundable credits)
PROVINCIAL_LOWEST_RATE = {
    "ON": 0.0505, "BC": 0.0506, "AB": 0.10, "SK": 0.105, "MB": 0.108,
    "QC": 0.14, "NB": 0.094, "NS": 0.0879, "PE": 0.0965, "NL": 0.087,
    "YT": 0.064, "NT": 0.059, "NU": 0.04,
}

PROVINCE_NAMES = {
    "ON": "Ontario", "BC": "British Columbia", "AB": "Alberta",
    "SK": "Saskatchewan", "MB": "Manitoba", "QC": "Quebec",
    "NB": "New Brunswick", "NS": "Nova Scotia", "PE": "Prince Edward Island",
    "NL": "Newfoundland and Labrador", "YT": "Yukon",
    "NT": "Northwest Territories", "NU": "Nunavut",
}


def apply_brackets(income: float, brackets: list[tuple[float, float]]) -> float:
    """Apply progressive tax brackets to an income amount.

    brackets is a list of (upper_threshold, rate) tuples.
    """
    if income <= 0:
        return 0.0
    tax = 0.0
    prev_threshold = 0.0
    for threshold, rate in brackets:
        if income <= threshold:
            tax += (income - prev_threshold) * rate
            return tax
        tax += (threshold - prev_threshold) * rate
        prev_threshold = threshold
    return tax


def federal_bpa(income: float) -> float:
    """Calculate the Federal Basic Personal Amount based on income (it phases down)."""
    if income <= FEDERAL_BPA_PHASEOUT_START:
        return FEDERAL_BPA_2024
    if income >= FEDERAL_BPA_PHASEOUT_END:
        return FEDERAL_BPA_MIN
    # Linear phaseout
    range_total = FEDERAL_BPA_PHASEOUT_END - FEDERAL_BPA_PHASEOUT_START
    income_in_range = income - FEDERAL_BPA_PHASEOUT_START
    reduction = (FEDERAL_BPA_2024 - FEDERAL_BPA_MIN) * (income_in_range / range_total)
    return FEDERAL_BPA_2024 - reduction


def calculate_estimated_tax(summary: dict, province: str = "ON") -> dict:
    """Estimate federal + provincial tax owing/refund based on the summary.

    Returns a dict with breakdown of tax calculation and final refund/owing.
    """
    province = province.upper()
    if province not in PROVINCIAL_BRACKETS_2024:
        province = "ON"  # Default to Ontario

    # ── Step 1: Compute taxable income ──
    total_income = summary.get("total_income", 0)

    # Gross up eligible dividends by 38% (Box 25 from T5 if not already)
    # If T5 has actual dividends (not grossed up), we need to gross up
    eligible_div = summary.get("total_eligible_dividends", 0)
    grossed_up_div = eligible_div * 1.38
    # The 'actual' dividend is already in total_income — replace with grossed-up
    gross_up_addition = grossed_up_div - eligible_div

    # Capital gains: only 50% is taxable (simplification — 2024 had a mid-year change)
    capital_gains = summary.get("total_capital_gains", 0)
    taxable_capital_gains = capital_gains * 0.5
    capital_gains_adjustment = taxable_capital_gains - capital_gains  # negative if cap gains > 0

    # Adjusted gross income
    adjusted_income = total_income + gross_up_addition + capital_gains_adjustment

    # ── Step 2: Apply deductions ──
    rrsp_deduction = summary.get("total_rrsp_contributions", 0)
    rpp_deduction = summary.get("total_rpp_contributions", 0)
    union_dues = summary.get("total_union_dues", 0)
    total_deductions = rrsp_deduction + rpp_deduction + union_dues

    net_income = max(0, adjusted_income - total_deductions)
    taxable_income = net_income  # Simplified — ignores complex adjustments

    # ── Step 3: Calculate federal tax ──
    federal_tax = apply_brackets(taxable_income, FEDERAL_BRACKETS_2024)

    # Federal non-refundable credits (15% rate)
    federal_bpa_amount = federal_bpa(net_income)
    cpp = summary.get("total_cpp_contributions", 0)
    ei = summary.get("total_ei_premiums", 0)
    tuition = summary.get("total_tuition", 0)

    federal_credits = (federal_bpa_amount + cpp + ei + tuition) * 0.15

    # Eligible dividend tax credit (15.0198% of grossed-up amount)
    div_tax_credit_fed = grossed_up_div * 0.150198

    federal_tax_after_credits = max(0, federal_tax - federal_credits - div_tax_credit_fed)

    # ── Step 4: Calculate provincial tax ──
    prov_brackets = PROVINCIAL_BRACKETS_2024[province]
    prov_tax = apply_brackets(taxable_income, prov_brackets)

    # Provincial credits (at lowest provincial rate)
    prov_bpa = PROVINCIAL_BPA_2024.get(province, 12000)
    prov_lowest = PROVINCIAL_LOWEST_RATE.get(province, 0.05)
    prov_credits = (prov_bpa + cpp + ei + tuition) * prov_lowest

    # Provincial dividend tax credit (varies by province, simplified estimate)
    div_tax_credit_prov = grossed_up_div * 0.10  # rough average

    prov_tax_after_credits = max(0, prov_tax - prov_credits - div_tax_credit_prov)

    # ── Step 5: Total tax owing ──
    total_tax = federal_tax_after_credits + prov_tax_after_credits

    # Self-employment CPP (both employer + employee = 11.9% on net SE income above $3,500)
    se_income = summary.get("total_self_employment", 0)
    se_cpp = max(0, (se_income - 3500)) * 0.119 if se_income > 3500 else 0
    total_tax += se_cpp

    # ── Step 6: Compare to amounts already deducted ──
    tax_already_paid = summary.get("total_income_tax_deducted", 0)
    refund_or_owing = tax_already_paid - total_tax

    return {
        "province": province,
        "province_name": PROVINCE_NAMES.get(province, province),
        "gross_income": total_income,
        "gross_up_addition": gross_up_addition,
        "capital_gains_adjustment": capital_gains_adjustment,
        "adjusted_income": adjusted_income,
        "total_deductions": total_deductions,
        "taxable_income": taxable_income,
        "federal_tax_before_credits": federal_tax,
        "federal_credits": federal_credits + div_tax_credit_fed,
        "federal_tax": federal_tax_after_credits,
        "provincial_tax_before_credits": prov_tax,
        "provincial_credits": prov_credits + div_tax_credit_prov,
        "provincial_tax": prov_tax_after_credits,
        "se_cpp_owing": se_cpp,
        "total_tax": total_tax,
        "tax_already_paid": tax_already_paid,
        "refund_or_owing": refund_or_owing,
        "is_refund": refund_or_owing >= 0,
        "marginal_rate_federal": _get_marginal_rate(taxable_income, FEDERAL_BRACKETS_2024),
        "marginal_rate_provincial": _get_marginal_rate(taxable_income, prov_brackets),
    }


def _get_marginal_rate(income: float, brackets: list[tuple[float, float]]) -> float:
    """Find the marginal tax rate at a given income."""
    for threshold, rate in brackets:
        if income <= threshold:
            return rate
    return brackets[-1][1]


# ── T1 Line Number Mapping ──────────────────────────────────────
# Maps summary fields → T1 line numbers for the cheat sheet
T1_LINE_MAP = [
    ("Line 10100", "Employment income", "total_employment_income"),
    ("Line 10400", "Other employment income", None),
    ("Line 11300", "Old Age Security pension", None),
    ("Line 11400", "CPP or QPP benefits", None),
    ("Line 11500", "Other pensions and superannuation", "total_pension_income"),
    ("Line 11900", "Employment insurance benefits", "total_ei_benefits"),
    ("Line 12000", "Taxable amount of dividends (grossed up)", "total_eligible_dividends_grossed"),
    ("Line 12100", "Interest and other investment income", "total_interest_income"),
    ("Line 12700", "Taxable capital gains (50% of total)", "total_capital_gains_taxable"),
    ("Line 12900", "RRSP income", "total_rrsp_withdrawals"),
    ("Line 13000", "Other income", "total_other_income"),
    ("Line 13700", "Self-employment income", "total_self_employment"),
    ("Line 15000", "Total income", "total_income_adjusted"),
    ("Line 20700", "Registered Pension Plan deduction", "total_rpp_contributions"),
    ("Line 20800", "RRSP deduction", "total_rrsp_contributions"),
    ("Line 21200", "Annual union, professional, or like dues", "total_union_dues"),
    ("Line 22215", "Deduction for CPP enhanced contributions", None),
    ("Line 23600", "Net income", "net_income"),
    ("Line 30000", "Basic personal amount", "federal_bpa"),
    ("Line 30800", "CPP/QPP contributions through employment", "total_cpp_contributions"),
    ("Line 31200", "EI premiums through employment", "total_ei_premiums"),
    ("Line 32300", "Tuition amount", "total_tuition"),
    ("Line 40500", "Foreign tax credit", "total_us_tax_withheld"),
    ("Line 43700", "Total income tax deducted", "total_income_tax_deducted"),
]
