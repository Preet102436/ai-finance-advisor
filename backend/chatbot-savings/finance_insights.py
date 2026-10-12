"""
Chatbot & Savings Recommendation Subsystem - financial reasoning layer
Owner: Thiwanka Kaushalya Nagasanga

Sits on top of finance_data.py's raw transaction/budget loaders and adds a
real financial-summary view (income, expenses, savings, per-category budget
comparison, month-over-month deltas), plus deterministic (non-LLM) answers
for the specific question types the chat assistant needs to support:
affordability checks, overspending, a monthly summary, savings tips, a
next-month budget suggestion, a savings-goal plan, and "what if" projections.

These are computed in plain Python so they are correct and available even
when the LLM call fails, is slow, or no OPENAI_API_KEY is configured at all
(a real risk on the day, given campus network restrictions) - the LLM is
only ever asked to add a short narrative on top of these numbers, never to
invent them.
"""

import re
from datetime import date, datetime, timedelta
from statistics import mean

GENERIC_TIPS = (
    "I don't have any transaction history for you yet, so here's general guidance: a common "
    "rule of thumb is the 50/30/20 split - about 50% of income to needs, 30% to wants, and 20% "
    "to savings. Once you sync a bank account, add a transaction, or upload a receipt, I can give "
    "you advice based on your real numbers instead."
)

_AMOUNT_RE = re.compile(r"\$?\s?([0-9][0-9,]*(?:\.[0-9]{1,2})?)")
_MONTHS_RE = re.compile(r"(\d+)\s*month")
_WEEKS_RE = re.compile(r"(\d+)\s*week")


def _parse_date(d):
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _extract_amount(text):
    m = _AMOUNT_RE.search(text.replace(",", ""))
    return float(m.group(1)) if m else None


def _extract_months(text):
    m = _MONTHS_RE.search(text.lower())
    return int(m.group(1)) if m else None


def _extract_weeks(text):
    m = _WEEKS_RE.search(text.lower())
    return int(m.group(1)) if m else None


def compute_financial_summary(transactions, budgets=None, as_of=None):
    """transactions: list of {date, category, amount, merchant} dicts (as
    returned by finance_data.load_user_transactions). budgets: {category: amount}.

    Returns a dict summarising income/expenses/savings and a per-category
    breakdown for the current calendar month, plus the previous calendar
    month (for month-over-month deltas)."""
    budgets = budgets or {}
    as_of = as_of or date.today()
    this_month_start = as_of.replace(day=1)
    prev_month_end = this_month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    def _in_range(txn, start, end):
        d = _parse_date(txn["date"])
        return start <= d <= end

    this_month = [t for t in transactions if _in_range(t, this_month_start, as_of)]
    prev_month = [t for t in transactions if _in_range(t, prev_month_start, prev_month_end)]

    def _totals(rows):
        income = sum(t["amount"] for t in rows if t["amount"] > 0)
        expenses = sum(-t["amount"] for t in rows if t["amount"] < 0)
        by_category = {}
        for t in rows:
            if t["amount"] < 0:
                by_category[t["category"]] = by_category.get(t["category"], 0) + (-t["amount"])
        return income, expenses, by_category

    income, expenses, category_totals = _totals(this_month)
    _prev_income, _prev_expenses, prev_category_totals = _totals(prev_month)

    savings = income - expenses
    savings_rate = (savings / income) if income > 0 else None

    category_vs_budget = []
    for category, budget_amount in budgets.items():
        spent = category_totals.get(category, 0)
        category_vs_budget.append({
            "category": category,
            "spent": round(spent, 2),
            "budget": round(budget_amount, 2),
            "remaining": round(budget_amount - spent, 2),
            "over_budget": spent > budget_amount,
        })
    category_vs_budget.sort(key=lambda c: c["spent"], reverse=True)

    category_deltas = []
    for category, amount in category_totals.items():
        prev_amount = prev_category_totals.get(category, 0)
        if prev_amount > 0:
            pct_change = ((amount - prev_amount) / prev_amount) * 100
        elif amount > 0:
            pct_change = None  # new category this month, no baseline to compare to
        else:
            pct_change = 0
        category_deltas.append({
            "category": category,
            "this_month": round(amount, 2),
            "last_month": round(prev_amount, 2),
            "pct_change": round(pct_change, 1) if pct_change is not None else None,
        })
    category_deltas.sort(key=lambda c: c["this_month"], reverse=True)

    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate * 100, 1) if savings_rate is not None else None,
        "top_category": category_deltas[0]["category"] if category_deltas else None,
        "category_vs_budget": category_vs_budget,
        "category_deltas": category_deltas,
        "has_data": bool(this_month) or bool(prev_month),
        "transaction_count": len(transactions),
    }


