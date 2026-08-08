"""
Budgeting & Forecasting Subsystem - Prototype
Owner: Parth Patel

Loads a sample transaction CSV, aggregates net daily cash flow, and forecasts the
account balance for the next N days. Falls back to a simple moving-average forecast
if Prophet is not available or there is not enough history.

Usage:
    python forecast_prototype.py --input sample_transactions.csv --days 14
"""

import argparse
import csv
from datetime import datetime, timedelta
from statistics import mean, pstdev

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


def load_transactions(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "date": datetime.strptime(r["date"], "%Y-%m-%d").date(),
                "amount": float(r["amount"]),
                "category": r.get("category", "uncategorised"),
            })
    return rows


def daily_net_cashflow(rows):
    by_day = {}
    for r in rows:
        by_day.setdefault(r["date"], 0.0)
        by_day[r["date"]] += r["amount"]
    return dict(sorted(by_day.items()))


def moving_average_forecast(daily_totals, days_ahead, window=14):
    values = list(daily_totals.values())
    last_date = max(daily_totals.keys())
    recent = values[-window:] if len(values) >= window else values
    avg_daily_change = mean(recent) if recent else 0.0
    running_balance = sum(values)  # naive running balance from the sample data

    forecast = []
    for i in range(1, days_ahead + 1):
        running_balance += avg_daily_change
        forecast.append({
            "date": last_date + timedelta(days=i),
            "predicted_balance": round(running_balance, 2),
        })
    return forecast


def prophet_forecast(daily_totals, days_ahead, min_history_days=10):
    """Forecast running balance using Facebook Prophet.

    Returns None (so the caller can fall back to the moving-average method)
    if Prophet isn't installed or there isn't enough history to fit on.
    """
    if not PROPHET_AVAILABLE or len(daily_totals) < min_history_days:
        return None

    import pandas as pd

    dates = sorted(daily_totals.keys())
    running_balance = 0.0
    balances = []
    for d in dates:
        running_balance += daily_totals[d]
        balances.append(running_balance)

    df = pd.DataFrame({"ds": dates, "y": balances})
    model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
    model.fit(df)

    future = model.make_future_dataframe(periods=days_ahead)
    result = model.predict(future)

    forecast = []
    for _, row in result.tail(days_ahead).iterrows():
        forecast.append({
            "date": row["ds"].date(),
            "predicted_balance": round(row["yhat"], 2),
            "lower_bound": round(row["yhat_lower"], 2),
            "upper_bound": round(row["yhat_upper"], 2),
        })
    return forecast


def forecast_balance(daily_totals, days_ahead, use_prophet=True):
    """Forecast the account balance for the next `days_ahead` days.

    Tries Prophet first when available and there's enough history; falls back
    to the moving-average method otherwise. Returns (forecast, method_used).
    """
    if use_prophet:
        prophet_result = prophet_forecast(daily_totals, days_ahead)
        if prophet_result is not None:
            return prophet_result, "prophet"
    return moving_average_forecast(daily_totals, days_ahead), "moving_average"


def detect_anomalies(rows, z_threshold=3.0):
    """Flag transactions whose amount is a z-score outlier within their own category."""
    by_category = {}
    for r in rows:
        by_category.setdefault(r["category"], []).append(r["amount"])

    anomalies = []
    for r in rows:
        cat_values = by_category[r["category"]]
        if len(cat_values) < 3:
            continue
        m = mean(cat_values)
        sd = pstdev(cat_values) or 1e-6
        z = abs((r["amount"] - m) / sd)
        if z >= z_threshold:
            anomalies.append({**r, "z_score": round(z, 2)})
    return anomalies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="sample_transactions.csv")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--no-prophet", action="store_true",
                         help="Skip Prophet and always use the moving-average forecast.")
    args = parser.parse_args()

    rows = load_transactions(args.input)
    daily_totals = daily_net_cashflow(rows)

    print(f"Loaded {len(rows)} transactions across {len(daily_totals)} days.")

    forecast, method = forecast_balance(daily_totals, args.days, use_prophet=not args.no_prophet)
    print(f"\nForecast for the next {args.days} days (method: {method}):")
    for f in forecast:
        print(f"  {f['date']}: predicted balance = {f['predicted_balance']}")

    anomalies = detect_anomalies(rows)
    print(f"\nDetected {len(anomalies)} potential anomalies:")
    for a in anomalies:
        print(f"  {a['date']} | {a['category']} | amount={a['amount']} | z={a['z_score']}")


if __name__ == "__main__":
    main()
