import { useEffect, useState } from "react";
import { fetchFinancialSummary } from "../lib/insights";

function scoreLabel(score) {
  if (score === null || score === undefined) return "No data yet";
  if (score >= 75) return "Healthy";
  if (score >= 50) return "Okay";
  return "Needs attention";
}

function scoreColor(score) {
  if (score === null || score === undefined) return "var(--color-text-faint)";
  if (score >= 75) return "var(--color-success-text)";
  if (score >= 50) return "var(--color-warning-text)";
  return "var(--color-error-text)";
}

export default function FinancialSummaryCards() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchFinancialSummary()
      .then(setSummary)
      .catch((err) => setError(err.message || "Failed to load financial summary"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading summary...</p>;
  if (error) return <p className="status-banner status-error">{error}</p>;
  if (!summary || summary.transaction_count === 0) {
    return (
      <p className="empty-state">
        No transactions yet this month - sync a bank account, add a transaction, or upload a
        receipt to see your summary and health score here.
      </p>
    );
  }

  const overBudgetCount = summary.category_vs_budget.filter((c) => c.over_budget).length;

  const topDelta = summary.category_deltas[0];

  return (
    <div className="stat-tiles">
      <div className="stat-tile">
        <span className="stat-tile-label">Financial health score</span>
        <span className="stat-tile-value" style={{ color: scoreColor(summary.health_score) }}>
          {summary.health_score ?? "-"}
        </span>
        <span className="stat-tile-sub">{scoreLabel(summary.health_score)}</span>
      </div>
      <div className="stat-tile">
        <span className="stat-tile-label">Income this month</span>
        <span className="stat-tile-value">${summary.income.toFixed(2)}</span>
      </div>
      <div className="stat-tile">
        <span className="stat-tile-label">Expenses this month</span>
        <span className="stat-tile-value">${summary.expenses.toFixed(2)}</span>
      </div>
      <div className="stat-tile">
        <span className="stat-tile-label">Savings this month</span>
        <span className="stat-tile-value">${summary.savings.toFixed(2)}</span>
        {summary.savings_rate !== null && (
          <span className="stat-tile-sub">{summary.savings_rate.toFixed(1)}% savings rate</span>
        )}
      </div>
      {summary.top_category && (
        <div className="stat-tile">
          <span className="stat-tile-label">Biggest category</span>
          <span className="stat-tile-value stat-tile-value-text">{summary.top_category}</span>
          <span className="stat-tile-sub">
            ${topDelta.this_month.toFixed(2)} this month
            {topDelta.pct_change !== null &&
              ` (${topDelta.pct_change > 0 ? "up" : "down"} ${Math.abs(topDelta.pct_change).toFixed(0)}% vs last month)`}
          </span>
        </div>
      )}
      {overBudgetCount > 0 && (
        <div className="stat-tile stat-tile-alert">
          <span className="stat-tile-label">Budget alerts</span>
          <span className="stat-tile-value">{overBudgetCount}</span>
          <span className="stat-tile-sub">
            {overBudgetCount === 1 ? "category is" : "categories are"} over budget
          </span>
        </div>
      )}
    </div>
  );
}
