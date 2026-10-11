"""GET /insights/summary - a real financial snapshot for the current user
(income/expenses/savings this month, savings rate, top categories, budget
comparison) plus a simple Financial Health Score, both computed by
finance_insights.py and reused by the chat assistant, the dashboard's
Monthly Summary and Financial Health Score cards, and Budget Alerts.

GET /insights/money-radar - a proactive scan (no question needed) for things
worth the user's attention right now: categories over budget, categories
whose spend is rising sharply vs last month, and a negative savings rate.
Each alert carries a ready-to-ask follow-up question so the Chat page's
Money Radar panel can send it straight into the chat with one click.
"""

import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from chatbot_prototype import (
    build_context_block,
    build_prompt,
    call_llm,
    generate_savings_suggestions_detailed,
    retrieve_relevant_transactions,
)
from database import get_db
from deps import get_current_user
from finance_data import load_user_budgets, load_user_transactions
from finance_insights import (
    build_period_context_block,
    compute_financial_summary,
    compute_period_comparison,
    compute_period_totals,
    detect_recurring_expenses,
    financial_health_score,
    scan_money_radar,
)
from forecast_prototype import detect_anomalies
from models import User

router = APIRouter(prefix="/insights", tags=["insights"])


class CategoryVsBudgetOut(BaseModel):
    category: str
    spent: float
    budget: float
    remaining: float
    over_budget: bool


class CategoryDeltaOut(BaseModel):
    category: str
    this_month: float
    last_month: float
    pct_change: float | None = None


class FinancialSummaryOut(BaseModel):
    income: float
    expenses: float
    savings: float
    savings_rate: float | None = None
    top_category: str | None = None
    category_vs_budget: list[CategoryVsBudgetOut]
    category_deltas: list[CategoryDeltaOut]
    transaction_count: int
    health_score: int | None = None


class MoneyRadarAlertOut(BaseModel):
    id: str
    severity: str
    icon: str
    title: str
    message: str
    category: str | None = None
    suggested_question: str


class CategoryAmountOut(BaseModel):
    category: str
    total: float
    count: int


class PeriodTotalsOut(BaseModel):
    income: float
    expenses: float
    savings: float
    savings_rate: float | None = None
    transaction_count: int
    category_breakdown: list[CategoryAmountOut]
    category_vs_budget: list[CategoryVsBudgetOut]


class CategoryComparisonOut(BaseModel):
    category: str
    current: float
    previous: float
    pct_change: float | None = None


class PeriodComparisonOverallOut(BaseModel):
    income_pct_change: float | None = None
    expenses_pct_change: float | None = None
    savings_pct_change: float | None = None


class PeriodComparisonOut(BaseModel):
    previous_start_date: date
    previous_end_date: date
    overall: PeriodComparisonOverallOut
    categories: list[CategoryComparisonOut]


class EvidenceTransactionOut(BaseModel):
    id: int | None = None
    date: str
    category: str
    merchant: str
    amount: float


class KeyInsightOut(BaseModel):
    id: str
    severity: str
    title: str
    text: str
    evidence: list[EvidenceTransactionOut] = []


class UnusualTransactionOut(BaseModel):
    evidence: EvidenceTransactionOut
    z_score: float
    reason: str


class RecurringExpenseOut(BaseModel):
    merchant: str
    frequency: str
    average_amount: float
    occurrences: int
    last_seen: str
    evidence: list[EvidenceTransactionOut]


class SavingOpportunityOut(BaseModel):
    category: str
    overspend: float
    suggestion: str
    evidence: list[EvidenceTransactionOut] = []


class StatementAnalysisOut(BaseModel):
    start_date: date
    end_date: date
    totals: PeriodTotalsOut
    period_comparison: PeriodComparisonOut
    key_insights: list[KeyInsightOut]
    unusual_transactions: list[UnusualTransactionOut]
    recurring_expenses: list[RecurringExpenseOut]
    saving_opportunities: list[SavingOpportunityOut]
    ai_summary: str
    ai_generated: bool


