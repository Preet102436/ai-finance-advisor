"""
Unit tests for the anomaly detection function in forecast_prototype.py
Owner: Parth Patel

Run with:
    pytest backend/budgeting-forecasting/test_forecast_prototype.py
"""

from datetime import date

from forecast_prototype import detect_anomalies


def make_row(day, amount, category="groceries"):
    return {"date": date(2026, 7, day), "amount": amount, "category": category}


def test_no_anomalies_when_amounts_are_consistent():
    rows = [make_row(d, -50.0) for d in range(1, 6)]
    assert detect_anomalies(rows) == []


def test_flags_outlier_amount_in_category():
    rows = [make_row(d, -50.0) for d in range(1, 11)]
    rows.append(make_row(11, -900.0))

    anomalies = detect_anomalies(rows)

    assert len(anomalies) == 1
    assert anomalies[0]["amount"] == -900.0
    assert anomalies[0]["z_score"] > 3.0


def test_ignores_categories_with_too_few_transactions():
    rows = [make_row(1, -20.0, category="dining"), make_row(2, -800.0, category="dining")]
    assert detect_anomalies(rows) == []


def test_anomalies_are_scoped_per_category():
    rows = [make_row(d, -50.0, category="groceries") for d in range(1, 6)]
    rows += [make_row(d, -5000.0, category="rent") for d in range(1, 4)]

    anomalies = detect_anomalies(rows)

    assert anomalies == []


def test_custom_threshold_flags_smaller_deviations():
    rows = [make_row(d, -50.0) for d in range(1, 6)]
    rows.append(make_row(6, -120.0))

    assert detect_anomalies(rows, z_threshold=3.0) == []
    assert len(detect_anomalies(rows, z_threshold=1.0)) == 1
