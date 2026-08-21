# Budgeting & Forecasting Subsystem — Design Notes

**Owner:** Parth Patel (Budgeting & Forecasting)
**Status:** Data inputs/outputs and model approach defined; prototype forecasting script
implemented against sample transaction data (see `backend/budgeting-forecasting/`).
Real `/budgets/recommend` and `/forecasts` endpoints now read live transactions and
write to the database (see `backend/api/routers/budgets.py` and `forecasts.py`).

## Purpose
Generate a personalised monthly budget per category and forecast a user's near-term
account balance, flagging when a predicted balance is likely to go low.

## Data Inputs
- `transactions` (amount, category_id, txn_date, account_id) for the trailing 3-6 months
- `bank_accounts.currency` and current balance (from bank sync)
- `categories` reference table

## Data Outputs
- `budgets` rows: one recommended amount per category per month
- `forecasts` rows: predicted balance per day for the next 14-30 days, with a
  lower/upper confidence bound

## Model Approach (prototype stage)
- Aggregate transactions by category and month to produce historical spend per category.
- Recommended budget per category = weighted average of the last 3 months' spend,
  with a configurable saving-target adjustment (e.g. -5% to nudge reduction).
- Balance forecasting uses Facebook Prophet on the daily net cash-flow series
  (income − expenses), producing a forecast with confidence intervals. A simple
  moving-average fallback is included for accounts with too little history for Prophet.
- Anomaly flags (feeding the `anomalies` table) are produced by comparing each new
  transaction's amount to a rolling per-category mean and standard deviation; a
  z-score above a threshold (e.g. 3) is flagged for review.

## Current Progress
- [x] Requirements for this subsystem confirmed against the proposal's scope (Section 5)
- [x] Data inputs/outputs defined against the shared schema (see `db/schema.sql`)
- [x] Prototype script (`forecast_prototype.py`) built and tested against a sample CSV
- [x] Prophet-based balance forecast (`prophet_forecast`/`forecast_balance`), with
  automatic fallback to the moving-average method when Prophet isn't installed or
  there isn't enough history
- [x] Unit tests for the anomaly detection function (`test_forecast_prototype.py`, pytest)
- [x] `POST /budgets/recommend` implemented in `backend/api/routers/budgets.py`: reads
  real transactions grouped by category/month, computes a recency-weighted average
  spend per category with a savings-target reduction, and upserts into `budgets`
- [x] `POST /forecasts` implemented in `backend/api/routers/forecasts.py`: builds the
  account's daily net cash-flow from real transactions, runs `forecast_balance()`
  (Prophet if available, moving-average fallback otherwise), and stores the result
  into `forecasts`
- [ ] Tuning of the anomaly threshold using a larger sample dataset
- [ ] Wire anomaly detection (`detect_anomalies`) into a real endpoint/table write
- [ ] Prophet not yet installed in `backend/api/requirements.txt` (moving-average
  fallback is exercised by default; add it once we want real confidence intervals)

## Next Steps
- Add unit tests for the budget-recommendation calculation.
- Add a real `GET /budgets` and `GET /forecasts` for listing stored results.