class StatementAskRequest(BaseModel):
    start_date: date
    end_date: date
    question: str


class StatementAskResponse(BaseModel):
    answer: str
    sources: list[str]
    evidence: list[EvidenceTransactionOut]
    ai_generated: bool


@router.get("/summary", response_model=FinancialSummaryOut)
def get_financial_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_user_transactions(db, current_user.user_id, lookback_days=120)
    budgets = load_user_budgets(db, current_user.user_id)
    summary = compute_financial_summary(transactions, budgets)
    score = financial_health_score(summary)

    return FinancialSummaryOut(
        income=summary["income"],
        expenses=summary["expenses"],
        savings=summary["savings"],
        savings_rate=summary["savings_rate"],
        top_category=summary["top_category"],
        category_vs_budget=summary["category_vs_budget"],
        category_deltas=summary["category_deltas"],
        transaction_count=summary["transaction_count"],
        health_score=score,
    )


@router.get("/money-radar", response_model=list[MoneyRadarAlertOut])
def get_money_radar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_user_transactions(db, current_user.user_id, lookback_days=120)
    budgets = load_user_budgets(db, current_user.user_id)
    summary = compute_financial_summary(transactions, budgets)
    alerts = scan_money_radar(summary)
    return [MoneyRadarAlertOut(**a) for a in alerts]



def _statement_totals(transactions):
    """income, expenses (both positive numbers), and category -> total
    spent, sorted highest-spend first - same convention compute_financial_
    summary uses, just over whatever date range was asked for instead of a
    fixed "this calendar month"."""
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expenses = sum(-t["amount"] for t in transactions if t["amount"] < 0)
    by_category: dict[str, float] = {}
    for t in transactions:
        if t["amount"] < 0:
            by_category[t["category"]] = by_category.get(t["category"], 0) + (-t["amount"])
    category_rows = sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
    return round(income, 2), round(expenses, 2), [(c, round(v, 2)) for c, v in category_rows]


def _statement_csv(full_name, start_date, end_date, income, expenses, savings, savings_rate, category_rows, transactions):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["AI Finance Advisor - Financial Statement"])
    writer.writerow(["Account holder", full_name])
    writer.writerow(["Period", f"{start_date.isoformat()} to {end_date.isoformat()}"])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total income", f"{income:.2f}"])
    writer.writerow(["Total expenses", f"{expenses:.2f}"])
    writer.writerow(["Net savings", f"{savings:.2f}"])
    writer.writerow(["Savings rate", f"{savings_rate:.1f}%" if savings_rate is not None else "n/a"])
    writer.writerow([])
    writer.writerow(["Spending by category"])
    writer.writerow(["Category", "Total spent"])
    for category, total in category_rows:
        writer.writerow([category, f"{total:.2f}"])
    writer.writerow([])
    writer.writerow(["Transactions"])
    writer.writerow(["Date", "Category", "Merchant", "Amount"])
    for t in transactions:
        writer.writerow([t["date"], t["category"], t["merchant"], f"{t['amount']:.2f}"])
    return buf.getvalue()