def financial_health_score(summary):
    """A simple, transparent 0-100 score: starts at a neutral 50, moves up
    with a healthy savings rate, and down for every category currently over
    its budget. Not a real credit-style score - just a quick at-a-glance
    number for the dashboard."""
    if summary["transaction_count"] == 0:
        return None
    score = 50
    if summary["savings_rate"] is not None:
        score += max(min(summary["savings_rate"], 40), -40) * 0.75
    over_count = sum(1 for c in summary["category_vs_budget"] if c["over_budget"])
    score -= over_count * 8
    return round(max(0, min(100, score)))


def detect_intent(question):
    q = question.lower()
    if "afford" in q:
        return "affordability"
    if "what if" in q:
        return "what_if"
    if ("save" in q or "saving" in q) and (_extract_months(q) or _extract_weeks(q)) and _extract_amount(question):
        return "savings_goal"
    if "budget" in q and ("create" in q or "generate" in q or "next month" in q or "make" in q or "suggest" in q):
        return "budget_generator"
    if "overspend" in q or "overspending" in q or "spending too much" in q or "where am i spending" in q:
        return "overspending"
    if "save more" in q or "how can i save" in q or "increase my savings" in q or "save money" in q:
        return "savings_tips"
    if "summary" in q or "how am i doing" in q or "how am i tracking" in q:
        return "monthly_summary"
    return "general"


def answer_affordability(question, summary):
    amount = _extract_amount(question)
    if amount is None:
        return None
    available = summary["savings"] if summary["savings"] > 0 else 0
    if available >= amount:
        remaining = available - amount
        return (
            f"Based on this month so far, you have about ${available:.2f} left after your usual "
            f"expenses, so a ${amount:.2f} purchase looks affordable - that would leave roughly "
            f"${remaining:.2f}. This is a rough estimate from your recent transactions, not financial advice."
        )
    shortfall = amount - available
    return (
        f"Based on this month so far, you have about ${available:.2f} available after your usual "
        f"expenses, which is ${shortfall:.2f} short of ${amount:.2f}. You could wait until your next "
        f"pay cycle, or trim a discretionary category first"
        + (f" like {summary['top_category']}" if summary["top_category"] else "")
        + ". This is a rough estimate, not financial advice."
    )


def answer_savings_goal(question, summary):
    target = _extract_amount(question)
    months = _extract_months(question)
    weeks = _extract_weeks(question)
    if target is None or (months is None and weeks is None):
        return None

    if weeks is not None:
        periods, label = weeks, "week"
    else:
        periods, label = months, "month"

    per_period = target / periods if periods else target
    text = f"To save ${target:.2f} in {periods} {label}s, you'd need to set aside about ${per_period:.2f} per {label}."

    current_monthly_savings = summary["savings"]
    if current_monthly_savings > 0:
        current_per_period = current_monthly_savings if label == "month" else current_monthly_savings / 4
        gap = per_period - current_per_period
        if gap > 0:
            text += (
                f" You're currently averaging about ${current_monthly_savings:.2f} saved this month, "
                f"so you'd need to find roughly ${gap:.2f} more per {label}"
                + (f" - your biggest category right now is {summary['top_category']}, worth a look" if summary["top_category"] else "")
                + "."
            )
        else:
            text += f" At your current pace of about ${current_monthly_savings:.2f} saved this month, you're already on track."
    else:
        text += " You're not currently saving anything most months, so this will take cutting expenses, increasing income, or both."
    return text


