"""Tax tips and explanations for common tax form fields (Canada + US)."""

FORM_TIPS = {
    # ═══════════════════════════════════════════════════════════════
    #  CANADIAN FORMS
    # ═══════════════════════════════════════════════════════════════

    # ── T4 ──────────────────────────────────────────────────────
    "t4": {
        "_form": (
            "T4: Statement of Remuneration Paid",
            "Your employer issues a T4 to report your employment income and "
            "deductions for the year. You get one from each employer. This is "
            "the Canadian equivalent of the US W-2. File your return by "
            "April 30 — employers must issue T4s by the end of February.",
        ),
        "employment_income": (
            "Box 14 — Employment Income",
            "Your total employment income before deductions. This is the big "
            "number — it goes on line 10100 of your T1 return. It includes "
            "salary, wages, commissions, bonuses, tips, and taxable benefits.",
        ),
        "income_tax_deducted": (
            "Box 22 — Income Tax Deducted",
            "The total federal and provincial income tax your employer took "
            "off your paycheques. When you file, CRA compares this to what "
            "you actually owe. Over-deducted = refund. Under-deducted = you "
            "owe the difference.",
        ),
        "cpp_contributions": (
            "Box 16 — Employee's CPP Contributions",
            "Your Canada Pension Plan contributions (deducted at 5.95%% of "
            "pensionable earnings between $3,500 and $68,500 for 2024). "
            "You get a non-refundable tax credit for these on Schedule 8. "
            "Your employer matches your contribution.",
        ),
        "cpp2_contributions": (
            "Box 16A — Employee's Second CPP Contributions (CPP2)",
            "Starting 2024, CPP2 applies on earnings between the first and "
            "second earnings ceilings ($68,500–$73,200 for 2024) at 4%%. "
            "You also get a tax credit for these contributions.",
        ),
        "ei_premiums": (
            "Box 18 — Employee's EI Premiums",
            "Employment Insurance premiums deducted (1.66%% of insurable "
            "earnings up to $63,200 for 2024, max $1,049.12). You get a "
            "non-refundable tax credit for these. If you overpaid (e.g. "
            "multiple jobs), you can claim the excess back.",
        ),
        "rpp_contributions": (
            "Box 20 — RPP Contributions",
            "Registered Pension Plan contributions — if your employer has a "
            "workplace pension. These reduce your RRSP room but are "
            "deductible on your return (line 20700).",
        ),
        "union_dues": (
            "Box 44 — Union Dues",
            "Union or professional dues deducted from your pay. Fully "
            "deductible on line 21200 of your return.",
        ),
        "charitable_donations": (
            "Box 46 — Charitable Donations",
            "Donations made through payroll deduction. You get a tax credit: "
            "15%% federal on the first $200, 29%% (or 33%% if income > $235K) "
            "on amounts above $200.",
        ),
        "employer_name": (
            "Employer Information",
            "Your employer's name, address, and payroll account number. "
            "Verify these match your records.",
        ),
    },
    # ── T4A ─────────────────────────────────────────────────────
    "t4a": {
        "_form": (
            "T4A: Statement of Pension, Retirement, Annuity, and Other Income",
            "Covers a variety of income types: pensions, retiring allowances, "
            "self-employed commissions, scholarships, fellowships, research "
            "grants, RESP payments, and other miscellaneous income. Also used "
            "for COVID benefits (CERB, CRB, etc.).",
        ),
        "pension_income": (
            "Box 016 — Pension or Superannuation",
            "Pension income received. If you're 65+, the first $2,000 may "
            "qualify for the pension income tax credit. You may also be "
            "eligible for pension income splitting with a spouse.",
        ),
        "self_employed_commissions": (
            "Box 020 — Self-Employed Commissions",
            "Commission income earned as a self-employed individual. You'll "
            "need to report business income and can deduct related expenses. "
            "You may owe CPP on self-employment income.",
        ),
        "fees_for_services": (
            "Box 048 — Fees for Services",
            "Payments for services rendered. Similar to freelance income — "
            "report as self-employment income if applicable.",
        ),
        "scholarships": (
            "Box 105 — Scholarships, Bursaries, Fellowships",
            "Generally tax-free if you're a full-time student enrolled in a "
            "qualifying program. Part-time students get a $500 exemption. "
            "Research grants may be partially taxable.",
        ),
        "resp_educational": (
            "Box 042 — RESP Educational Assistance Payments",
            "Payments from an RESP. The EAP portion (government grants + "
            "growth) is taxable in the student's hands. The original "
            "contributions come out tax-free.",
        ),
        "income_tax_deducted": (
            "Box 022 — Income Tax Deducted",
            "Income tax withheld from the payments.",
        ),
    },
    # ── T5 ──────────────────────────────────────────────────────
    "t5": {
        "_form": (
            "T5: Statement of Investment Income",
            "Banks, brokerages, and companies issue T5s if you earned $50+ "
            "in investment income (interest, dividends, royalties). Canadian "
            "eligible dividends get a tax credit that significantly reduces "
            "the effective tax rate.",
        ),
        "actual_dividends": (
            "Box 10 — Actual Amount of Eligible Dividends",
            "The actual eligible dividends you received. But you DON'T report "
            "this number — you report the grossed-up amount in Box 25. The "
            "gross-up/credit system makes eligible dividends very tax-efficient.",
        ),
        "taxable_dividends": (
            "Box 25 — Taxable Amount of Eligible Dividends",
            "Eligible dividends grossed up by 38%%. This is what you report "
            "as income. You then get a dividend tax credit (Box 26) that "
            "offsets much of the tax. Effective tax rate on eligible dividends "
            "is much lower than on salary.",
        ),
        "dividend_tax_credit": (
            "Box 26 — Federal Dividend Tax Credit (Eligible)",
            "The federal dividend tax credit for eligible dividends. This "
            "directly reduces your tax owing. Combined with the provincial "
            "credit, eligible dividends are taxed very favourably.",
        ),
        "interest_income": (
            "Box 13 — Interest from Canadian Sources",
            "Interest earned on savings accounts, GICs, bonds, etc. Taxed at "
            "your full marginal rate — the least tax-efficient type of "
            "investment income.",
        ),
        "other_dividends": (
            "Box 11 — Actual Amount of Other Dividends",
            "Non-eligible (ordinary) dividends — typically from small "
            "businesses (CCPCs). Grossed up by 15%% with a smaller tax credit "
            "than eligible dividends.",
        ),
        "foreign_income": (
            "Box 15 — Foreign Income",
            "Foreign investment income in Canadian dollars. You may be able "
            "to claim a foreign tax credit if tax was withheld in the "
            "source country.",
        ),
    },
    # ── T3 ──────────────────────────────────────────────────────
    "t3": {
        "_form": (
            "T3: Statement of Trust Income Allocations and Designations",
            "Issued by mutual fund trusts, income trusts, and estates. If you "
            "hold mutual funds or ETFs outside a registered account (RRSP/TFSA), "
            "you'll get T3s for any distributions. Usually arrives in March.",
        ),
        "actual_dividends": (
            "Box 23 — Actual Eligible Dividends",
            "Eligible dividends allocated to you from the trust. Same "
            "gross-up and credit treatment as T5 eligible dividends.",
        ),
        "capital_gains": (
            "Box 21 — Capital Gains",
            "Capital gains allocated to you. Only 50%% is taxable (the "
            "'taxable capital gain'). The inclusion rate increased to 66.7%% "
            "for gains above $250K starting June 25, 2024.",
        ),
        "foreign_income": (
            "Box 25 — Foreign Non-Business Income",
            "Foreign income from the trust. Report on your return and claim "
            "a foreign tax credit for any foreign tax paid (Box 34).",
        ),
        "other_income": (
            "Box 26 — Other Income",
            "Other income allocated from the trust that doesn't fit the "
            "other categories.",
        ),
        "return_of_capital": (
            "Box 42 — Return of Capital",
            "NOT taxable when received — it reduces your adjusted cost base "
            "(ACB) of the investment. Track this carefully: when you sell, "
            "a lower ACB means a larger capital gain.",
        ),
    },
    # ── T2202 ───────────────────────────────────────────────────
    "t2202": {
        "_form": (
            "T2202: Tuition and Enrolment Certificate",
            "Your school issues this to report eligible tuition fees. You "
            "get a 15%% federal tax credit on eligible tuition. Unused "
            "amounts can be transferred to a parent/spouse (up to $5,000) "
            "or carried forward to future years.",
        ),
        "eligible_tuition": (
            "Box A — Eligible Tuition Fees",
            "Total eligible tuition fees paid. You get a 15%% federal "
            "non-refundable tax credit. Provincial credits vary. "
            "Includes tuition, mandatory fees, but NOT textbooks or "
            "student association fees.",
        ),
        "months_part_time": (
            "Box B — Part-Time Months",
            "Number of months you were a part-time student. Used for "
            "calculating education-related benefits.",
        ),
        "months_full_time": (
            "Box C — Full-Time Months",
            "Number of months you were a full-time student. Important for "
            "scholarship exemptions and other education benefits.",
        ),
    },
    # ── RRSP ────────────────────────────────────────────────────
    "rrsp_receipt": {
        "_form": (
            "RRSP Contribution Receipt",
            "Your financial institution issues this for RRSP contributions. "
            "Contributions are deductible and directly reduce your taxable "
            "income. Your contribution limit is on your latest Notice of "
            "Assessment. Deadline is 60 days after year-end (usually March 1).",
        ),
        "contribution_amount": (
            "Contribution Amount",
            "The amount you contributed to your RRSP. Deductible on line "
            "20800. You don't have to deduct it all in the current year — "
            "you can carry forward unused deductions to a year when you're "
            "in a higher tax bracket.",
        ),
    },
    # ── T4E ─────────────────────────────────────────────────────
    "t4e": {
        "_form": (
            "T4E: Statement of Employment Insurance and Other Benefits",
            "Reports EI benefits received during the year. EI is taxable "
            "income. If your net income exceeds ~$79K, you may have to "
            "repay some or all of the benefits (EI clawback).",
        ),
        "ei_benefits": (
            "Box 14 — Total EI Benefits Paid",
            "Total EI regular, maternity, parental, sickness, or fishing "
            "benefits received. Fully taxable as income.",
        ),
        "income_tax_deducted": (
            "Box 22 — Income Tax Deducted",
            "Tax withheld from your EI payments.",
        ),
    },
    # ── T4RSP ───────────────────────────────────────────────────
    "t4rsp": {
        "_form": (
            "T4RSP: Statement of RRSP Income",
            "Reports withdrawals from your RRSP. Withdrawals are fully "
            "taxable as income (except HBP or LLP repayments). Tax is "
            "withheld at source: 10%% up to $5K, 20%% on $5K-$15K, "
            "30%% over $15K.",
        ),
        "withdrawal_amount": (
            "Box 22 — Withdrawal/Annuity Amount",
            "Amount withdrawn from your RRSP. Added to your income for "
            "the year. You also permanently lose that RRSP contribution "
            "room — it doesn't come back.",
        ),
        "income_tax_deducted": (
            "Box 30 — Income Tax Deducted",
            "Tax withheld at source on the withdrawal. This is just "
            "withholding — you may owe more or get some back depending "
            "on your total income for the year.",
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    #  US FORMS (kept for cross-border / US income scenarios)
    # ═══════════════════════════════════════════════════════════════

    # ── W-2 Fields ──────────────────────────────────────────────
    "w2": {
        "_form": (
            "W-2: Wage and Tax Statement (US)",
            "Your US employer sends this to report your annual wages and the "
            "taxes withheld from your paycheck. If you have US-source "
            "employment income, you'll report this on your Canadian return "
            "and claim a foreign tax credit for US taxes paid.",
        ),
        "wages_tips": (
            "Box 1 — Wages, Tips, Other Compensation",
            "Total taxable wages, tips, and other compensation. Convert to "
            "CAD using the Bank of Canada annual average exchange rate for "
            "your Canadian return.",
        ),
        "federal_tax_withheld": (
            "Box 2 — Federal Income Tax Withheld",
            "US federal income tax withheld. You can claim a foreign tax "
            "credit on your Canadian return for this (Form T2209).",
        ),
        "social_security_wages": (
            "Box 3 — Social Security Wages",
            "Wages subject to US Social Security tax.",
        ),
        "social_security_tax": (
            "Box 4 — Social Security Tax Withheld",
            "Social Security tax withheld (6.2%%).",
        ),
        "medicare_wages": (
            "Box 5 — Medicare Wages and Tips",
            "Wages subject to US Medicare tax.",
        ),
        "medicare_tax": (
            "Box 6 — Medicare Tax Withheld",
            "Medicare tax withheld (1.45%%).",
        ),
        "state_wages": (
            "Box 16 — State Wages",
            "Wages subject to US state income tax.",
        ),
        "state_tax_withheld": (
            "Box 17 — State Income Tax Withheld",
            "US state income tax withheld. Also eligible for foreign tax "
            "credit on your Canadian return.",
        ),
        "employer_name": (
            "Employer Information",
            "Your US employer's name, address, and EIN.",
        ),
    },
    # ── 1099-INT ────────────────────────────────────────────────
    "1099_int": {
        "_form": (
            "1099-INT: Interest Income (US)",
            "US banks/institutions send this for $10+ in interest. Report "
            "on your Canadian return as foreign income (convert to CAD).",
        ),
        "interest_income": (
            "Box 1 — Interest Income",
            "US-source taxable interest. Convert to CAD for your T1 return.",
        ),
        "federal_tax_withheld": (
            "Box 4 — Federal Income Tax Withheld",
            "US tax withheld — claim as foreign tax credit.",
        ),
    },
    # ── 1099-DIV ────────────────────────────────────────────────
    "1099_div": {
        "_form": (
            "1099-DIV: Dividends and Distributions (US)",
            "US dividends. Report on your Canadian return as foreign income. "
            "US dividends do NOT qualify for the Canadian dividend tax credit.",
        ),
        "ordinary_dividends": (
            "Box 1a — Total Ordinary Dividends",
            "All US dividends paid to you. Convert to CAD.",
        ),
        "qualified_dividends": (
            "Box 1b — Qualified Dividends",
            "US qualified dividends. Taxed at lower US rates, but on your "
            "Canadian return they're just foreign income at your marginal rate.",
        ),
        "capital_gains": (
            "Box 2a — Total Capital Gain Distributions",
            "US capital gain distributions. 50%% inclusion rate in Canada.",
        ),
        "federal_tax_withheld": (
            "Box 4 — Federal Income Tax Withheld",
            "US withholding tax — claim as foreign tax credit in Canada.",
        ),
    },
    # ── 1099-NEC ────────────────────────────────────────────────
    "1099_nec": {
        "_form": (
            "1099-NEC: Nonemployee Compensation (US)",
            "US freelance/contract income of $600+. Report as self-employment "
            "income on your Canadian return. You may owe CPP contributions.",
        ),
        "nonemployee_compensation": (
            "Box 1 — Nonemployee Compensation",
            "US contract payments. Convert to CAD. Deduct related business "
            "expenses.",
        ),
        "federal_tax_withheld": (
            "Box 4 — Federal Income Tax Withheld",
            "US withholding — claim as foreign tax credit.",
        ),
    },
    # ── 1099-MISC ───────────────────────────────────────────────
    "1099_misc": {
        "_form": (
            "1099-MISC: Miscellaneous Income (US)",
            "Various US income types: rents, royalties, prizes.",
        ),
        "rents": ("Box 1 — Rents", "US rental income. Convert to CAD."),
        "royalties": ("Box 2 — Royalties", "US royalty income. Convert to CAD."),
        "other_income": ("Box 3 — Other Income", "US miscellaneous income."),
        "federal_tax_withheld": ("Box 4 — Federal Income Tax Withheld", "US withholding."),
    },
    # ── 1098 ────────────────────────────────────────────────────
    "1098": {
        "_form": (
            "1098: Mortgage Interest Statement (US)",
            "US mortgage interest. Generally not deductible on Canadian "
            "returns unless the property generates rental income.",
        ),
        "mortgage_interest": ("Box 1 — Mortgage Interest Received", "US mortgage interest paid."),
        "points_paid": ("Box 6 — Points Paid on Purchase", "Mortgage points."),
    },
    "1098_t": {
        "_form": (
            "1098-T: Tuition Statement (US)",
            "US tuition. Canadian residents attending US schools can claim "
            "the tuition tax credit if the school is on the CRA's list of "
            "designated educational institutions.",
        ),
        "tuition_paid": ("Box 1 — Qualified Tuition Payments", "US tuition paid."),
        "scholarships": ("Box 5 — Scholarships or Grants", "Scholarships received."),
    },
    "1098_e": {
        "_form": (
            "1098-E: Student Loan Interest (US)",
            "US student loan interest. Not deductible on Canadian returns "
            "(Canada only allows interest on Canadian student loans).",
        ),
        "interest_paid": ("Box 1 — Student Loan Interest", "US student loan interest paid."),
    },
}

# ── Canadian General Tax Tips ───────────────────────────────────
GENERAL_TIPS = [
    {
        "title": "Basic Personal Amount (BPA)",
        "tip": (
            "Every Canadian gets a federal basic personal amount — $15,705 "
            "for 2024. You pay $0 federal tax on income up to this amount "
            "(15%% credit = $2,355 saved). Provincial BPAs vary."
        ),
    },
    {
        "title": "RRSP — Your Best Tax Deduction",
        "tip": (
            "RRSP contributions directly reduce your taxable income. If "
            "you're in the 29%% bracket, a $10,000 contribution saves you "
            "$2,900 in federal tax alone. Contribution limit is 18%% of "
            "prior year earned income (max $31,560 for 2024). Deadline: "
            "60 days after year-end. Check your limit on your Notice of "
            "Assessment or MyCRA."
        ),
    },
    {
        "title": "TFSA — Tax-Free Growth",
        "tip": (
            "TFSA contributions aren't deductible, but ALL growth and "
            "withdrawals are tax-free forever. 2024 limit: $7,000. "
            "Cumulative room since 2009: $95,000 (if you were 18+ and a "
            "resident for all years). Unused room carries forward. "
            "Withdrawals re-open room the following January."
        ),
    },
    {
        "title": "Tuition Tax Credit — Don't Lose It",
        "tip": (
            "15%% federal credit on eligible tuition (T2202). If you don't "
            "owe enough tax to use it all, you can transfer up to $5,000 "
            "to a parent, grandparent, or spouse. The rest carries forward "
            "indefinitely. File your return even if you owe $0 — otherwise "
            "CRA doesn't know about your carryforward."
        ),
    },
    {
        "title": "CPP/EI Overpayment — Multiple Employers",
        "tip": (
            "If you had multiple jobs, each employer deducts CPP and EI as "
            "if they're your only employer. You may have overpaid. The CRA "
            "auto-calculates this on your return and refunds the excess. "
            "Max employee CPP for 2024: $3,867.50. Max EI: $1,049.12."
        ),
    },
    {
        "title": "Medical Expenses — The 3%% Threshold",
        "tip": (
            "You can claim medical expenses that exceed 3%% of your net "
            "income (or $2,759, whichever is less). This includes dental, "
            "prescriptions, glasses, travel for medical care, and premiums "
            "for private health insurance. Claim on the return of the "
            "lower-income spouse for a better credit."
        ),
    },
    {
        "title": "Moving Expenses — If You Moved for Work/School",
        "tip": (
            "If you moved 40+ km closer to a new job or full-time school, "
            "you can deduct moving expenses: travel, temporary lodging, "
            "meals, lease cancellation, legal fees on new home, and more. "
            "Claim on line 21900."
        ),
    },
    {
        "title": "Home Office Deduction",
        "tip": (
            "If you worked from home, you can claim home office expenses. "
            "The detailed method lets you deduct the proportional share of "
            "rent, utilities, internet, and supplies. Keep receipts and "
            "get a signed T2200 or T2200S from your employer."
        ),
    },
    {
        "title": "Charitable Donations — The First-Time Super Credit",
        "tip": (
            "Federal credit: 15%% on first $200, 29%% (33%% if income > "
            "$235K) on the rest. You can carry forward donations for up to "
            "5 years to bundle them above $200 for the higher rate. "
            "First-time donor? You may get an extra 25%% credit on up to "
            "$1,000 (check eligibility)."
        ),
    },
    {
        "title": "Keep Records for 6 Years",
        "tip": (
            "CRA can reassess your return up to 3 years after your Notice "
            "of Assessment (6 years in some cases). Keep all tax slips, "
            "receipts, and records for at least 6 years."
        ),
    },
    {
        "title": "File Even If You Owe Nothing",
        "tip": (
            "Always file your return. Even if you owe $0, you need to file "
            "to get: GST/HST credit, Canada Child Benefit, provincial "
            "benefits, RRSP room calculation, tuition credit carryforward, "
            "and to avoid issues with CRA."
        ),
    },
]

# Map form types to display names
FORM_DISPLAY_NAMES = {
    # Canadian forms (shown first)
    "t4": "T4",
    "t4a": "T4A",
    "t4e": "T4E",
    "t4rsp": "T4RSP",
    "t5": "T5",
    "t3": "T3",
    "t2202": "T2202",
    "rrsp_receipt": "RRSP Receipt",
    # US forms
    "w2": "W-2 (US)",
    "1099_int": "1099-INT (US)",
    "1099_div": "1099-DIV (US)",
    "1099_nec": "1099-NEC (US)",
    "1099_misc": "1099-MISC (US)",
    "1098": "1098 (US)",
    "1098_t": "1098-T (US)",
    "1098_e": "1098-E (US)",
}