def _statement_pdf(full_name, start_date, end_date, income, expenses, savings, savings_rate, category_rows, transactions):
    # Imported lazily so a backend that hasn't picked up the new
    # `reportlab` dependency yet (see requirements.txt) still starts fine
    # and every other route keeps working - only this PDF path 404/501s
    # until `pip install -r requirements.txt` is re-run.
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError(
            "PDF export needs the 'reportlab' package, which isn't installed yet. "
            "Run: pip install -r requirements.txt (then restart the backend). "
            "CSV export works right now without it."
        ) from exc

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("AI Finance Advisor - Financial Statement", styles["Title"]),
        Paragraph(f"Account holder: {full_name}", styles["Normal"]),
        Paragraph(f"Period: {start_date.isoformat()} to {end_date.isoformat()}", styles["Normal"]),
        Spacer(1, 8 * mm),
        Paragraph("Summary", styles["Heading2"]),
    ]

    summary_table = Table(
        [
            ["Total income", f"${income:,.2f}"],
            ["Total expenses", f"${expenses:,.2f}"],
            ["Net savings", f"${savings:,.2f}"],
            ["Savings rate", f"{savings_rate:.1f}%" if savings_rate is not None else "n/a"],
        ],
        colWidths=[80 * mm, 60 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Spending by category", styles["Heading2"]))
    cat_rows = [["Category", "Total spent"]]
    if category_rows:
        cat_rows += [[c, f"${v:,.2f}"] for c, v in category_rows]
    else:
        cat_rows.append(["No spending in this period", "-"])
    cat_table = Table(cat_rows, colWidths=[100 * mm, 40 * mm], repeatRows=1)
    cat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6FFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 6 * mm))

    shown = transactions[:500]
    elements.append(Paragraph(f"Transactions ({len(transactions)})", styles["Heading2"]))
    txn_rows = [["Date", "Category", "Merchant", "Amount"]]
    txn_rows += [[t["date"], t["category"], t["merchant"] or "-", f"${t['amount']:,.2f}"] for t in shown]
    txn_table = Table(txn_rows, colWidths=[25 * mm, 40 * mm, 55 * mm, 25 * mm], repeatRows=1)
    txn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6FFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(txn_table)
    if len(transactions) > len(shown):
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f"...and {len(transactions) - len(shown)} more transaction(s) not shown here - "
            "download the CSV for the complete list.",
            styles["Normal"],
        ))

    doc.build(elements)
    return buf.getvalue()


def _to_evidence(t):
    return EvidenceTransactionOut(
        id=t.get("id"), date=t["date"], category=t["category"],
        merchant=t["merchant"], amount=t["amount"],
    )


def _build_key_insights(totals, previous_totals, comparison, unusual, recurring, saving_opportunities, transactions):
    """Deterministic, individually-cited findings - the structured content
    the AI Statement Insights page shows with "View evidence" links. Kept
    separate from the free-text ai_summary paragraph (below) so every claim
    here always traces back to real transactions, whether or not an LLM is
    reachable."""
    insights = []

    if totals["category_breakdown"]:
        top = totals["category_breakdown"][0]
        top_delta = next((c for c in comparison["categories"] if c["category"] == top["category"]), None)
        change_text = ""
        if top_delta and top_delta["pct_change"] is not None:
            direction = "up" if top_delta["pct_change"] > 0 else "down"
            change_text = f", {direction} {abs(top_delta['pct_change']):.0f}% versus the previous period"
        evidence = [_to_evidence(t) for t in transactions if t["category"] == top["category"]][:5]
        insights.append(KeyInsightOut(
            id="top-category",
            severity="info",
            title=f"{top['category']} was your biggest category",
            text=f"You spent ${top['total']:.2f} on {top['category']} across {top['count']} transactions{change_text}.",
            evidence=evidence,
        ))

    expenses_change = comparison["overall"]["expenses_pct_change"]
    savings_change = comparison["overall"]["savings_pct_change"]
    if expenses_change is not None and expenses_change > 15:
        insights.append(KeyInsightOut(
            id="expenses-up",
            severity="warning",
            title="Overall spending rose",
            text=(
                f"Total expenses were up {expenses_change:.0f}% versus the previous period "
                f"(${previous_totals['expenses']:.2f} to ${totals['expenses']:.2f})."
            ),
            evidence=[],
        ))
    elif savings_change is not None and savings_change > 15 and totals["savings"] > 0:
        insights.append(KeyInsightOut(
            id="savings-up",
            severity="positive",
            title="Savings improved",
            text=f"Net savings were up {savings_change:.0f}% versus the previous period.",
            evidence=[],
        ))

    for c in totals["category_vs_budget"]:
        if not c["over_budget"]:
            continue
        evidence = [_to_evidence(t) for t in transactions if t["category"] == c["category"]][:5]
        insights.append(KeyInsightOut(
            id=f"over-budget-{c['category']}",
            severity="warning",
            title=f"{c['category']} went over budget",
            text=(
                f"${c['spent']:.2f} spent against a ${c['budget']:.2f} budget - "
                f"${c['spent'] - c['budget']:.2f} over."
            ),
            evidence=evidence,
        ))

    for u in unusual[:3]:
        insights.append(KeyInsightOut(
            id=f"unusual-{u.evidence.id}",
            severity="warning",
            title=f"Unusually large {u.evidence.category} transaction",
            text=(
                f"${abs(u.evidence.amount):.2f} at {u.evidence.merchant or 'an unknown merchant'} "
                f"on {u.evidence.date} - about {u.z_score:.1f}x your typical {u.evidence.category} spend."
            ),
            evidence=[u.evidence],
        ))

    for r in recurring[:3]:
        insights.append(KeyInsightOut(
            id=f"recurring-{r.merchant}",
            severity="info",
            title=f"Possible {r.frequency} charge: {r.merchant}",
            text=f"~${r.average_amount:.2f} {r.frequency}, seen {r.occurrences} times, last on {r.last_seen}.",
            evidence=r.evidence,
        ))

    for s in saving_opportunities[:3]:
        insights.append(KeyInsightOut(
            id=f"saving-{s.category}",
            severity="positive",
            title=f"Saving opportunity: {s.category}",
            text=s.suggestion,
            evidence=s.evidence,
        ))

    return insights