def answer_what_if(question, summary):
    amount = _extract_amount(question)
    if amount is None:
        return None
    projections = {m: amount * m for m in (3, 6, 12)}
    return (
        f"Cutting about ${amount:.2f} a month would add up to ${projections[3]:.2f} over 3 months, "
        f"${projections[6]:.2f} over 6 months, and ${projections[12]:.2f} over 12 months, on top of "
        f"whatever you're already saving (currently about ${summary['savings']:.2f} this month)."
    )


def answer_budget_generator(summary):
    if not summary["category_deltas"]:
        return None
    lines = []
    for c in summary["category_deltas"][:6]:
        suggested = round(c["this_month"] * 0.9, 2) if c["this_month"] > 0 else 0
        lines.append(f"- {c['category']}: ${suggested:.2f} (about 10% below this month's ${c['this_month']:.2f})")
    return (
        "Here's a suggested budget for next month, trimming each category about 10% below what "
        "you actually spent this month:\n" + "\n".join(lines)
    )


def answer_overspending(summary):
    over = [c for c in summary["category_vs_budget"] if c["over_budget"]]
    if over:
        lines = [
            f"- {c['category']}: ${c['spent']:.2f} spent vs a ${c['budget']:.2f} budget "
            f"(${c['spent'] - c['budget']:.2f} over)"
            for c in over
        ]
        return "You're over budget in:\n" + "\n".join(lines)
    if summary["category_deltas"]:
        top = summary["category_deltas"][0]
        return (
            f"You're not over any set budget right now. Your biggest category this month is "
            f"{top['category']} at ${top['this_month']:.2f}."
        )
    return None


def answer_monthly_summary(summary):
    text = (
        f"This month so far: ${summary['income']:.2f} in, ${summary['expenses']:.2f} out, "
        f"leaving about ${summary['savings']:.2f} saved"
    )
    if summary["savings_rate"] is not None:
        text += f" (a {summary['savings_rate']:.1f}% savings rate)"
    text += "."
    if summary["category_deltas"]:
        top = summary["category_deltas"][0]
        change_text = ""
        if top["pct_change"] is not None:
            direction = "up" if top["pct_change"] > 0 else "down"
            change_text = f", {direction} {abs(top['pct_change']):.0f}% from last month"
        text += f" Your biggest category is {top['category']} at ${top['this_month']:.2f}{change_text}."
    return text


def answer_savings_tips(summary):
    if not summary["category_deltas"]:
        return None
    top = summary["category_deltas"][:3]
    lines = [f"- {c['category']}: ${c['this_month']:.2f} this month" for c in top]
    return (
        "Your top spending categories this month are:\n" + "\n".join(lines) +
        f"\n\nTrimming your biggest one, {top[0]['category']}, even by 10-15% would make the "
        "fastest difference to your savings."
    )


def deterministic_answer(question, summary):
    """Returns a ready-to-show answer string for question types this module
    can compute exactly, or None if the question needs the general RAG+LLM
    path in chatbot_prototype.py instead."""
    if summary["transaction_count"] == 0:
        return GENERIC_TIPS

    intent = detect_intent(question)
    if intent == "affordability":
        return answer_affordability(question, summary)
    if intent == "what_if":
        return answer_what_if(question, summary)
    if intent == "savings_goal":
        return answer_savings_goal(question, summary)
    if intent == "budget_generator":
        return answer_budget_generator(summary)
    if intent == "overspending":
        return answer_overspending(summary)
    if intent == "monthly_summary":
        return answer_monthly_summary(summary)
    if intent == "savings_tips":
        return answer_savings_tips(summary)
    return None


