"""Tax deadline calculations for Canadian residents."""

from datetime import date, datetime, timedelta


def get_deadlines(tax_year: int, today: date = None) -> list[dict]:
    """Get all relevant tax deadlines for a given tax year.

    Returns a list of {name, date, days_until, description, urgent} dicts,
    sorted by date.
    """
    if today is None:
        today = date.today()

    # File year is tax_year + 1 (e.g. 2024 taxes are filed in 2025)
    file_year = tax_year + 1

    # ── RRSP contribution deadline ──
    # 60 days after year-end (typically March 1 or first business day)
    rrsp_deadline = date(file_year, 3, 1)
    if rrsp_deadline.weekday() == 5:
        rrsp_deadline = rrsp_deadline + timedelta(days=2)
    elif rrsp_deadline.weekday() == 6:
        rrsp_deadline = rrsp_deadline + timedelta(days=1)

    # ── Tax filing deadline (most people) ──
    filing_deadline = date(file_year, 4, 30)
    if filing_deadline.weekday() == 5:
        filing_deadline = filing_deadline + timedelta(days=2)
    elif filing_deadline.weekday() == 6:
        filing_deadline = filing_deadline + timedelta(days=1)

    # ── Self-employed filing deadline ──
    se_filing_deadline = date(file_year, 6, 15)
    if se_filing_deadline.weekday() == 5:
        se_filing_deadline = se_filing_deadline + timedelta(days=2)
    elif se_filing_deadline.weekday() == 6:
        se_filing_deadline = se_filing_deadline + timedelta(days=1)

    deadlines = [
        {
            "name": "RRSP Contribution Deadline",
            "date": rrsp_deadline,
            "description": (
                f"Last day to contribute to your RRSP for the {tax_year} tax year. "
                f"Contributions reduce your taxable income."
            ),
        },
        {
            "name": "Tax Return Filing Deadline",
            "date": filing_deadline,
            "description": (
                f"Most Canadians must file their {tax_year} tax return by this date. "
                f"Filing late = 5% penalty + 1% per month."
            ),
        },
        {
            "name": "Self-Employed Filing Deadline",
            "date": se_filing_deadline,
            "description": (
                f"If you or your spouse had self-employment income in {tax_year}, "
                f"you have until June 15 to file. BUT any tax owing is still due April 30."
            ),
        },
    ]

    # Filter to upcoming deadlines (or just passed within 30 days)
    upcoming = []
    for d in deadlines:
        days_until = (d["date"] - today).days
        d["days_until"] = days_until
        d["urgent"] = 0 < days_until <= 30
        d["passed"] = days_until < 0
        if days_until >= -30:  # Show up to 30 days past
            upcoming.append(d)

    upcoming.sort(key=lambda x: x["date"])
    return upcoming


def format_deadline_text(deadline: dict) -> str:
    """Format a deadline as a short status string."""
    days = deadline["days_until"]
    if days < 0:
        return f"{abs(days)} days ago"
    if days == 0:
        return "TODAY"
    if days == 1:
        return "TOMORROW"
    return f"in {days} days ({deadline['date'].strftime('%b %d, %Y')})"