def _ai_statement_narrative(start_date, end_date, totals, comparison, unusual, recurring, saving_opportunities):
    """A short free-text paragraph on top of the cited key_insights above -
    real LLM output when OPENAI_API_KEY is configured (same chatbot_
    prototype.call_llm path /chat/messages uses), and an honest deterministic
    fallback built from the same facts when it isn't. ai_generated tells the
    frontend which one it got, so the UI never implies an LLM ran when it
    didn't."""
    bullet_lines = [f"Period {start_date} to {end_date}."]
    bullet_lines.append(
        f"Income ${totals['income']:.2f}, expenses ${totals['expenses']:.2f}, "
        f"net savings ${totals['savings']:.2f}."
    )
    expenses_change = comparison["overall"]["expenses_pct_change"]
    if expenses_change is not None:
        direction = "up" if expenses_change > 0 else "down"
        bullet_lines.append(
            f"Expenses are {direction} {abs(expenses_change):.0f}% versus the previous equivalent period."
        )
    if unusual:
        bullet_lines.append(f"{len(unusual)} unusually large transaction(s) were flagged.")
    if recurring:
        names = ", ".join(r.merchant for r in recurring[:3])
        bullet_lines.append(f"Possible recurring charges detected: {names}.")
    if saving_opportunities:
        bullet_lines.append(
            f"{len(saving_opportunities)} category(ies) are over budget with a specific saving suggestion."
        )

    deterministic_summary = " ".join(bullet_lines)

    prompt = (
        "You are a personal finance assistant. In 2-3 short sentences, summarise this "
        "financial statement period in plain, encouraging language. Use ONLY the facts "
        "below - do not invent numbers or claims not listed here.\n\n" + "\n".join(bullet_lines)
    )
    llm_answer = call_llm(prompt)
    if llm_answer:
        return llm_answer, True
    return deterministic_summary, False


def _ai_statement_csv(full_name, start_date, end_date, income, expenses, savings, savings_rate,
                       category_rows, transactions, ai_summary, insight_lines):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["AI Finance Advisor - AI Statement Insights"])
    writer.writerow(["Account holder", full_name])
    writer.writerow(["Period", f"{start_date.isoformat()} to {end_date.isoformat()}"])
    writer.writerow([])
    writer.writerow(["AI Summary"])
    writer.writerow([ai_summary])
    writer.writerow([])
    writer.writerow(["AI Key Insights"])
    for line in insight_lines:
        writer.writerow([line])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total income", f"{income:.2f}"])
    writer.writerow(["Total expenses", f"{expenses:.2f}"])
    writer.writerow(["Net savings", f"{savings:.2f}"])
    writer.writerow(["Savings rate", f"{savings_rate:.1f}%" if savings_rate is not None else "n/a"])
    writer.writerow([])
    writer.writerow(["Spending by category"])
    writer.writerow(["Category", "Total spent"])
    for category, total in category_rows:
        writer.writerow([category, f"{total:.2f}"])
    writer.writerow([])
    writer.writerow(["Transactions"])
    writer.writerow(["Date", "Category", "Merchant", "Amount"])
    for t in transactions:
        writer.writerow([t["date"], t["category"], t["merchant"], f"{t['amount']:.2f}"])
    return buf.getvalue()