def build_summary_context_block(summary):
    """Human-readable financial summary, used both as LLM context (for
    "general" questions that don't match a deterministic intent) and as the
    final fallback answer text if the LLM is unavailable."""
    lines = [
        f"Income this month: ${summary['income']:.2f}",
        f"Expenses this month: ${summary['expenses']:.2f}",
        f"Savings this month: ${summary['savings']:.2f}"
        + (f" ({summary['savings_rate']:.1f}% savings rate)" if summary["savings_rate"] is not None else ""),
    ]
    if summary["category_vs_budget"]:
        lines.append("Budget comparison:")
        for c in summary["category_vs_budget"][:8]:
            status = "OVER" if c["over_budget"] else "within budget"
            lines.append(f"  - {c['category']}: ${c['spent']:.2f} spent of ${c['budget']:.2f} budget ({status})")
    if summary["category_deltas"]:
        lines.append("Top spending categories this month:")
        for c in summary["category_deltas"][:5]:
            lines.append(f"  - {c['category']}: ${c['this_month']:.2f}")
    return "\n".join(lines)


def scan_money_radar(summary):
    """Proactive scan for things worth flagging right now: categories over
    budget, categories whose spend has jumped sharply vs last month, and a
    negative savings rate. Returns a list of alert dicts ready for the
    frontend's Money Radar panel - each with a suggested follow-up question
    so a card's "Ask AI" button can go straight into the chat."""
    if summary["transaction_count"] == 0:
        return []

    alerts = []

    if summary["savings_rate"] is not None and summary["savings_rate"] < 0:
        alerts.append({
            "id": "negative-savings",
            "severity": "high",
            "icon": "\U0001F6A8",
            "title": "Spending more than you earn",
            "message": (
                f"This month you've spent ${summary['expenses']:.2f} against "
                f"${summary['income']:.2f} in income - about "
                f"{abs(summary['savings_rate']):.0f}% over."
            ),
            "category": None,
            "suggested_question": "How can I get back to positive savings this month?",
        })

    for c in summary["category_vs_budget"]:
        if not c["over_budget"]:
            continue
        overspend = c["spent"] - c["budget"]
        pct_over = (overspend / c["budget"] * 100) if c["budget"] > 0 else 0
        alerts.append({
            "id": f"over-budget-{c['category']}",
            "severity": "high" if pct_over >= 20 else "medium",
            "icon": "\U0001F4B8",
            "title": f"{c['category']} is over budget",
            "message": (
                f"${overspend:.2f} over your ${c['budget']:.2f} {c['category']} budget "
                f"(${c['spent']:.2f} spent so far)."
            ),
            "category": c["category"],
            "suggested_question": f"How can I cut back on {c['category']} spending?",
        })

    for c in summary["category_deltas"]:
        if c["pct_change"] is None or c["pct_change"] < 50 or c["this_month"] < 20:
            continue
        alerts.append({
            "id": f"rising-{c['category']}",
            "severity": "medium",
            "icon": "\U0001F4C8",
            "title": f"{c['category']} spending is rising",
            "message": (
                f"Up {c['pct_change']:.0f}% vs last month "
                f"(${c['last_month']:.2f} -> ${c['this_month']:.2f})."
            ),
            "category": c["category"],
            "suggested_question": f"Why did my {c['category']} spending go up?",
        })

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_rank.get(a["severity"], 3))
    return alerts


_DEFAULT_FOLLOWUPS = [
    "Analyse my spending",
    "How can I save more?",
    "Where am I spending too much?",
]

_NO_DATA_FOLLOWUPS = [
    "Add a transaction",
    "Link my bank account",
    "Upload a receipt",
]


