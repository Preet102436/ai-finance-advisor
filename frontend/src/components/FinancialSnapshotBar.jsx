import { useEffect, useState } from "react";
import { fetchFinancialSummary } from "../lib/insights";

export default function FinancialSnapshotBar() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    fetchFinancialSummary()
      .then(setSummary)
      .catch(() => {
        // Snapshot bar is a nice-to-have above the chat - fail silently and
        // just don't render it rather than showing an error banner here.
      });
  }, []);

  if (!summary || summary.transaction_count === 0) return null;

  const topDelta = summary.category_deltas && summary.category_deltas[0];

  return (
    <div className="financial-snapshot-bar">
      <div className="snapshot-item">
        <span className="snapshot-label">Health score</span>
        <span className="snapshot-value">{summary.health_score ?? "-"}</span>
      </div>
      <div className="snapshot-divider" aria-hidden="true" />
      <div className="snapshot-item">
        <span className="snapshot-label">Income</span>
        <span className="snapshot-value">${summary.income.toFixed(2)}</span>
      </div>
      <div className="snapshot-divider" aria-hidden="true" />
      <div className="snapshot-item">
        <span className="snapshot-label">Expenses</span>
        <span className="snapshot-value">${summary.expenses.toFixed(2)}</span>
      </div>
      <div className="snapshot-divider" aria-hidden="true" />
      <div className="snapshot-item">
        <span className="snapshot-label">Savings</span>
        <span className="snapshot-value">${summary.savings.toFixed(2)}</span>
      </div>
      {summary.top_category && topDelta && (
        <>
          <div className="snapshot-divider" aria-hidden="true" />
          <div className="snapshot-item">
            <span className="snapshot-label">Biggest category</span>
            <span className="snapshot-value snapshot-value-text">{summary.top_category}</span>
          </div>
        </>
      )}
    </div>
  );
}