def _ai_statement_pdf(full_name, start_date, end_date, income, expenses, savings, savings_rate,
                       category_rows, transactions, ai_summary, insight_lines):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PDF export needs the 'reportlab' package, which isn't installed yet. "
            "Run: pip install -r requirements.txt (then restart the backend). "
            "CSV export works right now without it."
        ) from exc

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("AI Finance Advisor - AI Statement Insights", styles["Title"]),
        Paragraph(f"Account holder: {full_name}", styles["Normal"]),
        Paragraph(f"Period: {start_date.isoformat()} to {end_date.isoformat()}", styles["Normal"]),
        Spacer(1, 6 * mm),
        Paragraph("AI Summary", styles["Heading2"]),
        Paragraph(ai_summary, styles["Normal"]),
        Spacer(1, 6 * mm),
    ]

    if insight_lines:
        elements.append(Paragraph("AI Key Insights", styles["Heading2"]))
        elements.append(ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in insight_lines],
            bulletType="bullet",
        ))
        elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Summary", styles["Heading2"]))
    summary_table = Table(
        [
            ["Total income", f"${income:,.2f}"],
            ["Total expenses", f"${expenses:,.2f}"],
            ["Net savings", f"${savings:,.2f}"],
            ["Savings rate", f"{savings_rate:.1f}%" if savings_rate is not None else "n/a"],
        ],
        colWidths=[80 * mm, 60 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Spending by category", styles["Heading2"]))
    cat_rows = [["Category", "Total spent"]]
    if category_rows:
        cat_rows += [[c, f"${v:,.2f}"] for c, v in category_rows]
    else:
        cat_rows.append(["No spending in this period", "-"])
    cat_table = Table(cat_rows, colWidths=[100 * mm, 40 * mm], repeatRows=1)
    cat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6FFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 6 * mm))

    shown = transactions[:500]
    elements.append(Paragraph(f"Transactions ({len(transactions)})", styles["Heading2"]))
    txn_rows = [["Date", "Category", "Merchant", "Amount"]]
    txn_rows += [[t["date"], t["category"], t["merchant"] or "-", f"${t['amount']:,.2f}"] for t in shown]
    txn_table = Table(txn_rows, colWidths=[25 * mm, 40 * mm, 55 * mm, 25 * mm], repeatRows=1)
    txn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6FFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(txn_table)
    if len(transactions) > len(shown):
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f"...and {len(transactions) - len(shown)} more transaction(s) not shown here - "
            "download the CSV for the complete list.",
            styles["Normal"],
        ))

    doc.build(elements)
    return buf.getvalue()


_COMPARISON_KEYWORDS = ("compare", "previous", "last month", "last period", "vs ", "versus")