def suggested_followups(intent, summary):
    """A few contextual follow-up questions to show as buttons under the
    assistant's last answer, instead of always showing the same static
    quick-prompt chips."""
    if summary.get("transaction_count", 0) == 0:
        return list(_NO_DATA_FOLLOWUPS)

    top_category = summary.get("top_category")

    if intent == "affordability":
        return [
            "What could I cut to make this easier?",
            "How does this affect my savings this month?",
        ]
    if intent == "overspending":
        options = []
        if top_category:
            options.append(f"How can I cut back on {top_category}?")
        options.append("Create a budget for next month")
        return options
    if intent == "budget_generator":
        return ["Am I overspending anywhere right now?", "What if I saved $50 more a week?"]
    if intent == "savings_goal":
        return ["How can I save more?", "Create a budget for next month"]
    if intent == "what_if":
        return ["Create a budget based on this", "How can I save more?"]
    if intent == "monthly_summary":
        options = ["How can I save more?"]
        if top_category:
            options.append(f"Am I overspending on {top_category}?")
        return options
    if intent == "savings_tips":
        return ["Create a budget for next month", "Am I over budget anywhere?"]
    return list(_DEFAULT_FOLLOWUPS)
# ---------------------------------------------------------------------------
# AI Statement Insights - date-range statement analysis
#
# The functions above all work from a fixed "this calendar month vs last
# calendar month" window (compute_financial_summary). The AI Statement
# Insights feature (backend/api/routers/insights.py's /statement/* routes)
# lets the user pick ANY date range, so the functions below are the same
# kind of reasoning (totals, category breakdown, budget comparison, period
# deltas, recurring-charge detection) generalised to an explicit start/end
# window instead of being pinned to a calendar month.
# ---------------------------------------------------------------------------


def compute_period_totals(transactions, budgets=None):
    """Income/expenses/savings/category breakdown/budget comparison for
    whatever `transactions` list the caller passes in - already filtered to
    a date range by finance_data.load_user_transactions, so this function
    itself does no date filtering."""
    budgets = budgets or {}
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expenses = sum(-t["amount"] for t in transactions if t["amount"] < 0)

    category_totals = {}
    category_counts = {}
    for t in transactions:
        if t["amount"] < 0:
            category_totals[t["category"]] = category_totals.get(t["category"], 0) + (-t["amount"])
            category_counts[t["category"]] = category_counts.get(t["category"], 0) + 1

    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else None

    category_breakdown = sorted(
        [
            {"category": c, "total": round(v, 2), "count": category_counts[c]}
            for c, v in category_totals.items()
        ],
        key=lambda c: c["total"],
        reverse=True,
    )

    category_vs_budget = []
    for category, budget_amount in budgets.items():
        spent = category_totals.get(category, 0)
        category_vs_budget.append({
            "category": category,
            "spent": round(spent, 2),
            "budget": round(budget_amount, 2),
            "remaining": round(budget_amount - spent, 2),
            "over_budget": spent > budget_amount,
        })
    category_vs_budget.sort(key=lambda c: c["spent"], reverse=True)

    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate, 1) if savings_rate is not None else None,
        "transaction_count": len(transactions),
        "category_breakdown": category_breakdown,
        "category_vs_budget": category_vs_budget,
    }


def compute_period_comparison(current_totals, previous_totals):
    """Percentage change for income/expenses/savings and for each category
    appearing in either period, current vs. the immediately preceding
    equal-length period (the caller works out what "previous" means - this
    just compares two already-computed compute_period_totals() results)."""

    def _pct(cur, prev):
        if prev > 0:
            return round((cur - prev) / prev * 100, 1)
        if cur > 0:
            return None  # new this period, no baseline to compare to
        return 0.0

    overall = {
        "income_pct_change": _pct(current_totals["income"], previous_totals["income"]),
        "expenses_pct_change": _pct(current_totals["expenses"], previous_totals["expenses"]),
        "savings_pct_change": _pct(current_totals["savings"], previous_totals["savings"]),
    }

    prev_by_category = {c["category"]: c["total"] for c in previous_totals["category_breakdown"]}
    cur_by_category = {c["category"]: c["total"] for c in current_totals["category_breakdown"]}

    categories = []
    for category in set(prev_by_category) | set(cur_by_category):
        cur = cur_by_category.get(category, 0)
        prev = prev_by_category.get(category, 0)
        categories.append({
            "category": category,
            "current": round(cur, 2),
            "previous": round(prev, 2),
            "pct_change": _pct(cur, prev),
        })
    categories.sort(key=lambda c: c["current"], reverse=True)

    return {"overall": overall, "categories": categories}