@router.get("/statement/analyze", response_model=StatementAnalysisOut)
def analyze_statement(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The heart of AI Statement Insights: pick a date range, and get back a
    financial summary, category breakdown, budget comparison, a comparison
    against the immediately preceding equal-length period, unusual-spending
    and recurring-charge detection, saving opportunities, and a set of
    individually-cited key insights, plus a short AI narrative on top."""
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    period_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)

    current_transactions = load_user_transactions(db, current_user.user_id, start_date=start_date, end_date=end_date)
    current_transactions.sort(key=lambda t: t["date"])
    previous_transactions = load_user_transactions(db, current_user.user_id, start_date=prev_start, end_date=prev_end)

    budgets = load_user_budgets(db, current_user.user_id)
    current_totals = compute_period_totals(current_transactions, budgets)
    previous_totals = compute_period_totals(previous_transactions, budgets)
    comparison = compute_period_comparison(current_totals, previous_totals)

    # Unusual spending: establish "normal" per category from a longer
    # lookback window ending at end_date (more stable than stats from the
    # selected period alone, which may be short or sparse), then only
    # surface the outliers that actually fall inside the selected period.
    lookback_start = end_date - timedelta(days=180)
    lookback_transactions = load_user_transactions(db, current_user.user_id, start_date=lookback_start, end_date=end_date)
    flagged = detect_anomalies(lookback_transactions, z_threshold=2.5)
    start_iso, end_iso = start_date.isoformat(), end_date.isoformat()
    unusual = [
        UnusualTransactionOut(
            evidence=_to_evidence(f),
            z_score=f["z_score"],
            reason=(
                f"This {f['category']} transaction is unusually large compared to your "
                f"typical {f['category']} spending."
            ),
        )
        for f in flagged
        if start_iso <= f["date"] <= end_iso
    ]
    unusual.sort(key=lambda u: u.z_score, reverse=True)

    # Recurring expenses: same longer lookback, so a monthly subscription
    # shows up even when the selected period is shorter than its interval -
    # but only keep ones with an occurrence actually inside the period.
    recurring_all = detect_recurring_expenses(lookback_transactions)
    recurring_in_period = [
        r for r in recurring_all
        if any(start_iso <= t["date"] <= end_iso for t in r["transactions"])
    ]
    recurring = [
        RecurringExpenseOut(
            merchant=r["merchant"], frequency=r["frequency"], average_amount=r["average_amount"],
            occurrences=r["occurrences"], last_seen=r["last_seen"],
            evidence=[_to_evidence(t) for t in r["transactions"][-5:]],
        )
        for r in recurring_in_period
    ]

    # Saving opportunities: reuses the same over-budget + top-merchant logic
    # the chat assistant's savings suggestions use, scoped to this period's
    # transactions. Budgets are monthly, so this is most directly comparable
    # when the selected period is close to a month - the frontend says so.
    saving_suggestions = generate_savings_suggestions_detailed(current_transactions, budgets)
    saving_opportunities = []
    for s in saving_suggestions:
        evidence = [
            _to_evidence(t) for t in current_transactions
            if t["category"] == s["category"] and t["merchant"] == s["top_merchant"]
        ][:5]
        saving_opportunities.append(SavingOpportunityOut(
            category=s["category"], overspend=s["overspend"], suggestion=s["suggestion"], evidence=evidence,
        ))

    key_insights = _build_key_insights(
        current_totals, previous_totals, comparison, unusual, recurring, saving_opportunities, current_transactions,
    )
    ai_summary, ai_generated = _ai_statement_narrative(
        start_date, end_date, current_totals, comparison, unusual, recurring, saving_opportunities,
    )

    return StatementAnalysisOut(
        start_date=start_date,
        end_date=end_date,
        totals=PeriodTotalsOut(**current_totals),
        period_comparison=PeriodComparisonOut(
            previous_start_date=prev_start,
            previous_end_date=prev_end,
            overall=PeriodComparisonOverallOut(**comparison["overall"]),
            categories=[CategoryComparisonOut(**c) for c in comparison["categories"]],
        ),
        key_insights=key_insights,
        unusual_transactions=unusual,
        recurring_expenses=recurring,
        saving_opportunities=saving_opportunities,
        ai_summary=ai_summary,
        ai_generated=ai_generated,
    )


@router.post("/statement/ask", response_model=StatementAskResponse)
def ask_about_statement(
    payload: StatementAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """"Ask AI about this period" - a chat-style question restricted to the
    transactions inside the selected date range, so the model can't quietly
    reason over the user's whole history instead. Only pulls in the
    previous period's data too when the question itself asks for a
    comparison (e.g. "compare with last month")."""
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    transactions = load_user_transactions(db, current_user.user_id, start_date=payload.start_date, end_date=payload.end_date)
    budgets = load_user_budgets(db, current_user.user_id)
    totals = compute_period_totals(transactions, budgets)
    context = build_period_context_block(totals, payload.start_date, payload.end_date)

    sources = [f"Transactions in this period ({len(transactions)})", "This period's financial summary"]

    wants_comparison = any(k in payload.question.lower() for k in _COMPARISON_KEYWORDS)
    if wants_comparison:
        period_days = (payload.end_date - payload.start_date).days + 1
        prev_end = payload.start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)
        previous_transactions = load_user_transactions(db, current_user.user_id, start_date=prev_start, end_date=prev_end)
        previous_totals = compute_period_totals(previous_transactions, budgets)
        context += (
            f"\n\nPrevious period for comparison ({prev_start.isoformat()} to {prev_end.isoformat()}):\n"
            + build_period_context_block(previous_totals, prev_start, prev_end)
        )
        sources.append(f"Previous period for comparison ({len(previous_transactions)} transactions)")

    retrieved = retrieve_relevant_transactions(payload.question, transactions=transactions, known_categories=budgets.keys())
    prompt = (
        "Here is the user's financial data for the period they're asking about:\n"
        f"{context}\n\n" + build_prompt(payload.question, retrieved, budgets=budgets)
    )

    llm_answer = call_llm(prompt)
    if llm_answer:
        answer, ai_generated = llm_answer, True
        sources = [f"Transactions matching your question ({len(retrieved)})"] + sources[1:]
    else:
        answer, ai_generated = (
            "I can't reach the AI model right now, but here's what this period looks like:\n\n" + context,
            False,
        )

    return StatementAskResponse(
        answer=answer,
        sources=sources,
        evidence=[_to_evidence(t) for t in retrieved][:10],
        ai_generated=ai_generated,
    )


@router.get("/statement/report")
def download_ai_statement_report(
    start_date: date,
    end_date: date,
    format: str = Query(default="pdf", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Downloads the same AI Statement Insights analysis shown on the AI
    Insights page - summary, category breakdown, AI key insights, and the
    full transaction list - as a PDF or CSV to keep or share."""
    analysis = analyze_statement(start_date, end_date, db, current_user)
    transactions = load_user_transactions(db, current_user.user_id, start_date=start_date, end_date=end_date)
    transactions.sort(key=lambda t: t["date"])

    category_rows = [(c.category, c.total) for c in analysis.totals.category_breakdown]
    insight_lines = [f"{i.title}: {i.text}" for i in analysis.key_insights]
    filename_base = f"ai_statement_{start_date.isoformat()}_to_{end_date.isoformat()}"

    if format == "csv":
        content = _ai_statement_csv(
            current_user.full_name, start_date, end_date, analysis.totals.income, analysis.totals.expenses,
            analysis.totals.savings, analysis.totals.savings_rate, category_rows, transactions,
            analysis.ai_summary, insight_lines,
        )
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    try:
        content = _ai_statement_pdf(
            current_user.full_name, start_date, end_date, analysis.totals.income, analysis.totals.expenses,
            analysis.totals.savings, analysis.totals.savings_rate, category_rows, transactions,
            analysis.ai_summary, insight_lines,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
    )


@router.get("/statement")
def download_statement(
    start_date: date,
    end_date: date,
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Downloads a financial statement (summary + category breakdown +
    transaction list) for a date range the user picks on the AI Advisor
    page, as CSV or PDF."""
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    transactions = load_user_transactions(db, current_user.user_id, start_date=start_date, end_date=end_date)
    transactions.sort(key=lambda t: t["date"])
    income, expenses, category_rows = _statement_totals(transactions)
    savings = round(income - expenses, 2)
    savings_rate = round(savings / income * 100, 1) if income > 0 else None

    filename_base = f"statement_{start_date.isoformat()}_to_{end_date.isoformat()}"

    if format == "csv":
        content = _statement_csv(
            current_user.full_name, start_date, end_date, income, expenses, savings, savings_rate,
            category_rows, transactions,
        )
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    try:
        content = _statement_pdf(
            current_user.full_name, start_date, end_date, income, expenses, savings, savings_rate,
            category_rows, transactions,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
    )