def detect_recurring_expenses(transactions, min_occurrences=2):
    """Groups transactions by merchant and flags ones that repeat at a
    roughly regular interval (weekly/fortnightly/monthly) with a roughly
    consistent amount - a simple stand-in for "this looks like a
    subscription or regular bill" without needing a dedicated subscriptions
    table. Pass a reasonably long lookback window - you need at least two
    occurrences to see any pattern at all."""
    by_merchant = {}
    for t in transactions:
        merchant = (t.get("merchant") or "").strip()
        if not merchant or t["amount"] >= 0:
            continue
        key = merchant.lower()
        by_merchant.setdefault(key, {"display": merchant, "rows": []})
        by_merchant[key]["rows"].append(t)

    frequency_buckets = [
        ("weekly", 5, 9),
        ("fortnightly", 12, 16),
        ("monthly", 25, 35),
    ]

    recurring = []
    for data in by_merchant.values():
        rows = sorted(data["rows"], key=lambda t: t["date"])
        if len(rows) < min_occurrences:
            continue

        dates = [_parse_date(t["date"]) for t in rows]
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        if not gaps:
            continue
        avg_gap = mean(gaps)

        frequency = None
        for label, lo, hi in frequency_buckets:
            if lo <= avg_gap <= hi:
                frequency = label
                break
        if frequency is None:
            continue

        # Consistent interval: every gap within 40% of the average.
        if any(abs(g - avg_gap) > avg_gap * 0.4 for g in gaps):
            continue

        amounts = [abs(t["amount"]) for t in rows]
        avg_amount = mean(amounts)
        if avg_amount > 0 and any(abs(a - avg_amount) > avg_amount * 0.2 for a in amounts):
            continue

        recurring.append({
            "merchant": data["display"],
            "frequency": frequency,
            "average_amount": round(avg_amount, 2),
            "occurrences": len(rows),
            "last_seen": rows[-1]["date"],
            "transactions": rows,
        })

    recurring.sort(key=lambda r: r["average_amount"] * r["occurrences"], reverse=True)
    return recurring


def build_period_context_block(totals, start_date, end_date):
    """Human-readable financial summary for an explicit date range - the
    period-scoped equivalent of build_summary_context_block(), used both as
    LLM context and as the deterministic fallback answer/narrative text."""
    lines = [
        f"Period: {start_date} to {end_date}",
        f"Income: ${totals['income']:.2f}",
        f"Expenses: ${totals['expenses']:.2f}",
        f"Net savings: ${totals['savings']:.2f}"
        + (f" ({totals['savings_rate']:.1f}% savings rate)" if totals["savings_rate"] is not None else ""),
        f"Transactions: {totals['transaction_count']}",
    ]
    if totals["category_breakdown"]:
        lines.append("Spending by category:")
        for c in totals["category_breakdown"][:8]:
            lines.append(f"  - {c['category']}: ${c['total']:.2f} ({c['count']} transactions)")
    if totals["category_vs_budget"]:
        lines.append("Budget comparison:")
        for c in totals["category_vs_budget"][:8]:
            status = "OVER" if c["over_budget"] else "within budget"
            lines.append(f"  - {c['category']}: ${c['spent']:.2f} spent of ${c['budget']:.2f} budget ({status})")
    return "\n".join(lines)
